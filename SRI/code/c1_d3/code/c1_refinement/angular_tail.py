"""Sign-aware odd radial-state tail envelope.
Uses positive normalized radial-state coefficients; no spin/spectrum fit.
For j>J, NIST DLMF 18.14.7 at lambda=1/2 bounds Legendre polynomials.
For continuous radial exponent use a second-derivative interpolation remainder.
Quadrature values remain numerical rather than interval-certified.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,numpy as np
from pathlib import Path
from scipy.special import roots_legendre,eval_legendre
from crossing_envelope import Envelope,BASE,rho,radialP,S,E

def moment_bound(env,n=100,J=64,step=.1,span=60):
 gap=env.go;q,w=roots_legendre(n);u=(q+1)/2;ww=[];rr=[];ee=[]
 for lo,hi in [(0,.5),(.5,1.)]:
  if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
  else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
  mx=np.minimum(1,1/(2*r));eta=-1+(mx[:,None]+1)*(q[None,:]+1)/2
  z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
  wg=2*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*w[None,:]/2
  rh=rho(z);ra=abs(rh)
  W=2*np.pi*wg*2*v**(-(3-S))*r[:,None]**(-S-E)/radialP(rh)
  rr.extend(ra.ravel());ee.extend((rh.real/ra).ravel());ww.extend(W.ravel())
 rr=np.array(rr);eta=np.array(ee);ww=np.array(ww)
 jj=np.arange(J+1);es=gap+np.arange(round(span/step)+1)*step
 refbase=.3;P=np.array([eval_legendre(j,eta) for j in jj]);M=[]
 for ebatch in np.array_split(es,20):
  radial=np.exp(np.outer(ebatch,np.log(rr/refbase)))
  M.extend(-(radial*ww)@P.T)
 M=np.array(M)
 # Guaranteed bound for every angular spin j>=J+1.
 hb=np.minimum(1,np.sqrt(2/(np.pi*(J+1.5)*np.sqrt(1-eta**2))))
 results=[]
 for x,B in zip(env.xo,env.Bodd):
  ref=rho(x)
  if ref<=2-np.sqrt(3):continue
  vals=M*(refbase/ref)**es[:,None]
  curv=np.sum(ww*(rr/ref)**gap*np.log(rr/ref)**2)*step**2/8
  highspin=np.sum(ww*(rr/ref)**gap*hb)
  negative=np.sum(ww*(rr/ref)**gap)
  highE=negative*((2-np.sqrt(3))/ref)**(gap+span-gap)
  upper=max(float(vals.max()+curv),highspin,highE)
  ix=np.unravel_index(np.argmax(vals),vals.shape)
  results.append(dict(x=float(x),rref=float(ref),reference_bound=float(B),
   sampled_upper=float(vals.max()),max_at_radial_exponent=float(es[ix[0]]),max_at_j=int(jj[ix[1]]),
   exponent_interpolation_allowance=float(curv),high_spin_allowance=float(highspin),high_exponent_allowance=float(highE),
   upper_kernel=float(upper),odd_integral_upper=float(B*upper),odd_integral_lower=float(-B*negative)))
 best=min(results,key=lambda d:d['odd_integral_upper'])
 return dict(quadrature=n,J=J,step=step,span=span,anchors=results,best_upper=best,all_j_and_continuous_exponents_covered_analytically_up_to_quadrature=True)
if __name__=='__main__':
 n=int(sys.argv[1]) if len(sys.argv)>1 else 100
 env=Envelope(8,7,level=40);lp=np.load(BASE/'final_8_7_pad1_lp.npz');env.A=lp['A'];env.B=lp['B'];env.Beven=lp['Beven'];env.Bodd=lp['Bodd']
 o=moment_bound(env,n);json.dump(o,open(BASE/f'angular_tail_{n}.json','w'),indent=2)
 print(o['best_upper'])
