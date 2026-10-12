"""Publish reviewed Stage-2 receipt after numerical gates and image inspection.

This writes repository authoring input, not a native extract or presentation
image. Preview review is irreducible visual judgement and must precede use.
"""
from copy import deepcopy
import gzip,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.furniture_fit import require_furniture_geometry,review_selection
from archpipe.concept.furniture_stage2 import room_context
from archpipe.concept import villa_r11 as R,villa_furnish as F,revit_spec as RS

def main():
    folder=ROOT/'out/desks/stage2';models=json.loads((folder/'models-pending.json').read_text())
    evidence={r['bed']:r for r in json.loads((folder/'previews/evidence.json').read_text())}
    comparisons=json.loads((folder/'room-comparison.json').read_text());combined=json.loads((folder/'combined-room-comparison.json').read_text())
    review=json.loads((folder/'preview-review.json').read_text())
    if review.get('status')!='accepted' or set(review['items'])!={m['label'] for m in models} or not combined['ok']:
        raise ValueError('all previews and combined numerical comparison must be reviewed and passed')
    geometry={};credits=[]
    for model in models:
        row=evidence[model['label']]
        if not comparisons[model['label']]['ok'] or row['source_sha256']!=model['review_geometry']['source_sha256'] or row['import_transform_max_error_m']>1e-5:
            raise ValueError('real model gate failed: '+model['label'])
        images=[Path(row['isolated']['image']),Path(row['context_image'])]
        for path in images:
            if hashlib.sha256(path.read_bytes()).hexdigest()!=review['images'][str(path)]:raise ValueError('reviewed preview changed')
        model['neutral_review'].update(status='accepted',images={str(p):review['images'][str(p)] for p in images},review_basis=review['items'][model['label']])
        model['room_review']=dict(ok=True,selection=review_selection(model),comparison=deepcopy(comparisons[model['label']]['comparison']),
            evidence_sha256=hashlib.sha256(json.dumps(comparisons[model['label']],sort_keys=True).encode()).hexdigest())
        require_furniture_geometry(model)
        geometry[model['asset']]=model.pop('review_geometry');credits.append(model['credit'])
    scene=json.loads((folder/'live-procedural-scene.json').read_text())
    context=json.loads(gzip.decompress((folder/'live-authoring-context.json.gz').read_bytes()))
    layout,furniture,sp=context['layout'],context['furniture'],context['specification']
    expanded=[dict(m,review_geometry=geometry[m['asset']]) for m in models]
    receipt=dict(schema='furniture-stage2/1',option='D1',status='accepted',models=models,geometry=geometry,
        combined_room_review_ok=True,room_context_sha256=room_context(scene,layout,sp,furniture,expanded),
        layout_findings=combined['layout_findings'],reviewed_images=review['images'],credits=sorted(set(credits)),
        scope='Whole-item measured desks; exact existing footprint, heights and placement; all task chairs remain procedural',
        room_comparison_sha256=hashlib.sha256((folder/'combined-room-comparison.json').read_bytes()).hexdigest())
    reviewed_views={r['existing_view'] for r in evidence.values()}
    from archpipe.concept.furniture_stage2 import digest
    receipt['reviewed_cameras']={v['id']:digest(v['camera']) for v in scene['views'] if v['id'] in reviewed_views}
    target=ROOT/'knowledge/furniture-stage2.json.gz';target.write_bytes(gzip.compress(json.dumps(receipt,separators=(',',':')).encode(),mtime=0))
    (folder/'models-accepted.json').write_text(json.dumps(expanded,separators=(',',':'))+'\n')
    (folder/'credits.md').write_text('# Stage 2 accepted desk appearance credits\n\n'+'\n\n'.join(receipt['credits'])+'\n\nWhole-item nonuniform plan and independent vertical fit; source meshes/materials retained unchanged. Render appearance proxies, not certified buyable products.\n')
    print('Accepted',len(models),'desk instances; portable receipt bytes',target.stat().st_size)
if __name__=='__main__':main()
