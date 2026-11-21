# G1 — client decisions on the D1 safety report (2026-11-21)

Source: `docs/lanes/L1-safety-report-D1.md` (international best practice; Egyptian values informative).

| Finding | Decision | Consequence stated at decision time |
|---|---|---|
| LS2 open-riser stair: 116.5 mm gap vs 100 mm sphere; 0 mm tread overlap vs 16 mm (ADK 1.9) | **Keep open risers, add infill** so no 100 mm sphere passes, and extend treads for ≥16 mm overlap | Floating look kept; infill must be designed and modelled; closed risers (A+ target) not adopted |
| LS5 basement cinema: windowless inner room reached only through the lounge (ADB 2.11) | **Accepted risk — waiver.** Cinema stays where it is | Recorded waiver; grade note: this item remains a best-practice failure; mitigation (interlinked smoke detection in lounge and cinema) to be included by the electrical lane |
| LS3 missing guards: GF stair-void edge (3.71 m), GF front terrace (3.0 m drop), entrance-steps edge over the patio (1.2–1.8 m drop) | **Add guards** (1100 mm at external drops, policy; 900 mm minimum internal) | Guards modelled in spec, Revit and scene |
| LS4 GF core door 75 mm from top step (400 mm needed, ADK 1.24) | **Hang the door to swing outward**, away from the stair | Door swing authored in the spec |
| LS1 open space under the lowest 11 treads, soffit < 2 m | **Enclose as a cupboard** | Storage gained |
| CL2 basement daylight factor low (lounge 0.59 %, kitchen 0.33 %, cinema 0.04 % vs 1.5–2 % guidance) | **Raise basement daylight** (client prefers shade, so modest increase, keep shading) | Glazing/rooflight options to be proposed with daylight figures before modelling |
| Follow-up (lane D options) | **Lounge street glazing widened 3.41 → 3.71 m (built). No light slot.** The 0.9 m grated slot along the east fence under the car ramp was dropped: it would cost 0.9 m from the store, cinema, guest WC and dirty kitchen, and its claimed lounge/kitchen gains were scaled from an older layout (P3/P4), not computed for D1. Direction checked against the model: street = north (client naming), the slot side is the east fence. | Basement relies on the lighting design; revisit only with a D1 Radiance calculation |
