(* C6(1): exact finite reduction of P_b (NOT the unresolved primitive P_a).
   Replaces the complete old 24 P_b block, including its -144 Q^3/Pi term.
   All functions below use ordinary Wolfram Language built-ins.
   This file has NOT been executed in a Wolfram kernel in this session.
   It does not claim a complete integral-free expression for C6(1). *)

BeginPackage["C6SixthPowerPatch`"];
PbMeijerPair::usage = "PbMeijerPair[] returns P_b as two MeijerG values with rational parameters.";
PbMeijerSingle::usage = "PbMeijerSingle[] returns P_b as one MeijerG value; it uses alpha=ArcTan[11/13]/Pi.";
PbContributionR6::usage = "PbContributionR6[] returns the complete 24 P_b contribution to r6=2187 C6(1), in the rational-parameter two-value form.";
PbPreviousForm::usage = "PbPreviousForm[] returns the inherited three-hypergeometric-value formula for P_b.";
PbKnownPolynomialShiftR6::usage = "PbKnownPolynomialShiftR6[] is the +144 Q^3/Pi shift that cancels the old separately recorded constant when inserting the complete 24 P_b block.";
PbNumericalCheck::usage = "PbNumericalCheck[d] compares the old and both new finite forms at d-digit working precision. Numerical agreement is not a rigorous certificate.";

Begin["`Private`"];
x35[] := MeijerG[
  {{1/2, 1/2, 1/2, 1/2, 1/2}, {1/2}},
  {{0, 0, 0}, {0, 0, 0}}, 1];
x44[] := MeijerG[
  {{1/2, 1/2, 1/2, 1/2}, {1/2, 1/2}},
  {{0, 0, 0, 0}, {0, 0}}, 1];

PbMeijerPair[] := 8 Pi (13 x35[] + 11 x44[]);
PbMeijerSingle[] := With[{alpha = ArcTan[11/13]/Pi},
  8 Pi Sqrt[290] MeijerG[
    {{1/2, 1/2, 1/2, 1/2, 1/2}, {1/2, alpha}},
    {{0, 0, 0, 0}, {0, 0, alpha}}, 1]];
PbContributionR6[] := 192 Pi (13 x35[] + 11 x44[]);
PbKnownPolynomialShiftR6[] := 144 (Gamma[1/4]^4/Pi)^3/Pi;

PbPreviousForm[] := With[{q = Gamma[1/4]^4/Pi},
  (6 q^3/Pi) (2 HypergeometricPFQ[
      {1,1/4,1/4,1/4,1/4,1/4,1/4},
      {3/4,3/4,3/4,3/4,3/4,3/4},1] - 1)
  -104 Pi^5 HypergeometricPFQ[
      {1/2,1/2,1/2,1/2,1/2,1/2},{1,1,1,1,1},1]
  +(2^18 Pi^5/q^3) HypergeometricPFQ[
      {1,3/4,3/4,3/4,3/4,3/4,3/4},
      {5/4,5/4,5/4,5/4,5/4,5/4},1]];

PbNumericalCheck::digits = "Use an integer digit request between 15 and 100.";
PbNumericalCheck[digits_Integer:30] := Module[{wp, old, pair, single},
  If[digits < 15 || digits > 100,
    Message[PbNumericalCheck::digits]; Return[$Failed]];
  wp = digits + 20;
  Block[{$MaxExtraPrecision = 5 wp},
    old = N[PbPreviousForm[], wp];
    pair = N[PbMeijerPair[], wp];
    single = N[PbMeijerSingle[], wp];
    <|"WorkingPrecision" -> wp, "PbOld" -> old,
      "PbTwoMeijerG" -> pair, "PbOneMeijerG" -> single,
      "PairMinusOld" -> pair-old, "SingleMinusPair" -> single-pair,
      "RigorousErrorCertificate" -> False|>]];
End[];
EndPackage[];
