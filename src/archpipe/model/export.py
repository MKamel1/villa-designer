"""python -m archpipe.model.export [--design D1] [--snapshot] [--out PATH]"""
from __future__ import annotations

import argparse
import json

from . import api


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design", default="D1")
    ap.add_argument("--snapshot", action="store_true", help="also refresh the committed snapshot in src/archpipe/model/data")
    ap.add_argument("--out")
    a = ap.parse_args()
    els = api.generate(a.design)
    path = api.export(a.design, elements=els, path=a.out, snapshot=a.snapshot)
    print(json.dumps(dict(path=str(path), counts=api.counts(els), total=len(els)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
