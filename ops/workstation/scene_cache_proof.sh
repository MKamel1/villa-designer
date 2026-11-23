#!/usr/bin/env bash
# Time one villa_scene.py run and record the blender process's GPU SM-busy share (nvidia-smi pmon, 1 s samples).
# usage: scene_cache_proof.sh OUTDIR VIEWS [extra villa_scene args, e.g. --blend-cache DIR]
# env: SCENE (default RF's production scene.json) ; run from the repo root. Writes OUTDIR/timing.json.
set -u
OUT=$1; VIEWS=$2; shift 2
SCENE=${SCENE:-$HOME/archpipe/lanes/RF/out/RF/set/scene.json}
mkdir -p "$OUT"
nvidia-smi pmon -s u -d 1 > "$OUT/pmon.txt" 2>/dev/null & PMON=$!
t0=$(date +%s.%N)
PYTHONPATH=src NO_COLOR=1 blender -b -t 4 --python-exit-code 1 -P src/archpipe/blender/villa_scene.py -- \
  --scene "$SCENE" --views "$VIEWS" --samples "${SAMPLES:-16}" --res "${RES:-480x320}" --out "$OUT" \
  --ies-dir "${IES:-$HOME/archpipe/lanes/RF/out/RF/d4/ies}" --library-root "$HOME/archpipe/assets/library" "$@" \
  > "$OUT/blender.log" 2>&1 &
BPID=$!
wait $BPID
rc=$?
t1=$(date +%s.%N)
kill $PMON 2>/dev/null
python - "$OUT" "$t0" "$t1" "$rc" "$BPID" <<'PY'
import json, re, sys
out, t0, t1, rc, bpid = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
log = open(out + "/blender.log", errors="replace").read()
rows = [l.split() for l in open(out + "/pmon.txt") if l.strip() and not l.startswith("#")]
# only OUR blender pid (the other lanes' processes share the GPU and are excluded)
sm = [int(r[3]) for r in rows if len(r) > 3 and r[1] == bpid and r[3].isdigit()]
pid = bpid
wall = t1 - t0
import glob, os
rec = out + "/scene-receipt.json"  # written right after the scene is built (or opened from cache)
build = round(os.path.getmtime(rec) - t0, 1) if os.path.exists(rec) else None
json.dump(dict(rc=rc, wall_s=round(wall, 1), start_to_scene_ready_s=build, gpu_pid=pid, gpu_busy_samples=len(sm),
               gpu_sm_mean_while_active_pct=round(sum(sm) / len(sm), 1) if sm else None,
               gpu_busy_share_of_wall=round(sum(1 for v in sm if v > 0) / wall, 3) if sm else 0.0,
               cache=re.findall(r"SCENE CACHE [^\n]*", log)), open(out + "/timing.json", "w"), indent=1)
PY
exit $rc
