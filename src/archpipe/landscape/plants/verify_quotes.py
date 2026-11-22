"""Re-fetch every cited page and check each SOURCED quote appears verbatim (whitespace/case-normalised).

    python -m archpipe.landscape.plants.verify_quotes [--write]

Result per (slug, attribute): verified | quote_not_found | page_unavailable. Writes
knowledge/landscape/plants/quote-verification.json with --write. Never edits species files.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import os
import ssl
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .library import DATA, load_species

UA = {"User-Agent": "Mozilla/5.0 (plant-library quote check)"}


def norm(t: str, page: bool = False) -> str:
    if not page:  # a quote is plain text: "<6.0) ... (>8.0" must not be read as a tag
        return re.sub(r"[^a-z0-9]+", "", html.unescape(t).replace("\u2019", "'").lower())
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))  # strip tags first: "&lt;6.0" must survive as text
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9]+", "", t.lower())  # letters+digits only: spacing/degree-sign quirks vanish


# Missouri Botanical Garden's server omits its intermediate certificate. Verification stays ON: the bundle is the
# system roots plus the GeoTrust intermediate fetched from the certificate's own AIA URL (see docs/lanes/LDL.md).
MBG_BUNDLE = Path(os.environ.get("LDL_MBG_BUNDLE", Path.home() / "archpipe/shared/assets/user/landscape/ca-bundle-mbg.pem"))


def _ctx(url: str):
    if "mobot.org" in url or "missouribotanicalgarden.org" in url:
        return ssl.create_default_context(cafile=str(MBG_BUNDLE)) if MBG_BUNDLE.is_file() else None
    return None


def fetch(url: str) -> str | None:
    for wait in (0, 3, 8):  # polite retry: the extension sites rate-limit parallel clients
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60, context=_ctx(url)) as r:
                raw = r.read()
            if url.lower().endswith(".pdf"):
                with tempfile.TemporaryDirectory() as d:
                    (Path(d) / "x.pdf").write_bytes(raw)
                    txt = subprocess.run(["pdftotext", str(Path(d) / "x.pdf"), "-"], capture_output=True, text=True).stdout
                return norm(txt, page=True)
            return norm(raw.decode("utf-8", "replace"), page=True)
        except Exception:
            pass
    return None


def run() -> dict:
    sp = load_species()
    items = [(s, a, o["source"]) for s, r in sp.items() for a, o in r["attributes"].items()
             if isinstance(o, dict) and o.get("status") == "SOURCED" and o["source"]["url"].startswith("https://")
             and o["source"].get("quote")]
    urls = sorted({i[2]["url"] for i in items})
    with ThreadPoolExecutor(3) as ex:
        pages = dict(zip(urls, ex.map(fetch, urls)))
    out = {}
    for s, a, src in items:
        pg = pages[src["url"]]
        if src["source_id"] == "GBIF":  # quote is assembled from API JSON fields, not page text
            out.setdefault(s, {})[a] = "api_derived"
            continue
        out.setdefault(s, {})[a] = ("page_unavailable" if pg is None
                                    else "verified" if norm(src["quote"]) in pg else "quote_not_found")
    return out


if __name__ == "__main__":
    res = run()
    from collections import Counter
    c = Counter(v for d in res.values() for v in d.values())
    print(dict(c))
    if "--write" in sys.argv:
        (DATA / "quote-verification.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
