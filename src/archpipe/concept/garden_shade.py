"""Metre-native young shade foliage; authored appearances, not supplier assets.

Coordinates use x/y in the plot plane and z vertically, all in metres.
Leaf faces remain explicit so basal foliage is independently measurable.
"""
from math import cos, sin, pi
import numpy as np


def clump(identifier, species, center, ground, data, *, bed, layer):
    from . import villa_landscape as L
    row=L.require_species(species,data)
    size=row['placement_assumptions']['procedural-clump']
    height=size['height']['range_m'][0];spread=size['spread']['range_m'][0]
    faces=[];leaf_indices=[];slots=[];laminae=[];crown_nodes=[];fan_tips=[]

    def add(polygons, leaf=False, variegated=False):
        for face_index, f in enumerate(polygons):
            for k in range(1,len(f)-1):
                if leaf:leaf_indices.append(len(faces))
                faces.append([f[0],f[k],f[k+1]])
                slots.append('shade-variegation' if variegated and face_index%4==1 else 'garden-foliage')

    def tube(a,b,r=.009):
        a,b=np.array(a),np.array(b);axis=b-a;axis/=np.linalg.norm(axis)
        helper=np.array([0.,0.,1.]) if abs(axis[2])<.9 else np.array([1.,0.,0.])
        u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
        low,high=[[(p+r*(u*cos(k*pi/3)+v*sin(k*pi/3))).tolist() for k in range(6)] for p in (a,b)]
        add([low[::-1],high]+[[low[k],low[(k+1)%6],high[(k+1)%6],high[k]] for k in range(6)])

    def blade(base, direction, length, width, rise, droop=0.,variegated=False,truncate=False):
        base=np.array(base);radial=np.array([cos(direction),sin(direction),0.]);side=np.array([-sin(direction),cos(direction),0.])
        rings=[]
        for k in range(13):
            t=k/12;point=base+radial*length*t+np.array([0.,0.,rise*t-droop*t*t])
            w=width*(.65 if truncate and k==12 else max(.012,sin(pi*t)**.65))
            rings.append([(point-side*w).tolist(),(point-np.array([0.,0.,.002])).tolist(),(point+side*w).tolist(),(point+np.array([0.,0.,.006])).tolist()])
        if truncate:fan_tips.append(dict(tip=[rings[-1][0],rings[-1][2]],widest=[rings[6][0],rings[6][2]]))
        add([rings[0][::-1],rings[-1]]+[[a[k],a[(k+1)%4],b[(k+1)%4],b[k]] for a,b in zip(rings,rings[1:]) for k in range(4)],True,variegated)

    if species in ('Chlorophytum comosum','Ophiopogon japonicus'):
        for i in range(32 if species.startswith('Ophiopogon') else 23):
            angle=i*pi*(3-5**.5)
            blade((0,0,0),angle,.48+.05*(i%3),.013 if species.startswith('Ophiopogon') else .022,.9+.08*(i%5),.8,variegated=species.startswith('Chlorophytum'))
    elif species=='Fatsia japonica':
        for i in range(15):
            angle=i*pi*(3-5**.5);z=.09 if i<3 else .32+.08*(i%7)
            end=(.19*cos(angle),.19*sin(angle),z)
            tube((0,0,0),end)
            # One continuous palmately lobed lamina, not seven separate
            # fan blades. Seven pointed lobes encircle the petiole.
            upper=[];lower=[]
            for k in range(42):
                a=angle+k*2*pi/42
                radius=(.12,.18,.24,.27,.24,.18)[k%6]
                z=end[2]-.075*(radius/.27)**2+.04*cos(a-angle)
                point=[end[0]+radius*cos(a),end[1]+radius*sin(a),z]
                upper.append(point);lower.append([point[0],point[1],point[2]-.004])
            top=list(end);bottom=[end[0],end[1],end[2]-.004]
            start=len(faces)
            add([[top,upper[k],upper[(k+1)%42]] for k in range(42)]+
                [[bottom,lower[(k+1)%42],lower[k]] for k in range(42)]+
                [[upper[k],lower[k],lower[(k+1)%42],upper[(k+1)%42]] for k in range(42)],True)
            laminae.append(dict(face_indices=list(range(start,len(faces))),outline=upper,petiole=top))
    elif species=='Rhapis excelsa':
        for cane in range(5):
            angle=cane*2*pi/5;root=(.07*cos(angle),.07*sin(angle),0)
            tip=(root[0],root[1],.65+.075*cane);tube(root,tip,.013)
            for level in (.08+.011*cane,.29+.043*((cane*3)%5),tip[2]):
                end=(root[0]+.32*cos(angle),root[1]+.32*sin(angle),level)
                tube((root[0],root[1],max(0,level-.09)),end,.006)
                crown_nodes.append(dict(cane=cane,point=end))
                for segment in range(9):
                    blade(end,angle+(segment-4)*.19,.31,.024,.18,.07,truncate=True)
    else:
        raise ValueError('No shade botanical builder for '+species)
    points=[q for f in faces for q in f];lo=np.min(points,axis=0);hi=np.max(points,axis=0)
    scale=np.array([spread/max((hi-lo)[:2])]*2+[height/(hi[2]-lo[2])])
    offset=np.array([center[0],center[1],ground]);origin=np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
    faces=[[(offset+(np.array(q)-origin)*scale).tolist() for q in f] for f in faces]
    mesh=L._mesh(identifier,'dressing','garden-foliage',faces,'ASSUMED young '+species+' authored botanical appearance; nursery procurement and photographic likeness UNVERIFIED; '+row['source_url']['value'],kind='plant-clump')
    mesh.update(center=center,species=species,bed=bed,planting_layer=layer,root_z_m=ground,leaf_face_indices=leaf_indices,spread_m=row['spread']['range_m'][0],bevel_m=.0001)
    def world(q):return (offset+(np.array(q)-origin)*scale).tolist()
    if laminae:mesh['palmate_laminae']=[dict(face_indices=r['face_indices'],outline=[world(q) for q in r['outline']],petiole=world(r['petiole'])) for r in laminae]
    if crown_nodes:mesh['crown_nodes']=[dict(cane=r['cane'],point=world(r['point'])) for r in crown_nodes]
    if fan_tips:mesh['fan_segments']=[{key:[world(q) for q in points] for key,points in r.items()} for r in fan_tips]
    if 'shade-variegation' in slots:mesh['face_materials']=slots
    return mesh


