(* Review r0, numerics lens: Route A (A0-A6) at >= 50 digits. *)
$MaxExtraPrecision = 500;
Get[FileNameJoin[{DirectoryName[$InputFileName], "emsum.wl"}]];
wp = 66;
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

ta = ToExpression[$ScriptCommandLine[[2]]]; l = ToExpression[$ScriptCommandLine[[3]]];
omI[nu_?NumericQ] := Re[OmL[l, ta, I SetPrecision[nu, wp + 20 + Ceiling[Max[0, Log10[nu]]]]]];
omU[u_?NumericQ] := omI[1000/u] 1000/u^2;   (* nu = 1000/u on the tail; omitted nu > 10^403 is O(10^-500) *)
bar = (NIntegrate[omI[nu], {nu, 0, 1, 10, 100, 1000}, WorkingPrecision -> wp, PrecisionGoal -> 55, MaxRecursion -> 40, Method -> "DoubleExponential"] +
   NIntegrate[omU[u], {u, 10^-400, 10^-20, 10^-3, 1}, WorkingPrecision -> wp, PrecisionGoal -> 55, MaxRecursion -> 40, Method -> "DoubleExponential"])/Pi;
rs = -emSum[(Res1[l, #, ta] + Res2[l, #, ta]) &, 0, 60, 25, wp];
Print["tau = ", ta, " l = ", l, ": Barnes integral = ", N[bar, 30], "   (integral) - (-sum Res) = ", InputForm[N[bar - rs, 6]], "  rel ", N[(bar - rs)/bar, 6]];
Quit[];
