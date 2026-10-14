"""Neutral-only cloth evidence from physical scene plus bound appearances."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe import drape_appearance as D
from archpipe.imported_appearance import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=ROOT/'out/garments/final-scene.json')
    parser.add_argument('--fresh',action='store_true',help='Build and save fresh authoritative scene before evidence')
    args=parser.parse_args();args.scene=args.scene.resolve();out=ROOT/'out/drape';out.mkdir(exist_ok=True)
    build_seconds=None
    if args.fresh:
        from archpipe.concept import villa_render
        started=time.perf_counter()
        scene=villa_render.build()
        build_seconds=time.perf_counter()-started
        print('full build seconds:',build_seconds,flush=True)
        args.scene=out/'final-scene.json';args.scene.write_text(json.dumps(scene,separators=(',',':')))
    else:scene=json.loads(args.scene.read_text());D.bind_scene(scene)
    D.require_scene(scene)
    rendered=D.rendered_meshes(scene);by={r['id']:r for r in rendered}
    samples=[]
    for typ in ('dress','abaya','shirt','jacket','trousers'):
        part=next(p for p in scene['meshes'] if p.get('garment_type')==typ)
        samples.append(dict(id=typ,meshes=[by[part['id']],by[part['contents_support']]],
                            camera_direction=[3,-1,1],detail_swatch=True,detail_full_specimen=True,
                            detail_target_m=[0,0,.75 if typ in ('dress','abaya') else .4],
                            detail_ortho_scale_m=2.5 if typ in ('dress','abaya') else 1.5))
    part=next(p for p in scene['meshes'] if p.get('contents_role')=='folded sportswear')
    module=part['contents_module'];support=part['contents_support']
    package=[p for p in scene['meshes'] if p.get('contents_module')==module and p.get('part_kind')=='folded-fabric']
    # Exactly one authored stack, joined through its physical support chain.
    chain={part['id']}
    changed=True
    while changed:
        changed=False
        for p in package:
            if p.get('contents_support') in chain and p['id'] not in chain:chain.add(p['id']);changed=True
    samples.append(dict(id='folded-stack',meshes=[by[p['id']] for p in package if p['id'] in chain],detail_swatch=True,
                        detail_target_m=[0,0,.07],detail_ortho_scale_m=.55))
    scene['appearance_basis']='ASSUMED garment cuts, textile parameters, weave, sheen and restrained colours; owned procedural appearances, no product claim'
    (out/'specimens.json').write_text(json.dumps(dict(materials=D.render_materials(scene),assemblies=samples,
        appearance_basis=scene['appearance_basis']),separators=(',',':')))
    # Keep the actual scene's physical parts; the reader resolves appearances
    # only after admission. Context light records come from the old receipt.
    old=json.loads((ROOT/'out/garments/context/context-preview-evidence.json').read_text())
    fill=next(r for r in old if r['id']=='v31-dressing-hers')['neutral_preview_fill']
    scene['neutral_preview_fill']=fill
    scene['neutral_preview_source_sha256']=hashlib.sha256(args.scene.read_bytes()).hexdigest()
    scene['views']=[v for v in scene['views'] if v['id'] in ('v31-dressing-hers','v32-dressing-his')]
    (out/'neutral-scene.json').write_text(json.dumps(scene,separators=(',',':')))
    physical=[p for p in scene['meshes'] if D.eligible(p)]
    receipt=dict(physical_geometry_sha256=digest(physical),appearance_sha256=digest(scene['draped_appearances']),
                 full_build_seconds=build_seconds,full_build_budget_seconds=120,
                 full_build_budget_pass=build_seconds is not None and build_seconds<120,
                 physical_count=len(physical),appearance_count=len(scene['draped_appearances']),
                 physical_source=str(args.scene.relative_to(ROOT)) if args.scene.is_relative_to(ROOT) else str(args.scene),policy=D.policy(),
                 camera_sha256=digest(scene['views']),neutral_preview_fill=fill,
                 camera_comparison_unchanged=all(v['camera']==next(r for r in old if r['id']==v['id'])['camera'] for v in scene['views']),
                 collisions=D.collision_findings(scene),
                 measurements=[dict(id=p['id'],metrics=D.measure(by[p['id']]['skin_vertices'],by[p['id']]['boundary_indices']) if p.get('garment_type') else None,
                                    enclosure=p['enclosure']) for p in scene['draped_appearances']])
    (out/'measurements.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(physical_count=len(physical),collisions=receipt['collisions'])))
    if build_seconds is not None and build_seconds>=120:
        raise ValueError('unchanged 120 second full-build budget exceeded; diagnostic evidence retained')

if __name__=='__main__':main()
