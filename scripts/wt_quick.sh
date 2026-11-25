#!/bin/sh
# aim -> plan -> audit -> summary on the current stops. usage: scripts/wt_quick.sh <audit id>
cd /home/omar/archpipe/lanes/WT
scripts/wt_py.sh scripts/tour_aim.py > /tmp/ta.log 2>&1; tail -1 /tmp/ta.log
python scripts/wt_plan.py | grep -E "^frames|^cov|^stair"
scripts/wt_py.sh scripts/wt_cover.py measure out/wt/villa4/plan-only.json 2>&1 | tail -1
scripts/wt_audit.sh out/wt/villa4/plan-only.json "$1" | tail -1
python scripts/wt_summary.py out/wt/audits/"$1" knowledge/flyaudit/wt-villa4-tour | grep -E "informative|ALL|^runs|^   \("
