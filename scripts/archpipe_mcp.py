"""Local Model Context Protocol server. Uses standard input/output transport."""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import asyncio
from typing import Literal
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
def read_model(path: str = 'out/bedroom-from-revit.json', include_meshes: bool = False) -> dict:
    """Read measured geometry and markup; summarize dense meshes unless explicitly requested."""
    data = json.loads(local_path(path).read_text(encoding='utf-8'))
    if not include_meshes:
        for category in ('furniture','casework','openings','lighting'):
            for item in data.get(category,[]):
                if 'meshes' in item:
                    meshes=item.pop('meshes')
                    item['mesh_summary']={'components':len(meshes),
                        'vertices':sum(len(m['vertices_mm']) for m in meshes),
                        'triangles':sum(len(m['triangles']) for m in meshes),
                        'materials':sorted({m.get('material',{}).get('name','unspecified') for m in meshes})}
        data['mesh_data_path']=path
    return data


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
        from run_bedroom import input_hashes, artifacts_match
        evidence = json.loads(p.read_text(encoding='utf-8'))
        result['example'] = {k:evidence.get(k) for k in
            ('passed','scope','finished_utc','error','limitations')}
        result['example'].update(evidence_path=str(p.relative_to(ROOT)),
            matches_current_local_inputs=(evidence.get('input_hashes')==input_hashes() and
                                          artifacts_match(evidence.get('artifacts',{}))),
            remote_runtime_checked_now=False)
    result['workstation'] = {}
    for operation in ('verify','benchmark','sweep','batch','bedroom','radiance'):
        path = ROOT/'out/workstation'/(operation+'-latest.json')
        if path.is_file():
            record = json.loads(path.read_text())
            result['workstation'][operation] = {'passed':record.get('passed'),
                'batch_id':record.get('batch_id'),'reused':record.get('reused'),
                'jobs':len(record.get('jobs',[])),'report':str(path.relative_to(ROOT))}
    return result


@mcp.resource('archpipe://learnings')
def learnings() -> str:
    return (ROOT / 'docs/LEARNINGS.md').read_text(encoding='utf-8')


@mcp.resource('archpipe://method')
def method() -> str:
    return (ROOT / 'docs/method/villa-design-method.md').read_text(encoding='utf-8')


@mcp.resource('archpipe://compute')
def compute_placement() -> str:
    return (ROOT/'docs/ops/compute-placement.md').read_text(encoding='utf-8')


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False,openWorldHint=True))
async def run_workstation_job(operation: Literal['verify','batch','bedroom','benchmark','sweep','radiance'],
                             input_path: str = 'out/bedroom-render.json',
                             samples: int = 256, resolution: str = '1600x1000',
                             workers: int = 2) -> dict:
    """Run bounded Ubuntu jobs, reuse matching evidence and fetch outputs in one call.

    Operations cover portable verification, camera batches, a complete
    bedroom render/probe/Radiance batch, processor/graphics benchmarks,
    unbuilt lighting/layout alternatives and independent Radiance studies.
    No Revit authoring or native family transfer. Parameters are bounded.
    """
    if not 1 <= workers <= 4 or not 32 <= samples <= 4096:
        raise ValueError('workers must be 1..4 and samples 32..4096')
    try:
        dimensions = [int(v) for v in resolution.split('x')]
    except ValueError:
        raise ValueError('resolution must be widthxheight in pixels')
    if len(dimensions)!=2 or any(v<128 or v>4096 for v in dimensions):
        raise ValueError('Image dimensions must be 128..4096 pixels')
    path = local_path(input_path)
    argv = [sys.executable,str(ROOT/'scripts/workstation.py'),operation,'--input',str(path),
            '--samples',str(samples),'--resolution',resolution,'--workers',str(workers)]
    response = await asyncio.to_thread(subprocess.run,argv,cwd=ROOT,
        stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',
        errors='replace',timeout=2400,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    if response.returncode:
        return {'passed':False,'exit_code':response.returncode,
                'error':(response.stdout+response.stderr)[-5000:]}
    return json.loads(response.stdout)


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


@mcp.tool(annotations=READ)
def check_render(image: str = 'out/photoreal/bedroom-off-window.png') -> dict:
    """Run the automatic presentation-render checks on a saved render.

    Each check is a defect that once shipped and had to be spotted by eye
    (void/mirror window, glass blocking daylight, lost photometry, tilted
    camera, colour cast, clipping, CAD colours, grey textiles, collapsed
    cloth). Reads the image and its `.log` beside it. Passing means no
    KNOWN defect; still look at the image for new ones.
    """
    from archpipe import render_qa
    png = local_path(image)
    log = png.with_suffix('.log')
    if not log.is_file():
        raise ValueError('no render log beside the image; render with scripts/render_hyperreal.py')
    return render_qa.check(png, render_qa.scene_qa_from_log(log.read_text(encoding='utf-8', errors='replace')))


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
    return {'passed':result.returncode == 0 and bool(evidence and evidence.get('passed')),
            'exit_code': result.returncode, 'log': result.stdout[-10000:],
            'error': result.stderr[-3000:],
            'acceptance': evidence if result.returncode == 0 else None,
            'evidence_path':str(report.relative_to(ROOT))}


if __name__ == '__main__':
    mcp.run(transport='stdio')
