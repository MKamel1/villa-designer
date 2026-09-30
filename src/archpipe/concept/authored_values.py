"""Preserve authored record fields and audit deliberate replacements."""

from copy import deepcopy


def fill_defaults(record, defaults):
    """Fill absent keys only; None, zero and empty values are authored."""
    for key, value in defaults.items():
        if key not in record:
            record[key] = deepcopy(value)
    return record


def override(record, key, value, reason):
    """Replace a field with a stated reason and retain its previous value."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("an override requires a non-empty reason")
    if key not in record:
        raise KeyError("override requires an existing field: " + key)
    if record[key] != value:
        record.setdefault("overrides", []).append({
            "field": key, "prior": deepcopy(record[key]),
            "new": deepcopy(value), "reason": reason.strip(),
        })
        record[key] = deepcopy(value)
    return record
