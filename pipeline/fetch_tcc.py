import json,os,time,urllib.request,urllib.parse,sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
g=json.load(open('base/grid.json'))
W,H=g['W'],g['H']; mxa,mxb,mya,myb=g['mxa'],g['mxb'],g['mya'],g['myb']
URL='https://www.mrlc.gov/geoserver/wms?'
CW,CH=3,2
out=np.zeros((H,W),dtype=np.uint8)
for cj in range(CH):
    for ci in range(CW):
        px0=W*ci//CW; px1=W*(ci+1)//CW; py0=H*cj//CH; py1=H*(cj+1)//CH
        bx0=mxa+(mxb-mxa)*px0/W; bx1=mxa+(mxb-mxa)*px1/W
        by1=myb-(myb-mya)*py0/H; by0=myb-(myb-mya)*py1/H
        p={'service':'WMS','version':'1.3.0','request':'GetMap',
           'layers':'nlcd_tcc_conus_2021_v2021-4','styles':'','crs':'EPSG:3857',
           'bbox':'%f,%f,%f,%f'%(bx0,by0,bx1,by1),
           'width':str(px1-px0),'height':str(py1-py0),'format':'image/png'}
        f='base/tcc_%d_%d.png'%(ci,cj)
        if not os.path.exists(f):
            for a in range(4):
                try:
                    rq=urllib.request.Request(URL+urllib.parse.urlencode(p),headers={'User-Agent':'gmu44/1.0'})
                    d=urllib.request.urlopen(rq,timeout=180).read()
                    if d[:4]!=b'\x89PNG': raise RuntimeError(str(d[:120]))
                    open(f,'wb').write(d); break
                except Exception as e:
                    print("  retry %d %s"%(a,str(e)[:90])); time.sleep(4)
            else: sys.exit("FAILED "+f)
        im=Image.open(f)
        assert im.mode=='P', (f,im.mode)          # indices are the canopy percent
        a=np.asarray(im)
        assert a.shape==(py1-py0,px1-px0),(f,a.shape)
        out[py0:py1,px0:px1]=a
        print("  chunk %d,%d %s  max %d%%"%(ci,cj,a.shape,a.max()))
np.save('base/tcc.npy',out)
print("canopy: mean %.1f%%   bare(0) %.1f%%   >=50%% %.1f%%   max %d%%"%(
    out.mean(),100*(out==0).mean(),100*(out>=50).mean(),out.max()))
