#!/bin/sh
# Cycles lookdev of villa9 on the GPU (resumable). Measured peak 9.1 GB (persistent data, 480x270, 16 spp): fits the ~14 GB left beside the RAG service. usage: scripts/wt_lookdev9.sh [out dir]
set -e
cd /home/omar/archpipe/lanes/WT
PY=/home/omar/archpipe/envs/laneP-venv/bin/python
O=${1:-/home/omar/archpipe/lanes/WT/out/wt/villa9e}
B=src/archpipe/blender/walkthrough.py
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage lookdev --frames $(cat /home/omar/archpipe/lanes/WT/out/wt/even9b.txt)
$PY scripts/flythrough.py contact --stage lookdev --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage lookdev --every 2 --out $O
