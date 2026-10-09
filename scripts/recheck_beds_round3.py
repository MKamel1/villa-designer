"""Re-evaluate cached round-2 bed faces under client decision 2026-10-08.

Read-only library: hashes are checked before any measurement. No model,
shared extract, layout or texture is modified. Connected components are
measured diagnostics; unidentified/fused mattresses never count as passed.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.beds import fit_bed,unit_scale
from bed_axis_evidence import components,native,bounds


def recheck(geometry_root,library_root):
    old=json.loads((ROOT/'tests/fixtures/bed-round2-measurements.json').read_text())
    manifest=json.loads((ROOT/'ops/workstation/library-manifest.json').read_text())
    entries={r['id']:r for r in manifest['props']}
    results=[]
    for row in old:
        asset=row['id'];entry=entries[asset]
        geometry=json.loads(gzip.decompress((geometry_root/(asset+'.json.gz')).read_bytes()))
        for name,digest in geometry['source_sha256'].items():
            path=library_root/'props'/asset/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError(asset+': stale receipt '+name)
        meshes=geometry['meshes'];mattresses={};notes=[];selection={}
        if asset=='sf_bed_forssa':
            part=next(m for m in meshes if m['name'].startswith('Matras011'))
            mattresses['lower']=bounds(native([p for f in part['faces'] for p in f]))
            selection['lower']=dict(mesh=part['name'],basis='named mattress, actual indexed faces')
        elif asset=='sf_bed_scandi_bare':
            part=next(m for m in meshes if m['name']=='Object_14')
            mattresses['lower']=bounds(native([p for f in part['faces'] for p in f]))
            selection['lower']=dict(mesh=part['name'],basis='round-2 actual mattress-cut binding')
        elif asset=='sf_bed_upholstered_cyberfox':
            part=next(m for m in meshes if m['name']=='Object_4')
            candidates=[p for p in components(part['faces']) if len(p)==126]
            if len(candidates)!=1:raise ValueError('Cyberfox mattress component changed')
            mattresses['lower']=bounds(native(candidates[0]))
            selection['lower']=dict(mesh='Object_4',component_vertices=126,
                basis='rounded mattress component above base, under pillows/duvet; seven body components, neutral silhouette reviewed',
                production_binding_status='fused mesh; component measurement only, no activation binding')
            notes.append('No bedside tables, benches or rugs among either imported mesh or their eleven connected components; omitted meshes: none.')
        elif asset=='sf_bunk_home_series':
            part=next(m for m in meshes if m['name'].startswith('materass'))
            berths=sorted(components(part['faces']),key=lambda p:min(v[2] for v in p))
            if len(berths)!=2:raise ValueError('Home Series mattress components changed')
            for key,points in zip(('lower','upper'),berths):
                mattresses[key]=bounds(native(points))
                selection[key]=dict(mesh=part['name'],component_vertices=len(points),basis='separate vertical mattress component',
                    production_binding_status='both berths share one mesh; lower head direction unresolved')
            notes.append('Lower head direction unresolved; unit correction cannot be guessed from large dimensions.')
        else:
            notes.append('Single fused mesh: six components; bedding surfaces connect to mattress. Actual naked mattress bounds unresolved; no ladder in reviewed silhouette. Refused, not a fit pass.')
        native_frame=bounds(native([p for m in meshes for f in m['faces'] for p in f]))
        required=2 if 'bunk' in asset else 1
        fit=fit_bed(native_frame,*row['target'],row['front_axis'],row['length_axis'],
            mattress_bounds=mattresses,scale=1.,required_berths=required)
        old_fit=fit_bed(row['bounds_m'],*row['target'],row['front_axis'],row['length_axis'],
            mattress_bounds=mattresses,scale=row['fit']['scale'],required_berths=required)
        results.append(dict(asset=asset,author=entry.get('author'),url=entry.get('source_url'),
            licence=entry.get('licence'),source_sha256=geometry['source_sha256'],
            units=dict(unit='m',source='glTF 2.0 default metres; no alternate unit declaration identified',conversion=unit_scale()),
            real_frame_bounds_native_m=native_frame,mattress_selection=selection,mattress_bounds_native_m=mattresses,
            omitted_meshes=[],notes=notes,real_size_fit=fit,round2_scale_refusal=old_fit['reason'],
            c8_status='not run in room: actual mattress fit/identification rejected before placement',
            preview_status='no accepted replacement; neutral previews required only for passing candidates'))
    return dict(schema='beds-round3-recheck/1',client_decision_date='2026-10-08',
        rule='source units only; actual mattress +/-20 mm; frame may extend; fixed mattress datum and layout; bed-only meshes',
        geometry_basis='unchanged round-2 imported actual faces; source hashes rechecked on disk',results=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry',type=Path,default=ROOT/'out/beds/round2/geometry')
    parser.add_argument('--library-root',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round3/recheck.json')
    args=parser.parse_args();report=recheck(args.geometry,args.library_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for row in report['results']:
        print(row['asset'],row['real_size_fit']['reason'])
