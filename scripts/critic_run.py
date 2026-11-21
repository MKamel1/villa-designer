"""Render critic CLI.

    python scripts/critic_run.py out/villa/finals-2026-10-15/v27-east-yard-above.png
    python scripts/critic_run.py out/villa/finals-2026-10-15 --vlm ssh
    python scripts/critic_run.py some.png --vlm off          # deterministic only; verdict fails closed

Prints one RenderVerdict JSON per image and writes the CheckResult records to out/checks/L3.json.
--vlm ssh : copies a 1280 px jpg to the GPU workstation, runs scripts/critic_vlm_batch.py under
            `flock ~/archpipe/locks/graphics.lock`, fetches the scores (about 25 s per image).
--vlm DIR : reads cached <stem>.json scores from DIR (as written by critic_vlm_batch.py).
--vlm off : no model; every VLM criterion is not_evaluated and the verdict is fail (fail closed).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image   # noqa: E402

from archpipe import contracts            # noqa: E402
from archpipe.critic import meta as M     # noqa: E402
from archpipe.critic import verdict as V  # noqa: E402

REMOTE = "~/archpipe/scratch/critic"


def collect(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.glob("*.png") if not p.name.startswith("review"))
    return [target]


def title_for(png: Path) -> str:
    cap = png.with_suffix(".caption.json")
    if cap.exists():
        try:
            return json.loads(cap.read_text(encoding="utf-8")).get("title", "") or png.stem
        except (OSError, ValueError):
            pass
    return png.stem


def vlm_via_ssh(pngs: list[Path], rubric_path: Path, host: str = "ai-workstation") -> dict[str, dict]:
    """Copy jpgs + titles, run the batch under the GPU lock, fetch results. {stem: result json}."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        titles = {}
        for p in pngs:
            im = Image.open(p).convert("RGB")
            im.thumbnail((1280, 1280))
            im.save(td / f"{p.stem}.jpg", quality=90)
            titles[p.stem] = title_for(p)
        (td / "titles.json").write_text(json.dumps(titles), encoding="utf-8")
        run = f"{REMOTE}/run_cli"
        subprocess.run(["ssh", host, f"mkdir -p {run}/in {run}/out"], check=True)
        files = [str(f) for f in td.glob("*")] + [str(rubric_path), str(ROOT / "src/archpipe/critic/vlm.py"),
                                                  str(ROOT / "scripts/critic_vlm_batch.py")]
        subprocess.run(["scp", "-q", *files, f"{host}:{run}/in/"], check=True)
        bench = f"{REMOTE}/run/bench_32.jpg"
        cmd = (f"cd {run}/in && flock ~/archpipe/locks/graphics.lock python3 critic_vlm_batch.py "
               f"--rubric {rubric_path.name} --vlm vlm.py --imgdir . --bench {bench} --titles titles.json "
               f"--views {','.join(p.stem for p in pngs)} --out ../out --force")
        subprocess.run(["ssh", host, cmd], check=True)
        subprocess.run(["scp", "-q", "-r", f"{host}:{run}/out/.", str(td)], check=True)
        return {p.stem: json.loads((td / f"{p.stem}.json").read_text(encoding="utf-8"))
                for p in pngs if (td / f"{p.stem}.json").exists()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--vlm", default="off", help="ssh | off | DIR with cached <stem>.json")
    ap.add_argument("--rubric", default=str(V.RUBRIC_PATH))
    ap.add_argument("--checks-dir", default="out/checks")
    ap.add_argument("--json", default="", help="also write all verdicts to this file")
    a = ap.parse_args(argv)
    rubric = V.load_rubric(a.rubric)
    gating = set(V.ALWAYS_GATING) | set(rubric.get("gating", {}).get("vlm", V.VLM_CRITERIA))
    pngs = collect(Path(a.target))
    if not pngs:
        print("no png images found", file=sys.stderr)
        return 2
    cache: dict[str, dict] = {}
    if a.vlm == "ssh":
        cache = vlm_via_ssh(pngs, Path(a.rubric))
    elif a.vlm != "off":
        for p in pngs:
            f = Path(a.vlm) / f"{p.stem}.json"
            if f.exists():
                cache[p.stem] = json.loads(f.read_text(encoding="utf-8"))
    verdicts, results = [], []
    for p in pngs:
        view = M.load_view(p)
        det = V.deterministic_scores(p, view)
        j = cache.get(p.stem)
        ok = bool(j and j.get("status") == "ok")
        merged = V.merge(det, j["scores"] if ok else None, rubric)
        verdict, notes = V.decide(merged, gating, hero=True, vlm_ok=ok)
        notes["vlm"] = "ok" if ok else "unavailable"
        notes["rubric"] = rubric["version"]
        rv = V.build_verdict(p.stem, str(p), view, merged, verdict, notes)
        verdicts.append(asdict(rv))
        results += V.check_results(p.stem, merged, gating)
        print(json.dumps(asdict(rv), indent=2))
    path = contracts.write_results(V.LANE, results, a.checks_dir)
    if a.json:
        Path(a.json).write_text(json.dumps(verdicts, indent=2), encoding="utf-8")
    print(f"wrote {path}: {len(results)} CheckResults, {sum(v['verdict'] == 'fail' for v in verdicts)}/{len(verdicts)} FAIL",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
