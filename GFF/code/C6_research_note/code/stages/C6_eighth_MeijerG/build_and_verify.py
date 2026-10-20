"""Exact finite algebra for a univariate-MeijerG representation of the eighth block.
The historical graph/period identification is an input, not proved by these tests.
"""
from pathlib import Path
import copy, hashlib, json, re
import sympy as s
from sympy.printing.mathematica import mathematica_code
ROOT=Path(__file__).resolve().parent
source=ROOT/'inputs/previous_partial_expression.json'
old=json.loads(source.read_text())
checks=[]
def ck(label, expr):
    if s.simplify(s.expand(expr))!=0:
        raise AssertionError((label,s.simplify(expr)))
    checks.append(label)
h,d,y,p,T=s.symbols('h d y p T', real=True)
r=s.sqrt(2)
a=1233-278*r;b=s.Integer(556);c=139*r
rho2=s.expand((a-c)**2+b*b)
ck('radical normalization',rho2-(2177203-1028322*r))
ck('angle numerator',a+c-(1233-139*r))
ck('angle denominator',a-c-(1233-417*r))
ck('positive discriminant identity',4*a*c-b*b-(685548*r-618272))
assert a>c>0 and 4*a*c-b*b>0
checks.append('real angle and positive inverse-hyperbolic-cosine domain')
# Local residues derived from the gamma ratio expansion, to the required order.
e=s.symbols('e')
f=1+16*h*e+(128*h*h+4*d-8*p*p/3)*e*e
R1=p**3*y
R2=p**2*(16*y*h-1)
R3=p*(y*(128*h*h+4*d-p*p)-16*h)
for j,want in [(1,R1),(2,R2),(3,R3)]:
    analytic=f*(1+(8-j)*p*p*e*e/3)*(y-e)
    got=p**(4-j)*s.expand(analytic).coeff(e,j-1)
    ck(f'weighted residue j={j}',got-want)
u=1-16*y*h
v=256*y*h*h-32*h+8*y*d-8*p*p*y
pz=(816+92*r)*p**6*y-368*p**5*u+46*r*p**4*v
pk=(432+48*r)*p**6*y-192*p**5*u+24*r*p**4*v
old_summand=8*p**4*((2466-834*r)*p*p*y-1112*p*u+139*r*(256*y*h*h-32*h+8*y*d))
ck('inherited eighth block weights',24*pz+pk/3-old_summand)
new_summand=16*p**3*(a*R1+b*R2+c*R3)
ck('complete coefficient-to-residue match',old_summand-new_summand)
ck('shared Barnes kernel polynomial',a*T**7+b*T**6+c*T**5-T**5*(a*T*T+b*T+c))
ck('rational-kernel N37',T**7+T**5-T**5*(1+T*T))
ck('rational-kernel N46',T**6+T**4-T**4*(1+T*T))
# Replace trig functions by real sine/cosine variables; all coefficients are exact.
x,z=s.symbols('x z',real=True)
quad=a*x*x+b*x*z+c*z*z
via_angle=((a+c)*(x*x+z*z)-(a-c)*(z*z-x*x)+2*b*x*z)/2
ck('quadratic sine-product factorization',quad-via_angle)
# The gamma prefactor (1/4-s) is an exact contiguous factor.
w=s.symbols('w')
ck('linear Mellin multiplier',s.Rational(1,4)-w-(s.Rational(5,4)-w-1))
# Kernel reflection: on s -> 1/2-s, j -> 8-j; the multiplier changes sign.
ck('antisymmetric Mellin multiplier',s.Rational(1,4)-(s.Rational(1,2)-w)+(s.Rational(1,4)-w))
U,J37,J46,K1,K2,K3=s.symbols('U J37 J46 K1 K2 K3')
raw=16*p**3*(a*K1+b*K2+c*K3)
alt=4*p**6*(1233-417*r)*U+16*p*(139*r*J37+556*J46)
ck('rational alternative full coefficient',raw.subs({K1:p**3*U/4,K2:J46/p**2,K3:J37/p**2-p**3*U/4})-alt)
# Pochhammer and coefficient checks, including the n=0 term.
for n in [0,1,2,3,5,10]:
    an=s.rf(s.Rational(1,2),n)/s.factorial(n)
    up=s.rf(s.Rational(5,4),n)*s.rf(s.Rational(1,2),n)**8
    dn=s.rf(s.Rational(1,4),n)*s.factorial(n)**8
    ck(f'U8 coefficient n={n}',up/dn-(4*n+1)*an**8)
