"""Behaviour-preserving refactor audit tool.

Audits Python source changes between two versions to ensure that refactorings
do not silently drop assigned variables, function calls, or scopes.

Quick Test:
    python -c "from archpipe.refactor_audit import audit_source; print(len(audit_source('x = 1', 'pass', 't.py')))"

Example Usage:
    >>> from archpipe.refactor_audit import audit_source
    >>> findings = audit_source("a = calc()", "b = calc()", "example.py")
    >>> [f.kind for f in findings]
    ['renamed']
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Finding:
    """A single finding from comparing old and new source code."""

    path: str
    scope: str
    kind: str  # "removed", "removed_call", "removed_scope", "renamed", "moved", "allowed"
    name: str  # assigned variable name, call target, or scope name
    call: str | None = None  # primary call target associated with assignment or call
    calls: list[str] = field(default_factory=list)  # all call targets in RHS expression
    rhs: str | None = None  # RHS expression representation
    detail: str = ""
    reason: str | None = None  # justification if allowed
    is_removal: bool = True  # True if this is an un-allowed removal that fails closed

    def __str__(self) -> str:
        parts = [f"{self.path}:{self.scope}"] if self.path else [self.scope]
        if self.kind == "renamed":
            parts.append(f"renamed {self.name} -> {self.detail}")
        elif self.kind == "moved":
            parts.append(f"moved {self.name} ({self.detail})")
        elif self.kind == "allowed":
            parts.append(f"allowed removal of {self.name}: {self.reason}")
        elif self.kind == "removed_scope":
            parts.append(f"removed scope '{self.name}'")
        elif self.kind == "removed_call":
            parts.append(f"removed call '{self.name}'")
        else:
            msg = f"removed assignment '{self.name}'"
            if self.call:
                msg += f" (call: {self.call})"
            parts.append(msg)
        return " - ".join(parts)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


@dataclass
class AssignmentRecord:
    """An assignment target and its right-hand side expression details."""

    targets: list[str]
    rhs: str
    calls: list[str]


@dataclass
class ScopeData:
    """Extracted assigned names, call targets, and assignments for a scope."""

    name: str
    assigned_names: set[str] = field(default_factory=set)
    call_targets: set[str] = field(default_factory=set)
    assignments: list[AssignmentRecord] = field(default_factory=list)
    standalone_calls: set[str] = field(default_factory=set)


def _iter_scope_nodes(body: list[ast.stmt]) -> Iterable[ast.AST]:
    """Yield all nodes in body, without descending into nested function/class bodies."""
    stack = list(reversed(body))
    while stack:
        curr = stack.pop()
        yield curr
        if isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        children = list(ast.iter_child_nodes(curr))
        for child in reversed(children):
            stack.append(child)


def _extract_assigned_names_from_target(target: ast.AST) -> list[str]:
    """Extract all variable identifier names with ast.Store context from a target."""
    names: list[str] = []
    for node in ast.walk(target):
        if isinstance(node, ast.Name) and isinstance(getattr(node, "ctx", None), ast.Store):
            if node.id not in names:
                names.append(node.id)
    return names


def _extract_scope_data(scope_name: str, body: list[ast.stmt]) -> ScopeData:
    """Extract assignments, assigned names, and call targets within a single lexical scope."""
    data = ScopeData(name=scope_name)
    assignment_calls: set[str] = set()

    for node in _iter_scope_nodes(body):
        # 1. Assignments
        if isinstance(node, ast.Assign):
            targets: list[str] = []
            for t in node.targets:
                targets.extend(_extract_assigned_names_from_target(t))
            rhs_str = ast.unparse(node.value).strip()
            calls = [ast.unparse(c.func).strip() for c in ast.walk(node.value) if isinstance(c, ast.Call)]
            if targets:
                data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                data.assigned_names.update(targets)
                assignment_calls.update(calls)

        elif isinstance(node, ast.AnnAssign):
            targets = _extract_assigned_names_from_target(node.target)
            rhs_str = ast.unparse(node.value).strip() if node.value is not None else ""
            calls = (
                [ast.unparse(c.func).strip() for c in ast.walk(node.value) if isinstance(c, ast.Call)]
                if node.value is not None
                else []
            )
            if targets:
                data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                data.assigned_names.update(targets)
                assignment_calls.update(calls)

        elif isinstance(node, ast.AugAssign):
            targets = _extract_assigned_names_from_target(node.target)
            if not targets and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            rhs_str = ast.unparse(node.value).strip()
            calls = [ast.unparse(c.func).strip() for c in ast.walk(node.value) if isinstance(c, ast.Call)]
            if targets:
                data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                data.assigned_names.update(targets)
                assignment_calls.update(calls)

        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets = _extract_assigned_names_from_target(node.target)
            rhs_str = ast.unparse(node.iter).strip()
            calls = [ast.unparse(c.func).strip() for c in ast.walk(node.iter) if isinstance(c, ast.Call)]
            if targets:
                data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                data.assigned_names.update(targets)
                assignment_calls.update(calls)

        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    targets = _extract_assigned_names_from_target(item.optional_vars)
                    rhs_str = ast.unparse(item.context_expr).strip()
                    calls = [
                        ast.unparse(c.func).strip()
                        for c in ast.walk(item.context_expr)
                        if isinstance(c, ast.Call)
                    ]
                    if targets:
                        data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                        data.assigned_names.update(targets)
                        assignment_calls.update(calls)

        elif isinstance(node, ast.NamedExpr):
            targets = _extract_assigned_names_from_target(node.target)
            rhs_str = ast.unparse(node.value).strip()
            calls = [ast.unparse(c.func).strip() for c in ast.walk(node.value) if isinstance(c, ast.Call)]
            if targets:
                data.assignments.append(AssignmentRecord(targets=targets, rhs=rhs_str, calls=calls))
                data.assigned_names.update(targets)
                assignment_calls.update(calls)

        # 2. Call targets
        elif isinstance(node, ast.Call):
            target = ast.unparse(node.func).strip()
            data.call_targets.add(target)

    # Standalone calls: calls not occurring in any assignment RHS
    data.standalone_calls = data.call_targets - assignment_calls
    return data


def _collect_scopes(tree: ast.AST) -> dict[str, ScopeData]:
    """Extract all scopes and their data across a parsed AST module."""
    scopes: dict[str, ScopeData] = {}

    if isinstance(tree, ast.Module):
        scopes["<module>"] = _extract_scope_data("<module>", tree.body)

    def walk_defs(parent_name: str, body: list[ast.stmt]) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qname = f"{parent_name}.{stmt.name}" if parent_name and parent_name != "<module>" else stmt.name
                scopes[qname] = _extract_scope_data(qname, stmt.body)
                walk_defs(qname, stmt.body)
            elif isinstance(stmt, ast.ClassDef):
                qname = f"{parent_name}.{stmt.name}" if parent_name and parent_name != "<module>" else stmt.name
                scopes[qname] = _extract_scope_data(qname, stmt.body)
                walk_defs(qname, stmt.body)
            elif hasattr(stmt, "body") and isinstance(stmt.body, list):
                walk_defs(parent_name, stmt.body)
            if hasattr(stmt, "orelse") and isinstance(stmt.orelse, list):
                walk_defs(parent_name, stmt.orelse)
            if hasattr(stmt, "finalbody") and isinstance(stmt.finalbody, list):
                walk_defs(parent_name, stmt.finalbody)

    if isinstance(tree, ast.Module):
        walk_defs("<module>", tree.body)

    return scopes


def normalize_allowed(allowed: Any) -> dict[str, dict[str, str]]:
    """Normalize allowlist into {path: {name: reason}} dictionary.

    Validates that every declared removal includes a non-empty justification reason.

    Raises:
        ValueError: If any allowed removal lacks a reason.
    """
    if not allowed:
        return {}

    normalized: dict[str, dict[str, str]] = {}

    if isinstance(allowed, dict):
        for path_key, val in allowed.items():
            norm_path = Path(path_key).as_posix()
            path_map: dict[str, str] = {}

            if isinstance(val, dict):
                for name, reason in val.items():
                    if not reason or not str(reason).strip():
                        raise ValueError(
                            f"Intentional removal of '{name}' in '{path_key}' requires a non-empty reason"
                        )
                    path_map[str(name).strip()] = str(reason).strip()

            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("target") or item.get("id")
                        reason = item.get("reason") or item.get("justification")
                        if not name:
                            raise ValueError(f"Allow entry in '{path_key}' missing name: {item}")
                        if not reason or not str(reason).strip():
                            raise ValueError(
                                f"Intentional removal of '{name}' in '{path_key}' requires a non-empty reason"
                            )
                        path_map[str(name).strip()] = str(reason).strip()
                    elif isinstance(item, (tuple, list)) and len(item) == 2:
                        name, reason = item[0], item[1]
                        if not reason or not str(reason).strip():
                            raise ValueError(
                                f"Intentional removal of '{name}' in '{path_key}' requires a non-empty reason"
                            )
                        path_map[str(name).strip()] = str(reason).strip()
                    elif isinstance(item, str):
                        raise ValueError(
                            f"Intentional removal of '{item}' in '{path_key}' requires a non-empty reason"
                        )
                    else:
                        raise ValueError(f"Unsupported allow entry in '{path_key}': {item}")
            else:
                raise ValueError(f"Unsupported allow format for '{path_key}': {type(val).__name__}")

            normalized[norm_path] = path_map

    return normalized


def _get_allowed_reason(
    path: str,
    name: str,
    call: str | None,
    allowed_map: dict[str, dict[str, str]],
) -> str | None:
    """Check if name or call is allowed for the given path."""
    if not allowed_map:
        return None

    path_posix = Path(path).as_posix() if path else ""
    path_name = Path(path).name if path else ""

    for norm_path, name_map in allowed_map.items():
        if (
            norm_path == path_posix
            or norm_path == path_name
            or path_posix.endswith(norm_path)
            or norm_path.endswith(path_posix)
        ):
            if name in name_map:
                return name_map[name]
            if call and call in name_map:
                return name_map[call]

    return None


def audit_source(
    old_src: str,
    new_src: str,
    path: str = "",
    allowed: Any = None,
    removals_only: bool = False,
) -> list[Finding]:
    """Compare old and new Python source code and report removals, moves, and renames.

    Per function scope (module, defs, class methods), compares:
    (a) names assigned (ast.Store targets)
    (b) call targets (ast.unparse of Call.func)

    Moving top-level module code into a function scope is reported as 'moved'
    (is_removal=False).
    Pure renames (same RHS expression) are reported as 'renamed' (is_removal=False).
    Intentional removals with reasons in allowlist are reported as 'allowed' (is_removal=False).

    Args:
        old_src: Old Python source code text.
        new_src: New Python source code text.
        path: Path identifier of the file being audited.
        allowed: Optional dict {path: [names with reasons]} declaring intentional removals.
        removals_only: If True, return only un-allowed removals.

    Returns:
        List of Finding objects.

    Raises:
        SyntaxError: If either old_src or new_src cannot be parsed by Python ast.
        ValueError: If an entry in allowed lacks a non-empty reason.
    """
    allowed_map = normalize_allowed(allowed)

    old_tree = ast.parse(old_src, filename=path or "<old>")
    new_tree = ast.parse(new_src, filename=path or "<new>")

    old_scopes = _collect_scopes(old_tree)
    new_scopes = _collect_scopes(new_tree)

    findings: list[Finding] = []

    # Map of all new assignments by RHS across the whole new file
    all_new_assignments_by_rhs: dict[str, list[tuple[str, str]]] = {}
    for sc_name, sc_data in new_scopes.items():
        for assign in sc_data.assignments:
            if assign.rhs:
                for tgt in assign.targets:
                    all_new_assignments_by_rhs.setdefault(assign.rhs, []).append((sc_name, tgt))

    # All names and calls in any new function scope
    new_function_names: set[str] = set()
    new_function_calls: set[str] = set()
    for sc_name, sc_data in new_scopes.items():
        if sc_name != "<module>":
            new_function_names.update(sc_data.assigned_names)
            new_function_calls.update(sc_data.call_targets)

    # 1. Check for disappeared scopes
    for scope_name in old_scopes:
        if scope_name not in new_scopes:
            reason = _get_allowed_reason(path, scope_name, None, allowed_map)
            if reason:
                findings.append(
                    Finding(
                        path=path,
                        scope=scope_name,
                        kind="allowed",
                        name=scope_name,
                        reason=reason,
                        detail=f"allowed removal: {reason}",
                        is_removal=False,
                    )
                )
            else:
                findings.append(
                    Finding(
                        path=path,
                        scope=scope_name,
                        kind="removed_scope",
                        name=scope_name,
                        detail=f"Scope '{scope_name}' was removed",
                        is_removal=True,
                    )
                )

    # 2. Check each scope present in old
    for scope_name, old_data in old_scopes.items():
        if scope_name not in new_scopes:
            continue

        new_data = new_scopes[scope_name]

        # Track which calls belonged to removed assignments so we do not double-report
        accounted_calls: set[str] = set()

        # (a) Compare assigned names
        # Map of new assignments in this scope by RHS
        scope_new_by_rhs: dict[str, list[str]] = {}
        for assign in new_data.assignments:
            if assign.rhs:
                for tgt in assign.targets:
                    scope_new_by_rhs.setdefault(assign.rhs, []).append(tgt)

        for assign in old_data.assignments:
            rhs = assign.rhs
            calls = assign.calls
            primary_call = calls[0] if calls else None

            for target_name in assign.targets:
                if target_name in new_data.assigned_names:
                    # Preserved in scope
                    continue

                # Check if moved from module to a new function scope
                if scope_name == "<module>" and target_name in new_function_names:
                    findings.append(
                        Finding(
                            path=path,
                            scope=scope_name,
                            kind="moved",
                            name=target_name,
                            call=primary_call,
                            calls=calls,
                            rhs=rhs,
                            detail="moved from module to function scope",
                            is_removal=False,
                        )
                    )
                    accounted_calls.update(calls)
                    continue

                # Check pure rename in matching scope
                scope_renames = [
                    new_tgt
                    for new_tgt in scope_new_by_rhs.get(rhs, [])
                    if new_tgt not in old_data.assigned_names
                ]
                if scope_renames:
                    findings.append(
                        Finding(
                            path=path,
                            scope=scope_name,
                            kind="renamed",
                            name=target_name,
                            call=primary_call,
                            calls=calls,
                            rhs=rhs,
                            detail=f"{scope_renames[0]} (same rhs)",
                            is_removal=False,
                        )
                    )
                    accounted_calls.update(calls)
                    continue

                # Check if moved and renamed from module to a function scope
                if scope_name == "<module>":
                    file_renames = [
                        (sc, tgt)
                        for sc, tgt in all_new_assignments_by_rhs.get(rhs, [])
                        if sc != "<module>" and tgt not in old_data.assigned_names
                    ]
                    if file_renames:
                        sc, tgt = file_renames[0]
                        findings.append(
                            Finding(
                                path=path,
                                scope=scope_name,
                                kind="renamed",
                                name=target_name,
                                call=primary_call,
                                calls=calls,
                                rhs=rhs,
                                detail=f"{tgt} in {sc} (same rhs)",
                                is_removal=False,
                            )
                        )
                        accounted_calls.update(calls)
                        continue

                # Check allowlist
                reason = _get_allowed_reason(path, target_name, primary_call, allowed_map)
                if reason:
                    findings.append(
                        Finding(
                            path=path,
                            scope=scope_name,
                            kind="allowed",
                            name=target_name,
                            call=primary_call,
                            calls=calls,
                            rhs=rhs,
                            reason=reason,
                            detail=f"allowed removal: {reason}",
                            is_removal=False,
                        )
                    )
                    accounted_calls.update(calls)
                    continue

                # Otherwise: un-allowed removal of assignment
                accounted_calls.update(calls)
                findings.append(
                    Finding(
                        path=path,
                        scope=scope_name,
                        kind="removed",
                        name=target_name,
                        call=primary_call,
                        calls=calls,
                        rhs=rhs,
                        detail=f"removed assignment '{target_name}'"
                        + (f" (call: {primary_call})" if primary_call else ""),
                        is_removal=True,
                    )
                )

        # (b) Compare call targets
        missing_calls = old_data.call_targets - new_data.call_targets

        for call_target in sorted(missing_calls):
            # If call was already represented by an assignment removal finding, do not emit duplicate
            if call_target in accounted_calls:
                continue

            # Check if moved from module to a function scope
            if scope_name == "<module>" and call_target in new_function_calls:
                findings.append(
                    Finding(
                        path=path,
                        scope=scope_name,
                        kind="moved",
                        name=call_target,
                        call=call_target,
                        detail="call moved from module to function scope",
                        is_removal=False,
                    )
                )
                continue

            # Check allowlist
            reason = _get_allowed_reason(path, call_target, call_target, allowed_map)
            if reason:
                findings.append(
                    Finding(
                        path=path,
                        scope=scope_name,
                        kind="allowed",
                        name=call_target,
                        call=call_target,
                        reason=reason,
                        detail=f"allowed removal: {reason}",
                        is_removal=False,
                    )
                )
                continue

            # Un-allowed removed call
            findings.append(
                Finding(
                    path=path,
                    scope=scope_name,
                    kind="removed_call",
                    name=call_target,
                    call=call_target,
                    detail=f"removed call '{call_target}'",
                    is_removal=True,
                )
            )

    if removals_only:
        return [f for f in findings if f.is_removal]

    return findings
