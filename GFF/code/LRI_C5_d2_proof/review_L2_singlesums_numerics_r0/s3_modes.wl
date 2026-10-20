(* Lemmas 1.1, 1.2, 1.3, 2, 3, 4 and Prop. 4.1, independently in Mathematica, at the generic point x=9/20 and at x=1/2. *)
Get["em.wl"];
res = <||>; add[name_, v_] := (res[name] = v; Print[StringPadRight[name, 84], " ", ScientificForm[N[v, 4]]]);
sv = Get["s1_values.m"]; {a, b, Sy, Sxy, L2note, P4note} = {sv["a"], sv["b"], sv["Sy"], sv["Sxy"], sv["L2note"], sv["P4note"]};
Nx[x_] := Gamma[1 - x]/Gamma[x];
Cj[1, x_] := Pi Cot[Pi x]; Cj[2, x_] := Pi^2/3 - Pi^2/Sin[Pi x]^2; Cj[3, x_] := 2 Pi^3 Cos[Pi x]/Sin[Pi x]^3;
Xj[j_, k_, x_] := PolyGamma[j - 1, k + x] - PolyGamma[j - 1, k + 1];
ck[k_, x_] := Pochhammer[x, k]/k!;
F4p[l1_, l2_, l3_] := 32/3 l1^3 + 8 l1 l2 + 2/3 l3;
(* ---- C_j as series coefficients, exact *)
Module[{ser = Series[Log[Pi u/Sin[Pi u]] + Log[Sin[Pi (x + u)]/Sin[Pi x]], {u, 0, 3}]},
  Do[add["C_" <> ToString[j] <> "(x) closed form (symbolic, Simplify -> 0?)", If[Simplify[SeriesCoefficient[ser, j] j! - Cj[j, x]] === 0, 0, 1]], {j, 1, 3}]];
(* ---- Lemma 1.1 at x = 9/20, (m,n) = (3,5) and (0,2) : residue of G^4 vs T^4 F4 *)
Do[Module[{x = 9/20, m = mn[[1]], n = mn[[2]], G, resid, T, lam},
   G = Nx[x] Sin[Pi (x + u)]/Sin[Pi u] Gamma[m + u + x]/Gamma[m + u + 1] Gamma[n + u + x]/Gamma[n + u + 1];
   resid = SeriesCoefficient[Series[G^4, {u, 0, -1}], -1];
   T = ck[m, x] ck[n, x]; lam = Table[Xj[j, m, x] + Xj[j, n, x] + Cj[j, x], {j, 3}];
   add["Lemma 1.1 Res G^4 - T^4 F4 at x=9/20, (m,n)=" <> ToString[mn], N[resid - T^4 F4p @@ lam, 80]]], {mn, {{3, 5}, {0, 2}}}];
(* ---- Lemma 1.2: note-literal L-summand vs (1/2) d/dx [T(x)^4 F4(x)] at x=1/2 *)
q = 1/2;
chi[j_, n_] := (-1)^j PolyGamma[j, n + 1 - q] + PolyGamma[j, q] - (-1)^j PolyGamma[j, 1 - q];
lamN[mm_, l_, n_] := PolyGamma[mm - 1, l + n + q] - PolyGamma[mm - 1, l + n + 2 q] - (-1)^mm chi[mm - 1, n] + (1 + (-1)^mm) PolyGamma[mm - 1, 1] - PolyGamma[mm - 1, n + 1];
etaN[mm_, l_, n_] := 1/2 (PolyGamma[mm, l + n + q] + (-1)^mm chi[mm, n]);
mu1N[l_, n_] := 1/2 (PolyGamma[0, l + n + q] - PolyGamma[0, q] + PolyGamma[0, n + 1 - q] - PolyGamma[0, 1 - q]);
TN[l_, n_] := Pochhammer[q, l + n] Pochhammer[1 - q, n]/(Pochhammer[2 q, l + n] n!);
Do[Module[{l = ln[[1]], n = ln[[2]], m, F4n, F41n, lhs, rhs, xx},
   m = l + n;
   F4n = F4p[lamN[1, l, n], lamN[2, l, n], lamN[3, l, n]];
   F41n = 32 lamN[1, l, n]^2 etaN[1, l, n] + 8 etaN[1, l, n] lamN[2, l, n] + 8 lamN[1, l, n] etaN[2, l, n] + 2/3 etaN[3, l, n];
   lhs = TN[l, n]^4 (4 mu1N[l, n] F4n + F41n);
   rhs = 1/2 D[(ck[m, xx] ck[n, xx])^4 F4p @@ Table[Xj[j, m, xx] + Xj[j, n, xx] + Cj[j, xx], {j, 3}], xx] /. xx -> 1/2;
   add["Lemma 1.2 L-summand - (1/2)d_x[T^4F4] at (l,n)=" <> ToString[ln], N[lhs - rhs, 80]];
   add["Lemma 1.2 P-summand T^4F4(note) - T^4F4(x=1/2) at (l,n)=" <> ToString[ln], N[TN[l, n]^4 F4n - ((ck[m, 1/2] ck[n, 1/2])^4 F4p @@ Table[Xj[j, m, 1/2] + Xj[j, n, 1/2] + Cj[j, 1/2], {j, 3}]), 80]]], {ln, {{0, 0}, {2, 3}, {5, 1}}}];
