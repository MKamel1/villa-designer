"""Real cache round trip: keep every referenced material without changing meshes."""
from pathlib import Path
import bpy,json,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.blender import villa_scene as V
from archpipe import flythrough as W
def test_real_referenced_material_cache_roundtrip(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    scene=json.loads((root/'scene.json').read_text());metadata=json.loads((root/'assembly/assembly.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(root/'assembly/scene.blend'))
    missing_before=[name for name in metadata['materials'].values() if name not in bpy.data.materials]
    from archpipe.drape_appearance import needs_admission,render_materials
    specs=render_materials(scene) if needs_admission(scene) else scene['materials']
    materials={}
    for key,name in metadata['materials'].items():
     material=bpy.data.materials.get(name)
     if material is None:material=V.add_material(name,specs[key],os.path.expandvars(os.path.expanduser(scene['library_root'])),[])
     materials[key]=material
    before=V.evaluated_scene_receipt(scene,{})['evaluated_meshes_sha256']
    retain=getattr(W,'retain_cache_materials',lambda mapping:None)
    retain(materials)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'cache.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(out/'cache.blend'))
    missing_after=[name for name in metadata['materials'].values() if name not in bpy.data.materials]
    after=V.evaluated_scene_receipt(scene,{})['evaluated_meshes_sha256']
    result=dict(missing_before=missing_before,missing_after=missing_after,geometry_unchanged=before==after,
                passed=bool(missing_before) and not missing_after and before==after)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise ValueError(result)

if __name__=='__main__':
    index=sys.argv.index('--')
    test_real_referenced_material_cache_roundtrip(sys.argv[index+1],sys.argv[index+2])