for rr in [1,7]:
    t=s.Rational(rr,8);aa=t+s.Rational(1,4);bb=t+s.Rational(3,4)
    for n in [0,1,2,5]:
        coefficient=s.rf(1+t,n)*s.rf(aa,n)**8/(s.rf(t,n)*s.rf(bb,n)**8)
        ck(f'Y{rr} normalized coefficient n={n}',t*coefficient-(n+t)*(s.rf(aa,n)/s.rf(bb,n))**8)
# A deliberately restricted wheel test; this is NOT a general no-go theorem.
A0,A1,A2=s.symbols('A0 A1 A2')
wheel_poly=s.Poly(A0+A1*h+A2*(32*h*h+2*d-p*p)-d,h,d,p)
assert s.solve(wheel_poly.coeffs(),(A0,A1,A2))==[]
checks.append('restricted three-residue wheel ansatz does not isolate delta')

new=copy.deepcopy(old)
removed=[r for r in old['ordinary_hypergeometric_terms_unchanged'] if r['id'] in {'U8','Y1','Y7'}]
assert len(removed)==3
remaining=[r for r in old['ordinary_hypergeometric_terms_unchanged'] if r['id'] not in {'U8','Y1','Y7'}]
assert len(remaining)==7
new['ordinary_hypergeometric_terms_unchanged']=remaining
new['scope']='Partial finite Mathematica-built-in representation. The COMPLETE ordinary eighth-power block 24*PZ6+PK6/3 is replaced by one univariate MeijerG[11,11;3,8] value with two explicitly elementary conjugate parameters. This compresses three standard values to one; it does NOT evaluate the wheel, seventh logarithmic sector, or primitive, and it does not prove arithmetic dependence of periods. All earlier inputs are inherited.'
new['known_shift_this_step']='0'
new['latest_identity']='24*PZ6+PK6/3 = 16*pi**3*rho8*G8'
new['eighth_parameters']={
 'rho8':'sqrt(2177203-1028322*sqrt(2))',
 'd8':'atan(556/(1233-417*sqrt(2)))/(2*pi)',
 'eta8':'acosh((1233-139*sqrt(2))/rho8)/(2*pi)',
 'alpha_plus':'d8+i*eta8', 'alpha_minus':'d8-i*eta8',
 'parameter_branch':'d8,eta8 positive real; all inverse functions principal',
 'a_for_proof':'1233-278*sqrt(2)', 'b_for_proof':'556', 'c_for_proof':'139*sqrt(2)'}
newterm={'id':'G8','function':'ordinary univariate MeijerG','p':11,'q':11,'m':3,'n':8,
 'upper_numerator':['-1/4']+['1/2']*7,
 'upper_denominator':['1/2','alpha_plus','alpha_minus'],
 'lower_numerator':['0']*3,
 'lower_denominator':['0']*5+['3/4','alpha_plus','alpha_minus'],
 'argument':'1','coefficient_in_r6':'16*pi**3*rho8',
 'Mellin_contour_for_proof':'Re(s)=1/4, upward',
 'proof_kernel':'Gamma(s)**3*Gamma(1/2-s)**7*Gamma(5/4-s)/(Gamma(1-s)**5*Gamma(1/2+s)*Gamma(1/4-s)*Gamma(s+alpha_plus)*Gamma(1-s-alpha_plus)*Gamma(s+alpha_minus)*Gamma(1-s-alpha_minus))',
 'no_parameter_derivative_or_limit':True,'repeated_parameters_in_denominators_do_not_cancel':True,
 'new_rigorous_interval_claimed':False}
new['univariate_meijer_g_terms'].append(newterm)
new['eighth_rational_parameter_alternative']={
 'formula':'pi**6*(4932-1668*sqrt(2))*U8+16*pi*(139*sqrt(2)*J37+556*J46)',
 'J37':{'p':9,'q':9,'m':3,'n':8,'upper_numerator':['-1/4']+['1/2']*7,'upper_denominator':['1/2'],'lower_numerator':['0']*3,'lower_denominator':['0']*5+['3/4'],'argument':'1'},
 'J46':{'p':9,'q':9,'m':4,'n':7,'upper_numerator':['-1/4']+['1/2']*6,'upper_denominator':['1/2']*2,'lower_numerator':['0']*4,'lower_denominator':['0']*4+['3/4'],'argument':'1'},
 'U8':'9F8(5/4,(1/2)^8;1/4,1^7;1)',
 'tradeoff':'3 calls, all rational parameters. Primary form has 1 higher-order call with nonrational conjugate parameters. Neither is claimed numerically faster.'}
