import json, glob, numpy as np
from scipy.optimize import least_squares
from fitlib import load, fit, MODELS
R=load()
D={L:{v:R[L]['variants'][v]['spacing_d1'] for v in R[L]['variants']} for L in R}
for f in glob.glob('d1_L*.json'):
    d=json.load(open(f)); D.setdefault(d['L'],{v:d['variants'][v]['spacing_d1'] for v in d['variants']})
D=dict(sorted(D.items())); L=np.array(list(D),float)
print('dphi data L=',int(L.min()),'..',int(L.max()),'n=',len(L))
def ser(v,k): return np.array([D[int(l)][v][k] for l in L])
# independent fits
for v in ['raw','g2D','Dfull_c','Dfull_raw']:
  for k,models in ((3,['h,1,3h','hl,h,1','hl,h,1,1l']),(4,['hl,h,1,1l','hl2,hl,h,1','hl2,hl,h,1,1l'])):
    if k==3 and v=='Dfull_raw': continue
    y=ser(v,k); out=[]
    for mn in models:
        for Lmin in [16,24,32,40]:
            c,res,n=fit(L,y,MODELS[mn],Lmin); out.append(c[0])
    out=np.array(out); print(f'{v:9s} eps^{k}: last={y[-1]:+.5f}  intercepts {np.round(out,4).tolist()}  -> median {np.median(out):+.4f}, range [{out.min():+.4f},{out.max():+.4f}]')
# joint eps-structured fit
def model(par,Lx,P,fix):
    i=0
    if fix: A2=A3=0.;A4=par[0];i=1
    else: A2,A3,A4=par[:3];i=3
    l=np.log(Lx); y2=A2+0*Lx; y3=A3+0*Lx; y4=A4+0*Lx
    for p in P:
        a,c2,c3,c4=par[i:i+4];i+=4;Lp=Lx**(-p)
        y2=y2+c2*Lp;y3=y3+(c3-a*c2*l)*Lp;y4=y4+(c4-a*c3*l+a*a*c2*l*l/2)*Lp
    return y2,y3,y4
def jfit(v,Lmin,P,fix):
    m=L>=Lmin; Lx=L[m]; Y=[ser(v,k)[m] for k in (2,3,4)]; w=[1/np.std(y) for y in Y]
    f=lambda par: np.concatenate([(model(par,Lx,P,fix)[i]-Y[i])*w[i] for i in range(3)])
    n=(1 if fix else 3)+4*len(P); best=None
    for a0 in [-1,0,1,2,3]:
        x0=np.zeros(n)
        for j in range(len(P)): x0[(1 if fix else 3)+4*j]=a0
        r=least_squares(f,x0,method='lm',max_nfev=20000)
        if best is None or r.cost<best.cost: best=r
    return best.x
for v in ['raw','g2D','Dfull_c']:
    out=[]
    for P in [(0.5,1,1.5),(0.5,1,1.5,2)]:
        for fix in ([True,False] if v=='Dfull_c' else [False]):
            for Lmin in [16,24,32]:
                x=jfit(v,Lmin,P,fix); out.append(x[0] if fix else x[2])
    out=np.array(out); print(f'JOINT {v:8s} A4: {np.round(out,4).tolist()} -> median {np.median(out):+.4f} range [{out.min():+.4f},{out.max():+.4f}]')
