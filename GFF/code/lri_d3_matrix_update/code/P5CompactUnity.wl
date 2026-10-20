(* Fixed-parameter representations of P5. No parameter derivatives or limits.
   The two-value formulas use Re of one complex hypergeometric evaluation.
   This file is supplied but was not executed in a Wolfram kernel in this revision.
   Python/mpmath verification: code/verify_compact_unity.py. *)
ClearAll[P5Rho, P5GammaFactor, P5HMinus, P5EUnity, P5D7, P5CubicRoots,
 P5PolynomialRoots, P5UUnity, P5HFromE, P5HFromU, P5Assemble,
 P5Compact, P5UnityFour, P5UnityTwo, P5Evaluate];
P5Rho = ArcCosh[22/13]/(2 Pi);
P5GammaFactor[r_] := (11 Gamma[1/4 + I r] Gamma[1/4 - I r]/(13 Pi))^7;
P5HMinus[z_] := HypergeometricPFQ[
 Join[{1, 1 + z}, ConstantArray[z + 1/4, 7]],
 Join[{z}, ConstantArray[z + 3/4, 7]], -1];
P5EUnity[z_] := HypergeometricPFQ[
 Join[{1, 1 + z/2}, ConstantArray[z/2 + 1/8, 7],
  ConstantArray[z/2 + 5/8, 7]],
 Join[{z/2}, ConstantArray[z/2 + 3/8, 7],
  ConstantArray[z/2 + 7/8, 7]], 1];
P5D7[z_] := z (z + 3/4)^7 - (z + 1) (z + 1/4)^7;
P5CubicRoots = Table[Root[20480 #^3 - 1792 #^2 - 784 # - 13 &, k], {k, 3}];
P5PolynomialRoots = Join[{-1/2},
 Flatten[({-1/2 + Sqrt[#], -1/2 - Sqrt[#]} &) /@ P5CubicRoots]];
P5UUnity[z_] := Module[{eta = (z - P5PolynomialRoots)/2},
 HypergeometricPFQ[
  Join[{1}, ConstantArray[z/2 + 1/8, 7], ConstantArray[z/2 + 5/8, 7], 1 + eta],
  Join[ConstantArray[z/2 + 7/8, 7], ConstantArray[z/2 + 11/8, 7], eta], 1]];
P5HFromE[z_] := P5EUnity[z] - (z + 1)/z ((z + 1/4)/(z + 3/4))^7 P5EUnity[z + 1];
P5HFromU[z_] := P5D7[z]/(z (z + 3/4)^7) P5UUnity[z];
P5Assemble[h0_, hr_, r_] := 8 Pi^(3/2)/11 (
 29 Pi^(7/2)/4 h0 + 2197 r/(3 Sqrt[35]) P5GammaFactor[r] (2 Re[hr] - 1));
P5Compact[] := P5Assemble[P5HMinus[1/4], P5HMinus[I P5Rho], P5Rho];
P5UnityFour[] := P5Assemble[P5HFromE[1/4], P5HFromE[I P5Rho], P5Rho];
P5UnityTwo[] := P5Assemble[P5HFromU[1/4], P5HFromU[I P5Rho], P5Rho];
(* Guard digits and numeric inputs for direct numerical evaluation. *)
P5Evaluate[method_String : "minus", digits_Integer : 50] /; digits >= 20 :=
 Module[{r = N[P5Rho, digits + 20], q = N[1/4, digits + 20], fun},
  fun = Switch[method, "minus", P5HMinus, "unity-four", P5HFromE,
    "unity-two", P5HFromU, _, Return[$Failed]];
  N[P5Assemble[fun[q], fun[I r], r], digits]];
(* Examples:
 P5Evaluate["minus", 60]
 P5Evaluate["unity-four", 60]
 P5Evaluate["unity-two", 60]
 Expected beginning: 28599.29317656210353664647702142205749...
 This is an example output prefix, not an input to any formula.
*)
