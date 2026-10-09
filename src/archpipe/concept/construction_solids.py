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
