(* Intermediate parameter directions, NOT a completed fixed-value formula.
   The inactive Derivative objects below have not been eliminated.
   No Wolfram-kernel execution is claimed for this file. *)
BeginPackage["C6ParameterDirections`"];
WheelFamily4::usage = "WheelFamily4[u] is the ordinary 4F3 parameter family.";
WheelFamily6::usage = "WheelFamily6[u] is the ordinary 7F6 parameter family.";
SeventhFamily::usage = "SeventhFamily[r,u] has a FIXED gamma prefactor; r is 1,2,3,5,7.";
WheelParameterTargets::usage = "WheelParameterTargets[] returns exact INACTIVE derivative identities for D4,D6 and the r6 wheel contribution. Not a fixed-value evaluation.";
SeventhParameterTarget::usage = "SeventhParameterTarget[] returns the five-term INACTIVE derivative expression for the logarithmic seventh block only.";
ParameterReductionStatus::usage = "ParameterReductionStatus[] reports the remaining limitations.";
Begin["`Private`"];
WheelFamily4[u_] := HypergeometricPFQ[
 {1/2+u, 1/2-u, 1/2, 1/2}, {1+u, 1-u, 1}, 1];
WheelFamily6[u_] := HypergeometricPFQ[
 {5/4, 1/2+u, 1/2-u, 1/2, 1/2, 1/2, 1/2},
 {1/4, 1+u, 1-u, 1, 1, 1}, 1];
SeventhFamily[r_,u_] := With[{t=r/8,a=(r+2)/8,b=(r+6)/8},
 t (Gamma[a]/Gamma[b])^7 HypergeometricPFQ[
 Join[{1,1+t},ConstantArray[a+u,7]],
 Join[{t},ConstantArray[b-u,7]], -1]];
WheelParameterTargets[] := Module[{d4,d6,f4,f6},
 d4=Inactive[Derivative][2][WheelFamily4][0];
 d6=Inactive[Derivative][2][WheelFamily6][0];
 f4=WheelFamily4[0]; f6=WheelFamily6[0];
 <|"D4"->d4/2+Pi^2 f4/3,
   "D6"->d6/2+Pi^2 f6/3,
   "WheelR6"->-1572 Pi^3 d4-(1965/2) Pi^4 d6-1048 Pi^5 f4-655 Pi^6 f6,
   "ParameterDerivativesRemain"->True|>];
SeventhParameterTarget[] := Module[{rr,pp,dd},
 rr={1,2,3,5,7};
 pp={Cos[Pi/8]^7 (13+22 Sqrt[2]),-35,
     Cos[Pi/8]^7 (22 Sqrt[2]-13),-Sin[Pi/8]^7 (22 Sqrt[2]-13),
     Sin[Pi/8]^7 (13+22 Sqrt[2])};
 dd=Table[Inactive[Derivative][0,1][SeventhFamily][r,0],{r,rr}];
 <|"LogarithmicSeventhR6"->672 Pi^(3/2) (pp.dd),
   "OrdinarySeventhCorrectionsIncluded"->False,
   "ParameterDerivativesRemain"->True|>];
ParameterReductionStatus[] := <|
 "FullFixedValueFormEstablished"->False,
 "KnownPolynomialChanged"->False,
 "UnresolvedFixedValueBlocks"->{"Wheel","Seventh logarithmic sector","Primitive Pa"},
 "PrimitiveEvaluatedInThisPass"->False,
 "NewRigorousIntervalCertificate"->False,
 "WolframKernelExecutedForPackage"->False,
 "Purpose"->"Expose exact parameter directions and document a restricted termwise matching obstruction, not rename a completed C6 result."|>;
End[];
EndPackage[];
