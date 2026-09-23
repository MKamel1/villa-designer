"""Review an actual Revit extract; isolate room scope explicitly."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from archpipe.review_extract import review_model


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('extract', type=Path)
    ap.add_argument('--scope', choices=['room', 'dwelling'], default='dwelling')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    result = review_model(json.loads(a.extract.read_text(encoding='utf-8')), scope=a.scope)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result['disclaimer'])
    print('Scope:', result['scope'])
    print('Furniture measured:', result['furniture_count'])
    for note in result['conversion_notes']:
        print('NOTE', note)
    for f in result['findings']:
        print(f['severity'].upper(), f['rule'], f['message'])
    for item in result['not_assessed']:
        print('NOT ASSESSED', item['rule'], item['reason'])
    print('RESULT:', 'PASS' if result['passed'] else 'FAIL')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
