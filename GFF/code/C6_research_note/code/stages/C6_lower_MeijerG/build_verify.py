"""Build and verify the partial C6 lower-period transformation.

Only finite algebra and preservation assertions are proof certificates here.
The analytic Barnes boundary argument is recorded separately in DERIVATION.md.
"""
from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, re
import sympy as s

ROOT=Path(__file__).resolve().parent
src=ROOT/'inputs'/'previous_expression.json'
old=json.loads(src.read_text())
new=copy.deepcopy(old)
checks=[]
def check(name, flag):
    if not bool(flag):raise AssertionError(name)
    checks.append(name)
A,Q,pi,X,Y,R,T,S,C,ga,gb=s.symbols('A Q pi X Y R T S C ga gb',nonzero=True)
Cd=-42*A*A-18*A*pi+96*Q-1227*pi*pi
Cs=-s.Rational(105,4)*A*A-9*A*pi+60*Q-s.Rational(2469,4)*pi*pi
Xexpr=-Cd;Yexpr=-Cs
check('X=-Cd',s.expand(Xexpr+Cd)==0)
check('Y=-Cs',s.expand(Yexpr+Cs)==0)
u4,u6,g13,g22,g23=s.symbols('U4 U6 G13 G22 G23')
original=4*pi**3*Cd*u4+2*pi**4*Cs*u6
pair=4*pi**2*(Cd*g13+Cs*g22)
check('complete lower-block normalization',s.expand(original.subs({u4:g13/pi,u6:2*g22/pi**2})-pair)==0)
check('packed complete lower block',s.expand((-4*pi**2*R*g23).subs(g23,(X*g13+Y*g22)/R)+4*pi**2*(X*g13+Y*g22))==0)
# Repeat the previous assertion as the explicit coefficient equalities (no
# expression-pattern substitution is needed for the composite Cs,Cd values).
check('packed lower coefficient G13',s.simplify(-4*pi**2*Xexpr-4*pi**2*Cd)==0)
check('packed lower coefficient G22',s.simplify(-4*pi**2*Yexpr-4*pi**2*Cs)==0)
# Gamma reflection written with ga=Gamma(s), gb=Gamma(1/2+s),
# S=sin(pi*s), C=cos(pi*s).
g1s=pi/(ga*S);ghs=pi/(gb*C)
M1=ga*ghs**3/(g1s**3*gb)
M2=ga**2*ghs**2/(g1s**2*gb**2)
M0=ghs**4/g1s**4
Kb=ga**2*ghs**4/g1s**2
base=ga**4/gb**4
check('M1 reflected gamma kernel',s.factor(M1-base*(S/C)**3)==0)
check('M2 reflected gamma kernel',s.factor(M2-base*(S/C)**2)==0)
check('M0 reflected gamma kernel',s.factor(M0-base*(S/C)**4)==0)
res=s.together(Kb/pi**2-M1*0-M2-M0)
num=s.fraction(res)[0]
check('Bailey kernel = pi^2(M2+M0)',s.Poly(num,S,C).rem(s.Poly(S*S+C*C-1,S,C)).as_expr()==0)
# sin(pi(s+alpha))=(X*S+Y*C)/R.
shift_sine=(X*S+Y*C)/R
Na=ga**2*ghs**3/(g1s**2*gb)*shift_sine/pi
check('shifted gamma kernel equals sine addition',s.factor(Na-(X*M1+Y*M2)/R)==0)
# The simple-pole residue for G44^(1,3).
for n in range(12):
    half=s.Rational(1,2)
    residue=(-1)**n/s.factorial(n)*s.gamma(n+half)**3/(s.factorial(n)**3*s.gamma(half-n))
    an=s.rf(half,n)/s.factorial(n)
    check(f'G13 residue at -{n}',s.simplify(residue-s.pi*an**4)==0)
# Check local parameter group counts, not merely their concatenated lists.
spec={'id':'G4packed','function':'MeijerG','p':5,'q':5,'m':2,'n':3,
 'upper_numerator':['1/2']*3,'upper_denominator':['1/2','alpha4'],
 'lower_numerator':['0']*2,'lower_denominator':['0','0','alpha4'],
 'argument':'1','coefficient_in_r6':'-4*pi**2*rho4',
 'parameter_branch':'alpha4=atan(Y4/X4)/pi, 0<alpha4<1/2',
 'kernel':'Gamma(s)**2*Gamma(1/2-s)**3/(Gamma(1-s)**2*Gamma(1/2+s)*Gamma(s+alpha4)*Gamma(1-s-alpha4))'}
for side,pkey,nkey in [('upper','p','n'),('lower','q','m')]:
    check(f'{side} total parameter count',len(spec[side+'_numerator'])+len(spec[side+'_denominator'])==spec[pkey])
    check(f'{side} numerator split count',len(spec[side+'_numerator'])==spec[nkey])
