"""V5 three engines per room: (a) analytic direct, (b) Radiance (direct = ab 0, total = ab 6), (c) Cycles render.

Same sensor points for all three (a sub-sample of each plane's engine grid), 'full' scene (every functional zone at its
fixture scale, night zones off), maintenance factor 0.8 in all. The three share the SOURCE MODEL (placement positions, aims,
photometry text, generic strip sampling) but not the transport code: (a) inverse square, (b) Radiance rtrace, (c) Cycles path
tracing with the production light/sensor constructors. A source-model error is therefore for V1/V2/V10 to catch, not V5.
Bars (LV-V5-ENG): direct within 3 %, total within 10 %, on the plane-average of the sampled points.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from .common import LayerResult, check
from .sources import ids

SRC = ids("LV-V5-ENG")
DIRECT_TOL, TOTAL_TOL = 0.03, 0.10
BLENDER = os.path.expanduser("~/opt/blender/blender")
JOBQ = os.path.expanduser("~/archpipe/bin/jobq")
ROOT = Path(__file__).resolve().parents[3]

# label -> (cluster, plane ids). Stair/circulation is the corridor plane of the circulation cluster (no stair-tread plane exists).
ROOMS = {
    "open-plan living/dining": ("B-open", ["room-living", "room-lounge", "dining-table"]),
    "kitchen": ("B-open", ["island-prep", "sink", "room-kitchen"]),
    "guest WC (small wet room)": ("B-guest-wc", ["gwc-basin", "room-guest-wc"]),
    "family bathroom": ("GF-family-bath", ["fb-basin"]),
    "stair / circulation": ("GF-circulation", ["room-corridor"]),
    "parents' bedroom": ("GF-parents-bed", ["pillow-1", "room-parents-bed"]),
    "study": ("GF-circulation", ["study-desk", "room-study-game"]),
}
PTS_PER_PLANE = 8


def sample_points(villa, plane_ids):
    from .v3_sensors import plane_points
    out = {}
    for pl in villa.planes():
        if pl.id in plane_ids:
            pts, _, _ = plane_points(pl)
            idx = sorted({round(i * (len(pts) - 1) / max(1, PTS_PER_PLANE - 1)) for i in range(min(PTS_PER_PLANE, len(pts)))})
            out[pl.id] = (pl, [(i, pts[i]) for i in idx])
    return out


def cycles_lights(villa, cluster, tmp: Path):
    from ..lightcalc.villa import cluster_of
    from ..lightcalc import villa_report as VR
    specs = []
    (tmp / "ies").mkdir(parents=True, exist_ok=True)
    for k, p in enumerate(villa.cluster_placements(cluster)):
        if p.layer in VR.NIGHT_LAYERS:
            continue
        name = "p%03d.ies" % k
        if p.meta.get("ies_path"):
            (tmp / "ies" / name).write_bytes(Path(p.meta["ies_path"]).read_bytes())
        else:
            (tmp / "ies" / name).write_text(p.meta["ies_text"], encoding="utf-8")
        specs.append(dict(id="L%03d" % k, type="ies", cct_k=2700, ies=name, lumens=p.dim * p.photometry.integrated_flux(),
                          position=list(p.position), aim=list(p.aim), spin_deg=p.spin_deg))
    return specs


def run_cycles(job: dict, workdir: Path, reuse=True) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    jp, op = workdir / "job.json", workdir / "out.json"
    job = dict(job, probe_sha=hashlib.sha1(Path(__file__).with_name("cycles_probe.py").read_bytes()).hexdigest()[:8])
    blob = json.dumps(job)
    sha = hashlib.sha1(blob.encode()).hexdigest()[:10]
    shaf = workdir / "job.sha"
    if reuse and op.exists() and shaf.exists() and shaf.read_text() == sha:
        return json.loads(op.read_text())
    op.unlink(missing_ok=True)
    jp.write_text(blob)
    shaf.write_text(sha)
    jid = "lv-cycles-%s-%s" % (workdir.name, sha)
    cmd = [JOBQ, "submit", "--gpu", "--timeout", "3000", "--cwd", str(ROOT), "--id", jid, "--", BLENDER, "-b", "-P",
           str(Path(__file__).with_name("cycles_probe.py")), "--", str(jp), str(op)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    subprocess.run([JOBQ, "wait", jid], capture_output=True, text=True)
    if not op.exists():
        raise RuntimeError("cycles job %s failed: %s %s" % (jid, r.stdout[-300:], r.stderr[-300:]))
    return json.loads(op.read_text())


def run(villa, rad_dir: Path, work: Path = ROOT / "out" / "LV" / "cycles", with_cycles=True) -> LayerResult:
    from ..lightcalc import villa_report as VR
    from ..lightcalc.direct import direct_illuminance
    from ..lightcalc.villa import MF
    L = LayerResult("V5")
    from ..lightcalc.villa import CLUSTERS, cluster_of
    by_cluster = {}
    rooms = dict(ROOMS)
    if not getattr(run, "headline_only", False):          # every other cluster too: its planes, labelled by cluster
        for cl in CLUSTERS:
            if cl not in {c for c, _ in ROOMS.values()}:
                pl = [p.id for p in villa.planes() if cluster_of(p.room) == cl]
                if pl:
                    rooms[cl] = (cl, pl)
    for label, (cl, pids) in rooms.items():
        by_cluster.setdefault(cl, []).append((label, pids))
    cyc = {}
    for cl, items in by_cluster.items():
        jf = Path(rad_dir) / (cl + ".json")
        if not jf.exists():
            for label, _ in items:
                L.results.append(check("LV5", "not_evaluated", label, (), message="no Radiance results for cluster %s" % cl))
            continue
        res = VR.ClusterRes.load(jf)
        levels = VR.full_levels(res)
        pl_all = [p for p in villa.cluster_placements(cl) if p.layer not in VR.NIGHT_LAYERS]
        want = [pid for _, ps in items for pid in ps]
        samples = sample_points(villa, set(want))
        pts_flat = [(pid, i, (x, y, samples[pid][0].z)) for pid in want if pid in samples for i, (x, y) in samples[pid][1]]
        c_out = None
        if with_cycles:
            room = villa.cluster_room(cl)
            job = dict(src=str(ROOT / "src"), ies_dir=str(work / cl / "ies"), lights=cycles_lights(villa, cl, work / cl),
                       room=dict(polygon=[list(p) for p in room.polygon], floor=room.floor_z, ceiling=room.ceiling_z,
                                 rho_floor=room.rho_floor, rho_wall=room.rho_wall, rho_ceiling=room.rho_ceiling),
                       points=[list(p[2]) for p in pts_flat], mf=MF, samples=int(os.environ.get("LV_SAMPLES", "256")), bounces=int(os.environ.get("LV_BOUNCES", "8")))
            try:
                c_out = run_cycles(job, work / cl)["readings"]
            except Exception as e:                       # a failed render is not_evaluated, never a pass
                L.notes.append("cycles %s: %s" % (cl, e))
        for label, pids in items:
            a_d, r_d, r_t, c_d, c_t = [], [], [], [], []
            for k, (pid, i, pt) in enumerate(pts_flat):
                if pid not in pids:
                    continue
                a_d.append(direct_illuminance(pl_all, pt) * MF)
                r_d.append(res.values(pid, levels, direct=True)[i])
                r_t.append(res.values(pid, levels)[i])
                if c_out:
                    c_d.append(c_out[k]["direct_lux"])
                    c_t.append(c_out[k]["total_lux"])
            if not a_d:
                continue
            m = lambda v: sum(v) / len(v)
            ad, rd, rt = m(a_d), m(r_d), m(r_t)
            row = dict(room=label, cluster=cl, n=len(a_d), analytic_direct=ad, radiance_direct=rd, radiance_total=rt,
                       ad_vs_rd=ad / rd - 1 if rd else None)
            ok = True
            msg = ["direct: analytic %.1f / Radiance %.1f lx (%+.1f %%)" % (ad, rd, 100 * row["ad_vs_rd"])]
            ok &= abs(row["ad_vs_rd"]) <= DIRECT_TOL
            if c_d:
                cd_, ct_ = m(c_d), m(c_t)
                row.update(max_point_dev_direct=max(abs(c / a - 1) for c, a in zip(c_d, a_d) if a > 5), cycles_direct=cd_, cycles_total=ct_, cd_vs_ad=cd_ / ad - 1, ct_vs_rt=ct_ / rt - 1)
                msg.append("Cycles direct %.1f lx (%+.1f %% vs analytic)" % (cd_, 100 * row["cd_vs_ad"]))
                msg.append("total: Radiance %.1f / Cycles %.1f lx (%+.1f %%)" % (rt, ct_, 100 * row["ct_vs_rt"]))
                ok &= abs(row["cd_vs_ad"]) <= DIRECT_TOL and abs(row["ct_vs_rt"]) <= TOTAL_TOL
                status = "pass" if ok else "fail"
            else:
                status = "fail" if not ok else "not_evaluated"
                msg.append("Cycles not run")
            L.table.append(row)
            L.results.append(check("LV5", status, label, SRC, achieved=round(rt, 1), unit="lx", message="; ".join(msg)))
            for r in CLUSTERS[cl]:                      # the three engines share one closed volume per cluster
                L.mark(r, status)
    return L
