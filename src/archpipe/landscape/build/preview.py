"""Scene -> JSON spec -> Blender preview renders through jobq (L8 runner). PREVIEW only: not the production scene, not exposure-locked."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from . import policy as P

BLENDER = str(Path("~/opt/blender/blender").expanduser())
JOBQ = str(Path("~/archpipe/bin/jobq").expanduser())
SCRIPT = Path(__file__).with_name("preview_blender.py")
EYE = 1.6          # m above the garden level (assumed: the door sills are at garden level)

# Doors from the LDS inventory (src/archpipe/landscape/critic/site.doors()); stored so the preview does not import the critic stack.
DOORS = {"living": dict(id="door-B-8", at=(22.597, -26.131), faces=(1, 0)), "dining": dict(id="door-B-6", at=(16.889, -23.591), faces=(0, 1))}


def _mesh_parts(o):
    out = []
    for i, p in enumerate(o.parts):
        m = p.material
        if m == "paving-unit":
            m = "paving-unit#%d" % ((i * 7919) % 3)
        out.append(dict(material=m, verts=[[round(float(v), 5) for v in r] for r in p.verts], faces=p.faces))
    return out


def scene_spec(scene, views, size=(1500, 950), samples=96, mature_note=""):
    objs = []
    for o in scene.objects:
        d = dict(id=o.id, kind=o.kind, label=o.label, state=o.state, standin=o.standin)
        if o.parts:
            d["parts"] = _mesh_parts(o)
        if o.asset:
            d["asset"] = {k: o.asset[k] for k in ("asset_id", "gltf", "at", "bounds", "grade")}
        objs.append(d)
    return dict(ground_z=scene.ground_z, age=scene.age, objects=objs, context=scene.context, views=views, size=list(size), samples=samples, note=mature_note)


def default_views(scene, tag):
    g = scene.ground_z
    e = g + EYE
    lv, dv = DOORS["living"], DOORS["dining"]
    v = [dict(name="bird-south-east", eye=[34.5, -35.0, g + 17.0], target=[24.5, -25.3, g + 0.3], lens=32, state="closed"),
         dict(name="eye-living-door", eye=[lv["at"][0] + 0.25, lv["at"][1], e], target=[27.5, lv["at"][1] - 0.2, g + 1.0], lens=24, state="closed"),
         dict(name="eye-dining-door", eye=[dv["at"][0], dv["at"][1] + 0.25, e], target=[dv["at"][0] + 1.5, -21.0, g + 0.6], lens=24, state="closed")]
    if scene.age is not None:
        v += [dict(name="bird-north-court", eye=[-4.5, -35.0, g + 11.0], target=[1.6, -26.5, g + 0.3], lens=35, state="closed"),
              dict(name="firepit-closed", eye=[23.0, -23.6, g + 1.5], target=[25.1, -24.5, g], lens=35, state="closed"),
              dict(name="firepit-open", eye=[23.0, -23.6, g + 1.5], target=[25.1, -24.5, g], lens=35, state="open")]
    return v


def render(scene, out_dir, tag, views=None, samples=96, timeout=1500):
    """Write the spec and run Blender through jobq (GPU lock). Returns the receipt (measured asset placement, per-view files)."""
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    views = views or default_views(scene, tag)
    spec = scene_spec(scene, views, samples=samples)
    sp = Path("/tmp/ldb-specs"); sp.mkdir(exist_ok=True)
    spec_path = sp / ("%s.spec.json" % tag)
    spec_path.write_text(json.dumps(spec))
    jid = "ldb-%s-%s" % (tag, hashlib.sha1((spec_path.read_text() + SCRIPT.read_text()).encode()).hexdigest()[:10])
    cmd = [JOBQ, "submit", "--gpu", "--timeout", str(timeout), "--id", jid, "--", BLENDER, "-b", "--factory-startup", "--python-exit-code", "1",
           "-P", str(SCRIPT), "--", str(spec_path), str(out), tag]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run([JOBQ, "wait", jid], capture_output=True, text=True)
    rec = out / ("%s.receipt.json" % tag)
    if r.returncode != 0 or not rec.exists():
        raise RuntimeError("preview job %s failed (exit %s): %s; log ~/archpipe/queue/jobs/%s/job.log" % (jid, r.returncode, (r.stdout + r.stderr)[-300:], jid))
    return json.loads(rec.read_text())
