"""Direct delta derivative of second-order spectral X; no finite-delta fit."""
import numpy as np,json
from scipy.signal import fftconvolve
from scipy.special import digamma
from math import pi
from resummed import ROOT,coeff,CHI
from improved_regulator import trunc_exp

def derivative(lam,order=0,N=200000):
    m=min(N,int((65+10*order)/lam)+100);j=np.arange(m,dtype=float);q=np.exp(-lam);xx=lam*(j+CHI/2)
    c=coeff(CHI,m)*q**j;P=trunc_exp(xx,order)
    cp=-c*(P*(digamma(CHI+j)-digamma(CHI))+(lam/2*trunc_exp(xx,order-1) if order else 0))
    c*=P;ci=coeff(1/8,N);ff=[];fp=[]
    for poly in [[1.],[.5,.5],[.125,.375,.375,.125]]:
        a=np.convolve(ci,poly)[:N];ff.append(fftconvolve(a,c)[:N]);fp.append(fftconvolve(a,cp)[:N])
    ee=[];dd=[];fac=4*pi*pi*q**CHI
    for a,(l,r,s) in enumerate([(0,0,0),(1,1,0),(2,1,1)]):
        num=N-s;n=np.arange(num,dtype=float);de=2*n+(2 if a==0 else 1)
        f=ff[l][s:s+num]*ff[r][:num]
        g=fp[l][s:s+num]*ff[r][:num]+ff[l][s:s+num]*fp[r][:num]
        ee.append(float(-fac*np.sum(f/de)))
        dd.append(float(-fac*np.sum((lam*f+g)/de+f/de**2)))
    return dict(lam=lam,order=order,N=N,X2=2*ee[1]-ee[2]-ee[0],a1=2*dd[1]-dd[2]-dd[0],state_derivatives=dd)
if __name__=='__main__':
 out=[]
 for k in [0,1,2]:
  for a in [.1,.05,.025,.0125,.00625]:
   d=derivative(a,k);print(d,flush=True);out.append(d)
 (ROOT/'slope_check.json').write_text(json.dumps(out,indent=2))
