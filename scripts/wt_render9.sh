#!/bin/sh
set -e
cd /home/omar/archpipe/lanes/WT
PY=/home/omar/archpipe/envs/laneP-venv/bin/python
O=${1:-/home/omar/archpipe/lanes/WT/out/wt/villa9c}
B=src/archpipe/blender/walkthrough.py
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage workbench --animation
$PY scripts/flythrough.py contact --stage workbench --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage workbench --every 1 --out $O
$PY scripts/flythrough.py exposure --out $O
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage lookdev --frames $(cat /home/omar/archpipe/lanes/WT/out/wt/even9b.txt)
$PY scripts/flythrough.py contact --stage lookdev --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage lookdev --every 2 --out $O
