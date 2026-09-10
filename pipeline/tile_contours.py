import json,math,gzip,io,os,time
from shapely.geometry import box,shape,LineString,MultiLineString
from shapely.strtree import STRtree
import mapbox_vector_tile
from pmtiles.writer import Writer
from pmtiles.tile import Compression,TileType,zxy_to_tileid
from unit import LON0,LAT0,LON1,LAT1
EXTENT=4096; BUF=64
SPEC={'index':{'minz':11,'file':'contours_index.geojson'},
      'intermediate':{'minz':13,'file':'contours_intermediate.geojson'}}
MINZ,MAXZ=11,15
def tx(lon,z): return (lon+180.0)/360.0*(1<<z)
def ty(lat,z):
    s=math.sin(math.radians(lat)); return (0.5-math.log((1+s)/(1-s))/(4*math.pi))*(1<<z)
data={}
for name,cfg in SPEC.items():
    fs=json.load(open(cfg['file']))['features']
    geoms=[];props=[]
    for f in fs:
        g=shape(f['geometry'])
        if g.is_empty: continue
        geoms.append(g); props.append({'ele':int(f['properties']['contourelevation'])})
    data[name]=(geoms,props,STRtree(geoms),cfg['minz'])
    print("%-14s %4d geoms  minzoom %d"%(name,len(geoms),cfg['minz']))
tiles={}; t0=time.time()
for z in range(MINZ,MAXZ+1):
    x0,x1=int(math.floor(tx(LON0,z))),int(math.ceil(tx(LON1,z)))
    y0,y1=int(math.floor(ty(LAT0,z))),int(math.ceil(ty(LAT1,z)))
    n=0
    for X in range(x0,x1):
        for Y in range(y0,y1):
            wl=X/(1<<z)*360.0-180.0; wr=(X+1)/(1<<z)*360.0-180.0
            def lat_of(yy):
                nn=math.pi-2*math.pi*yy/(1<<z)
                return math.degrees(math.atan(math.sinh(nn)))
            wt=lat_of(Y); wb=lat_of(Y+1)
            bx=(wr-wl)*BUF/EXTENT; by=(wt-wb)*BUF/EXTENT
            clip=box(wl-bx,wb-by,wr+bx,wt+by)
            layers=[]
            for name,(geoms,props,tree,minz) in data.items():
                if z<minz: continue
                feats=[]
                for i in tree.query(clip):
                    g=geoms[i].intersection(clip)
                    if g.is_empty: continue
                    parts=[g] if isinstance(g,LineString) else (list(g.geoms) if isinstance(g,MultiLineString) else [])
                    for p in parts:
                        if len(p.coords)<2: continue
                        c=[(int(round((lo-wl)/(wr-wl)*EXTENT)),
                            int(round((la-wb)/(wt-wb)*EXTENT))) for lo,la in p.coords]
                        d=[c[0]]
                        for pt in c[1:]:
                            if pt!=d[-1]: d.append(pt)      # drop points that quantise together
                        if len(d)<2: continue
                        feats.append({'geometry':LineString(d),'properties':props[i]})
                if feats: layers.append({'name':name,'features':feats})
            if not layers: continue
            raw=mapbox_vector_tile.encode(layers,extents=EXTENT,
                    default_options={'quantize_bounds':None,'y_coord_down':False})
            tiles[zxy_to_tileid(z,X,Y)]=gzip.compress(raw,6); n+=1
    print("  z%-2d -> %4d tiles"%(z,n))
print("total %d tiles  %.2f MB  %.0fs"%(len(tiles),sum(len(v) for v in tiles.values())/1e6,time.time()-t0))
out='base/gmu44_contours.pmtiles'
with open(out,'wb') as f:
    w=Writer(f)
    for tid in sorted(tiles): w.write_tile(tid,tiles[tid])
    w.finalize({"tile_type":TileType.MVT,"tile_compression":Compression.GZIP,
                "min_zoom":MINZ,"max_zoom":MAXZ,
                "min_lon_e7":int(LON0*1e7),"min_lat_e7":int(LAT1*1e7),
                "max_lon_e7":int(LON1*1e7),"max_lat_e7":int(LAT0*1e7),
                "center_zoom":13,"center_lon_e7":int((LON0+LON1)/2*1e7),
                "center_lat_e7":int((LAT0+LAT1)/2*1e7)},
               {"name":"GMU 44 contours","format":"pbf",
                "description":"USGS contours: index 200 ft, intermediate 40 ft",
                "vector_layers":[{"id":"index","fields":{"ele":"Number"},"minzoom":11,"maxzoom":15},
                                 {"id":"intermediate","fields":{"ele":"Number"},"minzoom":13,"maxzoom":15}]})
print("wrote %s  %.2f MB"%(out,os.path.getsize(out)/1e6))
