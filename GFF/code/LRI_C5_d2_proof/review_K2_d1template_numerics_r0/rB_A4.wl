(* Review r0, numerics lens: Route A (A0-A6) at >= 50 digits. *)
$MaxExtraPrecision = 500;
Get[FileNameJoin[{DirectoryName[$InputFileName], "emsum.wl"}]];
wp = 80;
pr[s_, x_] := Print[s, "  ", N[x, 6]];
F[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
Ecl[a_, b_] := Pi/2 Beta[a, b] HypergeometricPFQ[{1/2, 1/2, a}, {1, a + b}, 1];
Om[l_, ta_, s_] := Module[{a = l/2 + 1/4, b = l/2 + 3/4},
   Gamma[a + s]^3 Gamma[a - s]^2 Gamma[b - ta - s]/(Gamma[b + s]^2 Gamma[b - s]^3 Gamma[a + ta + s])];
(* N7 integrand as written in the note: t_l^2 R_tau, t_l = Gamma(2q) g, q=1/2 *)
OmL[l_, ta_, s_] := Module[{a = l/2 + 1/4, b = l/2 + 3/4},
   Exp[3 LogGamma[a + s] + 2 LogGamma[a - s] + LogGamma[b - ta - s] - 2 LogGamma[b + s] - 3 LogGamma[b - s] - LogGamma[a + ta + s]]];
OmNote[l_, ta_, s_] := Module[{a = l/2 + 1/4, b = l/2 + 3/4, g},
   g = Gamma[a + s] Gamma[a - s]/(Gamma[b + s] Gamma[b - s]);
   g^2 Gamma[a + s] Gamma[b - ta - s]/(Gamma[a + ta + s] Gamma[b - s])];
h[z_, ta_] := Exp[3 LogGamma[z + 1/2] - 2 LogGamma[z + 1] - LogGamma[z + 1/2 + ta]];
hp[z_, ta_] := h[z, ta] (3 PolyGamma[z + 1/2] - 2 PolyGamma[z + 1] - PolyGamma[z + 1/2 + ta]);
k[z_, ta_] := Exp[3 LogGamma[z + 1 - ta] - 2 LogGamma[z + 3/2 - ta] - LogGamma[z + 1]];
Res1[l_, n_, ta_] := With[{s = Sin[Pi ta], c = Cos[Pi ta], m = l + n},
   (Pi s/c^2 h[m, ta] h[n, ta] + (hp[m, ta] h[n, ta] + h[m, ta] hp[n, ta])/c)/Pi^2];
Res2[l_, n_, ta_] := With[{s = Sin[Pi ta], c = Cos[Pi ta], m = l + n}, -(s^3/(Pi c^2)) k[m, ta] k[n, ta]];

ta = ToExpression[$ScriptCommandLine[[2]]]; s = Sin[Pi ta]; c = Cos[Pi ta];
Print["tau = ", ta];
  H0 = emSum[h[#, ta] &, 0, 60, 25, wp];
  H1 = emSum[hp[#, ta] &, 0, 60, 25, wp];
  K0 = emSum[k[#, ta] &, 0, 60, 25, wp];
  Fa = N[F[ta], wp]; Fb = N[F[1 - ta], wp];
  pr["A4(i)  H0 - 2E(1/2,tau)/Gamma", H0 - N[2 Ecl[1/2, ta]/Gamma[ta], wp]];
  pr["A4(ii) H1 + 2pi E(tau,1/2)/Gamma", H1 + N[2 Pi Ecl[ta, 1/2]/Gamma[ta], wp]];
  pr["A4(iii) K0 - Gamma Gamma(1-tau)^2 F(tau)", K0 - N[Gamma[ta] Gamma[1 - ta]^2, wp] Fa];
  pr["A5: H0 - pi^2/Gamma (F + cot F'), H1 + pi^3 F'/Gamma",
   {H0 - N[Pi^2/Gamma[ta], wp] (Fa + Cot[Pi ta] Fb), H1 + N[Pi^3/Gamma[ta], wp] Fb}];
  JA3 = N[Gamma[ta]/Gamma[1 - ta], wp] (-(s/(Pi c^2)) H0^2 - 2/(Pi^2 c) H0 H1 + s^3/(Pi c^2) K0^2);
  pr["A3 (direct sums) - pi^2(F^2+F'^2)", JA3 - Pi^2 (Fa^2 + Fb^2)];
Quit[];
