(* Exact (symbolic) verification of the algebraic steps of proof_v2.md.
   Every line should print 0, True or {0,...}. Symbols are real unless stated (ComplexExpand convention).
   S0 = the new self-contained position-space route (Lemmas 1-3, Theorem 1).
   S1, S2 = the spectral cross-check (Route A, conditional on N7).
   S3 = Laurent extraction (Theorem 2). *)

(* ================= S0. Route B (Lemmas 1-3) ================= *)

(* S0a. Lemma 1: boundary terms of the Stokes identity on C \ Gamma_y.
   W_L + W_R = 0 on (0,y), W_L - W_R = 2a on (y,1), W_L + W_R = 2b on (1,oo), and c = -a (Cauchy).
   Edge integrand W_L conj(w_L) - W_R conj(w_R) with w_R = -w_L, +w_L, -w_L on the three pieces.
   a = 2 eta1 K(y), b = -2 I eta2 K(1-y);  K(y) = k1 + I k2, K(1-y) = k3 + I k4. *)
Clear[k1, k2, k3, k4, eta1, eta2];
aa = 2 eta1 (k1 + I k2); bb = -2 I eta2 (k3 + I k4); cc = -aa;
bsum = 2 aa Conjugate[bb] + 2 bb Conjugate[cc];          (* sum of the three edge integrals *)
PhiStokes = ComplexExpand[(I/2) bsum];
Print["S0a Lemma 1: (i/2)(boundary) + 8 eta1 eta2 Re[K(y) conj K(1-y)] = ",
  Simplify[PhiStokes + 8 eta1 eta2 ComplexExpand[Re[(k1 + I k2) Conjugate[k3 + I k4]]]]];
Print["S0a Lemma 1: (i/2)(boundary) is real: ", Simplify[ComplexExpand[Im[(I/2) bsum]]]];
Print["S0a Lemma 1: equals 2 Im(conj(a) b): ", Simplify[PhiStokes - ComplexExpand[2 Im[Conjugate[aa] bb]]]];
(* the two segment integrals: x = y s on [0,y] and x = 1-(1-y) sig on [y,1] *)
Clear[y, s, sig];
Print["S0a x(x-1)(x-y) at x = y s  minus y^2 s(1-s)(1-y s): ", Simplify[(x (x - 1) (x - y) /. x -> y s) - y^2 s (1 - s) (1 - y s)]];
Print["S0a x(x-1)(x-y) at x = 1-(1-y)sig  plus (1-y)^2 sig(1-sig)(1-(1-y)sig): ",
  Simplify[(x (x - 1) (x - y) /. x -> 1 - (1 - y) sig) + (1 - y)^2 sig (1 - sig) (1 - (1 - y) sig)]];

(* S0b. Edge values on the slits (abstract K; KK = K, the Pfaff and cut formulas inserted by hand):
   x<0:  u_pm = -+ I p,   v_pm = phi_pm * Kcut(1-x, -+) with Kcut(w,sgn) = w^(-1/2)(K(1/w) + sgn I K(1-1/w)),
         K(1-1/(1-x)) = K(x/(x-1)) = (1-x)^(1/2) K(x)  (Pfaff).  *)
Clear[x, tau, KK];
assumeNeg = x < 0 && 0 < tau < 1;
phiP = -I (-x)^(-1/2) (1 - x)^(tau - 1); phiM = I (-x)^(-1/2) (1 - x)^(tau - 1);
pp = (-x)^(-1/2) (1 - x)^(tau - 1) KK[x]; qq = (-x)^(-1/2) (1 - x)^(tau - 3/2) KK[1/(1 - x)];
KcutM[w_] := w^(-1/2) (KK[1/w] - I KK[1 - 1/w]);   (* value of K(1-y) for y = x + i0, i.e. 1-y = w - i0 *)
KcutP[w_] := w^(-1/2) (KK[1/w] + I KK[1 - 1/w]);   (* value of K(1-y) for y = x - i0 *)
pfaffRule = KK[1 - 1/(1 - x)] -> (1 - x)^(1/2) KK[x];
vP = (phiP KcutM[1 - x]) /. pfaffRule; vM = (phiM KcutP[1 - x]) /. pfaffRule;
Print["S0b v(x+i0) - (-p - I q), x<0: ", FullSimplify[vP - (-pp - I qq), assumeNeg]];
Print["S0b v(x-i0) - (-p + I q), x<0: ", FullSimplify[vM - (-pp + I qq), assumeNeg]];
(* x>1: phi_pm = -x^(-1/2)(x-1)^(tau-1) e^(-+ I pi tau); K(x pm i0) = x^(-1/2)(K(1/x) pm I K(1-1/x));
   K(1-x) = x^(-1/2) K(1-1/x) (Pfaff at 1-x < 0). *)
