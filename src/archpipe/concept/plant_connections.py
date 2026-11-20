"""Read declared organ contact witnesses from actual closed plant faces.

A contact witness is a point in metres shared by a child organ's solid and
its supporting solid. Face indices identify rows of the same mesh. This is
an authored construction screen, not botanical likeness or a pixel-size rule.
A failed witness does not prove two solids have no other intersection. Mona
corollas deliberately use the stronger ASSUMED axial-seat construction.
"""
from __future__ import annotations

import numpy as np


def contains_contact(faces, contact, tolerance=1e-8):
    """Whether a point is inside or on a closed triangle shell.

    tolerance is a numerical distance in metres. Solid angles are summed in
    radians; an interior point subtends four times pi. Boundary triangles are
    checked first so a cap contact is not treated as an indeterminate ray hit.
    """
    triangles=np.asarray([[face[0],face[i],face[i+1]] for face in faces for i in range(1,len(face)-1)],dtype=float)
    if not len(triangles):return False
    point=np.asarray(contact,dtype=float)
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    ab,ac=b-a,c-a;normal=np.cross(ab,ac);length=np.linalg.norm(normal,axis=1)
    valid=length>1e-15
    if not valid.all():return False
    distance=np.sum((point-a)*normal,axis=1)/length
    projected=point-distance[:,None]*normal/length[:,None]
    ap=projected-a
    aa=np.sum(ab*ab,axis=1);bb=np.sum(ab*ac,axis=1);cc=np.sum(ac*ac,axis=1)
    d=np.sum(ap*ab,axis=1);e=np.sum(ap*ac,axis=1);den=aa*cc-bb*bb
    u=(cc*d-bb*e)/den;v=(aa*e-bb*d)/den
    # Barycentric tolerance is dimensionless; convert the distance tolerance
    # using each actual triangle's shortest edge.
    edge=np.minimum.reduce([np.linalg.norm(ab,axis=1),np.linalg.norm(ac,axis=1),np.linalg.norm(c-b,axis=1)])
    slack=tolerance/np.maximum(edge,1e-15)
    if np.any((abs(distance)<=tolerance)&(u>=-slack)&(v>=-slack)&(u+v<=1+slack)):return True
    vectors=triangles-point
    x,y,z=vectors[:,0],vectors[:,1],vectors[:,2]
    lx,ly,lz=[np.linalg.norm(vectors[:,i],axis=1) for i in range(3)]
    numerator=np.sum(x*np.cross(y,z),axis=1)
    denominator=lx*ly*lz+np.sum(x*y,axis=1)*lz+np.sum(y*z,axis=1)*lx+np.sum(z*x,axis=1)*ly
    return abs(float(np.sum(2*np.arctan2(numerator,denominator))))>2*np.pi


def organ_connection_findings(meshes):
    """Fail closed on missing coverage, open organs or detached actual faces.

    Every declared leaf/flower face must belong to an attachment record. Each
    witness is independently tested against both its child and parent faces;
    moving geometry while keeping a plausible record therefore still refuses.
    """
    from .physical_part import geometry_errors
    findings=[]
    for mesh in meshes:
        faces=mesh.get('faces',[]);records=mesh.get('organ_connections',[])
        expected=set(mesh.get('leaf_face_indices',[]))|set(mesh.get('flower_face_indices',[]))
        covered=set()
        if not records:
            if expected or mesh.get('part_kind') in ('plant-clump','climber'):
                findings.append((mesh['id'],'missing physical organ attachment records'))
            continue
        for number,record in enumerate(records):
            child=record.get('child_face_indices',[]);parent=record.get('parent_face_indices',[]);contact=record.get('contact_m',[])
            if (not child or not parent or set(child).intersection(parent) or len(contact)!=3 or
                    any(not isinstance(i,int) or i<0 or i>=len(faces) for i in child+parent)):
                findings.append((mesh['id'],'invalid organ attachment record %d'%number));continue
            covered.update(child)
            child_faces=[faces[i] for i in child];parent_faces=[faces[i] for i in parent]
            if geometry_errors(child_faces) or geometry_errors(parent_faces):
                findings.append((mesh['id'],'organ attachment %d has an open or invalid solid'%number));continue
            if not contains_contact(child_faces,contact) or not contains_contact(parent_faces,contact):
                findings.append((mesh['id'],'organ attachment %d contact witness is outside organ or support'%number))
        if expected-covered:findings.append((mesh['id'],'leaf or flower faces lack physical attachment coverage'))
    return findings
