"""python -m archpipe.markup ingest <pdf|csv|json> | list | decide <id> accept|reject --reason R | close <id> --commit SHA | revise <sheet.pdf> | frames

Exit 0 ok, 2 on missing/invalid input or a refused transition."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from archpipe import model

from . import frames as F, ingest, revise, store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="archpipe.markup")
    ap.add_argument("--design", default="D1")
    ap.add_argument("--root", type=Path, default=store.ROOT, help="request directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest").add_argument("path", type=Path)
    sub.add_parser("list")
    d = sub.add_parser("decide"); d.add_argument("id"); d.add_argument("verdict", choices=["accept", "reject"]); d.add_argument("--reason", required=True)
    c = sub.add_parser("close"); c.add_argument("id"); c.add_argument("--commit", required=True); c.add_argument("--element", action="append")
    r = sub.add_parser("revise"); r.add_argument("sheet", type=Path); r.add_argument("--out", type=Path)
    sub.add_parser("frames")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "frames":
            import json
            d_ = F.record(a.design)
            F.FRAMES_PATH.write_text(json.dumps(d_, indent=1), encoding="utf-8")
            print("frames for %s -> %s" % (", ".join(d_["sheets"]), F.FRAMES_PATH))
        elif a.cmd == "ingest":
            els = model.load(a.design)
            f = ingest.from_pdf if a.path.suffix.lower() == ".pdf" else ingest.from_table
            for rec, new in f(a.path, els, a.root):
                print("%s %s  %s  %s  %s" % (rec["id"], "new " if new else "seen", rec["sheet"], rec["link_status"], ", ".join(l["element_id"] for l in rec["links"]) or rec["link_reason"]))
        elif a.cmd == "list":
            for rec in store.all_requests(a.root):
                print("%s  %-8s %s  %-12s %s  | %s" % (rec["id"], rec["status"], rec["sheet"], rec["link_status"],
                      ", ".join("%s(%.0f)" % (l["element_id"], l["distance_mm"] or 0) for l in rec["links"]) or "-", rec["text"][:60]))
        elif a.cmd == "decide":
            rec = store.decide(a.id, a.verdict, a.reason, a.root)
            print("%s %s" % (rec["id"], rec["status"]))
        elif a.cmd == "close":
            ids = {e.id for e in model.load(a.design)}
            rec = store.close(a.id, a.commit, a.element, ids, a.root)
            print("%s closed by %s" % (rec["id"], a.commit))
        elif a.cmd == "revise":
            print(revise.revise_pdf(a.sheet, model.load(a.design), a.root, a.out))
    except (ingest.IngestError, store.StoreError, F.FrameError, revise.ReviseError, FileNotFoundError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
