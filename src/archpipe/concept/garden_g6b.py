"""Species forms and warm contemporary outdoor stand-ins for G6b.

Coordinates and dimensions are metres. Angles are radians. Leaves are
closed folded laminae, with per-leaf face records for independent read-back.
Botanical sources and ASSUMED dimensions live in the sole garden palette.
"""
from math import sin, cos, pi
import numpy as np
from .garden_g6 import tube, _tri


def lamina(center, length, width, angle, tilt, *, obovate=False):
    """Closed leaf with pointed ends and a raised midrib; full length/width."""
    center=np.array(center);along=np.array([cos(angle)*cos(tilt),sin(angle)*cos(tilt),sin(tilt)])
    across=np.array([-sin(angle),cos(angle),0.]);normal=np.cross(along,across)
    ring=[]
    for index in range(12):
        phase=index*2*pi/12
        breadth=width/2*sin(phase)*(1+.25*cos(phase) if obovate else 1)
        ring.append(center+along*length/2*cos(phase)+across*breadth)
    top=center+normal*width*.09;bottom=center-normal*.0015
    return [[top.tolist(),ring[index].tolist(),ring[(index+1)%12].tolist()] for index in range(12)]+[[bottom.tolist(),ring[(index+1)%12].tolist(),ring[index].tolist()] for index in range(12)]


class Growth:
    """Accumulate closed connected stems, leaves and flowers with material slots."""
    def __init__(self, foliage):
        self.faces=[];self.materials=[];self.leaves=[];self.flowers=[];self.records=[];self.foliage=foliage
    def add(self, faces, material):
        indices=list(range(len(self.faces),len(self.faces)+len(faces)))
        self.faces+=faces;self.materials += [material]*len(faces)
        return indices
    def stem(self, start, end, radius=.003):
        if np.linalg.norm(np.array(end)-start)>1e-9:self.add(tube(start,end,radius,count=6),'trellis')
    def blade(self, center, length, width, angle, tilt, *, obovate=False, veined=False):
        indices=self.add(lamina(center,length,width,angle,tilt,obovate=obovate),self.foliage)
        self.leaves+=indices;self.records.append(dict(face_indices=indices,length_m=length,width_m=width))
        if veined:
            c=np.array(center);u=np.array([cos(angle)*cos(tilt),sin(angle)*cos(tilt),sin(tilt)]);v=np.array([-sin(angle),cos(angle),0.]);n=np.cross(u,v)
            ridge=c+n*width*.091
            self.add(tube(ridge-u*length*.44,ridge+u*length*.44,.0013,count=6),'g6-leaf-vein')
            for side in (-1,1):
                for t in (-.3,-.1,.1,.3):
                    a=ridge+u*length*t
                    b=c+u*length*(t+.08)+v*side*width*.34+n*width*.025
                    self.add(tube(a,b,.00065,count=6),'g6-leaf-vein')
    def star(self, center, diameter, material):
        for k in range(5):
            angle=k*2*pi/5
            p=np.array(center)+np.array([cos(angle),sin(angle),0])*diameter*.25
            self.flowers+=self.add(lamina(p,diameter*.55,diameter*.18,angle,.15),material)
    def fields(self):
        return dict(face_materials=self.materials,leaf_face_indices=self.leaves,
                    flower_face_indices=self.flowers,leaf_records=self.records,explicit_geometry=True)


def mound(dense=True):
    """Low branching rounded crown with continuously distributed tip whorls.

    A fixed random seed makes the crown reproducible without stacking tips
    on horizontal rings. Radius tapers to the apex of a half ellipsoid.
    """
    growth=Growth('g6-pittosporum-leaf');growth.stem([0,0,0],[0,0,.14],.018)
    rng=np.random.default_rng(6062)
    for tip in range(210):
        z=.045+.54*(tip+rng.uniform(.1,.9))/210
        angle=tip*pi*(3-5**.5)+rng.uniform(-.18,.18)
        radius=.265*np.sqrt(max(.02,1-((z-.045)/.56)**2))*rng.uniform(.88,1.)
        node=np.array([radius*cos(angle),radius*sin(angle),z])
        fork=node*np.array([.65,.65,.60]);fork[2]+=.035
        growth.stem([0,0,.09],fork,.0035)
        growth.stem(fork,node,.0025)
        for k in range(5):
            a=angle+k*2*pi/5+rng.uniform(-.2,.2)
            p=node+np.array([.025*cos(a),.025*sin(a),rng.uniform(-.015,.015)])
            growth.stem(node,p,.0014)
            growth.blade(p,rng.uniform(.062,.078),.033,a,rng.uniform(-.25,.85),obovate=True)
    growth.materials=['g6-shrub-wood' if material=='trellis' else material for material in growth.materials]
    return growth


