#!/bin/sh
# usage: scripts/wt_vram_peak.sh <log> -- <command...>   runs the command, sampling every 2 s the GPU memory held by this command's own process tree (so parallel shards are told apart; set WT_VRAM_MATCH=<text> to match command lines instead) and the whole GPU; prints peaks at the end
L=$1; shift 2; ME=$$
mine() { p=$1; n=0; while [ "$p" -gt 1 ] && [ $n -lt 12 ]; do [ "$p" = "$ME" ] && return 0; p=$(awk '{print $4}' /proc/$p/stat 2>/dev/null); [ -z "$p" ] && return 1; n=$((n+1)); done; return 1; }
( while :; do
    B=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | while IFS=', ' read pid mem; do
        if [ -n "$WT_VRAM_MATCH" ]; then grep -qa "$WT_VRAM_MATCH" /proc/$pid/cmdline 2>/dev/null && echo $mem; else mine $pid && echo $mem; fi; done | awk '{s+=$1} END {print s+0}')
    T=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    echo "$(date +%T) $B $T" >> "$L"; sleep 2; done ) & P=$!
"$@"; R=$?
kill $P
awk '{if($2>b)b=$2; if($3>t)t=$3} END {print "VRAM peak: this job " b " MiB, whole GPU " t " MiB"}' "$L"
exit $R
