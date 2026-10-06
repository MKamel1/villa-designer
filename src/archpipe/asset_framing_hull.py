"""Convex-hull vertices for framing, with exact signs near coplanar faces.

Coordinates stay unchanged. The determinant sign says which side of an
oriented face a point occupies; uncertain floating signs use rational
arithmetic on the original binary floating-point values. No hull is used
for route obstruction geometry.
"""
from fractions import Fraction
import numpy as np


def _signs(points, face):
    a, b, c = face
    normal = np.cross(b-a, c-a)
    delta = points-a
    values = delta @ normal
    # A deliberately generous roundoff bound selects exact fallback, never
    # rejects a point. Fraction(float) represents the float exactly.
    size = np.max(np.abs(np.concatenate((face, points), axis=0)))
    uncertain = np.abs(values) <= 128*np.finfo(float).eps*max(1., size)**3
    signs = np.sign(values)
    if uncertain.any():
        aa, bb, cc = [[Fraction(float(x)) for x in p] for p in face]
        ab = [y-x for x,y in zip(aa,bb)]
        ac = [y-x for x,y in zip(aa,cc)]
        exact_normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
        for index in np.flatnonzero(uncertain):
            d = [Fraction(float(x))-y for x,y in zip(points[index],aa)]
            value = sum(x*y for x,y in zip(d,exact_normal))
            signs[index] = (value > 0)-(value < 0)
    return signs, values


def framing_hull_vertices(points):
    """Return only original hull vertices; handle point, line and plane inputs."""
    points = np.unique(np.asarray(points, dtype=float).reshape(-1,3), axis=0)
    if not len(points) or not np.isfinite(points).all():
        raise ValueError('empty or non-finite framing geometry')
    if len(points) == 1:
        return points
    a = 0
    b = int(np.argmax(np.linalg.norm(points-points[a],axis=1)))
    cross = np.cross(points[b]-points[a],points-points[a])
    c = int(np.argmax(np.linalg.norm(cross,axis=1)))
    if not np.any(cross):
        axis = int(np.argmax(np.abs(points[b]-points[a])))
        return points[[np.argmin(points[:,axis]),np.argmax(points[:,axis])]]
    signs, distances = _signs(points,points[[a,b,c]])
    if not np.any(signs):
        # Monotone chain in a nonsingular coordinate projection of the plane.
        axes = np.delete(np.arange(3),np.argmax(np.abs(cross[c])))
        order = np.lexsort((points[:,axes[1]],points[:,axes[0]]))
        def turn(i,j,k):
            p,q,r = [[Fraction(float(x)) for x in points[n,axes]] for n in (i,j,k)]
            return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        def chain(indices):
            result=[]
            for index in indices:
                while len(result)>1 and turn(result[-2],result[-1],index)<=0:
                    result.pop()
                result.append(index)
            return result
        lower,upper=chain(order),chain(order[::-1])
        return points[sorted(set(lower[:-1]+upper[:-1]))]
    d = int(np.argmax(np.abs(distances)))
    if signs[d] == 0:
        d = int(np.flatnonzero(signs)[0])
    seed=[a,b,c,d]
    interior=points[seed].mean(axis=0)
    def oriented(face):
        if _signs(interior[None,:],points[list(face)])[0][0]>0:
            face=(face[0],face[2],face[1])
        return face
    faces={}
    unassigned=np.setdiff1d(np.arange(len(points)),seed)
    for face in ((a,b,c),(a,d,b),(a,c,d),(b,d,c)):
        face=oriented(face)
        outside=_signs(points[unassigned],points[list(face)])[0]>0
        faces[face]=unassigned[outside]
        unassigned=unassigned[~outside]
    while True:
        selected=next((face for face,indices in faces.items() if len(indices)),None)
        if selected is None:
            break
        indices=faces[selected]
        distances=_signs(points[indices],points[list(selected)])[1]
        eye=int(indices[np.argmax(distances)])
        visible=[face for face in faces if _signs(points[eye:eye+1],points[list(face)])[0][0]>0]
        horizon={}
        candidates=[]
        for face in visible:
            candidates.extend(faces.pop(face))
            for edge in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
                reverse=(edge[1],edge[0])
                if reverse in horizon:
                    del horizon[reverse]
                else:
                    horizon[edge]=True
        candidates=np.array(sorted(set(candidates)-{eye}),dtype=int)
        for edge in horizon:
            face=oriented((*edge,eye))
            outside=_signs(points[candidates],points[list(face)])[0]>0 if len(candidates) else np.zeros(0,dtype=bool)
            faces[face]=candidates[outside]
            candidates=candidates[~outside]
    return points[sorted({i for face in faces for i in face})]
