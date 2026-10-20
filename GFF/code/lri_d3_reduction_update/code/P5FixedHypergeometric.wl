(* Four fixed 9F8(-1) values and one fixed 8F7(-1) value for P5.
   No parameter derivatives, limits, Cauchy coefficients or MeijerG.
   The r=2 cancellation may be left to HypergeometricPFQ.
   This file is supplied as a symbolic/numeric translation; it has not
   been run in a Wolfram kernel in this revision. Python is verified.
*)
ClearAll[P5Y, P5FixedHypergeometric];
P5Y[r_Integer, wp_Integer : 80] /;
   MemberQ[{1, 2, 3, 5, 7}, r] && wp >= 30 :=
 N[(r/8) (Gamma[(r + 2)/8]/Gamma[(r + 6)/8])^7
   HypergeometricPFQ[
    Join[{1, 1 + r/8}, ConstantArray[(r + 2)/8, 7]],
    Join[{r/8}, ConstantArray[(r + 6)/8, 7]], -1], wp];
P5FixedHypergeometric[digits_Integer : 50] /; digits >= 20 :=
 Module[{wp = digits + 20, c8, s8, x0, xp, xm},
  c8 = N[Cos[Pi/8], wp]; s8 = N[Sin[Pi/8], wp];
  x0 = P5Y[2, wp];
  xp = c8^7 P5Y[3, wp] - s8^7 P5Y[5, wp];
  xm = c8^7 P5Y[1, wp] + s8^7 P5Y[7, wp];
  N[16 Pi^(3/2) (-35 x0 + (22 Sqrt[2] - 13) xp
                      + (22 Sqrt[2] + 13) xm), digits]
 ];
(* Example: P5FixedHypergeometric[80] *)
