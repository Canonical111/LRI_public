(* checks_all.wl -- numerical and exact checks for PROOF_L2.md (structural route).
   Numerical agreement is NOT used as a proof step; these checks only guard each step.
   Run:  wolframscript -file checks_all.wl > checks_all.log  *)

Print["=== 0. residue functional (exact): Res_{t=0} (A+B cos(2pi t+pi x))^2/(sin^4(pi t) sin^4(pi(t+x))) ==="];
res = SeriesCoefficient[(A + B Cos[2 Pi t + Pi x])^2/(Sin[Pi t]^4 Sin[Pi (t + x)]^4), {t, 0, -1}];
target = -4 (2 A B (1 + 4 Cos[Pi x]^2) + Cos[Pi x] (3 A^2 + 4 B^2) + Cos[Pi x]^3 (2 A^2 + B^2))/(Pi Sin[Pi x]^7);
Print["residue - target  (should be 0): ", FullSimplify[TrigExpand[res - target]]];

(* two-mode data: Omega_x(tau) = pi^4 Sum_k [Gamma(1-x/2+k+tau)Gamma(1-x/2-k-tau)]^-4 = A(x) + B(x) cos(2 pi tau)
   A+B = Omega_x(0) = sin^4(pi x/2) Sum_k [Gamma(k+x/2)/Gamma(k+1-x/2)]^4,
   A-B = Omega_x(1/2) = cos^4(pi x/2) Sum_k [Gamma(k+1/2+x/2)/Gamma(k+3/2-x/2)]^4 *)
Hp[u_, d_] := Gamma[u]^4/Gamma[u + d]^4 HypergeometricPFQ[{1, u, u, u, u}, {u + d, u + d, u + d, u + d}, 1];
Omt[u_, d_] := Sin[Pi u]^4 Hp[u, d] + Sin[Pi (u + d)]^4 Hp[2 - u - d, d];
AB[x_] := Module[{d = 1 - x, p, m}, p = Omt[(1 - d)/2, d]; m = Omt[-d/2, d]; {(p + m)/2, (p - m)/2}];
Wres[x_] := Module[{a, b, c, s}, {a, b} = AB[x]; c = Cos[Pi x]; s = Sin[Pi x];
   (Gamma[1 - x]/Gamma[x])^4*4*(2 a b (1 + 4 c^2) + c (3 a^2 + 4 b^2) + c^3 (2 a^2 + b^2))/(Pi s^7)];
Phi[x_] := 2^(4 - 4 x) Gamma[1 - x]^4 Gamma[x]^6/(Pi^(11/2) Gamma[2 x - 1/2]);
Wbil[x_] := Module[{a, b, ap, bp}, {a, b} = AB[x]; {ap, bp} = AB[1 - x]; Phi[x] (a bp + b ap)];

Print["=== 1. Theorem A: W(x) [residue form] vs Phi(x)[A(x)B(1-x)+B(x)A(1-x)] ==="];
Do[Module[{w1 = N[Wres[x], 40], w2 = N[Wbil[x], 40]}, Print["x=", N[x, 6], "  W(residue)=", N[w1, 25], "  Phi*(AB'+BA')=", N[w2, 25], "  |diff|<", N[Abs[w1 - w2] + 10^-35, 3]]], {x, {1/2, 2/5, 1/3, 3/10, 27/100, 3/5, 7/10}}];
Print["W(1/2) = 8AB/pi = P4(2) = ", N[Wres[1/2], 30]];

Print["=== 2. Gamma prefactor: d/dx log Phi at x=1/2 (exact) ==="];
Print[FullSimplify[(D[Log[Phi[x]], x] /. x -> 1/2)]];
Print["reflection ratio Phi(x)/Phi(1-x) == 2^(4-8x) gamma(x)^2/gamma(2x-1/2) ? ",
  FullSimplify[Phi[x]/Phi[1 - x] - 2^(4 - 8 x) (Gamma[x]/Gamma[1 - x])^2 Gamma[3/2 - 2 x]/Gamma[2 x - 1/2], 1/4 < x < 3/4]];

Print["=== 3. duality K*: Barnes side vs reciprocal bilateral side (general a, complex tau) ==="];
lam[as_] := Module[{S = Total[as]}, 2^(2 - 2 S) Product[Gamma[as[[i]] + as[[j]]], {i, 4}, {j, i + 1, 4}] Times @@ Gamma[2 as]/(Pi^(9/2) Gamma[S - 1/2])];
J[m_, as_] := NIntegrate[Cosh[2 Pi m y] Re[Times @@ (Gamma[as + I y] Gamma[as - I y])], {y, 0, Infinity}, WorkingPrecision -> 40, PrecisionGoal -> 28, MaxRecursion -> 40]/Pi;
bil[u_, v_] := (Times @@ Gamma[u]/Times @@ Gamma[v]) HypergeometricPFQ[Join[{1}, u], v, 1] +
   (Times @@ (Sin[Pi v]/Sin[Pi u])) (Times @@ Gamma[2 - v]/Times @@ Gamma[2 - u]) HypergeometricPFQ[Join[{1}, 2 - v], 2 - u, 1];
