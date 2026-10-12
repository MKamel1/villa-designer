"""Apply the reviewed parents source-bed omission after measured room furniture.

The portable receipt binds every physical input, retained face, original camera
and evaluated procedural soft good. The generated covers keep their own gate.
"""
from copy import deepcopy
import gzip,json
from pathlib import Path
from .furniture_stage2 import room_context,digest
RECEIPT=Path(__file__).resolve().parents[3]/'knowledge/parents-bed.json.gz'
def apply(scene,layout,specification,furniture):
    if not RECEIPT.is_file():return scene
    receipt=json.loads(gzip.decompress(RECEIPT.read_bytes()))
    if layout['id']!=receipt['option']:return scene
    models=deepcopy(receipt['models'])
    if receipt.get('status')!='accepted' or receipt.get('room_context_sha256')!=room_context(scene,layout,specification,furniture,models):
        raise ValueError('parents bed fixed-room inputs changed; repeat relative review and neutral previews')
    cloth=[c for c in scene['cloth'] if c['id'].startswith(tuple(p+m['label'] for m in models for p in ('duvet-','throw-')))]
    if receipt.get('cloth_specs_sha256')!=digest(cloth):
        raise ValueError('parents bed authored cloth changed; repeat evaluated cloth review')
    for view in scene.get('views',[]):
        if view['id'] in receipt['reviewed_cameras'] and digest(view['camera'])!=receipt['reviewed_cameras'][view['id']]:
            raise ValueError('reviewed parents bed camera changed')
    from ..beds import integrate_bed_models
    result=integrate_bed_models(scene,models,layout,specification,furniture,baseline_meshes=receipt['baseline_cloth'],
                                accepted_room_review=receipt['room_review'])
    result['parents_bed']=dict(status='active',items=[m['label'] for m in models],source_receipt_sha256=digest(receipt),omitted_meshes={m['label']:m['omitted_meshes'] for m in models})
    return result
