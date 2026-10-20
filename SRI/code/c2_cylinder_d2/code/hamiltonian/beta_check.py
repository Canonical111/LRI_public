import numpy as np,json,time
from scipy.fft import fft,next_fast_len
from scipy.signal import fftconvolve
from resummed import coeff,two_point,CHI,ROOT
from math import pi

def run(N=200000):
 M=next_fast_len(5*N);r=np.exp(-4/N);z=r*np.exp(2j*pi*np.arange(M)/M)
 t=np.sqrt(1-z)
 f0=(1-z)**(-1/8)*np.sqrt((1+t)/2)
 f1=(1-z)**(-1/8)/np.sqrt(2*(1+t))
 fac=np.exp(4*np.arange(N)/N)
 f0=(fft(f0)[:N]/M*fac).real;f1=(fft(f1)[:N]/M*fac).real
 rows=[]
 for a in [.25,.15,.1,.075,.05,.025,.0125]:
  q=np.exp(-a);nn=min(N,int(60/a)+100);c=coeff(CHI,nn)*q**np.arange(nn)
  g0=fftconvolve(f0,c)[:N];g1=fftconvolve(f1,c)[:N];n=np.arange(N)
  E=-4*pi*pi*q**CHI*np.sum(g0*g0/(2*n+7/4)+g1*g1/(2*n+11/4))
  b=two_point(a,N)
  val=E-b['states'][0]['E2']+pi*b['t2']+b['k2']/8
  row=dict(lam=a,N=N,E2sigma=float(E),gap2=float(E-b['states'][0]['E2']),t2=b['t2'],k2=b['k2'],beta_diagnostic=float(val))
  print(row,flush=True);rows.append(row)
 (ROOT/'beta_check.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':run()
