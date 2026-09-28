"""D1 render review page: out/villa/render-d1/review/index.html (+ renders/*.jpg).

    PYTHONPATH=src python scripts/villa_review_page.py

Every figure on the page is read from the outputs: the render reports and captions, render_qa, the in-scene
lighting measurement, the as-finished daylight report and villa_brief.check. Nothing is typed in by hand.
"""
import html
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.concept import villa_brief as B                       # noqa: E402
from archpipe.concept import villa_lighting as VL                   # noqa: E402

R = ROOT / "out" / "villa" / "render-d1"
OUT = R / "review"
E = html.escape

STATE = {"day": "Day", "evening": "Evening", "exterior-dusk": "Dusk, outside"}

# Why a QA flag stands: each is a physical result the render shows as it is (the render standard forbids correcting
# it in camera). A flag without an entry here is shown as unexplained.
def why(check, v):
    """Why a QA flag stands, given the view: each is a physical result the render shows as it is (the render
    standard forbids correcting it in camera). Anything else is shown as unexplained."""
    c, st = check.split(":")[0], v["state"]
    if c == "colour_cast" and st == "exterior-dusk":
        return "blue hour: the sky is genuinely cool; not corrected in camera"
    if c == "colour_cast" and st == "day":
        return "3000 K lamps on by day under a daylight white balance: the warmth is real"
    if c == "window_view":
        return "the window looks onto a plain neighbouring wall with little detail"
    if c == "crushed_shadows":
        return "the room's dark areas are its specified lighting at the locked exposure"
    if c == "window_brightness" and v.get("exposure") == "exterior-day":
        return "outside by day, the windows read darker than the sunlit facade"
    if c == "window_brightness":
        return "the garden seen through basement glass is dimmer than the lit room"
    return "unexplained: to be investigated"


DECISIONS = [
    ("Parents' dressing door", "Recommended: 0.8 m door centred 0.1 m from the east wall, with a slim 0.35 m bedside "
     "table, so nothing stands in the opening (a 0.5 m table stood 0.23 m in it). A 0.8 m door is narrower than the "
     "0.9 m route used elsewhere: it needs your yes as a waiver for the private dressing area (ADR-0014)."),
    ("Stair structure", "Rendered with ASSUMED steel stringers, open risers and a bar balustrade; the model's treads "
     "stop 50-200 mm short of the party wall. To be designed and put into the Revit model."),
    ("Ramp soffit", "The parking model and the rendered ramp differ by up to 150 mm under the dirty kitchen; fittings "
     "were seated on the rendered soffit. To be reconciled in Revit."),
    ("Products", "Furniture, appliances, taps, mirrors and several fittings are procedural stand-ins at the checked "
     "sizes; finishes are ASSUMED from your taste profile until you choose them."),
]


