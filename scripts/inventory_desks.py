"""Inventory authored D1 desks and their derived chairs; no native extract edits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from archpipe.concept import villa_furnish as F, villa_furnish3d as F3
from archpipe.concept import villa_furniture_detail as FD, villa_r11 as R

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    """Read the same authored pieces, boxes and dispatch used by the renderer."""
    desks = [i for i in F.layout(R.design('D1')) if i['type'] == 'desk']
    rows = []
    for desk in desks:
        rows.append(dict(id=desk['id'], room=desk['room'], level=desk['level'],
                         type='desk', planned_footprint_m=[desk['w'], desk['d']],
                         world_footprint_m=list(F.footprint(desk)),
                         centre_m=[desk['cx'], desk['cy']], rotation_deg=desk['rot'],
                         heights_m=dict(desktop=desk['h']),
                         height_source='src/archpipe/concept/villa_furnish.py:_layout h (authored design)',
                         procedural_render_builder='villa_furniture_detail._desk via local_parts/world_parts',
                         native_builder='villa_furnish3d.body (top and legs)',
                         why=desk['why']))
        for f in F3.spec(items=[desk]):
            if f['type'] != 'chair':
                continue
            seat = FD.seat_item(f)
            # Use the real dispatch, avoiding a second list of task-chair IDs.
            detail = FD.seat_parts(f, 0)
            task = 'gas-lift' in detail
            rows.append(dict(id=f['mark'], parent_id=desk['id'], room=desk['room'],
                             level=desk['level'], type='task_chair' if task else 'vanity_chair',
                             planned_footprint_m=[round(seat['w'], 6), round(seat['d'], 6)],
                             world_footprint_m=list(f['envelope'][:2])+list(f['envelope'][3:5]),
                             centre_m=[seat['cx'], seat['cy']], rotation_deg=seat['rot'],
                             heights_m=dict(seat=seat['seat_h'], back=seat['h']),
                             height_source='src/archpipe/concept/villa_furnish3d.py:_chair defaults, via extras/spec '
                                           '(ASSUMED authored design, not verified ergonomics)',
                             procedural_render_builder='villa_furniture_detail.'+('_task_chair' if task else '_chair')+
                                                       ' via seat_parts/world_parts',
                             native_builder='villa_furnish3d._chair via extras/spec'))
    return dict(schema='desks-inventory/1', option='D1',
                units='Metres; footprint is local width/depth. World footprint is minimum X/Y then maximum X/Y. '
                      'Heights are above the room floor. Rotation is degrees about vertical.',
                authority='Existing furnishing design input, not a new Revit read-back or product approval',
                counts=dict(desks=len(desks), task_chairs=sum(r['type']=='task_chair' for r in rows),
                            vanity_chairs=sum(r['type']=='vanity_chair' for r in rows)), items=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/desks-inventory.json')
    args = parser.parse_args()
    args.output.write_text(json.dumps(inventory(), indent=2)+'\n', encoding='utf-8')