def stone(identifier,center,ground):
    """Closed irregular mineral stone, with its base exactly on court soil."""
    from . import villa_landscape as L
    rings=[]
    for z,factor in ((0,.78),(.08,.96),(.22,1),(.35,.82),(.43,.47)):
        rings.append([[center[0]+.34*factor*(1+.15*sin(i*7+z*11))*cos(i*pi/8),center[1]+.27*factor*(1+.12*cos(i*5+z*8))*sin(i*pi/8),ground+z+(.025*sin(i*3+z*9) if z else 0)] for i in range(16)])
    faces=[rings[0][::-1],rings[-1]]+[[a[k],a[(k+1)%16],b[(k+1)%16],b[k]] for a,b in zip(rings,rings[1:]) for k in range(16)]
    faces=[[f[0],f[k],f[k+1]] for f in faces for k in range(1,len(f)-1)]
    mesh=L._mesh(identifier,'dressing','stone-substrate',faces,'ASSUMED irregular feature stone appearance; no supplier product claim',kind='feature-stone')
    mesh['stone_rings']=rings
    return mesh


def form_findings(meshes):
    """Measured authored shape invariants, not horticultural size standards.

    Palmate leaves require one closed connected lamina per leaf; fans require
    independent crown levels and broad terminal segments. Irregular feature
    stones require an uneven radial shell. Review still judges resemblance.
    """
    from collections import defaultdict
    from .physical_part import geometry_errors
    findings=[]
    for m in meshes:
        if m.get('species')=='Fatsia japonica':
            records=m.get('palmate_laminae',[])
            if not records:findings.append(m['id']+': missing continuous palmate laminae')
            for record in records:
                faces=[m['faces'][i] for i in record['face_indices']]
                if geometry_errors(faces):findings.append(m['id']+': palmate lamina must be closed')
                # Edge adjacency prevents disconnected blades sharing only
                # a petiole point from masquerading as one broad leaf.
                edges=defaultdict(list)
                for i,face in enumerate(faces):
                    for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((tuple(a),tuple(b))))].append(i)
                adjacency=defaultdict(set)
                for indices in edges.values():
                    for i in indices:adjacency[i].update(indices)
                reached=set();todo=[0]
                while todo:
                    i=todo.pop()
                    if i not in reached:reached.add(i);todo.extend(adjacency[i]-reached)
                if len(reached)!=len(faces):findings.append(m['id']+': disconnected palmate blades')
                if len(record['outline'])!=42:findings.append(m['id']+': missing authored seven-lobe outline')
        if m.get('species')=='Rhapis excelsa':
            nodes=m.get('crown_nodes',[]);segments=m.get('fan_segments',[])
            if not nodes or not segments:findings.append(m['id']+': missing measured fan crowns/segments')
            else:
                levels=defaultdict(set)
                for r in nodes:levels[round(r['point'][2],6)].add(r['cane'])
                if any(len(canes)>=3 for canes in levels.values()):findings.append(m['id']+': repeated aligned fan tiers')
                for r in segments:
                    width=lambda q:float(np.linalg.norm(np.array(q[0])-q[1]))
                    if width(r['tip'])<.4*width(r['widest']):
                        findings.append(m['id']+': pointed fan segment; authored broad truncate tip required');break
        if m.get('part_kind')=='feature-stone':
            rings=m.get('stone_rings',[])
            if not rings:findings.append(m['id']+': missing irregular shell measurement')
            else:
                outlines=[]
                for ring in rings:
                    points=np.array(ring)[:,:2]
                    span=np.ptp(points,axis=0)
                    outlines.append((points-points.mean(axis=0))/span)
                if all(a.shape==outlines[0].shape and np.allclose(a,outlines[0],atol=1e-6) for a in outlines[1:]):
                    findings.append(m['id']+': repeated aligned stone rings')

    return findings
