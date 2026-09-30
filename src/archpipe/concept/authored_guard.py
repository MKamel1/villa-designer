"""Compare declared values with exported values and their override chain."""


def unexplained_changes(declared, written, fields):
    """Return fields whose value changed without a complete reasoned audit chain."""
    changes = []
    entries = written.get("overrides", [])
    for field in fields:
        if field not in declared:
            continue
        if field not in written:
            changes.append(field)
            continue
        prior = declared[field]
        chain = [entry for entry in entries if entry.get("field") == field]
        valid = True
        for entry in chain:
            if entry.get("prior") != prior or not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
                valid = False
                break
            prior = entry.get("new")
        if not valid or written.get(field) != prior:
            changes.append(field)
    return changes
