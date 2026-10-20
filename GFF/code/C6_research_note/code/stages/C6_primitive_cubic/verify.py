"""Exact symbolic checks supporting DERIVATION.md (not a formal proof assistant)."""
from __future__ import annotations
import json
from pathlib import Path
import sympy as s
from formula import build, CHANGED_FIELDS, NEW_FIELDS

ROOT = Path(__file__).resolve().parent
checks = []

def check(name: str, statement) -> None:
    if not bool(statement):
        raise AssertionError(name)
    checks.append(name)

def zero(name: str, expression) -> None:
    check(name, s.expand(expression) == 0)

f,g,F,G = s.symbols('f g fstar gstar', real=True)
u,r,a,b = s.symbols('u r a b', real=True)
P = (g*g*G*G+g*g*F*F+f*f*G*G-4*f*g*F*G-3*f*f*F*F
     +4*s.I*(f*g*F*F-f*f*F*G))
expected = 2*r*(a-b)*((a+b)*r-2*(a-b)*u)
for label, sub in [
    ('negative', {f:u,g:r-s.I*u,F:a-s.I*b,G:a+s.I*b}),
    ('positive', {f:a+s.I*b,g:a-s.I*b,F:u,G:r+s.I*u}),
]:
    out = s.expand(P.subs(sub, simultaneous=True))
    zero(label+' exterior numerator is real', s.im(out))
    zero(label+' exterior numerator explicit factorization', out-expected)

# The symmetric real numerator is the normalized I relation pointwise.
q0,q1,q2 = f*f, f*(f+g), (f+g)**2
Q0,Q1,Q2 = F*F, F*(F+G), (F+G)**2
relation_poly = q2*Q2-2*(q1*Q2+q2*Q1)+2*(q0*Q2+q2*Q0)-4*q0*Q0
zero('real numerator equals symmetrized I relation', s.re(P)-relation_poly)
zero('imaginary numerator is antisymmetric under reflection',
     s.im(P)+s.im(P).subs({f:F,g:G,F:f,G:g}, simultaneous=True))

# Recover, rather than assume, the real-boundary coefficient solution.
c = s.symbols('c:6', real=True)
d = s.symbols('d:3', real=True)
C = s.Matrix([[c[0],c[1],c[2]],[c[1],c[3],c[4]],[c[2],c[4],c[5]]])
D = s.Matrix([[0,d[0],d[1]],[-d[0],0,d[2]],[-d[1],-d[2],0]])
vec = lambda x,y: s.Matrix([x*x,x*y,y*y])
equations = []
for v,w in [(vec(u,r-s.I*u),vec(a-s.I*b,a+s.I*b)),
            (vec(a+s.I*b,a-s.I*b),vec(u,r+s.I*u))]:
    equations += s.Poly(s.im(s.expand((v.T*(C+s.I*D)*w)[0])),u,r,a,b).coeffs()
M,_ = s.linear_eq_to_matrix(equations,c+d)
check('boundary ansatz rank is 8 of 9', M.rank()==8 and M.cols==9)
cert = s.Matrix([-3,0,1,-4,0,1,-4,0,0])
check('explicit boundary null vector', M*cert == s.zeros(M.rows,1))

p,l,z3,z4 = s.symbols('pi ell z3 z4')
J00,J02,J11,J12,J22 = s.symbols('J00 J02 J11 J12 J22')
old_pa = 15*J22+24*p*p*J11-4*p**4*J00
new_pa = 60*p*J12-60*p*p*J02+24*p*p*J11+56*p**4*J00
zero('complete primitive substitution',
     old_pa.subs(J22,4*p*J12-4*p*p*J02+4*p**4*J00)-new_pa)

# Explicit beta moment of the cubic kernel.
t,u,e,v,H2,Z3 = s.symbols('t u e v H2 Z3')
U,V = t+p,u+p
vm,vn=e-p*p,v-p*p
cov=H2-p*p/6
mixed3=-2*Z3
A_m,A_n=U*U+vm,V*V+vn
E02=(A_m+A_n)/2
E11=U*V+cov
E12=(U*A_n+V*A_m)/2+(U+V)*cov+mixed3
Gbeta=60*p*E12-60*p*p*E02+24*p*p*E11+56*p**4
T=(15*t*u*(t+u)+15*(t*v+u*e)+72*p*(t*u+H2)
   +(30*H2+7*p*p)*(t+u)+28*p**3-60*Z3)
zero('beta expectation gives exactly 2*pi*T', Gbeta-2*p*T)
zero('T is symmetric in the two indices',
     T-T.subs({t:u,u:t,e:v,v:e}, simultaneous=True))
