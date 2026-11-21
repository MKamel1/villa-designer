# Substitution loop: checking a supplier's or installer's product against the design

The client direction (2026-11-21): the products need not be the ones named in the design, as long as they are common
products that do the same job. The supplier confirms availability, proposes equivalents where something is not found,
and the installer later sends the sheet of what will actually be installed. Each proposal is checked here before it is
accepted. Nothing is bought on a name.

## What the client sends

For each luminaire type tag in `luminaire-schedule.xlsx` (DL, ADJ, WW, PEN-LIN, PEN-GLOBE-A, ...), the supplier's or
installer's answer, as three things:

1. the **type tag** it replaces;
2. the product's photometric file: **IES or LDT** (the maker's own; the supplier can download it from the maker);
3. the product's **datasheet** as a PDF, or a small `points.json` that states what the datasheet says
   (format below; `examples/` has two real ones).

If no IES/LDT can be obtained, the answer stays **unconfirmed**: the product may be shortlisted, never accepted.

## The command

```
PYTHONPATH=src python -m archpipe.luminaires.substitute --tag DL --ies proposed.ies --datasheet proposed.pdf
PYTHONPATH=src python -m archpipe.luminaires.substitute --tag ADJ --ies x.ldt --datasheet x.points.json --radiance
```

`--radiance` adds the full Radiance run of the affected rooms (minutes); without it the answer comes in about 30 seconds.
The exit status is 0 for ACCEPT, 3 for ACCEPT WITH DIMMING CHANGE, 1 for REJECT. A JSON report is written to `--out`.
The check needs the frozen per-zone Radiance results of the design in `knowledge/lighting/radiance-l6c/`.

## What it does

| step | what | how |
|---|---|---|
| a | **Inputs (V1, V10)** | The file's candela distribution is integrated two independent ways and compared with the lumens the datasheet states (bar 2 %). Every published non-lumen point (Imax, lux at a distance, beam angle) is reproduced from the file within 5 %. With no published point, V10 is reported `not_evaluated`: the distribution is not checked against the maker's own data. |
| b | **Performance spec** | Lumens (+/-15 % of the reference, else the room check decides), beam angle (+/-15 %, at least 2 deg), CCT (+/-100 K), CRI (>= 90), R9 (>= 50 if stated), IP, dimming protocol (DALI-2 or the on-board dimmer named in the row; phase-cut is rejected), flicker and cut-out (asked, not gated). A **missing mandatory figure** (CCT, CRI, dimming, or IP where the row needs one) rejects the submission as incomplete. |
| c | **Rooms re-run** | The type's fittings keep their positions and aims and take the proposal's distribution and lumens at the same dimming level. Direct light is recomputed analytically on the design's own sensor points; inter-reflected light is scaled by the flux ratio on the frozen Radiance results (fast path). Then the zone drivers are re-solved against the task cards. `--radiance` repeats it with Radiance. |
| d | **Verdict** | see below |

## What comes back

- **ACCEPT**: every task card still met within +/-10 % (and <= 1.5x) at the same dimming levels, and the spec passes. Use it.
- **ACCEPT WITH DIMMING CHANGE**: the spec passes and every card is met once the named zones are re-commissioned; all new
  levels are <= 80 % of maximum output (V12) and >= 5 %. The report lists each zone: old level -> new level.
  Only the commissioning level changes; nothing is redesigned.
- **REJECT**: with every reason: a spec item that fails, a missing figure, a card that cannot be met, a zone that would need
  more than 80 % output, or a zone that would be dimmed below 5 % (the product is oversized for the job).

A reject names what to change (a narrower beam, a DALI driver, more lumens), so the next proposal can be better aimed.

## `points.json`

```json
{"maker": "ERCO", "code": "41321.000", "name": "...", "url": "...",
 "claims": {"lumens": 1065, "watts": 14.4, "cct_k": 2700, "cri": 92, "r9": null, "ip": "IP20",
            "dimming": "DALI-2", "flicker": "TLA SVM <= 0.1", "cutout_mm": null, "finish": "white"},
 "points": [{"kind": "imax", "published": 1147, "source": "datasheet p1"},
            {"kind": "lux_axis", "distance_m": 2, "published": 287, "source": "datasheet cone table"},
            {"kind": "beam_angle", "published": 56}]}
```

Point kinds: `imax` (cd), `lux_axis` (lx at `distance_m` on axis), `beam_diameter` (m at `distance_m`), `beam_angle` (deg), `lumens`.
A PDF is read by text layer: lumens, CCT, CRI, IP, `Imax=`, and dimming words are picked out and quoted; always read the quoted
values against the PDF (a scanned PDF gives nothing, then use `points.json`).

## Limits to know

- The fast path assumes the proposal replaces **every fitting of the type**. Replacing only some rooms: run once per room group
  with the tag's fittings of that group (not built; ask).
- The fast estimate scales inter-reflected light by flux and is not Radiance; the final word on an accepted product is the
  `--radiance` run (the design is re-solved with it, ab 12).
- Ambient (untuned) zones are not re-driven: a proposal with much lower output in an ambient type fails its room planes
  rather than silently raising the level.
- Product identity is taken from the supplier's own files. A product we have no maker file for (decorative types) is
  specified by performance alone; it is `lumens-only` and its absorbed error is the V12 headroom, not a verified figure.
