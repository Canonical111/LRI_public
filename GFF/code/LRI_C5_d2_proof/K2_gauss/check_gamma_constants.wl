q[t_] := Sin[Pi t]^2 Gamma[t]^4/Gamma[1/2 + t]^4 t^2;
q4 = SeriesCoefficient[q[t], {t, 0, 4}];
q1 = SeriesCoefficient[q[t], {t, 0, 1}];
g2 = SeriesCoefficient[(Gamma[t]/Gamma[1 - t])^2 (Gamma[1/2 - t/2]/Gamma[1/2 + t/2])^4, {t, 0, 2}];
simp[x_] := FullSimplify[FunctionExpand[x /. {PolyGamma[n_, 1/2] :> FunctionExpand[PolyGamma[n, 1/2]], EulerGamma -> EulerGamma}]];
Print["q1 = ", simp[q1]];
Print["q4 = ", simp[q4]];
Print["g2 = ", simp[g2]];
Print["q4 - g2 = ", simp[q4 - g2]];
Print["target pi^4/3 + 56 log2 z3 - 32 pi^2 log2^2 = ", N[Pi^4/3 + 56 Log[2] Zeta[3] - 32 Pi^2 Log[2]^2, 20], "   q4-g2 numeric: ", N[q4 - g2, 20]];

Quiet@CloseKernels[];
Exit[0];