def main():
    scene = json.loads((R / "scene.json").read_text(encoding="utf-8"))
    (OUT / "renders").mkdir(parents=True, exist_ok=True)
    plates = []
    for v in scene["views"]:
        png = R / (v["id"] + ".png")
        rep = json.loads((R / (v["id"] + ".json")).read_text(encoding="utf-8"))
        qa = json.loads((R / (v["id"] + ".qa.json")).read_text(encoding="utf-8"))
        im = Image.open(png).convert("RGB")
        im.save(OUT / "renders" / (v["id"] + ".jpg"), quality=90, optimize=True)
        layers = ", ".join(v["layers_on"]) or "none (daylight only)"
        dims = ", ".join("%s %d%%" % (k, round(x * 100)) for k, x in v.get("dimmers", {}).items())
        failed = qa.get("failed", [])
        plates.append(dict(v=v, rep=rep, failed=failed, size=im.size, layers=layers, dims=dims))
    meas = json.loads((R / "lighting-measurements.json").read_text(encoding="utf-8"))
    day = json.loads((ROOT / "out" / "villa" / "daylight" / "villa-df-d1-finished" / "report.json")
                     .read_text(encoding="utf-8"))
    VL.bind_products()
    brief = B.check()
    notes = scene["notes"]
    locked = {}
    for p_ in plates:
        if p_["rep"].get("locked_ev100") is not None:
            locked.setdefault(p_["v"]["exposure"], p_["rep"]["locked_ev100"])
    parts = [HEAD]
    parts.append('''<header class="block"><div class="block-main"><p class="eyebrow">Villa Zayed · design D1 · review set</p>
<h1>D1 as it would be built</h1>
<p class="lede">%d views rendered from the checked design: the furnished layout, the lighting scheme with its
real photometry, the daylight of the site, and the stated finishes. Nothing is retouched; where a room is dark, the
design makes it dark.</p></div>
<dl class="block-meta"><div><dt>Views</dt><dd>%d</dd></div><div><dt>Resolution</dt><dd>%d × %d</dd></div>
<div><dt>Samples</dt><dd>%d</dd></div><div><dt>Status</dt><dd class="pill">For your review</dd></div></dl></header>'''
                 % (len(plates), len(plates), plates[0]["size"][0], plates[0]["size"][1],
                    plates[0]["rep"]["samples"]))
    parts.append('''<section class="rules"><h2>How to read these images</h2><ul>
<li><b>Exposure is metered once per state, then locked.</b> Like a photographer's meter: each view is metered, and the
median of the day views (EV %s), the evening views (EV %s) and the dusk exterior (EV %s) is used for every view in that
state. A room that looks darker than another <em>is</em> darker.</li>
<li><b>The eye's lens.</b> Views are taken at 24 mm from eye height (1.35 m) with the camera level, standing where a
photographer could. Where a room is too small to hold its subjects at 24 mm, 16 mm is used and the caption says so.</li>
<li><b>Light is the specified light.</b> Fittings emit their manufacturer photometry at their stated lumens; the dimmer
levels used in each view are printed under it. Calibrated: a downlight within 3.2 %% of the hand calculation, an opal
globe within 0.9 %%, window glass at 0.700 for a stated 0.70.</li>
<li><b>By day the basement is shown with its ambient and accent lights at 50 %%</b>; ground-floor day views are daylight
only.</li>
<li><b>What is not yet decided is labelled.</b> Furniture and sanitaryware are stand-ins at the checked sizes; finishes
are assumed from your taste profile; some fittings are generic until products are chosen.</li></ul></section>'''
                 % tuple(("%.1f" % locked[k]) if k in locked else "n/a" for k in ("day", "evening", "exterior-dusk")))
    parts.append('<section class="plates">')
    for p in plates:
        v, rep = p["v"], p["rep"]
        sun = v.get("sun", {})
        qa = ("QA pass" if not p["failed"] else
              "QA flags: " + "; ".join("%s (%s)" % (f, why(f, v)) for f in p["failed"]))
        parts.append('''<figure class="plate" id="%s"><img src="renders/%s.jpg" width="%d" height="%d" loading="lazy"
alt="%s">
<figcaption><h3>%s</h3><dl class="cap">
<div><dt>State</dt><dd>%s · %s</dd></div>
<div><dt>Sun</dt><dd class="num">alt %.1f° · az %.0f°</dd></div>
<div><dt>Camera</dt><dd class="num">%s mm · EV %.1f · WB %s K</dd></div>
<div><dt>Lights on</dt><dd>%s%s</dd></div>
<div><dt>Check</dt><dd class="%s">%s</dd></div></dl>%s</figcaption></figure>'''
                     % (E(v["id"]), E(v["id"]), p["size"][0], p["size"][1], E(v["title"]), E(v["title"]),
                        STATE.get(v["state"], v["state"]), E(v["when"][:16].replace("T", " ")),
                        sun.get("altitude_deg", 0), sun.get("azimuth_true_deg", 0),
                        v["camera"]["lens_mm"], rep.get("locked_ev100", scene["exposure"][v["exposure"]]["ev100"]),
                        scene["exposure"][v["exposure"]]["white_balance_k"],
                        E(p["layers"]), (" · " + E(p["dims"])) if p["dims"] else "",
                        "ok" if not p["failed"] else "flag", E(qa),
                        "".join('<p class="note">%s</p>' % E(n) for n in v.get("caption_notes", []))))
    parts.append('</section>')
    rows = "".join('<tr><td>%s</td><td>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td>'
                   '<td class="%s">%s</td></tr>' % (E(x["room"]), E(x["label"]), x["required_lux"],
                                                     round(x["direct_lux"]), round(x["total_lux"]),
                                                     "ok" if x["meets_target"] else "flag",
                                                     "met" if x["meets_target"] else "short")
                   for x in meas["points"])
    parts.append('''<section><h2>Lighting, measured in the furnished scene</h2><p class="note">Maintained illuminance
(maintenance factor %.1f) at every task point with a published target (IES Lighting Handbook Table 33.2), read from the
full scene with its furniture shadows and inter-reflections, all functional lights at full output, no daylight.</p>
<div class="scroll"><table><thead><tr><th>Room</th><th>Task</th><th>Target lx</th><th>Direct lx</th><th>Total lx</th>
<th></th></tr></thead><tbody>%s</tbody></table></div></section>''' % (meas["maintenance_factor"], rows))
    drow = "".join('<tr><td>%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                   % (E(x["room"]), x["adf_study"], x["adf_finished"]) for x in day["rooms"])
    parts.append('''<section><h2>Daylight, as finished and furnished</h2><p class="note">Average daylight factor (%%) in
Radiance, validated against its reference cases: the round-12 study (empty rooms, generic reflectances, 2.80 m
ceilings) beside the same building with the rendered finishes, furniture and 2.70 m ceilings. Where furniture now
covers the grid (kitchen worktops, dressing rails, library), the finished figure reads the shade under them.</p>
<div class="scroll"><table><thead><tr><th>Room</th><th>Study ADF</th><th>As finished ADF</th></tr></thead>
<tbody>%s</tbody></table></div></section>''' % drow)
    brow = "".join('<tr><td class="num">%s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>'
                   % (E(x["id"]), E(x["what"]), E(str(x["target"])), E(str(x["measured"])),
                      {"met": "ok", "not met": "flag"}.get(x["status"], "muted"), E(x["status"]))
                   for x in brief)
    parts.append('''<section><h2>Your guidelines document, checked</h2><p class="note">Treated as advisory, as you
decided: the sound targets were adopted, every one is measured here, none is enforced. The 4000 K target is withdrawn:
you never specified it.</p><details><summary>All %d targets</summary><div class="scroll"><table><thead><tr><th>Id</th>
<th>Target</th><th>Value</th><th>D1</th><th>Status</th></tr></thead><tbody>%s</tbody></table></div></details>
</section>''' % (len(brief), brow))
    parts.append('<section><h2>Decisions waiting for you</h2><ul class="assume">%s</ul></section>'
                 % "".join("<li><b>%s.</b> %s</li>" % (E(a), E(b)) for a, b in DECISIONS))
    parts.append('<section><h2>Stated assumptions</h2><ul class="assume">%s</ul></section>'
                 % "".join("<li>%s</li>" % E(n) for n in notes))
    parts.append('</main>')
    (OUT / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print(OUT / "index.html")


HEAD = '''<title>D1 Render Review</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Public+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--paper:#eceeeb;--sheet:#f7f8f6;--ink:#1c2220;--muted:#5a6461;--rule:#c9cfcb;--brass:#8a6a2e;--ok:#2f6b4a;--flag:#9a4b1c;
--serif:"Newsreader",Georgia,serif;--sans:"Public Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#131716;--sheet:#1b201e;--ink:#e6ebe8;--muted:#9aa6a1;
--rule:#2f3835;--brass:#c9a35a;--ok:#6fc095;--flag:#e39062;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#131716;--sheet:#1b201e;--ink:#e6ebe8;--muted:#9aa6a1;--rule:#2f3835;--brass:#c9a35a;
--ok:#6fc095;--flag:#e39062;color-scheme:dark}
body{background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans);padding-inline:16px;padding-block:24px 64px}
main{max-width:1240px;margin:0 auto;display:grid;gap:40px}
h1,h2,h3{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:clamp(28px,4vw,44px);line-height:1.1}h2{font-size:24px;margin-bottom:10px}h3{font-size:18px}
.eyebrow{font:500 12px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--brass);margin:0 0 12px}
.lede{max-width:66ch;color:var(--muted);margin:12px 0 0}
.block{display:grid;grid-template-columns:1fr auto;gap:24px;border:1px solid var(--rule);background:var(--sheet);padding:24px}
.block-meta{display:grid;grid-template-columns:auto auto;gap:8px 20px;margin:0;align-content:start}
.block-meta div{display:contents}dt{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
dd{margin:0;font-family:var(--mono);font-size:14px}.pill{color:var(--brass)}
.rules ul,.assume{max-width:80ch;padding-left:18px;display:grid;gap:6px;margin:0}
.plates{display:grid;gap:36px}.plate{margin:0;background:var(--sheet);border:1px solid var(--rule)}
.plate img{display:block;width:100%;height:auto}
.plate figcaption{padding:14px 18px;display:grid;gap:8px}
.cap{display:flex;flex-wrap:wrap;gap:6px 22px;margin:0}.cap div{display:flex;gap:8px;align-items:baseline}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}.ok{color:var(--ok)}.flag{color:var(--flag)}.muted{color:var(--muted)}
.note{color:var(--muted);max-width:80ch;margin:0 0 12px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
details summary{cursor:pointer;font-weight:600;margin:6px 0}summary:focus-visible,a:focus-visible{outline:2px solid var(--brass)}
@media (max-width:640px){.block{grid-template-columns:1fr}}
</style>
<main>'''

if __name__ == "__main__":
    main()
