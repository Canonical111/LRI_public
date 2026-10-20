"""Angular-tail acceleration and independent finite-node controls.
The tail uses the even inverse-spin expansion forced by centered Gamma ratios.
The numerical fit is only a quadrature acceleration, not a conjectured identity.
"""
import numpy as np,mpmath as mp,json,time
from scipy.special import digamma,polygamma,gammaln,loggamma,roots_legendre
from pathlib import Path
from wheel_spectrum import terms,kterms

def tailfit(d,col,L=256,nodes=384,orders=3):
    # n=l+(d-2)/2 is the natural centered spin.
    shift=(d-2)/2
    scales=np.geomspace(.4,1.4,24)*L
    ls=np.unique(np.round(scales-shift).astype(int));ns=ls+shift
    if col==4:vals=kterms(d,ls,nodes)
    else:vals=terms(d,ls,nodes)[col]
    powers=[d/2+1,d+1,d+1,d/2+1,3]
    degrees=[0,0,1,2,1]
    p=powers[col];kmax=degrees[col]
    X=[]
    for j in range(orders):
      for k in range(kmax+1):X.append((L/ns)**(2*j)*np.log(ns/L)**k)
    X=np.array(X).T
    coef=np.linalg.lstsq(X,vals*ns**p,rcond=None)[0]
    mp.mp.dps=40
    z=mp.mpf(L)+mp.mpf(str(shift));logL=mp.log(L)
    total=mp.mpf(0)
    for j in range(orders):
      for k in range(kmax+1):
        ss=mp.mpf(str(p))+2*j
        mom=sum(mp.binomial(k,h)*(-logL)**(k-h)*(-1)**h*mp.diff(lambda s:mp.zeta(s,z),ss,h) for h in range(k+1))
        total+=mp.mpf(float(coef[j*(kmax+1)+k]))*mp.mpf(L)**(2*j)*mom
    resid=np.max(np.abs(X@coef-vals*ns**p))
    return float(total),float(resid)

def evaluate(d,L=256,nodes=384,orders=3):
    base=terms(d,np.arange(L),nodes)[:4].sum(axis=1)
    base=np.r_[base,kterms(d,np.arange(L),nodes).sum()]
    tails=[];errs=[]
    for c in range(5):
        t,r=tailfit(d,c,L,nodes,orders);tails.append(t);errs.append(r)
    q=d/4;A=digamma(2*q)+digamma(1)-2*digamma(q)
    base[4]-=A*polygamma(2,q)/4
    out=base+tails
    return dict(d=d,spins=L,nodes=nodes,orders=orders,values=out.tolist(),tails=tails,fit_residuals=errs,
                labels=['W3','P4','L','Z','K'])

def zig2(loops=5,nodes=384,spins=128):
    xx,ww=roots_legendre(nodes);u=(xx+1)/2;ww=ww/2
    n=np.arange(spins)[:,None];a=n/2+.25;b=a+.5
    v=(a+b)/2*np.tan(np.pi*u/2);jac=(a+b)/2*(np.pi/2)/np.cos(np.pi*u/2)**2
    deg=np.where(n==0,1,2)
    val=deg/(2*np.pi)*(n*n+4*v*v)*np.exp((loops+2)*2*(loggamma(a+1j*v)-loggamma(b+1j*v)).real)
    ts=np.sum(val*jac*ww,axis=1)
    if loops%2:
        import sys
        sys.path.insert(0,str(Path(__file__).parent.parent))
        from primitive_spectral import euler
        return euler(ts),ts
    return ts.sum(),ts

if __name__=='__main__':
    rows=[]
    for d in [2,3,4]:
      for L,nodes,orders in [(128,384,2),(256,512,3),(512,768,3)]:
        tt=time.time();v=evaluate(d,L,nodes,orders);v['seconds']=time.time()-tt
        rows.append(v);print(v,flush=True)
    z2=[]
    for nodes in [192,384,768]:
      vs={str(L):zig2(L,nodes)[0] for L in [3,4,5]};vs['nodes']=nodes
      print('zig2',vs,flush=True);z2.append(vs)
    Path(__file__).with_name('spectral_master_values.json').write_text(json.dumps({'rows':rows,'zigzag_d2':z2},indent=2))
