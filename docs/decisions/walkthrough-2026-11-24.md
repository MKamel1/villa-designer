# Walkthrough requirements (client, 2026-11-24)

The client watched the first whole-villa preview (lane WT, out/wt/villa3/preview/walkthrough.mp4) and said:

- "it had some non informative scenes where the camera [turns] back to where we want to actually look"
- "I want a 360 at each room"
- "I want both floors and the stairs covered"
- "before spending a lot of time in 1080 feel free to follow a more efficient way just to confirm the walkthrough is working as expected"

## Requirements that follow
1. **A full 360° turn in every room** on both floors, from the most informative standing point, with a short hold on the room's best view.
2. **No non-informative stretches.** Between rooms the camera looks along the direction of travel or at the next subject, never backward, and turns are eased. An automatic check fails any run of more than 1 s dominated by a near wall or near-black.
   - Lead review on 2026-11-24 of the first preview, sampled every 6 s: about 30 % of frames were wardrobe fronts or walls at close range, about 12 % were near-black, and about 40 % were good room views.
3. **Both floors and the stair** (a continuous flight, the landing, the gallery), plus the gardens.
4. **Validate cheaply first:** a Workbench shape preview of every frame, then a low-sample Cycles preview, with contact sheets and the wall-check report. The 1080p final starts only after the client approves the route.
5. **Dark rooms** (cinema, stores) use their own exposure groups, not one house-wide exposure.

## Client decision (2026-11-24, later): 16 mm in small rooms
- **Lens:** small rooms (those where the geometric audit finds a 24 mm 360 wall-dominated: guest WC, parents' ensuite and dressing, pantry, family bath, kids-b, landing-GF and similar, decided by the audit's rule, not by eye) use a **16 mm** lens for their 360. Everywhere else stays at 24 mm.
- **Labelling:** the video LABELS those scenes as 16 mm, with an on-screen caption such as "16 mm wide lens: small room" for as long as the lens is wider than 24 mm.
- **Transitions:** 24→16 and 16→24 are SMOOTH. Ease the focal length over a stated duration (about 1–1.5 s, policy) while the camera is moving or turning, never as a cut. The audit and the preview check the transition frames too.

## Client feedback on version 2 (2026-11-24): too much redundancy
"the walkthrough has many redundancy of the 360, it covers everything but it is redundant."
- The design-model "rooms" inside one open space (entry-b, dining, dining-side, kitchen, kitchen-island, living, lounge and so on) each got their own 360, so the same views repeat.
- **Rule from now on:** one 360 per VISUALLY CONNECTED SPACE, not per model room, placed where it shows the most. Smaller sub-areas get a short look or a partial arc only if they show something not yet seen.
- **Coverage drives the route.** Use the geometric audit's per-surface coverage. A turn, arc or hold must add new coverage (a stated minimum share of the space's surfaces and features not seen before); otherwise shorten or drop it. Report the redundancy before → after (seconds spent on already-seen surfaces).
- Keep everything covered (every room, both floors, the stair, the gardens), with 16 mm in the small rooms.
