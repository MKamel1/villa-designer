# -*- coding: utf-8 -*-
"""Enumerate Revit 2027's built-in MCP tools, from inside Revit.

    pyrevit run "<abs>\\revit\\dump_mcp_tools.py" --revit=2027

Revit 2027 ships an AI Assistant built on the official Model Context
Protocol SDK. Its journal registers a debug command `ID_DEBUG_DUMP_MCP_TOOLS`,
and `Autodesk.MCP.Tools.ToolsExposer` has a `GetPublicToolDefinitions`
method. Posting the command needs an interactive UI session and runs
asynchronously; calling the method by reflection does not, so that is what
this does.

WHY BOTHER, RATHER THAN READ THE STRINGS OUT OF THE DLL

Strings tell you a type called `SheetView` exists. They do not tell you a
tool's name, its parameters, or whether it is exposed at all. The
difference matters before we decide to build on it: a capability we can
call is worth planning around, a type name is not.

WHAT IT MIGHT NOT DO

The Assistant loads in its own assembly-load context
(`AUTODESKASSISTANT`), and its dependencies are .NET 10 assemblies that
live beside it rather than next to Revit.exe. If reflection cannot
resolve them, this reports that plainly instead of half a list -- an
incomplete inventory presented as complete is worse than none.

Output: `ARCHPIPE_MCP_OUT` or `%USERPROFILE%\\archpipe_mcp_tools.json`.
"""
import json
import os
import traceback

import clr  # noqa: F401  (pythonnet/IronPython .NET bridge)
from System import Activator
from System.IO import Path as IOPath
from System.Reflection import Assembly, BindingFlags

ASSISTANT_DIRS = [
    r"C:\Program Files\Autodesk\Revit Assistant 2027\27.2.0",
    r"C:\Program Files\Autodesk\Revit 2027\AddIns\Assistant",
]

out = {"ok": False, "tools": [], "notes": []}


def note(msg):
    out["notes"].append(str(msg))


def find_assistant_dir():
    for d in ASSISTANT_DIRS:
        if os.path.isdir(d):
            return d
    # Fall back to any version folder under the Assistant root.
    root = r"C:\Program Files\Autodesk\Revit Assistant 2027"
    if os.path.isdir(root):
        for name in sorted(os.listdir(root), reverse=True):
            cand = os.path.join(root, name)
            if os.path.isdir(cand):
                return cand
    return None


def load_with_dependencies(directory):
    """Load the tools assembly, resolving its neighbours by hand.

    The Assistant's dependencies are not on Revit's probing path, so a
    plain LoadFrom raises FileNotFoundException on the first transitive
    reference. Registering a resolver that looks in the same folder is the
    smallest thing that works.
    """
    from System import ResolveEventHandler
    from System.AppDomain import CurrentDomain  # noqa: F401

    def resolver(sender, args):
        simple = args.Name.split(",")[0]
        cand = os.path.join(directory, simple + ".dll")
        if os.path.isfile(cand):
            try:
                return Assembly.LoadFrom(cand)
            except Exception:
                return None
        return None

    try:
        import System
        System.AppDomain.CurrentDomain.AssemblyResolve += ResolveEventHandler(resolver)
        note("assembly resolver registered for %s" % directory)
    except Exception as exc:
        note("could not register resolver: %s" % exc)

    path = os.path.join(directory, "Autodesk.Assistant.Tools.dll")
    if not os.path.isfile(path):
        raise IOError("Autodesk.Assistant.Tools.dll not found in %s" % directory)
    return Assembly.LoadFrom(path)


def describe_tool(obj):
    """Pull whatever a tool definition object will give us."""
    rec = {}
    t = obj.GetType()
    rec["_type"] = t.FullName
    for prop in t.GetProperties():
        try:
            val = prop.GetValue(obj, None)
        except Exception:
            continue
        if val is None:
            continue
        name = prop.Name
        try:
            if isinstance(val, (int, float, bool)):
                rec[name] = val
            else:
                s = str(val)
                rec[name] = s if len(s) < 4000 else s[:4000] + "...(truncated)"
        except Exception:
            pass
    return rec


