"""Prepare matched neutral before/after specimens for walk2 plant review.

Run this with project Python first. Render its before.json and after.json
using garden_g6_preview.py, passing the before receipt as --reference-receipt
for the after render. The diagnostic camera, metre-native geometry, neutral
light and 1.8 metre reference are therefore held equal within each pair.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def prepare(output):
    from archpipe.concept import garden_g6 as G,garden_g6b as B,villa_landscape as L,villa_render as V
    fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))
    old=fixture['old_lavender_clump']
    current=G.clump('g6-centrepiece-mona-0',old['species'],old['center'],old['root_z_m'],L._plant_data(),bed=old['bed'],layer=old['planting_layer'],context='bowl')
    old_spike=fixture['meshes'][0]
    flowers=[r for r in current['organ_connections'] if r['kind']=='flower'][:6]
    indices=flowers[0]['parent_face_indices']+[index for record in flowers for index in record['child_face_indices']]
    spike=deepcopy(current);spike['faces']=[deepcopy(current['faces'][i]) for i in indices]
    spike['face_materials']=[current['face_materials'][i] for i in indices]
    old_star=fixture['meshes'][1]
    growth=B.Growth('garden-foliage')
    growth.faces=deepcopy(old_star['faces'][:20]);growth.materials=['trellis']*20;growth._last_stem=list(range(20))
    growth.star(old_star['organ_connections'][0]['contact_m'],.041,'g6-lavender-flower')
    star=dict(id='walk2-petrea-flower',material='garden-foliage',faces=growth.faces,face_materials=growth.materials,explicit_geometry=True)
    # Preserve captured face slots, rather than assigning a plausible stem
    # material from the specimen label. The rejected first diagnostic made
    # a green Mona stem brown by guessing its material here.
    old_spike=deepcopy(old_spike);old_star=deepcopy(old_star)
    for mesh in (old_spike,old_star):mesh['explicit_geometry']=True
    # Only materials used by these actual specimens enter the preview input.
    names={'garden-foliage','g6-lavender-flower','trellis'}
    materials={name:deepcopy(V.M[name]) for name in names}
    output.mkdir(parents=True,exist_ok=True)
    for phase,meshes in [('before',[old,old_spike,old_star]),('after',[current,spike,star])]:
        assemblies=[]
        for identifier,mesh,width,target in zip(('mona-clump','mona-spike','petrea-flower'),meshes,(.65,.19,.095),((0,0,.20),(0,0,.06),(0,0,.015))):
            assemblies.append(dict(id=identifier,meshes=[mesh],detail_swatch=True,detail_ortho_scale_m=width,detail_target_m=target))
        data=dict(appearance_basis='Diagnostic actual old and first-fix botanical geometry. Materials unchanged; construction assumptions only; review pending.',materials=materials,assemblies=assemblies)
        (output/(phase+'.json')).write_text(json.dumps(data,separators=(',',':'))+'\n')
    print(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'out/walk2/plant-preview')
    prepare(parser.parse_args().output)
