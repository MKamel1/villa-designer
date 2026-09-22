"""IES photometric files: read real luminaire data instead of inventing it.

A lighting scheme is only as honest as its photometry. Average-lumens
arithmetic ("a 3000 lm fixture in a 15 m2 room gives 200 lx") ignores where
the light actually goes, which is the entire question a heat map is asked to
answer. This module reads the measured candela distribution so `lighting.py`
can compute point-by-point illuminance.

The format is **IESNA LM-63** (the Illuminating Engineering Society's
photometric data standard; revisions LM-63-1986/91/95/2002 differ only in
the header). Revit ships 141 of these files with the base install, at
`C:\\ProgramData\\Autodesk\\RVT 2025\\IES` -- they need no content library
download, which is why the lighting work can start before families arrive.

File layout, after the keyword block and the TILT line:

    <lamps> <lumens/lamp> <multiplier> <n_vert> <n_horiz> <photo_type>
        <units_type> <width> <length> <height>
    <ballast_factor> <future_use> <input_watts>
    <vertical angles ...>       n_vert values
    <horizontal angles ...>     n_horiz values
    <candela ...>               n_vert * n_horiz values

TWO TRAPS, both of which produce plausible-looking wrong numbers rather
than an error:

1. **Values are whitespace-delimited across line breaks, not one row per
   line.** A parser that reads the candela block line-by-line and assumes
   each line is one horizontal plane will silently mis-shape the grid.
   Everything after the TILT line is therefore tokenised as one stream.

2. **Lumens/lamp of -1 means absolute photometry.** The candela values are
   then already absolute and must NOT be scaled by lamp lumens. Treating
   -1 as a lumen count yields negative light.

Angles are in degrees. Vertical angle is measured from **nadir** (0 =
straight down) for the Type C photometry used by virtually all interior
luminaires. Candela values are cd; distances in this module are metres.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

# LM-63 units_type field. Luminous opening dimensions -- not the grid.
UNITS_FEET = 1
UNITS_METRES = 2

FEET_TO_M = 0.3048

# LM-63 photometric_type field.
PHOTO_TYPE_C = 1        # the interior-luminaire convention
PHOTO_TYPE_B = 2
PHOTO_TYPE_A = 3


class IESError(ValueError):
    """An IES file we could not read, with a reason worth reading."""


@dataclass(frozen=True)
class Photometry:
    """A parsed luminaire photometric distribution.

    `candela[i][j]` is the intensity at vertical angle `vertical[i]` and
    horizontal angle `horizontal[j]`, already multiplied by the file's
    candela multiplier and ballast factor so callers need no further
    scaling.
    """

    name: str
    lamps: int
    lumens_per_lamp: float          # -1.0 for absolute photometry
    input_watts: float
    vertical: tuple[float, ...]
    horizontal: tuple[float, ...]
    candela: tuple[tuple[float, ...], ...]
    photometric_type: int
    units_type: int
    width: float                    # luminous opening, in units_type
    length: float
    height: float
    source: Path | None = None

    # ----------------------------------------------------------------- facts

    @property
    def absolute(self) -> bool:
        """True when candela values are absolute rather than per-lamp-lumen.

        LM-63 signals this with lumens/lamp of -1. It matters because an
        absolute file must not be rescaled.
        """
        return self.lumens_per_lamp < 0

    @property
    def total_lumens(self) -> float:
        """Rated lamp output. 0.0 for absolute photometry, where the file
        does not state it -- callers must not treat that as darkness."""
        if self.absolute:
            return 0.0
        return self.lamps * self.lumens_per_lamp

    @property
    def peak_candela(self) -> float:
        return max(max(row) for row in self.candela)

    @property
    def efficacy(self) -> float | None:
        """Lumens per watt, or None when the file omits either figure.

        Useful as a sanity check on a fixture choice: an LED downlight
        below about 60 lm/W in 2026 is a poor specification, and a
        fluorescent troffer around 60-90 lm/W is period-typical.
        """
        if self.input_watts <= 0 or self.total_lumens <= 0:
            return None
        return self.total_lumens / self.input_watts

    def luminous_dimensions_m(self) -> tuple[float, float, float]:
        """Luminous opening as (width, length, height) in metres.

        The file gives these in feet or metres depending on `units_type`;
        this is the single place that conversion happens.
        """
        k = FEET_TO_M if self.units_type == UNITS_FEET else 1.0
        return (self.width * k, self.length * k, self.height * k)

    # ------------------------------------------------------------ the physics

    def intensity(self, vertical_deg: float, horizontal_deg: float = 0.0) -> float:
        """Candela in a given direction, bilinearly interpolated.

        `vertical_deg` is measured from nadir (0 = straight down).
        Directions outside the measured range return 0.0 -- a luminaire
        reports no data above its last measured angle because it emits
        nothing there.
        """
        v = float(vertical_deg)
        if v < self.vertical[0] or v > self.vertical[-1]:
            return 0.0

        h = self._fold_horizontal(horizontal_deg)
        i, fi = _bracket(self.vertical, v)
        j, fj = _bracket(self.horizontal, h)

        c = self.candela
        i2 = min(i + 1, len(self.vertical) - 1)
        j2 = min(j + 1, len(self.horizontal) - 1)

        lower = c[i][j] * (1 - fj) + c[i][j2] * fj
        upper = c[i2][j] * (1 - fj) + c[i2][j2] * fj
        return lower * (1 - fi) + upper * fi

    def _fold_horizontal(self, h: float) -> float:
        """Map an arbitrary azimuth into the measured range using LM-63's
        symmetry conventions.

        A file measures only as much as the luminaire's symmetry requires,
        and the convention is carried by the *range* of horizontal angles
        rather than by any flag:

            single angle  -> axially symmetric, one plane describes all
            0 .. 90       -> symmetric in four quadrants
            0 .. 180      -> symmetric about the 0-180 plane
            0 .. 360      -> no symmetry

        Reading a quadrant-symmetric file as if it were fully measured
        would leave three quarters of the room dark, which looks like a
        lighting fault rather than a parsing one.
        """
        lo, hi = self.horizontal[0], self.horizontal[-1]
        if len(self.horizontal) == 1:
            return lo

        h = math.fmod(float(h), 360.0)
        if h < 0:
            h += 360.0

        if hi <= 90.0 + 1e-6:
            # Fold into the first quadrant.
            h = math.fmod(h, 180.0)
            if h > 90.0:
                h = 180.0 - h
            return h
        if hi <= 180.0 + 1e-6:
            return 360.0 - h if h > 180.0 else h
        return h

    def illuminance_at(self, dx: float, dy: float, mounting_height: float,
                       *, aim: float = 0.0) -> float:
        """Illuminance in lux on a horizontal plane below the luminaire.

        `dx`, `dy` are metres from the point directly beneath the fixture;
        `mounting_height` is metres from the luminaire to the working
        plane. `aim` rotates the distribution about the vertical axis, in
        degrees, for an asymmetric fixture.

        The inverse-square cosine law for a point source:

            E = I(theta, phi) * cos(incidence) / d^2

        and for a horizontal plane the incidence cosine is h/d, giving

            E = I * h / d^3

        POINT-SOURCE ASSUMPTION. This is accurate when the distance is
        large relative to the luminaire -- the usual rule is at least five
        times its largest luminous dimension. Close to a long linear
        fitting it overestimates the peak directly beneath. `lighting.py`
        is responsible for reporting when a grid violates that; silently
        returning a confident number would be the worse failure.
        """
        if mounting_height <= 0:
            raise ValueError("mounting_height must be positive: the luminaire "
                             "has to be above the plane it lights")

        r = math.hypot(dx, dy)
        d = math.hypot(r, mounting_height)
        theta = math.degrees(math.atan2(r, mounting_height))
        phi = math.degrees(math.atan2(dy, dx)) - aim

        return self.intensity(theta, phi) * mounting_height / (d ** 3)


def _bracket(values: tuple[float, ...], x: float) -> tuple[int, float]:
    """Index of the sample at or below `x`, and the fraction beyond it."""
    n = len(values)
    if n == 1 or x <= values[0]:
        return 0, 0.0
    if x >= values[-1]:
        return n - 1, 0.0
    lo = 0
    hi = n - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if values[mid] <= x:
            lo = mid
        else:
            hi = mid
    span = values[hi] - values[lo]
    return lo, 0.0 if span <= 0 else (x - values[lo]) / span


# --------------------------------------------------------------------- parsing

def parse(text: str, *, name: str = "", source: Path | None = None) -> Photometry:
    """Parse IES (LM-63) text into a `Photometry`.

    Raises `IESError` with a specific reason rather than returning
    something half-built -- a partly-parsed luminaire would produce a heat
    map that looks fine and is wrong.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # The keyword block runs until TILT=, which is mandatory in every
    # revision of the format and is the only reliable separator.
    tilt_at = None
    keywords: dict[str, str] = {}
    for n, line in enumerate(lines):
        s = line.strip()
        if s.upper().startswith("TILT"):
            tilt_at = n
            break
        if s.startswith("[") and "]" in s:
            key, _, value = s[1:].partition("]")
            keywords[key.strip().upper()] = value.strip()
    if tilt_at is None:
        raise IESError("no TILT= line: this is not an IES file, or it is "
                       "truncated before the photometric data begins")

    tilt = lines[tilt_at].split("=", 1)[1].strip().upper() if "=" in lines[tilt_at] else "NONE"

    rest = lines[tilt_at + 1:]
    if tilt == "INCLUDE":
        # An embedded tilt table: 1 value (orientation), 1 count, then
        # count angle/factor pairs. Skipping it by a fixed line count
        # would be wrong for the same reason as the candela block, so
        # tokenise and drop the right number of NUMBERS.
        toks = _tokens(rest)
        if len(toks) < 2:
            raise IESError("TILT=INCLUDE but the tilt table is missing")
        count = int(float(toks[1]))
        rest_tokens = toks[2 + 2 * count:]
    else:
        rest_tokens = _tokens(rest)

    if len(rest_tokens) < 13:
        raise IESError(f"only {len(rest_tokens)} numbers after TILT: the two "
                       f"parameter rows need 13 before any angles")

    try:
        lamps = int(float(rest_tokens[0]))
        lumens_per_lamp = float(rest_tokens[1])
        multiplier = float(rest_tokens[2])
        n_vert = int(float(rest_tokens[3]))
        n_horiz = int(float(rest_tokens[4]))
        photo_type = int(float(rest_tokens[5]))
        units_type = int(float(rest_tokens[6]))
        width, length, height = (float(v) for v in rest_tokens[7:10])
        ballast = float(rest_tokens[10])
        # rest_tokens[11] is reserved/future-use in every revision.
        watts = float(rest_tokens[12])
    except (ValueError, IndexError) as e:
        raise IESError(f"malformed parameter rows: {e}") from e

    if n_vert <= 0 or n_horiz <= 0:
        raise IESError(f"angle counts must be positive, got "
                       f"{n_vert} vertical x {n_horiz} horizontal")

    at = 13
    vertical = tuple(float(v) for v in rest_tokens[at:at + n_vert])
    at += n_vert
    horizontal = tuple(float(v) for v in rest_tokens[at:at + n_horiz])
    at += n_horiz
    flat = rest_tokens[at:at + n_vert * n_horiz]

    if len(vertical) != n_vert or len(horizontal) != n_horiz:
        raise IESError(f"file declares {n_vert}x{n_horiz} angles but supplies "
                       f"{len(vertical)}x{len(horizontal)}")
    if len(flat) != n_vert * n_horiz:
        raise IESError(f"file declares {n_vert}x{n_horiz} = "
                       f"{n_vert * n_horiz} candela values but supplies "
                       f"{len(flat)}")

    # Angles must ascend for the interpolator's bisection to mean anything.
    for label, arr in (("vertical", vertical), ("horizontal", horizontal)):
        if any(b < a for a, b in zip(arr, arr[1:])):
            raise IESError(f"{label} angles are not in ascending order")

    # Fold the multiplier and ballast factor in here, once, so no caller
    # can forget them. An unscaled file reads as the right shape at the
    # wrong brightness -- the hardest kind of error to notice.
    scale = multiplier * (ballast if ballast > 0 else 1.0)

    # Stored vertical-major: candela[i][j] = vertical i, horizontal j. The
    # file writes it horizontal-plane-major, so this transposes.
    grid = tuple(
        tuple(float(flat[j * n_vert + i]) * scale for j in range(n_horiz))
        for i in range(n_vert)
    )

    return Photometry(
        name=name or keywords.get("LUMINAIRE", "") or keywords.get("LUMCAT", "")
        or (source.stem if source else "unnamed"),
        lamps=lamps, lumens_per_lamp=lumens_per_lamp, input_watts=watts,
        vertical=vertical, horizontal=horizontal, candela=grid,
        photometric_type=photo_type, units_type=units_type,
        width=width, length=length, height=height, source=source,
    )


