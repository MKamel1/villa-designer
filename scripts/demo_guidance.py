"""Exercise all eight stages without authoring models or launching render jobs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from archpipe.guidance import review_stage, stage_context, lookup_evidence, _indexed


def main():
    report = {'scope': 'Fictional design-guidance demonstration; no real gate approval',
              'villa': [], 'bedroom': []}
    for stage in range(8):
        result = review_stage(stage)
        repeated = review_stage(stage)
        assert repeated['reused'] and not repeated['approved']
        assert {k:v for k,v in repeated.items() if k != 'reused'} == {k:v for k,v in result.items() if k != 'reused'}
        report['villa'].append(result)
    for stage in range(4, 8):
        report['bedroom'].append(review_stage(stage, 'knowledge/projects/bedroom.json'))
    report['focused_lookup'] = lookup_evidence('shading', stage=3)
    report['repeated_reviews_reused'] = 8
    report['index_cache'] = _indexed.cache_info()._asdict()
    report['next_inputs'] = stage_context(0)['missing_inputs']
    path = ROOT/'out/guidance-demo.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Wrote', path)
    print('Eight repeated reviews reused; all example approval gates remain closed.')
    print('Area result:', report['villa'][2]['checks'][0])
    print('Pavilion privacy:', next(c for c in report['villa'][3]['checks']
                                    if c['concept']=='pavilion' and c['check']=='private_access'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
