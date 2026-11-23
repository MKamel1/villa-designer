#!/usr/bin/env python3
"""jobq: a small durable job queue for the workstation (stdlib only).

One directory per job under <root>/jobs/<id>/:
  spec.json    what to run (argv, cwd, env, gpu, timeout_s, max_attempts)
  status.json  current state, written atomically (tmp file + os.replace)
  job.log      the job's stdout+stderr (appended across attempts)
  history.jsonl  one line per state change worth keeping

States: queued -> launching -> waiting_lock -> running -> done | failed | timeout | died | cancelled
A job whose runner or command died WITHOUT writing a terminal status (reboot, kill -9, OOM) is put
back in `queued` by the daemon until max_attempts is spent, then `died`. Exit by signal that we did
not send counts as a death. A timeout and an ordinary nonzero exit are final.

GPU jobs hold one slot lock for the whole run: slot 0 is <gpu lock> itself (so tools that flock
graphics.lock directly exclude exactly one slot), slot k>0 is <gpu lock>.k. The daemon admits up to
--gpu-slots GPU jobs at once, strictly in submit order (a head job that cannot start blocks the later
ones), and only while nvidia-smi shows >= --vram-mb free (reserving that for jobs still starting) plus a
1 GB margin. --exclusive jobs hold every slot, i.e. run with no other queue GPU job. CPU jobs run up to
--cpu-slots at once.

    jobq submit [--id ID] [--gpu [--vram-mb M] [--exclusive]] [--timeout S] [--attempts N] [--cwd D] [--env K=V] [--retry] -- argv...
    jobq status ID | list | wait ID | log ID | cancel ID | daemon | tick
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows (the tests run there too)
    fcntl = None
    import msvcrt

TERMINAL = {"done", "failed", "timeout", "died", "cancelled"}
ACTIVE = {"launching", "waiting_lock", "running"}
LAUNCH_GRACE_S = 30
DEFAULT_VRAM_MB = 6000
VRAM_MARGIN_MB = 1024
VRAM_RESERVE_S = 60  # a freshly launched job's VRAM is not on nvidia-smi yet; reserve it this long
# Dirs put in front of PATH for every job: the service's own PATH lacks them (`blender` died with FileNotFoundError).
EXTRA_PATH = [Path.home() / "opt" / "blender", Path.home() / "archpipe" / "envs" / "laneP-venv" / "bin"]
DEFAULT_ROOT = Path(os.environ.get("JOBQ_ROOT", Path.home() / "archpipe" / "queue"))
DEFAULT_GPU_LOCK = Path(os.environ.get("JOBQ_GPU_LOCK", Path.home() / "archpipe" / "locks" / "graphics.lock"))


def now() -> float:
    return time.time()


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---- process helpers -------------------------------------------------------------------------

def proc_start(pid: int):
    """Start-time token of a process (guards against pid reuse). None where unavailable."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat.rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def pid_alive(pid, start=None) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(handle, ctypes.byref(code))
        k32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    current = proc_start(pid)
    if current is not None and Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
        return False  # zombie: dead, only unreaped
    return start is None or current is None or current == start


def kill_group(pid, sig=signal.SIGTERM) -> None:
    if not pid or os.name == "nt":
        if pid:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGTERM)
        return
    with contextlib.suppress(OSError):
        os.killpg(pid, sig)


def _try_lock(fh) -> bool:
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def _unlock(fh) -> None:
    if fcntl:
        fcntl.flock(fh, fcntl.LOCK_UN)
    else:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)


def slot_paths(gpu_lock: Path, n: int) -> list:
    return [Path(gpu_lock)] + [Path(f"{gpu_lock}.{k}") for k in range(1, n)]


@contextlib.contextmanager
def gpu_locks(gpu_lock: Path, n_slots: int, exclusive=False, poll=0.2):
    """Hold one free slot lock (or all of them, if exclusive); block, polling, until available.
    Process death releases them. Old runners hold only slot 0, which stays compatible."""
    paths = slot_paths(gpu_lock, n_slots)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    held = {}
    try:
        while True:
            for path in paths:
                if path in held:
                    continue
                fh = open(path, "a+b")
                if _try_lock(fh):
                    held[path] = fh
                    if not exclusive:
                        break
                else:
                    fh.close()
            if len(held) >= (len(paths) if exclusive else 1):
                break
            time.sleep(poll)
        yield
    finally:
        for fh in held.values():
            with contextlib.suppress(OSError):
                _unlock(fh)
            fh.close()


