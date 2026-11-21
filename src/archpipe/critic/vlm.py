"""Vision-model scoring through Ollama. Standard library only, so it also runs on the workstation
(`scripts/critic_vlm_batch.py` imports this file by path under `flock graphics.lock`).

One criterion per call, evidence field before the score, temperature 0, fixed seed.
"""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

SCORE_SCHEMA = {"type": "object",
                "properties": {"evidence": {"type": "string"}, "score": {"type": "integer", "enum": [0, 1, 2]}},
                "required": ["evidence", "score"]}
PAIR_SCHEMA = {"type": "object",
               "properties": {"evidence": {"type": "string"},
                              "more_photographic": {"type": "string", "enum": ["A", "B", "equal"]},
                              "margin": {"type": "string", "enum": ["clear", "slight"]}},
               "required": ["evidence", "more_photographic", "margin"]}


class VlmUnavailable(RuntimeError):
    pass


def b64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def chat(host: str, model: str, prompt: str, images: list[str], options: dict, schema: dict,
         think: bool = False, timeout: float = 600.0) -> dict:
    body = {"model": model, "stream": False, "think": think, "format": schema, "options": options,
            "messages": [{"role": "user", "content": prompt, "images": images}]}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except Exception as e:                      # noqa: BLE001 - any transport failure is "unavailable"
        raise VlmUnavailable(str(e)) from e
    if data.get("error"):
        raise VlmUnavailable(data["error"])
    return parse_json(data["message"]["content"])


def parse_json(text: str) -> dict:
    """Tolerant JSON extraction: strict first, then the outermost {...}."""
    try:
        return json.loads(text)
    except ValueError:
        i, j = text.find("{"), text.rfind("}")
        if i >= 0 < j:
            return json.loads(text[i:j + 1])
        raise


def render_prompt(rubric: dict, key: str, title: str = "", pair: bool = False) -> str:
    p = rubric["prompts"][key].replace("{title}", title or "unnamed view")
    return p if pair else rubric["vlm"]["preamble"] + "\n\n" + p


def clean_score(raw: dict) -> dict:
    """Validate a model reply: score must be 0, 1 or 2, else the criterion is not_evaluated."""
    s = raw.get("score")
    if isinstance(s, str) and s.strip().isdigit():
        s = int(s)
    if s not in (0, 1, 2):
        return {"score": None, "evidence": str(raw.get("evidence", ""))[:300], "error": f"bad score {raw.get('score')!r}"}
    return {"score": int(s), "evidence": str(raw.get("evidence", ""))[:300]}


def pair_score(first: dict, second: dict) -> dict:
    """Combine two R13 orders. `first`/`second` are the model replies with `render_is` = 'A' or 'B'
    (which letter held the render). Per order: render at least as photographic -> 2; benchmark by a
    slight margin -> 1; by a clear margin -> 0. Final: 2 only if both orders give 2, 0 only if both
    give 0, otherwise 1 (disagreement across orders is position bias, treated as a tie-ish warn)."""
    per = []
    for r in (first, second):
        m = r.get("more_photographic")
        if m is None:
            return {"score": None, "error": "unparsed pair reply", "orders": [first, second]}
        if m == "equal" or m == r["render_is"]:
            per.append(2)
        else:
            per.append(1 if r.get("margin") == "slight" else 0)
    final = 2 if per == [2, 2] else 0 if per == [0, 0] else 1
    return {"score": final, "per_order": per,
            "evidence": " | ".join(str(r.get("evidence", ""))[:150] for r in (first, second))}


def score_view(host: str, rubric: dict, image_jpg: str, bench_jpg: str, title: str,
               criteria: list[str] | None = None, log=print) -> dict:
    """Run every VLM criterion for one image. Returns {criterion: {...}}."""
    model = rubric["preregistration"]["model"]
    opts = rubric["vlm"]["options"]
    think = bool(rubric["vlm"].get("think", False))
    img = b64(image_jpg)
    out: dict = {}
    for crit, spec in rubric["criteria"].items():
        if not spec["kind"].startswith("vlm") or (criteria and crit not in criteria):
            continue
        if spec["kind"] == "vlm_pair":
            bench = b64(bench_jpg)
            replies = []
            for render_is in ("A", "B"):
                imgs = [img, bench] if render_is == "A" else [bench, img]
                r = chat(host, model, render_prompt(rubric, spec["prompt"], title, pair=True), imgs, opts, PAIR_SCHEMA, think)
                r["render_is"] = render_is
                replies.append(r)
            out[crit] = pair_score(*replies)
        else:
            if rubric["vlm"].get("reference_relative"):
                imgs = [b64(bench_jpg), img]            # image 1 = reference, image 2 = render under review
            else:
                imgs = [img]
            r = chat(host, model, render_prompt(rubric, spec["prompt"], title), imgs, opts, SCORE_SCHEMA, think)
            out[crit] = clean_score(r)
        log(f"  {crit}: {out[crit].get('score')}")
    return out
