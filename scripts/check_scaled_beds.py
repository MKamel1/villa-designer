"""Actual scaled importer/cloth read-back, never replacement approval.

Writes failures before exiting nonzero. Source faces and physics stay intact.
Neutral diagnostics admit pending reviews; presentation imports do not.
"""
from pathlib import Path
import argparse
import fcntl
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def run(args):
    import bpy
    import numpy as np
    from archpipe.blender import villa_scene as builder
    from archpipe.beds import model_review_meshes,bind_model_cloth,mattress_cloth
    models=json.loads(args.models.read_text());scene=json.loads(args.scene.read_text())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result=[]
    for model in models:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        # Keep a physical fallback in the import proof, just as in the room.
        bpy.ops.mesh.primitive_cube_add(size=1)
        fallback=bpy.context.object;fallback.name=model['replaces']+'mechanical-fallback'
        imported=builder.import_models([model],str(args.library),neutral_diagnostic=True)
        actual=np.asarray([list(o.matrix_world@v.co) for o in imported[0]['objects'] for v in o.data.vertices])
        portable=np.asarray([p for r in model_review_meshes([model]) for f in r['faces'] for p in f])
        error=float(np.abs(np.concatenate((actual.min(0)-portable.min(0),actual.max(0)-portable.max(0)))).max())
        proof=dict(asset=model['asset'],bed=model['label'],import_bounds_max_error_m=error,
            fallback_hidden=bool(fallback.hide_render and fallback.get('replaced_by_model')==model['id']),
            retained_source_triangles=sum(len(o.data.polygons) for o in imported[0]['objects']),
            source_triangles=sum(len(r['faces']) for r in model['review_geometry']['meshes']),cloth=[])
        specs=[c for c in scene['cloth'] if c['id'].startswith(('duvet-'+model['label'],'throw-'+model['label']))]
        mat=bpy.data.materials.new('neutral diagnostic cloth');mat.diffuse_color=(.8,.8,.8,1)
        for spec in specs:
            bound=bind_model_cloth([spec],imported)[0]
            objs=[o for o in imported[0]['objects'] if o.get('source_part') in bound['mattress_parts']]
            faces=[[list(o.matrix_world@o.data.vertices[i].co) for i in p.vertices] for o in objs for p in o.data.polygons]
            cut=(mattress_cloth(spec,faces,bound['head_at_max']) if bound['model_cloth_kind']=='duvet' else
                 dict(center=spec['center'],size=spec['size'],geometry_basis='authored throw over actual model and simulated duvet'))
            candidate=dict(spec,id=spec['id'],material='diagnostic')
            try:
                records=builder.drape_cloth([candidate],{'diagnostic':mat},imported)
                row=dict(id=spec['id'],passed=True,records=records,actual_mattress_cut=cut)
            except ValueError as error_message:
                row=dict(id=spec['id'],passed=False,refused=str(error_message),actual_mattress_cut=cut)
                sheet=next((o for o in bpy.data.objects if o.name=='cloth-'+spec['id']),None)
                if sheet:row['clearance']=builder.cloth_model_clearance(sheet,imported[0]['objects'])
            proof['cloth'].append(row)
        # Force only missing-file detection, not source/intake acceptance.
        from unittest.mock import patch
        with patch('os.path.isfile',return_value=False):
            missing=builder.import_models([model],str(args.library))
        proof['missing_file_fallback']=bool(missing[0]['status']=='procedural-bed-fallback' and not fallback.hide_render and not fallback.get('replaced_by_model'))
        result.append(proof);args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(proof['asset'],'error',proof['import_bounds_max_error_m'],'cloth',[r['passed'] for r in proof['cloth']],flush=True)
    if any(r['import_bounds_max_error_m']>1e-5 or not r['fallback_hidden'] or not r['missing_file_fallback']
           or r['retained_source_triangles']!=r['source_triangles'] or not all(c['passed'] for c in r['cloth']) for r in result):
        raise ValueError('scaled importer/cloth proof refused; see '+str(args.output))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path,default=ROOT/'out/beds/round5/models-pending.json')
    parser.add_argument('--scene',type=Path,default=ROOT/'out/beds/round4/scene.json')
    parser.add_argument('--library',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round5/importer-cloth-first.json')
    parser.add_argument('--graphics-lock',type=Path,default=Path('/home/omar/archpipe/locks/graphics.lock'))
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    with args.graphics_lock.open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);run(args)
