"""The shared analysis grid. Every LDS layer uses exactly this grid.

Frame: model metres (the villa scene frame; z = 0 is the ground-floor FFL, the garden floor is -3.0).
Client naming: street side = NORTH = model -x; east = +y; south = +x; west = -y (the sister plot).
Row j runs along model y, column i along model x; cell (i, j) has its centre at
    x = ORIGIN_X + (i + .5) * CELL,  y = ORIGIN_Y + (j + .5) * CELL.
"""
import numpy as np

ORIGIN_X, ORIGIN_Y = -0.5, -30.0
CELL = 0.25
NX, NY = 117, 40            # x -0.5 .. 28.75, y -30.0 .. -20.0 (plot is x -0.373..28.557, y ..-20.351)

HEADER = {"frame": "model metres (villa scene frame, z=0 = GF FFL)", "origin_m": [ORIGIN_X, ORIGIN_Y],
          "cell_m": CELL, "nx": NX, "ny": NY,
          "indexing": "rows[j][i]: j along model y from ORIGIN_Y, i along model x from ORIGIN_X",
          "client_naming": "north (street) = model -x; east = +y; south = +x; west (sister plot) = -y"}


def centres():
    """(X, Y) arrays of shape (NY, NX) with the cell-centre coordinates."""
    xs = ORIGIN_X + (np.arange(NX) + .5) * CELL
    ys = ORIGIN_Y + (np.arange(NY) + .5) * CELL
    return np.meshgrid(xs, ys)


def rect_mask(x0, y0, x1, y1):
    X, Y = centres()
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


def to_rows(a, ndigits=3):
    """numpy (NY, NX) -> nested list; NaN -> None (not analysed)."""
    a = np.asarray(a, float)
    return [[None if np.isnan(v) else round(float(v), ndigits) for v in row] for row in a]


def from_rows(rows):
    return np.array([[np.nan if v is None else v for v in row] for row in rows], float)
