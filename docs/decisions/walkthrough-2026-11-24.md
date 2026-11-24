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
