#!/bin/sh
# usage: scripts/wt_audit.sh <path.json> <id>   (audit against the villa4 scene meshes; ~12 s)
cd /home/omar/archpipe/lanes/WT
PYTHONPATH=src ~/archpipe/envs/wta-venv/bin/python -m archpipe.flyaudit "$1" --scene ${SCENE:-out/wt/villa4/scene.json} --id "$2" --out out/wt/audits 2>&1 | tail -3
