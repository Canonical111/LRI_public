"""Independent high-precision local identities; no saved period used as input."""
from pathlib import Path
import sys,json,importlib.util
import mpmath as mp
import sympy as sp
sys.path.insert(0,str(Path(__file__).parent))
import horn_compiler as hc
mp.mp.dps=60
out={}
def st(x):return mp.nstr(x,58)
q2a=(mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4/6
q2b=mp.gamma(mp.mpf(1)/4)**8/(24*mp.pi**4)
out['Q2']={'gamma_ratio':st(q2a),'gamma_eighth':st(q2b),'residual':st(q2a-q2b)}
out['Z2']=st(4*mp.catalan*q2a)
def lam(q,l,n,j):
 return (mp.polygamma(j-1,l+n+q)-mp.polygamma(j-1,l+n+2*q)-(-1)**j*mp.polygamma(j-1,q-n)
  +(1+(-1)**j)*mp.polygamma(j-1,1)-mp.polygamma(j-1,n+1))
def E(ks,r):
 e=[mp.mpf(1)]
 for k in range(1,r+1):e.append(sum(ks[j-1]*e[k-j]/mp.factorial(j-1) for j in range(1,k+1))/k)
 return e[r]
def check_K(q,l,n):
 m=l+n;ls=[lam(q,l,n,j) for j in range(1,5)];a,b,c,e=ls
 r=[ls[j+0]/2+mp.polygamma(j,m+2*q)+mp.polygamma(j,n+1)-(1-(-1)**j)*mp.polygamma(j,1) for j in range(4)]
 cc=mp.digamma(1)+mp.digamma(2*q)
 rr=(r[0]-cc)*(a**3+3*a*b+c)/2+3*r[1]*(a*a+b)/4-(a*r[2]+r[3])/4-a**4/12+a*a*b/8+7*a*c/24+b*b/8+e/12
 x=mp.pi/mp.tan(mp.pi*q);p=mp.pi**2
 C=[-x,-x*x-2*p/3,-2*x**3-2*p*x,-6*x**4-8*p*x*x-28*p*p/15]
 D=[ls[i]-C[i] for i in range(4)]
 J=[mp.polygamma(i,m+2*q)+mp.polygamma(i,n+1) for i in range(1,4)]
 H=mp.digamma(m+2*q)-mp.digamma(2*q)+mp.digamma(n+1)-mp.digamma(1)
 a,b,c,e=D;u,v,w=J
 reg=(a**4/6-2*a**3*x/3+5*a*a*b/4+3*a*a*u/4+a*a*(-13*p/12-x*x/4)
 -5*a*b*x/2+5*a*c/12-3*a*u*x/2-a*v/4+a*(4*p*x/3+x**3)
 +b*b/2+3*b*u/4+b*(-11*p/12+x*x/4)-5*c*x/12-e/24
 +H*(a**3/2-3*a*a*x/2+3*a*b/2-a*p-3*b*x/2+c/2)-u*p/2+v*x/4-w/4)
 ri=(p+x*x)**2/2
 T=mp.rf(q,m)*mp.rf(1-q,n)/(mp.rf(2*q,m)*mp.factorial(n))
 S=mp.rf(2*q,m)*mp.factorial(n)/(mp.rf(3*q,m)*mp.rf(1+q,n))
 M=mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)
 rga=lambda c:mp.gamma(c)**2/(mp.gamma(c-q)*mp.gamma(c+q))
 delta=lambda c:-q*q/c*mp.hyper([1,1-q,1+q],[2,c+1],1)
 ratio=M*M*S*S/(T*T)
 return dict(q=st(q),ell=l,n=n,polynomial_residual=st(rr-ri-reg),normalization_residual=st(ratio-2*ri*rga(m+2*q)**2*rga(n+1)**2),Gauss_residual=st(rga(m+2*q)-1-delta(m+2*q)))
