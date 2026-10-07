"""Check geometry-named client compass words before export and verification.

Building bounds are (minimum x, minimum y, maximum x, maximum y), in metres.
Top local edge names compare with the top garden's centre, rather than with
an unrelated true-north bearing. One-letter tokens n/e/s/w expand to side words.
"""
import re
import hashlib
from pathlib import Path
from .orientation import side_name, record

SHORT = dict(n='north',e='east',s='south',w='west')


def named_sides(text):
    return [SHORT.get(m[0].lower(),m[0].lower()) for m in re.finditer(r'\b(?:north|east|south|west|n|e|s|w)\b',text,re.I)]


def geometry_side(center,building_bounds):
    x,y=center[:2];x0,y0,x1,y1=building_bounds
    distances={'-x':x0-x,'+x':x-x1,'-y':y0-y,'+y':y-y1}
    return side_name(max(distances,key=distances.get))


def scene_findings(scene, *, building_bounds=None, top_bounds=None):
    from .concept import villa_landscape as L
    if building_bounds is None:
        from . import villa_env as E
        building_bounds=tuple(v/1000 for v in E.BAR)
    top_bounds=top_bounds or L.TOP
    items=[m for m in scene['meshes'] if m['id'].startswith('landscape-')]+[p for p in scene.get('props',[]) if p['id'].startswith('landscape-')]
    errors=[]
    for item in items:
        rect=L._rect(item);center=((rect[0]+rect[2])/2,(rect[1]+rect[3])/2)
        words=named_sides(item['id'])
        if not words:continue
        if item.get('zone')=='top' or item['id'].startswith('landscape-top-'):
            # Local trough edge along model Y, or model X for a named end.
            name=words[0]
            direction=('+y' if center[1]>(top_bounds[1]+top_bounds[3])/2 else '-y') if name in (side_name('+y'),side_name('-y')) else ('+x' if center[0]>(top_bounds[0]+top_bounds[2])/2 else '-x')
            expected=side_name(direction)
        else:expected=geometry_side(center,building_bounds)
        for label_word in named_sides(re.sub(r'https?://\S+','',item.get('label',''))):
            if label_word!=expected:errors.append(f"{item['id']} label: names {label_word}, expected {expected}")
        if words[0]!=expected and not ('door-pot' in item['id'] and len(words)==1):errors.append(f"{item['id']}: centroid {center} names {words[0]}, expected {expected}")
        # Paired pot suffixes name the lower/higher model-X member of their assembly.
        if 'door-pot' in item['id']:
            prefix=re.sub(r'-(n|e|s|w)(?=-|$).*','',item['id'])
            peers=[p for p in items if p['id'].startswith(prefix+'-')]
            if len(peers)>1:
                rects=[L._rect(p) for p in peers]
                xs=[(r[0]+r[2])/2 for r in rects]
                ys=[(r[1]+r[3])/2 for r in rects]
                axis=0 if max(xs)-min(xs)>=max(ys)-min(ys) else 1
                values=xs if axis==0 else ys
                direction=('-' if center[axis]<(min(values)+max(values))/2 else '+')+('x' if axis==0 else 'y')
                end=side_name(direction)
                if words[-1]!=end:errors.append(f"{item['id']}: paired end names {words[-1]}, expected {end}")
    for name,rect in scene.get('garden_zones',{}).items():
        center=((rect[0]+rect[2])/2,(rect[1]+rect[3])/2)
        expected=geometry_side(center,building_bounds)
        for word in named_sides(name):
            if word!=expected:errors.append(f"zone {name}: centroid {center} expects {expected}")
    for view in scene.get('views',[]):
        subjects=[m for m in items if any(m['id'].startswith(s) for s in view.get('subjects',[]))]
        if not subjects:continue
        # Views of top-garden east troughs may also include the west trough.
        local='top-garden' in view['id']
        rects=[L._rect(m) for m in subjects]
        center=(sum((r[0]+r[2])/2 for r in rects)/len(rects),sum((r[1]+r[3])/2 for r in rects)/len(rects))
        expected=side_name('+y') if local else geometry_side(center,building_bounds)
        for field in ('id','title'):
            for word in named_sides(view.get(field,'')):
                if word!=expected:errors.append(f"{view['id']} {field}: names {word}, expected {expected}")
        for caption in view.get('caption_notes',[]):
            allowed={expected}
            if local:
                allowed.update(word for subject in subjects for word in named_sides(subject['id']))
            for word in named_sides(re.sub(r'https?://\S+','',caption)):
                if word not in allowed:errors.append(f"{view['id']} caption: names {word}, expected {sorted(allowed)}")
    return errors


