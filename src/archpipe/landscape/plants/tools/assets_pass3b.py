"""Pass-3b: record the 83 downloaded Sketchfab plant candidates as graded assets (grades by eye on the 5 m / 15 m sheets
rendered through jobq: ldl-p3b-0/1), copy sheets, pin files in asset-manifest.json, update the species rows.
Inputs: /tmp/ldl/p3b/{all.json,o0,o1,sheets}; knowledge/landscape/plants/sketchfab-manifest.json (see docs/lanes/LDL.md)."""
from archpipe.safe_io import copy_file
import json, shutil, glob
from pathlib import Path
from archpipe.landscape.plants.assets import gltf_untextured_share

P = Path('knowledge/landscape/plants/')
doc = json.load(open(P / 'assets.json'))
man = json.load(open(P / 'sketchfab-manifest.json'))
allc = {a['id']: a for a in json.load(open('/tmp/ldl/p3b/all.json'))}
st = {}
for i in (0, 1):
    st.update(json.load(open(f'/tmp/ldl/p3b/o{i}/stats.json')))
RL = 'real_leaves'
# id8: (grade, leaf_type, fit, maps_to species, "Looked at: ...")
G = {
'0a927616': ('A', 'real_leaflets+flowers', 'species', ['jacaranda_mimosifolia'], "Looked at: full blue-flowering crown on a clean trunk at 5 m, even rounded silhouette at 15 m, no flat planes. Second jacaranda of the PlantCatalog series."),
'1f98c425': ('A', 'real_leaflets+flowers', 'species', ['jacaranda_mimosifolia'], "Looked at: broad branching jacaranda crown, flowers and fine foliage, no fishbone at 5 m, good 15 m silhouette."),
'ae20776e': ('A', 'real_leaflets+flowers', 'species', ['delonix_regia'], "Looked at: wide flat-topped crown with red flower mass and fine foliage, correct umbrella silhouette at both distances, shadow dappled."),
'5046ae40': ('A', 'real_leaflets+flowers', 'species', ['delonix_regia'], "Looked at: umbrella crown, red flowers over fine bipinnate leaves, single sturdy trunk; reads at 5 m and 15 m, no cards visible."),
'ebf5a55a': ('A', RL + '+flowers', 'genus', ['plumeria_rubra'], "Looked at: candelabra branching with broad leaves, reads at both distances; title 'Frangipani tree' so genus-level."),
'a05b5ef5': ('A', RL, 'species', ['phoenix_roebelenii'], "Looked at: pygmy date palm, short trunk and a full arching crown of fine real fronds, 2.6 m, no card planes; reads as a dwarf date palm at 5 m and 15 m. Foliage is dark under this sun but not black. Tags name Phoenix roebelenii."),
'11acf710': ('B', 'frond_cards', 'species', ['phoenix_dactylifera'], "Looked at: tall palm with a feathery crown and textured trunk; reads as a date palm at 5 m (no fishbone seen) and 15 m. 56 % alpha-card triangles. Authored 7.3 m tall against the sourced 15-40 m, so a young palm, not a mature one. Made in Treeit; source calls it 'Date Palm'."),
'86982789': ('B', RL, 'genus', ['rhapis_excelsa'], "Looked at: 1.4 m clump of slender canes with real palmate fronds, reads as a lady palm at 5 m, a small green palm shape at 15 m. Source says only 'Rhapis Palm', so genus level."),
'86de7dea': ('B', RL + '+flowers', 'species', ['punica_granatum'], "Looked at: Grove-generated pomegranate in red flower on a thin single stem, 3-4 m (sourced 3.0-3.7 m), real leaves and flowers, reads at 5 m and 15 m. Sparse and single-stemmed, no fruit, generated not scanned. 42k tris."),
'f697f7da': ('B', RL, 'species', ['punica_granatum'], "Looked at: L-system pomegranate, 4.5 m, fine twig crown with real small leaves, no flowers or fruit; airy but reads as a tree at 5 m and 15 m. Author tags it 'noai' (not for AI training; rendering it is not training). 335k tris."),
'a9cb68fd': ('B', RL + '+flowers', 'species', ['lagerstroemia_indica'], "Looked at: Grove-generated crape myrtle, 2.8 m, slender trunk and a sparse purple-pink flower crown; small and thin at 15 m but reads as a flowering tree. Sparse; use as a young specimen."),
'3821ea73': ('B', RL + '+flowers', 'species', ['nerium_oleander'], "Looked at: a SET of about 25 oleander shrubs over 13 m with real narrow leaves and pink flowers; each shrub reads as oleander at 5 m and the group at 15 m. Alpha-card share 0.62 but no fishbone seen. Extract one shrub before placing; 808k tris for the set."),
'75882b72': ('B', 'leaf_cards', 'genus', ['alocasia_macrorrhizos'], "Looked at: 2.8 m elephant-ear clump, big heart-shaped veined leaves on petioles, no fishbone, reads as Alocasia at 5 m and 15 m (hand-painted texture, 2k tris). Source says 'Elephant Ear (Alocasia)': genus level."),
'09127a06': ('C', RL, 'species', [], "Looked at: arrowhead-leaf Alocasia macrorrhizos but authored 9.5 m wide and 7.6 m tall against the sourced 1.5-2.5 m, leaves visibly angular (1.7k tris). Would need a 0.3 scale, a decision not taken here."),
'd0248242': ('C', RL, 'species', [], "Looked at: genuine papyrus stalks with thread umbels, but authored 18.5 m tall against the sourced 1.5-2.4 m and only about 8 stalks. Would be B after a 0.1 scale; not applied, so not drawable."),
'9efab7d2': ('D', 'none', 'none', [], "Looked at: grey untextured lady-palm silhouette (no images, base colour 0.5 grey in the file) with faceted trunk; 2k tris."),
'22c02e4e': ('D', 'none', 'none', [], "Looked at: same grey untextured Poly-by-Google lady palm; the glTF has no images or colour."),
'3d0510cc': ('D', 'none', 'none', [], "Looked at: third copy of the grey untextured Poly-by-Google lady palm."),
'd8083a67': ('D', 'none', 'none', [], "Looked at: renders white and almost invisible; the glTF has no images and no base colour, so nothing to repair."),
'4b6d1583': ('D', 'none', 'none', [], "Looked at: grey untextured calla lilies in a bunch; no images or colour in the file."),
'f59bab2a': ('C', RL, 'genus', [], "Looked at: 1.6 m livistona fan palm with real fronds but a white pot is part of the model; reads at 5 m, small at 15 m. Same file as library skf_f59bab2a."),
'03947862': ('C', RL, 'species', [], "Looked at: aloe rosette with visibly angular, faceted blades at 5 m (2.9k tris); fine at 15 m."),
'0e497993': ('C', RL, 'genus', [], "Looked at: monstera in an orange pot (pot is part of the model), 0.5 m; small at 15 m."),
'2fa12ba0': ('C', RL, 'genus', [], "Looked at: tiny monstera, about 0.3 m, a dot at 15 m."),
'805e6e8c': ('C', RL + '+flowers', 'genus', [], "Looked at: 1 m hibiscus shrub with red flowers, thin and sparse; too small to read as a hedge at 15 m."),
'4a0a7b34': ('C', RL, 'genus', [], "Looked at: 1 m dense round shrub, no flowers; small at 15 m."),
'f03774da': ('C', RL + '+fruit', 'genus', [], "Looked at: nandina shrub with red berries, but stray translucent discs (glass or plastic parts of the SketchUp export) float around it at 5 m; 3 m wide set."),
'fbb15d00': ('C', RL, 'genus', [], "Looked at: 0.5 m golden shrub (Otafuku cultivar), small and low; vanishes at 15 m."),
'34caa6c4': ('C', RL, 'species', [], "Looked at: potted 0.5 m umbrella sedge, the pot is part of the model; vanishes at 15 m."),
'dc17474a': ('C', RL + '+flowers', 'species', [], "Looked at: one liriope clump of three blades and two flower spikes, authored 1 m+; real leaves but a single sparse tuft; not tested as a drift."),
'734c4537': ('C', RL, 'species', [], "Looked at: three stylised young date palms with cartoon trunk rings and ground plants; not realistic at 5 m."),
'db514aa7': ('C', RL, 'species', [], "Looked at: 0.3 m potted fatsia, a dot at 15 m."),
'2a0dbcdf': ('C', RL, 'species', [], "Looked at: realistic banyan with hanging aerial roots and dark crown, but the tree is taller than the 5 m and 15 m framing so the crown is cut off; not gradeable on this rubric, treated as C."),
'46abe3eb': ('C', 'none', 'species', [], "Looked at: photogrammetry trunk of a 198-year-old cypress with a ground patch; no crown in frame."),
'73579baa': ('D', 'none', 'none', [], "Looked at: a scanned twig with flowers and a colour chart, 0.2 m."),
'33e52240': ('D', 'none', 'none', [], "Looked at: a single lemongrass stalk, not a clump."),
}
DEF = "Looked at: {why}"
D_WHY = {
'7131d835': "a guava fruit, 2 cm, a dot", 'f68ae1c3': "a lemon fruit, a dot", '07cc9113': "papyrus scrolls (paper), not a plant", '8c28ce11': "an Egyptian painted column, not a plant",
'1a0f2181': "a cartoon rabbit figure", 'b57fa97a': "a 3 cm calla flower, a dot", 'd879c298': "a lime fruit, a dot", '073d68f0': "a chewing-gum jar", '90df513f': "a rolled parchment",
'88ddf780': "a mouth-freshener bottle", 'c217a737': "a volcanic-island terrain scan", 'e21199e3': "two spider plants in hanging pots, tiny", 'cbcca629': "a handful of giant faceted green polygons (scale and form wrong)",
'73e19eaf': "a potion-bottle scene; the camera sits inside it", '98c88fbc': "a white T-pose human mannequin, not a plant", 'fceb7dee': "a low-poly mixed scene with a trunk and pots, not one plant",
'fb57d2cf': "a yuzu fruit, a dot", '3579fe79': "a dark photogrammetry blob, no readable plant", 'af07eee6': "a photogrammetry scrap of a planter with a few green blades", '2957a532': "a 2 cm jasmine flower, a dot",
'd3be8fed': "a heap of fruit (pineapple, kiwi, artichoke), no pomegranate plant", '71e14714': "a photogrammetry trunk base with a rope and moss, a ground patch", '110f62ea': "a 2 cm camphor leaf, a dot",
'a8d8109b': "a photogrammetry wall and ground scan with a few bottlebrush stems", 'f23b8272': "a 1 cm plumeria flower, a dot", '13209c1d': "two fig fruits, 3 cm", '1d4afb66': "two huge fig fruits filling the frame",
'd15b7c7b': "a photogrammetry ground scan with a few strelitzia leaves", 'c2b66c50': "authored 132 m across with flat dark-green colour only; leaves fill the frame; scale and look both wrong (and it is Salvia guaranitica, not leucantha)",
'a6f5e2c3': "a photogrammetry scene of a ruined wall with strelitzia in front", '72213356': "a 5 cm hornwort sprig, a dot", 'c8565ce8': "a blue lotus on a plate, a decorative object",
'7b6f11dc': "one fatsia leaf stalk (scan), not a plant", '1f6d549a': "a 1 cm star-jasmine flower, a dot", '19172c1a': "a 1 cm ficus leaf cluster, a dot", '817b0b06': "giant dark blades filling the frame, scale wrong",
'c969c2a3': "a 5 cm rosemary sprig, a dot", 'f35eeab5': "an olive twig, 5 cm", 'f47dc516': "a loquat twig, 3 cm", 'a939174a': "a flower cluster and leaf scan with a colour chart, 0.2 m",
'd69e1be5': "separate lotus parts (stalks, leaf, flower), scanned, not a plant", '33a8895c': "a bunch of grapes", '52518584': "a loquat leaf, 3 cm", '98b96bd4': "a tiny potted aloe, a dot",
'84ddce09': "a 5 cm spider-plant, a dot", 'b36256a5': "two guava fruits (one halved), 10 cm", 'ced201b1': "three pomegranate fruits (scan), no plant",
}
for k, w in D_WHY.items():
    G[k] = ('D', 'none', 'none', [], DEF.format(why=w + '; not usable.'))

