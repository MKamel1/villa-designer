#!/bin/sh
# villa9 renders. usage: scripts/wt_render9.sh [out dir]   Exposure and lookdev run Cycles on the CPU (ARCHPIPE_CYCLES_CPU=1): the GPU holds the client's RAG service (~10 GB) and
# the scene needs 13.4 GB there at peak (docs/lanes/WT.md Revision 6). Workbench frames come from the GPU/OpenGL stage as before.
set -e
cd /home/omar/archpipe/lanes/WT
PY=/home/omar/archpipe/envs/laneP-venv/bin/python
O=${1:-/home/omar/archpipe/lanes/WT/out/wt/villa9d}
B=src/archpipe/blender/walkthrough.py
blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage workbench --animation
$PY scripts/flythrough.py contact --stage workbench --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage workbench --every 1 --out $O
export ARCHPIPE_CYCLES_CPU=1 WT_BLENDER_THREADS=${WT_BLENDER_THREADS:-24}
$PY scripts/flythrough.py exposure --out $O
blender -b -t $WT_BLENDER_THREADS --python-exit-code 1 -P $B -- --root $O --stage lookdev --frames $(cat /home/omar/archpipe/lanes/WT/out/wt/even9b.txt)
$PY scripts/flythrough.py contact --stage lookdev --every 48 --out $O
$PY scripts/flythrough.py encode-draft --stage lookdev --every 2 --out $O
