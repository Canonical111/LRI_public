(* Exact Laurent extraction of K_2 = [t^2](J_t - J_t^Gamma) at d = 2, t = 2 tau.
   Proved closed form (this note):  J = Pi^2 F[tau]^2 + h[tau]^2 G[tau]^2 / tau^2,
     h[tau] = Pi Gamma[1+tau]/(Gamma[1-tau] Gamma[1/2+tau]^2),
     F[x] = 1 + u x + v x^2 + f3 x^3 + O(x^4),  G[x] = 1 + sig x^3 + w x^4 + O(x^5).
   Inputs proved in the note (d=1 K proof): w + Pi^2 v = Pi^2 u^2/2 - Pi^4/6 (eq:KproofTaylorCancellation),
     u = 4 Log[2] - 8 Catalan/Pi, sig = 8 Pi Catalan - 14 Zeta[3] (eq:KproofLowerCoefficients). *)
ord = 3;
h = Pi Gamma[1 + tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2);
Fs = 1 + u tau + v tau^2 + f3 tau^3 + f4 tau^4;
Gs = 1 + sig tau^3 + w tau^4 + g5 tau^5 + g6 tau^6;
J = Pi^2 Fs^2 + h^2 Gs^2/tau^2;
B[a_, b_] := Gamma[(2 - a)/2] Gamma[(2 - b)/2] Gamma[(a + b - 2)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(4 - a - b)/2]);
t = 2 tau;
JG = B[1, 2 - t]^2 + (2/t) (B[1, 2 - t] - B[1 + 2 t, 2 - t]);
diff = Series[J - JG, {tau, 0, 2}];
coeffs = Table[{k, FullSimplify[SeriesCoefficient[diff, k]]}, {k, -2, 2}];
Print["raw Laurent coefficients of J - J^Gamma in tau:"];
Do[Print["  tau^", c[[1]], " : ", c[[2]]], {c, coeffs}];
rules = {w -> Pi^2 u^2/2 - Pi^4/6 - Pi^2 v};
vals = {u -> 4 Log[2] - 8 Catalan/Pi, sig -> 8 Pi Catalan - 14 Zeta[3]};
Print["after inserting the bilinear cancellation and u, sigma:"];
Do[Print["  tau^", c[[1]], " : ", FullSimplify[Expand[(c[[2]] /. rules) /. vals]]], {c, coeffs}];
K2 = FullSimplify[Expand[(SeriesCoefficient[diff, 2] /. rules) /. vals]/4];
Print["K2 = [t^2](J - J^Gamma) = [tau^2]/4 = ", K2];
Print["K2 - (32 Catalan^2 - 28 Zeta[3] Log[2]) = ", FullSimplify[K2 - (32 Catalan^2 - 28 Zeta[3] Log[2])]];
Print["N[K2, 50] = ", N[K2, 50]];
(* separate Gamma-only checks *)
Print["[t^2] J^Gamma = ", FullSimplify[SeriesCoefficient[Series[JG, {tau, 0, 2}], 2]/4]];
Print["[tau^4] h^2 = ", FullSimplify[SeriesCoefficient[Series[h^2, {tau, 0, 4}], 4]]];
Print["[tau^1] h^2 = ", FullSimplify[SeriesCoefficient[Series[h^2, {tau, 0, 4}], 1]]];
