import json,math,os,numpy as np
from PIL import Image
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
from unit import LON0,LAT0,LON1,LAT1
from unit import EW,EH
CX=(LON1-LON0)/EW*111320*math.cos(math.radians(39.375))
CY=abs((LAT1-LAT0)/EH*110574)
BUF=7000.0
PX=int(math.ceil(BUF/CX)); PY=int(math.ceil(BUF/CY))
BW,BH=EW+2*PX,EH+2*PY
print("grid %dx%d  cell %.1f x %.1f m  -> buffered %dx%d (+%d,+%d cells)"%(EW,EH,CX,CY,BW,BH,PX,PY))
occ=np.zeros((BH,BW),bool)
def put(lon,lat):
    c=int(round((lon-LON0)/(LON1-LON0)*(EW-1)))+PX
    r=int(round((lat-LAT0)/(LAT1-LAT0)*(EH-1)))+PY
    if 0<=c<BW and 0<=r<BH: occ[r,c]=True
n=0
for f in json.load(open('buf_roads.geojson'))['features']:
    g=f.get('geometry') or {}
    if not g: continue
    parts=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
    for cds in parts:
        for a,b in zip(cds,cds[1:]):
            d=math.hypot((b[0]-a[0])*111320*math.cos(math.radians(a[1])),(b[1]-a[1])*110574)
            k=max(1,int(d/8))
            for i in range(k+1):
                t=i/k; put(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
    n+=1
print("rasterised %d road features, %d cells marked"%(n,occ.sum()))
INF=1e9
D=np.where(occ,0.0,INF)
dd=math.hypot(CX,CY)
for r in range(BH):
    row=D[r]
    if r>0:
        p=D[r-1]
        row=np.minimum(row,p+CY)
        row[1:]=np.minimum(row[1:],p[:-1]+dd)
        row[:-1]=np.minimum(row[:-1],p[1:]+dd)
    for c in range(1,BW):
        if row[c]>row[c-1]+CX: row[c]=row[c-1]+CX
    D[r]=row
for r in range(BH-1,-1,-1):
    row=D[r]
    if r<BH-1:
        p=D[r+1]
        row=np.minimum(row,p+CY)
        row[1:]=np.minimum(row[1:],p[:-1]+dd)
        row[:-1]=np.minimum(row[:-1],p[1:]+dd)
    for c in range(BW-2,-1,-1):
        if row[c]>row[c+1]+CX: row[c]=row[c+1]+CX
    D[r]=row
Dc=D[PY:PY+EH, PX:PX+EW]
old=np.asarray(Image.open(REPO+'/grids/roaddist_grid.png')).astype(float)*25.0
print("\n                    in-extent roads only   buffered")
print("max distance          %8.0f m        %8.0f m"%(old.max(),Dc.max()))
print("median                %8.0f m        %8.0f m"%(np.median(old),np.median(Dc)))
for thr in (400,800,1600,2760):
    print("beyond %4d m         %8.1f%%          %8.1f%%"%(thr,100*(old>thr).mean(),100*(Dc>thr).mean()))
STEP=25.0
rd=np.clip(np.round(Dc/STEP),0,255).astype(np.uint8)
Image.fromarray(rd).save(REPO+'/grids/roaddist_grid.png',optimize=True)
print("\nwrote roaddist_grid.png  %.1f KB   (%.0f m per step, ceiling %.0f m)"%(
      os.path.getsize(REPO+'/grids/roaddist_grid.png')/1024,STEP,255*STEP))
