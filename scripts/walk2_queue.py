"""Resumable bounded walkthrough packages with a complete preview checkpoint.

The preview phase stops after every preview frame and its image checks, an
encoded preview and chronological contact sheets. Review writes the bound
visual-review.json receipt before the final phase can acquire graphics work.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from archpipe.safe_io import save_bytes


def save(file,value):
    save_bytes(file,(json.dumps(value,indent=2)+'\n').encode())


def packages(count,size):
    if count<1 or size<1:raise ValueError('Positive frame count and package size required')
    return [list(range(first,min(first+size,count))) for first in range(0,count,size)]


def contacts(out,count):
    from PIL import Image,ImageDraw
    directory=out/'preview/contacts';directory.mkdir(exist_ok=True)
    receipts=[]
    for group in packages(count,40):
        sheet=Image.new('RGB',(320*5,198*8),'#181818');draw=ImageDraw.Draw(sheet)
        for slot,index in enumerate(group):
            source=out/'preview'/f'frame-{index:04d}.png'
            with Image.open(source) as image:thumb=image.convert('RGB').resize((320,180))
            x,y=(slot%5)*320,(slot//5)*198
            sheet.paste(thumb,(x,y));draw.text((x+4,y+181),f'{index:04d}',fill='white')
        file=directory/f'contact-{group[0]:04d}-{group[-1]:04d}.jpg';sheet.save(file,quality=92)
        receipts.append(dict(path=str(file),frames=group,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    save(directory/'index.json',dict(frame_count=count,sheets=receipts))


def commands(phase,settings):
    if phase=='preview':
        return [(stage,[stage]) for stage in ('prepare','assembly','same-camera','coverage','exposure','draft','preview')]+[
            ('all-preview-qa',['qa','--stage','preview','--frames',','.join(map(str,range(settings['frames'])))]),
            ('encode-preview',['encode','--stage','preview'])]
    result=[('choose-samples',['choose-samples'])]
    for group in packages(settings['frames'],settings['final_package_frames']):
        result.append((f'frames-{group[0]:04d}-{group[-1]:04d}',
                       ['final','--frames',','.join(map(str,group))]))
    return result+[(name,args) for name,args in [
        ('all-adjacent-temporal',['temporal']),('all-frame-speckle',['speckle','--stage','final']),
        ('encode-master',['encode','--stage','final']),('encode-web',['encode-web'])]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['preview','final'],required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'out/walk2')
    parser.add_argument('--plan',action='store_true')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    policy_file=ROOT/'knowledge/walk2-policy.json';settings=json.loads(policy_file.read_text())
    jobs=commands(args.phase,settings)
    if args.plan:
        print(json.dumps([dict(name=name,operation=command[0]) for name,command in jobs],indent=2));return 0
    if args.phase=='final':
        from scripts.flythrough import require_inputs,require_preview_review
        os.environ['ARCHPIPE_FLYTHROUGH_POLICY']=str(policy_file)
        require_preview_review(out,require_inputs(out))
    with (out/'queue.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        environment=dict(os.environ,PYTHONPATH=str(ROOT/'src'),NO_COLOR='1',
                         ARCHPIPE_FLYTHROUGH_POLICY=str(policy_file),MPLCONFIGDIR=str(out/'matplotlib'))
        state=dict(pid=os.getpid(),phase=args.phase,status='RUNNING',started_unix=time.time(),completed=[])
        ledger=out/(args.phase+'-queue.json')
        try:
            for name,arguments in jobs:
                command=[sys.executable,str(ROOT/'scripts/flythrough.py'),*arguments,'--out',str(out),'--policy',str(policy_file)]
                logfile=out/(name+'.log');state.update(active=name,command=command,log=str(logfile));save(ledger,state)
                started=time.monotonic()
                with logfile.open('w') as stream:result=subprocess.run(command,cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT)
                state['completed'].append(dict(name=name,exit_code=result.returncode,seconds=time.monotonic()-started,log=str(logfile)))
                save(ledger,state)
                if result.returncode:raise RuntimeError(f'{name} exited {result.returncode}; inspect {logfile}')
            if args.phase=='preview':contacts(out,settings['frames'])
            state.update(status='PREVIEW_REVIEW_PENDING' if args.phase=='preview' else 'NUMERIC_GATES_AND_ENCODE_COMPLETE_VISUAL_REVIEW_PENDING',
                         active=None,finished_unix=time.time());save(ledger,state)
        except BaseException as error:
            state.update(status='FAILED',error=str(error),finished_unix=time.time());save(ledger,state);raise
    return 0


if __name__=='__main__':raise SystemExit(main())