new['legacy_eighth_ordinary_records']=removed
new['provenance']={'input':'inputs/previous_partial_expression.json','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'inherited_identity':'C6_even_sector_derivation.md equations (8)-(10)','new_full_C6_evaluation':False,'Wolfram_kernel_executed':False}
for key in ['new_known_polynomial','finite_polylog_block_r6_wolfram','source_correction_unchanged','unresolved_blocks','remaining_elliptic_blocks_unchanged','optional_single_meijer_g_form']:
    assert new[key]==old[key]; checks.append(f'preserve {key}')
assert new['new_known_polynomial']==old['new_known_polynomial']
poly=s.sympify(old['new_known_polynomial'],locals={v:s.Symbol(v) for v in ['A','Q','G','z3','z5']})
assert len(s.Add.make_args(s.expand(poly)))==18
checks.append('known polynomial remains 18 expanded monomials')
assert len(newterm['upper_numerator'])==8 and len(newterm['upper_denominator'])==3
assert len(newterm['lower_numerator'])==3 and len(newterm['lower_denominator'])==8
checks.append('MeijerG 11,11 / 3,8 parameter splits')
new['finite_value_counts']={'ordinary_hypergeometric':7,'MeijerG_using_rational_Pb_pair':3,'polylogarithmic':2,'total_finite_special_values':12,'before_total_finite_special_values':14,'unresolved_elliptic_blocks':3,'arithmetic_independence_claimed':False}

# Generate a standalone Wolfram file with finite expressions only.
loc={'Gamma':s.gamma,'sqrt':s.sqrt,'A':s.Symbol('aa'),'Q':s.Symbol('qq'),'G':s.Catalan,'z3':s.zeta(3),'z5':s.zeta(5),'c7':s.Symbol('cc7'),'s7':s.Symbol('ss7')}
def wc(v):return mathematica_code(s.sympify(v,locals=loc))
def wl_list(items):return '{'+', '.join(wc(v) for v in items)+'}'
ordinary=[]
for row in remaining:
 ordinary.append('('+wc(row['coefficient_in_r6'])+') ('+wc(row['prefactor'])+') HypergeometricPFQ['+wl_list(row['upper'])+', '+wl_list(row['lower'])+', '+wc(row['argument'])+']')
known=wc(old['new_known_polynomial'])
wl=r'''(* Finite eighth-power block only; not a complete finite evaluation of C6.
   The functions C6FinitePartR6[] and C6ReductionStatus[] label that distinction.
   This file has not been executed in a Wolfram kernel here. *)
BeginPackage["C6EighthReduction`"];
C6EighthParameters::usage="C6EighthParameters[] returns exact MeijerG parameters.";
C6EighthBlockSingle::usage="C6EighthBlockSingle[] is the complete 24 PZ6 + PK6/3 block in r6 units, using one ordinary MeijerG.";
C6EighthBlockRational::usage="C6EighthBlockRational[] gives an equivalent rational-parameter form with three standard function values.";
C6EighthBlockOriginal::usage="C6EighthBlockOriginal[] is the preceding three-hypergeometric-value expression.";
C6EighthNumericalCheck::usage="C6EighthNumericalCheck[wp] compares the three finite expressions in your Wolfram kernel; no accuracy certification is implied.";
C6FinitePartR6::usage="C6FinitePartR6[] returns ONLY the reduced finite part of 2187 C6. The three elliptic residual blocks are NOT included.";
C6ReductionStatus::usage="C6ReductionStatus[] states the unresolved parts explicitly.";
Begin["`Private`"];
rho8=Sqrt[2177203-1028322 Sqrt[2]];
d8=ArcTan[556/(1233-417 Sqrt[2])]/(2 Pi);
eta8=ArcCosh[(1233-139 Sqrt[2])/rho8]/(2 Pi);
ap=d8+I eta8; am=d8-I eta8;
C6EighthParameters[]:=<|"Scale"->rho8,"AlphaPlus"->ap,"AlphaMinus"->am|>;
C6EighthBlockSingle[]:=16 Pi^3 rho8 MeijerG[
 {{-1/4,1/2,1/2,1/2,1/2,1/2,1/2,1/2},{1/2,ap,am}},
 {{0,0,0},{0,0,0,0,0,3/4,ap,am}},1];
u8[]:=HypergeometricPFQ[{5/4,1/2,1/2,1/2,1/2,1/2,1/2,1/2,1/2},{1/4,1,1,1,1,1,1,1},1];
j37[]:=MeijerG[{{-1/4,1/2,1/2,1/2,1/2,1/2,1/2,1/2},{1/2}},{{0,0,0},{0,0,0,0,0,3/4}},1];
j46[]:=MeijerG[{{-1/4,1/2,1/2,1/2,1/2,1/2,1/2},{1/2,1/2}},{{0,0,0,0},{0,0,0,0,3/4}},1];
C6EighthBlockRational[]:=4 Pi^6 (1233-417 Sqrt[2]) u8[]+16 Pi (139 Sqrt[2] j37[]+556 j46[]);
y1[]:=(Gamma[3/8]/Gamma[7/8])^8 HypergeometricPFQ[{1,9/8,3/8,3/8,3/8,3/8,3/8,3/8,3/8,3/8},{1/8,7/8,7/8,7/8,7/8,7/8,7/8,7/8,7/8},1]/8;
y7[]:=7 (Gamma[9/8]/Gamma[13/8])^8 HypergeometricPFQ[{1,15/8,9/8,9/8,9/8,9/8,9/8,9/8,9/8,9/8},{7/8,13/8,13/8,13/8,13/8,13/8,13/8,13/8,13/8},1]/8;
C6EighthBlockOriginal[]:=Pi^6 (4932-5004 Sqrt[2]) u8[]+556 Pi^2 ((17+12 Sqrt[2]) y1[]-(17-12 Sqrt[2]) y7[]);
C6EighthNumericalCheck[wp_Integer:40]/;wp>=20:=Module[{original,single,rational},
 Block[{$MaxExtraPrecision=4 wp},original=N[C6EighthBlockOriginal[],wp];single=N[C6EighthBlockSingle[],wp];rational=N[C6EighthBlockRational[],wp]];
 <|"Original"->original,"Single"->single,"RationalAlternative"->rational,"SingleDifference"->single-original,"RationalDifference"->rational-original,"WorkingPrecision"->wp|>];
aa=Pi+4 Log[2];qq=Gamma[1/4]^4/Pi;cc7=Cos[Pi/8]^7;ss7=Sin[Pi/8]^7;
'''
wl+='known='+known+';\n'
wl+='ordinaryR6[]:='+'+\n'.join(ordinary)+';\n'
wl+=r'''pbR6[]:=192 Pi (
 13 MeijerG[{{1/2,1/2,1/2,1/2,1/2},{1/2}},{{0,0,0},{0,0,0}},1]
 +11 MeijerG[{{1/2,1/2,1/2,1/2},{1/2,1/2}},{{0,0,0,0},{0,0}},1]);
C6FinitePartR6::hpl="This expression requires the System`HarmonicPolyLog built-in; no custom fallback has been installed.";
C6FinitePartR6[]:=If[!MemberQ[Attributes[System`HarmonicPolyLog],Protected],Message[C6FinitePartR6::hpl];$Failed,
 known+ordinaryR6[]+pbR6[]+C6EighthBlockSingle[]+
 4352 ((32 Catalan+9 Pi^2) Im[PolyLog[1,2,I]]-64 Re[System`HarmonicPolyLog[{0,1,1,0,1},I]])];
C6ReductionStatus[]:=<|"FullIntegralFreeSumFreeC6Established"->False,"OmittedFromFinitePart"->{"wheel","seventh-power logarithmic sector","primitive Pa"},"KnownPolynomialChangedThisStep"->False,"ThisFileWasExecutedInWolframKernelByAuthor"->False|>;
End[];
EndPackage[];
'''
# Static checks are explicitly not execution.
without_comments=re.sub(r'\(\*.*?\*\)','',wl,flags=re.S)
for forbidden in ['Integrate','NIntegrate','Sum','NSum','Limit','Derivative']:
    assert not re.search(r'\b'+forbidden+r'\s*\[',without_comments)
checks.append('no integral, sum, limit or derivative calls in Wolfram output')
text=re.sub(r'"(?:\\.|[^"\\])*"','""',without_comments)
stack=[];pairs={']':'[','}':'{',')':'('}
for ch in text:
    if ch in '[{(':stack.append(ch)
    elif ch in ']})':assert stack and stack.pop()==pairs[ch]
assert not stack
checks.append('balanced Wolfram delimiters, static only')
(ROOT/'C6_eighth_MeijerG_patch.wl').write_text(wl)
(ROOT/'results/partial_expression.json').write_text(json.dumps(new,indent=2)+'\n')
report={'check_count':len(checks),'checks':checks,'all_passed':True,'Wolfram_kernel_executed':False,'new_full_C6_evaluation':False,'new_interval_certificate':False,'restricted_wheel_ansatz_only':True}
(ROOT/'results/exact_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
