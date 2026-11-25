#!/bin/sh
# coverage-driven tour loop on the villa4 scene: lens rooms -> stops (select) -> order -> prune (refine) -> walking aim -> plan -> audit -> redundancy. usage: scripts/wt_chain.sh <audit id>
set -e
cd /home/omar/archpipe/lanes/WT
python scripts/lens_rooms.py knowledge/flyaudit/wt-villa4-tour/frames.json
scripts/wt_py.sh scripts/wt_cover.py select ${SCENE:-out/wt/villa4/scene.json} 2>&1 | grep -E "stations;"
scripts/wt_py.sh scripts/tour_order.py | tail -2
scripts/wt_py.sh scripts/wt_cover.py refine ${SCENE:-out/wt/villa4/scene.json} 2>&1 | grep -E "^iter|^restore" | tail -3
scripts/wt_py.sh scripts/tour_aim.py ${SCENE:-out/wt/villa4/scene.json} > /tmp/ta.log 2>&1; tail -1 /tmp/ta.log
python scripts/wt_plan.py | grep -E "^frames|^cov|^stair"
scripts/wt_py.sh scripts/wt_cover.py measure out/wt/villa4/plan-only.json 2>&1 | tail -1
scripts/wt_audit.sh out/wt/villa4/plan-only.json "$1" | tail -1
python scripts/wt_summary.py out/wt/audits/"$1" knowledge/flyaudit/wt-villa4-tour | head -50
