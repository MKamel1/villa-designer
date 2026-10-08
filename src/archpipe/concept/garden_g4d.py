"""Client 2026-10-07 north-court finishes and shielded evening uplights.

Lengths are metres, luminous flux is lumens, beam is full width at half
maximum in degrees, and diffuse reflectance is a linear fraction.
All new appearances and photometry are assumptions, not buyable products.
"""
from copy import deepcopy
import math
import numpy as np

LAYER = 'evening-garden'
GRAVEL = 'north-pale-gravel'
STONE = 'north-light-stone'
FLUX_LM = 120.
BEAM_DEG = 30.
KELVIN = 2700
SNOOT_M = .12
APERTURE_M = .048
LENS_M = .012


def shield_output(ies_text, source_flux_lm, shield):
    """Integrate source IES inside bounds of the physical polygon opening.

    The inner cone touches the aperture edge midpoints; the outer cone its
    vertices. Their solid-angle integrals bound free fitting output before
    external foliage/ground obstruction. This is assumed point-source optics,
    not measured manufacturer output. All angles are degrees and flux lumens.
    """
    from ..photometry import parse
    distribution=parse(ies_text)
    radius=shield['aperture_radius_m'];depth=shield['snoot_depth_m']
    sides=shield['facet_count']
    cutoff=[math.degrees(math.atan(radius*math.cos(math.pi/sides)/depth)),
            math.degrees(math.atan(radius/depth))]
    def integral(limit):
        steps=1800;step=math.radians(limit)/steps
        return sum(distribution.intensity(math.degrees((i+.5)*step),0)*
                   math.sin((i+.5)*step)*step*math.tau for i in range(steps))
    total=integral(180.)
    return dict(status='ASSUMED',source_flux_lm=source_flux_lm,cutoff_deg=cutoff,
                emitted_flux_lm_bounds=[source_flux_lm*integral(angle)/total for angle in cutoff],
                basis=f'Independent source IES solid-angle integral inside inner/outer cones of the actual {sides}-sided snoot; before external plant/ground obstruction')


def materials():
    reason = ('ASSUMED dry pale mineral target selected for client brightening; '
              'no measured product or accessible held passage establishes this value. '
              'Wetness, dirt and ageing may reduce reflectance; supplier sample pending.')
    rows = {
        GRAVEL: dict(kind='principled', base_rgb=[.74,.71,.65], reflectance=.70,
                     roughness=1., surface_use='ground-only', chip_size_m=[.010,.020],
                     procedural_gravel_m=.015, basis_status='ASSUMED',
                     reflectance_basis=reason, appearance_status='ASSUMED',
                     note='ASSUMED warm-white limestone-like gravel; no product. '
                          'Metre-native procedural cells at nominal 15 mm, assumed 10–20 mm chips; pattern proxy.'),
        STONE: dict(kind='principled', base_rgb=[.70,.67,.60], reflectance=.65,
                    roughness=.85, surface_use='ground-only', basis_status='ASSUMED',
                    reflectance_basis=reason, appearance_status='ASSUMED',
                    procedural_stone_m=.04,
                    note='ASSUMED pale honed limestone/travertine-like stepping surface; no product; underside retains stone-substrate.')}
    # Linear RGB luminance weights (red, green, blue): make the untextured
    # diffuse colour actually carry the stated target, rather than two
    # independently typed optical values. Bump changes normals only.
    for row in rows.values():
        mean=sum(c*w for c,w in zip(row['base_rgb'],(.2126,.7152,.0722)))
        row['base_rgb']=[c*row['reflectance']/mean for c in row['base_rgb']]
    return rows


def apply_finishes(meshes):
    """Change only northern existing finishes; preserve every face and underside."""
    from .villa_landscape import NORTH_COURT, _mesh_rect
    from .garden_render_review import normal
    from shapely.geometry import box
    court=box(*NORTH_COURT)
    changed=[]
    for mesh in meshes:
        if mesh['material'] not in ('garden-gravel','stepping-stone'):
            continue
        footprint=box(*_mesh_rect(mesh))
        if not court.covers(footprint):
            continue
        mesh['material']=GRAVEL if mesh['material']=='garden-gravel' else STONE
        if mesh['material']==STONE:
            mesh['face_materials']=['stone-substrate' if normal(face)[2]<-.7 else STONE for face in mesh['faces']]
        mesh['label']+='; client 2026-10-07 G4d pale finish ASSUMED'
        changed.append(mesh['id'])
    return changed


