import numpy as np
from fitlib import *
R=load(); L=np.array(list(R.keys()),float)
print('L:',L.min(),'..',L.max(),'n',len(L))
def series(var,key,k):
    return np.array([R[int(l)]['variants'][var][key][k] for l in L])
models3=['h,1','h,1,3h','hl,h','hl,h,1','hl,h,1,1l']
models4=['hl,h,1','hl,h,1,1l','hl2,hl,h','hl2,hl,h,1','hl2,hl,h,1,1l']
for key in ['spacing_d1','spacing_d2']:
  for k,models in ((3,models3),(4,models4)):
    for var in (['raw','g2D','Dfull_c'] if k==3 else ['raw','g2D','Dfull_c','Dfull_raw']):
        y=series(var,key,k)
        print(f'--- {key} eps^{k} {var}: last={y[-1]:+.6f}   intercepts for Lmin=12,16,20,24,32,40')
        for mname in models:
            out=[]
            for Lmin in [12,16,20,24,32,40]:
                c,res,n=fit(L,y,MODELS[mname],Lmin)
                out.append(f'{c[0]:+.5f}')
            print(f'   {mname:16s}', ' '.join(out))
