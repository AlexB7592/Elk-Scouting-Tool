import math,json,io,os,time
from PIL import Image
from pmtiles.writer import Writer
from pmtiles.tile import Compression,TileType,zxy_to_tileid
Image.MAX_IMAGE_PIXELS=None
from unit import LON0,LAT0,LON1,LAT1
MINZ,MAXZ,TS,Q=8,15,512,82
g=json.load(open('base/grid.json'))
W,H=g['W'],g['H']; mxa,mxb,mya,myb=g['mxa'],g['mxb'],g['mya'],g['myb']
WORLD=20037508.342789244
master=Image.open('base/terrain_final.png').convert('RGB')
assert master.size==(W,H), master.size
def tx(lon,z): return (lon+180.0)/360.0*(1<<z)
def ty(lat,z):
    s=math.sin(math.radians(lat)); return (0.5-math.log((1+s)/(1-s))/(4*math.pi))*(1<<z)
tiles={}; t0=time.time()
for z in range(MINZ,MAXZ+1):
    x0=int(math.floor(tx(LON0,z))); x1=int(math.ceil(tx(LON1,z)))
    y0=int(math.floor(ty(LAT0,z))); y1=int(math.ceil(ty(LAT1,z)))
    span=2*WORLD/(1<<z); n=0
    for X in range(x0,x1):
        for Y in range(y0,y1):
            ax=-WORLD+X*span; bx=ax+span; by=WORLD-Y*span; ay=by-span
            l=(ax-mxa)/(mxb-mxa)*W; r=(bx-mxa)/(mxb-mxa)*W
            t=(myb-by)/(myb-mya)*H; b=(myb-ay)/(myb-mya)*H
            if r<=0 or l>=W or b<=0 or t>=H: continue
            cl,ct=max(l,0.0),max(t,0.0); cr,cb=min(r,float(W)),min(b,float(H))
            if cr-cl<1e-6 or cb-ct<1e-6: continue
            dl=int(round((cl-l)/(r-l)*TS)); dr=int(round((cr-l)/(r-l)*TS))
            dt=int(round((ct-t)/(b-t)*TS)); db=int(round((cb-t)/(b-t)*TS))
            if dr-dl<1 or db-dt<1: continue
            im=Image.new('RGB',(TS,TS),(0xe8,0xe4,0xd9))
            im.paste(master.resize((dr-dl,db-dt),Image.LANCZOS,box=(cl,ct,cr,cb)),(dl,dt))
            buf=io.BytesIO(); im.save(buf,'JPEG',quality=Q,optimize=True,progressive=False)
            tiles[zxy_to_tileid(z,X,Y)]=buf.getvalue(); n+=1
    print("  z%-2d  %2d x %2d  -> %4d tiles"%(z,x1-x0,y1-y0,n))
print("total %d tiles, %.1f MB, %.1fs"%(len(tiles),sum(len(v) for v in tiles.values())/1e6,time.time()-t0))
out='base/gmu44_terrain_base.pmtiles'
with open(out,'wb') as f:
    w=Writer(f)
    for tid in sorted(tiles): w.write_tile(tid,tiles[tid])
    w.finalize({"tile_type":TileType.JPEG,"tile_compression":Compression.NONE,
                "min_zoom":MINZ,"max_zoom":MAXZ,
                "min_lon_e7":int(LON0*1e7),"min_lat_e7":int(LAT1*1e7),
                "max_lon_e7":int(LON1*1e7),"max_lat_e7":int(LAT0*1e7),
                "center_zoom":13,"center_lon_e7":int((LON0+LON1)/2*1e7),
                "center_lat_e7":int((LAT0+LAT1)/2*1e7)},
               {"name":"GMU 44 terrain basemap","format":"jpg",
                "description":"Softened NAIP with baked hillshade, EPSG:3857"})
print("wrote %s  %.1f MB"%(out,os.path.getsize(out)/1e6))
