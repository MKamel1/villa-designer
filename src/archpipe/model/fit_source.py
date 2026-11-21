"""Design-model elements for furniture, luminaires, plants and gardens (the slower sources: ~minutes).

Sources: `villa_furnish.layout` (checked furniture layout), `villa_lighting.design` + `fixture_record` (luminaires with
their bound manufacturer photometry), `villa_render.props` and `villa_landscape.build` (dressing and the garden plan).
Everything is passed in, so a caller may build each source once.
"""
from __future__ import annotations

from ..contracts import DesignElement
from .spec_source import LEVELS, mm, poly_area_m2, rect_poly_mm

LEVEL_FFL_M = {k: v["ffl_scene_mm"] / 1000.0 for k, v in LEVELS.items()}


def _rel(abs_z_m: float, level: str) -> float:
    return mm(abs_z_m - LEVEL_FFL_M[level])


def furniture(items) -> list[DesignElement]:
    out = []
    for it in items:
        lv = it.get("level", "B")
        known = {"id", "room", "type", "cx", "cy", "rot", "w", "d", "h", "why", "level", "asset"}
        out.append(DesignElement(
            id=f"furn-{it['id']}", kind="furniture", level=lv,
            placement=(mm(it["cx"]), mm(it["cy"]), 0.0), rotation_deg=float(it.get("rot", 0)),
            size=(mm(it["w"]), mm(it["d"]), mm(it["h"])), room=it["room"],
            product_id=str(it.get("asset") or ""),
            params=dict(type=it["type"], why=it.get("why", ""),
                        extra={k: v for k, v in it.items() if k not in known and _plain(v)})))
    return out


def _plain(v) -> bool:
    return isinstance(v, (str, int, float, bool, type(None))) or (
        isinstance(v, (list, tuple)) and all(_plain(x) for x in v))


def _ies_ref(path: str) -> str:
    """Repository-relative photometry reference, never an absolute machine path."""
    p = str(path).replace("\\", "/")
    i = p.find("out/villa/render-d1/ies/")
    if i >= 0:
        return p[i:]
    j = p.find("knowledge/lighting/ies/")          # L6c: the bound ERCO files live in the repo, not under out/
    return p[j:] if j >= 0 else p


def luminaires(fixtures) -> list[DesignElement]:
    out = []
    for f in fixtures:
        rec = f.record
        prod = dict(rec.product)
        req = dict(rec.definition.requirement)
        ies = _ies_ref(prod.get("ies", ""))
        out.append(DesignElement(
            id=f"lum-{f.id}", kind="luminaire", level=f.level,
            placement=(mm(f.x), mm(f.y), _rel(f.z, f.level)), room=f.room,
            product_id=f"{prod.get('manufacturer', '')}/{prod.get('code', '')}".strip("/"),
            size=(mm(f.length) if f.length else 0.0, 0.0, 0.0),
            params=dict(
                fixture_kind=f.kind, layer=f.layer, mount=req.get("mount", ""), what=req.get("what", ""),
                flux_lm=round(rec.flux_lm, 1), watts=prod.get("watts"), cct_k=prod.get("cct", req.get("cct")),
                cri=req.get("cri"), beam_deg=prod.get("beam", req.get("beam")),
                photometry=dict(manufacturer=prod.get("manufacturer", ""), code=prod.get("code", ""), ies=ies,
                                substitute=bool(prod.get("substitute", False)),
                                generic=not bool(prod.get("manufacturer"))),
                aim=list(f.aim), along=list(f.along), length_mm=mm(f.length), illuminance_card=f.card,
                why=f.why, emitter_z_scene_mm=mm(f.z))))
    return out


def plants(props, land_plan, land_props) -> list[DesignElement]:
    out, seen = [], set()
    for p in list(land_plan.get("plants", [])):
        c = p.get("center") or p["position"][:2]
        out.append(DesignElement(
            id=f"plant-{p['id']}", kind="plant", level="SITE",
            placement=(mm(c[0]), mm(c[1]), 0.0), size=(mm(p.get("spread_m", 0.0)), mm(p.get("spread_m", 0.0)),
                                                         mm(p.get("height_m", 0.0))),
            product_id=str(p.get("asset", "")),
            params=dict(species=p.get("species", ""), bed=p.get("bed", ""), layer=p.get("planting_layer", ""),
                        spread_m=p.get("spread_m"), height_m=p.get("height_m"), source="garden plan")))
        seen.add(p["id"])
    for p in land_props:
        if p["id"] in seen or "species" not in p:
            continue
        pos = p["position"]
        out.append(DesignElement(
            id=f"plant-{p['id']}", kind="plant", level="SITE", placement=(mm(pos[0]), mm(pos[1]), mm(pos[2] + 3.0)),
            product_id=str(p.get("asset", "")),
            params=dict(species=p["species"], bed=p.get("bed", ""), layer=p.get("planting_layer", ""),
                        spread_m=p.get("spread_m"), scale=p.get("scale"), source="garden props")))
        seen.add(p["id"])
    return out


def indoor_dressing(props) -> list[DesignElement]:
    """Props that are not plants: books, vases, art, bowls (dressing, not design)."""
    out = []
    for p in props:
        pos = p["position"]
        out.append(DesignElement(
            id=f"prop-{p['id']}", kind="furniture", level="GF" if pos[2] >= -0.5 else "B",
            placement=(mm(pos[0]), mm(pos[1]), mm(pos[2]) - (0 if pos[2] >= -0.5 else -3000.0)),
            rotation_deg=float(p.get("rotation_deg", [0, 0, 0])[2]), product_id=str(p.get("asset", "")),
            room=p.get("room", ""),
            params=dict(type="dressing", label=p.get("label", ""), scale=p.get("scale", 1.0),
                        plant=("species" in p))))
    return out


def garden_zones(land_plan) -> list[DesignElement]:
    out = []
    for name, rect in {**land_plan.get("beds", {}), **land_plan.get("accent_beds", {})}.items():
        out.append(DesignElement(
            id=f"garden-bed-{name}", kind="garden", level="SITE",
            placement=(mm((rect[0] + rect[2]) / 2), mm((rect[1] + rect[3]) / 2), 0.0),
            size=(mm(rect[2] - rect[0]), mm(rect[3] - rect[1]), 0.0),
            params=dict(role="planting bed", polygon_mm=rect_poly_mm(rect), area_m2=poly_area_m2(rect_poly_mm(rect)))))
    for name, rect in land_plan.get("paths", {}).items():
        out.append(DesignElement(
            id=f"garden-path-{name}", kind="garden", level="SITE",
            placement=(mm((rect[0] + rect[2]) / 2), mm((rect[1] + rect[3]) / 2), 0.0),
            size=(mm(rect[2] - rect[0]), mm(rect[3] - rect[1]), 0.0),
            params=dict(role="path", polygon_mm=rect_poly_mm(rect), area_m2=poly_area_m2(rect_poly_mm(rect)))))
    return out
