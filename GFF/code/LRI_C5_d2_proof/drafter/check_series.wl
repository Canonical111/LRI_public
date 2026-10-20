(* Drafter's analytic-series and numerical checks for note_insert.tex (Mathematica 15).
   Exact parts: rho_p residues, C_j(x), Gamma series (log Q^2, J^Gamma), note constants at q=1/2.
   Numerical parts (not proof steps): generating functions, elliptic moments, moment relations,
   closed forms vs C62d's 70-digit strings, C5(2) via the simplified formula. *)
pr[s_, e_] := Print[s, ": ", e];

(* ---- rho_p ---- *)
rhoClosed = {-4 (Cos[2 Pi x] + 4) Cos[Pi x]/(Pi Sin[Pi x]^7),
   4 (4 Sin[Pi x]^2 - 5)/(Pi Sin[Pi x]^7),
   4 (Sin[Pi x]^2 - 5) Cos[Pi x]/(Pi Sin[Pi x]^7)};
Do[
  r = Residue[Cos[2 Pi u + Pi x]^p/(Sin[Pi u]^4 Sin[Pi (u + x)]^4), {u, 0}];
  pr["rho_" <> ToString[p] <> " - closed form", FullSimplify[TrigReduce[r - rhoClosed[[p + 1]]]]],
  {p, 0, 2}];

(* ---- C_j(x) and the note's constants at q = 1/2 ---- *)
cser = Series[Log[Pi u/Sin[Pi u]] + Log[Sin[Pi (x + u)]/Sin[Pi x]], {u, 0, 3}];
Cj = Table[SeriesCoefficient[cser, j] j!, {j, 1, 3}];
pr["C_j(x)", FullSimplify[Cj]];
pr["C_j(1/2) - (1+(-1)^j)(psi_{j-1}(1)-psi_{j-1}(1/2))",
  FullSimplify[Table[(Cj[[j]] /. x -> 1/2) - (1 + (-1)^j) (PolyGamma[j - 1, 1] - PolyGamma[j - 1, 1/2]), {j, 1, 3}]]];
pr["(1/2)C_j'(1/2) - (1/2)((-1)^j-1)psi_j(1/2)",
  FullSimplify[Table[(D[Cj[[j]], x] /. x -> 1/2)/2 - ((-1)^j - 1) PolyGamma[j, 1/2]/2, {j, 1, 3}]]];
(* note's lambda_j and eta_j at q=1/2 vs general-x data, symbolic m,n *)
q = 1/2;
chi[mm_, n_] := (-1)^mm PolyGamma[mm, n + 1 - q] + PolyGamma[mm, q] - (-1)^mm PolyGamma[mm, 1 - q];
lamNote[j_, m_, n_] := PolyGamma[j - 1, m + q] - PolyGamma[j - 1, m + 2 q] - (-1)^j chi[j - 1, n] +
   (1 + (-1)^j) PolyGamma[j - 1, 1] - PolyGamma[j - 1, n + 1];
etaNote[j_, m_, n_] := (PolyGamma[j, m + q] + (-1)^j chi[j, n])/2;
mu1Note[m_, n_] := (PolyGamma[0, m + q] - PolyGamma[0, q] + PolyGamma[0, n + 1 - q] - PolyGamma[0, 1 - q])/2;
X[j_, k_, xx_] := PolyGamma[j - 1, k + xx] - PolyGamma[j - 1, k + 1];
lamGen[j_, m_, n_, xx_] := X[j, m, xx] + X[j, n, xx] + Cj[[j]] /. x -> xx;
pr["lambda_j(1/2) general - note (m=7/3? symbolic m,n)",
  FullSimplify[Table[lamGen[j, m, n, 1/2] - lamNote[j, m, n], {j, 1, 3}]]];
pr["(1/2)d_x lambda_j at 1/2 - eta_j",
  FullSimplify[Table[(D[lamGen[j, m, n, xx], xx] /. xx -> 1/2)/2 - etaNote[j, m, n], {j, 1, 3}]]];
logT[m_, n_, xx_] := LogGamma[m + xx] - LogGamma[xx] - LogGamma[m + 1] + LogGamma[n + xx] - LogGamma[xx] - LogGamma[n + 1];
pr["(1/2)d_x log T at 1/2 - mu1", FullSimplify[(D[logT[m, n, xx], xx] /. xx -> 1/2)/2 - mu1Note[m, n]]];
pr["T(1/2) - T_{l n}(q=1/2)", FullSimplify[(Gamma[m + 1/2] Gamma[n + 1/2]/(Gamma[1/2]^2 m! n!)) -
     Pochhammer[q, m] Pochhammer[1 - q, n]/(Pochhammer[2 q, m] n!), Element[{m, n}, NonNegativeIntegers]]];

(* ---- Gamma series for K2 ---- *)
Qt = Pi Gamma[1 + t]/(Gamma[1 - t] Gamma[1/2 + t]^2);
pr["log Q^2 series - claim", FullSimplify[Normal[Series[2 Log[Qt], {t, 0, 4}]] -
    (8 Log[2] t - Pi^2 t^2 + 8 Zeta[3] t^3 - Pi^4 t^4/6)]];
Bc = Gamma[t] Gamma[1/2 - t]/(Gamma[1 - t] Gamma[1/2 + t]);
Bt = Gamma[1/2 - 2 t] Gamma[t] Gamma[1/2 + t]/(Gamma[1/2 + 2 t] Gamma[1 - t] Gamma[1/2 - t]);
(* gs:convolution at d=2 *)
B2[aa_, bb_] := Gamma[1 - aa/2] Gamma[1 - bb/2] Gamma[(aa + bb)/2 - 1]/(Gamma[aa/2] Gamma[bb/2] Gamma[2 - (aa + bb)/2]);
pr["B2(1,2-2t) - Bc", FullSimplify[B2[1, 2 - 2 t] - Bc]];
pr["B2(1+4t,2-2t) - Bt", FullSimplify[B2[1 + 4 t, 2 - 2 t] - Bt]];
JG = Bc^2 + (Bc - Bt)/t;
pr["J^Gamma series - claim", FullSimplify[Normal[Series[JG, {t, 0, 2}]] -
    Normal[Series[Exp[8 Log[2] t]/t^2, {t, 0, 2}]] + 20 Zeta[3] t + 48 Log[2] Zeta[3] t^2]];
(* note's general [t^2]J^Gamma at q=1/2 times 4 = [tau^2] *)
Ad = 4 Log[2]; Rd = 0; Ud = PolyGamma[2, 1/2]; Vd = PolyGamma[2, 1] + PolyGamma[2, 1]; Xd = 0;
pr["4*(note [t^2]J^Gamma at q=1/2) - (512/3 log^4 2 - 48 log2 zeta3)",
  FullSimplify[4 (Ad^4/6 - Ad^2 Rd/2 + Rd^2/8 + Ad (Vd + Ud)/6 - Xd/48) - (512/3 Log[2]^4 - 48 Log[2] Zeta[3])]];
pr["U(1/2) = -14 zeta3", FullSimplify[Ud + 14 Zeta[3]]];

(* ---- numerics (not proof steps) ---- *)
$MaxExtraPrecision = 200;
wp = 50;
Kp[m_] := EllipticK[m];            (* parameter convention: K(m) *)
f[k_] := EllipticK[k^2]; g[k_] := EllipticK[1 - k^2];
c2[n_] := (Pochhammer[1/2, n]/n!)^2;
alpha[n_] := PolyGamma[n + 1/2] - PolyGamma[n + 1];
beta[n_] := PolyGamma[n + 1/2] - PolyGamma[1/2];
kk = 37/100;
G1 = NSum[c2[n] alpha[n] kk^(2 n), {n, 0, Infinity}, WorkingPrecision -> wp] - (-g[kk] - 2/Pi f[kk] Log[kk]);
G2 = NSum[c2[n] beta[n] kk^(2 n), {n, 0, Infinity}, WorkingPrecision -> wp] - (-2/Pi f[kk] Log[Sqrt[1 - kk^2]]);
G3 = NSum[c2[n] (4 alpha[n] beta[n] + 2 PolyGamma[1, n + 1/2]) kk^(2 n), {n, 0, Infinity}, WorkingPrecision -> wp] -
   (4 g[kk] Log[Sqrt[1 - kk^2]] + 2 Pi f[kk] + 8/Pi f[kk] Log[kk] Log[Sqrt[1 - kk^2]]);
pr["generating functions (G1,G2,G3) residuals at k=0.37", N[{G1, G2, G3}, 5]];
int[e_] := NIntegrate[e, {k, 0, 1/2, 1}, WorkingPrecision -> 40, PrecisionGoal -> 30, MaxRecursion -> 30];
Me = int[f[k]^2]; Ne = int[f[k] g[k]]; U0 = int[f[k]^2/Sqrt[1 - k^2]];
pr["U0 - 2N", N[U0 - 2 Ne, 5]];
pr["int g^2 log k + pi N", N[int[g[k]^2 Log[k]] + Pi Ne, 5]];
pr["int f g log k' + pi M/4 - log2 N/2", N[int[f[k] g[k] Log[Sqrt[1 - k^2]]] + Pi Me/4 - Log[2] Ne/2, 5]];
pr["int g^2 log k' - (log2 M - pi N/4)", N[int[g[k]^2 Log[Sqrt[1 - k^2]]] - (Log[2] Me - Pi Ne/4), 5]];
Fm = HypergeometricPFQ[{1/4, 1/4, 1/2, 1/2}, {3/4, 3/4, 1}, 1]; Fp = HypergeometricPFQ[{3/4, 3/4, 1/2, 1/2}, {5/4, 5/4, 1}, 1];
Bm = N[Gamma[1/4]^4 Fm, 90]; Bp = N[64 Pi^4/Gamma[1/4]^4 Fp, 90];
pr["M_e - (B-+B+)/64", N[Me - (Bm + Bp)/64, 5]]; pr["N_e - (B- - B+)/32", N[Ne - (Bm - Bp)/32, 5]];
P42 = (Bm^2 - Bp^2)/(4 Pi^3);
pr["P4(2)", N[P42, 60]];
L2c = -2 Log[2] P42; K2c = 32 Catalan^2 - 28 Zeta[3] Log[2];
L2C62d = -347.2491531232011310584767830752231692081676019948742708342016243405788`70;
K2C62d = 3.518109138590252241649090170307739522622672809471036069084557795421742`70;
pr["L2 closed", N[L2c, 60]]; pr["L2 closed - C62d", N[L2c - L2C62d, 5]];
pr["K2 closed", N[K2c, 60]]; pr["K2 closed - C62d", N[K2c - K2C62d, 5]];
(* moment relations and the master at tau = 3/10 by direct quadrature of the Euler moments *)
tv = 3/10;
E2[aa_, bb_] := NIntegrate[x^(aa - 1) (1 - x)^(bb - 1) Kp[x], {x, 0, 1/2, 1}, WorkingPrecision -> 40, PrecisionGoal -> 25, MaxRecursion -> 40];
Iv = {E2[1/2, tv], E2[tv, 1/2], E2[1 - tv, tv], E2[tv, 1 - tv], E2[1/2, 1 - tv], E2[1 - tv, 1/2]};
s = Sin[Pi tv]; c = Cos[Pi tv];
pr["moment relations residuals", N[{Iv[[1]] - (c Iv[[3]] + s Iv[[4]]), Iv[[5]] - (s Iv[[3]] - c Iv[[4]]),
     Iv[[2]] - s Iv[[3]], Iv[[6]] - s Iv[[4]]}, 5]];
qv = Exp[I Pi tv];
twelve = 4 (I Iv[[1]] Iv[[2]] - I qv Iv[[1]] Iv[[4]] - I Iv[[1]] Iv[[5]] + Iv[[1]] Iv[[6]] - I qv Iv[[2]] Iv[[3]] -
     qv Iv[[2]] Iv[[4]] + Iv[[2]] Iv[[5]] + I Iv[[3]] Iv[[4]] + I qv Iv[[3]] Iv[[5]] - qv Iv[[3]] Iv[[6]] +
     I qv Iv[[4]] Iv[[6]] + I Iv[[5]] Iv[[6]]);
FF[z_] := HypergeometricPFQ[{1/2, 1/2, z}, {1, 1}, 1];
Jclosed = Pi^2 (FF[tv]^2 + FF[1 - tv]^2);
pr["twelve-term form / pi^2 - closed form", N[twelve/Pi^2 - Jclosed, 5]];
pr["J_{2tau} closed at tau=3/10", N[Jclosed, 30]];
pr["J_1 = 3 Q2 check", FullSimplify[2 Pi^2 HypergeometricPFQ[{1/2, 1/2, 1/2}, {1, 1}, 1]^2 - 3 Gamma[1/4]^8/(24 Pi^4)]];
pr["J_1 = 3 Q2 numeric", N[2 Pi^2 FF[1/2]^2 - Gamma[1/4]^8/(8 Pi^4), 30]];
(* C5(2) end to end: P5(2) from fp:P5two with the five Y_r *)
Y[r_] := r/8 (Gamma[(r + 2)/8]/Gamma[(r + 6)/8])^7 HypergeometricPFQ[Join[{1, 1 + r/8}, Table[(r + 2)/8, 7]], Join[{r/8}, Table[(r + 6)/8, 7]], -1];
c8 = Cos[Pi/8]; s8 = Sin[Pi/8];
X0 = N[Y[2], 60]; Xp = N[c8^7 Y[3] - s8^7 Y[5], 60]; Xm = N[c8^7 Y[1] + s8^7 Y[7], 60];
P52 = 8/Pi (25 X0^2 - 28 Sqrt[2] X0 (Xp + Xm) + 18 (Xp^2 + Xm^2) + 28 Xp Xm);
P51 = 16 Pi^(3/2) (-35 X0 + (22 Sqrt[2] - 13) Xp + (22 Sqrt[2] + 13) Xm);
pr["P5(1) from eq:P5FixedAnswer (sanity)", N[P51, 30]];
pr["P5(2)", N[P52, 40]];
Q2v = Gamma[1/4]^8/(24 Pi^4);
lg = Log[2];
C52 = (-32 P52 + 56 lg P42 - 36 Q2v^2 + (240 lg^2 + 596 Catalan) Q2v - 1024 Catalan^2 + 449 Zeta[3] lg - 80 lg^4)/972;
C52orig = (-1536 (P52 + K2c) + 1536 lg P42 - 576 L2c - 1728 Q2v^2 + (11520 lg^2 + 28608 Catalan) Q2v - 3840 lg^4 - 21456 lg Zeta[3])/46656;
pr["C5(2) simplified formula", N[C52, 30]];
pr["C5(2) simplified - gc:d2coefficients", N[C52 - C52orig, 5]];
pr["C4(2) from gc:d2coefficients", N[(16 P42 - 64 lg^3 - 32 lg Q2v - 359 Zeta[3])/648, 20]];

Quiet@CloseKernels[];
Exit[0];
