"""Auto-Scout step 1 of 4: read the OLD hotspot layer into tiers, for comparison.

Auto-Scout does not use the old layer as an input -- nothing it scores comes
from here. This exists only so each area can report how much of it the old
layer also rated, which is the one corroboration we have (a guide who hunts the
unit called the old layer "mostly accurate", twice).

The old layer is a GMU 44 artefact whose generator was lost. Another unit will
not have it; this step then records that there is no reference layer, and the
areas say so instead of claiming disagreement.

Reads  elk_probability_files/11/*.png  (Deep Zoom level 11 = 1874 x 1251 px,
       one pixel short of matching the 1873 x 1250 grid on each axis)
Writes WORK/hotspot_tier.npy   0 none, 1 yellow, 2 orange, 3 red
       WORK/reference.json     {"has_reference": bool}
"""
import os, re, json, numpy as np
from PIL import Image
from unit import REPO, EW, EH

WORK = os.path.expanduser('~/gmu44-scratch/work/autoscout')
os.makedirs(WORK, exist_ok=True)
D = os.path.join(REPO, 'elk_probability_files', '11')
TS, OV = 254, 1                      # Deep Zoom tile size and overlap

tier = np.zeros((EH, EW), np.int8)
has_ref = os.path.isdir(D)
if has_ref:
    cols = rows = 0
    for f in os.listdir(D):
        m = re.match(r'(\d+)_(\d+)\.png', f)
        if m:
            cols = max(cols, int(m.group(1)) + 1)
            rows = max(rows, int(m.group(2)) + 1)
    canvas = Image.new('RGBA', (1874, 1251))
    for c in range(cols):
        for r in range(rows):
            p = os.path.join(D, '%d_%d.png' % (c, r))
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert('RGBA')
            canvas.paste(im, (c*TS - (OV if c > 0 else 0), r*TS - (OV if r > 0 else 0)))
    a = np.array(canvas)[:EH, :EW]
    rgb = a[..., :3].astype(int); al = a[..., 3]
    def near(t, tol=30):
        return ((np.abs(rgb[..., 0]-t[0]) < tol) & (np.abs(rgb[..., 1]-t[1]) < tol) &
                (np.abs(rgb[..., 2]-t[2]) < tol) & (al > 0))
    tier[near((255, 221, 51))] = 1   # yellow
    tier[near((255, 140, 0))]  = 2   # orange
    tier[near((214, 39, 40))]  = 3   # red

np.save(os.path.join(WORK, 'hotspot_tier.npy'), tier)
json.dump({'has_reference': has_ref}, open(os.path.join(WORK, 'reference.json'), 'w'))
if has_ref:
    print('old hotspot layer: yellow %.1f%%  orange %.1f%%  red %.1f%%  any %.1f%%' % (
        100*(tier == 1).mean(), 100*(tier == 2).mean(), 100*(tier == 3).mean(), 100*(tier > 0).mean()))
else:
    print('no old hotspot layer for this unit -- areas will report no reference')
