# Lane protocol (for every dispatched agent)

1. **Branch.** Start from `origin/integ/aplus`: `git fetch origin && git checkout -B lane/<id> origin/integ/aplus`.
   Push `lane/<id>` to origin at least after every milestone step. Never push to `main` or `integ/aplus`.
2. **Ownership.** Write only the paths your lane owns in `ops/lanes.yaml`. Lessons go to
   `docs/lessons/<lane>.md`. Before handing back: `python scripts/lane_guard.py <lane>` must print `clean`.
3. **Contracts.** Use `src/archpipe/contracts.py`: emit `CheckResult` records with criterion ids from
   `docs/quality/a-plus-*.md`, write them with `contracts.write_results(lane, results)`; every
   threshold you use is a `SourceCard`. Do not edit `contracts.py`; ask the lead for changes.
4. **Evidence.** Never invent a value, clause or quote. Unsourced values are `policy` (stated as ours)
   or `unverified` (cannot gate). A check that cannot run reports `not_evaluated`, never `pass`.
5. **Prove before applying.** Prove an engine against the reference cases in your brief before
   running it on the villa. Each rule gets a positive and a negative test.
6. **Tests.** Run your own tests plus `PYTHONPATH=src python -m pytest tests/<your dir> -q`. Do not
   run the whole legacy suite (slow); the lead does that at merge.
7. **Hand-back** (your final message): criteria passed with check output; reference cases reproduced
   (numbers); files changed (from `git diff --stat`, not memory); open items; anything blocked.
   Report only what you ran and saw.

Contract version: 0.1 (2026-11-21). Python: `C:\Users\mmbka\arch-pipeline\.venv\Scripts\python.exe`.
