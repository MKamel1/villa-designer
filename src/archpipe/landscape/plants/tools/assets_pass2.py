"""Pass-2 asset table update (one-off, reproducible): drop Ixora, add the 20 Poly Haven 1k glTF assets graded from
their rendered turntable sheets (looked at), flag the misnamed jacaranda and the textureless banana, write the manifest.
Inputs: sheets + stats from /tmp/ldl (previews rendered by asset_preview.py through jobq); see docs/lanes/LDL.md."""
import json, os, shutil, urllib.request
P = 'knowledge/landscape/plants/'
doc = json.load(open(P + 'assets.json'))
doc['species'] = [r for r in doc['species'] if r['slug'] != 'ixora_coccinea']
for x in doc['assets']:
    if x['id'] == 'sf_ixora':
        x['maps_to'] = []; x['species_fit'] = 'none'; x['rationale'] += ' Ixora dropped from the palette (pass 2); asset kept as a record only.'
st = {}
for d in ('a', 'b'):
    st.update(json.load(open(f'/tmp/ldl/prev3{d}/stats.json')))
G = {
'ph_island_tree_01': ('B', 'real_leaves', 'look-alike', [], "Looked at: gnarled trunk, olive-like small lanceolate leaves, full crown, no cards or flat planes visible at 5 m; reads as a small Mediterranean tree at 15 m. Source names no species (tags 'island, coastal'), so it cannot be mapped to Olea europaea."),
'ph_island_tree_02': ('B', 'real_leaves', 'look-alike', [], "Looked at: twisted multi-stem trunk with a ground disc, olive-like leaves; credible at 5 m and 15 m. Species not named by the source; look-alike only."),
'ph_island_tree_03': ('C', 'real_leaves', 'look-alike', [], "Looked at: low multi-stem shrub-tree on a visible rock/soil base plate (flat disc shows at 5 m), small at 15 m. Species not named."),
'ph_tree_small_02': ('B', 'real_leaves', 'none', [], "Looked at: slender trunk, light feathery crown with real leaflets; reads as a small tree at 5 m and 15 m. It is Burkea africana (source tag 'wild syringa'), not in the palette; usable only as a generic light-canopy tree."),
'ph_pachira_aquatica_01': ('C', 'real_leaves', 'none', [], "Looked at: set of five young saplings, spindly, 0.5-1 m; reads as seedlings not a tree at 5 m and vanishes at 15 m. Pachira aquatica is not in the palette."),
'ph_shrub_01': ('C', 'real_leaves', 'none', [], "Looked at: set of 8 weed-like seedlings (source tag Ageratina adenophora), 0.3-0.5 m; sparse, no mass at 5 m, invisible at 15 m."),
'ph_shrub_02': ('C', 'real_leaves', 'none', [], "Looked at: wispy brown-green weedy stems; sparse, not a shrub mass; poor at 5 m."),
'ph_shrub_03': ('C', 'real_leaves', 'none', [], "Looked at: four tiny thin plants; too small to read at 5 m, gone at 15 m."),
'ph_shrub_04': ('C', 'real_leaves', 'none', [], "Looked at: four tiny rosette seedlings; too small to read at 5 m."),
'ph_fern_02': ('C', 'real_leaves', 'none', [], "Looked at: small fern clumps 0.3 m; fine at 5 m as understory but invisible at 15 m; no palette species is a fern."),
'ph_calathea_orbifolia_01': ('C', 'real_leaves', 'none', [], "Looked at: scattered small calathea plants; sparse at 5 m. Not in the palette."),
'ph_anthurium_botany_01': ('C', 'real_leaves', 'none', [], "Looked at: small anthurium-like rosettes 0.3 m; sparse. Not in the palette; no use for Monstera or Thaumatophyllum (different leaf form)."),
'ph_potted_plant_01': ('C', 'real_leaves', 'none', [], "Looked at: small leafy plant in a terracotta pot (the pot is part of the model); 0.6 m; unidentified species."),
'ph_searsia_lucida': ('B', 'real_leaves', 'none', [], "Looked at: six dense dry-climate shrubs with real leaves and branching, readable at 5 m, small mass at 15 m. Searsia lucida is not in the palette; a generic dry shrub only."),
'ph_wild_rooibos_bush': ('D', 'real_leaves', 'none', [], "Looked at: foliage renders near-black at 5 m and 15 m under this sun; a set of five small bushes. Not usable as authored."),
'ph_periwinkle_plant': ('C', 'real_leaves', 'none', [], "Looked at: set of small sprawling plants 0.3 m with tiny flowers; instanced as a 3 m drift it is still thin and vanishes at 15 m (drift test). Not in the palette."),
'ph_flower_gazania': ('B', 'real_leaves+flowers', 'genus', ['gazania_rigens'], "Looked at: the single asset is a 4-plant set 0.3 m, tiny at 5 m and 15 m (grade C alone). DRIFT TEST (70 instances over 3 m, drift_preview.py): at 5 m it reads as an orange-flowered gazania groundcover drift; at 15 m a 3 m patch is a thin line, so use drifts of 6 m and wider. B for instanced drift use only; genus Gazania (source names no species)."),
'ph_grass_bermuda_01': ('C', 'real_leaves', 'species', [], "Looked at: set of separate dark grass tufts. DRIFT TEST (400 instances over 4 m): scattered dark tufts, not turf, at 5 m; a grey smudge at 15 m. Not usable as lawn."),
'ph_bananas': ('C', 'none', 'none', [], "Looked at: a hand of banana FRUIT (0.6 m), not a plant. No use for Musa foliage."),
'ph_food_pomegranate_01': ('C', 'none', 'none', [], "Looked at: a single pomegranate fruit (about 10 cm), a dot at 5 m. Fruit only, not a tree."),
}
op = urllib.request.build_opener(); op.addheaders = [('User-Agent', 'Mozilla/5.0')]
for k, (g, lt, fit, maps, rat) in G.items():
    a = k[3:]; s = st[k]
    shutil.copy(f'/tmp/ldl/sheets/{k}.jpg', P + f'asset-previews/{k}.jpg')
    au = json.load(op.open(f'https://api.polyhaven.com/info/{a}'))['authors']
    doc['assets'].append(dict(id=k, source=f'https://polyhaven.com/a/{a}', licence='CC0', author=', '.join(au),
        title=a.replace('_', ' ').title() + ' (Poly Haven, 1k glTF from shared store)', triangles=s['triangles'], size_m=s['size_m'],
        alpha_card_tri_share=s['alpha_card_tri_share'], preview=f'asset-previews/{k}.jpg', grade=g, leaf_type=lt, species_fit=fit,
        maps_to=maps, rationale=rat, storage='shared', manifest_key='polyhaven/' + a))
