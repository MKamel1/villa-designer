"""Compare content-bound evaluation drafts; missing or unequal inputs fail closed."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from archpipe.render_qa import check
from archpipe.villa_render_contract import presentation_view_ids
from villa_render import villa_qa_context

def image_metrics(first,second):
    a=np.asarray(first.convert('RGB'),dtype=float)/255
    b=np.asarray(second.convert('RGB'),dtype=float)/255
    if a.shape!=b.shape:raise ValueError('different image dimensions')
    def linear(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
    la,lb=linear(a),linear(b)
    ya,yb=la@np.array([.2126,.7152,.0722]),lb@np.array([.2126,.7152,.0722])
    matrix=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])
    xa,xb=la@matrix.T,lb@matrix.T
    sa,sb=xa.sum(-1),xb.sum(-1);valid=(sa>1e-6)&(sb>1e-6)
    chroma=np.abs(xa[valid,:2]/sa[valid,None]-xb[valid,:2]/sb[valid,None])
    error=np.abs(a-b)
    def qa_values(v):
        lum=v@np.array([.2126,.7152,.0722]);mids=v[(lum>.25)&(lum<.75)]
        cast=None if not len(mids) else float(np.std(mids.mean(0)))
        return dict(clipped_fraction=float(np.mean(v.max(-1)>=.995)),median_luminance=float(np.median(lum)),midtone_cast=cast)

    return dict(qa_values_45=qa_values(a),qa_values_52=qa_values(b),display_rgb_mae=float(error.mean()),display_rgb_absolute_error_p95=float(np.percentile(error,95)),
        linear_luminance=dict(before_mean=float(ya.mean()),after_mean=float(yb.mean()),mean_delta=float((yb-ya).mean()),
          absolute_difference_p50_p95_p99=[float(x) for x in np.percentile(np.abs(yb-ya),[50,95,99])],
          before_p5_p50_p95=[float(x) for x in np.percentile(ya,[5,50,95])],after_p5_p50_p95=[float(x) for x in np.percentile(yb,[5,50,95])]),
        chromaticity=dict(mean_absolute_xy_difference=chroma.mean(0).tolist() if len(chroma) else None,absolute_xy_difference_p95=np.percentile(chroma,95,axis=0).tolist() if len(chroma) else None,valid_pixels=int(valid.sum())))

def compare(scene,view,a,b,out):
    ident=view['id'];ra=json.loads((a/(ident+'.json')).read_text());rb=json.loads((b/(ident+'.json')).read_text())
    keys=['samples','resolution','exposure_stops','white_balance_applied','max_bounces','clamp_indirect']
    differences=[k for k in keys if ra.get(k)!=rb.get(k)]
    if ra['scene_receipt']['authored_scene_sha256']!=rb['scene_receipt']['authored_scene_sha256']:differences.append('authored_scene_sha256')
    ia,ib=Image.open(a/(ident+'.png')),Image.open(b/(ident+'.png'))
    qa=[]
    for folder,report in [(a,ra),(b,rb)]:
        q=check(folder/(ident+'.png'),villa_qa_context(scene,view,report));qa.append(q)
        (out/(ident+('-45' if folder==a else '-52')+'.qa.json')).write_text(json.dumps(q,indent=2))
    delta=ImageChops.difference(ia.convert('RGB'),ib.convert('RGB'));delta.point(lambda x:min(255,x*4)).save(out/(ident+'-difference-x4.png'))
    tile=Image.new('RGB',(960,350),'white');pen=ImageDraw.Draw(tile)
    for i,(im,label) in enumerate([(ia,'4.5.14'),(ib,'5.2.2'),(delta.point(lambda x:min(255,x*4)),'absolute difference x4')]):
        im=im.convert('RGB');im.thumbnail((320,300));tile.paste(im,(i*320,30));pen.text((i*320+5,8),label,fill='black')
    pen.text((5,325),ident,fill='black');tile.save(out/(ident+'-comparison.jpg'))
    return dict(view=ident,identical_settings=not differences,settings_differences=differences,
                render_seconds_45=ra['render_seconds'],render_seconds_52=rb['render_seconds'],
                qa_45=qa[0],qa_52=qa[1],metrics=image_metrics(ia,ib),
                evaluated_geometry_equal=ra['scene_receipt']['evaluated_meshes_sha256']==rb['scene_receipt']['evaluated_meshes_sha256'],
                exposures=[ra['exposure_stops'],rb['exposure_stops']])

def main():
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True)
    p.add_argument('--scene',type=Path,default=ROOT/'out/blender52/scene.json');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);s=json.loads(a.scene.read_text());by={v['id']:v for v in s['views']};rows=[];missing=[]
    for ident in presentation_view_ids(by):
        if not all((f/(ident+suffix)).exists() for f in [a.before,a.after] for suffix in ['.png','.json']):missing.append(ident);continue
        rows.append(compare(s,by[ident],a.before,a.after,a.out))
    result=dict(complete=not missing,expected_views=len(presentation_view_ids(by)),missing=missing,views=rows)
    (a.out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    if rows:
        sheet=Image.new('RGB',(960,350*len(rows)),'white')
        for i,row in enumerate(rows):sheet.paste(Image.open(a.out/(row['view']+'-comparison.jpg')),(0,i*350))
        sheet.save(a.out/'contact-sheet.jpg')
    print(json.dumps(dict(complete=not missing,compared=len(rows),missing=missing)))
    return 0 if not missing and all(r['identical_settings'] for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
