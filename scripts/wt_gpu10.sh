#!/bin/sh
# villa10 GPU stages, each wrapped for a per-job VRAM peak. usage: scripts/wt_gpu10.sh <out dir> exposure | workbench | lookdev <frames-file>
set -e
cd /home/omar/archpipe/lanes/WT
PY=/home/omar/archpipe/envs/laneP-venv/bin/python; O=$1; S=$2; B=src/archpipe/blender/walkthrough.py
case $S in
  exposure) $PY scripts/flythrough.py exposure --out $O ;;
  workbench) blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage workbench --animation ;;
  lookdev) blender -b -t 8 --python-exit-code 1 -P $B -- --root $O --stage lookdev --frames $(cat $3) ;;
esac
