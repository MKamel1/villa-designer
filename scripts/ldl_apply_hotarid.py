"""Apply hot-arid / regional authority evidence to plant species files (LDL pass 2).

Reads knowledge/landscape/plants/evidence/{selectree,amwua,mbg}.json (cached from the live sources) and the
Southern Nevada Regional Plant List text, and fills attributes that are a GAP or Wikipedia-sourced. A value is
only written with a quote that is a substring of the cached evidence; quotes are re-checked live by
`python -m archpipe.landscape.plants.verify_quotes`. Idempotent. Run: PYTHONPATH=src python scripts/ldl_apply_hotarid.py
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "knowledge/landscape/plants"
EV = P / "evidence"
TODAY = "2026-11-22"
sel = json.loads((EV / "selectree.json").read_text())
amw = json.loads((EV / "amwua.json").read_text())
mbg = json.loads((EV / "mbg.json").read_text())
LV_URL = "https://files.lasvegasnevada.gov/planning/Sustainability/water-smart-plant-list-2026.pdf"
LV_STARS = ("Trees rated 3 stars and above are recommended trees because they are well-adapted to our desert heat "
            "and seasonal drought.")
LV_INTRO = ("This list provides a region-wide reference to help homeowners, landscape designers, architects and "
            "developers select suitable plants for the Las Vegas area.")
# Southern Nevada list entries read from the PDF text (tree star rating where a tree; None for non-tree inclusion)
LV_TREE = {"laurus_nobilis": 4, "olea_europaea": 3, "phoenix_dactylifera": 3, "punica_granatum": 3}
LV_LISTED = ["callistemon_citrinus", "dodonaea_viscosa", "plumbago_auriculata", "lantana_montevidensis",
             "salvia_leucantha", "rosmarinus_officinalis", "gazania_rigens", "liriope_muscari",
             "ophiopogon_japonicus", "muhlenbergia_capillaris", "pennisetum_alopecuroides", "nandina_domestica",
             "pittosporum_tobira", "trachelospermum_jasminoides", "ficus_pumila", "aloe_vera", "aspidistra_elatior",
             "fatsia_japonica"]
# MBG: slug -> (attribute, class, verbatim quote). Heat/drought/alkaline statements chosen by reading the page.
MBG_RULES = {
    "cynodon_dactylon": [("heat", "high", "Tolerates heat, drought and a wide range of soils.")],
    "zoysia_japonica": [("heat", "high", "tolerance of drought and summer heat")],
    "liriope_muscari": [("heat", "high", "Also has good tolerance for heat, humidity and drought.")],
    "origanum_majorana": [("heat", "high", "Good heat and drought tolerance."),
                          ("alkaline_soil", "tolerant", "Prefers neutral to alkaline soils.")],
    "jacaranda_mimosifolia": [("heat", "high", "Likes heat and humidity.")],
    "acorus_gramineus": [("heat", "moderate", "Plants appreciate some relief from hot summer sun")],
    "alpinia_zerumbet": [("heat", "moderate", "Plants appreciate some afternoon shade in hot summer climates.")],
    "farfugium_japonicum": [("heat", "moderate", "leaf wilting may occur in hot summer climates, particularly when the plant is exposed to too much sun")],
    "justicia_brandegeeana": [("heat", "moderate", "with some protection from hot afternoon sun")],
    "nandina_domestica": [("alkaline_soil", "moderate", "Foliage may develop chlorosis in alkaline soils.")],
    "lagerstroemia_indica": [("alkaline_soil", "moderate", "Foliage may yellow (chlorosis) in alkaline soils.")],
}
CLS = {"heat": "class", "drought": "class", "alkaline_soil": "class", "salt": "class", "root_behaviour": "class",
       "toxicity_people": "class"}


def mbg_url(s):
    return mbg[s]["url"]


def put(rec, attr, value, source, note, why):
    cur = rec["attributes"][attr]
    if cur["status"] == "SOURCED" and cur["source"]["source_id"] != "Wikipedia":
        return False
    new = {"status": "SOURCED", "value": value, "source": source}
    if cur["status"] == "SOURCED":
        new["superseded"] = {"source_id": "Wikipedia", "value": cur["value"], "url": cur["source"]["url"]}
    if note:
        new["value"]["text"] = note
    rec["attributes"][attr] = new
    return True


def main():
    changed = {}
    for f in sorted((P / "species").glob("*.json")):
        s = f.stem
        rec = json.loads(f.read_text())
        n = 0

        def mark(a):
            nonlocal n
            n += 1
            changed.setdefault(a, []).append(s)

        # 1. SelecTree (Cal Poly) - trees
        if s in sel:
            d = sel[s]; url = f"https://selectree.calpoly.edu/api/tree/detail/{d['slug']}"
            loc = f"SelecTree tree-detail/{d['slug']} (Cal Poly)"
            src = lambda q: {"source_id": "SelecTree", "url": url, "accessed": TODAY, "locator": loc, "quote": q}
            st = (d["salt_tolerance"] or "").lower()
            if st in ("low", "moderate", "high", "none") and put(rec, "salt", {"class": st}, src(f'"salt_tolerance":"{d["salt_tolerance"]}"'), f"SelecTree salt tolerance: {d['salt_tolerance']}", ""):
                mark("salt")
            ph = d["soil_ph_high"]
            if ph:
                cl = "tolerant" if ph >= 6 else "moderate" if ph == 5 else "intolerant"
                lab = {2: "Acidic", 3: "Slightly Acidic", 4: "Neutral", 5: "Slightly Alkaline", 6: "Alkaline", 7: "Very Alkaline"}[ph]
                if put(rec, "alkaline_soil", {"class": cl}, src(f'"soil_ph_high":{ph}'), f"SelecTree upper soil pH limit: {lab} (scale 1 very acidic .. 7 very alkaline)", ""):
                    mark("alkaline_soil")
            rd = {"Low": "benign", "Moderate": "moderate", "High": "aggressive"}.get(d["root_damage_potential"])
            if rd and put(rec, "root_behaviour", {"class": rd}, src(f'"root_damage_potential":"{d["root_damage_potential"]}"'), f"SelecTree root damage potential: {d['root_damage_potential']}", ""):
                mark("root_behaviour")
            if d["litter_type"] and put(rec, "litter", {"text": "SelecTree litter types: " + ", ".join(d["litter_type"])}, src('"litter_type":' + json.dumps(d["litter_type"], separators=(",", ":"))), None, ""):
                mark("litter")
            hh = d["health_hazard"] or []
            tox = None
            if "Poisonous" in hh:
                tox = "toxic"
            elif hh == ["None Known"]:
                tox = "non_toxic"
            if tox and put(rec, "toxicity_people", {"class": tox}, src('"health_hazard":' + json.dumps(hh, separators=(",", ":"))), "SelecTree health hazard: " + ", ".join(hh) + " (Poisonous is not graded; toxic used, not highly_toxic)" if tox == "toxic" else "SelecTree health hazard: None Known", ""):
                mark("toxicity_people")
        # 2. Heat from Southern Nevada Regional Plant List (a tree >=3 stars states heat adaptation; other entries are inclusion = inference)
        heat_done = False
        for attr, cl, q in MBG_RULES.get(s, []):
            if q not in mbg[s]["text"]:
                sys.exit(f"{s}: MBG quote not in cached page: {q}")
            if put(rec, attr, {"class": cl}, {"source_id": "MBG", "url": mbg_url(s), "accessed": TODAY, "locator": "Missouri Botanical Garden Plant Finder, Culture / Noteworthy", "quote": q}, f"MBG: {q}", ""):
                mark(attr)
            heat_done |= attr == "heat"
        if not heat_done and rec["attributes"]["heat"]["status"] != "SOURCED":
            if s in LV_TREE and LV_TREE[s] >= 3:
                if put(rec, "heat", {"class": "high"}, {"source_id": "SNRPC-2026", "url": LV_URL, "accessed": TODAY, "locator": f"Southern Nevada Regional Plant List June 2026, Trees: {rec['attributes']['accepted_name']['value']['name']} rated {LV_TREE[s]} stars; How to Use the List", "quote": LV_STARS}, f"Rated {LV_TREE[s]} of 5 stars (3+ = well-adapted to desert heat) in the Las Vegas list", ""):
                    mark("heat")
            elif s in LV_LISTED or any(a["genus"].lower() + "_" + a["species"].lower().replace("-", "_") in s or (a["genus"].lower() == s.split("_")[0] and a["species"].lower() == s.split("_")[1]) for a in amw.values()):
                full = "full_sun" in rec["attributes"]["sun"].get("value", {}).get("classes", []) if rec["attributes"]["sun"]["status"] == "SOURCED" else False
                cl = "high" if full else "moderate"
                if s in LV_LISTED:
                    srcd = {"source_id": "SNRPC-2026", "url": LV_URL, "accessed": TODAY, "locator": f"Southern Nevada Regional Plant List June 2026: listed entry for {rec['attributes']['accepted_name']['value']['name']}", "quote": LV_INTRO}
                else:
                    a = next(a for a in amw.values() if a["genus"].lower() == s.split("_")[0] and a["species"].lower() == s.split("_")[1])
                    srcd = {"source_id": "AMWUA", "url": a["url"], "accessed": TODAY, "locator": "AMWUA Landscape Plants for the Arizona Desert: plant page", "quote": f"{a['genus']} {a['species'].replace('-', ' ')}"}
                if put(rec, "heat", {"class": cl, "inferred": True}, srcd, "INFERENCE: the source lists this plant as suitable for a hot low-desert landscape but states no heat tolerance in words; " + ("class high (our sun attribute includes full sun)" if full else "class moderate (our sun attribute does not include full sun: shade-tolerant plant listed)"), ""):
                    mark("heat")
        # 3. AMWUA litter where still a gap
        a = next((a for a in amw.values() if a["genus"].lower() == s.split("_")[0] and a["species"].lower() == (s.split("_")[1] if "_" in s else "")), None)
        if a and a.get("litter") and rec["attributes"]["litter"]["status"] != "SOURCED":
            if put(rec, "litter", {"text": f"AMWUA litter rating: {a['litter']}"}, {"source_id": "AMWUA", "url": a["url"], "accessed": TODAY, "locator": "AMWUA plant page", "quote": f"\"litter\":\"{a['litter']}\""}, None, ""):
                mark("litter")
        # 4. MBG drought
        m = mbg.get(s)
        if m and re.search(r"Tolerate:[^:]*\bDrought\b", m["text"]) and rec["attributes"]["drought"]["status"] != "SOURCED":
            if put(rec, "drought", {"class": "moderate"}, {"source_id": "MBG", "url": m["url"], "accessed": TODAY, "locator": "Plant Finder, Tolerate", "quote": "Tolerate: Drought" if "Tolerate: Drought" in m["text"] else re.search(r"Tolerate: [^:]*?Drought[A-Za-z ,]*?(?= Invasive| Garden)", m["text"]).group(0)}, "MBG lists Drought under Tolerate (class moderate: the source does not grade it)", ""):
                mark("drought")
        if n:
            f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print({k: len(v) for k, v in changed.items()})


main()
