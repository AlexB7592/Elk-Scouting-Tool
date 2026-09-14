"""Auto-Scout step 4 of 4: the surface the app draws, and the ranked areas.

SURFACE  every public cell ranked against every other, one byte (0 worst .. 255
         best). The app shades the top N% by comparing against a threshold, so
         the slider means "the best quarter of the unit", never a probability.

AREAS    Thresholding the top 5% and taking connected blobs produced a 1,194-acre
         "area" 5.8 miles across spanning 1,600 vertical feet, with a boundary
         that moved whenever the threshold did. Instead: smooth the surface,
         pick the 8 highest peaks at least 2.4 km apart, and grow each outward
         in score order to 320 acres -- about a day on foot. The cap is a design
         decision: an area you cannot walk is not a scouting result.

Each area carries its own evidence so the app can say why it ranks, including
when nothing corroborates it: overlap with the old hotspot layer, walk-in time,
and how much of it sits within 600 m of a developed trail.

Reads  WORK/as_score.npy, as_parts.npy, access_hours.npy, trail_dist.npy,
       hotspot_tier.npy, reference.json
       grids/elev_grid, forage_grid, canopy_grid, roaddist_grid, ownership_grid
Writes grids/autoscout_grid.png
       data/vectors/scout_areas.geojson
"""
import os, json, heapq, numpy as np, rasterio, warnings
warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter
from unit import REPO, EW, EH, LON0, LAT0, LON1, LAT1, SLUG, CELL_X_M, CELL_Y_M

WORK = os.path.expanduser('~/gmu44-scratch/work/autoscout')
G = os.path.join(REPO, 'grids')
CX, CY = (17.2, 22.1) if SLUG == 'gmu44' else (CELL_X_M, CELL_Y_M)
H, W = EH, EW
CELL_AC = CX*CY/4046.86
FNAME = {0: 'none', 1: 'Meadow & park', 2: 'Aspen', 3: 'Shrub & oak',
         4: 'Open conifer', 5: 'Dense conifer', 6: 'Alpine'}
TARGET_AC, MIN_SEP_M, N_AREAS = 320.0, 2400.0, 8

score = np.load(os.path.join(WORK, 'as_score.npy'))
bed, feed, water, sec = np.load(os.path.join(WORK, 'as_parts.npy'))
with rasterio.open(os.path.join(G, 'elev_grid.png')) as ds:
    Eft = (ds.read(1).astype(np.float32)*256 + ds.read(2).astype(np.float32))*0.25
forage = rasterio.open(os.path.join(G, 'forage_grid.png')).read(1)
canopy = rasterio.open(os.path.join(G, 'canopy_grid.png')).read(1)
roadm  = rasterio.open(os.path.join(G, 'roaddist_grid.png')).read(1)*25.0
own    = rasterio.open(os.path.join(G, 'ownership_grid.png')).read(1)

# ---- areas: peaks, then grow each to a day's worth of ground ------------------
sm = uniform_filter(score, size=(int(400/CY)*2+1, int(400/CX)*2+1), mode='nearest')
sm[own == 2] = 0
peaks = []; work = sm.copy()
sepr, sepc = int(MIN_SEP_M/CY), int(MIN_SEP_M/CX)
for _ in range(N_AREAS):
    idx = int(np.argmax(work)); r, c = divmod(idx, W)
    if work[r, c] <= 0:
        break
    peaks.append((r, c, float(sm[r, c])))
    work[max(0, r-sepr):r+sepr+1, max(0, c-sepc):c+sepc+1] = 0

def grow(seed_r, seed_c, target_cells, claimed):
    """Flood outward from the peak, always taking the best cell on the frontier."""
    got = []; seen = {(seed_r, seed_c)}
    pq = [(-score[seed_r, seed_c], seed_r, seed_c)]
    while pq and len(got) < target_cells:
        _, r, c = heapq.heappop(pq)
        if claimed[r, c] or own[r, c] == 2:
            continue
        got.append((r, c)); claimed[r, c] = True
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r+dr, c+dc
            if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in seen and not claimed[nr, nc]:
                seen.add((nr, nc)); heapq.heappush(pq, (-score[nr, nc], nr, nc))
    return got

claimed = np.zeros((H, W), bool)
target_cells = int(TARGET_AC/CELL_AC)
areas = []
for rank, (pr, pc, pv) in enumerate(peaks, 1):
    cells = grow(pr, pc, target_cells, claimed)
    if len(cells) < target_cells*0.5:
        continue
    ys = np.array([a for a, _ in cells]); xs = np.array([b for _, b in cells])
    ft = Eft[ys, xs]
    span = max((ys.max()-ys.min())*CY, (xs.max()-xs.min())*CX)/1609.34
    top = int(np.bincount(forage[ys, xs], minlength=7).argmax())
    areas.append(dict(
        rank=rank, cells=cells, acres=len(cells)*CELL_AC, span_mi=span,
        lat=float(LAT0+ys.mean()/(H-1)*(LAT1-LAT0)),
        lon=float(LON0+xs.mean()/(W-1)*(LON1-LON0)),
        ft_lo=float(ft.min()), ft_hi=float(ft.max()), ft_mean=float(ft.mean()),
        canopy=float(canopy[ys, xs].mean()), road_m=float(roadm[ys, xs].mean()),
        forage=FNAME[top],
        bed=float(bed[ys, xs].mean()), feed=float(feed[ys, xs].mean()),
        water=float(water[ys, xs].mean()), sec=float(sec[ys, xs].mean()),
        score=float(score[ys, xs].mean())))