try:
    directory = find_assistant_dir()
    if not directory:
        raise IOError("Revit Assistant 2027 directory not found")
    note("assistant dir: %s" % directory)

    asm = load_with_dependencies(directory)
    note("loaded: %s" % asm.FullName)

    types = []
    try:
        types = list(asm.GetTypes())
    except Exception as exc:
        # ReflectionTypeLoadException still carries the types it managed
        # to load; a partial list is useful as long as it says so.
        loaded = getattr(exc, "Types", None)
        if loaded:
            types = [t for t in loaded if t is not None]
            note("partial type load: %d types, some dependencies missing"
                 % len(types))
        else:
            raise

    out["type_count"] = len(types)
    out["tool_namespaces"] = sorted(set(
        t.Namespace for t in types
        if t.Namespace and "MCP" in t.Namespace))

    exposer = next((t for t in types if t.Name == "ToolsExposer"), None)
    if exposer is None:
        note("ToolsExposer type not found")
    else:
        note("ToolsExposer: %s" % exposer.FullName)
        flags = (BindingFlags.Public | BindingFlags.NonPublic
                 | BindingFlags.Static | BindingFlags.Instance)
        methods = [m.Name for m in exposer.GetMethods(flags)]
        out["exposer_methods"] = sorted(set(methods))

        # Record every signature: ToolsExposer turned out to be abstract
        # and the With* selectors take arguments, so guessing costs a
        # round trip each time.
        sigs = []
        for m in exposer.GetMethods(flags):
            if m.DeclaringType and m.DeclaringType.Name == "ToolsExposer":
                sigs.append("%s %s(%s)" % (
                    m.ReturnType.Name, m.Name,
                    ", ".join("%s %s" % (pp.ParameterType.Name, pp.Name)
                              for pp in m.GetParameters())))
        out["exposer_signatures"] = sorted(set(sigs))

        # The public set first -- this is what a third-party MCP client
        # would actually be offered.
        for m in exposer.GetMethods(flags):
            if (m.Name == "GetPublicToolDefinitions"
                    and len(m.GetParameters()) == 0 and m.IsStatic):
                for item in m.Invoke(None, None):
                    rec = describe_tool(item)
                    rec["_scope"] = "public"
                    out["tools"].append(rec)
                out["ok"] = True
                break

        # The full inventory. BuildToolDefinition takes a
        # ToolDiscovery.ToolInfo, not a Type -- and the With*Tools
        # selectors take an IMcpServerBuilder, i.e. they are ASP.NET Core
        # server-registration extensions rather than a way to list things.
        # ToolDiscovery.DiscoverAll() is the route that needs no server.
        discovery = next((t for t in types if t.Name == "ToolDiscovery"), None)
        builder = None
        for m in exposer.GetMethods(flags):
            if m.Name == "BuildToolDefinition":
                builder = m
                break
        if discovery is None or builder is None:
            note("ToolDiscovery or BuildToolDefinition unavailable")
        else:
            disc = None
            for m in discovery.GetMethods(flags):
                if m.Name == "DiscoverAll" and len(m.GetParameters()) == 0:
                    disc = m
                    break
            if disc is None:
                note("DiscoverAll() not found with zero args")
            else:
                try:
                    infos = disc.Invoke(None if disc.IsStatic else
                                        Activator.CreateInstance(discovery), None)
                    known = set(t.get("Name") for t in out["tools"])
                    count = 0
                    for info in infos:
                        count += 1
                        try:
                            val = builder.Invoke(None, (info,))
                            rec = describe_tool(val)
                        except Exception as exc:
                            out.setdefault("build_failures", []).append(
                                str(exc)[:160])
                            continue
                        nm = rec.get("Name")
                        if nm and nm not in known:
                            rec["_scope"] = "private"
                            out["tools"].append(rec)
                            known.add(nm)
                        elif nm:
                            for existing in out["tools"]:
                                if existing.get("Name") == nm:
                                    existing["_scope"] = "public"
                    out["discovered"] = count
                    out["ok"] = True
                except Exception as exc:
                    note("DiscoverAll failed: %s" % exc)

    # Even without the exposer, the tool CLASSES are informative.
    out["tool_classes"] = sorted(
        t.FullName for t in types
        if t.Namespace and "Autodesk.MCP.Tools.Tools" in t.Namespace
        and not t.Name.startswith("<"))

except Exception:
    out["error"] = traceback.format_exc()

dest = os.environ.get("ARCHPIPE_MCP_OUT") or os.path.join(
    os.environ.get("USERPROFILE", "."), "archpipe_mcp_tools.json")
with open(dest, "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
print("archpipe: mcp tools -> %s (ok=%s, tools=%d)"
      % (dest, out["ok"], len(out["tools"])))
