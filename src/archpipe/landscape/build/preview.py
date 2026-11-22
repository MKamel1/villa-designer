"""Scene -> JSON spec -> Blender preview renders through jobq (L8 runner). PREVIEW only: not the production scene, not exposure-locked."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from . import guard

from . import policy as P

BLENDER = str(Path("~/opt/blender/blender").expanduser())
JOBQ = str(Path("~/archpipe/bin/jobq").expanduser())
SCRIPT = Path(__file__).with_name("preview_blender.py")
EXPOSURE = {"bird": -2.0, "eye": -2.0, "court": -2.0, "pond": -2.0, "grape": -2.0, "vis": -2.0}   # fixed per view group (tuned from the test renders, see LDB.md)
EYE = 1.6          # m above the garden level (assumed: the door sills are at garden level)

# Doors from the LDS inventory (src/archpipe/landscape/critic/site.doors()); stored so the preview does not import the critic stack.
DOORS = {"living": dict(id="door-B-8", at=(22.597, -26.131), faces=(1, 0)), "dining": dict(id="door-B-6", at=(16.889, -23.591), faces=(0, 1))}


def _mesh_parts(o):
    out = []
    for i, p in enumerate(o.parts):
        m = p.material
        if m == "paving-unit":
            m = "paving-unit#%d" % ((i * 7919) % 3)
        faces = p.faces
        if m == "water":                       # the water solid is kept whole for measurement; only its top face is rendered (a surface, not a glass block)
            zt = float(p.verts[:, 2].max())
            faces = [f for f in faces if all(abs(float(p.verts[i, 2]) - zt) < 1e-6 for i in f)]
        out.append(dict(material=m, verts=[[round(float(v), 5) for v in r] for r in p.verts], faces=faces))
    return out


def scene_spec(scene, views, size=(1500, 950), samples=96, device="GPU"):
    objs = []
    for o in scene.objects:
        d = dict(id=o.id, kind=o.kind, label=o.label, state=o.state, standin=o.standin)
        if o.parts:
            d["parts"] = _mesh_parts(o)
        if o.asset:
            d["asset"] = {k: o.asset[k] for k in ("asset_id", "gltf", "at", "bounds", "grade", "mode", "scale_xyz", "box_m", "length_m", "yaw_deg", "tiles") if k in o.asset}
        objs.append(d)
    ponds = [o.meta for o in scene.objects if o.kind == "pond"]
    wr = [min(m["floor_z"] for m in ponds), max(m["water_z"] for m in ponds)] if ponds else None
    return dict(pond_rects=[list(m['rect']) for m in ponds], water_range=wr, ground_z=scene.ground_z, age=scene.age, season=scene.season, objects=objs, context=scene.context, views=views, size=list(size), samples=samples, device=device)


def default_views(scene, tag):
    """The review set, grouped so the exposure can be fixed per group: bird (south garden), eye (door / dining -> fire pit), court (north court pond, east yard pond), grape."""
    g = scene.ground_z
    e = g + EYE
    sp = scene.spec
    lv = DOORS["living"]
    v = [dict(name="bird-south-east", group="bird", eye=[29.5, -33.0, g + 15.5], target=[22.3, -25.2, g + 0.3], lens=34, state="closed", hide_house=True),
         dict(name="eye-living-door", group="eye", eye=[lv["at"][0] + 0.25, lv["at"][1], e], target=[27.5, lv["at"][1] - 0.2, g + 1.0], lens=24, state="closed")]
    if sp.get("pit") and sp.get("table"):
        px, py = sp["pit"]
        tx, ty = sp["table"]
        v.append(dict(name="eye-dining-firepit", group="eye", eye=[tx, ty + 3.0, e], target=[px, py + 0.2, g + 0.9], lens=26, state="closed"))
        v.append(dict(name="firepit-open", group="eye", eye=[px - 0.6, py + 3.2, g + 1.5], target=[px, py + 0.3, g], lens=30, state="open"))
        v.append(dict(name="firepit-closed", group="eye", eye=[px - 0.6, py + 3.2, g + 1.5], target=[px, py + 0.3, g], lens=30, state="closed"))
    for pid, r in sorted(sp.get("ponds", {}).items()):
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if pid.startswith("n"):
            v.append(dict(name="court-north-pond", group="court", eye=[r[2] + 1.6, r[1] - 3.6, g + 3.0], target=[cx, cy, g - 0.2], lens=22, state="closed", hide_house=True))
        else:
            v.append(dict(name="yard-east-pond", group="court", eye=[r[2] + 2.6, r[1] - 1.5, g + 1.9], target=[cx, cy, g - 0.2], lens=24, state="closed"))
        if pid.startswith("n"):
            v.append(dict(name="pond-close-" + pid, group="pond", eye=[cx + 1.9, cy - 2.2, g + 2.1], target=[cx, cy, g - 0.35], lens=32, state="closed", hide_house=True))
        else:
            v.append(dict(name="pond-close-" + pid, group="pond", eye=[r[2] + 2.4, r[1] - 1.1, g + 1.6], target=[cx, cy, g - 0.35], lens=34, state="closed"))
    for o in scene.objects:
        if o.kind == "plant" and o.meta.get("deciduous") and o.meta.get("climbing"):
            b = o.bounds()
            c = ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2)
            thin_x = (b[3] - b[0]) < (b[4] - b[1])
            gc = (25.3, -26.0)
            back = (np.sign(gc[0] - c[0]) * 4.2, 0.0) if thin_x else (0.0, np.sign(gc[1] - c[1]) * 4.2)
            v.append(dict(name="grape-" + scene.season, group="grape", eye=[c[0] + back[0], c[1] + back[1], g + 1.6], target=[c[0], c[1], g + 1.6], lens=26, state="closed"))
            break
    if scene.visualisation_only:
        v = [dict(name="vis-bird", group="vis", eye=[34.5, -30.0, g + 17.0], target=[24.3, -30.0, g + 0.2], lens=30, state="closed", hide_house=True)]
    return v


def render(scene, out_dir, tag, views=None, samples=96, timeout=3000, gpu=True, size=(1500, 950)):
    """Write the spec and run Blender through jobq (GPU lock). Returns the receipt (measured asset placement, per-view files)."""
    out = Path(out_dir).resolve()
    if scene.visualisation_only and "visualisation" not in out.parts:
        raise guard.VisualisationOnlyError("a visualisation-only scene may only be rendered into a directory named 'visualisation' (got %s)" % out)
    if not scene.visualisation_only and guard.has_vis(scene):
        raise guard.VisualisationOnlyError("a scene with visualisation-only objects must be flagged visualisation_only")
    out.mkdir(parents=True, exist_ok=True)
    views = views or default_views(scene, tag)
    spec = scene_spec(scene, views, size=size, samples=samples, device="GPU" if gpu else "CPU")
    spec["exposure_by_group"] = dict(EXPOSURE)
    sp = Path("/tmp/ldb-specs"); sp.mkdir(exist_ok=True)
    spec_path = sp / ("%s.spec.json" % tag)
    spec_path.write_text(json.dumps(spec))
    jid = "ldb-%s-%s" % (tag, hashlib.sha1((spec_path.read_text() + SCRIPT.read_text()).encode()).hexdigest()[:10])
    cmd = [JOBQ, "submit", *(["--gpu"] if gpu else []), "--timeout", str(timeout), "--id", jid, "--", BLENDER, "-b", "--factory-startup", "--python-exit-code", "1",
           "-P", str(SCRIPT), "--", str(spec_path), str(out), tag]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run([JOBQ, "wait", jid], capture_output=True, text=True)
    rec = out / ("%s.receipt.json" % tag)
    if r.returncode != 0 or not rec.exists():
        raise RuntimeError("preview job %s failed (exit %s): %s; log ~/archpipe/queue/jobs/%s/job.log" % (jid, r.returncode, (r.stdout + r.stderr)[-300:], jid))
    receipt = json.loads(rec.read_text())
    if scene.visualisation_only:                       # a red band in EVERY image; the receipt says so
        from .visualisation import band_present, stamp_band
        for v in receipt["views"]:
            stamp_band(v["file"])
            v["band"] = band_present(v["file"])
        receipt["visualisation_only"] = True
        rec.write_text(json.dumps(receipt, indent=1))
    return receipt
