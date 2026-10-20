#!/usr/bin/env python3
"""Exact finite algebra for a one-value bivariate-H compression of the primitive.

This uses the inherited definite-pairing relation H33+2 H13-H22=0.
It is not an independent derivation of that relation or of the Ising graphs.
"""
from pathlib import Path
import copy, hashlib, json
import sympy as s
BASE=Path(__file__).resolve().parent
checks=[]
def check(name, ok):
    assert bool(ok), name
    checks.append({'name':name, 'passed':True})
l,e,x,y=s.symbols('lambda eta x y')
f=4*l**3-112*l**2+909*l-2250
d=l-s.Rational(279,40)
h=(21*l-150)/(20*d)
e2=d/10

def replace_eta(expr):
    num,den=s.fraction(s.cancel(expr))
    num=s.rem(s.Poly(num,e).as_expr(),e**2-e2,e)
    den=s.rem(s.Poly(den,e).as_expr(),e**2-e2,e)
    return s.cancel(num/den)
def reduce_lambda(expr):
    num,den=s.fraction(s.cancel(expr))
    return s.rem(s.expand(num*s.invert(den,f,l)),f,l)
M=s.Matrix([[10,s.Rational(21,2),0],[s.Rational(21,2),18,s.Rational(15,2)],[0,s.Rational(15,2),0]])
N=s.Matrix([[0,0,1],[0,-1,0],[1,0,1]])
check('determinant certificate',s.factor((M+l*N).det()-f/4)==0)
check('root isolated: f(799/50)<0',f.subs(l,s.Rational(799,50))<0)
check('root isolated: f(1599/100)>0',f.subs(l,s.Rational(1599,100))>0)
check('unique root on (15,16): derivative at 15 positive',s.diff(f,l).subs(l,15)>0)
check('derivative increasing on (15,16)',s.diff(f,l,2).subs(l,15)>0)
Q=(s.Matrix([[x*x,x,1]])*M*s.Matrix([y*y,y,1]))[0]
Qzero=(s.Matrix([[x*x,x,1]])*N*s.Matrix([y*y,y,1]))[0]
Bp=s.Rational(21,20)+e; Bm=s.Rational(21,20)-e
Cp=l/10+e*h; Cm=l/10-e*h
Pp=lambda v:v*v+Bp*v+Cp
Pm=lambda v:v*v+Bm*v+Cm
symprod=s.expand(5*(Pp(x)*Pm(y)+Pm(x)*Pp(y)))
res=replace_eta(symprod-Q-l*Qzero)
check('exact bilinear factor certificate',s.factor(res-f/(40*l-279))==0)
check('bilinear factor modulo root polynomial',reduce_lambda(res)==0)
Dp2=(Cp-1)**2+Bp**2; Dm2=(Cm-1)**2+Bm**2
normres=replace_eta(s.expand(Dp2*Dm2-1))
certificate=f*(4*l**3-112*l**2+269*l+2214)/(100*(40*l-279)**2)
check('exact normalization certificate',s.factor(normres-certificate)==0)
check('Dplus^2 Dminus^2=1',reduce_lambda(normres)==0)
# Trigonometric numerator polynomial. u,v stand for tan(pi beta1),tan(pi beta2).
u,v,z=s.symbols('u v z')
check('quadratic roots factor',s.expand((z+u)*(z+v)-(z*z+(u+v)*z+u*v))==0)
check('cosine product norm',s.expand((1+u*u)*(1+v*v)-((1-u*v)**2+(u+v)**2))==0)
# Sixth-sector sine addition, with tan(theta)=z and alpha=atan(11/13)/pi.
check('sixth normalization',13**2+11**2==290)
check('sixth outer coefficient',192*13==2496 and 192*11==2112)
# Exact inherited four-H combination versus the new one after reflection symmetry.
a11,a12,a13,a22,a23,a33=s.symbols('H11 H12 H13 H22 H23 H33')
HH=s.Matrix([[a11,a12,a13],[a12,a22,a23],[a13,a23,a33]])
oldprim=10*a11+21*a12+18*a22+15*a23
vplus=s.Matrix([1,Bp,Cp]);vminus=s.Matrix([1,Bm,Cm])
pair=(vplus.T*HH*vminus)[0]
pairdiff=replace_eta(10*pair-oldprim-l*(a33+2*a13-a22))
check('pairing factor before contour relation',reduce_lambda(pairdiff)==0)
check('primitive prefactor',8*10==80)
check('full r6 primitive prefactor',96*80==7680)
check('spectral primitive factor',80/8==10)
check('cubic primitive factor',s.Rational(80,2)==40)
# Definition checks for the new standard bivariate H.
beta_p=['beta_p_upper','beta_p_lower'];beta_m=['beta_m_upper','beta_m_lower']
Hstar={
 'id':'Hstar','function':'bivariate Fox H, all slopes one',
 'shared':{'p':0,'q':1,'m':0,'n':0,'upper':[], 'lower':[['0','1','1']]},
 'local_x':{'p':6,'q':5,'m':3,'n':3,
  'upper_numerator':['1/2']*3,'upper_denominator':['1/2']+beta_p,
  'lower_numerator':['0']*3,'lower_denominator':beta_p,'slopes':'all 1'},
 'local_y':{'p':6,'q':5,'m':3,'n':3,
  'upper_numerator':['1/2']*3,'upper_denominator':['1/2']+beta_m,
  'lower_numerator':['0']*3,'lower_denominator':beta_m,'slopes':'all 1'},
 'arguments':['1','1'],'coefficient_in_r6':'7680*pi**3',
 'kernel': 'Gamma(s)^3*Gamma(1/2-s)^3*Gamma(t)^3*Gamma(1/2-t)^3 / (Gamma(1/2+s)*Gamma(1/2+t)*Gamma(1-s-t)*product_{b in beta_p}[Gamma(s+b)*Gamma(1-s-b)]*product_{b in beta_m}[Gamma(t+b)*Gamma(1-t-b)])',
 'contours':'Re(s)=Re(t)=1/4, both upward; measure ds dt/(2*pi*i)^2',
 'dimension':2,'no_parameter_derivative_or_limit':True}
