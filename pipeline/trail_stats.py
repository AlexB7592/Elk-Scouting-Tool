import json,math,collections,numpy as np,rasterio,warnings,os; warnings.filterwarnings('ignore')
REPO='/Users/alexbienemann/Downloads/gmu44_final 12'
from unit import LON0,LAT0,LON1,LAT1,EW,EH
STEP_M=30.48          # resample at 100 ft: vertex spacing varies, and raw
                      # vertex-to-vertex sums inflate gain on densely drawn lines
with rasterio.open(REPO+'/grids/elev_grid.png') as d:
    R=d.read(1).astype(np.float64); G=d.read(2).astype(np.float64)
E=(R*256+G)*0.25
def elev(lon,lat):
    c=(lon-LON0)/(LON1-LON0)*(EW-1); r=(lat-LAT0)/(LAT1-LAT0)*(EH-1)
    c=min(max(c,0),EW-1.001); r=min(max(r,0),EH-1.001)
    c0,r0=int(c),int(r); fc,fr=c-c0,r-r0
    return ((E[r0,c0]*(1-fc)+E[r0,c0+1]*fc)*(1-fr)+(E[r0+1,c0]*(1-fc)+E[r0+1,c0+1]*fc)*fr)
def m(a,b):
    return math.hypot((b[0]-a[0])*111320*math.cos(math.radians(a[1])),(b[1]-a[1])*110574)
def resample(c):
    """Points every STEP_M along the line, with the spacing carried across
    vertices. Restarting the grid at each vertex would oversample wherever the
    line is finely drawn, and oversampling inflates gain."""
    out=[c[0]]; carry=0.0
    for a,b in zip(c,c[1:]):
        d=m(a,b)
        if d<1e-9: continue
        t=STEP_M-carry
        while t<=d:
            f=t/d
            out.append([a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f])
            t+=STEP_M
        carry=d-(t-STEP_M)
    out.append(c[-1]); return out
def chain(segs,tol=40.0):
    segs=[list(s) for s in segs]; path=segs.pop(0)
    while segs:
        prog=False
        for i,s in enumerate(segs):
            for cand,att in ((s,'f'),(s[::-1],'r')):
                if m(path[-1],cand[0])<=tol: path+=cand[1:]; segs.pop(i); prog=True; break
                if m(path[0],cand[-1])<=tol: path=cand[:-1]+path; segs.pop(i); prog=True; break
            if prog: break
        if not prog: return None
    return path
tr=json.load(open(REPO+'/data/vectors/trails.geojson'))['features']
g=collections.defaultdict(list); meta={}
for f in tr:
    p=f['properties']; n=p['trail_name']
    g[n].append(f['geometry']['coordinates'])
    meta.setdefault(n,{'no':p.get('trail_no'),'cls':p.get('trail_class'),'use':p.get('allowed_terra_use')})
stats={}; chained=0
for n,segs in g.items():
    miles=sum(m(a,b) for c in segs for a,b in zip(c,c[1:]))/1609.34
    up=dn=0.0; lo=1e9; hi=-1e9
    for c in segs:
        e=[elev(x,y) for x,y in resample(c)]
        for a,b in zip(e,e[1:]):
            if b>a: up+=b-a
            else:   dn+=a-b
        lo=min(lo,min(e)); hi=max(hi,max(e))
    prof=None
    p=chain(segs) if len(segs)>1 else segs[0]
    if p:
        chained+=1
        e=[elev(x,y) for x,y in resample(p)]
        k=max(1,len(e)//64)
        prof=[round(v) for v in e[::k]][:64]
    stats[n]={'no':meta[n]['no'],'cls':meta[n]['cls'],'use':meta[n]['use'],
              'mi':round(miles,2),'up':round(up),'dn':round(dn),
              'lo':round(lo),'hi':round(hi),'segs':len(segs),'prof':prof}
print("trails: %d   profile available (segments chain end-to-end): %d"%(len(stats),chained))
print("%-22s %6s %7s %7s  %s"%("trail","mi","gain","loss","profile"))
for n,v in sorted(stats.items(),key=lambda x:-x[1]['mi'])[:8]:
    print("%-22s %6.1f %7d %7d  %s"%(n.title(),v['mi'],v['up'],v['dn'],
          ("%d pts"%len(v['prof'])) if v['prof'] else "-- segments do not connect"))
json.dump(stats,open(REPO+'/data/trail_stats.json','w'),separators=(',',':'))
print("\nwrote trail_stats.json  %.1f KB"%(os.path.getsize(REPO+'/data/trail_stats.json')/1024))
