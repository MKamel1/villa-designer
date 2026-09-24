# -*- coding: utf-8 -*-
"""Keep unattended Revit scripts from waiting on a person.

Measured 2026-09-24: loading a Signify family whose type catalogue lists a
parameter the family lacks ("The parameter Apparent Load doesn't exist in
the Family. It will be ignored.") raised a modal dialog, and the headless
run waited until someone clicked OK. A second attempt died the same way:
the handler read a script global after pyRevit had torn the script scope
down. So the store is bound at registration, and every dialog and every
transaction warning becomes a recorded finding instead of a hang.

    import unattended
    unattended.install(__revit__)
    t = unattended.transaction(doc, "name")   # warnings recorded, not shown
    ...
    report["revit_messages"] = unattended.MESSAGES
    unattended.uninstall(__revit__)
"""
from Autodesk.Revit.DB import FailureProcessingResult, FailureSeverity, IFailuresPreprocessor, Transaction

MESSAGES = []


def _answer(sender, args, _store=MESSAGES):
    _store.append({"kind": "dialog", "id": getattr(args, "DialogId", ""),
                   "message": getattr(args, "Message", "")})
    try:
        args.OverrideResult(1)                     # IDOK
    except Exception:
        pass


class RecordWarnings(IFailuresPreprocessor):
    store = MESSAGES

    def PreprocessFailures(self, accessor):
        for f in accessor.GetFailureMessages():
            if f.GetSeverity() == FailureSeverity.Warning:
                self.store.append({"kind": "warning", "message": f.GetDescriptionText()})
                accessor.DeleteWarning(f)
        return FailureProcessingResult.Continue


def install(uiapp):
    uiapp.DialogBoxShowing += _answer


def uninstall(uiapp):
    try:
        uiapp.DialogBoxShowing -= _answer
    except Exception:
        pass


def transaction(doc, name):
    t = Transaction(doc, name)
    opts = t.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(RecordWarnings())
    t.SetFailureHandlingOptions(opts)
    return t
