from pathlib import Path
import json, sympy as s, hashlib
from sympy.printing.mathematica import mathematica_code
ROOT=Path(__file__).resolve().parent
src=json.loads((ROOT/'inputs/C6_standard_primitive_expression.json').read_text())
prev=json.loads((ROOT/'inputs/C6_classical_trilog_expression.json').read_text())
A,Q,G,p,z3,z5,ell=s.symbols('A Q G pi z3 z5 ell',real=True)
loc={'A':A,'Q':Q,'G':G,'pi':p,'z3':z3,'z5':z5,'sqrt':s.sqrt,'c7':s.Symbol('c7'),'s7':s.Symbol('s7')}
old=s.sympify(src['known_polynomial'],locals=loc)
cl=s.sympify(prev['known_polynomial'],locals=loc)
new=s.expand(cl-144*Q**3/p+17408*G*p**3-40256*p**2*z3)
# Direct conversion from the CURRENT SVHPL expression, not just from the old basis.
C3=3*p**3/128+p*ell**2/32-G*ell/2
D_B=208896*(2*G*C3+G*p**3/96+s.Rational(33,512)*p**2*z3)
D_S=17408*G*p**3-40256*p**2*z3
assert s.expand(old+(D_B+D_S).subs(ell,(A-p)/4)-new)==0
checks={'known_polynomial_shift_exact':True,'before_monomials':len(s.Add.make_args(old)),
        'after_monomials':len(s.Add.make_args(new)),
        'native_mathematica_kernel_executed':False}
# Native expression metadata includes only ordinary functions and explicit quadrature.
out={'normalization':src['normalization'],
 'formula':'2187*C6 = native_known_polynomial + ordinary_fixed_values - 39168*pi**2*Im(PolyLog(3,(1+i)/2)) + Integral(Rpoly(x)+Rwheel(x)+Rseventh(x)+Rprimitive(x),x=0..1)',
 'scope':'Exact reformulation of inherited analytic expression in built-in univariate special functions and explicit one-dimensional quadrature. NOT a finite special-value-only closed form. No new physical graph/RG proof.',
 'native_known_polynomial':str(new),'shift_from_current':str(s.expand(new-old)),
 'ordinary_hypergeometric_terms':src['ordinary_hypergeometric_terms'],
 'finite_weights':src['seventh_finite_weights'],
 'kernels':{
  'Rpoly':'-417792*log(x)*Re((pi*Log(1-i*x)**2/4-i*PolyLog(3,1-i*x))/(1-i*x))',
  'Rwheel':'4*log(x)/(1+x)*(3144*pi**3*U4(x**2)+1965*pi**4*U6(x**2))',
  'Rseventh':'9408*pi**(3/2)*sum_r(p_r*x**((r+2)/4-1)*(Z_r(-1)-Z_r(-x**2))/(1-x)), r in {1,2,3,5,7} (finite sum)',
  'lambda':'x/(2*(1+sqrt(1-x)))',
  'K':'EllipticK(lambda(x))','Kc':'EllipticK(1-lambda(x))',
  'a':'(K(x)+Kc(x))*(K(1-x)+Kc(1-x))',
  'b':'K(x)*K(1-x)',
  'Rprimitive':'1536*(15*a**2+24*a*b-4*b**2)/sqrt(x*(1-x))'},
 'elliptic_identifications':{'v':'2*EllipticK(lambda(x))/pi',
  'sqrt(Q)*h(1-x)':'2*(EllipticK(lambda(x))+EllipticK(1-lambda(x)))',
  'g1':'4*K**2/pi**(3/2)','g2':'4*K*Kc/pi**(3/2)','g3':'2*(Kc**2-K**2)/pi**(3/2)'},
 'source_correction':src['source_correction'],
 'counts':{'rare_special_function_heads':0,'ordinary_fixed_hypergeometric_values':13,
 'fixed_classical_trilogarithm_values':1,'explicit_1D_integral_blocks':4,
 'can_combine_integral_blocks_into_one':True,'infinite_sums_in_active_formula':0,
 'parameter_derivatives_in_active_formula':0,'new_known_monomials':19,
 'finite_closed_form_claimed':False},
 'provenance':{'input_file':'C6_standard_primitive_expression.json','sha256':hashlib.sha256((ROOT/'inputs/C6_standard_primitive_expression.json').read_bytes()).hexdigest()},
 'implementation_notes':['Wolfram Language code supplied but no Wolfram kernel executed here.','Python checks do not constitute interval certification.','CarlsonRF is used only as the built-in stable form EllipticK(1-m)=CarlsonRF(0,m,1).']}
