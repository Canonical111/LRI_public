(* End-to-end check: C(tau)<t^2 (Re R_tau - S_tau)>_2 (direct spectral) vs closed form; and <t^2 E2>_2 = -21 zeta(3) *)
lgr[s_, a_, b_] := LogGamma[a + s] + LogGamma[a - s] - LogGamma[b + s] - LogGamma[b - s];
integrandD[nu_?NumericQ, l_, tau_] := Module[{a = l/2 + 1/4, b = l/2 + 3/4, s = I nu, lg, lR, lS},
   lg = lgr[s, a, b];
   lR = LogGamma[a + s] + LogGamma[b - tau - s] - LogGamma[a + tau + s] - LogGamma[b - s];
   lS = 2 (lgr[s, a - tau/4, b + tau/4] - lg);
   Re[Exp[2 lg] (Exp[lR] - Exp[lS])]];
omegaD[l_?NumericQ, tau_] := NIntegrate[integrandD[nu, l, tau], {nu, 0, 1, 5, 20, 100, Infinity}, WorkingPrecision -> 25, PrecisionGoal -> 14, MaxRecursion -> 40]/Pi;
closed[tau_] := Module[{fF, fG, Ct},
   fF = HypergeometricPFQ[{1/2, 1/2, tau}, {1, 1}, 1]; fG = HypergeometricPFQ[{tau, tau, tau}, {1/2 + tau, 1/2 + tau}, 1];
   Ct = Gamma[tau]/Gamma[1 - tau];
   (Pi^2 fF^2 + Sin[Pi tau]^2 Gamma[tau]^4 fG^2/Gamma[1/2 + tau]^4)/Ct - Ct (Gamma[1/2 - tau/2]/Gamma[1/2 + tau/2])^4];
Do[
  tab = Table[omegaD[l, tau], {l, 0, 60}];
  (* tail: fit omega_l ~ sum_j c_j (l+1/2)^(-3-2tau-j) on l=40..60 and extrapolate *)
  fitdata = Table[{l, tab[[l + 1]]}, {l, 40, 60}];
  model = Sum[c[j] (l + 1/2)^(-3 - 2 tau - j), {j, 0, 3}];
  fit = FindFit[fitdata, model, Table[c[j], {j, 0, 3}], l, WorkingPrecision -> 25];
  tail = 2 NSum[model /. fit, {l, 61, Infinity}, WorkingPrecision -> 25];
  direct = tab[[1]] + 2 Total[Rest[tab]] + tail;
  Print["tau=", tau, "  direct=", N[direct, 15], "  closed=", N[closed[tau], 15], "  tail=", N[tail, 5]],
  {tau, {1/10, 1/5}}];
(* <t^2 E2>: E2 = -h^2/2 - 5 j/8 *)
E2int[nu_?NumericQ, l_] := Module[{a = l/2 + 1/4, b = l/2 + 3/4, s = I nu, h, j},
   h = Im[PolyGamma[0, a + s] - PolyGamma[0, b + s]]; j = Re[PolyGamma[1, a + s] - PolyGamma[1, b + s]];
   Exp[2 Re[lgr[s, a, b]]] (-h^2/2 - 5 j/8)];
e2l[l_?NumericQ] := NIntegrate[E2int[nu, l], {nu, 0, 1, 5, 20, 100, Infinity}, WorkingPrecision -> 25, PrecisionGoal -> 14]/Pi;
tabE = Table[e2l[l], {l, 0, 60}];
fitdata = Table[{l, tabE[[l + 1]]}, {l, 40, 60}];
model = Sum[c[j] (l + 1/2)^(-3 - j), {j, 0, 3}];
fit = FindFit[fitdata, model, Table[c[j], {j, 0, 3}], l, WorkingPrecision -> 25];
tail = 2 NSum[model /. fit, {l, 61, Infinity}, WorkingPrecision -> 25];
Print["<t^2 E2> = ", N[tabE[[1]] + 2 Total[Rest[tabE]] + tail, 15], "   -21 zeta3 = ", N[-21 Zeta[3], 15]];

Quiet@CloseKernels[];
Exit[0];
