# -*- coding: utf-8 -*-
"""Probe: prove a script really runs inside Revit with API access.

The smallest thing that answers the question the whole Revit branch of
the architecture rests on -- can Revit be driven from a command line at
all? It writes a JSON file; if that file appears with a real Revit
version in it, the automation path works.

Run:
    pyrevit run revit\\probe.py --revit=2026 --purge

Output path is taken from the ARCHPIPE_PROBE_OUT environment variable so
the caller decides where it lands.
"""
import datetime
import json
import os
import sys

out = {
    "ran_at": datetime.datetime.now().isoformat(),
    "python": sys.version,
    "api_ok": False,
}

try:
    from pyrevit import HOST_APP, revit

    out["api_ok"] = True
    out["revit_version"] = str(HOST_APP.version)
    out["revit_build"] = str(HOST_APP.build)
    out["revit_username"] = str(HOST_APP.username)
    out["is_family_doc"] = bool(HOST_APP.is_doc_family) if hasattr(
        HOST_APP, "is_doc_family") else None
    doc = revit.doc
    out["doc_title"] = str(doc.Title) if doc else None
    out["doc_path"] = str(doc.PathName) if doc else None
except Exception as exc:                      # noqa: BLE001 - probe reports anything
    out["error"] = "%s: %s" % (type(exc).__name__, exc)

# A second, independent check: the raw Revit API, not the pyRevit wrapper.
try:
    from Autodesk.Revit.DB import BuiltInCategory  # noqa: F401

    out["raw_revitapi_import"] = True
except Exception as exc:                      # noqa: BLE001
    out["raw_revitapi_import"] = False
    out["raw_revitapi_error"] = "%s: %s" % (type(exc).__name__, exc)

dest = os.environ.get("ARCHPIPE_PROBE_OUT")
if not dest:
    dest = os.path.join(os.path.expanduser("~"), "archpipe_probe.json")

with open(dest, "w") as fh:
    json.dump(out, fh, indent=2)
