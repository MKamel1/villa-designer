"""Print the deterministic messages and VLM evidence for chosen views, and runtime statistics.

    python scripts/critic_report.py out/critic/vlm/held_frozen v21 v02
"""
import glob
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.critic import calibrate as C   # noqa: E402
from archpipe.critic import verdict as V     # noqa: E402

d = Path(sys.argv[1])
secs = [json.loads(f.read_text(encoding="utf-8"))["seconds"] for f in d.glob("v*.json")]
print(f"runtime per image: mean {statistics.mean(secs):.1f} s, min {min(secs):.1f}, max {max(secs):.1f}, n={len(secs)}")
for v in sys.argv[2:]:
    det = V.deterministic_scores(C.png_for(v))
    print("==", v)
    for c, x in det.items():
        print(f"  {c} {x['score']} {x['message']}")
    j = json.loads((d / f"{v}.json").read_text(encoding="utf-8"))
    for c, s in j["scores"].items():
        print(f"  VLM {c} {s.get('score')} {str(s.get('evidence'))[:260]}")
