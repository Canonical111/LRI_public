(* Review r0, numerics lens: one-dimensional lemmas N1-N5, (R1), A5, Route-B factors, Laurent data.
   Independent re-implementation; >= 60 working digits. *)
$MaxExtraPrecision = 500;
Get[FileNameJoin[{DirectoryName[$InputFileName], "emsum.wl"}]];
wp = 80;
pr[s_, x_] := Print[s, "  ", N[x, 6]];
F[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
Gf[t_] := HypergeometricPFQ[{t, t, t}, {1/2 + t, 1/2 + t}, 1];
Ecl[a_, b_] := Pi/2 Beta[a, b] HypergeometricPFQ[{1/2, 1/2, a}, {1, a + b}, 1];
Enum[a_, b_] := NIntegrate[x^(a - 1) (1 - x)^(b - 1) EllipticK[x], {x, 0, 1/2, 1},
   WorkingPrecision -> wp, PrecisionGoal -> 62, MaxRecursion -> 40, Method -> "DoubleExponential"];

Print["=== C6: tetrahedron point tau=1/2 and Hessian ==="];
Q2 = Gamma[1/4]^8/(24 Pi^4);
pr["2 pi^2 F(1/2)^2 - 3 Q2", N[2 Pi^2 F[1/2]^2 - 3 Q2, wp]];
pr["Dixon F(1/2) - Gamma(1/4)^4/(4pi^3)", N[F[1/2] - Gamma[1/4]^4/(4 Pi^3), wp]];
Nh = 288; rh = 1/4; hp = Table[1/2 + rh Exp[2 Pi I k/Nh], {k, 0, Nh - 1}];
Fh = N[F /@ hp, wp];
F1 = Total[Fh (hp - 1/2)^-1]/Nh; F2 = 2 Total[Fh (hp - 1/2)^-2]/Nh;
pr["Z2: pi^2/2 (F'^2 + F F'') - 4 G Q2", Pi^2/2 (F1^2 + N[F[1/2], wp] F2) - N[4 Catalan Q2, wp]];
Print["   (truncation ~ (0.25/0.5)^288 = ", N[(1/2)^288, 3], ")"];
Print["=== done ==="];
Quit[];
