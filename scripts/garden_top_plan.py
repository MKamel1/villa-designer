"""Preview measured G3 garden geometry on plan without invoking a renderer.

Run with PYTHONPATH=src. Output is a diagnostic schematic, not appearance
approval; the lead must render/review the fixed design before integration.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from archpipe.concept import villa_landscape as L, revit_spec as RS, villa_r11 as R


def main():
    meshes, props, _, plan = L.review_candidate(RS.build(R.design('D1')))
    if plan['conflicts']:
        raise ValueError(plan['conflicts'])
    fig, ax = plt.subplots(figsize=(15, 6))
    for rect in (L.DECK, L.ROOF):
        ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fill=False, lw=2))
        inner = (rect[0]+L.RAIL_CLEAR, rect[1]+L.RAIL_CLEAR,
                 rect[2]-rect[0]-2*L.RAIL_CLEAR, rect[3]-rect[1]-2*L.RAIL_CLEAR)
        ax.add_patch(Rectangle(inner[:2], inner[2], inner[3], fill=False, ls=':', ec='red'))
    for mesh in meshes:
        if mesh['id'].startswith('landscape-grass-top'):
            for face in mesh['faces']:
                ax.add_patch(Polygon([q[:2] for q in face], fc='#b9cb9b', ec='none'))
        if mesh.get('part_kind') == 'bench-slab':
            rect = L._rect(mesh)
            ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fc='#ded7c8'))
    for name in ('study', 'gate-link'):
        rect = plan['paths'][name]
        ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fc='#f1d48d', alpha=.55))
        ax.text((rect[0]+rect[2])/2, (rect[1]+rect[3])/2, name, ha='center',
                rotation=90 if name == 'study' else 0)
    for trough in plan['top_troughs']:
        rect = trough['rect']
        ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fc='#655042'))
        for plant in (m for m in meshes if m.get('species') and m.get('trough') == trough['id']):
            # Hulls show actual shoot/leaf bounds, including inward trails.
            from shapely.geometry import MultiPoint
            hull = MultiPoint([q[:2] for f in plant['faces'] for q in f]).convex_hull
            ax.add_patch(Polygon(list(hull.exterior.coords), fc='#4e8054', alpha=.5, zorder=4))
        ax.text((rect[0]+rect[2])/2, (rect[1]+rect[3])/2,
                trough['species'].split()[0]+' x3', color='white', ha='center', va='center', fontsize=8, zorder=5)
    for seating in plan['top_benches']:
        bench = next(p for p in props if p['id'] == seating['id'])
        rect = L._rect(bench)
        ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fc='#8d6641'))
        knee = seating['knee_rect']
        ax.add_patch(Rectangle(knee[:2], knee[2]-knee[0], knee[3]-knee[1], fill=False, ls='--', ec='#516aa4'))
        ax.text((knee[0]+knee[2])/2, (knee[1]+knee[3])/2,
                '0.60 m\nknee space\nASSUMED', ha='center', va='center', fontsize=8)
    for plant in props:
        if plant.get('zone') == 'top' and plant.get('species'):
            ax.add_patch(plt.Circle(plant['center'], .259, color='#bd6a42'))
            rect = L._rect(plant)
            ax.add_patch(Rectangle(rect[:2], rect[2]-rect[0], rect[3]-rect[1], fill=False, ec='#b56a42', ls='--'))
            ax.text(*plant['center'], 'Ixora', ha='center', va='center', fontsize=8)
    route = plan['gate_route']
    ax.add_patch(Rectangle((route['profile'][0][0], route['y0']),
                          L.DECK[0]-route['profile'][0][0], route['y1']-route['y0'],
                          fc='#eeeeee', ec='#999999', ls='--'))
    ax.text(3.3, -22.10, 'UNCHANGED DRIVEWAY\nreserved 0.914 m walking strip\nD2 envelope follows slope',
            ha='center', va='center', fontsize=8)
    ax.plot([7.377, 9.177], [-23.591, -23.591], color='blue', lw=4)
    ax.text(8.277, -23.85, '1.80 m existing study slider', ha='center', color='blue')
    ax.set_xlim(-.4, 15.8); ax.set_ylim(-24.3, -20.2); ax.set_aspect('equal')
    ax.set_xlabel('Scene x, metres'); ax.set_ylabel('Scene y, metres')
    ax.set_title('G3 top garden plan preview: '+L.TROUGH_COLOUR['name']+
                 '\nGround-floor scene z = 0; street +1.20 m. Red dotted lines: rail strip. '
                 'Nursery/roots, weathering and loaded weight UNVERIFIED.')
    fig.tight_layout()
    path = Path(__file__).resolve().parents[1] / 'out/garden-g3-plan.png'
    fig.savefig(path, dpi=150)
    print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