def _tokens(lines: list[str]) -> list[str]:
    """Whitespace-delimited numbers across line breaks.

    Commas appear in the wild despite not being in the specification, so
    they are treated as delimiters too.
    """
    out: list[str] = []
    for line in lines:
        out.extend(line.replace(",", " ").split())
    return out


def load(path: str | Path) -> Photometry:
    p = Path(path)
    # Latin-1 never fails, and IES files carry manufacturer names in
    # assorted 8-bit encodings. Mojibake in a keyword is harmless; a
    # UnicodeDecodeError that rejects a valid luminaire is not.
    return parse(p.read_text(encoding="latin-1"), source=p)


def load_directory(directory: str | Path) -> tuple[list[Photometry], list[tuple[Path, str]]]:
    """Load every .ies under `directory`, returning (parsed, failures).

    Failures are returned rather than raised so a bad file in a
    manufacturer bundle does not hide the 140 good ones.
    """
    good: list[Photometry] = []
    bad: list[tuple[Path, str]] = []
    for p in sorted(Path(directory).rglob("*.ies")):
        try:
            good.append(load(p))
        except (IESError, OSError) as e:
            bad.append((p, str(e)))
    return good, bad


# Where Revit keeps the photometry it ships. Checked in order; the first
# that exists wins, so a 2025-only machine and a two-version machine both
# work without configuration.
REVIT_IES_DIRS = (
    Path(r"C:\ProgramData\Autodesk\RVT 2025\IES"),
    Path(r"C:\ProgramData\Autodesk\RVT 2026\IES"),
)


def revit_ies_dir() -> Path | None:
    """The installed Revit IES folder, or None.

    Note that IES files are plain text and version-independent -- unlike
    `.rfa` families, which are forward-compatible only (ADR-0008). So the
    2026 folder is usable here even with a 2025-only entitlement.
    """
    for d in REVIT_IES_DIRS:
        if d.is_dir():
            return d
    return None
