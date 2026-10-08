"""Remove duplicated volumes from overlapping axis-aligned mineral stones.

All coordinates are metres. Authored records remain immutable. Only stones
with identical vertical datums, surface materials and substrate are fused.
The rendered solid occupies exactly the union of their authored boxes.
"""
from copy import deepcopy


def bounds(mesh):
    points=[p for face in mesh['faces'] for p in face]
    return tuple(min(p[k] for p in points) for k in range(3))+tuple(max(p[k] for p in points) for k in range(3))


def stone_box(mesh):
    if mesh.get('part_kind')!='stepping-stone':return None
    b=bounds(mesh)
    corners={(x,y,z) for x in (b[0],b[3]) for y in (b[1],b[4]) for z in (b[2],b[5])}
    if len(mesh['faces'])!=6 or any(tuple(p) not in corners for f in mesh['faces'] for p in f):return None
    slots=mesh.get('face_materials',[mesh['material']]*6)
    bottom=next(slots[i] for i,f in enumerate(mesh['faces']) if all(p[2]==b[2] for p in f))
    if any(slots[i]!=mesh['material'] for i,f in enumerate(mesh['faces']) if not all(p[2]==b[2] for p in f)):return None
    return b,bottom


def overlaps(a,b):
    return min(a[3],b[3])>max(a[0],b[0]) and min(a[4],b[4])>max(a[1],b[1])


def overlap_findings(meshes):
    stones=[(m,stone_box(m)) for m in meshes if stone_box(m)]
    return [(a['id'],b['id']) for i,(a,(ab,_)) in enumerate(stones) for b,(bb,_) in stones[i+1:]
            if ab[2]==bb[2] and ab[5]==bb[5] and overlaps(ab,bb)]


def prepare(meshes):
    """Partition a box union into closed exterior faces; alias each source id.

    A shared x/y grid avoids both coincident faces and T-junctions. Internal
    vertical faces are omitted. Every top/bottom cell is emitted once.
    Non-box stones and isolated stones retain their original records.
    """
    boxes={i:stone_box(m) for i,m in enumerate(meshes)};pending={i for i,b in boxes.items() if b};groups=[]
    while pending:
        first=min(pending);pending.remove(first);group=[first];front=[first]
        while front:
            i=front.pop();a,bottom=boxes[i]
            linked=[j for j in sorted(pending) if meshes[i]['material']==meshes[j]['material'] and bottom==boxes[j][1]
                    and a[2]==boxes[j][0][2] and a[5]==boxes[j][0][5] and overlaps(a,boxes[j][0])]
            for j in linked:pending.remove(j);group.append(j);front.append(j)
        if len(group)>1:groups.append(sorted(group))
    replacements={};retired=set();aliases={}
    for group in groups:
        source=[meshes[i] for i in group];bs=[boxes[i][0] for i in group];z0,z1=bs[0][2],bs[0][5]
        xs=sorted({b[k] for b in bs for k in (0,3)});ys=sorted({b[k] for b in bs for k in (1,4)})
        cells={(i,j) for i in range(len(xs)-1) for j in range(len(ys)-1)
               if any(b[0]<(xs[i]+xs[i+1])/2<b[3] and b[1]<(ys[j]+ys[j+1])/2<b[4] for b in bs)}
        faces=[];slots=[];top=source[0]['material'];bottom=boxes[group[0]][1]
        for i,j in sorted(cells):
            x0,x1=xs[i:i+2];y0,y1=ys[j:j+2]
            faces.extend([[[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[x1,y0,z0]],
                          [[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]]]);slots.extend([bottom,top])
            boundaries=[((i,j-1),[[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1]]),
                        ((i+1,j),[[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[x1,y0,z1]]),
                        ((i,j+1),[[x1,y1,z0],[x0,y1,z0],[x0,y1,z1],[x1,y1,z1]]),
                        ((i-1,j),[[x0,y1,z0],[x0,y0,z0],[x0,y0,z1],[x0,y1,z1]])]
            for neighbour,face in boundaries:
                if neighbour not in cells:faces.append(face);slots.append(top)
        fused=deepcopy(source[0]);fused.update(faces=faces,face_materials=slots,fused_source_ids=[m['id'] for m in source])
        replacements[group[0]]=fused;retired.update(group[1:])
        aliases.update({m['id']:fused['id'] for m in source})
    return [replacements.get(i,m) for i,m in enumerate(meshes) if i not in retired],aliases