doc['assets'] = [a for a in doc['assets'] if not a['id'].startswith('skf3_')]
for old in ('knowledge/landscape/plants/asset-previews',):
    pass
am = json.load(open(P / 'asset-manifest.json'))
am['licences']['sketchfab'] = 'CC Attribution or CC0 per the Sketchfab API at download time; CC-BY needs author credit (author and url recorded per asset)'
assert set(G) == {a[5:] for a in allc}, set(allc) ^ {'skf3_' + k for k in G}
uid_of = {'skf3_' + u[:8]: u for u in man}
new = []
for aid, a in allc.items():
    g, lt, fit, maps, why = G[aid[5:]]
    u = uid_of[aid]; m = man[u]; s = st[aid]
    copy_file(f'/tmp/ldl/p3b/sheets/{aid}.jpg', P / 'asset-previews' / f'{aid}.jpg')
    rec = dict(id=aid, source=m['url'], licence='CC0' if m['licence'].startswith('CC0') else 'CC Attribution', author=m['author'], title=m['name'],
               triangles=s['triangles'], size_m=s['size_m'], alpha_card_tri_share=s['alpha_card_tri_share'], preview=f'asset-previews/{aid}.jpg',
               grade=g, leaf_type=lt, species_fit=fit, maps_to=maps, rationale=why, storage='shared', manifest_key='sketchfab/' + u, candidate_for=m['species'])
    us = gltf_untextured_share(a['gltf'])
    if us:
        rec['untextured_material_share'] = us
    new.append(rec)
    am['assets']['sketchfab/' + u] = [dict(file=f, sha256=h, url=m['url']) for f, h in m['files'].items()]
