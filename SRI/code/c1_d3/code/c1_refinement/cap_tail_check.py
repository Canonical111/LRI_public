"""Alternative integration-domain remainder check, not independent measurements."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,numpy as np
from scipy.special import roots_legendre
from crossing_envelope import Envelope,BASE,rho,radialP,S,E
from alternative_domain import CapFunctional
from spectrum import get_rows

def cap_tails(env,h,n=100):
 q,w=roots_legendre(n);u=(q+1)/2;out=np.zeros(3);maxrho=0.
 for lo,hi in [(0,1-h),(1-h,1.)]:
  if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
  else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
  mx=np.minimum(1,(1+r*r-h*h)/(2*r));eta=-1+(mx[:,None]+1)*(q[None,:]+1)/2
  wg=4*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*w[None,:]/2
  z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2;rh=rho(z);rr=abs(rh);maxrho=max(maxrho,float(rr.max()))
  out[0]+=np.sum(wg*v**(-(3-S))*r[:,None]**(-2*S)*env.even(rr,0))
  out[2]+=np.sum(wg*v**(-(3-S))*r[:,None]**(-S-E)*env.odd(rr)/radialP(rh))
 r=h*u**4;wr=4*h*u**3*w/2;eta=r[:,None]/2+(1-r[:,None]/2)*(q[None,:]+1)/2
 y=r[:,None]*(eta+1j*np.sqrt(1-eta**2));cw=4*np.pi*r[:,None]**(-4)*wr[:,None]*(1-r[:,None]/2)*w[None,:]/2
 rr=abs(rho(y));maxrho=max(maxrho,float(rr.max()));ss=env.even(rr,0);ee=env.even(rr,1)
 out[0]+=np.sum(cw*ss);out[1]+=np.sum(cw*np.sqrt(ss*ee))
 return 2*np.pi*out,maxrho
if __name__=='__main__':
 e=Envelope(8,7,40);lp=np.load(BASE/'final_8_7_pad1_lp.npz');e.A=lp['A'];e.B=lp['B'];e.Beven=lp['Beven'];e.Bodd=lp['Bodd'];out=[]
 for h in [.45,.5,.65,.7,.8]:
  tails,rmax=cap_tails(e,h);c=CapFunctional(h=h,level=32,nr=100,na=100).evaluate(get_rows())
  vals=dict(h=h,retained_C1=c['C1'],max_rho=rmax,tail_magnitudes=tails.tolist(),remainder_C1_scale=float((tails[1]+tails[2]+c['C1']*tails[0])/c['b']),status='Tail-only sensitivity, not full physical interval; no averaging of domain values')
  if not np.all(np.isfinite(tails)):raise RuntimeError('Nonfinite alternative-domain tail')
  out.append(vals);print(vals,flush=True)
 json.dump(out,open(BASE/'alternative_domain_tail_checks.json','w'),indent=2)