(* ---- single sums at general x, and W(x) as the factorised square-lattice double sum *)
sx[x_, wt_] := re@emsum[Function[k, Exp[4 (LogGamma[k + x] - LogGamma[x] - LogGamma[k + 1])] wt[k]]];
Wdouble[x_] := Module[{s, X1, X2, X3, cc = Table[N[Cj[j, x], $wp], {j, 3}], poly, rules, vars},
   (* F4 with lambda_j = u_j + v_j + C_j ; u from m, v from n *)
   poly = Expand[F4p[u1 + v1 + cc[[1]], u2 + v2 + cc[[2]], u3 + v3 + cc[[3]]]];
   s[e_] := s[e] = sx[x, Function[k, Xj[1, k, x]^e[[1]] Xj[2, k, x]^e[[2]] Xj[3, k, x]^e[[3]]]];
   rules = CoefficientRules[poly, {u1, u2, u3, v1, v2, v3}];
   -Total[(#[[2]] s[#[[1, 1 ;; 3]]] s[#[[1, 4 ;; 6]]]) & /@ rules]];
(* ---- Omega and the two modes *)
S1[t_, x_] := re@emsum[Function[n, Exp[4 (LogGamma[n + x + t] - LogGamma[n + 1 + t])]]];
S2[t_, x_] := re@emsum[Function[j, Exp[4 (LogGamma[j + 1 - t] - LogGamma[j + 2 - x - t])]]];
Om[t_, x_] := Sin[Pi (t + x)]^4 S1[t, x] + Sin[Pi t]^4 S2[t, x];
x0 = 9/20; xn = N[x0, $wp];
ta = N[13/100, $wp]; tb = N[71/100, $wp];
Oa = Om[ta, xn]; Ob = Om[tb, xn];
{Ax, Bx} = LinearSolve[{{1, Cos[2 Pi (ta + xn/2)]}, {1, Cos[2 Pi (tb + xn/2)]}}, {Oa, Ob}];
Do[add["Lemma 2(iii) two modes at x=9/20, t=" <> ToString[tt], Om[N[tt, $wp], xn] - (Ax + Bx Cos[2 Pi (N[tt, $wp] + xn/2)])], {tt, {-31/100, 1/2 - 9/40, 2/10 + 7/10 I}}];
add["Lemma 2(i) periodicity Omega(t+1)-Omega(t), t=0.13, x=9/20", Om[ta + 1, xn] - Oa];
add["Lemma 2(i) reflection Omega(-x-t)-Omega(t), t=0.13, x=9/20", Om[-xn - ta, xn] - Oa];
Print["A(9/20) = ", N[Ax, 40], "   B(9/20) = ", N[Bx, 40]];
(* ---- Lemma 3: rho_p symbolic residues *)
rhoC = {-4 (Cos[2 Pi x] + 4) Cos[Pi x]/(Pi Sin[Pi x]^7), 4 (4 Sin[Pi x]^2 - 5)/(Pi Sin[Pi x]^7), 4 (Sin[Pi x]^2 - 5) Cos[Pi x]/(Pi Sin[Pi x]^7)};
Do[Module[{r = Residue[Cos[2 Pi u + Pi x]^p/(Sin[Pi u]^4 Sin[Pi (u + x)]^4), {u, 0}]},
   add["Lemma 3 rho_" <> ToString[p] <> " symbolic residue - closed form at x=9/20 and x=1/3 (max)", Max[Abs[N[(r - rhoC[[p + 1]]) /. x -> 9/20, 60]], Abs[N[(r - rhoC[[p + 1]]) /. x -> 1/3, 60]]]]], {p, 0, 2}];
add["rho at 1/2: rho0, rho2, rho1+4/pi", Max[Abs[N[{rhoC[[1]], rhoC[[3]], rhoC[[2]] + 4/Pi} /. x -> 1/2, 50]]]];
add["rho' at 1/2: rho0'-12, rho1', rho2'-16", Max[Abs[N[(D[rhoC, x] - {12, 0, 16}) /. x -> 1/2, 50]]]];
rho9 = N[rhoC /. x -> x0, $wp]; n2 = N[Nx[x0]^2, $wp];
W2mode = -(rho9[[1]] (n2 Ax)^2 + 2 rho9[[2]] n2^2 Ax Bx + rho9[[3]] (n2 Bx)^2);
Wd9 = Wdouble[xn];
add["Lemma 1.3+3: W(9/20) double sum - two-mode residue form", Wd9 - W2mode];
(* Lemma 1.3 residue of one-sided data: h^(j)(0;x) by termwise u-derivatives *)
hj[x_, j_] := Module[{ex = D[Exp[4 (LogGamma[kk + uu + x] - LogGamma[kk + uu + 1])], {uu, j}] /. uu -> 0},
   re@emsum[Function[kk2, Evaluate[ex /. kk -> kk2]]]];
hs = Table[hj[xn, j], {j, 0, 3}];
Wres = -n2^2 SeriesCoefficient[Series[Sin[Pi (xn + u)]^4 (Sum[hs[[j + 1]] u^j/j!, {j, 0, 3}])^2/Sin[Pi u]^4, {u, 0, -1}], -1];
add["Lemma 1.3: W(9/20) double sum - (-N^4 Res sin^4 pi(x+u) h^2/sin^4 pi u)", Wd9 - Wres];
(* ---- Lemma 4 (4.1),(4.2) at x=9/20 *)
add["(4.1) at x=9/20: N^2 sin^4 h(0) - (Ah + Bh cos pi x)", n2 Sin[Pi xn]^4 hs[[1]] - n2 (Ax + Bx Cos[Pi xn])];
add["(4.2) at x=9/20: N^2[4pi sin^3 cos h + sin^4 h_u] + 2pi Bh sin", n2 (4 Pi Sin[Pi xn]^3 Cos[Pi xn] hs[[1]] + Sin[Pi xn]^4 hs[[2]]) + 2 Pi n2 Bx Sin[Pi xn]];
(* ---- Lemma 4 at x=1/2, A', B' from termwise x-derivative of Omega at generic t (no use of h at u=0) *)
xh = N[1/2, $wp];
S1x[t_, x_] := re@emsum[Function[n, 4 Exp[4 (LogGamma[n + x + t] - LogGamma[n + 1 + t])] PolyGamma[n + x + t]]];
S2x[t_, x_] := re@emsum[Function[j, 4 Exp[4 (LogGamma[j + 1 - t] - LogGamma[j + 2 - x - t])] PolyGamma[j + 2 - x - t]]];
Omx[t_, x_] := 4 Pi Cos[Pi (t + x)] Sin[Pi (t + x)]^3 S1[t, x] + Sin[Pi (t + x)]^4 S1x[t, x] + Sin[Pi t]^4 S2x[t, x];
{A5, B5} = LinearSolve[{{1, Cos[2 Pi (ta + xh/2)]}, {1, Cos[2 Pi (tb + xh/2)]}}, {Om[ta, xh], Om[tb, xh]}];
add["x=1/2: A - pi^2 a (Lemma 4, N=1)", A5 - Pi^2 a]; add["x=1/2: B - pi^2 b", B5 - Pi^2 b];
{Ap5, Bp5} = LinearSolve[{{1, Cos[2 Pi (ta + xh/2)]}, {1, Cos[2 Pi (tb + xh/2)]}},
   {Omx[ta, xh] + Pi B5 Sin[2 Pi ta + Pi xh], Omx[tb, xh] + Pi B5 Sin[2 Pi tb + Pi xh]}];
tc = N[3/10 + 2/10 I, $wp];
add["check d_x Omega two-mode form at complex t=0.3+0.2i", Omx[tc, xh] - (Ap5 + Bp5 Cos[2 Pi tc + Pi xh] - Pi B5 Sin[2 Pi tc + Pi xh])];
dn2 = N[D[Nx[x]^2, x] /. x -> 1/2, $wp];
Ahp = dn2 A5 + Ap5; Bhp = dn2 B5 + Bp5;
add["Lemma 4: Ah'(1/2) - (pi Bh + 4pi^2 Sy)", Ahp - (Pi B5 + 4 Pi^2 Sy)];
add["Lemma 4: Bh'(1/2) - (2pi^3 a - 2pi Sxy)", Bhp - (2 Pi^3 a - 2 Pi Sxy)];
add["Lemma 3 at 1/2: W(1/2)=8AhBh/pi vs P4note", 8 A5 B5/Pi - P4note];
add["Prop 4.1 chain: (1/2)[-12Ah^2-16Bh^2+(8/pi)(Ah'Bh+AhBh')] - L2note", 1/2 (-12 A5^2 - 16 B5^2 + 8/Pi (Ahp B5 + A5 Bhp)) - L2note];
add["Equivalent form: Ah'(1/2) - (2pi bn - 2log2 an), an=Ah(1/2), bn=Bh(1/2)", Ahp - (2 Pi B5 - 2 Log[2] A5)];
add["Equivalent form: Bh'(1/2) - (3pi/2 an - 2log2 bn)", Bhp - (3 Pi/2 A5 - 2 Log[2] B5)];
(* ---- L2 = (1/2) W'(1/2), W' by Cauchy's formula on |x-1/2|=1/50, 48 points *)
Pc = 48; rc = 1/50;
Wc = Table[Wdouble[N[1/2 + rc Exp[2 Pi I p/Pc], $wp]], {p, 0, Pc - 1}];
Wp = Total[Wc Table[Exp[-2 Pi I p/Pc], {p, 0, Pc - 1}]]/(Pc rc);
W0c = Total[Wc]/Pc;
add["W(1/2) [Cauchy mean] - P4note", W0c - P4note];
add["L2note - (1/2) W'(1/2) [Cauchy, 48 pts r=1/50; aliasing ~ (r/(1/4))^48 ~ 1e-53]", L2note - Wp/2];
Put[Map[ToString[ScientificForm[N[#, 4]]] &, res], "s3_residuals.m"];
Print["done"];
