(* Exact companion identities, NOT a complete C6 formula.
   No active Integrate or infinite Sum is used. Numerical diagnostics contain
   finite sums only. This file was not executed in a Wolfram kernel here. *)
BeginPackage["C6DougallCompanion`"];
WheelCompanionExact::usage = "WheelCompanionExact[j] returns the finite zeta value for companion moment j=1,2,3. These are not D4 or D6.";
WheelCompanionGenerating::usage = "WheelCompanionGenerating[u] returns the finite digamma side of the subtracted generating identity, valid for Abs[u]<1/2.";
WheelCompanionCheck::usage = "WheelCompanionCheck[n,d] compares a finite n-term first companion sum with its exact value and analytic tail bound.";
CompanionReductionStatus::usage = "CompanionReductionStatus[] explicitly reports that no new C6 block has been eliminated.";
Begin["`Private`"];
WheelCompanionExact[1] = 28 Zeta[3]/Pi^2;
WheelCompanionExact[2] = 248 Zeta[5]/Pi^2;
WheelCompanionExact[3] = 3048 Zeta[7]/Pi^2;
WheelCompanionGenerating[u_] := 2/Pi^2 (2 PolyGamma[0,1/2] - PolyGamma[0,1/2+u] - PolyGamma[0,1/2-u]);
WheelCompanionCheck::arg = "Use positive integer n and integer d>=20.";
WheelCompanionCheck[n_Integer:512, d_Integer:50] := Module[{terms,partial,exact,bound},
 If[n<1 || d<20,Message[WheelCompanionCheck::arg];Return[$Failed]];
 terms=Table[N[(4 k+1)(Pochhammer[1/2,k]/k!)^4 (PolyGamma[1,k+1/2]-PolyGamma[1,k+1]),d+15],{k,0,n-1}];
 partial=Total[terms];exact=N[WheelCompanionExact[1],d+15];bound=N[1/(9(n-3/4)^2),d+15];
 <|"PartialSum"->N[partial,d],"ExactValue"->N[exact,d],
   "Difference"->N[exact-partial,d],"AnalyticTailBound"->bound,
   "DifferenceWithinBound"->TrueQ[0<exact-partial<bound],
   "IntervalCertificate"->False|>
];
CompanionReductionStatus[] := <|
 "FullIntegralAndSumFreeC6Established"->False,
 "CurrentC6FormulaChanged"->False,
 "NewResult"->"The weighted FOURTH-power companion equals 28 Zeta[3]/Pi^2.",
 "NotTheActualWheel"->"D4 lacks (4n+1); D6 has the SIXTH power of a_n.",
 "RemainingBlocks"->{"Wheel","Seventh logarithmic sector","Primitive Pa"}
|>;
End[];
EndPackage[];
