"""Pre-registered moving-image screens, using developed byte RGB images.

RGB means red, green and blue. Density and flicker count pixels per 10,000
interior pixels. These are assumed acceptance screens, not design standards.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]


def speckle_policy():
    return json.loads((ROOT/'knowledge/walk2-speckle-policy.json').read_text())


def isolated_mask(rgb):
    """Return interior mask; omit the one-pixel border from all counts."""
    values = np.asarray(rgb)
    if values.ndim != 3 or values.shape[2] != 3 or values.dtype != np.uint8:
        raise ValueError('An unsigned byte RGB image is required')
    if min(values.shape[:2]) < 3:
        raise ValueError('Image must contain an interior')
    gray = Image.fromarray(values).convert('L')
    median = np.asarray(gray.filter(ImageFilter.MedianFilter(3)), dtype=np.int16)
    return (np.abs(np.asarray(gray, dtype=np.int16)-median) > 35)[1:-1, 1:-1]


def speckle_frame(rgb, previous_mask=None, settings=None):
    settings = settings or speckle_policy()
    mask = isolated_mask(rgb)
    density = float(mask.mean()*10000)
    flicker = None
    if previous_mask is not None:
        if previous_mask.shape != mask.shape:
            raise ValueError('Adjacent image dimensions differ')
        flicker = float(np.logical_xor(mask, previous_mask).mean()*10000)
    return dict(density_per_10000=density, flicker_per_10000=flicker,
                isolated_pixels=int(mask.sum()), interior_pixels=mask.size,
                passed=(density <= settings['maximum_density_per_10000'] and
                        (flicker is None or flicker <= settings['maximum_flicker_per_10000']))), mask


def encoding_error(original, decoded, settings=None):
    """Lead's pixel-error screen: any RGB channel differs by over 40 bytes."""
    settings = settings or speckle_policy()['encoding']
    a, b = np.asarray(original), np.asarray(decoded)
    if a.shape != b.shape or a.dtype != np.uint8 or b.dtype != np.uint8:
        raise ValueError('Matching unsigned byte RGB images required')
    difference = np.abs(a.astype(np.int16)-b.astype(np.int16))
    fraction = float((difference.max(axis=2) > settings['channel_difference_threshold']).mean())
    return dict(fraction_pixels_over_threshold=fraction,
                mean_absolute_rgb_error=float(difference.mean()/255),
                passed=fraction <= settings['maximum_fraction_pixels_any_channel_exceeds'])
