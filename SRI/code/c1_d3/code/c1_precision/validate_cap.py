"""Exact generalized-free-field and integrated boundary checks for disk/cap split."""
from pathlib import Path
import json, numpy as np
from scipy.special import roots_legendre,binom
from spectrum import S,get_rows
from kernels import cb,crossing_rows
from alternative_domain import CapFunctional

def gff(h,S=S,r0=.12,nr=180,na=160):
 q,w=roots_legendre(nr);qa,wa=roots_legendre(na);u=(q+1)/2;total=0.
 for lo,hi in [(0,1-h),(1-h,1)]:
  if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
  else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
  mx=np.minimum(1,(1+r*r-h*h)/(2*r));eta=-1+(mx[:,None]+1)*(qa[None,:]+1)/2
  v=1-2*r[:,None]*eta+r[:,None]**2
  total+=np.sum(4*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*wa[None,:]/2*v**(-(3-S))*(1+r[:,None]**(-2*S)))
 p=2-2*S;pol=np.array([(-1)**(k+1)*binom(p,k)/p for k in range(1,45)])
 pol[0]+=1;pol[1]-=.5
 small=4*np.pi*sum(a*r0**(2*S-3+n)/(2*S-3+n) for n,a in enumerate(pol))
 r=r0+(h-r0)*u;wr=(h-r0)*w/2
 J=1-r/2+(1-(1-r)**p)/(p*r)
 total+=small+4*np.pi*np.sum(wr*r**(2*S-4)*J)
 return float(total)

def boundary(h,n=180):
 eta,w=roots_legendre(n);eta=h/2+(1-h/2)*(eta+1)/2;w=w*(1-h/2)/2
 y=h*(eta+1j*np.sqrt(1-eta**2));x=1-y
 cr=crossing_rows(get_rows(),x,level=32)
 # crossed = even channel, direct = original odd channel
 deriv={}
 for k in ['sigma','mixed']:
  diff=np.array(cr[k]['crossed'])-np.array(cr[k]['direct'])
  # for sigma crossing_rows(x) is right order, as external dimensions all equal
  deriv[k]=float(-2*np.pi*4*np.pi*h**(2-2*(3-S))*np.sum(w*diff))
 return deriv

if __name__=='__main__':
 vals={str(h):gff(h) for h in [.45,.6,.7,.8,.9]}
 print('GFF I analytically zero:',vals,flush=True)
 bs={str(h):boundary(h) for h in [.5,.7,.8,.9]};print('boundary',bs,flush=True)
 json.dump(dict(gff=vals,boundary=bs),open(Path(__file__).resolve().parent/'cap_validation.json','w'),indent=2)
