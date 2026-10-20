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

Do[
  Print["================ tau = ", ta];
  s = Sin[Pi ta]; c = Cos[Pi ta];
  (* A0: integrand identity with the note's t_l^2 R_tau and the G T split *)
  sp = N[1/3 + 7/5 I, wp];
  pr["A0: Omega - t^2 R (note) at s=1/3+1.4i, l=3", Om[3, ta, sp] - OmNote[3, ta, sp]];
  With[{a = 3/2 + 1/4, b = 3/2 + 3/4},
   Gl = (Gamma[a + sp] Gamma[1 - b + sp]/(Gamma[b + sp] Gamma[1 - a + sp]))^2 Gamma[a + sp] Gamma[1 - b + sp]/(Gamma[a + ta + sp] Gamma[1 - b + ta + sp]);
   Tt = Cot[Pi (a - sp)]^2 Cos[Pi (a - sp)]/Sin[Pi (b - ta - sp)];
   pr["A2: Omega - G_l T  (l=3)", Om[3, ta, sp] - Gl Tt]];
  pr["decay: nu^(2+2tau)|Omega_0(i nu)| at nu=10^3,10^4,10^6", N[{(10^3)^(2 + 2 ta) Abs[OmL[0, ta, I 10^3]], (10^4)^(2 + 2 ta) Abs[OmL[0, ta, I 10^4]], (10^6)^(2 + 2 ta) Abs[OmL[0, ta, I 10^6]]}, 20]];
  pr["OmL - Om at s=1/3+1.4i", OmL[3, ta, sp] - Om[3, ta, sp]];
  (* A1: residues by Cauchy circles *)
  Do[
   Module[{a = l/2 + 1/4, b = l/2 + 3/4, z0, z1, rr = (1/2 - ta)/4, Nc = 96, pts, r1, r2},
    z0 = a + n; z1 = b - ta + n;
    r1 = Total[Table[With[{w = rr Exp[2 Pi I j/Nc]}, N[Om[l, ta, z0 + w] w, wp]], {j, 0, Nc - 1}]]/Nc;
    r2 = Total[Table[With[{w = rr Exp[2 Pi I j/Nc]}, N[Om[l, ta, z1 + w] w, wp]], {j, 0, Nc - 1}]]/Nc;
    pr["A1 l=" <> ToString[l] <> " n=" <> ToString[n] <> ": Cauchy Res1 - formula, Res2 - formula",
     {r1 - N[Res1[l, n, ta], wp], r2 - N[Res2[l, n, ta], wp]}];
    ], {l, {0, 3}}, {n, {0, 2}}];
  Print["   (circle radius (1/2-tau)/4, 96 pts: truncation ~ 4^-96)"];
  (* square-lattice regrouping: partial check sum_l d_l (-sum_n Res) for l <= L vs truncated square *)
  , {ta, {ToExpression[$ScriptCommandLine[[2]]]}}];
Print["=== done ==="];
Quit[];