def vines(assumptions,posts,ground, botanical):
    """Rooted twining stems, rafter-trained shoots, hanging Petrea racemes."""
    from .garden_g6 import _mesh
    x0,y0,x1,y1=assumptions['pergola_rect_m'];roof=ground+2.85;out=[]
    for index,species in enumerate(('Petrea volubilis','Trachelospermum jasminoides')):
        record=botanical[species]['render_form'];length,width=record['leaf_length_m']['value'],record['leaf_width_m']['value']
        growth=Growth('g6-petrea-leaf' if index==0 else 'g6-jasmine-leaf')
        root=np.array([*posts[index],ground]);previous=root+[0,0,.03];growth.stem(root,previous,.009)
        for k in range(1,121):
            phase=k*2*pi/18;z=ground+.03+k*2.82/120;radius=min(.092,k*.015)
            p=np.array([root[0]+radius*cos(phase),root[1]+radius*sin(phase),z]);growth.stem(previous,p,.009);previous=p
            if k%3==0:
                angle=phase;node=p+np.array([.035*cos(angle),.035*sin(angle),.014])
                # The final post leaf must still fit the recorded 2.95 m
                # vine height; its raised blade extends above the petiole.
                node[2]=min(node[2],roof-.04)
                growth.stem(p,node,.003)
                growth.blade(node,length,width,angle,1.15+.15*sin(k))
        crown=previous
        # Each species occupies its half of the canopy; varying leaf tilt
        # and shoot height avoids a coplanar slab. Timber remains visible.
        left=x0+.12+index*1.5;right=x0+1.5+index*1.5-.12
        spacing=.122 if index==0 else .055
        xs=np.linspace(left,right,round((right-left)/spacing)+1)
        ys=np.linspace(y0+.12,y1-.12,round((y1-y0-.24)/spacing)+1)
        for row,y in enumerate(ys):
            start=np.array([root[0],y,roof-.024]);growth.stem(crown,start,.005)
            end=np.array([right,y,roof-.024]);growth.stem(start,end,.004)
            for col,x in enumerate(xs):
                angle=.75*sin(col*2.3+row*1.7)
                node=np.array([x+.013*sin(row*4+col),y+.013*cos(col*4+row),roof+.025*sin(col+row*2)])
                growth.stem([node[0],y,roof-.024],node,.0017)
                growth.blade(node,length*(1+.07*sin(col+row)),width,angle,.18+.35*sin(row+col*3))
                if index==0 and row%4==1 and col%3==1:
                    # 0.30 m raceme, 16 star calyces. A vertical stalk
                    # hangs below the rafters rather than dots above them.
                    top=node+np.array([0,0,-.32]);growth.stem(node,top,.002)
                    end=top+np.array([.018,.012,-.30]);growth.stem(top,end,.002)
                    for k in range(16):
                        phase=k*2.4;p=top+np.array([.025*cos(phase),.025*sin(phase),-.015-k*.018])
                        growth.stem(top+np.array([0,0,-.015-k*.018]),p,.001)
                        growth.star(p,.041,'g6-lavender-flower')
                elif index==1 and (col*7+row*3)%113==0:
                    growth.star(node,.021,'g6-white-flower')
        mesh=_mesh('g6-'+('petrea' if index==0 else 'jasmine')+'-roof','garden-foliage',growth.faces,'climber','climber',
             'ASSUMED rafter-trained twining vine; species-sized folded leaves; seasonal flower display, not year-round nursery proof',
             species=species,center=root[:2].tolist(),root_z_m=ground,bed='south-pergola',planting_layer='accent',spread_m=3.,appearance_key='procedural-pergola',post_index=index,**growth.fields())
        out.append(mesh)
    return out


