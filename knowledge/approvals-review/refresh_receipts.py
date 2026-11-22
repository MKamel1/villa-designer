"""RA2/B2: refresh knowledge/furniture-stage2.json.gz and parents-bed.json.gz after a reviewed fixed-input change.

Precondition (checked): the fresh baseline-relative reviews exist and pass -- sixteen individual comparisons and the joint
one, from `scripts/refresh_furniture_integ5.py review-current --output DIR`. The scene is stripped of the P2 element-id
fields first, because the receipts are computed mid-build, before ids are attached (same view as the build).
Visual approvals (reviewed images/cameras, source geometry) are retained: none of the sixteen items sits in a room whose
look changed; the section-diff/attribution/clearance evidence is recorded in the receipt under `refresh_2026_11_21`.
Usage: python refresh_receipts.py DIR [--write]
"""
import gzip, json, sys
from copy import deepcopy
from pathlib import Path
from archpipe.concept.furniture_stage2 import digest, integrate, room_context, room_context_inputs
from archpipe.blender.element_ids import without_ids
from archpipe.furniture_fit import review_selection
from archpipe.beds import review_selection as bed_selection

ROOT = Path(__file__).resolve().parents[2]
folder = Path(sys.argv[1]).resolve(); write = '--write' in sys.argv
load = lambda p: json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_text())
def save(path, value):
    data = json.dumps(value, separators=(',', ':')).encode()
    Path(path).write_bytes(gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data)

raw = without_ids(load(folder / 'procedural-scene.json')); ctx = raw['authoring_room_context']
fr = load(ROOT / 'knowledge/furniture-stage2.json.gz'); br = load(ROOT / 'knowledge/parents-bed.json.gz')
comparisons = load(folder / 'room-comparisons-current-furniture.json'); joint = load(folder / 'combined-room-comparison.json')
models = [dict(m, review_geometry=fr['geometry'][m['asset']]) for m in fr['models']] + br['models']
if set(comparisons) != {m['label'] for m in models} or not joint['ok'] or not all(r['ok'] for r in comparisons.values()):
    raise SystemExit('complete passing fresh room reviews required')
if any(r['findings'] for r in comparisons.values()) or joint['findings']:
    raise SystemExit('relative review has findings; refusing')
furniture = models[:-1]; bed = deepcopy(br['models'])
inputs = room_context_inputs(raw, ctx['layout'], ctx['specification'], ctx['furniture'], furniture)
for m in furniture:
    m['room_review'] = dict(ok=True, selection=review_selection(m), comparison=comparisons[m['label']]['comparison'],
                            evidence_sha256=digest(comparisons[m['label']]))
fr.update(models=[{k: v for k, v in m.items() if k != 'review_geometry'} for m in furniture],
          room_context_sha256=digest(inputs), layout_findings=joint['layout_findings'], room_comparison_sha256=digest(joint),
          room_context_components_sha256={k: digest(v) for k, v in inputs.items()})
current = integrate(raw, furniture, ctx['layout'], ctx['specification'], ctx['furniture'], fr)
sig = room_context(current, ctx['layout'], ctx['specification'], ctx['furniture'], bed)
cloth = digest([c for c in raw['cloth'] if c['id'].startswith(('duvet-pb-bed', 'throw-pb-bed'))])
print('cloth specs unchanged:', cloth == br['cloth_specs_sha256'])
br.update(room_context_sha256=sig, combined_room_review_sha256=digest(joint), cloth_specs_sha256=cloth)
br['room_review'] = dict(room_context_sha256=sig, selections=[bed_selection(m) for m in bed],
                         baseline_cloth_sha256=digest(br['baseline_cloth']), review=comparisons[bed[0]['label']])
note = dict(reason='fixed-input change by approved G1 (stair overlap/infill/guards/cupboard/lounge door/core door swing), M (wall corners) '
            'the G1 store trim, and (INT2 2026-11-21) the L6b/L6c lighting fixtures + landing PATH marker hosts (all changed meshes are fix-/lens-/lamp-/marker-, 12/16 landing finish faces) and the ERCO recessed housing depth (26 fix-* meshes) and (INT2b) the lead-approved 12 mm finished-face move of marker-PATH-landing-gf-01/02 (meshes section only; evidence-int2/section-diff-approved-markers.json) and (SC2) wall-B-ext-16 raised 2.65 -> 2.80 m to the roof soffit (specification: walls[16].height only; architecture: 81 faces removed and 81 added, all inside the wall own footprint, 0 unexplained; evidence-sc2/); evidence knowledge/approvals-review/2026-11-ra2-b2.md',
            reviews='16 individual + joint baseline-relative reviews, 0 findings', visual='retained, not re-approved')
fr['refresh_2026_11_21'] = note; br['refresh_2026_11_21'] = note
if write:
    save(ROOT / 'knowledge/furniture-stage2.json.gz', fr); save(ROOT / 'knowledge/parents-bed.json.gz', br)
    print('written')
print('furniture-stage2 room_context', fr['room_context_sha256'][:16], 'parents-bed', br['room_context_sha256'][:16])
