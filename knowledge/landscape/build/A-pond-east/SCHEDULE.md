# LDB build schedule

Plant sizes: at 3 years (policy, no growth curve is held) and at maturity.

| species | status | individuals | asset / reason | mature height m | shown height m (age 3) | size basis |
|---|---|---|---|---|---|---|
| punica_granatum | asset | 1 | skf3_f697f7da grade B (species fit) | 3.7 | 1.966 | layout |
| salvia_leucantha | STANDIN | 7 | not drawable yet | 0.76 | 0.404 | source mid-range |
| justicia_brandegeeana | STANDIN | 7 | not drawable yet | 1.22 | 0.648 | source mid-range |
| pennisetum_alopecuroides | STANDIN | 4 | not drawable yet | 0.915 | 0.486 | source mid-range |
| jasminum_sambac | STANDIN | 4 | not drawable yet | 3.25 | 1.727 | source mid-range |
| petrea_volubilis | STANDIN | 2 | not drawable yet | 2.75 | 1.925 | source mid-range |
| origanum_majorana | STANDIN | 2 | not drawable yet | 0.6 | 0.6 | source mid-range |
| aspidistra_elatior | STANDIN | 11 | not drawable yet | 0.6 | 0.24 | source mid-range |
| acorus_gramineus | STANDIN | 15 | not drawable yet | 0.3 | 0.159 | source mid-range |
| alpinia_zerumbet | STANDIN | 2 | not drawable yet | 2.7 | 1.434 | source mid-range |
| plumeria_rubra | asset | 1 | sf_frangipani grade A (genus fit) | 1.8 | 0.798 | ASSUMED: potted size is a GAP in LDL, 1.8 m |

Individuals: {"asset": 2, "standin": 53, "omitted": 1}

## Checks (age 3, closed cover)

```
{
 "clip:fail": 2,
 "footprint:pass": 97,
 "id:pass": 114,
 "plant-footprint:info": 1,
 "plant-footprint:pass": 48,
 "standin:pass": 55,
 "support:pass": 225
}
```

## Build warnings

- ld-plant-bed-se-03 (justicia_brandegeeana) at [27.857, -21.416] lies inside pot-0-plumeria: omitted

## Element ids

