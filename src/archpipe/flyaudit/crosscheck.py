"""Compare an audit's frames.json with a Blender Workbench depth-grid metrics.json (index = path frame; independent renderer).
python -m archpipe.flyaudit.crosscheck <frames.json> <metrics.json> -> prints and returns the agreement numbers."""
import json, sys
import numpy as np


def compare(frames_path, metrics_path):
    r = {x['i']: x for x in json.loads(open(frames_path).read())}
    m = [e for e in json.loads(open(metrics_path).read()) if e['index'] in r]
    both = [e for e in m if r[e['index']]['median_dist'] and e['median_depth_m']]
    nonin = np.array([e['non_informative'] for e in m]); mine = np.array([r[e['index']]['cat'] != 'informative' for e in m])
    out = dict(frames=len(m), median_depth_corr=round(float(np.corrcoef([e['median_depth_m'] for e in both], [r[e['index']]['median_dist'] for e in both])[0, 1]), 3),
               near_share_corr=round(float(np.corrcoef([e['near_fraction'] for e in both], [r[e['index']]['near_share'] for e in both])[0, 1]), 3),
               other_non_informative_share=round(float(nonin.mean()), 4), audit_non_informative_share=round(float(mine.mean()), 4),
               per_frame_agreement=round(float((nonin == mine).mean()), 4))
    return out


if __name__ == '__main__':
    print(json.dumps(compare(*sys.argv[1:3]), indent=1))
