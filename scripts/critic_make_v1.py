"""One-off: derive rubric v1 (tuning-half amendments) from the pre-registered v0 text in git history.

Every change is listed in rubric['amendments'] with the tuning-half evidence that motivated it.
"""
import json
import sys
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "knowledge" / "critic" / "rubric.json"
r = json.loads(p.read_text(encoding="utf-8"))
r["version"] = "v1-tuning"
r.setdefault("amendments", []).extend([
    {"id": "A1", "scope": "R12 pixel definition",
     "why": "v0 used red-minus-blue for warm limits, which flags every warm-lit room; the existing render_qa limit is on the cast magnitude. Warm now uses the cast magnitude (<= 0.09 pass, <= 0.10 warn); cool 0.03/0.06, cyan 0.05/0.08; green informational because foliage.",
     "evidence": "tuning half: v0 scored R12=0 on 11 of 20 views including B and B- views with cast 0.065"},
    {"id": "A2", "scope": "R10 pixel seam detector",
     "why": "could not separate the v27 seam (column 609 at 960 px) from real wall edges; the detector is informational, the VLM judges seams; band detector (v19) still gates.",
     "evidence": "tuning half: 7 of 20 views flagged, v27 itself missed"},
    {"id": "A3", "scope": "R3 pixel method",
     "why": "plain gradient median followed foliage and furniture lean; replaced by structure-tensor coherence > 0.9 on strong near-vertical edges with >= 3000 supporting pixels per column bin.",
     "evidence": "tuning half: v0 method gave 2-4 deg on garden views, new method 0.0-0.4 deg except v31 (2.05, slanted panels)"},
    {"id": "A4", "scope": "VLM prompts and mode",
     "why": "v0 single-image anchors made gemma4:31b score 0 on R7/R8/R9 for 20 of 20 tuning views (B and B- included): no discrimination, 0 hard-fails every good view. v1 scores each criterion relative to the benchmark render shown as a reference (image 1) with severity and extent anchors, and tells the model to score 2 when unsure.",
     "evidence": "tuning half: R8 0/20 >= 1 on every view; R9 0 on 19/20"},
    {"id": "A5", "scope": "R13 pair rule",
     "why": "mixed order results are position bias; final = 2 only when both orders agree the render is at least as photographic, 0 only when both say clearly less, else 1 (text in vlm.pair_rule corrected to match the code written before scoring)",
     "evidence": "none needed; the code was written before the first scoring run"}])
r["vlm"]["reference_relative"] = True
r["vlm"]["pair_rule"] = ("R13 runs both left/right orders (benchmark = the cropped 3:2 bedroom-overcast-door.png). Per order: render judged at least as "
                         "photographic -> 2; benchmark by a slight margin -> 1; by a clear margin -> 0. Final: 2 only if both orders give 2, "
                         "0 only if both give 0, otherwise 1.")
r["vlm"]["preamble"] = (
    "You are a strict but fair architectural-visualisation critic. Image 1 is the REFERENCE render: it is accepted quality "
    "and counts as score 2 on every criterion. Image 2 is the render under review. Judge Image 2 on the single criterion "
    "below, relative to the reference. Scoring: 2 = as good as the reference, or the problem is absent or minor; "
    "1 = the problem is clearly visible in a noticeable part of Image 2 and worse than in the reference; "
    "0 = the problem is severe, obvious at first glance, large in the frame, and much worse than in the reference. "
    "Every render has small flaws, so do not score down for small ones. If you are not sure you can see the problem, score 2. "
    "Only describe things you can actually see in Image 2. "
    "Reply with JSON only: {\"evidence\": \"<=40 words naming the object and where it is in Image 2\", \"score\": 0|1|2}.")
r["prompts"].update({
    "R5_CONTEXT": "Criterion: CONTEXT. What is seen through windows, doors and beyond the building should look like a textured, believable exterior (planting, detailed facades, graded sky). Problems: a window or opening that is a flat white or blank slab, a blank sky slab, neighbouring buildings that are plain white or clay boxes. If no exterior is visible in Image 2, score 2.",
    "R7_SCALE": "Criterion: PHYSICAL SCALE OF MATERIALS. Texture size should match the real material at real size: wood grain, stone veining, tile and paver size. Problems: grain or veins several times too large, blotchy over-coloured marble, stretched or smeared texture mapping, unnatural hue such as salmon-pink timber.",
    "R8_ASSETS": "Criterion: ASSET FIDELITY. How crude are the 3D models. Problems: visible polygon facets on round things (lamp globes, pots), flat card, disc or lollipop shaped foliage, furniture or bedding made of plain boxes, pillows as rigid wedges, clothes like boards. Compare the faceting and crudeness against what the reference shows.",
    "R9_CONTACT": "Criterion: CONTACT AND INTERSECTION. Problems: an object floating with no support, a fitting detached from its wall or ceiling, an object visibly passing through another (cushion through a frame, pillow into a headboard).",
    "R10_FRAME": "Criterion: COMPOSITION AND FRAME INTEGRITY. Problems: something close to the camera blocking more than about 15 percent of Image 2, the main subject cut off by the frame, plain empty wall covering more than about 40 percent, a hard straight vertical or horizontal seam cutting through objects, a dark or solid band along the frame edge, a milky haze or veil, wall or ceiling lines that visibly bend.",
    "R11_TRUTH": "Criterion: TRUTH AND STYLING. Image 2 is titled \"{title}\". Problems: the picture does not show what the title promises, the room is bare with none of the props that room would have, or the camera looks at the back of furniture. Judge the density of styling against the reference.",
})
p.write_text(json.dumps(r, indent=2), encoding="utf-8")
print("rubric ->", r["version"])
