"""Exact sixth-order assembly with unknown new internal-kernel jets retained."""
import sympy as s
import json
from pathlib import Path
A,R,U,V,M,N,T,P,b5=s.symbols('A R U V M N T P b5')
e,g=s.symbols('e g')
W4,W5,W6=s.symbols('W4 W5 W6') # S4[e^2], S5[e], S6[e^0]
H3=s.symbols('H3') # bubble h[e^3]
b3=T+s.Rational(87,4)*A**2-s.Rational(9,4)*R+M
b4=-s.Rational(393,4)*A**3-s.Rational(11,2)*A*M-9*A*T+s.Rational(117,4)*A*R-s.Rational(3,2)*M*N-6*P-s.Rational(165,8)*U+s.Rational(9,4)*V
bs={1:s.Integer(3),2:-6*A,3:b3,4:b4,5:b5}
G={1:s.Integer(1)}
for n in range(2,6):G[n]=s.expand(sum(bs[l]*(n-l)*G[n-l] for l in range(1,n))/((n-1)*e))
print('G5:',G[5],flush=True)
gB=sum(G[n]*g**n for n in G)
h=4/e+R*e-V*e**2/2+H3*e**3
S4=s.Rational(9,2)/e**2+A/e+A*A/8+3*R+M/9+e*(M*(A+N)/18+A*R+U/8-9*V/4)+W4*e**2
S5=18/e**3+11*A/e**2+(b3/9+s.Rational(3,2)*A*A+s.Rational(45,2)*R+4*M/3)/e+s.Rational(7,8)*A**3+M*(A+N)+s.Rational(145,8)*A*R+s.Rational(43,16)*U-s.Rational(181,8)*V+W5*e
sn=s.symbols('s64 s63 s62 s61')
S6=sn[0]/e**4+sn[1]/e**3+sn[2]/e**2+sn[3]/e+W6
kernels={2:s.Rational(1,6),3:-h/4,4:S4,5:-S5,6:S6}
powers={n:s.Poly(gB,g)**n for n in range(2,7)}
# Solve pole constraints at constant outer factor; other constraints are checked below.
pureF={n:s.expand(sum(kernels[m]*powers[m].coeff_monomial(g**n) for m in range(2,n+1))) for n in range(2,7)}
sol=s.solve([pureF[6].coeff(e,k) for k in (-4,-3,-2,-1)],sn)
print('S6 poles:',sol,flush=True)
# fixed point via Lagrange inversion of e=g(3+b2*g+...)
B=sum(bs[l]*g**(l-1) for l in range(1,6))
# easier standard known inversion
x={1:s.Rational(1,3),2:2*A/9,3:8*A*A/27-b3/81,4:40*A**3/81-(10*A*b3+b4)/243,
5:(14*(-6*A)**4)/3**9-21*(-6*A)**2*b3/3**8+(6*(-6*A)*b4+3*b3**2)/3**7-b5/3**6}
# avoid float denominators
x[5]=s.Rational(14,3**9)*(-6*A)**4-s.Rational(21,3**8)*(-6*A)**2*b3+s.Rational(1,3**7)*(6*(-6*A)*b4+3*b3**2)-b5/s.Integer(3**6)
gstar=sum(x[n]*e**n for n in x)
pure=0
for n in range(2,7):
    gp=s.Poly(gstar,e)**n
    for k in range(7-n):pure+=pureF[n].subs(sol).coeff(e,k)*gp.coeff_monomial(e**(6-k))
pure=s.expand(54*pure)
print('h4 before H3 substitution:',pure,flush=True)
# Bubble log has R/4 e² -V/8 e³ +7(psi3(2q)-psi3(1))/192 e4.
X,t1=s.symbols('X t1') # X=psi3(2q)-psi3(1), t1=psi1(1)
# H3 = R²/8 +7(psi3(2q)-psi3(1))/48.
h3expr=R**2/8+s.Rational(7,48)*X
pure=s.expand(pure.subs(H3,h3expr))
# General derivatives of the outer J through degree4.
j={(0,0):s.Integer(1)}
for n in range(1,5):
    for k in range(n+1):j[k,n-k]=s.Symbol(f'j{k}{n-k}')
def J(n):
 return sum((-e/4)**k/s.factorial(k)*sum(s.binomial(k,r)*(2*n-1)**r*j[k-r,r] for r in range(k+1)) for k in range(5))
Fs={n:s.expand(sum(kernels[m]*powers[m].coeff_monomial(g**n)*J(m) for m in range(2,n+1))).subs(sol) for n in range(2,7)}
for n in Fs:
 for k in range(-4,0):
  assert s.expand(Fs[n]).coeff(e,k)==0,(n,k,s.expand(Fs[n]).coeff(e,k))
result=0
for n in range(2,7):
 gp=s.Poly(gstar,e)**n
 for k in range(7-n):result+=s.expand(Fs[n]).coeff(e,k)*gp.coeff_monomial(e**(6-k))
result=s.expand(54*result).subs(H3,h3expr).expand()
h1=4*A/3;h2=25*A*A/36+R/6-2*T/27
h3=s.Rational(17,108)*A**3+A*R/12-2*A*T/27+4*P/27+s.Rational(71,216)*U-V/36
D=lambda n:sum((-1)**r*s.binomial(n,r)*j[n-r,r] for r in range(n+1))
expected=pure-h3*D(1)/4+h2*D(2)/32-h1*D(3)/384+D(4)/6144
rem=s.expand(result-expected)
print('outer factorization remainder:',rem,flush=True)
assert rem==0
print('h4:',pure,flush=True)
res={'G5':str(G[5]),'S6_poles':{str(k):str(v) for k,v in sol.items()},'h4':str(pure),'factorization_remainder':str(rem),'H3':str(h3expr)}
Path('universal_assembly.json').write_text(json.dumps(res,indent=2))
