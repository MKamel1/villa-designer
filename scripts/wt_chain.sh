#!/bin/sh
# plan -> audit loop on the villa4 scene: lens rooms, 360 points, walking aim, plan, audit. usage: scripts/wt_chain.sh <audit id>
set -e
cd /home/omar/archpipe/lanes/WT
python scripts/lens_rooms.py knowledge/flyaudit/wt-villa4-tour/frames.json
python scripts/wt_plan.py > /dev/null
scripts/wt_py.sh scripts/tour_points.py > /tmp/tp.log 2>&1
python scripts/wt_plan.py > /dev/null
scripts/wt_py.sh scripts/tour_aim.py > /tmp/ta.log 2>&1; tail -1 /tmp/ta.log
python scripts/wt_plan.py | grep -E "^frames|^dir|^cov"
scripts/wt_audit.sh out/wt/villa4/plan-only.json "$1" | tail -1
python scripts/wt_summary.py out/wt/audits/"$1" knowledge/flyaudit/wt-villa4-tour | head -26
python scripts/wt_summary.py out/wt/audits/"$1" | grep -A30 "^runs"
