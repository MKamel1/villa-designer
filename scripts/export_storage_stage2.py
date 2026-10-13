"""Save the exact current authored context and declared storage preview requests."""
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.concept import villa_render
from archpipe.concept.villa_furnish import _cluster

OUT = ROOT / 'out/storage/stage2'
VIEWS = {'dining-sideboard': 'v09-dining-evening', 'lounge-tv': 'v03-street-lounge',
         'study-tv': 'v18-study-evening', 'pb-bedside': 'v22-parents-day', 'pb-vanity': 'v22-parents-day'}


def export(scene=None, output=OUT):
    scene = scene if scene is not None else villa_render.build()
    output.mkdir(parents=True, exist_ok=True)
    context = scene['authoring_room_context']
    (output / 'authoring-context.json.gz').write_bytes(gzip.compress(json.dumps(context, separators=(',', ':')).encode(), mtime=0))
    items = {i['id']: i for i in context['furniture']}
    requests = [[mark, items[mark]['room'], view] for mark, view in VIEWS.items()]
    rooms = {room for mark in VIEWS for room in _cluster(context['layout'], items[mark]['room'])}
    subset = dict(scene, models=[m for m in scene['models'] if m.get('room') in rooms],
                  meshes=[m for m in scene['meshes'] if m['group'] in ('shell', 'context') or m.get('room') in rooms])
    (output / 'storage-room-scene.json').write_text(json.dumps(subset, separators=(',', ':'))+'\n')
    (output / 'preview-requests.json').write_text(json.dumps(requests, indent=2)+'\n')
    return subset, requests


if __name__ == '__main__':
    export()
