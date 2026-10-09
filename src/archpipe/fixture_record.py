"""Fixture record consistency and cross-subsystem verification.

In accordance with the Class C5 rule established in docs/lessons-audit.md:
"One fixture record owns photometry, emitter, housing and mount."

This module cross-checks luminaire data across:
1. Photometry declared flux and CCT vs render emitter & design requirements (l0123, l0080).
2. Emitter position vs housing geometry (emitter inside housing, l0095).
3. Mounting height in specification vs built emitter (l0095, l0096).
4. Housing clearance vs finished ceiling (l0119, l0096).
5. Fitting label vs room containment and product records (l0610).

Quick Test:
    python -c "from archpipe.fixture_record import fixture_findings; print(callable(fixture_findings))"

Example Usage:
    >>> from archpipe.fixture_record import fixture_findings, check_fixture_record_consistency
    >>> findings = fixture_findings({"spec": {"lighting": []}})
    >>> isinstance(findings, list)
    True
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from archpipe import fixture_source
from archpipe.concept import villa_furnish as F
from archpipe.luminaires import install
from archpipe.luminaires import library as lib
from archpipe import photometry as ph



from types import MappingProxyType

# kind -> the requirement (what a product must meet) and its generic stand-in
KINDS = {
    "DL":   dict(what="flush trimless downlight, wide", mount="recessed", lm=650, beam=55, cct=2700, cri=90,
                 layer="ambient", aperture=0.075),
    "DLN":  dict(what="flush trimless downlight, medium (task)", mount="recessed", lm=750, beam=36, cct=3000,
                 cri=90, layer="task", aperture=0.075),
    "ADJ":  dict(what="flush trimless adjustable accent", mount="recessed", lm=500, beam=24, cct=2700, cri=90,
                 layer="accent", aperture=0.075),
    "WW":   dict(what="flush trimless wall washer", mount="recessed", lm=650, beam=70, cct=2700, cri=90,
                 layer="accent", aperture=0.075),
    "PEN-GLOBE": dict(what="opal glass globe pendant D300", mount="pendant", lm=800, beam=None, cct=2700, cri=90,
                      layer="decorative", diameter=0.30),
    "PEN-SMALL": dict(what="opal glass globe pendant D200 (bedside)", mount="pendant", lm=350, beam=None, cct=2700,
                      cri=90, layer="decorative", diameter=0.20),
    "WALL-READ": dict(what="adjustable wall-mounted swing-arm reading light (ASSUMED product)", mount="wall",
                      lm=350, beam=None, cct=2700, cri=90, layer="decorative", diameter=0.12),
    "SWING": dict(what="movable wall reading light: wall plate, articulated 0.6 m reach and rotating head "
                  "(ASSUMED product; TODO swing-arm-product)", mount="wall", lm=350, beam=None,
                  cct=2700, cri=90, layer="task", diameter=0.12, reach=0.6),
    "PEN-LIN": dict(what="linear pendant 1.6 m, direct/indirect", mount="pendant", lm=1200, beam=90, cct=2700,
                    cri=90, layer="task", length=1.6),
    "SCONCE": dict(what="vanity wall light, opal, each side of the mirror", mount="wall", lm=450, beam=None,
                   cct=3000, cri=90, layer="task", diameter=0.12),
    "COVE": dict(what="LED strip in the cove, 2700 K", mount="strip", lm_per_m=900, cct=2700, cri=90,
                 layer="decorative"),
    "BACK": dict(what="LED strip inside glass-door book cabinet", mount="strip", lm_per_m=400, cct=2700, cri=90,
                 layer="accent"),
    "UC":   dict(what="under-cabinet LED strip", mount="strip", lm_per_m=1000, cct=3000, cri=90, layer="task"),
    "RAIL": dict(what="LED strip over the hanging rail (in-wardrobe)", mount="strip", lm_per_m=500, cct=3000, cri=90,
                 layer="task"),
    "TOE":  dict(what="toe-kick LED strip", mount="strip", lm_per_m=150, cct=2200, cri=90, layer="night"),
    "NL":   dict(what="night-light strip under the bed / plinth", mount="strip", lm_per_m=100, cct=2200, cri=90,
                 layer="night"),
    "DESK": dict(what="adjustable wall-arm desk lamp, shielded head, 3000 K", mount="task-lamp", lm=450, beam=70,
                 cct=3000, cri=90, layer="task"),
    "VSTRIP": dict(what="vertical LED strip at a hanging-section edge (shadow-free dressing light)", mount="strip",
                   lm_per_m=500, cct=3000, cri=90, layer="task"),
    "STORE-BATTEN": dict(what="ASSUMED opal LED storage batten, 0.70 m per shelving bay", mount="strip",
                          lm_per_m=900, cct=3000, cri=90, layer="task"),
    "MIRROR": dict(what="backlit mirror halo, 3000 K", mount="strip", lm_per_m=250, cct=3000, cri=90, layer="task"),
    "VANITY-LIN": dict(what="ASSUMED generic linear LED bar over the mirror", mount="wall",
                       lm=100, beam=None, cct=3000, cri=90, layer="task"),
    "VSCONCE": dict(what="vertical opal sconce 0.5 m, each side of the mirror", mount="wall", lm=450, beam=None,
                    cct=3000, cri=90, layer="task", diameter=0.12),
    "STEP": dict(what="recessed step marker in the stair wall", mount="wall-marker", lm=60, beam=None, cct=2200,
                 cri=90, layer="night"),
    "PATH": dict(what="low recessed path marker (0.3 m AFF)", mount="wall-marker", lm=60, beam=None, cct=2200,
                 cri=90, layer="night"),
}

# kind -> the verified library product that meets it (lighting-library: imported, flux vs LORL and LDT vs the
# manufacturer's IES checked). Strips, pendants, sconces and markers stay GENERIC: iGuzzini Underscore ST49 failed
# its LDT/IES pair check (59.8 %), the Laser Evo wall washer LSEVO-AAKR2I failed it (100 %, asymmetric), and no
# decorative globe pendant with photometry was found. WW is served meanwhile by the soft flood placed 0.3 m off the
# wall (grazing), stated as a substitute.
PRODUCT_CHOICE = {
    "DL": ("iguzzini", "LSEVO-AAK3EW", "Laser Evo recessed D75 Soft, Flood 33 deg, 2700 K CRI97, phase-cut; "
                                       "flush (trimless) accessory"),
    "DLN": ("iguzzini", "LSEVO-AAIIA6", "Laser Evo recessed D75 Cone, Medium 29 deg, 2700 K CRI90, phase-cut; "
                                        "flush (trimless) accessory"),
    "ADJ": ("iguzzini", "LSEVO-AAHENX", "Laser Evo recessed D75 Cone Easy Adjustable, Spot 18 deg, 2700 K CRI97, "
                                        "phase-cut; flush (trimless) accessory"),
    "WW": ("iguzzini", "LSEVO-AAK3EW", "SUBSTITUTE for the wall washer LSEVO-AAKR2I (files failed the pair check): "
                                       "Laser Evo D75 Soft Flood 33 deg grazing from 0.3 m"),
}

@dataclass(frozen=True)
class FixtureKind:
    """Authored requirement and procedural housing; all dimensions metres.

    lm means lumens, lm_per_m lumens per metre, cct colour temperature in
    kelvin, cri colour rendering index, beam full width at half maximum in
    degrees. None beam means isotropic. Unknown native family, measured
    housing and recess depth remain unknown rather than fabricated.
    """
    kind: str
    requirement: tuple
    geometry: tuple
    product_choice: tuple | None = None

    @property
    def spec(self):
        return MappingProxyType(dict(self.requirement))

    @property
    def housing(self):
        return MappingProxyType(dict(self.geometry))

    @property
    def mount(self):
        return self.spec['mount']


# Frozen existing procedural dimensions: re-expression, not new product claims.
_GEOMETRY = {
    'recessed': dict(trim_radius=.0415, trim_z=-.0015, lens_radius=.018, lens_z=-.002, render_z=-.03),
    'DESK': dict(render_z=-.03, shade_half=.08, shade_bottom=-.01, shade_top=.05,
                 stem_radius=.007, arm_top=.12, base_radius=.07, base_height=.015, reach=.28),
    'BACK': dict(cabinet_rear=-.04, cabinet_front=.006, body_bottom=-.012, body_top=.002, storage_half_width=.008),
    'WALL-READ': dict(bracket_half_width=.012),
    'VANITY-LIN': dict(length=.50, half_depth=.02, half_height=.02, centre_above_mirror=.10,
                       diffuser_inset=.004, edge_margin=.005),
    'VSCONCE': dict(half_width=.03, half_height=.25, wall_offset=.06,
                    bracket_half_width=.015, bracket_half_height=.02, emitting_area=.12),
    'SWING': dict(arm_length=.30, plate_depth=.012, plate_radius=.05, arm_radius=.018,
                  knuckle_radius=.022, shade_radius=.06, shade_height=.10, shade_tilt=.03,
                  shade_inner_drop=.008, shade_wall=.006, shade_lip=.002, emitter_radius=.055, emitter_z=-.002),
    'PEN-LIN': dict(half_width=.03, height=.06, diffuser_end=.05, diffuser_half_width=.015,
                    diffuser_z=-.001, wire_span=.6, wire_radius=.002),
    'strip': dict(width=.012, spread=120),
    'wall-marker': dict(width=.10, height=.04, face_offset=.001),
    'globe': dict(inner_ratio=.55, cord_radius=.003, canopy_radius=.05, canopy_depth=.02),
    'STORE-BATTEN': dict(half_width=.025, height=.035, mount_end=.04, mount_half_width=.012,
                        mount_z=.03, diffuser_end=.015, diffuser_half_width=.018, diffuser_z=-.001),
}


def _kind_record(kind, requirement):
    geometry = dict(_GEOMETRY.get(requirement['mount'], {}))
    geometry.update(_GEOMETRY.get(kind, {}))
    if kind in ('PEN-GLOBE', 'PEN-SMALL', 'SCONCE', 'WALL-READ'):
        geometry.update(_GEOMETRY['globe'])
        geometry['radius'] = requirement['diameter']/2
        if requirement['mount'] == 'wall':
            geometry['wall_offset'] = geometry['radius']
    if kind in ('SCONCE','VSCONCE'):
        geometry.update(vanity_half_spacing=.475, edge_margin=.005)
    return FixtureKind(kind, tuple(requirement.items()), tuple(geometry.items()), PRODUCT_CHOICE.get(kind))


FIXTURE_KINDS = MappingProxyType({kind: _kind_record(kind, spec) for kind, spec in KINDS.items()})
KINDS = MappingProxyType({kind: record.spec for kind, record in FIXTURE_KINDS.items()})
PRODUCT_CHOICE = MappingProxyType({kind: record.product_choice for kind, record in FIXTURE_KINDS.items()
                                   if record.product_choice is not None})
PRODUCTS = {}
_products_bound = False


def bind_products(ies_dir=None):
    """Bind measured library photometry once, retaining original generic fallback."""
    global _products_bound
    if _products_bound:
        return PRODUCTS
    ies_dir = Path(ies_dir or Path(__file__).resolve().parents[2] / 'out/villa/render-d1/ies')
    for kind, (mfr, sku, what) in PRODUCT_CHOICE.items():
        row = lib.get(mfr, sku, 0)
        if not row or not row.get('verified'):
            continue
        path = lib.export_ies(mfr, sku, 0, ies_dir / mfr / (sku + '.ies'))
        PRODUCTS[kind] = dict(manufacturer=mfr, code=sku, ies=str(path), lm=float(row['luminaire_lm']),
                              watts=row['watts'], cct=row['cct_k'], beam=row['beam_deg'], what=what,
                              substitute=what.startswith('SUBSTITUTE'))
    _products_bound = True
    return PRODUCTS


@dataclass(frozen=True)
class FixtureRecord:
    """Placed identity, photometry, emitter datum, housing and mount.

    position is authored x/y/z in model metres. aim and along are unit
    directions. length is metres; flux_lm is luminous flux in lumens.
    The analytic datum and legacy render offset remain explicitly distinct;
    unification preserves calibration. Product metadata is immutable.
    """
    id: str
    definition: FixtureKind
    room: str
    level: str
    position: tuple
    aim: tuple
    length: float
    along: tuple
    flux_lm: float
    product: tuple
    extra: tuple

    @property
    def housing(self):
        return self.definition.housing

    @property
    def mount(self):
        return self.definition.mount

    @property
    def cct_k(self):
        return int(dict(self.product)['cct']) if self.product else self.definition.spec['cct']

    @property
    def ies_relative(self):
        product = dict(self.product)
        return (product['manufacturer']+'/'+product['code']+'.ies') if product else 'generic/'+self.definition.kind+'.ies'

    @property
    def render_position(self):
        x,y,z = self.position
        return (x,y,z+self.housing.get('render_z',0))

    def photometry(self):
        product = dict(self.product)
        if product:
            return ph.load(product['ies']), False
        from archpipe.concept.villa_lighting import generic_ies
        spec = self.definition.spec
        flux = spec.get('lm') or spec.get('lm_per_m',100)
        beam = 120 if self.mount == 'strip' else spec.get('beam',120)
        return ph.parse(generic_ies(flux,beam), name=self.definition.kind), True

    def native_spec(self):
        """Native lighting adapter; convert authored metres to millimetres."""
        result = dict(id=self.id,kind=self.definition.kind,room=self.room,level=self.level,
                    at=[1000*v for v in self.position[:2]],mounting_height=1000*self.position[2],
                    lumens=self.flux_lm,kelvin=self.cct_k,mount=self.mount,ies=self.ies_relative,
                    housing=dict(self.housing))
        extra = dict(self.extra)
        if extra.get('over_mirror'):
            result.update(assumptions=extra['assumptions'],decision_source=extra['decision_source'])
        return result


def _freeze_value(value):
    """Own nested metadata so an authored Fixture cannot mutate a frozen record."""
    if isinstance(value, dict):
        return tuple((key,_freeze_value(item)) for key,item in value.items())
    if isinstance(value, (list,tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


def record_for(fixture):
    """Resolve a placed compatibility Fixture without copying declarations."""
    definition = FIXTURE_KINDS[fixture.kind]
    product = bind_products().get(fixture.kind)
    spec = definition.spec
    if product:
        flux = product['lm']
    elif fixture.lm is not None:
        flux = fixture.lm
    else:
        flux = spec['lm_per_m']*fixture.length if 'lm_per_m' in spec else spec['lm']
    flux *= fixture.extra.get('dimmer',1.0)
    return FixtureRecord(fixture.id,definition,fixture.room,fixture.level,
                         (fixture.x,fixture.y,fixture.z),tuple(fixture.aim),fixture.length,
                         tuple(fixture.along),flux,tuple(product.items()) if product else (),
                         _freeze_value(fixture.extra))


def kind_photometry(kind):
    """The same immutable kind definition serves calculations and exporters."""
    definition = FIXTURE_KINDS[kind]
    product = bind_products().get(kind)
    record = FixtureRecord(kind,definition,'','',(0,0,0),(0,0,-1),0,(1,0,0),0,
                           tuple(product.items()) if product else (),())
    return record.photometry()



# Client decision is authored input, separate from the frozen migration history.
VANITY_DECISIONS = MappingProxyType({
    'guest-wc': ('SCONCE-guest-wc-03', 'SCONCE-guest-wc-04'),
    'parents-ensuite': ('VSCONCE-parents-ensuite-04', 'VSCONCE-parents-ensuite-05'),
})
VANITY_DECISION_SOURCE = 'CLIENT DECISION 2026-10-08'


def over_mirror_datum(room_rect, basin, mirror_width, mirror_top, finished_wall, normal):
    """Construct a centred wall bar without moving the mirror/basin axis.

    All distances are model metres. basin is its plan rectangle; normal is
    +1 or -1 along x into the room. finished_wall is the finished x face.
    Size, 100 mm centre offset and 100 lumen raw output are ASSUMED authored;
    held cards supply neither an over-mirror offset nor a bar lumen output.
    """
    housing = FIXTURE_KINDS['VANITY-LIN'].housing
    axis = (basin[1]+basin[3])/2
    length = housing['length']
    z = mirror_top+housing['centre_above_mirror']
    failures = vanity_pair_findings([axis], (room_rect[1],room_rect[3]), axis,
        (axis-mirror_width/2,axis+mirror_width/2), length/2, 0,
        housing['edge_margin'], over_mirror=(z,mirror_top,housing['half_height']))
    x = finished_wall+normal*housing['half_depth']
    if (x-housing['half_depth'] < room_rect[0]+housing['edge_margin']-1e-6
            or x+housing['half_depth'] > room_rect[2]-housing['edge_margin']+1e-6):
        failures.append('over-mirror depth exceeds room clear boundary')
    if failures:
        raise ValueError('; '.join(failures))
    return x, axis, z


def centred_vanity_pair(clear_interval, axis, mirror_interval, half_width,
                        minimum_gap, authored_separation=.950, edge_allowance=.005):
    """Return the largest feasible separation without moving the mirror axis.

    All values are metres along the mounting wall. clear_interval and
    mirror_interval are their lower/upper edges; axis is the fixed basin and
    mirror centre. half_width covers the complete fitting envelope.
    minimum_gap must carry an external source or an explicit authored
    assumption at the call site. The 950 mm preference and 5 mm allowance
    are authored design values, not standards. Refuse an infeasible pair.
    """
    values = (*clear_interval, axis, *mirror_interval, half_width,
              minimum_gap, authored_separation, edge_allowance)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Vanity dimensions must be finite')
    low, high = clear_interval
    mirror_low, mirror_high = mirror_interval
    if (low >= high or mirror_low >= mirror_high or half_width <= 0
            or minimum_gap <= 0 or authored_separation <= 0 or edge_allowance < 0):
        raise ValueError('Vanity intervals, widths and clear gap must be positive')
    if abs((mirror_low+mirror_high)/2-axis) > 1e-6:
        raise ValueError('Mirror and basin axes disagree; do not move either')
    maximum = min(authored_separation,
                  2*(axis-low-half_width-edge_allowance),
                  2*(high-axis-half_width-edge_allowance))
    minimum = 2*max(axis-mirror_low+half_width+minimum_gap,
                    mirror_high-axis+half_width+minimum_gap)
    if minimum > maximum+1e-12:
        raise ValueError(f'No centred vanity pair: requires {minimum*1000:.3f} mm separation; '
                         f'maximum {maximum*1000:.3f} mm; '
                         f'shortfall {(minimum-maximum)*1000:.3f} mm')
    return axis-maximum/2, axis+maximum/2


def vanity_pair_findings(centres, clear_interval, axis, mirror_interval,
                         half_width, minimum_gap, edge_allowance=.005, *, over_mirror=None):
    """Review an actual pair independently of its placement solver.

    Inputs are metres along the wall, as defined by centred_vanity_pair.
    The two centres come from authored datums or measured complete fitting
    bounds. A 1 micrometre arithmetic tolerance absorbs floating point only.
    """
    if over_mirror is not None:
        # Explicit type prevents a missing side-pair member becoming a pass.
        # over_mirror gives centre z, mirror top z and fitting half-height.
        if len(centres) != 1:
            return ['vanity_single_members: expected one complete over-mirror fitting']
        centre_z, mirror_top, half_height = over_mirror
        centre = centres[0]
        values = (centre, *clear_interval, axis, *mirror_interval, half_width,
                  edge_allowance, centre_z, mirror_top, half_height)
        if (not all(math.isfinite(v) for v in values) or half_width <= 0 or half_height <= 0
                or clear_interval[0] >= clear_interval[1] or mirror_interval[0] >= mirror_interval[1]
                or edge_allowance < 0):
            return ['vanity_single_dimensions: invalid complete fitting or mirror bounds']
        findings = []
        if abs(centre-axis) > 1e-6:
            findings.append('vanity_pair_symmetry: single fitting differs from fixed mirror/basin axis')
        if centre-half_width < clear_interval[0]+edge_allowance-1e-6 or centre+half_width > clear_interval[1]-edge_allowance+1e-6:
            findings.append('vanity_pair_boundary: complete fitting envelope exceeds clear boundary allowance')
        if centre-half_width < mirror_interval[0]-1e-6 or centre+half_width > mirror_interval[1]+1e-6:
            findings.append('vanity_single_length: fitting exceeds mirror width')
        if centre_z-half_height <= mirror_top+1e-6:
            findings.append('vanity_single_mirror_overlap: fitting must clear mirror top')
        return findings
    if len(centres) != 2:
        return ['vanity_pair_members: expected exactly two complete fittings']
    left, right = sorted(centres)
    low, high = clear_interval
    mirror_low, mirror_high = mirror_interval
    findings = []
    offset = (left+right)/2-axis
    if abs(offset) > 1e-6:
        findings.append(f'vanity_pair_symmetry: midpoint differs from fixed mirror/basin axis '
                        f'by {offset*1000:.3f} mm')
    if left-half_width < low+edge_allowance-1e-6 or right+half_width > high-edge_allowance+1e-6:
        findings.append('vanity_pair_boundary: complete fitting envelope exceeds clear boundary allowance')
    gaps = (mirror_low-left-half_width, right-half_width-mirror_high)
    if min(gaps) < minimum_gap-1e-6:
        findings.append(f'vanity_pair_mirror_gap: {gaps[0]*1000:.3f}/{gaps[1]*1000:.3f} mm; '
                        f'requires {minimum_gap*1000:.3f} mm each side')
    return findings


def vanity_pair_datum(room_rect, centre, kind):
    """Prevent a mirror pair crossing a room end, preserving authored spacing.

    LEAD-REJECTED historical Phase-2 placement. Do not integrate this
    result as an accepted correction; use centred_vanity_pair for proposals
    and vanity_pair_findings for review (docs/c5-phase2-report.md).

    room_rect is the wall-clear rectangle in metres. centre is the original
    centre along the wall. The authored separation is 0.95 metre. The 5 mm
    edge margin is the existing lead-approved mounting envelope allowance,
    not a new standard. Return the centre and whether correction is needed.
    """
    definition = FIXTURE_KINDS[kind]
    housing = definition.housing
    half_width = housing['half_width'] if kind == 'VSCONCE' else housing['radius']
    half_span = housing['vanity_half_spacing'] + half_width + housing['edge_margin']
    low, high = room_rect[1]+half_span, room_rect[3]-half_span
    if low > high:
        raise ValueError('Vanity wall cannot hold the authored sconce pair and fixing envelopes')
    corrected = min(max(centre,low),high)
    return corrected, abs(corrected-centre)>1e-9


def reconcile_vanity_emitters(scene, fixtures):
    """Carry complete fitting assemblies to current authored emitter datums.

    C4 frozen approval inputs remain unchanged. This lighting-only final
    step resolves the current record after those historical moves, without
    moving furniture, hosts, cameras, meters or altering luminous flux.
    """
    from archpipe.concept.attached_assembly import translate
    by = {m['id']:m for m in scene['meshes']}
    changes = []
    for fixture in fixtures:
        if not fixture.extra.get('vanity_pair_source_correction'):
            continue
        record = fixture.record
        root = by['lamp-'+record.id]
        points = [p for face in root['faces'] for p in face]
        centre = [(min(p[i] for p in points)+max(p[i] for p in points))/2 for i in range(3)]
        delta = [record.position[i]-centre[i] for i in range(3)]
        # Lamp and bracket are one assembly; translate both exactly once.
        members = [m for m in scene['meshes'] if m['id'].endswith('-'+record.id)]
        member_ids = {m['id'] for m in members}
        for member in members:
            translate(scene,member['id'],delta,deferred_ids=member_ids-{member['id']})
            if 'mounting' in member:
                footprint = member['mounting'].get('fixing_footprint')
                if footprint:
                    member['mounting']['fixing_footprint'] = [[p[i]+delta[i] for i in range(3)] for p in footprint]
        changes.append(dict(id=record.id,delta_mm=[round(1000*v,6) for v in delta],
                            source='current authored pair, retained 950 mm separation'))
    scene['fixture_source_corrections'] = changes
    failures = vanity_scene_findings(scene, [fixture.record for fixture in fixtures
                                           if fixture.extra.get('vanity_pair_source_correction')])
    if failures:
        raise FixtureConsistencyError('; '.join(failures))
    return changes


class UnreadableFixtureRecordError(FileNotFoundError, ValueError):
    """Raised when fixture record input is missing, unreadable, or invalid."""
    pass


class FixtureConsistencyError(ValueError):
    """Raised when fixture consistency checks find discrepancies."""
    pass


@dataclass(frozen=True)
class FixtureFinding:
    """A single finding from fixture consistency inspection."""
    fixture_id: str
    rule: str
    lesson_id: str
    status: str  # "FAIL", "WARN", "NOTE", "PASS"
    message: str
    declared: Any = None
    actual: Any = None


def fixture_findings(
    scene_or_spec: Any = None,
    *,
    spec: dict | None = None,
    scene: dict | None = None,
    meshes: dict | None = None,
    layout: dict | None = None,
    ceiling_mm: float = 2700.0,
) -> list[FixtureFinding]:
    """Inspect luminaire records and report discrepancies across subsystems.

    Calls authoritative production functions to evaluate:
    - Photometry declared flux / CCT vs render emitter (l0123, l0080).
    - Emitter position vs housing geometry (l0095).
    - Specification mounting height vs built emitter (l0096).
    - Housing penetration vs ceiling height, distinguishing recessed (l0119).
    - Fitting label vs room clear rectangle containment (l0610).

    Args:
        scene_or_spec: Path to spec/scene JSON/YAML, or dictionary containing
            spec, scene, meshes, layout, or lighting entries.
        spec: Explicit specification dictionary with lighting list.
        scene: Explicit render scene dictionary with lights and meshes.
        meshes: Explicit mapping of fixture ID to extract mesh lists.
        layout: Explicit architectural layout dictionary (rooms, clear rects).
        ceiling_mm: Finished ceiling elevation in millimetres.

    Returns:
        List of FixtureFinding records detailing PASS, NOTE, WARN, or FAIL.

    Raises:
        UnreadableFixtureRecordError: If inputs are missing, unreadable, empty,
            or corrupt.
    """
    if (
        scene_or_spec is None
        and spec is None
        and scene is None
        and meshes is None
        and layout is None
    ):
        raise UnreadableFixtureRecordError(
            "Missing fixture record input: no scene, spec, meshes, or layout provided"
        )

    # Resolve file path input if provided
    if isinstance(scene_or_spec, (str, Path)):
        path = Path(scene_or_spec)
        if not str(path).strip():
            raise UnreadableFixtureRecordError("Fixture record input path cannot be empty")
        if not path.exists():
            raise UnreadableFixtureRecordError(f"Fixture record file not found: {path}")
        if not path.is_file():
            raise UnreadableFixtureRecordError(f"Fixture record path is not a file: {path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise UnreadableFixtureRecordError(f"Could not read fixture record file {path}: {exc}") from exc

        if not raw_text.strip():
            raise UnreadableFixtureRecordError(f"Fixture record file is empty: {path}")

        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(raw_text)
            except Exception as exc:
                raise UnreadableFixtureRecordError(f"Failed to parse YAML from {path}: {exc}") from exc
        elif path.suffix.lower() == ".json":
            try:
                data = json.loads(raw_text)
            except Exception as exc:
                raise UnreadableFixtureRecordError(f"Failed to parse JSON from {path}: {exc}") from exc
        else:
            raise UnreadableFixtureRecordError(f"Unsupported fixture record format: {path.suffix}")

        if not isinstance(data, (dict, list)):
            raise UnreadableFixtureRecordError(
                f"Parsed fixture record must be dict or list, got {type(data).__name__}"
            )
        scene_or_spec = data

    # Unpack composite dict if provided
    if isinstance(scene_or_spec, dict):
        if "_metadata" in scene_or_spec and len(scene_or_spec) == 1:
            raise UnreadableFixtureRecordError("Fixture record file contains metadata only with no fixture data")
        if "spec" in scene_or_spec and spec is None:
            spec = scene_or_spec["spec"]
        if "scene" in scene_or_spec and scene is None:
            scene = scene_or_spec["scene"]
        if "meshes" in scene_or_spec and meshes is None:
            meshes = scene_or_spec["meshes"]
        if "layout" in scene_or_spec and layout is None:
            layout = scene_or_spec["layout"]
        if "ceiling_mm" in scene_or_spec:
            ceiling_mm = float(scene_or_spec["ceiling_mm"])

        # If scene_or_spec itself is a spec dict (e.g. contains lighting list)
        if "lighting" in scene_or_spec and spec is None:
            spec = scene_or_spec
        # If scene_or_spec itself is a scene dict (e.g. contains lights list)
        if "lights" in scene_or_spec and scene is None:
            scene = scene_or_spec

    from archpipe.concept import villa_lighting as VL

    findings: list[FixtureFinding] = []

    # -------------------------------------------------------------------------
    # 1. Spec Lighting Consistency (Flux, CCT, Mounting Height, Geometry)
    # -------------------------------------------------------------------------
    if spec is not None:
        if not isinstance(spec, dict):
            raise UnreadableFixtureRecordError(f"Spec must be a dictionary, got {type(spec).__name__}")

        lighting_list = spec.get("lighting", [])
        if not isinstance(lighting_list, list):
            raise UnreadableFixtureRecordError(
                f"Spec lighting must be a list, got {type(lighting_list).__name__}"
            )

        for item in lighting_list:
            if not isinstance(item, dict):
                raise UnreadableFixtureRecordError(
                    f"Lighting entry must be a dictionary, got {type(item).__name__}"
                )
            fid = str(item.get("id", "unknown"))

            # 1.1 Luminaire Flux vs Requirement (l0123)
            req = item.get("requirement")
            prod = item.get("product")
            if req and isinstance(req, dict) and "lumens" in req:
                req_lo, req_hi = req["lumens"]
                actual_lm = None
                if isinstance(prod, dict) and "luminaire_lm" in prod:
                    actual_lm = float(prod["luminaire_lm"])
                elif "lumens" in item:
                    actual_lm = float(item["lumens"])

                if actual_lm is not None and not (req_lo <= actual_lm <= req_hi):
                    findings.append(FixtureFinding(
                        fixture_id=fid,
                        rule="photometry_flux_requirement",
                        lesson_id="l0123-swapping-4300-lm",
                        status="FAIL",
                        message=(
                            f"Luminaire flux {actual_lm:.1f} lm outside required range "
                            f"[{req_lo}, {req_hi}] lm (l0123)"
                        ),
                        declared=[req_lo, req_hi],
                        actual=actual_lm,
                    ))

            # 1.2 Hand-typed vs Product Record Clashes
            if isinstance(prod, dict) and "manufacturer" in prod and "sku" in prod:
                mfr = str(prod["manufacturer"]).lower()
                sku = str(prod["sku"])
                lamp_set = int(prod.get("lamp_set", 0))
                row = lib.get(mfr, sku, lamp_set)
                if row:
                    if "lumens" in item:
                        spec_lm = float(item["lumens"])
                        want_lm = float(row["lamp_lm"])
                        if abs(spec_lm - want_lm) > max(1.0, 0.05 * want_lm):
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="spec_lumens_product_agreement",
                                lesson_id="l0123-swapping-4300-lm",
                                status="FAIL",
                                message=(
                                    f"Spec lumens {spec_lm:.1f} lm contradicts library product "
                                    f"{want_lm:.1f} lm from {mfr}/{sku}"
                                ),
                                declared=spec_lm,
                                actual=want_lm,
                            ))
                    if "kelvin" in item:
                        spec_k = float(item["kelvin"])
                        want_k = float(row["cct_k"])
                        if abs(spec_k - want_k) > 50:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="spec_cct_product_agreement",
                                lesson_id="l0080-lamps-rendered-far",
                                status="FAIL",
                                message=(
                                    f"Spec CCT {spec_k:.0f} K contradicts library product "
                                    f"{want_k:.0f} K from {mfr}/{sku}"
                                ),
                                declared=spec_k,
                                actual=want_k,
                            ))

            # 1.3 Extracted Meshes vs Emitter Datum & Housing (l0095, l0096, l0119)
            if meshes and fid in meshes:
                fx_meshes = meshes[fid]
                if not isinstance(fx_meshes, list):
                    raise UnreadableFixtureRecordError(f"Meshes for fixture {fid} must be a list")

                src = fixture_source.source_point(fx_meshes)
                if src is None:
                    findings.append(FixtureFinding(
                        fixture_id=fid,
                        rule="emitter_geometry_measured",
                        lesson_id="l0095-lamp-sources-sat",
                        status="FAIL",
                        message=f"Fitting {fid} has no measurable Light Source symbol or luminous face geometry",
                    ))
                else:
                    sx, sy, sz, basis = src
                    mh = item.get("mounting_height")
                    if mh is not None:
                        mh_val = float(mh)
                        dz = abs(sz - mh_val)
                        if dz > 25.0:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="emitter_mounting_height_agreement",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Measured emitter height {sz:.1f} mm differs by {dz:.1f} mm "
                                    f"from spec mounting_height {mh_val:.1f} mm (tol 25.0 mm) (l0095)"
                                ),
                                declared=mh_val,
                                actual=round(sz, 1),
                            ))

                    at_pt = item.get("at")
                    if at_pt and len(at_pt) >= 2:
                        d_plan = math.hypot(sx - at_pt[0], sy - at_pt[1])
                        if d_plan > 25.0:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="emitter_plan_offset_agreement",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Measured emitter plan offset {d_plan:.1f} mm exceeds "
                                    f"tolerance 25.0 mm (l0095)"
                                ),
                                declared=at_pt,
                                actual=[round(sx, 1), round(sy, 1)],
                            ))

                # Body geometry vs Ceiling clearance (l0119, l0096)
                body_pts = [
                    p
                    for m in fx_meshes
                    if m.get("geometry_role") != "light_source_symbol"
                    for p in m.get("vertices_mm", [])
                ]
                if body_pts:
                    top_z = max(p[2] for p in body_pts)
                    mount = (
                        (item.get("product") or {}).get("mount")
                        or item.get("mount")
                        or item.get("host")
                    )
                    tol_ceiling = 5.0
                    if mount == "recessed":
                        if top_z > ceiling_mm:
                            recess_needed = top_z - ceiling_mm
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="housing_ceiling_clearance",
                                lesson_id="l0119-housing-below-ceiling",
                                status="NOTE",
                                message=(
                                    f"Recessed luminaire body top {top_z:.1f} mm requires "
                                    f"{recess_needed:.1f} mm recess depth above {ceiling_mm:.1f} mm "
                                    f"ceiling (coordination note) (l0119)"
                                ),
                                declared=ceiling_mm,
                                actual=round(top_z, 1),
                            ))
                    else:
                        if top_z > ceiling_mm + tol_ceiling:
                            findings.append(FixtureFinding(
                                fixture_id=fid,
                                rule="housing_ceiling_clearance",
                                lesson_id="l0096-two-spec-heights",
                                status="FAIL",
                                message=(
                                    f"Housing penetrates ceiling: body top {top_z:.1f} mm "
                                    f"exceeds finished ceiling {ceiling_mm:.1f} mm by "
                                    f"{top_z - ceiling_mm:.1f} mm (l0096, l0119)"
                                ),
                                declared=ceiling_mm,
                                actual=round(top_z, 1),
                            ))

    # -------------------------------------------------------------------------
    # 2. Render Scene Emitter Consistency (Flux, CCT, Position)
    # -------------------------------------------------------------------------
    if scene is not None:
        if not isinstance(scene, dict):
            raise UnreadableFixtureRecordError(f"Scene must be a dictionary, got {type(scene).__name__}")

        lights = scene.get("lights", [])
        if not isinstance(lights, list):
            raise UnreadableFixtureRecordError(f"Scene lights must be a list, got {type(lights).__name__}")

        scene_meshes = {
            m["id"]: m
            for m in scene.get("meshes", [])
            if isinstance(m, dict) and "id" in m
        }

        for L in lights:
            if not isinstance(L, dict):
                raise UnreadableFixtureRecordError(f"Light entry must be a dictionary, got {type(L).__name__}")
            lid = str(L.get("id", "unknown"))
            cct = L.get("cct_k")
            lm = L.get("lumens")
            prod = L.get("product", {})

            # Check verified product CCT and flux agreement (l0080, l0123)
            if isinstance(prod, dict) and not prod.get("generic"):
                mfr = prod.get("manufacturer")
                sku = prod.get("code")
                lamp_set = int(prod.get("lamp_set", 0))
                if mfr and sku:
                    row = lib.get(mfr, sku, lamp_set)
                    if row:
                        if cct is not None and abs(cct - row["cct_k"]) > 50:
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="render_cct_agreement",
                                lesson_id="l0080-lamps-rendered-far",
                                status="FAIL",
                                message=(
                                    f"Render emitter CCT {cct} K differs from verified product "
                                    f"CCT {row['cct_k']} K (l0080)"
                                ),
                                declared=row["cct_k"],
                                actual=cct,
                            ))
                        if lm is not None and abs(lm - row["luminaire_lm"]) > 0.05 * row["luminaire_lm"]:
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="render_flux_agreement",
                                lesson_id="l0123-swapping-4300-lm",
                                status="FAIL",
                                message=(
                                    f"Render emitter flux {lm:.1f} lm differs from verified product "
                                    f"flux {row['luminaire_lm']:.1f} lm (l0123)"
                                ),
                                declared=row["luminaire_lm"],
                                actual=lm,
                            ))

            # Check emitter position vs corresponding fixture mesh in scene
            mesh_id = "fix-" + lid
            if mesh_id in scene_meshes:
                fix_mesh = scene_meshes[mesh_id]
                faces = fix_mesh.get("faces", [])
                if faces and faces[0] and len(faces[0][0]) >= 3:
                    mesh_z = faces[0][0][2]
                    light_pos = L.get("position", [0, 0, 0])
                    if len(light_pos) >= 3:
                        dz = abs(light_pos[2] - mesh_z)
                        if dz > 0.10:  # 100 mm offset threshold
                            findings.append(FixtureFinding(
                                fixture_id=lid,
                                rule="emitter_mesh_offset",
                                lesson_id="l0095-lamp-sources-sat",
                                status="FAIL",
                                message=(
                                    f"Render emitter at z={light_pos[2]:.3f} sits {dz*1000:.0f} mm "
                                    f"from housing trim at z={mesh_z:.3f} (l0095)"
                                ),
                                declared=mesh_z,
                                actual=light_pos[2],
                            ))

    # -------------------------------------------------------------------------
    # 3. Room Containment and Fitting Labeling (l0610)
    # -------------------------------------------------------------------------
    fixtures_for_rooms: list[Any] = []
    if isinstance(scene_or_spec, list):
        fixtures_for_rooms = scene_or_spec
    elif isinstance(spec, dict) and "fixtures" in spec:
        fixtures_for_rooms = spec["fixtures"]
    elif layout and "fixtures" in layout:
        fixtures_for_rooms = layout["fixtures"]

    target_layout = layout
    if target_layout is None and isinstance(scene_or_spec, dict) and "rooms" in scene_or_spec:
        target_layout = scene_or_spec

    if fixtures_for_rooms and target_layout is not None:
        if not isinstance(target_layout, dict):
            raise UnreadableFixtureRecordError(
                f"Target layout must be a dictionary, got {type(target_layout).__name__}"
            )
        rooms_dict = target_layout.get("rooms", {})

        for fx in fixtures_for_rooms:
            fx_id = getattr(fx, "id", None) or (fx.get("id", "unknown") if isinstance(fx, dict) else "unknown")
            fx_room = getattr(fx, "room", None) or (fx.get("room") if isinstance(fx, dict) else None)
            if hasattr(fx, "x") and hasattr(fx, "y"):
                fx_x, fx_y = fx.x, fx.y
            elif isinstance(fx, dict):
                fx_x = fx.get("x") if "x" in fx else (fx.get("at", [None])[0] if "at" in fx else None)
                fx_y = fx.get("y") if "y" in fx else (fx.get("at", [None, None])[1] if "at" in fx else None)
            else:
                fx_x, fx_y = None, None

            if fx_room and fx_x is not None and fx_y is not None and fx_room in rooms_dict:
                rc_x0, rc_y0, rc_x1, rc_y1 = F.clear_rect(target_layout, fx_room)
                tol = 1e-4
                if not (rc_x0 - tol <= fx_x <= rc_x1 + tol and rc_y0 - tol <= fx_y <= rc_y1 + tol):
                    # Outside assigned room clear rect: measure distance and check cluster neighbours
                    dx = max(0.0, rc_x0 - fx_x, fx_x - rc_x1)
                    dy = max(0.0, rc_y0 - fx_y, fx_y - rc_y1)
                    dist_outside_mm = math.hypot(dx, dy) * 1000.0
                    dist_str = (
                        f"{dist_outside_mm:.0f} mm"
                        if abs(dist_outside_mm - round(dist_outside_mm)) < 0.05
                        else f"{dist_outside_mm:.1f} mm"
                    )

                    contained_in = None
                    for other in F._cluster(target_layout, fx_room):
                        if other != fx_room and other in rooms_dict:
                            qx0, qy0, qx1, qy1 = F.clear_rect(target_layout, other)
                            if qx0 - tol <= fx_x <= qx1 + tol and qy0 - tol <= fx_y <= qy1 + tol:
                                contained_in = other
                                break

                    findings.append(FixtureFinding(
                        fixture_id=str(fx_id),
                        rule="fitting_room_containment",
                        lesson_id="l0610-fitting-labelled-wrong",
                        status="FAIL",
                        message=(
                            f"Fitting {fx_id} labelled with room '{fx_room}' at ({fx_x:.3f}, {fx_y:.3f}) "
                            f"sits {dist_str} outside {fx_room} clear rect"
                            + (f" and inside '{contained_in}'" if contained_in else "")
                            + " (l0610)"
                        ),
                        declared=fx_room,
                        actual=contained_in or "outside",
                    ))

    # If no findings were added, record baseline pass
    if not findings:
        findings.append(FixtureFinding(
            fixture_id="all",
            rule="fixture_record_consistency",
            lesson_id="clean",
            status="PASS",
            message="All checked fixture records are consistent with physical and photometric contracts",
        ))

    return findings


def check_fixture_record_consistency(target: Any = None, **kwargs) -> list[FixtureFinding]:
    """Guard registry adapter: runs fixture_findings and fails closed on FAIL findings.

    Args:
        target: File path, specification dict, scene dict, or composite payload.
        **kwargs: Optional spec, scene, meshes, layout, ceiling_mm parameters.

    Returns:
        List of FixtureFinding records if all pass or only generate notes.

    Raises:
        UnreadableFixtureRecordError: If target cannot be found, read, or parsed.
        FixtureConsistencyError: If any consistency check generates a FAIL finding.
    """
    findings = fixture_findings(target, **kwargs)
    fails = [f for f in findings if f.status == "FAIL"]
    if fails:
        msg = "; ".join(f"{f.fixture_id} [{f.lesson_id}]: {f.message}" for f in fails)
        raise FixtureConsistencyError(
            f"Fixture consistency guard failed ({len(fails)} issues): {msg}"
        )
    return findings


def vanity_scene_findings(scene, records):
    """Check corrected pair emitters independently from final mesh bounds.

    records are immutable FixtureRecords. A 1 micrometre arithmetic tolerance
    only absorbs floating point translations; it is not a design allowance.
    The correction marker identifies a construction rule, never room names.
    """
    meshes = {m['id']:m for m in scene['meshes']}
    findings = []
    for record in records:
        extra = dict(record.extra)
        if not (extra.get('vanity_pair_source_correction') or extra.get('over_mirror')):
            continue
        mesh = meshes.get('lamp-'+record.id)
        if mesh is None:
            findings.append(record.id+': missing built vanity emitter')
            continue
        points = [p for face in mesh['faces'] for p in face]
        centre = [(min(p[i] for p in points)+max(p[i] for p in points))/2 for i in range(3)]
        error = math.dist(centre,record.position)*1000
        if error > .001:
            findings.append(record.id+f': built emitter differs from record by {error:.3f} mm')
        if extra.get('over_mirror'):
            from archpipe.concept.fitting_mounting import bounds
            mirror = meshes.get(extra['mirror_id'])
            body = meshes.get('body-'+record.id)
            if mirror is None or body is None:
                findings.append(record.id+': missing mirror or complete fitting body')
                continue
            mb, bb = bounds(mirror), bounds(body)
            rect = extra['room_rect']
            issues = vanity_pair_findings([(bb[1]+bb[4])/2], (rect[1],rect[3]),
                (mb[1]+mb[4])/2, (mb[1],mb[4]), (bb[4]-bb[1])/2, 0,
                record.housing['edge_margin'], over_mirror=((bb[2]+bb[5])/2,mb[5],(bb[5]-bb[2])/2))
            if bb[0] < rect[0]+record.housing['edge_margin']-1e-6 or bb[3] > rect[2]-record.housing['edge_margin']+1e-6:
                issues.append('vanity_single_depth: fitting exceeds room clear boundary')
            if abs((bb[2]+bb[5])/2-mb[5]-record.housing['centre_above_mirror']) > 1e-6:
                issues.append('vanity_single_height: centre differs from authored mirror-top offset')
            fixing = bb[0] if record.aim[0] > 0 else bb[3]
            if abs(fixing-extra['finished_wall']) > 1e-6:
                issues.append('vanity_single_mount: body fixing face differs from finished wall')
            if any(abs((bb[i]+bb[i+3])/2-record.position[i]) > 1e-6 for i in (1,2)):
                issues.append('vanity_single_emitter: body and emitter axes disagree')
            expected = (2*record.housing['half_depth'],record.housing['length'],2*record.housing['half_height'])
            if any(abs(bb[i+3]-bb[i]-expected[i]) > 1e-6 for i in range(3)):
                issues.append('vanity_single_envelope: complete body differs from recorded dimensions')
            if bb[5] > extra['ceiling_z']-record.housing['edge_margin']+1e-6:
                issues.append('vanity_single_ceiling: fitting exceeds room height allowance')
            findings.extend(record.id+': '+issue for issue in issues)
    return findings
