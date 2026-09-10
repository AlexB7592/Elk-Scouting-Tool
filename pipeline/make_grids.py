import json,math,os,numpy as np,warnings; warnings.filterwarnings('ignore')
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
from unit import LON0,LAT0,LON1,LAT1
from unit import EW,EH   # same grid as cost_grid / elev_grid
R_=6378137.0
g=json.load(open('base/grid.json')); MW,MH=g['W'],g['H']
mxa,mxb,mya,myb=g['mxa'],g['mxb'],g['mya'],g['myb']

# ---- resample the mercator NLCD/TCC rasters onto the app's lat/lon grid ------
lons=LON0+(np.arange(EW)+0.5)*(LON1-LON0)/EW
lats=LAT0+(np.arange(EH)+0.5)*(LAT1-LAT0)/EH
mx=np.radians(lons)*R_
my=R_*np.log(np.tan(np.pi/4+np.radians(lats)/2))
cx=np.clip(((mx-mxa)/(mxb-mxa)*MW).astype(np.int32),0,MW-1)
cy=np.clip(((myb-my)/(myb-mya)*MH).astype(np.int32),0,MH-1)
tcc=np.load('base/tcc.npy')[cy][:,cx]
nl =np.asarray(Image.open('base/nlcd_master.png').convert('RGB'))[cy][:,cx]
key=(nl[...,0].astype(np.int32)<<16)|(nl[...,1].astype(np.int32)<<8)|nl[...,2].astype(np.int32)
print("canopy grid %s  mean %.1f%%  max %d%%"%(tcc.shape,tcc.mean(),tcc.max()))

# ---- forage classes ---------------------------------------------------------
# The old build read LANDFIRE vegetation type alone. NLCD class plus canopy
# percent is a better split, because "open conifer" vs "dense conifer" IS
# canopy density -- the thing the old model had to infer.
EVERGREEN,MIXED=0x1c6330,0xb5c98e
PRIME={0xe2e2c1,0xdbd83d,0xbad8ea,0x70a3ba}       # grass, pasture, wetland
GOOD ={0x68aa63,0xccba7c}                          # aspen/deciduous, shrub
DENSE_AT=45
forage=np.zeros((EH,EW),np.uint8)
forage[np.isin(key,list(PRIME))]=1
forage[np.isin(key,list(GOOD))]=2
con=np.isin(key,[EVERGREEN,MIXED])
forage[con & (tcc< DENSE_AT)]=3
forage[con & (tcc>=DENSE_AT)]=4
lab=['unclassified','prime meadow/riparian','good aspen/shrub','low open conifer','minimal dense conifer']
for v in range(5):
    print("  forage %d  %-24s %5.1f%%"%(v,lab[v],100*(forage==v).mean()))

# ---- distance from roads ----------------------------------------------------
roads=json.load(open(REPO+'/data/vectors/roads_all.geojson'))['features']
occ=np.zeros((EH,EW),bool)
def put(lon,lat):
    c=int((lon-LON0)/(LON1-LON0)*(EW-1)); r=int((lat-LAT0)/(LAT1-LAT0)*(EH-1))
    if 0<=c<EW and 0<=r<EH: occ[r,c]=True
for f in roads:
    gm=f['geometry']; parts=[gm['coordinates']] if gm['type']=='LineString' else gm['coordinates']
    for cds in parts:
        for a,b in zip(cds,cds[1:]):
            d=math.hypot((b[0]-a[0])*111320*math.cos(math.radians(a[1])),(b[1]-a[1])*110574)
            n=max(1,int(d/10))
            for i in range(n+1):
                t=i/n; put(a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
print("\nroad cells marked: %d (%.2f%% of grid)"%(occ.sum(),100*occ.mean()))
# chamfer distance transform, two passes, in cell units then scaled
CX=(LON1-LON0)/EW*111320*math.cos(math.radians((LAT0+LAT1)/2))
CY=abs((LAT1-LAT0)/EH*110574)
print("cell %.1f x %.1f m"%(CX,CY))
INF=1e9
D=np.where(occ,0.0,INF)
dx,dy,dd=CX,CY,math.hypot(CX,CY)
for _ in range(2):
    for r in range(EH):                       # forward
        row=D[r]
        if r>0:
            prev=D[r-1]
            row=np.minimum(row,prev+dy)
            row[1:]=np.minimum(row[1:],prev[:-1]+dd)
            row[:-1]=np.minimum(row[:-1],prev[1:]+dd)
        for c in range(1,EW): row[c]=min(row[c],row[c-1]+dx)
        D[r]=row
    for r in range(EH-1,-1,-1):               # backward
        row=D[r]
        if r<EH-1:
            nxt=D[r+1]
            row=np.minimum(row,nxt+dy)
            row[1:]=np.minimum(row[1:],nxt[:-1]+dd)
            row[:-1]=np.minimum(row[:-1],nxt[1:]+dd)
        for c in range(EW-2,-1,-1): row[c]=min(row[c],row[c+1]+dx)
        D[r]=row
print("road distance: max %.0f m, median %.0f m"%(D.max(),np.median(D)))
STEP=25.0                                     # 0-6375 m in one byte
rd=np.clip(np.round(D/STEP),0,255).astype(np.uint8)
print("  encoded at %.0f m per step, ceiling %.0f m"%(STEP,255*STEP))
for thr in (400,800,1600,2760):
    print("    beyond %4d m from any road: %5.1f%% of the unit"%(thr,100*(D>thr).mean()))
os.makedirs(REPO+'/grids',exist_ok=True)
Image.fromarray(tcc.astype(np.uint8)).save(REPO+'/grids/canopy_grid.png',optimize=True)
Image.fromarray(forage).save(REPO+'/grids/forage_grid.png',optimize=True)
Image.fromarray(rd).save(REPO+'/grids/roaddist_grid.png',optimize=True)
for n in ('canopy_grid','forage_grid','roaddist_grid'):
    print("  %-16s %6.1f KB"%(n,os.path.getsize(REPO+'/grids/%s.png'%n)/1024))