def _tube(start, end, radius, inner=None):
    """Closed solid cylinder or closed hollow snoot; triangulated curved surfaces."""
    start,end=np.asarray(start,float),np.asarray(end,float)
    axis=end-start;axis/=np.linalg.norm(axis)
    helper=np.array([1.,0.,0.]) if abs(axis[0])<.9 else np.array([0.,1.,0.])
    u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
    def ring(point,r):
        return [(point+r*(u*math.cos(k*math.tau/24)+v*math.sin(k*math.tau/24))).tolist() for k in range(24)]
    a,b=ring(start,radius),ring(end,radius)
    faces=[[a[k],a[(k+1)%24],b[(k+1)%24],b[k]] for k in range(24)]
    if inner:
        c,d=ring(start,inner),ring(end,inner)
        faces += [[c[k],d[k],d[(k+1)%24],c[(k+1)%24]] for k in range(24)]
        faces += [[a[k],c[k],c[(k+1)%24],a[(k+1)%24]] for k in range(24)]
        faces += [[b[k],b[(k+1)%24],d[(k+1)%24],d[k]] for k in range(24)]
    else:faces += [a[::-1],b]
    return [[face[0],face[k],face[k+1]] for face in faces for k in range(1,len(face)-1)]


def fixtures(plants):
    """Derive rooted mounts and inward foliage aim from retained plant geometry."""
    meshes,lights,records=[],[],[]
    for plant in plants:
        if plant.get('species') not in ('Rhapis excelsa','Fatsia japonica') or not plant.get('bed','').startswith('north'):
            continue
        x,y=plant['center'];ground=plant['root_z_m']
        # Street side of each root, within its existing soil bed; away from
        # the lounge and swing sightlines. No root, foliage or path moves.
        position=np.array([x-.22,y,ground+.065])
        target=np.array([x,y,ground+.80])
        aim=target-position;aim/=np.linalg.norm(aim)
        ident='garden-uplight-'+plant['id'].removeprefix('landscape-')
        body=ident+'-body';lens=ident+'-lens';snoot=ident+'-snoot'
        base=[position[0],position[1],ground]
        # Ground disc and tilted solid head overlap by construction.
        head_start=position-aim*.025
        body_faces=_tube(base,[*base[:2],ground+.025],.055)+_tube([*base[:2],ground+.012],head_start,.021)+_tube(head_start,position,.055)
        common=dict(group='fixture',room='north-garden',garden_g4d=True,
                    fixture_id=ident,label='ASSUMED shielded outdoor uplight; client 2026-10-07; product/IP rating pending')
        meshes += [dict(common,id=body,material='black-metal',faces=body_faces,part_kind='lamp-housing'),
                   dict(common,id=snoot,material='black-metal',faces=_tube(position,position+aim*SNOOT_M,.055,APERTURE_M),part_kind='lamp-housing'),
                   dict(common,id=lens,material='glass-clear',faces=_tube(position-aim*.002,position,LENS_M),part_kind='light-lens',layer=LAYER)]
        record=dict(id=ident,status='ASSUMED',product=None,plant_id=plant['id'],
                    body_ids=[body,snoot],lens_id=lens,mount_point_m=base,
                    emitter_m=position.tolist(),aim=aim.tolist(),target_m=target.tolist(),
                    flux_lm=FLUX_LM,beam_deg=BEAM_DEG,cct_k=KELVIN,layer=LAYER,
                    cri=90,cri_status='ASSUMED',
                    photometry=dict(status='ASSUMED',ies='generic/GARDEN-UP.ies',
                                    basis='Rotational cosine-power LM-63 distribution, 120 lm, 30 degree full half-maximum beam; not manufacturer photometry'),
                    shielding=dict(snoot_depth_m=SNOOT_M,aperture_radius_m=APERTURE_M,lens_radius_m=LENS_M,facet_count=24),
                    mounting_status='modeled ground bearing; electrical/drainage/IP specification pending')
        from .villa_lighting import generic_ies
        record['flux_basis']='source-before-physical-snoot'
        record['photometry']['basis'] += '; source distribution BEFORE physical snoot, not final luminaire output'
        record['shield_output']=shield_output(generic_ies(FLUX_LM,BEAM_DEG,'GARDEN-UP'),FLUX_LM,record['shielding'])
        records.append(record)
        lights.append(dict(id=ident,room='north-garden',layer=LAYER,type='ies',
                           position=record['emitter_m'],aim=record['aim'],spin_deg=0.,
                           lumens=FLUX_LM,cct_k=KELVIN,ies=record['photometry']['ies'],
                           cri=90,product=dict(manufacturer='GENERIC',code='ASSUMED GARDEN-UP',generic=True),
                           generic=True,garden_g4d=True,fixture_record=deepcopy(record),
                           label=record['photometry']['basis']))
    metadata=fixture_metadata_findings(lights)
    if metadata:raise ValueError('; '.join(metadata))
    return meshes,lights,records


