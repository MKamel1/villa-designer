"""Build the villa scene once, reuse it as a .blend (L8).

villa_scene.render() spends minutes importing hundreds of glTF files and draping cloth before any GPU
work. With `--blend-cache DIR` (or env ARCHPIPE_BLEND_CACHE) `install()` patches the build functions
of villa_scene so that:

  miss: the build runs normally, each wrapped call's return value is recorded, and just before
        configure_cycles() the scene is saved to DIR/<key>/ (scene.blend + state.pkl + meta.json).
  hit:  the .blend is opened and the wrapped calls return the recorded values (bpy objects by name),
        so render() carries on with the same locals it would have built.

key = sha256 of (cache format, scene.json bytes, builder source hash, Blender version, library root,
IES dir). Builder source = src/archpipe/blender/*.py and src/archpipe/*.py (conservative: any edit there
invalidates). Not in the key: the *contents* of library assets at an unchanged path.
ponytail: add an asset-manifest hash to the key if in-place library edits become a real risk.

Safety: entries are written to a temp dir, meta.json last, then renamed (atomic); a flock on
DIR/<key>.lock is held for the whole build, so concurrent jobs wait and then hit. A hit is verified
(sizes + sha256 of both files, key match); a failing entry is MOVED to DIR/_refused/ (never deleted)
and the scene is rebuilt fresh. Any failure to store (e.g. an unpicklable value) only logs; it never
fails the render.

Env ARCHPIPE_BLEND_CACHE_BUILD_ONLY=1: exit 0 as soon as the entry exists (the CPU "build once" job).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import pickle
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: the pure-python parts are still testable, locking degrades to none
    fcntl = None

FORMAT = 1
SRC = Path(__file__).resolve().parents[1]          # src/archpipe
# Build calls whose results render() keeps in locals; the first name-list entries also append to `warnings`.
WRAPPED = ("add_material", "configure_glass", "build_meshes", "build_climbers", "layered_emissive_materials",
           "import_models", "drape_cloth", "build_curtains", "import_props", "add_light")
NO_REPLAY_CALL = ("configure_glass", "build_climbers")   # mutate bpy data only; the .blend already has it
WARNS = ("add_material", "build_meshes", "build_climbers")  # take the shared `warnings` list as last arg
_held = {}                                               # key -> open lock file (miss in progress)


def log(msg):
    print("SCENE CACHE " + msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hash(root: Path = SRC) -> str:
    h = hashlib.sha256()
    for p in sorted(list((root / "blender").glob("*.py")) + list(root.glob("*.py"))):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def cache_key(scene_sha256, src_hash, blender_version, library_root, ies_dir) -> str:
    parts = [str(FORMAT), scene_sha256, src_hash, blender_version, str(library_root), str(ies_dir)]
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:24]


@contextlib.contextmanager
def file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX)
        yield fh
    finally:
        fh.close()


def verify_entry(entry: Path, key: str):
    """Return meta if entry is a complete, intact entry for key; else a reason string."""
    try:
        meta = json.loads((entry / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"no readable meta.json ({exc!r})"
    if meta.get("format") != FORMAT or meta.get("key") != key:
        return "meta does not match key/format"
    for name in ("scene.blend", "state.pkl"):
        f = entry / name
        if not f.is_file() or f.stat().st_size != meta.get(name + "_bytes"):
            return f"{name} missing or wrong size"
        if sha256_file(f) != meta.get(name + "_sha256"):
            return f"{name} sha256 mismatch (corrupt)"
    return meta


def refuse(root: Path, entry: Path, why: str):
    dest = root / "_refused" / f"{entry.name}-{int(time.time())}-{os.getpid()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.rename(entry, dest)
    log(f"REFUSED {entry.name}: {why}; moved to {dest}; rebuilding fresh")


def store_entry(root: Path, key: str, components: dict, save_blend, state_bytes: bytes):
    """Write scene.blend (via save_blend(path)), state.pkl and meta.json last into a temp dir, then rename."""
    tmp = root / f".tmp-{key}-{os.getpid()}"
    tmp.mkdir(parents=True)
    try:
        save_blend(str(tmp / "scene.blend"))
        (tmp / "state.pkl").write_bytes(state_bytes)
        meta = dict(format=FORMAT, key=key, components=components, created=time.time())
        for name in ("scene.blend", "state.pkl"):
            meta[name + "_bytes"] = (tmp / name).stat().st_size
            meta[name + "_sha256"] = sha256_file(tmp / name)
        with open(tmp / "meta.json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, root / key)
    except BaseException:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        raise


# ---- bpy state <-> pickle ------------------------------------------------------------------------

def _collections(bpy):
    t = bpy.types
    return ((t.Object, "objects"), (t.Material, "materials"), (t.Mesh, "meshes"), (t.Light, "lights"),
            (t.Image, "images"), (t.NodeTree, "node_groups"))


class _Pickler(pickle.Pickler):
    def __init__(self, fh, bpy):
        super().__init__(fh, protocol=4)
        self.bpy = bpy

    def persistent_id(self, o):
        bpy = self.bpy
        if isinstance(o, bpy.types.ID):
            for cls, coll in _collections(bpy):
                if isinstance(o, cls):
                    if o.users == 0:
                        o.use_fake_user = True   # an unused ID (e.g. a material no mesh uses) is dropped by save
                    return ("id", coll, o.name)
            raise TypeError("uncacheable bpy ID " + type(o).__name__)
        if isinstance(o, bpy.types.Node):
            for m in bpy.data.materials:
                if m.node_tree is not None and m.node_tree.as_pointer() == o.id_data.as_pointer():
                    return ("node", m.name, o.name)
            raise TypeError("node outside a material")
        mu = type(o).__module__ == "mathutils"
        if mu and hasattr(o, "col"):                     # Matrix
            return ("mu", type(o).__name__, tuple(tuple(r) for r in o))
        if mu:
            return ("mu", type(o).__name__, tuple(o))
        return None


class _Unpickler(pickle.Unpickler):
    def __init__(self, fh, bpy):
        super().__init__(fh)
        self.bpy = bpy

    def persistent_load(self, pid):
        bpy = self.bpy
        if pid[0] == "id":
            return getattr(bpy.data, pid[1])[pid[2]]
        if pid[0] == "node":
            return bpy.data.materials[pid[1]].node_tree.nodes[pid[2]]
        import mathutils
        return getattr(mathutils, pid[1])(pid[2])


def dump_state(bpy, obj) -> bytes:
    buf = io.BytesIO()
    _Pickler(buf, bpy).dump(obj)
    return buf.getvalue()


def load_state(bpy, data: bytes):
    return _Unpickler(io.BytesIO(data), bpy).load()


# ---- the hook ------------------------------------------------------------------------------------

def _recording(name, fn, calls):
    def wrapper(*a, **k):
        warn = a[-1] if name in WARNS and a and isinstance(a[-1], list) else None
        n0 = len(warn) if warn is not None else 0
        result = fn(*a, **k)
        calls.setdefault(name, []).append((result, list(warn[n0:]) if warn is not None else []))
        return result
    return wrapper


def _replaying(name, calls, counters):
    def wrapper(*a, **k):
        i = counters.get(name, 0)
        counters[name] = i + 1
        result, added = calls[name][i]
        if added and a and isinstance(a[-1], list):
            a[-1].extend(added)
        return result
    return wrapper


def install(g: dict, scene_data: dict, args) -> None:
    """Called once from villa_scene.render(); g is villa_scene's globals()."""
    root = getattr(args, "blend_cache", None) or os.environ.get("ARCHPIPE_BLEND_CACHE")
    if not root:
        return
    import bpy
    root = Path(root).expanduser().resolve()
    scene_file = getattr(args, "scene", None)
    if scene_file and os.path.isfile(scene_file):
        scene_sha = sha256_file(scene_file)
    else:  # walkthrough assembly passes no file: hash the parsed scene instead
        scene_sha = hashlib.sha256(json.dumps(scene_data, sort_keys=True, default=str).encode()).hexdigest()
    library_root = os.path.expandvars(os.path.expanduser(getattr(args, "library_root", None)
                                                         or scene_data["library_root"]))
    components = dict(scene_sha256=scene_sha, source_sha256=source_hash(), blender=bpy.app.version_string,
                      library_root=library_root, ies_dir=os.path.abspath(args.ies_dir))
    key = cache_key(components["scene_sha256"], components["source_sha256"], components["blender"],
                    library_root, components["ies_dir"])
    entry = root / key
    build_only = bool(os.environ.get("ARCHPIPE_BLEND_CACHE_BUILD_ONLY"))
    lock = file_lock(root / (key + ".lock"))
    lock.__enter__()                       # held until a hit is loaded or a miss is stored
    released = [False]

    def release():
        if not released[0]:
            released[0] = True
            lock.__exit__(None, None, None)

    if entry.exists():
        meta = verify_entry(entry, key)
        if isinstance(meta, str):
            refuse(root, entry, meta)
        else:
            t0 = time.monotonic()
            bpy.ops.wm.open_mainfile(filepath=str(entry / "scene.blend"), load_ui=False)
            try:
                calls = load_state(bpy, (entry / "state.pkl").read_bytes())
            except Exception as exc:   # the blend is already open, so cannot fall back in-process: refuse and fail loudly
                refuse(root, entry, f"state does not match scene.blend ({exc!r})")
                release()
                raise RuntimeError("scene cache entry refused; re-run to rebuild") from exc
            release()
            log(f"HIT {key}: opened in {time.monotonic() - t0:.1f}s")
            if build_only:
                raise SystemExit(0)
            counters = {}
            for name in WRAPPED:
                g[name] = _replaying(name, calls, counters)
            return
    log(f"MISS {key}: building fresh")
    calls = {}
    for name in WRAPPED:
        g[name] = _recording(name, g[name], calls)
    real_configure = g["configure_cycles"]

    def configure_then_store(cpu):
        g["configure_cycles"] = real_configure
        if "build_meshes" in calls and "import_models" in calls:   # the build ran; configure_cycles also runs alone elsewhere
            stored = False
            try:
                state = dump_state(bpy, calls)
                store_entry(root, key, components, lambda p: bpy.ops.wm.save_as_mainfile(
                    filepath=p, copy=True, compress=False, relative_remap=False), state)
                stored = True
                log(f"STORED {key}")
            except Exception as exc:   # a cache that cannot be written must not fail the render
                log(f"NOT STORED {key}: {exc!r}")
            finally:
                release()
            if build_only:
                raise SystemExit(0 if stored else 3)
        release()
        return real_configure(cpu)
    g["configure_cycles"] = configure_then_store
