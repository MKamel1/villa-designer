"""python -m archpipe.exchange --out out/exchange/D1 [--design D1] [--no-validate]

Writes D1-ARCH.ifc, D1-LIGHT.ifc, D1-ELEC.ifc, D1-B.dxf, D1-GF.dxf, D1-SITE.dxf, quantities (CSV + XLSX), validation.txt and
manifest.json (counts, sha256, validation result). Exit status 1 if any validation check fails, 2 if the model cannot be exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import ezdxf
import ifcopenshell

from ..model import api
from . import common as C
from . import disciplines as D
from . import dxf as X
from . import ifc as I
from . import quantities as Q
from . import validate as V


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def oda_converter() -> str | None:
    """Path of an ODA File Converter / Teigha binary if one is installed (needed for true .dwg), else None."""
    for n in ("ODAFileConverter", "ODAFileConverter.exe", "TeighaFileConverter"):
        if shutil.which(n):
            return shutil.which(n)
    return None


def run(out: Path, design: str = "D1", validate: bool = True) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    elements = api.load(design)
    levels = C.load_levels(design)
    files: dict[str, Path] = {}
    checks: dict[str, list[V.Check]] = {}
    try:
        for scope in ("ARCH", "LIGHT"):
            files[f"{design}-{scope}.ifc"] = I.write_ifc(elements, out / f"{design}-{scope}.ifc", levels, design, scope)
        elec = D.build_elec(elements, levels, design)
        p = out / f"{design}-ELEC.ifc"
        elec.write(str(p))
        files[p.name] = p
        dxfs = X.write_dxfs(elements, out, design)
        files.update({k: v["path"] for k, v in dxfs.items()})
        import csv
        dev = D.read_csv("device_list.csv")
        tk = Q.takeoff(elements, dev)
        for name, rows in tk.items():
            Q.write_csv(rows, out / "quantities" / f"{design}-{name}.csv")
            files[f"quantities/{design}-{name}.csv"] = out / "quantities" / f"{design}-{name}.csv"
        Q.write_xlsx(tk, out / "quantities" / f"{design}-takeoff.xlsx")
        files[f"quantities/{design}-takeoff.xlsx"] = out / "quantities" / f"{design}-takeoff.xlsx"
    except C.ExchangeError as exc:
        print(f"EXPORT REFUSED: {exc}", file=sys.stderr)
        raise
    if validate:
        for scope in ("ARCH", "LIGHT"):
            checks[f"{design}-{scope}.ifc"] = V.validate_ifc(files[f"{design}-{scope}.ifc"], elements, levels, scope)
        checks[f"{design}-LIGHT.ifc"] += V.validate_light_zones(files[f"{design}-LIGHT.ifc"], elements)
        checks[f"{design}-ELEC.ifc"] = V.validate_elec(files[f"{design}-ELEC.ifc"], elements, levels)
        checks["shared-origin"] = V.validate_shared_origin({n: files[n] for n in files if n.endswith(".ifc")})
        for r in tk["reconciliation"]:
            checks.setdefault("quantities", []).append(V.Check(r["check"], 1, abs(r["difference"]), r["tolerance"], r["unit"], r["ok"]))
        for n, f in files.items():
            if n.endswith(".dxf"):
                d = ezdxf.readfile(str(f))
                aud = ezdxf.audit.Auditor(d)
                aud.run()
                checks.setdefault("dxf", []).append(V.Check(f"{n}: audit errors, units mm", len(d.modelspace()), len(aud.errors), 0, "errors",
                                                            d.units == 4 and not aud.errors, f"$INSUNITS={d.units}"))
    text = "\n".join(f"== {k}\n{V.report_text(v)}" for k, v in checks.items())
    (out / "validation.txt").write_text(text + "\n", encoding="utf-8")
    ok = all(V.all_ok(v) for v in checks.values())
    man = dict(
        design=design, ok=ok, model_elements=len(elements), model_counts=dict(sorted(api.counts(elements).items())) if hasattr(api, "counts") else None,
        tools=dict(ifcopenshell=ifcopenshell.version, ezdxf=ezdxf.__version__), ifc_schema="IFC4",
        datum="Revit datum (B FFL -1800 mm, GF FFL +1200 mm); scene datum = Revit - 1200 mm",
        dwg=dict(produced=False, oda_file_converter=oda_converter(), note="DXF written; .dwg needs the ODA File Converter or Autodesk, not installed"),
        files={n: dict(sha256=sha256(f), bytes=f.stat().st_size) for n, f in sorted(files.items())},
        ifc_class_counts={n: dict(sorted(_class_counts(f).items())) for n, f in files.items() if n.endswith(".ifc")},
        quantities={k: len(v) for k, v in tk.items()},
        validation={k: dict(checks=len(v), failed=[c.name for c in v if not c.ok]) for k, v in checks.items()},
    )
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    return man


def _class_counts(p: Path) -> dict:
    f = ifcopenshell.open(str(p))
    c: dict[str, int] = {}
    for e in f:
        if e.is_a("IfcProduct") or e.is_a("IfcTypeObject") or e.is_a("IfcGroup"):
            c[e.is_a()] = c.get(e.is_a(), 0) + 1
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m archpipe.exchange")
    ap.add_argument("--out", default="out/exchange/D1")
    ap.add_argument("--design", default="D1")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)
    try:
        man = run(Path(a.out), a.design, not a.no_validate)
    except C.ExchangeError:
        return 2
    print(json.dumps({"ok": man["ok"], "files": len(man["files"]), "validation": man["validation"]}, indent=1))
    return 0 if man["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
