"""Summarise out/wt/villa4 guards: failure runs by kind with phase/room/obstacles."""
import json,collections,sys
d=sys.argv[1] if len(sys.argv)>1 else 'out/wt/villa4'
g=json.load(open(d+'/assembly/guards.json'));F=json.load(open(d+'/path.json'))['frames']
print(g['summary'],'waived',sum('waived_wall_sightline' in r for r in g['frames']))
bad=[r for r in g['frames'] if r['failures']]
def runs(idx):
    out=[];s=prev=None
    for i in idx:
        if s is None:s=i
        elif i!=prev+1:out.append((s,prev));s=i
        prev=i
    return out+[(s,prev)] if s is not None else out
for kind in ('physical','camera faces','standing','crosses','lens','speed','yaw'):
    idx=[r['index'] for r in bad if any(kind in f for f in r['failures'])]
    if idx:
        print(kind,len(idx))
        for a,b in runs(idx)[:15]:
            c=collections.Counter(h for r in g['frames'][a:b+1] for h in r.get('swept_obstacles',[]))
            print('  ',a,b,F[a]['phase'],F[a]['room'],F[a]['station'],c.most_common(2))
