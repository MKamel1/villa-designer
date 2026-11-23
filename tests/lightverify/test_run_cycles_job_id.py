"""Guard: run_cycles must not be answered by a dead job. jobq's submit is idempotent on --id (an existing id returns the OLD job and runs
nothing); the v5 orientation test failed in a fresh clone created at a path an earlier clone had used, because the id was a hash of the
job JSON (paths only). A fake jobq with that exact behaviour stands in for the GPU queue."""
import json
import stat

from archpipe.lightverify import v5_engines as V5

FAKE_JOBQ = """#!/bin/bash
# submit ... --id ID -- cmd args | wait ID ; state in $FAKE_JOBQ_STATE: a seen id is "finished" and its command is never run again
if [ "$1" = submit ]; then
  while [ "$1" != --id ]; do shift; done; id=$2; shift 2; shift
  if [ -e "$FAKE_JOBQ_STATE/$id" ]; then echo "existing $id"; exit 0; fi
  touch "$FAKE_JOBQ_STATE/$id"; "$@"
fi
"""
FAKE_BLENDER = """#!/bin/bash
# blender -b -P probe -- job out : writes the readings file
echo '{"readings": [1.0]}' > "${@: -1}"
"""


def _exe(p, text):
    p.write_text(text)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def test_a_recreated_workdir_with_the_same_job_is_run_again_not_answered_by_the_old_job_id(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("FAKE_JOBQ_STATE", str(state))
    monkeypatch.setattr(V5, "JOBQ", _exe(tmp_path / "jobq", FAKE_JOBQ))
    monkeypatch.setattr(V5, "BLENDER", _exe(tmp_path / "blender", FAKE_BLENDER))
    work = tmp_path / "clone" / "cycles" / "DL"
    job = {"points": [[0, 0, 0]]}
    assert V5.run_cycles(job, work)["readings"] == [1.0]
    assert V5.run_cycles(job, work)["readings"] == [1.0] and len(list(state.iterdir())) == 1      # same content, outputs present: the cache answers, no new job
    import shutil
    shutil.rmtree(work.parent.parent)                                                               # the clone is deleted and re-created at the same path
    assert V5.run_cycles(job, work)["readings"] == [1.0]                                            # before the fix: RuntimeError, the old id returned, no output
    assert len(list(state.iterdir())) == 2