def fixture_metadata_findings(lights):
    """Early C5 boundary: the generic renderer also requires CRI and identity.

    CRI means colour rendering index on a zero-to-one-hundred scale. The
    assumed value is metadata only; no spectral performance is verified.
    """
    out=[]
    for light in lights:
        cri=light.get('cri');product=light.get('product',{})
        if not isinstance(cri,(int,float)) or not 0<=cri<=100:
            out.append(light['id']+': missing colour rendering index metadata')
        if not isinstance(product,dict) or not isinstance(product.get('manufacturer'),str) or not isinstance(product.get('code'),str) or product.get('generic') is not True:
            out.append(light['id']+': missing assumed generic fixture identity')
    return out


def glare_evidence(records, observers):
    """Trace 17 lens samples to each eye through the actual circular snoot.

    An eye behind the opaque head cannot see the lens. For an eye in front,
    each lens-to-eye ray crosses the aperture plane; its radial distance must
    exceed the opening radius to be blocked. This is a geometric direct-lamp
    screen, not a quantified human glare assessment.
    """
    rows=[]
    for record in records:
        origin=np.array(record['emitter_m']);axis=np.array(record['aim'])
        helper=np.array([0.,1.,0.]);u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
        shield=record['shielding']
        samples=[origin]+[origin+shield['lens_radius_m']*(u*math.cos(k*math.tau/16)+v*math.sin(k*math.tau/16)) for k in range(16)]
        for name,eye in observers.items():
            eye=np.array(eye);depth=float(np.dot(eye-origin,axis));visible=0;radials=[]
            for sample in samples:
                if depth<=shield['snoot_depth_m']:continue
                hit=sample+(eye-sample)*shield['snoot_depth_m']/depth
                delta=hit-origin-axis*shield['snoot_depth_m'];radial=float(np.linalg.norm(delta))
                radials.append(radial)
                visible+=radial<=shield['aperture_radius_m']
            rows.append(dict(fixture=record['id'],observer=name,eye_m=eye.tolist(),visible_lens_samples=visible,
                             samples=len(samples),minimum_aperture_radius_m=min(radials) if radials else None))
    return rows


def material_basis(scene):
    """C7: new mineral finishes need explicit optical assumption and real scale."""
    out=[]
    for name in (GRAVEL,STONE):
        material=scene.get('materials',{}).get(name,{})
        if material.get('basis_status') not in ('ASSUMED','VERIFIED') or not material.get('reflectance_basis'):
            out.append(name+': missing reflectance basis/status')
        value=material.get('reflectance')
        if not isinstance(value,(int,float)) or not 0<value<=1:
            out.append(name+': missing physical diffuse reflectance')
        elif abs(sum(c*w for c,w in zip(material.get('base_rgb',[]),(.2126,.7152,.0722)))-value)>.001:
            out.append(name+': diffuse colour diverges from optical target')
    gravel=scene.get('materials',{}).get(GRAVEL,{})
    if gravel.get('chip_size_m')!=[.010,.020] or gravel.get('procedural_gravel_m')!=.015:
        out.append(GRAVEL+': missing 10–20 mm chip scale')
    return out


