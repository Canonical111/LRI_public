"""Exact finite two-index spectral sums and their full cutoff sequence."""
import numpy as np
from scipy.fft import rfft,irfft,next_fast_len
from scipy.signal import fftconvolve
from math import pi
from resummed import CHI,coeff,inv,shift_multiply,descendant_polys,CENT_E,SIDE_E,ROOT
from improved_regulator import trunc_exp

def make_matrix(a,b,c,symmetric=False):
 K=len(a);out=np.empty((K,K))
 for d in range(K):
  L=K-d;M=next_fast_len(2*L-1);fk=rfft(c[:L],n=M)
  pos=irfft(rfft(a[d:]*b[:L],n=M)*fk,n=M)[:L]
  ii=np.arange(L);out[ii+d,ii]=pos
  if d:
   if symmetric:out[ii,ii+d]=pos
   else:out[ii,ii+d]=irfft(rfft(a[:L]*b[d:],n=M)*fk,n=M)[:L]
 return out

def run(lam,order=0,N=2048):
 K=N+1;q=np.exp(-lam);chi=coeff(CHI,K)*q**np.arange(K)*trunc_exp(lam*(np.arange(K)+CHI/2),order)
 half=coeff(.5,K);negative=coeff(-3/8,K);line=fftconvolve(negative,chi)[:K]
 dc,ds=descendant_polys();n=np.arange(N,dtype=float);fac=(2*pi)**3*q**CHI;parts=[]
 for name,pe,pd in [('central',CENT_E,dc),('side',SIDE_E,ds)]:
  G=make_matrix(half,half,line,True) if name=='central' else make_matrix(half,line,half)
  E=shift_multiply(G,pe)/(2*np.sqrt(2));D=shift_multiply(G,pd)/(2*np.sqrt(2))
  e=E[:N,:N];d=D[1:N+1,1:N+1]
  if name=='central':dv1=dv2=inv(2*n+2);de1=de2=inv(2*n+1)
  else:dv1=inv(2*n+1);dv2=inv(2*n+2);de1=inv(2*n-1);de2=inv(2*n+1)
  work=(2*e-d)*e;work*=de1[:,None];work*=de2[None,:]
  tmp=G[:N,:N]**2/2;tmp*=dv1[:,None];tmp*=dv2[None,:];work-=tmp
  del tmp,G,E,D,e,d
  np.cumsum(work,axis=0,out=work);np.cumsum(work,axis=1,out=work)
  ii=np.arange(N);seq=fac*work[ii,ii]
  parts.append(dict(ordering=name,X=seq.tolist()));del work
 return dict(lam=lam,order=order,Nmax=N,parts=parts,Xmixed=(np.array(parts[0]['X'])+2*np.array(parts[1]['X'])).tolist())

def extrapolate(seq):
 y=np.asarray(seq);N=len(y);out=[]
 for pp in [[1,2],[1,2,2.75],[1,2,3],[1,2,2.75,3],[1,2,3,4],[1,2,2.75,3,4]]:
  for frac in [.25,.4,.5,.625,.75]:
   n=np.arange(int(frac*N),N+1);u=n/N;A=np.array([np.ones_like(u)]+[u**(-p) for p in pp]).T
   c=np.linalg.lstsq(A,y[n-1],rcond=None)[0];err=np.max(abs(A@c-y[n-1]));out.append(dict(powers=pp,Nmin=int(n[0]),limit=float(c[0]),max_residual=float(err)))
 return out

if __name__=='__main__':
 import json
 import resummed_improved as r
 out=[]
 for order,a in [(0,.5),(2,.25)]:
  r.ORDER=order;x=run(a,order,64)
  for n in [8,16,32,64]:
   y=r.mixed(a,n);err=x['Xmixed'][n-1]-y['Xmixed'];out.append(dict(order=order,lam=a,N=n,error=err));print(out[-1])
 (ROOT/'mixed_sequence_checks.json').write_text(json.dumps(out,indent=2))
