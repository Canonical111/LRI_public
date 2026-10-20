"""Build the new 17-value expression and perform finite symbolic checks.

The source-derived global identity connecting fourth/sixth wheel moments is
explicitly inherited; no assertion of an upstream Ising proof is made.
"""
from pathlib import Path
from fractions import Fraction as Q
from math import isqrt
import copy, hashlib, json
import sympy as S
ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'
RESULTS.mkdir(exist_ok=True)
checks=[]
def check(name,condition):
    ok=bool(condition)
    checks.append({'name':name,'passed':ok})
    if not ok: raise AssertionError(name)
def eq(name,a,b):
    check(name,S.simplify(a-b)==0)

s,t,alpha,eps,h,delta,tau=S.symbols('s t alpha eps h delta tau')
p=S.pi
R=S.sqrt(89)
# Published H parameter convention: unit slopes in this specialization.
shared_upper=[S.Rational(1,2)]*2
shared_lower=[-S.Rational(1,2)]*2
s_up_num=[S.Rational(1,2)]*3
s_up_den=[S.Rational(1,2),alpha]
s_lo_num=[0,0]
s_lo_den=[0,0,alpha]
t_up_num=[S.Rational(1,2),0]
t_lo_num=[0,S.Rational(1,2)]
def local(up_n,up_d,lo_n,lo_d,z):
    return (S.prod(S.gamma(b+z) for b in lo_n)*S.prod(S.gamma(1-a-z) for a in up_n)/
            (S.prod(S.gamma(1-b-z) for b in lo_d)*S.prod(S.gamma(a+z) for a in up_d)))
Ns=S.gamma(s)**2*S.gamma(S.Rational(1,2)-s)**3/(S.gamma(1-s)**2*S.gamma(S.Rational(1,2)+s)*S.gamma(s+alpha)*S.gamma(1-s-alpha))
Pt=S.gamma(t)*S.gamma(t+S.Rational(1,2))*S.gamma(S.Rational(1,2)-t)*S.gamma(1-t)
eq('s-local gamma kernel matches ordered Meijer parameter groups',local(s_up_num,s_up_den,s_lo_num,s_lo_den,s),Ns)
eq('t-local gamma kernel matches ordered parameter groups',local(t_up_num,[],t_lo_num,[],t),Pt)
shared=S.prod(S.gamma(1-a-s-t) for a in shared_upper)/S.prod(S.gamma(1-b-s-t) for b in shared_lower)
eq('shared gamma ratio equals reciprocal square',S.expand_func(shared),1/(S.Rational(1,2)-s-t)**2)
check('all local upper/lower orders equal stated 5,5;2,2',(len(s_up_num+s_up_den),len(s_lo_num+s_lo_den),len(t_up_num),len(t_lo_num))==(5,5,2,2))
check('shared orders and numerator index are 2,2;0,2',(len(shared_upper),len(shared_lower))==(2,2))
# The sine addition part of the packing is exact algebra after reflection.
z=S.symbols('z')
c=S.Rational(8)/R; ss=S.Rational(5)/R
eq('packing angle unit-circle normalization',c*c+ss*ss,1)
eq('packing coefficients 8 and 5',R*z**2*(z*c+ss),8*z**3+5*z**2)
# Residues of the two inherited fourth-order kernels with analytic d(s).
# M1=pi*a_n^4/eps+...; M2=a_n^4/eps**2*(1+8*h*eps+...).
res1=S.expand((p/eps)*(delta+tau*eps)).coeff(eps,-1)
res2=S.expand((1+8*h*eps)/eps**2*(delta+tau*eps)).coeff(eps,-1)
eq('M1 times trigamma difference simple residue',res1,p*delta)
eq('M2 times trigamma difference double residue',res2,8*h*delta+tau)
# Integral factors: J1=pi*D4; J2=pi**2*D6, latter is inherited core identity.
D4,D6,Hw,W=S.symbols('D4 D6 Hw W')
eq('weighted wheel has common fourth-order kernel',(8*p*D4+5*p**2*D6)/p,8*D4+5*p*D6)
# t_old = 2*t: factor 2 from measure, (2*pi)^-1 from duplication,
# and 1/4 from (1-2*s-2*t)^-2.
eq('duplication and contour scaling factor',2/(2*p)/4,1/(4*p))
# d(s)=4*I_old; I_old=I_unit/(4*pi), hence I_unit=pi*d(s).
eq('inner Barnes normalization',4/(4*p),1/p)
F4,F6=S.symbols('F4 F6')
Wold=24*F4+15*p*F6
Wnew=R*Hw/p**2
eq('complete wheel coefficient after replacement',-393*p**3*Wnew,-393*p*R*Hw)
eq('previous KdF weights match zero-included wheel',-393*p**3*Wold,-9432*p**3*F4-5895*p**4*F6)
# Core identity d(-n)=delta_n is checked at several integers with exact values.
for n in range(5):
    dn=p**2/3-4*S.harmonic(2*n,2)+2*S.harmonic(n,2)
    half = p**2/2 - sum(1/(S.Rational(1,2)+j)**2 for j in range(n))
    integer = p**2/6 - sum(S.Rational(1,j*j) for j in range(1,n+1))
    eq(f'trigamma recurrence identity at n={n}',half-integer,dn)