shutil.copy('/tmp/ldl/sheets/ph_flower_gazania_drift.jpg', P + 'asset-previews/ph_flower_gazania_drift.jpg')
for a in doc['assets']:
    if a['id'] == 'ph_flower_gazania': a['drift_preview'] = 'asset-previews/ph_flower_gazania_drift.jpg'
    if a['id'] == 'jacaranda_tree':
        a['misnamed_as'] = 'jacaranda_mimosifolia'
        a['identity_note'] = "Library name 'jacaranda_tree' is wrong: broad lobed (maple/oak-like) leaves, genus unidentified. Not a Jacaranda; the real one is sf_jacaranda."
    if a['id'] == 'skf_fd421074':
        a['defect'] = {'cause': 'no textures in the exported glTF: images and textures absent and no baseColorFactor, so every material falls back to white',
                       'also': "the model is a mixed Ravenala (traveller's palm) and banana-leaf plant in pots, not a banana", 'fix': 'none from this file; re-export with textures from the author or replace'}
        a['untextured_material_share'] = 1.0
rows = {r['slug']: r for r in doc['species']}
rows['gazania_rigens'].update(best_asset='ph_flower_gazania', grade='B', drawable='drawable')
rows['cynodon_dactylon'].update(best_asset='ph_grass_bermuda_01', grade='C', drawable='not drawable yet')
doc['sketchfab_candidates'] = 'knowledge/landscape/plants/sketchfab-candidates.json: downloadable CC0/CC-BY models, ungraded; download needs a Sketchfab API token that does not exist on this machine (HTTP 401)'
json.dump(doc, open(P + 'assets.json', 'w'), indent=1, ensure_ascii=False)
man = {}
for m in json.load(open('/tmp/ldl/ph_manifest.json')):
    man.setdefault('polyhaven/' + m['asset'], []).append(dict(file=m['file'], sha256=m['sha256'], url=m['url']))
json.dump({'root': '~/archpipe/shared/assets/user/landscape/polyhaven/<asset>/', 'note': 'binaries are NOT in git; every file is pinned by sha256',
           'licences': {'polyhaven': 'CC0 1.0 (https://polyhaven.com/license)'}, 'assets': man}, open(P + 'asset-manifest.json', 'w'), indent=1)
print(len(doc['assets']))