areas.sort(key=lambda a: -a['score'])
for i, a in enumerate(areas, 1):
    a['rank'] = i
cells_arr = np.array([[r, c, a['rank']] for a in areas for r, c in a['cells']])
np.save(os.path.join(WORK, 'as_areas_cells.npy'), cells_arr)
json.dump([{k: v for k, v in a.items() if k != 'cells'} for a in areas],
          open(os.path.join(WORK, 'as_areas.json'), 'w'), indent=1)

# ---- the surface the app draws -------------------------------------------------
pub = own != 2
flat = score[pub]; order = np.argsort(flat)
ranks = np.empty_like(order, dtype=np.float64); ranks[order] = np.arange(len(flat))
pct = np.zeros(score.shape); pct[pub] = ranks/max(1, len(flat)-1)
byte = np.clip(np.round(pct*255), 0, 255).astype(np.uint8); byte[~pub] = 0
gout = os.path.join(G, 'autoscout_grid.png')
with rasterio.open(gout, 'w', driver='PNG', width=W, height=H, count=1, dtype='uint8') as ds:
    ds.write(byte, 1)

# ---- the areas the app draws, each carrying its own evidence --------------------
cells = np.load(os.path.join(WORK, 'as_areas_cells.npy'))
meta  = json.load(open(os.path.join(WORK, 'as_areas.json')))
tier  = np.load(os.path.join(WORK, 'hotspot_tier.npy'))
acc   = np.load(os.path.join(WORK, 'access_hours.npy'))
td    = np.load(os.path.join(WORK, 'trail_dist.npy'))
has_ref = json.load(open(os.path.join(WORK, 'reference.json')))['has_reference']

def ll(r, c):
    return [round(LON0+c/(W-1)*(LON1-LON0), 6), round(LAT0+r/(H-1)*(LAT1-LAT0), 6)]
feats = []
for m in meta:
    sel = cells[cells[:, 2] == m['rank']]; ys, xs = sel[:, 0], sel[:, 1]
    mask = np.zeros((H, W), np.float32); mask[ys, xs] = 1
    r0 = max(0, ys.min()-2); r1 = min(H, ys.max()+3)
    c0 = max(0, xs.min()-2); c1 = min(W, xs.max()+3)
    sub = mask[r0:r1, c0:c1]
    if sub.shape[0] < 2 or sub.shape[1] < 2:
        continue
    fig = plt.figure(); cs = plt.contour(sub, levels=[0.5]); plt.close(fig)
    rings = []
    for pth in cs.allsegs[0]:
        if len(pth) < 10:
            continue
        ring = [ll(r0+y, c0+x) for x, y in pth[::2]]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        if len(ring) >= 5:
            rings.append(ring)
    if not rings:
        continue
    rings.sort(key=len, reverse=True)
    t = tier[ys, xs]; h = float(np.median(acc[ys, xs])); d = td[ys, xs]
    p = {k: v for k, v in m.items()}
    p['acres'] = round(p['acres']); p['span_mi'] = round(p['span_mi'], 2)
    for f in ('ft_lo', 'ft_hi', 'ft_mean', 'road_m', 'canopy'):
        p[f] = round(p[f])
    for f in ('bed', 'feed', 'water', 'sec', 'score'):
        p[f] = round(p[f], 3)
    p['on_hotspot_pct'] = round(100*float((t > 0).mean()))
    p['on_red_pct'] = round(100*float((t == 3).mean()))
    p['walk_h'] = round(h, 1); p['round_h'] = round(h*2, 1)
    p['trail_pct'] = round(100*float((d < 600).mean()))
    if not has_ref:
        p['confidence'] = 'no reference layer for this unit'
    else:
        p['confidence'] = ('agrees with the old hotspot layer' if p['on_hotspot_pct'] >= 70
                           else 'partly corroborated' if p['on_hotspot_pct'] >= 50
                           else 'untested — the old layer does not rate this')
    feats.append({'type': 'Feature', 'properties': p,
                  'geometry': {'type': 'Polygon', 'coordinates': [rings[0]]}})
aout = os.path.join(REPO, 'data', 'vectors', 'scout_areas.geojson')
json.dump({'type': 'FeatureCollection', 'features': feats}, open(aout, 'w'))
print('%d areas' % len(feats))
for f in feats:
    q = f['properties']
    print('  %d  %-14s %.1f h round trip  %2d%% trail  %3d%% on old layer  %s' % (
        q['rank'], q['forage'], q['round_h'], q['trail_pct'], q['on_hotspot_pct'], q['confidence']))
