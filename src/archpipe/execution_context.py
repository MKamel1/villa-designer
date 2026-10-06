"""One fail-closed execution boundary; never infer success from log text.

Preflight resolves paths against the declared project root. The external
launch boundary requires absolute script arguments, never a tool's implicit cwd.
Only tools used by the operation are required (no Revit on render workers).
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable
import uuid
from .safe_io import save_json


DISTRIBUTION_TO_IMPORT: dict[str, str] = {
    "contourpy": "contourpy",
    "cycler": "cycler",
    "ezdxf": "ezdxf",
    "fonttools": "fonttools",
    "ifcopenshell": "ifcopenshell",
    "kiwisolver": "kiwisolver",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "packaging": "packaging",
    "pillow": "PIL",
    "pymupdf": "pymupdf",
    "pyparsing": "pyparsing",
    "python-dateutil": "dateutil",
    "pyyaml": "yaml",
    "shapely": "shapely",
    "six": "six",
    "typing_extensions": "typing_extensions",
}


def requirements_import_names(requirements_path: Path | str) -> list[str]:
    """Read a requirements file and return mapped top-level import names.

    Maps package distribution names explicitly to import names (e.g. PyYAML -> yaml,
    pillow -> PIL, shapely -> shapely, numpy -> numpy) without guessing packages
    not declared in the requirements file.
    """
    path = Path(requirements_path).resolve()
    if not path.is_file():
        raise ContextError(f"requirements missing file: {path}")
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.split("#")[0].strip()
        if not clean:
            continue
        dist = re.split(r"[=<>!~;@\s]", clean)[0].strip()
        if not dist:
            continue
        import_name = DISTRIBUTION_TO_IMPORT.get(dist.lower(), dist)
        if import_name not in names:
            names.append(import_name)
    return names


def check_dependencies(
    modules: Iterable[str],
    *,
    root: Path,
    interpreter: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Verify that declared Python modules can be located via importlib.util.find_spec.

    Uses importlib.util.find_spec without import side effects. If any module is
    missing, raises ContextError with the missing modules, the active interpreter,
    and a hint pointing to the project environment derived from root.
    """
    target_interpreter = str(interpreter or sys.executable)
    checked: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    for name in modules:
        if not name:
            continue
        try:
            spec = importlib.util.find_spec(name)
            found = spec is not None
        except (ImportError, ValueError, AttributeError):
            found = False

        checked[name] = {"found": found}
        if not found:
            missing.append(name)

    if missing:
        venv_candidate = root / ".venv"
        if os.name == "nt":
            venv_exe = venv_candidate / "Scripts" / "python.exe"
        else:
            venv_exe = venv_candidate / "bin" / "python"
        hint_path = str(
            venv_exe
            if venv_candidate.is_dir()
            else (root / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"))
        )
        missing_names = ", ".join(missing)
        raise ContextError(
            f"missing required Python module(s): {missing_names}; "
            f"interpreter: {target_interpreter}; "
            f"use the project environment (e.g. {hint_path} on Windows or the worker venv on the workstation)"
        )

    return checked


class ContextError(RuntimeError):
    """Execution must stop before launching the requested operation."""


def absolute(path, label: str, *, file: bool = False) -> Path:
    value = Path(path)
    if not value.is_absolute():
        raise ContextError(f"{label} must be absolute: {value}")
    value = value.resolve()
    if file and not value.is_file():
        raise ContextError(f"{label} missing file: {value}")
    return value


def project_path(root: Path, path, label: str, *, file: bool = False) -> Path:
    """Give relative paths one meaning, independent of the launch directory."""
    value = Path(path)
    return absolute(value if value.is_absolute() else root / value, label, file=file)


def writable_directory(path, label: str) -> Path:
    value = absolute(path, label)
    probe = value / (".context-probe-" + uuid.uuid4().hex)
    try:
        value.mkdir(parents=True, exist_ok=True)
        # Probe a CHILD directory too: Python 3.14 sandbox permissions may
        # allow parent writes while denying writes/removal in newly made dirs.
        probe.mkdir()
        data = probe / "write-read-delete"
        data.write_bytes(b"execution context")
        if data.read_bytes() != b"execution context":
            raise OSError("read-back differs")
        data.unlink()
        probe.rmdir()
    except OSError as exc:
        raise ContextError(f"{label} is not writable/readable/removable: {value}: {exc}") from exc
    return value


@dataclass(frozen=True)
class Tool:
    name: str
    path: Path
    expected_version: str
    version_args: tuple[str, ...] = ("--version",)


def resolve_tool(tool: Tool, env: dict, cwd: Path) -> dict:
    path = absolute(tool.path, tool.name, file=True)
    if not tool.expected_version:
        raise ContextError(f"{tool.name}: an expected version is required")
    try:
        result = subprocess.run([str(path), *tool.version_args], cwd=cwd, env=env,
                                stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContextError(f"{tool.name}: version probe failed: {exc}") from exc
    output = (result.stdout + result.stderr).strip()
    versions = re.findall(r"(?<![\w.])\d+\.\d+(?:\.\d+)*(?![\w.])", output)
    if result.returncode or not versions or versions[0] != tool.expected_version:
        raise ContextError(f"{tool.name}: expected version {tool.expected_version}, "
                           f"probe exit {result.returncode}, observed {output[:300]!r}")
    return {"path": str(path), "requested_path": str(tool.path), "version": tool.expected_version,
            "version_output": output, "version_exit_code": result.returncode}


def preflight(*, root: Path, scripts=(), inputs=(), output: Path, temp: Path,
              tools=(), env: dict | None = None, required_roles=(), available_roles=(),
              python_version: str | None = None, modules=(), required_modules=()) -> dict:
    """Validate, then return a JSON-safe record before any requested work.

    Python policy is 3.11 through 3.14; optional python_version pins an exact
    interpreter release. Other tools always require an exact release.
    Role availability comes from the live session, never roles.json.
    Declared modules are validated via find_spec before work commences.
    """
    root = absolute(root, "project root")
    if not root.is_dir():
        raise ContextError(f"project root missing directory: {root}")
    interpreter = absolute(sys.executable, "Python interpreter", file=True)
    version = ".".join(map(str, sys.version_info[:3]))
    if not (3, 11) <= sys.version_info[:2] <= (3, 14) or (python_version and version != python_version):
        raise ContextError(f"unsupported Python {version}; required {python_version or '3.11 through 3.14'}")
    module_list = list(modules or required_modules)
    checked_modules = check_dependencies(module_list, root=root, interpreter=interpreter)
    paths = [str(project_path(root, p, "script", file=True)) for p in scripts]
    input_paths = [str(project_path(root, p, "input", file=True)) for p in inputs]
    output = writable_directory(project_path(root, output, "output directory"), "output directory")
    temp = writable_directory(project_path(root, temp, "temporary directory"), "temporary directory")
    effective = dict(os.environ if env is None else env)
    effective.update(NO_COLOR="1", PYTHONPATH=str(root / "src"),
                     TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp))
    missing_roles = sorted(set(required_roles) - set(available_roles))
    if missing_roles:
        raise ContextError("required roles unavailable in live session: " + ", ".join(missing_roles))
    resolved = {"python": {"path": str(interpreter), "version": version}}
    for tool in tools:
        if tool.name in resolved:
            raise ContextError(f"duplicate tool: {tool.name}")
        checked_tool = Tool(tool.name, project_path(root, tool.path, tool.name, file=True),
                            tool.expected_version, tool.version_args)
        resolved[tool.name] = resolve_tool(checked_tool, effective, root)
        requested = Path(tool.path)
        resolved[tool.name]["requested_path"] = str(requested if requested.is_absolute() else root / requested)
    return {"schema": "execution-context/1", "working_directory": str(root),
            "launch_directory": str(Path.cwd().resolve()),
            "scripts": paths, "inputs": input_paths, "tools": resolved,
            "modules": checked_modules,
            "output_directory": str(output),
            "temporary_directory": str(temp), "environment": {
                key: effective[key] for key in ("NO_COLOR", "PYTHONPATH", "TMP", "TEMP", "TMPDIR")},
            "required_roles": list(required_roles), "available_roles": list(available_roles)}


def write_record(context: dict, path: Path) -> None:
    path = absolute(path, "context record")
    try:
        save_json(path, context, indent=2)
    except OSError as exc:
        raise ContextError(f"cannot write context record {path}: {exc}") from exc


def project_context(root: Path, script: Path, name: str, *, tools=(), modules=(), required_modules=()) -> dict:
    """Preflight a project entry point and configure its own process."""
    module_reqs = modules or required_modules
    context = preflight(root=root, scripts=[script], output=root / "out",
                        temp=root / "out/tmp", tools=tools, modules=module_reqs)
    os.environ.update(context["environment"])
    tempfile.tempdir = context["temporary_directory"]
    write_record(context, Path(context["output_directory"]) / (name + "-execution-context.json"))
    return context


def run_checked(argv, *, context: dict, scripts, record: Path, env=None,
                expected: Path | None = None, timeout=360):
    """Execute checked absolute paths, record exit status, require fresh output.

    expected is the artifact promised by a native tool; an exit of zero alone
    does not prove pyRevit, AutoCAD or Blender ran the script.
    """
    argv = [str(v) for v in argv]
    executable = str(absolute(argv[0], "executable", file=True))
    if executable not in [t["path"] for t in context["tools"].values()]:
        raise ContextError(f"executable has not been version-checked: {executable}")
    paths = [str(absolute(p, "script", file=True)) for p in scripts]
    if any(p not in argv for p in paths):
        raise ContextError("checked script paths must appear verbatim in command")
    root = absolute(context["working_directory"], "child working directory")
    record = project_path(root, record, "context record")
    if expected is not None:
        expected = project_path(root, expected, "expected artifact")
    effective = dict(os.environ if env is None else env)
    effective.update(context["environment"])
    run = {"execution_context": context, "argv": argv, "scripts": paths,
           "exit_code": None, "passed": False}
    write_record(run, record)
    started = time.time_ns()
    try:
        result = subprocess.run(argv, cwd=context["working_directory"], env=effective,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        run["exit_code"] = result.returncode
        run["stdout"] = result.stdout
        run["stderr"] = result.stderr
        if result.returncode:
            raise ContextError(f"command exited {result.returncode}: {argv[0]}")
        if expected and (not expected.is_file() or expected.stat().st_mtime_ns < started):
            raise ContextError(f"exit zero without fresh artifact: {expected}")
        run["passed"] = True
        return result
    except (OSError, subprocess.TimeoutExpired, ContextError) as exc:
        run["error"] = str(exc)
        raise ContextError(str(exc)) from exc
    finally:
        write_record(run, record)
