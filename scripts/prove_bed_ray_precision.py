"""Blender proof on the real evaluated shell, translated sibling and inside mutation."""
from pathlib import Path
import gzip,json,sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from archpipe.bed_containment import local_query_coordinates,unique_triangle_parity,RAY_DIRECTIONS,closed_shell_contains
case=json.loads(gzip.decompress((ROOT/'tests/fixtures/bed-round7-ray-duplicate.json.gz').read_bytes()))
triangles=np.asarray(case['triangles']);point=np.asarray(case['point_m'])
direction=np.asarray(RAY_DIRECTIONS[0]);direction/=np.linalg.norm(direction)
inside=point+direction*np.mean(case['diagnostics'][0]['ray_distances'][0])
records=[]
for name,travel in [('real-case',[0,0,0]),('renamed-translated-sibling',[1200,-2500,30])]:
 origin,points=local_query_coordinates((triangles+travel).reshape(-1,3));tree=BVHTree.FromPolygons(points.tolist(),[(3*i,3*i+1,3*i+2) for i in range(len(triangles))],all_triangles=True)
 for status,sample in [('outside',point),('inside-mutation',inside)]:
  votes=[];ray_faces=[]
  for d in RAY_DIRECTIONS:
   ray=Vector((sample+travel-origin).tolist());direction=Vector(d).normalized();hits=[]
   for _ in range(len(triangles)+1):
    location,normal,index,distance=tree.ray_cast(ray,direction)
    if location is None:break
    hits.append(index);ray=location+direction*.00001
   votes.append(unique_triangle_parity(hits));ray_faces.append(hits)
  expected=status=='inside-mutation'
  if votes!=[expected]*3:raise ValueError('precision proof failed '+str(votes))
  if closed_shell_contains(triangles+travel,sample+travel)!=expected:raise ValueError('independent proof disagrees')
  records.append(dict(case=name,status=status,votes=votes,face_hits=ray_faces,query_origin_m=origin.tolist(),passed=True))
output=ROOT/'out/beds/round7/ray-precision-proof.json';output.write_text(json.dumps(records,indent=2)+'\n');print('All four real/translated/outside/enclosed Blender proofs pass')
