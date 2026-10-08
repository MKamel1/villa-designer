"""Rebuild measured naming/solar evidence without a renderer or shared writes."""
import gzip
import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from archpipe import orientation as O,solar,villa_env as E
from archpipe.orientation_guard import scene_findings,document_findings
from archpipe.concept import villa_render as V,villa_landscape as L,villa_r11 as R
from archpipe.concept.garden_sun import SunStudy,DATES,scene_findings as sun_findings
from archpipe.concept.render_support import unsupported,blocked_openings

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out/orientation'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    scene=V.build();study=SunStudy(scene)
    frozen=json.loads(gzip.decompress((ROOT/'tests/fixtures/orientation-before.json.gz').read_bytes()))
    reference=json.loads((ROOT/'tests/fixtures/orientation-sun-reference.json').read_text())
    scope=dict(solar=solar,datetime=datetime,timezone=timezone,E=E,BUILDING_HEIGHT=3,inside_yard=L.inside_yard,
               sin=math.sin,cos=math.cos,radians=math.radians,tan=math.tan)
    exec(frozen['legacy_sun_source'],scope)
    zones={
        'north open':(-.123,-28.671,3.617,-23.591),
        'north balcony':(-.123,E.AXIS_Y/1000,3.617,-28.671),
        'east sunken':(15.412,-23.591,22.597,-20.601),
        'south rear':(22.597,E.AXIS_Y/1000,28.307,-20.601),
        # Sample the actual usable deck inside its recorded assumed rail strip.
        'top deck':(L.TOP[0]+L.RAIL_CLEAR,L.TOP[1]+L.RAIL_CLEAR,L.TOP[2]-L.RAIL_CLEAR,L.TOP[3]-L.RAIL_CLEAR)}
    results={}
    for name,rect in zones.items():
        ground=0 if name=='top deck' else -3
        points=[(float(x),float(y)) for x in np.arange(rect[0]+.5,rect[2],1) for y in np.arange(rect[1]+.5,rect[3],1)]
        samples=[dict(point_m=[x,y,ground+.05],days={d:study.hours(x,y,ground,d) for d in DATES},legacy_june_hours=scope['direct_sun_hours'](x,y)) for x,y in points]
        results[name]=dict(rect_m=rect,sample_count=len(points),samples=samples,
            means={d:float(np.mean([len(s['days'][d]) for s in samples])) for d in DATES},
            legacy_june_mean=float(np.mean([len(s['legacy_june_hours']) for s in samples])))
    tolerance=.5
    comparisons=[dict(zone='north open',day=DATES[0],lead=reference['NORTH garden (street side), open part'][1]['21 Jun'][1]),
                 dict(zone='south rear',day=DATES[0],lead=reference['SOUTH garden (rear)'][1]['21 Jun'][1]),
                 dict(zone='south rear',day=DATES[2],lead=reference['SOUTH garden (rear)'][1]['21 Dec'][1])]
    for c in comparisons:
        c['measured']=results[c['zone']]['means'][c['day']];c['difference']=abs(c['measured']-c['lead']);c['passed']=c['difference']<=tolerance
    acceptance=dict(unsupported=unsupported(scene),blocked_openings=blocked_openings(scene,R.design('D1')),
                    naming=scene_findings(scene),documents=document_findings(),sun_evidence=sun_findings(scene),
                    tolerance_hours=tolerance,lead_comparisons=comparisons)
    (OUT/'scene.json').write_text(json.dumps(scene)+'\n')
    report=dict(schema='orientation-sun-report/1',orientation=O.record(),
                geometry_sha256=study.geometry_sha256,dates=DATES,timezone='UTC+02:00',step_hours=1,
                sun_above_horizon_only=True,surface_offset_m=.05,latitude_deg=E.LATITUDE,longitude_deg=E.LONGITUDE,
                reference_source='out/villa/garden-sun-hours.json (lead 2026-10-06)',
                reference_sha256=hashlib.sha256((ROOT/'tests/fixtures/orientation-sun-reference.json').read_bytes()).hexdigest(),
                reference_limits='Lead point coordinates and sampling phase were not supplied; means are independently resampled, not exact replay.',
                zones=results,plants=scene['garden_sun_evidence']['plants'],acceptance=acceptance)
    (OUT/'sun-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
    lines=['# Client orientation naming and actual-scene sun hours','',
           '2026-10-06. No render, commit, native-model change or protected shared-data write. The authoritative record is [site-orientation.json](../knowledge/site-orientation.json).',
           '', '| Model direction | Client name | Garden |','|---|---|---|',
           '| −x | north | Street-side sunken garden; ground-floor balcony and open part |',
           '| +y | east | Ramp, top deck and open sunken yard |',
           '| +x | south | Rear lawn with frangipani |','| −y | west | Sister side |','',
           'Model x and y are horizontal scene coordinates in metres; z is elevation in metres, with ground-floor finished level at zero. IDs means identifiers; UTC means Coordinated Universal Time; RHS means Royal Horticultural Society. True model +y bearing remains 20 degrees clockwise from true north; the street facade true azimuth remains 290 degrees. These are solar/sun inputs only. No sun bearing rotates because of the naming change.',
           '', 'The guard checks landscape IDs (including one-letter side tokens), actual bed/route centroids, garden view IDs, labels, titles and every compass word in captions. Top trough edge names use the local top-garden centre. Paired pot end suffixes use the measured local axis order. Garden report coordinate tables and explicit model-axis statements are checked in portable verification; other narrative is bound to recorded reviewed hashes so an edit requires renewed naming review. The frozen committed street-side `landscape-bed-west` and `v36-west-court` fail; renamed/translated siblings and mutations also fail, while the corrected geometry stays quiet.',
           '', 'Actual landscape faces, asset transforms, materials and camera coordinates are preserved. Climber appearance seeds preserve the legacy deterministic foliage distribution. Frozen fixtures and historical approval coordinates remain unchanged; consumers migrate their identifiers explicitly through the recorded aliases. The route archive is keyed by native asset identities, not placement IDs, so `knowledge/asset-route-geometry.json.gz` is unchanged.',
           '', 'Sun rays use the final actual scene’s opaque building, context and architectural ground, including the house, four-metre basement-level fence and twelve-metre neighbours. Glass/translucent surfaces, plants and furniture are excluded. Sampling is at 50 mm above lower ground or deck, at each local standard clock hour when the sun is above the horizon, on 21 June, 20 March and 21 December 2026. Local standard time is UTC+02:00; latitude and longitude come from villa_env. True azimuth subtracts the recorded 20-degree model-Y bearing before conversion to model direction.',
           '', 'Comparison tolerance was declared as 0.5 hour: half the one-hour step. The lead file gives counts and rounded means but no point coordinates or sampling phase; this is an independent resampling comparison. The machine-readable report records every coordinate, date and visible hour. The balcony sample covers only our own half of the shared twin strip (four grid points); the lead counted eight points without disclosing their positions. Top samples remain inside the recorded rail-clear strip. It is a geometric enclosure screen, not weather-weighted plant illuminance or nursery approval.',
           '', '| Zone | Points | June mean, hours | March mean, hours | December mean, hours | Old proxy June mean, hours |','|---|---:|---:|---:|---:|---:|']
    for name,row in results.items():lines.append('| %s | %d | %.3f | %.3f | %.3f | %.3f |'%(name,row['sample_count'],*(row['means'][d] for d in DATES),row['legacy_june_mean']))
    lines += ['', '| Required independent comparison | Measured hours | Lead hours | Difference hours | Pass at 0.5 h |','|---|---:|---:|---:|---|']
    for c in comparisons:lines.append('| %s, %s | %.3f | %.1f | %.3f | %s |'%(c['zone'],c['day'],c['measured'],c['lead'],c['difference'],c['passed']))
    lines += ['', 'Every planted species is checked below, including both climbers. Ranges are per actual plant sampling point; the full JSON preserves individual dates and hours. The RHS midsummer full-sun definition in the sole palette is strictly more than six hours; quoted best-flowering preferences are distinguished from tolerance of some shade. Missing quotes remain UNVERIFIED. Direct rays at ground do not measure neighbouring foliage shade, so indirect-light suitability remains unresolved where rays reach an Aspidistra. Retained placement is unchanged; newly found mismatch is not a waiver or a nursery acceptance.',
              '', '| Species / actual zone | June hours | March hours | December hours | June quote applicability / seasonal limits |','|---|---|---|---|---|']
    plants=report['plants']
    for species,zone in sorted({(r['species'],r['zone']) for r in plants}):
        rows=[r for r in plants if r['species']==species and r['zone']==zone]
        ranges=['%d–%d'%(min(len(r['sunlit_local_standard_hours'][d]) for r in rows),max(len(r['sunlit_local_standard_hours'][d]) for r in rows)) for d in DATES]
        statuses=', '.join(sorted({r['status'] for r in rows}));reasons=' '.join(sorted({r['reason'] for r in rows if r['reason']}))+' '+' '.join(sorted({r['seasonal_limits'] for r in rows if r['seasonal_limits']}))
        lines.append('| [%s](%s) / %s | %s | %s | %s | %s. %s |'%(species,rows[0]['source_url'],zone,*ranges,statuses.replace('_',' '),reasons))
    lines += ['', 'Species source quotes and statuses remain in [garden-palette.json](../knowledge/garden-palette.json); the output records the exact quote joined to every plant. Cairo performance, leaf-level seasonal light and nursery/root/structural decisions remain unresolved.',
              '', 'Reproduce with `PYTHONPATH=src python scripts/orientation_naming_report.py`. [Measured evidence](../out/orientation/sun-report.json), [acceptance](../out/orientation/acceptance.json), and [current generated scene](../out/orientation/scene.json). Actual unsupported and blocked-opening lists: '+json.dumps({k:acceptance[k] for k in ('unsupported','blocked_openings')})+'.',
              '', 'Renamed current IDs and subject prefixes (historical removed assemblies also have explicit aliases in the record):','', '| Old ID | New ID |','|---|---|']
    current_old=set()
    def collect(v):
        if isinstance(v,dict):
            for k,item in v.items():collect(k);collect(item)
        elif isinstance(v,list):
            for item in v:collect(item)
        elif isinstance(v,str) and v in O.record()['legacy_aliases']:current_old.add(v)
    collect(frozen)
    for old in sorted(current_old):lines.append('| `%s` | `%s` |'%(old,O.record()['legacy_aliases'][old]))
    status_path=OUT/'verify-status.json'
    if status_path.exists():
        statuses=json.loads(status_path.read_text())
        lines += ['', 'Portable verification: normal exit '+str(statuses['normal_exit'])+', fresh empty-HOME exit '+str(statuses['empty_home_exit'])+'; HOME verified empty before launch: '+str(statuses['home_initially_empty'])+'. Logs: [normal](../out/orientation/verify-normal-final.log), [empty HOME](../out/orientation/verify-empty-home-final.log).']
    lines += ['', '| Legacy zone/route/edge | Current name |','|---|---|']
    for old,new in {**O.record()['legacy_zone_aliases'],**O.record()['legacy_fragment_aliases']}.items():lines.append('| `%s` | `%s` |'%(old,new))
    (ROOT/'docs/orientation-naming-report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(acceptance))
    return int(any(acceptance[k] for k in ('unsupported','blocked_openings','naming','documents','sun_evidence')) or not all(c['passed'] for c in comparisons))

if __name__=='__main__':raise SystemExit(main())
