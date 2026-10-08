"""Render-host-only raw glTF reader used by the tracked geometry generator."""
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

