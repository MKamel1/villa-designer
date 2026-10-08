"""Deterministic Bougainvillea placement inside a measured vertical envelope.

`box` is (minimum x, minimum y, minimum z, maximum x, maximum y, maximum z)
in metres. Density counts visible foliage and bracts per square metre of the
largest vertical face. The 70 percent foliage share is an ASSUMED render detail.

Client round-3 defect (v01/v02/v24 etc.): the trellis climbers read as
"almost invisible: too sparse/small" at the previous density=120. SIZE below
gives each instance's HALF-extent in metres (so a "leaf" spans ~2*0.032 =
6.4 cm, inside the requested 5-8 cm; a "bract" spans ~3.6 cm, inside 3-4 cm).
`placements` renders each instance as a rhombus (two half-diagonals SIZE[kind]),
so one instance's area is 2 * half * half. For independently, uniformly
scattered instances the probability a given point on the face is covered by
at least one instance is 1 - exp(-density * mean_instance_area) (a 2D Poisson
coverage model); `coverage_estimate` computes that, and `density_for_coverage`
inverts it (with a safety margin, since edge-clipped instances near the
envelope boundary cover less than their nominal area) to find the density
needed for a stated coverage fraction. villa_scene.build_climbers calls
`density_for_coverage()` instead of hardcoding a count, so raising the
coverage target here raises the render automatically. The current default
is ASSUMED young planting at 35 percent target coverage so the open frame
remains visible; the 80 percent target used for the earlier sparse-climber
correction is historical.
"""
from __future__ import annotations

import math
import random

# Half-extent (metres) of one leaf/bract instance, shared with
# archpipe.blender.villa_scene.build_climbers so the coverage estimate below
# describes exactly what gets rendered, not a guess.
SIZE = {"leaf": 0.032, "bract": 0.018}
LEAF_FRACTION = 0.70
COVERAGE_TARGET = 0.35  # ASSUMED young planting: leave most open lattice visible.


def _instance_area(kind):
    half = SIZE[kind]
    return 2 * half * half     # rhombus, half-diagonals (half, half)


def mean_instance_area(leaf_fraction=LEAF_FRACTION):
    return leaf_fraction * _instance_area("leaf") + (1 - leaf_fraction) * _instance_area("bract")


def coverage_estimate(density, leaf_fraction=LEAF_FRACTION):
    """Fraction of the face expected to be covered by at least one instance
    (2D Poisson coverage model; see module docstring)."""
    return 1 - math.exp(-density * mean_instance_area(leaf_fraction))


def density_for_coverage(target=COVERAGE_TARGET, leaf_fraction=LEAF_FRACTION, safety=1.25):
    """Instances per square metre needed for >= `target` coverage, with a
    safety margin for instances the envelope boundary clips (a leaf half off
    the edge of a shallow trellis mass covers less than its nominal area)."""
    if not 0 < target < 1:
        raise ValueError("target coverage must be between 0 and 1")
    raw = -math.log(1 - target) / mean_instance_area(leaf_fraction)
    return raw * safety


def placements(box, density=120, seed=7):
    x0, y0, z0, x1, y1, z1 = box
    if not (x0 < x1 and y0 < y1 and z0 < z1 and density > 0):
        raise ValueError("positive envelope and density required")
    area = max(x1-x0, y1-y0) * (z1-z0)
    count = max(1, math.ceil(area * density))
    rng = random.Random(seed)
    result = []
    for index in range(count):
        # Stratify height and alternate the two faces to cover the whole trellis.
        z = z0 + (index + rng.random()) / count * (z1-z0)
        result.append((x0 + rng.random()*(x1-x0), y0 + rng.random()*(y1-y0), z,
                       "leaf" if index % 10 < 7 else "bract"))
    rng.shuffle(result)
    return result


def grape_ivy_faces(box, seed=7):
    """Young trifoliate grape-ivy leaves, no blossom/bract fallback.

    Three serrated leaflets meet at each petiole on the large vertical
    plane. Coordinates are metres; the complete leaves stay in the measured
    source envelope. Coverage remains the ASSUMED 35 percent young intent.
    """
    x0,y0,z0,x1,y1,z1=box
    along_y=(y1-y0)>(x1-x0)
    result=[]
    # Triplets occupy approximately three ordinary leaf areas.
    density=density_for_coverage(leaf_fraction=1.)/3
    for x,y,z,_ in placements(box,density,seed):
        across=y if along_y else x
        centre=(y0+y1)/2 if along_y else (x0+x1)/2
        across=centre+(across-centre)*.94
        z=(z0+z1)/2+(z-(z0+z1)/2)*.94
        for leaflet in range(3):
            angle=(leaflet-1)*.9
            # Serrated lanceolate perimeter, with narrow base at petiole.
            shape=[(0,0),(-.012,.013),(-.021,.025),(-.017,.032),(-.022,.041),(-.015,.049),(0,.070),(.015,.049),(.022,.041),(.017,.032),(.021,.025),(.012,.013)]
            polygon=[]
            for u,v in shape:
                aa=across+u*math.cos(angle)+v*math.sin(angle)
                zz=z-u*math.sin(angle)+v*math.cos(angle)
                if along_y:polygon.append([x,min(y1,max(y0,aa)),min(z1,max(z0,zz))])
                else:polygon.append([min(x1,max(x0,aa)),y,min(z1,max(z0,zz))])
            # Ear clipping is handled by Blender for the visible thin leaf.
            result.append(polygon)
    return result