assumeBig = x > 1 && 0 < tau < 1;
(* principal-branch one-sided limits: Limit[] substitutes eps = 0 on the cut, so test at eps = 1e-25 with 80-digit arithmetic (expected residual O(eps)) *)
bvNum[expr_, val_] := Abs[N[(expr - val), 80]];
With[{xv = 23/10, tv = 37/100, ev = 10^-25},
  Print["S0b |(1-(x+i0))^(tau-1) + (x-1)^(tau-1) e^(-I pi tau)| at x=2.3 = ", ScientificForm[bvNum[(1 - (xv + I ev))^(tv - 1), -(xv - 1)^(tv - 1) Exp[-I Pi tv]], 3]];
  Print["S0b |(1-(x-i0))^(tau-1) + (x-1)^(tau-1) e^(+I pi tau)| at x=2.3 = ", ScientificForm[bvNum[(1 - (xv - I ev))^(tv - 1), -(xv - 1)^(tv - 1) Exp[I Pi tv]], 3]]];
With[{xv = -17/10, ev = 10^-25},
  Print["S0b |(x+i0)^(-1/2) + I (-x)^(-1/2)| at x=-1.7 = ", ScientificForm[bvNum[(xv + I ev)^(-1/2), -I (-xv)^(-1/2)], 3]];
  Print["S0b |(x-i0)^(-1/2) - I (-x)^(-1/2)| at x=-1.7 = ", ScientificForm[bvNum[(xv - I ev)^(-1/2), I (-xv)^(-1/2)], 3]]];
Print["S0b Pfaff argument: 1 - 1/(1-x) == x/(x-1): ", Simplify[1 - 1/(1 - x) - x/(x - 1)]];

(* S0c. Lemma 2: Stokes boundary algebra on D, primitive U based at 0.
   p,q,P,Q (x<0) and r,s,R,S,I1 (x>1) are real; P' = -p, S' = s. *)
Clear[p, q, P, Q, r, sv, R, S, I1, I2, I3, I4, I5, I6];
ep = Exp[-I Pi tau]; em = Exp[I Pi tau];
(* x<0 *)
uP = -I p; uM = I p; vPn = -p - I q; vMn = -p + I q; UP = I P; UM = -I P;
edgeNeg = ComplexExpand[UP Conjugate[vPn] - UM Conjugate[vMn]];
Print["S0c edge integrand on (-oo,0) + 2 I P p: ", Simplify[edgeNeg + 2 I P p]];
(* x>1 *)
uPb = -ep (r + I sv); uMb = -em (r - I sv); vPb = -ep sv; vMb = -em sv;
UPb = I1 - ep (R + I S); UMb = I1 - em (R - I S);
edgePos = ComplexExpand[UPb Conjugate[vPb] - UMb Conjugate[vMb]];
Print["S0c edge integrand on (1,oo) - (-2 I sin(pi tau) I1 s + 2 I S s): ",
  Simplify[ExpToTrig[edgePos - (-2 I Sin[Pi tau] I1 sv + 2 I S sv)]]];
(* integrals: int_{-oo}^0 (-2 I P p) = -I I5^2 (P(0)=0, P(-oo)=I5);
   int_1^oo (-2 I sin I1 s + 2 I S s) = -2 I sin I1 I4 + I I4^2 (S(1)=0, S(oo)=I4). FTC checked on test functions: *)
