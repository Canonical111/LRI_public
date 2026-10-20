(* ::Package:: *)
(* PARTIAL RESULT ONLY.
   Finite polylogarithmic contribution and known-polynomial replacement for C6(1).
   This is NOT a complete C6 evaluator: three elliptic blocks are unresolved.
   No Wolfram kernel was used to test this file in the producing environment.
   The formulas were checked symbolically with SymPy and numerically with mpmath.
*)

BeginPackage["C6FinitePolylog`"];

C6FinitePolylogR6::usage =
  "C6FinitePolylogR6[] gives the finite polylogarithmic block in r6 = 2187 C6(1) units. It is not the whole coefficient.";
C6PolylogPolynomialShift::usage =
  "C6PolylogPolynomialShift[aa, gg] gives the exact adjustment to the known polynomial in C6_Mathematica_native_expression.json, with aa = Pi + 4 Log[2] and gg = Catalan.";
C6FiniteKnownPolynomial::usage =
  "C6FiniteKnownPolynomial[aa, qq, gg] is the known polynomial after the finite polylogarithm replacement, with qq = Gamma[1/4]^4/Pi. It excludes the ordinary hypergeometric block and all three unresolved elliptic blocks.";
C6FinitePolylogAvailableQ::usage =
  "C6FinitePolylogAvailableQ[] tests for the System HarmonicPolyLog built-in documented in 2026.";

C6FinitePolylogR6::missing =
  "This installation does not contain the System HarmonicPolyLog built-in. No substitute definition, sum, or numerical integral has been installed.";

Begin["`Private`"];

(* Do not create a System symbol while testing for availability. *)
C6FinitePolylogAvailableQ[] :=
  Length[Names["System`HarmonicPolyLog"]] > 0;

C6FinitePolylogR6[] := Module[{hpl},
  If[! C6FinitePolylogAvailableQ[],
    Message[C6FinitePolylogR6::missing]; Return[$Failed]
  ];
  hpl = ToExpression["System`HarmonicPolyLog"];
  4352 ((32 Catalan + 9 Pi^2) Im[PolyLog[1, 2, I]]
    - 64 Re[hpl[{0, 1, 1, 0, 1}, I]])
];

C6PolylogPolynomialShift[aa_, gg_] := (
  -153 aa^2 Pi^3/2 + 4896 aa gg Pi^2 + 153 aa Pi^4
  -69088 gg Pi^3/3 -1989 Pi^5/2 +124712 Pi^2 Zeta[3]/3
);

C6FiniteKnownPolynomial[aa_, qq_, gg_] := (
  -144 qq^3/Pi
  + qq (63 aa^3 + 120 aa gg + 79 aa Pi^2 + 2013 Pi^3
      + 54204 Zeta[3])/8
  + qq^2 (29 Pi - 249 aa)
  + 21 aa^5/640 + 7 aa^3 Pi^2/64 + 1149 aa^2 Pi^3/64
  + 7863 aa^2 Zeta[3]/16
  + 192 aa gg (16 gg + 3 Pi^2)
  + 14853 aa Pi^4/640 - 544 gg Pi^3/3 + 37631 Pi^5/128
  + 722279 Pi^2 Zeta[3]/48 - 805959 Zeta[5]/8
);

End[];
EndPackage[];

(* Example:
   Get["C6_finite_polylog_patch.wl"];
   C6FinitePolylogAvailableQ[]
   N[C6FinitePolylogR6[], 40]

   Expected numerical value for this BLOCK in r6 units:
   -67450.56164482480701958371604490623353863...

   aa = Pi + 4 Log[2]; qq = Gamma[1/4]^4/Pi;
   C6FiniteKnownPolynomial[aa, qq, Catalan]

   This known polynomial and polylogarithm block are not a full C6 result.
   Keep the original finite ordinary hypergeometric block unchanged.
   The wheel, seventh-power logarithmic, and elliptic primitive blocks
   still require evaluation to obtain a complete sum-/integral-free formula.
*)
