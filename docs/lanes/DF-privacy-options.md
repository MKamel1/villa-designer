# Lane DF: parents' suite privacy, option sketches (2026-11-26)

**Sketches only. No model, spec or render was changed.** Plans (1:50, PNG + SVG): `docs/lanes/DF-privacy-options/plan-{1a,1b,2,3,4}.png`.
Reproduce: `python scripts/df_privacy_options.py` (engine `scripts/df_privacy_engine.py`; numbers in `results.json`).

**Test (client criterion, `docs/decisions/privacy-2026-11-26.md`).** Every suite door open, furniture ignored (worst case). 2D straight lines from
371-451 outside viewpoints (corridor along its length, stair landing, stair void, kids-a/kids-b/family-bath doorways) to a 0.2 m grid over the
dressing room, dressing-ext, ensuite and the ensuite doorway. Pass = zero lines. Negative control: the same engine finds 399 and 367 lines in 1b and 2, so it is not blind.
Limit: plan view only (no eye height or sill); the entry bay just inside a suite door is unavoidably seen when that door is open and is not counted.

**Finding that reframes the problem.** The model as built (1a) already passes: the head-wall door is at the far east and no line from the corridor reaches it.
The sightline the client describes appears when the dressing door moves to the lobby/vestibule end (1b, 2), where the corridor, the open entry and the open dressing door line up.
Plans 1b and 2 show it: a person at the stair landing, 17 m away, sees into the dressing room.

| # | Option | Criterion (doors open) | Cost | Gained | Lost | Route corridor-end to dressing* |
|---|---|---|---|---|---|---|
| 1a | **Today**: dressing door in the head wall, east end | **PASS** 0/451 | none | privacy as built | arrival to dressing is the long way round the bed (9.2 m from the lobby) | 11.2 m |
| 1b | Today + the A3 lobby door we proposed earlier | **FAIL** 399/451 (to 17 m, incl. stair landing) | lobby wall moved 0.15 m; corridor 1.05 to 0.90 | short arrival route | privacy; this is the client's scenario | 4.5 m (756 mm) |
| 2 | **Client idea**: annex corridor end past kids-b, suite door across corridor, door straight from vestibule end into dressing | **FAIL** 367/371 (to 18 m, incl. landing and kids-b doorway) | suite door + 1 wall; vestibule 1.93 x 1.05 | private vestibule, centred bed, solid head wall, hers hanging 2.72 m | the three openings are on one axis, so an open pair shows the dressing room | 3.8 m (702 mm, 750 needed) |
| 3 | **Dog-leg**: option 2 plus a cross wall and a 1.2 x 1.9 m bump-out south of the facade; walk turns south, east, north | **PASS** 0/371 | suite door, cross wall, 3 new wall runs, facade change, pocket door re-set to 0.83 | everything in 2, plus geometry that cannot be defeated by an open door | 2.3 m² outside the south facade (planning and site not checked); a longer walk; 739 mm narrowest at the turn, 11 mm short of 750 | 4.6 m (739 mm) |
| 4 | **Minimal**: no annex; dressing door at the west end of the head wall | **PASS** 0/451 | one door moved | short arrival route, no new rooms | the bed cannot stay centred (east bedside 0.37 m, 0.12 with a tray; 750 needed); head wall broken | 5.9 m (800 mm) |

\* Shortest centreline of a 750 body from the corridor at x 17.2 (just west of the new suite door), widest-pinch in brackets; doors as modelled openings, leaves ignored.
kids-b: in 2 and 3 its door (jamb x 17.14) stays on the public side; the suite door is at x 17.45, so its 0.30 m approach strip is unchanged.

**A hinged or pocket door alone cannot fix 1b or 2 (brute force).** A search of pocket-opening positions and lobby nibs on the A3 lobby never got below 178/241 viewpoints; the lobby is only 1.0 x 0.68 m. Within the 1.05 m corridor width no screen leaves a 750 passage that also blocks the axis. That is why 3 needs extra width.

## Recommendation
Choose by what the client wants most:
1. **If the dressing door must be by the suite entrance: option 3**, the only one that passes with all doors open and keeps the bed centred and the head wall solid. Before it goes further the client must accept the south bump-out; check planning and the site first. Pinch 739 to 750 by trimming 11 mm from the cross-wall stub in the next iteration. A self-closing suite door is then a second layer, not the first.
2. **If no envelope change is acceptable: keep option 1a**. It already meets the criterion; the cost is the long arrival route, as the earlier study stated. Option 4 passes too but costs the centred bed.
3. **Do not build option 2 as drawn.** It is the client's idea and fails in the worst case. If the client still wants it, it needs the dog-leg of option 3 or a closed door as the only protection, which the criterion rules out.

Decisions I made (no one to ask): treated the vestibule entry bay as exempt; ignored door leaves (a leaf can be at any angle); used a 1.2 m bump-out depth so 0.35 storage still leaves 0.85 passage; did no fire, render or model work.