check('contours separate the shared pole',S.Rational(1,2)-S.Rational(1,4)-S.Rational(1,8)>0)
# Load and transcribe full coefficient; only the weighted F4,F6 pair changes.
source=ROOT/'inputs/C6_compact_H_expression.json'
old=json.loads(source.read_text())
new=copy.deepcopy(old)
loc={'Gamma':S.gamma,'pi':p,'sqrt':S.sqrt,'F4':F4,'F6':F6,'Q':S.Symbol('Q')}
oldexpr=S.sympify(old['formula_C6'],locals=loc)
wheelold=(-9432*p**3*F4-5895*p**4*F6)/2187
wheelnew=-393*p*R*Hw/2187
rest=S.expand(oldexpr-wheelold)
check('only wheel depended on F4,F6',not (rest.has(F4) or rest.has(F6)))
newexpr=rest+wheelnew
implied=S.expand(oldexpr.subs(F6,(Wnew-24*F4)/(15*p)))
eq('full coefficient equality under proved wheel identity',newexpr,implied)
new['title']='C6(1): finite 17-value representation with a single bivariate wheel H value'
new['scope']='The two wheel Kampe de Feriet values are replaced by one fixed unit-slope bivariate Fox H value at (1,1). This uses the inherited global fourth/sixth wheel identity, ordinary gamma reflection, and a proved inner Barnes transform. 18 fixed values become 17. No elementary evaluation, arithmetic independence, new graph/RG proof, or new full-C6 numerical certificate is claimed. All other sectors remain unchanged.'
new['formula_C6']=str(S.expand(newexpr))
new['known_polynomial_change_this_assembly']='0'
new['elementary_definitions']['alphaW']='atan(5/8)/pi'
new['kampe_de_feriet_terms']=[v for v in old['kampe_de_feriet_terms'] if v['id'] not in ('F4','F6')]
new['bivariate_fox_H_terms'].append({
 'id':'Hw','function':'standard bivariate Fox H (unit-slope bivariate Meijer G subclass)',
 'p_shared':2,'q_shared':2,'m_shared':0,'n_shared':2,
 'upper_shared':[['1/2','1','1'],['1/2','1','1']],
 'lower_shared':[['-1/2','1','1'],['-1/2','1','1']],
 'p_s':5,'q_s':5,'m_s':2,'n_s':3,
 'upper_s':[['1/2','1']]*4+[['alphaW','1']],
 'lower_s':[['0','1']]*4+[['alphaW','1']],
 'p_t':2,'q_t':2,'m_t':2,'n_t':2,
 'upper_t':[['1/2','1'],['0','1']],
 'lower_t':[['0','1'],['1/2','1']],
 'arguments':['1','1'],
 'coefficient_in_r6':'-393*pi*sqrt(89)',
 'contours_for_normalization':['Re(s)=1/4 upward','Re(t)=1/8 upward'],
 'specialized_inverse_Mellin_kernel':'Gamma(s)**2*Gamma(1/2-s)**3*Gamma(t)*Gamma(t+1/2)*Gamma(1/2-t)*Gamma(1-t)/(Gamma(1-s)**2*Gamma(1/2+s)*Gamma(s+alphaW)*Gamma(1-s-alphaW)*(1/2-s-t)**2)',
 'no_parameter_derivative_or_limit':True,
 'all_slopes_one':True,
 'absolute_convergence':'|N(s)|=O((1+|Im(s)|)**-2), t gamma product decays exponentially, and |1/2-s-t|>=1/8.'
})
new['counts']['kampe_de_feriet_values']=5
new['counts']['bivariate_H_values']=2
new['counts']['total_fixed_function_values']=17
new['residual_replacements']['W0']='sqrt(89)*Hw/pi**2'
new['residual_replacements']['Wcentral']='sqrt(89)*Hw/pi**2-(8+5*pi)*pi**2/3'
new['bivariate_fox_H_convention'].pop('specialized_kernel',None)
new['bivariate_fox_H_convention']['specialized_kernel_location']='Each bivariate term has its own kernel; Hstar retains its source definition, Hw is specified explicitly.'
new['provenance']={
 'input_file':source.name,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'inherited_core_identity':'sum a_n**4*(8*h_n*delta_n+tau_n)=pi**2*sum(4*n+1)*a_n**6*delta_n',
 'inherited_core_source':'C6_central_binomial_wheel_reduction.md section 2; equivalently C6_wheel_Meijer_curvature_derivation.md section 4.',
 'new_identity':'24*F4+15*pi*F6=sqrt(89)*Hw/pi**2',
 'new_all_sector_evaluation':False,'independence_claimed':False}
