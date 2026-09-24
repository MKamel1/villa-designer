"""Run a bounded Claude Code implementation task; the lead owns validation.

The task is a project-local text file. Result, session identity and stderr
are persisted under out/delegation for compact handover and model auditing.
Only invoke when external assistant delegation is authorized.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task',type=Path)
    parser.add_argument('--name',required=True)
    parser.add_argument('--owns',nargs='+',required=True)
    parser.add_argument('--resume')
    args = parser.parse_args()
    if not args.name.replace('-','').replace('_','').isalnum():
        parser.error('name must contain letters, digits, hyphens or underscores')
    task = args.task.resolve()
    if not task.is_relative_to(ROOT) or not task.is_file():
        parser.error('task must be an existing project file')
    owned=[]
    for name in args.owns:
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or path.suffix not in ('.py','.md'):
            parser.error('owned implementation paths must be project Python or Markdown files')
        owned.append(path.relative_to(ROOT).as_posix())
    folder=ROOT/'out/delegation'/args.name
    folder.mkdir(parents=True,exist_ok=True)
    model='claude-sonnet-5'
    session=str(uuid.UUID(args.resume)) if args.resume else str(uuid.uuid4())
    record={'model_requested':model,'session_id':session,'owned_files':owned,
            'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'status':'running'}
    status=folder/'status.json'
    status.write_text(json.dumps(record,indent=2))
    config=folder/'empty-mcp.json'
    config.write_text('{"mcpServers":{}}')
    prompt=('The lead authorized a bounded implementation task. Edit ONLY: '+', '.join(owned)+
        '. Other agents share this checkout: do not revert or edit their files. '
        'No shell commands, network, installers, commits, pushes, Revit, or further delegation. '
        'Use the supplied context; the lead runs tests and integration. '
        'Do not read unrelated history. Define abbreviations and notation before using them. '
        'Implement the requested files, do one review pass, and return a concise handover. '
        'Do not spend turns repeatedly rereading the same completed file; identify remaining uncertainties for the lead.\n\n'+
        task.read_text(encoding='utf-8'))
    argv=[str(Path.home()/'.local/bin/claude.exe'),'-p',prompt,'--model',model,
          '--effort','medium','--safe-mode','--output-format','json','--permission-mode','acceptEdits',
          '--max-turns','30','--tools','Read,Edit,Write,Glob,Grep',
          '--allowedTools','Read','Edit','Write','Glob','Grep',
          '--strict-mcp-config','--mcp-config',str(config)]
    argv.extend(['--resume',session] if args.resume else ['--session-id',session])
    with (folder/'result.json').open('w',encoding='utf-8') as output, \
         (folder/'stderr.log').open('w',encoding='utf-8') as errors:
        process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=output,stderr=errors)
        record['process_id']=process.pid
        status.write_text(json.dumps(record,indent=2))
        deadline=time.time()+2400
        while process.poll() is None:
            if time.time() >= deadline:
                process.kill()
                process.wait()
                record['timed_out']=True
                break
            time.sleep(1)
    exit_code=124 if record.get('timed_out') else process.returncode
    record.update(exit_code=exit_code,status='finished',
                  finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    try:
        result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
        record.update(is_error=result.get('is_error'),usage=result.get('usage'),
                      model_usage=result.get('modelUsage'),cost_usd=result.get('total_cost_usd'),
                      result_subtype=result.get('subtype'))
    except (ValueError,OSError):
        record['result_error']='No valid structured result; inspect stderr and transcript'
    if exit_code or record.get('is_error') or record.get('result_error'):
        record['status']='incomplete'
    status.write_text(json.dumps(record,indent=2))
    print(json.dumps({'session_id':session,'exit_code':exit_code,
                      'status_file':str(status),'result':str(folder/'result.json')},indent=2))
    return exit_code or (1 if record['status']=='incomplete' else 0)


if __name__=='__main__':
    raise SystemExit(main())