for label in ['local_x','local_y']:
    rr=Hstar[label]
    check(label+' upper length',len(rr['upper_numerator'])+len(rr['upper_denominator'])==rr['p'])
    check(label+' lower length',len(rr['lower_numerator'])+len(rr['lower_denominator'])==rr['q'])
    check(label+' numerator splits',len(rr['upper_numerator'])==rr['n'] and len(rr['lower_numerator'])==rr['m'])
# Export a FULL expression, retaining all unmodified parameter tables.
inpath=BASE/'inputs/previous_expression.json'
source=json.loads(inpath.read_text()); out=copy.deepcopy(source)
parse_locals={'Q':s.Symbol('Q'), 'G':s.Symbol('G')}
old_expr=s.sympify(source['formula_C6'], locals=parse_locals)
BH11,BH12,BH22,BH23,X35,X44,HHstar,GG6=s.symbols('BH11 BH12 BH22 BH23 X35 X44 Hstar G6packed')
old_r6prim=768*s.pi**3*(10*BH11+21*BH12+18*BH22+15*BH23)
old_r6six=192*s.pi*(13*X35+11*X44)
newexpr=s.expand(old_expr-(old_r6prim+old_r6six)/2187+(7680*s.pi**3*HHstar+192*s.pi*s.sqrt(290)*GG6)/2187)
back=newexpr.subs({HHstar:(10*BH11+21*BH12+18*BH22+15*BH23)/10, GG6:(13*X35+11*X44)/s.sqrt(290)})
check('full r6 transcription',s.expand(back-old_expr)==0)
check('legacy primitive symbols absent',not any(newexpr.has(q) for q in [BH11,BH12,BH22,BH23]))
check('legacy sixth symbols absent',not newexpr.has(X35) and not newexpr.has(X44))
out['title']='C6(1): compact finite representation with one bivariate primitive value'
out['scope']='Exact representation compression using an inherited primitive contour relation, a new algebraic rank-two factorization, and the previously established sixth-sector sine packing. 22 fixed function values become 18. No new elementary evaluation, arithmetic-independence theorem, or physical graph/RG verification is claimed. Parameter complexity increases in the primitive. All former residuals remain represented by convergent established multivariate functions.'
out['formula_C6']=s.sstr(newexpr)
out['known_polynomial_change_this_assembly']='0'
out['primitive_compression_parameters']={
 'lambda':'unique root in (15,16) of 4*lambda**3-112*lambda**2+909*lambda-2250=0',
 'lambda_elementary':'(28+sqrt(409)*cos(acos(7298/(409*sqrt(409)))/3))/3',
 'eta':'sqrt((40*lambda-279)/400)',
 'chi':'2*(21*lambda-150)/(40*lambda-279)',
 'B_sigma':'21/20+sigma*eta, sigma=+1,-1',
 'C_sigma':'lambda/10+sigma*eta*chi',
 'beta_sigma_upper':'atan(B_sigma/2+i*sqrt(C_sigma-B_sigma**2/4))/pi',
 'beta_sigma_lower':'conjugate(beta_sigma_upper)',
 'branches':'positive real square roots; principal complex atan; lambda as isolated above',
 'D_sigma_for_proof':'sqrt((1-C_sigma)**2+B_sigma**2); D_plus*D_minus=1',
 'dependence':'only fixed rational/algebraic and elementary constants; no unknown period occurs in a parameter'}
