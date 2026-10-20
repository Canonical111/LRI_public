(* Machine check (q=1/2) of the note's residue proof of gs:Kseries from gs:Kholomorphic:
   (i)  Res_{s=a+n} [g(s)^2 F(s)/4] = T_{ln}^2 R_{ln}/4   (so the negative residue is -T^2 R/4)
   (ii) Res_{s=b+n} [g(s)^2 F(s)/4] = -M^2 S_{ln}^2/8 = -2 E_m E_n.
   Symbols: Pm[j]=psi_j(m+1/2), Qm[j]=psi_j(m+1), Pn[j], Qn[j]; u = s - (pole). *)
ClearAll["Global`*"];
J = 5;
ser[f_] := Series[f, {u, 0, J}];
psiShift[P_, k_] := Sum[P[k + j] u^j/j!, {j, 0, J}];      (* psi_k(K+u) expanded *)
(* ---------- family (i): s = a+n+u ---------- *)
logc[P_, Q_] := Sum[(P[j - 1] - Q[j - 1]) u^j/j!, {j, 1, J + 1}];   (* log c(K+u) - log c(K) *)
gfac = -Pi Cot[Pi u];      (* g = gfac * c(m+u) c(n+u); c(m)c(n) = T *)
lg = Log[-Cot[Pi u]] + logc[Pm, Qm] + logc[Pn, Qn];   (* log g up to the constant log T *)
ell = D[lg, u];
p = (psiShift[Pm, 0] + (psiShift[Qn, 0] + Pi Cot[Pi u]) + psiShift[Qm, 0] + (psiShift[Pn, 0] - Pi Tan[Pi u]))/2;
cs = 2 PolyGamma[0, 1];
F = (cs - p) (ell^2/8 - 5 D[ell, u]/16) + ell D[p, u]/4 - 5 D[p, {u, 2}]/32;
g2overT2 = (gfac)^2 Exp[2 (logc[Pm, Qm] + logc[Pn, Qn])];
resA = SeriesCoefficient[Series[g2overT2 F/4, {u, 0, 1}], -1];
(* gs:Kpoly at q=1/2 *)
ph[j_] := PolyGamma[j, 1/2]; p1[j_] := PolyGamma[j, 1];
lam[j_] := (Pm[j - 1] - Qm[j - 1]) + (Pn[j - 1] - Qn[j - 1]) + (1 + (-1)^j) (p1[j - 1] - ph[j - 1]);
r[j_] := lam[j + 1]/2 + Qm[j] + Qn[j] - (1 - (-1)^j) p1[j];
{l1, l2, l3, l4} = lam /@ {1, 2, 3, 4};
Rpoly = (r[0] - cs)/2 (l1^3 + 3 l1 l2 + l3) + 3 r[1]/4 (l1^2 + l2) - (l1 r[2] + r[3])/4 - l1^4/12 + l1^2 l2/8 + 7 l1 l3/24 + l2^2/8 + l4/12;
diffA = Simplify[FunctionExpand[Expand[resA - Rpoly/4]]];
Print["family (i): Res[g^2F/4]/T^2 - R/4 = ", diffA];
(* ---------- family (ii): s = b+n+u ;  g = tan(pi u) * (4/pi) e(m+u) e(n+u), e(K)=Gamma(K+1)Gamma(3/2)/Gamma(K+3/2) ---------- *)
(* symbols: Am[j]=psi_j(m+1), Bm[j]=psi_j(m+3/2), An[j], Bn[j] *)
loge[A_, B_] := Sum[(A[j - 1] - B[j - 1]) u^j/j!, {j, 1, J + 1}];
lg2 = Log[Tan[Pi u]] + loge[Am, Bm] + loge[An, Bn];
ell2 = D[lg2, u];
(* a+s = m+1+u, b+s = m+3/2+u, a-s = -1/2-n-u, b-s = -n-u ;
   psi(-1/2-n-u) = psi(n+3/2+u) + pi cot(pi(1/2+n+u))... use reflection: psi(1-z)-psi(z)=pi cot(pi z), z=-1/2-n-u:
   psi(3/2+n+u) - psi(-1/2-n-u) = pi cot(pi(-1/2-n-u)) = pi tan(pi u)  -> psi(-1/2-n-u) = psi(n+3/2+u) - pi tan(pi u)
   psi(-n-u) = psi(n+1+u) + pi cot(pi u) *)
p2 = (psiShift[Am, 0] + (psiShift[Bn, 0] - Pi Tan[Pi u]) + psiShift[Bm, 0] + (psiShift[An, 0] + Pi Cot[Pi u]))/2;
F2 = (cs - p2) (ell2^2/8 - 5 D[ell2, u]/16) + ell2 D[p2, u]/4 - 5 D[p2, {u, 2}]/32;
g2overE = Tan[Pi u]^2 (16/Pi^2) Exp[2 (loge[Am, Bm] + loge[An, Bn])];  (* g^2/(E_m E_n) *)
resB = SeriesCoefficient[Series[g2overE F2/4, {u, 0, 1}], -1];
Print["family (ii): Res[g^2F/4]/(E_m E_n) = ", Simplify[resB], "   (expected -2)"];
(* sanity: check the reflection-derived local forms numerically at m=3,n=2 (l=1), u=0.0123 *)
Block[{mm = 3, nn = 2, uu = 123/10000, a, b, s, gdir, gloc},
  a = (mm - nn)/2 + 1/4; b = a + 1/2; s = a + nn + uu;
  gdir = Gamma[a + s] Gamma[a - s]/(Gamma[b + s] Gamma[b - s]);
  gloc = -Cot[Pi uu] Gamma[mm + 1/2 + uu] Gamma[nn + 1/2 + uu]/(Gamma[mm + 1 + uu] Gamma[nn + 1 + uu]);
  Print["local form (i) check: ", N[{gdir, gloc}, 15]];
  s = b + nn + uu;
  gdir = Gamma[a + s] Gamma[a - s]/(Gamma[b + s] Gamma[b - s]);
  gloc = Tan[Pi uu] Gamma[mm + 1 + uu] Gamma[nn + 1 + uu]/(Gamma[mm + 3/2 + uu] Gamma[nn + 3/2 + uu]);
  Print["local form (ii) check: ", N[{gdir, gloc}, 15]]];

Quiet@CloseKernels[];
Exit[0];
