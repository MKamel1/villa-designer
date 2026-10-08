"""G4e authored shade habit, measured in metres; nursery identity unverified.

Counts and shape thresholds here implement this review brief, not botanical
standards. Face indices always refer to the delivered triangle geometry.
"""
import math
import numpy as np


def materials():
    return {'aspidistra-leaf':dict(kind='principled',base_rgb=[.035,.15,.045],reflectance=.10,
        roughness=.32,note='ASSUMED glossy dark-green Aspidistra optical appearance; NC State describes glossy leaves; no measured nursery sample or product')}


def clump(identifier, species, center, ground, data, *, bed, layer):
    from . import villa_landscape as L
    row=L.require_species(species,data)
    size=row['placement_assumptions']['procedural-clump']
    height=size['height']['range_m'][0];spread=size['spread']['range_m'][0]
    faces=[];slots=[];leaf_indices=[];canes=[];fans=[];leaves=[];nodes=[];segments=[]
    def skin(rings, material, leaf=False):
        start=len(faces)
        polygons=[rings[0][::-1],rings[-1]]+[[a[k],a[(k+1)%len(a)],b[(k+1)%len(a)],b[k]] for a,b in zip(rings,rings[1:]) for k in range(len(a))]
        triangles=[[f[0],f[k],f[k+1]] for f in polygons for k in range(1,len(f)-1)]
        # Each curved solid has outward winding independently of its axis.
        volume=sum(float(np.dot(f[0],np.cross(f[1],f[2]))) for f in triangles)
        if volume<0:triangles=[f[::-1] for f in triangles]
        faces.extend(triangles);slots.extend([material]*len(triangles))
        indices=list(range(start,len(faces)))
        if leaf:leaf_indices.extend(indices)
        return indices
    def tube(a,b,r,material='garden-foliage',fibrous=False):
        a,b=np.asarray(a),np.asarray(b);axis=b-a;axis/=np.linalg.norm(axis)
        helper=np.array([1.,0.,0.]) if abs(axis[2])>.9 else np.array([0.,0.,1.])
        u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
        rings=[]
        count=25 if fibrous else 2
        for j in range(count):
            point=a+(b-a)*j/(count-1)
            rings.append([(point+r*(1+.10*math.sin(k*7+j*3) if fibrous else 1)*(u*math.cos(k*math.tau/8)+v*math.sin(k*math.tau/8))).tolist() for k in range(8)])
        return skin(rings,material)
    def fan_segment(base,angle,offset,tilt,length,width,droop):
        radial=np.array([math.cos(angle),math.sin(angle),0.]);lateral=np.array([-radial[1],radial[0],0.])
        central=radial*math.cos(tilt)+np.array([0.,0.,math.sin(tilt)])
        direction=central*math.cos(offset)+lateral*math.sin(offset)
        normal=np.cross(lateral,central);side=np.cross(direction,normal);rings=[]
        for k in range(10):
            t=k/9;point=np.asarray(base)+direction*length*t-np.array([0.,0.,droop*t**4])
            w=width*(.52 if k==9 else max(.06,math.sin(math.pi*t)**.55))
            rings.append([(point-side*w).tolist(),(point-normal*.0012).tolist(),(point+side*w).tolist(),(point+normal*.002).tolist()])
        indices=skin(rings,'garden-foliage',True)
        segments.append(dict(tip=[rings[-1][0],rings[-1][2]],widest=[rings[5][0],rings[5][2]]))
        return indices
    if species=='Rhapis excelsa':
        for cane in range(13):
            angle=cane*math.pi*(3-math.sqrt(5));radius=.025+.09*math.sqrt(cane/12)
            root=np.array([radius*math.cos(angle),radius*math.sin(angle),0.])
            high=.46+.065*((cane*7)%13)
            tip=root+np.array([.016*math.cos(angle),.016*math.sin(angle),high])
            indices=tube(root,tip,.010+.001*(cane%3),'trellis',True)
            canes.append(dict(root=root.tolist(),tip=tip.tolist(),face_indices=indices))
            for level in range(4):
                z=high*(.27+.23*level)+.006*cane
                direction=angle+level*2.05+.13*cane
                attach=root+(tip-root)*min(z/high,1.)
                end=attach+np.array([(.12+.025*(level%2))*math.cos(direction),(.12+.025*(level%2))*math.sin(direction),.035])
                tube(attach,end,.004)
                nodes.append(dict(cane=cane,point=end.tolist()))
                count=7+cane%3;fan_faces=[]
                for segment in range(count):
                    fan_faces+=fan_segment(end,direction,(segment-(count-1)/2)*.29,.45+.15*((cane+level)%4),.28+.025*((cane+level)%4),.027,.045+.008*(cane%3))
                fans.append(dict(cane=cane,face_indices=fan_faces,segments=count))
    elif species=='Aspidistra elatior':
        for index in range(14):
            angle=index*math.pi*(3-math.sqrt(5));radial=np.array([math.cos(angle),math.sin(angle),0.]);side=np.array([-radial[1],radial[0],0.])
            radius=.025+.065*math.sqrt((index+.5)/14)
            root=radial*radius;petiole=.11+.023*((index*3)%6)
            base=root+radial*.035+np.array([0.,0.,petiole])
            petiole_faces=tube(root,base,.004)
            rings=[];centres=[]
            reach=.29+.025*(index%4);rise=.28+.015*((index*7)%5)
            arch=.84+.015*(index%4)
            for k in range(21):
                t=k/20;point=base+radial*reach*(.35*t+.65*t*t)+np.array([0.,0.,rise*math.sin(math.pi*arch*t)])
                # Broad elliptic-lanceolate lamina: middle maximum, pointed end.
                w=(.105+.008*(index%4))*max(.008,math.sin(math.pi*t)**.85)
                dz=rise*math.pi*arch*math.cos(math.pi*arch*t)
                dr=reach*(.35+1.30*t)
                normal=radial*dz-np.array([0.,0.,dr]);normal/=np.linalg.norm(normal)
                rings.append([(point-side*w).tolist(),(point-normal*.0015).tolist(),(point+side*w).tolist(),(point+normal*.0025).tolist()]);centres.append(point.tolist())
            indices=skin(rings,'aspidistra-leaf',True)
            leaves.append(dict(root=root.tolist(),petiole_face_indices=petiole_faces,face_indices=indices,centreline=centres))
    else:raise ValueError('No G4e habit builder for '+species)
    points=np.asarray([p for f in faces for p in f]);lo=points.min(axis=0);hi=points.max(axis=0)
    scale=np.array([spread/max((hi-lo)[:2])]*2+[height/(hi[2]-lo[2])]);offset=np.array([*center,ground]);origin=np.array([*(lo[:2]+hi[:2])/2,lo[2]])
    if species=='Aspidistra elatior':
        # An oval open spray retains the authored maximum foliage reach.
        # Across the fixed narrow beds, 0.86 of that reach keeps the physical
        # leaves inside the planting domain at unchanged clump centres/datums.
        scale[0]=.86*spread/(hi[0]-lo[0])
    def world(p):return (offset+(np.asarray(p)-origin)*scale).tolist()
    faces=[[world(p) for p in f] for f in faces]
    mesh=L._mesh(identifier.removeprefix('landscape-'),'dressing','aspidistra-leaf' if species=='Aspidistra elatior' else 'garden-foliage',faces,'ASSUMED young '+species+' authored appearance; photographic likeness, procurement and nursery performance UNVERIFIED; '+row['source_url']['value'],kind='plant-clump')
    # Preserve each shared builder's original recorded spread metadata;
    # the procedural young envelope above separately owns actual geometry.
    recorded_spread=row['spread']['range_m'][0 if species=='Rhapis excelsa' else 1]
    mesh.update(center=center,species=species,bed=bed,planting_layer=layer,root_z_m=ground,leaf_face_indices=leaf_indices,spread_m=recorded_spread,bevel_m=.0001,face_materials=slots)
    if canes:
        mesh['canes']=[dict(r,root=world(r['root']),tip=world(r['tip'])) for r in canes];mesh['fans']=fans
        mesh['crown_nodes']=[dict(r,point=world(r['point'])) for r in nodes]
        mesh['fan_segments']=[{k:[world(p) for p in v] for k,v in r.items()} for r in segments]
    if leaves:mesh['basal_leaves']=[dict(r,root=world(r['root']),centreline=[world(p) for p in r['centreline']]) for r in leaves]
    return mesh


