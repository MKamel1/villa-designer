#!/bin/sh
set -e
cd /home/omar/archpipe/lanes/WT
PY=/home/omar/archpipe/envs/laneP-venv/bin/python
O=/home/omar/archpipe/lanes/WT/out/wt/villa8
B=src/archpipe/blender/walkthrough.py
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage workbench --out-name full --animation
$PY scripts/flythrough.py report --out $O
$PY scripts/flythrough.py contact --stage workbench --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage workbench --every 1 --out $O
$PY scripts/flythrough.py exposure --out $O
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage lookdev --frames $(cat /home/omar/archpipe/lanes/WT/out/wt/even8.txt)
$PY scripts/flythrough.py contact --stage lookdev --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage lookdev --every 2 --out $O
