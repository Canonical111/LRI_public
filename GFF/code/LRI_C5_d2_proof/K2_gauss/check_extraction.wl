(* Laurent structure of T(tau) = pi^2 F^2 + sin^2 Gamma^4 G^2/Gamma(1/2+tau)^4 - C^2 Gr^4 using symbolic Taylor data of F,G *)
Ff = 1 + u t + v t^2 + w3 t^3 + w4 t^4;
Gg = 1 + sig t^3 + tg t^4 + g5 t^5 + g6 t^6;
q = Series[t^2 Sin[Pi t]^2 Gamma[t]^4/Gamma[1/2 + t]^4, {t, 0, 6}];
Cs = Series[(Gamma[t]/Gamma[1 - t])^2 (Gamma[1/2 - t/2]/Gamma[1/2 + t/2])^4, {t, 0, 4}];
T = Series[Pi^2 Ff^2 + q Gg^2/t^2 - Cs, {t, 0, 2}];
cf[k_] := FullSimplify[FunctionExpand[SeriesCoefficient[T, k]]];
Do[Print["[t^", k, "] T = ", cf[k]], {k, -2, 2}];
(* impose bilinear identity tg + pi^2 v = pi^2 u^2/2 - pi^4/6 and u, sigma values *)
K2 = 14 Zeta[3] Log[2] + cf[2]/4 /. tg -> Pi^2 u^2/2 - Pi^4/6 - Pi^2 v /. {u -> 4 Log[2] - 8 Catalan/Pi, sig -> 8 Pi Catalan - 14 Zeta[3]};
Print["K2 = ", FullSimplify[Expand[K2]]];
Print["K2 - (32 G^2 - 28 z3 log2) = ", FullSimplify[Expand[K2 - (32 Catalan^2 - 28 Zeta[3] Log[2])]]];

Quiet@CloseKernels[];
Exit[0];
