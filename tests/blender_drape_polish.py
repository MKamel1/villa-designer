"""Live Blender read-back of exact separately cached tailoring references."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe import drape_appearance as D
argv=sys.argv[sys.argv.index('--')+1:]
parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
args=parser.parse_args(argv);case=json.loads(args.input.read_text())
actual=[D.make_reference(p) for p in case['parts']]
if actual!=case['references']:raise ValueError('portable tailoring reference differs in Blender')
args.output.write_text(json.dumps(dict(references=actual,exact_match=True)))
