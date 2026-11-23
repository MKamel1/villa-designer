#!/bin/sh
# FG: render rubric sheets (5 m / 15 m / close) for the given specs through jobq. usage: fg_sheets.sh JOBID OUTDIR spec...
J=$1; O=$2; shift 2
A=""; for s in "$@"; do A="$A --spec $s"; done
~/archpipe/bin/jobq submit --gpu --timeout 3000 --id "$J" --cwd /home/omar/archpipe/lanes/FG -- sh -c "PYTHONPATH=src /home/omar/opt/blender-4.5.14-linux-x64/blender -b --python-exit-code 1 -P src/archpipe/landscape/foliage/blender_build.py -- sheet --out $O $A"
