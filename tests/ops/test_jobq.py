"""Queue logic: status, dead-runner relaunch, timeout, GPU serialisation (ops/workstation/jobq.py)."""
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("jobq", Path(__file__).resolve().parents[2] / "ops/workstation/jobq.py")
jobq = importlib.util.module_from_spec(SPEC)
sys.modules["jobq"] = jobq
SPEC.loader.exec_module(jobq)

PY = sys.executable


def py(code):
    return [PY, "-c", code]


class JobqTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = self.root / "graphics.lock"

    def queue(self, **kw):
        return jobq.Queue(self.root / "q", self.lock, **kw)

    def run_all(self, q):
        """Tick with a synchronous launcher until nothing is started."""
        q.launcher = q.execute
        for _ in range(6):
            if not q.tick()["started"]:
                break

    def test_submit_is_idempotent_and_runs(self):
        q = self.queue()
        a = q.submit(py("print('hi')"), job_id="j1")
        b = q.submit(py("print('other')"), job_id="j1")
        self.assertEqual((a, b), ("j1", "j1"))
        self.assertEqual(q.status("j1")["state"], "queued")
        self.run_all(q)
        st = q.status("j1")
        self.assertEqual((st["state"], st["exit_code"], st["attempt"]), ("done", 0, 1))
        self.assertIn("hi", (q.jobdir("j1") / "job.log").read_text())
        self.assertEqual([p.name for p in q.jobdir("j1").glob("*.tmp")], [])

    def test_nonzero_exit_is_final_not_retried(self):
        q = self.queue()
        q.submit(py("raise SystemExit(3)"), job_id="bad", max_attempts=3)
        self.run_all(q)
        st = q.status("bad")
        self.assertEqual((st["state"], st["exit_code"], st["attempt"]), ("failed", 3, 1))

    def test_timeout_fires_and_is_final(self):
        q = self.queue()
        q.submit(py("import time; time.sleep(60)"), job_id="slow", timeout_s=1, max_attempts=3)
        t0 = time.time()
        self.run_all(q)
        st = q.status("slow")
        self.assertEqual(st["state"], "timeout")
        self.assertEqual(st["attempt"], 1)
        self.assertLess(time.time() - t0, 30)

    def test_dead_runner_without_status_is_relaunched(self):
        # the villa_render bug: a pid file with no status wedged the job forever
        q = self.queue(alive=lambda pid, start=None: False)
        q.launcher = lambda j: None            # launch "succeeds" but nothing ever runs
        q.submit(py("print('x')"), job_id="dead", max_attempts=2)
        q.tick()
        st = q.set_status("dead", runner_pid=424242, state="running")   # runner claims it, then dies
        self.assertEqual(st["attempt"], 1)
        out = q.tick()
        self.assertEqual(out["reaped"], ["dead"])
        self.assertEqual(out["started"], ["dead"])
        self.assertEqual(q.status("dead")["attempt"], 2)
        self.assertEqual(q.status("dead")["state"], "launching")
        # second death spends the last attempt
        q.set_status("dead", runner_pid=424242, state="running")
        q.tick()
        st = q.status("dead")
        self.assertEqual(st["state"], "died")
        self.assertIn("attempts spent", st["reason"])
        states = [json.loads(line)["state"] for line in (q.jobdir("dead") / "history.jsonl").read_text().splitlines()]
        self.assertEqual(states.count("queued"), 2)  # submit + one relaunch

    def test_launch_that_never_claims_is_reaped_after_grace(self):
        q = self.queue()
        q.launcher = lambda j: None
        q.submit(py("pass"), job_id="stuck")
        q.tick()
        self.assertEqual(q.tick()["reaped"], [])                      # still within the grace period
        q.set_status("stuck", launched=time.time() - jobq.LAUNCH_GRACE_S - 1)
        self.assertEqual(q.tick()["reaped"], ["stuck"])

    def test_live_runner_is_left_alone(self):
        q = self.queue(alive=lambda pid, start=None: True)
        q.launcher = lambda j: None
        q.submit(py("pass"), job_id="live")
        q.tick()
        q.set_status("live", runner_pid=1, state="running")
        self.assertEqual(q.tick(), {"reaped": [], "started": []})
        self.assertEqual(q.status("live")["state"], "running")

    @unittest.skipIf(os.name == "nt", "signal death is a POSIX notion")
    def test_command_killed_by_signal_is_requeued(self):
        q = self.queue()
        q.submit(py("import os,signal; os.kill(os.getpid(), signal.SIGKILL)"), job_id="oom", max_attempts=2)
        q.launcher = q.execute
        q.tick()
        st = q.status("oom")
        self.assertEqual(st["state"], "queued")
        self.assertIn("signal 9", st["reason"])
        q.tick()
        self.assertEqual(q.status("oom")["state"], "died")

    def test_scheduler_starts_one_gpu_job_in_submit_order_but_cpu_in_parallel(self):
        q = self.queue(cpu_slots=2)
        q.launcher = lambda j: None
        q.submit(py("pass"), job_id="g1", gpu=True)
        q.submit(py("pass"), job_id="g2", gpu=True)
        for i in range(3):
            q.submit(py("pass"), job_id=f"c{i}")
        started = q.tick()["started"]
        self.assertEqual([j for j in started if j.startswith("g")], ["g1"])
        self.assertEqual(len([j for j in started if j.startswith("c")]), 2)
        self.assertEqual(q.status("g2")["state"], "queued")

    def test_gpu_lock_serialises_runners_even_if_the_scheduler_is_bypassed(self):
        log = self.root / "spans.txt"
        code = ("import time,sys; f=open(sys.argv[1],'a'); f.write('start %.3f\\n'%time.time()); f.flush(); "
                "time.sleep(0.8); f.write('end %.3f\\n'%time.time()); f.close()")
        q = self.queue()
        for j in ("a", "b"):
            q.submit(py(code) + [str(log)], job_id=j, gpu=True)
            q.set_status(j, state="launching", attempt=1)
        threads = [threading.Thread(target=q.execute, args=(j,)) for j in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        events = [line.split() for line in log.read_text().splitlines()]
        self.assertEqual([e[0] for e in events], ["start", "end", "start", "end"])  # never start,start
        self.assertLessEqual(float(events[1][1]), float(events[2][1]))
        self.assertEqual({q.status(j)["state"] for j in "ab"}, {"done"})

    def test_retry_requeues_a_failed_job_but_not_a_done_one(self):
        q = self.queue()
        q.submit(py("raise SystemExit(1)"), job_id="r")
        self.run_all(q)
        self.assertEqual(q.status("r")["state"], "failed")
        q.submit(py("x"), job_id="r", retry=True)
        self.assertEqual((q.status("r")["state"], q.status("r")["attempt"]), ("queued", 0))
        q.submit(py("pass"), job_id="ok")
        self.run_all(q)
        q.submit(py("pass"), job_id="ok", retry=True)
        self.assertEqual(q.status("ok")["state"], "done")

    def test_cancel_before_start(self):
        q = self.queue()
        q.submit(py("pass"), job_id="c")
        q.cancel("c")
        self.assertEqual(q.status("c")["state"], "cancelled")
        self.assertEqual(q.tick()["started"], [])


if __name__ == "__main__":
    unittest.main()