def espalier(x0,x1,wall,ground,height,spacing,botanical):
    """Dense terminal rosettes along fixed horizontal tiers; physical wire ties."""
    growth=Growth('g6-loquat-leaf');root=np.array([(x0+x1)/2,wall-.20,ground]);growth.stem(root,root+[0,0,height],.035)
    length=botanical['render_form']['leaf_length_m']['value'];width=botanical['render_form']['leaf_width_m']['value']
    tiers=[];wires=[]
    for k in range(3):
        node=root+[(k-1)*.07,-.01,.13];growth.stem(root+[0,0,.10],node)
        growth.blade(node,length,width,k*.7,.55)
    for tier in range(1,int(height/spacing)+1):
        z=ground+tier*spacing;tiers.append(z);wires+=tube([x0,wall-.009,z],[x1,wall-.009,z],.009)
        growth.stem([x0+.13,root[1],z],[x1-.13,root[1],z],.014)
        for j in range(14):
            x=x0+.17+(x1-x0-.34)*j/13
            tip=np.array([x,root[1]-.01,z+.055+.024*sin(j*2+tier)])
            growth.stem([x,root[1],z],tip,.004)
            if j%3==0:
                growth.add(tube([x,root[1]-.015,z],[x,wall-.018,z],.002),'g6-wire-tie')
            for k in range(7):
                # Leaves clustered around each shoot end, with front-facing
                # pinnate veins. Full plant remains within the fixed run/depth.
                angle=pi/2+(.9*sin(k*2.4+j));tilt=.45+.40*cos(k*2+tier)
                node=tip+np.array([.026*sin(k*2.4),-.012-.030*cos(k*2.4),.022*sin(k+j)])
                growth.stem(tip,node,.002)
                growth.blade(node,length*(1+.07*sin(j+k)),width,angle,tilt,veined=True)
    return growth,root,tiers,wires


def lounge_parts(width,depth,seats):
    """Original timber outdoor seating in millimetres; +y is front, z is up.

    Slatted seat/back, solid armrests, crowned thick seat and back cushions.
    Width/depth are the recorded footprint; height is exactly 800 mm.
    """
    from . import villa_furniture_detail as F
    from .. import furniture as G
    x0,x1,y0,y1=-width/2,width/2,-depth/2,depth/2;parts=[]
    def box(name,a,b,c,d,e,f):parts.append((name,G._box(a,b,c,d,e,f)))
    for side in (-1,1):
        x=side*(width/2-30)
        for y in (y0+30,y1-30):box('timber-leg',x-22,x+22,y-22,y+22,0,560 if y>0 else 780)
        parts.append(('timber-arm',F._slab(x-30,x+30,y0,y1,550,590,12,5)))
        box('timber-rail',x-22,x+22,y0+10,y1-10,290,340)
    box('timber-front',x0+10,x1-10,y1-48,y1-12,295,345)
    box('timber-rear',x0+10,x1-10,y0+12,y0+48,295,345)
    for k in range(9):
        y=y0+45+k*(depth-90)/9
        box('timber-seat-slat',x0+40,x1-40,y,y+(depth-90)/9-7,335,360)
    for k in range(5):
        z=440+k*64
        parts.append(('timber-back-slat',F._slab(x0+28,x1-28,y0+8,y0+36,z,z+45,7,3)))
    inner0,inner1=x0+65,x1-65;unit=(inner1-inner0)/seats
    for k in range(seats):
        a,b=inner0+k*unit+4,inner0+(k+1)*unit-4
        parts.append(('seat-cushion',G._loft_rings([
            F._ring(a+8,b-8,y0+85,y1-24,360,25),F._ring(a,b,y0+76,y1-16,382,30),
            F._ring(a,b,y0+76,y1-16,440,30),F._ring(a+18,b-18,y0+94,y1-34,458,26)],6)))
        parts.append(('back-cushion',G._loft_rings([
            F._ring(a+10,b-10,y0+40,y0+145,442,24),F._ring(a,b,y0+35,y0+145,490,28),
            F._ring(a,b,y0+20,y0+122,764,28),F._ring(a+18,b-18,y0+31,y0+110,800,24)],6)))
    return parts
