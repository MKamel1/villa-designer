"""Mean relative luminance (linear, Rec.709 weights, 0-1) of render PNGs: python scripts/mean_luminance.py a.png b.png ..."""
import sys

import numpy as np
from PIL import Image


def mean_luminance(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return float((lin @ np.array([0.2126, 0.7152, 0.0722])).mean())


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(f"{mean_luminance(p):.4f}  {p}")
