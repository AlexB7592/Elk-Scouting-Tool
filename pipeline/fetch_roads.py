import json,urllib.parse,urllib.request,os,time,math
# 7 km buffer: the encoded ceiling is 6375 m, so any road that could ever be the
# nearest one to a cell inside the extent is inside this box.
from unit import LON0,LAT0,LON1,LAT1,buffered_extent
BUF=7000.0
dlat=BUF/110574.0
dlon=BUF/(111320.0*math.cos(math.radians(39.375)))
EXT=buffered_extent(BUF)
print("buffered box: %s  (+%.0f m)"%(EXT,BUF))
BASE="https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/%d/query"
def fetch(layer,name,page=1000):
    if os.path.exists(name+'.geojson'):
        d=json.load(open(name+'.geojson')); print("  %-14s cached %5d"%(name,len(d['features']))); return d['features']
    feats=[];off=0
    while True:
        p={'where':'1=1','geometry':EXT,'geometryType':'esriGeometryEnvelope','inSR':'4326','outSR':'4326',
           'spatialRel':'esriSpatialRelIntersects','outFields':'OBJECTID','returnGeometry':'true','f':'geojson',
           'resultOffset':off,'resultRecordCount':page,'orderByFields':'OBJECTID'}
        u=(BASE%layer)+'?'+urllib.parse.urlencode(p)
        for a in range(4):
            try:
                d=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'gmu44/1.0'}),timeout=200).read())
                break
            except Exception as e:
                print("   retry",a,str(e)[:70]); time.sleep(4)
        else: raise SystemExit("failed "+name)
        f=d.get('features',[]); feats+=f
        if len(f)<page: break
        off+=page; time.sleep(0.3)
    json.dump({'type':'FeatureCollection','features':feats},open(name+'.geojson','w'))
    print("  %-14s %5d features"%(name,len(feats)))
    return feats
a=fetch(35,'buf_4wd'); b=fetch(32,'buf_local')
json.dump({'type':'FeatureCollection','features':a+b},open('buf_roads.geojson','w'),separators=(',',':'))
print("total %d road features in the buffered box (%.1f MB)"%(len(a+b),os.path.getsize('buf_roads.geojson')/1e6))
