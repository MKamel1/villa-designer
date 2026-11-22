"""Print GAP counts per attribute, verdict counts and source counts for the plant library."""
import json, collections, sys
d = json.load(open("knowledge/landscape/plants/plants.json"))
gap, src, ver = collections.Counter(), collections.Counter(), collections.Counter()
for r in d["species"]:
    ver[r["site_viability"]["verdict"]] += 1
    for a, o in r["attributes"].items():
        if not isinstance(o, dict): continue
        if o["status"] == "GAP": gap[a] += 1
        if o["status"] == "SOURCED": src[o["source"]["source_id"]] += 1
print("species", len(d["species"]), "GAP slots", sum(gap.values()))
print(dict(sorted(gap.items(), key=lambda x: -x[1])))
print(dict(ver)); print("sources", dict(src.most_common()))