def fixture_record(scene):
    """C5: join photometry, actual lens, foliage aim and finite C4 mount."""
    from .fitting_mounting import bounds
    by={m['id']:m for m in scene.get('meshes',[])}
    out=[]
    records=scene.get('garden_g4d',{}).get('fixtures',[])
    lights={light['id']:light for light in scene.get('lights',[]) if light.get('garden_g4d')}
    out.extend(fixture_metadata_findings(list(lights.values())))
    if set(lights)!={r['id'] for r in records}:out.append('garden C5: fixture/light identity mismatch')
    expected_parts={mid for r in records for mid in r['body_ids']+[r['lens_id']]}
    actual_parts={m['id'] for m in by.values() if m.get('garden_g4d')}
    if expected_parts!=actual_parts:out.append('garden C5: unregistered or missing physical fitting part')
    targets={m['id'] for m in by.values() if m.get('species') in ('Rhapis excelsa','Fatsia japonica') and m.get('bed','').startswith('north')}
    if targets!={r['plant_id'] for r in records}:out.append('garden C5: every north Rhapis/Fatsia needs one uplight')
    if len(records)!=len(targets):out.append('garden C5: each plant needs exactly one fixture record')
    for record in records:
        ident=record['id'];light=lights.get(ident,{})
        if light.get('fixture_record')!=record:out.append(ident+': divergent fixture record')
        for field,source in (('position','emitter_m'),('aim','aim'),('lumens','flux_lm'),('cct_k','cct_k'),('layer','layer'),('cri','cri')):
            if light.get(field)!=record[source]:out.append(ident+': inconsistent '+field)
        if light.get('ies')!=record['photometry']['ies'] or record['photometry']['status']!='ASSUMED':out.append(ident+': missing assumed photometry')
        lens=by.get(record['lens_id'])
        if lens is None:out.append(ident+': missing physical lens');continue
        # The source is the centre of the actual outward lens face, not an
        # independently guessed housing centre.
        face_points=np.asarray([p for face in lens['faces'] for p in face])
        origin=np.asarray(record['emitter_m']);axis=np.asarray(record['aim'])
        axial=(face_points-origin)@axis
        centroid=(face_points.min(axis=0)+face_points.max(axis=0))/2
        if abs(float(axial.max()))>.001 or float(axial.min())<-.003 or np.linalg.norm(centroid+axis*.001-origin)>.001:
            out.append(ident+': emitter outside actual lens')
        members=[by.get(mid) for mid in record['body_ids']+[record['lens_id']]]
        if any(m is None for m in members):out.append(ident+': missing fitting part');continue
        if any(m.get('fixture_id')!=ident for m in members):out.append(ident+': inconsistent physical fitting identity')
        body=members[0];mount=body.get('mounting',{});host=scene.get('mounting_hosts',{}).get(mount.get('host_id'),{})
        shroud=members[1];vertices=np.asarray([p for f in shroud['faces'] for p in f])-origin
        distances=vertices@axis;radial=np.linalg.norm(vertices-distances[:,None]*axis,axis=1)
        shield=record['shielding']
        if abs(float(distances.min()))>1e-6 or abs(float(distances.max())-shield['snoot_depth_m'])>1e-6 or abs(float(radial.min())-shield['aperture_radius_m'])>1e-6:
            out.append(ident+': shielding record diverges from physical snoot')
        rim={tuple(round(float(c),7) for c in p) for p,d,r in zip(vertices,distances,radial)
             if abs(d-shield['snoot_depth_m'])<1e-6 and abs(r-shield['aperture_radius_m'])<1e-6}
        if shield.get('facet_count')!=len(rim):
            out.append(ident+': shielding facet count diverges from physical aperture')
        from .villa_lighting import generic_ies
        expected_output=shield_output(generic_ies(record['flux_lm'],record['beam_deg'],'GARDEN-UP'),record['flux_lm'],dict(shield,facet_count=len(rim))) if len(rim)>=3 else None
        if record.get('flux_basis')!='source-before-physical-snoot' or record.get('shield_output')!=expected_output:
            out.append(ident+': source lumens confused with emitted fitting lumens')
        if record['cct_k']!=KELVIN or record['flux_lm']!=FLUX_LM or record['beam_deg']!=BEAM_DEG or not math.isclose(float(np.linalg.norm(axis)),1.):
            out.append(ident+': wrong assumed uplight specification')
        plant=by.get(record['plant_id'])
        target=np.asarray(record['target_m'])
        if plant is None or np.linalg.norm(target[:2]-np.asarray(plant['center']))>1e-6 or not np.allclose((target-origin)/np.linalg.norm(target-origin),axis):
            out.append(ident+': beam misses retained foliage target')
        source=by.get(host.get('source_mesh'))
        point=record['mount_point_m']
        from .garden_render_review import normal
        from .mounting import _on_polygon
        if (source is None or abs(bounds(body)[2]-point[2])>.001 or not any(normal(f)[2]>.999 and abs(f[0][2]-point[2])<.001 and _on_polygon(point,f,(0,0,1)) for f in source['faces'])):
            out.append(ident+': absent live ground contact')
        if light.get('layer')!=LAYER:out.append(ident+': evening layer missing')
    return out