def vram_free_mb():
    """Free VRAM of GPU 0 from nvidia-smi, or None if it cannot be read (guard then does not apply)."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
        return int(out.splitlines()[0].strip())
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


# ---- queue ------------------------------------------------------------------------------------

class Queue:
    def __init__(self, root=DEFAULT_ROOT, gpu_lock=DEFAULT_GPU_LOCK, cpu_slots=2, launcher=None, alive=pid_alive,
                 gpu_slots=3, vram_free=vram_free_mb):
        self.root = Path(root)
        self.gpu_lock = Path(gpu_lock)
        self.cpu_slots = cpu_slots
        self.launcher = launcher or self._spawn_wrapper
        self.alive = alive
        self.gpu_slots = gpu_slots
        self.vram_free = vram_free

    def jobdir(self, job_id: str) -> Path:
        return self.root / "jobs" / job_id

    def status(self, job_id: str):
        return read_json(self.jobdir(job_id) / "status.json")

    def spec(self, job_id: str):
        return read_json(self.jobdir(job_id) / "spec.json")

    def set_status(self, job_id: str, **changes) -> dict:
        st = self.status(job_id) or {"id": job_id}
        st.update(changes)
        st["updated"] = now()
        atomic_write(self.jobdir(job_id) / "status.json", st)
        with open(self.jobdir(job_id) / "history.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": st["updated"], "state": st["state"], "attempt": st.get("attempt", 0),
                                 "reason": st.get("reason")}) + "\n")
        return st

    def submit(self, argv, job_id=None, gpu=False, timeout_s=3600, max_attempts=2, cwd=None, env=None,
               retry=False, vram_mb=DEFAULT_VRAM_MB, exclusive=False) -> str:
        """Idempotent: an existing job id returns as-is unless it ended badly and retry is set."""
        argv = [str(a) for a in argv]
        if not argv:
            raise ValueError("no command")
        job_id = job_id or hashlib.sha256(json.dumps([argv, cwd, env, gpu], sort_keys=True).encode()).hexdigest()[:16]
        if not job_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("job id must be alphanumeric with - _ .")
        existing = self.status(job_id)
        if existing:
            if retry and existing["state"] in TERMINAL - {"done"}:
                self.set_status(job_id, state="queued", attempt=0, reason="resubmitted", exit_code=None,
                                runner_pid=None, command_pid=None, finished=None)
            return job_id
        atomic_write(self.jobdir(job_id) / "spec.json",
                     {"id": job_id, "argv": argv, "gpu": bool(gpu), "timeout_s": timeout_s,
                      "max_attempts": max_attempts, "cwd": cwd, "env": env or {}, "submitted": now(),
                      "vram_mb": vram_mb, "exclusive": bool(exclusive)})
        self.set_status(job_id, state="queued", attempt=0, gpu=bool(gpu), submitted=now(),
                        timeout_s=timeout_s, max_attempts=max_attempts, vram_mb=vram_mb,
                        exclusive=bool(exclusive))
        return job_id

    def job_ids(self):
        d = self.root / "jobs"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []

    def cancel(self, job_id: str) -> None:
        st = self.status(job_id)
        if not st or st["state"] in TERMINAL:
            return
        self.set_status(job_id, state="cancelled", reason="cancelled by user")
        if st.get("command_pid"):
            kill_group(st["command_pid"])

    # -- scheduler --
    def reap(self) -> list:
        """Find active jobs whose runner is gone without a terminal status; requeue or mark died."""
        reaped = []
        for job_id in self.job_ids():
            st = self.status(job_id)
            if not st or st["state"] not in ACTIVE:
                continue
            runner = st.get("runner_pid")
            if runner:
                if self.alive(runner, st.get("runner_start")):
                    continue
            elif now() - st.get("launched", 0) < LAUNCH_GRACE_S:
                continue
            # runner is dead: make sure its command is too (it would otherwise outlive the GPU lock)
            cmd = st.get("command_pid")
            if cmd and self.alive(cmd, st.get("command_start")):
                kill_group(cmd, signal.SIGKILL)
            self._requeue_or_die(job_id, st, f"runner died in state {st['state']}")
            reaped.append(job_id)
        return reaped

    def _requeue_or_die(self, job_id: str, st: dict, why: str) -> None:
        spec = self.spec(job_id) or {}
        if st.get("attempt", 1) < spec.get("max_attempts", 1):
            self.set_status(job_id, state="queued", reason=why + "; relaunching", runner_pid=None, command_pid=None)
        else:
            self.set_status(job_id, state="died", reason=why + "; attempts spent", finished=now(),
                            runner_pid=None, command_pid=None)

    def tick(self) -> dict:
        reaped = self.reap()
        sts = {j: self.status(j) for j in self.job_ids()}
        active = [j for j, s in sts.items() if s and s["state"] in ACTIVE]
        gpu_active = [j for j in active if sts[j].get("gpu")]
        cpu_busy = len(active) - len(gpu_active)
        queued = sorted((j for j, s in sts.items() if s and s["state"] == "queued"),
                        key=lambda j: sts[j].get("submitted", 0))
        started = []
        gpu_blocked = False  # submit-order fairness: once the head GPU job waits, later ones wait too
        cache = [None]  # nvidia-smi read once per tick
        for j in queued:
            if sts[j].get("gpu"):
                if gpu_blocked or not self._gpu_admits(j, sts, gpu_active, cache):
                    gpu_blocked = True
                    continue
                gpu_active.append(j)
                sts[j] = dict(sts[j], launched=now(), run_started=None)  # so later admits this tick reserve its VRAM
            else:
                if cpu_busy >= self.cpu_slots:
                    continue
                cpu_busy += 1
            attempt = sts[j].get("attempt", 0) + 1
            self.set_status(j, state="launching", attempt=attempt, launched=now(), runner_pid=None,
                            command_pid=None, reason=None)
            self.launcher(j)
            started.append(j)
        return {"reaped": reaped, "started": started}

    def _gpu_admits(self, j, sts, gpu_active, free_cache) -> bool:
        excl = bool(sts[j].get("exclusive"))
        if any(sts[a].get("exclusive") for a in gpu_active):
            return False
        if len(gpu_active) >= self.gpu_slots or (excl and gpu_active):
            return False
        need = sts[j].get("vram_mb", DEFAULT_VRAM_MB) + VRAM_MARGIN_MB
        if free_cache[0] is None:
            free_cache[0] = self.vram_free()
        free = free_cache[0]
        if free is None:
            return True  # nvidia-smi unreadable: slots alone limit us
        # ponytail: reservation window is time-based; track per-pid VRAM if over-admission shows up
        reserved = sum(sts[a].get("vram_mb", DEFAULT_VRAM_MB) for a in gpu_active
                       if now() - (sts[a].get("run_started") or sts[a].get("launched") or 0) < VRAM_RESERVE_S)
        return free - reserved >= need

    def _spawn_wrapper(self, job_id: str):
        log = open(self.jobdir(job_id) / "runner.log", "ab")
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--root", str(self.root), "--gpu-lock",
                          str(self.gpu_lock), "--gpu-slots", str(self.gpu_slots), "exec", job_id], stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         start_new_session=True, close_fds=True)

    # -- runner (one process per attempt) --
    def execute(self, job_id: str) -> dict:
        spec = self.spec(job_id)
        st = self.status(job_id)
        if not spec or not st or st["state"] != "launching":
            return st
        me = os.getpid()
        self.set_status(job_id, runner_pid=me, runner_start=proc_start(me),
                        state="waiting_lock" if spec["gpu"] else "running", started=now())
        lock = (gpu_locks(self.gpu_lock, self.gpu_slots, spec.get("exclusive", False)) if spec["gpu"]
                else contextlib.nullcontext())
        with lock:
            if (self.status(job_id) or {}).get("state") in TERMINAL:  # cancelled while waiting
                return self.status(job_id)
            return self._run_command(job_id, spec)

    def _run_command(self, job_id: str, spec: dict) -> dict:
        env = dict(os.environ, **spec.get("env", {}), JOBQ_JOB_ID=job_id, JOBQ_JOB_DIR=str(self.jobdir(job_id)))
        env["PATH"] = os.pathsep.join([str(d) for d in EXTRA_PATH if d.is_dir()] + [env.get("PATH", os.defpath)])
        started = now()
        with open(self.jobdir(job_id) / "job.log", "ab") as log:
            log.write(f"--- attempt {self.status(job_id).get('attempt')} {time.strftime('%F %T')} ---\n".encode())
            log.flush()
            kwargs = {"start_new_session": True} if os.name != "nt" else {}
            try:
                child = subprocess.Popen(spec["argv"], cwd=spec.get("cwd"), env=env, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, **kwargs)
            except OSError as exc:  # missing/unexecutable argv[0] or cwd: a verdict, not a death; retrying cannot help
                log.write(f"exec failed: {exc!r}\n".encode())
                return self.set_status(job_id, state="failed", reason=f"exec failed: {exc!r}", exit_code=None,
                                       finished=now(), seconds=0, runner_pid=None, command_pid=None)
            self.set_status(job_id, state="running", command_pid=child.pid, command_start=proc_start(child.pid),
                            run_started=started)
            timed_out = False
            try:
                code = child.wait(timeout=spec["timeout_s"])
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_group(child.pid, signal.SIGTERM)
                try:
                    code = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    kill_group(child.pid, signal.SIGKILL)
                    code = child.wait()
        finished = now()
        cur = self.status(job_id) or {}
        if cur.get("state") == "cancelled":
            return cur
        common = dict(exit_code=code, finished=finished, seconds=round(finished - started, 2),
                      runner_pid=None, command_pid=None)
        if timed_out:
            return self.set_status(job_id, state="timeout", reason=f"killed after {spec['timeout_s']}s", **common)
        if code < 0 and os.name != "nt":
            # killed by a signal nobody here sent: a death, not a verdict; requeue unless attempts are spent
            self._requeue_or_die(job_id, cur, f"command killed by signal {-code}")
            return self.status(job_id)
        return self.set_status(job_id, state="done" if code == 0 else "failed",
                               reason=None if code == 0 else f"exit {code}", **common)

    def daemon(self, interval=3.0):
        print(f"jobq daemon root={self.root} gpu_lock={self.gpu_lock}", flush=True)
        while True:
            try:
                self.tick()
            except Exception as exc:  # keep serving; a bad job dir must not stop the queue
                print("tick error:", repr(exc), flush=True)
            time.sleep(interval)


# ---- CLI --------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--gpu-lock", default=str(DEFAULT_GPU_LOCK))
    ap.add_argument("--cpu-slots", type=int, default=4)
    ap.add_argument("--gpu-slots", type=int, default=3)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--id")
    s.add_argument("--gpu", action="store_true")
    s.add_argument("--vram-mb", type=int, default=DEFAULT_VRAM_MB)
    s.add_argument("--exclusive", action="store_true", help="GPU job that must run with no other GPU job (implies --gpu)")
    s.add_argument("--timeout", type=int, default=3600)
    s.add_argument("--attempts", type=int, default=2)
    s.add_argument("--cwd")
    s.add_argument("--env", action="append", default=[])
    s.add_argument("--retry", action="store_true")
    s.add_argument("command", nargs=argparse.REMAINDER)
    for name in ("status", "wait", "log", "cancel", "exec"):
        p = sub.add_parser(name)
        p.add_argument("id")
        if name == "wait":
            p.add_argument("--poll", type=float, default=2.0)
            p.add_argument("--max-wait", type=float, default=None)
        if name == "log":
            p.add_argument("-n", type=int, default=40)
    sub.add_parser("list")
    sub.add_parser("tick")
    d = sub.add_parser("daemon")
    d.add_argument("--interval", type=float, default=3.0)
    a = ap.parse_args(argv)
    q = Queue(a.root, a.gpu_lock, a.cpu_slots, gpu_slots=a.gpu_slots)
    if a.cmd == "submit":
        cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
        env = dict(kv.split("=", 1) for kv in a.env)
        print(q.submit(cmd, a.id, a.gpu or a.exclusive, a.timeout, a.attempts, a.cwd, env, a.retry, a.vram_mb,
                       a.exclusive))
    elif a.cmd == "status":
        st = q.status(a.id)
        print(json.dumps(st, indent=2, sort_keys=True) if st else "unknown job")
        return 0 if st else 1
    elif a.cmd == "list":
        for j in q.job_ids():
            st = q.status(j) or {}
            print(f"{j}\t{st.get('state')}\tattempt={st.get('attempt')}\texit={st.get('exit_code')}\t{st.get('reason') or ''}")
    elif a.cmd == "wait":
        t0 = now()
        while True:
            st = q.status(a.id)
            if st and st["state"] in TERMINAL:
                print(json.dumps(st, sort_keys=True))
                return 0 if st["state"] == "done" else 1
            if a.max_wait is not None and now() - t0 > a.max_wait:
                return 124
            time.sleep(a.poll)
    elif a.cmd == "log":
        lines = (q.jobdir(a.id) / "job.log").read_text(errors="replace").splitlines()
        print("\n".join(lines[-a.n:]))
    elif a.cmd == "cancel":
        q.cancel(a.id)
    elif a.cmd == "tick":
        print(json.dumps(q.tick()))
    elif a.cmd == "exec":
        st = q.execute(a.id)
        return 0 if st and st.get("state") in ("done", "running") else 1
    elif a.cmd == "daemon":
        q.daemon(a.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
