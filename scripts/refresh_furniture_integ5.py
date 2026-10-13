"""Fresh fixed-room comparisons of existing selections on integration 5.

Diagnostic baseline export patches activation only in this explicit review
command. It never changes production guards or publishes unreviewed receipts.
"""
from copy import deepcopy
import argparse,gzip,json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.concept.furniture_stage2 import digest
from archpipe.furniture_fit import review_selection
from archpipe.beds import review_selection as bed_selection
from review_furniture_oct11 import compare
OUT=ROOT/'out/furniture-integ5'
def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())
def save(path,value):
    data=json.dumps(value,separators=(',',':')).encode()
    path.write_bytes(gzip.compress(data,mtime=0) if path.suffix=='.gz' else data)
def inputs():
    raw=load(OUT/'procedural-scene.json');context=raw['authoring_room_context']
    fr=load(ROOT/'knowledge/furniture-stage2.json.gz');br=load(ROOT/'knowledge/parents-bed.json.gz')
    models=[dict(m,review_geometry=fr['geometry'][m['asset']]) for m in fr['models']]+br['models']
    return raw,context,models,fr,br

def export():
    from archpipe.concept import villa_render as V
    with patch('archpipe.concept.furniture_stage2.apply',side_effect=lambda s,*a:s), patch('archpipe.concept.parents_bed.apply',side_effect=lambda s,*a:s):
        raw=V.build()
    save(OUT/'procedural-scene.json',raw)
    save(OUT/'authoring-context.json.gz',raw['authoring_room_context'])
    print('Exported integrated diagnostic baseline',flush=True)

def prepare():
    raw,context,models,fr,br=inputs()
    save(OUT/'old-furniture-receipt.json.gz',fr);save(OUT/'old-bed-receipt.json.gz',br)
    save(OUT/'pending-furniture.json',[m for m in models if m['role']!='bed'])
    save(OUT/'pending-bed.json',[m for m in models if m['role']=='bed'])
    # The diagnostic preview retains every imported selection, exact body
    # hiding and unchanged view, without publishing a production receipt.
    from archpipe.concept.furniture_stage2 import integrate,room_context
    trial=deepcopy(fr);trial['room_context_sha256']=room_context(raw,context['layout'],context['specification'],context['furniture'],models[:-1])
    furnished=integrate(raw,models[:-1],context['layout'],context['specification'],context['furniture'],trial)
    furnished['models']+=deepcopy(br['models'])
    save(OUT/'pending-furnished-scene.json',furnished)
    print('Prepared neutral diagnostics; production snapshots remain unchanged',flush=True)

def review():
    raw,context,models,fr,br=inputs()
    baseline=deepcopy(raw);baseline['meshes']+=br['baseline_cloth']
    results={}
    for model in models:
        result=compare(baseline,context,[model],[model['label']]);results[model['label']]=result
        save(OUT/'room-comparisons.json',results)
        print(model['label'],result['ok'],'relative failures',len(result['findings']),flush=True)
    joint=compare(baseline,context,models,[m['label'] for m in models]);save(OUT/'combined-room-comparison.json',joint)
    print('Combined',joint['ok'],len(joint['findings']),flush=True)
    if not joint['ok'] or not all(r['ok'] for r in results.values()):raise ValueError('integrated relative room gate closed')

