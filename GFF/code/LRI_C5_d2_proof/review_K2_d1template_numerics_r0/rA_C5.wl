(* Review r0, numerics lens: one-dimensional lemmas N1-N5, (R1), A5, Route-B factors, Laurent data.
   Independent re-implementation; >= 60 working digits. *)
$MaxExtraPrecision = 500;
Get[FileNameJoin[{DirectoryName[$InputFileName], "emsum.wl"}]];
wp = 66;
pr[s_, x_] := Print[s, "  ", N[x, 6]];
F[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
Gf[t_] := HypergeometricPFQ[{t, t, t}, {1/2 + t, 1/2 + t}, 1];
Ecl[a_, b_] := Pi/2 Beta[a, b] HypergeometricPFQ[{1/2, 1/2, a}, {1, a + b}, 1];
KA[x_] := Pi/(2 ArithmeticGeometricMean[1, Sqrt[1 - x]]);
KB[y_] := Pi/(2 ArithmeticGeometricMean[1, Sqrt[y]]);   (* K(1-y), no cancellation for small y *)
Enum[a_, b_] := Module[{g1, g2},
   g1[x_?NumericQ] := x^(a - 1) (1 - x)^(b - 1) KA[x];
   g2[y_?NumericQ] := (1 - y)^(a - 1) y^(b - 1) KB[y];
   NIntegrate[g1[x], {x, 0, 1/2}, WorkingPrecision -> wp, PrecisionGoal -> 56, MaxRecursion -> 40, Method -> "DoubleExponential"] +
   NIntegrate[g2[y], {y, 0, 1/2}, WorkingPrecision -> wp, PrecisionGoal -> 56, MaxRecursion -> 40, Method -> "DoubleExponential"]];

Print["=== C5: Euler moments by direct quadrature; N1, N2 at t=tau and t=1-tau; (R1); N3; Route-B factors ==="];
Ord[a_, b_, A_, B_, cc_] := Beta[a + 1, cc + 1] Beta[a + A + cc + 2, B + 1] HypergeometricPFQ[{-b, a + 1, a + A + cc + 2}, {a + cc + 2, a + A + B + cc + 3}, 1];
Mix[a_, b_, A_, B_, cc_] := Beta[a + 1, -a - b - cc - 1] Beta[B + 1, -A - B - cc - 1] HypergeometricPFQ[{-cc, a + 1, B + 1}, {-b - cc, -A - cc}, 1];
ta = ToExpression[$ScriptCommandLine[[2]]];
  s = Sin[Pi ta]; c = Cos[Pi ta]; Fa = N[F[ta], wp]; Fb = N[F[1 - ta], wp];
  Print["--- tau = ", ta];
  {tq, Iq} = AbsoluteTiming[{Enum[1/2, ta], Enum[ta, 1/2], Enum[1 - ta, ta], Enum[ta, 1 - ta], Enum[1/2, 1 - ta], Enum[1 - ta, 1/2]}]; Print["   quadrature time ", tq];
  Ic = N[{Ecl[1/2, ta], Ecl[ta, 1/2], Ecl[1 - ta, ta], Ecl[ta, 1 - ta], Ecl[1/2, 1 - ta], Ecl[1 - ta, 1/2]}, wp];
  pr["N1 |quad - Euler| for I1..I6", Abs[Iq - Ic]];
  pr["N2 at t=tau: I1-(cI3+sI4), I5-(sI3-cI4), I2-sI3, I6-sI4",
   {Iq[[1]] - (c Iq[[3]] + s Iq[[4]]), Iq[[5]] - (s Iq[[3]] - c Iq[[4]]), Iq[[2]] - s Iq[[3]], Iq[[6]] - s Iq[[4]]}];
  pr["N2 at t=1-tau (relabelled)",
   {Iq[[5]] - (-c Iq[[4]] + s Iq[[3]]), Iq[[1]] - (s Iq[[4]] + c Iq[[3]]), Iq[[6]] - s Iq[[4]], Iq[[2]] - s Iq[[3]]}];
  pr["A4(iv): I3 - pi^2/(2s) F(1-tau), I4 - pi^2/(2s) F(tau)", {Iq[[3]] - Pi^2/(2 s) Fb, Iq[[4]] - Pi^2/(2 s) Fa}];
  pr["(R1) residual", N[Beta[1/2, ta] HypergeometricPFQ[{1/2, 1/2, 1/2}, {1, 1/2 + ta}, 1], wp] - Pi (Fa + Cot[Pi ta] Fb)];
  pr["B3: 2I1 - pi^2[F+cotF'], 2I5 - pi^2[F'-cotF]", {2 Iq[[1]] - Pi^2 (Fa + Cot[Pi ta] Fb), 2 Iq[[5]] - Pi^2 (Fb - Cot[Pi ta] Fa)}];
  pr["A5: E(tau,1/2) - pi^2/2 F(1-tau)", Iq[[2]] - Pi^2/2 Fb];
  pr["N3 Thomae at t=tau, t=1-tau",
   {Fb - N[Gamma[ta]/(Gamma[1 - ta] Gamma[1/2 + ta]^2) Gf[ta], wp], Fa - N[Gamma[1 - ta]/(Gamma[ta] Gamma[3/2 - ta]^2) Gf[1 - ta], wp]}];
  {aa, bb, AA, BB, cc} = {-1/2, -1/2, -1/2, ta - 1, -1/2};
  O1 = N[Ord[aa, bb, AA, BB, cc], wp]; M1 = N[Mix[aa, bb, AA, BB, cc], wp];
  O2 = N[Ord[AA, BB, aa, bb, cc], wp]; M2 = N[Mix[AA, BB, aa, bb, cc], wp];
  pr["note factors (HypergeometricPFQ) vs quadrature: O1-2I1, M1-2I4, O2-pi^2F', O2-2I2, M2-2I5",
   {O1 - 2 Iq[[1]], M1 - 2 Iq[[4]], O2 - Pi^2 Fb, O2 - 2 Iq[[2]], M2 - 2 Iq[[5]]}];
  Jk = (Sin[Pi aa] Sin[Pi BB] O1 M1 + Sin[Pi AA] Sin[Pi bb] O2 M2)/Pi^2;
  pr["done:kiteFactorization at the point - pi^2(F^2+F'^2)", Jk - Pi^2 (Fa^2 + Fb^2)];
  pr["quadrature moments: (4/pi^2)[s I1 I4 + I2 I5], (4/pi^2)s^2(I3^2+I4^2), (4/pi^2)(I2^2+I6^2) minus pi^2(F^2+F'^2)",
   {4/Pi^2 (s Iq[[1]] Iq[[4]] + Iq[[2]] Iq[[5]]), 4/Pi^2 s^2 (Iq[[3]]^2 + Iq[[4]]^2), 4/Pi^2 (Iq[[2]]^2 + Iq[[6]]^2)} - Pi^2 (Fa^2 + Fb^2)];
  Print["   J value = ", N[Pi^2 (Fa^2 + Fb^2), 40]];
  

Quit[];
