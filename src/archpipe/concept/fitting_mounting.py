"""C4 packages b/c: finite measured hosts, explicit assemblies and bounded moves.

All coordinates are metres. Proposed geometry is exported separately; a move
larger than five millimetres is never applied to the working scene. Child
projections preserve their generated relation to the assembly's fixing plane,
not an arbitrary measured wall gap. Existing ceiling surfaces are datums only;
no ceiling board thickness, recessed housing or void is inferred.
"""
from copy import deepcopy
from dataclasses import asdict
import math

from .mounting import Host, Finish, MountItem, binding, finish_from_record, _on_polygon
from . import villa_furnish as F, villa_lighting as VL


def points(mesh):
    return [p for face in mesh["faces"] for p in face]


def bounds(mesh):
    ps = points(mesh)
    return [min(p[i] for p in ps) for i in range(3)] + [max(p[i] for p in ps) for i in range(3)]


def normal(face):
    a, b, c = face[:3]
    u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
    cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    length = math.sqrt(sum(x*x for x in cross))
    return tuple(x / length for x in cross) if length else (0, 0, 0)


def measured_host(scene, anchor, outward, room, host_id, *, kind="wall", panel=False):
    """Select a real face in the intended direction over the fixing anchor.

    Restrict wall selection to the room's shell; joinery selection to its
    actual furniture. Door/glass faces are never accepted as masonry hosts.
    """
    candidates = []
    for mesh in scene["meshes"]:
        if panel:
            eligible = mesh["group"] == "furniture" and mesh.get("room") == room
        elif kind == "ceiling":
            eligible = mesh["group"] == "shell" and mesh["material"] == "ceiling-white"
        else:
            eligible = (mesh["group"] == "shell" and mesh.get("room") == room and
                        mesh["material"] in ("marble-bath", "plaster-warm-white", "porcelain-tile") and
                        not mesh.get("finished_host_id"))
        if not eligible:
            continue
        for face in mesh["faces"]:
            n = normal(face)
            if sum(n[i]*outward[i] for i in range(3)) < .999999:
                continue
            gap = sum((anchor[i]-face[0][i])*outward[i] for i in range(3))
            projected = [anchor[i]-gap*outward[i] for i in range(3)]
            if abs(gap) <= .25:
                # Keep the intended room's real finite face when an authored
                # fitting crosses its edge. The coverage guard must report
                # that defect; selecting a different room would hide it.
                candidates.append((0 if _on_polygon(projected, face, outward) else 1,
                                   abs(gap), mesh, face))
    if not candidates:
        raise ValueError(host_id + ": no real host at authored fixing anchor")
    _, distance, member, face = min(candidates, key=lambda row: row[:2])
    if distance > .25:
        raise ValueError(host_id + ": nearest host more than 250 mm from fixing anchor")
    if panel or kind == "ceiling":
        finish = Finish("existing-exported-" + member["material"] + "; thickness unknown; datum retained", 0)
    else:
        assembly = ("marble-wall-thinset" if member["material"] == "marble-bath" else
                    "porcelain-wall-thinset" if "tile" in member["material"] else "interior-plaster")
        finish = finish_from_record(assembly)
    host = Host(host_id, "joinery-panel" if panel else kind, tuple(face[0]), outward, finish)
    # Keep the finite polygon and original source, independent of item bounds.
    coplanar = [f for f in member["faces"] if sum(normal(f)[i]*outward[i] for i in range(3)) > .999999
                and all(abs(sum((p[i]-face[0][i])*outward[i] for i in range(3))) < 1e-8 for p in f)]
    surfaces = [[[p[i] + outward[i]*finish.thickness_m for i in range(3)] for p in f] for f in coplanar]
    scene["mounting_hosts"][host_id] = dict(asdict(host), source_mesh=member["id"],
                                           source_face=deepcopy(face), source_faces=deepcopy(coplanar), source_material=member["material"])
    host_mesh = dict(id="host-face-" + host_id, material=member["material"],
                                faces=deepcopy(coplanar), group="shell", room=room, part_kind="finish-layer",
                                finished_host_id=host_id, label="Measured finished fixing face",
                                visibility={"camera": False}, diagnostic=True)
    applied = finish.thickness_m <= .005
    if applied:
        host_mesh["faces"] = surfaces
    scene.setdefault("diagnostic_meshes", []).append(host_mesh)
    before = dict(host_mesh, faces=coplanar)
    after = dict(host_mesh, faces=surfaces)
    scene["mounting_movements"].append(dict(id=host_mesh["id"], package="b-bathroom" if host_id.startswith(("bath-", "detail-")) else "c-wall-lights",
        host_id=host_id, old=bounds(before), new=bounds(after), mm=round(finish.thickness_m*1000,6),
        why="Declared finish face over measured source polygon; " + finish.name,
        approval="APPLIED <=5 mm" if applied else "PENDING", proposed_faces=surfaces))
    return host


