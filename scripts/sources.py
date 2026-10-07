"""Books, standards and datasets: what to obtain, and taking delivery.

    python scripts/sources.py list      # rewrite the purchase list (docs + out/purchase-list.html)
    python scripts/sources.py intake    # file what you saved into ~/archpipe-sources/inbox/
    python scripts/sources.py fetch-free  # download the public ones (robots.txt checked)
    python scripts/sources.py status    # counts per state: identified / held / content_verified

Originals stay outside the repository (ARCHPIPE_SOURCES, default
~/archpipe-sources). See src/archpipe/sources.py for the states.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context  # noqa: E402
from archpipe import sources as src  # noqa: E402

DOC = ROOT / "docs" / "guidance" / "coverage-and-acquisition.md"
BEGIN, END = "<!-- purchase-list:begin -->", "<!-- purchase-list:end -->"


def write_doc(lib: dict) -> None:
    text = DOC.read_text(encoding="utf-8")
    a, b = text.index(BEGIN) + len(BEGIN), text.index(END)
    DOC.write_text(text[:a] + "\n" + src.purchase_markdown(lib) + text[b:], encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["list", "intake", "fetch-free", "status"])
    a = ap.parse_args(argv)
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "sources",
            inputs=[ROOT / "knowledge/library.json"],
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2

    lib = src.load()
    if a.cmd == "list":
        write_doc(lib)
        print(src.write_purchase_html(lib, ROOT / "out" / "purchase-list.html"))
        return 0
    if a.cmd == "intake":
        rep = src.intake(lib)
        src.save(lib)
        write_doc(lib)
        for k in ("locked", "unreadable", "unmatched"):
            for r in rep[k]:
                print(f"  {k.upper()}: {r['file']}: {r['detail']}")
        print(f"  {len(rep['held'])} filed; registry updated")
        return 0 if not (rep["locked"] or rep["unreadable"] or rep["unmatched"]) else 1
    if a.cmd == "fetch-free":
        rep = src.fetch_free(lib)
        src.save(lib)
        write_doc(lib)
        print(f"  {len(rep['held'])} files held, {len(rep['failed'])} failed")
        return 1 if rep["failed"] else 0
    counts = {}
    for s in lib["sources"]:
        counts[s.get("status")] = counts.get(s.get("status"), 0) + 1
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
