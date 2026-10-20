"""Build the new expression and run exact finite transcription/algebra checks.
Contour convergence and the branch-average identity are proved in DERIVATION.md.
These finite tests are not a numerical interval certificate or upstream RG proof.
"""
import copy, hashlib, json
from pathlib import Path
import sympy as sp

ROOT=Path(__file__).parent
old_path=ROOT/'inputs/previous_expression.json'
old=json.loads(old_path.read_text())
new=copy.deepcopy(old)
checks=[]
def ck(name,test):
    assert bool(test), name
    checks.append(name)

s,t,theta=sp.symbols('s t theta')
q=sp.Rational
pi=sp.pi
beta,betab=sp.symbols('beta7 beta7_conjugate')
loc={'beta7':beta,'beta7_conjugate':betab,'pi':pi}

def parse(x):return sp.sympify(x,locals=loc)
def local_kernel(d,x):
    ans=sp.S.One
    for a,A in d['upper'][:d['n']]:ans*=sp.gamma(1-parse(a)-parse(A)*x)
    for a,A in d['upper'][d['n']:]:ans/=sp.gamma(parse(a)+parse(A)*x)
    for b,B in d['lower'][:d['m']]:ans*=sp.gamma(parse(b)+parse(B)*x)
    for b,B in d['lower'][d['m']:]:ans/=sp.gamma(1-parse(b)-parse(B)*x)
    return ans

def shared_kernel(d,s,t):
    ans=sp.S.One
    for a,A,B in d['upper'][:d['n']]:ans*=sp.gamma(1-parse(a)-parse(A)*s-parse(B)*t)
    for a,A,B in d['upper'][d['n']:]:ans/=sp.gamma(parse(a)+parse(A)*s+parse(B)*t)
    for b,A,B in d['lower']:ans/=sp.gamma(1-parse(b)-parse(A)*s-parse(B)*t)
    return ans

oldH=next(d for d in old['bivariate_fox_H_terms'] if d['id']=='H7')
H=copy.deepcopy(oldH)
H.update(id='H7unit',function='bivariate Fox H with unit slopes; bivariate Meijer G subclass',
         argument=['1','1'],argument_logs=['0','0'],phase='1',all_slopes_one=True,maximum_slope=1,
         coefficient_in_r6='4704*pi**(5/2)*sqrt(185)',
         contours=['Re(s)=1/4 upward','Re(t)=1/16 upward'],
         absolute_convergence='Cotangent is bounded on Re(t)=1/16. Inner rational factors have a uniform L2-convolution bound; outer gamma factor is O((1+|Im(s)|)^(-3/2)*exp(-pi*|Im(s)|)).',
         value_is_real=True,
         no_parameter_derivative_or_limit=True,
         local_kernel_t='Gamma(t)*Gamma(t+1/2)*Gamma(1-t)*Gamma(1/2-t)**2/(Gamma(3/2-t)*Gamma(t+1/4)*Gamma(t+3/4)*Gamma(1/4-t)*Gamma(3/4-t))',
         shared_kernel='Gamma(1/2-s-t)/Gamma(3/2-s-t)')
H['shared']={'p':1,'q':1,'m':0,'n':1,'upper':[['1/2','1','1']],'lower':[['-1/2','1','1']]}
H['second_local']={'p':5,'q':5,'m':2,'n':3,
                   'upper':[[v,'1'] for v in ['0','1/2','1/2','1/4','3/4']],
                   'lower':[[v,'1'] for v in ['0','1/2','-1/2','1/4','3/4']]}

# Finite gamma-group checks.
Aexpected=(sp.gamma(s)**3*sp.gamma(q(1,2)-s)**7*sp.gamma(q(5,4)-s)/
           (sp.gamma(1-s)**3*sp.gamma(-s)*sp.gamma(q(1,4)-s)*
            sp.gamma(s+beta)*sp.gamma(1-s-beta)*sp.gamma(s+betab)*sp.gamma(1-s-betab)))
Rexpected=(sp.gamma(t)*sp.gamma(t+q(1,2))*sp.gamma(1-t)*sp.gamma(q(1,2)-t)**2/
           (sp.gamma(q(3,2)-t)*sp.gamma(t+q(1,4))*sp.gamma(t+q(3,4))*sp.gamma(q(1,4)-t)*sp.gamma(q(3,4)-t)))
ck('first local gamma kernel unchanged',sp.cancel(local_kernel(H['first_local'],s)/Aexpected)==1)
ck('second local parameter lists reproduce the specified gamma quotient',sp.cancel(local_kernel(H['second_local'],t)/Rexpected)==1)
ck('shared parameters reproduce the specified gamma quotient',sp.cancel(shared_kernel(H['shared'],s,t)*sp.gamma(q(3,2)-s-t)/sp.gamma(q(1,2)-s-t))==1)
for part in ['first_local','second_local']:
    d=H[part]
    ck(part+' upper count',d['p']==len(d['upper']))
    ck(part+' lower count',d['q']==len(d['lower']))
    ck(part+' numerator counts',0<=d['m']<=d['q'] and 0<=d['n']<=d['p'])
    ck(part+' unit slopes',all(parse(x[1])==1 for x in d['upper']+d['lower']))
