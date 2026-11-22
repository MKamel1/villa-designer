"""Download CC0 / CC-BY Sketchfab plant candidates (licence re-read from the API at download time).

    python -m archpipe.landscape.plants.tools.fetch_plants [--max-faces N] [--per-species K] [slug ...]

Token: ~/archpipe/lead/sketchfab-api.txt (never printed). Binaries go to
~/archpipe/shared/assets/user/landscape/sketchfab/<uid>/ (outside git); the repo records
knowledge/landscape/plants/sketchfab-manifest.json (sha256, licence, author, url; CC-BY needs attribution).
"""
import hashlib, json, sys, time, urllib.request, zipfile
from pathlib import Path

P = Path('knowledge/landscape/plants')
OUT = Path.home() / 'archpipe/shared/assets/user/landscape/sketchfab'
TOKEN = Path.home() / 'archpipe/lead/sketchfab-api.txt'
API = 'https://api.sketchfab.com/v3/models/'
OK = {'CC0 Public Domain', 'CC Attribution'}
PRIORITY = ['punica_granatum', 'jasminum_sambac', 'petrea_volubilis', 'justicia_brandegeeana', 'acorus_gramineus',
            'alpinia_zerumbet', 'fatsia_japonica', 'aspidistra_elatior', 'origanum_majorana', 'rosmarinus_officinalis',
            'pennisetum_alopecuroides', 'salvia_leucantha', 'phoenix_roebelenii', 'bougainvillea_glabra', 'pittosporum_tobira']


def get(url, auth=False):
    h = {'User-Agent': 'archpipe-asset-fetch/1'}
    if auth:
        h['Authorization'] = 'Token ' + TOKEN.read_text().strip()
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < 3:
                time.sleep(20 * (i + 1)); continue
            raise


def main(argv):
    mx, per = 1_700_000, 2
    slugs = []
    it = iter(argv)
    for a in it:
        if a == '--max-faces': mx = int(next(it))
        elif a == '--per-species': per = int(next(it))
        else: slugs.append(a)
    cands = json.load(open(P / 'sketchfab-candidates.json'))
    slugs = slugs or PRIORITY + [s for s in cands if s not in PRIORITY]
    mf = P / 'sketchfab-manifest.json'
    man = json.load(open(mf)) if mf.is_file() else {}
    for slug in slugs:
        # species-named first, then fewest faces; skip multi-plant packs/fruit-only by name below
        lst = sorted(cands.get(slug, []), key=lambda c: (c['match'] != 'species', c['faces']))
        got = 0
        for c in lst:
            if got >= per: break
            if c['faces'] > mx or c['faces'] < 500 or c['uid'] in man: continue
            meta = json.loads(get(API + c['uid']))
            lic = (meta.get('license') or {}).get('label')
            if lic not in OK or not meta.get('isDownloadable'):
                man[c['uid']] = dict(species=slug, status='licence-rejected', licence=lic, name=meta.get('name')); print('REJECT', slug, c['uid'], lic); continue
            links = json.loads(get(API + c['uid'] + '/download', True))
            pkg = links.get('gltf')
            if not pkg:
                man[c['uid']] = dict(species=slug, status='no-gltf', licence=lic); continue
            dest = OUT / c['uid']; dest.mkdir(parents=True, exist_ok=True)
            z = dest / 'pkg.zip'; z.write_bytes(get(pkg['url']))
            with zipfile.ZipFile(z) as zf: zf.extractall(dest)
            z.unlink()
            files = {str(f.relative_to(dest)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dest.rglob('*')) if f.is_file()}
            man[c['uid']] = dict(species=slug, status='downloaded', name=meta['name'], licence=lic, author=meta['user']['username'],
                                 url=meta['viewerUrl'], faces=meta.get('faceCount'), match=c['match'], files=files)
            got += 1; print('OK', slug, c['uid'], lic, meta.get('faceCount'))
            json.dump(man, open(mf, 'w'), indent=1, ensure_ascii=False)
            time.sleep(1)
    json.dump(man, open(mf, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main(sys.argv[1:])
