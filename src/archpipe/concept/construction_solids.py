"""Close authored construction skins without moving their visible interfaces.

Coordinates and thicknesses are in metres. A backing skin occupies the host
side of each polygon. It is an assumed render construction layer, not a
specified build-up or a replacement for the mounting finish assembly.
"""
from collections import Counter
import math

from .physical_part import geometry_errors

BACKING_M = .001  # Render skin only; front datum and openings are unchanged.


def backed_polygon(face, thickness=BACKING_M):
    """Keep the front polygon and close its back and true boundary edges.

    Repeated reverse edges are hole bridges, not physical boundaries. Keeping
    the authored front also preserves mounting-face identity and triangulation.
    """
    if thickness <= 0:
        raise ValueError('Construction backing must have positive thickness')
    # The first triangle of a concave ramp profile can face the opposite
    # direction. Use the complete polygon's signed area vector.
    area = [0., 0., 0.]
    for a, b in zip(face, face[1:]+face[:1]):
        area[0] += (a[1]-b[1])*(a[2]+b[2])
        area[1] += (a[2]-b[2])*(a[0]+b[0])
        area[2] += (a[0]-b[0])*(a[1]+b[1])
    length = math.sqrt(sum(v*v for v in area))
    if length <= 1e-10:
        raise ValueError('Construction polygon has no oriented area')
    outward = [v/length for v in area]
    back = [[p[i]-thickness*outward[i] for i in range(3)] for p in face]
    result = [[list(p) for p in face], back[::-1]]
    keys = [tuple(round(v, 9) for v in p) for p in face]
    counts = Counter(zip(keys, keys[1:]+keys[:1]))
    for index, (a, b) in enumerate(zip(keys, keys[1:]+keys[:1])):
        if counts[(b, a)]:
            continue
        following = (index+1) % len(face)
        result.append([list(face[following]), list(face[index]), back[index], back[following]])
    errors = geometry_errors(result)
    if errors:
        raise ValueError('Construction polygon cannot form a solid: '+ '; '.join(errors))
    return result


def close_skin(faces, thickness=BACKING_M):
    """Each oriented construction polygon becomes its own closed skin."""
    return [side for face in faces for side in backed_polygon(face, thickness)]


def complete_shell(scene):
    """Finish the shell after wall-zone clipping, before physical admission.

    Source buckets deliberately hold working interfaces during mounting and
    zone clipping. Already closed sources and actual finish assemblies retain
    their geometry. A surface flag is retained only for registered films.
    """
    physical_door_leaves(scene)
    for mesh in scene['meshes']:
        if mesh.get('group') not in ('shell', 'context') or mesh.get('part_kind') not in ('finish-layer', 'door-leaf'):
            continue
        if not geometry_errors(mesh['faces']):
            continue
        slots = mesh.get('face_materials')
        if slots is not None and len(slots) != len(mesh['faces']):
            raise ValueError(mesh['id'] + ': source face material count does not match faces')
        from .garden_render_review import GROUND_ONLY
        faces, materials = [], []
        for index, face in enumerate(mesh['faces']):
            skin = backed_polygon(face)
            material = slots[index] if slots is not None else mesh['material']
            # Keep every original front's runtime finish. The added backing
            # and edge walls of a floor finish are its physical substrate,
            # never another exposed paving/turf texture on an underside.
            ground_only = material in GROUND_ONLY or scene.get('materials', {}).get(material, {}).get('surface_use') == 'ground-only'
            backing = 'stone-substrate' if ground_only else material
            faces.extend(skin)
            materials.extend([material] + [backing]*(len(skin)-1))
        mesh['faces'] = faces
        if slots is not None or any(m != mesh['material'] for m in materials):
            mesh['face_materials'] = materials
        mesh.pop('surface', None)
        mesh.pop('occupied_side', None)
        mesh.pop('surface_exemption_reason', None)
        mesh['construction_backing_m'] = BACKING_M
        mesh['basis'] = 'authored-construction-skin; visible datum retained'

def physical_door_leaves(scene):
    """Assemble connected source door bodies before any bucket closure.

    Room captions are render bookkeeping. Exact shared source vertices own a
    physical leaf; no coordinate, material or authored front face is changed.
    View hiding follows the complete leaf rather than a subset of its skins.
    """
    import hashlib
    import json
    rows=[m for m in scene['meshes'] if m.get('part_kind')=='door-leaf'
          and m.get('group') in ('shell','context')]
    if not rows:return
    faces=[]
    for row in rows:
        slots=row.get('face_materials',[row['material']]*len(row['faces']))
        if len(slots)!=len(row['faces']):raise ValueError('door face materials incomplete')
        faces.extend((face,material,row) for face,material in zip(row['faces'],slots))
    parent=list(range(len(faces)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    vertices={}
    for i,(face,material,row) in enumerate(faces):
        for vertex in face:
            key=tuple(vertex)
            if key in vertices:parent[root(i)]=root(vertices[key])
            else:vertices[key]=i
    groups={}
    for i,data in enumerate(faces):groups.setdefault(root(i),[]).append(data)
    replacements=[];aliases={row['id']:set() for row in rows}
    for group in groups.values():
        ordered=sorted(group,key=lambda data:json.dumps([data[0],data[1]],separators=(',',':')))
        solid=[data[0] for data in ordered];materials=[data[1] for data in ordered]
        backed=bool(geometry_errors(solid))
        if backed:
            # A genuinely clipped source remains the existing assumed skin.
            # Canonical identity follows the completed body, not its former
            # open front, so replay cannot rename that same physical result.
            from .garden_render_review import GROUND_ONLY
            completed=[]
            for face,material in zip(solid,materials):
                skin=backed_polygon(face)
                ground=material in GROUND_ONLY or scene.get('materials',{}).get(material,{}).get('surface_use')=='ground-only'
                completed.extend(zip(skin,[material]+['stone-substrate' if ground else material]*(len(skin)-1)))
            completed.sort(key=lambda data:json.dumps(list(data),separators=(',',':')))
            solid=[data[0] for data in completed];materials=[data[1] for data in completed]
        identity=hashlib.sha256(json.dumps([solid,materials],separators=(',',':')).encode()).hexdigest()[:24]
        identifier='door-leaf-'+identity
        prior={data[2]['id']:data[2] for data in group}
        if len(prior)==1 and identifier in prior:
            replacements.append(prior[identifier]);aliases[identifier].add(identifier)
            continue
        record=dict(id=identifier,source_id=identifier,group='shell',part_kind='door-leaf',
                    material=materials[0],faces=solid,room=None,label='Physical door leaf',keep_object=True,
                    local_axes=['x','y','z'],
                    basis='authored CAD door component; independent of view captions')
        if backed:record['construction_backing_m']=BACKING_M
        if any(m!=materials[0] for m in materials):record['face_materials']=materials
        replacements.append(record)
        for face,material,row in group:aliases[row['id']].add(identifier)
    scene['meshes']=[m for m in scene['meshes'] if m['id'] not in aliases]+sorted(replacements,key=lambda m:m['id'])
    for view in scene.get('views',[]):
        hidden=[]
        for identifier in view.get('hide_meshes',[]):hidden.extend(sorted(aliases.get(identifier,{identifier})))
        if 'hide_meshes' in view:view['hide_meshes']=list(dict.fromkeys(hidden))
