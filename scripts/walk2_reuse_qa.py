"""Revalidate unchanged rendered pixels after a proven QA-only source correction.

Original packages remain immutable. Fresh preparation/admission must independently
match all render inputs and evaluated geometry before importing anything. Native
measurement generates fresh QA sidecars; an old QA verdict is never imported.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from archpipe.safe_io import save_bytes


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    from archpipe.safe_io import save_bytes
    save_bytes(path,(json.dumps(value,indent=2)+'\n').encode())


FUNCTIONS={'src/archpipe/blender/villa_scene.py':{'frame_qa_scene'},
           'src/archpipe/blender/photoreal.py':{'scene_qa'},
           'src/archpipe/render_qa.py':{'check'}}
ADAPTER_SOURCE='scripts/villa_render.py'


def render_ast(source,name):
    tree=ast.parse(source)
    class AnalysisOnly(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name in FUNCTIONS.get(name,set()):return None
            if name==ADAPTER_SOURCE and node.name=='villa_qa_context':
                returns=[statement for statement in node.body if isinstance(statement,ast.Return)]
                if len(returns)!=1 or not isinstance(returns[0].value,ast.Dict):
                    raise ValueError('Post-render QA adapter boundary differs')
                value=returns[0].value
                indices=[i for i,key in enumerate(value.keys)
                         if isinstance(key,ast.Constant) and key.value=='room_glazing_pixels']
                if len(indices)>1:raise ValueError('Ambiguous QA adapter ownership field')
                if indices:
                    index=indices[0]
                    if ast.dump(value.values[index])!=ast.dump(ast.parse('measured.get("room_glazing_pixels")',mode='eval').body):
                        raise ValueError('Post-render QA adapter ownership value differs')
                    value.keys.pop(index);value.values.pop(index)
                return node
            if name=='src/archpipe/blender/walkthrough.py' and node.name=='render_frames':
                records=[]
                for parent in ast.walk(node):
                    for _field,suite in ast.iter_fields(parent):
                        if not isinstance(suite,list):continue
                        for index,statement in enumerate(suite):
                            if (not isinstance(statement,ast.Assign) or len(statement.targets)!=1
                                    or not isinstance(statement.targets[0],ast.Name)
                                    or statement.targets[0].id!='record'
                                    or not isinstance(statement.value,ast.Call)
                                    or not isinstance(statement.value.func,ast.Name)
                                    or statement.value.func.id!='dict'):continue
                            renders=[item for item in suite[:index] if isinstance(item,ast.Expr)
                                     and isinstance(item.value,ast.Call)
                                     and ast.unparse(item.value.func)=='bpy.ops.render.render']
                            owned=[kw for kw in statement.value.keywords if kw.arg=='qa_scene']
                            if (len(renders)!=1 or len(owned)!=1 or not isinstance(owned[0].value,ast.Call)
                                    or ast.unparse(owned[0].value.func)!='V.frame_qa_scene'):
                                raise ValueError('Post-render QA boundary is missing or changed')
                            records.append(statement.value)
                if len(records)!=1:raise ValueError('Post-render QA record is missing or ambiguous')
                records[0].keywords=[kw for kw in records[0].keywords if kw.arg!='qa_scene']
                return node
            return node
    return ast.dump(AnalysisOnly().visit(tree),include_attributes=False)


def prove_qa_only(before,after,frozen,root=ROOT):
    added=set(after)-set(before);removed=set(before)-set(after)
    if added!={'src/archpipe/window_qa.py'} or removed:
        raise ValueError('QA reuse source inventory addition/removal differs')
    changed={name for name in before if before[name]!=after[name]}
    permitted=set(FUNCTIONS)|{'src/archpipe/blender/walkthrough.py'}
    if changed not in (permitted,permitted|{ADAPTER_SOURCE}):
        raise ValueError(f'QA reuse source changes differ: {sorted(changed)}')
    for name in sorted(changed):
        old=frozen/name;new=root/name
        if file_hash(old)!=before[name] or file_hash(new)!=after[name]:
            raise ValueError('QA reuse source snapshot differs')
        if render_ast(old.read_text(),name)!=render_ast(new.read_text(),name):
            raise ValueError('Rendering or non-QA source changed: '+name)
    return dict(passed=True,changed_sources=sorted(changed),added_sources=sorted(added),
                control='AST equality outside post-render QA functions/context keyword; exact inventory elsewhere',
                before=before,after=after)


def validate(source,out,frozen):
    from scripts.flythrough import require_inputs,source_inventory
    from archpipe.flythrough import require_path_hash
    old=json.loads((source/'manifest.json').read_text());new=json.loads((out/'manifest.json').read_text())
    proof=prove_qa_only(old['sources'],source_inventory(),frozen)
    path=require_inputs(out);oldpath=require_path_hash(json.loads((source/'path.json').read_text()))
    if path!=oldpath:raise ValueError('Rendered path changed')
    for directory,manifest in ((source,old),(out,new)):
        if manifest['scene_sha256']!=file_hash(directory/'scene.json'):
            raise ValueError('Prepared scene bytes differ')
        if manifest['photometry']!={str(p.relative_to(directory/'ies')):file_hash(p) for p in (directory/'ies').rglob('*.ies')}:
            raise ValueError('Photometry bytes differ')
    if old['photometry']!=new['photometry']:raise ValueError('Rendered photometry changed')
    scenes=[json.loads((d/'scene.json').read_text()) for d in (source,out)]
    for scene in scenes:scene.pop('provenance',None)
    if scenes[0]!=scenes[1]:raise ValueError('Physical scene or render view data changed')
    proof.update(source_manifest_sha256=file_hash(source/'manifest.json'),
                 target_manifest_sha256=file_hash(out/'manifest.json'),path_sha256=path['sha256'],
                 physical_scene_equal=True,photometry_equal=True)
    return proof


def import_pixels(source,out,frozen):
    from archpipe.exposure_groups import transport_digest,RULE_SHA256
    from archpipe.flythrough import digest,require_renderable
    proof=validate(source,out,frozen)
    a=json.loads((source/'assembly/assembly.json').read_text());b=json.loads((out/'assembly/assembly.json').read_text())
    geometry=a['receipt']['evaluated_meshes_sha256']
    if geometry!=b['receipt']['evaluated_meshes_sha256']:raise ValueError('Native evaluated geometry changed')
    require_renderable(json.loads((out/'assembly/guards.json').read_text()))
    lock=json.loads((source/'exposure/lock.json').read_text());scene=json.loads((out/'scene.json').read_text())
    if (lock['sha256']!=digest({k:v for k,v in lock.items() if k!='sha256'})
            or lock['transport_sha256']!=transport_digest(scene) or lock['rule_sha256']!=RULE_SHA256
            or lock['path_sha256']!=proof['path_sha256']):raise ValueError('Source meter/transport binding changed')
    (out/'exposure').mkdir(exist_ok=True);images=[];meters=[]
    count=json.loads((out/'path.json').read_text())['settings']['frames']
    for i in range(count):
        file=source/'exposure'/f'frame-{i:04d}.json';record=json.loads(file.read_text())
        if (record['path_sha256']!=proof['path_sha256']
                or record['source']!=lock['source_measurements'][i]
                or record['meter']!=lock['group_meters'][f'frame-{i:04d}']):
            raise ValueError('Stale original source meter')
        save_bytes(out/'exposure'/file.name,file.read_bytes());meters.append(dict(index=i,sha256=file_hash(file)))
    save_bytes(out/'exposure/lock.json',(source/'exposure/lock.json').read_bytes())
    for stage,indices in (('preview',range(count)),('draft',(0,(count-1)//2,count-1))):
        (out/stage).mkdir(exist_ok=True)
        originals=out/'reuse/original-receipts'/stage;originals.mkdir(parents=True,exist_ok=True)
        for i in indices:
            png=source/stage/f'frame-{i:04d}.png';receipt=png.with_suffix('.json');record=json.loads(receipt.read_text())
            if (record['png_sha256']!=file_hash(png) or record['path_sha256']!=proof['path_sha256']
                    or record['lock_sha256']!=lock['sha256']):raise ValueError('Original image/receipt changed')
            save_bytes(out/stage/png.name,png.read_bytes());save_bytes(originals/receipt.name,receipt.read_bytes())
            images.append(dict(stage=stage,index=i,source_png=str(png),source_receipt=str(receipt),
                               png_sha256=file_hash(png),receipt_sha256=file_hash(receipt)))
    proof.update(evaluated_meshes_sha256=geometry,source_directory=str(source),target_directory=str(out),
                 images=images,source_meters=meters,lock_sha256=lock['sha256'],
                 generator_sha256=file_hash(__file__))
    save(out/'reuse/plan.json',proof)
    print('Imported',len(images),'immutable pixel images and',len(meters),'unchanged source meters; fresh native QA required')


def native_refresh(out):
    import bpy
    from archpipe.blender import walkthrough as W
    from scripts.flythrough import require_inputs
    from types import SimpleNamespace
    import time
    plan=json.loads((out/'reuse/plan.json').read_text());require_inputs(out)
    if not plan['passed'] or plan['generator_sha256']!=file_hash(__file__):
        raise ValueError('QA-only reuse proof/generator missing or changed')
    path,scene,context=W.load_context(SimpleNamespace(root=str(out)));views=W.frame_views(path,scene)
    if context['receipt']['evaluated_meshes_sha256']!=plan['evaluated_meshes_sha256']:
        raise ValueError('Native revalidation geometry differs')
    completed=[]
    for row in plan['images']:
        stage,index=row['stage'],row['index'];png=out/stage/f'frame-{index:04d}.png';original=out/'reuse/original-receipts'/stage/png.with_suffix('.json').name
        if file_hash(png)!=row['png_sha256'] or file_hash(original)!=row['receipt_sha256']:
            raise ValueError('Reused pixel/original receipt changed')
        receipt=png.with_suffix('.json')
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            if prior.get('render_origin')==row and prior.get('qa_sources')==plan['after']:
                completed.append(dict(stage=stage,index=index,receipt_sha256=file_hash(receipt)));continue
            raise ValueError('Refusing overwrite of a nonmatching fresh QA receipt')
        record=json.loads(original.read_text());view=views[index];camera,pitch,emissive=W.setup(scene,context,view)
        bpy.context.scene.render.resolution_x,bpy.context.scene.render.resolution_y=record['resolution']
        bpy.context.scene.render.resolution_percentage=100;bpy.context.view_layer.update();started=time.monotonic()
        record.update(qa_scene=W.V.frame_qa_scene(scene,view,camera,context['objects'],context['materials'],context['cloth_report'],geometry_key=plan['evaluated_meshes_sha256']),
                      subjects=W.V.subjects(view,scene['meshes'],context['objects']),render_origin=row,
                      qa_sources=plan['after'],qa_measurement_seconds=time.monotonic()-started)
        W.remove_camera(camera);save(receipt,record);completed.append(dict(stage=stage,index=index,receipt_sha256=file_hash(receipt)))
        if len(completed)%50==0:print('Fresh native QA',len(completed),'/',len(plan['images']),flush=True)
    require_inputs(out);save(out/'reuse/native-revalidation.json',dict(passed=True,images=completed,plan_sha256=file_hash(out/'reuse/plan.json')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['validate','import','native-refresh'])
    parser.add_argument('--source',type=Path,default=ROOT/'out/walk2/production3')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--frozen',type=Path,default=ROOT/'out/walk2/diagnosis/window-qa-before/source')
    args=parser.parse_args();os.environ['ARCHPIPE_FLYTHROUGH_POLICY']=str(ROOT/'knowledge/walk2-policy.json')
    source,out=args.source.resolve(),args.out.resolve()
    if source==out:raise ValueError('Original package must remain immutable')
    if args.operation=='validate':print(json.dumps(validate(source,out,args.frozen),indent=2))
    elif args.operation=='import':import_pixels(source,out,args.frozen)
    else:native_refresh(out)

if __name__=='__main__':
    arguments=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    sys.argv=[sys.argv[0]]+arguments;main()