| id | kind | layout id | note |
|---|---|---|---|
| ld-paving-0 | paving | paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-1 | paving | paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-2 | paving | paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-3 | paving | paving-3 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-4 | paving | paving-4 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-5 | paving | paving-5 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-6 | paving | paving-6 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-0-r1 | paving | paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-1-r1 | paving | paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-2-r1 | paving | paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-0-r2 | paving | paving-0 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-1-r2 | paving | paving-1 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-2-r2 | paving | paving-2 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-3-r1 | paving | paving-3 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-4-r1 | paving | paving-4 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-5-r1 | paving | paving-5 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-paving-6-r1 | paving | paving-6 | unit paving 0.6 x 0.3 m running bond, 8 mm joints (ASSUMED pattern and unit thickness 40 mm; layout material u |
| ld-path-door | path | path-door | main path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-path-n-0 | path | path-n-0 | main path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-path-e-0 | path | path-e-0 | service path, units laid along the route (ASSUMED pattern; width/class from the layout) |
| ld-bed-west | bed | bed-west | planting bed (border), mulched soil flush with the ground |
| ld-bed-se | bed | bed-se | planting bed (border), mulched soil flush with the ground |
| ld-bed-herb | bed | bed-herb | planting bed (herb), mulched soil flush with the ground |
| ld-n-street | bed | n-street | planting bed (border), mulched soil flush with the ground |
| ld-e-edge | bed | e-edge | planting bed (strip), mulched soil flush with the ground |
| ld-e-pondmass | bed | e-pondmass | planting bed (mass), mulched soil flush with the ground |
| ld-firepit | firepit | firepit | flush gas fire pit chamber (gas, gas; liner/burner dimensions ASSUMED, product not chosen: LS-FIRE-PRODUCT) |
| ld-firepit-flame | flame |  | flame shown in the open state: an emissive cone (not simulated fire) |
| ld-firepit-cover | firepit-cover | firepit | flush fire-pit cover, CLOSED: paving-faced disc 6 mm proud (layout lip 6 mm, load rating 15.0 kN), 3 mm gap to |
| ld-firepit-cover | firepit-cover | firepit | flush fire-pit cover, OPEN: lifted off and set on the paving beside the pit |
| ld-bbq | bbq | bbq | portable BBQ stand: generic kettle, SIMPLE GEOMETRY, not a product (brief: portable, hard surface under it) |
| ld-pond-e | pond | pond-e | flush koi pond 3.5 x 1.0 m: rim at ground level, water 150 mm below the rim, 80 mm contrasting flush lip, safe |
| ld-pond-e-water | water |  | pond water surface 150 mm below the rim |
| ld-pond-e-grille | grille |  | rigid child-protection grille 40 mm below the water surface, bars 20 mm at 100 mm (layout: rigid_grille; bar s |
| ld-bench-quiet | bench | bench-quiet | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-bench-rear | bench | bench-rear | built-in bench / seat wall, 6 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-bench-n | bench | bench-n | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-bench-e | bench | bench-e | built-in bench / seat wall, 2 seats: masonry plinth + 50 mm timber seat (heights from layout seat-wall spec; f |
| ld-dining-table | table | dining-table | generic dining table 2.4 x 0.9 m for 8: SIMPLE GEOMETRY, not a product (no free outdoor table in the library) |
| ld-dining-table-chair-0 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-1 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-2 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-3 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-4 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-5 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-6 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-dining-table-chair-7 | chair |  | generic dining chair: SIMPLE GEOMETRY, not a product (the library's only dining chair is an indoor bouclé upho |
| ld-gravel-0 | gravel | zones:gravel | gravel surface (layout zone surface = gravel; depth 50 mm ASSUMED) |
| ld-gravel-1 | gravel | zones:gravel | gravel surface (layout zone surface = gravel; depth 50 mm ASSUMED) |
| ld-ground-0 | ground | gap | ground with NO built surface in the layout (a zone says paving/other or nothing is drawn): shown as bare compa |
| ld-fence-rear | wall | fence-rear | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-fence-east | wall | fence-east | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-street-fence | wall | street-fence | wall / fence 4.0 m: height from the layout (the LDS fence figure); construction not specified, shown as render |
| ld-sister-screen | screen | sister-screen | trellis screen 2.1 m: timber posts at <=1.5 m, rails and 150 mm batten lattice (ASSUMED detail) for climbers |
| ld-pergola-dining | pergola | pergola-dining | louvred aluminium pergola 2.7 m high: 6 posts, 2 beams, 23 louvre blades at 160 mm (ASSUMED sections; supplier |
| ld-pergola-bench | pergola | pergola-bench | louvred aluminium pergola 2.7 m high: 5 posts, 2 beams, 33 louvre blades at 160 mm (ASSUMED sections; supplier |
| ld-pergola-n | pergola | pergola-n | louvred aluminium pergola 2.6 m high: 4 posts, 2 beams, 12 louvre blades at 160 mm (ASSUMED sections; supplier |
| ld-pergola-e | pergola | pergola-e | louvred aluminium pergola 2.6 m high: 4 posts, 2 beams, 13 louvre blades at 160 mm (ASSUMED sections; supplier |
| ld-pot-0-plumeria | pot | pot-0-plumeria | terracotta pot (ASSUMED 0.55 m high; brief: terracotta pots) |
| ld-tree-0-punica | plant | tree-0-punica | punica_granatum: graded B asset skf3_f697f7da (CC Attribution, UESReseach), scaled to 1.97 m at 3 years |
| ld-plant-bed-west-00 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.41 x 0.40 m |
| ld-plant-bed-west-01 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.41 x 0.40 m |
| ld-plant-bed-west-02 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.41 x 0.40 m |
| ld-plant-bed-west-03 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.41 x 0.40 m |
| ld-plant-bed-west-04 | plant | bed-west | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-bed-west-05 | plant | bed-west | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-bed-west-06 | plant | bed-west | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-bed-west-07 | plant | bed-west | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.41 x 0.65 m |
| ld-plant-bed-west-08 | plant | bed-west | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: not drawable yet) at 0.47 x 0.49  |
| ld-plant-bed-west-09 | plant | bed-west | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: not drawable yet) at 0.47 x 0.49  |
| ld-plant-bed-west-10 | plant | bed-west | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: not drawable yet) at 0.47 x 0.49  |
| ld-plant-bed-west-11 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.47 x 0.40 m |
| ld-plant-bed-west-12 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.47 x 0.40 m |
| ld-plant-bed-west-13 | plant | bed-west | STAND-IN generic shrub mass (salvia_leucantha has no drawable asset: not drawable yet) at 0.47 x 0.40 m |
| ld-plant-bed-west-14 | plant | bed-west | STAND-IN generic shrub mass (pennisetum_alopecuroides has no drawable asset: not drawable yet) at 0.47 x 0.49  |
| ld-plant-bed-west-15 | plant | bed-west | STAND-IN generic climber mass (jasminum_sambac has no drawable asset; not drawable yet) on the screen |
| ld-plant-bed-west-16 | plant | bed-west | STAND-IN generic climber mass (jasminum_sambac has no drawable asset; not drawable yet) on the screen |
| ld-plant-bed-west-17 | plant | bed-west | STAND-IN generic climber mass (petrea_volubilis has no drawable asset; not drawable yet) on the screen |
| ld-plant-bed-west-18 | plant | bed-west | STAND-IN generic climber mass (petrea_volubilis has no drawable asset; not drawable yet) on the screen |
| ld-plant-bed-west-19 | plant | bed-west | STAND-IN generic climber mass (jasminum_sambac has no drawable asset; not drawable yet) on the screen |
| ld-plant-bed-se-00 | plant | bed-se | STAND-IN generic shrub mass (jasminum_sambac has no drawable asset: not drawable yet) at 0.64 x 1.73 m |
| ld-plant-bed-se-01 | plant | bed-se | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.35 x 0.65 m |
| ld-plant-bed-se-02 | plant | bed-se | STAND-IN generic shrub mass (justicia_brandegeeana has no drawable asset: not drawable yet) at 0.35 x 0.65 m |
| ld-plant-bed-herb-00 | plant | bed-herb | STAND-IN generic ground_cover mass (origanum_majorana has no drawable asset: not drawable yet) at 0.66 x 0.60  |
| ld-plant-bed-herb-01 | plant | bed-herb | STAND-IN generic ground_cover mass (origanum_majorana has no drawable asset: not drawable yet) at 0.66 x 0.60  |
| ld-plant-n-street-00 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-01 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-02 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-03 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-04 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-05 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-06 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-07 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-08 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-09 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-n-street-10 | plant | n-street | STAND-IN generic shrub mass (aspidistra_elatior has no drawable asset: not drawable yet) at 0.20 x 0.24 m |
| ld-plant-e-edge-00 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-01 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-02 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-03 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-04 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-05 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-06 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-07 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-edge-08 | plant | e-edge | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-00 | plant | e-pondmass | STAND-IN generic shrub mass (alpinia_zerumbet has no drawable asset: not drawable yet) at 0.58 x 1.43 m |
| ld-plant-e-pondmass-01 | plant | e-pondmass | STAND-IN generic shrub mass (alpinia_zerumbet has no drawable asset: not drawable yet) at 0.58 x 1.43 m |
| ld-plant-e-pondmass-02 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-03 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-04 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-05 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-06 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-plant-e-pondmass-07 | plant | e-pondmass | STAND-IN generic shrub mass (acorus_gramineus has no drawable asset: not drawable yet) at 0.23 x 0.16 m |
| ld-pot-0-plumeria-plant | plant | pot-0-plumeria | plumeria_rubra: graded A asset sf_frangipani (CC Attribution, PlantCatalog), scaled to 0.80 m at 3 years |