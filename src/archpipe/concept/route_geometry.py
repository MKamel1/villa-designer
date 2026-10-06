"""Actual prop triangles for walking-envelope checks; coordinates are metres.

Native glTF x/y/z axes become scene x/-z/y axes. Only upright props are
supported. Files are read from the same library the Blender importer uses.
Missing geometry fails closed when its full bounds overlap a walking route.
"""
from functools import lru_cache
import base64
import json
from pathlib import Path
import numpy as np


def asset_triangles(path):
    """Cache by file signatures; replacing an asset cannot reuse old triangles."""
    path = Path(path)
    data = json.loads(path.read_text())
    files = [path] + [path.parent/b['uri'] for b in data['buffers'] if not b['uri'].startswith('data:')]
    signature = tuple((f.stat().st_mtime_ns,f.stat().st_size) for f in files)
    return _read_asset_triangles(str(path),signature)


@lru_cache(maxsize=64)
def _read_asset_triangles(path, signature):
    """Read indexed triangles and all scene-node transforms, never accessor boxes."""
    path = Path(path)
    data = json.loads(path.read_text())
    buffers = []
    for row in data['buffers']:
        uri = row['uri']
        buffers.append(base64.b64decode(uri.split(',', 1)[1]) if uri.startswith('data:') else (path.parent/uri).read_bytes())

    def accessor(index):
        row = data['accessors'][index]
        if 'sparse' in row: raise ValueError('sparse route geometry not supported')
        view = data['bufferViews'][row['bufferView']]
        dtype = {5121:'<u1',5123:'<u2',5125:'<u4',5126:'<f4'}[row['componentType']]
        count = {'SCALAR':1,'VEC3':3}[row['type']]
        offset = view.get('byteOffset',0)+row.get('byteOffset',0)
        stride = view.get('byteStride', np.dtype(dtype).itemsize*count)
        return np.ndarray((row['count'],count),dtype=dtype,buffer=buffers[view['buffer']],offset=offset,strides=(stride,np.dtype(dtype).itemsize)).copy()

    result=[]
    def visit(index,parent):
        node=data['nodes'][index]
        if 'matrix' in node:
            local=np.array(node['matrix']).reshape(4,4).T
        else:
            x,y,z,w=node.get('rotation',[0,0,0,1])
            local=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],
                            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],
                            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]],float)
            local[:3,:3] *= node.get('scale',[1,1,1])
            local[:3,3]=node.get('translation',[0,0,0])
        matrix=parent@local
        if 'mesh' in node:
            for primitive in data['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode',4)!=4: raise ValueError('route geometry must be triangles')
                vertices=accessor(primitive['attributes']['POSITION'])@matrix[:3,:3].T+matrix[:3,3]
                indices=accessor(primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(vertices))
                result.append(vertices[indices.reshape(-1,3)])
        for child in node.get('children',[]): visit(child,matrix)
    for root in data['scenes'][data.get('scene',0)]['nodes']: visit(root,np.eye(4))
    if not result: raise ValueError('asset has no route triangles')
    triangles=np.concatenate(result)[:,:, [0,2,1]]
    triangles[:,:,1]*=-1
    if not np.isfinite(triangles).all(): raise ValueError("asset has non-finite route geometry")
    triangles.setflags(write=False)
    return triangles


def prop_triangles(prop):
    """Reproduce Blender import scale, yaw and lowest-point floor seating."""
    if any(abs(v)>1e-9 for v in prop.get('rotation_deg',[0,0,0])[:2]):
        raise ValueError('tilted prop route geometry not supported')
    from math import cos,sin,radians
    native=asset_triangles(str(Path.home()/'archpipe/assets/library/props'/prop['asset']/'model.gltf'))
    triangles=native*np.array(prop.get('scale',1.0))
    yaw=radians(prop.get('rotation_deg',[0,0,0])[2]);c,s=cos(yaw),sin(yaw)
    triangles=triangles@np.array([[c,s,0],[-s,c,0],[0,0,1]])
    triangles[:,:,2]-=triangles[:,:,2].min()
    return triangles+np.array(prop['position'])


def nearest_clear_translation(triangles, bounds, routes, route_ground, height=2.0, clearance=1e-6):
    """Nearest horizontal translation of actual triangles in a bounded domain.

    bounds is (minimum x shift, minimum y shift, maximum x shift, maximum
    y shift), in metres. routes maps names to walking rectangles; route_ground
    maps those names to floor heights. Clip triangles to each walking height
    band, then subtract every forbidden translation polygon from the domain.
    A forbidden polygon is all rectangle corners minus all clipped triangle
    vertices, joined by their convex hull. This searches the continuous domain,
    including disconnected clear regions, rather than a local sampled grid.
    clearance separates touching geometry by one micrometre by default; it is
    a numerical separation, not an ergonomic allowance. None means no solution.
    """
    from shapely.geometry import MultiPoint, Point, box
    from shapely.ops import nearest_points, unary_union

    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        return None
    domain = box(*bounds)
    forbidden = []
    for name, rect in routes.items():
        floor = route_ground[name]
        corners = np.array([(rect[0],rect[1]), (rect[0],rect[3]),
                            (rect[2],rect[1]), (rect[2],rect[3])])
        nearby = ((triangles[:,:,2].min(axis=1) <= floor+height) &
                  (triangles[:,:,2].max(axis=1) >= floor) &
                  (triangles[:,:,0].min(axis=1)+bounds[0] <= rect[2]) &
                  (triangles[:,:,0].max(axis=1)+bounds[2] >= rect[0]) &
                  (triangles[:,:,1].min(axis=1)+bounds[1] <= rect[3]) &
                  (triangles[:,:,1].max(axis=1)+bounds[3] >= rect[1]))
        for triangle in triangles[nearby]:
            polygon = list(triangle)
            for limit, above in ((floor, True), (floor+height, False)):
                clipped = []
                for a,b in zip(polygon, polygon[1:]+polygon[:1]):
                    a_in = a[2] >= limit if above else a[2] <= limit
                    b_in = b[2] >= limit if above else b[2] <= limit
                    if a_in:
                        clipped.append(a)
                    if a_in != b_in:
                        clipped.append(a+(b-a)*((limit-a[2])/(b[2]-a[2])))
                polygon = clipped
                if not polygon:
                    break
            if polygon:
                points = (corners[:,None,:]-np.array(polygon)[None,:,:2]).reshape(-1,2)
                forbidden.append(MultiPoint(points).convex_hull)
    occupied = unary_union(forbidden)
    clear = domain.difference(occupied.buffer(clearance, join_style=2))
    if clear.is_empty:
        return None
    nearest = nearest_points(Point(0,0), clear)[1]
    return dict(translation_m=[nearest.x,nearest.y], distance_m=nearest.distance(Point(0,0)),
                boundary_distance_m=Point(0,0).distance(domain.difference(occupied)),
                clearance_m=clearance, bounds_m=list(bounds), forbidden_polygons=len(forbidden))
