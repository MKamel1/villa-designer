"""Activate measured, previewed furniture against unchanged room evidence.

The compressed repository receipt carries exact source geometry for portable
review. The library still supplies unchanged source glTF and textures at real
import; no HOME-based library read is required to build the authored scene.
"""
from copy import deepcopy
import gzip,hashlib,json
from pathlib import Path

RECEIPT=Path(__file__).resolve().parents[3]/'knowledge/furniture-stage2.json.gz'

def derived_seats(furniture):
    """Resolve actual derived chairs from the same authored desk inputs."""
    from . import villa_furnish3d as F3, villa_furniture_detail as FD
    result=[]
    for desk in furniture:
        if desk['type']!='desk':continue
        for spec in F3.spec(items=[desk]):
            if spec['type']!='chair':continue
            seat=FD.seat_item(spec)
            # Match inventory's declared micrometre precision; subtracting
            # world box endpoints otherwise yields 0.4399999999999995 m for
            # the authored 0.440 m chair, defeating exact target identity.
            seat['w']=round(seat['w'],6)
            seat['d']=round(seat['d'],6)
            result.append(dict(seat,room=desk['room'],level=desk['level'],parent_id=desk['id'],
                               type='task_chair' if 'gas-lift' in FD.seat_parts(spec,0) else 'vanity_chair'))
    return result

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def physical_architecture(meshes):
    """Bind every face and physical attribute independently of export buckets.

    Doorway view selections change bucket names and door caption ownership,
    without changing the leaf faces. Source mesh names are bucket references;
    actual source/finish host identities, finish datums and face winding stay
    bound. Keep-object is an export batching choice, not physical visibility.
    """
    records=[]
    for row in meshes:
        attributes={key:value for key,value in row.items() if key not in (
            'id','label','source_mesh','keep_object','faces','face_materials','material')}
        attributes.setdefault('source_id','villa-shell')
        if row['part_kind']=='door-leaf':
            attributes.pop('room',None)
        materials=row.get('face_materials',[row['material']]*len(row['faces']))
        if len(materials)!=len(row['faces']):
            raise ValueError('architectural face materials must cover every face')
        records.extend(dict(attributes,face=face,material=material)
                       for face,material in zip(row['faces'],materials))
    return sorted(records,key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))

def room_context(scene,layout,specification,furniture,models):
    """Bind a passed review to every fixed room input and its existing camera.

    Architectural faces remain complete. Target procedural bodies remain in
    this signature as the measured baseline; newly imported faces never
    substitute for that baseline. Any fixed input change requires re-review.
    """
    from .villa_furnish import _cluster
    rooms={room for model in models for room in _cluster(layout,model['room'])}
    prefixes={m['replaces'] for m in models};instances={m['id'] for m in models}
    # Override audit explanations differ between a cold layout and a cache
    # restoration. Bind every actual field/value, not those derivation notes.
    physical_furniture=[{key:value for key,value in item.items() if key!='overrides'} for item in furniture]
    return digest(dict(layout=layout,specification=specification,furniture=physical_furniture,
        architecture=physical_architecture([r for r in scene['meshes'] if r['group'] in ('shell','context')]),
        meshes=[r for r in scene['meshes'] if r.get('model_instance') not in instances and
                r['group'] not in ('shell','context') and r.get('room') in rooms],
        models=[m for m in scene.get('models',[]) if m.get('room') in rooms and m.get('replaces') not in prefixes],
        props=[p for p in scene.get('props',[]) if p.get('room') in rooms],
        materials=scene['materials']))

def integrate(scene,models,layout,specification,furniture,receipt):
    """Require original placement, exact native fallback identity and bound gates."""
    from ..furniture_fit import require_furniture_geometry,review_selection,model_fit,replacement_floor
    from ..furniture_orientation import check_model_orientation
    from .villa_furnish import footprint
    items={it['id']:it for it in furniture+derived_seats(furniture)}
    if receipt.get('status')!='accepted' or receipt.get('combined_room_review_ok') is not True:
        raise ValueError('furniture activation requires a reviewed passing combined room comparison')
    if receipt.get('room_context_sha256')!=room_context(scene,layout,specification,furniture,models):
        raise ValueError('furniture fixed-room inputs changed; repeat baseline-relative review and previews')
    # A requested subset (including no views in numerical verification) is
    # not a camera edit. Check every supplied reviewed camera by identity.
    for view in scene.get('views',[]):
        if view['id'] in receipt.get('reviewed_cameras',{}) and digest(view['camera'])!=receipt['reviewed_cameras'][view['id']]:
            raise ValueError('reviewed furniture room camera changed; repeat neutral preview')
    for model in models:
        require_furniture_geometry(model);check_model_orientation(model)
        item=items[model['label']];bounds=footprint(item)
        floor=replacement_floor(scene,model)
        if (model['furniture_fitting']['footprint_m']!=[item['w'],item['d']] or
                model['furniture_fitting']['height_m']!=item.get('seat_h',item['h']) or
                model['layout_rotation_deg']!=item['rot'] or
                any(abs(a-b)>1e-5 for a,b in zip(model['position'],[item['cx'],item['cy'],floor])) or
                any(abs(a-b)>1e-5 for a,b in zip([model['footprint_w'],model['footprint_d']],
                                               [bounds[2]-bounds[0],bounds[3]-bounds[1]]))):
            raise ValueError('furniture replacement must retain original footprint, centre, floor, height and front')
        room=model.get('room_review',{})
        if room.get('ok') is not True or room.get('selection')!=review_selection(model):
            raise ValueError('furniture requires selection-bound baseline-relative room acceptance')
        if not model_fit(model)['ok']:raise ValueError('furniture fit gate closed')
    prefixes={m['replaces'] for m in models}
    exact={identifier for model in models for identifier in model['replacement_mesh_ids']}
    hidden={'camera':False,'shadow':False,'diffuse':False,'glossy':False,'transmission':False}
    return dict(scene,meshes=[dict(row,visibility=hidden) if row['id'] in exact else row for row in scene['meshes']],
        models=[m for m in scene.get('models',[]) if m.get('replaces') not in prefixes]+deepcopy(models),
        furniture_stage2=dict(status='active',items=[m['label'] for m in models],
            source_receipt_sha256=digest(receipt),room_context_sha256=receipt['room_context_sha256'],
            layout_findings=receipt['layout_findings']))

def apply(scene,layout,specification,furniture):
    if not RECEIPT.is_file():return scene
    receipt=json.loads(gzip.decompress(RECEIPT.read_bytes()))
    if layout['id']!=receipt['option']:return scene
    models=[dict(m,review_geometry=receipt['geometry'][m['asset']]) for m in receipt['models']]
    return integrate(scene,models,layout,specification,furniture,receipt)
