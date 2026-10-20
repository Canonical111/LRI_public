(* Exact (symbolic) verification of every algebraic step of the d=2 proof.
   Output: True/0 lines; any failure prints False or a nonzero residual. *)

(* ---------- S1. local forms of the Barnes integrand at the two right pole families ----------
   integrand: g(s)^2 R_tau(s) = Gamma(a+s)^3 Gamma(a-s)^2 Gamma(b-tau-s) /
                               (Gamma(b+s)^2 Gamma(b-s)^3 Gamma(a+tau+s)),  a = l/2+1/4, b = a+1/2.
   Family 1: s = a+n+u, m = l+n.  Claim: integrand = cos(pi u)^3/(sin(pi u)^2 cos(pi(tau+u))) h(m+u) h(n+u)
   Family 2: s = b-tau+n+u.       Claim: integrand = -[sin(pi tau)^3/(pi cos(pi tau)^2)] k(m+u)k(n+u) *
                                            [pi/sin(pi(-u))]... checked via the n-part identity below.  *)
reflect = {Gamma[z_] :> Pi/(Sin[Pi z] Gamma[1 - z])};
(* n-part identity, family 1:  Gamma(-n-u)^2 Gamma(1/2-n-tau-u)/Gamma(1/2-n-u)^3
      = cos(pi u)^3/(sin(pi u)^2 cos(pi(tau+u))) * Gamma(n+1/2+u)^3/(Gamma(n+1+u)^2 Gamma(n+1/2+tau+u)) *)
lhs1 = Gamma[-n - u]^2 Gamma[1/2 - n - tau - u]/Gamma[1/2 - n - u]^3;
rhs1 = Cos[Pi u]^3/(Sin[Pi u]^2 Cos[Pi (tau + u)]) Gamma[n + 1/2 + u]^3/(Gamma[n + 1 + u]^2 Gamma[n + 1/2 + tau + u]);
chk1 = FullSimplify[(lhs1 /. reflect)/rhs1, Assumptions -> Element[n, Integers] && n >= 0];
Print["S1 family-1 n-part identity (ratio) : ", chk1];
(* numeric spot check of the same identity at random noninteger u, tau and integer n *)
Print["S1 family-1 spot check            : ", N[(lhs1/rhs1) /. {n -> 3, u -> 0.137, tau -> 0.29}, 20]];
(* m-part: Gamma(a+s)^3/(Gamma(b+s)^2 Gamma(a+tau+s)) at s=a+n+u with 2a = l+1/2 is h(m+u): trivial
   (a+s = m+1/2+u, b+s = m+1+u, a+tau+s = m+1/2+tau+u). *)
