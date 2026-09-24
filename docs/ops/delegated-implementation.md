# Bounded Claude Code implementation

When the user authorizes Claude Code assistance, the lead can use
`scripts/delegate_implementation.py` to assign implementation to
`claude-sonnet-5` while retaining integration and acceptance checks.

Write a concise task under `out/delegation` and run:

```text
.venv/Scripts/python.exe scripts/delegate_implementation.py out/delegation/task.md --name task-name --owns src/archpipe/module.py tests/test_module.py
```

The helper pins the requested model, uses medium effort and at most thirty
turns, supplies explicit file ownership, and exposes only file reading and
editing tools. Safe mode disables inherited hooks, plugins and other
customizations; the lead must include relevant project constraints in the
task. There is no permission bypass, shell tool, external browsing or
additional delegation. File ownership is an instruction boundary, not an
operating-system sandbox: the lead still reviews the actual diff.

`out/delegation/<task-name>/status.json` records the session identity,
requested model and eventual model usage. `result.json` preserves the
handover and usage; stderr is separate. Verify the actual returned model
usage or session transcript before claiming a particular model did the work.
A stopped/incomplete invocation is not completed implementation.
The helper records the owned process identifier and a forty-minute wall
deadline, including time spent asleep. It marks timeout, turn-limit and
invalid-result cases incomplete. Preserve any produced draft and have the
lead review it; an error exit does not imply no files were written.

Observed CLI usage can include additional internal models even when the
main implementation model is pinned. The presentation run recorded Sonnet
5 and Opus 5.5 usage, and reached its turn limit after producing a working
draft. Record the returned model breakdown rather than claiming all token
use belongs to the requested model. Narrow tasks and one review pass help
avoid repetitive self-review.

Provide a narrow interface, ownership, representative input, acceptance
conditions and the facts already established. Avoid sending an entire
conversation or asking each implementation worker to rediscover the same
environment. Keep scientific/library assumptions tied to primary sources
and real integration checks. For tasks requiring additional research or
execution, the lead supplies that evidence or adapts the tool contract
explicitly; do not silently expand the implementation worker's tools.

The lead runs tests, reviews scientific assumptions, integrates the native
model and inspects final renders. Portable mocks cannot prove an external
tool's command syntax or file placement. In the first Radiance integration,
portable tests passed while the actual workstation invocation exposed an
output-directory error. Capture such failures as reusable regressions.

Delegation moves implementation token use to Claude; it does not eliminate
cost or prove a net token saving. Keep compact task results and avoid
repeating the worker's implementation in the lead session.
