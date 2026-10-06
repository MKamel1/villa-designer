"""Retained C4(e) lead review follow-through; no presentation integration."""
from copy import deepcopy
from checkpoint_mounting_e import main


def preview(scene, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from archpipe.concept.fitting_mounting import bounds
    rows={r['id']:r for r in scene['mounting_movements']}
    meshes={m['id']:m for m in scene['meshes']}
    ids=['landscape-trellis-'+d for d in ('east','south','north','west')]
    ids+=['detail-vent-'+r+'-grille' for r in ('guest-wc','dirty-kitchen')]
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    for ax,mid in zip(axes.flat,ids):
        mesh=meshes[mid];row=rows[mid];record=scene['mounting_hosts'][mesh['mounting']['host_id']]
        outward=record['normal'];axis=0 if abs(outward[0])>.5 else 1;other=1-axis
        before=bounds(mesh);after=row['new'];centre=(before[other]+before[other+3])/2
        for bb,color,label in ((before,'#286fa8','Retained authored geometry'),(after,'#008345','Unapproved revised proposal')):
            ax.add_patch(Polygon([(bb[0],bb[1]),(bb[3],bb[1]),(bb[3],bb[4]),(bb[0],bb[4])],fill=False,edgecolor=color,label=label))
        for face in record['source_faces']:
            ax.plot([p[0] for p in face[:2]],[p[1] for p in face[:2]],c='#b88800',label='Finite structural support face')
        if axis==0:
            ax.set_xlim(min(before[0],after[0])-.08,max(before[3],after[3])+.08);ax.set_ylim(min(before[1],after[1])-.08,max(before[4],after[4])+.08)
        else:
            ax.set_ylim(min(before[1],after[1])-.08,max(before[4],after[4])+.08);ax.set_xlim(min(before[0],after[0])-.08,max(before[3],after[3])+.08)
        ax.set_title(mid+'\n'+str(row['mm'])+' mm; '+('no modeled wall solid' if record.get('wall_thickness_m','exists') is None else 'modeled wall face'),fontsize=9)
        ax.set_xlabel('model x (metres)');ax.set_ylabel('model y (metres)');ax.legend(fontsize=7)
    fig.suptitle('C4 lead-review first fix: finite yard hosts and outdoor grille faces; proposals remain unapproved')
    fig.tight_layout();fig.savefig(folder/'exterior-first-fix-preview.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(16,6))
    ids=['appliance-coffee-main-body','appliance-coffee-dirty-body','detail-headboard-slats','appliance-hood-dirty-canopy']
    for ax,mid in zip(axes,ids):
        root=meshes[mid];host=scene['mounting_hosts'][root['mounting']['host_id']]
        members=[root]+[m for m in scene['meshes'] if m.get('associated_mounting_root')==mid]
        for m in members:
            ps=[p for f in m['faces'] for p in f]
            ax.scatter([p[0] for p in ps],[p[2] for p in ps],s=2,c='#286fa8')
        if mid.startswith('appliance-coffee-'):
            ax.axhline(host['structural_point'][2],c='#b88800',label='Modeled worktop top')
            ax.set_title(mid+'\nRigid tray penetrates worktop 12 mm',fontsize=8)
        else:
            patches=[f for m in scene['meshes'] if m.get('finished_host_id')==host['id'] for f in m['faces']]
            for f in patches:
                ps=f+[f[0]];ax.plot([p[0] for p in ps],[p[2] for p in ps],c='#b88800',lw=.6)
            ax.set_title(mid+'\n'+('47 mm beyond real wall edge' if 'headboard' in mid else 'Actual coplanar supporting wall'),fontsize=8)
            if 'hood-' in mid:
                ps=[p for m in members for f in m['faces'] for p in f]
                ax.set_xlim(min(p[0] for p in ps)-.2,max(p[0] for p in ps)+.2)
                ax.set_ylim(min(p[2] for p in ps)-.2,max(p[2] for p in ps)+.2)
        ax.set_xlabel('model x (metres)');ax.set_ylabel('model z (metres)')
    fig.suptitle('Approved candidate assemblies: support conflicts retained for lead review; no presentation integration')
    fig.tight_layout();fig.savefig(folder/'approved-assemblies-preview.png',dpi=140);plt.close(fig)


if __name__=='__main__':raise SystemExit(main('c4-phase2f',preview))
