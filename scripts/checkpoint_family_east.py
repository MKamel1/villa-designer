"""Family bathroom east-wall candidate; diagnostic output, no native writer."""
import csv
import json
from pathlib import Path
from unittest.mock import patch

from archpipe.concept import villa_render as VR, villa_r11 as R, villa_furnish as F, villa_furnish3d as F3, revit_spec as RS
from archpipe.concept.mounting_clearances import review, measured_items
from archpipe.concept.mounting import scene_findings
from archpipe.concept import render_support

OUT=Path('out/c4-family-east')


def preview(before,after,lay):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,2,figsize=(11,7))
    for ax,scene,title in zip(axes,(before,after),('Before: west WC','After: east WC')):
        items=[i for i in measured_items(scene,lay) if i['room']=='family-bath' and not i.get('mounting_obstacle')]
        rect=F.clear_rect(lay,'family-bath');rect=[rect[0]+.023,rect[1]+.023,rect[2]-.023,rect[3]-.023]
        ax.add_patch(Rectangle(rect[:2],rect[2]-rect[0],rect[3]-rect[1],fill=False,ec='black',lw=3))
        for item in items:
            box=F.footprint(item)
            ax.add_patch(Rectangle(box[:2],box[2]-box[0],box[3]-box[1],
                fc={'wc':'#88aacc','washbasin':'#aabb88','shower_walkin':'#bbddff'}[item['type']],ec='black'))
            ax.text(item['cx'],item['cy'],item['id'],ha='center',va='center',fontsize=9)
            if item['id']=='fb-basin':
                ax.add_patch(Rectangle((box[2],item['cy']-.35),1.1,.7,fill=False,ec='#557722',ls='--',label='Basin: 700 x 1100 mm'))
            if item['id']=='fb-wc' and scene is after:
                ax.add_patch(Rectangle((box[0]-1.1,item['cy']-.35),1.1,1.35,fill=False,ec='#2255aa',ls=':',label='WC front/side access zone'))
        ax.add_patch(Rectangle((9.952,-26.371),.8,.8,fill=False,ec='#cc6600',ls='--',label='Conservative door swing'))
        ax.set_xlim(9.15,11.55);ax.set_ylim(-26.5,-23.5);ax.set_aspect('equal');ax.set_title(title)
        ax.set_xlabel('model x (metres), west to east wall');ax.set_ylabel('model y (metres)');ax.legend(loc='upper center',fontsize=7)
    fig.suptitle('Family bathroom: diagnostic plan; services coordination pending')
    fig.tight_layout();fig.savefig(OUT/'preview.png',dpi=150);plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True);lay=R.design('D1')
    before_path=OUT/'before-scene.json'
    if before_path.exists():before=json.loads(before_path.read_text())
    else:
        with patch('archpipe.concept.sanitary_relocation.apply_family'):before=VR.build(views=[])
        before['provenance']='Reconstructed historical mounting input with east-wall relocation disabled'
        before_path.write_text(json.dumps(before))
    # Only the two bathroom views are needed in this reviewable candidate package.
    views=[v for v in VR.VIEWS(lay) if v['id'] in ('v15-family-bath','v35-family-bath-wc')]
    scene=VR.build(lay,views=views)
    report=review(scene,lay);rows=[r for r in report['rows'] if r['room']=='family-bath']
    moves=[r for r in scene['mounting_movements'] if r['package']=='client-sanitary-relocation' or r['id']=='host-face-bath-fb-wc-east']
    checks=dict(mounting=scene_findings(scene),unsupported=render_support.unsupported(scene),
        family_clearance_failures=[r for r in rows if r['status'] in ('FAIL','UNRESOLVED')])
    native=RS.build(lay);native['furniture']=F3.spec(lay)
    for name,data in [('scene',scene),('clearances',report),('movements',moves),('native-spec',native),('checks',checks),('views',views)]:
        (OUT/(name+'.json')).write_text(json.dumps(data,indent=2))
    with (OUT/'clearances.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    preview(before,scene,lay)
    print(json.dumps(dict(relocation=scene['family_wc_relocation'],checks=checks,views=[v['id'] for v in views]),indent=2))
    return int(any(checks.values()))


if __name__=='__main__':raise SystemExit(main())
