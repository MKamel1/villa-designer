# -*- coding: utf-8 -*-
"""Extract the open Revit model to the L0 text extract.

This button is the PRIMARY export path, not a convenience wrapper. The
CLI (`pyrevit run`) launches a second Revit instance, which costs a full
startup and fails outright while another session holds the licence. Here
the model is already open: the export is immediate and there is no
licence contention.

The CLI path remains for batch work over many models, where paying
startup once is worth it.
"""
__title__ = "Extract\nModel"
__doc__ = ("Write this model to a JSON extract for the archpipe rule "
           "engine. The extract is generated output and is never "
           "hand-edited (ADR-0002).")

import os
import sys

from pyrevit import forms, revit, script

logger = script.get_logger()
output = script.get_output()

# The extractor lives beside the extension rather than inside it, so the
# same file serves both this button and the CLI. One implementation, so
# the two paths can never silently diverge.
_HERE = os.path.dirname(__file__)
_REVIT_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REVIT_DIR not in sys.path:
    sys.path.append(_REVIT_DIR)

try:
    import extract_model
except ImportError:
    forms.alert("Could not find extract_model.py.\n\nExpected beside the "
                "extension at:\n%s" % _REVIT_DIR, exitscript=True)


def main():
    doc = revit.doc
    if doc is None:
        forms.alert("No document open.", exitscript=True)

    if not doc.PathName:
        forms.alert("Save the model first.\n\nThe extract is written next "
                    "to the .rvt file, so the model needs a path.",
                    exitscript=True)

    try:
        data = extract_model.build(doc)
        dest = extract_model.destination(doc)
        import json
        with open(dest, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True,
                      separators=(",", ": "))
    except Exception as exc:
        logger.error("extract failed: %s", exc)
        forms.alert("Extract failed:\n\n%s: %s" % (type(exc).__name__, exc),
                    exitscript=True)
        return

    counts = dict((k, len(v)) for k, v in data.items() if isinstance(v, list))
    output.print_md("### Extract written")
    output.print_md("`%s`" % dest)
    for key in sorted(counts):
        output.print_md("- **%s**: %s" % (key, counts[key]))

    skipped = [w for w in data.get("walls", []) if w.get("is_curved")]
    if skipped:
        output.print_md("> %d curved wall(s) exported with end points only "
                        "- the arc is not yet represented." % len(skipped))


main()
