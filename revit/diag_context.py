# -*- coding: utf-8 -*-
"""Diagnostic: what does `pyrevit run <model>` actually hand the script?

Written because two reasonable assumptions were both wrong: `revit.doc`
is None in the runner, and `Application.Documents` came back empty even
with a model passed on the command line. Rather than guess a third time,
this dumps every plausible route to the document.
"""
import json
import os

out = {}


def probe(label, fn):
    try:
        out[label] = fn()
    except Exception as exc:
        out[label] = "ERR %s: %s" % (type(exc).__name__, exc)


probe("revit_obj_type", lambda: str(type(__revit__)))          # noqa: F821
probe("has_ActiveUIDocument", lambda: hasattr(__revit__, "ActiveUIDocument"))  # noqa: F821
probe("ActiveUIDocument", lambda: str(__revit__.ActiveUIDocument))  # noqa: F821
probe("app_type", lambda: str(type(__revit__.Application)))     # noqa: F821
probe("documents_count",
      lambda: sum(1 for _ in __revit__.Application.Documents))  # noqa: F821
probe("document_titles",
      lambda: [str(d.Title) for d in __revit__.Application.Documents])  # noqa: F821
probe("document_paths",
      lambda: [str(d.PathName) for d in __revit__.Application.Documents])  # noqa: F821


def _pyrevit_doc():
    from pyrevit import revit
    return {"doc": str(revit.doc), "uidoc": str(revit.uidoc),
            "docs": str(getattr(revit, "docs", None))}


probe("pyrevit_revit", _pyrevit_doc)


def _host_app():
    from pyrevit import HOST_APP
    return {"doc": str(HOST_APP.doc), "uidoc": str(HOST_APP.uidoc),
            "app": str(HOST_APP.app), "uiapp": str(HOST_APP.uiapp)}


probe("pyrevit_HOST_APP", _host_app)

# pyRevit's runner communicates through environment variables; the model
# path is very likely in one of them.
out["env_pyrevit"] = dict(
    (k, v) for k, v in os.environ.items()
    if "PYREVIT" in k.upper() or "REVIT" in k.upper() or "MODEL" in k.upper())

dest = os.environ.get("ARCHPIPE_PROBE_OUT") or os.path.join(
    os.path.expanduser("~"), "archpipe_diag.json")
with open(dest, "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
print("archpipe: diag -> %s" % dest)
