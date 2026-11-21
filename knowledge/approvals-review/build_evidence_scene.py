"""Build the D1 scene with the PRODUCTION approval guards and write it (lane RA evidence).

The only deviation from production is --bypass-receipts, which skips the furniture-stage2 / parents-bed receipt passes
(they fail on the base for reasons outside the approvals; docs/lanes/RA-review.md, blocker B2). Usage:
  python build_evidence_scene.py OUT_DIR [--bypass-receipts]
"""
import hashlib, json, sys, time
from pathlib import Path
from archpipe.concept import villa_render

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
if '--bypass-receipts' in sys.argv:
    from archpipe.concept import furniture_stage2 as FS, parents_bed as PB
    FS.apply = lambda scene, *a: scene
    PB.apply = lambda scene, *a: scene
t = time.time()
path, _ = villa_render.write(out / 'scene.json', measure_exposure_groups=True)  # no frozen record: it is stale for any geometry change (blocker B3)
path = Path(path)
raw = path.read_bytes()
scene = json.loads(raw)
from archpipe.blender.element_ids import without_ids, FIELDS
stripped = hashlib.sha256(json.dumps(without_ids(scene), sort_keys=True).encode()).hexdigest()
ids_kept = sum(1 for m in scene['meshes'] if any(f in m for f in FIELDS))
rec = dict(scene=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), stripped_ids_json_sha256=stripped,
           meshes=len(scene['meshes']), meshes_with_ids=ids_kept, seconds=round(time.time() - t, 1),
           lead_approved_count=scene.get('lead_approved_count'), bypass_receipts='--bypass-receipts' in sys.argv)
(out / 'scene-record.json').write_text(json.dumps(rec, indent=1))
print(json.dumps(rec, indent=1))
