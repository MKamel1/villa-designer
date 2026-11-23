"""Markdown product tables for the finish palettes (generated; never hand-edited). No prices."""
from __future__ import annotations

from . import finishes as F


def _fmt(p):
    f = p.get("format_mm") or {}
    return " x ".join(str(f[k]) for k in ("w", "l", "t") if f.get(k)) + " mm" if f else ""


def table(pal: dict, group: str) -> str:
    rows = ["| id | use | maker, range | colour | format / finish | LRV | Egypt | maker page | look-alike (not the product) | scale |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for it in pal["items"]:
        if it["group"] != group:
            continue
        p, la, eg = it["product"], it.get("lookalike"), it.get("egypt") or {}
        sc = ""
        if la:
            tm, basis = F.texture_scale_m(it)
            sc = f"{tm:.2f} m ({basis})"
        lrv = f"{p['lrv']} ({p.get('lrv_source', '')[:40]})" if p.get("lrv") is not None else "n/a"
        egt = f"[{eg['supplier']}]({eg['url']})" if eg.get("available") is True else "GAP: " + str(eg.get("gap") or "unknown").split(". ")[0][:70]
        rows.append("| {} | {} | {} {} | {} {} | {} {} | {} | {} | [page]({}) | {} | {} |".format(
            it["id"], it.get("use", ""), p.get("maker") or "", p.get("range") or p.get("name") or "",
            p.get("colour_name") or "", p.get("colour_code") or "", _fmt(p), p.get("finish") or "", lrv, egt,
            it["source"]["url"],
            f"{la['maker_site']} [{la['id']}]({la['url']}) {la['licence']}" if la else "flat colour / chip", sc).replace("  ", " "))
    return "\n".join(rows)


def maintenance(pal: dict) -> str:
    out = []
    for it in pal["items"]:
        m = it.get("maintenance")
        if m and m.get("note"):
            out.append(f"- **{it['id']}**: {m['note']} ([source]({m.get('url')})): \"{(m.get('quote') or '')[:200]}\"")
    return "\n".join(out)


def cushion_schedule(pal: dict) -> str:
    rows = ["| sofa / bed | item | maker, range | colour | size | composition | Egypt |", "|---|---|---|---|---|---|---|"]
    for it in pal["items"]:
        if it["group"] == "soft" and any(k in it["id"] for k in ("cushion", "throw", "sofa", "daybed", "parents-bed")):
            p, eg = it["product"], it.get("egypt") or {}
            rows.append(f"| {it.get('use', '')} | {it['id']} | {p.get('maker')} {p.get('range') or p.get('name')} | "
                        f"{p.get('colour_name') or ''} {p.get('colour_code') or ''} | {_fmt(p)} | {p.get('composition') or 'not stated'} | "
                        f"{'yes' if eg.get('available') is True else 'GAP'} |")
    return "\n".join(rows)