def integrate(scene):
    from .support_mounting import nearest,floor_assembly
    changed=apply_finishes(scene['meshes'])
    scene['materials'].update(materials())
    meshes,lights,records=fixtures(scene['meshes'])
    sources=[m for m in scene['meshes'] if m.get('part_kind')=='soil-bed']
    scene['meshes'].extend(meshes);scene['lights'].extend(lights)
    for record in records:
        host=nearest(scene,record['mount_point_m'],(0,0,1),sources,'support-'+record['id'],'floor',maximum=.001)
        members=[m for m in scene['meshes'] if m.get('fixture_id')==record['id']]
        floor_assembly(scene,members,host,record['id'])
    scene['garden_g4d']=dict(decision='client 2026-10-07',changed_finishes=changed,fixtures=records)


def observers(scene):
    """Lounge window width and standing/seated heights, plus swing eye envelope."""
    from .garden_swing import design
    # Use the real retained lounge camera positions, and the entire lounge
    # west window at its actual authored plane, sampled at both adult eyes.
    points={v['id']:v['camera']['position'] for v in scene.get('views',[]) if v['id'].startswith(('v37-','v38-'))}
    from . import villa_r11 as R, revit_spec as RS
    spec=RS.build(R.design('D1'))
    for opening in spec['windows']+spec['doors']:
        if 'lounge' not in opening.get('rooms',[]) and opening.get('room')!='lounge':continue
        span=opening.get('span')
        if span:
            for index,t in enumerate(np.linspace(0,1,9)):
                for height in (1.20,1.35):
                    along=span[2]+(span[3]-span[2])*float(t)
                    points['lounge-opening-%d-%s'%(index,height)]=[span[1],along,-3.+height] if span[0]=='v' else [along,span[1],-3.+height]
    swing=design();x,y=swing['center'];z=swing['ground_m']+swing['eye_height_m']
    for i,dx in enumerate((-.20,0,.20)):
        for j,dy in enumerate((-.20,0,.20)):
            points['swing-seat-%d-%d'%(i,j)]=[x+dx,y+dy,z]
    return points


def scene_findings(scene):
    active=any(m.get('garden_g4d') or m.get('material') in (GRAVEL,STONE) for m in scene.get('meshes',[])) or any(l.get('garden_g4d') for l in scene.get('lights',[]))
    if not scene.get('garden_g4d'):
        return ['garden G4d: missing fixture/material registry'] if active else []
    out=material_basis(scene)+fixture_record(scene)
    rows=glare_evidence(scene['garden_g4d']['fixtures'],observers(scene))
    out += [r['fixture']+': direct lens visible from '+r['observer'] for r in rows if r['visible_lens_samples']]
    for view in scene.get('views',[]):
        if view.get('state')=='day' and LAYER in view.get('layers_on',[]):out.append(view['id']+': evening garden lights on by day')
    return out


