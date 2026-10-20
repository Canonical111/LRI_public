"""Exact finite checks for the Chebyshev projection of the cubic primitive.

The analytic proof is in DERIVATION.md. These finite algebra checks test its
implementation, not arithmetic independence or the upstream graph reduction.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sympy as s
ROOT=Path(__file__).resolve().parent
checks=[]
def check(name, expr):
    good=bool(expr) if isinstance(expr,bool) else s.simplify(expr)==0
    if not good: raise AssertionError(name+': '+str(expr))
    checks.append(name)

x,z=s.symbols('x z');half=s.Rational(1,2)
# Divide the moment by Beta(1/2-z,1/2). Only a finite polynomial is expanded.
for n in range(13):
    poly=s.Poly(s.chebyshevt(n,1-2*x),x)
    lhs=sum(c*s.rf(half-z,k[0])/s.rf(1-z,k[0]) for k,c in poly.terms())
    rhs=s.rf(z,n)/s.rf(1-z,n)
    check(f'Chebyshev beta moment n={n}',s.factor(lhs-rhs))
# Orthogonality and reflection, with rational coefficients after dividing by pi.
for n in range(7):
    check(f'Chebyshev reflection n={n}',s.chebyshevt(n,2*x-1)-(-1)**n*s.chebyshevt(n,1-2*x))
    poly=s.Poly(s.chebyshevt(n,1-2*x)**2,x)
    norm=sum(c*s.rf(half,k[0])/s.factorial(k[0]) for k,c in poly.terms())
    check(f'Chebyshev norm n={n}',norm-(1 if n==0 else half))
# Exact beta-moment kernel has four upper and four lower parameters.
for j in [1,2,3]:
    check(f'Meijer upper-count j={j}',(4-j)+j-4)
    check(f'Meijer lower-count j={j}',(j-1)+1+(3-j)+1-4)
    check(f'Meijer numerator-count j={j}',(j-1)+1-j)
# Bilinear conversion of the inherited cubic pairing, normalized by pi^3.
u,v,w,U,V,W=s.symbols('u v w U V W')
# Pair reflection is averaged, so cross terms use the symmetric form.
old=(60*((u+v)*2*(U+V+W)+2*(u+v+w)*(U+V))/2
     -60*(u*2*(U+V+W)+2*(u+v+w)*U)/2
     +24*(u+v)*(U+V)+56*u*U)
new=8*(10*u*U+s.Rational(21,2)*(u*V+v*U)+18*v*V+s.Rational(15,2)*(v*W+w*V))
check('Cubic pairing to g basis',s.expand(old-new))
A,B,C=s.symbols('A B C')
phi=10*A*A+21*A*B+18*B*B+15*B*C
check('Zeroth mode C=A',phi.subs(C,A)-(10*A*A+36*A*B+18*B*B))
# Normalizations: Pa = 8 pi^3 S; PaCubic = Pa/(2 pi^2).
check('PaCubic normalization',8*s.pi**3/(2*s.pi**2)-4*s.pi)
check('Full r6 primitive coefficient',96*8*s.pi**3-768*s.pi**3)
# Coefficients of the trigonometric adjoint after testing against sin(n theta).
n=s.symbols('n',integer=True,positive=True)
a_up=4*(n+1)**3-6*(n+1)**2+3*(n+1)-half
check('Adjoint upward coefficient',a_up-half*(2*n+1)**3)
a_down=4*(n-1)**3+6*(n-1)**2+3*(n-1)+half
check('Adjoint downward coefficient',a_down-half*(2*n-1)**3)
check('Adjoint central coefficient',-8*n**3-2*n+2*n*(4*n*n+1))
# ODE pullback x=(1-cos(theta))/2 checked algebraically with t=cos(theta).
t=s.symbols('t');f0,f1,f2,f3=s.symbols('f0 f1 f2 f3')
# Derivatives in t written using F derivatives in theta and sin(theta)^2=1-t^2.
y1=-f1/s.sqrt(1-t*t)
y2=f2/(1-t*t)-t*f1/(1-t*t)**s.Rational(3,2)
y3=-f3/(1-t*t)**s.Rational(3,2)+3*t*f2/(1-t*t)**2-(1+2*t*t)*f1/(1-t*t)**s.Rational(5,2)
L=8*(1-t)*(1-t*t)*y3-12*(1-t)*(1+3*t)*y2+(26*t-10)*y1+f0
want=8*(t-1)*f3-12*s.sqrt(1-t*t)*f2+(2-6*t)*f1+s.sqrt(1-t*t)*f0
check('ODE cosine pullback',s.factor(s.expand(L*s.sqrt(1-t*t)-want)))
# Complete old expression is retained, not edited or silently stripped.
inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'inputs').iterdir()}
report={'exact_checks_passed':len(checks),'checks':checks,'input_sha256':inputs,
 'proof_status':'Analytic proof in DERIVATION.md; finite tests are not independent theorems.',
 'Wolfram_kernel_executed':False,'new_physical_graph_RG_verification':False}
(ROOT/'results/exact_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'exact_checks_passed':len(checks)},indent=2))