def _closest_triangle(point, a, b, c):
    """Closest point on a physical triangle, including its edges."""
    sub=lambda u,v:tuple(x-y for x,y in zip(u,v))
    dot=lambda u,v:sum(x*y for x,y in zip(u,v))
    add=lambda u,v,s:tuple(x+s*y for x,y in zip(u,v))
    ab,ac,ap=sub(b,a),sub(c,a),sub(point,a)
    d1,d2=dot(ab,ap),dot(ac,ap)
    if d1<=0 and d2<=0:return a
    bp=sub(point,b);d3,d4=dot(ab,bp),dot(ac,bp)
    if d3>=0 and d4<=d3:return b
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:return add(a,ab,d1/(d1-d3))
    cp=sub(point,c);d5,d6=dot(ab,cp),dot(ac,cp)
    if d6>=0 and d5<=d6:return c
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:return add(a,ac,d2/(d2-d6))
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:return add(b,sub(c,b),(d4-d3)/(d4-d3+d5-d6))
    denominator=va+vb+vc
    if abs(denominator)<1e-18:return a
    return add(add(a,ab,vb/denominator),ac,vc/denominator)


def grape_ivy_geometry(box, branch_faces, seed=7):
    """Connect every trifoliate petiole to the actual training-stem surface.

    Returns leaf polygons, closed metre-native petiole solids and measured
    root/contact pairs. No botanical topology is left to random scattering.
    """
    if not branch_faces:raise ValueError('Cissus foliage requires physical training stems')
    leaves=grape_ivy_faces(box,seed);petioles=[];contacts=[]
    triangles=[(f[0],f[k],f[k+1]) for f in branch_faces for k in range(1,len(f)-1)]
    for leaf in leaves[::3]:
        root=leaf[0]
        candidates=[_closest_triangle(root,*t) for t in triangles]
        contact=min(candidates,key=lambda q:sum((q[k]-root[k])**2 for k in range(3)))
        contacts.append(dict(root=root,contact=contact))
        axis=[root[k]-contact[k] for k in range(3)];length=math.sqrt(sum(v*v for v in axis))
        if length<1e-7:continue
        axis=[v/length for v in axis]
        helper=[0,0,1] if abs(axis[2])<.9 else [1,0,0]
        u=[axis[1]*helper[2]-axis[2]*helper[1],axis[2]*helper[0]-axis[0]*helper[2],axis[0]*helper[1]-axis[1]*helper[0]]
        norm=math.sqrt(sum(v*v for v in u));u=[v/norm for v in u]
        v=[axis[1]*u[2]-axis[2]*u[1],axis[2]*u[0]-axis[0]*u[2],axis[0]*u[1]-axis[1]*u[0]]
        # Embed into both stem and lamina by 1 mm.
        rings=[[[point[k]+.0012*(u[k]*math.cos(i*math.pi/3)+v[k]*math.sin(i*math.pi/3)) for k in range(3)] for i in range(6)] for point in ([contact[k]-.001*axis[k] for k in range(3)],[root[k]+.001*axis[k] for k in range(3)])]
        a,b=rings;petioles += [a[::-1],b]+[[a[i],a[(i+1)%6],b[(i+1)%6],b[i]] for i in range(6)]
    return leaves,petioles,contacts


def ivy_connection_findings(leaves, petioles, branch_faces):
    """Measure lamina-root contact with physical stems and petiole solids."""
    findings=[]
    triangles=[(f[0],f[k],f[k+1]) for f in branch_faces for k in range(1,len(f)-1)]
    def close(point):
        return any(sum((q[k]-point[k])**2 for k in range(3))<=1e-12 for q in (_closest_triangle(point,*t) for t in triangles))
    supports=[]
    for i in range(0,len(petioles),8):
        low,high=petioles[i:i+2]
        a=[sum(q[k] for q in low)/len(low) for k in range(3)]
        b=[sum(q[k] for q in high)/len(high) for k in range(3)]
        radius=min(math.sqrt(sum((q[k]-a[k])**2 for k in range(3))) for q in low)
        supports.append((a,b,radius))
    for i,leaf in enumerate(leaves[::3]):
        root=leaf[0]
        if close(root):continue
        connected=False
        for a,b,radius in supports:
            axis=[b[k]-a[k] for k in range(3)];den=sum(v*v for v in axis)
            if not den:continue
            t=sum((root[k]-a[k])*axis[k] for k in range(3))/den
            radial=math.sqrt(sum((root[k]-a[k]-t*axis[k])**2 for k in range(3)))
            if 0<=t<=1 and radial<=radius+1e-9:
                # The near end is embedded 1 mm inside a real stem; measure
                # proximity at that endpoint, not a declared contact token.
                if any(math.sqrt(sum((q[k]-a[k])**2 for k in range(3)))<=.00101 for q in (_closest_triangle(a,*tri) for tri in triangles)):
                    connected=True;break
        if not connected:findings.append('leaf triplet %d is disconnected from training stems'%i)
    return findings
