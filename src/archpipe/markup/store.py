"""Change-request records: one JSON per request in knowledge/markup/requests/, plus the status machine.

open -> accepted | rejected (reason required) ; accepted -> closed (commit required, elements linked). Silence is not approval:
nothing moves without an explicit decide/close call. Ids are MK-001.. in ingest order; a source hash makes ingest idempotent.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "knowledge" / "markup" / "requests"


class StoreError(ValueError):
    pass


def _today() -> str:
    return datetime.date.today().isoformat()


def all_requests(root: Path = ROOT) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(root).glob("MK-*.json"))]


def get(rid: str, root: Path = ROOT) -> dict:
    p = Path(root) / (rid + ".json")
    if not p.exists():
        raise StoreError("no request %s" % rid)
    return json.loads(p.read_text(encoding="utf-8"))


def put(rec: dict, root: Path = ROOT) -> None:
    Path(root).mkdir(parents=True, exist_ok=True)
    (Path(root) / (rec["id"] + ".json")).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def add(rec: dict, root: Path = ROOT) -> tuple[dict, bool]:
    """Store a new request (id assigned); an identical source hash returns the existing record, created=False."""
    existing = all_requests(root)
    for r in existing:
        if r["source"]["hash"] == rec["source"]["hash"]:
            return r, False
    n = 1 + max([int(r["id"][3:]) for r in existing] or [0])
    rec = {"id": "MK-%03d" % n, **rec, "status": "open", "decision": None, "closure": None}
    put(rec, root)
    return rec, True


def decide(rid: str, verdict: str, reason: str, root: Path = ROOT, date: str | None = None) -> dict:
    r = get(rid, root)
    if verdict not in ("accept", "reject"):
        raise StoreError("decision must be accept or reject")
    if not reason or not reason.strip():
        raise StoreError("a decision needs a reason")
    if r["status"] != "open":
        raise StoreError("%s is %s, not open" % (rid, r["status"]))
    r["status"] = "accepted" if verdict == "accept" else "rejected"
    r["decision"] = {"verdict": verdict, "reason": reason.strip(), "date": date or _today()}
    put(r, root)
    return r


def close(rid: str, commit: str, elements: list[str] | None = None, known_ids: set[str] | None = None,
          root: Path = ROOT, date: str | None = None) -> dict:
    r = get(rid, root)
    if r["status"] != "accepted":
        raise StoreError("%s is %s: only an accepted request can be closed (silence is not approval)" % (rid, r["status"]))
    if not commit or not commit.strip():
        raise StoreError("closing needs the commit that resolved it")
    if elements:
        if known_ids is not None and set(elements) - known_ids:
            raise StoreError("unknown element id(s): %s" % ", ".join(sorted(set(elements) - known_ids)))
        r["links"] = [l for l in r["links"] if l["element_id"] in elements] + [
            {"element_id": i, "kind": None, "distance_mm": None, "tier": "resolved-by-lead"}
            for i in elements if i not in {l["element_id"] for l in r["links"]}]
        r["link_status"] = "linked"
    if not [l for l in r["links"] if l["tier"] != "context"]:
        raise StoreError("%s has no linked element (%s): pass --element ID to say what changed" % (rid, r["link_status"]))
    r["status"] = "closed"
    r["closure"] = {"commit": commit.strip(), "date": date or _today()}
    put(r, root)
    return r
