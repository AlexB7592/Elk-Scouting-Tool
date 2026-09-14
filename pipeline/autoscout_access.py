"""Auto-Scout step 2 of 4: how reachable and how pressured every cell is.

Two lessons are built into this, both learned the hard way on 2026-09-10/11:

1. Reward REACHABILITY, not remoteness. The first version scored straight-line
   distance from a road with no ceiling, and two of its eight areas came out at
   12.5 h and 10.2 h round trip on foot. This scores real walking time and peaks
   across the band a hunter can work: 0 at the roadside where the pressure is,
   full marks from ~1.5 to 3 h in, back to 0 by 5 h.

2. Trails are pressure. Hunters drive to a road and then walk trails fast, so
   trails go into the travel cost at 0.55x the terrain multiplier. Walking time
   alone still cannot see a trail through an area -- the trail makes it FASTER
   to reach, which read as ideal -- so a separate corridor term penalises ground
   within 600 m of a developed trail, fully within 120 m. Three of the first
   eight areas sat entirely inside a trail corridor before this.

Reads  grids/elev_grid.png, terrain_mult_grid.png, roaddist_grid.png
       data/vectors/trails.geojson
Writes WORK/trail_dist.npy      metres to the nearest trail
       WORK/access_hours.npy    one-way hours on foot from the nearest road
       WORK/access_usable.npy   0..1, reachable x not in a trail corridor
"""
import os, json, math, heapq, numpy as np, rasterio, warnings
warnings.filterwarnings('ignore')
from scipy.ndimage import distance_transform_edt
from unit import REPO, EW, EH, LON0, LAT0, LON1, LAT1, SLUG, CELL_X_M, CELL_Y_M

WORK = os.path.expanduser('~/gmu44-scratch/work/autoscout')
os.makedirs(WORK, exist_ok=True)
G = os.path.join(REPO, 'grids')
H, W = EH, EW
# GMU 44 was built with these rounded cell sizes and the committed outputs depend
# on them. Any other unit uses the computed values from unit.py.
CX, CY = (17.2, 22.1) if SLUG == 'gmu44' else (CELL_X_M, CELL_Y_M)

TRAIL_MULT = 0.55                    # trail vs bushwhacking, as a terrain multiplier
TRAIL_FULL, TRAIL_FADE = 120.0, 600.0
def usable(h, a=0.35, b=1.25, c=3.0, d=5.0):
    """0 at the road, 1 across a workable walk-in, back to 0 where the round
    trip eats the day. Hours, one way."""
    return np.clip((h-a)/(b-a), 0, 1) * np.clip((d-h)/(d-c), 0, 1)

# ---- 1. distance to the nearest trail ----------------------------------------
grid = np.zeros((H, W), bool)
def burn(coords):
    pts = []
    for lo, la in coords:
        pts.append(((la-LAT0)/(LAT1-LAT0)*(H-1), (lo-LON0)/(LON1-LON0)*(W-1)))
    for i in range(1, len(pts)):
        r0, c0 = pts[i-1]; r1, c1 = pts[i]
        n = int(max(abs(r1-r0), abs(c1-c0))) + 1
        for k in range(n+1):
            r = int(round(r0+(r1-r0)*k/n)); c = int(round(c0+(c1-c0)*k/n))
            if 0 <= r < H and 0 <= c < W:
                grid[r, c] = True
trails = json.load(open(os.path.join(REPO, 'data', 'vectors', 'trails.geojson')))
for f in trails['features']:
    g = f['geometry']
    if g['type'] == 'LineString':
        burn(g['coordinates'])
    elif g['type'] == 'MultiLineString':
        for part in g['coordinates']:
            burn(part)
td = distance_transform_edt(~grid, sampling=(CY, CX)).astype(np.float32)
np.save(os.path.join(WORK, 'trail_dist.npy'), td)
print('trails: %d cells, median %.0f m to the nearest' % (grid.sum(), np.median(td)))

# ---- 2. one-way walking time from the nearest road ---------------------------
with rasterio.open(os.path.join(G, 'elev_grid.png')) as ds:
    E = (ds.read(1).astype(np.float64)*256 + ds.read(2).astype(np.float64))*0.25   # feet
tm = rasterio.open(os.path.join(G, 'terrain_mult_grid.png')).read(1).astype(np.float64)
roadm = rasterio.open(os.path.join(G, 'roaddist_grid.png')).read(1)*25.0
mult = 1.0*np.exp((tm/255.0)*math.log(12.0/1.0))
mult = np.where(td <= 25.0, np.minimum(mult, TRAIL_MULT), mult)

NB = [(-1, 0, CY), (1, 0, CY), (0, -1, CX), (0, 1, CX),
      (-1, -1, math.hypot(CX, CY)), (-1, 1, math.hypot(CX, CY)),
      (1, -1, math.hypot(CX, CY)), (1, 1, math.hypot(CX, CY))]
INF = 1e18
dist = np.full((H, W), INF); pq = []
ys, xs = np.where(roadm <= 25.0)
for r, c in zip(ys, xs):
    dist[r, c] = 0.0; pq.append((0.0, r, c))
heapq.heapify(pq)
while pq:
    d, r, c = heapq.heappop(pq)
    if d > dist[r, c]:
        continue
    ez = E[r, c]
    for dr, dc, dm in NB:
        nr, nc = r+dr, c+dc
        if nr < 0 or nr >= H or nc < 0 or nc >= W:
            continue
        dz = (E[nr, nc]-ez)*0.3048
        spd = 6.0*math.exp(-3.5*abs(dz/dm+0.05))        # Tobler, km/h
        if spd < 0.05:
            spd = 0.05
        nd = d + (dm/1000.0)/spd*mult[nr, nc]
        if nd < dist[nr, nc]:
            dist[nr, nc] = nd; heapq.heappush(pq, (nd, nr, nc))
acc = dist.astype(np.float32)
np.save(os.path.join(WORK, 'access_hours.npy'), acc)

# ---- 3. reachable, and not in a trail corridor --------------------------------
fin = np.isfinite(acc) & (acc < 1e17)
corridor = np.clip((td-TRAIL_FULL)/(TRAIL_FADE-TRAIL_FULL), 0, 1)
u = usable(np.where(fin, acc, 99)) * (0.35 + 0.65*corridor)
np.save(os.path.join(WORK, 'access_usable.npy'), u.astype(np.float32))
print('walk-in: median %.2f h; usable band (>0.5) %.1f%% of the unit' % (
    np.median(acc[fin]), 100*(u > 0.5).mean()))