def package(scene, members, host, fixing_coordinate, package_name, root_id):
    """Resolve an authored assembly fixing plane and its generated children."""
    n = host.normal
    target = sum(host.structural_point[i]*n[i] for i in range(3)) + host.finish.thickness_m
    delta = target - fixing_coordinate
    for mesh in members:
        before = deepcopy(mesh)
        proposed = deepcopy(mesh)
        proposed["faces"] = [[list(p) for p in face] for face in proposed["faces"]]
        # Every component's projection is relative to its assembly root.
        projection = max(0, min(sum(p[i]*n[i] for i in range(3)) for p in points(mesh)) - fixing_coordinate)
        if projection < 1e-9:
            projection = 0.0
        for face in proposed["faces"]:
            for p in face:
                signed = sum(p[i]*n[i] for i in range(3)) + delta
                fixing_end = mesh.get("part_kind") == "rail-bracket" or mesh["id"].startswith("swing-arm-")
                correction = delta + (max(0, target - signed) if fixing_end else 0)
                for i in range(3):
                    p[i] += correction*n[i]
        kind = "surface-mounted" if projection < 1e-9 else "suspended" if host.kind == "ceiling" else "wall-hung"
        contract = dict(binding(MountItem(mesh["id"]), host, projection, kind),
                        assembly_root=root_id, projection_basis="Generated child relative to authored assembly fixing plane")
        proposed["mounting"] = contract
        movement = max(math.dist(a, b) for a, b in zip(points(before), points(proposed))) * 1000
        applied = movement <= 5 + 1e-9
        mesh["mounting"] = deepcopy(contract)
        mesh["mounting_package"] = package_name
        if applied:
            # Automatic small parent corrections use the same declared
            # assembly binding as explicit approvals. Children already in
            # this package are processed below, so never carry them twice.
            attached = [child for child in scene.get('meshes', []) if
                        child.get('associated_mounting_root') == mesh['id'] and
                        child not in members]
            if attached:
                from .attached_assembly import translate
                translate(scene, mesh['id'], [delta*v for v in n],
                          deferred_ids={member['id'] for member in members if member is not mesh})
            mesh["faces"] = proposed["faces"]
        else:
            mesh["mounting"]["approval"] = "PENDING"
        scene["mounting_movements"].append(dict(id=mesh["id"], package=package_name,
            host_id=host.id, old=bounds(before), new=bounds(proposed), mm=round(movement, 6),
            why="Assembly fixing face from measured host; " + host.finish.name,
            approval="APPLIED <=5 mm" if applied else "PENDING", proposed_faces=proposed["faces"]))