check('alpha appears only in two denominator groups','alpha4' not in spec['upper_numerator']+spec['lower_numerator'])
# Elementary sign bounds used to fix the ArcTan branch.
check('Gamma quarter bound below four',s.Rational(4)-s.Rational(4,5)+s.Rational(2,9)+s.Rational(2,5)<4)
check('strict Cs upper bound is negative',60*s.Rational(256,3)-s.Rational(105,4)*25-9*5*3-s.Rational(2469,4)*9<0)
check('strict Cd upper bound is negative',96*s.Rational(256,3)-42*25-18*5*3-1227*9<0)

new['scope']='Partial finite Mathematica-built-in reduction. U6 has a lower-order G44^(2,2) representation. The combined U4,U6 lower-period block is optionally packed into one G55^(2,3) at 1, with alpha4 fixed by already known A and Q. This is order reduction and linear-combination encoding, not an arithmetic-independence result. The wheel, seventh logarithmic block and primitive remain unresolved. No full coefficient evaluation or new interval certificate is claimed.'
records=old['ordinary_hypergeometric_terms_unchanged']
new['legacy_lower_ordinary_records']=[v for v in records if v['id'] in ('U4','U6')]
new['ordinary_hypergeometric_terms_unchanged']=[v for v in records if v['id'] not in ('U4','U6')]
new['univariate_meijer_g_terms'].append(spec)
new['lower_parameters']={'X4':str(Xexpr),'Y4':str(Yexpr),'rho4':'sqrt(X4**2+Y4**2)','alpha4':'atan(Y4/X4)/pi','proof_of_signs':'X4>4171,Y4>2453/2 from A>5, pi>3, Gamma(1/4)<4.'}
new['lower_rational_parameter_alternative']={'U4':'G44^(1,3)((1/2)^4;0^4;1)/pi','U6':'2*G44^(2,2)((1/2)^4;0^4;1)/pi**2','lower_block':'4*pi**2*(Cd*G44^(1,3)+Cs*G44^(2,2))','status':'Two fixed values with rational parameters; independent of the packing angle.'}
new['latest_identity']='4*pi**3*Cd*U4+2*pi**4*Cs*U6=-4*pi**2*rho4*G4packed'
new['known_shift_this_step']='0'
new['finite_value_counts']={'ordinary_hypergeometric':5,'MeijerG_using_rational_Pb_pair':4,'polylogarithmic':2,'total_finite_special_values':11,'before_total_finite_special_values':12,'unresolved_elliptic_blocks':3,'arithmetic_independence_claimed':False}
new['provenance_lower']={'input':src.name,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'external_identity':'Bailey-Mishev Barnes and 7F6 representations at all-half/unit symmetric point','new_full_C6_evaluation':False,'wolfram_kernel_executed':False}
for field in ['new_known_polynomial','source_correction_unchanged','unresolved_blocks','finite_polylog_block_r6_wolfram','remaining_elliptic_blocks_unchanged']:
    check('preserve '+field,new[field]==old[field])
check('retain five ordinary seventh values',len(new['ordinary_hypergeometric_terms_unchanged'])==5)
check('remove only U4 and U6 records',[v['id'] for v in new['legacy_lower_ordinary_records']]==['U4','U6'])
check('Meijer records increased by one',len(new['univariate_meijer_g_terms'])==len(old['univariate_meijer_g_terms'])+1)
check('known polynomial has 18 expanded terms',len(s.Add.make_args(s.expand(s.sympify(new['new_known_polynomial'],locals={'Q':Q}))))==18)
(ROOT/'results'/'updated_expression.json').write_text(json.dumps(new,indent=2)+'\n')
# Static delimiter and disallowed-operator inspection is not Wolfram execution.
wlf=ROOT/'C6_lower_MeijerG_patch.wl'
if wlf.exists():
    text=wlf.read_text();text=re.sub(r'\(\*.*?\*\)','',text,flags=re.S);text=re.sub(r'"(?:\\.|[^"\\])*"','""',text)
    stack=[];pairs={']':'[','}':'{',')':'('}
    for ch in text:
        if ch in '[{(':stack.append(ch)
        elif ch in ']})':
            if not stack or stack.pop()!=pairs[ch]:raise AssertionError('Wolfram delimiters')
    check('Wolfram delimiters balanced',not stack)
    for head in ('Integrate','NIntegrate','Sum','NSum','Limit','Derivative'):
        check('finite Wolfram file has no '+head,re.search(r'\b'+head+r'\s*\[',text) is None)
report={'all_passed':True,'count':len(checks),'checks':checks,'scope':'Finite algebra and static code checks, not a count of independent theorems and not Wolfram-kernel execution.'}
(ROOT/'results'/'exact_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'all_passed':True,'count':len(checks)},indent=2))