(* family-1 residue: (1/pi^2) d/du[ (pi u/sin(pi u))^2 cos^3(pi u)/cos(pi(tau+u)) H(u) ] at u=0 *)
res1 = SeriesCoefficient[Cos[Pi u]^3/(Sin[Pi u]^2 Cos[Pi (tau + u)]) hh[u], {u, 0, -1}];
target1 = (1/Pi^2) (Pi Sin[Pi tau]/Cos[Pi tau]^2 hh[0] + hh'[0]/Cos[Pi tau]);
Print["S1 family-1 residue formula        : ", FullSimplify[res1 - target1]];
(* family 2: n-part  Gamma(tau-1/2-n-u)^2 Gamma(-n-u)/Gamma(tau-n-u)^3 ; residue at u=0 (s = b-tau+n+u) *)
lhs2 = Gamma[tau - 1/2 - n]^2/Gamma[tau - n]^3;
rhs2 = (-1)^n Sin[Pi tau]^3/(Pi Cos[Pi tau]^2) Gamma[n + 1 - tau]^3/Gamma[n + 3/2 - tau]^2;
chk2 = FullSimplify[(lhs2 /. reflect)/rhs2, Assumptions -> Element[n, Integers] && n >= 0];
Print["S1 family-2 n-part identity (ratio) : ", chk2];
Print["S1 family-2 spot check            : ", N[(lhs2/rhs2) /. {n -> 4, tau -> 0.31}, 20]];
(* Res_{u=0} Gamma(-n-u) (as a function of s=...+u) = -(-1)^n/n! *)
Print["S1 Res Gamma(-n-u) at n=0..4       : ", Table[Residue[Gamma[-nn - u], {u, 0}] + (-1)^nn/nn!, {nn, 0, 4}]];

(* ---------- S2. collapse of the bilinear form to a sum of squares ---------- *)
Clear[F, Fp];
SS = Sin[Pi tau]; CC = Cos[Pi tau];
H0 = Pi^2/Gamma[tau] (F + CC/SS Fp);
H1 = -Pi^3/Gamma[tau] Fp;
K0 = Gamma[tau] Gamma[1 - tau]^2 F;
J = Gamma[tau]/Gamma[1 - tau] (-(1/Pi^2) (Pi SS/CC^2 H0^2 + (2/CC) H0 H1) + SS^3/(Pi CC^2) K0^2);
Jred = FullSimplify[J /. Gamma[1 - tau] -> Pi/(Sin[Pi tau] Gamma[tau])];
Print["S2 J - Pi^2(F^2+Fp^2)              : ", FullSimplify[Jred - Pi^2 (F^2 + Fp^2)]];
(* the moment-relation step: I5 = s I3 - c I4, I6 = s I4 at t = 1-tau, with
   I3(1-tau) = Pi^2 F/(2 SS), I4(1-tau) = Pi^2 Fp/(2 SS); H0 = 2 I5/Gamma(tau), H1 = -2 Pi I6/Gamma(tau),
   K0 = 2 Gamma(1-tau) I3/Pi *)
s1 = Sin[Pi (1 - tau)]; c1 = Cos[Pi (1 - tau)];
I3v = Pi^2 F/(2 SS); I4v = Pi^2 Fp/(2 SS);
I5v = s1 I3v - c1 I4v; I6v = s1 I4v;
Print["S2 H0 from I5                      : ", FullSimplify[2 I5v/Gamma[tau] - H0]];
Print["S2 H1 from I6                      : ", FullSimplify[-2 Pi I6v/Gamma[tau] - H1]];
Print["S2 K0 from I3                      : ", FullSimplify[(2 Gamma[1 - tau] I3v/Pi - K0) /. Gamma[1 - tau] -> Pi/(Sin[Pi tau] Gamma[tau])]];
(* the KLT route: J = (1/pi^2)[ s I1 (2)(2) I4 + (2 I2)(2 I5) ] at t = tau, with moment relations at t = tau *)
st = Sin[Pi tau]; ct = Cos[Pi tau];
Clear[i3, i4];
i1 = ct i3 + st i4; i2 = st i3; i5 = st i3 - ct i4; i6 = st i4;
Print["S2 KLT: s I1 I4 + I2 I5 - s^2(I3^2+I4^2) : ", Simplify[st i1 i4 + i2 i5 - st^2 (i3^2 + i4^2)]];
Print["S2 KLT: s^2(I3^2+I4^2) - (I2^2+I6^2)      : ", Simplify[st^2 (i3^2 + i4^2) - (i2^2 + i6^2)]];

(* ---------- S3. Laurent extraction and assembly ---------- *)
Clear[u, v, w, x4, sg, tg, g5, g6, l2];
ord = 6;
Fser = 1 + u tau + v tau^2 + w tau^3 + x4 tau^4 + O[tau]^5;
Gser = 1 + sg tau^3 + tg tau^4 + g5 tau^5 + g6 tau^6 + O[tau]^7;
Fmser = Series[Gamma[tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2), {tau, 0, 5}] Gser;  (* F(1-tau), Thomae *)
Jser = Pi^2 (Fser^2 + Fmser^2);
(* gamma interpolation of gs:Kdefinition at d=2: J^Gamma_t = B(1,2-t)^2 + (2/t)[B(1,2-t) - B(1+2t,2-t)] *)
Bd[d_, a_, b_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
JG[t_] := Bd[2, 1, 2 - t]^2 + (2/t) (Bd[2, 1, 2 - t] - Bd[2, 1 + 2 t, 2 - t]);
JGser = Series[JG[2 tau], {tau, 0, 2}];
diff = Jser - JGser;
cf = Table[Simplify[FunctionExpand[SeriesCoefficient[diff, k]]], {k, -2, 2}];
Print["S3 [tau^-2..tau^2] of J - J^Gamma (raw):"];
Do[Print["    k=", k - 3, ": ", cf[[k]]], {k, 1, 5}];
(* insert the proved elementary values and the elimination rule *)
vals = {u -> 4 Log[2] - 8 Catalan/Pi, sg -> 8 Pi Catalan - 14 Zeta[3], tg -> Pi^2 u^2/2 - Pi^4/6 - Pi^2 v};
cf2 = Table[FullSimplify[(cf[[k]] /. vals) /. vals], {k, 1, 5}];
Print["S3 after u, sigma, elimination rule:"];
Do[Print["    k=", k - 3, ": ", cf2[[k]]], {k, 1, 5}];
K2 = FullSimplify[cf2[[5]]/4];
Print["S3 K2 = [t^2](J - J^Gamma) = ", K2];
Print["S3 K2 - (32 G^2 - 28 zeta3 log2) = ", FullSimplify[K2 - (32 Catalan^2 - 28 Zeta[3] Log[2])]];
Print["S3 numeric K2 = ", N[K2, 50]];
(* uniform form: K_d = (Phi_d + A U)/2 with A = 4 log2, U = psi2(1/2) *)
Print["S3 uniform form check: ", FullSimplify[K2 - (1/2) ((PolyGamma[1, 1/4] - PolyGamma[1, 3/4])^2/4 + 4 Log[2] PolyGamma[2, 1/2])]];
Quiet@CloseKernels[]; Exit[0];
