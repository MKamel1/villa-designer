"""Closed connected collider shells; plane-side tests are not containment.

All points are metres in world coordinates. The one-micrometre weld joins
exported material/normal seams for topology only; it never moves a vertex.
Open surfaces still participate in exact surface-crossing checks.
"""
from collections import Counter

WELD_DECIMALS = 6
RAY_DIRECTIONS = ((1.,.371,.529),(-.23,1.,.43),(.29,-.31,1.))


def face_shells(points, faces):
    """Return source face indices and whether every shell edge has two faces."""
    parent={}
    def root(key):
        parent.setdefault(key,key)
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    keys=[tuple(round(float(v),WELD_DECIMALS) for v in point) for point in points]
    for face in faces:
        for i in face:parent[root(keys[i])]=root(keys[face[0]])
    groups={}
    for index,face in enumerate(faces):groups.setdefault(root(keys[face[0]]),[]).append(index)
    result=[]
    for indices in groups.values():
        edges=Counter(tuple(sorted((keys[face[i]],keys[face[(i+1)%len(face)]])))
                      for index in indices for face in [faces[index]] for i in range(len(face)))
        result.append(dict(face_indices=indices,closed=bool(edges) and all(n==2 for n in edges.values())))
    return result


def ray_hits(triangles, point, direction):
    """Independent vectorized ray/triangle distances; co-located hits merge.

    A hit is a positive distance along a normalized ray. Parallel triangles
    have zero determinant. Barycentric weights locate the hit on a triangle.
    Numerical merging at ten micrometres removes duplicate shared-edge hits.
    """
    import numpy as np
    t=np.asarray(triangles,float);p=np.asarray(point,float);d=np.asarray(direction,float);d/=np.linalg.norm(d)
    edge1=t[:,1]-t[:,0];edge2=t[:,2]-t[:,0]
    h=np.cross(d,edge2);det=np.einsum('ij,ij->i',edge1,h)
    inverse=np.divide(1.,det,out=np.zeros_like(det),where=np.abs(det)>1e-12)
    s=p-t[:,0];u=inverse*np.einsum('ij,ij->i',s,h);q=np.cross(s,edge1)
    v=inverse*(q@d);distance=inverse*np.einsum('ij,ij->i',edge2,q)
    hits=np.sort(distance[(np.abs(det)>1e-12)&(u>=0)&(v>=0)&(u+v<=1)&(distance>1e-5)])
    return hits[np.r_[True,np.diff(hits)>1e-5]].tolist() if len(hits) else []


def closed_shell_contains(triangles, point):
    """True inside, False outside; disagreeing rays return None (unresolved)."""
    votes=[len(ray_hits(triangles,point,d))%2==1 for d in RAY_DIRECTIONS]
    return votes[0] if len(set(votes))==1 else None
