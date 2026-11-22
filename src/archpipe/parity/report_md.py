"""Render out/parity/d1-report.json (from `run_d1 --prove`) as the markdown results section of docs/lanes/RV1-checks.md."""
from __future__ import annotations

import json
import sys


def md(rep):
    o = []
    o.append(f"Scene `{rep['scene']['path']}` sha256 `{rep['scene']['sha256']}`  \nIFC `{rep['ifc']['path']}` sha256 `{rep['ifc']['sha256']}`\n")
    o.append("### Checks on the D1 scene and IFC\n\n| check | pass | fail | not evaluated |\n|---|---|---|---|")
    for c, v in rep["counts"].items():
        o.append(f"| {c} | {v['pass']} | {v['fail']} | {v['not_evaluated']} |")
    o.append("\n### Scene vs IFC kernel, per clash pair\n")
    o.append("| pair | scene | IFC | agree |\n|---|---|---|---|" if rep["scene_vs_ifc"] else "No pair fails in either the scene or the IFC: they agree on every clash tested.")
    for r in rep["scene_vs_ifc"]:
        o.append(f"| {r['pair']} | {r['scene']} {r['scene_mm']} | {r['ifc']} {r['ifc_mm']} | {r['agree']} |")
    h = rep.get("historic_and_synthetic", [])
    o.append("\n### Recall on the frozen reproductions\n\n| row | source | check | subject | expected | got | ok |\n|---|---|---|---|---|---|---|")
    for r in h:
        o.append(f"| {r['row']} | {r['source']} | {r['check']} | {r.get('option') or r.get('subject') or ''} | {str(r['expect'])[:40]} | {r['got']} | {r['ok']} |")
    m = rep.get("mutations", [])
    o.append("\n### Mutation set\n\n| id | check | kind | expected | result | detail |\n|---|---|---|---|---|---|")
    for r in m:
        res = ("caught" if r["caught"] else "quiet") + ("" if r["ok"] else " **(MISS)**" if r["expect"] == "catch" else " **(FALSE ALARM)**")
        o.append(f"| {r['id']} | {r['check']} | {r['kind']} | {r['expect']} | {res} | {r['detail'][:110]} |")
    return "\n".join(o)


if __name__ == "__main__":
    print(md(json.load(open(sys.argv[1]))))
