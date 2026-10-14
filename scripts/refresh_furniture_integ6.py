"""Refresh numerical room evidence without changing geometry or visual approval.

Use the integration-5 review command to export/review into out/integ6 first.
This command requires all sixteen individual reviews and their joint review.
Previously inspected source geometry, cameras and visual records are retained.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from archpipe.concept.furniture_stage2 import digest, integrate, room_context, room_context_inputs
from archpipe.imported_appearance import bind_scene
from archpipe.furniture_fit import review_selection
from archpipe.beds import review_selection as bed_selection
from refresh_furniture_integ5 import load, save


def refresh(folder):
    raw = load(folder/'procedural-scene.json')
    context = raw['authoring_room_context']
    fr = load(ROOT/'knowledge/furniture-stage2.json.gz')
    br = load(ROOT/'knowledge/parents-bed.json.gz')
    models = [dict(m, review_geometry=fr['geometry'][m['asset']]) for m in fr['models']]+br['models']
    comparisons = load(folder/'room-comparisons-current-furniture.json')
    joint = load(folder/'combined-room-comparison.json')
    if set(comparisons) != {m['label'] for m in models} or not joint['ok'] or not all(r['ok'] for r in comparisons.values()):
        raise ValueError('complete passing fresh integration-6 room reviews required')
    save(folder/'receipt-before-furniture.json.gz', fr)
    save(folder/'receipt-before-bed.json.gz', br)
    previous = load(ROOT/'out/furniture-integ5/door-fix/procedural-scene.json')
    prior_context = previous['authoring_room_context']
    furniture = models[:-1]
    old_inputs = room_context_inputs(previous, prior_context['layout'], prior_context['specification'], prior_context['furniture'], furniture)
    new_inputs = room_context_inputs(raw, context['layout'], context['specification'], context['furniture'], furniture)
    if old_inputs != new_inputs or digest(new_inputs) != fr['room_context_sha256']:
        raise ValueError('fixed furniture review inputs differ: new neutral context preview required')
    for model in furniture:
        model['room_review'] = dict(ok=True, selection=review_selection(model),
            comparison=comparisons[model['label']]['comparison'], evidence_sha256=digest(comparisons[model['label']]))
    fr.update(models=[{k:v for k,v in m.items() if k!='review_geometry'} for m in furniture],
              layout_findings=joint['layout_findings'], room_comparison_sha256=digest(joint),
              room_context_components_sha256={k:digest(v) for k,v in new_inputs.items()})
    current = integrate(raw, furniture, context['layout'], context['specification'], context['furniture'], fr)
    bed = deepcopy(br['models'])
    signature = room_context(current, context['layout'], context['specification'], context['furniture'], bed)
    br.update(room_context_sha256=signature, combined_room_review_sha256=digest(joint))
    br['room_review'] = dict(room_context_sha256=signature, selections=[bed_selection(m) for m in bed],
        baseline_cloth_sha256=digest(br['baseline_cloth']), review=comparisons[bed[0]['label']])
    save(ROOT/'knowledge/furniture-stage2.json.gz', fr)
    save(ROOT/'knowledge/parents-bed.json.gz', br)
    save(folder/'review-refresh.json', dict(status='reviewed', individual_count=len(comparisons),
        combined_sha256=digest(joint), fixed_furniture_inputs_unchanged=True,
        visual_basis='Previously inspected unchanged room/source/camera receipts retained; no new visual approval.'))
    print('Refreshed sixteen individual and joint numerical reviews; strict input/visual gates retained', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'out/integ6')
    refresh(parser.parse_args().output.resolve())
