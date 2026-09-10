import json,urllib.request,urllib.parse,time,sys,os,collections
from unit import EXTENT_STR as EXT
U="https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query"
feats=[];off=0
while True:
    p={'where':'1=1','geometry':EXT,'geometryType':'esriGeometryEnvelope','inSR':'4326','outSR':'4326',
       'spatialRel':'esriSpatialRelIntersects','outFields':'gnis_name,lengthkm,ftype,fcode',
       'returnGeometry':'true','f':'geojson','resultOffset':off,'resultRecordCount':1000,
       'orderByFields':'permanent_identifier'}
    for a in range(4):
        try:
            d=json.loads(urllib.request.urlopen(urllib.request.Request(U+'?'+urllib.parse.urlencode(p),
                headers={'User-Agent':'gmu44/1.0'}),timeout=180).read()); break
        except Exception as e:
            print("  retry",a,str(e)[:70]); time.sleep(4)
    else: sys.exit("failed")
    f=d.get('features',[]); feats+=f
    if len(f)<1000: break
    off+=1000; time.sleep(0.3)
print("flowlines fetched: %d"%len(feats))
FC={46006:'perennial',46003:'intermittent',46007:'ephemeral',55800:'artificial path',
    46000:'unspecified',33600:'canal/ditch',33400:'connector',42800:'pipeline'}
c=collections.Counter(f['properties'].get('fcode') for f in feats)
print("\nfcode breakdown:")
tot=sum(c.values())
for k,v in c.most_common(8):
    print("   %-8s %-18s %5d  %5.1f%%"%(k,FC.get(k,'?'),v,100*v/tot))
per=sum(v for k,v in c.items() if k==46006)
print("\nPERENNIAL (holds water in September): %d of %d = %.1f%%"%(per,tot,100*per/tot))
json.dump({'type':'FeatureCollection','features':feats},open('streams_fcode.geojson','w'),separators=(',',':'))
print("saved %.1f MB"%(os.path.getsize('streams_fcode.geojson')/1e6))
