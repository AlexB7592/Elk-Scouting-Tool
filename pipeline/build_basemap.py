import math,json,time,numpy as np,warnings; warnings.filterwarnings('ignore')
import rasterio
from PIL import Image,ImageFilter
Image.MAX_IMAGE_PIXELS=None
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
R_=6378137.0
from unit import LON0,LAT0,LON1,LAT1
from unit import EW,EH
RELIEF=0.26; SOFTEN=1.6; CANOPY_W=0.75
g=json.load(open('base/grid.json')); W,H=g['W'],g['H']
mxa,mxb,mya,myb=g['mxa'],g['mxb'],g['mya'],g['myb']; MPP=(mxb-mxa)/W
sp=MPP*math.cos(math.radians((LAT0+LAT1)/2)); t0=time.time()

# ---- elevation on the mercator grid, then hillshade at image resolution -----
with rasterio.open(REPO+'/grids/elev_grid.png') as ds:
    Rb=ds.read(1).astype(np.float32); Gb=ds.read(2).astype(np.float32)
elev=(Rb*256.0+Gb)*0.25*0.3048
xs=mxa+(np.arange(W)+0.5)*MPP; ys=myb-(np.arange(H)+0.5)*MPP
lon=np.degrees(xs/R_); lat=np.degrees(2*np.arctan(np.exp(ys/R_))-math.pi/2)
COVER=((lat<=LAT0)&(lat>=LAT1))[:,None]&((lon>=LON0)&(lon<=LON1))[None,:]
print("coverage %.1f%% of tile grid inside the data extent"%(100*COVER.mean()))
col=np.clip((lon-LON0)/(LON1-LON0)*(EW-1),0,EW-1); row=np.clip((lat-LAT0)/(LAT1-LAT0)*(EH-1),0,EH-1)
c0=np.floor(col).astype(np.int32);c1=np.minimum(c0+1,EW-1);fc=(col-c0).astype(np.float32)
r0=np.floor(row).astype(np.int32);r1=np.minimum(r0+1,EH-1);fr=(row-r0).astype(np.float32)
dem=(elev[r0][:,c0]*(1-fc)+elev[r0][:,c1]*fc)*(1-fr[:,None])+(elev[r1][:,c0]*(1-fc)+elev[r1][:,c1]*fc)*fr[:,None]
assert 2100<dem.min()<2400 and 3900<dem.max()<4300, (dem.min(),dem.max())
gy,gx=np.gradient(dem,sp); slope=np.arctan(np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
az,alt=math.radians(315),math.radians(45)
hs=np.clip(np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-aspect),0,1).astype(np.float32)
del gx,gy,slope,aspect,dem,elev
print("hillshade mean %.3f  ground %.2f m/px  (%.1fs)"%(hs.mean(),sp,time.time()-t0))

# ---- landcover class -> pale tint -------------------------------------------
PAL={0x1c6330:(196,210,186),  # evergreen forest      0x68aa63:(208,219,192) deciduous
     0x68aa63:(208,219,192), 0xb5c98e:(202,215,189),  # deciduous, mixed forest
     0xccba7c:(226,220,199), 0xe2e2c1:(233,230,210),  # shrub/scrub, grassland
     0xdbd83d:(231,228,198), 0xb2ada3:(224,220,213),  # pasture, barren
     0xddc9c9:(229,225,220), 0x476ba0:(170,199,219),  # developed, open water
     0xbad8ea:(206,221,219), 0x70a3ba:(201,218,218),  # woody / herbaceous wetland
     0xd1ddf9:(240,243,247)}                          # ice / snow
nl=np.asarray(Image.open('base/nlcd_master.png').convert('RGB'))
key=(nl[...,0].astype(np.int32)<<16)|(nl[...,1].astype(np.int32)<<8)|nl[...,2].astype(np.int32); del nl
tint=np.empty((H,W,3),dtype=np.float32); tint[:]= [233,229,214]     # cream fallback
hit=np.zeros((H,W),dtype=bool)
for k,v in PAL.items():
    m=key==k; tint[m]=v; hit|=m
print("landcover: %.2f%% of the unit matched a known NLCD class"%(100*hit.mean()))
assert hit.mean()>0.98, "too many unmatched classes - palette is wrong"
del key,hit
tint/=255.0

# ---- canopy density deepens the green ---------------------------------------
tcc=np.load('base/tcc.npy').astype(np.float32)
assert tcc.shape==(H,W)
w=(np.clip(tcc/70.0,0,1)*CANOPY_W)[...,None]
tint=tint*(1-w)+np.float32([166,188,156])/255.0*w
print("canopy: mean %.1f%%  >=50%% on %.1f%% of the unit"%(tcc.mean(),100*(tcc>=50).mean()))
del tcc,w

# 30 m source upsampled to 7.4 m/px leaves hard blocks; a touch of blur reads as
# a polygon edge rather than a pixel edge, without smearing class boundaries.
tint=np.asarray(Image.fromarray((tint*255).astype(np.uint8)).filter(
      ImageFilter.GaussianBlur(radius=SOFTEN)),dtype=np.float32)/255.0
out=np.clip(tint*((1.0-RELIEF)+2*RELIEF*hs[...,None]),0,1)
out=np.where(COVER[...,None],out,np.float32([0xe8,0xe4,0xd9])/255.0)
Image.fromarray((out*255).astype(np.uint8)).save('base/carto_master.png',optimize=True)
f=out[COVER]
print("in-extent mean %.3f  saturation %.3f   (%.1fs)"%(f.mean(),(f.max(1)-f.min(1)).mean(),time.time()-t0))
