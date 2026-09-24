"""Replace output files safely on Windows.

An image viewer or the search indexer holding the previous file makes a
plain overwrite fail with OSError 22 (seen twice: halfway through a render
batch, and at the end of a 20-minute pipeline run when out/bedroom.png was
open). Write beside the target, then swap it in, retrying the sharing lock.
The fix first lived only in the render driver, so the pipeline runner hit
the same error; every writer to out/ uses this module (verify.py lint).
"""
from __future__ import annotations

import time
from pathlib import Path


def save_bytes(path: Path, data: bytes, attempts: int = 10, wait_s: float = 1.0) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    for i in range(attempts):
        try:
            tmp.replace(path)
            return
        except OSError:
            if i == attempts - 1:
                raise
            time.sleep(wait_s)


def copy_file(src: Path, dst: Path, **kw) -> None:
    save_bytes(Path(dst), Path(src).read_bytes(), **kw)
