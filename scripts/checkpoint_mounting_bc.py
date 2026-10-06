"""Write C4 packages b/c evidence; never replace the presentation scene."""
import csv
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.concept import villa_render as VR
from archpipe.concept.mounting import scene_findings
from archpipe.concept.fitting_mounting import bounds
from PIL import Image, ImageDraw


def preview(scene, folder, package):
    """Orthographic measured before/after diagnostic, explicit metre axes."""
    rows = [r for r in scene["mounting_movements"] if r["package"] == package and not r["id"].startswith("host-face-")]
    roots = {}
    meshes = {m["id"]: m for m in scene["meshes"]}
    for row in rows:
        roots.setdefault(row["host_id"], []).append(row)
    img = Image.new("RGB", (1200, 140 + 220*((len(roots)+2)//3)), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20,20), package + " - measured fixing section; diagnostic only; photoreal review pending", fill="black")
    draw.text((20,42), "Red: retained geometry. Blue: proposed. Gold: finished host. Wall sections: outward distance / height.", fill="black")
    draw.text((20,60), "Ceiling/floor sections: model x across / height up. Host faces are analytical records; this is not a render.", fill="black")
    for index, (hid, members) in enumerate(roots.items()):
        x, y = 20+(index%3)*400, 90+(index//3)*220
        host = scene["mounting_hosts"][hid]
        n = host["normal"]
        plane = sum(host["structural_point"][i]*n[i] for i in range(3))+host["finish"]["thickness_m"]
        draw.text((x,y), hid[:53], fill="black")
        ps = [p for r in members for f in r["proposed_faces"] for p in f]
        zlo, zhi = min(p[2] for p in ps), max(p[2] for p in ps)
        scale = min(250,160/max(zhi-zlo,.1))
        horizontal_host = abs(n[2]) > .5
        centre_x = (min(p[0] for p in ps)+max(p[0] for p in ps))/2
        def pixel(p):
            horizontal = x+180+(p[0]-centre_x)*scale if horizontal_host else x+80+(sum(p[i]*n[i] for i in range(3))-plane)*scale
            return horizontal, y+190-(p[2]-zlo)*scale
        if horizontal_host:
            face_z = host["structural_point"][2]+n[2]*host["finish"]["thickness_m"]
            face_y = y+190-(face_z-zlo)*scale
            draw.line([(x+60,face_y),(x+320,face_y)],fill="#b88800",width=3)
        else:
            draw.line([(x+80,y+25),(x+80,y+190)],fill="#b88800",width=3)
        for r in members:
            for faces, color in ((meshes[r["id"]]["faces"],"#bd2222"),(r["proposed_faces"],"#2264ac")):
                for face in faces:
                    draw.line([pixel(p) for p in face+[face[0]]],fill=color,width=1)
        draw.text((x,y+198), "Max move %.3f mm" % max(r["mm"] for r in members),fill="black")
    img.save(folder/(package+"-preview.png"))


def main():
    folder = ROOT/"out/c4-phase2bc"
    folder.mkdir(parents=True,exist_ok=True)
    scene = VR.build(views=[])
    (folder/"working-scene.json").write_text(json.dumps(scene),encoding="utf-8")
    proposed = deepcopy(scene)
    by_id = {m["id"]:m for m in proposed["meshes"]}
    for row in scene["mounting_movements"]:
        by_id[row["id"]]["faces"] = row["proposed_faces"]
        by_id[row["id"]].get("mounting",{}).pop("approval",None)
    (folder/"proposed-scene.json").write_text(json.dumps(proposed),encoding="utf-8")
    failures = scene_findings(scene)
    proposal_failures = scene_findings(proposed)
    stair = [m for m in scene["meshes"] if m["id"].startswith("detail-stair-wall") and m.get("mounting")]
    surfaces = [m for m in scene["meshes"] if m.get("finished_host_id")]
    stair_failures = scene_findings(dict(meshes=stair+surfaces,mounting_hosts=scene["mounting_hosts"]))
    rows = scene["mounting_movements"]
    for name, selected in (("movements-over-5mm.csv",[r for r in rows if r["approval"]=="PENDING"]),
                           ("movements-applied.csv",[r for r in rows if r["approval"]!="PENDING"])):
        with (folder/name).open("w",newline="",encoding="utf-8") as stream:
            writer = csv.DictWriter(stream,fieldnames=[k for k in rows[0] if k!="proposed_faces"])
            writer.writeheader()
            writer.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items() if k!="proposed_faces"} for r in selected)
    approved = list(csv.DictReader((ROOT/"out/c4-phase2a/movements-over-5mm.csv").open(encoding="utf-8")))
    for row in approved:
        row["approval"] = "APPROVED; applied per lead decision 2026-10-05"
    with (folder/"stair-approved-movements.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(approved[0])); writer.writeheader(); writer.writerows(approved)
    for package in ("b-bathroom","c-wall-lights"):
        preview(scene,folder,package)
    baseline = json.loads((ROOT/"tests/fixtures/c4-stair-phase1.json").read_text(encoding="utf-8"))
    old = {m["id"]:m for m in baseline["meshes"]}
    stair_rows = [dict(id=m["id"],package="a-stair",host_id=m["mounting"]["host_id"],old=bounds(old[m["id"]]),
                       new=bounds(m),why="Lead-approved real return/party/floor support; structural geometry retained",
                       approval="APPLIED per lead decisions 1-4",proposed_faces=m["faces"],
                       mm=round(max(abs(a-b) for a,b in zip(bounds(old[m["id"]]),bounds(m)))*1000,6)) for m in stair]
    with (folder/"stair-final-bounds-movements.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=[k for k in stair_rows[0] if k!="proposed_faces"])
        writer.writeheader(); writer.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items() if k!="proposed_faces"} for row in stair_rows)
    stair_preview = dict(scene, mounting_movements=stair_rows, meshes=baseline["meshes"])
    preview(stair_preview,folder,"a-stair")
    report = dict(status="CHECKPOINT; incomplete; uncommitted",stair_component_count=len(stair),
        stair_findings=stair_failures,missing_host_count=sum("MISSING mounting host" in f for f in failures),
        whole_scene_findings=failures,proposed_scene_findings=proposal_failures,
        pending_moves=sum(r["approval"]=="PENDING" for r in rows),
        applied_moves=sum(r["approval"]!="PENDING" for r in rows),photoreal_review="PENDING")
    (folder/"mounting-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if not k.endswith("scene_findings")},indent=2))
    return int(bool(stair_failures or [f for f in proposal_failures if "MISSING mounting host" not in f]))


if __name__ == "__main__":
    raise SystemExit(main())
