"""Review unchanged loose storage and preserve inherited baseline findings.

No failing-fit candidate enters the physical room. Where intake admits none,
this writes a baseline and explicitly records that candidate review is absent.
"""
from pathlib import Path
import gzip,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import bed_room_review
OUT=ROOT/'out/storage/stage2'
MARKS=['dining-sideboard','lounge-tv','study-tv','pb-bedside','pb-vanity']

def main():
    scene=json.loads((OUT/'storage-room-scene.json').read_text())
    context=json.loads(gzip.decompress((OUT/'authoring-context.json.gz').read_bytes()))
    selection=json.loads((OUT/'selection.json').read_text())
    if selection['eligible']:raise ValueError('eligible candidates need individual and combined comparison, not a baseline-only report')
    baseline=bed_room_review(scene,context['layout'],context['specification'],context['furniture'],target_marks=MARKS,absolute=True)
    (OUT/'room-review.json').write_text(json.dumps(dict(baseline=baseline,
        candidates_reviewed=[],activated=[],candidate_review_status='not applicable: no eligible complete loose candidate',
        layout_findings=baseline['findings']),indent=2)+'\n')
    print('Baseline access:',baseline['clearances'])
    print('Inherited findings:',len(baseline['findings']))

if __name__=='__main__':main()
