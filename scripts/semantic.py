"""Search the books by meaning: the client's agent-rag-research corpus on the workstation.

    python scripts/semantic.py "how deep does daylight reach from a side window" [-k 8]

Layer 3 of ADR-0018. Use it when the wording of a question differs from the
books'; for exact terms and numbers use scripts/knowledge.py (layer 2). Each hit
names the book (with its registry id in brackets) and the PDF page; read the page
with knowledge.py before citing, and cite the PRINTED page.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.execution_context import ContextError, project_context

HOST = "ai-workstation"
REPO = "~/ai-projects/research-system-rag"
DATA = "~/ai-projects/archpipe-knowledge-data"
PY = "~/miniconda3/envs/agent-rag-research/bin/python"


# Runs on the workstation in the RAG environment: starts the corpus's own MCP server
# (app.serve) and calls its semantic_search tool, printing the full JSON result.
REMOTE = r"""
import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
q, k, data = sys.argv[1], int(sys.argv[2]), sys.argv[3]
async def run():
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.serve", "--data-dir", data],
                                   env={"PYTHONPATH": "."})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("semantic_search", {"query": q, "k": k})
            print("@@JSON@@" + res.content[0].text)
asyncio.run(run())
"""


def search(query: str, k: int = 8) -> list[dict]:
    remote = (f"cd {REPO} && PYTHONPATH=. timeout 300 {PY} - {shlex.quote(query)} {k} {DATA} 2>/dev/null")
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, remote], input=REMOTE, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=400).stdout
    if "@@JSON@@" not in out:
        return []
    data = json.loads(out.split("@@JSON@@", 1)[1], strict=False)
    hits = []
    for r in data.get("results", [])[:k]:
        cit = r.get("citation") or {}
        anc = r.get("anchor") or {}
        hits.append({"title": cit.get("title"), "pdf_page": anc.get("page"), "section": anc.get("section_path"),
                     "score": r.get("score"), "text": " ".join((r.get("passage_text") or "").split())[:300]})
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("query", nargs="+")
    ap.add_argument("-k", type=int, default=8)
    a = ap.parse_args(argv)
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "semantic",
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    hits = search(" ".join(a.query), a.k)
    for h in hits:
        print(f"  {h['title']}\n    PDF page {h['pdf_page']} | {h['section']}\n    {h['text']}")
    print(f"  ({len(hits)} hits)")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
