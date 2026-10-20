(* Symbolic checks for the generic-d S family (route S_part).
   q = d/4, tau regulator; mu = q - tau/2 = 2 alpha0, kappa = q + tau/2, alpha0 = q/2 - tau/4, beta0 = 3q/2 + tau/4. *)
ok[name_, expr_] := Print[name, ": ", expr];

(* 1. t_l^2 S_tau = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2 t_{l,b'}^2, b' = d/2 - tau  (gs:RS, gs:balancedWheel) *)
tl[l_, s_] := Gamma[2 q] Gamma[l/2 + q/2 + s] Gamma[l/2 + q/2 - s]/(Gamma[l/2 + 3 q/2 + s] Gamma[l/2 + 3 q/2 - s]);
Sfac[l_, s_] := (Gamma[l/2 + q/2 - tau/4 + s] Gamma[l/2 + q/2 - tau/4 - s] Gamma[l/2 + 3 q/2 + s] Gamma[l/2 + 3 q/2 - s]/
     (Gamma[l/2 + 3 q/2 + tau/4 + s] Gamma[l/2 + 3 q/2 + tau/4 - s] Gamma[l/2 + q/2 + s] Gamma[l/2 + q/2 - s]))^2;
tlb[l_, s_, b_, d_] := Gamma[d/2] Gamma[(d - b)/2]/Gamma[b/2] Gamma[l/2 + b/4 + s] Gamma[l/2 + b/4 - s]/
    (Gamma[l/2 + d/2 - b/4 + s] Gamma[l/2 + d/2 - b/4 - s]);
ok["1  t^2 S / t_{l,b'}^2 - [G(q-tau/2)/G(q+tau/2)]^2",
  FullSimplify[tl[l, s]^2 Sfac[l, s]/tlb[l, s, 2 q - tau, 4 q]^2 - (Gamma[q - tau/2]/Gamma[q + tau/2])^2]];

(* 2. two-wheel convolution B_d(d-b', 2b') (gs:convolution) = C(tau) [G(q-tau/2)/G(q+tau/2)]^2 *)
Bd[a_, b_, d_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
Cc[t_] := Gamma[2 q] Gamma[t]/Gamma[2 q - t];
Xd[t_] := (Gamma[q - t/2]/Gamma[q + t/2])^2;
ok["2  B_d(d-b',2b') - C X_d", FullSimplify[Bd[4 q - (2 q - tau), 2 (2 q - tau), 4 q] - Cc[tau] Xd[tau]]];
ok["2b W_2(d;b) general b: B_d(d-b,2b) - G(d/2)G(b/2)^2G(d/2-b)/(G((d-b)/2)^2G(b))",
  FullSimplify[Bd[d - b, 2 b, d] - Gamma[d/2] Gamma[b/2]^2 Gamma[d/2 - b]/(Gamma[(d - b)/2]^2 Gamma[b])]];

(* 3. Laurent expansion of C^2 X_d^2 in the note's psi basis (gs:psiBasis) *)
basis = {A -> PolyGamma[0, 2 q] + PolyGamma[0, 1] - 2 PolyGamma[0, q], R -> PolyGamma[1, 2 q] - PolyGamma[1, 1],
   U -> PolyGamma[2, q], V -> PolyGamma[2, 1] + PolyGamma[2, 2 q], X -> PolyGamma[3, 2 q] - PolyGamma[3, 1]};
ser = Series[Cc[tau]^2 Xd[tau]^2, {tau, 0, 2}];
coefs = Table[SeriesCoefficient[ser, k], {k, -2, 2}];
claimed = {1, 2 A, 2 A^2 - R, (4 A^3)/3 - 2 A R + (2 V - U)/6, 2 A^4/3 - 2 A^2 R + R^2/2 + A (2 V - U)/3 - X/12} /. basis;
qv = {1/5, 5/16, 3/8, 1/2, 5/8, 11/16, 3/4, 7/8};
ok["3  [tau^k](C^2 X^2), k=-2..2, claimed - exact at q in qv (should be 0)",
  Table[Chop[N[(coefs - claimed) /. q -> qq, 40], 10^-35], {qq, qv}]];
ok["3b note: [t^2] Gamma term = A^4/6-A^2R/2+R^2/8+A(2V-U)/12-X/48 equals [tau^2]/4",
  Table[Chop[N[(coefs[[5]]/4 - (A^4/6 - A^2 R/2 + R^2/8 + A (2 V - U)/12 - X/48) /. basis) /. q -> qq, 40], 10^-35], {qq, qv}]];

(* 4. s_k = [tau^k] <t^2 S_tau>_d = [tau^k] C X^2, k=-1..3: tau^-1 exp(sum eps_k tau^k) *)
eps = {PolyGamma[0, 1] + PolyGamma[0, 2 q] - 4 PolyGamma[0, q], (PolyGamma[1, 1] - PolyGamma[1, 2 q])/2,
   (PolyGamma[2, 1] + PolyGamma[2, 2 q] - PolyGamma[2, q])/6, (PolyGamma[3, 1] - PolyGamma[3, 2 q])/24};
sk = CoefficientList[Normal[Series[Exp[Sum[eps[[k]] x^k, {k, 1, 4}]], {x, 0, 4}]], x];
serS = Series[Cc[tau] Xd[tau]^2, {tau, 0, 3}];
ok["4  s_k exact - Bell form, k=-1..3",
  Table[Chop[N[(Table[SeriesCoefficient[serS, k], {k, -1, 3}] - sk[[1 ;; 5]]) /. q -> qq, 40], 10^-35], {qq, qv}]];

(* 5. two-mode residue functional: Xi = c0 + c1 cos(2 pi (t + a0)), S = Xi/(sin^2(pi t) sin^2(pi (t + 2 a0))) *)
SS = (c0 + c1 Cos[2 Pi (t + a0)])/(Sin[Pi t]^2 Sin[Pi (t + 2 a0)]^2);
res = Residue[SS, {t, 0}];
ok["5a -Res_{t=0} S - 2(c1 + c0 cos 2pi a0)/(pi sin^3 2pi a0)", FullSimplify[-res - 2 (c1 + c0 Cos[2 Pi a0])/(Pi Sin[2 Pi a0]^3)]];
fplus = (SS /. t -> -a0); fminus = (SS /. t -> 1/2 - a0);
ok["5b -Res - [sin^2(pi a0) f+ - cos^2(pi a0) f-]/(2 pi sin 2 pi a0)",
  FullSimplify[-res - (Sin[Pi a0]^2 fplus - Cos[Pi a0]^2 fminus)/(2 Pi Sin[2 Pi a0])]];
ok["5c leading double-pole coefficient at t=0 of S: p = (c0 + c1 cos 2pi a0)/(pi^2 sin^2 2pi a0)",
  FullSimplify[SeriesCoefficient[SS, {t, 0, -2}] - (c0 + c1 Cos[2 Pi a0])/(Pi^2 Sin[2 Pi a0]^2)]];

(* 6. d = 2 (q=1/2): spin-summed lattice sums factorize into Dougall 2H2 squares and reproduce C X^2 *)
dougall[a_, b_, c_, e_] := Pi^2/(Sin[Pi a] Sin[Pi b]) Gamma[c + e - a - b - 1]/(Gamma[c - a] Gamma[e - a] Gamma[c - b] Gamma[e - b]);
With[{a0 = 1/4 - tau/4, b0 = 3/4 + tau/4},
  Fp = dougall[a0, a0, b0, b0]^2; Fm = dougall[a0 + 1/2, a0 + 1/2, b0 + 1/2, b0 + 1/2]^2;
  ok["6a d=2: [sin^2 F+ - cos^2 F-]/(2 pi sin 2pi a0) - C X^2",
   FullSimplify[(Sin[Pi a0]^2 Fp - Cos[Pi a0]^2 Fm)/(2 Pi Sin[2 Pi a0]) - (Cc[tau] Xd[tau]^2 /. q -> 1/2), 0 < tau < 1]];
  ok["6b d=2: c1 = (sin^4 F+ - cos^4 F-)/2 (global one mode)", FullSimplify[(Sin[Pi a0]^4 Fp - Cos[Pi a0]^4 Fm)/2, 0 < tau < 1]]];

(* 7. d=2: residue-lattice identity Sigma0 = pi tan(pi mu) G(tau)G(mu)^4/(2 sin^2(pi kappa) G(2q)G(2q-tau)G(kappa)^4) via Gauss *)
With[{mu = 1/2 - tau/2, kap = 1/2 + tau/2},
  Hg = Gamma[mu]^2 Gamma[1 - 2 mu]/Gamma[1 - mu]^2;
  ok["7  d=2 Sigma0 (Gauss^2) - closed", FullSimplify[Hg^2 - Pi Tan[Pi mu] Gamma[tau] Gamma[mu]^4/(2 Sin[Pi kap]^2 Gamma[1] Gamma[1 - tau] Gamma[kap]^4), 0 < tau < 1]]];

(* 8. global one-mode coefficient c0 = pi sin^3(pi mu) W/(2 cos(pi mu)), W = C X^2/Gamma(2q)^2; check at d=2 against Dougall *)
With[{a0 = 1/4 - tau/4, b0 = 3/4 + tau/4},
  ok["8  d=2 c0: sin^4(pi a0) F+ - pi sin^3(2 pi a0) W/(2 cos 2 pi a0)",
   FullSimplify[Sin[Pi a0]^4 dougall[a0, a0, b0, b0]^2 - Pi Sin[2 Pi a0]^3 (Cc[tau] Xd[tau]^2 /. q -> 1/2)/(2 Cos[2 Pi a0]), 0 < tau < 1]]];

Quiet@CloseKernels[];
Exit[0];
