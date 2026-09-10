import json,math,os,time,urllib.request,urllib.parse,sys
from unit import LON0,LAT0,LON1,LAT1
BUF=7000.0
dlat=BUF/110574.0; dlon=BUF/(111320.0*math.cos(math.radians(39.375)))
EXT="%.6f,%.6f,%.6f,%.6f"%(LON0-dlon,LAT1-dlat,LON1+dlon,LAT0+dlat)
U="https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer/1/query"
feats=[];off=0
while True:
    p={'where':'1=1','geometry':EXT,'geometryType':'esriGeometryEnvelope','inSR':'4326','outSR':'4326',
       'spatialRel':'esriSpatialRelIntersects','outFields':'*','returnGeometry':'true','f':'geojson',
       'resultOffset':off,'resultRecordCount':1000,'orderByFields':'OBJECTID'}
    u=U+'?'+urllib.parse.urlencode(p)
    for a in range(4):
        try:
            d=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'gmu44/1.0'}),timeout=200).read())
            break
        except Exception as e:
            print("  retry",a,str(e)[:70]); time.sleep(4)
    else: sys.exit("failed")
    f=d.get('features',[]); feats+=f
    if len(f)<1000: break
    off+=1000; time.sleep(0.3)
print("MVUM open motorized roads in buffered box: %d"%len(feats))
if feats:
    ks=sorted(feats[0]['properties'].keys())
    print("fields:",[k for k in ks if 'SEASON' in k.upper() or 'SYMBOL' in k.upper() or 'NAME' in k.upper() or 'JURIS' in k.upper()][:8])
json.dump({'type':'FeatureCollection','features':feats},open('mvum_roads.geojson','w'),separators=(',',':'))
print("saved %.1f MB"%(os.path.getsize('mvum_roads.geojson')/1e6))
