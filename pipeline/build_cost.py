import numpy as np, rasterio, math, warnings; warnings.filterwarnings('ignore')
from PIL import Image
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
with rasterio.open(REPO+'/grids/elev_grid.png') as ds:
    Eft=(ds.read(1).astype(np.float64)*256+ds.read(2).astype(np.float64))*0.25
E=Eft*0.3048
C=np.asarray(Image.open(REPO+'/grids/canopy_grid.png')).astype(float)
F=np.asarray(Image.open(REPO+'/grids/forage_grid.png'))
H,W=E.shape; CX,CY=17.2,22.1
# --- 1. Tobler's hiking function: speed as a function of SIGNED slope --------
# w = 6 * exp(-3.5 * |S + 0.05|)  km/h, S = rise/run. Asymmetric: fastest at a
# gentle DOWNHILL (-2.9 deg), not on the flat. Cost is time, so cost = 1/speed.
def tobler_cost(dz, dist):
    S = dz/dist
    speed = 6.0*np.exp(-3.5*np.abs(S+0.05))     # km/h
    return (dist/1000.0)/np.maximum(speed,1e-3) # hours
print("Tobler speed check (km/h):")
for deg in (-30,-20,-10,-2.9,0,10,20,30,40):
    s=math.tan(math.radians(deg))
    print("   %+5.1f deg  %5.2f km/h"%(deg,6.0*math.exp(-3.5*abs(s+0.05))))
# --- 2. terrain penalties that multiply travel time -------------------------
gy,gx=np.gradient(E,CY,CX)
slope=np.degrees(np.arctan(np.hypot(gx,gy)))
# ruggedness: how much the slope varies locally -- smooth 25 deg face vs boulders
P=np.pad(slope,1,mode='edge')
rug=np.zeros_like(slope)
for dy in(-1,0,1):
    for dx in(-1,0,1):
        rug+=np.abs(P[1+dy:H+1+dy,1+dx:W+1+dx]-slope)
rug/=8.0
print("\nruggedness (mean neighbour slope difference, degrees):")
print("   median %.2f   90th %.2f   99th %.2f"%(np.median(rug),np.percentile(rug,90),np.percentile(rug,99)))
RUG = 1.0 + np.clip(rug/6.0,0,1.5)
# deadfall / brush: dense conifer and shrub slow you down; LANDFIRE SB = blowdown
fb=np.load('fbfm.npy')
blowdown=(fb>=201)&(fb<=204)
BRUSH = 1.0 + 0.35*(F==5) + 0.25*(F==3) + 0.9*blowdown
print("\nbrush/deadfall multiplier: median %.2f  max %.2f  (blowdown on %.2f%% of cells)"%(
      np.median(BRUSH),BRUSH.max(),100*blowdown.mean()))
# perennial water crossings -- only the 21.7% that actually hold water
import json
from PIL import ImageDraw
LON0,LAT0=-106.8750600,39.5000693; LON1,LAT1=-106.5003350,39.2499693
im=Image.new('L',(W,H),0); dr=ImageDraw.Draw(im); n=0
for f in json.load(open(REPO+'/data/vectors/streams.geojson'))['features']:
    if f['properties'].get('flow')!='perennial': continue
    pts=[(((x-LON0)/(LON1-LON0)*(W-1)),((y-LAT0)/(LAT1-LAT0)*(H-1))) for x,y in f['geometry']['coordinates']]
    if len(pts)>1: dr.line(pts,fill=255,width=1); n+=1
water=np.asarray(im)>0
WATER = 1.0 + 2.0*water
print("perennial crossings rasterised from %d segments (%.2f%% of cells)"%(n,100*water.mean()))
np.save('cost_terrain_mult.npy',(RUG*BRUSH*WATER).astype(np.float32))
np.save('cost_elev_m.npy',E.astype(np.float32))
M=RUG*BRUSH*WATER
print("\ncombined terrain multiplier: median %.2f  90th %.2f  max %.2f"%(
      np.median(M),np.percentile(M,90),M.max()))
