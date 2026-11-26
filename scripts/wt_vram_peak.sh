#!/bin/sh
# usage: scripts/wt_vram_peak.sh <log> -- <command...>   runs the command, sampling every 2 s the GPU memory held by processes whose command line contains $WT_VRAM_MATCH (default villa9) and the whole GPU; prints peaks at the end
L=$1; shift 2
( while :; do
    B=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | while IFS=', ' read pid mem; do grep -qa "${WT_VRAM_MATCH:-villa9}" /proc/$pid/cmdline 2>/dev/null && echo $mem; done | awk '{s+=$1} END {print s+0}')
    T=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    echo "$(date +%T) $B $T" >> "$L"; sleep 2; done ) & P=$!
"$@"; R=$?
kill $P
awk '{if($2>b)b=$2; if($3>t)t=$3} END {print "VRAM peak: blender " b " MiB, whole GPU " t " MiB"}' "$L"
exit $R
