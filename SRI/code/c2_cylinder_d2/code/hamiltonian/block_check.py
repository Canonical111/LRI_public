import sys,numpy as np
from ising_basis import modes,spin_chiral
import sympy as sp
u,v,w=sp.symbols('u v w')
z=[1,u,u*v,u*v*w]
for A,B in ([] if __name__!="__main__" else [([0,2],[1,3]),([0,3],[1,2])]):
 a=(sum(z[i] for i in B)-sum(z[i] for i in A))/2
 b=(sum(1/z[i] for i in B)-sum(1/z[i] for i in A))/2
 print(sp.factor(u*v*w*(1-a*b)))

def blocks(u,v,w):
 s=np.sqrt(1-u*v)*np.sqrt(1-v*w);t=np.sqrt(1-v)*np.sqrt(1-u*v*w)
 D=np.exp(-sum(np.log(1-x) for x in [u,v,w,u*v,v*w,u*v*w])/8)
 R=np.sqrt((s+t)/2);Q=np.sqrt(1-u)*np.sqrt(1-w)
 g0=D*R;g1=.5*D*Q/R
 e0=.25*D*(s*(1+u*w)+t*(u+w))/R
 e1=.5*D*R/Q*(s*(1+u*w)-t*(u+w))
 PP=[]
 for SS,II in [((u+u*v*w)-(1+u*v),(1/u+1/(u*v*w))-(1+1/(u*v))),((u+u*v)-(1+u*v*w),(1/u+1/(u*v))-(1+1/(u*v*w)))]:
  PP.append(u*v*w*(1-SS*II/4))
 k,l=PP
 d0=.25*D*(s*(1+u*w)*k+t*(u+w)*l)/R
 d1=.5*D*R/Q*(s*(1+u*w)*k-t*(u+w)*l)
 return [g0,g1,e0,e1,d0,d1]

def check(N=16,uu=.2,vv=.3,ww=.4):
 rr=modes(2*N,True);nn=modes(2*N,False)
 Er=np.array([sum(r)/2+1/16 for r in rr]);En=np.array([sum(r)/2 for r in nn])
 S=np.array([[spin_chiral(r,n) for r in rr] for n in nn])
 ext=[(),(1,),(3,)]
 f=blocks(uu,vv,ww)
 for a in ext:
  h=sum(a)/2;x=S[nn.index(a)];left=x*uu**(Er-h);right=x*ww**(Er-h)
  for parity in [0,1]:
   jj=np.array([len(n)%2==parity for n in nn])
   val=(S[jj]@left)@(vv**(En[jj]-h)*(S[jj]@right))
   if a==():idx=parity;base=uu**(1/16)*ww**(1/16)*vv**(parity/2)
   elif a==(1,):idx=2+(1-parity);base=uu**(-7/16)*ww**(-7/16)*vv**((parity-1)/2)
   else:idx=4+(1-parity);base=uu**(-23/16)*ww**(-23/16)*vv**((parity-3)/2)
   print(a,parity,'spectral',val,'closed',base*f[idx],'error',val-base*f[idx])
if __name__=='__main__':check()
