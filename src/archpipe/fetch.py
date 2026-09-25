"""A polite, robots.txt-checking HTTP client for public pages and files.

Every automated download in the project goes through here (the Signify
catalogue keeps its own fetcher, which predates this and refuses its file
server by name). Rules, enforced rather than promised:

* robots.txt is read per host and obeyed for our User-Agent. A host whose
  robots.txt answers 401/403 is treated as disallowing everything, which is
  urllib.robotparser's documented behaviour.
* One request at a time per process, with a fixed delay between requests.
* Pages are cached on disk, so reruns cost the site nothing.
* No login, no cookies, no form posts. A page that needs an account is a
  click-list item for the user, not something to work around.
"""
from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

UA = "archpipe-research/1.0 (architectural design research; robots.txt respected)"
DELAY_S = 2.0
MAX_BYTES = 2_000_000_000
_last = [0.0]
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


class Disallowed(PermissionError):
    """robots.txt disallows this URL for our User-Agent."""


def _wait() -> None:
    gap = DELAY_S - (time.monotonic() - _last[0])
    if gap > 0:
        time.sleep(gap)
    _last[0] = time.monotonic()


def _open(url: str, timeout: int = 60):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%#~+,;@!$'()*"), headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    parts = urllib.parse.urlsplit(url)
    host = f"{parts.scheme}://{parts.netloc}"
    rp = _robots.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser(host + "/robots.txt")
        _wait()
        try:
            with _open(host + "/robots.txt", timeout=30) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True           # no robots.txt: everything allowed
        except Exception:
            rp.disallow_all = True            # unreachable: do not assume permission
        _robots[host] = rp
    return rp


def allowed(url: str) -> bool:
    return robots_for(url).can_fetch(UA, url)


def get_text(url: str, cache_dir: Path, refresh: bool = False) -> str:
    """GET a page (cached). Raises Disallowed when robots.txt says no."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
    if f.is_file() and not refresh:
        return f.read_text(encoding="utf-8")
    if not allowed(url):
        raise Disallowed(f"robots.txt disallows {url}")
    _wait()
    with _open(url) as r:
        text = r.read().decode("utf-8", "replace")
    f.write_text(text, encoding="utf-8")
    return text


def download(url: str, dest: Path, refresh: bool = False) -> Path:
    """Stream a file to dest (skipped if present). Raises Disallowed when robots.txt says no."""
    if dest.is_file() and dest.stat().st_size > 0 and not refresh:
        return dest
    if not allowed(url):
        raise Disallowed(f"robots.txt disallows {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    _wait()
    n = 0
    with _open(url, timeout=300) as r, part.open("wb") as out:
        while chunk := r.read(1 << 20):
            n += len(chunk)
            if n > MAX_BYTES:
                raise ValueError(f"{url} exceeds {MAX_BYTES} bytes")
            out.write(chunk)
    part.replace(dest)
    return dest
