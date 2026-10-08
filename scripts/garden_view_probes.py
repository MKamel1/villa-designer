"""Small quantitative garden probes at the archived whole-set exposure locks.

This diagnostic does not meter a subset or create a presentation delivery.
Exposure stops are base-two brightness multipliers saved by the lead's set.
It preserves full production scene assembly and records the archived cohort.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

def resolve_probe_photometry(data, generated_root, archive_root):
    """Resolve all actual IES paths before assembly; generated files win."""
    resolved={}
    for light in data['lights']:
        name=light.get('ies')
        if not name:continue
        source=None
        for root in (Path(generated_root),Path(archive_root)):
            candidate=(root/name).resolve()
            if not candidate.is_relative_to(root.resolve()):
                raise ValueError('Photometry path escapes its declared root: '+name)
            if candidate.is_file():source=candidate;break
        if source is None:raise FileNotFoundError('Missing probe photometry: '+name)
        resolved[name]=source
    return resolved

def main():
    sys.path.insert(0,str(ROOT/'src'))
    from archpipe.blender import villa_scene as B
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scene',type=Path,required=True)
    ap.add_argument('--candidates',type=Path,required=True)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--samples',type=int,default=64)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    data=json.loads(args.scene.read_text());candidates=json.loads(args.candidates.read_text());by={v['id']:v for v in data['views']}
    locks={};cohorts={}
    for v in candidates:
        report=json.loads((args.archive/(v['id']+'.json')).read_text())
        if not report['exposure_locked_per_state']:raise ValueError('Archived exposure is not a whole-set lock')
        state=report['exposure_state'];value=report['exposure_stops']
        if state in locks and locks[state]!=value:raise ValueError('Inconsistent archived exposure locks')
        locks[state]=value;cohorts[state]=report['exposure_metered_over'];by[v['id']]=v
    data['views']=list(by.values())
    # Inject saved state locks at the same production boundary used by the
    # set meter. This neither changes the live driver nor re-meters cameras.
    B.exposure_locks=lambda views,selected,meter:(locks,{},cohorts)
    args.output.mkdir(parents=True,exist_ok=True)
    # Resolve all text photometry before expensive assembly, using current
    # generated files first and the retained authoritative bundle second.
    from archpipe.safe_io import copy_file
    photometry={}
    for name,source in resolve_probe_photometry(data,args.scene.parent/'ies',args.archive.parent/'ies').items():
        target=args.output/'ies'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        copy_file(source,target)
        photometry[name]=dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    receipt=dict(scene=str(args.scene),scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),archive=str(args.archive),locks=locks,cohorts=cohorts,purpose='numerical probes only; no presentation delivery',photometry=photometry,samples=args.samples,resolution=[800,534])
    (args.output/'probe-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    options=SimpleNamespace(out=str(args.output),views=','.join(v['id'] for v in candidates),calibrate=False,measure_lighting=False,cpu=False,library_root='/home/omar/archpipe/assets/library',ies_dir=str(args.output/'ies'),samples=args.samples,res=[800,534])
    import fcntl
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        B.render(data,options)

if __name__=='__main__':main()