Ptest[t_] := Exp[t];  (* P(-oo)=0 would be wrong; use a test with P(0)=0: *)
Ptest2[t_] := 1 - Exp[t]; (* P(0)=0, P(-oo)=1, p = -P' = Exp[t] *)
Print["S0c FTC test: int_{-oo}^0 P p dx - P(-oo)^2/2 = ",
  Integrate[Ptest2[t] Exp[t], {t, -Infinity, 0}] - 1/2];
lhs2 = (I/2) (-I I5^2 - 2 I Sin[Pi tau] I1 I4 + I I4^2);
Print["S0c int_D u conj(v) d^2y - (1/2)(I5^2 + 2 s I1 I4 - I4^2): ",
  Simplify[lhs2 - (1/2) (I5^2 + 2 Sin[Pi tau] I1 I4 - I4^2)]];
(* second evaluation: primitive V of v based at 1 *)
VPn = -I2 + P + I Q; VMn = -I2 + P - I Q;
edgeNegV = ComplexExpand[VPn Conjugate[uP] - VMn Conjugate[uM]];
Print["S0c (V based at 1) edge on (-oo,0) - (-2 I I2 p + 2 I P p): ", Simplify[edgeNegV - (-2 I I2 p + 2 I P p)]];
VPb = -ep S; VMb = -em S;
edgePosV = ComplexExpand[VPb Conjugate[uPb] - VMb Conjugate[uMb]];
Print["S0c (V based at 1) edge on (1,oo) + 2 I S s: ", Simplify[ExpToTrig[edgePosV + 2 I S sv]]];
(* -> int_D v conj(u) = (I/2)(-I I4^2 - 2 I I2 I5 + I I5^2) = (1/2)(I4^2 + 2 I2 I5 - I5^2) *)

(* S0d. Lemma 3: Cauchy in the upper half plane for u and v, then N2 *)
st = Sin[Pi tau]; ct = Cos[Pi tau];
cauchyU = -I I5 + I1 - ep (I3 + I I4);
cauchyV = -I5 - I I6 + I2 - ep I4;
sol = Solve[ComplexExpand[{Re[cauchyU] == 0, Im[cauchyU] == 0, Re[cauchyV] == 0, Im[cauchyV] == 0}], {I1, I5, I2, I6}][[1]];
Print["S0d Cauchy relations give N2: ",
  Simplify[{I1 - (ct I3 + st I4), I5 - (st I3 - ct I4), I2 - st I3, I6 - st I4} /. sol]];

(* S0e. Theorem 1 assembly *)
Clear[F, Fp];
n2 = {I1 -> ct I3 + st I4, I5 -> st I3 - ct I4, I2 -> st I3, I6 -> st I4};
nn1 = {I3 -> Pi^2 Fp/(2 st), I4 -> Pi^2 F/(2 st)};
X1 = I5^2 + 2 st I1 I4 - I4^2; X2 = I4^2 + 2 I2 I5 - I5^2; XK = st I1 I4 + I2 I5;
Print["S0e X1 - s^2(I3^2+I4^2) under N2: ", Simplify[(X1 - st^2 (I3^2 + I4^2)) /. n2]];
Print["S0e X2 - X1 under N2 (the two Stokes evaluations agree): ", Simplify[(X2 - X1) /. n2]];
Print["S0e (X1+X2)/2 - (s I1 I4 + I2 I5) identically (KLT form): ", Simplify[(X1 + X2)/2 - XK]];
Print["S0e J = (4/pi^2) X1 -> pi^2(F^2+F'^2): ", Simplify[((4/Pi^2) X1 /. n2 /. nn1) - Pi^2 (F^2 + Fp^2)]];
Print["S0e also (4/pi^2)(I2^2+I6^2): ", Simplify[((4/Pi^2) (I2^2 + I6^2) /. n2 /. nn1) - Pi^2 (F^2 + Fp^2)]];
(* N1: E(1-tau,tau) and E(tau,1-tau) *)
Print["S0e N1 Beta(tau,1-tau) = pi/sin(pi tau): ", FullSimplify[Beta[tau, 1 - tau] - Pi/Sin[Pi tau], 0 < tau < 1]];

(* S0f. changes of variables for the four edge integrals (abstract K):
   p: x = -w/(1-w), with K(x) = (1-x)^(-1/2) K(w);  q: x = 1 - 1/w, K(1/(1-x)) = K(w);
   r: x = 1/w, K(1/x) = K(w);  s: x = 1/w, K(1-1/x) = K(1-w).  Each should give the Euler integrand. *)
Clear[w];
asw = 0 < w < 1 && 0 < tau < 1;
xp = -w/(1 - w);
Print["S0f p dx -> w^(-1/2)(1-w)^(-tau) K(w) dw (x decreasing in w): ",
  FullSimplify[(-((-xp)^(-1/2) (1 - xp)^(tau - 1) (1 - xp)^(-1/2) KK[w] D[xp, w])) - w^(-1/2) (1 - w)^(-tau) KK[w], asw]];
xq = 1 - 1/w;
Print["S0f q dx -> w^(-tau)(1-w)^(-1/2) K(w) dw: ",
  FullSimplify[((-xq)^(-1/2) (1 - xq)^(tau - 3/2) KK[w] D[xq, w]) - w^(-tau) (1 - w)^(-1/2) KK[w], asw]];
xr = 1/w;
Print["S0f r dx -> w^(-tau)(1-w)^(tau-1) K(w) dw: ",
  FullSimplify[(-(xr^-1 (xr - 1)^(tau - 1) KK[w] D[xr, w])) - w^(-tau) (1 - w)^(tau - 1) KK[w], asw]];
Print["S0f s dx -> w^(-tau)(1-w)^(tau-1) K(1-w) dw: ",
  FullSimplify[(-(xr^-1 (xr - 1)^(tau - 1) KK[1 - w] D[xr, w])) - w^(-tau) (1 - w)^(tau - 1) KK[1 - w], asw]];
Print["S0f  (q: 1/(1-x) at x = 1-1/w equals w): ", Simplify[1/(1 - xq) - w], "   (p: x/(x-1) at x=-w/(1-w) equals w): ", Simplify[xp/(xp - 1) - w]];

(* ================= S1. Route A residues (unchanged) ================= *)
reflect = {Gamma[z_] :> Pi/(Sin[Pi z] Gamma[1 - z])};
Clear[n, u];
lhs1 = Gamma[-n - u]^2 Gamma[1/2 - n - tau - u]/Gamma[1/2 - n - u]^3;
rhs1 = Cos[Pi u]^3/(Sin[Pi u]^2 Cos[Pi (tau + u)]) Gamma[n + 1/2 + u]^3/(Gamma[n + 1 + u]^2 Gamma[n + 1/2 + tau + u]);
Print["S1 family-1 n-part identity (ratio) : ", FullSimplify[(lhs1 /. reflect)/rhs1, Assumptions -> Element[n, Integers] && n >= 0]];
res1 = SeriesCoefficient[Cos[Pi u]^3/(Sin[Pi u]^2 Cos[Pi (tau + u)]) hh[u], {u, 0, -1}];
target1 = (1/Pi^2) (Pi Sin[Pi tau]/Cos[Pi tau]^2 hh[0] + hh'[0]/Cos[Pi tau]);
Print["S1 family-1 residue formula        : ", FullSimplify[res1 - target1]];
lhs2b = Gamma[tau - 1/2 - n]^2/Gamma[tau - n]^3;
rhs2b = (-1)^n Sin[Pi tau]^3/(Pi Cos[Pi tau]^2) Gamma[n + 1 - tau]^3/Gamma[n + 3/2 - tau]^2;
Print["S1 family-2 n-part identity (ratio) : ", FullSimplify[(lhs2b /. reflect)/rhs2b, Assumptions -> Element[n, Integers] && n >= 0]];
Print["S1 Res Gamma(-n-u) at n=0..4       : ", Table[Residue[Gamma[-nn - u], {u, 0}] + (-1)^nn/nn!, {nn, 0, 4}]];
(* Omega = G T factorization used in A2 *)
Clear[a, b, sx];
OmegaDirect = Gamma[a + sx]^3 Gamma[a - sx]^2 Gamma[a + 1/2 - tau - sx]/(Gamma[a + 1/2 + sx]^2 Gamma[a + 1/2 - sx]^3 Gamma[a + tau + sx]);
GG = (Gamma[a + sx] Gamma[1 - (a + 1/2) + sx]/(Gamma[a + 1/2 + sx] Gamma[1 - a + sx]))^2 Gamma[a + sx] Gamma[1 - (a + 1/2) + sx]/(Gamma[a + tau + sx] Gamma[1 - (a + 1/2) + tau + sx]);
TT = Cot[Pi (a - sx)]^2 Cos[Pi (a - sx)]/Sin[Pi (a + 1/2 - tau - sx)];
Print["S1 A2: Omega/(G T) at random point = ", N[(OmegaDirect/(GG TT)) /. {a -> 7/4, tau -> 3/10, sx -> 1/3 + 2 I/7}, 30]];
Print["S1 A2: Omega/(G T) symbolic        = ",
  FullSimplify[FunctionExpand[(OmegaDirect /. {Gamma[a - sx] -> Pi/(Sin[Pi (a - sx)] Gamma[1 - a + sx]),
        Gamma[a + 1/2 - tau - sx] -> Pi/(Sin[Pi (a + 1/2 - tau - sx)] Gamma[1/2 - a + tau + sx]),
        Gamma[a + 1/2 - sx] -> Pi/(Sin[Pi (a + 1/2 - sx)] Gamma[1/2 - a + sx])})/(GG TT)]]];

(* ================= S2. Route A collapse (unchanged) ================= *)
SS = Sin[Pi tau]; CC = Cos[Pi tau];
H0 = Pi^2/Gamma[tau] (F + CC/SS Fp); H1 = -Pi^3/Gamma[tau] Fp; K0 = Gamma[tau] Gamma[1 - tau]^2 F;
JA = Gamma[tau]/Gamma[1 - tau] (-(1/Pi^2) (Pi SS/CC^2 H0^2 + (2/CC) H0 H1) + SS^3/(Pi CC^2) K0^2);
Print["S2 (A.3) - Pi^2(F^2+Fp^2)          : ", FullSimplify[(JA /. Gamma[1 - tau] -> Pi/(Sin[Pi tau] Gamma[tau])) - Pi^2 (F^2 + Fp^2)]];

(* ================= S3. Laurent extraction (Theorem 2) ================= *)
Clear[u, v, w3, x4, sg, tg, g5, g6];
Fser = 1 + u tau + v tau^2 + w3 tau^3 + x4 tau^4 + O[tau]^5;
Gser = 1 + sg tau^3 + tg tau^4 + g5 tau^5 + g6 tau^6 + O[tau]^7;
Fmser = Series[Gamma[tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2), {tau, 0, 5}] Gser;   (* F(1-tau) by Thomae *)
Jser = Pi^2 (Fser^2 + Fmser^2);
Bd[d_, a_, b_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
JG[t_] := Bd[2, 1, 2 - t]^2 + (2/t) (Bd[2, 1, 2 - t] - Bd[2, 1 + 2 t, 2 - t]);
diff = Jser - Series[JG[2 tau], {tau, 0, 2}];
cf = Table[Simplify[FunctionExpand[SeriesCoefficient[diff, k]]], {k, -2, 2}];
Print["S3 [tau^-2..tau^2] of J - J^Gamma (raw):"];
Do[Print["    k=", k - 3, ": ", cf[[k]]], {k, 1, 5}];
vals = {u -> 4 Log[2] - 8 Catalan/Pi, sg -> 8 Pi Catalan - 14 Zeta[3], tg -> Pi^2 u^2/2 - Pi^4/6 - Pi^2 v};
cf2 = Table[FullSimplify[(cf[[k]] /. vals) /. vals], {k, 1, 5}];
Print["S3 after u, sigma, elimination rule:"];
Do[Print["    k=", k - 3, ": ", cf2[[k]]], {k, 1, 5}];
K2 = FullSimplify[cf2[[5]]/4];
Print["S3 K2 = [t^2](J - J^Gamma) = ", K2];
Print["S3 K2 - (32 G^2 - 28 zeta3 log2) = ", FullSimplify[K2 - (32 Catalan^2 - 28 Zeta[3] Log[2])]];
Print["S3 uniform form check: ", FullSimplify[K2 - (1/2) ((PolyGamma[1, 1/4] - PolyGamma[1, 3/4])^2/4 + 4 Log[2] PolyGamma[2, 1/2])]];
K2num = N[K2, 70];
Print["S3 K2 (70 significant digits) = ", NumberForm[K2num, 70]];
c62d = 3.5181091385902522416490901703077395226226728094710360690845577954`70;
Print["S3 C62d 64-decimal value     = ", NumberForm[c62d, 65]];
Print["S3 |K2 - C62d| = ", ScientificForm[N[Abs[K2num - c62d], 3]], "   (C62d value has 64 decimals, so <= 5e-65 is full agreement)"];
(* the C5(2) line after inserting K2 *)
Clear[P5, P4, L2, Q2, aL];
lhsC5 = (-1536 (P5 + K2s) + 1536 aL P4 - 576 L2 - 1728 Q2^2 + (11520 aL^2 + 28608 Catalan) Q2 - 3840 aL^4 - 21456 aL Zeta[3])/48 /. K2s -> 32 Catalan^2 - 28 Zeta[3] aL;
rhsC5 = -32 P5 + 32 aL P4 - 12 L2 - 36 Q2^2 + (240 aL^2 + 596 Catalan) Q2 - 80 aL^4 - 1024 Catalan^2 + 449 aL Zeta[3];
Print["S3 972 C5(2) line: ", Simplify[lhsC5 - rhsC5]];
Print["=== done ==="];
Quiet@CloseKernels[]; Exit[0];