(ROOT/'results/expression.json').write_text(json.dumps(out,indent=2)+'\n')
(ROOT/'results/exact_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
# Mathematica code: exact symbols mapped only after polynomial collection.
wlvars={A:s.Symbol('aa'),Q:s.Symbol('qq'),G:s.Symbol('Catalan'),p:s.Symbol('Pi'),z3:s.Function('Zeta')(3),z5:s.Function('Zeta')(5),s.Symbol('c7'):s.cos(s.Symbol('Pi')/8)**7,s.Symbol('s7'):s.sin(s.Symbol('Pi')/8)**7}
def wl(expr):return mathematica_code(s.sympify(expr,locals=loc).xreplace(wlvars))
rows=[]
for it in src['ordinary_hypergeometric_terms']:
 rows.append('  {"'+it['id']+'", {'+', '.join(it['upper'])+'}, {'+', '.join(it['lower'])+'}, '+it['argument']+', '+wl(it['prefactor'])+', '+wl(it['coefficient_in_r6'])+'}')
weights=[src['seventh_finite_weights'][str(r)]['p_r'] for r in [1,2,3,5,7]]
head='''(* Exact inherited C6(1), Mathematica-native special functions plus quadrature.
   No external packages. No bivariate Fox H, Kampe de Feriet, or SVHPL heads.
   This is NOT a finite special-value-only evaluation.
   Local Wolfram kernel execution was not available for this deliverable.
   All numerical integration goals are empirical, not certified error bounds. *)
BeginPackage["C6Native`"];
C6NativeExpression::usage = "C6NativeExpression[] gives the exact native expression with an inactive real integral.";
C6NativeEvaluate::usage = "C6NativeEvaluate[d] evaluates each integral block separately, requesting d output digits, and returns a block report.";
Begin["`Private`"];
aa = Pi + 4 Log[2];
qq = Gamma[1/4]^4/Pi;
'''
head+='known = '+wl(new)+';\n'
head+='data = {\n'+',\n'.join(rows)+'\n};\n'
head+='shifts = {1,2,3,5,7};\nweights = {'+', '.join(wl(x) for x in weights)+'};\n'
head+='''u4[x_] := HypergeometricPFQ[ConstantArray[1/2,4], ConstantArray[1,3], x];
u6[x_] := HypergeometricPFQ[Join[{5/4},ConstantArray[1/2,6]], Join[{1/4},ConstantArray[1,5]], x];
zfun[r_,w_] := With[{t=r/8,a=(r+2)/8,b=(r+6)/8},
 t (Gamma[a]/Gamma[b])^7 HypergeometricPFQ[Join[{1,1+t},ConstantArray[a,7]],Join[{t},ConstantArray[b,7]],w]];
lam[x_] := x/(2(1+Sqrt[1-x]));
kk[x_] := EllipticK[lam[x]];
kc[x_] := EllipticK[1-lam[x]];
polyKernel[x_] := -417792 Log[x] Re[(Pi Log[1-I x]^2/4-I PolyLog[3,1-I x])/(1-I x)];
wheelKernel[x_] := 4 Log[x]/(1+x) (3144 Pi^3 u4[x^2]+1965 Pi^4 u6[x^2]);
seventhKernel[x_] := 9408 Pi^(3/2) Total[MapThread[
 Function[{r,w},w x^((r+2)/4-1) (zfun[r,-1]-zfun[r,-x^2])/(1-x)],{shifts,weights}]];
primitiveKernel[x_] := With[{a=(kk[x]+kc[x])(kk[1-x]+kc[1-x]),b=kk[x]kk[1-x]},
 1536 (15a^2+24a b-4b^2)/Sqrt[x(1-x)]];
ordinaryExact[] := Total[Function[row,row[[6]] row[[5]] HypergeometricPFQ[row[[2]],row[[3]],row[[4]]]] /@ data];
C6NativeExpression[] := Module[{x},
 (known+ordinaryExact[]-39168 Pi^2 Im[PolyLog[3,(1+I)/2]]+
  Inactive[Integrate][polyKernel[x]+wheelKernel[x]+seventhKernel[x]+primitiveKernel[x],{x,0,1}])/2187];
C6NativeEvaluate::digits = "The digit request must be an integer between 10 and 200.";
C6NativeEvaluate[digits_Integer:25] := Module[
 {wp,goal,pn,qn,wn,ordvals,ord,zn,zp,up,lo,pref,t,a,b,znum,zprime,
 pol,wh,sev,prim,ni,iv,raw,u,x,la,lb,k,ks,kcomp,kscomp,ap,bp},
 If[digits<10||digits>200,Message[C6NativeEvaluate::digits];Return[$Failed]];
 wp=digits+25;goal=digits+5;
 pn=N[Pi,wp];qn=N[qq,wp];wn=N[weights,wp];
 Block[{$MaxExtraPrecision=4wp},
  ordvals=Function[row,N[row[[5]],wp] HypergeometricPFQ[row[[2]],row[[3]],N[row[[4]],wp]]] /@ data;
  ord=Total[N[data[[All,6]],wp] ordvals];
  up=Table[Join[{1,1+r/8},ConstantArray[(r+2)/8,7]],{r,shifts}];
  lo=Table[Join[{r/8},ConstantArray[(r+6)/8,7]],{r,shifts}];
  pref=N[Table[(r/8)(Gamma[(r+2)/8]/Gamma[(r+6)/8])^7,{r,shifts}],wp];
  znum[j_Integer,w_?NumericQ] := pref[[j]] HypergeometricPFQ[up[[j]],lo[[j]],w];
  zn=Table[znum[j,N[-1,wp]],{j,5}];
  zp=Table[pref[[j]] (Times@@up[[j]])/(Times@@lo[[j]])
     HypergeometricPFQ[up[[j]]+1,lo[[j]]+1,N[-1,wp]],{j,5}];
  pol[u_?NumericQ] := If[u==0,0,-417792 Log[u] Re[(pn Log[1-I u]^2/4-I PolyLog[3,1-I u])/(1-I u)]];
  (* x=u^4 removes endpoint powers; u=1 has a removable zero. *)
  wh[u_?NumericQ] := If[u==0||u==1,0,With[{x=u^4},
     16u^3 Log[x]/(1+x) (3144pn^3 u4[x^2]+1965pn^4 u6[x^2])]];
  sev[u_?NumericQ] := Which[u==0,0,u==1,-75264pn^(3/2) Total[wn zp],True,
    37632pn^(3/2) Total[Table[wn[[j]] u^(shifts[[j]]+1)
      (zn[[j]]-znum[j,-u^8])/(1-u^4),{j,5}]]];
  (* Fold reflection symmetry and put x=u^4/2. CarlsonRF avoids subtracting a
     tiny parameter from 1 in a complementary complete elliptic integral. *)
  prim[u_?NumericQ] := If[u==0,0,Module[{x=u^4/2,la,lb,k,ks,kcomp,kscomp,ap,bp},
    la=x/(2(1+Sqrt[1-x]));lb=(1-Sqrt[x])/2;
    k=EllipticK[la];ks=EllipticK[lb];
    kcomp=CarlsonRF[0,la,1];kscomp=CarlsonRF[0,lb,1];
    ap=(k+kcomp)(ks+kscomp);bp=k ks;
    6144 Sqrt[2] u (15ap^2+24ap bp-4bp^2)/Sqrt[1-x]]];
  ni[f_] := NIntegrate[f[u],{u,0,1/4,1/2,3/4,1},WorkingPrecision->wp,
    AccuracyGoal->goal,PrecisionGoal->goal,MaxRecursion->25,
    Method->{"GlobalAdaptive","SymbolicProcessing"->0}];
  iv=<|"PolylogIntegral"->ni[pol],"WheelIntegral"->ni[wh],
        "SeventhIntegral"->ni[sev],"PrimitiveIntegral"->ni[prim]|>;
  raw=(N[known,wp]+ord-39168pn^2 Im[PolyLog[3,N[(1+I)/2,wp]]]+Total[Values[iv]])/2187;
  <|"C6"->N[raw,digits],"UnroundedC6"->raw,"WorkingPrecision"->wp,
    "KnownPolynomialInR6Units"->N[known,wp],"OrdinaryValuesInR6Units"->ord,
    "ClassicalTrilogInR6Units"->-39168pn^2 Im[PolyLog[3,N[(1+I)/2,wp]]],
    "IntegralBlocksInR6Units"->iv,
    "CertifiedInterval"->False,
    "Qualification"->"Numerical quadrature of an inherited analytic representation; inspect any integration warnings."|>
 ]
];
End[];
EndPackage[];
'''
(ROOT/'C6Native.wl').write_text(head)
print('Polynomial monomials:',len(s.Add.make_args(old)),'->',len(s.Add.make_args(new)))
print('wrote',ROOT/'C6Native.wl')
