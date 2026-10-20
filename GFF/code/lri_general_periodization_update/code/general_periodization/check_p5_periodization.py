import sys,json,time
from pathlib import Path
import numpy as np
import mpmath as mp
from scipy.special import loggamma,gammaln
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from primitive_spectral import euler,terms as spectral_terms
from check_wheel_periodization import residue_weights
mp.mp.dps=50

def deg(q,l):
    if l==0:return 1.
    return (2*l+4*q-2)*np.exp(gammaln(l+4*q-2)-gammaln(4*q-1)-gammaln(l+1))

def mtheta(theta,v):
    v=np.asarray(v,dtype=complex)
    v=np.where(v.real<0,-v,v)
    f=-np.sin(np.pi*v)/np.sin(np.pi*(theta-v))
    return f*np.exp(loggamma(theta+v)+loggamma(1+v)-loggamma(v)-loggamma(1+v-theta))

def right(q,l,t,N):
    n=np.arange(N,dtype=float)
    lg=loggamma(l+q+n+t)-loggamma(l+2*q+n+t)+loggamma(1-q+n+t)-loggamma(1+n+t)
    g=-np.sin(np.pi*(q-t))/np.sin(np.pi*t)*np.exp(lg)
    v=l+q+2*n+2*t
    return (mtheta(2*q,v)+l*(l+4*q-2)*mtheta(2*q-1,v))*g**7

def fixed_l(q,l,t,N):
    ans=np.sum(right(q,l,t,N),dtype=np.clongdouble)+np.sum(right(q,l,1-q-t,N),dtype=np.clongdouble)
    if l:
        j=np.arange(l,dtype=float);k=l-j-1
        lg=loggamma(k+q+t)-loggamma(k+2*q+t)+loggamma(j+1-t)-loggamma(j+1+q-t)
        v=k-j-1+q+2*t
        ans+=np.sum((mtheta(2*q,v)+l*(l+4*q-2)*mtheta(2*q-1,v))*np.exp(7*lg),dtype=np.clongdouble)
    return ans*deg(q,l)

def eulerc(a,start=14,depth=90):
    seq=np.asarray(a[start:start+depth],dtype=np.clongdouble)
    v=np.sum(np.asarray(a[:start],dtype=np.clongdouble)*(-1)**np.arange(start))
    tail=np.clongdouble(0);fac=np.longdouble(.5)
    while len(seq):
        tail+=seq[0]*fac;seq=seq[:-1]-seq[1:];fac*=.5
    return v+(-1)**start*tail

def xi(q,t,N,spins):
    vals=[fixed_l(q,l,t,N) for l in range(spins)]
    return (np.sin(np.pi*t)*np.sin(np.pi*(t+q)))**7*eulerc(vals,14,min(90,spins-14))

def calculate(q,N=512,spins=128):
    r=7;eta=1/(8*mp.pi*r);Ngrid=2*r-1
    ts=[complex(-q/2+j/Ngrid,float(eta)) for j in range(r)]
    vals=[xi(q,t,N,spins) for t in ts]
    ys=[mp.mpf(str(v.real)) for v in vals]
    c=mp.matrix(r,1)
    c[0]=(ys[0]+2*sum(ys[1:]))/Ngrid
    for k in range(1,r):
        c[k]=2*(ys[0]+2*sum(ys[j]*mp.cos(2*mp.pi*k*j/Ngrid) for j in range(1,r)))/(Ngrid*mp.cosh(2*mp.pi*k*eta))
    v=-mp.gamma(2*q)**5/(2*(mp.pi*mp.sin(mp.pi*q))**7)*sum(c[k]*residue_weights(mp.mpf(str(q)),7)[k] for k in range(r))
    t=complex(-q/2+.071,.039)
    observed=xi(q,t,N,spins)
    predicted=sum(c[k]*mp.cos(2*mp.pi*k*(mp.mpc(t)+q/2)) for k in range(r))
    spec=euler(spectral_terms(4*q,[5],spins=160,nodes=640)[5],start=14,depth=90)
    return {'q':q,'d':4*q,'radial_terms_each_tail':N,'spins':spins,'P5':str(v),'fresh_spectral_value':spec,'difference':str(v-spec),'off_grid_residual':str(mp.mpc(complex(observed))-predicted),'samples':[str(v) for v in vals]}

if __name__=='__main__':
    rows=[]
    for q,N in [(0.75,384),(0.75,768),(0.6,768),(0.6,1536)]:
        st=time.time();v=calculate(q,N);v['seconds']=time.time()-st;rows.append(v);print(v,flush=True)
        Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/p5_periodization.json').write_text(json.dumps({'scope':'Double-precision quadrature and gamma-ratio summation controls; no certified error bound','rows':rows},indent=2))
