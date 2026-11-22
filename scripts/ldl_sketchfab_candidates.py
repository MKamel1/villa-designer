"""List downloadable CC0 / CC-BY Sketchfab models per species (public search API, no token needed to search).
Downloading needs an API token (sketchfab-api.txt, user-created); none exists on this machine (HTTP 401).
Output: knowledge/landscape/plants/sketchfab-candidates.json. Licence labels must be re-read at download time."""
import json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "knowledge/landscape/plants"
OK = {"CC0 Public Domain", "CC Attribution"}  # Sketchfab licence labels
H = {"User-Agent": "Mozilla/5.0"}


def search(q):
    u = "https://api.sketchfab.com/v3/search?" + urllib.parse.urlencode(
        {"type": "models", "q": q, "downloadable": "true", "sort_by": "-likeCount", "count": 24})
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30)).get("results", [])
    except Exception as e:
        print("ERR", q, e); return []


out = {}
for f in sorted((P / "species").glob("*.json")):
    rec = json.loads(f.read_text())
    a = rec["attributes"]["accepted_name"]["value"]
    sci = " ".join(a["name"].replace(" x ", " ").split()[:2])
    genus = sci.split()[0]
    terms = [sci, a["common_names"][0] if a.get("common_names") else genus]
    seen, hits = set(), []
    for q in terms:
        for m in search(q):
            lic = (m.get("license") or {}).get("label", "")
            if m["uid"] in seen or lic not in OK or not m.get("isDownloadable"):
                continue
            nm = (m["name"] + " " + " ".join(t["name"] for t in m.get("tags", []))).lower()
            if not (genus.lower() in nm or q.lower() in nm):
                continue
            seen.add(m["uid"])
            hits.append({"uid": m["uid"], "name": m["name"], "licence": m["license"]["label"], "author": m["user"]["displayName"],
                         "faces": m.get("faceCount"), "url": m["viewerUrl"], "matched_on": q,
                         "match": "species" if sci.lower() in nm else "genus/common"})
        time.sleep(0.4)
    hits.sort(key=lambda h: (h["match"] != "species", (h["faces"] or 9e9) > 1_500_000, -0))
    out[f.stem] = hits[:5]
    print(f.stem, len(hits))
(P / "sketchfab-candidates.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
