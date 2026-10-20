"""Single-product Euler-kernel expansion derived by harmonic stuffle products."""
from formal_series import *
import mzv_endpoints as cert
from collections import defaultdict

e=s.Symbol('e'); ds=s.symbols('d1:5')
def stuffmul(a,b):
    out=defaultdict(lambda:0)
    for wa,aa in a.items():
        for wb,bb in b.items():
            for w,k in cert.stuffle(wa,wb).items():out[w]+=aa*bb*k
    return {w:s.expand(v) for w,v in out.items() if s.expand(v)!=0}
def mzv(w):
    n=sum(w); a,b=cert.BINARY_ALL[n][cert.bits(w)]; sig=(-1)**len(w)
    return sig*(s.Rational(a.numerator,a.denominator)*z(n)+s.Rational(b.numerator,b.denominator)*({5:z2*z3,6:z3*z3}.get(n,0)))
Es=[{():s.Integer(1)}]
for n in range(1,5):
    out=defaultdict(lambda:0)
    for j in range(1,n+1):
        for w,v in stuffmul(Es[n-j],{(j,):1}).items():out[w]+=(-1)**(j+1)*ds[j-1]*v/n
    Es.append({w:s.expand(v) for w,v in out.items()})
ks=[]
for n in range(5):
    ks.append(canonical(sum((-e)**r*co*mzv((2+r,)+w) for r in range(n+1) for w,co in Es[n-r].items())))
