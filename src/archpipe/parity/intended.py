"""The design model as the *intended* side of comparisons (read-only JSON; no generator is imported)."""
from __future__ import annotations

import json
from pathlib import Path

MODEL_JSON = Path(__file__).resolve().parents[1] / "model" / "data" / "d1-elements.json"
LEVEL_Z = {"B": -3.0, "GF": 0.0, "L1": 3.0, "ROOF": 6.0, "SITE": -3.0}   # scene metres; cross-checked by K18


def load_model(path=None) -> dict:
    p = Path(path) if path else MODEL_JSON
    if not p.exists():
        raise FileNotFoundError(p)
    d = json.loads(p.read_text())
    return {e["id"]: e for e in d["elements"]}


def along_y(e) -> bool:
    """True when a door/window's width runs along y (host wall runs north-south)."""
    sp = e["params"].get("span")
    if sp:
        return sp[0] == "v"
    return round(e.get("rotation_deg", 0.0)) % 180 == 90


def of_kind(model: dict, *kinds):
    return [e for e in model.values() if e["kind"] in kinds]
