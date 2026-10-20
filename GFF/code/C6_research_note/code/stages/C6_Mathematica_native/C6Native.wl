(* Exact inherited C6(1), Mathematica-native special functions plus quadrature.
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
known = 3072*Catalan^2*aa + 22848*Catalan*Pi^3 - 4320*Catalan*Pi^2*aa + 15*Catalan*aa*qq + (164927/128)*Pi^5 - 83067/640*Pi^4*aa + (6045/64)*Pi^3*aa^2 + (2013/8)*Pi^3*qq + (7/64)*Pi^2*aa^3 + (79/8)*Pi^2*aa*qq - 424371/16*Pi^2*Zeta[3] + 29*Pi*qq^2 + (21/640)*aa^5 + (63/8)*aa^3*qq + (7863/16)*aa^2*Zeta[3] - 249*aa*qq^2 + (13551/2)*qq*Zeta[3] - 805959/8*Zeta[5] - 144*qq^3/Pi;
data = {
  {"U4", {1/2, 1/2, 1/2, 1/2}, {1, 1, 1}, 1, 1, 4*Pi^3*(-1227*Pi^2 - 18*Pi*aa - 42*aa^2 + 96*qq)},
  {"U6", {5/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/4, 1, 1, 1, 1, 1}, 1, 1, 2*Pi^4*(-2469/4*Pi^2 - 9*Pi*aa - 105/4*aa^2 + 60*qq)},
  {"Hminus", {1, 1/4, 1/4, 1/4, 1/4, 1/4, 1/4}, {3/4, 3/4, 3/4, 3/4, 3/4, 3/4}, 1, 1, 288*qq^3/Pi},
  {"H0", {1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1, 1, 1, 1, 1}, 1, 1, -2496*Pi^5},
  {"Hplus", {1, 3/4, 3/4, 3/4, 3/4, 3/4, 3/4}, {5/4, 5/4, 5/4, 5/4, 5/4, 5/4}, 1, 1, 6291456*Pi^5/qq^3},
  {"U8", {5/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/4, 1, 1, 1, 1, 1, 1, 1}, 1, 1, Pi^6*(4932 - 5004*2^(1/2))},
  {"Y1", {1, 9/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8}, {1/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8}, 1, (1/8)*Gamma[3/8]^8/Gamma[7/8]^8, 556*Pi^2*(12*2^(1/2) + 17)},
  {"Y7", {1, 15/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8}, {7/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8}, 1, (7/8)*Gamma[9/8]^8/Gamma[13/8]^8, -556*Pi^2*(17 - 12*2^(1/2))},
  {"Z7_1", {1, 9/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8}, {1/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8}, -1, (1/8)*Gamma[3/8]^7/Gamma[7/8]^7, 96*Pi^(3/2)*(Pi*(1127*2^(1/2) + 2303) - 55*aa*(13 + 22*2^(1/2)))*Cos[(1/8)*Pi]^7},
  {"Z7_2", {5/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/4, 1, 1, 1, 1, 1, 1}, -1, (1/4)*Gamma[1/2]^7/Gamma[1]^7, 96*Pi^(3/2)*((3283/2)*Pi - 1295/2*aa)},
  {"Z7_3", {1, 11/8, 5/8, 5/8, 5/8, 5/8, 5/8, 5/8, 5/8}, {3/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8}, -1, (3/8)*Gamma[5/8]^7/Gamma[9/8]^7, 96*Pi^(3/2)*(Pi*(-2303 + 1127*2^(1/2)) + (-13 + 22*2^(1/2))*(392 - 55*aa))*Cos[(1/8)*Pi]^7},
  {"Z7_5", {1, 13/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8}, {5/8, 11/8, 11/8, 11/8, 11/8, 11/8, 11/8, 11/8}, -1, (5/8)*Gamma[7/8]^7/Gamma[11/8]^7, 96*Pi^(3/2)*(Pi*(2303 - 1127*2^(1/2)) + (-13 + 22*2^(1/2))*(55*aa - 392/3))*Sin[(1/8)*Pi]^7},
  {"Z7_7", {1, 15/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8}, {7/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8}, -1, (7/8)*Gamma[9/8]^7/Gamma[13/8]^7, 96*Pi^(3/2)*(Pi*(1127*2^(1/2) + 2303) + (13 + 22*2^(1/2))*(2352/5 - 55*aa))*Sin[(1/8)*Pi]^7}
};
shifts = {1,2,3,5,7};
weights = {(13 + 22*2^(1/2))*Cos[(1/8)*Pi]^7, -35, (-13 + 22*2^(1/2))*Cos[(1/8)*Pi]^7, -(-13 + 22*2^(1/2))*Sin[(1/8)*Pi]^7, (13 + 22*2^(1/2))*Sin[(1/8)*Pi]^7};
u4[x_] := HypergeometricPFQ[ConstantArray[1/2,4], ConstantArray[1,3], x];
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
