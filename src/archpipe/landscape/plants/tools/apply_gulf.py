"""Pass 3: close heat GAPs from Gulf / Cairo public-realm and garden lists (inferred, never measured).

Policy (ours, not a published standard): a species listed for outdoor public-realm or garden use in a hot-desert
Gulf or Cairo source gets an *inferred* heat class. Where the Abu Dhabi PRDM gives an Exposure Group, A/B -> high,
C/D/E (needs afternoon sun shelter / partial shade / total shade) -> moderate. Cairo/UAE list inclusion without
an exposure group follows the sun attribute (full_sun -> high, else moderate). Only a GAP is filled.
Run: python src/archpipe/landscape/plants/tools/apply_gulf.py ; then verify_quotes.
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[5] / "knowledge/landscape/plants/species"
TODAY = "2026-11-22"
PRDM = "https://www.cip-icu.ca/wp-content/uploads/2023/11/2011-HM-Urban-Design21.pdf"
CFC = "https://www.plantarchives.org/article/landscape-use-and-aesthetical-value-of-surveyed-woody-ornamental-plants-in-cairo-festival-city-cairo-egypt-in-landscape-gardening.pdf"
ENHG = "https://enhg.org/bulletin/b29/29_23.htm"
BIO = "https://archive.org/download/biostor-185341/biostor-185341.pdf"
LEG = {"B": "B. Requires some wind shelter for best growth",
       "C": "C. Requires shelter from afternoon sun and strong wind",
       "D": "D. Requires partial shade all day during summer, full shade in afternoon and wind shelter",
       "E": "E. Requires total shade and shelter"}
SRC = {"PRDM": ("PRDM-2011", PRDM, "Abu Dhabi Urban Planning Council, Public Realm Design Manual (2011), Appendix B Plant List"),
       "CFC": ("CFC-2021", CFC, "Abdelnaby et al., Plant Archives 21(1):104-109 (2021), survey of woody ornamentals in Cairo Festival City gardens, Cairo, 2018-2019"),
       "ENHG": ("ENHG-1986", ENHG, "Emirates Natural History Group Bulletin 29 (1986), Common Landscape Plants in the UAE (Arabian Gulf cities)"),
       "BIO": ("Egypt-papyrus", BIO, "Mitt. Bot. Staatssamml. Munchen, Rediscovery of Papyrus in Wadi Natroun (Egypt)")}
# slug: (source, group letter or None, row text for locator, quote, extra note)
E = {
 "ficus_carica": ("PRDM", "B", "Ficus carica Fig", "Ficus carica Fig B SSS", ""),
 "ficus_microcarpa": ("PRDM", "C", "Ficus microcarpa (Malayan Banyan), user note: good street and park tree providing dense shade", LEG["C"], ""),
 "delonix_regia": ("PRDM", "C", "Delonix regia (Royal Poinciana)", "Use only in humid coastal areas, excellent park, urban plaza and street tree",
                   " PRDM also says use only in humid coastal areas (the site is dry inland); also in the Cairo Festival City survey and the 1986 UAE list."),
 "citrus_limon": ("PRDM", "D", "Citrus limonum (Lemon Tree)", "Citrus limonum Lemon Tree D SSSS", ""),
 "hibiscus_rosa_sinensis": ("PRDM", "C", "Hibiscus rosa-sinensis", "Hibiscus rosasinensis Tropical Hibiscus, Rose of China C SSS",
                   " PRDM user note: badly damaged by insect attacks, use not advised; also in the Cairo Festival City survey and the 1986 UAE list."),
 "murraya_paniculata": ("PRDM", "D", "Murraya exotica (synonym of M. paniculata)", "Murraya exotica Orange Jasmine, Satin Wood, Honey Bush, Chinese Box D SSS",
                   " Also in the Cairo Festival City survey as M. paniculata."),
 "psidium_guajava": ("PRDM", "C", "Psidium guajava (Tropical Guava)", LEG["C"], " Also in the 1986 UAE list."),
 "rhapis_excelsa": ("PRDM", "E", "Rhapis excelsa Lady Palm (user note: needs shaded and sheltered location)", "Rhapis excelsa Lady Palm E SSS", ""),
 "lagerstroemia_indica": ("CFC", None, "Table: Lagerstroemia indica L.", "Lagerstroemia indica L.", ""),
 "jasminum_sambac": ("CFC", None, "Table: Jasminum sambac (L.) Aiton", "Jasminum sambac (L.) Aiton", " Also in the 1986 UAE list (Arabian jasmine)."),
 "jasminum_grandiflorum": ("CFC", None, "Table: Jasminum grandiflorum L.", "Jasminum grandiflorum L.", ""),
 "vitis_vinifera": ("ENHG", None, "Introduced Shrubs and Climbers, Vitaceae", "Vitis vinifera grape vine", ""),
 "cyperus_papyrus": ("BIO", None, "Wadi Natroun depression, Egypt", "a stand consisting of about 20 plants of Cyperus papyrus L. which were growing among other reeds in a fresh water marsh close to Umm Risha lake", " Wild stand in a desert depression, always in marsh water."),
}


def main():
    n = 0
    for slug, (k, g, row, quote, extra) in E.items():
        f = P / f"{slug}.json"
        r = json.loads(f.read_text())
        if r["attributes"]["heat"]["status"] != "GAP":
            continue
        sid, url, cite = SRC[k]
        if g:
            cl = "high" if g in "AB" else "moderate"
            why = f"Exposure Group {g}: {LEG[g][3:]}"
        else:
            sun = r["attributes"]["sun"]
            full = sun["status"] == "SOURCED" and "full_sun" in sun["value"].get("classes", [])
            cl = "high" if full else "moderate"
            why = "no exposure group given; class from our sun attribute (" + ("full sun" if full else "not full sun") + ")"
        txt = f"INFERENCE: listed for outdoor use in a hot-desert source ({cite}); {why}; no heat tolerance stated in words; class {cl}.{extra}"
        r["attributes"]["heat"] = {"status": "SOURCED", "value": {"class": cl, "inferred": True, "text": txt},
                                   "source": {"source_id": sid, "url": url, "accessed": TODAY, "locator": f"{cite}: {row}", "quote": quote}}
        f.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
        n += 1
    print("filled", n)


main()
