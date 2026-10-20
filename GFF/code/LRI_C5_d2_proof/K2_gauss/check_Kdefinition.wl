(* consistency with gs:Kdefinition at d=2: [t^2](C(t/2)^2 Gr^4 - J_t^Gamma) = -A U/4 = 14 zeta3 log2,
   hence K2 = [t^2](J_t - J_t^Gamma) with J_t = pi^2 F(t/2)^2 + sin^2(pi t/2) Gamma(t/2)^4 G(t/2)^2/Gamma(1/2+t/2)^4 *)
Bd[d_, a_, b_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
JG[t_] := Bd[2, 1, 2 - t]^2 + 2/t (Bd[2, 1, 2 - t] - Bd[2, 1 + 2 t, 2 - t]);
Cg[t_] := (Gamma[t/2]/Gamma[1 - t/2])^2 (Gamma[1/2 - t/4]/Gamma[1/2 + t/4])^4;
diff = SeriesCoefficient[Series[Cg[t] - JG[t], {t, 0, 2}], 2];
Print["[t^2](C^2 Gr^4 - J^Gamma) = ", FullSimplify[FunctionExpand[diff]], "   ( -AU/4 = 14 Zeta[3] Log[2] )"];
(* full K2 from gs:Kdefinition with symbolic Taylor data *)
Ff = 1 + u tt + v tt^2 + w3 tt^3; Gg = 1 + sig tt^3 + tg tt^4 + g5 tt^5;
Jt = Pi^2 Ff^2 + Sin[Pi tt]^2 Gamma[tt]^4 Gg^2/Gamma[1/2 + tt]^4 /. tt -> t/2;
K2 = SeriesCoefficient[Series[Jt - JG[t], {t, 0, 2}], 2];
K2 = FullSimplify[FunctionExpand[K2] /. tg -> Pi^2 u^2/2 - Pi^4/6 - Pi^2 v /. {u -> 4 Log[2] - 8 Catalan/Pi, sig -> 8 Pi Catalan - 14 Zeta[3]}];
Print["K2 from gs:Kdefinition = ", K2];
Print["low orders of J_t - J^Gamma: ", Table[FullSimplify[FunctionExpand[SeriesCoefficient[Series[Jt - JG[t], {t, 0, 1}], k]]], {k, -2, 1}]];

Quiet@CloseKernels[];
Exit[0];
