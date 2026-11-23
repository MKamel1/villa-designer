# FG: items the client should download (2026-11-22)

Destination: `~/archpipe/shared/assets/user/landscape/fab/` (zips) and `.../fab/unzipped/<name>/` (unzipped; the existing convention).
Fab needs the Epic account the client already has. Click **Add to My Library / Download** on the listing; on the download dialog pick:
* **Atlas listings** (type "material" on Fab): the **4K** (highest) resolution, format **JPG** maps (not EXR). Keep the `.json` that ships in the zip (it lists the maps and the translucency tint).
* **3D-model listings**: **FBX**, highest quality (not Low/Medium), JPG maps.

All Fab items below are listed by Quixel Megascans with licences "Personal" and "Professional" (checked on the listing API 2026-11-22, price 0.0). Terms (quoted by LDL pass 4 from the Fab EULA summary): "Use the assets commercially or privately"; "Use the assets with any compatible tools (usage is not limited to Unreal Engine)"; you may not "Resell or redistribute the asset for free on a standalone basis". Do not put the zips into the git repo (the shared folder is outside it). Poly Haven items are **CC0** (public domain; polyhaven.com/license).

Already downloaded and used: Star Jasmine, Creeping Fig, Bougainvillea Flower atlases; Cast-Iron Plant, Red Fountain Grass, Oregano, Ginger Lily, Jungle Ginger, Taro, Lady/Fan palms, Aloe, Rosemary, Sage, English Ivy.
Spelled out below are only the NEW ones, most important first. Fab "material" listings come in several variants of one scan; the first URL is the one I want, the others are extra variants (optional).

## A. Leaf atlases (the leaf bank for the generator)

| # | item | URL | why (species or class served) | scan |
|---|---|---|---|---|
| 1 | **Australian Laurel** (material, atlas) | https://www.fab.com/listings/ce7d24c5-e2d0-4f01-ad64-8d2de5fcbeea | **Pittosporum**: "Australian laurel" is *Pittosporum undulatum*, the same genus as our *P. tobira*: entire-margined, glossy, leathery. Genus-level, so `fidelity: form-class` for tobira unless the client accepts genus match. Highest texel density of the laurels | 0.39 m, 10503 px/m |
| 2 | **Spotted Laurel** (material, atlas) | https://www.fab.com/listings/ea03b183-805b-445e-a47c-edec1b627f83 (variant: .../7a60327f-7003-40fe-bb25-f20376e20515) | Broad glossy entire leaves: the **broadleaf-shrub bank** (Justicia/farfugium-class mass, Pittosporum fallback). The listing also has a 3D model: https://www.fab.com/listings/ebbd5efc-9069-4ae1-a766-c5627cb21f34 (optional) | 0.79 m, 5185 px/m |
| 3 | **Weeping Fig** (material, atlas) | https://www.fab.com/listings/441f1dfc-4ae1-4003-a024-f12dcc30d6e0 | *Ficus benjamina*: small glossy entire pointed leaves; second glossy bank, and the dense small-leaf look for Justicia and Arabian jasmine (form-class) | 0.99 m, 4137 px/m |
| 4 | **Common Grape Vine** (material, atlas) | https://www.fab.com/listings/3051e851-ead3-461e-87b3-7991f5407330 (variant .../53b06bb5-fdf6-4715-9cd1-61dcdb2ebc14) | **Grape** on the pergola/trellis: *Vitis vinifera* leaves, so the grape climber becomes **species-faithful** (the brief lists 2 grapes). Also palmate-lobed fallback for Fatsia | 0.92 m, 4452 px/m |
| 5 | **Tree Philodendron** (material, atlas) | https://www.fab.com/listings/69a80972-5160-4b46-bbdd-6aee490ec179 | Large deeply lobed glossy leaves: **Fatsia** (palmate) as form-class. Not a Fatsia scan, so labelled form-class | 0.91 m, 4501 px/m |
| 6 | **Elephant Ear** (material, atlas) | https://www.fab.com/listings/413b8457-1c03-4383-b45b-033ef0faf027 | Large rounded glossy leaves on long petioles: **Farfugium** (leopard plant) as form-class (it is a different, similar-looking leaf; labelled so) | 0.92 m, 4452 px/m |
| 7 | **African Flag** (material, atlas) | https://www.fab.com/listings/142549d3-4ca7-4c7d-b22c-c309722c8d17 | Strap/iris-type blades with flowers: **Acorus** (sweet flag is an iris-like marginal strap leaf) as form-class | 0.41 m, 9990 px/m |
| 8 | **Chinese Wisteria** (material, atlas) | https://www.fab.com/listings/a7dd24e0-3e03-4e1a-b542-e5e49d561882 | Pinnate-leaflet twining climber foliage: **Petrea / Arabian jasmine** climbers as form-class (the leaflets are not the species) | 0.86 m, 4763 px/m |

## B. Bark (crape myrtle tree, others)

| # | item | URL | why | licence |
|---|---|---|---|---|
| 9 | **bark_platanus** (Poly Haven, texture) | https://polyhaven.com/a/bark_platanus | Smooth, mottled, flaking bark: the nearest CC0 look to the pale mottled bark of crape myrtle (*Lagerstroemia*). Pick **2k or 4k, JPG** (diff/nor_gl/rough/disp) | CC0 |
| 10 | **sakura_bark** (Poly Haven, texture) | https://polyhaven.com/a/sakura_bark | Smooth bark with lenticels: alternative/for young stems. Same format | CC0 |
| 11 | **Banyan Bark** (Fab material) | https://fab.com/listings/7f005254-8cd3-4194-b5ae-dada270235b3 | Smooth-ish grey Ficus bark for ficus-type stems (optional) | Fab Standard |

## C. Ground (mulch, soil under planting)

| # | item | URL | why |
|---|---|---|---|
| 12 | **Mulch** (Fab material) | https://www.fab.com/listings/7a4cea01-9dbc-4a4b-8ebd-da4c6d45280c | Bed surface under shrubs: shows planting reads as planted, not floating on grass. 4K JPG |
| 13 | **Soil Mulch** (Fab material) | https://www.fab.com/listings/df9ace97-a606-4464-889a-5cd7b96e4d28 | Alternative: finer soil |

## D. CC0 leaf/ground textures (no download needed unless noted)

ambientCG (CC0, https://docs.ambientcg.com/license/): Leaf001/002/003 are toothed or pinnate single leaves, **already judged a weak fit by LDL** (no entire glossy leaf); not requested. Poly Haven has **no** leaf atlas (only ground and bark scans). So the glossy entire-margin leaf comes from items 1-3, not from CC0.

## What this does NOT cover (so the generator labels it form-class)

No free scan exists for: Fatsia, Farfugium, Justicia, Salvia leucantha, Acorus, Alpinia zerumbet, Arabian jasmine, Petrea. The leaves above are stand-in leaf shapes for those; each plant is recorded `fidelity: form-class`. Searching Fab for "pittosporum", "aucuba", "fatsia", "ligularia" and "aspidistra" as listings returns nothing besides the Cast-Iron Plant already held.
