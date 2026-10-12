"""Publish source-bed and task-chair receipts only after bound neutral review."""
from copy import deepcopy
import gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.furniture_fit import review_selection,require_furniture_geometry
from archpipe.beds import review_selection as bed_selection,require_bed_geometry
from archpipe.concept.furniture_stage2 import room_context,digest,integrate
from review_furniture_oct11 import compare
from review_all_furniture_oct11 import inputs as joint_inputs
OUT=ROOT/'out/furniture-oct11'
def encoded(value):return gzip.compress(json.dumps(value,separators=(',',':')).encode(),mtime=0)
def main():
    visual=json.loads((OUT/'preview-review.json').read_text())
    if visual.get('status')!='accepted':raise ValueError('neutral review is pending')
    context=json.loads(gzip.decompress((ROOT/'out/desks/stage2/live-authoring-context.json.gz').read_bytes()))
    raw=json.loads((ROOT/'out/desks/stage2/live-procedural-scene.json').read_text())
    current=json.loads((OUT/'current-furniture-scene.json').read_text())
    bed=json.loads((OUT/'bed-pending.json').read_text())[0]
    chairs=json.loads((OUT/'chairs-pending.json').read_text())
    for kind,models in [('bed',[bed]),('chairs',chairs)]:
        evidence={r['bed']:r for r in json.loads((OUT/('bed-previews-current' if kind=='bed' else 'chair-previews-current')/'evidence.json').read_text())}
        comparison=json.loads((OUT/(kind+'-room-comparison.json')).read_text())
        combined=json.loads((OUT/(kind+'-combined.json')).read_text())
        if not combined['ok']:raise ValueError('combined room gate closed: '+kind)
        for model in models:
            r=evidence[model['label']];selection=bed_selection(model) if kind=='bed' else review_selection(model)
            if r['scaled_model_selection']!=selection or r['source_sha256']!=model['review_geometry']['source_sha256'] or not comparison[model['label']]['ok']:
                raise ValueError('preview/room receipt disagrees with proposed selection')
            images=[r['isolated']['image'],r['context_image']]
            for image in images:
                if hashlib.sha256(Path(image).read_bytes()).hexdigest()!=visual['images'].get(image):raise ValueError('reviewed image changed')
            model['neutral_review'].update(status='accepted',images={im:visual['images'][im] for im in images},review_basis=visual['items'][model['label']])
            if kind=='bed':
                if any(any(row['model_clearance'][key] for key in ('intersections','inside_vertices','uncertain_vertices')) for row in r['cloth_report']):raise ValueError('cloth refused')
                model['physical_cloth_review']=dict(status='accepted',selection=bed_selection(model),records=r['cloth_report'])
                model.pop('diagnostic_status',None)
                model['source_selection_status']='accepted: separable source covers omitted; room, physical cloth and neutral gates passed'
                require_bed_geometry(model)
            else:
                if r['import_transform_max_error_m']>1e-5:raise ValueError('actual furniture readback failed')
                model['room_review']=dict(ok=True,selection=review_selection(model),comparison=comparison[model['label']]['comparison'],evidence_sha256=digest(comparison[model['label']]))
                require_furniture_geometry(model)
    old=json.loads(gzip.decompress((ROOT/'knowledge/furniture-stage2.json.gz').read_bytes()))
    desks=[dict(m,review_geometry=old['geometry'][m['asset']]) for m in old['models'] if m['role']=='desk']
    all_models=desks+chairs
    combined=json.loads((OUT/'all-replacements-combined.json').read_text())
    if combined.get('inputs_sha256')!=joint_inputs()[3]:raise ValueError('joint room review inputs changed')
    if not combined['ok']:raise ValueError('all replacements combined gate closed')
    receipt=deepcopy(old);receipt['geometry']={m['asset']:m['review_geometry'] for m in all_models}
    receipt['models']=[{k:v for k,v in m.items() if k!='review_geometry'} for m in all_models]
    receipt['room_context_sha256']=room_context(raw,context['layout'],context['specification'],context['furniture'],all_models)
    receipt['scope']='Seven measured desks and eight seat-scaled task-chair appearances; vanity remains procedural; all inherited room findings retained'
    receipt['reviewed_images'].update(visual['images']);receipt['credits']=sorted(set(receipt['credits']+[m['credit'] for m in chairs]))
    receipt['layout_findings']=combined['layout_findings'];receipt['room_comparison_sha256']=digest(combined)
    receipt['reviewed_cameras'].update({v['id']:digest(v['camera']) for v in raw['views'] if v['id'] in visual['existing_views']})
    furniture_scene=integrate(raw,all_models,context['layout'],context['specification'],context['furniture'],receipt)
    bed_receipt=dict(schema='parents-bed/1',option='D1',status='accepted',models=[bed],
        baseline_cloth=json.loads(gzip.decompress((ROOT/'out/beds/round7/baseline-previews/pb-bed-evaluated-cloth.json.gz').read_bytes())),
        room_context_sha256=room_context(furniture_scene,context['layout'],context['specification'],context['furniture'],[bed]),
        reviewed_cameras={'v22-parents-day':digest(next(v['camera'] for v in raw['views'] if v['id']=='v22-parents-day'))},
        combined_room_review_sha256=digest(combined),reviewed_images={p:h for p,h in visual['images'].items() if '/bed-previews-current/' in p},credit=bed['attribution'])
    bed_receipt['cloth_specs_sha256']=digest([c for c in raw['cloth'] if c['id'].startswith(('duvet-pb-bed','throw-pb-bed'))])
    bed_receipt['room_review']=dict(room_context_sha256=bed_receipt['room_context_sha256'],selections=[bed_selection(bed)],
        baseline_cloth_sha256=digest(bed_receipt['baseline_cloth']),review=json.loads((OUT/'bed-room-comparison.json').read_text())['pb-bed'])
    # Finish both receipts before running any fresh consumers.
    (ROOT/'knowledge/furniture-stage2.json.gz').write_bytes(encoded(receipt))
    (ROOT/'knowledge/parents-bed.json.gz').write_bytes(encoded(bed_receipt))
    (OUT/'models-accepted.json').write_text(json.dumps(all_models+[bed],separators=(',',':'))+'\n')
    (OUT/'credits.md').write_text('\n\n'.join(receipt['credits']+[bed['attribution']['credit']])+'\n\nAppearance proxies with recorded whole-item/source-frame transforms; not verified buyable products.\n')
    print('Accepted seven desks, eight task chairs and parents bed; combined room gate passed',flush=True)
if __name__=='__main__':main()
