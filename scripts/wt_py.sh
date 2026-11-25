#!/bin/sh
# run a script with embreex (wta-venv) plus the lane venv's packages (shapely etc.)
cd /home/omar/archpipe/lanes/WT
PYTHONPATH=src:/home/omar/archpipe/envs/laneP-venv/lib/python3.14/site-packages exec ~/archpipe/envs/wta-venv/bin/python "$@"