out['K_term_identities']=[check_K(mp.mpf(q),l,n) for q,l,n in [('0.25',0,0),('0.3',2,3),('0.5',0,4),('0.75',3,2)]]
print('K identities done',flush=True)
def p5local(q,l,n,theta,points=96,radius=mp.mpf('.018')):
 a=l/2+q/2;b=a+q;s0=a+n;N=l+2*n
 g=lambda s:mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(b+s)*mp.gamma(b-s))
 ker=lambda s:mp.gamma(theta+2*s)*mp.gamma(theta-2*s)/(mp.gamma(2*s)*mp.gamma(-2*s))*g(s)**7
 H=mp.gamma(theta+q+N)*mp.gamma(theta-q-N)/(mp.gamma(q+N)*mp.gamma(-q-N))
 kap=[]
 for j in range(1,7):
  h=2**j*(mp.polygamma(j-1,theta+q+N)+(-1)**j*mp.polygamma(j-1,theta-q-N)-mp.polygamma(j-1,q+N)-(-1)**j*mp.polygamma(j-1,-q-N))
  kap.append(7*lam(q,l,n,j)+h)
 T=mp.rf(q,l+n)*mp.rf(1-q,n)/(mp.rf(2*q,l+n)*mp.factorial(n))
 pred=-(T/mp.gamma(2*q))**7*H*E(kap,6)
 calc=sum(radius*mp.exp(2j*mp.pi*j/points)*ker(s0+radius*mp.exp(2j*mp.pi*j/points)) for j in range(points))/points
 return dict(q=st(q),ell=l,n=n,theta=st(theta),residue_predicted=st(pred),relative_residual=st(abs(calc-pred)/max(1,abs(pred))),imaginary=st(mp.im(calc)))
out['P5_local_residues']=[]
for q,l,n in [('0.3',0,0),('0.5',2,1),('0.75',1,2)]:
 q=mp.mpf(q)
 for theta in [2*q,2*q-1]:
  if l==0 and theta==2*q-1:continue
  v=p5local(q,l,n,theta);out['P5_local_residues'].append(v);print(v,flush=True)
def deg(q,l):return mp.mpf(1) if l==0 else (2*l+4*q-2)*mp.gamma(l+4*q-2)/(mp.gamma(4*q-1)*mp.factorial(l))
def G(q,l,k):
 return mp.gamma((l+k+3*q-1)/2)/mp.gamma((l+k+5*q-1)/2)*mp.gamma((l-k+1-q)/2)/mp.gamma((l-k+1+q)/2)
out['measure_antisymmetry']=[]
for q in [mp.mpf('.6'),mp.mpf('.75')]:
 p=2*q-1
 for l,k in [(0,1),(0,2),(2,5)]:
  f=lambda l,k:(-1)**l*deg(q,l)*deg(q,k)*((l+p)**2-(k+p)**2)*G(q,l,k)**7
  u,v=f(l,k),f(k,l)
  out['measure_antisymmetry'].append(dict(q=st(q),ell=l,k=k,relative_residual=st((u+v)/max(1,abs(u),abs(v)))))
# Fixed half-integer d=1 gamma moment recomputed, not loaded from historical record.
fn=lambda y:y*abs(mp.gamma(mp.mpf('.25')+1j*y))**14*(mp.sinh(6*mp.pi*y)+13*mp.sinh(4*mp.pi*y)+29*mp.sinh(2*mp.pi*y))/mp.pi**mp.mpf('5.5')
out['P5_d1_gamma_integral']=st(mp.quad(fn,[0,mp.mpf('.08'),mp.mpf('.4'),1,3,8,mp.inf]))
out['scope']='60 decimal working digits. Local residue/normalization checks and fresh d=1 gamma integral; not an interval enclosure or independent full graph evaluation.'
path=Path(__file__).resolve().parents[2]/'verification/general_closed/identity_checks.json';path.write_text(json.dumps(out,indent=2));print(path,flush=True)