def evening_view():
    """Reviewed lounge-window camera; fixed 24 mm level eye, no design moves."""
    subjects=['landscape-north-rhapis-accent','landscape-north-back-02',
              'landscape-north-swing-basket','landscape-north-swing-cushions']
    return dict(id='v42-north-garden-evening',aliases=['v41-north-garden-evening'],title='North garden — soft evening uplights and hanging retreat',
                state='exterior-dusk',when='2026-10-15T18:35:00+03:00',
                camera=dict(position=[3.9,-26.55,-1.65],target=[1.739460010201047,-24.468638197602477,-1.65],
                            lens_mm=24,sensor_mm=36,shift_x=0.,shift_y=-.15420195429557562),
                resolution=[1920,1280],subjects=subjects,require_full_subject_frame=True,
                visibility_targets=subjects[:3],visibility_basis='ASSUMED majority of 13 actual first-hit rays, plus independent neutral review',
                layers_on=[LAYER],dimmers={LAYER:1.},exposure='exterior-dusk',samples=1024,
                room=None,final_only=True,seated=False,standing_room='lounge',
                presentation_retired=True,
                presentation_decision=('Lead decision 2026-10-08: retire from review/final presentation; keep for diagnostics. '
                    'The view exists to show the approved palm uplighting. The in-lounge camera above was rejected (looks through glazing at the back of the swing; '
                    'uplights-only foliage 99.5th-percentile linear luminance 0.437 against 14.30 from the original camera). '
                    'Bounded camera-only searches (320 western, 96 transition poses; out/garden-g4f/resume-*-search-evidence.json) found no pose passing every unchanged '
                    'standing, lens-clearance, opening-frame, foreground-fitting and subject-visibility check; the best open-court candidate kept 3.6% of the original '
                    'uplit peak and 22.8% of the uplit screen population (out/garden-g4f/resume-preview-review.md). Lights, aim, flux, sky, exposure and QA limits unchanged. '
                    'The original camera shows the uplighting but frames a spike housing in the foreground: client choice pending.'),
                faithful_colour_cast=dict(source='specified dusk sky amplified by pale gravel',sky_blue_red_ratio=1.379,
                    lamp_blue_red_ratio=.0996,retained_colour_cast=.105,colour_cast_limit=.02,
                    colour_cast_status='FAIL',highlights_status='WARN',
                    diagnosis='docs/garden-g4e-report.md#evening-diagnosis',decision='lead 2026-10-08; v07 precedent'),
                caption_notes=['North garden from inside the lounge through its existing window, 1.35 m eye above the court; level 24 mm lens and downward shift. G4e camera-only relocation keeps uplight housings incidental; v41-north-garden-evening is the recorded historical alias. '
                               'Rhapis, Fatsia and rear of the swing basket/cushions are wholly framed through glazing; the basket partly screens the planting. The seating face is shown separately in v39. Upper rope and fixing plate lie outside this view. '
                               'Foreground pale gravel is a visible portion of the retained path/mulch, not the complete court. '
                               'Four ground-bearing shielded uplights: each ASSUMED 120 source lumens BEFORE the snoot, approximately 93 emitted fitting lumens, 30 degree beam and 2700 K; source cosine-power photometry plus physical shield. Only the evening garden layer is on. '
                               'Pale gravel diffuse reflectance 0.70 and light stone 0.65 ASSUMED, no product; 10–20 mm gravel with nominal 15 mm metre-native pattern proxy. '
                               'Authored botanical/furniture appearances ASSUMED; photographic likeness, procurement and nursery performance UNVERIFIED. '
                               'Swing dynamic load and anchorage remain UNVERIFIED; outdoor fixture/IP/drainage/electrical product specification pending. '
                               'Faithful cool cast from the specified dusk sky: horizontal-weighted linear blue/red 1.379; warm uplight source blue/red 0.0996. Pale gravel amplifies the sky. Retained colour_cast FAIL (0.105 against 0.02) is disclosed, with highlights WARN (0.76 against 0.9); exposure and white balance were not compensated. Diagnosis: docs/garden-g4e-report.md, Evening diagnosis; lead decision 2026-10-08 following v07. Linear probes and neutral previews do not constitute new presentation QA.'])