OmSharp[tau_, as_] := Module[{c = 1/2 + as}, Times @@ (Sin[Pi (c - tau)]/Pi) bil[1 - c + tau, c + tau]];
as = {21/100, 17/100, 26/100, 19/100};
j0 = J[0, N[as, 40]]; j1 = J[1, N[as, 40]]; l = lam[N[as, 40]];
Do[Print["tau=", tau, "  Barnes=", N[j1 + j0 Cos[2 Pi tau], 20], "  reciprocal=", N[4 Pi^7 l OmSharp[tau, N[as, 40]], 20]],
  {tau, {13/100 + 7/100 I, 31/100}}];
Print["symmetric x=2/5: J0/(4pi^3 lam B(1-x)) and J1/(4pi^3 lam A(1-x)):"];
Module[{x = 2/5, a, ap, bp, j0s, j1s, ls}, a = x/2; {ap, bp} = N[AB[1 - x], 40];
  j0s = J[0, N[{a, a, a, a}, 40]]; j1s = J[1, N[{a, a, a, a}, 40]]; ls = lam[N[{a, a, a, a}, 40]];
  Print[N[j0s/(4 Pi^3 ls bp), 20], "   ", N[j1s/(4 Pi^3 ls ap), 20]]];

Print["=== 4. Lemma R'' at complex parameters ==="];
Iint[as3_, b_] := NIntegrate[Times @@ (Gamma[as3 + I y] Gamma[as3 - I y])/(Gamma[b + I y] Gamma[b - I y]), {y, -Infinity, Infinity}, WorkingPrecision -> 40, PrecisionGoal -> 25, MaxRecursion -> 40]/(2 Pi);
rhsR[as3_, b_] := Module[{A = Total[as3]}, 2 Sqrt[Pi] 2^(2 b - 2 A) Gamma[as3[[1]] + as3[[2]]] Gamma[as3[[1]] + as3[[3]]] Gamma[as3[[2]] + as3[[3]]] (Times @@ Gamma[2 as3])/(Gamma[A + 1/2 - b] Times @@ Gamma[as3 + b]) HypergeometricPFQ[Join[{2 b - 1}, b - as3], b + as3, 1]];
p3 = {31/100 + 5/100 I, 22/100 - 3/100 I, 2/5}; bb = 83/100 + 1/10 I;
Print["LHS=", N[Iint[N[p3, 40], N[bb, 40]], 20], "   RHS=", N[rhsR[N[p3, 40], N[bb, 40]], 20]];
Print["R'' at b=1/2 reduces to de Branges-Wilson (a4=0); at b=a3 to Barnes' first lemma: see PROOF_L2.md"];

Print["=== 5. terminating case of R'' (a3=b+n): exact checks ==="];
ClearAll[a1, a2, b, n];
Pref[nn_] := Module[{a3 = b + nn, A}, A = a1 + a2 + a3; 2 Sqrt[Pi] 2^(2 b - 2 A) Gamma[a1 + a2] Gamma[a1 + a3] Gamma[a2 + a3] Gamma[2 a1] Gamma[2 a2] Gamma[2 a3]/(Gamma[A + 1/2 - b] Gamma[a1 + b] Gamma[a2 + b] Gamma[a3 + b])];
Kn[nn_] := Pochhammer[2 b, nn] Pochhammer[1/2, nn]/(Pochhammer[b + 1/2, nn] Pochhammer[b, nn])*Pochhammer[b - a2, nn] Pochhammer[1/2 - nn - a1 - a2, nn]/(Pochhammer[b + a1, nn] Pochhammer[1/2 - nn, nn]);
LHSpref[nn_] := Pochhammer[a2 + b, nn] Pochhammer[b - a2, nn] Gamma[2 a1] Gamma[2 a2] Gamma[a1 + a2]^2/Gamma[2 a1 + 2 a2];
Print["Pref*K_n/LHSpref for n=0..6: ", Table[FullSimplify[FunctionExpand[Pref[nn] Kn[nn]/LHSpref[nn]]], {nn, 0, 6}]];
FL[nn_, p_] := HypergeometricPFQ[{-nn, p[[1]] + p[[2]], p[[2]], p[[2]] + 1/2}, {p[[2]] + p[[3]], 1 + p[[2]] - p[[3]] - nn, p[[1]] + p[[2]] + 1/2}, 1];
FR[nn_, p_] := HypergeometricPFQ[{2 p[[3]] - 1, p[[3]] - p[[1]], p[[3]] - p[[2]], -nn}, {p[[3]] + p[[1]], p[[3]] + p[[2]], 2 p[[3]] + nn}, 1];
pp = {3/17, 5/13, 7/11};
Print["F_R - K_n F_L for n=0..6 (exact rationals): ", Table[Simplify[FR[nn, pp] - (Kn[nn] /. {a1 -> pp[[1]], a2 -> pp[[2]], b -> pp[[3]]}) FL[nn, pp]], {nn, 0, 6}]];
(* direct terminating check of R'' itself: LHS integral with polynomial insertion vs RHS *)
Module[{p = {1/5, 3/10}, bq = 7/10, nn = 2, lhs, rhs},
  lhs = NIntegrate[Re[Gamma[p[[1]] + I y] Gamma[p[[1]] - I y] Gamma[p[[2]] + I y] Gamma[p[[2]] - I y] Pochhammer[bq + I y, nn] Pochhammer[bq - I y, nn]], {y, -Infinity, Infinity}, WorkingPrecision -> 40, PrecisionGoal -> 25]/(2 Pi);
  rhs = rhsR[{p[[1]], p[[2]], bq + nn}, bq];
  Print["R'' terminating n=2 numeric: ", N[lhs, 20], "  ", N[rhs, 20]]];
Quit[];
