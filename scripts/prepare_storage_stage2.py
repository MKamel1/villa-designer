"""Measure credited storage sources; fit whole items without activating rejects.

All distances are metres. Native glTF axes are X/Z horizontal and Y up.
The width, depth and vertical fit factors are dimensionless. The source's
default metre declaration is retained; no target-derived unit conversions.
"""
from pathlib import Path
import gzip
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.furniture_fit import native_box, fit_furniture

OUT = ROOT / 'out/storage/stage2'
LIBRARY = Path('/home/omar/archpipe/assets/library/props')
FRONTS = {'20a54670': '+X', '2402ee23': '+X', '3028ba44': '+X',
          '0999a8a7': '+Z', '48bd85b3': '+Z', '65c10ad6': '+Z',
          '79138881': '+Z', '9ef2d891': '-Z', 'ba32c03d': '+Z',
          'c5046eb6': '+Z', 'c5105496': '+X', 'f5d363e1': '+Z',
          '62227102': '+Z'}


def measured_candidate(geometry, suffix):
    """Return complete immutable items; only the duplicate open wardrobe omits.

    Exact separate source meshes identify the open pose, never a geometric
    crop. A staging platform and fused hutch remain explicit refusals.
    """
    names = [m['name'] for m in geometry['meshes']]
    omitted = []
    if suffix == '0999a8a7':
        omitted = ['Body.004_Body baked_0', 'DoorL.004_DoorL baked_0',
                   'DoorR.004_DoorR baked_0', 'DrawerL.006_Drawer baked_0',
                   'DrawerL.007_Drawer baked_0', 'DrawerT.004_Drawer baked_0']
    if suffix == 'c5046eb6':
        omitted = ['Object_7']
    if not set(omitted) <= set(names):
        raise ValueError('source contents changed; repeat neutral inspection')
    retained = [m for m in geometry['meshes'] if m['name'] not in omitted]
    basis = ('Both opposing neutral source views and imported part bounds; '
             'complete furniture body, hardware and supports retained')
    return dict(id=geometry['asset'], role='storage', asset=geometry['asset'],
                front_axis=FRONTS.get(suffix), review_geometry=geometry,
                omitted_meshes=omitted,
                unit_evidence=dict(unit='m', source='glTF 2.0 metre coordinates; no overriding source-unit declaration'),
                contents_review=dict(status='item-only', basis=basis, extras=omitted,
                                     fused_extras=['integral desk hutch'] if suffix == '2402ee23' else [])), retained


def prepare(output=OUT, library=LIBRARY):
    research = json.loads((ROOT / 'docs/storage-candidates.json').read_text())
    context = json.loads(gzip.decompress((output / 'authoring-context.json.gz').read_bytes()))
    items = {i['id']: i for i in context['furniture']}
    records = []
    for path in sorted((output / 'geometry').glob('*.json.gz')):
        geometry = json.loads(gzip.decompress(path.read_bytes()))
        geometry['schema'] = 'furniture-model-geometry/1'
        suffix = geometry['asset'].removeprefix('sf_store_')
        provenance = json.loads((library / geometry['asset'] / 'provenance.json').read_text())
        if provenance['licence'] != 'CC Attribution':
            raise ValueError('storage intake admits only the lead-downloaded CC Attribution assets')
        candidate, retained = measured_candidate(geometry, suffix)
        source = next((c for c in research['candidates'] if c['uid'].startswith(suffix)), None)
        bounds = native_box(retained)
        record = dict(asset=geometry['asset'], name=provenance['name'],
                      bounds_native_m=bounds,
                      extent_native_x_z_height_m=[bounds['max'][i]-bounds['min'][i] for i in (0, 2, 1)],
                      retained_meshes=[m['name'] for m in retained],
                      contents_review=candidate['contents_review'], omitted_meshes=candidate['omitted_meshes'],
                      source_sha256=geometry['source_sha256'],
                      front_axis=candidate['front_axis'],
                      orientation_basis='Opposing source previews and actual front/handle bounds; modular diagonal cabinet unresolved' if suffix == '5577bdb9' else 'Opposing source previews and actual front/handle bounds',
                      credit=(library / geometry['asset'] / 'license.txt').read_text(),
                      asset_kind='appearance proxy; not a certified buyable product', fits={})
        for mark in source['target_ids'] if source else []:
            item = items[mark]
            heights = [m['name'] for m in retained]
            if suffix == '79138881':
                heights = ['Body1_Oak Honey Matte_0']  # Complete desktop; mirror is retained.
            if suffix == '20a54670':
                heights = ['Metallic Office Desk_board_0']
            if suffix == 'c5105496':
                heights = ['Object_4', 'Object_5']
            try:
                fit = fit_furniture(candidate, item['w'], item['d'], height_parts=heights,
                                    height_m=item['h'], height_source='Exact live authoring_room_context furniture '+mark+' h',
                                    height_basis='design')
            except ValueError as error:
                fit = dict(ok=False, reason=str(error))
            reasons = [] if fit['ok'] else [fit['reason']]
            if item['type'] == 'wardrobe':
                reasons.append('User scope: wardrobes stay procedural, including kids wardrobes; no activation')
            if suffix in ('5577bdb9', '9ef2d891', '3028ba44') and item['type'] == 'tv_unit':
                reasons.append('Floor-standing source cannot replace authored wall-hung cabinet; complete feet retained')
            if suffix == '5577bdb9':
                reasons.append('Diagonal source modules: a single cardinal furniture front is unverified')
            if suffix == 'c5046eb6':
                reasons.append('Search2 provenance quarantine: re-upload does not establish original rights')
            record['fits'][mark] = dict(fit=fit, eligible=not reasons, refusals=reasons)
        if source is None:
            record['scope_refusal'] = 'Additional wardrobe download; wardrobes retained procedural; not an inventoried loose-unit shortlist match'
        records.append(record)
    (output / 'intake.json').write_text(json.dumps(records, indent=2)+'\n')
    eligible = [(r['asset'], mark) for r in records for mark, fit in r['fits'].items() if fit['eligible']]
    (output / 'selection.json').write_text(json.dumps(dict(status='completed', eligible=eligible,
        activated=[], scope='Wardrobes and built-in joinery stay procedural. Existing desks/chairs preserved.',
        reason='No complete loose source passes fit, mounting and provenance together.'), indent=2)+'\n')
    for r in records:
        print(r['asset'], [(k, v['fit']['ok'], v['eligible']) for k, v in r['fits'].items()])
    if eligible:
        raise ValueError('new eligible candidate requires whole-room review and neutral preview before activation')
    return records


if __name__ == '__main__':
    prepare()
