"""Build the two-value seventh-sector representation and run exact finite checks.

Analytic contour arguments are in DERIVATION.md. Finite symbolic checks do not
replace those arguments and do not certify an upstream graph/RG identification.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sympy as s

BASE=Path(__file__).resolve().parent
OUT=BASE/'results'; OUT.mkdir(exist_ok=True)
old=json.loads((BASE/'inputs/previous_expression.json').read_text())
checks=[]
def eq(label, x, y=0):
    delta=s.simplify(s.expand(x-y))
    if delta != 0: raise AssertionError((label,delta))
    checks.append(label)
def yes(label, condition):
    if not condition: raise AssertionError(label)
    checks.append(label)

pi,l,A=s.symbols('pi ell A',real=True)
z,eps=s.symbols('z eps')
h,d,H,H2,H3,z3,y=s.symbols('h delta H H2 H3 zeta3 y')
u=1-14*y*h
v=196*y*h*h-28*h+7*y*(d-pi*pi)
T=80*pi*pi*y-26*pi*u+11*v
K=28*pi*pi*y-10*pi*u+3*v
F=(98*H+74*l-6*pi)*T-98*pi*K-98*(11*u-13*pi*y)*(pi*pi/3+4*H2)-8624*y*(z3-H3)
# Normalized residues of M_j, after division by sqrt(pi), excluding (-1)^n a_n^7.
r1=pi*pi*y
r2=pi*(14*y*h-1)
r3=y*(98*h*h+s.Rational(7,2)*d-pi*pi/2)-14*h
psi0=H; psi1=2*H2-pi*pi/3; psi2=-8*(z3-H3)
rd1=r1*psi0
rd2=r2*psi0+pi*y*psi1
rd3=r3*psi0+(14*y*h-1)*psi1+y*psi2/2
qa=259*A-49*pi;qb=481*A-539*pi;qc=407*A-1127*pi
q=qa*z*z+qb*z+qc
res=(196*(7*rd1+13*rd2+11*rd3)+qa*r1+qb*r2+qc*r3).subs(A,pi+4*l)
eq('complete central F_n equals the Barnes integer-pole residue',res,F)
eq('coefficient A conversion',q.subs(A,pi+4*l),(1036*l+210*pi)*z*z+(1924*l-58*pi)*z+1628*l-720*pi)
eq('quadratic T residue',14*r1+26*r2+22*r3,T)
eq('quadratic K residue',10*r1+10*r2+6*r3,K)
# The third-pole coefficient is obtained from the local gamma expansion and tan/sec.
for j in (1,2,3):
    coeff2=s.Rational(7,2)*(d-s.Rational(2,3)*pi*pi)+(s.Rational(7-j,3)+s.Rational(1,2))*pi*pi
    if j==3: eq('third-pole quadratic logarithmic coefficient',coeff2,s.Rational(7,2)*d-pi*pi/2)
    yes(f'negative half-integer has nonnegative net zero order for M_{j}',j-1>=0)
# Elementary quadratic factorizations; signs are fixed in the derivation.
qbeta=(13+s.I*s.sqrt(139))/14
qbetabar=(13-s.I*s.sqrt(139))/14
eq('fixed beta tangent sum',qbeta+qbetabar,s.Rational(13,7))
eq('fixed beta tangent product',qbeta*qbetabar,s.Rational(11,7))
eq('fixed quadratic factorization',7*(z+qbeta)*(z+qbetabar),7*z*z+13*z+11)
eq('fixed quadratic normalization squared',7**2*(1+qbeta*qbeta)*(1+qbetabar*qbetabar),185)
Disc=qb*qb-4*qa*qc
xplus=(qb+s.sqrt(Disc))/(2*qa);xminus=(qb-s.sqrt(Disc))/(2*qa)
eq('real eta tangent sum',xplus+xminus,qb/qa)
eq('real eta tangent product',xplus*xminus,qc/qa)
eq('A-dependent quadratic factorization',qa*(z+xplus)*(z+xminus),q)
eq('A-dependent normalization squared',qa*qa*(1+xplus*xplus)*(1+xminus*xminus),(qa-qc)**2+qb*qb)
eq('rho7 compact form',(qa-qc)**2+qb*qb,(148*A-1078*pi)**2+(481*A-539*pi)**2)
# Explicit elementary bounds sufficient to fix real branches.
yes('a7 strictly positive from pi>0 and log2>0',1036>0 and 210>0)
yes('c7 negative using log2<7/10 and pi>3',1628*s.Rational(7,10)-720*3<0)
yes('b7 positive using log2>2/3 and pi<22/7',1924*s.Rational(2,3)-58*s.Rational(22,7)>0)
# Gamma parameter-list transcription, under the stored inverse-Mellin convention.
svar,tvar,beta,bc,ep,em=s.symbols('s t beta betabar etaPlus etaMinus')
def factor_args(upper_num,upper_den,lower_num,lower_den,x):
    num=Counter([b+x for b in lower_num]+[1-a-x for a in upper_num])
    den=Counter([1-b-x for b in lower_den]+[a+x for a in upper_den])
    return num,den
G_un=[-s.Rational(1,4)]+[s.Rational(1,2)]*7;G_ud=[ep,em]
G_ln=[0]*3;G_ld=[0]*4+[s.Rational(3,4),ep,em]
gnum,gden=factor_args(G_un,G_ud,G_ln,G_ld,svar)
expected_num=Counter([svar]*3+[s.Rational(1,2)-svar]*7+[s.Rational(5,4)-svar])
expected_den=Counter([1-svar]*4+[s.Rational(1,4)-svar,svar+ep,1-svar-ep,svar+em,1-svar-em])
yes('G7 gamma numerator list',gnum==expected_num)
yes('G7 gamma denominator list',gden==expected_den)
H_un=G_un;H_ud=[beta,bc];H_ln=[0]*3;H_ld=[0]*3+[1,s.Rational(3,4),beta,bc]
hnum,hden=factor_args(H_un,H_ud,H_ln,H_ld,svar)
yes('H7 first local gamma numerator list',hnum==expected_num)
yes('H7 first local gamma denominator list',hden==Counter([1-svar]*3+[-svar,s.Rational(1,4)-svar,svar+beta,1-svar-beta,svar+bc,1-svar-bc]))
tnum,tden=factor_args([0,0],[],[0],[-1],tvar)
yes('H7 second local gamma lists',tnum==Counter([tvar,1-tvar,1-tvar]) and tden==Counter([2-tvar]))
shared_num=1-2*svar-tvar;shared_den=2-2*svar-tvar
eq('shared gamma quotient corresponds to one reciprocal',shared_den-shared_num,1)
eq('Gamma(1-s)/Gamma(-s) factor is -s',(-svar)*(-2*svar)**-1,s.Rational(1,2))
for k in range(8):
    # gamma(t)gamma(1-t)e^(-i*pi*t) has residue 1 at t=-k
    eq(f'inner residue factorial and phase at t=-{k}',(-1)**k/s.factorial(k)*s.factorial(k)*(-1)**k,1)
# Build complete expression by preserving its complement of the old five-value block.
new=deepcopy(old)
ids=[x['id'] for x in old['kampe_de_feriet_terms']]
expr=s.sympify(old['formula_C6'],locals={'Q':s.Symbol('Q'),'pi':pi,'A':A})
variables={str(x):x for x in expr.free_symbols}
old_seventh=s.expand(expr-expr.subs({variables[x]:0 for x in ids}))
finite=s.expand(expr-old_seventh)
G7,H7,rho7=s.symbols('G7 H7 rho7')
replacement=24*s.pi**s.Rational(3,2)*(rho7*G7+392*s.sqrt(185)*H7)/2187
# The input uses the symbolic name pi rather than SymPy's built-in pi.
replacement=replacement.xreplace({s.pi:variables['pi']})
newexpr=s.expand(finite+replacement)
eq('every unaffected term of the complete coefficient is preserved',newexpr-replacement,finite)
yes('all five old KdF symbols removed',not any(s.Symbol(x) in newexpr.free_symbols for x in ids))
new['title']='C6(1): nine fixed values; seventh sector reduced to one Meijer G and one bivariate H'
new['scope']='Exact finite representation reduction using inherited central-seventh identity and a new Barnes residue transform. Five seventh-sector KdF values become two fixed values with explicit quadratic-root parameters. No elementary evaluation, arithmetic-independence or minimality theorem, new upstream graph/RG verification, or new full-C6 certificate. One shared slope is 2, and H7 uses argument -1 with Log(-1)=i*pi.'
new['formula_C6']=str(newexpr)
new['formula_r6_block']='E+Bpol+Blow+B6+B8-393*pi*sqrt(89)*Hw+24*pi**(3/2)*(rho7*G7+392*sqrt(185)*H7)+7680*pi**3*Hstar'
new['known_polynomial_change_this_assembly']='0'
new['kampe_de_feriet_terms']=[]
new['ordinary_hypergeometric_terms']=[]
# Remove obsolete active seventh parameter machinery; retained input remains in package.
for key in ['seventh_parameter_polynomials','seventh_new_coefficient_rule','seventh_finite_weights','parameter_complexity_note']:
    new.pop(key,None)
new['elementary_definitions'].update({'a7':'259*A-49*pi','b7':'481*A-539*pi','c7quad':'407*A-1127*pi','rho7':'sqrt((a7-c7quad)**2+b7**2)','Delta7':'sqrt(b7**2-4*a7*c7quad)','eta7_plus':'atan((b7+Delta7)/(2*a7))/pi','eta7_minus':'atan((b7-Delta7)/(2*a7))/pi','beta7':'atan((13+i*sqrt(139))/14)/pi','beta7_conjugate':'conjugate(beta7)'})
new['univariate_meijer_g_terms'].append({'id':'G7','function':'ordinary univariate MeijerG','p':10,'q':10,'m':3,'n':8,'upper_numerator':['-1/4']+['1/2']*7,'upper_denominator':['eta7_plus','eta7_minus'],'lower_numerator':['0']*3,'lower_denominator':['0']*4+['3/4','eta7_plus','eta7_minus'],'argument':'1','coefficient_in_r6':'24*pi**(3/2)*rho7','inverse_Mellin_kernel':'Gamma(s)**3*Gamma(1/2-s)**7*Gamma(5/4-s)/(Gamma(1-s)**4*Gamma(1/4-s)*Gamma(s+eta7_plus)*Gamma(1-s-eta7_plus)*Gamma(s+eta7_minus)*Gamma(1-s-eta7_minus))','contour':'Re(s)=1/4 upward'})
new['bivariate_fox_H_terms'].append({'id':'H7','function':'standard bivariate Fox H','argument':['1','-1'],'argument_logs':['0','i*pi'],'shared':{'p':1,'q':1,'m':0,'n':1,'upper':[['0','2','1']],'lower':[['-1','2','1']]},'first_local':{'p':10,'q':10,'m':3,'n':8,'upper':[['-1/4','1']]+[['1/2','1']]*7+[['beta7','1'],['beta7_conjugate','1']],'lower':[['0','1']]*6+[['1','1'],['3/4','1'],['beta7','1'],['beta7_conjugate','1']]},'second_local':{'p':2,'q':2,'m':1,'n':2,'upper':[['0','1'],['0','1']],'lower':[['0','1'],['-1','1']]},'coefficient_in_r6':'9408*pi**(3/2)*sqrt(185)','local_kernel_s':'Gamma(s)**3*Gamma(1/2-s)**7*Gamma(5/4-s)/(Gamma(1-s)**3*Gamma(-s)*Gamma(1/4-s)*Gamma(s+beta7)*Gamma(1-s-beta7)*Gamma(s+beta7_conjugate)*Gamma(1-s-beta7_conjugate))','local_kernel_t':'Gamma(t)*Gamma(1-t)**2/Gamma(2-t)','shared_kernel':'Gamma(1-2*s-t)/Gamma(2-2*s-t)','phase':'exp(-i*pi*t)','contours':['Re(s)=1/4 upward','Re(t)=1/8 upward'],'all_slopes_one':False,'maximum_slope':2,'absolute_convergence':'Outer kernel O((1+|Im s|)^(-3/2)*exp(-pi*|Im s|)); absolute inner rational kernel has a uniform L2 convolution bound. Full proof in DERIVATION.md.','value_is_real':True,'sign':'negative; no positivity claimed','parameter_derivatives':False})
new['residual_replacements']['M7']='(rho7*G7+392*sqrt(185)*H7)/pi**(3/2)'
new['residual_replacements']['seventh']={'complete_r6':'24*pi**(3/2)*(rho7*G7+392*sqrt(185)*H7)','explicit_infinite_sum':False,'full_ordinary_correction_included':True}
new['counts']={'polylogarithm_values':2,'ordinary_hypergeometric_values':0,'univariate_meijer_G_values':4,'kampe_de_feriet_values':0,'bivariate_H_values':3,'total_fixed_function_values':9,'explicit_residual_sums':0,'explicit_residual_integrals':0,'parameter_derivatives':0,'known_polynomial_monomials':18,'new_seventh_parameter_entries_counting_multiplicity':46,'new_seventh_nonrational_shift_parameters':4,'new_seventh_implicit_polynomial_root_problems':0,'arithmetic_independence_claimed':False}
new['new_all_sector_evaluation']=False
new['new_interval_certificate']=False
new['seventh_reduction']={'identity':'B7=24*pi**(3/2)*(rho7*G7+392*sqrt(185)*H7)','inherited_input':'C6_central_seventh_derivation.md equations (1)-(3)','proof_devices_not_in_final':'Barnes contours and digamma insertion','parameter_complexity_tradeoff':'One shared coefficient 2 is introduced; H argument -1 uses principal log. No KdF or higher-than-quadratic root problem remains in seventh sector.'}
new['provenance_this_step']={'input_file':'C6_seventh_cubic_quartic_expression.json','input_sha256':hashlib.sha256((BASE/'inputs/previous_expression.json').read_bytes()).hexdigest(),'central_source_sha256':hashlib.sha256((BASE/'inputs/central_seventh_derivation.md').read_bytes()).hexdigest(),'Wolfram_kernel_executed':False}
yes('known polynomial preserved byte-for-byte',new['known_polynomial']==old['known_polynomial'])
yes('source repair metadata preserved',new['source_correction_unchanged']==old['source_correction_unchanged'])
for field in ['polylogarithm_values','lower_parameters','eighth_parameters','primitive_compression_parameters','wheel_reduction']:
    yes(field+' unchanged',new[field]==old[field])
yes('old univariate G blocks preserved',new['univariate_meijer_g_terms'][:3]==old['univariate_meijer_g_terms'])
yes('old primitive and wheel H blocks preserved',new['bivariate_fox_H_terms'][:2]==old['bivariate_fox_H_terms'])
yes('fixed function count is nine',sum([len(new['polylogarithm_values']),len(new['ordinary_hypergeometric_terms']),len(new['univariate_meijer_g_terms']),len(new['kampe_de_feriet_terms']),len(new['bivariate_fox_H_terms'])])==9)
(OUT/'expression.json').write_text(json.dumps(new,indent=2))
(OUT/'exact_checks.json').write_text(json.dumps({'passed':True,'finite_check_count':len(checks),'checks':checks,'interval_certificate':False,'scope':'Finite algebra, residue-polynomial and parameter-transcription checks; analytic contour proof separately in DERIVATION.md.'},indent=2))
print(f'PASS: {len(checks)} exact finite checks; expression built.')
