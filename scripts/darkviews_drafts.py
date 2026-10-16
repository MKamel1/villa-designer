"""Replay small dark-view drafts through the existing locked garden probe driver.

The archived whole-set locks are retained. Counterfactual developments of
those same linear images isolate exposure, and are explicitly diagnostic.
They never replace the locked drafts or receive presentation acceptance.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]


def main():
    import bpy
    from archpipe.blender import villa_scene as B
    import garden_view_probes as driver

    original = B.render

    def render_and_diagnose(data, args):
        original(data, args)
        output = Path(args.out)
        fixture = json.loads(__import__('gzip').decompress((ROOT / 'tests/fixtures/darkviews-real.json.gz').read_bytes()))
        results = {}
        for vid, archive in [('v29-under-stair-store', 'j2'), ('v36-north-garden', 'j9')]:
            view = next(v for v in data['views'] if v['id'] == vid)
            report = json.loads((output / (vid + '.json')).read_text())
            scene = bpy.context.scene
            scene.view_settings.exposure = fixture[archive]['reports'][vid]['exposure_stops']
            B.photoreal.white_balance(data['exposure'][view['exposure']]['white_balance_k'],
                                     illuminant='daylight')
            image = bpy.data.images.load(str(output / (vid + '.exr')), check_existing=False)
            path = output / (vid + '-historical-exposure-DIAGNOSTIC.png')
            scene.render.image_settings.file_format = 'PNG'
            scene.render.image_settings.color_depth = '8'
            image.save_render(str(path), scene=scene)
            bpy.data.images.remove(image)
            results[vid] = {'locked_exposure_stops': report['exposure_stops'],
                            'diagnostic_historical_exposure_stops': scene.view_settings.exposure,
                            'counterfactual_image': path.name,
                            'purpose': 'Source diagnosis only; historical exposure is not an exemption or a replacement presentation.'}
            scene.view_settings.exposure = report['exposure_stops']
        (output / 'source-diagnosis.json').write_text(json.dumps(results, indent=2) + '\n')

    B.render = render_and_diagnose
    driver.main()


if __name__ == '__main__':
    main()
