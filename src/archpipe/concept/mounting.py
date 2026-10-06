"""Place mounted objects from declared finished building faces.

Coordinates and lengths are metres.  A face normal points from its structural
datum toward the occupied side of the finish.  Offsets use that same direction.
This module is intentionally independent of the D1 layout and renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path


HOST_KINDS = frozenset({"wall", "ceiling", "floor", "stair-stringer", "joinery-panel"})
MOUNT_KINDS = frozenset({"surface-mounted", "recessed", "wall-hung", "suspended", "floor-standing"})

# One millimetre is an authored model comparison tolerance, not a workmanship
# allowance: it accommodates millimetre coordinate rounding and floating point
# export, but cannot hide the 13 mm plaster layer or the frozen 32 mm housing.
FACE_TOLERANCE_M = 0.001
BUILD_UP_RECORD = Path(__file__).resolve().parents[3] / "knowledge/finish-build-ups.json"
SITE_KINDS = frozenset({
    "handrail", "rail-bracket", "wall-plate", "stair-stringer",
    "wall-panel", "downlight-trim", "wall-marker", "light-diffuser",
    "lamp-housing", "lamp-cord", "lamp-wire", "lamp-arm", "lamp-head",
    "rain-head", "riser-rail", "mirror-panel", "extract-valve",
    "fan-grille", "screen", "tv_unit", "wc", "washbasin", "shelf",
    "trellis", "climber", "climber-branch", "curtain-track", "drain",
    "hanging-rail", "joinery_end_panel", "led-strip", "shower-head",
    "light-lens", "light-bulb", "lamp-joint", "appliance-housing",
})


def finish_from_record(assembly: str) -> Finish:
    """Read the sole lead-reviewed build-up record; unknown layers fail closed."""
    data = json.loads(BUILD_UP_RECORD.read_text(encoding="utf-8"))
    parts = [data["records"][key] for key in data["assemblies"][assembly]]
    if any(part["selected_mm"] is None for part in parts):
        raise ValueError(assembly + ": MISSING finish thickness")
    return Finish(assembly, sum(part["selected_mm"] for part in parts) / 1000)


@dataclass(frozen=True)
class Finish:
    name: str
    thickness_m: float

    def __post_init__(self):
        if not self.name or not math.isfinite(self.thickness_m) or self.thickness_m < 0:
            raise ValueError("Finish needs a name and nonnegative, finite build-up thickness")


@dataclass(frozen=True)
class Host:
    id: str
    kind: str
    structural_point: tuple[float, float, float]
    normal: tuple[float, float, float]
    finish: Finish
    void_depth_m: float | None = None

    def __post_init__(self):
        if not self.id or self.kind not in HOST_KINDS:
            raise ValueError("Mount host must be a declared building element")
        if len(self.structural_point) != 3 or not all(math.isfinite(v) for v in self.structural_point):
            raise ValueError("Host structural point needs three finite coordinates")
        if len(self.normal) != 3 or not all(math.isfinite(v) for v in self.normal):
            raise ValueError("Host normal needs three finite coordinates")
        if not math.isclose(math.sqrt(sum(v * v for v in self.normal)), 1.0, abs_tol=1e-9):
            raise ValueError("Host normal must have unit length")
        if not isinstance(self.finish, Finish):
            raise ValueError("Host needs a finish record")
        if self.void_depth_m is not None and (not math.isfinite(self.void_depth_m) or self.void_depth_m < 0):
            raise ValueError("Void depth must be finite and nonnegative")
        if self.kind == "floor" and self.normal != (0.0, 0.0, 1.0):
            raise ValueError("Floor normal must point upward")
        if self.kind == "ceiling" and self.normal[2] >= 0:
            raise ValueError("Ceiling normal must point into the room")


@dataclass(frozen=True)
class MountItem:
    id: str
    housing_depth_m: float | None = 0.0

    def __post_init__(self):
        if not self.id or (self.housing_depth_m is not None and
                          (not math.isfinite(self.housing_depth_m) or self.housing_depth_m < 0)):
            raise ValueError("Item needs an id and nonnegative, finite housing depth")


@dataclass(frozen=True)
class Placement:
    item_id: str
    host_id: str
    kind: str
    finished_face: tuple[float, float, float]
    position: tuple[float, float, float]
    normal: tuple[float, float, float]
    offset_m: float


def mount(item: MountItem, host: Host, face: str, offset: float, kind: str) -> Placement:
    """Return the item's fixing plane in world coordinates.

    ``face`` is ``finished``; bare structural/outline faces are forbidden.
    A surface mount and floor standing item use zero offset.  A wall-hung
    offset is its outward projection.  A recess offset is the positive depth
    behind the finished face to the item's fixing plane.  The full housing
    depth must fit behind that plane within the declared clear void.
    """
    if not isinstance(item, MountItem) or not isinstance(host, Host):
        raise TypeError("Mount needs a declared item and host")
    if face != "finished" or kind not in MOUNT_KINDS:
        raise ValueError("Mount needs a finished face and supported kind")
    if not math.isfinite(offset) or offset < 0:
        raise ValueError("Mount offset must be finite and nonnegative")
    if kind in ("surface-mounted", "floor-standing") and offset != 0:
        raise ValueError("Surface and floor mounts sit on the finished face")
    if kind == "wall-hung" and host.kind not in ("wall", "stair-stringer", "joinery-panel"):
        raise ValueError("Wall-hung mount needs a vertical host")
    if kind == "floor-standing" and host.kind != "floor":
        raise ValueError("Floor-standing mount needs a floor")
    if kind == "suspended" and host.kind != "ceiling":
        raise ValueError("Suspended mount needs a ceiling")
    if kind == "recessed":
        if host.void_depth_m is None or item.housing_depth_m is None:
            raise ValueError("MISSING recessed housing depth or clear void")
        if offset + item.housing_depth_m > host.void_depth_m + 1e-9:
            raise ValueError("Recessed housing exceeds the clear void behind the finished face")
    finished = tuple(host.structural_point[i] + host.normal[i] * host.finish.thickness_m for i in range(3))
    direction = -1 if kind == "recessed" else 1
    position = tuple(finished[i] + direction * host.normal[i] * offset for i in range(3))
    return Placement(item.id, host.id, kind, finished, position, host.normal, offset)


def binding(item: MountItem, host: Host, offset: float, kind: str) -> dict:
    """Export the fixing contract; the guard independently measures mesh vertices."""
    placement = mount(item, host, "finished", offset, kind)
    return dict(host_id=host.id, kind=kind, offset_m=offset,
                housing_depth_m=item.housing_depth_m,
                finished_face=list(placement.finished_face))


def stacked_finish_bridge(lower: Host, upper: Host, lower_faces, upper_faces, slab_depth_m):
    """Continue an identical coplanar wall finish across the intervening slab.

    Only the slab-edge strip is added, using the upper wall's actual run.
    Neither wall footprint is extended below or above that strip. Offsets,
    different finishes, nonvertical hosts and excessive gaps do not merge.
    """
    if (lower.kind != "wall" or upper.kind != "wall" or lower.finish != upper.finish or
            lower.normal != upper.normal or abs(lower.normal[2]) > 1e-9 or
            abs(sum((lower.structural_point[i] - upper.structural_point[i]) * lower.normal[i]
                    for i in range(3))) > 1e-9):
        return []
    low_top = max(p[2] for f in lower_faces for p in f)
    high_bottom = min(p[2] for f in upper_faces for p in f)
    if not 1e-9 < high_bottom - low_top <= slab_depth_m + 1e-9:
        return []
    bridges = []
    for face in upper_faces:
        edge = [p for p in face if abs(p[2] - high_bottom) < 1e-9]
        if len(edge) == 2:
            a, b = edge
            bridges.append([list(a), list(b), [*b[:2], low_top], [*a[:2], low_top]])
    return bridges


def check_mesh(mesh: dict, hosts: dict[str, Host]) -> list[str]:
    """Compare the nearest mesh plane to its declared fixing projection.

    Projection is distance along the host's outward normal. The nearest
    vertex plane is the back of a surface/wall-hung component, or the deepest
    plane of a recessed housing. Child components need their own explicit
    projection; their emitter position is never treated as a fixing point.
    """
    mid = mesh["id"]
    contract = mesh.get("mounting")
    if not contract or contract.get("host_id") not in hosts:
        return [mid + ": MISSING mounting host"]
    host = hosts[contract["host_id"]]
    try:
        item = MountItem(mid, contract.get("housing_depth_m"))
        placement = mount(item, host, "finished", contract["offset_m"], contract["kind"])
    except (TypeError, ValueError, KeyError) as exc:
        return [mid + ": " + str(exc)]
    points = [point for face in mesh["faces"] for point in face]
    if not points or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        return [mid + ": MISSING or nonfinite mounting geometry"]
    gaps = [sum((p[i] - placement.finished_face[i]) * host.normal[i] for i in range(3)) for p in points]
    # Recessed records measure their deepest body plane, not a trim or emitter.
    if contract.get('geometry_role') == 'recessed-trim':
        clearance = contract.get('installation_clearance_m')
        if clearance is None or not math.isfinite(clearance) or clearance < 0:
            return [mid + ': MISSING installation clearance requirement']
        if item.housing_depth_m + contract['offset_m'] + clearance > host.void_depth_m + 1e-9:
            return [mid + ': housing plus installation clearance exceeds required void']
        if contract.get('resolution_status') != 'requirement':
            return [mid + ': recessed trim must retain construction requirement status']
    expected = (-contract["offset_m"] if contract.get('geometry_role') == 'recessed-trim' else
                -contract["offset_m"] - item.housing_depth_m
                if contract["kind"] == "recessed" else contract["offset_m"])
    if contract.get('geometry_role') == 'assembly-child':
        projection = contract.get('child_projection_m')
        if (contract['kind'] != 'floor-standing' or not isinstance(projection, (int,float))
                or not math.isfinite(projection) or projection < 0):
            return [mid + ': invalid generated support projection']
        expected = projection
    error = min(gaps) - expected
    if abs(error) > FACE_TOLERANCE_M + 1e-9:
        return [f"{mid}: finished-face error {error * 1000:+.3f} mm (tolerance 1 mm)"]
    recorded = contract.get("finished_face")
    if recorded is None or len(recorded) != 3 or any(
            not math.isfinite(v) or abs(v - placement.finished_face[i]) > 1e-9
            for i, v in enumerate(recorded)):
        return [mid + ": stale or MISSING finished face"]
    return []


def scene_findings(scene: dict) -> list[str]:
    """Fail closed on every phase-1 inventory site, with no exemption list.

    Legacy sites remain failures until each builder declares a measured host
    and fixing contract. A shared hierarchy for child parts is future work;
    the guard cannot silently accept an arm, lens or climber without one.
    """
    hosts, failures = {}, []
    for host_id, record in scene.get("mounting_hosts", {}).items():
        try:
            host = Host(record["id"], record["kind"], tuple(record["structural_point"]),
                        tuple(record["normal"]), Finish(**record["finish"]), record.get("void_depth_m"))
            if host.id != host_id:
                raise ValueError("host key disagrees with host id")
            hosts[host_id] = host
        except (TypeError, ValueError, KeyError) as exc:
            failures.append(host_id + ": invalid mounting host: " + str(exc))
    for mesh in scene["meshes"]:
        if mesh.get("part_kind") in SITE_KINDS or mesh["id"].startswith("furn-") or "mounting" in mesh:
            failures.extend(check_mesh(mesh, hosts))
        contract = mesh.get('mounting', {})
        if contract.get('geometry_role') == 'assembly-child':
            root = next((m for m in scene['meshes'] if m['id']==contract.get('assembly_root')),None)
            root_contract = {} if root is None else root.get('mounting',{})
            if (root is mesh or root_contract.get('geometry_role')=='assembly-child' or
                    root_contract.get('kind')!='floor-standing' or
                    root_contract.get('host_id')!=contract.get('host_id')):
                failures.append(mesh['id']+': MISSING independent floor-bearing assembly root')
        for support_id in contract.get('support_parts', []):
            support=next((m for m in scene['meshes'] if m['id']==support_id),None)
            if support is None or not support.get('mounting'):
                failures.append(mesh['id']+': MISSING declared supporting part '+support_id)
            else:
                a=[p for f in mesh['faces'] for p in f]; b=[p for f in support['faces'] for p in f]
                if any(max(min(p[i] for p in a),min(p[i] for p in b))>
                       min(max(p[i] for p in a),max(p[i] for p in b)) + FACE_TOLERANCE_M for i in range(3)):
                    failures.append(mesh['id']+': supporting part does not meet assembly '+support_id)
        contract=mesh.get('mounting',{})
        if contract.get('geometry_role')=='recessed-trim':
            record=scene.get('mounting_hosts',{}).get(contract.get('host_id'),{})
            if record.get('void_status') != 'requirement' or not record.get('housing_source') or not record.get('clearance_source'):
                failures.append(mesh['id']+': MISSING sourced construction requirement host status')
    from .attached_assembly import findings as attached_findings
    failures.extend(attached_findings(scene))
    from .support_mounting import plant_support_findings
    failures.extend(plant_support_findings(scene))
    failures.extend(host_coverage_findings(scene, hosts))
    for mesh in scene['meshes']:
        root_id=mesh.get('associated_mounting_root')
        if root_id:
            root=next((m for m in scene['meshes'] if m['id']==root_id),None)
            contract={} if root is None else root.get('mounting',{})
            host=hosts.get(contract.get('host_id'))
            if host is None:
                failures.append(mesh['id']+': MISSING associated assembly support root')
            else:
                face=[host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
                gap=min(sum((p[i]-face[i])*host.normal[i] for i in range(3)) for f in mesh['faces'] for p in f)
                if gap < -FACE_TOLERANCE_M-1e-9:
                    failures.append(f"{mesh['id']}: associated assembly body penetrates support face {-gap*1000:.3f} mm")
        path = mesh.get('hose_path')
        contract = mesh.get('mounting', {})
        if path and contract.get('host_id') in hosts:
            host = hosts[contract['host_id']]
            face = [host.structural_point[i]+host.normal[i]*host.finish.thickness_m for i in range(3)]
            gap = lambda p: sum((p[i]-face[i])*host.normal[i] for i in range(3))
            if (path['points'][0] != path['retained_endpoints'][0] or
                    path['points'][-1] != path['retained_endpoints'][1]):
                failures.append(mesh['id'] + ': hose connection endpoints changed')
            if (min(map(gap,path['points'])) < path['radius_m']+path['clearance_m']-1e-9 or
                    min(gap(p) for f in mesh['faces'] for p in f) < path['clearance_m']-1e-9):
                failures.append(mesh['id'] + ': hose violates radius plus finished-wall clearance')
    return failures


def _on_polygon(point, face, normal):
    """Inclusive point containment projected onto the host's two tangent axes.

    Drop the coordinate with the largest normal component; the remaining
    coordinates uniquely describe points on this plane, including non-axis
    aligned faces. Polygon edge contact is accepted to avoid a false positive
    at the ends of an authored wall panel.
    """
    dropped = max(range(3), key=lambda axis: abs(normal[axis]))
    axes = [axis for axis in range(3) if axis != dropped]
    x, y = (point[axis] for axis in axes)
    polygon = [(p[axes[0]], p[axes[1]]) for p in face]
    inside = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if (abs(cross) < 1e-9 and min(ax, bx) - 1e-9 <= x <= max(ax, bx) + 1e-9 and
                min(ay, by) - 1e-9 <= y <= max(ay, by) + 1e-9):
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def host_coverage_findings(scene: dict, hosts: dict[str, Host]) -> list[str]:
    """A surface fixing must reach an actual finite host face in the scene.

    This first layer checks every back-plane vertex and their centre. It
    cannot certify anchor capacity or full polygon containment across holes;
    those need native coordination. A projected wall-hung component still
    needs separately declared brackets/parent support, not a false assertion
    that its body touches the wall.
    """
    failures = []
    for mesh in scene["meshes"]:
        contract = mesh.get("mounting")
        if (not contract or contract.get('geometry_role')=='assembly-child' or
                contract.get("kind") not in ("surface-mounted","floor-standing") or contract.get("host_id") not in hosts):
            continue
        host = hosts[contract["host_id"]]
        position = mount(MountItem(mesh["id"]), host, "finished", 0, "surface-mounted").finished_face
        surfaces = [face for member in (scene.get("diagnostic_meshes", []) + scene.get("meshes", []))
                    if member.get("finished_host_id") == host.id
                    for face in member["faces"] if all(abs(sum((p[i] - position[i]) * host.normal[i]
                                                               for i in range(3))) < 1e-8 for p in face)]
        points = [p for face in mesh["faces"] for p in face]
        fixing = []
        for point in points:
            gap = sum((point[i] - position[i]) * host.normal[i] for i in range(3))
            if abs(gap) <= FACE_TOLERANCE_M + 1e-9:
                # Use the same 1 mm comparison tolerance as the plane check,
                # then project onto the actual host plane for containment.
                fixing.append([point[i] - gap * host.normal[i] for i in range(3)])
        if fixing:
            fixing.append([sum(p[i] for p in fixing) / len(fixing) for i in range(3)])
        fixing.extend(contract.get('fixing_footprint', []))
        if not fixing or not all(any(_on_polygon(point, face, host.normal) for face in surfaces) for point in fixing):
            failures.append(mesh["id"] + ": MISSING finite host coverage at fixing footprint")
    return failures
