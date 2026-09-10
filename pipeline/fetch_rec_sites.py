import json,re,urllib.request,urllib.parse
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
U=("https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_RecreationOpportunities_01/MapServer/0/query?"
   +urllib.parse.urlencode({'where':'1=1','geometry':'-106.8751,39.2500,-106.5003,39.5001',
     'geometryType':'esriGeometryEnvelope','inSR':'4326','spatialRel':'esriSpatialRelIntersects',
     'outFields':'recareaname,recareaurl,open_season_start,open_season_end,recareadescription',
     'returnGeometry':'true','outSR':'4326','f':'json'}))
d=json.loads(urllib.request.urlopen(urllib.request.Request(U,headers={'User-Agent':'gmu44/1.0'}),timeout=120).read())
assert 'features' in d, d
trails=json.load(open(REPO+'/data/vectors/trails.geojson'))['features']
no2name={}
for f in trails:
    p=f['properties']
    if p.get('trail_no'): no2name[str(p['trail_no']).strip()]=p['trail_name']
def kind(n):
    s=n.lower()
    if re.search(r'\bth\b|trailhead',s):        return 'trailhead'
    if 'campground' in s:                        return 'campground'
    if 'picnic' in s:                            return 'picnic'
    if 'wilderness' in s:                        return 'wilderness'
    return 'rec'
out=[]
for f in d['features']:
    a=f['attributes']; g=f.get('geometry') or {}
    if 'x' not in g: continue
    n=(a.get('recareaname') or '').strip()
    if not n: continue
    k=kind(n)
    m=re.search(r'#\s*(\d+)',n)
    pr={'name':re.sub(r'\s*#\s*\d+$','',n).strip(),'kind':k}
    if m:
        pr['trail_no']=m.group(1)
        if m.group(1) in no2name: pr['trail']=no2name[m.group(1)]
    for src,dst in (('open_season_start','open'),('open_season_end','close')):
        v=a.get(src)
        if v: pr[dst]=str(v)[:10]
    out.append({'type':'Feature','properties':pr,
                'geometry':{'type':'Point','coordinates':[round(g['x'],6),round(g['y'],6)]}})
import collections
print("rec sites: %d"%len(out))
print("kinds:",collections.Counter(f['properties']['kind'] for f in out).most_common())
print("trailheads linked to a trail: %d of %d"%(
    sum(1 for f in out if f['properties'].get('trail')),
    sum(1 for f in out if f['properties']['kind']=='trailhead')))
json.dump({'type':'FeatureCollection','features':out},
          open(REPO+'/data/vectors/rec_sites.geojson','w'),separators=(',',':'))
import os; print("wrote rec_sites.geojson  %.1f KB"%(os.path.getsize(REPO+'/data/vectors/rec_sites.geojson')/1024))