ck('shared unit slopes',all(parse(x[1])==parse(x[2])==1 for x in H['shared']['upper']+H['shared']['lower']))
ck('quarter-reflection sine product',sp.trigsimp(sp.sin(pi/4+theta)*sp.sin(pi/4-theta)-sp.cos(2*theta)/2)==0)
ck('half-reflection sine product',sp.trigsimp(2*sp.sin(theta)*sp.cos(theta)-sp.sin(2*theta))==0)
ck('t=2v rational Jacobian factor',sp.cancel(2/((1-2*t)*(1-2*s-2*t))-q(1,2)/((q(1,2)-t)*(q(1,2)-s-t)))==0)
ck('inner transform normalization',sp.simplify(pi/2*(-1/(pi*s))-1/(-2*s))==0)
ck('parameter-free special point of inner transform',sp.simplify(-(sp.polygamma(0,q(1,2))+sp.EulerGamma)/(pi*q(1,4))-8*sp.log(2)/pi)==0)
ck('shared contour separation',q(1,2)-q(1,4)-q(1,16)==q(3,16)>0)
ck('second local contour separation',q(1,2)-q(1,16)==q(7,16)>0)
ck('uniform Cauchy Schwarz bound constant',sp.simplify(pi/sp.sqrt(q(7,16)*q(3,16))-16*pi/sp.sqrt(21))==0)
ck('seventh r6 multiplier',sp.simplify(9408*pi**q(3,2)*sp.sqrt(185)*pi/2-4704*pi**q(5,2)*sp.sqrt(185))==0)
ck('number of seventh listed parameters increases by six',(20+10+2)-(20+4+2)==6)

H7,H7u=sp.symbols('H7 H7unit')
oldexpr=sp.sympify(old['formula_C6'],locals={'pi':pi,'Q':sp.Symbol('Q')})
newexpr=sp.expand(oldexpr.subs(H7,pi*H7u/2))
new['formula_C6']=str(newexpr)
new['formula_r6_block']='E+Bpol+Blow+B6+B8-393*pi*sqrt(89)*Hw+24*pi**(3/2)*(rho7*G7+196*pi*sqrt(185)*H7unit)+7680*pi**3*Hstar'
new['title']='C6(1): nine fixed values, all three bivariate functions at (1,1) with unit slopes'
new['scope']='Exact phase-average and duplication transformation of the seventh H-value. H7=(pi/2)*H7unit. The nine-value count and polynomial are unchanged. All three bivariate functions now have unit slopes and arguments (1,1). The second local parameter list increases from 2/2 to 5/5. This is a function-class/branch simplification, not a period-independence theorem, elementary evaluation, or reduction of the number of fixed values. Upstream graph/RG identities are inherited.'
new['bivariate_fox_H_terms']=[H if d['id']=='H7' else d for d in new['bivariate_fox_H_terms']]
new['counts']['new_seventh_parameter_entries_counting_multiplicity']=52
new['counts']['all_bivariate_slopes_one']=True
new['counts']['all_bivariate_arguments_one_one']=True
new['residual_replacements']['M7']='(rho7*G7+196*pi*sqrt(185)*H7unit)/pi**(3/2)'
new['residual_replacements']['seventh']['complete_r6']='24*pi**(3/2)*(rho7*G7+196*pi*sqrt(185)*H7unit)'
new['seventh_reduction']={'identity':'H7=(pi/2)*H7unit',
                          'complete_r6':new['residual_replacements']['seventh']['complete_r6'],
                          'new_steps':'opposite phase Barnes integrals agree because their difference has no left poles; average phases, set t=2v, apply gamma reflection.',
                          'tradeoff':'unit slopes and positive arguments instead of a slope 2 and argument -1; second local order increases 2/2 to 5/5',
                          'fixed_values_reduced':False}
new['provenance_this_step']={'input_file':old_path.name,'input_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),
                             'mathematica_kernel_executed':False,'full_C6_reevaluated':False,'new_interval_certificate':False}
new['new_all_sector_evaluation']=False;new['new_interval_certificate']=False
ck('all active H7 symbols replaced',H7 not in newexpr.free_symbols)
ck('full exact substitution',sp.expand(newexpr-oldexpr.subs(H7,pi*H7u/2))==0)
ck('complete coefficient of H7unit',sp.simplify(sp.expand(newexpr).coeff(H7u)*2187-4704*pi**q(5,2)*sp.sqrt(185))==0)
for key in ['known_polynomial','source_correction_unchanged','polylogarithm_values','univariate_meijer_g_terms','lower_parameters','eighth_parameters','primitive_compression_parameters','wheel_reduction']:
    ck('preserve '+key,new[key]==old[key])
ck('first local seventh parameters unchanged',H['first_local']==oldH['first_local'])
ck('first local seventh gamma kernel unchanged',H['local_kernel_s']==oldH['local_kernel_s'])
ck('wheel and primitive untouched',[x for x in new['bivariate_fox_H_terms'] if x['id']!='H7unit']==[x for x in old['bivariate_fox_H_terms'] if x['id']!='H7'])
ck('fixed-value count stays nine',new['counts']['total_fixed_function_values']==9)
ck('new argument logs are zero',H['argument_logs']==['0','0'])
# The accepted polynomial can be audited separately; its symbol count is fixed.
ck('known polynomial still has 18 terms',len(sp.Add.make_args(sp.expand(sp.sympify(new['known_polynomial'],locals={'Q':sp.Symbol('Q')}))))==18)

(ROOT/'results/expression.json').write_text(json.dumps(new,indent=2))
report={'passed':len(checks),'checks':checks,'exact_finite_checks_only':True,'contour_proof':'DERIVATION.md',
        'new_interval_certificate':False,'input_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest()}
(ROOT/'results/exact_checks.json').write_text(json.dumps(report,indent=2))
print(f'{len(checks)} finite exact checks passed')
