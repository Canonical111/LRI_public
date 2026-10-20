"""Exact finite checks and machine-readable partial-expression update."""
from pathlib import Path
from copy import deepcopy
import json, hashlib
import sympy as S
R=Path(__file__).resolve().parent
source=R/'inputs/latest_partial_expression.json'
d=json.loads(source.read_text())
A,Q,G,pi,z3,z5=S.symbols('A Q G pi z3 z5')
checks=[]
def check(name, cond):
    if not cond: raise AssertionError(name)
    checks.append(name)

sym_locals={str(v):v for v in (A,Q,G,pi,z3,z5)}
old=S.sympify(d['new_known_polynomial'], locals=sym_locals)
new=S.expand(old+144*Q**3/pi)
check('old known part has the separated -144 Q^3/pi once',old.coeff(Q,3)==-144/pi)
check('remove the separated constant when replacing complete 24 Pb',new.coeff(Q,3)==0)
check('known monomial count 19 to 18',len(S.Add.make_args(old))==19 and len(S.Add.make_args(new))==18)

# Purely finite algebra of the new linear combination.
sh,sh2,sd,h0,x35,x44=S.symbols('sh sh2 sd h0 X35 X44')
old_pb=24*pi**3*(88*pi*sh+312*sh2+13*sd)
new_pb=8*pi*(13*x35+11*x44)
check('full Pb residue combination',S.expand(new_pb.subs({x35:3*pi**2*(24*sh2+sd),x44:24*pi**3*sh})-old_pb)==0)
check('r6 multiplier',S.expand(24*new_pb-192*pi*(13*x35+11*x44))==0)

# Gamma reflection expressed as exact rational algebra with a rational
# parametrization of sin and cos, so sin^2+cos^2=1 holds identically.
t,gs,gh=S.symbols('t gs gh',nonzero=True)
ss=2*t/(1+t*t);cc=(1-t*t)/(1+t*t)
g1m=pi/(ss*gs);ghm=pi/(cc*gh)
k=lambda j:gs**j*ghm**(6-j)/(g1m**(6-j)*gh**j)
k35=gs**3*ghm**5/(g1m**3*gh)
k44=gs**4*ghm**4/(g1m**2*gh**2)
check('Gamma reflection: X35 kernel = pi^2 (M1+M3)',S.cancel(k35-pi**2*(k(1)+k(3)))==0)
check('Gamma reflection: X44 kernel = pi^2 (M2+M4)',S.cancel(k44-pi**2*(k(2)+k(4)))==0)
rr,tt=S.symbols('rr tt',nonzero=True)
for j in range(1,6):
    check(f'contour reflection M{j}(1/2-s)=M{6-j}(s)',S.cancel((rr*tt)**6*(1/tt)**(6-j)-rr**6*tt**j)==0)

# Optional compression using a single angle parameter alpha.
# sin(pi alpha)=11/sqrt(290), cos(pi alpha)=13/sqrt(290).
sa=11/S.sqrt(290);ca=13/S.sqrt(290)
check('single-value trigonometric normalization',S.simplify(sa**2+ca**2)==1)
kalpha=k44*(ss*ca+cc*sa)/cc
check('single G77 kernel: sqrt(290) Kalpha=13 N35+11 N44',S.cancel(S.sqrt(290)*kalpha-13*k35-11*k44)==0)

# Exact finite shifts establishing the logarithmic Laurent coefficients.
for n in range(11):
    f=S.prod((S.Rational(1,2)-j)/(-S.Integer(j)) for j in range(1,n+1))
    h=S.harmonic(n)-S.harmonic(2*n)
    delta_offset=-4*S.harmonic(2*n,2)+2*S.harmonic(n,2)
    first=S.Add(*[1/(S.Rational(1,2)-j)+1/S.Integer(j) for j in range(1,n+1)])
    second=S.Add(*[-1/(S.Rational(1,2)-j)**2+1/S.Integer(j)**2 for j in range(1,n+1)])
    check(f'pole shift coefficient n={n}',S.simplify(f-S.rf(S.Rational(1,2),n)/S.factorial(n))==0)
    check(f'pole shift first logarithmic coefficient n={n}',S.simplify(first-2*h)==0)
    check(f'pole shift second logarithmic coefficient n={n}',S.simplify(second-delta_offset)==0)

