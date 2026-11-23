# LDB build schedule

Plant sizes: at 3 years (policy, no growth curve is held) and at maturity.

| species | status | individuals | asset / reason | mature height m | shown height m (age 3) | size basis |
|---|---|---|---|---|---|---|
| koi | asset | 6 | skf_3e1b80c3 grade B (None fit) | None | None | None |
| punica_granatum | asset | 1 | skf3_f697f7da grade B (species fit) | 3.7 | 1.966 | layout |
| vitis_vinifera | STANDIN | 2 | not drawable yet | 0.3 | 1.7 | POLICY: 80 % of the structure height at maturity (height not sourced) |
| jasminum_sambac | STANDIN | 4 | not drawable yet | 3.25 | 1.727 | source mid-range |
| justicia_brandegeeana | STANDIN | 13 | not drawable yet | 1.22 | 0.648 | source mid-range |
| pennisetum_alopecuroides | STANDIN | 3 | graded asset file missing on this machine | 0.915 | 0.486 | source mid-range |
| salvia_leucantha | STANDIN | 2 | not drawable yet | 0.76 | 0.404 | source mid-range |
| origanum_majorana | STANDIN | 2 | graded asset file missing on this machine | 0.6 | 0.6 | source mid-range |
| rhapis_excelsa | asset | 2 | skf3_86982789 grade B (genus fit) | 2.45 | 0.98 | source mid-range |
| aspidistra_elatior | STANDIN | 5 | graded asset file missing on this machine | 0.6 | 0.24 | source mid-range |
| acorus_gramineus | STANDIN | 20 | not drawable yet | 0.3 | 0.159 | source mid-range |
| phoenix_roebelenii | asset | 4 | skf3_a05b5ef5 grade A (species fit) | 1.9 | 0.76 | source mid-range |
| farfugium_japonicum | STANDIN | 6 | not drawable yet | 0.6 | 0.319 | source mid-range |
| plumeria_rubra | asset | 1 | sf_frangipani grade A (genus fit) | 1.8 | 1.26 | ASSUMED: potted size is a GAP in LDL, 1.8 m |

Individuals: {"asset": 14, "standin": 57}
Furniture and koi: {"koi:asset": 6, "table:asset": 1, "chair:asset": 8}

## Checks (age 3, closed cover)

```
{
 "climber-coverage:pass": 4,
 "climber-coverage:warn": 1,
 "footprint:pass": 117,
 "id:pass": 146,
 "pit-half:pass": 2,
 "plant-footprint:info": 7,
 "plant-footprint:pass": 51,
 "pond-section:pass": 18,
 "standin:pass": 65,
 "support:pass": 289
}
```

## Build warnings

- canopy s-pergola-grape: pergola NOT built (client change 2026-11-22: pruned shade trees replace pergolas); shade comes from the trees
- canopy s-pergola-rear: pergola NOT built (client change 2026-11-22: pruned shade trees replace pergolas); shade comes from the trees
- canopy n-pergola: pergola NOT built (client change 2026-11-22: pruned shade trees replace pergolas); shade comes from the trees
- canopy e-pergola: pergola NOT built (client change 2026-11-22: pruned shade trees replace pergolas); shade comes from the trees
- climber coverage: wall-street-fence (4.0 m) carries no climber in the layout: no panel built, a layout gap

## Element ids

