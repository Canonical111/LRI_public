import numpy as np,json
from scipy.fft import fft,next_fast_len
from scipy.signal import fftconvolve
import resummed_improved as ri
from improved_regulator import trunc_exp,planar_constants
from math import pi
N=150000;M=next_fast_len(5*N);r=np.exp(-4/N);z=r*np.exp(2j*pi*np.arange(M)/M)
t=np.sqrt(1-z);fac=np.exp(4*np.arange(N)/N)
f0=(fft((1-z)**(-1/8)*np.sqrt((1+t)/2))[:N]/M*fac).real
f1=(fft((1-z)**(-1/8)/np.sqrt(2*(1+t)))[:N]/M*fac).real
rows=[]
for k in [0,1,2,3]:
 ri.ORDER=k;con=planar_constants(k,256)
 for a in [.5,.25,.125,.0625,.03125]:
  q=np.exp(-a);nn=min(N,int((60+10*k)/a)+100);c=ri.coeff(ri.CHI,nn)*q**np.arange(nn)*trunc_exp(a*(np.arange(nn)+ri.CHI/2),k)
  g0=fftconvolve(f0,c)[:N];g1=fftconvolve(f1,c)[:N];n=np.arange(N)
  E=-4*pi*pi*q**ri.CHI*np.sum(g0*g0/(2*n+7/4)+g1*g1/(2*n+11/4))
  b=ri.two_point(a,N)
  beta0=E-b['states'][0]['E2']+pi*con['ct']/a-con['kappa']/8
  betam=E-b['states'][0]['E2']+pi*b['t2']+b['k2']/8
  row=dict(order=k,lam=a,beta_planar=float(beta0),beta_matched=float(betam),planar=con,t2=b['t2'],k2=b['k2'])
  print(row,flush=True);rows.append(row)
 (ri.ROOT/'beta_improved.json').write_text(json.dumps(rows,indent=2))
