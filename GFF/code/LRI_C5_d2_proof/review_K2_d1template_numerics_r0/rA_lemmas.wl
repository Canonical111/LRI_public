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

Print["=== C1: closed-form value vs C62d 64-digit value ==="];
K2c62 = 35181091385902522416490901703077395226226728094710360690845577954/10^64;
K2cf = 32 Catalan^2 - 28 Zeta[3] Log[2];
pr["K2 closed - C62d", N[K2cf - K2c62, 80]];
pr["uniform form - K2cf", N[(PolyGamma[1, 1/4] - PolyGamma[1, 3/4])^2/8 + 2 Log[2] PolyGamma[2, 1/2] - K2cf, 80]];
pr["Phi2 = (psi1(1/4)-psi1(3/4))^2/4 - 64 G^2", N[(PolyGamma[1, 1/4] - PolyGamma[1, 3/4])^2/4 - 64 Catalan^2, 80]];

Print["=== C2: N5 and N4 by Euler-Maclaurin direct sums and by Cauchy Taylor coefficients ==="];
lc2[n_] := Exp[2 (LogGamma[n + 1/2] - LogGamma[n + 1])]/Pi;           (* c_n^2 *)
sgT[n_] := Exp[3 LogGamma[n] - 2 LogGamma[n + 1/2] - LogGamma[n + 1]] Pi;   (* Gamma(n)^3/((1/2)_n^2 n!) *)
uS = emSum[lc2[#]/# &, 1, 60, 25, wp];
sS = emSum[sgT, 1, 60, 25, wp];
vS = emSum[lc2[#] (PolyGamma[#] + EulerGamma)/# &, 1, 60, 25, wp];
rS = emSum[sgT[#] (3 (PolyGamma[#] + EulerGamma) - 2 (PolyGamma[# + 1/2] - PolyGamma[1/2])) &, 1, 60, 25, wp];
pr["u (EM) - (4log2 - 8G/pi)", uS - N[4 Log[2] - 8 Catalan/Pi, wp]];
pr["sigma (EM) - (8 pi G - 14 zeta3)", sS - N[8 Pi Catalan - 14 Zeta[3], wp]];
Print["   v = ", N[vS, 30], "   rho = ", N[rS, 30]];
pr["N4 (EM): rho + pi^2 v - (pi^2 u^2/2 - pi^4/6)", rS + Pi^2 vS - (Pi^2 uS^2/2 - Pi^4/6)];
Nc = 128; r0 = 1/5;
pts = Table[r0 Exp[2 Pi I k/Nc], {k, 0, Nc - 1}];
Fv = N[F /@ pts, wp]; Gv = N[Gf /@ pts, wp];
coef[vals_, k_] := Total[vals pts^(-k)]/Nc;
pr["Cauchy [t^0]F - 1, [t^1]F - u(EM), [t^2]F - v(EM)", {coef[Fv, 0] - 1, coef[Fv, 1] - uS, coef[Fv, 2] - vS}];
pr["Cauchy [t^0]G - 1, [t^1]G, [t^2]G", {coef[Gv, 0] - 1, coef[Gv, 1], coef[Gv, 2]}];
pr["Cauchy [t^3]G - sigma(EM), [t^4]G - rho(EM)", {coef[Gv, 3] - sS, coef[Gv, 4] - rS}];
Print["   (Cauchy truncation ~ (r0/0.5)^Nc = ", N[(2 r0)^Nc, 3], ")"];

Print["=== C3: J^Gamma at d=2 (gs:convolution, gs:Kdefinition) Laurent data ==="];
B2[a_, b_] := Gamma[(2 - a)/2] Gamma[(2 - b)/2] Gamma[(a + b - 2)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(4 - a - b)/2]);
JG[t_] := B2[1, 2 - t]^2 + 2/t (B2[1, 2 - t] - B2[1 + 2 t, 2 - t]);
pr["B2(1,2-t) at t=0.37 - proof's displayed form", N[B2[1, 2 - 37/100] - Gamma[37/200] Gamma[63/200]/(Gamma[1 - 37/200] Gamma[137/200]), wp]];
pr["B2(1+2t,2-t) at t=0.37 - proof's displayed form", N[B2[1 + 74/100, 2 - 37/100] - Gamma[1/2 - 37/100] Gamma[37/200] Gamma[137/200]/(Gamma[1/2 + 37/100] Gamma[1 - 37/200] Gamma[63/200]), wp]];
Ng = 160; rg = 1/10; tp = Table[rg Exp[2 Pi I k/Ng], {k, 0, Ng - 1}];
JGv = N[JG[2 #] & /@ tp, wp];
lc[vals_, k_] := Total[vals tp^(-k)]/Ng;
claimedJG = {1, 8 Log[2], 32 Log[2]^2, 256/3 Log[2]^3 - 20 Zeta[3], 512/3 Log[2]^4 - 48 Log[2] Zeta[3]};
Do[pr["[tau^" <> ToString[k] <> "] JGamma_{2tau} - claimed", lc[JGv, k] - claimedJG[[k + 3]]], {k, -2, 2}];
pr["[tau^-3] JGamma", lc[JGv, -3]];
Ad = 4 Log[2]; Ud = -14 Zeta[3]; Vd = -4 Zeta[3];
pr["4*(note's [t^2]J^Gamma at q=1/2, R=X=0) - claimed", N[4 (Ad^4/6 + Ad (Vd + Ud)/6) - claimedJG[[5]], wp]];
pr["note's Ksubtraction Gamma-term check: difference of the two note formulas = -AU/4 ?", N[(Ad (2 Vd - Ud)/12) - (Ad (Vd + Ud)/6) + Ad Ud/4, wp]];

Print["=== C4: proof's J = pi^2 F^2 + tau^-2 Q^2 G^2 near tau=0; Laurent of J - J^Gamma ==="];
Qf[x_] := Pi Gamma[1 + x]/(Gamma[1 - x] Gamma[1/2 + x]^2);
Jth[x_] := Pi^2 F[x]^2 + x^-2 Qf[x]^2 Gf[x]^2;
Jv = N[Jth /@ tp, wp];
Do[pr["[tau^" <> ToString[k] <> "] (Jproof - JGamma)", lc[Jv - JGv, k]], {k, -3, 1}];
pr["[tau^2](Jproof - JGamma)/4 - K2 (C62d)", lc[Jv - JGv, 2]/4 - K2c62];
pr["Q^2 Taylor: [tau^k]Q^2 - q_k (k=0..4)", Table[lc[N[Qf /@ tp, wp]^2 tp^0, k], {k, 0, 4}] -
   N[{1, 8 Log[2], 32 Log[2]^2 - Pi^2, 256/3 Log[2]^3 - 8 Pi^2 Log[2] + 8 Zeta[3], 512/3 Log[2]^4 - 32 Pi^2 Log[2]^2 + 64 Log[2] Zeta[3] + Pi^4/3}, wp]];
Print["   (truncation ~ (0.1/0.5)^160 = ", N[(1/5)^160, 3], ")"];

Print["=== C5: Euler moments by direct quadrature; N1, N2 at t=tau and t=1-tau; (R1); N3; Route-B factors ==="];
Ord[a_, b_, A_, B_, cc_] := Beta[a + 1, cc + 1] Beta[a + A + cc + 2, B + 1] HypergeometricPFQ[{-b, a + 1, a + A + cc + 2}, {a + cc + 2, a + A + B + cc + 3}, 1];
Mix[a_, b_, A_, B_, cc_] := Beta[a + 1, -a - b - cc - 1] Beta[B + 1, -A - B - cc - 1] HypergeometricPFQ[{-cc, a + 1, B + 1}, {-b - cc, -A - cc}, 1];
Do[
  s = Sin[Pi ta]; c = Cos[Pi ta]; Fa = N[F[ta], wp]; Fb = N[F[1 - ta], wp];
  Print["--- tau = ", ta];
  Iq = {Enum[1/2, ta], Enum[ta, 1/2], Enum[1 - ta, ta], Enum[ta, 1 - ta], Enum[1/2, 1 - ta], Enum[1 - ta, 1/2]};
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
  , {ta, {3/10, 9/20, 3/5, 1/7}}];

Print["=== C6: tetrahedron point tau=1/2 and Hessian ==="];
Q2 = Gamma[1/4]^8/(24 Pi^4);
pr["2 pi^2 F(1/2)^2 - 3 Q2", N[2 Pi^2 F[1/2]^2 - 3 Q2, wp]];
pr["Dixon F(1/2) - Gamma(1/4)^4/(4pi^3)", N[F[1/2] - Gamma[1/4]^4/(4 Pi^3), wp]];
Nh = 160; rh = 1/4; hp = Table[1/2 + rh Exp[2 Pi I k/Nh], {k, 0, Nh - 1}];
Fh = N[F /@ hp, wp];
F1 = Total[Fh (hp - 1/2)^-1]/Nh; F2 = 2 Total[Fh (hp - 1/2)^-2]/Nh;
pr["Z2: pi^2/2 (F'^2 + F F'') - 4 G Q2", Pi^2/2 (F1^2 + N[F[1/2], wp] F2) - N[4 Catalan Q2, wp]];
Print["   (truncation ~ (0.25/0.5)^160 = ", N[(1/2)^160, 3], ")"];
Print["=== done ==="];
Quit[];
