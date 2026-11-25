"""Prepare, guard, meter, render and encode the production villa walkthrough.

Every graphics stage uses the existing shared graphics lock and Blender pin.
A completed frame is reusable only with matching inputs and its saved bytes.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from archpipe.flythrough import authored_path,policy,digest,require_path_hash,frame_views,villa_policy,is_villa_path
from archpipe.execution_context import Tool,project_context,write_record
from archpipe.safe_io import save_bytes


def save(path,value):
    save_bytes(path,(json.dumps(value,indent=2)+'\n').encode())


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def source_inventory():
    from archpipe.concept.villa_render import provenance_inputs
    files=provenance_inputs()+[ROOT/'knowledge/flythrough-policy.json',ROOT/'knowledge/flythrough-route.json',ROOT/'scripts/flythrough.py',
                              ROOT/'scripts/villa_render_views.py',ROOT/'scripts/villa_render.py',
                              ROOT/'knowledge/flythrough/villa-policy.json',ROOT/'knowledge/flythrough/villa-route.json',
                              ROOT/'knowledge/flythrough/tour-policy.json',ROOT/'knowledge/flythrough/villa-tour.json',ROOT/'knowledge/flythrough/tour-stills.json',
                              ROOT/'knowledge/flythrough/informative-rule.json',ROOT/'src/archpipe/walkthrough_tour.py']
    return {str(p.relative_to(ROOT)):file_hash(p) for p in files}


def prepare(out,route='clip'):
    from archpipe.concept import villa_render as V,villa_lighting as L
    project_context(ROOT,Path(__file__).resolve(),'flythrough-prepare',output=out)
    if (out/'manifest.json').exists():
        require_inputs(out)
        print('Reusing unchanged prepared path and scene');return
    out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    before=source_inventory()
    scene=V.build(views=[])
    if route in ('villa','tour'):
        from archpipe.concept import villa_r11 as R,revit_spec as RS
        from archpipe import flythrough as FT
        layout=R.design('D1');spec=RS.build(layout);vm=FT.VillaMap(layout,spec,scene=scene)
        if route=='tour':
            from archpipe import walkthrough_tour as WT
            path=WT.plan_tour(vm)
        else:
            nodes,stations=FT.plan_villa_route(vm);path=FT.sample_villa_path(vm,nodes,stations)
        # interior door leaves swing open (rotated, never hidden); the report travels with the scene
        scene['door_states']=FT.open_interior_doors(scene,vm,path['frames'])
        save(out/'door-states.json',scene['door_states'])
    else:path=authored_path()
    save(out/'path.json',path)
    scene['views']=frame_views(path,scene)
    from archpipe.concept.garden_render_review import subject_points
    scene['route']=route
    for subject in sorted({s for v in scene['views'] for s in v['subjects']}):
        subject_points(subject,scene)
    scene['provenance']=V.source_provenance()
    save(out/'scene.json',scene)
    for light in scene['lights']:
        if light['type']!='ies':continue
        name=light['ies'];target=out/'ies'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if name.startswith('generic/'):
            kind=Path(name).stem;record=light.get('fixture_record')
            flux=record['flux_lm'] if light.get('garden_g4d') else L.KINDS[kind]['lm']
            beam=record['beam_deg'] if light.get('garden_g4d') else L.KINDS[kind]['beam']
            target.write_text(L.generic_ies(flux,beam,kind))
        else:
            source=ROOT/'out/task-probe-fix/ies'/name
            if not source.is_file():raise FileNotFoundError(source)
            save_bytes(target,source.read_bytes())
    if before!=source_inventory():raise RuntimeError('Source changed during scene assembly; retain interrupted output and prepare a fresh directory')
    save(out/'manifest.json',dict(path_sha256=path['sha256'],scene_sha256=file_hash(out/'scene.json'),
         sources=source_inventory(),photometry={str(p.relative_to(out/'ies')):file_hash(p) for p in (out/'ies').rglob('*.ies')},
         build_seconds=time.monotonic()-started))


def require_inputs(out):
    manifest=json.loads((out/'manifest.json').read_text())
    if manifest['sources']!=source_inventory():raise ValueError('Walkthrough source inputs changed; retain old output and prepare a new isolated output directory')
    path=require_path_hash(json.loads((out/'path.json').read_text()))
    if manifest['path_sha256']!=path['sha256'] or manifest['scene_sha256']!=file_hash(out/'scene.json'):
        raise ValueError('Walkthrough path or scene bytes changed')
    if manifest['photometry']!={str(p.relative_to(out/'ies')):file_hash(p) for p in (out/'ies').rglob('*.ies')}:
        raise ValueError('Walkthrough photometry changed')
    return path


def graphics(out,stage,blender,samples=64,frames=None,segments=None,extra=()):
    # Admit downstream host imports before starting expensive native work.
    from scripts.villa_render_views import camera_proximity_violations
    from scripts.villa_render import villa_qa_context
    require_inputs(out)
    if stage=='exposure' and not is_villa_path(require_inputs(out)):
        coverage=json.loads((out/'coverage/summary.json').read_text())
        assembly=json.loads((out/'assembly/assembly.json').read_text())
        if (not coverage.get('passed') or coverage.get('path_sha256')!=require_inputs(out)['sha256']
                or coverage.get('policy_sha256')!=digest(policy())
                or coverage.get('evaluated_meshes_sha256')!=assembly['receipt']['evaluated_meshes_sha256']
                or coverage.get('sha256')!=digest({k:v for k,v in coverage.items() if k!='sha256'})):
            raise ValueError('Native static-surface coverage checkpoint missing or stale')
    if stage in ('sampling','reference','final') and not Path('/home/omar/archpipe/logs/render/finals.done').is_file():
        raise ValueError('Lead stills have not released final graphics work')
    if stage=='final' and not json.loads((out/'sampling/choice.json').read_text()).get('passed'):
        raise ValueError('Measured sample choice has not passed')
    context=project_context(ROOT,Path(__file__).resolve(),'flythrough-'+stage,output=out,
                            tools=[Tool('blender',blender.resolve(),'4.5.14')])
    write_record(context,out/(stage+'-execution-context.json'))
    command=[str(blender.resolve()),'-b','-t','8','--python-exit-code','1','-P',
             str(ROOT/'src/archpipe/blender/walkthrough.py'),'--','--root',str(out),'--stage',stage,'--samples',str(samples)]
    if frames:command+=['--frames',frames]
    if segments:command+=['--segments',segments]
    command+=list(extra)
    preflight=list(command)
    preflight[preflight.index('--stage')+1]='preflight'
    preflight+=['--target-stage',stage]
    directory=out/'process';directory.mkdir(exist_ok=True)
    token=f'{stage}-{samples}-{time.time_ns()}'
    environment=dict(os.environ,BLENDER_USER_CONFIG=str(out/'blender-config'),TMPDIR=str(out/'tmp'))
    (out/'tmp').mkdir(exist_ok=True)
    start=time.monotonic()
    # Under jobq --gpu the runner already holds graphics.lock; locking again from the child would deadlock.
    with (contextlib.nullcontext() if os.environ.get('JOBQ_JOB_ID') else Path('/home/omar/archpipe/locks/graphics.lock').open('rb')) as lock:
        if lock is not None:fcntl.flock(lock,fcntl.LOCK_EX)
        with (directory/(token+'.log')).open('w') as log:
            status=subprocess.run(preflight,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT).returncode
            if status==0:status=subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT).returncode
    save(directory/(token+'.json'),dict(command=command,preflight=preflight,exit_code=status,seconds=time.monotonic()-start,
         log=str(directory/(token+'.log'))))
    require_inputs(out)
    if status:raise RuntimeError(f'Blender {stage} exited {status}; inspect {directory/(token+".log")}')
    if stage=='assembly':
        from archpipe.flythrough import admit_path,require_renderable
        from archpipe.concept import villa_r11 as R,revit_spec as RS
        scene=json.loads((out/'scene.json').read_text())
        measured=json.loads((out/'assembly/evaluated-path-meshes.json').read_text())
        layout=R.design('D1')
        path_=require_inputs(out)
        if is_villa_path(path_):
            from archpipe.flythrough import admit_villa_path
            guards=admit_villa_path(path_,scene,layout,RS.build(layout),measured)
        else:guards=admit_path(path_,scene,layout,RS.build(layout),measured)
        save(out/'assembly/guards.json',guards)
        save(out/'assembly/admission.json',dict(guards_sha256=digest(guards),
             assembly_sha256=file_hash(out/'assembly/assembly.json'),blend_sha256=file_hash(out/'assembly/scene.blend')))
        require_renderable(guards)



def qa_frames(out,stage,indices):
    from archpipe.render_qa import check
    from scripts.villa_render import villa_qa_context
    from archpipe.flythrough import frame_views
    path=require_inputs(out);scene=json.loads((out/'scene.json').read_text());views=frame_views(path,scene)
    results=[]
    for i in indices:
        png=out/stage/f'frame-{i:04d}.png';record=json.loads(png.with_suffix('.json').read_text())
        result=check(png,villa_qa_context(scene,views[i],record))
        save(png.with_suffix('.qa.json'),result);results.append(dict(index=i,passed=result['passed']))
    report=dict(passed=all(r['passed'] for r in results),frames=results)
    save(out/stage/'qa-summary.json',report)
    return report


def encode(out,stage):
    from PIL import Image
    path=require_inputs(out);directory=out/stage
    if stage=='final':
        if not json.loads((directory/'temporal.json').read_text()).get('passed'):raise ValueError('Temporal acceptance missing')
        if not qa_frames(out,stage,range(0,720,24))['passed']:raise ValueError('Final frame QA failed')
    for frame in path['frames']:
        png=directory/f"frame-{frame['index']:04d}.png";record=json.loads(png.with_suffix('.json').read_text())
        if record['path_sha256']!=path['sha256'] or record['png_sha256']!=file_hash(png):raise ValueError('Incomplete or stale frames')
    target=directory/'walkthrough.mp4';temporary=directory/'walkthrough.tmp.mp4'
    command=['ffmpeg','-y','-framerate','24','-start_number','0','-i',str(directory/'frame-%04d.png'),
             '-frames:v','720','-c:v','libx264','-threads','8','-preset','slow','-crf',str(policy()['encode'][stage+'_crf']),
             '-vf','scale=out_color_matrix=bt709:out_range=tv','-pix_fmt','yuv420p',
             '-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-color_range','tv',
             '-movflags','+faststart',str(temporary)]
    subprocess.run(command,check=True,capture_output=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                    'stream=codec_name,width,height,pix_fmt,nb_frames,r_frame_rate,duration','-of','json',str(temporary)]))
    stream=info['streams'][0]
    if (stream['nb_frames']!='720' or stream['r_frame_rate']!='24/1' or stream['pix_fmt']!='yuv420p'
            or float(stream['duration'])!=30):raise ValueError('Encoded video differs from registered format')
    temporary.replace(target)
    save_bytes(directory/'poster.png',(directory/'frame-0359.png').read_bytes())
    save(directory/'video.json',dict(path=str(target),sha256=file_hash(target),stream=stream,
        caption='Real villa model, level B: entrance, island flank, dining, living, south garden threshold. Garden glazing remains closed; no exit is shown.',
        path_sha256=path['sha256']))
    print(target)


def encode_villa(out,stage,segments,step):
    """Encode the rendered frames of the given segments, every `step`th frame, at 24/step fps (real-time pace)."""
    path=require_inputs(out);directory=out/stage
    keep=[f['index'] for f in path['frames'] if f['segment'] in segments and f['index']%step==0]
    link=out/'tmp'/(stage+'-seq');link.mkdir(parents=True,exist_ok=True)
    for old in link.glob('*.png'):old.unlink()
    for n,i in enumerate(keep):
        png=directory/f'frame-{i:04d}.png';record=json.loads(png.with_suffix('.json').read_text())
        if record['path_sha256']!=path['sha256'] or record['png_sha256']!=file_hash(png):raise ValueError(f'frame {i} incomplete or stale')
        (link/f'{n:05d}.png').symlink_to(png)
    fps=24//step;target=directory/'walkthrough.mp4'
    subprocess.run(['ffmpeg','-y','-framerate',str(fps),'-i',str(link/'%05d.png'),'-c:v','libx264','-threads','8','-preset','slow',
        '-crf',str(policy()['encode'][stage+'_crf']),'-vf','scale=out_color_matrix=bt709:out_range=tv','-pix_fmt','yuv420p',
        '-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-color_range','tv','-movflags','+faststart',str(target)],
        check=True,capture_output=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=codec_name,width,height,pix_fmt,nb_frames,r_frame_rate,duration','-of','json',str(target)]))
    save(directory/'video.json',dict(path=str(target),sha256=file_hash(target),stream=info['streams'][0],frames=keep,fps=fps,
        step=step,segments=segments,path_sha256=path['sha256']))
    print(target,info['streams'][0])


def frame_file(out,path,stage,i):
    if stage=='workbench':return out/'workbench'/path['sha256'][:10]/f'frame-{i:05d}.jpg'
    return out/stage/f'frame-{i:04d}.png'


def encode_draft(out,stage,step,crf=26):
    """MP4 of every `step`th frame at 24/step fps (real-time pace). Workbench JPEGs or Cycles PNGs of the current path only."""
    path=require_inputs(out);keep=[f['index'] for f in path['frames'] if f['index']%step==0]
    link=out/'tmp'/(stage+'-seq');link.mkdir(parents=True,exist_ok=True)
    for old in link.glob('*'):old.unlink()
    for n,i in enumerate(keep):
        src=frame_file(out,path,stage,i)
        if not src.exists():raise ValueError(f'frame {i} missing: {src}')
        if stage!='workbench':
            record=json.loads(src.with_suffix('.json').read_text())
            if record['path_sha256']!=path['sha256'] or record['png_sha256']!=file_hash(src):raise ValueError(f'frame {i} stale')
        (link/f'{n:05d}{src.suffix}').symlink_to(src)
    ext=frame_file(out,path,stage,keep[0]).suffix;fps=24//step
    target=out/f'walkthrough-{stage}.mp4'
    subprocess.run(['ffmpeg','-y','-framerate',str(fps),'-i',str(link/f'%05d{ext}'),'-c:v','libx264','-threads','8','-preset','medium','-crf',str(crf),
        '-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True,capture_output=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,pix_fmt,nb_frames,r_frame_rate,duration','-of','json',str(target)]))
    save(out/f'walkthrough-{stage}.json',dict(path=str(target),sha256=file_hash(target),stream=info['streams'][0],frames=len(keep),fps=fps,step=step,path_sha256=path['sha256']))
    print(target,info['streams'][0])


def report(out):
    """Non-informative-frame report for the workbench pass: metrics runs, direction, coverage, stair; written to report.json."""
    from archpipe import walkthrough_tour as WT
    path=require_inputs(out);rule=WT.informative_rule()
    wb=out/'workbench'/path['sha256'][:10]
    final=out/'workbench'/'metrics2'/'metrics.json'      # full re-measure with hidden objects and glass skipped
    rows={r['index']:r for r in json.loads((final if final.exists() else wb/'metrics.json').read_text())}
    for extra in ([] if final.exists() else sorted((out/'workbench').glob('pan*/metrics.json'))):   # re-measured subsets (glass classified by material) override
        rows.update({r['index']:r for r in json.loads(extra.read_text())})
    rows=[rows[k] for k in sorted(rows)];phase={f['index']:f['phase'] for f in path['frames']}
    flagged={s['room'] for s in path['stations'] if s.get('flagged_under_1m')}
    waived={f['index'] for f in path['frames'] if f['station'] in flagged and f['phase']=='turn'}
    move=[r for r in rows if phase[r['index']]!='turn'];turn=[r for r in rows if phase[r['index']]=='turn']
    runs=WT.run_findings(move,24,rule['max_run_seconds'])
    runs_turn=WT.run_findings(turn,24,rule['max_run_seconds'],waived=waived)
    per_room={}
    for f in path['frames']:
        if f['phase']=='turn':
            a=per_room.setdefault(f['station'],[0,0]);a[1]+=1
    bad={r['index'] for r in rows if r['non_informative']}
    per_room={k:[sum(1 for f in path['frames'] if f['station']==k and f['phase']=='turn' and f['index'] in bad),sum(1 for f in path['frames'] if f['station']==k and f['phase']=='turn')] for k in per_room}
    rooms=[s['room'] for s in path['stations'] if s['room'] and s['kind']=='turn']
    result=dict(rule=rule,frames=len(rows),non_informative_frames=len(bad),
        moving_frames=len(move),moving_non_informative=sum(r['non_informative'] for r in move),runs_over_limit_walk_stair_pan=runs,
        turn_frames=len(turn),turn_non_informative=sum(r['non_informative'] for r in turn),runs_over_limit_in_turns_unwaived=runs_turn,
        turn_wall_facing_fraction_by_room={k:round(v[0]/v[1],2) for k,v in per_room.items()},waived_turn_frames=len(waived),
        direction_findings=WT.direction_findings(path['frames']),stair_findings=WT.stair_findings(path['frames']),
        coverage_findings=WT.coverage_findings(path['frames'],rooms),path_sha256=path['sha256'])
    save(out/'report.json',result);print(json.dumps({k:(v if not isinstance(v,list) else len(v)) for k,v in result.items() if k!='rule'}))
    return result


def contact(out,stage,every,columns=6):
    """Contact sheet of every Nth rendered frame, captioned with frame, time and the room the camera is in."""
    from PIL import Image,ImageDraw
    path=require_inputs(out);directory=out/stage
    rows=[f for f in path['frames'] if f['index']%every==0 and frame_file(out,path,stage,f['index']).exists()]
    thumb=(320,180);pad=16
    directory.mkdir(parents=True,exist_ok=True)
    sheets=[];per=columns*6
    for s in range(0,len(rows),per):
        part=rows[s:s+per];h=(len(part)+columns-1)//columns
        sheet=Image.new('RGB',(columns*thumb[0],h*(thumb[1]+pad)),'black');draw=ImageDraw.Draw(sheet)
        for k,f in enumerate(part):
            with Image.open(frame_file(out,path,stage,f['index'])) as im:im=im.convert('RGB').resize(thumb)
            x,y=(k%columns)*thumb[0],(k//columns)*(thumb[1]+pad)
            sheet.paste(im,(x,y+pad));draw.text((x+3,y+2),f"{f['index']} {f['seconds']:.0f}s {f.get('station') or f['room'] or ''} {f.get('phase','')}",fill='white')
        target=out/f'contact-{stage}-{s//per:02d}.jpg';sheet.save(target,quality=88);sheets.append(str(target))
    print('\n'.join(sheets))


def choose_samples(out,blender):
    """All three cameras must pass unchanged QA and the registered error bound."""
    import numpy as np
    from PIL import Image
    representatives=[0,359,719]
    graphics(out,'reference',blender,1024,','.join(map(str,representatives)))
    trials=[]
    for samples in policy()['sample_candidates']:
        graphics(out,'sampling',blender,samples,','.join(map(str,representatives)))
        stage='sampling/'+str(samples)
        qa=qa_frames(out,stage,representatives)
        differences=[]
        for index in representatives:
            name=f'frame-{index:04d}.png'
            with Image.open(out/stage/name) as image:a=np.array(image.convert('RGB'),dtype=float)
            with Image.open(out/'reference'/name) as image:b=np.array(image.convert('RGB'),dtype=float)
            differences.append(dict(index=index,mean_absolute_rgb_error=float(np.abs(a-b).mean()/255)))
        passed=qa['passed'] and all(r['mean_absolute_rgb_error']<=policy()['sample_difference']['maximum'] for r in differences)
        trials.append(dict(samples=samples,passed=passed,qa=qa,differences=differences))
        result=dict(passed=passed,samples=samples if passed else None,trials=trials,
                    policy_sha256=digest(policy()),path_sha256=require_inputs(out)['sha256'])
        save(out/'sampling/choice.json',result)
        if passed:return result
    raise ValueError('No sample count passes registered image fidelity and production QA')


def temporal(out):
    import numpy as np
    from PIL import Image
    from archpipe.flythrough import temporal_pair
    path=require_inputs(out);directory=out/'final';results=[]
    previous_rgb=previous_positions=None
    for index in range(720):
        name=f'frame-{index:04d}'
        receipt=json.loads((directory/(name+'.json')).read_text())
        positions_file=directory/(name+'-positions.npz')
        if receipt['positions_sha256']!=file_hash(positions_file):raise ValueError('Temporal measurement buffer changed')
        with np.load(positions_file) as buffer:positions=buffer['positions']
        with Image.open(directory/(name+'.png')) as image:rgb=np.array(image.convert('RGB'))
        if index:
            row=temporal_pair(previous_rgb,rgb,previous_positions,positions,path['frames'][index-1]['camera'])
            row['index']=index;results.append(row)
            save(directory/'temporal.json',dict(passed=False,completed_pairs=len(results),pairs=results))
        previous_rgb,previous_positions=rgb,positions
    report=dict(passed=all(r['passed'] for r in results),pairs=results,
                path_sha256=path['sha256'],policy_sha256=digest(policy()))
    save(directory/'temporal.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['prepare','contact','encode-villa','encode-draft','workbench','report','assembly','coverage','exposure','draft','preview','sampling','reference','final','choose-samples','temporal','qa','encode'])
    parser.add_argument('--out',type=Path,default=ROOT/'out/flythrough')
    parser.add_argument('--route',choices=['clip','villa','tour'],default='clip')
    parser.add_argument('--blender',type=Path,default=Path('/home/omar/opt/blender/blender'))
    parser.add_argument('--samples',type=int,default=64);parser.add_argument('--every',type=int,default=1)
    parser.add_argument('--frames');parser.add_argument('--segments');parser.add_argument('--stage',choices=['draft','preview','workbench','sampling','reference','final'],default='preview')
    args=parser.parse_args();out=args.out.resolve()
    if args.operation=='prepare':prepare(out,args.route)
    elif args.operation=='choose-samples':choose_samples(out,args.blender)
    elif args.operation=='temporal':
        result=temporal(out);return 0 if result['passed'] else 1
    elif args.operation=='qa':
        indices=[int(i) for i in args.frames.split(',')] if args.frames else range(0,720,24)
        result=qa_frames(out,args.stage+('/'+str(args.samples) if args.stage=='sampling' else ''),indices);print(json.dumps(result));return 0 if result['passed'] else 1
    elif args.operation=='encode':encode(out,args.stage)
    elif args.operation=='encode-villa':encode_villa(out,args.stage,(args.segments or 'interior').split(','),args.every)
    elif args.operation=='contact':contact(out,args.stage,args.every)
    elif args.operation=='encode-draft':encode_draft(out,args.stage,args.every)
    elif args.operation=='report':report(out)
    else:
        samples=args.samples
        if args.operation=='final':
            choice=json.loads((out/'sampling/choice.json').read_text())
            if choice.get('path_sha256')!=require_inputs(out)['sha256'] or choice.get('policy_sha256')!=digest(policy()):
                raise ValueError('Sample selection binding changed')
            samples=choice['samples']
        frames=args.frames
        if not frames and args.every>1:
            wanted=(args.segments or 'interior,garden-placeholder').split(',')
            frames=','.join(str(f['index']) for f in require_inputs(out)['frames'] if f['index']%args.every==0 and f['segment'] in wanted)
        graphics(out,args.operation,args.blender,samples,frames,args.segments)
    return 0


if __name__=='__main__':raise SystemExit(main())
