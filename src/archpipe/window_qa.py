"""Visible glazing owns its image samples; projected rectangles do not.

Coordinates in runs are image pixels, with the origin at the top left. Each
run is [row, first column, exclusive last column], sampled every two pixels.
The native first-hit ray identifies the actual visible mesh polygon. The two
pixel spacing retains the production image check's existing detail baseline.
"""
from collections import defaultdict
import math

_geometry_cache = {}


def render_geometry(scene, depsgraph, geometry_key=None):
    """First-hit tree of evaluated camera-visible render geometry.

    Batch callers may supply their independently verified static-assembly
    fingerprint. Visibility is part of the cache key. Without that proof the
    tree is rebuilt, so generic callers cannot reuse changed geometry silently.
    """
    from mathutils.bvhtree import BVHTree
    visible = [(obj, obj.matrix_world.copy()) for obj in scene.objects if obj.type == 'MESH'
               and not obj.hide_render and obj.visible_camera]
    # Collection/geometry instances may block a pane even though their source
    # mesh is not a direct scene member. Use the evaluated instance transform.
    visible.extend((instance.object, instance.matrix_world.copy())
        for instance in depsgraph.object_instances if instance.is_instance
        and instance.object.type == 'MESH' and not instance.object.hide_render
        and instance.object.visible_camera
        and (instance.parent is None or not instance.parent.hide_render))
    key = (scene.as_pointer(), geometry_key,
           tuple((obj.name, obj.data.as_pointer(), tuple(v for row in matrix for v in row))
                 for obj, matrix in visible))
    if geometry_key is not None and key in _geometry_cache:
        return _geometry_cache[key]
    points, faces, owners = [], [], []
    for obj, matrix in visible:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            offset = len(points)
            points.extend(matrix @ vertex.co for vertex in mesh.vertices)
            for polygon in mesh.polygons:
                faces.append([offset + index for index in polygon.vertices])
                owners.append((obj.name, polygon.index))
        finally:
            evaluated.to_mesh_clear()
    tree = BVHTree.FromPolygons(points, faces)
    result = tree, owners
    if geometry_key is not None:
        _geometry_cache.clear()
        _geometry_cache[key] = result
    return result


def pack_pixels(coordinates, width, height, step=2):
    if any(type(v) is not int or v < 1 for v in (width, height)):
        raise ValueError('Invalid native window image size')
    if type(step) is not int or step not in (2, 3):
        raise ValueError('Invalid native glazing sample spacing')
    rows = defaultdict(list)
    for x, y in coordinates:
        if x % step or y % step or not (0 <= x < width and 0 <= y < height):
            raise ValueError('Glazing samples must lie on their declared image grid')
        rows[y].append(x)
    runs = []
    for y, values in sorted(rows.items()):
        values = sorted(set(values))
        start = last = values[0]
        for x in values[1:]:
            if x != last + step:
                runs.append([y, start, last + step]); start = x
            last = x
        runs.append([y, start, last + step])
    if not runs:
        raise ValueError('A declared visible window needs nonempty native pixel ownership')
    return dict(size=[width, height], step=step, runs=runs,
                basis='native evaluated first-hit glass polygon at image sample centres')


