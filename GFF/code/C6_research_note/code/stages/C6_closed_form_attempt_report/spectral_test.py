import sympy as s
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from sympy.solvers.recurr import rsolve_ratio
n=s.symbols('n',integer=True)
a=lambda n:(2*n-1)**3/(2*n+1)**3
b=lambda n:4*n*(4*n*n+1)/(2*n+1)**3
# Product state (u_n v_n, u_n v_(n-1)+u_(n-1) v_n, u_(n-1)v_(n-1)).
T=lambda n:s.Matrix([[b(n)**2,-a(n)*b(n),a(n)**2],[2*b(n),-a(n),0],[1,0,0]])
e=s.Matrix([[1,0,0]])
rows=[e]
prod=s.eye(3)
for k in range(3):
 prod=T(n+k)*prod
 rows.append(s.simplify(e*prod))
M=s.Matrix.vstack(*rows)
cs=M.T.nullspace()[0]
cs=[s.factor(x) for x in cs]
dens=s.lcm([s.denom(x) for x in cs]); cs=[s.factor(x*dens) for x in cs]
gcd=s.gcd_list(cs);cs=[s.factor(x/gcd) for x in cs]
print('Product recurrence sum(c_k(n) w_(n+k))=0:',cs,flush=True)
# for t_n=(-1)^n w_n recurrence coefficient (-1)^k c_k(n).
ct=[(-1)**k*cs[k] for k in range(4)]
# seek adjoint rational certificate r: sum_k c_k(n-k)*r(n-k)=1.
# with index shifted n -> n+3, becomes positive-shift recursion.
adj=[s.factor(ct[3-k].subs(n,n+k)) for k in range(4)]
print('Adjoint equation coefficients:',adj,flush=True)
r=rsolve_ratio(adj,s.Integer(1),n)
print('Rational telescoping certificate:',r,flush=True)
open(ROOT/'spectral_result.txt','w').write(str({'product_recurrence':cs,'adjoint':adj,'rational_solution':r}))
