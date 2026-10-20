(* One-index Chebyshev representation of the complete cubic primitive.
   Only ordinary univariate MeijerG occurs in the coefficients.
   This is NOT a finite special-value-only formula: one infinite sum remains.
   The file was statically checked, not executed in a Wolfram kernel here. *)
BeginPackage["C6PrimitiveChebyshev`"];
PrimitiveMode::usage = "PrimitiveMode[j,n] is the exact G44 coefficient for j=1,2,3 and n>=0.";
PrimitiveSpectralExpression::usage = "PrimitiveSpectralExpression[] returns Pa, with the single infinite sum inactive.";
PrimitiveCubicSpectralExpression::usage = "PrimitiveCubicSpectralExpression[] returns Pa/(2 Pi^2).";
PrimitiveContributionR6::usage = "PrimitiveContributionR6[] returns the entire 96 Pa contribution to r6=2187 C6.";
PrimitiveSpectralPartial::usage = "PrimitiveSpectralPartial[N,d] computes N literal spectral modes at d+25 working digits. This is a partial sum, not a certified value of Pa.";
PrimitiveSpectralStatus::usage = "PrimitiveSpectralStatus[] reports normalization and limitations.";
Begin["`Private`"];
PrimitiveMode[1,n_] := MeijerG[
  {{1/2,1/2,1/2},{1/2}}, {{n},{0,0,-n}}, 1];
PrimitiveMode[2,n_] := MeijerG[
  {{1/2,1/2},{1/2,1/2}}, {{0,n},{0,-n}}, 1];
PrimitiveMode[3,n_] := MeijerG[
  {{1/2},{1/2,1/2,1/2}}, {{0,0,n},{-n}}, 1];
modePolynomial[v_List] := 10 v[[1]]^2 + 21 v[[1]] v[[2]] + 18 v[[2]]^2 + 15 v[[2]] v[[3]];
phi[n_] := modePolynomial[{PrimitiveMode[1,n],PrimitiveMode[2,n],PrimitiveMode[3,n]}];
PrimitiveSpectralExpression[] := Module[{n},
  With[{p0=phi[0],term=2(-1)^n phi[n]},
    8 Pi^3 (p0+Inactive[Sum][term,{n,1,Infinity}])]];
PrimitiveCubicSpectralExpression[] := PrimitiveSpectralExpression[]/(2 Pi^2);
PrimitiveContributionR6[] := 96 PrimitiveSpectralExpression[];
PrimitiveSpectralPartial::arg = "Use integers N>=2 and 10<=d<=200.";
PrimitiveSpectralPartial[nmax_Integer:128,digits_Integer:40] := Module[
  {wp,rows,n,j,s,pn},
  If[nmax<2 || digits<10 || digits>200, Message[PrimitiveSpectralPartial::arg]; Return[$Failed]];
  wp=digits+25; pn=N[Pi,wp];
  rows=ConstantArray[0,{nmax,3}];
  rows[[1]]=N[{PrimitiveMode[1,0],PrimitiveMode[2,0],PrimitiveMode[3,0]},wp];
  rows[[2]]=N[{PrimitiveMode[1,1],PrimitiveMode[2,1],PrimitiveMode[3,1]},wp];
  If[!And@@(NumericQ /@ Flatten[rows[[1;;2]]]),
    Return[Failure["SeedEvaluation",<|"MessageTemplate"->"The six MeijerG seed values did not all evaluate numerically."|>]]];
  Do[rows[[n+2]]=Table[
    (4 n (4 n^2+1) rows[[n+1,j]]-(2n-1)^3 rows[[n,j]]
      +32(j-2)n(-1)^n/pn)/(2n+1)^3,{j,1,3}],{n,1,nmax-2}];
  s=modePolynomial[rows[[1]]]+Total[Table[2(-1)^n modePolynomial[rows[[n+1]]],{n,1,nmax-1}]];
  <|"ModesRetained"->nmax,"WorkingPrecision"->wp,
    "PaPartial"->N[8 pn^3 s,digits],
    "PaCubicPartial"->N[4 pn s,digits],
    "ContributionR6Partial"->N[768 pn^3 s,digits],
    "IsLiteralPartialSum"->True,"InfiniteTailIncluded"->False,
    "RigorousErrorCertificate"->False|>
];
PrimitiveSpectralStatus[] := <|
  "Identity"->"Pa=2 Pi^2 PaCubic=8 Pi^3 (phi[0]+2 Sum[(-1)^n phi[n],{n,1,Infinity}])",
  "DefiningInfiniteIndices"->1,
  "HiddenFiniteConvolution"->False,
  "ParameterDerivatives"->False,
  "BivariateSpecialFunctions"->False,
  "AbsoluteConvergenceProved"->True,
  "KnownPolynomialShiftInR6"->0,
  "FiniteBuiltInClosedFormEstablished"->False,
  "OtherC6BlocksChanged"->False,
  "WolframKernelExecutedHere"->False|>;
End[];
EndPackage[];
