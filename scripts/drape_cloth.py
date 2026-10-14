"""Blender-only gravity cloth bake. Fixed inputs, one process/thread, no wind.

Input/output JSON paths follow Blender's '--'. All coordinates are metres.
Owned patterns, seam/collar form and material appearance are ASSUMED.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import bpy


def bake(data):
    from archpipe.concept.garments import folded,loft,rounded_ring
    from archpipe.imported_appearance import digest
    if data.get('runtime') and data['runtime']['blender_version']!=bpy.app.version_string:
        raise ValueError('unpinned Blender cloth runtime')
    rule=data['policy'];random.seed(rule['seed'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.gravity=rule['gravity_m_s2']
    scene.render.threads_mode='FIXED';scene.render.threads=1
    scene.frame_end=rule['frames']
    typ=data['garment_type'];source=data['faces']
    if data['kind']=='folded-fabric':
        # Rounded individual folded layers retain their measured shelf bases.
        p=[p for f in source for p in f]
        low=[min(q[k] for q in p) for k in range(3)]
        high=[max(q[k] for q in p) for k in range(3)]
        w,d,h=[high[k]-low[k] for k in range(3)]
        rings=[]
        for i in range(13):
            t=i/12;scale=.88+.10*math.sin(math.pi*t)**.5
            ring=rounded_ring(0,0,w*scale,d*scale,h*t,min(h*.28,w*.12,d*.12))
            for q in ring:
                q[2]+=.0008*math.sin(q[0]*47+q[1]*31)*math.sin(math.pi*t)
            rings.append(ring)
        faces=loft(rings)
        return dict(faces=faces,skin_vertices=rings[-1],boundary_indices=list(range(len(rings[-1]))),
                    simulation=dict(method='ASSUMED procedural rounded folded layers',seed=rule['seed']))
    # Use the measured cut silhouette for shirts, jackets and long garments.
    # The two skins of the old extrusion alternated in its first 2048 faces.
    if typ!='trousers':
        first_edge=next(i for i,f in enumerate(source) if len(f)!=3)
        original=source[:first_edge:2]
        # Structured quad cloth, cut from the frozen measured silhouette.
        # Triangle fans concentrated artificial diagonal wrinkles; uniform
        # warp/weft edges avoid directional stiffness from that topology.
        edge_counts={}
        for face in original:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((tuple(a[1:]),tuple(b[1:]))))
                edge_counts[edge]=edge_counts.get(edge,0)+1
        boundary_edges=[e for e,n in edge_counts.items() if n==1]
        def inside(y,z):
            crossings=0
            for (ay,az),(by,bz) in boundary_edges:
                if (az>z)!=(bz>z) and y<ay+(by-ay)*(z-az)/(bz-az):crossings+=1
            return crossings%2==1
        top=max(q[2] for f in original for q in f)
        width=.53;columns=80;rows=max(50,round(top/.010))
        verts=[];polys=[];index={}
        for i in range(rows):
            for j in range(columns):
                corners=[(j,i),(j+1,i),(j+1,i+1),(j,i+1)]
                if not all(inside(-width/2+width*jj/columns,top*ii/rows) for jj,ii in corners):continue
                poly=[]
                for jj,ii in corners:
                    key=(jj,ii)
                    if key not in index:
                        y=-width/2+width*jj/columns;z=top*ii/rows
                        fraction=(top-z)/top
                        z+=.012*fraction+.0025*math.sin(y*81)*fraction**3
                        amplitude=.0045+.004*math.sin(math.pi*fraction)
                        x=amplitude*math.sin(y*79+fraction*.4)
                        index[key]=len(verts);verts.append([x,y,z])
                    poly.append(index[key])
                polys.append(poly)
        # Project raster boundary vertices onto the measured cut contour
        # BEFORE gravity evaluation. Welding removes the collapsed grid edges;
        # output is never clamped or displaced to pass containment.
        counts={}
        for poly in polys:
            for a,b in zip(poly,poly[1:]+poly[:1]):
                edge=tuple(sorted((a,b)));counts[edge]=counts.get(edge,0)+1
        outer={i for edge,n in counts.items() if n==1 for i in edge}
        # Recover unlifted initial positions from grid identity.
        identities={v:k for k,v in index.items()}
        for vi in outer:
            jj,ii=identities[vi];y=-width/2+width*jj/columns;z=top*ii/rows
            candidates=[]
            for (ay,az),(by,bz) in boundary_edges:
                dy,dz=by-ay,bz-az
                t=max(0,min(1,((y-ay)*dy+(z-az)*dz)/(dy*dy+dz*dz)))
                yy,zz=ay+t*dy,az+t*dz
                candidates.append(((yy-y)**2+(zz-z)**2,yy,zz))
            _,y,z=min(candidates)
            fraction=(top-z)/top
            zz=z+.012*fraction+.0025*math.sin(y*81)*fraction**3
            amplitude=.0045+.004*math.sin(math.pi*fraction)
            verts[vi]=[amplitude*math.sin(y*79+fraction*.4),y,zz]
        # Deform the rest pattern with restrained nonuniform vertical folds.
        for q in verts:
            fraction=(top-q[2])/top;y=q[1]
            q[0]=(.0038*math.sin(y*79+fraction*2.8)+.0021*math.sin(y*43+fraction*4.1)+
                   .0010*math.sin(y*141-fraction*1.9))*(.5+.5*math.sin(math.pi*fraction)**.5)
        unique={};merged=[];remap={}
        for vi,q in enumerate(verts):
            key=tuple(round(v,9) for v in q)
            if key not in unique:unique[key]=len(merged);merged.append(q)
            remap[vi]=unique[key]
        welded=[]
        for poly in polys:
            ids=list(dict.fromkeys(remap[i] for i in poly))
            if len(ids)>=3:welded.append(ids)
        verts,polys=merged,welded
        pins=[i for i,p in enumerate(verts) if p[2]>top-.080]
    else:
        # A single continuous pattern goes over the existing hanger bar;
        # both leg panels hang from the bar, without a squared folded slab.
        p=[q for f in source for q in f];top=max(q[2] for q in p)-.001
        verts=[];polys=[];pins=[]
        rows=60;cols=24
        for side in (-1,1):
            base=len(verts)
            for i in range(rows+1):
                t=i/rows
                for j in range(cols+1):
                    y=-.130+.260*j/cols
                    x=side*(.005+.004*math.sin(y*99)*math.sin(math.pi*t))
                    z=top-(top-.018)*t+.002*math.sin(y*89)*t**3
                    verts.append([x,y,z])
                    if i==0:pins.append(len(verts)-1)
            for i in range(rows):
                for j in range(cols):
                    if i>6 and j in (11,12):continue
                    a=base+i*(cols+1)+j
                    quad=[a,a+1,a+cols+2,a+cols+1]
                    polys.append(quad if side==-1 else quad[::-1])
        # Join the folded nose, so the bar passes inside a real U fold.
        base=(rows+1)*(cols+1)
        for j in range(cols):polys.append([j,j+base,j+base+1,j+1])
    # Omit unused grid vertices so they cannot free-fall into morphology
    # measurements when a trouser-leg gap removes its adjacent cells.
    used=sorted({i for f in polys for i in f});remap={old:new for new,old in enumerate(used)}
    verts=[verts[i] for i in used];polys=[[remap[i] for i in f] for f in polys]
    pins=[remap[i] for i in pins if i in remap]
    mesh=bpy.data.meshes.new('cloth pattern');mesh.from_pydata(verts,[],polys);mesh.update()
    obj=bpy.data.objects.new('pinned garment',mesh);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    group=obj.vertex_groups.new(name='hanger shoulders');group.add(pins,1.,'REPLACE')
    cloth=obj.modifiers.new('gravity only fixed frames','CLOTH')
    cloth.settings.quality=rule['solver_quality'];cloth.settings.mass=.10
    cloth.settings.tension_stiffness=80;cloth.settings.compression_stiffness=80
    cloth.settings.shear_stiffness=40;cloth.settings.bending_stiffness=.5
    cloth.settings.vertex_group_mass=group.name
    cloth.settings.air_damping=2.;cloth.settings.effector_weights.all=0;cloth.settings.effector_weights.gravity=1
    cloth.collision_settings.use_collision=False;cloth.collision_settings.use_self_collision=False
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=rule['frames']
    for frame in range(1,rule['frames']+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        # Force solver evaluation at every frame in a headless process.
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated.to_mesh();evaluated.to_mesh_clear()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());skin=evaluated.to_mesh()
    skin_vertices=[list(v.co) for v in skin.vertices]
    counts={}
    for f in skin.polygons:
        ids=list(f.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            edge=tuple(sorted((a,b)));counts[edge]=counts.get(edge,0)+1
    boundary=sorted({i for e,n in counts.items() if n==1 for i in e})
    # Apply solver before creating closed thin shells. Long/short tops have
    # a front and back panel; trouser pattern already wraps over the bar.
    faces=[]
    if typ!='trousers':
        # Sew front and back to curved side returns; keep neckline, hems and
        # cuffs open. One Solidify pass closes the thickness around those
        # openings, rather than depicting two unrelated flat ribbons.
        def bulk(p):
            fraction=max(0,min(1,(top-p[2])/top))
            torso=max(0,1-(abs(p[1])/.26)**2)
            return .002+.006*math.sin(math.pi*fraction)**.65*torso
        vv=[[p[0]+side*bulk(p),p[1],p[2]] for side in (1,-1) for p in skin_vertices]
        count=len(skin_vertices)
        pp=[list(f.vertices) for f in skin.polygons]
        pp += [[i+count for i in reversed(f.vertices)] for f in skin.polygons]
        oriented=[]
        for f in skin.polygons:
            ids=list(f.vertices)
            oriented += [(a,b) for a,b in zip(ids,ids[1:]+ids[:1]) if counts[tuple(sorted((a,b)))]==1]
        sleeve_drop=.52 if typ in ('dress','abaya') else .39 if typ=='jacket' else .31
        for a,b in oriented:
            middle=[(skin_vertices[a][k]+skin_vertices[b][k])/2 for k in range(3)]
            hem=middle[2]<.035
            neck=middle[2]>top-.095 and abs(middle[1])<.12
            cuff=abs(middle[1])>.18 and middle[2]<top-sleeve_drop+.045
            if not (hem or neck or cuff):pp.append([b,a,a+count,b+count])
    else:
        vv=skin_vertices;pp=[list(f.vertices) for f in skin.polygons]
    temp=bpy.data.meshes.new('relaxed sewn garment')
    temp.from_pydata(vv,[],pp);temp.update()
    shell=bpy.data.objects.new('closed fabric shell',temp);bpy.context.collection.objects.link(shell)
    solid=shell.modifiers.new('0.8 mm fabric shell','SOLIDIFY');solid.thickness=rule['thickness_m'];solid.offset=0
    out=shell.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    faces.extend([[list(out.vertices[i].co) for i in f.vertices] for f in out.polygons])
    evaluated.to_mesh_clear()
    if typ in ('shirt','jacket'):
        # Two turned collar/lapel skins. They share the shoulder datum,
        # remain inside the measured garment envelope, and have fabric edges.
        for side in (-1,1):
            points=[[.006,side*.044,top-.032],[.007,side*.079,top-.002],
                    [.014,side*.118,top-.092],[.009,side*.056,top-.125]]
            for i,q in enumerate(points):
                near=min(skin_vertices,key=lambda p:(p[1]-q[1])**2+(p[2]-q[2])**2)
                q[0]=near[0]+bulk(near)+(.004 if i in (1,2) else .001)
            collar=bpy.data.meshes.new('ASSUMED turned collar')
            collar.from_pydata(points,[],[[0,1,2,3]]);collar.update()
            item=bpy.data.objects.new('turned collar',collar);bpy.context.collection.objects.link(item)
            thick=item.modifiers.new('closed collar fabric','SOLIDIFY')
            thick.thickness=rule['thickness_m'];thick.offset=0
            out=item.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
            faces.extend([[list(out.vertices[i].co) for i in f.vertices] for f in out.polygons])
    return dict(faces=[[[round(v,rule['cache_precision_decimal_places']) for v in p] for p in f] for f in faces],
                skin_vertices=[[round(v,7) for v in p] for p in skin_vertices],boundary_indices=boundary,
                simulation=dict(method='Blender CLOTH, shoulder pinned, gravity only',blender=bpy.app.version_string,
                    seed=rule['seed'],frames=rule['frames'],threads=1,gravity=rule['gravity_m_s2'],pins=pins,
                    thickness_m=rule['thickness_m'],initial_vertices_sha256=digest(verts)))


def main():
    argv=sys.argv[sys.argv.index('--')+1:]
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from archpipe.imported_appearance import digest
    data=json.loads(args.input.read_text())
    if data['generator_sha256']!=digest(Path(__file__).read_text()):
        raise ValueError('generator changed after cloth input was hashed')
    out=bake(data)
    out['input_sha256']=digest(data);out['mesh_sha256']=digest(out['faces'])
    args.output.write_text(json.dumps(out,separators=(',',':')))

if __name__=='__main__':main()
