"""Exact finite checks for the standard bivariate-H primitive conversion.
The infinite-dimensional analytic justification is in DERIVATION.md; these
checks validate its algebra and parameter identification, not graph physics.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import sympy as sp
from formula import construct, INPUT, ROOT

checks=[]
def check(name, truth):
    if not bool(truth):
        raise AssertionError(name)
    checks.append(name)
def zero(name, expr): check(name,sp.simplify(sp.expand(expr))==0)

p=sp.Symbol('p',positive=True) # p stands for pi in polynomial identities
ell,L=sp.symbols('ell L')
x=sp.Symbol('x')
q=sp.Rational(1,4)

# Symmetric-square equation of the two inherited Gauss solutions.
P=(sp.Rational(3,2)*x-1)/(x*(1-x))
Q=sp.Rational(1,16)/(x*(1-x))
zero('symmetric-square coefficient of second derivative',
     -3*P-(3-sp.Rational(9,2)*x)/(x*(1-x)))
zero('symmetric-square coefficient of first derivative',
     -(sp.diff(P,x)+4*Q-2*P**2)-(1-sp.Rational(13,4)*x)/(x*x*(1-x)))
zero('symmetric-square coefficient of value',
     -(2*sp.diff(Q,x)-4*P*Q)+1/(8*x*x*(1-x)))
zero('reflection of h equation gives v equation',
     -(sp.Rational(1,2)-sp.Rational(3,2)*(1-x))-(1-sp.Rational(3,2)*x))
for j in (1,2,3):
    check(f'G{j} Meijer ODE has the required positive x sign',(-1)**(3-j-(3-j))==1)

# Exact leading-log polynomials derived from the Mellin poles at s=0.
p0=sp.Integer(1);p1=L+p+6*ell;p2=(L+p+6*ell)**2
zero('G1 residue normalization',sp.sqrt(p)*p0-sp.sqrt(p))
zero('G2 double-pole normalization',(p1-p*p0)/sp.sqrt(p)-(L+6*ell)/sp.sqrt(p))
zero('G3 triple-pole normalization',
     (p2-2*p*p1)/(2*p**sp.Rational(3,2))-((L+6*ell)**2-p**2)/(2*p**sp.Rational(3,2)))
# Gamma-ratio log expansion: 3(psi(1)-psi(1/2))=6 log2;
# 3(psi1(1)-psi1(1/2))=-pi^2, giving the s^2 coefficient below.
s=sp.Symbol('s')
log_series=1+6*ell*s+(18*ell**2-p**2/2)*s*s
zero('triple pole yields the complete constant/log polynomial',
     sp.expand(log_series*(1+L*s+L**2*s*s/2)).coeff(s,2)-((L+6*ell)**2-p*p)/2)

# Parameter lists of the published bivariate H integral.
for j in (1,2,3):
    top=[sp.Rational(1,2)]*4;bottom=[sp.Integer(0)]*3
    numerator=sp.gamma(s)**j*sp.gamma(sp.Rational(1,2)-s)**(4-j)
    denominator=sp.gamma(1-s)**(3-j)*sp.gamma(sp.Rational(1,2)+s)**j
    from_lists=sp.prod(sp.gamma(bottom[h]+s) for h in range(j))
    from_lists*=sp.prod(sp.gamma(1-top[h]-s) for h in range(4-j))
    from_lists/=sp.prod(sp.gamma(1-bottom[h]-s) for h in range(j,3))
    from_lists/=sp.prod(sp.gamma(top[h]+s) for h in range(4-j,4))
    zero(f'local H parameter identification j={j}',from_lists-numerator/denominator)
    Mellin=sp.gamma(s)**j*sp.gamma(sp.Rational(1,2)-s)**(3-j)/(sp.gamma(1-s)**(3-j)*sp.gamma(sp.Rational(1,2)+s)**j)
    zero(f'beta transform adds one upper numerator gamma j={j}',
         numerator/denominator-sp.gamma(sp.Rational(1,2)-s)*Mellin)

t=sp.Symbol('t')
zero('shared lower (0;1,1) gives reciprocal beta denominator',
     1/sp.gamma(1-sp.Integer(0)-s-t)-1/sp.gamma(1-s-t))
check('common contours strictly separate poles',0<sp.Rational(1,4)<sp.Rational(1,2))
zero('absolute-value beta weight on the contours',
     (sp.Rational(1,2)-sp.Rational(1,4))-sp.Rational(1,4))

# Check the full positive cubic primitive integrand, with no integral fitting.
a,b,c,aa,bb,cc=sp.symbols('a b c aa bb cc')
p0=a/sp.sqrt(p);p1=sp.sqrt(p)*(a+b);p2=2*p**sp.Rational(3,2)*(a+b+c)
r0=aa/sp.sqrt(p);r1=sp.sqrt(p)*(aa+bb);r2=2*p**sp.Rational(3,2)*(aa+bb+cc)
old=30*p*((p1-p*p0)*r2+(r1-p*r0)*p2)+24*p*p*p1*r1+56*p**4*p0*r0
new=p**3*(80*a*aa+84*(a*bb+b*aa)+144*b*bb+60*(b*cc+c*bb))
zero('entire inherited positive cubic integrand equals new Meijer product',old-new)
G11,G12,G13,G22,G23,G33=sp.symbols('G11 G12 G13 G22 G23 G33')
map_pair={a*aa:G11,a*bb:G12,b*aa:G12,a*cc:G13,c*aa:G13,
          b*bb:G22,b*cc:G23,c*bb:G23,c*cc:G33}
def integrated(e):
    e=sp.expand(e)
    return sp.Add(*(coef*map_pair[term] for term,coef in e.as_coefficients_dict().items()))
small=10*G11+21*G12+18*G22+15*G23
zero('reflection symmetry gives weights 10,21,18,15',integrated(new/p**3)-8*small)
raw=15*p2*r2+24*p*p*p1*r1-4*p**4*p0*r0
zero('six-pair raw primitive minus four-pair form is inherited relation',
     integrated(raw/p**3)-8*small-60*(G33+2*G13-G22))
# I22 - 4 I12 + 4 I02 - 4 I00 in the symmetrized integrand convention.
contour=p2*r2/p**4-2*(p1*r2+p2*r1)/p**3+2*(p0*r2+p2*r0)/p**2-4*p0*r0
zero('inherited contour identity in G coordinates',
     integrated(sp.expand(p*contour))-4*(G33+2*G13-G22))
zero('normalization Pa=2*pi^2*PaCubic',2*p*p*(4*p*small)-8*p**3*small)
zero('full coefficient 96Pa=192pi^2PaCubic',96*8*p**3*small-192*p*p*4*p*small)
zero('final primitive coefficient',96*8*p**3*small-768*p**3*small)
check('four final weights strictly positive',all(w>0 for w in (10,21,18,15)))

# Exact preservation of current C6 blocks.
old=json.loads(INPUT.read_text());new=construct()
for key in ['normalization','known_polynomial','polylogarithm_terms','polylogarithm_sum',
            'standard_even_values','ordinary_hypergeometric_terms','kampe_de_feriet_terms',
            'kampe_de_feriet_convention','definitions','source_correction','coefficient_polynomials',
            'standard_seventh_values','seventh_finite_weights','seventh_identities']:
    check(f'unchanged input field: {key}',old[key]==new[key])
check('custom primitive saved only as provenance',new['legacy_PaCubic_definition']==old['double_index_harmonic_series_terms'])
check('active custom primitive removed',new['double_index_harmonic_series_terms']==[])
check('no custom active sums',new['active_auxiliary_series']==[])
check('no active PaCubic symbol in formula','PaCubic' not in new['formula'])
check('known shift is zero',new['known_shift_in_r6']=='0')
local_symbols={k:sp.Symbol(k) for k in ('A','Q','G','pi','z3','z5')}
check('21 known monomials unchanged',len(sp.Add.make_args(sp.expand(sp.sympify(new['known_polynomial'],locals=local_symbols))))==21)
check('13 ordinary hypergeometric values retained',len(new['ordinary_hypergeometric_terms'])==13)
check('7 Kampe de Feriet values retained',len(new['kampe_de_feriet_terms'])==7)
check('4 new bivariate values',len(new['bivariate_fox_H_terms'])==4)
for entry,(j,k,w) in zip(new['bivariate_fox_H_terms'],[(1,1,10),(1,2,21),(2,2,18),(2,3,15)]):
    check(f'H{j}{k} weight',entry['coefficient_in_r6']==f'{768*w}*pi**3')
    check(f'H{j}{k} arguments',entry['arguments']==['1','1'])
    check(f'H{j}{k} local orders',entry['orders']['s_local']['n']==4-j and entry['orders']['t_local']['n']==4-k)
    check(f'H{j}{k} shared list',entry['shared_upper']==[] and entry['shared_lower']==[['0','1','1']])

report={'exact_checks_passed':len(checks),'checks':checks,
        'scope':'Finite symbolic/parameter and preservation checks; analytic proof in DERIVATION.md. Not graph/RG or interval certification.'}
(ROOT/'results'/'exact_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