def aspidistra_habit_metrics(mesh):
    """G4f authored morphology assumptions, measured from delivered triangles.

    Lean is the angle from vertical between the crown axis at soil and each
    blade tip. Width is the largest opposite-edge distance along a blade;
    length is the sum of distances along its physical section centres. Drop
    is the blade's highest surface minus its tip, divided by clump height.
    ASSUMED minima: mean lean 35 degrees, width/length .20, drop/height .18.
    These express 'well away', 'broad' and 'clearly lower' in the lead brief;
    they are appearance screens, not botanical standards or likeness proof.
    The skin's first four triangles cap base and tip; each following eight
    triangles connects four section corners. No declared centreline is read.
    """
    rows=[]
    all_points=np.asarray([p for f in mesh['faces'] for p in f])
    height=np.ptp(all_points[:,2]);axis=np.asarray(mesh['center'])
    for leaf in mesh.get('basal_leaves',[]):
        faces=[mesh['faces'][i] for i in leaf['face_indices']]
        current={tuple(p) for f in faces[:2] for p in f}
        sections=[np.asarray(sorted(current))]
        for start in range(4,len(faces),8):
            connected={tuple(p) for f in faces[start:start+8] for p in f}
            current=connected-current
            sections.append(np.asarray(sorted(current)))
        centres=np.asarray([ring.mean(axis=0) for ring in sections]);tip=centres[-1]
        length=np.linalg.norm(np.diff(centres,axis=0),axis=1).sum()
        width=max(np.linalg.norm(ring[:,None,:]-ring[None,:,:],axis=2).max() for ring in sections)
        blade=np.asarray(faces).reshape(-1,3)
        rows.append(dict(outward_lean_deg=float(math.degrees(math.atan2(np.linalg.norm(tip[:2]-axis),tip[2]-mesh['root_z_m']))),
                         width_length_ratio=float(width/length),tip_drop_height_ratio=float((blade[:,2].max()-tip[2])/height),
                         width_m=float(width),length_m=float(length),tip_drop_m=float(blade[:,2].max()-tip[2])))
    return dict(leaves=rows,mean_outward_lean_deg=float(np.mean([r['outward_lean_deg'] for r in rows])) if rows else 0.,
                minimum_width_length_ratio=min((r['width_length_ratio'] for r in rows),default=0.),
                minimum_tip_drop_height_ratio=min((r['tip_drop_height_ratio'] for r in rows),default=0.))