def document_findings(paths=None, *, building_bounds=None, top_bounds=None):
    """Bind narrative review and independently measure coordinate-bearing claims.

    Narrative references without coordinates need an explicit review; hashes
    ensure that review cannot silently survive a text change. Coordinate tables
    and stated model directions are checked independently of those hashes.
    """
    from . import villa_env as E
    from .concept import villa_landscape as L
    root=Path(__file__).resolve().parents[2]
    paths=paths or list((root/'docs').glob('garden-*-report.md'))+[root/'docs/ops/garden-rebuild.md']
    building_bounds=building_bounds or tuple(v/1000 for v in E.BAR)
    top_bounds=top_bounds or L.TOP
    reviewed=record()['garden_document_review']['sha256']
    errors=[]
    for path in paths:
        path=Path(path);text=path.read_text(encoding='utf-8')
        try:key=path.resolve().relative_to(root).as_posix()
        except ValueError:key=None
        if key in reviewed and hashlib.sha256(path.read_bytes()).hexdigest()!=reviewed[key]:
            errors.append(f'{path}: narrative changed since its recorded coordinate/naming review')
        for direction,name in re.findall(r'<!-- garden-side: ([+-][xy]); name: (north|east|south|west) -->',text):
            if name!=side_name(direction):errors.append(f'{path}: {direction} must be named {side_name(direction)}, found {name}')
        # Explicit direction prose, including bench facing and measured offsets.
        for name,sign,axis in re.findall(r'\b(north|east|south|west), (positive|negative) ([xy])\b(?=[,.;]|$)',text,re.I):
            direction=('+' if sign.lower()=='positive' else '-')+axis.lower()
            if name.lower()!=side_name(direction):errors.append(f'{path}: {name} disagrees with {direction}')
        for sign,axis,name in re.findall(r'\b(positive|negative) ([xy])(?: is|,) (north|east|south|west)\b',text,re.I):
            direction=('+' if sign.lower()=='positive' else '-')+axis.lower()
            if name.lower()!=side_name(direction):errors.append(f'{path}: {direction} disagrees with {name}')
        # A named row's first coordinate pair/rectangle is its geometric anchor.
        for line in text.splitlines():
            if not line.startswith('|'):continue
            cells=line.split('|');names=named_sides(cells[1])
            if not names:continue
            numbers=re.search(r'\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)(?:\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?))?\s*\)',line.replace('−','-'))
            if not numbers:continue
            values=[float(v) for v in numbers.groups() if v is not None]
            center=values if len(values)==2 else ((values[0]+values[2])/2,(values[1]+values[3])/2)
            if re.search(r'\b(deck|roof)\b',cells[1],re.I):
                expected=side_name('+y' if center[1]>(top_bounds[1]+top_bounds[3])/2 else '-y')
            else:expected=geometry_side(center,building_bounds)
            label=cells[1].strip().strip('`')
            paired=re.match(r'(dining|living|lounge)-.*-[nesw]$',label) or re.match(r'dining-[nesw]$',label)
            if paired:
                prefix=label.rsplit('-',1)[0]
                peers=[]
                for other in text.splitlines():
                    if not other.startswith('|'):continue
                    other_label=other.split('|')[1].strip().strip('`')
                    if other_label.rsplit('-',1)[0]!=prefix:continue
                    pair=re.search(r'\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)',other.replace('−','-'))
                    if pair:peers.append(tuple(float(v) for v in pair.groups()))
                if len(peers)>1:
                    xs=[p[0] for p in peers];ys=[p[1] for p in peers]
                    axis=0 if max(xs)-min(xs)>=max(ys)-min(ys) else 1
                    values=xs if axis==0 else ys
                    end=side_name(('-' if center[axis]<(min(values)+max(values))/2 else '+')+('x' if axis==0 else 'y'))
                    if names[-1]!=end:errors.append(f'{path}: paired end {label} expects {end}')
                    if len(names)==1:expected=end
            if names[0]!=expected:errors.append(f'{path}: coordinate table names {names[0]}, expected {expected} at {center}')
    return errors
