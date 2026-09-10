import json,os,time,urllib.request,urllib.parse,sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
g=json.load(open('base/grid.json'))
W,H=g['W'],g['H']; mxa,mxb,mya,myb=g['mxa'],g['mxb'],g['mya'],g['myb']
URL='https://www.mrlc.gov/geoserver/wms?'
CW,CH=3,2
canvas=Image.new('RGB',(W,H))
for cj in range(CH):
    for ci in range(CW):
        px0=W*ci//CW; px1=W*(ci+1)//CW; py0=H*cj//CH; py1=H*(cj+1)//CH
        bx0=mxa+(mxb-mxa)*px0/W; bx1=mxa+(mxb-mxa)*px1/W
        by1=myb-(myb-mya)*py0/H; by0=myb-(myb-mya)*py1/H
        p={'service':'WMS','version':'1.3.0','request':'GetMap',
           'layers':'NLCD_2021_Land_Cover_L48','styles':'','crs':'EPSG:3857',
           'bbox':'%f,%f,%f,%f'%(bx0,by0,bx1,by1),
           'width':str(px1-px0),'height':str(py1-py0),'format':'image/png'}
        f='base/nlcd_%d_%d.png'%(ci,cj)
        if not os.path.exists(f):
            for a in range(4):
                try:
                    rq=urllib.request.Request(URL+urllib.parse.urlencode(p),
                                              headers={'User-Agent':'gmu44/1.0'})
                    d=urllib.request.urlopen(rq,timeout=180).read()
                    if d[:4]!=b'\x89PNG': raise RuntimeError('not PNG: %r'%d[:120])
                    open(f,'wb').write(d); break
                except Exception as e:
                    print("  retry %d %s"%(a,str(e)[:110])); time.sleep(4)
            else: sys.exit("FAILED "+f)
        im=Image.open(f).convert('RGB')
        assert im.size==(px1-px0,py1-py0),(f,im.size)
        canvas.paste(im,(px0,py0)); print("  chunk %d,%d %s %d KB"%(ci,cj,im.size,os.path.getsize(f)//1024))
canvas.save('base/nlcd_master.png',optimize=True)
print("nlcd master %s  %.1f MB"%(canvas.size,os.path.getsize('base/nlcd_master.png')/1e6))
import numpy as np
a=np.asarray(canvas).reshape(-1,3)
cols,counts=np.unique(a,axis=0,return_counts=True)
o=np.argsort(-counts)[:12]
print("\ntop colours (NLCD classes):")
for i in o:
    print("   #%02x%02x%02x  %7.3f%%"%(*cols[i],100*counts[i]/len(a)))