terms=d['ordinary_hypergeometric_terms_unchanged']
remove={'Hminus','H0','Hplus'}
check('exactly the three intended ordinary values removed', {x['id'] for x in terms if x['id'] in remove}==remove)
remaining=[deepcopy(x) for x in terms if x['id'] not in remove]
check('ordinary values 13 to 10',len(terms)==13 and len(remaining)==10)
for x in remaining:
    check('unchanged '+x['id'],x==next(t for t in terms if t['id']==x['id']))

out=deepcopy(d)
out['scope']='Partial finite built-in reduction. Pb is reduced from three pFq values to two ordinary univariate MeijerG values. The wheel, seventh-logarithmic block and primitive quadratures are NOT evaluated here.'
out['new_known_polynomial']=str(new)
out['shift_from_previous_partial_known_polynomial']='144*Q**3/pi'
if 'shift_from_native_known_polynomial' in d:
    out['shift_from_native_known_polynomial']=str(S.expand(S.sympify(d['shift_from_native_known_polynomial'],locals=sym_locals)+144*Q**3/pi))
out['ordinary_hypergeometric_terms_unchanged']=remaining
out['univariate_meijer_g_terms']=[
 {'id':'X35','p':6,'q':6,'m':3,'n':5,'upper_numerator':['1/2']*5,'upper_denominator':['1/2'],'lower_numerator':['0']*3,'lower_denominator':['0']*3,'argument':'1','coefficient_in_r6':'2496*pi'},
 {'id':'X44','p':6,'q':6,'m':4,'n':4,'upper_numerator':['1/2']*4,'upper_denominator':['1/2']*2,'lower_numerator':['0']*4,'lower_denominator':['0']*2,'argument':'1','coefficient_in_r6':'2112*pi'}]
out['latest_identity']='Pb=8*pi*(13*X35+11*X44)'
out['optional_single_meijer_g_form']={
 'alpha':'atan(11/13)/pi',
 'id':'Xalpha','p':7,'q':7,'m':4,'n':5,
 'upper_numerator':['1/2']*5,'upper_denominator':['1/2','alpha'],
 'lower_numerator':['0']*4,'lower_denominator':['0','0','alpha'],
 'argument':'1', 'identity':'Pb=8*pi*sqrt(290)*Xalpha',
 'coefficient_in_r6':'192*pi*sqrt(290)',
 'tradeoff':'One value instead of two, but alpha is not rational. This packages a linear combination and does not prove a smaller independent period space.'}
for field in ('finite_polylog_block_r6_wolfram','source_correction_unchanged','unresolved_blocks','polylogarithmic_quadrature_eliminated'):
    check('preserved '+field,out[field]==d[field])
check('two-value inserted coefficients',S.expand(2496*pi*x35+2112*pi*x44-24*new_pb)==0)
out['full_integral_free_sum_free_C6_established']=False
out['remaining_elliptic_blocks_unchanged']=['wheel','seventh logarithmic','primitive Pa']
out['upstream_graph_RG_verification']='Inherited, not independently established in this pass.'
out['provenance']={'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input':'latest_partial_expression.json from supplied C6_finite_polylog_reduction.zip'}
(R/'results/partial_expression.json').write_text(json.dumps(out,indent=2)+'\n')
report={'passed':len(checks),'checks':checks,'interpretation':'Finite implementation and symbolic checks, not proof of the upstream six-loop calculation. Analytic convergence and contour arguments are in DERIVATION.md.'}
(R/'results/exact_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
