B[a_, b_] := Gamma[(2 - a)/2] Gamma[(2 - b)/2] Gamma[(a + b - 2)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(4 - a - b)/2]);
t = 2 tau;
JG = B[1, 2 - t]^2 + (2/t) (B[1, 2 - t] - B[1 + 2 t, 2 - t]);
s1 = Series[JG, {tau, 0, 2}];
s2 = Series[Exp[8 Log[2] tau]/tau^2 - 20 Zeta[3] tau - 48 Log[2] Zeta[3] tau^2, {tau, 0, 2}];
Print["J^Gamma - (e^{8 log2 tau}/tau^2 - 20 zeta3 tau - 48 log2 zeta3 tau^2) = ", FullSimplify[Normal[s1 - s2]]];
h = Pi Gamma[1 + tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2);
Print["log h - (4 log2 tau - Pi^2 tau^2/2 + 4 zeta3 tau^3 - Pi^4 tau^4/12) = ",
  FullSimplify[Normal[Series[Log[h], {tau, 0, 4}]] - (4 Log[2] tau - Pi^2 tau^2/2 + 4 Zeta[3] tau^3 - Pi^4 tau^4/12)]];
Bt = Gamma[tau] Gamma[1/2 - tau]/(Gamma[1 - tau] Gamma[1/2 + tau]);
Btt = Gamma[1/2 - 2 tau] Gamma[tau] Gamma[1/2 + tau]/(Gamma[1/2 + 2 tau] Gamma[1 - tau] Gamma[1/2 - tau]);
Print["B(1,2-t) - Bt = ", FullSimplify[B[1, 2 - t] - Bt], ",  B(1+2t,2-t) - Btt = ", FullSimplify[B[1 + 2 t, 2 - t] - Btt]];
Print["log(tau Bt) - (4 log2 tau + 4 zeta3 tau^3) = ", FullSimplify[Normal[Series[Log[tau Bt], {tau, 0, 4}]] - (4 Log[2] tau + 4 Zeta[3] tau^3)]];
Print["log(tau Btt) - (4 log2 tau + 32 zeta3 tau^3) = ", FullSimplify[Normal[Series[Log[tau Btt], {tau, 0, 4}]] - (4 Log[2] tau + 32 Zeta[3] tau^3)]];
(* d=1 remark: note eq:KproofTwoFunctions rewritten with Thomae *)
F[x_] := HypergeometricPFQ[{1/2, 1/2, x}, {1, 1}, 1];
G[x_] := HypergeometricPFQ[{x, x, x}, {1/2 + x, 1/2 + x}, 1];
x0 = 3/10;
j1 = 2 Pi (1 + Cos[Pi x0] + 2 Sin[Pi x0]) Gamma[x0]^2/Gamma[1/2 + x0]^2 G[x0] + 2 Pi^2 (2 + Tan[Pi x0/2]) F[x0];
j2 = 2 Pi^2 ((2 + Cot[Pi x0/2]) F[1 - x0] + (2 + Tan[Pi x0/2]) F[x0]);
Print["d=1: note two-function form minus 2pi^2[(2+cot)F(1-t)+(2+tan)F(t)] at t=3/10: ", N[j1 - j2, 30]];
Print["Thomae check F(1-x) - Gamma(x) G(x)/(Gamma(1-x)Gamma(1/2+x)^2) at x=3/10: ", N[F[1 - x0] - Gamma[x0] G[x0]/(Gamma[1 - x0] Gamma[1/2 + x0]^2), 30]];
