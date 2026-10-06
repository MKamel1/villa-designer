"""Deploy, render, retrieve and check villa-render/1 scenes on the workstation."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.render_qa import check
from archpipe.safe_io import save_bytes
from archpipe.stage_result import enforce_clean_verdict, validate_stage_result, write_stage_result
from archpipe.villa_render_contract import validate_scene
from archpipe.concept.villa_render import source_provenance, write as write_scene
from archpipe.execution_context import ContextError, project_context, write_record
from render_remote import _ssh, _push
from workstation import deploy, digest


def remote_preflight(host: str, release: str, job: str, blender: str) -> dict:
    """Check where Blender executes, before launching or reusing its job."""
    remote_check = [release + "/scripts/preflight.py", "--root", release,
                    "--script", release + "/src/archpipe/blender/villa_scene.py",
                    "--out", job + "/out", "--temp", job + "/tmp",
                    "--record", job + "/out/execution-context.json",
                    "--tool", "blender", blender, "4.5.14"]
    checked = _ssh(host, "cd " + shlex.quote(release) +
                   " && NO_COLOR=1 PYTHONPATH=" + shlex.quote(release + "/src") +
                   ' "$(command -v python3)" ' + shlex.join(remote_check))
    if checked.returncode:
        raise ContextError("remote preflight failed: " + checked.stderr.decode(errors="replace"))
    fetched = _ssh(host, "cat " + shlex.quote(job + "/out/execution-context.json"))
    if fetched.returncode:
        raise ContextError("remote preflight context record missing")
    try:
        context = json.loads(fetched.stdout)
        valid = (context["schema"] == "execution-context/1" and
                 context["working_directory"] == release and
                 context["tools"]["blender"]["requested_path"] == blender and
                 context["tools"]["blender"]["version"] == "4.5.14" and
                 context["environment"]["NO_COLOR"] == "1" and
                 release + "/src/archpipe/blender/villa_scene.py" in context["scripts"])
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise ContextError("remote preflight returned an incomplete or mismatched context")
    return context


def poll_remote(host: str, command: str, job: str):
    """Retry a transient read without relaunching an expensive render."""
    for attempt in range(3):
        try:
            result = _ssh(host, command, timeout=30)
            if result.returncode != 255:
                return result
            detail = result.stderr.decode(errors="replace").strip()
        except subprocess.TimeoutExpired:
            detail = "SSH read timed out after 30 seconds"
        if attempt < 2:
            time.sleep(5)
    raise RuntimeError(
        f"Lost contact with render job {job}: {detail}. "
        "The detached job may still be rendering. Rerun the identical command "
        "to retrieve its result; do not launch a different job to recover it.")


def villa_qa_context(scene: dict, view: dict, render_report: dict) -> dict:
    """Supply only measurements the villa scene actually reports."""
    ies_on = sum(l["type"] == "ies" and l["layer"] in view["layers_on"] and
                 l.get("dimmer", 1) * view.get("dimmers", {}).get(l["layer"], 1) > 0
                 for l in scene["lights"])
    day = view["state"] == "day"
    measured = render_report["qa_scene"]
    return {"subjects": render_report["subjects"],
            "exterior_camera": view["exposure"].startswith("exterior"),
            "camera": {"pitch_deg": 90 + render_report["camera_pitch_deg"],
                       "shift_y": view["camera"].get("shift_y", 0)},
            "white_balance": render_report["white_balance_applied"],
            "exposure_locked": True, "daylight": day,
            "sky": {"sun": day}, "windows": measured["windows"],
            "glass": measured["glass"], "materials": measured["materials"],
            "textiles": measured["textiles"], "soft_goods": measured["soft_goods"],
            "bedding": measured["bedding"],
            "lights": {"on": render_report["lights_on_count"] > 0 or any(
                           source.get("emitted_lumens", 0) > 0 for source in render_report.get("emissive_sources", [])),
                       "count": ies_on, "with_ies": ies_on}}


def villa_qa_scope(qa: dict, context: dict | None = None) -> dict:
    applied = [item["check"] for item in qa["checks"]]
    context = context or {}
    omitted = {}
    for prefix in ("window_view", "glass_passes_daylight", "finish_matches_name", "textile_reflectance",
                   "soft_goods_simulated", "cloth_plausible"):
        if any(name == prefix or name.startswith(prefix + ":") for name in applied):
            continue
        if prefix in ("window_view", "glass_passes_daylight"):
            omitted[prefix] = ("night view: a dark reflective window is expected" if not context.get("daylight")
                               else "no visible glass pane occupies at least 3% of this view")
        elif prefix == "finish_matches_name":
            omitted[prefix] = "no scheduled dark or black finish is present"
        elif prefix == "textile_reflectance":
            omitted[prefix] = "no textile material is present"
        elif prefix == "soft_goods_simulated":
            omitted[prefix] = "no simulated soft goods are present"
        else:
            omitted[prefix] = "no simulated duvet with measured bounds is present"
    return {"applied": applied, "omitted": omitted}


def villa_caption(scene: dict, view: dict, render_report: dict, qa: dict) -> dict:
    generic = [light["id"] for light in scene["lights"]
               if light.get("product", {}).get("generic") and light["layer"] in view["layers_on"]]
    return {"view": view["id"], "title": view.get("title", view["id"]),
            "design": {"meshes": [mesh["id"] for mesh in scene["meshes"]],
                       "lights": [light["id"] for light in scene["lights"]
                                  if light["layer"] in view["layers_on"]]},
            "view_notes": view.get("caption_notes", []),
            "assumed": scene["notes"] + render_report["warnings"],
            "generic_photometry": generic,
            "emissive_sources": render_report.get("emissive_sources", []),
            "dressing (not design)": render_report.get("imported_props", []),
            "sun": view.get("sun"), "exposure": scene["exposure"][view["exposure"]],
            "qa_checks_ran": [item["check"] for item in qa["checks"]]}


def select_views(by_id: dict, requested: str, calibrate: bool) -> list[str]:
    if requested == "none" and calibrate:
        return []
    # "review" = every view not marked final_only (the client's review drafts); "all" includes the final-only set
    selected = (list(by_id) if requested == "all" else
                [k for k, v in by_id.items() if not v.get("final_only")] if requested == "review" else
                requested.split(","))
    unknown = sorted(set(selected) - set(by_id))
    if unknown:
        raise ValueError("Unknown views: " + ", ".join(unknown))
    return selected


def run(scene_path: Path, views: str, samples: int | None, resolution: str | None,
        host: str, ies_dir: Path, dry_run: bool = False, calibrate: bool = False,
        measure_lighting: bool = False, allow_stale_scene: bool = False) -> dict:
    scene_path = scene_path.resolve()
    context = project_context(ROOT, Path(__file__).resolve(), "villa-render")
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    provenance = scene.get("provenance") or {}
    scene_hash = provenance.get("source_hash")
    current_hash = source_provenance()["source_hash"]
    stale = scene_hash != current_hash
    if stale and not allow_stale_scene:
        raise ValueError("Scene provenance mismatch: scene source hash " + str(scene_hash) +
                         " differs from current source hash " + current_hash +
                         ". Rebuild by omitting --scene, or pass --allow-stale-scene to label this render STALE-SCENE.")
    stale_label = "STALE-SCENE" if stale else None
    errors = validate_scene(scene)
    if errors:
        raise ValueError("Invalid villa scene:\n" + "\n".join(errors))
    by_id = {v["id"]: v for v in scene["views"]}
    if measure_lighting and (calibrate or views != "none"):
        raise ValueError("--measure-lighting requires --views none and no --calibrate")
    selected = select_views(by_id, views, calibrate or measure_lighting)
    ies_names = sorted({l["ies"] for l in scene["lights"] if l["type"] == "ies"})
    files = {}
    for name in ies_names:
        path = (ies_dir / name).resolve()
        if not path.is_relative_to(ies_dir.resolve()) or not path.is_file():
            raise FileNotFoundError(path)
        files[name] = path
    # Content identity means a dropped SSH session can resume the same job.
    # the renderer's own code is part of the identity: a changed renderer must not resume an old job's results
    # (it did once: a calibration after a renderer change returned the previous run's files)
    code = b"".join((ROOT / "src/archpipe/blender" / n).read_bytes() for n in ("villa_scene.py", "photoreal.py",
                                                                                 "build_scene.py", "presentation.py"))
    code += (ROOT / "src/archpipe/villa_render_contract.py").read_bytes()
    code += (ROOT / "src/archpipe/furniture_orientation.py").read_bytes()
    code += (ROOT / "src/archpipe/execution_context.py").read_bytes()
    code += (ROOT / "scripts/preflight.py").read_bytes()
    identity = digest(scene_path.read_bytes() + code + b"".join(files[n].read_bytes() for n in ies_names)
                      + json.dumps([selected, samples, resolution, calibrate, measure_lighting], sort_keys=True).encode())[:24]
    if dry_run:
        return {"dry_run": True, "views": selected, "ies": ies_names, "job_id": identity,
                "execution_context": context, "remote_preflight": "not run (dry run)",
                "host": host, "scene": str(scene_path), "scene_provenance": provenance,
                "scene_source_hash": scene_hash, "stale_scene": stale, "label": stale_label}
    root, release, release_id = deploy(host)
    job = root + "/villa-render/" + identity
    remote_ies = job + "/ies"
    result = _ssh(host, "mkdir -p " + shlex.quote(job + "/out") + " " +
                  " ".join(shlex.quote(remote_ies + "/" + n.rsplit("/", 1)[0]) for n in ies_names if "/" in n) +
                  " " + shlex.quote(remote_ies))
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    _push(host, scene_path, job + "/scene.json")
    for name, path in files.items():
        _push(host, path, remote_ies + "/" + name)
    argv = [root + "/opt/blender/blender", "-b", "--python-exit-code", "1", "-P", release + "/src/archpipe/blender/villa_scene.py",
            "--", "--scene", job + "/scene.json", "--views", "none" if not selected else ",".join(selected), "--out", job + "/out",
            "--ies-dir", remote_ies, "--library-root", scene["library_root"]]
    # Workstation Blender is installed under ~/opt, outside the archpipe root.
    argv[0] = root.rsplit("/archpipe", 1)[0] + "/opt/blender/blender"
    if samples is not None:
        argv.extend(["--samples", str(samples)])
    if resolution:
        argv.extend(["--res", resolution])
    if calibrate:
        argv.append("--calibrate")
    if measure_lighting:
        argv.append("--measure-lighting")
    # Run the same boundary on the machine that actually executes Blender.
    # Resolve python3 there, record its actual interpreter, require absolute
    # renderer paths and the pinned release from 10-blender.sh.
    remote_context = remote_preflight(host, release, job, argv[0])
    write_record({"local": context, "remote": remote_context},
                 ROOT / "out/villa-render-execution-context.json")
    command = ("cd " + shlex.quote(release) + " && NO_COLOR=1 TMP=" + shlex.quote(job + "/tmp") +
               " TEMP=" + shlex.quote(job + "/tmp") + " TMPDIR=" + shlex.quote(job + "/tmp") +
               " PYTHONPATH=" + shlex.quote(release + "/src") + " " + shlex.join(argv))
    # The shell writes status even if Blender exits nonzero. setsid and nohup
    # keep it alive when the initiating SSH connection drops.
    shell = command + " > " + shlex.quote(job + "/render.log") + " 2>&1; echo $? > " + shlex.quote(job + "/status")
    launch = ("test -f " + shlex.quote(job + "/status") + " || (test -f " + shlex.quote(job + "/pid") +
              " || (setsid nohup sh -c " + shlex.quote(shell) + " </dev/null >/dev/null 2>&1 & echo $! > " +
              shlex.quote(job + "/pid") + "))")
    result = _ssh(host, launch)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    while True:
        status = poll_remote(host, "cat " + shlex.quote(job + "/status"), job)
        if status.returncode == 0:
            break
        live = poll_remote(host, "test -f " + shlex.quote(job + "/pid") +
                           " && kill -0 $(cat " + shlex.quote(job + "/pid") + ")", job)
        if live.returncode:
            # the shell writes status and exits between our two reads: read status once more before calling the
            # job dead (a finished 24-view final was reported "stopped without status" this way)
            status = poll_remote(host, "cat " + shlex.quote(job + "/status"), job)
            if status.returncode == 0:
                break
            log = _ssh(host, "tail -n 80 " + shlex.quote(job + "/render.log"))
            raise RuntimeError("Detached Blender job stopped without status: " + log.stdout.decode(errors="replace"))
        time.sleep(10)
    if status.stdout.strip() != b"0":
        log = _ssh(host, "tail -n 80 " + shlex.quote(job + "/render.log"))
        raise RuntimeError("Blender failed: " + log.stdout.decode(errors="replace"))
    output = scene_path.parent
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for ident in selected:
        for suffix in (".png", ".json"):
            fetched = _ssh(host, "cat " + shlex.quote(job + "/out/" + ident + suffix), timeout=120)
            if fetched.returncode or not fetched.stdout:
                raise RuntimeError("Missing remote render artifact: " + ident + suffix)
            save_bytes(output / (ident + suffix), fetched.stdout)
        render_report = json.loads((output / (ident + ".json")).read_text(encoding="utf-8"))
        render_report["scene_provenance"] = provenance
        render_report["execution_context"] = {"local": context, "remote": remote_context}
        render_report["scene_source_hash"] = scene_hash
        render_report["stale_scene"] = stale
        if stale:
            render_report["label"] = stale_label
        save_bytes(output / (ident + ".json"), json.dumps(render_report, indent=2).encode("utf-8"))
        view = by_id[ident]
        # Only bedroom-agnostic checks: image metrics, camera level, subjects,
        # glass presence and white-balance availability. The bedroom-specific
        # window and fitting checks require its scene_qa geometry.
        qa_input = villa_qa_context(scene, view, render_report)
        qa = check(output / (ident + ".png"), qa_input)
        qa["scope"] = villa_qa_scope(qa, qa_input)
        qa["scene_provenance"] = provenance
        qa["scene_source_hash"] = scene_hash
        qa["stale_scene"] = stale
        if stale:
            qa["label"] = stale_label
        save_bytes(output / (ident + ".qa.json"), json.dumps(qa, indent=2).encode("utf-8"))
        caption = villa_caption(scene, view, render_report, qa)
        caption["scene_source_hash"] = scene_hash
        caption["stale_scene"] = stale
        if stale:
            caption["label"] = stale_label
        save_bytes(output / (ident + ".caption.json"), json.dumps(caption, indent=2).encode("utf-8"))
        reports.append({"view": ident, "png": str(output / (ident + ".png")), "qa_passed": qa["passed"],
                        "scene_source_hash": scene_hash, "stale_scene": stale, "label": stale_label})
    calibration = None
    if calibrate:
        for suffix in ("calibration.json", "calibration.png", "calibration.exr", "calibration-emissive.exr"):
            fetched = _ssh(host, "cat " + shlex.quote(job + "/out/" + suffix), timeout=120)
            if fetched.returncode or not fetched.stdout:
                raise RuntimeError("Missing remote calibration artifact: " + suffix)
            save_bytes(output / suffix, fetched.stdout)
        calibration = json.loads((output / "calibration.json").read_text(encoding="utf-8"))
        calibration.update(scene_provenance=provenance, scene_source_hash=scene_hash, stale_scene=stale)
        if stale:
            calibration["label"] = stale_label
        save_bytes(output / "calibration.json", json.dumps(calibration, indent=2).encode("utf-8"))
    measurements = None
    if measure_lighting:
        fetched = _ssh(host, "cat " + shlex.quote(job + "/out/lighting-measurements.json"), timeout=120)
        if fetched.returncode or not fetched.stdout:
            raise RuntimeError("Missing lighting measurements")
        save_bytes(output / "lighting-measurements.json", fetched.stdout)
        measurements = json.loads(fetched.stdout)
        measurements.update(scene_provenance=provenance, scene_source_hash=scene_hash, stale_scene=stale)
        if stale:
            measurements["label"] = stale_label
        save_bytes(output / "lighting-measurements.json", json.dumps(measurements, indent=2).encode("utf-8"))
    stage_record_path = output / "villa-render.stage-result.json"
    outputs = []
    for ident in selected:
        for suffix in (".png", ".json", ".qa.json", ".caption.json"):
            outputs.append(output / (ident + suffix))
    if calibrate:
        for suffix in ("calibration.json", "calibration.png", "calibration.exr", "calibration-emissive.exr"):
            outputs.append(output / suffix)
    if measure_lighting:
        outputs.append(output / "lighting-measurements.json")
    all_qa_passed = all(r.get("qa_passed", False) for r in reports) if reports else True
    write_stage_result(
        "villa-render",
        record_path=stage_record_path,
        inputs=[scene_path, *files.values()],
        outputs=outputs,
        exit_code=0 if (all_qa_passed and (not stale or allow_stale_scene)) else 1,
        metadata={
            "job_id": identity,
            "views_count": len(reports),
            "all_qa_passed": all_qa_passed,
            "stale_scene": stale,
            "label": stale_label,
        },
    )
    return {"release": release_id, "job_id": identity, "views": reports, "out": str(output),
            "execution_context": {"local": context, "remote": remote_context},
            "scene_provenance": provenance, "scene_source_hash": scene_hash,
            "stale_scene": stale, "label": stale_label,
            "calibration": calibration,
            "lighting_measurements": (None if measurements is None else {
                "path": str(output / "lighting-measurements.json"),
                "all_targets_met": measurements["all_targets_met"],
                "failed": [p for p in measurements["points"] if not p["meets_target"]]})}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", type=Path)
    ap.add_argument("--allow-stale-scene", action="store_true")
    ap.add_argument("--views", default="all")
    ap.add_argument("--samples", type=int)
    ap.add_argument("--res")
    ap.add_argument("--host", default="ai-workstation")
    ap.add_argument("--ies-dir", type=Path, default=ROOT / "out/villa/render-d1/ies")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--measure-lighting", action="store_true")
    a = ap.parse_args()
    try:
        project_context(ROOT, Path(__file__).resolve(), "villa-render")
    except ContextError as exc:
        ap.exit(2, "PREFLIGHT FAILED: " + str(exc) + "\n")
    if a.scene is None:
        scene_path, _ = write_scene()
    else:
        scene_path = a.scene
    try:
        result = run(scene_path, a.views, a.samples, a.res, a.host, a.ies_dir, a.dry_run, a.calibrate,
                     a.measure_lighting, a.allow_stale_scene)
    except (ValueError, ContextError) as exc:
        ap.error(str(exc))
    print(json.dumps(result, indent=2))
    if not a.dry_run:
        all_passed = all(v.get("qa_passed", True) for v in result.get("views", []))
        stale_ok = (not result.get("stale_scene")) or a.allow_stale_scene
        enforce_clean_verdict(all_passed and stale_ok, exit_code=1)


if __name__ == "__main__":
    main()
