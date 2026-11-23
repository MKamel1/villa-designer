# Downloads for the finishes and styling palettes (L4, 2026-11-22)

**The client needs to download nothing to see the three palettes.** The workstation has internet access, and every
render look-alike is a CC0 material from ambientCG or Poly Haven, which need no login. L4 fetches them itself:

- ambientCG: `https://ambientcg.com/get?file=<ID>_2K-JPG.zip` (2K JPG; the scene uses the Color, Roughness and Normal maps).
- Poly Haven: `https://api.polyhaven.com/files/<id>` lists the JPG files; 2K JPG is used (the scene library is 2K).

The exact ids and URLs, per palette, are in `knowledge/products/finishes/<A|B|C>.json` (field `lookalike.url`),
and in the final hand-back table.

## Optional Fab items (only if the client wants 3D look-alikes for soft goods)

Fab (fab.com) needs the client's login. Nothing in the palette boards depends on these: the palettes render with
the cushion and rug props already in the library and a swapped fabric material. If the client wants a different
cushion or throw MODEL per sofa (RF open item 4), download format **glTF/GLB** (or FBX) at the highest
size offered, and put the file under `~/archpipe/inbox/`:

- search Fab for: "boucle cushion", "throw blanket folded", "lumbar pillow", "knitted throw" (CC0 / CC-BY only;
  say the licence on the page, we record it).

Items will be listed here with exact URLs only if a palette is chosen that needs them.
