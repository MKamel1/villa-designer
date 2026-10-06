"""Import manufacturer downloads into a verified, searchable luminaire library.

    assets/user/luminaires/
        inbox/<anything>            downloads as they arrive: zip (nested), ldt, ies, rfa+txt
        <manufacturer>/<sku>/       the imported product: its files, untouched, plus product.json
        library.sqlite             one row per product LAMP SET, the search index

Files are identified by content, never by extension or a server's content
type (Signify's IES endpoint returns a zip labelled application/json). The
specification comes from the manufacturer's own file -- the LDT states flux,
colour temperature, CRI, watts and dimensions per lamp set -- and every
product is checked before it can be picked:

    flux      the LDT distribution integrates to its stated LORL
    pair      where the manufacturer also ships IES, our conversion of the
              LDT agrees with it direction by direction (catches axis and
              scaling errors in either file or in this code)
    sanity    efficacy, dimensions and colour data are plausible

A failed check keeps the product out of search results unless asked for;
it is never silently repaired.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import shutil
import sqlite3
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from archpipe import photometry as ph
from archpipe.luminaires import eulumdat as eu

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "assets/user/luminaires"

# Company line / [MANUFAC] text -> one manufacturer key. Folder names under
# inbox/ win when given (inbox/erco/... is ERCO whatever the file says).
MANUFACTURERS = {
    "signify": "signify", "philips": "signify", "erco": "erco", "zumtobel": "zumtobel",
    "thorn": "thorn", "iguzzini": "iguzzini", "i guzzini": "iguzzini", "trilux": "trilux", "ledvance": "ledvance",
    "osram": "ledvance", "fagerhult": "fagerhult", "delta light": "deltalight", "deltalight": "deltalight",
    "flos": "flos", "artemide": "artemide", "louis poulsen": "louispoulsen", "reggiani": "reggiani",
    "opple": "opple", "disano": "disano", "linea light": "linealight", "xal": "xal", "occhio": "occhio",
}

# Mount type from the product name. Inferred, and labelled so: a manufacturer
# category (catalogue pages) overrides it.
MOUNT_WORDS = [
    ("pendant", ("pendant", "suspended", "suspension", "hanging", " sp ", "pendel")),
    ("recessed", ("recessed", "downlight", "einbau", "rc1", "rc2", "rc4", "dn1", "dn5", "dn6", "trimless")),
    ("track", ("track", "3-phase", "3 phase", "stromschiene")),
    ("wall", ("wall", "wandleuchte", "sconce", "wl1", "wall-mounted")),
    ("surface", ("surface", "ceiling-mounted", "anbau", "sm1", "sm2", "sm4")),
    ("floor", ("floor lamp", "floor luminaire", "stehleuchte")),
    ("table", ("table lamp", "desk lamp", "tischleuchte")),
    ("linear", ("linear", "batten", "strip")),
    ("outdoor", ("bollard", "floodlight", "road", "street", "facade")),
]

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"     # Revit .rfa / .rvt are OLE compound files


@dataclass
class Row:
    manufacturer: str
    sku: str
    lamp_set: int
    name: str
    mount: str
    mount_basis: str
    lamp_lm: float
    luminaire_lm: float
    watts: float
    efficacy: float | None
    cct: str
    cct_k: float | None
    cri: str
    cri_ra: float | None
    beam_deg: float | None
    length_mm: float
    width_mm: float
    height_mm: float
    round: int
    lum_length_mm: float
    lum_width_mm: float
    dff: float
    lorl: float
    has_rfa: int
    has_mfr_ies: int
    flux_check: str
    pair_check: str
    sanity: str
    verified: int
    markets: str
    ldt: str
    folder: str


# ------------------------------------------------------------------ identify
def sniff(data: bytes) -> str | None:
    """'zip' | 'rfa' | 'ies' | 'ldt' | 'gldf' | 'txt' | None, by content."""
    if data[:4] == b"PK\x03\x04":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return None
        return "gldf" if any(n.lower().endswith("product.xml") for n in names) else "zip"
    if data[:8] == OLE_MAGIC:
        return "rfa"
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):          # Revit type catalogues are UTF-16
        try:
            if "##" in data.decode("utf-16")[:400]:
                return "txt"
        except UnicodeDecodeError:
            return None
    head = data[:400].decode("latin-1", "replace")
    if head.lstrip().upper().startswith("IESNA") or "TILT=" in head.upper()[:400]:
        return "ies"
    try:
        eu.parse(data.decode("latin-1"))
        return "ldt"
    except eu.LDTError:
        pass
    except Exception:
        pass
    if head.count(",") > 3 and "##" in head:          # Revit type catalogue
        return "txt"
    return None


def _walk_inbox(inbox: Path):
    """(relative origin, bytes) for every file, expanding zips recursively."""
    for p in sorted(inbox.rglob("*")):
        if p.is_file():
            yield from _expand(str(p.relative_to(inbox)), p.read_bytes(), 0)


def _expand(origin: str, data: bytes, depth: int):
    kind = sniff(data)
    if kind == "zip" and depth < 5:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if not n.endswith("/"):
                    yield from _expand(origin + "!" + n, z.read(n), depth + 1)
        return
    yield origin, data, kind


def _manufacturer(origin: str, text: str) -> str:
    top = origin.split("/")[0].split("\\")[0].lower()
    if top in MANUFACTURERS.values():
        return top
    low = text.lower()
    for k, v in MANUFACTURERS.items():
        if k in low:
            return v
    return "unknown"


def _sku_clean(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s.strip()).strip("-")[:80] or "unnamed"


def _iguzzini_code(origin: str) -> str | None:
    parts = re.split(r"[/\\]", origin)
    return parts[1].upper() if len(parts) > 2 and parts[0].lower() == "iguzzini" and re.fullmatch(r"[A-Za-z0-9]{4,8}", parts[1]) else None


def _mount(name: str) -> str:
    low = " " + name.lower() + " "
    for mount, words in MOUNT_WORDS:
        if any(w in low for w in words):
            return mount
    return "unknown"


def beam_angle(p: ph.Photometry) -> float | None:
    """Full angle (deg) where intensity falls to 50% of its nadir value, averaged
    over the C0 and C90 planes. COMPUTED from the file, not a catalogue figure.
    None for batwing or up-lighting distributions where it is undefined."""
    i0 = p.intensity(0, 0)
    if i0 <= 0 or p.peak_candela > 1.5 * i0:
        return None
    halves = []
    for h in (0.0, 90.0):
        g = 0.0
        while g < 90.0 and p.intensity(g, h) > 0.5 * i0:
            g += 0.25
        halves.append(g)
    return round(sum(halves), 1)


# --------------------------------------------------------------------- import
def import_inbox(library: Path = LIBRARY, log=print) -> dict:
    """Import everything in inbox/ and rebuild the index. Idempotent."""
    inbox = library / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    ldts, iess, rfas, txts, skipped = [], [], [], [], []
    for origin, data, kind in _walk_inbox(inbox):
        {"ldt": ldts, "ies": iess, "rfa": rfas, "txt": txts}.get(kind, skipped).append((origin, data, kind))
    products = {}
    for origin, data, _ in ldts:
        try:
            L = eu.parse(data.decode("latin-1"))
        except eu.LDTError as exc:
            skipped.append((origin, data, f"ldt error: {exc}"))
            continue
        mfr = _manufacturer(origin, L.company)
        sku = _iguzzini_code(origin) or _sku_clean(L.number or L.name)
        key = (mfr, sku)
        folder = library / mfr / sku
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{sku}.ldt").write_bytes(data)
        products.setdefault(key, {"folder": folder, "ies": [], "rfa": [], "sources": []})
        products[key]["sources"].append({"origin": origin, "sha256": hashlib.sha256(data).hexdigest(),
                                         "kind": "ldt", "imported": time.strftime("%Y-%m-%d")})
    for origin, data, _ in iess:
        text = data.decode("latin-1", "replace")
        cat = re.search(r"\[LUMCAT\]\s*(.+)", text)
        mfr = _manufacturer(origin, (re.search(r"\[MANUFAC\]\s*(.+)", text) or [None, ""])[1] or "")
        sku = _sku_clean(cat.group(1)) if cat else None
        code = _iguzzini_code(origin)
        match = next((k for k in products if (code and k == ("iguzzini", code)) or
                      (not code and sku and k[1] == sku)), None)
        if match is None:
            skipped.append((origin, data, "ies without a matching ldt (ies-only import is not yet indexed)"))
            continue
        f = products[match]["folder"] / ("mfr_" + _sku_clean(Path(origin.split("!")[-1]).name))
        f.write_bytes(data)
        products[match]["ies"].append(f)
        products[match]["sources"].append({"origin": origin, "sha256": hashlib.sha256(data).hexdigest(),
                                           "kind": "ies", "imported": time.strftime("%Y-%m-%d")})
    for origin, data, _ in rfas + txts:
        stem = Path(origin.split("!")[-1]).stem
        match = next((k for k in products if k[1] in origin or k[1] in stem), None)
        if match is None:
            # A zip named by product (Signify: "<name>.zip" holding "<name>.RFA") is
            # matched through the LDT's luminaire name.
            match = next((k for k in products if _norm(stem) and _norm(stem) in _norm(
                eu.parse((products[k]["folder"] / f"{k[1]}.ldt").read_text(encoding="latin-1")).name)), None)
        if match is None:
            skipped.append((origin, data, "rfa/txt without a matching product"))
            continue
        name = Path(origin.split("!")[-1]).name
        (products[match]["folder"] / name).write_bytes(data)
        if name.lower().endswith(".rfa"):
            products[match]["rfa"].append(products[match]["folder"] / name)
        products[match]["sources"].append({"origin": origin, "sha256": hashlib.sha256(data).hexdigest(),
                                           "kind": "rfa" if name.lower().endswith(".rfa") else "txt",
                                           "imported": time.strftime("%Y-%m-%d")})
    catalogue_db = library / "catalogue.sqlite"
    for key, prod in products.items():
        if key[0] == "iguzzini" and catalogue_db.is_file():
            con = sqlite3.connect(catalogue_db)
            try:
                row = con.execute("select mount, markets from products where manufacturer=? and sku=?", key).fetchone()
            finally:
                con.close()
            if row:
                meta_path = prod["folder"] / "product.json"
                meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
                meta.update(mount=row[0], markets=row[1].split(",") if row[1] else [])
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        _write_product(key, prod)
    n = rebuild_index(library)
    report = {"products": len(products), "rows": n, "skipped": [(o, str(k)) for o, _, k in skipped]}
    log(f"imported {len(products)} products, {n} lamp-set rows; {len(skipped)} files skipped")
    for o, k in report["skipped"][:20]:
        log(f"  skipped {o}: {k}")
    return report


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _write_product(key, prod):
    folder = prod["folder"]
    meta_path = folder / "product.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    seen = {s["sha256"] for s in meta.get("sources", [])}
    meta["manufacturer"], meta["sku"] = key
    meta["sources"] = meta.get("sources", []) + [s for s in prod["sources"] if s["sha256"] not in seen]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


# ----------------------------------------------------------------- verification
def verify_product(folder: Path) -> tuple[eu.Eulumdat, list[dict]]:
    """Parse and check one imported product; one result per lamp set."""
    L = eu.load(next(folder.glob("*.ldt")))
    flux = L.integrated_rel_flux(steps=180, azimuths=36)
    flux_ok = abs(flux - L.lorl * 10) <= max(30.0, 0.03 * L.lorl * 10)
    flux_check = f"{'ok' if flux_ok else 'FAIL'}: distribution {flux:.0f} lm/klm vs LORL {L.lorl * 10:.0f}"
    mfr_ies = sorted(folder.glob("mfr_*.ies")) + sorted(folder.glob("mfr_*.IES"))
    out = []
    for k, ls in enumerate(L.lamp_sets):
        conv = L.to_photometry(k)
        pair = "n/a: manufacturer ships no IES"
        for path in mfr_ies:
            try:
                ies = ph.load(path)
            except Exception:
                continue
            if ies.total_lumens and abs(ies.total_lumens - ls.flux_lm) > 0.01 * ls.flux_lm:
                continue                                  # a different lamp set's file
            worst = 0.0
            for g in range(0, int(min(ies.vertical[-1], conv.vertical[-1])) + 1, 5):
                for h in range(0, 360, 15):
                    a, b = ies.intensity(g, h), conv.intensity(g, h)
                    if max(a, b) > 0.02 * max(ies.peak_candela, 1e-9):
                        worst = max(worst, abs(a - b) / max(a, b))
            pair = f"{'ok' if worst < 0.02 else 'FAIL'}: worst direction {worst:.1%} vs {path.name}"
            break
        lm = L.luminaire_flux(k)
        eff = lm / ls.watts if ls.watts > 0 else None
        problems = []
        if eff is not None and not 5 <= eff <= 250:
            problems.append(f"efficacy {eff:.0f} lm/W implausible")
        if L.size_mm[0] <= 0:
            problems.append("no luminaire size")
        if ls.cct_k is None:
            problems.append(f"colour temperature not a single value ({ls.cct!r})")
        sanity = "ok" if not problems else "; ".join(problems)
        out.append({"lamp_set": k, "flux_check": flux_check, "pair_check": pair, "sanity": sanity,
                    "verified": int(flux_ok and not pair.startswith("FAIL") and not problems),
                    "beam": beam_angle(conv), "luminaire_lm": lm, "efficacy": eff})
    return L, out


def rebuild_index(library: Path = LIBRARY) -> int:
    db = library / "library.sqlite"
    rows = []
    for folder in sorted(p for p in library.glob("*/*") if p.is_dir() and (p / "product.json").is_file()):
        meta = json.loads((folder / "product.json").read_text(encoding="utf-8"))
        try:
            L, checks = verify_product(folder)
        except Exception as exc:                          # recorded, never hidden
            meta["import_error"] = str(exc)
            (folder / "product.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            continue
        mount, basis = meta.get("mount"), "manufacturer category"
        if not mount:
            mount, basis = _mount(L.name), "inferred from name"
        for c in checks:
            ls = L.lamp_sets[c["lamp_set"]]
            rows.append(Row(
                manufacturer=meta["manufacturer"], sku=meta["sku"], lamp_set=c["lamp_set"], name=L.name,
                mount=mount, mount_basis=basis, lamp_lm=ls.flux_lm, luminaire_lm=round(c["luminaire_lm"], 1),
                watts=ls.watts, efficacy=round(c["efficacy"], 1) if c["efficacy"] else None,
                cct=ls.cct, cct_k=ls.cct_k, cri=ls.cri, cri_ra=ls.cri_ra, beam_deg=c["beam"],
                length_mm=L.size_mm[0], width_mm=L.size_mm[1], height_mm=L.size_mm[2], round=int(L.round),
                lum_length_mm=L.luminous_mm[0], lum_width_mm=L.luminous_mm[1], dff=L.dff, lorl=L.lorl,
                has_rfa=int(any(folder.glob("*.[rR][fF][aA]"))), has_mfr_ies=int(any(folder.glob("mfr_*"))),
                flux_check=c["flux_check"], pair_check=c["pair_check"], sanity=c["sanity"],
                verified=c["verified"], markets=",".join(meta.get("markets", [])),
                ldt=next(folder.glob("*.ldt")).relative_to(library).as_posix(),
                folder=folder.relative_to(library).as_posix()))
    tmp = db.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    cols = list(Row.__dataclass_fields__)
    con.execute(f"create table rows ({', '.join(cols)})")
    con.executemany(f"insert into rows values ({', '.join('?' * len(cols))})",
                    [tuple(asdict(r).values()) for r in rows])
    con.commit()
    con.close()
    tmp.replace(db)
    return len(rows)


# ---------------------------------------------------------------------- query
def _portable_row(row) -> dict:
    """Decode relative index paths written on either Windows or Linux."""
    result = dict(row)
    for key in ("ldt", "folder"):
        if key in result:
            result[key] = result[key].replace("\\", "/")
    return result


class _connect:
    """Read connection that is CLOSED on exit (sqlite3's own context manager
    only commits, and left handles open)."""
    def __init__(self, library: Path = LIBRARY):
        self.con = sqlite3.connect(library / "library.sqlite")
        self.con.row_factory = sqlite3.Row

    def __enter__(self):
        return self.con

    def __exit__(self, *exc):
        self.con.close()


def search(*, library: Path = LIBRARY, manufacturer=None, mount=None, lm=None, cct=None, cri_min=None,
           beam=None, max_length_mm=None, max_width_mm=None, efficacy_min=None, market=None,
           text=None, has_rfa=None, include_unverified=False, limit=50) -> list[dict]:
    """Filter the library. `lm` and `beam` are (min, max); `cct` is a Kelvin value."""
    where, args = [], []
    def add(sql, *a):
        where.append(sql)
        args.extend(a)
    if manufacturer: add("manufacturer = ?", manufacturer.lower())
    if mount: add("mount = ?", mount)
    if lm: add("luminaire_lm between ? and ?", *lm)
    if cct is not None: add("abs(cct_k - ?) < 1", cct)
    if cri_min is not None: add("cri_ra >= ?", cri_min)
    if beam: add("beam_deg between ? and ?", *beam)
    if max_length_mm is not None: add("length_mm <= ?", max_length_mm)
    if max_width_mm is not None: add("(width_mm <= ? or round = 1)", max_width_mm)
    if efficacy_min is not None: add("efficacy >= ?", efficacy_min)
    if market: add("(',' || markets || ',') like ?", f"%,{market.upper()},%")
    if text: add("(lower(name) like ? or lower(sku) like ?)", f"%{text.lower()}%", f"%{text.lower()}%")
    if has_rfa is not None: add("has_rfa = ?", int(bool(has_rfa)))
    if not include_unverified: add("verified = 1")
    sql = "select * from rows" + (" where " + " and ".join(where) if where else "") + \
          " order by efficacy desc limit ?"
    with _connect(library) as con:
        return [_portable_row(r) for r in con.execute(sql, args + [limit])]


def get(manufacturer: str, sku: str, lamp_set: int = 0, library: Path = LIBRARY) -> dict | None:
    with _connect(library) as con:
        r = con.execute("select * from rows where manufacturer=? and sku=? and lamp_set=?",
                        (manufacturer.lower(), sku, lamp_set)).fetchone()
    return _portable_row(r) if r else None


def alternates(manufacturer: str, sku: str, lamp_set: int = 0, *, lm_tol=0.15, any_manufacturer=True,
               library: Path = LIBRARY, limit=10) -> list[dict]:
    """Products that can replace this one: same mount, same colour temperature,
    at least the same CRI, luminaire flux within +/- lm_tol, no larger."""
    base = get(manufacturer, sku, lamp_set, library)
    if base is None:
        raise KeyError(f"{manufacturer}/{sku} lamp set {lamp_set} is not in the library")
    rows = search(library=library, mount=base["mount"], cct=base["cct_k"], cri_min=base["cri_ra"],
                  lm=(base["luminaire_lm"] * (1 - lm_tol), base["luminaire_lm"] * (1 + lm_tol)),
                  manufacturer=None if any_manufacturer else manufacturer, limit=limit + 5)
    return [r for r in rows if (r["manufacturer"], r["sku"]) != (base["manufacturer"], base["sku"])][:limit]


def export_ies(manufacturer: str, sku: str, lamp_set: int, dest: Path, library: Path = LIBRARY) -> Path:
    """Write the product's lamp set as IES (the pipeline's photometry format).

    Converted from the manufacturer's LDT; `verify_product` has already
    compared that conversion with the manufacturer's own IES where one exists.
    """
    row = get(manufacturer, sku, lamp_set, library)
    if row is None:
        raise KeyError(f"{manufacturer}/{sku} lamp set {lamp_set} is not in the library")
    L = eu.load(library / row["ldt"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(L.to_ies_text(lamp_set, manufacturer=manufacturer), encoding="utf-8")
    return dest
