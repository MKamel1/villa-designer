#!/bin/sh
# usage: scripts/wt_vram_peak.sh <log> -- <command...>   runs the command, sampling every 2 s the GPU memory held by blender processes (MiB) and the whole GPU; prints peaks at the end
L=$1; shift 2
( while :; do
    B=$(nvidia-smi --query-compute-apps=name,used_memory --format=csv,noheader,nounits | awk -F', ' '$1 ~ /blender/ {s+=$2} END {print s+0}')
    T=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    echo "$(date +%T) $B $T" >> "$L"; sleep 2; done ) & P=$!
"$@"; R=$?
kill $P
awk '{if($2>b)b=$2; if($3>t)t=$3} END {print "VRAM peak: blender " b " MiB, whole GPU " t " MiB"}' "$L"
exit $R
