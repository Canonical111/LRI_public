import numpy as np
from fitlib import *
R=load(); L=np.array(list(R.keys()),float)
def series(var,key,k):
    return np.array([R[int(l)]['variants'][var][key][k] for l in L])
print('Lmax',L.max(),'n',len(L))
for key in ['spacing_d1','spacing_d2','spacing_d3']:
    for var in ['raw','g2D']:
        y=series(var,key,2)
        print(f'--- {key} eps^2 {var}  (x54)')
        for mname in ['h,1','h,1,3h','hl,h,1','hl,h,1,1l']:
            out=[]
            for Lmin in [12,16,20,24,32]:
                c,res,n=fit(L,y,MODELS[mname],Lmin)
                out.append(f'{c[0]*54:+.5f}')
            print(f'   {mname:12s}', ' '.join(out))
