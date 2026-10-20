"""EXPLORATORY positivity remainder bounds, not a certified result."""
import numpy as np,json
from scipy.special import gammaln
from spectrum import get_rows,S,E
from kernels import cb

def rho(x):return x/(1+np.sqrt(1-x))**2
def radialP(r):return ((1+r)/(1-r))**(2*(E-S))
rows=get_rows()
xs=np.linspace(.10,.49,60)

def blocks(rows,x,y=None,level=32):
 out=[]
 for p in rows:
  l=p['ell']; fac=np.exp(gammaln(l+1)-gammaln(l+.5)+gammaln(.5))
  da,db=(0.,0.) if p['sector']=='even' else(E-S,S-E)
  out.append(fac*cb.Block(p['Delta'],l,level,da,db)(x))
 return np.array(out)

ev=[p for p in rows if p['sector']=='even'];od=[p for p in rows if p['sector']=='odd']
Gs=blocks(ev,xs);Gl=blocks(ev,1-xs)

def bound_at(rr,typ='sigma',nsig=2.,gap=5.):
 D=S if typ=='sigma' else E;key='f' if typ=='sigma' else'h'
 A=(xs/(1-xs))**(2*D);q=rho(xs)/rho(1-xs)
 residual=1/A-1;unc=np.zeros(len(xs))
 for p,gs,gl in zip(ev,Gs,Gl):
  k=gs/A-gl;c=p[key];ce=p[key+'_error']
  residual+=c*c*k
  unc+=abs(k)*(2*abs(c)*ce+nsig*ce*ce) # multiplied nsig below
  de=p['Delta_error']
  if de and p['Delta']>2:
   pp=dict(p);pp['Delta']+=de;pm=dict(p);pm['Delta']-=de
   gp=blocks([pp],xs)[0]/A-blocks([pp],1-xs)[0]
   gm=blocks([pm],xs)[0]/A-blocks([pm],1-xs)[0]
   unc+=c*c*np.abs(gp-gm)/2
 den=1-q**gap/A
 bounds=(residual+nsig*unc)/den*(rr/rho(1-xs))**gap
 bounds=np.where((rho(1-xs)>=rr)&(den>0),bounds,np.inf)
 i=np.argmin(bounds)
 return dict(value=float(bounds[i]),xref=float(xs[i]),frozen_residual=float(residual[i]),input_padding=float(nsig*unc[i]))

if __name__=='__main__':
 for rr in [.09,.15,.268,.35]:
  vals={k:bound_at(rr,k) for k in ['sigma','epsilon']};print(rr,vals,flush=True)
 for x in [.6,.667,.7,.75]:
  r=rho(x);y=1-x;ry=rho(y)
  bs=bound_at(ry,'sigma')['value'];be=bound_at(ry,'epsilon')['value']
  G=blocks(ev,np.array(y))
  mixed=1+sum(p['f']*p['h']*g for p,g in zip(ev,G))
  Go=blocks(od,np.array(x));odd=sum(p['f']**2*g for p,g in zip(od,Go))
  fac=x**(S+E)*y**(-2*S)
  val=(fac*mixed-odd)*radialP(r);corr=fac*np.sqrt(max(0,bs*be))*radialP(r)
  # rough correlated OPE-only interval padding for difference
  pad=0.
  for p,g in zip(ev,G):pad+=fac*(abs(p['f'])*p['h_error']+abs(p['h'])*p['f_error'])*g
  for p,g in zip(od,Go):pad+=2*abs(p['f'])*p['f_error']*g
  print('odd',x,'rho',r,'mismatch',val,'tail_pad',corr,'data_pad',2*radialP(r)*pad,'bound',val+corr+2*radialP(r)*pad,flush=True)
