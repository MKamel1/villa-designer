"""Measure immutable search-2 sources; preserve unresolved mattress refusals.

Metres are retained as the glTF default. Overall bounds never stand in for a
mattress. Factors are dimensionless; source height comes from one transform.
"""
from pathlib import Path
import gzip,hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import scaled_bed_fit
from archpipe.furniture_fit import native_box
from bed_axis_evidence import components,native,bounds
OUT=ROOT/'out/beds/search2';LIB=Path('/home/omar/archpipe/assets/library/props')
# Recipes name measured complete connected rectangular mattress components.
RECIPES={
 '3ddab7a9': [('defaultMaterial',0),('defaultMaterial',5)],
 'ea60847a': [('low_03 - Default_0',33),('low_03 - Default_0',34)],
 '560110ad': [('BunkBed1_Matress_0',0),('BunkBed1_Matress_0',1)],
 '7e5f290c': [('BunkBed2_Matress_0',0),('BunkBed2_Matress_0',1)],
 'e81c12b7': [('Bed Down_0',None),('Bed Up_0',None)],
 'b8fb5120': [('Object_32',None),('Object_50',None)],
 '8aeacdcd': [('beddown_beddown_0',1)],
 'c7bea79b': [('Object_16',None)],
}

def measure():
    results=[]
    for path in sorted((OUT/'geometry').glob('*.json.gz')):
        g=json.loads(gzip.decompress(path.read_bytes()));asset=g['asset'];folder=LIB/asset
        for name,h in g['source_sha256'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=h:raise ValueError('stale source '+asset)
        pts=np.asarray([p for m in g['meshes'] for f in m['faces'] for p in f]);lo,hi=pts.min(0),pts.max(0)
        p=json.loads((folder/'provenance.json').read_text())
        row=dict(asset=asset,name=p['name'],credit=(folder/'license.txt').read_text(),source_sha256=g['source_sha256'],
                 declared_unit='glTF metres; no inferred centimetre conversion',native_converted_bounds_m=[lo.tolist(),hi.tolist()],
                 triangles=sum(len(m['faces']) for m in g['meshes']),status='refused',claim='appearance proxy; not a verified buyable product')
        key=asset.removeprefix('sf_kbed_')
        if key in RECIPES:
            mattresses={};recipe_rows=[]
            for berth,(name,index) in zip(('lower','upper'),RECIPES[key]):
                m=next(m for m in g['meshes'] if m['name']==name)
                actual=np.asarray(components(m['faces'])[index] if index is not None else [p for f in m['faces'] for p in f])
                mattresses[berth]=bounds(native(actual))
                recipe_rows.append(dict(berth=berth,mesh=name,component_index=index,unique_vertices=len(set(map(tuple,actual))),converted_bounds_m=[actual.min(0).tolist(),actual.max(0).tolist()]))
            frame=bounds(native(pts));axis='X';front='-X'
            bunk=len(RECIPES[key])==2
            fit=scaled_bed_fit(frame,.9 if bunk else 1.2,2.,front,length_axis=axis,mattress_bounds=mattresses,mattress_top_m=1.4 if bunk else .475,
                 height_berth='upper' if bunk else 'lower',height_source='ASSUMED unchanged design mattress top above finished floor',
                 headboard_bounds=frame,headboard_limit_m=2.4,headboard_limit_source='ASSUMED existing diagnostic cap',required_berths=2 if bunk else 1)
            row.update(target='ka-bunk' if bunk else 'kb-bed',recipes=recipe_rows,mattress_bounds_native_m=mattresses,fit=fit)
            if bunk and fit.get('scale_xyz'):
                z=fit['scale_xyz'][2];lower=(recipe_rows[0]['converted_bounds_m'][1][2]-lo[2])*z
                upper=(recipe_rows[1]['converted_bounds_m'][1][2]-lo[2])*z
                row.update(resulting_tops_above_floor_m=[lower,upper],design_tops_above_floor_m=[.4,1.4],top_errors_m=[lower-.4,upper-1.4])
            row['refusal']=fit['reason'] if not fit['ok'] else 'both unchanged berth heights required; lower top differs under the upper-derived whole-item transform'
        else:
            row.update(target='kb-bed' if key in ('d92ab947','8aeacdcd','28a8b705','b5a75d2a','c7bea79b') else 'ka-bunk',
                       refusal='complete separate mattress geometry unresolved; no fit from frame, pillow or dressed surface bounds')
        results.append(row)
    (OUT/'measured-intake.json').write_text(json.dumps(results,indent=2)+'\n')
    (OUT/'credits.md').write_text('\n\n'.join(r['credit'] for r in results)+'\n\nSource bytes unchanged. glTF metres retained. No candidates activated.\n')
    for r in results:print(r['asset'],r.get('fit',{}).get('reason'),r.get('top_errors_m'),r['refusal'],flush=True)
if __name__=='__main__':measure()
