"""Generate the unintegrated C4(e) candidate, schedules and diagnostic preview."""
import csv
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.concept import villa_render as VR
from archpipe.concept.mounting import scene_findings
from archpipe.concept.mounting_clearances import review
from checkpoint_mounting_d import schedule


def geometry_diff(scene, old):
    original={m['id']:m for m in old['meshes']}
    # Exported JSON arrays and in-memory tuple points carry the same geometry.
    # Compare coordinate values, not Python container types.
    changes=[m['id'] for m in scene['meshes'] if m['id'] in original and
             [[list(p) for p in f] for f in m['faces']]!=original[m['id']]['faces']]
    return dict(changed_original_meshes=changes,
        changed_family_meshes=[mid for mid in changes if original[mid].get('room')=='family-bath'],
        cameras_unchanged=old['views']==scene['views'])


def preview(scene,folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from archpipe.concept.fitting_mounting import points
    ids=['furn-study-desk-1','fix-DLN-bar-alcove-11','landscape-trellis-south','marker-STEP-stair-b-04']
    fig,axes=plt.subplots(1,4,figsize=(16,5))
    for ax,mid in zip(axes,ids):
        mesh=next(m for m in scene['meshes'] if m['id']==mid)
        host=scene['mounting_hosts'][mesh['mounting']['host_id']]
        axes_pair=(1,2) if 'trellis' in mid or 'marker' in mid else (0,2)
        host_faces=host.get('source_faces') or [f for m in scene['meshes'] if m.get('finished_host_id')==host['id'] for f in m['faces']]
        for faces,color,label in ((mesh['faces'],'#206ba8','Working geometry'),(host_faces,'#b88800','Actual support source')):
            ps=[p for f in faces for p in f]
            ax.scatter([p[axes_pair[0]] for p in ps],[p[axes_pair[1]] for p in ps],s=2,c=color,label=label)
        ax.set_title(mid,fontsize=8);ax.set_xlabel(('model x' if axes_pair[0]==0 else 'model y')+' (metres)')
        ax.set_ylabel('model z (metres)');ax.legend(fontsize=7)
    fig.suptitle('C4(e) diagnostic: modeled floor, joinery top, pending south boundary correction and wall marker')
    fig.tight_layout();fig.savefig(folder/'support-first-fix-preview.png',dpi=140);plt.close(fig)
    from archpipe.concept.mounting_clearances import measured_items
    from archpipe.concept import villa_furnish as F,villa_r11 as R
    from matplotlib.patches import Rectangle
    items=measured_items(scene,R.design('D1'));fig,axes=plt.subplots(1,2,figsize=(11,6))
    for ax,room in zip(axes,('guest-wc','parents-ensuite')):
        for it in items:
            if it['room']!=room or it.get('mounting_obstacle'):continue
            box=F.footprint(it);ax.add_patch(Rectangle(box[:2],box[2]-box[0],box[3]-box[1],fill=False,edgecolor='#206ba8'))
            ax.text(it['cx'],it['cy'],it['id'],fontsize=8,ha='center')
            if it['id'] in scene['wc_slides']:
                d=scene['wc_slides'][it['id']]['delta'];before=(box[0]-d[0],box[1]-d[1])
                ax.add_patch(Rectangle(before,box[2]-box[0],box[3]-box[1],fill=False,edgecolor='#ba2929',ls='--'))
        rr=F.clear_rect(R.design('D1'),room);ax.set_xlim(rr[0]-.1,rr[2]+.1);ax.set_ylim(rr[1]-.1,rr[3]+.1)
        ax.set_aspect('equal');ax.set_title(room);ax.set_xlabel('model x (metres)');ax.set_ylabel('model y (metres)')
    fig.suptitle('Authorized same-wall WC slides: red dashed before; blue after; all room checks rerun')
    fig.tight_layout();fig.savefig(folder/'wc-slides-preview.png',dpi=140);plt.close(fig)


def main(folder_name='c4-phase2e', preview_function=preview):
    folder=ROOT/'out'/folder_name;folder.mkdir(parents=True,exist_ok=True)
    scene=VR.build()
    from archpipe.villa_render_contract import validate_scene
    errors=validate_scene(scene)
    if errors:raise ValueError('Scene contract: '+'; '.join(errors))
    findings=scene_findings(scene);clearance=review(scene)
    pending=[r for r in scene['mounting_movements'] if r['approval']=='PENDING']
    last={r['id']:r for r in scene['mounting_movements'] if r['package']=='e-support'}
    proposal=deepcopy(scene);by={m['id']:m for m in proposal['meshes']}
    for row in pending:
        by[row['id']]['faces']=row['proposed_faces']
        by[row['id']].get('mounting',{}).pop('approval',None)
    proposed_findings=scene_findings(proposal)
    report=dict(status='CHECKPOINT; uncommitted; no presentation/native integration',
        original_missing_sites=len(scene['support_inventory_before']),
        missing_hosts=sum('MISSING mounting host' in f for f in findings),
        declared_host_count=len(scene['mounting_hosts']),
        pending_movement_rows=len(pending),pending_item_count=len({r['id'] for r in pending}),
        applied_e_items=sum(r['approval']!='PENDING' for r in last.values()),
        findings=findings,proposed_findings=proposed_findings,
        unexplained_findings=[f for f in findings if f.split(':')[0] not in {r['id'] for r in pending}],
        wc_slides=scene['wc_slide_decisions'],light_movements=scene['support_light_movements'],
        associated_movements=scene['support_associated_movements'],
        construction_requirements=[dict(id=m['id'],requirement=m['mounting']['installation_status'])
            for m in scene['meshes'] if m.get('mounting',{}).get('installation_status')],
        clearance_failures=clearance['failures'],clearance_unresolved=clearance['unresolved'])
    if 'e_lead_review' in scene:
        report['lead_review']=scene['e_lead_review']
        report['approved_associated_movements']=scene['e_approved_associated_movements']
        report['approved_light_movements']=scene['e_approved_light_movements']
        report['finding_types']=dict(missing_hosts=sum('MISSING mounting host' in f for f in findings),
            signed_plane=sum('finished-face error' in f for f in findings),
            finite_coverage=sum('finite host coverage' in f for f in findings),
            support_body_penetration=sum('associated assembly body penetrates' in f for f in findings),
            client_clearance=len(clearance['failures']))
        old=json.loads((ROOT/'out/c4-phase2e/working-scene.json').read_text())
        diff=geometry_diff(scene,old)
        (folder/'geometry-diff.json').write_text(json.dumps(diff,indent=2))
    for name,data in (('working-scene.json',scene),('proposed-scene.json',proposal),('mounting-report.json',report),('clearance-results.json',clearance)):
        (folder/name).write_text(json.dumps(data,indent=None if 'scene' in name else 2),encoding='utf-8')
    schedule(folder,'movements-over-5mm.csv',pending)
    schedule(folder,'movements-applied.csv',[r for r in last.values() if r['approval']!='PENDING'])
    schedule(folder,'wc-slides.csv',[r for r in scene['mounting_movements'] if r['package']=='wc-same-wall-slide'])
    with (folder/'clearance-results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(clearance['rows'][0]));writer.writeheader();writer.writerows(clearance['rows'])
    preview_function(scene,folder)
    print(json.dumps({k:v for k,v in report.items() if k not in ('findings','proposed_findings','wc_slides','associated_movements','light_movements','construction_requirements','approved_associated_movements','approved_light_movements')},indent=2))
    print('Proposed findings:',len(proposed_findings))
    return int(bool(findings or clearance['failures'] or clearance['unresolved']))


if __name__=='__main__':raise SystemExit(main())
