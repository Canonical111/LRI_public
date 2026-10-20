"""Independent completeness check of the class enumeration (weighted counts).
Sum over classes of wa = 24/den (den = aut * prod m_e! * prod (4-d_v)!) must equal |g^(L+1)| of the
amputated 1PI four-point function Gamma4 = W4/W2^4 of zero-dimensional phi^4 theory with Wick-ordered
vertex -g/4! :x^4: (no self-loops), and the sum of wb = wa*ss/12 is compared with the 1PI function
Gamma^(2,1) of a Wick-ordered x^2/2 insertion (ratio printed). Exact rationals throughout.
Usage: python zero_dim_check.py <dir with classes1..Lmax.txt> Lmax"""
import sys
from fractions import Fraction as F
from math import factorial
from pathlib import Path
D=Path(sys.argv[1]);Lmax=int(sys.argv[2]);NG=Lmax+2  # series in g up to g^(Lmax+1)
def pmul(a,b):
 c=[F(0)]*(len(a)+len(b)-1)
 for i,x in enumerate(a):
  if x:
   for j,y in enumerate(b):
    if y:c[i+j]+=x*y
 return c
def gauss(p):return sum(c*(factorial(k)//(2**(k//2)*factorial(k//2))) for k,c in enumerate(p) if k%2==0)
He4=[F(3),F(0),F(-6),F(0),F(1)];He2=[F(-1),F(0),F(1)]
pw=[[F(1)]]
for j in range(1,NG+1):pw.append(pmul(pw[-1],He4))
def moment(k,extra=None):
 # series in g of <x^k extra(x) exp(-g He4/24)>
 out=[]
 for j in range(NG+1):
  p=pmul([F(0)]*k+[F(1)],pw[j])
  if extra:p=pmul(p,extra)
  out.append(gauss(p)*F(-1,24)**j/factorial(j))
 return out
def smul(a,b):return [sum(a[i]*b[n-i] for i in range(n+1)) for n in range(NG+1)]
def sinv(a):
 out=[1/a[0]]
 for n in range(1,NG+1):out.append(-sum(a[j]*out[n-j] for j in range(1,n+1))/a[0])
 return out
m0,m2,m4=moment(0),moment(2),moment(4);i0=sinv(m0)
W2=smul(m2,i0);W4=[x-3*y for x,y in zip(smul(m4,i0),smul(W2,W2))]
iW2=sinv(W2);G4=smul(W4,smul(smul(iW2,iW2),smul(iW2,iW2)))
d0,d2=moment(0,[F(-1,2)*c for c in He2]),moment(2,[F(-1,2)*c for c in He2])
dW2=[x-y for x,y in zip(smul(d2,i0),smul(smul(m2,d0),smul(i0,i0)))]
G21=[-x for x in smul(dW2,smul(iW2,iW2))]
bad=[]
for L in range(1,Lmax+1):
 t=(D/f'classes{L}.txt').read_text().split();n,ng=int(t[0]),int(t[1]);sa=F(0);sb=F(0)
 for i in range(ng):
  key,aut=int(t[2+3*i]),int(t[3+3*i]);deg=[0]*n;den=aut;k=0
  for a in range(n):
   for b in range(a+1,n):
    m=key>>(2*k)&3;k+=1;den*=factorial(m);deg[a]+=m;deg[b]+=m
  ss=sum((4-d)*(3-d) for d in deg)
  for d in deg:den*=factorial(4-d)
  sa+=F(24,den);sb+=F(24,den)*ss/12
 print(f'L={L} classes={ng} sum_wa={sa} ({float(sa)!r}) |Gamma4[g^{L+1}]|={abs(G4[L+1])} match={sa==abs(G4[L+1])}  sum_wb={sb} ({float(sb)!r}) Gamma21[g^{L}]={G21[L]} ratio={sb/G21[L] if G21[L] else None}',flush=True)
 ok=sa==abs(G4[L+1]) and sb==(-1)**L*G21[L] # exact identities (sign (-1)^L of the Wick-ordered insertion)
 if not ok:bad.append(L)
if bad:raise SystemExit(f'zero-dimensional identity FAILED at L={bad}')
print('zero-dimensional identities hold for every L')
