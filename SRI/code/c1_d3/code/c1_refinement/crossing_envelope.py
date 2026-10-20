"""Crossing-constrained numerical OUTER relaxation for C1 input and tails.
No missing primary is fitted away. Real-axis positivity and complex crossing
inequalities retain nonzero omitted tails. Gaps are assumptions, not certified.
Affine errors are padded from sampled nonlinear evaluations, not intervals.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'c1_precision'))
import numpy as np
from scipy.optimize import linprog
from scipy.special import roots_legendre
from spectrum import S,E,get_rows
from runtime_config import load_reference,ratio_interval,OBJECTIVE_ALLOWANCE,EPSILONPRIME_WINDOW

def rho(x):return x/(1+np.sqrt(1-x))**2

def radialP(x):return (abs(1+x)/abs(1-x))**(2*(E-S))

class Envelope:
 def __init__(self,ge=8,go=7,level=32,use_reehorst=True,padfactor=1.,ngrid=0):
  b=np.load(BASE/f'basis_L{level}.npz'); self.z=b['z'];self.xs=b['xs'];self.xo=b['xo'];self.d0=b['d0'];self.J=b['J'];self.pad=b['pad']*padfactor;self.obj=b['obj'];self.meta=json.load(open(BASE/f'basis_L{level}.json'))
  self.ge=ge;self.go=go;self.bnds=[(-1,1) for q in self.obj];self.A=None;self.B=None;self.ngrid=ngrid
  if use_reehorst:
   k=self.meta['names'].index('even_ss1_l0_d3.82968:h')
   row=get_rows()[self.meta['parameters'][k]['row']]
   scale=self.meta['parameters'][k]['scale']; center=row['h']
   if scale<=0:raise ValueError('Nonpositive epsilon-prime parameter scale')
   lo,hi=EPSILONPRIME_WINDOW
   self.bnds[k]=(max(-1.,(lo-center)/scale),min(1.,(hi-center)/scale))
   if self.bnds[k][0]>self.bnds[k][1]:raise ValueError('Empty epsilon-prime input intersection')
  self.reference_C,self.reference_b,self.denominator_box=load_reference(BASE)
 def extrema(self,v):
  out=[]
  for sign in [1,-1]:
   rr=linprog(sign*v,A_ub=self.A,b_ub=self.B,bounds=self.bnds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
   if not rr.success:raise RuntimeError('LP infeasible or failed: '+rr.message)
   out.append(float(v@rr.x))
  return out
 def d_extrema(self,k,i):
  vals=self.extrema(self.J[k,i]);return self.d0[k,i]+np.array(vals)+self.pad[k,i]*np.array([-1,1])
 def anchors(self):
  xs=self.xs;r1=rho(xs);rr=rho(1-xs);n=len(xs);self.Beven=[]
  for k,D in enumerate([S,E]):
   mx=np.array([self.d_extrema(k,i)[1] for i in range(n)])
   den=1-(r1/rr)**self.ge*((1-xs)/xs)**(2*D)
   if not np.all(den>0):raise ValueError('Identical-channel anchor denominator must be positive')
   B=(1-xs)**(2*D)*mx/den
   if np.min(B)<-1e-9:raise RuntimeError(f'Negative upper remainder {k} {B.min()}')
   self.Beven.append(np.maximum(B,0)*1.001) # 0.1% allowance for tiny external-dimension dependence
  self.Bodd=[]
  for j,x in enumerate(self.xo):
   r=rho(x);y=1-x;ry=rho(y);i=n+j
   lower=self.d_extrema(2,i)[0]
   v=x**(S+E)*radialP(r)*(-lower+y**(-2*S)*np.sqrt(self.even(ry,0)*self.even(ry,1)))
   if v<-1e-9:raise RuntimeError(f'Negative odd bound {v}')
   self.Bodd.append(max(v,0)*1.001)
  self.Bodd=np.array(self.Bodd)
 def even(self,r,k):
  r=np.asarray(r);rr=rho(1-self.xs);vals=self.Beven[k]*(r[...,None]/rr)**self.ge
  vals=np.where(r[...,None]<=rr,vals,np.inf)
  return np.min(vals,axis=-1)
 def odd(self,r):
  r=np.asarray(r);rr=rho(self.xo);vals=self.Bodd*(r[...,None]/rr)**self.go
  vals=np.where(r[...,None]<=rr,vals,np.inf)
  return np.min(vals,axis=-1)
 def add_constraints(self):
  z=self.z;rz=rho(z);rzt=rho(1-z);rzabs=abs(rz);rtabs=abs(rzt)
  lims=[]
  for k,D in enumerate([S,E]):
   td=abs(z)**(-2*D)*self.even(rzabs,k);tt=abs(1-z)**(-2*D)*self.even(rtabs,k)
   lower=-(td+tt);upper=td+tt
   # Positivity plus assumed gap fixes the sign of identical crossing residual.
   real=abs(z.imag)<1e-14;lo=real&(z.real<.5);hi=real&(z.real>.5)
   x=np.minimum(z.real[real],1-z.real[real])
   factor=(rho(x)/rho(1-x))**self.ge*((1-x)/x)**(2*D)
   if np.any(factor>1+1e-13):
    raise ValueError('Real-axis sign sharpening requires radial suppression factor <= 1')
   lower[lo]=0;upper[lo]=tt[lo];upper[hi]=0;lower[hi]=-td[hi]
   lims.append((lower,upper))
  tmo=abs(z)**(-S-E)*self.odd(rzabs)/radialP(rz)
  tme=abs(1-z)**(-2*S)*np.sqrt(self.even(rtabs,0)*self.even(rtabs,1))
  lower=-(tmo+tme);upper=tmo+tme
  real=abs(z.imag)<1e-14;upper[real]=tme[real]
  lims.append((lower,upper))
  mat=[];rhs=[]
  for k,(lower,upper) in enumerate(lims):
   for i in range(len(z)):
    if self.ngrid and i>=len(self.xs)+len(self.xo) and (i-len(self.xs)-len(self.xo))%self.ngrid:continue
    if not np.isfinite(lower[i]+upper[i]):continue
    a=self.J[k,i];v=self.d0[k,i];p=self.pad[k,i]
    scale=max(abs(v),np.max(abs(a)),p,1e-10)
    mat.extend([a/scale,-a/scale]);rhs.extend([(upper[i]-v+p)/scale,(-lower[i]+v+p)/scale])
  a=np.array(mat);b=np.array(rhs)
  if self.A is None:self.A=a;self.B=b
  else:
   if not np.array_equal(self.A,a):raise RuntimeError('Crossing matrix changed during envelope iteration')
   self.B=np.minimum(self.B,b)
 def integral(self,n=80):
  q,w=roots_legendre(n);u=(q+1)/2;out=np.zeros(3)
  for lo,hi in [(0,.5),(.5,1.)]:
   if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
   else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
   mx=np.minimum(1,1/(2*r));eta=-1+(mx[:,None]+1)*(q[None,:]+1)/2
   z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
   wg=2*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*w[None,:]/2
   rh=rho(z);rr=abs(rh);rs=self.even(rr,0);re=self.even(rr,1);rm=np.sqrt(rs*re);ro=self.odd(rr)/radialP(rh)
   sig=wg*(2*v**(-(3-S))*r[:,None]**(-2*S)+r[:,None]**(-6))*rs
   ee=wg*r[:,None]**(-6)*rm;eo=wg*2*v**(-(3-S))*r[:,None]**(-S-E)*ro
   out+=2*np.pi*np.array([sig.sum(),ee.sum(),eo.sum()])
  return out
 def run(self,iterations=4):
  out=[];C=self.reference_C;b=self.reference_b
  for it in range(iterations+1):
   self.anchors();integ=self.integral();tail=(integ[1]+integ[2]+C*integ[0])/b
   oval=self.extrema(self.obj)
   # Provisional objective nonlinear pad, to be separately tested.
   objpad=OBJECTIVE_ALLOWANCE; dbmax=self.denominator_box+integ[0]
   Flo=oval[0]-objpad-tail;Fhi=oval[1]+objpad+tail
   interval=ratio_interval(C,b,Flo,Fhi,dbmax)
   out.append(dict(iteration=it,input_linear_C1_shift=oval,objective_nonlinear_allowance=objpad,
    tail_integrals=integ.tolist(),tail_C1=tail,interval=interval))
   json.dump(out,open(BASE/f'checkpoint_{self.ge:g}_{self.go:g}.json','w'),indent=2)
   np.savez_compressed(BASE/f'checkpoint_lp_{self.ge:g}_{self.go:g}.npz',A=self.A if self.A is not None else np.empty((0,len(self.obj))),B=self.B if self.B is not None else np.empty(0),Beven=self.Beven,Bodd=self.Bodd)
   print(self.ge,self.go,it,out[-1],flush=True)
   if it<iterations:self.add_constraints()
  pulls={}
  for name in ['even_ss1_l0_d3.82968:f','even_ss1_l0_d3.82968:h','even_ss1_l0_d3.82968:Delta','odd_se0_l3_d4.63804:f']:
   v=np.zeros_like(self.obj);v[self.meta['names'].index(name)]=1;pulls[name]=self.extrema(v)
  return dict(even_gap=self.ge,odd_gap=self.go,iterations=out,parameter_ranges= pulls,status='Conditional numerical outer relaxation; NOT rigorous or a confidence interval')
if __name__=='__main__':
 ge=float(sys.argv[1]) if len(sys.argv)>1 else 8.;go=float(sys.argv[2]) if len(sys.argv)>2 else 7.
 level=int(sys.argv[3]) if len(sys.argv)>3 else 32
 env=Envelope(ge,go,level=level);out=env.run(4)
 json.dump(out,open(BASE/f'envelope_{ge:g}_{go:g}_L{level}.json','w'),indent=2)
 np.savez_compressed(BASE/f'lp_{ge:g}_{go:g}_L{level}.npz',A=env.A,B=env.B,Beven=env.Beven,Bodd=env.Bodd)
