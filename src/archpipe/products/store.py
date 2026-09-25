"""SQLite index for products and appearances, their checks and their links.

The index lives on the laptop (assets/user/products/index.sqlite, git-ignored)
so search is instant. Heavy files (textures, models) live on the render
workstation under ~/archpipe/library/<source>/<key>/ and are fetched on demand.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from archpipe.products import schema

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "assets" / "user" / "products"

DDL = """
create table if not exists items(
  id text primary key, kind text not null, category text, source text not null, key text not null,
  name text, brand text, url text, license text, tags text, styles text, data text,
  layer text not null default 'catalogue', updated real);
create table if not exists checks(
  item_id text, name text, status text, expected text, measured text, detail text, at real,
  primary key(item_id, name));
create table if not exists links(product_id text, appearance_id text, claim text, note text,
  primary key(product_id, appearance_id));
create table if not exists coverage(source text primary key, listed integer, indexed integer, at real);
"""


class connect:
    def __init__(self, library: Path = LIBRARY):
        self.path = Path(library) / "index.sqlite"

    def __enter__(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(DDL)
        return self.con

    def __exit__(self, *exc):
        if exc[0] is None:
            self.con.commit()
        self.con.close()


def upsert_items(items: list[dict], library: Path = LIBRARY) -> int:
    """Insert or refresh catalogue rows. A refresh never demotes a verified or failed layer."""
    with connect(library) as con:
        for it in items:
            assert it["kind"] in schema.KINDS, it
            row = con.execute("select layer from items where id=?", (it["id"],)).fetchone()
            layer = row["layer"] if row else "catalogue"
            con.execute("insert or replace into items values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                it["id"], it["kind"], it.get("category"), it["source"], it["key"], it.get("name"), it.get("brand"),
                it.get("url"), it.get("license"), json.dumps(it.get("tags", [])), json.dumps(it.get("styles", [])),
                json.dumps(it.get("data", {})), layer, time.time()))
    return len(items)


def set_coverage(source: str, listed: int, indexed: int, library: Path = LIBRARY) -> None:
    with connect(library) as con:
        con.execute("insert or replace into coverage values(?,?,?,?)", (source, listed, indexed, time.time()))


def record_checks(item_id: str, results: list[dict], library: Path = LIBRARY) -> str:
    """Store check results and set the item's layer: verified only if nothing failed
    AND at least one check actually passed (all-not_checkable is not verification)."""
    for r in results:
        assert r["status"] in schema.CHECK_STATES, r
    with connect(library) as con:
        for r in results:
            con.execute("insert or replace into checks values(?,?,?,?,?,?,?)", (
                item_id, r["name"], r["status"], json.dumps(r.get("expected")), json.dumps(r.get("measured")),
                r.get("detail", ""), time.time()))
        rows = con.execute("select status from checks where item_id=?", (item_id,)).fetchall()
        states = [x["status"] for x in rows]
        layer = "failed" if "failed" in states else ("verified" if "passed" in states else "catalogue")
        con.execute("update items set layer=?, updated=? where id=?", (layer, time.time(), item_id))
    return layer


def link(product_id: str, appearance_id: str, claim: str, note: str = "", library: Path = LIBRARY) -> None:
    if claim not in schema.CLAIMS:
        raise ValueError(f"claim must be one of {schema.CLAIMS}")
    with connect(library) as con:
        con.execute("insert or replace into links values(?,?,?,?)", (product_id, appearance_id, claim, note))


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("tags", "styles", "data"):
        d[k] = json.loads(d[k]) if d.get(k) else ([] if k != "data" else {})
    return d


def search(*, kind=None, category=None, text=None, style=None, source=None, include_unverified=False,
           limit=50, library: Path = LIBRARY) -> list[dict]:
    q, a = "select * from items where 1=1", []
    for col, val in (("kind", kind), ("category", category), ("source", source)):
        if val:
            q += f" and {col}=?"
            a.append(val)
    if not include_unverified:
        q += " and layer='verified'"
    if text:
        q += " and (lower(name) like ? or lower(tags) like ?)"
        a += [f"%{text.lower()}%"] * 2
    if style:
        q += " and styles like ?"
        a.append(f'%"{style}"%')
    q += " order by (layer='verified') desc, name limit ?"
    a.append(limit)
    with connect(library) as con:
        return [_row(r) for r in con.execute(q, a)]


def checks_for(item_id: str, library: Path = LIBRARY) -> list[dict]:
    with connect(library) as con:
        return [dict(r) for r in con.execute("select * from checks where item_id=? order by name", (item_id,))]


def counts(library: Path = LIBRARY) -> dict:
    with connect(library) as con:
        rows = con.execute("select source, kind, layer, count(*) n from items group by source, kind, layer").fetchall()
        cov = [dict(r) for r in con.execute("select * from coverage")]
    return {"items": [dict(r) for r in rows], "coverage": cov}
