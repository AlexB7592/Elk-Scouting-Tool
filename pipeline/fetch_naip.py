import math,os,sys,time,urllib.request,json
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
R=6378137.0; WORLD=20037508.342789244
from unit import LON0,LAT0,LON1,LAT1
Z=13; TS=512
def mx(lon): return math.radians(lon)*R
def my(lat): return R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
def tilex(lon): return (lon+180.0)/360.0*(1<<Z)
def tiley(lat):
    s=math.sin(math.radians(lat))
    return (0.5-math.log((1+s)/(1-s))/(4*math.pi))*(1<<Z)
X0=math.floor(tilex(LON0)); X1=math.ceil(tilex(LON1))
Y0=math.floor(tiley(LAT0)); Y1=math.ceil(tiley(LAT1))
NX,NY=X1-X0,Y1-Y0
W,H=NX*TS,NY*TS
span=2*WORLD/(1<<Z)
mxa=-WORLD+X0*span; mxb=-WORLD+X1*span
mya= WORLD-Y1*span; myb= WORLD-Y0*span     # a=min, b=max
print("tile grid x %d..%d  y %d..%d   -> %d x %d tiles  = %d x %d px"%(X0,X1-1,Y0,Y1-1,NX,NY,W,H))
print("mercator bbox %.1f %.1f %.1f %.1f  (%.3f m/px merc)"%(mxa,mya,mxb,myb,span/TS))
json.dump(dict(Z=Z,TS=TS,X0=X0,X1=X1,Y0=Y0,Y1=Y1,W=W,H=H,
               mxa=mxa,mya=mya,mxb=mxb,myb=myb),open('base/grid.json','w'))
URL=("https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer"
     "/exportImage?bbox=%f,%f,%f,%f&bboxSR=3857&imageSR=3857&size=%d,%d"
     "&format=jpg&interpolation=RSP_BilinearInterpolation&f=image")
CW,CH=3,2                                   # chunk the request grid
canvas=Image.new('RGB',(W,H))
for cj in range(CH):
    for ci in range(CW):
        px0=W*ci//CW; px1=W*(ci+1)//CW; py0=H*cj//CH; py1=H*(cj+1)//CH
        bx0=mxa+(mxb-mxa)*px0/W; bx1=mxa+(mxb-mxa)*px1/W
        by1=myb-(myb-mya)*py0/H; by0=myb-(myb-mya)*py1/H
        u=URL%(bx0,by0,bx1,by1,px1-px0,py1-py0)
        f='base/naip_%d_%d.jpg'%(ci,cj)
        if not os.path.exists(f):
            for a in range(4):
                try:
                    rq=urllib.request.Request(u,headers={'User-Agent':'gmu44/1.0'})
                    d=urllib.request.urlopen(rq,timeout=180).read()
                    if d[:2]!=b'\xff\xd8': raise RuntimeError('not JPEG: %r'%d[:60])
                    open(f,'wb').write(d); break
                except Exception as e:
                    print("  retry %d %s"%(a,e)); time.sleep(3)
            else: sys.exit("FAILED %s"%f)
        im=Image.open(f).convert('RGB')
        assert im.size==(px1-px0,py1-py0), (f,im.size,(px1-px0,py1-py0))
        canvas.paste(im,(px0,py0))
        print("  chunk %d,%d  %dx%d  %d KB"%(ci,cj,im.size[0],im.size[1],os.path.getsize(f)//1024))
canvas.save('base/naip_master.jpg',quality=92)
print("master %s  %.1f MB"%(canvas.size,os.path.getsize('base/naip_master.jpg')/1e6))
