"""render_qa and captions for rendered garden views (the checks `scripts/villa_render.py` runs after a remote render, for a render done by the lane's own jobq command).

    python -m archpipe.landscape.build.tools.gi_qa SCENE.json RENDER_DIR
Writes <view>.qa.json and <view>.caption.json beside each <view>.png and prints one line per view: passed / failed checks. Exit 1 if any view fails.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))


def main(scene_path, out):
    from villa_render import villa_qa_context, villa_qa_scope, villa_caption
    from archpipe.render_qa import check
    from archpipe.blender.element_ids import without_ids
    scene = without_ids(json.loads(Path(scene_path).read_text(encoding="utf-8")))
    views = {v["id"]: v for v in scene["views"]}
    bad = 0
    for png in sorted(Path(out).glob("*.png")):
        ident = png.stem
        report = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
        qa_in = villa_qa_context(scene, views[ident], report)
        qa = check(png, qa_in)
        qa["scope"] = villa_qa_scope(qa, qa_in)
        png.with_suffix(".qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
        png.with_suffix(".caption.json").write_text(json.dumps(villa_caption(scene, views[ident], report, qa), indent=2), encoding="utf-8")
        fails = [c["check"] for c in qa["checks"] if not c.get("passed", c.get("ok", True))]
        print("%-34s %s  failed: %s" % (ident, "PASS" if qa["passed"] else "FAIL", ", ".join(fails) or "-"))
        bad += not qa["passed"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
