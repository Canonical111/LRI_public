(* Exact seed relations for the inherited C6 primitive coefficient recurrence.
   This file does NOT evaluate the residual primitive or the full C6.
   The code has not been executed in a Wolfram kernel in this calculation. *)
BeginPackage["C6PrimitiveSeeds`"];
PrimitiveG::usage = "PrimitiveG[j,n] is the inherited ordinary MeijerG coefficient; j=1,2,3 and n>=0.";
PrimitiveReducedSeeds::usage = "PrimitiveReducedSeeds[] returns all six seeds expressed in three fixed MeijerG values.";
PrimitiveSeedChecks::usage = "PrimitiveSeedChecks[d] numerically tests the two exact seed identities using d working digits. Not an error certificate.";
PrimitiveDifferenceRational::usage = "PrimitiveDifferenceRational[n] returns exactly Pi (G[3,n]-G[1,n]) by its rational recurrence.";
PrimitiveSeedStatus::usage = "PrimitiveSeedStatus[] reports the scope of the reduction.";
Begin["`Private`"];
PrimitiveG[1,n_Integer] /; n>=0 := MeijerG[{{1/2,1/2,1/2},{1/2}},{{n},{0,0,-n}},1];
PrimitiveG[2,n_Integer] /; n>=0 := MeijerG[{{1/2,1/2},{1/2,1/2}},{{0,n},{0,-n}},1];
PrimitiveG[3,n_Integer] /; n>=0 := MeijerG[{{1/2},{1/2,1/2,1/2}},{{0,0,n},{-n}},1];
PrimitiveReducedSeeds[] := Module[{x=PrimitiveG[1,0],y=PrimitiveG[2,0],z=PrimitiveG[2,1],v},
  v=(x z+8/Pi)/y;
  <|"G10"->x,"G11"->v-4/Pi,"G20"->y,"G21"->z,"G30"->x,"G31"->v+4/Pi|>
];
PrimitiveSeedChecks::digits="The precision must be an integer of at least 20 digits.";
PrimitiveSeedChecks[d_Integer:50] := Module[{x,y,z,a,b},
  If[d<20,Message[PrimitiveSeedChecks::digits];Return[$Failed]];
  {x,y,z,a,b}=N[{PrimitiveG[1,0],PrimitiveG[2,0],PrimitiveG[2,1],PrimitiveG[1,1],PrimitiveG[3,1]},d];
  <|"WorkingPrecision"->d,"DifferenceResidual"->N[b-a-8/Pi,d],
    "DeterminantResidual"->N[y(a+b)-2x z-16/Pi,d],
    "ReducedSeedResidual"->N[(x z+8/Pi)/y-4/Pi-a,d],
    "IsIntervalCertificate"->False|>
];
PrimitiveDifferenceRational[n_Integer] /; n>=0 := Module[{r0=0,r1=8,r2,k},
  If[n==0,Return[r0]]; If[n==1,Return[r1]];
  Do[r2=Together[(4k(4k^2+1)r1-(2k-1)^3 r0+64k(-1)^k)/(2k+1)^3];
     r0=r1;r1=r2,{k,1,n-1}]; r1
];
PrimitiveSeedStatus[] := <|"StartingSeeds"->6,"FixedSeedValuesNeeded"->3,
  "NewClosedFormResidualEvaluations"->0,"FullPrimitiveEvaluated"->False,
  "AcceptedC6FormulaChanged"->False,"WolframKernelExecutedHere"->False,
  "RemainingResiduals"->{"Wheel","SeventhPowerSector","Primitive"}|>;
End[];
EndPackage[];
