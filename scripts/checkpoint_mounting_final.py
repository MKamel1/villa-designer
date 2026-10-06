"""Final C4 candidate checkpoint and neutral geometric previews."""
import json
from checkpoint_mounting_e import main, ROOT, geometry_diff


def preview(scene, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from archpipe.concept.fitting_mounting import bounds
    before = json.loads((ROOT/'out/c4-phase2f/working-scene.json').read_text())
    old = {m['id']:m for m in before['meshes']}
    new = {m['id']:m for m in scene['meshes']}
    ids = ['landscape-trellis-'+d for d in ('east','west','north','south')]
    ids += ['detail-vent-'+r+'-grille' for r in ('guest-wc','dirty-kitchen')]
    fig, axes = plt.subplots(2,3,figsize=(15,9))
    for ax,mid in zip(axes.flat,ids):
        for meshes,color,label in ((old,'#286fa8','Before'),(new,'#008345','Approved after')):
            bb=bounds(meshes[mid]);ax.add_patch(Rectangle(bb[:2],bb[3]-bb[0],bb[4]-bb[1],fill=False,ec=color,label=label))
        host=scene['mounting_hosts'][new[mid]['mounting']['host_id']]
        for face in host['source_faces']:
            ax.plot([p[0] for p in face[:2]],[p[1] for p in face[:2]],c='#b88800')
        boxes=[bounds(old[mid]),bounds(new[mid])]
        ax.set_xlim(min(b[0] for b in boxes)-.08,max(b[3] for b in boxes)+.08)
        ax.set_ylim(min(b[1] for b in boxes)-.08,max(b[4] for b in boxes)+.08)
        ax.set_title(mid+('\nDeclared edge; wall solid unverified' if host.get('wall_thickness_m','exists') is None else ''),fontsize=9)
        ax.set_xlabel('model x (metres)');ax.set_ylabel('model y (metres)');ax.legend(fontsize=7)
    fig.suptitle('Approved exterior candidate: blue before, green applied; gold actual fixing face')
    fig.tight_layout();fig.savefig(folder/'approved-exterior-preview.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,6))
    for ax,mid in zip(axes,['detail-headboard-slats','appliance-coffee-main-body','appliance-coffee-dirty-body']):
        for meshes,color,label in ((old,'#286fa8','Before'),(new,'#008345','After')):
            members=[meshes[mid]]+[m for m in meshes.values() if m.get('associated_mounting_root')==mid]
            for member in members:
                for face in member['faces']:
                    ps=face+[face[0]];ax.plot([p[0] for p in ps],[p[2] for p in ps],c=color,lw=.4)
            ax.plot([],[],c=color,label=label)
        host=scene['mounting_hosts'][new[mid]['mounting']['host_id']]
        if 'coffee' in mid:
            ax.axhline(host['structural_point'][2],c='#b88800',label='Worktop top')
            ax.set_ylim(host['structural_point'][2]-.025,host['structural_point'][2]+.3)
        else:
            b=scene['c4_final']['headboard']['wall_span']
            ax.axvline(b[0],c='#b88800',label='Wall end')
            ax.axvline(scene['c4_final']['headboard']['centre_x_m'],c='grey',ls='--',label='Unchanged bed centre')
        ax.set_title(mid,fontsize=9);ax.set_xlabel('model x (metres)');ax.set_ylabel('model z (metres)');ax.legend()
    fig.suptitle('Final C4 candidate: symmetric headboard trim and complete coffee assembly seating')
    fig.tight_layout();fig.savefig(folder/'assembly-first-fix-preview.png',dpi=140);plt.close(fig)
    (folder/'final-decisions.json').write_text(json.dumps(scene['c4_final'],indent=2))
    (folder/'geometry-diff-from-f.json').write_text(json.dumps(geometry_diff(scene,before),indent=2))
    from checkpoint_mounting_d import schedule
    rows=[]
    for assembly in scene['c4_final']['coffee']:
        for record in assembly['members']:
            rows.append(dict(id=record['id'],package='final-assembly-seating',
                host_id=new[assembly['root_id']]['mounting']['host_id'],
                old=bounds(dict(faces=record['old_faces'])),new=bounds(dict(faces=record['new_faces'])),
                mm=12.0,why=assembly['fixing_basis'],approval='APPROVED final lead; APPLIED'))
    schedule(folder,'final-assembly-movements.csv',rows)


if __name__=='__main__': raise SystemExit(main('c4-final',preview))
