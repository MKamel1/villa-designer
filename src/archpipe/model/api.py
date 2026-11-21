"""Load / generate / export the canonical design model.

    load("D1")                      # cached JSON if present, else the committed snapshot, else generate (minutes)
    generate("D1")                  # derive from the pipeline sources (design layout, Revit spec, lighting, landscape)
    export("D1")                    # write out/model/d1-elements.json (and optionally the committed snapshot)
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ..contracts import CONTRACT_VERSION, DesignElement
from .schema import SCHEMA, validate

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = Path(__file__).resolve().parent / "data"


def schema_version() -> str:
    return SCHEMA


def cache_path(design: str = "D1") -> Path:
    return ROOT / "out" / "model" / f"{design.lower()}-elements.json"


def snapshot_path(design: str = "D1") -> Path:
    return SNAPSHOT_DIR / f"{design.lower()}-elements.json"


def counts(elements: list[DesignElement]) -> dict[str, int]:
    return dict(sorted(Counter(e.kind for e in elements).items()))


def generate(design: str = "D1", *, sources: dict | None = None) -> list[DesignElement]:
    """Derive the model from the live pipeline sources. Slow (the garden plan alone is minutes)."""
    from ..concept import revit_spec as RS
    from ..concept import villa_furnish as F
    from ..concept import villa_lighting as VL
    from ..concept import villa_r11 as R
    from ..concept import villa_render as VR
    from ..concept import villa_landscape as LAND
    from . import fit_source as FS
    from . import spec_source as SS

    lay = R.design(design)
    sp = RS.build(lay)
    src = dict(sources or {})
    items = src.get("items") or F.layout(lay)
    fixtures = src.get("fx") or VL.design(lay)
    props = src.get("props") or VR.props(lay)
    if "plan" in src:
        land_props, plan = src["land_props"], src["plan"]
    else:
        _m, land_props, _n, plan = LAND.build(sp, lay)
    els = SS.all_from_spec(lay, sp, finish=VR.FINISH)
    els += FS.furniture(items) + FS.luminaires(fixtures) + FS.indoor_dressing(props) \
        + FS.plants(props, plan, land_props) + FS.garden_zones(plan)
    from . import geometry_complete as GC
    from . import validate_rules as VR_
    from .. import villa_env as E
    els = GC.complete(els, lay, sp, VR.FINISH)
    problems = validate(els) + [f"{f['rule']}: {f['element']}: {f['message']}" for f in VR_.check(els, lay, sp, E.COLUMNS)
                                if f["severity"] == "error"]
    if problems:
        raise ValueError("model is not well formed: " + "; ".join(problems[:10]))
    return els


def _payload(design: str, elements: list[DesignElement]) -> dict:
    from .schema import REVISION
    from .spec_source import LEVELS
    return dict(schema=SCHEMA, schema_revision=REVISION, contract=CONTRACT_VERSION, design=design, units="mm", levels=LEVELS,
                counts=counts(elements), elements=[asdict(e) for e in elements])


def _from_payload(data: dict) -> list[DesignElement]:
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unexpected model schema {data.get('schema')!r}")
    out = []
    for e in data["elements"]:
        e = dict(e)
        for k in ("placement", "size", "finish_codes"):
            e[k] = tuple(e.get(k, ()))
        out.append(DesignElement(**e))
    return out


def export(design: str = "D1", *, elements: list[DesignElement] | None = None, path: Path | str | None = None,
           snapshot: bool = False) -> Path:
    """Write the model JSON (default out/model/<design>-elements.json); `snapshot=True` also refreshes the committed copy."""
    elements = elements if elements is not None else generate(design)
    problems = validate(elements)
    if problems:
        raise ValueError("refusing to export a malformed model: " + "; ".join(problems[:10]))
    target = Path(path) if path else cache_path(design)
    targets = [target] + ([snapshot_path(design)] if snapshot else [])
    text = json.dumps(_payload(design, elements), indent=1, sort_keys=False)
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(text, encoding="utf-8")
    return target


def load_json(path: Path | str) -> list[DesignElement]:
    return _from_payload(json.loads(Path(path).read_text(encoding="utf-8")))


def load(design: str = "D1", *, refresh: bool = False, path: Path | str | None = None) -> list[DesignElement]:
    """The canonical model. Order of preference: explicit `path`, out/model cache, committed snapshot, generate."""
    if path:
        return load_json(path)
    if not refresh:
        for p in (cache_path(design), snapshot_path(design)):
            if p.is_file():
                return load_json(p)
    els = generate(design)
    export(design, elements=els)
    return els
