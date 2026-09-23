"""Local Model Context Protocol server. Uses standard input/output transport."""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from archpipe import catalogue, photometry
from archpipe.lighting import Luminaire, point_illuminance
from archpipe.review_extract import review_model as review

mcp = FastMCP('archpipe')
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


def local_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('path must stay inside this project')
    return path


@mcp.tool(annotations=READ)
def read_model(path: str = 'out/bedroom-from-revit.json') -> dict:
    """Read a generated model extract, including measured geometry and review markup."""
    return json.loads(local_path(path).read_text(encoding='utf-8'))


@mcp.tool(annotations=READ)
def review_model(path: str = 'out/bedroom-from-revit.json', scope: str = 'dwelling') -> dict:
    """Run cited deterministic rules. Use room scope only for an isolated-room test."""
    return review(read_model(path), scope=scope)


@mcp.tool(annotations=READ)
def catalogue_item(type_id: str) -> dict:
    """Look up a furniture type's published size, access requirement, and source."""
    return asdict(catalogue.get(type_id))


@mcp.tool(annotations=READ)
def lighting_at(x_mm: float, y_mm: float, height_mm: float,
                path: str = 'out/bedroom-render.json') -> dict:
    """Compute direct illuminance at a point in millimetres; no occlusion or bounce claim."""
    data = read_model(path)
    ies_dir = photometry.revit_ies_dir()
    if ies_dir is None:
        raise ValueError('Local photometric library unavailable')
    scheme = []
    for f in data['lighting']:
        ies_name = f['ies_file']
        if Path(ies_name).name != ies_name:
            raise ValueError('ies_file must be a library filename')
        scheme.append(Luminaire(f['id'], photometry.load(ies_dir / ies_name),
                      f['at'][0], f['at'][1], f['mounting_height'],
                      aim=f.get('rotation') or 0, layer=f.get('layer') or 'ambient',
                      output=float(f.get('output', 1))))
    return {'direct_lux': point_illuminance(scheme, x_mm, y_mm, height_mm),
            'at_mm': [x_mm, y_mm, height_mm],
            'limitation': 'Direct light only, no shadows or inter-reflection; not uniformity compliance.'}


@mcp.tool(annotations=READ)
def project_status() -> dict:
    """Read the full villa roadmap and latest example acceptance evidence."""
    result = {'roadmap': (ROOT / 'docs/ROADMAP.md').read_text(encoding='utf-8')}
    p = ROOT / 'out/bedroom-acceptance.json'
    if p.is_file():
        result['example'] = json.loads(p.read_text(encoding='utf-8'))
    return result


@mcp.resource('archpipe://learnings')
def learnings() -> str:
    return (ROOT / 'docs/LEARNINGS.md').read_text(encoding='utf-8')


@mcp.resource('archpipe://method')
def method() -> str:
    return (ROOT / 'docs/method/villa-design-method.md').read_text(encoding='utf-8')


@mcp.tool(annotations=WRITE)
def propose_example_edit(item_id: str, x_mm: float, y_mm: float,
                         rotation_deg: float | None = None) -> dict:
    """Write a candidate example spec under out/proposals; never edit a generated extract.

    This is a proposal only: it does not change the current specification
    or authoring model. A design lead must review its measured consequences.
    """
    import yaml
    spec = yaml.safe_load((ROOT / 'spec/bedroom-test.yaml').read_text(encoding='utf-8'))
    if not (0 <= x_mm <= spec['room']['width'] and 0 <= y_mm <= spec['room']['depth']):
        raise ValueError('placement is outside the example room')
    items = spec['furniture'] + spec['lighting']
    selected = next((v for v in items if v['id'] == item_id), None)
    if selected is None:
        raise ValueError('unknown item id')
    old = dict(selected)
    selected['at'] = [x_mm, y_mm]
    if rotation_deg is not None:
        if not math.isfinite(rotation_deg):
            raise ValueError('rotation must be finite')
        selected['rotation'] = rotation_deg % 360
    import hashlib
    content = yaml.safe_dump(spec, sort_keys=False)
    proposal_id = hashlib.sha256(content.encode()).hexdigest()[:12]
    dest = ROOT / 'out/proposals' / (proposal_id + '.yaml')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')
    return {'proposal': str(dest.relative_to(ROOT)), 'before': old, 'after': selected,
            'invalidates': ['Revit build', 'extract', 'clearances', 'native sheets', 'lighting', 'render'],
            'status': 'Unbuilt proposal; current model unchanged.'}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True))
def run_bedroom_example(resume: bool = True) -> dict:
    """Rebuild the current approved example spec, overwriting its generated model and outputs.

    Runs local Revit 2027 and the configured ai-workstation renderer. Use
    only when asked to rebuild the example. Does not author a real villa.
    Runtime can be several minutes. It fails closed on missing or stale output.
    """
    argv = [sys.executable, str(ROOT / 'scripts/run_bedroom.py')]
    if resume:
        argv.append('--resume')
    # The protocol owns standard input. Inheriting its live Windows pipe
    # hung Python startup before the coordinator even created its lock.
    result = subprocess.run(argv,
                            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=1200,
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    report = ROOT / 'out/bedroom-acceptance.json'
    evidence = json.loads(report.read_text()) if report.is_file() else None
    return {'exit_code': result.returncode, 'log': result.stdout[-10000:],
            'error': result.stderr[-3000:],
            'acceptance': evidence}


if __name__ == '__main__':
    mcp.run(transport='stdio')
