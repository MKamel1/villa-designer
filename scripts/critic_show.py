"""Print cached VLM scores (and optionally the model's evidence) next to the human grade.

    python scripts/critic_show.py out/critic/vlm/tune_v0 [evidence]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
labels = json.loads((ROOT / "knowledge" / "critic" / "split.json").read_text(encoding="utf-8"))["labels"]
for f in sorted(Path(sys.argv[1]).glob("v*.json")):
    j = json.loads(f.read_text(encoding="utf-8"))
    v = j["view"]
    print(v, labels[v]["grade"], j["seconds"], {c: s.get("score") for c, s in j["scores"].items()})
    if len(sys.argv) > 2:
        for c, s in j["scores"].items():
            print("    ", c, str(s.get("evidence"))[:230])
