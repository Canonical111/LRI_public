"""Conditional remainder estimate probe. NOT a certified bootstrap interval.
The quoted CFT errors are NOT rigorous and the odd gap is an explicit assumption.
Finite dimension differences are first-order sensitivity pads, not interval arithmetic.
"""
from pathlib import Path
from tail_probe import *
from scipy.special import roots_legendre

def prep_even(typ,nsig=2.,gap=5.):
 D=S if typ=='sigma' else E;key='f' if typ=='sigma' else'h'
 A=(xs/(1-xs))**(2*D);q=rho(xs)/rho(1-xs)
 residual=1/A-1;unc=np.zeros(len(xs))
 for p,gs,gl in zip(ev,Gs,Gl):
  k=gs/A-gl;c=p[key];ce=p[key+'_error'];residual+=c*c*k
  unc+=abs(k)*(2*abs(c)*ce+nsig*ce*ce)
  de=p['Delta_error']
  if de and p['Delta']>2:
   pp=dict(p);pp['Delta']+=de;pm=dict(p);pm['Delta']-=de
   gp=blocks([pp],xs)[0]/A-blocks([pp],1-xs)[0]
   gm=blocks([pm],xs)[0]/A-blocks([pm],1-xs)[0]
   unc+=c*c*np.abs(gp-gm)/2
 rr=rho(1-xs);B=(residual+nsig*unc)/(1-q**gap/A)
 def fun(r):
  r=np.asarray(r); v=B*(r[...,None]/rr)**gap
  v=np.where(rr>=r[...,None],v,np.inf)
  return np.min(v,axis=-1)
 return fun

def oddbound(x,fs,fe,nsig=2):
 r=rho(x);y=1-x;ry=rho(y);G=blocks(ev,np.array(y));Go=blocks(od,np.array(x))
 mixed=1+sum(p['f']*p['h']*g for p,g in zip(ev,G));odd=sum(p['f']**2*g for p,g in zip(od,Go));fac=x**(S+E)*y**(-2*S)
 residual=(fac*mixed-odd)*radialP(r)
 pad=0.
 for p,g in zip(ev,G):
  pad+=fac*(abs(p['f'])*p['h_error']+abs(p['h'])*p['f_error']+nsig*p['f_error']*p['h_error'])*abs(g)
  de=p['Delta_error']
  if de and p['Delta']>2:
   pp=dict(p,Delta=p['Delta']+de);pm=dict(p,Delta=p['Delta']-de)
   pad+=fac*abs(p['f']*p['h'])*(abs(blocks([pp],np.array(y))[0]-blocks([pm],np.array(y))[0]))/2
 for p,g in zip(od,Go):
  pad+=(2*abs(p['f'])*p['f_error']+nsig*p['f_error']**2)*abs(g)
  de=p['Delta_error']
  if de and p['Delta']>2:
   pp=dict(p,Delta=p['Delta']+de);pm=dict(p,Delta=p['Delta']-de)
   pad+=p['f']**2*abs(blocks([pp],np.array(x))[0]-blocks([pm],np.array(x))[0])/2
 b=residual+radialP(r)*(fac*np.sqrt(fs(ry)*fe(ry))+nsig*pad)
 return float(r),float(b)

def integrate_tails(fs,fe,ob,gap,nr=100,na=100):
 q,w=roots_legendre(nr);qa,wa=roots_legendre(na);u=(q+1)/2;out=np.zeros(3)
 for lo,hi in [(0,.5),(.5,1.)]:
  if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
  else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
  mx=np.minimum(1,1/(2*r));eta=-1+(mx[:,None]+1)*(qa[None,:]+1)/2
  z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
  wg=2*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*wa[None,:]/2
  rh=z/(1+np.sqrt(1-z))**2;rr=abs(rh)
  rs=fs(rr);re=fe(rr);rmix=np.sqrt(rs*re)
  ro=np.min(np.array([b*(rr/r0)**gap for r0,b in ob]),axis=0)
  P=(abs(1+rh)/abs(1-rh))**(2*(E-S));ro/=P
  sig=wg*(2*v**(-(3-S))*r[:,None]**(-2*S)+r[:,None]**(-6))*rs
  eps_even=wg*r[:,None]**(-6)*rmix
  eps_odd=wg*2*v**(-(3-S))*r[:,None]**(-S-E)*ro
  out+=2*np.pi*np.array([sig.sum(),eps_even.sum(),eps_odd.sum()])
 return out

if __name__=='__main__':
 fs=prep_even('sigma');fe=prep_even('epsilon');ob=[oddbound(x,fs,fe) for x in [2/3,.68,.7,.75,.8]]
 print('odd anchor',ob,flush=True)
 out=[]
 for gap in [2,4,6,7,8]:
  eb,ee,eo=integrate_tails(fs,fe,ob,gap)
  print('gaps even5 odd',gap,'tail estimates',eb,ee,eo,'deltaC1',(ee+eo+.2731524*eb)/12.2549141,flush=True)
  out.append(dict(even_gap=5,odd_gap=gap,b_tail_estimate=eb,a_even_tail_estimate=ee,a_odd_tail_estimate=eo,C1_tail_estimate=(ee+eo+.2731524*eb)/12.2549141))
 json.dump(dict(anchors=ob,cases=out,status='exploratory conditional estimates NOT rigorous bounds'),open(Path(__file__).resolve().parent/'tail_estimates.json','w'),indent=2)