doc['assets'] += new
json.dump(am, open(P / 'asset-manifest.json', 'w'), indent=1)
byid = {a['id']: a for a in doc['assets']}
rank = {'A': 0, 'B': 1, 'C': 2, 'D': 3}; frank = {'species': 0, 'genus': 1}
cands = {}
for a in doc['assets']:
    for sp in a.get('maps_to', []) + ([a['candidate_for']] if a.get('candidate_for') and a['grade'] in 'ABC' and a['species_fit'] in frank else []):
        cands.setdefault(sp, set()).add(a['id'])
for r in doc['species']:
    cs = [byid[i] for i in cands.get(r['slug'], ())]
    cs = [a for a in cs if a['species_fit'] in frank]
    if r.get('best_asset'):
        cs.append(byid[r['best_asset']])
    if not cs:
        continue
    b = min(cs, key=lambda a: (rank[a['grade']], frank.get(a['species_fit'], 9), a['id']))
    r['best_asset'], r['grade'] = b['id'], b['grade']
    ok = b['grade'] in 'AB' and b['species_fit'] in frank
    if ok and r['slug'] not in b['maps_to']:
        b['maps_to'] = sorted(set(b['maps_to']) | {r['slug']})
    r['drawable'] = ('drawable' if ok else 'not drawable yet') if r.get('drawable') != 'drawable_as_genus_standin' or ok else r['drawable']
doc['sketchfab_candidates'] = 'knowledge/landscape/plants/sketchfab-candidates.json + sketchfab-manifest.json (83 downloaded with the client token, all graded in this table as skf3_*; binaries in ~/archpipe/shared/assets/user/landscape/sketchfab/, outside git)'
json.dump(doc, open(P / 'assets.json', 'w'), indent=1, ensure_ascii=False)
print(len(new), sum(r['drawable'] == 'drawable' for r in doc['species']))