new['wheel_reduction']={
 'old_block_r6':'-9432*pi**3*F4-5895*pi**4*F6',
 'new_block_r6':'-393*pi*sqrt(89)*Hw',
 'known_polynomial_shift':'0',
 'new_identity_requires_inherited_core':True,
 'primitive_compression_preserved':True,
 'numerical_method':'Outer Barnes gamma kernel with proved inner evaluation; independent direct inner-Barnes spot checks.',
 'interval_scope':'Optional exact Hw enclosure is PROPAGATED from an existing wheel certificate, not certified numerical double Barnes integration.'}
for key in ['known_polynomial','polylogarithm_values','ordinary_hypergeometric_terms','univariate_meijer_g_terms','lower_parameters','eighth_parameters','seventh_finite_weights','source_correction_unchanged','primitive_compression_parameters']:
    check('unchanged '+key,new[key]==old[key])
check('primitive Hstar term unchanged',new['bivariate_fox_H_terms'][0]==old['bivariate_fox_H_terms'][0])
check('all remaining KdF entries unchanged',all(v in old['kampe_de_feriet_terms'] for v in new['kampe_de_feriet_terms']))
check('fixed-value count sums to 17',sum(new['counts'][k] for k in ['polylogarithm_values','ordinary_hypergeometric_values','univariate_meijer_G_values','kampe_de_feriet_values','bivariate_H_values'])==17)
check('no old wheel symbols active',not (newexpr.has(F4) or newexpr.has(F6)))
check('known polynomial still 18 monomials',len(S.Add.make_args(S.expand(S.sympify(new['known_polynomial'],locals=loc))))==18)
(RESULTS/'expression.json').write_text(json.dumps(new,indent=2)+'\n')
(RESULTS/'exact_checks.json').write_text(json.dumps({'passed':True,'check_count':len(checks),'checks':checks,'scope':'Finite algebra and transcription checks; inherited analytic identities remain inherited.'},indent=2)+'\n')
print('Passed',len(checks),'checks.')