def accept():
    """Publish only fresh bound individual/joint room and inspected image proofs."""
    import hashlib
    from archpipe.concept.furniture_stage2 import integrate,room_context
    from archpipe.furniture_fit import require_furniture_geometry
    from archpipe.beds import require_bed_geometry
    raw,context,models,fr,br=inputs()
    comparisons=load(OUT/'room-comparisons-current-furniture.json')
    combined=load(OUT/'combined-room-comparison.json')
    if not combined['ok'] or set(comparisons)!={m['label'] for m in models} or not all(r['ok'] for r in comparisons.values()):
        raise ValueError('fresh integrated room review missing or refused')
    baseline=load(OUT/'baseline-bed-previews/pb-bed-evaluated-cloth.json.gz')
    if baseline!=br['baseline_cloth']:raise ValueError('fresh baseline changed; repeat every comparison using new evaluated cloth')
    visual=load(OUT/'preview-review.json')
    if visual.get('status')!='accepted':raise ValueError('neutral image inspection missing')
    rows={r['bed']:r for r in load(OUT/'furniture-previews/evidence.json')+load(OUT/'bed-previews/evidence.json')}
    for m in models:
        r=rows[m['label']];selection=bed_selection(m) if m['role']=='bed' else review_selection(m)
        if r['scaled_model_selection']!=selection or r['source_sha256']!=m['review_geometry']['source_sha256']:
            raise ValueError('source/selection preview mismatch')
        images=[r['isolated']['image'],r['context_image']]
        for path in images:
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=visual['images'].get(path):raise ValueError('inspected image changed')
        m['neutral_review'].update(status='accepted',images={p:visual['images'][p] for p in images},review_basis=visual['items'][m['label']])
        if m['role']=='bed':
            if not isinstance(r['cloth_report'],list) or any(any(c['model_clearance'][k] for k in ('intersections','inside_vertices','uncertain_vertices')) for c in r['cloth_report']):
                raise ValueError('fresh evaluated cloth refused')
            m['physical_cloth_review']=dict(status='accepted',selection=bed_selection(m),records=r['cloth_report'])
            require_bed_geometry(m)
        else:
            if r['import_transform_max_error_m']>1e-5:raise ValueError('import transform changed')
            m['room_review']=dict(ok=True,selection=review_selection(m),comparison=comparisons[m['label']]['comparison'],evidence_sha256=digest(comparisons[m['label']]))
            require_furniture_geometry(m)
    furniture=[m for m in models if m['role']!='bed'];bed=[m for m in models if m['role']=='bed']
    fr.update(geometry={m['asset']:m['review_geometry'] for m in furniture},models=[{k:v for k,v in m.items() if k!='review_geometry'} for m in furniture],
              room_context_sha256=room_context(raw,context['layout'],context['specification'],context['furniture'],furniture),
              reviewed_images=visual['images'],layout_findings=combined['layout_findings'],room_comparison_sha256=digest(combined))
    reviewed={r['existing_view'] for r in rows.values()}
    fr['reviewed_cameras']={v['id']:digest(v['camera']) for v in raw['views'] if v['id'] in reviewed}
    current=integrate(raw,furniture,context['layout'],context['specification'],context['furniture'],fr)
    signature=room_context(current,context['layout'],context['specification'],context['furniture'],bed)
    br.update(models=bed,baseline_cloth=baseline,room_context_sha256=signature,combined_room_review_sha256=digest(combined),
              reviewed_images={p:h for p,h in visual['images'].items() if '/bed-previews/' in p},
              reviewed_cameras={'v22-parents-day':digest(next(v['camera'] for v in raw['views'] if v['id']=='v22-parents-day'))})
    br['room_review']=dict(room_context_sha256=signature,selections=[bed_selection(m) for m in bed],baseline_cloth_sha256=digest(baseline),review=comparisons['pb-bed'])
    br['cloth_specs_sha256']=digest([c for c in raw['cloth'] if c['id'].startswith(('duvet-pb-bed','throw-pb-bed'))])
    save(ROOT/'knowledge/furniture-stage2.json.gz',fr);save(ROOT/'knowledge/parents-bed.json.gz',br)
    print('Refreshed both reviewed snapshots; all geometry and camera guards retained',flush=True)

_WORK=None

def _review_one(index):
    raw,context,models,fr,br=_WORK
    model=models[index]
    baseline=dict(raw,meshes=raw['meshes']+br['baseline_cloth'])
    if model['role']!='desk':
        fixed=[m for m in models if m['role']=='desk' or (model['role']=='bed' and m['role']=='task_chair')]
        baseline=dict(baseline,models=raw['models']+fixed)
    return model['label'],compare(baseline,context,[model],[model['label']])

def review_current():
    """Bounded three-process same-card review; workers never mutate receipts."""
    global _WORK
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    _WORK=inputs();raw,context,models,fr,br=_WORK
    results={}
    with ProcessPoolExecutor(max_workers=3,mp_context=get_context('fork')) as pool:
        for label,result in pool.map(_review_one,range(len(models))):
            results[label]=result;save(OUT/'room-comparisons-current-furniture.json',results)
            print(label,result['ok'],len(result['findings']),flush=True)
    baseline=dict(raw,meshes=raw['meshes']+br['baseline_cloth'])
    joint=compare(baseline,context,models,[m['label'] for m in models]);save(OUT/'combined-room-comparison.json',joint)
    print('Combined',joint['ok'],len(joint['findings']),flush=True)
    if not joint['ok'] or not all(r['ok'] for r in results.values()):raise ValueError('integrated furnished room gate closed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['export','prepare','review','review-current','accept']);p.add_argument('--output',type=Path,default=OUT);a=p.parse_args();OUT=a.output.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    {'export':export,'prepare':prepare,'review':review,'review-current':review_current,'accept':accept}[a.action]()