def habit_findings(meshes):
    """Measure delivered faces, not declared counts alone; assumptions in brief."""
    out=[]
    def points(m,indices):return np.asarray([p for i in indices for p in m['faces'][i]])
    for m in meshes:
        if m.get('species')=='Rhapis excelsa':
            canes=m.get('canes',[]);fans=m.get('fans',[])
            if len(canes)<9 or not fans:out.append(m['id']+': missing dense multi-cane fan habit');continue
            for i,cane in enumerate(canes):
                leaves=[r for r in fans if r['cane']==i]
                if len(leaves)<3 or any(not 5<=r['segments']<=10 for r in leaves):out.append(m['id']+': sparse upper-cane fans');break
                leaf_points=points(m,[j for r in leaves for j in r['face_indices']])
                cane_points=points(m,cane['face_indices'])
                if leaf_points[:,2].max()+.025<cane_points[:,2].max():out.append(m['id']+': bare cane above foliage');break
            leaf_points=points(m,m['leaf_face_indices']);height=leaf_points[:,2].max()-m['root_z_m']
            # Upper and middle thirds must each contain broad physical foliage.
            for low,high in ((1/3,2/3),(2/3,1.01)):
                band=leaf_points[(leaf_points[:,2]-m['root_z_m']>low*height)&(leaf_points[:,2]-m['root_z_m']<high*height)]
                if not len(band) or min(np.ptp(band,axis=0)[:2])<.45*max(np.ptp(leaf_points,axis=0)[:2]):out.append(m['id']+': skeletal foliage mass');break
        elif m.get('species')=='Aspidistra elatior':
            records=m.get('basal_leaves',[])
            if not 10<=len(records)<=16:out.append(m['id']+': missing loose basal fountain (10–16 leaves)')
            roots=[]
            for leaf in records:
                stem=points(m,leaf['petiole_face_indices']);roots.append(stem[stem[:,2].argmin(),:2])
                if abs(stem[:,2].min()-m['root_z_m'])>.01:out.append(m['id']+': petiole does not rise from soil');break
            if len(roots)>1 and max(np.ptp(roots,axis=0))<.08:out.append(m['id']+': common basal stalk')
            metrics=aspidistra_habit_metrics(m)
            if metrics['mean_outward_lean_deg']<35:out.append(m['id']+': upright bundle, insufficient outward tip lean')
            if metrics['minimum_width_length_ratio']<.20:out.append(m['id']+': narrow strap blades')
            if metrics['minimum_tip_drop_height_ratio']<.18:out.append(m['id']+': insufficient arch-over tip drop')
    return out


def fixture_projection(view,scene):
    """Actual fitting vertices in sensor-width fractions; distance in metres."""
    c=view['camera'];eye=np.asarray(c['position']);yaw=math.atan2(c['target'][1]-eye[1],c['target'][0]-eye[0]);half=view['resolution'][1]/view['resolution'][0]/2;rows=[]
    for m in scene.get('meshes',[]):
        if m.get('part_kind')!='lamp-housing' or not m.get('garden_g4d'):continue
        delta=np.asarray([p for f in m['faces'] for p in f])-eye
        depth=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
        if depth.min()<=0:continue
        x=c['lens_mm']/c['sensor_mm']*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/depth-c.get('shift_x',0.)
        y=c['lens_mm']/c['sensor_mm']*delta[:,2]/depth-c.get('shift_y',0.)
        width=max(0,min(.5,x.max())-max(-.5,x.min()));height=max(0,min(half,y.max())-max(-half,y.min()))
        rows.append(dict(id=m['id'],width=float(width),height=float(height),area_fraction=float(width*height/(2*half)),nearest_m=float(np.linalg.norm(delta,axis=1).min()),vertical_max=float(y.max())))
    return rows


def foreground_fixture_findings(view,scene):
    """Authored composition screen: near lower-frame fittings cannot dominate.

    A fitting over 3% of image width in the bottom third,
    is a foreground subject. This is a G4e composition intent, not a standard.
    """
    half=view['resolution'][1]/view['resolution'][0]/2
    candidates=[r for r in fixture_projection(view,scene)
                if r['width']>.03 and r['height']>0 and r['vertical_max']<-half/3]
    if not candidates:return []
    from .garden_render_review import subject_visibility_evidence
    evidence=subject_visibility_evidence(dict(view,visibility_targets=[r['id'] for r in candidates]),scene)
    return [view['id']+': foreground fixture body '+r['subject'] for r in evidence if r['visible']>=3]
