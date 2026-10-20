"""Exact finite-part bulk moments for the charge derivative of the 3-kink endpoint response."""
import sympy as s
from functools import lru_cache
r,l,m,P=s.symbols('r l m P')
u=(1-r)/r
K=-2*u*(m+l)+4*P-2*m*m+2*l*l+2*(m+l+1)/u+2*m+2
I=s.expand(-2*(u*m-l)*K)
poly=s.Poly(I,l,m,P)
a,b=s.symbols('a b')
z2,z3,z4,z5,z6=s.symbols('z2 z3 z4 z5 z6')
zs={2:z2,3:z3,4:z4,5:z5,6:z6}
logs={j:s.expand((-1)**j*zs[j]*(a**j+b**j-(a+b)**j)/j) for j in zs}
F=s.expand(1+logs[2]+logs[3]+logs[4]+logs[2]**2/2+logs[5]+logs[2]*logs[3]+logs[6]+logs[2]*logs[4]+logs[3]**2/2+logs[2]**3/6)
def gr(p,x):
    if p>=1:return s.prod(x+j for j in range(1,p))
    return 1/s.prod(x+j for j in range(p,1))
@lru_cache(None)
def bm(p,q,i,j):
    B=gr(p,a)*gr(q,b)/gr(p+q,a+b)*F
    ser=s.series(B,a,0,i+1).removeO().expand().coeff(a,i)
    val=s.series(ser,b,0,j+1).removeO().expand().coeff(b,j)
    return s.expand(s.factorial(i)*s.factorial(j)*val).subs(z2**2,s.Rational(5,2)*z4)
# Integrate a rational coefficient using a partial fraction expansion.
def integ(c,i,j):
    pp=s.apart(c,r); total=0
    for term in s.Add.make_args(pp):
        cd=term.as_powers_dict();ir=cd.get(r,0);jr=cd.get(r-1,0)
        fac=s.simplify(term/(r**ir*(r-1)**jr))
        if r in fac.free_symbols:raise ValueError((term,fac))
        total+=fac*(-1)**jr*bm(int(ir)+1,int(jr)+1,i,j)
    return s.expand(total)
res=0
for (i,j,k),c in poly.terms():
    if k:continue
    val=integ(c,i,j)
    print('moment',i,j,s.apart(c,r),'->',val,flush=True)
    res+=val
# dilogarithmic contribution: -8 int (1/r-1) log(1-r) Li2(1-r) +8 int log(r) Li2(1-r).
dilog=48-24*z2-16*z3+6*z4
Br=s.expand(res+dilog)
BR=-144+64*z2+32*z3-24*z4
LR=-24+16*s.log(2)+12*z2+30*z3
final=s.expand(Br+BR+LR)
print('pure log bulk',s.expand(res))
print('Br',Br)
print('EP3v',final)
print('numeric',s.N(final.subs({z2:s.zeta(2),z3:s.zeta(3),z4:s.zeta(4)}),60))
