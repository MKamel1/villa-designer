"""C4 approved b/c corrections and ceiling package checkpoint; no integration."""
import csv
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from archpipe.concept import villa_render as VR
from archpipe.concept import villa_r11 as R
from archpipe.concept.mounting import scene_findings
from archpipe.concept.mounting_clearances import review


def schedule(folder,name,rows):
    fields=['id','package','host_id','old','new','mm','why','approval']
    with (folder/name).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(row[k]) if isinstance(row[k],list) else row[k] for k in fields})


def preview(scene,folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from archpipe.concept.fitting_mounting import points
    frozen=json.loads((ROOT/'tests/fixtures/c4-guest-before-fixes.json').read_text())
    old={m['id']:m for m in frozen['meshes']}
    meshes={m['id']:m for m in scene['meshes']}
    fig,axes=plt.subplots(1,3,figsize=(15,6))
    ids=['detail-gwc-hand-shower-head','detail-gwc-hand-shower-hose','lamp-SCONCE-guest-wc-03']
    for ax,mid,coordinates in zip(axes,ids,((0,2),(0,2),(1,2))):
        for mesh,color,label in ((old[mid],'#ba2929','Before separate guest correction'),(meshes[mid],'#206ba8','Applied candidate')):
            ps=points(mesh)
            ax.scatter([p[coordinates[0]] for p in ps],[p[coordinates[1]] for p in ps],s=1,c=color,label=label)
        host=scene['mounting_hosts'][meshes[mid]['mounting']['host_id']]
        if coordinates[0]==0:
            face=host['structural_point'][0]+host['normal'][0]*host['finish']['thickness_m']
            ax.axvline(face,c='#b88800',label='Finished wall')
        else:
            edge=min(p[1] for f in host['source_faces'] for p in f)
            ax.axvline(edge,c='#b88800',label='Wall end')
            ax.axvline(edge+.005,c='#777777',ls='--',label='5 mm design edge margin')
        if mid.endswith('-hose'):
            curve=meshes[mid]['hose_path']['points']
            ax.plot([p[0] for p in curve],[p[2] for p in curve],c='#206ba8',lw=1,label='Retained connections / hanging curve')
        from matplotlib.ticker import MaxNLocator
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.set_xlabel(('model x' if coordinates[0]==0 else 'model y')+' (metres)')
        ax.set_ylabel('model z (metres)'); ax.set_title(mid.replace('detail-gwc-','').replace('lamp-',''))
        ax.set_aspect('equal',adjustable='datalim'); ax.legend(fontsize=7)
    fig.suptitle('C4 first guest fix - measured diagnostic; product back plate unverified; photoreal review pending')
    fig.tight_layout();fig.savefig(folder/'guest-fixes-preview.png',dpi=140);plt.close(fig)
    members=[m for m in scene['meshes'] if m.get('mounting_package')=='d-ceiling']
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,prefix in zip(axes,('fix-DL-lounge-01','batten-mount-STORE-BATTEN-store-ramp-02-1')):
        mesh=next(m for m in members if m['id']==prefix)
        host=scene['mounting_hosts'][mesh['mounting']['host_id']]
        for f in mesh['faces']:
            ax.plot([p[0] for p in f+[f[0]]],[p[2] for p in f+[f[0]]],c='#206ba8',lw=.7)
        for f in host['source_faces']:
            ax.plot([p[0] for p in f+[f[0]]],[p[2] for p in f+[f[0]]],c='#b88800',lw=.7)
        ps=points(mesh); cx=sum(p[0] for p in ps)/len(ps);cz=max(p[2] for p in ps)
        ax.set_xlim(cx-.08,cx+.08);ax.set_ylim(cz-.1,cz+.04)
        ax.set_aspect('equal');ax.set_title(prefix,fontsize=9)
        ax.set_xlabel('model x (metres)');ax.set_ylabel('model z (metres)')
    fig.suptitle('Ceiling package diagnostic: void is a construction REQUIREMENT, not verified-as-built; sloping batten fixing')
    fig.tight_layout();fig.savefig(folder/'ceiling-preview.png',dpi=140);plt.close(fig)


def lead_preview(scene,clearance,folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from archpipe.concept.mounting_clearances import measured_items
    from archpipe.concept import villa_furnish as F
    from archpipe.concept.fitting_mounting import bounds
    items=measured_items(scene,R.design('D1'))
    old=json.loads((ROOT/'tests/fixtures/c4-lead-before.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    for ax,room in zip(axes,('guest-wc','family-bath')):
        for it in items:
            if it['room']!=room or it.get('mounting_obstacle'): continue
            bb=F.footprint(it)
            ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fill=False,edgecolor='#206ba8'))
            ax.text(it['cx'],it['cy'],it['id'],ha='center',fontsize=8)
            if it['type'].startswith('washbasin'):
                zone=(bb[2],it['cy']-.35,1.1,.7)
                ax.add_patch(Rectangle(zone[:2],zone[2],zone[3],facecolor='#e5ab44',alpha=.3))
        if room=='guest-wc':
            for mesh in old['meshes']:
                bb=bounds(mesh);ax.add_patch(Rectangle(bb[:2],bb[3]-bb[0],bb[4]-bb[1],fill=False,ls='--',edgecolor='#ba2929'))
            bb=bounds(next(m for m in scene['meshes'] if m['id']=='detail-gwc-linear-drain'))
            ax.add_patch(Rectangle(bb[:2],bb[3]-bb[0],bb[4]-bb[1],color='#555555'))
        rr=R.design('D1')['rooms'][room]['rect']
        ax.set_xlim(rr[0]-.1,rr[2]+.1);ax.set_ylim(rr[1]-.1,rr[3]+.1)
        ax.set_aspect('equal');ax.set_title(room+(' — applied wet floor/drain; red dashed before' if room=='guest-wc' else ' — unchanged; orange basin approach blocked'))
        ax.set_xlabel('Model x, metres (street to garden)');ax.set_ylabel('Model y, metres (toward plot east)')
    fig.suptitle('C4 lead decisions: diagnostic geometry checkpoint; no presentation/native integration')
    fig.tight_layout();fig.savefig(folder/'lead-decisions-preview.png',dpi=140);plt.close(fig)


def main():
    folder=ROOT/'out/c4-phase2d-lead';folder.mkdir(parents=True,exist_ok=True)
    scene=VR.build()
    frozen=json.loads((ROOT/'tests/fixtures/c4-lead-before.json').read_text())
    from archpipe.concept.fitting_mounting import bounds, points
    import math
    meshes={m['id']:m for m in scene['meshes']}
    wet_moves=[]
    for before in frozen['meshes']:
        after=meshes[before['id']]
        wet_moves.append(dict(id=before['id'],package='lead-wet-floor',host_id='guest finished east wall',
            old=bounds(before),new=bounds(after),mm=round(max(math.dist(a,b) for a,b in zip(points(before),points(after)))*1000,6),
            why='Lead 23 mm translation: retain finished 800 mm wet depth and drain containment',
            approval='APPROVED lead 2026-10-05; APPLIED'))
    schedule(folder,'wet-floor-drain-movements.csv',wet_moves)
    from archpipe.villa_render_contract import validate_scene
    schema_errors=validate_scene(scene)
    if schema_errors:
        raise ValueError('Candidate scene contract invalid: '+'; '.join(schema_errors))
    clearance=review(scene)
    from archpipe.concept.ceiling_requirements import write_table
    write_table(scene['ceiling_requirements'],ROOT/'docs/requirements/ceiling-void.md')
    from archpipe.concept import revit_spec as RS
    authored_spec=RS.build(R.design('D1'))
    authored_spec['ceiling_void_requirements']=scene['ceiling_requirements']
    (folder/'revit-spec-requirements.json').write_text(json.dumps(authored_spec,indent=2),encoding='utf-8')
    failures=scene_findings(scene)
    proposed=deepcopy(scene);meshes={m['id']:m for m in proposed['meshes']}
    pending=[r for r in scene['mounting_movements'] if r['approval']=='PENDING']
    for row in pending:
        meshes[row['id']]['faces']=row['proposed_faces']
        meshes[row['id']]['mounting'].pop('approval',None)
    ids={'detail-gwc-hand-shower-head','detail-gwc-hand-shower-hose','lamp-SCONCE-guest-wc-03'}
    fixed=dict(scene,meshes=[m for m in scene['meshes'] if m['id'] in ids or m.get('finished_host_id')])
    report=dict(status='CHECKPOINT; incomplete; uncommitted',approvals_applied=scene['lead_approved_count'],
        clearance_results=clearance,guest_fixes=scene['guest_fix_evidence'],guest_guard_findings=scene_findings(fixed),
        ceiling_component_count=sum(m.get('mounting_package')=='d-ceiling' for m in scene['meshes']),
        ceiling_existing_bc_components=scene['ceiling_existing_bc'],ceiling_unresolved=scene['ceiling_unresolved'],
        deferred_joinery_lights=scene['ceiling_deferred_joinery'],pending_movement_count=len(pending),
        ceiling_requirements=scene['ceiling_requirements'],
        remaining_missing_host_count=sum('MISSING mounting host' in f for f in failures),
        whole_scene_findings=failures,proposed_scene_findings=scene_findings(proposed),
        presentation_integration='PENDING neutral-light photoreal review; no native rebuild/deployment',
        lighting_remeasurement='PENDING analytical and rendered probes after approved fitting/emitter movements')
    for name,data in (('working-scene.json',scene),('proposed-scene.json',proposed),('mounting-report.json',report),('clearance-results.json',clearance)):
        (folder/name).write_text(json.dumps(data,indent=2 if 'scene' not in name else None),encoding='utf-8')
    schedule(folder,'movements-awaiting-approval.csv',pending)
    schedule(folder,'movements-applied.csv',[r for r in scene['mounting_movements'] if r['approval']!='PENDING'])
    with (folder/'clearance-results.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(clearance['rows'][0]));writer.writeheader();writer.writerows(clearance['rows'])
    preview(scene,folder)
    lead_preview(scene,clearance,folder)
    print(json.dumps({k:v for k,v in report.items() if k not in ('whole_scene_findings','proposed_scene_findings','clearance_results','ceiling_unresolved','ceiling_requirements')},indent=2))
    print('Clearance FAIL:',[(r['check'],r['achieved_mm'],r['required_mm']) for r in clearance['failures']])
    return int(bool(failures or clearance['failures'] or clearance['unresolved']))


if __name__=='__main__':
    raise SystemExit(main())