check('harmonic polynomial degree is three',s.Poly(T,t,u,e,v,H2,Z3).total_degree()==3)
T00=15360*l**3+4608*p*l*l+432*p*p*l+28*p**3-60*z3
zero('zero-index term',T.subs({t:8*l,u:8*l,e:4*p*p/3,v:4*p*p/3,H2:0,Z3:z3})-T00)

# Fourth-moment difference is a global zero-sum relation, not termwise equality.
H4=s.symbols('H4')
mixed4=-6*(p**4/90-H4)
E22=A_m*A_n+4*U*V*cov+2*cov**2+2*(U+V)*mixed3+mixed4
F_old=15*E22+24*p*p*E11-4*p**4
D_beta=E22-4*p*E12+4*p*p*E02-4*p**4
zero('quartic minus cubic is 15 times the beta relation',F_old-2*p*T-15*D_beta)
check('quartic and cubic summands are not claimed pointwise equal',s.expand(D_beta)!=0)

# Check beta-mean transformations at exact integer indices.
H=lambda n,r=1:s.harmonic(n,r)
for m,n in [(0,0),(0,3),(1,1),(2,5),(7,4)]:
    k=m+n
    hm=l+H(m)-H(2*m)
    delta=p*p/3-4*H(2*m,2)+2*H(m,2)
    mean_log=2*l+H(k)+H(m)-2*H(2*m)
    var_log=p*p/3-4*H(2*m,2)+H(m,2)+H(k,2)
    zero(f'beta centered first moment {m},{n}',mean_log+6*hm-(8*hm+H(k)-H(m)))
    zero(f'beta corrected second moment {m},{n}',
         var_log+3*delta-(4*delta+H(k,2)-H(m,2)))
    beta=s.factorial(2*m)*s.factorial(2*n)/(
        4**(m+n)*s.factorial(m)*s.factorial(n)*s.factorial(m+n))
    am=s.binomial(2*m,m)/4**m;an=s.binomial(2*n,n)/4**n
    zero(f'beta weight {m},{n}', beta-am*an/s.binomial(k,m))
    w=lambda j,k:(s.binomial(2*j,j)/4**j)**4*(s.binomial(2*k,k)/4**k)**4/s.binomial(j+k,j)
    zero(f'rational weight update {m},{n}',
         w(m+1,n)/w(m,n)-(m+s.Rational(1,2))**4/((m+1)**3*(m+n+1)))

# The simple uniform positivity and tail majorants use rational inequalities.
check('strict positivity lower bound',28*3**3-60*s.Rational(5,4)==681)
B=s.symbols('B',nonnegative=True)
major=s.Rational(75,2)*B**2+s.Rational(3279,4)*B+s.Rational(4285,2)
shift=s.Poly(s.expand((200*B**2-major).subs(B,B+7)),B)
check('T<200*(7+log(k))^2 majorant coefficients',all(c>0 for c in shift.all_coeffs()))
for k in range(1,20):
    check(f'reciprocal binomial shell bound k={k}',sum(1/s.binomial(k,m) for m in range(k+1))<3)

# Full artifact preservation and normalization.
old=json.loads((ROOT/'inputs/central_expression.json').read_text())
new=build()
check('only declared new fields added',set(new)-set(old)==NEW_FIELDS)
for key in old:
    if key not in CHANGED_FIELDS:
        check('unchanged inherited field: '+key, old[key]==new[key])
check('known polynomial unchanged',new['known_polynomial']==old['known_polynomial'])
check('source repair unchanged',new['source_correction']==old['source_correction'])
check('quartic primitive retained verbatim',new['retained_quartic_primitive_series_terms']==old['double_index_harmonic_series_terms'])
check('full C6 primitive weight',new['formula'].replace('192*pi**2*PaCubic','96*pi*PaCentral')==old['formula'])
check('all three active auxiliary quantities retained',len(new['active_auxiliary_series'])==3)
check('new primitive maximal harmonic order',new['double_index_harmonic_series_terms'][0]['max_harmonic_order']==3)
check('both indices still begin at zero',new['double_index_harmonic_series_terms'][0]['zero_index_included'])

out={'check_count':len(checks),'all_passed':True,'checks':checks,
     'scope':'Exact algebra and implementation checks. Analytic branch, arc and convergence arguments are in DERIVATION.md; this is not a formal proof-assistant certificate.'}
(ROOT/'results/exact_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'check_count':len(checks),'all_passed':True},indent=2))