def unpack_pixels(value, width, height, expected_step=2):
    if (type(expected_step) is not int or expected_step not in (2, 3)
            or value.get('size') != [width, height] or value.get('step') != expected_step
            or value.get('basis') != 'native evaluated first-hit glass polygon at image sample centres'):
        raise ValueError('Window pixel ownership is missing or mismatches the checked image')
    result = set()
    step = expected_step
    for y, first, end in value['runs']:
        if (not all(type(v) is int for v in (y, first, end)) or y % step or first % step
                or end % step or not (0 <= y < height and 0 <= first < end <= ((width + step - 1) // step) * step)):
            raise ValueError('Invalid native window pixel run')
        for x in range(first, end, step):
            if (x, y) in result:
                raise ValueError('Duplicate native window sample')
            result.add((x, y))
    if not result:
        raise ValueError('A declared visible window needs nonempty native pixel ownership')
    return result


def room_background_pixels(windows, width, height, room_glazing=None):
    """Sample the room every three pixels, excluding every declared window.

    Native room ownership is measured on this exact three-pixel grid, separately
    from the two-pixel window grid. Older native contexts retain their two-pixel
    cell approximation; legacy rectangles retain their rectangle approximation.
    Small panes remain exterior even when their individual check is skipped.
    """
    native = set()
    exact = unpack_pixels(room_glazing, width, height, expected_step=3) if room_glazing is not None else None
    rectangles = []
    for window in windows:
        if 'visible_pixels' in window:
            owned = unpack_pixels(window['visible_pixels'], width, height)
            if exact is None:
                native.update(owned)
        elif window.get('screen'):
            left, bottom, right, top = window['screen']
            rectangles.append((int(left * width), int((1 - top) * height),
                               int(right * width), int((1 - bottom) * height)))
    return [(x, y) for y in range(0, height, 3) for x in range(0, width, 3)
            if (x, y) not in (exact or ()) and (x - x % 2, y - y % 2) not in native
            and not any(left <= x < right and top <= y < bottom
                        for left, top, right, bottom in rectangles)]


def visible_windows(scene, camera, glass_objects, geometry_key=None, include_room=False):
    """Measure actual visible glazing for the image QA grid, never its colour.

    All glass candidates are native mesh objects; each result belongs to its
    first-hit evaluated polygon, so front/back surfaces cannot double-count a
    window. Bounds only prune rays. Occlusion is tested at every image sample.
    """
    import bpy
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    width = round(scene.render.resolution_x * scene.render.resolution_percentage / 100)
    height = round(scene.render.resolution_y * scene.render.resolution_percentage / 100)
    if width > 800:
        height = round(800 * height / width); width = 800
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tree, owners = render_geometry(scene, depsgraph, geometry_key)
    candidates = {obj.name: obj for obj in glass_objects if not obj.hide_render and obj.visible_camera}
    bounds = []
    for obj in candidates.values():
        points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(p)) for p in obj.bound_box]
        if all(p.z <= 0 for p in points):
            continue
        if any(p.z <= 0 for p in points):
            bounds.append((0, 0, width, height)); continue
        bounds.append((max(0, math.floor(min(p.x for p in points) * width)),
                       max(0, math.floor((1 - max(p.y for p in points)) * height)),
                       min(width, math.ceil(max(p.x for p in points) * width)),
                       min(height, math.ceil((1 - min(p.y for p in points)) * height))))
    corners = camera.data.view_frame(scene=scene)
    xmin, xmax = min(p.x for p in corners), max(p.x for p in corners)
    ymin, ymax = min(p.y for p in corners), max(p.y for p in corners)
    origin = camera.matrix_world.translation
    rotation = camera.matrix_world.to_3x3()
    pixels = defaultdict(list)
    room_pixels = []
    rows = sorted(set(range(0, height, 2)) | (set(range(0, height, 3)) if include_room else set()))
    columns = sorted(set(range(0, width, 2)) | (set(range(0, width, 3)) if include_room else set()))
    for y in rows:
        for x in columns:
            window_sample = x % 2 == 0 and y % 2 == 0
            room_sample = include_room and x % 3 == 0 and y % 3 == 0
            if not (window_sample or room_sample):
                continue
            if not any(a <= x < c and b <= y < d for a, b, c, d in bounds):
                continue
            local = Vector((xmin + (x + .5) / width * (xmax - xmin),
                            ymax - (y + .5) / height * (ymax - ymin), corners[0].z))
            location, _normal, polygon, _distance = tree.ray_cast(
                origin, (rotation @ local).normalized(), camera.data.clip_end)
            if location is not None:
                name, face = owners[polygon]
                if name in candidates:
                    if window_sample:
                        pixels[(name, face)].append((x, y))
                    if room_sample:
                        room_pixels.append((x, y))
    result = []
    for (name, polygon), coordinates in sorted(pixels.items()):
        xs, ys = zip(*coordinates)
        left, right = min(xs) / width, min(width, max(xs) + 2) / width
        bottom, top = 1 - min(height, max(ys) + 2) / height, 1 - min(ys) / height
        # Retain every glazing owner for the room-background population. The
        # consumer keeps its existing 3% individual-window check screen; early
        # removal here would misclassify small bright panes as inside the room.
        result.append(dict(id=f'{name}-face-{polygon}', screen=[left, bottom, right, top],
                           visible_pixels=pack_pixels(coordinates, width, height)))
    if include_room:
        return result, pack_pixels(room_pixels, width, height, step=3) if room_pixels else None
    return result