| id | kind | layout id | note |
|---|---|---|---|
| ld-s-paving-0 | paving | s-paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-1 | paving | s-paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-2 | paving | s-paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-3 | paving | s-paving-3 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-4 | paving | s-paving-4 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-5 | paving | s-paving-5 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-6 | paving | s-paving-6 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-7 | paving | s-paving-7 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-8 | paving | s-paving-8 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-9 | paving | s-paving-9 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-10 | paving | s-paving-10 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-paving-11 | paving | s-paving-11 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-0 | paving | n-paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-1 | paving | n-paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-2 | paving | n-paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-3 | paving | n-paving-3 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-4 | paving | n-paving-4 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-n-paving-5 | paving | n-paving-5 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-0 | paving | e-paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-1 | paving | e-paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-2 | paving | e-paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-3 | paving | e-paving-3 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-4 | paving | e-paving-4 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-5 | paving | e-paving-5 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-6 | paving | e-paving-6 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-7 | paving | e-paving-7 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-e-paving-8 | paving | e-paving-8 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-s-path-door | path | s-path-door | main path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-n-path-0 | path | n-path-0 | main path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-e-path-0 | path | e-path-0 | service path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-s-bed-vine | bed | s-bed-vine | planting bed (climber-strip), mulched soil flush with the ground |
| ld-s-bed-mass | bed | s-bed-mass | planting bed (mass), mulched soil flush with the ground |
| ld-s-bed-mass-corner | bed | s-bed-mass-corner | planting bed (strip), mulched soil flush with the ground |
| ld-s-bed-herb | bed | s-bed-herb | planting bed (herb), mulched soil flush with the ground |
| ld-s-bed-screen-n | bed | s-bed-screen-n | planting bed (screen-climber), mulched soil flush with the ground |
| ld-s-bed-screen-s | bed | s-bed-screen-s | planting bed (screen-climber), mulched soil flush with the ground |
| ld-n-screen | bed | n-screen | planting bed (mass), mulched soil flush with the ground |
| ld-n-edge-far | bed | n-edge-far | planting bed (strip), mulched soil flush with the ground |
| ld-n-edge-back | bed | n-edge-back | planting bed (strip), mulched soil flush with the ground |
| ld-e-divider | bed | e-divider | planting bed (mass), mulched soil flush with the ground |
| ld-e-far | bed | e-far | planting bed (mass), mulched soil flush with the ground |
| ld-e-edge | bed | e-edge | planting bed (strip), mulched soil flush with the ground |
| ld-s-firepit | firepit | s-firepit | flush gas fire pit chamber (gas, gas; ours half only (the pit straddles the shared west line; the neighbour's  |
| ld-s-firepit-flame | flame |  | flame shown in the open state: an emissive cone (not simulated fire) |
| ld-s-firepit-cover | firepit-cover | s-firepit | flush fire-pit cover, CLOSED: paver-pattern top continuing the paving grid, 6 mm proud (layout lip 6 mm, load  |
| ld-s-firepit-cover | firepit-cover | s-firepit | flush fire-pit cover, OPEN: lifted off and set on the paving beside the pit (paver-pattern face up) |
| ld-s-bbq | bbq | s-bbq | portable BBQ stand: generic kettle, SIMPLE GEOMETRY, not a product (brief: portable, hard surface under it) |
| ld-n-pond | pond | n-pond | flush koi pond 2.0 x 1.4 m from the layout section: 150 mm freeboard, entry slope 1:4 over 0.60 m to a 0.30 m  |
| ld-n-pond-lip | pond-lip |  | flush contrasting lip: 80 mm wide coping inside the pond rect, top at ground level, overhanging the water edge |
| ld-n-pond-water | water | n-pond | pond water surface 150 mm below the rim, depth-tinted closed solid |
| ld-n-pond-grille | grille |  | rigid child-protection grille 40 mm below the water surface, bars 20 x 30 mm at 100 mm, resting on a rib on th |
| ld-n-pond-koi-0 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-n-pond-koi-1 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-e-pond | pond | e-pond | flush koi pond 3.2 x 1.4 m from the layout section: 150 mm freeboard, entry slope 1:4 over 0.60 m to a 0.30 m  |
| ld-e-pond-lip | pond-lip |  | flush contrasting lip: 80 mm wide coping inside the pond rect, top at ground level, overhanging the water edge |
| ld-e-pond-water | water | e-pond | pond water surface 150 mm below the rim, depth-tinted closed solid |
| ld-e-pond-grille | grille |  | rigid child-protection grille 40 mm below the water surface, bars 20 x 30 mm at 100 mm, resting on a rib on th |
| ld-e-pond-koi-0 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-e-pond-koi-1 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-e-pond-koi-2 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-e-pond-koi-3 | koi |  | koi, graded B asset skf_3e1b80c3 (CC Attribution, SDPM Esare), 0.70 m long |
| ld-s-bench-rear | bench | s-bench-rear | built-in bench / seat wall, 3 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-s-bench-quiet | bench | s-bench-quiet | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-n-bench | bench | n-bench | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-e-bench | bench | e-bench | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-s-dining-table | table | s-dining-table | dining table for 8: graded B asset skf_4febe1ee (CC Attribution, toxiccrack), fitted to 2.4 x 0.9 x 0.75 m |
| ld-s-dining-table-chair-0 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-1 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-2 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-3 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-4 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-5 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-6 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-s-dining-table-chair-7 | chair |  | dining chair: graded B asset skf_7f558fcd (CC Attribution, pigfinite), scaled to 0.88 m high |
| ld-gravel-0 | gravel | zones:gravel | gravel surface (layout zone surface = gravel; depth 50 mm ASSUMED) |
| ld-wall-fence-rear | wall | wall-fence-rear | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-wall-fence-east | wall | wall-fence-east | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-wall-street-fence | wall | wall-street-fence | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-sister-screen-n | screen | sister-screen-n | trellis screen 2.1 m: timber posts at <=1.5 m, rails and 150 mm batten lattice (ASSUMED detail) for climbers |
| ld-sister-screen-s | screen | sister-screen-s | trellis screen 2.1 m: timber posts at <=1.5 m, rails and 150 mm batten lattice (ASSUMED detail) for climbers |
| ld-pot-0-plumeria | pot | pot-0-plumeria | terracotta pot (ASSUMED 0.55 m high; brief: terracotta pots) |
| ld-s-tree-punica | plant | s-tree-punica | punica_granatum: graded B asset skf3_f697f7da (CC Attribution, UESReseach), scaled to 1.97 m at 3 years |
| ld-plant-s-bed-vine-00 | plant | s-bed-vine | STAND-IN procedural leaf-cutout panel for the climber vitis_vinifera (no graded climber asset: not drawable ye |
| ld-plant-s-bed-vine-01 | plant | s-bed-vine | STAND-IN procedural leaf-cutout panel for the climber vitis_vinifera (no graded climber asset: not drawable ye |
| ld-plant-s-bed-mass-00 | plant | s-bed-mass | STAND-IN procedural leaf-cutout panel for the climber jasminum_sambac (no graded climber asset: not drawable y |
| ld-plant-s-bed-mass-01 | plant | s-bed-mass | STAND-IN procedural leaf-cutout panel for the climber jasminum_sambac (no graded climber asset: not drawable y |
| ld-plant-s-bed-mass-02 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-s-bed-mass-03 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-s-bed-mass-04 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-s-bed-mass-05 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-s-bed-mass-06 | plant | s-bed-mass | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: graded asset file missing on this |
| ld-plant-s-bed-mass-07 | plant | s-bed-mass | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: graded asset file missing on this |
| ld-plant-s-bed-mass-08 | plant | s-bed-mass | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: graded asset file missing on this |
| ld-plant-s-bed-mass-09 | plant | s-bed-mass | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.41 x 0.40 m |
| ld-plant-s-bed-mass-10 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-11 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-12 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-13 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-14 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-15 | plant | s-bed-mass | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.29 x 0.65 m |
| ld-plant-s-bed-mass-corner-00 | plant | s-bed-mass-corner | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.35 x 0.65 m |
| ld-plant-s-bed-mass-corner-01 | plant | s-bed-mass-corner | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.35 x 0.65 m |
| ld-plant-s-bed-mass-corner-02 | plant | s-bed-mass-corner | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.35 x 0.65 m |
| ld-plant-s-bed-mass-corner-03 | plant | s-bed-mass-corner | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.35 x 0.40 m |
| ld-plant-s-bed-herb-00 | plant | s-bed-herb | STAND-IN generic ground_cover mass (origanum_majorana has no drawable asset: graded asset file missing on this |
| ld-plant-s-bed-herb-01 | plant | s-bed-herb | STAND-IN generic ground_cover mass (origanum_majorana has no drawable asset: graded asset file missing on this |
| ld-plant-s-bed-screen-n-00 | plant | s-bed-screen-n | STAND-IN procedural leaf-cutout panel for the climber jasminum_sambac (no graded climber asset: not drawable y |
| ld-plant-s-bed-screen-s-00 | plant | s-bed-screen-s | STAND-IN procedural leaf-cutout panel for the climber jasminum_sambac (no graded climber asset: not drawable y |
| ld-plant-n-screen-00 | plant | n-screen | rhapis_excelsa: graded B asset skf3_86982789 (CC Attribution, wadcon), scaled to 0.98 m at 3 years |
| ld-plant-n-screen-01 | plant | n-screen | rhapis_excelsa: graded B asset skf3_86982789 (CC Attribution, wadcon), scaled to 0.98 m at 3 years |
| ld-plant-n-screen-02 | plant | n-screen | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: graded asset file missing on this machi |
| ld-plant-n-screen-03 | plant | n-screen | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: graded asset file missing on this machi |
| ld-plant-n-screen-04 | plant | n-screen | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: graded asset file missing on this machi |
| ld-plant-n-screen-05 | plant | n-screen | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: graded asset file missing on this machi |
| ld-plant-n-screen-06 | plant | n-screen | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: graded asset file missing on this machi |
| ld-plant-n-edge-far-00 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-far-01 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-far-02 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-far-03 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-far-04 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-far-05 | plant | n-edge-far | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-back-00 | plant | n-edge-back | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-back-01 | plant | n-edge-back | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-back-02 | plant | n-edge-back | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-back-03 | plant | n-edge-back | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-n-edge-back-04 | plant | n-edge-back | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.21 x 0.16 m |
| ld-plant-e-divider-00 | plant | e-divider | phoenix_roebelenii: graded A asset skf3_a05b5ef5 (CC Attribution, herve.rey.421), scaled to 0.76 m at 3 years |
| ld-plant-e-divider-01 | plant | e-divider | phoenix_roebelenii: graded A asset skf3_a05b5ef5 (CC Attribution, herve.rey.421), scaled to 0.76 m at 3 years |
| ld-plant-e-divider-02 | plant | e-divider | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-divider-03 | plant | e-divider | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-divider-04 | plant | e-divider | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-far-00 | plant | e-far | phoenix_roebelenii: graded A asset skf3_a05b5ef5 (CC Attribution, herve.rey.421), scaled to 0.76 m at 3 years |
| ld-plant-e-far-01 | plant | e-far | phoenix_roebelenii: graded A asset skf3_a05b5ef5 (CC Attribution, herve.rey.421), scaled to 0.76 m at 3 years |
| ld-plant-e-far-02 | plant | e-far | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-far-03 | plant | e-far | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-far-04 | plant | e-far | STAND-IN generic shrub mass (farfugium_japonicum has no drawable asset: not drawable yet) at 0.27 x 0.32 m |
| ld-plant-e-edge-00 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-01 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-02 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-03 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-04 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-05 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-06 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-07 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-plant-e-edge-08 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.18 x 0.16 m |
| ld-pot-0-plumeria-plant | plant | pot-0-plumeria | plumeria_rubra: graded A asset sf_frangipani (CC Attribution, PlantCatalog), scaled to 1.26 m at 3 years |