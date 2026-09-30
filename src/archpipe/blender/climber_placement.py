"""Deterministic Bougainvillea placement inside a measured vertical envelope.

`box` is (minimum x, minimum y, minimum z, maximum x, maximum y, maximum z)
in metres. Density counts visible foliage and bracts per square metre of the
largest vertical face. The 70 percent foliage share is an ASSUMED render detail.

Client round-3 defect (v01/v02/v24 etc.): the trellis climbers read as
"almost invisible: too sparse/small" at the previous density=120. SIZE below
gives each instance's HALF-extent in metres (so a "leaf" spans ~2*0.032 =
6.4 cm, inside the requested 5-8 cm; a "bract" spans ~3.6 cm, inside 3-4 cm).
`placements` renders each instance as a rhombus (two half-diagonals SIZE[kind]),
so one instance's area is 2 * half * half. For independently, uniformly
scattered instances the probability a given point on the face is covered by
at least one instance is 1 - exp(-density * mean_instance_area) (a 2D Poisson
coverage model); `coverage_estimate` computes that, and `density_for_coverage`
inverts it (with a safety margin, since edge-clipped instances near the
envelope boundary cover less than their nominal area) to find the density
needed for a stated coverage fraction. villa_scene.build_climbers calls
`density_for_coverage()` instead of hardcoding a count, so raising the
coverage target here raises the render automatically.
"""
from __future__ import annotations

import math
import random

# Half-extent (metres) of one leaf/bract instance, shared with
# archpipe.blender.villa_scene.build_climbers so the coverage estimate below
# describes exactly what gets rendered, not a guess.
SIZE = {"leaf": 0.032, "bract": 0.018}
LEAF_FRACTION = 0.70


def _instance_area(kind):
    half = SIZE[kind]
    return 2 * half * half     # rhombus, half-diagonals (half, half)


def mean_instance_area(leaf_fraction=LEAF_FRACTION):
    return leaf_fraction * _instance_area("leaf") + (1 - leaf_fraction) * _instance_area("bract")


def coverage_estimate(density, leaf_fraction=LEAF_FRACTION):
    """Fraction of the face expected to be covered by at least one instance
    (2D Poisson coverage model; see module docstring)."""
    return 1 - math.exp(-density * mean_instance_area(leaf_fraction))


def density_for_coverage(target=0.80, leaf_fraction=LEAF_FRACTION, safety=1.25):
    """Instances per square metre needed for >= `target` coverage, with a
    safety margin for instances the envelope boundary clips (a leaf half off
    the edge of a shallow trellis mass covers less than its nominal area)."""
    if not 0 < target < 1:
        raise ValueError("target coverage must be between 0 and 1")
    raw = -math.log(1 - target) / mean_instance_area(leaf_fraction)
    return raw * safety


def placements(box, density=120, seed=7):
    x0, y0, z0, x1, y1, z1 = box
    if not (x0 < x1 and y0 < y1 and z0 < z1 and density > 0):
        raise ValueError("positive envelope and density required")
    area = max(x1-x0, y1-y0) * (z1-z0)
    count = max(1, math.ceil(area * density))
    rng = random.Random(seed)
    result = []
    for index in range(count):
        # Stratify height and alternate the two faces to cover the whole trellis.
        z = z0 + (index + rng.random()) / count * (z1-z0)
        result.append((x0 + rng.random()*(x1-x0), y0 + rng.random()*(y1-y0), z,
                       "leaf" if index % 10 < 7 else "bract"))
    rng.shuffle(result)
    return result
