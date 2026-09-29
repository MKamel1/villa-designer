"""Deterministic Bougainvillea placement inside a measured vertical envelope.

`box` is (minimum x, minimum y, minimum z, maximum x, maximum y, maximum z)
in metres. Density counts visible foliage and bracts per square metre of the
largest vertical face. The 70 percent foliage share is an ASSUMED render detail.
"""
from __future__ import annotations

import math
import random


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
