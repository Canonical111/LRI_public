import sympy as s
u,v=s.symbols('u v');P,S,z=s.symbols('P S z')
B0=S-2*z-2*P/z
B10=2*z*(S-z);B01=2*(S/z-P/z**2);B11=-2*S
QD=s.expand(B11+S*B01/2+S*B10/(2*P)+S*S*B0/(4*P))
print('QD=',QD)
for name,ss,pp,zz in [('central',1+u*v,u*v,u),('side',u*(1+v),u*u*v,1)]:
 print(name,'eps=',s.factor(B0.subs({S:ss,P:pp,z:zz})))
 print(name,'desc=',s.factor(u*v*QD.subs({S:ss,P:pp,z:zz})))

import numpy as np
from ising_basis import modes,spin_chiral,fermion

def polynomials(u,v,typ):
 if typ=='central':S=1+u*v;P=u*v;z=u
 else:S=u*(1+v);P=u*u*v;z=1
 B0=S-2*z-2*P/z;B10=2*z*(S-z);B01=2*(S/z-P/z**2)
 Q=-2*S+S*B01/2+S*B10/(2*P)+S*S*B0/(4*P)
 return B0,u*v*Q

def blocks(u,v,typ):
 B,Q=polynomials(u,v,typ)
 if typ=='central':D=(1-u*v)**(3/8)/np.sqrt((1-u)*(1-v))
 else:D=(1-v)**(3/8)/np.sqrt((1-u)*(1-u*v))
 return [D/np.sqrt(2),D*B/(2*np.sqrt(2)),D*Q/(2*np.sqrt(2))]

def check(N=12,u=.15,v=.25):
 rr=modes(2*N,True);nn=modes(2*N,False)
 Er=np.array([sum(r)/2+1/16 for r in rr]);En=np.array([sum(r)/2 for r in nn])
 T=np.array([[spin_chiral(r,n) for r in rr] for n in nn])
 FR=np.array([[fermion(r,k,True) for k in rr] for r in rr])
 FN=np.array([[fermion(r,k,False) for k in nn] for r in nn])
 for it,a in enumerate([(),(1,),(3,)]):
  h=sum(a)/2;ia=nn.index(a);x=T[ia]
  val=(x*u**(Er-h))@FR@(x*v**(Er-h))
  pred=blocks(u,v,'central')[it]*u**(1/16-h)*v**(1/16-h)
  side=(FN[ia]*u**(En-h))@T@(x*v**(Er-h))
  # W swaps external parity so middle sector is psi for vacuum, id for either external psi mode.
  base=u**((.5 if not it else 0)-h)*v**(1/16-h)
  pside=blocks(u,v,'side')[it]*base
  print(a,'central',val,pred,'side',side,pside)
if __name__=='__main__':check()