out['bivariate_fox_H_terms']=[Hstar]
out['bivariate_fox_H_convention']['specialized_kernel']=Hstar['kernel']
out['univariate_meijer_g_terms']=[v for v in out['univariate_meijer_g_terms'] if v['id'] not in ['X35','X44']]
G6={'id':'G6packed','function':'ordinary univariate MeijerG','p':7,'q':7,'m':4,'n':5,
'upper_numerator':['1/2']*5,'upper_denominator':['1/2','alpha6'],
'lower_numerator':['0']*4,'lower_denominator':['0','0','alpha6'],
'argument':'1','coefficient_in_r6':'192*pi*sqrt(290)',
'alpha6':'atan(11/13)/pi','identity':'sqrt(290)*G6packed=13*X35+11*X44; inherited earlier sixth-sector reduction'}
out['univariate_meijer_g_terms'].append(G6)
out['residual_replacements']['primitive_spectral_bracket']='10*Hstar'
out['residual_replacements']['Pa']='80*pi**3*Hstar'
out['counts']['univariate_meijer_G_values']=3
out['counts']['bivariate_H_values']=1
out['counts']['total_fixed_function_values']=18
out['counts']['known_polynomial_monomials']=18
out['new_all_sector_evaluation']=False
out['new_interval_certificate']=False
out['provenance']={'input_file':'C6_unrestricted_finite_expression.json','input_sha256':hashlib.sha256(inpath.read_bytes()).hexdigest(),
 'inherited_identity':'H33+2*H13-H22=0, from C6_standard_primitive_derivation.md',
 'new_identity':'10*H11+21*H12+18*H22+15*H23=10*Hstar',
 'sixth_packing':'reuses C6_sixth_MeijerG_derivation.md',
 'independence_claimed':False}
for name in ['known_polynomial','elementary_definitions','polylogarithm_values','ordinary_hypergeometric_terms','lower_parameters','eighth_parameters','kampe_de_feriet_terms','seventh_finite_weights','source_correction_unchanged']:
 check('preserve '+name,out[name]==source[name])
check('fixed function count',sum(len(out[k]) for k in ['polylogarithm_values','ordinary_hypergeometric_terms','univariate_meijer_g_terms','kampe_de_feriet_terms','bivariate_fox_H_terms'])==18)
check('known monomial count',len(s.Add.make_args(s.sympify(out['known_polynomial'], locals=parse_locals)))==18)
check('no old primitive tag in active formula','BH' not in out['formula_C6'])
results=BASE/'results'; results.mkdir(exist_ok=True)
(results/'expression.json').write_text(json.dumps(out,indent=2)+'\n')
(results/'exact_checks.json').write_text(json.dumps({'checks':checks,'count':len(checks),'all_passed':True,
'qualification':'Finite identities conditional on the inherited definite-pairing relation; not a reproof of the whole graph calculation.'},indent=2)+'\n')
print(f'Passed {len(checks)} finite exact checks; exported full expression.')
