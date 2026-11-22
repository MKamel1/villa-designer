"""LDL pass 6: close the Hedera helix heat GAP from a hot-arid source (ASU Plants for the Phoenix area, opened 2026-11-22).
    PYTHONPATH=src python -I src/archpipe/landscape/plants/tools/apply_ivy_heat.py"""
import json
from pathlib import Path

F = Path(__file__).resolve().parents[5] / "knowledge/landscape/plants/species/hedera_helix.json"
URL = "https://www.asu.edu/lib/camartin/plants/Plant%20html%20files/hederahelix.html"
rec = json.loads(F.read_text())
rec["attributes"]["heat"] = {"status": "SOURCED", "value": {"class": "low", "text":
    "ASU (Phoenix, hot-arid): does not tolerate full summer sun; plant only in light to full shade. Class low = our policy for a plant that dies in full sun at this heat; shade siting is the only route"},
  "source": {"source_id": "ASU-Phoenix", "url": URL, "accessed": "2026-11-22", "locator": "Light",
             "quote": "In the Phoenix area, English ivy DOES NOT tolerate full sun and will quickly die when exposed to western afternoon sun during summer. Because of this, plant English ivy only in light to full shade in Phoenix."}}
rec["notes"] = rec["notes"].replace("Heat tolerance is a GAP, so the viability verdict stays unverified; do not read the cold hardiness or the NCSU tag as heat evidence.",
    "Heat: ASU (Phoenix) says it dies in full summer sun and belongs only in light to full shade, so it is not viable on a sun-exposed trellis or wall; shaded north-side use only.")
F.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
