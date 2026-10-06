"""Single typed boundary for unit and coordinate frame conversions.

All physical unit constants, conversion arithmetic, and coordinate frame
transformations go through this boundary.

Definitions & Authority:
- 1 foot = 0.3048 m exactly, per the International Yard and Pound Agreement
  of 1959 (effective 1 July 1959, codified in NIST Special Publication 811).
- 1 inch = 25.4 mm exactly (1/12 foot = 0.0254 m).
- 1 metre = 1000 mm exactly (SI base unit).
- 1 kilowatt-hour = 3,600,000 Joules exactly (1000 W * 3600 s).
- glTF to Scene frame: glTF uses right-handed Y-up (x, y, z). The scene/Blender
  coordinate frame uses right-handed Z-up (x, -z, y), matching the established
  convention in src/archpipe/concept/villa_landscape.py:78-80.

Quick Test:
    python -c "from archpipe.units import ft_to_mm, gltf_yup_to_scene_zup; assert ft_to_mm(1.0) == 304.8; assert gltf_yup_to_scene_zup(1, 2, 3) == (1.0, -3.0, 2.0)"

Example Usage:
    >>> from archpipe.units import ft_to_mm, mm_to_ft, gltf_yup_to_scene_zup
    >>> ft_to_mm(1.0)
    304.8
    >>> mm_to_ft(304.8)
    1.0
    >>> gltf_yup_to_scene_zup(1.0, 2.0, 3.0)
    (1.0, -3.0, 2.0)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple

# -----------------------------------------------------------------------------
# Exact Physical Constants (NIST SP 811 / International Agreement 1959)
# -----------------------------------------------------------------------------

M_PER_FOOT: float = 0.3048
MM_PER_FOOT: float = 304.8
FEET_PER_M: float = 1.0 / 0.3048
FEET_PER_MM: float = 1.0 / 304.8

MM_PER_M: float = 1000.0
M_PER_MM: float = 0.001

MM_PER_INCH: float = 25.4
INCHES_PER_MM: float = 1.0 / 25.4

JOULES_PER_KWH: float = 3_600_000.0
KWH_PER_JOULE: float = 1.0 / 3_600_000.0


# -----------------------------------------------------------------------------
# Length Conversions
# -----------------------------------------------------------------------------

def mm_to_ft(val: float) -> float:
    """Convert millimetres to decimal feet."""
    return float(val) / MM_PER_FOOT


def ft_to_mm(val: float) -> float:
    """Convert decimal feet to millimetres."""
    return float(val) * MM_PER_FOOT


def m_to_mm(val: float) -> float:
    """Convert metres to millimetres."""
    return float(val) * MM_PER_M


def mm_to_m(val: float) -> float:
    """Convert millimetres to metres."""
    return float(val) / MM_PER_M


def m_to_ft(val: float) -> float:
    """Convert metres to decimal feet."""
    return float(val) / M_PER_FOOT


def ft_to_m(val: float) -> float:
    """Convert decimal feet to metres."""
    return float(val) * M_PER_FOOT


def in_to_mm(val: float) -> float:
    """Convert inches to millimetres."""
    return float(val) * MM_PER_INCH


def mm_to_in(val: float) -> float:
    """Convert millimetres to inches."""
    return float(val) / MM_PER_INCH


# -----------------------------------------------------------------------------
# Energy Conversions (EnergyPlus Joules <-> Ladybug kWh)
# -----------------------------------------------------------------------------

def joules_to_kwh(val: float) -> float:
    """Convert energy from Joules to kilowatt-hours (kWh).

    Exact factor: 1 kWh = 3,600,000 J (1000 W * 3600 s).
    Used to prevent the 3.6 million scaling error (l0182).
    """
    return float(val) / JOULES_PER_KWH


def kwh_to_joules(val: float) -> float:
    """Convert energy from kilowatt-hours (kWh) to Joules.

    Exact factor: 1 kWh = 3,600,000 J.
    """
    return float(val) * JOULES_PER_KWH


# -----------------------------------------------------------------------------
# Datetime UTC Validation (Solar Position Contract)
# -----------------------------------------------------------------------------

def require_utc(dt: datetime) -> datetime:
    """Enforce that a datetime is explicitly timezone-aware and set to UTC (offset 0).

    Prevents timezone misinterpretation where local time with tzinfo is treated
    as UTC hours, causing severe solar altitude/azimuth calculation errors (l0473).

    Raises:
        ValueError: If dt is naive (no tzinfo or utcoffset is None) or if dt's UTC
            offset is not exactly zero.

    Returns:
        The validated datetime unchanged.
    """
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(
            "Datetime must be timezone-aware UTC (offset 0), but got naive datetime"
        )
    offset = dt.utcoffset()
    if offset.total_seconds() != 0:
        raise ValueError(
            f"Datetime must have UTC timezone (offset 0), but got offset {offset} "
            f"({offset.total_seconds()} seconds)"
        )
    return dt


# -----------------------------------------------------------------------------
# Coordinate Frame Transformations
# -----------------------------------------------------------------------------

def gltf_yup_to_scene_zup(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Transform right-handed Y-up glTF coordinate (x, y, z) to right-handed Z-up scene (x, -z, y).

    Blender's glTF importer converts native Y-up (x, y, z) to scene Z-up (x, -z, y).
    Matches the existing codebase convention verified in
    src/archpipe/concept/villa_landscape.py:78-80.

    Args:
        x: Native glTF x coordinate (width).
        y: Native glTF y coordinate (vertical height).
        z: Native glTF z coordinate (depth).

    Returns:
        Tuple (scene_x, scene_y, scene_z) where:
            scene_x = x
            scene_y = -z
            scene_z = y
    """
    return (float(x), -float(z), float(y))
