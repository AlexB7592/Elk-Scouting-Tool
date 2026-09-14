"""Auto-Scout step 3 of 4: score every cell.

Scores JUXTAPOSITION, not what a cell is. Elk need security cover to bed in,
food close enough to use the same day, and water, with pressure low enough that
they can. The old hotspot layer measured ~78% a feeding surface because it scored
ground type; this asks whether all three are present together.

  bedding  the cell's OWN cover: canopy (full marks at 45%) plus broken ground,
           cut to a quarter above measured treeline (11,500 ft, HANDOFF 5h)
  feed     HOW MUCH good forage is within 600 m -- a mean over the window, not
           the best value in it. Taking the best made 99.4% of cells pass,
           because in a forested unit almost everywhere is near some timber
           and some forage, and the first surface lit up 71% of the unit.
  water    within 1,200 m, linear
  access   step 2: reachable in a day and not in a trail corridor

Combined as a GEOMETRIC mean of bedding x feed x water, so a gap in any one
sinks the cell. An arithmetic mean lets strong forage paper over no water --
which is how you get a feeding surface. Access then scales it 0.30..1.00.

Forage weights follow Brough et al. 2017 (72 collared cow elk, White River NF):
aspen and open conifer are selected; meadow is AVOIDED in daylight despite good
grass, so it is scored low. The first cut of this model had meadow on top.

NOT validated against elk locations -- none went into it. See HANDOFF.

Reads  grids/canopy, forage, roaddist, ownership, water_dist, elev, terrain_mult
       WORK/access_usable.npy
Writes WORK/as_score.npy, WORK/as_parts.npy   (bed, feed, water, access)
"""
import os, numpy as np, rasterio, warnings
warnings.filterwarnings('ignore')
from scipy.ndimage import uniform_filter
from unit import REPO, SLUG, CELL_X_M, CELL_Y_M, TREELINE_FT

WORK = os.path.expanduser('~/gmu44-scratch/work/autoscout')
G = os.path.join(REPO, 'grids')
CX, CY = (17.2, 22.1) if SLUG == 'gmu44' else (CELL_X_M, CELL_Y_M)
def g(n, band=1):
    with rasterio.open(os.path.join(G, n + '.png')) as ds:
        return ds.read(band).astype(np.float32)

canopy = g('canopy_grid')                       # percent
forage = g('forage_grid').astype(np.int16)      # 1..6
own    = g('ownership_grid').astype(np.int16)   # 2 = private
waterm = g('water_dist_grid')*25.0              # metres
with rasterio.open(os.path.join(G, 'elev_grid.png')) as ds:
    elev = (ds.read(1).astype(np.float32)*256 + ds.read(2).astype(np.float32))*0.25   # feet
rugg   = g('terrain_mult_grid')/255.0

FORAGE = {0: 0.00,
          1: 0.35,   # meadow & park   - grass, but avoided in daylight
          2: 1.00,   # aspen           - selected, richest understory
          3: 0.70,   # shrub & oak
          4: 0.85,   # open conifer    - selected
          5: 0.30,   # dense conifer   - cover, not food
          6: 0.15}   # alpine
feedval = np.zeros_like(canopy)
for k, v in FORAGE.items():
    feedval[forage == k] = v

bedval = np.clip(canopy/45.0, 0, 1)*0.75 + np.clip(rugg, 0, 1)*0.25
bedval[elev > TREELINE_FT] *= 0.25
bedval[forage == 6] *= 0.25

def rad(m, axis):
    return max(1, int(round(m/(CX if axis == 'x' else CY))))
def density(a, metres):
    return uniform_filter(a, size=(2*rad(metres, 'y')+1, 2*rad(metres, 'x')+1), mode='nearest')

FEED_R, WATER_R = 600.0, 1200.0
feed_near  = density(feedval, FEED_R)
water_near = np.clip(1.0 - waterm/WATER_R, 0, 1)
access     = np.load(os.path.join(WORK, 'access_usable.npy')).astype(np.float32)

core  = (np.clip(bedval, 0, 1) * feed_near * water_near) ** (1.0/3.0)
score = core * (0.30 + 0.70*access)
score[own == 2] = 0.0                           # private: cannot hunt it
score[np.isnan(score)] = 0.0

np.save(os.path.join(WORK, 'as_score.npy'), score.astype(np.float32))
np.save(os.path.join(WORK, 'as_parts.npy'),
        np.stack([bedval, feed_near, water_near, access]).astype(np.float32))
print('surface: %.1f%% of the unit scores > 0.5; 95th percentile %.3f' % (
    100*np.mean(score > 0.5), np.percentile(score, 95)))
