#!/bin/sh
# client pass 2026-11-25 (version 3 route): aim (close-ups, corridors) -> plan without doors -> audit -> dull headings -> plan -> door schedule -> plan with doors -> audits (doors open / animated).
# usage: scripts/wt_pass3.sh <id>   (audits against the villa8 scene's own door poses)
set -e
cd /home/omar/archpipe/lanes/WT
export SCENE=out/wt/villa8/scene.json
nodoors() { python - <<'PY'
import sys, json; sys.path[:0] = ['scripts', 'src']
from wt_plan import vmap
from archpipe import walkthrough_tour as WT
l, s, vm = vmap(); p = WT.plan_tour(vm, doors=False); json.dump(p, open('out/wt/villa4/plan-nodoors.json', 'w')); print('frames', len(p['frames']))
PY
}
scripts/wt_py.sh scripts/tour_aim.py $SCENE 2>&1 | tail -1
rm -f knowledge/flythrough/tour-doors.json
nodoors; scripts/wt_audit.sh out/wt/villa4/plan-nodoors.json "$1-nd" | tail -1
python scripts/wt_reaim.py out/wt/villa4/plan-nodoors.json out/wt/audits/"$1-nd"/frames.json > /dev/null
nodoors
scripts/wt_py.sh scripts/wt_doors.py schedule 2>&1 | tail -4 | cut -c1-300
python scripts/wt_plan.py | grep -E "^frames|stale"
for m in open anim; do f=""; [ $m = open ] && f="--doors-open"; PYTHONPATH=src ~/archpipe/envs/wta-venv/bin/python -m archpipe.flyaudit out/wt/villa4/plan-only.json --scene $SCENE --id "$1-$m" --out out/wt/audits $f 2>&1 | tail -2; done
