"""Resolve the still-render set to camera yaws (the best view of each room) for the tour."""
import json, math, time
import sys; from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/"src")]
from archpipe.concept import villa_r11 as R, villa_render as V
from archpipe.critic import render_set as RS
t=time.time()
lay=R.design('D1'); data=RS.load()
base=V.VIEWS(lay) if callable(getattr(V,'VIEWS',None)) else V.VIEWS
views=RS.resolve(data,lay,base)
print(len(views), time.time()-t)
out={}
for e,v in zip(data['views'],views):
    if e.get('garden'): continue
    c=v['camera']; p,tg=c['position'],c['target']
    yaw=math.degrees(math.atan2(tg[1]-p[1],tg[0]-p[0]))
    out[e['id']]=dict(pos=p[:2],yaw=round(yaw,1),covers=e['covers'],lens=c['lens_mm'])
json.dump(out,open('/home/omar/archpipe/lanes/WT/knowledge/flythrough/tour-stills.json','w'),indent=1)

