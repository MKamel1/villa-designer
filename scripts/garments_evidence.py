"""Fresh dressing receipts and neutral-preview inputs; never presentation images.

Run with the project Python and PYTHONPATH=src. Blender diagnostics use the
existing garden_g6_preview.py reader, its graphics lock and neutral lighting.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.concept import garments as G


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first-fix',action='store_true')
    parser.add_argument('--scene-path',type=Path,default=ROOT/'out/garments/final-scene.json')
    parser.add_argument('--candidate',action='store_true',help='Checkpoint current contents in the unchanged saved architectural context')
    parser.add_argument('--context',action='store_true',help='Derive neutral lighting input, preserving every source mesh and camera')
    args=parser.parse_args()
    output=ROOT/'out/garments';output.mkdir(exist_ok=True)
    if args.first_fix:
        before=json.loads(gzip.decompress((ROOT/'tests/fixtures/l0923-dressing-before.json.gz').read_bytes()))
        wardrobe_meshes=[]
        for row in before['meshes']:
            if not row['id'].startswith('furn-pd-hang'):continue
            faces=[]
            for i,kind in enumerate(row['physical_components']):
                if kind in ('plinth','divider','back'):faces+=row['faces'][i*6:i*6+6]
            wardrobe_meshes.append(dict(row,faces=faces,physical_components=[n for n in row['physical_components'] if n in ('plinth','divider','back')]))
        meshes,modules=G.build(before['wardrobes'],.002)
        scene=dict(meshes=wardrobe_meshes+meshes,garment_modules=modules,dressing_wardrobes=before['wardrobes'],
                   materials=json.loads((output/'before.json').read_text())['materials'])
    else:
        scene=json.loads(args.scene_path.read_text())
    if args.candidate:
        if args.first_fix:raise ValueError('Candidate requires saved live joinery')
        scene['meshes']=[m for m in scene['meshes'] if not m.get('wardrobe_id')]
        G.integrate(scene)
        scene['garment_preview_status']='CANDIDATE: new contents in unchanged saved architectural context; final fresh build still required'
    if args.context:
        if args.first_fix:raise ValueError('Context requires a fresh complete scene')
        source=args.scene_path
        scene['neutral_preview_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        scene['neutral_preview_fill']=[dict(position_m=[20.4,-27.60,2.65],target_m=[20.4,-27.0,1.2],size_m=1.,watts=350.),
                                       dict(position_m=[20.4,-27.60,2.65],target_m=[20.4,-28.5,1.2],size_m=1.,watts=350.)]
        (output/'neutral-scene.json').write_text(json.dumps(scene,separators=(',',':')))
    by_id={m['id']:m for m in scene['meshes']}
    assemblies=[]
    for typ in G.DROP:
        m=next(m for m in scene['meshes'] if m.get('garment_type')==typ and
               (typ in ('dress','abaya') or 'dress-his-' in m['id']))
        assemblies.append(dict(id=typ,meshes=[m,by_id[m['contents_support']]],camera_direction=[3,-1,1]))
    for role in ('folded sportswear','folded knit hat','lingerie','headscarves','shoe','lidded top box'):
        m=next(m for m in scene['meshes'] if m.get('contents_role')==role)
        samples=[m]
        if role=='lidded top box':samples+=[by_id[m['id']+'-lid']]
        if role in ('lingerie','headscarves'):
            module=m['contents_module'];front=by_id[m['drawer_front_id']]
            index=front['id'].rsplit('-',1)[1]
            # Diagnostic only: omit named opaque front so contents can be inspected.
            samples=[r for r in scene['meshes'] if r.get('contents_module')==module and
                     (r.get('drawer_front_id')==front['id'] or r['id'].startswith(module+'-tray-'+index) or r['id']==module+'-insert-'+index)]
        assemblies.append(dict(id=role.replace(' ','-'),meshes=samples))
    for wardrobe in scene['dressing_wardrobes']:
        package=[m for m in scene['meshes'] if m.get('wardrobe_id')==wardrobe['id'] or m['id']=='furn-'+wardrobe['id']+'-0']
        direction=[1.3,3,1.5] if wardrobe['rot']==0 else [-1.3,-3,1.5]
        assemblies.append(dict(id=wardrobe['partner']+'-wardrobe',meshes=package,camera_direction=direction))
    specimen_file=output/('first-fix-specimens.json' if args.first_fix else 'specimens.json')
    specimen_file.write_text(json.dumps(dict(materials=scene['materials'],assemblies=assemblies),separators=(',',':')))
    findings=G.contents_findings(scene['dressing_wardrobes'],scene['meshes'])
    receipt=dict(findings=findings,contents=len([m for m in scene['meshes'] if m.get('wardrobe_id')]),
                 counts={t:sum(m.get('garment_type')==t for m in scene['meshes']) for t in G.DROP},
                 modules=scene['garment_modules'],geometry_sha256=hashlib.sha256(json.dumps(scene['meshes'],sort_keys=True).encode()).hexdigest())
    (output/('first-fix-measurements.json' if args.first_fix else 'measurements.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(specimens=str(specimen_file),findings=findings,counts=receipt['counts'])))
    if findings:return 1
    return 0


if __name__=='__main__':sys.exit(main())
