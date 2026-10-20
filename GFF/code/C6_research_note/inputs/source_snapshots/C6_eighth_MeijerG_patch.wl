(* Finite eighth-power block only; not a complete finite evaluation of C6.
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
known=(21/640)*aa^5 + (63/8)*aa^3*qq + (7/64)*Pi^2*aa^3 + (1149/64)*Pi^3*aa^2 + (7863/16)*aa^2*Zeta[3] - 249*aa*qq^2 + 15*Catalan*aa*qq + (79/8)*Pi^2*aa*qq + (14853/640)*Pi^4*aa + 3072*Catalan^2*aa + 576*Catalan*Pi^2*aa + 29*Pi*qq^2 + (2013/8)*Pi^3*qq + (13551/2)*qq*Zeta[3] - 805959/8*Zeta[5] - 544/3*Catalan*Pi^3 + (37631/128)*Pi^5 + (722279/48)*Pi^2*Zeta[3];
ordinaryR6[]:=(4*Pi^3*(-42*aa^2 - 18*Pi*aa + 96*qq - 1227*Pi^2)) (1) HypergeometricPFQ[{1/2, 1/2, 1/2, 1/2}, {1, 1, 1}, 1]+
(2*Pi^4*(-105/4*aa^2 - 9*Pi*aa + 60*qq - 2469/4*Pi^2)) (1) HypergeometricPFQ[{5/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/4, 1, 1, 1, 1, 1}, 1]+
(96*Pi^(3/2)*cc7*(-55*aa*(13 + 22*2^(1/2)) + Pi*(1127*2^(1/2) + 2303))) ((1/8)*Gamma[3/8]^7/Gamma[7/8]^7) HypergeometricPFQ[{1, 9/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8}, {1/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8}, -1]+
(96*Pi^(3/2)*(-1295/2*aa + (3283/2)*Pi)) ((1/4)*Pi^(7/2)) HypergeometricPFQ[{5/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/4, 1, 1, 1, 1, 1, 1}, -1]+
(96*Pi^(3/2)*cc7*((-13 + 22*2^(1/2))*(392 - 55*aa) + Pi*(-2303 + 1127*2^(1/2)))) ((3/8)*Gamma[5/8]^7/Gamma[9/8]^7) HypergeometricPFQ[{1, 11/8, 5/8, 5/8, 5/8, 5/8, 5/8, 5/8, 5/8}, {3/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8}, -1]+
(96*Pi^(3/2)*ss7*((-13 + 22*2^(1/2))*(55*aa - 392/3) + Pi*(2303 - 1127*2^(1/2)))) ((5/8)*Gamma[7/8]^7/Gamma[11/8]^7) HypergeometricPFQ[{1, 13/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8, 7/8}, {5/8, 11/8, 11/8, 11/8, 11/8, 11/8, 11/8, 11/8}, -1]+
(96*Pi^(3/2)*ss7*((13 + 22*2^(1/2))*(2352/5 - 55*aa) + Pi*(1127*2^(1/2) + 2303))) ((7/8)*Gamma[9/8]^7/Gamma[13/8]^7) HypergeometricPFQ[{1, 15/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8, 9/8}, {7/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8, 13/8}, -1];
pbR6[]:=192 Pi (
 13 MeijerG[{{1/2,1/2,1/2,1/2,1/2},{1/2}},{{0,0,0},{0,0,0}},1]
 +11 MeijerG[{{1/2,1/2,1/2,1/2},{1/2,1/2}},{{0,0,0,0},{0,0}},1]);
C6FinitePartR6::hpl="This expression requires the System`HarmonicPolyLog built-in; no custom fallback has been installed.";
C6FinitePartR6[]:=If[!MemberQ[Attributes[System`HarmonicPolyLog],Protected],Message[C6FinitePartR6::hpl];$Failed,
 known+ordinaryR6[]+pbR6[]+C6EighthBlockSingle[]+
 4352 ((32 Catalan+9 Pi^2) Im[PolyLog[1,2,I]]-64 Re[System`HarmonicPolyLog[{0,1,1,0,1},I]])];
C6ReductionStatus[]:=<|"FullIntegralFreeSumFreeC6Established"->False,"OmittedFromFinitePart"->{"wheel","seventh-power logarithmic sector","primitive Pa"},"KnownPolynomialChangedThisStep"->False,"ThisFileWasExecutedInWolframKernelByAuthor"->False|>;
End[];
EndPackage[];
