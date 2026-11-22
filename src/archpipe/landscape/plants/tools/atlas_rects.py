"""Cut-out rectangles of an atlas's Opacity map (4-connected components on a 4x-downsampled mask; no scipy).
    python -I atlas_rects.py OUT.json   ->  {name: {"scan_m", "rects": [[x0,y0,x1,y1] in 4096-px, area_px]}}
Rects are in atlas pixels (origin top-left). Components under min_px are dropped (stems, specks)."""
import json, os, sys
from collections import deque
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
FAB = "/home/omar/archpipe/shared/assets/user/landscape/fab/unzipped/"
SRC = {"star_jasmine": ("star_jasmine_pjycl2_4k/Star_Jasmine_pjycl2_4K", 0.79, 400),
       "bougainvillea_flower": ("bougainvillea_flower_phfeffeh2_4k/Bougainvillea_Flower_phfeffeh2_4K", 0.25, 150)}


def components(mask, min_px):
    h, w = mask.shape; seen = np.zeros_like(mask); out = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]: continue
        q = deque([(y, x)]); seen[y, x] = True; ys = [y]; xs = [x]
        while q:
            cy, cx = q.popleft()
            for ny, nx in ((cy+1, cx), (cy-1, cx), (cy, cx+1), (cy, cx-1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx)); ys.append(ny); xs.append(nx)
        if len(ys) >= min_px:
            out.append([int(min(xs))*4, int(min(ys))*4, (int(max(xs))+1)*4, (int(max(ys))+1)*4, len(ys)*16])
    return out


if __name__ == "__main__":
    res = {}
    for k, (p, scan, mn) in SRC.items():
        o = np.asarray(Image.open(FAB + p + "_Opacity.jpg"))[..., 0]
        m = np.asarray(Image.fromarray(o).resize((1024, 1024), Image.BILINEAR)) > 128
        col = np.asarray(Image.open(FAB + p + "_BaseColor.jpg").convert("RGB")).astype(float)
        rs = components(m, mn)
        for r in rs:   # mean colour of the cut-out: dead (brown) leaves have R >= G
            sub = col[r[1]:r[3], r[0]:r[2]]; w = np.asarray(Image.fromarray(o).crop((r[0], r[1], r[2], r[3]))) > 128
            mc = sub[w].mean(axis=0); r.append(round(float(mc[1] / max(mc[0], 1)), 3))   # index 5 = G/R ratio
        res[k] = {"scan_m": scan, "rects": rs}
        print(k, len(res[k]["rects"]), [(round((r[2]-r[0])*scan/4096*100, 1), round((r[3]-r[1])*scan/4096*100, 1)) for r in res[k]["rects"]][:30])
    json.dump(res, open(sys.argv[1], "w"))
