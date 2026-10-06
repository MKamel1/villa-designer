"""Construction targets from stored manufacturer body dimensions, not as-built voids."""
from pathlib import Path
import math
import json

from ..luminaires import eulumdat
from . import villa_lighting as VL

ROOT = Path(__file__).resolve().parents[3]
ASSUMED_CLEARANCE_MM = 25.0
CLEARANCE_BASIS = ('ASSUMED lead construction allowance: 25 mm for cable/connector handling; '
                   'no manufacturer clearance recorded. Installer must obtain thermal, driver, '
                   'accessory and installation instructions and increase this allowance if required.')


def product_depth(kind, product_record=None):
    choice = VL.PRODUCT_CHOICE.get(kind)
    if choice is None:
        return dict(kind=kind, housing_depth_mm=None, source='UNRESOLVED: no selected product record')
    manufacturer, sku, _ = choice
    path = ROOT / 'assets/user/luminaires' / manufacturer / sku / (sku+'.ldt')
    manifest=path.with_name('product.json')
    if product_record is None:
        product_record=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    depth = None
    if path.exists():
        depth = eulumdat.load(path).size_mm[2]
        if not math.isfinite(depth) or depth <= 0:
            depth = None
    depth_source=str(path.relative_to(ROOT)).replace('\\','/')+'; EULUMDAT line 15, luminaire body height'
    for field in ('housing_depth_mm','installation_depth_mm'):
        value=product_record.get(field)
        if value is not None:
            if not isinstance(value,(float,int)) or not math.isfinite(value) or value<=0:
                raise ValueError(sku+': invalid stored manufacturer '+field)
            if depth is None or value>=depth:
                depth=value
                depth_source=str(manifest.relative_to(ROOT)).replace('\\','/')+'; '+field
    clearance=product_record.get('installation_clearance_mm')
    if clearance is None:
        clearance=ASSUMED_CLEARANCE_MM;clearance_source=CLEARANCE_BASIS
    else:
        if not isinstance(clearance,(float,int)) or not math.isfinite(clearance) or clearance<0:
            raise ValueError(sku+': invalid stored manufacturer installation clearance')
        clearance_source=str(manifest.relative_to(ROOT)).replace('\\','/')+'; manufacturer installation_clearance_mm'
    if depth is None:
        depth_source='UNRESOLVED: housing/installation depth absent in '+str(path.relative_to(ROOT)).replace('\\','/')+' and product.json'
    return dict(kind=kind, manufacturer=manufacturer, sku=sku, housing_depth_mm=depth,
                source=depth_source, clearance_mm=clearance, clearance_source=clearance_source,
                basis='Stored body height used conservatively as housing depth; trimless accessory/driver installation data pending')


def requirements(lamps):
    zones = {}
    for lamp in lamps:
        if lamp.kind not in ('DL','DLN','ADJ','WW'):
            continue
        # A zone may contain several physical soffits. Same requirement applies
        # behind each actual finite host, measured along that host's normal.
        zone = lamp.level+'/'+lamp.room+('/joinery-top' if 'nook top' in lamp.why else '/ceiling')
        row = zones.setdefault(zone, dict(zone=zone, fitting_ids=[], products={}, status='requirement'))
        row['fitting_ids'].append(lamp.id)
        row['products'][lamp.kind] = product_depth(lamp.kind)
    for row in zones.values():
        missing = [k for k,p in row['products'].items() if p['housing_depth_mm'] is None]
        clearance=max((p.get('clearance_mm',ASSUMED_CLEARANCE_MM) for p in row['products'].values()))
        row.update(unresolved_kinds=missing, clearance_mm=clearance,
                   clearance_source='; '.join(dict.fromkeys(p.get('clearance_source',CLEARANCE_BASIS) for p in row['products'].values())))
        row['max_housing_depth_mm'] = None if missing else max(p['housing_depth_mm'] for p in row['products'].values())
        row['required_void_mm'] = None if missing else row['max_housing_depth_mm']+row['clearance_mm']
        if missing:
            row['status'] = 'UNRESOLVED'
    return list(zones.values())


def write_table(rows, path):
    lines = ['# Ceiling void construction requirements', '',
        'B means basement; GF means ground floor. Zone names group each room ceiling under one uniform minimum, including any sloping or stepped host faces. EULUMDAT is the European luminaire photometric data format; IES is the Illuminating Engineering Society photometric file format. The selected recessed body dimensions are recorded in EULUMDAT line 15.', '',
        'D1, lead instruction 2026-10-05. All dimensions are millimetres. Required void is the largest recorded housing depth in a zone plus installation clearance, measured perpendicular to the finished ceiling. Status is **requirement**, never verified-as-built.', '',
        'DL means wide downlight; DLN means task downlight; ADJ means adjustable accent; WW means the selected flood substitute for a wall washer. STEP and PATH are recessed wall markers, not ceiling fittings; their housing depths have no product record and remain UNRESOLVED for package (e).', '',
        'The three selected Laser Evo products have stored manufacturer EULUMDAT body dimensions. Product manifests contain photometry origins/hashes only; stored iGuzzini crawl pages do not contain these selected codes or installation clearance. IES files contain photometry, not installation instructions. No installation clearance is recorded. The assumed allowance below is a construction target requiring manufacturer confirmation, not a thermal rating or installability pass. No board thickness or available as-built void is inferred.', '',
        '| Zone | Fittings (kind/count) | Max housing depth + source | Clearance + source/ASSUMED | Required void | Status |',
        '|---|---|---|---|---|---|']
    for row in rows:
        kinds = ', '.join(k+' ('+str(sum(i.startswith(k+'-') for i in row['fitting_ids']))+')' for k in row['products'])
        sources = '; '.join(k+': '+str(p['housing_depth_mm'])+' mm, '+(p['source'] if p['source'].startswith('UNRESOLVED') else '['+p.get('sku','unknown')+'](../../'+p['source'].split(';')[0]+') '+p['source'].split(';')[-1]) for k,p in row['products'].items())
        clearance_text=(str(row['clearance_mm'])+' mm ASSUMED: cable/connector handling; manufacturer instructions required'
                        if row['clearance_source']==CLEARANCE_BASIS else str(row['clearance_mm'])+' mm; '+row['clearance_source'])
        lines.append('| '+row['zone']+' | '+kinds+' | '+str(row['max_housing_depth_mm'])+' mm; '+sources+' | '+clearance_text+' | '+str(row['required_void_mm'])+' mm | '+row['status']+' |')
    missing=sorted({kind for row in rows for kind in row['unresolved_kinds']})
    lines += ['', ('UNRESOLVED ceiling kinds: '+', '.join(missing)+'.' if missing else 'No unresolved ceiling kind in the current selected DL/DLN/ADJ/WW records.')+' Joinery-top requirements are listed but mounting remains package (e). The wall-marker kinds STEP and PATH remain UNRESOLVED: no recorded housing depth; they do not establish a ceiling void.', '', CLEARANCE_BASIS]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
