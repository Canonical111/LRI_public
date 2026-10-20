import numpy as np, sys
from scipy.optimize import least_squares
from fitlib import load
R=load(); Lall=np.array(list(R.keys()),float)
def ser(var,key,k,L): return np.array([R[int(l)]['variants'][var][key][k] for l in L])
def model(par,L,P,fixA23):
    # par: [A2,A3,A4] (A2,A3 maybe fixed 0) + per j: a_j, c2,c3,c4
    i=0
    if fixA23: A2=A3=0.; A4=par[0]; i=1
    else: A2,A3,A4=par[:3]; i=3
    l=np.log(L); y2=A2+0*L; y3=A3+0*L; y4=A4+0*L
    for p in P:
        a,c2,c3,c4=par[i:i+4]; i+=4
        Lp=L**(-p)
        y2=y2+c2*Lp; y3=y3+(c3-a*c2*l)*Lp; y4=y4+(c4-a*c3*l+a*a*c2*l*l/2)*Lp
    return y2,y3,y4
def run(var,key,Lmin,P,fixA23,Lmax=99):
    L=Lall[(Lall>=Lmin)&(Lall<=Lmax)]
    Y=[ser(var,key,k,L) for k in (2,3,4)]
    # weight each order by its scale
    w=[1/np.std(y) for y in Y]
    def resid(par):
        m=model(par,L,P,fixA23)
        return np.concatenate([(m[i]-Y[i])*w[i] for i in range(3)])
    n=(1 if fixA23 else 3)+4*len(P)
    best=None
    for a0 in [-1,0,1,2,3]:
        x0=np.zeros(n); 
        for j in range(len(P)): x0[(1 if fixA23 else 3)+4*j]=a0
        r=least_squares(resid,x0,method='lm',max_nfev=20000)
        if best is None or r.cost<best.cost: best=r
    m=model(best.x,L,P,fixA23)
    mx=[np.max(np.abs(m[i]-Y[i])) for i in range(3)]
    return best.x, mx
for key in ['spacing_d1','spacing_d2']:
  for var in ['Dfull_c','g2D','raw']:
    print(f'=== {key} {var}')
    for P in [(0.5,1),(0.5,1,1.5),(0.5,1,1.5,2)]:
      for fix in ([True,False] if var=='Dfull_c' else [False]):
        out=[]
        for Lmin in [12,16,20,24,32]:
            x,mx=run(var,key,Lmin,P,fix)
            A=(x[0],) if fix else tuple(x[:3])
            out.append(('A4=%+.4f'%A[-1])+('' if fix else ' A2=%+.1e A3=%+.4f'%(A[0],A[1]))+' maxres4=%.0e'%mx[2])
        print(f'  P={P} fixA23={fix}:'); [print('     Lmin',lm,o) for lm,o in zip([12,16,20,24,32],out)]
