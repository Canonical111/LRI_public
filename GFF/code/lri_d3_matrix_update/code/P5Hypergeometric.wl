(* Ordinary generalized-hypergeometric presentation of the LRI period P5.
   All rational parameters are exact. The argument remains -1.
   This source has not been executed in a Wolfram kernel in this revision.
   Python/mpmath and direct Barnes/gamma integrals provide the executed checks.
*)
ClearAll[H5, Phi5, P5HypergeometricExpression, P5HypergeometricN];
H5[t_] := HypergeometricPFQ[
  Join[{1, 5/4 + t}, ConstantArray[1/2 + t, 7]],
  Join[{1/4 + t}, ConstantArray[1 + t, 7]], -1];
Phi5[t_] := (1 + 4 t) (Gamma[1/2 + t]/(Sqrt[Pi] Gamma[1 + t]))^7 H5[t];

(* Do not set t=0 or cancel the fixed upper 1 against a lower 1+t
   before taking the derivatives. *)
P5HypergeometricExpression[] := Module[{t},
  Pi^3 ((11 D[Phi5[t], {t, 2}] - 26 Pi D[Phi5[t], t]
    + 3 Pi^2 Phi5[t]) /. t -> 0)
];

(* Cauchy coefficient evaluation avoids symbolic parameter derivatives.
   Vary nodes and radius as well as digits to test convergence.
   This is not a rigorous interval enclosure. *)
P5HypergeometricN::args = "Use digits>=20, an even node count>=16, and 0<radius<1/10.";
P5HypergeometricN[digits_Integer:50, nodes_:Automatic, radius_:1/100] :=
 Module[{wp = digits + 25, n, r, angles, values, c},
  n = If[nodes === Automatic, Max[48, 2 Ceiling[(digits + 15)/2]], nodes];
  If[digits < 20 || !IntegerQ[n] || n < 16 || OddQ[n] ||
      !TrueQ[0 < radius < 1/10],
    Message[P5HypergeometricN::args]; Return[$Failed]];
  r = N[radius, wp];
  angles = Table[N[2 Pi j/n, wp], {j, 0, n - 1}];
  values = (N[Phi5[r Exp[I #]], wp] &) /@ angles;
  c = Table[Re[Total[values Exp[-I k angles]]]/(n r^k), {k, 0, 2}];
  N[Pi^3 (22 c[[3]] - 26 Pi c[[2]] + 3 Pi^2 c[[1]]), digits]
];