def migrate(scene, lay, spec, finishes):
    scene["mounting_movements"] = []
    originals = list(scene["meshes"])
    furniture = F.layout(lay)
    for item in furniture:
        if item["type"] not in ("wc", "washbasin", "washbasin_double"):
            continue
        members = [m for m in originals if m["id"].startswith("furn-" + item["id"] + "-")]
        members += [m for m in originals if m["id"] == "mirror-" + item["id"]]
        outward = {0: (0, 1, 0), 180: (0, -1, 0), -90: (1, 0, 0), 90: (-1, 0, 0)}[item["rot"]]
        rect = F.footprint(item)
        anchor = [(rect[0]+rect[2])/2, (rect[1]+rect[3])/2, VL.LEVEL_Z[item["level"]]+.7]
        axis = 0 if outward[0] else 1
        anchor[axis] = rect[axis] if outward[axis] > 0 else rect[axis+2]
        host = measured_host(scene, anchor, outward, item["room"], "bath-" + item["id"])
        fixing = min(sum(p[i]*outward[i] for i in range(3)) for m in members for p in points(m))
        package(scene, members, host, fixing, "b-bathroom", members[0]["id"])
    for fitting in spec["bath_fittings"]:
        prefix = "detail-" + fitting["id"]
        members = [m for m in originals if m["id"].startswith(prefix + "-")]
        if fitting["kind"] == "ceiling-rain-head":
            drop = next(m for m in members if m["id"].endswith("-drop"))
            fixing = -max(p[2] for p in points(drop))
            anchor = (fitting["x"], fitting["y"], -fixing)
            host = measured_host(scene, anchor, (0, 0, -1), fitting["room"], prefix, kind="ceiling")
            package(scene, members, host, fixing, "b-bathroom", drop["id"])
        elif fitting["kind"] == "hand-shower":
            bracket = next(m for m in members if m["id"].endswith("bracket-lower"))
            # Rail location is authored; select the closest finite room wall,
            # then replace the historical 20 mm buried bracket endpoint.
            anchor = (fitting["x"], fitting["y"]+.025, VL.LEVEL_Z[fitting["level"]]+fitting["z"])
            choices = []
            for outward in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0)):
                trial = dict(scene, meshes=list(scene["meshes"]), mounting_hosts=dict(scene["mounting_hosts"]), mounting_movements=[])
                try:
                    h = measured_host(trial, anchor, outward, fitting["room"], prefix)
                    gap = abs(sum((anchor[i]-h.structural_point[i])*outward[i] for i in range(3)))
                    signed = sum((anchor[i]-h.structural_point[i])*outward[i] for i in range(3))
                    projected = [anchor[i]-signed*outward[i] for i in range(3)]
                    faces = trial["mounting_hosts"][prefix]["source_faces"]
                    contains = any(_on_polygon(projected, face, outward) for face in faces)
                    choices.append((0 if contains else 1, gap, outward))
                except ValueError:
                    pass
            outward = min(choices)[2]
            host = measured_host(scene, anchor, outward, fitting["room"], prefix)
            # Keep rail and handset elevations/position: shorten only the fixing end.
            fixing = sum(host.structural_point[i]*outward[i] for i in range(3))
            package(scene, members, host, fixing, "b-bathroom", bracket["id"])
    for valve in [m for m in originals if m.get("part_kind") == "extract-valve"]:
        ps = points(valve)
        anchor = tuple(sum(p[i] for p in ps)/len(ps) for i in range(3))
        host = measured_host(scene, anchor, (0,0,-1), valve["room"], valve["id"], kind="ceiling")
        package(scene, [valve], host, -max(p[2] for p in ps), "b-bathroom", valve["id"])
    for lamp in VL.design(lay):
        if lamp.kind not in ("SCONCE", "VSCONCE", "SWING", "WALL-READ"):
            continue
        members = [m for m in originals if m["id"].endswith("-" + lamp.id)]
        if lamp.kind == "SWING":
            x, y = lamp.extra["wall_plate"]
            outward = (1 if lamp.x > x else -1, 0, 0)
            anchor = (x, y, lamp.z)
            host = measured_host(scene, anchor, outward, lamp.room, lamp.id, panel=True)
            fixing = x*outward[0]
        else:
            outward = (0,1,0) if lamp.kind == "WALL-READ" else (1 if lamp.aim[0] > 0 else -1,0,0)
            anchor = (lamp.x, lamp.y, lamp.z)
            host = measured_host(scene, anchor, outward, lamp.room, lamp.id)
            # Bracket root, or body fixing back for sconces without brackets.
            root = next((m for m in members if m["id"].startswith("bracket-")), members[0])
            fixing = min(sum(p[i]*outward[i] for i in range(3)) for p in points(root))
        package(scene, members, host, fixing, "c-wall-lights", members[0]["id"])
