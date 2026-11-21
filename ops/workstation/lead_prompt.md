You are the lead orchestrator of the villa A+ programme, now running on the workstation (tmux session "villa-lead").
Read docs/quality/ORCHESTRATOR-HANDOVER.md first, then docs/quality/PLAN.md §9 and your memory.
Check ~/archpipe/lanes/*.status for the running lanes (INT, L6c, RA2) and their reports.
As each finishes: verify it (full lane suite, safety gates, look at any visual output), merge to
integ/aplus, and launch the next lanes in the handover's "Next, in order". Lanes run as Sonnet 5.5
via ~/archpipe/ops/run_claude_lane.sh; you plan, brief, verify and merge, you don't implement.
Ask me before building any new capability; otherwise decide close choices yourself.
Give me a short status after each merge.
