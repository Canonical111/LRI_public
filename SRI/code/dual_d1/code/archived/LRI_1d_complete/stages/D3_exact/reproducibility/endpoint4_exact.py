import sympy as s
from endpoint3_exact import bm,integ,z2,z3,z4,r,l,m
D2=s.symbols('D2')
A=(r+1)*(r*r+1)/(r*r*(1-r));B=(1+1/r)/(1-r)
VA=-r+2*l-4*m-1/r
C=2*B-2*A*(m-1)-VA*(1/r-1/(1-r))
R=l*m*(B-A*(m-1))+VA*l*m/(1-r)-VA*z2/(1-r)
Rres=0
for (i,j),c in s.Poly(s.expand(R),l,m).terms():
    val=integ(c,i,j)
    print('polylogfree',i,j,s.apart(c,r),'->',val)
    Rres+=val

def jm(p,q,i,j):
    assert i+j<=1
    if q==0 and p==1:
        return {(0,0):-2*z3,(1,0):-s.Rational(3,4)*z4,(0,1):3*z4}[(i,j)]
    assert q==1,(p,q,i,j)
    power=p-1
    if power==-2:
        return {(0,0):2-z2,(1,0):2-z2-bm(-1,1,1,1),(0,1):z3-2*z2}[(i,j)]
    if power==-1:
        return {(0,0):z3,(1,0):-z4,(0,1):-s.Rational(5,4)*z4}[(i,j)]
    assert power>=0
    n=power+1;H=s.harmonic(n);H2=s.harmonic(n,2)
    if (i,j)==(0,0):return z2/n-H/n**2
    if (i,j)==(1,0):return (-2*z2+H2)/n**2+2*H/n**3
    return -z2*H/n+(H*H+H2)/n**2-2*z3/n+s.Add(*[s.harmonic(k)/k**2 for k in range(1,n+1)])/n

Cres=0
for (i,j),c in s.Poly(s.expand(C),l,m).terms():
    val=0
    for term in s.Add.make_args(s.apart(c,r)):
        cd=term.as_powers_dict();ir=cd.get(r,0);jr=cd.get(r-1,0)
        fac=s.simplify(term/(r**ir*(r-1)**jr))
        if r in fac.free_symbols:raise ValueError((term,fac))
        val+=fac*(-1)**jr*jm(int(ir)+1,int(jr)+1,i,j)
    print('Li2',i,j,s.apart(c,r),'->',s.expand(val))
    Cres+=val
boundary=1+z2-4*z3
bulk=s.expand(2*(boundary+Rres+Cres)).subs(z2**2,s.Rational(5,2)*z4)
endpoints=4+16*z2+20*z4
radial_log_shift=-10-28*z2-28*z3-16*z4
result=s.expand(bulk+endpoints+radial_log_shift)
print('bulk:',bulk)
print('radial logarithm shift:',radial_log_shift)
print('EQ40:',result)
print('numeric:',s.N(result.subs({z2:s.zeta(2),z3:s.zeta(3),z4:s.zeta(4)}),60))
