# WINDOW_SPEC: the complete window scheme "W" for the 2D LRI level-truncated Hamiltonian, all orders through eps^8

Status: final (see `WINDOW_SPEC.READY`). Changelog at the end. Companion: `README.md` (derivation and eps^4 verification).

Everything not defined here is as in `../SPEC.md`: GFF on the unit circle, x = 1/2 - eps/4, modes (a,b),
w_ab(x) = (x)_a (x)_b/(a! b!), H0 = N + P x, M = <:phi^2:>_theta, V = <:phi^4:>_theta/12, J = 0 reflection-even
sectors, field parity conserved, level cutoff N <= l, primaries |p> = (A_00^dag)^p/sqrt(p!)|0> (p = 0..3), tuning
E_1 - E_0 = x and E_3 - E_0 = 2 - x at cutoff L, C_n = [eps^n](E_2 - E_0), one r(eps), g(eps) without eps^0 terms
(r_1 = 0, g_1 = 1/3) for every Hamiltonian.

## 0. Purpose and status in one table

The level cutoff gives a divergent sub-process (sub-bubble) inside a state only the budget left by the other quanta
alive in that slice, while r, g and the vacuum energy are tuned with the full budget L. Scheme W adds to the cutoff-l
Hamiltonian a correction D_l that restores this budget for every sub-bubble attached to the zero mode
(component D^zm), and, through local-operator windows, for mass- and coupling-type sub-bubbles attached to chi lines
(components D^M and D^V).

| component | definition | status |
|---|---|---|
| D^zm at eps^2 | second-order Bloch zero-mode window, all z -> z' (Sec. 2.3) | **derived** (linked-cluster theorem) and **verified**: C_4(L) -> continuum to 2e-7, exact to L = 2000 |
| D^M at eps^2 | (1/4){Delta c_1, M'} (Sec. 2.5) | **derived at leading order in 1/L, verified at eps^4** (same C_4 limit as the slope form; difference O(1/L^2)) |
| D^V at eps^2 | (1/2){Delta c_2, V'} (Sec. 2.6) | **invalid** [2026-10-09]: shifts C_4 by a finite ~0.49 at L = 10..16 (../complete_exact) and makes the eps^3 descendant residual grow (Sec. 5); the power-counting claim of Sec. 3 is wrong |
| D^zm at eps^k, k >= 3 | Bloch effective Hamiltonian of the level-0 sector, X Lambda X^-1 (Sec. 2.3) | **supported at eps^5** [2026-10-09]: with D^zm alone (eps^2 + eps^3 Bloch) C_5(L) has no linear divergence and fits the continuum without logs, -38.54 +- 0.57 vs -38.834. The eigenvalue-diagonal eps^3 form leaves -0.0051 L. Finite offsets below ~0.5 are not resolved |
| D^M, D^V at eps^k, k >= 3 | same formulas with the all-order Newton coefficients c_1, c_2 | **W fails at eps^5** [2026-10-09]: C_5^W(L) keeps a linear divergence of about -0.0019 L. It is located entirely in the Z-chi part (2<Z chi>_theta) of D^M,(2), which contributes -0.001965 L. D^M,(3) adds no linear term. The eps^3 descendant identity is not restored either (../complete_exact; Sec. 5). A correct chi-attached mass window beyond eps^4 is open |
| **Wc rule** [2026-10-09, provisional]: auxiliary windows referenced to the outer cutoff L (Sec. 2.2a) | removes the double counting of nested windows. It changes D^zm,(k>=3) and D^M,(k>=3) through h^(k), c_1^(k) | T1 passes: C_4 unchanged. T2 passes: C_5^Wc has no linear term; its linear coefficient equals the consistent one within the fit spread (2e-6), and it extrapolates to -38.794 +- 0.038 (L <= 200) against -38.8336 [corrected 2026-10-14: with the ln^3 L / L tail that C_5 needs, -38.833 +- 0.028; large_L/README.md]. **T3 fails**: the eps^3 descendant residual tends to a constant, about 0.062 a w_aa [2026-10-14: exactly 16/(81 pi) a w_aa, two thirds of the eps^2 exchange-sunset defect; large_L/README.md] |
| **Wcs: slice-resolved eps^3 chi self-window** [2026-10-09, provisional] (Sec. 2.5a) | the legs of a chi mass sub-process are charged only in the slices where they are present: D^(3) += (delta^(3)(L)/2) X_0, delta^(3) from the tagged phi channel; no fitted parameter | T1 passes (C_0..C_4, r, g through eps^3 identical to Wc). T2 passes: C_5 shift delta^(3)(L) S(L), S -> 0.367187 with no ln L; C_5^Wcs(inf) = -38.800 +- 0.038 [corrected 2026-10-14: that is the old tower protocol. With the ln^3 L / L tail, C_5^Wcs(inf) = -38.839 +- 0.028 (no ln L); a small ln L, abs(b) <~ 0.01, is not excluded at L <= 200; the shift is delta_inf S_inf = -0.005772; large_L/README.md]. **T3 for chi_aa: at least about 95% of the defect removed at L <= 16** (a = 1, 2, 3: R_3 = -4.9e-5, -1.2e-5, 5.5e-4 at L = 14; -1.6e-4, -2.3e-4, 5e-5 at L = 16); a zero limit is not excluded, and the blind L = 16 test slightly favours a remainder of about -0.0005 [wording and L = 14 values corrected 2026-10-13]. [Corrected 2026-10-14: delta^(3)(L) -> -4/(81 pi) exactly, with a minimum at L = 34, so the L <= 16 values lie on the falling branch. The expected limit is zero: R_3^Wc(chi_aa) -> 16/(81 pi) a w_aa and the window's -4 a w_aa x 4/(81 pi) cancel. The small negative remainder is a finite-L effect; large_L/README.md.] The phi^2 descendants are not settled at L <= 16 [corrected 2026-10-13]. T4: R_4 of chi_aa is unchanged and still grows, like about 0.028 ln L [corrected 2026-10-13; was "~0.0145 ln L"]. Budget-free legs remove it, so it is the same defect at eps^4. The eps^4 leg window is Sec. 2.5b (provisional) |
| **Wcs4chi: eps^4 chi-line window** [2026-10-13, provisional] (Sec. 2.5b) | the eps^4 chi mass window rebuilt from a chi line: uniform part from the chi-line function c1chi (X_4 = Delta c1chi^(4) - Delta c_1^(4) on the chi-chi M' terms), leg part calibrated on the chi_11 line with budget-free legs | exact invariances (C_0..C_5, r, g through eps^4, R_2, R_3); R_4(chi_11) = budget-free by construction; chi_22, chi_33 are the tests (README Sec. 12.3); the window grows like ln L and shifts C_6 by about -0.010 ln L asymptotically; C_6(inf) not assessable at L <= 16 |
| completeness (no other window types through eps^8) | Sec. 7 | **conjectured** |

Two schemes are defined and both should be implemented: **W** = D^zm + D^M (primary; the eps^4-verified content)
and **W+V** = D^zm + D^M + D^V. They differ only by the coupling window D^V.

## 1. Notation

* Basis states s = |z> (x) |chi>: z = n_00(s) zero-mode quanta (normalized |z> = (a^dag)^z/sqrt(z!)|0>, a = A_00), and
  chi = the occupation of the non-zero modes. Level N_s = sum over chi quanta of (a + b) (zero modes have level 0);
  N_s is reflection invariant. P0 = span{|z> (x) |chi = 0>} = all level-0 states.
* F_l = J = 0 reflection-even states with N_s <= l (l even, 0 <= l <= L), both field parities.
* N_hat = the level operator (diagonal, N_hat s = N_s s).
* M_Z := the part of M whose ladder operators all act on the zero mode, M_Z = :Z^2: (x) 1 with Z = a + a^dag.
  M' := M - M_Z = 2 <Z chi>_theta + <:chi^2:>_theta (every term of M with at least one chi ladder operator).
* V_Z := :Z^4:/12 (x) 1, V' := V - V_Z.
* M, M', V, V' carry their eps dependence through w_ab(x(eps)) exactly as in H.
* For an eps series f, f^(k) is its eps^k coefficient.

## 2. Definition of scheme W (and W+V)

### 2.1 Hamiltonians
For every even l = 0, 2, ..., L

    H_l = P_l (H0 + r M + g V) P_l + D_l,          D_l = D_l^zm + D_l^M  [+ D_l^V in W+V],

acting on F_l. r(eps), g(eps) are the same series for every l and are fixed by the tuning at l = L (Sec. 2.8).

### 2.2 Auxiliary channels
For every l and every z >= 0, let E_z(l) and psi_z(l) be the eigenvalue and right eigenvector of H_l on the branch
analytically connected to |z> at eps = 0 (as in ../zeromode_exact Sec. 1 and 4: the branch is unique, the degeneracy
with partners at z >= 5 is lifted at first order, and the windows do not change first order), normalized by
<z|psi_z(l)> = 1 (intermediate normalization). E_p(L), p = 0..3, are the primaries.

### 2.2a Windows inside the auxiliary channels (rule Wc, provisional, 2026-10-09)
The auxiliary channel at cutoff l < L represents the zero-mode cluster embedded in a state of the cutoff-L theory
whose spectators have level L - l. Every window acting inside it is therefore the cutoff-L window of the embedded
state. The levels are shifted by L - l and referenced to L:

    D^zm_aux |z, chi> = sum_z' [h(L) - h(l - N_chi)]_{z'z} |z', chi>   for N_chi >= 2   (none on aux level-0 states),
    D^M_aux  = (1/4) { c_1(L) - c_1(l - N_hat), M' }                 (on aux level-0 states: c_1(L) - c_1(l)),

and likewise for any other window type. h(.) and c_1(.) are the objects of these same auxiliary channels. The
channels at cutoff L (the primaries, h(L), c_1(L), the descendant channels) are unchanged. Equivalently: inside an
auxiliary channel at cutoff l, replace the first argument of every window difference Delta f(l, N) = f(l) - f(l - N)
by L. The outer windows keep their form, D^zm(L, N) = h(L) - h(L - N) and D^M = (1/4){c_1(L) - c_1(L - N_hat), M'},
but h(l) and c_1(l) are now the Wc objects. The previous rule ("h(l - N) belongs to H_{l-N} with its own window")
double counts nested windows (README Sec. 10). At eps^3 only D^M,(2) is nested, which gives:

    h^(3)(l; L)   = h^(3)(l) + (1/2) [c_1^(2)(L) - c_1^(2)(l)] H^{M'}_3(l),
    c_1^(3)(l; L) = c_1^(3)(l) + g_1 [c_1^(2)(L) - c_1^(2)(l)] [A_1(l) - A_0(l)],

with H^{M'}_3 the response of the Bloch h^(3) to adding M'_0 with unit coefficient at eps^2 in the auxiliary
Hamiltonian, and A_z(l) = <z|M'_0 R V_0|z>. Status: provisional. T1 and T2 pass, T3 fails (Sec. 0).

### 2.3 Zero-mode window D^zm
Let X(l) be the matrix on P0 with X_{z'z}(l) = <z'|psi_z(l)> (so X = 1 + O(eps), X_zz = 1), Lambda(l) = diag(E_z(l)),
and

    h(l) := X(l) Lambda(l) X(l)^-1      (generalized Bloch effective Hamiltonian of the level-0 sector of H_l).

Equivalent recursion (no inversion; h^(0) = diag(z/2)), for z' != z:

    h^(n)_{z'z} = ((z - z')/2) X^(n)_{z'z} + sum_{j=1}^{n} E_z^(j) X^(n-j)_{z'z} - sum_{z'' != z} sum_{m=1}^{n-1} h^(m)_{z'z''} X^(n-m)_{z''z},
    h^(n)_{zz}  = E_z^(n) - sum_{z'' != z} sum_{m=1}^{n-1} h^(m)_{zz''} X^(n-m)_{z''z}.

Then, for a basis state s = |z> (x) |chi> of F_l,

    D_l^zm |z, chi> = sum_{z'} [ h(l) - h(l - N_s) ]_{z'z} |z', chi>   if N_s >= 2;    D_l^zm |z, chi> = 0 if N_s = 0.

The chi factor is untouched; the window acts on the zero-mode factor only. h(l - N_s) belongs to the Hamiltonian at
cutoff l - N_s, with its own window (self-consistency, as in the consistent scheme).

At eps^2 this is h^(2)_{z'z}(l) = sum_{k in F_l \ P0} <z'|W_1|k><k|W_1|z>/(E^0_z - E^0_k) + l-independent terms
(W_1 = g1 V - P/4). The window is therefore the ket-referenced second-order effective interaction of bubbles with
level in (l - N_s, l]. Its z' = z part is the zeromode window of ../zeromode_exact, and its identity component is
the consistent (vacuum) window. At eps^2 a bra-referenced or Hermitian version gives identical C_4. Beyond eps^2 the
diagonal h_zz differs from the eigenvalue differences E_z(l) - E_z(l - N) of the zeromode scheme. Use h_zz.

### 2.4 Newton coefficients and windows
    c_1(l) := E_1(l) - E_0(l),        c_2(l) := E_2(l) - 2 E_1(l) + E_0(l),
    Delta c_k(l, N) := c_k(l) - c_k(l - N)     (N even, 0 <= N <= l;  Delta c_k(l, 0) = 0).

(E_z = sum_k c_k C(z,k). <z|M|z> = 2 C(z,1) and <z|V|z> = C(z,2), so c_1 and c_2 are the coefficients that the mass
and coupling counterterms renormalize. The r and g terms are l independent and drop out of every window.)

### 2.5 Chi mass window D^M

    <s'| D_l^M |s> = (1/4) [ Delta c_1(l, N_s) + Delta c_1(l, N_s') ] <s'| M' |s>,
    i.e. D_l^M = (1/4) { Delta c_1(l, N_hat), M' }.

It is symmetric where M' is. Unlike D^zm it does **not** vanish on level-0 states, because M' A^dag A^dag maps |z>
to two-quantum states. Leading form at eps^2: Delta c_1^(2)(l, N) = -(4/(27 pi)) N + O(N/l), i.e.
D^M,(2) = -(g1^2/(3 pi)) {N, M'} + O(1/l) = -(1/2)(dr_2/dl) {N, M'}.

### 2.5a Slice-resolved chi self-window at eps^3 (rule Wcs, provisional, 2026-10-09)
**Why D^M is incomplete at eps^3.** D^M treats a mass-type sub-process on chi lines (the sub-bubbles that the
counterterm r M' cancels) as if its two external legs, the legs of the M' term, were present with their average
level (N_s + N_s')/2 in every slice of the sub-process. The truncation charges a leg only in the slices where it is
present: an absorbed ("in") leg before its absorption, an emitted ("out") leg after its emission. At eps^2 the
sub-process has two orderings, normal (no leg present) and exchange (both legs present), with equal weight at large
bubble level, so the average is exact and R_2 -> 0. At eps^3 the self-energy also has mixed orderings, in which one
leg is present in one of its two internal slices. Their weights are not equal, so the response of the window to the
level of a leg is not half its response to a spectator. This is the whole eps^3 remainder of Wc: if the external
line of chi_aa is made invisible to the level budget, R_2 and R_3 both tend to 0 like 1/L (README Sec. 11.1).

**Auxiliary object: the tagged phi channel.** c1tag(l; nu_in, nu_out) is E - E_0 of the channel |1> at cutoff l in
which the external zero-mode line is tagged:
* the initial quantum is a distinguishable copy X_in of the zero mode that can only be absorbed;
* the final quantum is a copy X_out that can only be created, at most once;
* the tags have level 0 in H0, but add nu_in and nu_out to the budget level of every state that contains them. The
  cutoff and every window (rule Wc, with N = budget level) use the budget level;
* terms of M whose legs are only zero modes and tags are not part of M' (the tags are zero modes);
* glued RS: the model states |X_in>, |X_out> and |1> are excluded from every resolvent, E = <X_in|rhs> + <X_out|rhs>,
  and components on |1> are dropped (they double count the X_out histories);
* r and g are those of the primaries at the outer cutoff L.
With nu_in = nu_out = 0 the tagged channel is identical to the phi channel through eps^3 (c1tag(l; 0, 0) = c1(l)
exactly). From eps^4 on they differ, because D^zm acts on the regular zero modes only and not on the tag.

**Window (definition of scheme Wcs).**

    D^(3) = (1/4){Delta c_1^(3)(L, N_hat), M'_0} + (1/4){Delta c_1^(2)(L, N_hat), M'_1} + (delta^(3)(L)/2) X_0,
    delta^(3)(L) = (1/4) [ c_1^(3)(L - 2) - c1tag^(3)(L; 2, 2) ].

* X = M'^{+-}_nu is M' with every term multiplied by s x (sum of the levels of its chi legs). s = +1 for terms with
  one creator and one annihilator (chi hops and Z <-> chi hops), s = -1 for pair creation and pair annihilation
  (chi chi or Z chi). Zero-mode legs have level 0. In the monomial frame of Sec. 2.9 this is a reweighting of the
  M' columns.
* c_1^(3) and c1tag^(3) are taken on the same footing (window functions, r_3 removed: c1tag^(3) -> c1tag^(3) - 2 r_3).
* delta^(3)(L) is one number per outer cutoff. Every channel uses it, the auxiliary channels included (outer
  reference, Sec. 2.2a).
* Everything else is Wc: D^(2), D^zm at all orders, D^M,(k) for k >= 4, and the rule of Sec. 2.2a.

**Derivation of the operator form.** For a hop transition s -> s' with spectator level N_spec and chi legs nu_in,
nu_out, the slice-resolved window is (1/2)[c_1(L) - c1tag(L - N_spec; nu_in, nu_out)] M'_{s's}. To first order in the
charges this is (1/2)[c_1' N_spec + rho (nu_in + nu_out)] M'_{s's}, with c_1' = dc_1/dl and rho = c_1'/2 + delta
the response to one unit of leg level. In and out legs respond equally by time reversal. Crossing a leg (in <-> out)
exchanges the slices in which it is present. A pair leg therefore responds with c_1' - rho = c_1'/2 - delta. With (N_s + N_s')/2 = N_spec + (nu_in + nu_out)/2 this is D^M plus
(delta/2) X. delta is calibrated on the smallest charges (2, 2) at the outer cutoff. For chi_11 the window is then
exactly the slice-resolved one; for larger a it is its linearization.

**Other orders.**
* eps^2: unchanged. D^M,(2) is exact at leading order (R_2 -> 0 in Wc). The eps^2 analogue of delta,
  (1/4)[c_1^(2)(L - 2) - c1tag^(2)(L; 2, 2)], is 0.00095 at L = 12 and 0.0008 at L = 14, and vanishes like 1/L.
* eps^k, k >= 4: **open.** The principle (legs charged only where present) holds at eps^4: with budget-free legs the
  eps^4 residual of chi_11 goes to zero, while in Wcs it grows like ln L (README Sec. 11.4). The zero-mode proxy is not
  exact at eps^4, however. In the phi channel D^zm treats the external zero-mode line as part of the zero-mode sector,
  which has no counterpart for a chi line. The direct transcription D^(4) += (1/2)[delta^(4) X_0 + delta^(3) X_1]
  removes the growth but does not reproduce the budget-free values (diagnostic scheme Wcs4, README Sec. 11.5): R_4 of
  chi_11 flattens at about -0.0107. At eps^4 the chi self-energy and the zero-mode proxy differ by more than the leg
  budget. delta^(4)(L) grows like ln L.

**Status** (README Sec. 11): T1 passes (C_0..C_4, r_1..r_3, g_1..g_3 identical to Wc, exactly). T2 passes:
C_5^Wcs - C_5^Wc = delta^(3)(L) S(L) with S(inf) = 0.367187 and no ln L (the ln L of the separate M' types cancel
within the Z-chi and chi-chi sectors), and C_5^Wcs(inf) = -38.800 +- 0.038 [corrected 2026-10-14: old tower protocol; with
the ln^3 L / L tail C_5^Wcs(inf) = -38.839 +- 0.028, no ln L, and abs(b) <~ 0.01 not excluded at L <= 200; large_L/README.md
Sec. 5]. T3 for chi_aa, a = 1, 2, 3: at least about 95% of the defect is removed at L <= 16 (R_3 = -4.9e-5, -1.2e-5,
5.5e-4 at L = 14, from 0.0157, 0.0177, 0.0190 in Wc). A zero limit is not excluded; the blind L = 16 test (README
Sec. 11.9) slightly favours a small negative remainder of about -0.0005. [Wording and values corrected 2026-10-13; was
"T3 passes", "-5e-5, -1e-5, 6e-4".] [Corrected 2026-10-14: the negative remainder is a finite-L effect. delta^(3)(L) has
a minimum at L = 34, and its limit is -4/(81 pi), which cancels R_3^Wc(chi_aa) -> 16/(81 pi) a w_aa. The single-leg
responses and the larger charges (chi_22, chi_33 forms) all tend to the same limit, so the linearized window is
asymptotically exact; large_L/README.md Sec. 4.] For the phi^2 descendants T3 is
shifted by exactly (3/2) delta^(3)(L) (level 2) and is not settled at L <= 16 [corrected 2026-10-13]. T4: the eps^3
window leaves R_4 of chi_aa unchanged (exactly), and R_4 still grows (about 0.028 ln L). delta^(3)(L) is known exactly for
L <= 16 (README Sec. 11.2). Beyond the brute-force range (L ~ 16) it needs a diagrammatic version of the tagged channel,
which is not built. By extrapolation, delta_inf = -0.0160, with a range of -0.0158 to -0.0165 over the fit families
[corrected 2026-10-13; was "-0.0159 +- 0.0002"]. [Corrected 2026-10-14: both values are wrong. A chain-sum version of the
tagged channel (large_L/tagchan.py, equal to the exact values for L <= 16 to 4e-16) gives delta^(3)(L) to L = 16000.
It is not monotone: it falls to -0.0159046 at L = 34 and then rises. Its limit is delta_inf = -4/(81 pi) =
-0.0157190, matched by free fits to 3e-11, and

    delta^(3)(L) = -4/(81 pi) - (1/(54 pi)) ln L / L + 0.013856 / L + O(ln L / L^2).

The L^-2 extrapolations of L <= 16 data were on the falling branch; large_L/README.md Sec. 4.]

### 2.5b The eps^4 chi-line window (rule Wcs4chi, provisional, 2026-10-13)
**Why the zero-mode proxy fails at eps^4.** Through eps^3 a chi line and the zero-mode line have the same self-energy
function up to O(1/L), so D^M can use c_1 (the zero-mode channel) and the leg window can be calibrated on the tagged
phi channel (Sec. 2.5a). At eps^4 they differ. In the phi channel the external zero mode belongs to the zero-mode sector
and joins the zero-mode clusters (windowed by D^zm); a chi line cannot. Both parts of the chi mass window are then off:
* **leg part.** The chi_11 line with budget-free legs (tagged, README Sec. 11.1) has R_4 -> 0. Charged, in Wcs, R_4
  grows like about 0.028 ln L. The proxy transcription (Sec. 2.5a, Wcs4) removes the growth but leaves about -0.0107.
* **uniform (spectator) part.** The response of the chi-line self-energy to a spectator level N differs from that of
  c_1. With X_n(L, N) = Delta c1chi^(n)(L, N) - Delta c_1^(n)(L, N), X_2 and X_3 vanish like 1/L at fixed N, but
  X_4(L, 2) = +0.062, +0.079, +0.083, +0.083, +0.082, +0.082 (L = 6..16) does not (README Sec. 12.2).

**Auxiliary objects (both from the chi_11 line, exact brute force for L <= 16, `brute_desc_tag4.py`,
`brute_desc_chi4.py`).**
* The budget-free chi_11 line at the outer cutoff: the tagged chi_11 channel of README Sec. 11.1 with charges (0, 0).
  Its residual Rbf_4(L) = [eps^4](E_bf(chi_11) - E(phi) - 2).
* The chi-line function c1chi(l) = Sigma_chi(l) / w_11(eps), with Sigma_chi(l) = E(chi_11 line; l) - E_0(l). The line
  is the budget-free tagged chi_11 channel at cutoff l under rule Wc (windows referenced to L). M' terms whose legs are
  only tags and zero modes are left out of its windows, as pure zero-mode terms are left out of M' for c_1. c1chi is
  needed only through X_4(L, N) = Delta c1chi^(4)(L, N) - Delta c_1^(4)(L, N), N = 2..L (X_4(L, 0) = 0).

**Window (definition of scheme Wcs4chi).** Wcs plus, at eps^4,

    D^(4) += (1/4){ X_4(L, N_hat), M'_cc,0 } + (1/2)[ delta4chi(L) X_0 + delta^(3)(L) X_1 ],
    delta4chi(L) = Rbf_4(L) - R_4^Wcs(chi_11; L) + delta^(3)(L) - X_4(L, 2)/4 .

* M'_cc is the chi-chi part of M' (hops and pair terms with no zero-mode leg). The anticommutator uses the same
  per-state rule as D^M: N_hat is the level of the state, and X_4 is evaluated at L - (l - N_s) in auxiliary channels
  (rule Wc).
* X is the leg operator of Sec. 2.5a; X_1 is its eps^1 coefficient.
* The second line is the chi_11 calibration. On chi_11 the window adds w0 X_4(L, 2) + 4 [w0 delta4chi + w1 delta^(3)]
  (w_11 = w0 + w1 eps + ..., w0 = 1/4, w1 = -1/4). This is fixed so that the charged chi_11 line has the eps^4
  self-energy of the budget-free line. Hence **R_4(chi_11) = Rbf_4(L) by construction**, and chi_11 is not a test.
* Variant 'all' applies X_4 to the Z-chi terms of M' as well. Whether a Z <-> chi sub-process uses c_1, c1chi or a
  mixture is not derived. 'cc' is the definition; 'all' brackets the choice.
* Reduced variant A ("leg only") keeps the uniform part on c_1:
  D^(4) += (1/2)[(delta4chi + X_4(L, 2)/4) X_0 + delta^(3) X_1].
  On chi_aa, A and Wcs4chi differ by w0(a)[X_4(L, 2a) - a X_4(L, 2)], i.e. only through the nonlinearity of X_4 in N.

**What is not new.** D^(2), D^(3) (Wcs), D^zm at all orders and D^M,(k >= 5) are unchanged. delta4chi(L) and
X_4(L, N) are numbers per outer cutoff, used in every channel (outer reference, Sec. 2.2a).

**Status** (README Sec. 12).
* Invariances are exact for L <= 16: C_0..C_5, r_1..r_4, g_1..g_4, E_p through eps^4, and R_2, R_3 of every
  descendant are identical to Wcs. r_5, g_5 change; the window first reaches C_6.
* T4: chi_11 equals the budget-free line by construction. chi_22 and chi_33 are the tests (README Sec. 12.3). At
  L = 14, 95% (chi_22) and 90% (chi_33) of the Wcs gap to the budget-free lines is closed, leaving +0.0044 and
  +0.0100. The chi_22 gap is not yet shrinking, so a zero limit for a >= 2 is not established. The leg response depends
  on a by a few percent, which the charge-2 calibration cannot see.
* R_5 of chi_aa is unchanged, exactly, as R_4 was under the eps^3 window. R_5 grows.
* delta4chi(L) grows like ln L. Its C_6 effect is about -0.010 ln L asymptotically (README Sec. 12.5).
* The objects are exact only for L <= 16. L = 16 already takes 6-7 h and 76-110 GB per run, and L = 18 is not
  feasible in exact brute force. A large-L version needs a diagrammatic tagged chi channel, which is not built.

### 2.6 Chi coupling window D^V (scheme W+V only)

    <s'| D_l^V |s> = (1/2) [ Delta c_2(l, N_s) + Delta c_2(l, N_s') ] <s'| V' |s>,
    i.e. D_l^V = (1/2) { Delta c_2(l, N_hat), V' }.

It does not vanish on level-0 states (V' with chi creators).

### 2.7 eps structure and order-by-order closure
* Windows of eps^1 quantities vanish (E_z^(1) and h^(1) do not depend on l), so D_l = sum_{k>=2} eps^k D_l^(k).
  D^M,(k) = (1/4) sum_{j=2}^{k} {Delta c_1^(j), M'_{k-j}}, where M'_i is the eps^i coefficient of M'. D^V likewise.
* In RS for any channel: D^zm,(k) enters E^(n) only for n >= k+2 (it vanishes on |z>); D^M,(k) and D^V,(k) enter
  for n >= k+1 (they connect |z> to excited states).
* Order n, for all channels (z, l) in lock step:
  1. form RHS_n with D^(k), k <= n-1;
  2. E^(n) of the primaries gives r_n, g_n (Sec. 2.8);
  3. E_z^(n)(l) for every channel;
  4. form D^(n) from c^(n) and h^(n). D^(n) never depends on r_n, g_n;
  5. psi_z^(n) with D^(n)|z> included (only D^M, D^V contribute there).
  The P0 components X^(n) do not involve D^(n), because D^M|z> and D^V|z> have no P0 component.

### 2.8 Tuning and observable
r_n and g_n are fixed at cutoff L from the primaries E_p := E_{z=p}(L), p = 0..3, with every window included:
E_1 - E_0 = x and E_3 - E_0 = 2 - x order by order. Then C_n = [eps^n](E_2 - E_0) = Pi[X_p^(n)], with
Pi f = f(2) - f(1) - (f(3) - f(0))/3 = -(1/3) Delta_p^3 f. The same r, g enter every auxiliary H_l (l < L) and every
window, so all E_z(l) and h(l) depend on L through r, g, exactly as in the consistent and zeromode schemes.

Consequences:
* D^M changes E_p from eps^3 on (through <V R D^M>). This shifts r_3 and g_3, but not C_3: the projector kills
  degree <= 2 in p.
* In W+V, D^V,(2) changes C_3(L) at finite L (the Z^3 chi part of V' survives Pi), by O(ln L/L).

### 2.9 Frames
In the monomial similarity frame of ../rs_exact (S^-1 H S, unnormalized monomials, w_00 = 1):
* zero-mode monomials |z>_m = sqrt(z!) |z>. Take X^m_{z'z} = coefficient of |z'>_m in psi_z when psi_z has coefficient
  1 on |z>_m. Then h^m = X^m Lambda (X^m)^-1 is the matrix of h in the monomial basis, and
  D^zm (|z>_m (x) chi_m) = sum_{z'} [h^m(l) - h^m(l - N)]_{z'z} |z'>_m (x) chi_m.
* S^-1 D^M S = (1/4){Delta c_1(l, N_hat), S^-1 M' S} (N_hat is diagonal), and likewise for D^V.
* The pure-zero-mode part of S^-1 M S is the same as in the original frame (w_00 = 1). So M' in the frame = all terms
  with at least one ladder operator on a non-zero mode.

### 2.10 Degenerate partners
Channels z >= 5 have degenerate partners (levels 2, 4, 6 with P = z - 2N; ../zeromode_exact Sec. 4). Use the
B-equation of zeromode_modular.py. D^M and D^V cannot connect |z> to a partner directly (that needs Delta P <= -4
together with creating a level >= 2 quantum, impossible for a 2- or 4-leg vertex), so fact 1 of zeromode_exact Sec. 4
still holds. psi_z, X and h are those of the branch through |z>.

**[Changed 2026-10-09; see the changelog.]** For the window objects the partners are *projected out*: X(l), h(l) and
the E_z(l) that enter h_zz are computed from the RS series of H_l with the partners B of |z> removed from the
resolvent (R -> R restricted to the complement of span{B}; no B-equation). This is what the eps^2 formula of Sec. 2.3
says, and it is what the Sec. 8 reference values and the eps^4 verification used. The B-equation is still needed for
the eigenvalues of the zeromode scheme of ../zeromode_exact, but that is a different scheme. The primaries (p <= 3)
and the Newton channels z = 0, 1, 2 have no partners, so they are unaffected.

## 3. Reduction to the verified eps^4 content

Only eps^2 windows enter C_4. Their effect through E_p:
* D^zm,(2) through <V R D R V>: the full zero-mode window (diagonal = zeromode scheme; off-diagonal carries the
  -8/(243 pi) ln L);
* D^M,(2) through <V R V R D>, <V R D R V> and the shift of g_3 (from <V R D> at eps^3);
* D^V,(2) and D^V,(3) through <V R D^V>-type terms and g_3. The original text claimed these vanish as L -> inf by power
  counting (window ~ ln(L/(L - N)) for soft N; the hard region local and absorbed by g). **That claim is wrong**
  [2026-10-09]: the exact solver (../complete_exact) finds a finite shift C_4(W+V) - C_4(W) of about 0.49 at
  L = 10..16 (Sec. 0).

Verified (README Sec. 5): C_4^W(L) -> 5.0488682(6) against the continuum 5.04886843, with the slope form of D^M.
The c1 form of Sec. 2.5 differs by +1.8e-6, +4.9e-7, +1.2e-7, +2.9e-8 at L = 50, 100, 200, 400 (`nm_window_c1.py`):
same limit. With the c1 form, scheme W at finite L is an exact rational.

## 4. What enters C_n (projector Pi kills polynomial degree <= 2 in p; degree = zero-mode legs/2)

| component | first enters E_p at | survives Pi from | therefore needed for C_n: |
|---|---|---|---|
| D^zm,(k) | eps^(k+2) (<V R D R V>) | eps^(k+2) | k <= n - 2 |
| D^M,(k) | eps^(k+1) (<V R D>, degree <= 2: killed) | eps^(k+2) | k <= n - 2 |
| D^V,(k) | eps^(k+1) (<V R D>, Z^3 chi x Z^3 chi: degree 3) | eps^(k+1) | k <= n - 1 |

So C_5 needs D^zm,(2..3), D^M,(2..3) and D^V,(2..4); C_8 needs D^zm,(2..6), D^M,(2..6) and D^V,(2..7). The
auxiliary data needed are: c_1^(k) for k <= n - 2 and c_2^(k) for k <= n - 1, i.e. channels z = 0, 1, 2 at every
l <= L through order n - 1; and h^(k)(l) for k <= n - 2 for the zero-mode numbers reached. The bounds of
../zeromode_exact Sec. 3 still hold: z_s <= z0 + 4 floor((n - k)/2) - 1, and an h^(k) entry connects |z' - z| <= 4k.
The X^-1 recursion needs h^(m)_{z'z''} for intermediate z'' within the same reach. The h recursion of Sec. 2.3 needs
the X columns of every channel z'' that occurs, so the set of zero-mode channels is larger than the eigenvalue table
of zeromode_exact. **The implementation must demonstrate closure**: replace every entry outside its claimed
(z, z', order) set by random numbers (or residues) and show that nothing changes; also raise the particle caps and the
z range by 2.

## 5. Recommended exact checks for an implementation

1. With D = 0 and with the consistent D, reproduce ../rs_exact (L <= 18) exactly.
2. At eps^2 order only (set D^(k>=3) = 0), reproduce the scheme-W C_4 reference values of Sec. 8.
3. Descendant identities, order by order, in every scheme. These are window-completeness tests that need no
   continuum input.
   * single-quantum descendants chi_aa = A^dag_aa|0> (d^a dbar^a phi, P = 1, level 2a; non-degenerate after first
     order): E(chi_aa) - E_1 - 2a = 0 at every order. In consistent and zeromode the eps^2 coefficient tends to
     8a w_aa/(27 pi) as L -> inf (README Sec. 2.4). In raw it grows (0.1077 at L = 16 for a = 1). In W it tends to 0
     like ~1.2e-2/L. [Corrected 2026-10-09.]
   * the descendant of phi^2 at level (1,1) (P = 2): E - E_2 - 2 = 0. At eps = 0 it is degenerate with the other
     P = 2, level-2 state and with |6> (space spanned by |1> (x) chi_11, chi_10 chi_01 and |6>), so it needs a
     degenerate treatment; optional.
4. Closure, garbage and cap tests (Sec. 4).

## 6. Derivations (summary; details in README.md)

* D^zm: two chi-components (outer O, inner B) sharing only zero modes. Because H0 is additive, the six time orderings
  plus the RS unlinked terms cancel at leading degree in p, for any zero-mode transfer d. The cutoff removes the region
  where both share a slice. The exact repair is a nested insertion of B's effective interaction with its own
  ket-referenced energy, for all z -> z'. Proven at eps^2, where subleading-degree remainders vanish as L -> inf.
  The all-order form (Bloch effective Hamiltonian of P0, self-consistent) is the natural generalization: any
  zero-mode-attached connected sub-process is a term of h. It is not proven: folded terms of h^(k>=3) and
  three-component processes are untested.
* D^M, D^V: a 2-vertex sub-bubble whose two vertices are consecutive in time sees, averaged over its two internal time
  orderings, extra quanta of total level (N_s + N_s')/2 for a transition s -> s'. This holds for any external legs:
  nested and exchange for A^dag A, both assignments for AA and A^dag A^dag. The local counterterm of that bubble type
  needs the budget-dependent coefficient window. That gives the anticommutator with the c_k window of the auxiliary
  channels. This is exact at leading order in 1/L for soft extras. For hard extras it is an approximation whose error
  is either local (absorbed by r, g) or vanishing; demonstrated only for D^M at eps^4.

## 7. Conjectured completeness and known open points
* No window is included for chi-attached non-local effective interactions (the analogues of the c_3, c_4, ... and
  1-line-bubble terms) or for sub-bubbles with interleaved vertices. Their windows vanish for soft extras; their
  hard-extra effects are untested beyond eps^4.
* Folded terms in h^(k>=3): the Bloch (X Lambda X^-1) choice is a convention until tested. Alternatives, such as the
  Hermitian des Cloizeaux form or eigenvalue-diagonal windows, differ from eps^3 windows on.
* The ket/bra asymmetry of D^zm beyond eps^2 is unconstrained by the eps^4 test.

## 8. Reference values (scheme W at eps^2 windows; exact rationals from brute_W.py, floats from the large-L codes)

See `results/w_spec_small_L.txt` (L = 2..24, floats) and `brute/brute_W_L*.json` (L = 2..12: exact C_0..C_4, r, g).
C_0..C_3 equal the raw values. r_3 and g_3 are shifted by D^M,(2) (columns dr3, dg3). C_4^W:

| L | C_4^W (exact rational, brute_W.py) | float | large-L codes (results/w_spec_small_L.txt) |
|---|---|---|---|
| 2 | 11011547/5598720 | 1.966797232224508 | 1.966797232224511 |
| 4 | 73521971885/32105299968 | 2.290026006867428 | 2.290026006867429 |
| 6 | 1384724933304404437/543683991778099200 | 2.546929750084623 | 2.546929750084605 |
| 8 | 4321146298014108087781237/1567758459747458403532800 | 2.756257681881798 | 2.756257681881861 |
| 10 | 288911195324827065802678199257/98643362287310082750283776000 | 2.928845779641413 | 2.928845779641416 |
| 12 | 209876991923656713192935165737409071/68283302815970934721732436557824000 | 3.073620977141254 | 3.073620977141309 |

The exact r_n, g_n of scheme W are in brute/brute_W_L{L}.json (keys r_W_spec, g_W_spec). Only r_n, g_n for n <= 3
and C_0..C_4 are complete scheme-W values. The brute force included the eps^2 windows only; D^M,(3) (and D^V) also
shift r_4 and g_4 (not C_4), so the r_4, g_4 entries are not scheme-W values. C_0..C_3 equal raw. For L = 14..24 use the floats of results/w_spec_small_L.txt (the brute force and the large-L codes agree to
6e-14 at L <= 12).

## Changelog
* 2026-10-08: first version.
* 2026-10-08 (same day, minutes after READY): Sec. 8 clarified: the brute-force reference r_4, g_4 lack the
  D^(3) windows; only C_0..C_4 and r, g up to order 3 are scheme-W reference values. No change to the definitions.
* 2026-10-09: **Sec. 2.10 partner convention (definition change for channels z >= 5).** Read literally,
  "X and h of the branch through |z>" with the B-equation puts the partner component psi_1^B(l) = G_B T(l) of psi_1
  into X^(2). That adds to h^(2)_{z'z} for z >= 5 the l-dependent term sum_B <z'|W_1|B> psi_1^B(l), for example
  z = 5 -> z' = 3 through B = chi_11. It adds further terms at eps^3, in X^(3) and in E_z^(3). This contradicts the
  eps^2 formula of Sec. 2.3, and it is not what the eps^4 verification or the Sec. 8 reference values (brute_W.py)
  computed. Those take h from the RHS before the B-equation. The definition is now: partners are projected out of
  every window object, at every order (Sec. 2.10, new paragraph). Exact small-L references for this convention:
  `brute_W5.py` (variant Wb: partners dropped, no B-equation in the auxiliary channels; h^(3) by the Sec. 2.3
  recursion in the monomial frame). The partner effect on C_5 is reported in README.md Sec. 9. Nothing changes at
  eps^4 or in Sec. 8.
* 2026-10-09 (later the same day): **status after the exact eps^5 test** (README.md Sec. 9; ../complete_exact for the
  descendant identities). The definitions are unchanged; Sec. 0 now gives the status of each component.
  1. Scheme W (D^zm + D^M) does not converge at eps^5. C_5^W(L) = C_5^raw(L) + dC_5^W(L), with the shift known exactly
     to L = 1000 and raw to L = 160. The shift carries -0.002329 L. Raw carries +0.0004(4) L (profile fit, L <= 160).
     The net linear divergence is about -0.0019 L.
  2. Location of the defect: the Z-chi part of D^M,(2) contributes exactly -0.001965 L. The hop (chi in, chi out) and
     pair parts of D^M,(2) and all of D^M,(3) contribute none. At eps^4 the Z-chi part is still needed: alone it gives
     +0.012293 - 0.002947 ln L, and its ln L cancels against the chi-chi parts. The total D^M,(2) effect on C_4 is
     +0.010241 with no log. A min-side variant of the Z-chi window does not remove the linear term at eps^5 and
     breaks C_4 (+0.00295 ln L).
  3. The D^zm Bloch form passes the linear test. D^zm,(2) + D^zm,(3) ('Zb') leaves no linear term: shift -0.000364 L
     against raw +0.0004(4) L. The eigenvalue-diagonal eps^3 form ('W3e', E_z^(3)(L) - E_z^(3)(L - N)) leaves
     -0.0051 L, so it is excluded. The consistent (vacuum-only) scheme also has no linear term but keeps about +0.2 ln L.
  4. D^V (scheme W+V) is invalid as specified. The eps^3 descendant residual grows (0.067 -> 0.136 for L = 2..12,
     against 0.022 -> 0.030 in W), and ../complete_exact finds a finite C_4 shift of ~0.49.
  5. Partners (Sec. 2.10). Their terms in the diagonal E_z^(3) shift C_5 by less than 2e-5, decaying like 1/L^2.
     The full literal reading ('WB' in ../complete_exact) differs from W by -1.6e-4 in C_5 and 2.8e-5 in C_4 at
     L = 16. This is far below the defect in item 1.
  Open: a chi-attached mass window valid beyond eps^4. Its Z-chi part must reproduce the eps^4 finite shift without the
  eps^5 linear term.
* 2026-10-09 (third entry): **new provisional rule Wc (Sec. 2.2a): windows inside auxiliary channels are referenced to
  the outer cutoff.**
  * Diagnosis. The eps^5 linear divergence of W is a double counting, not a missing window. A Z-chi sunset
    (Z -> 3 chi -> chi_aa) followed by the absorption of chi_aa into the zero mode is a P0 -> P0 cluster, i.e. a term of
    h^(3). Its sunset budget is restored once by the outer D^M,(2) on the Z -> chi_aa transition, and once more by
    D^zm,(3) = h^(3)(L) - h^(3)(L - N). The self-consistent h(L - N) contains the sunset restored only to L - N.
  * General statement: with the old rule, every window nested inside an auxiliary object is counted twice, once by
    the outer windows on the cluster's internal states and once through the l dependence of the auxiliary object.
  * Order of appearance:
    * eps^5: only D^M,(2) inside h^(3) and c_1^(3). This is why the C_5 defect is purely Z-chi: Z-chi is the only M'
      part that connects P0 to a one-chi state.
    * eps^6 and up: D^zm, hop and pair D^M, and the vacuum window inside h^(4), c^(4) and E_0^(4).
  * Fix: Sec. 2.2a, a definition with no fitted parameter.
  * Results (README.md Sec. 10):
    * T1: C_4 is unchanged (Wc - W = 6e-13 for L <= 1000).
    * T2: the C_5 shift has linear coefficient -0.0003922 (consistent: -0.0003923; raw: +0.0004(4)). The log terms are
      zero within errors. C_5^Wc(inf) = -38.794 +- 0.038 (raw to L = 200) against -38.8336. Without D^M ('Zb') the
      limit is -38.540 +- 0.031, so D^M's finite part is needed and correct.
    * T3 fails. chi_aa: R_3 -> about 0.062 a w_aa (0.01565 at a = 1, 0.01755 at a = 2, L = 16, flat); the ln L
      growth of W is gone. phi^2 descendant: -0.034 at L = 16.
  * Exact small-L implementations: brute_W5.py and brute_desc.py (variant Wc), eps5/ (scheme Wc), and ce_wc/ (copy of
    ../complete_exact with outer_ref=True, all orders, L <= 16). They agree with each other exactly.
  * Still open: an eps^3 chi-attached self-budget term with the {N, M'} structure (README Sec. 10.6).
* 2026-10-09 (fourth entry, corrections only, no definition change):
  * Sec. 3: the D^V power-counting claim is marked wrong; the exact solver finds a finite C_4 shift.
  * Sec. 5 item 3: the raw eps^2 descendant residual grows; it does not tend to 8a w_aa/(27 pi).
  * README: Sec. 9.2, 9.7, 10.4 and the C_4 free-log statement are made precise (protocols, ln L caveat on C_5^Wc).
* 2026-10-09 (fifth entry): **new provisional rule Wcs (Sec. 2.5a): slice-resolved eps^3 chi self-window.**
  * Diagnosis, exact. In the chi_aa channel the external line is tagged: X_in can only be absorbed and X_out can only
    be created, both glued to chi_aa. If its level budget is switched off, R_2 and R_3 both go to zero like 1/L
    (R_3 = 0.0051 at L = 14, against 0.0157 in Wc). So the whole eps^3 remainder of Wc is the budget of the external
    legs of the chi mass sub-processes. D^M charges both legs with (N_s + N_s')/2 in every slice. That is exact at
    eps^2 and wrong at eps^3, where mixed time orderings of the vertex-corrected sunset have unequal weights.
  * Definition (Sec. 2.5a): D^(3) += (delta^(3)(L)/2) X_0, with X = M' weighted by +-(level of its chi legs)
    (+ for hops, - for pair terms, by crossing) and delta^(3)(L) = (1/4)[c_1^(3)(L - 2) - c1tag^(3)(L; 2, 2)] from the
    phi channel with a tagged external zero-mode line. One number per outer cutoff, used in every channel. Nothing is
    fitted. The Sec. 2.2a rule, D^(2) and the other windows are unchanged.
  * Tests (README Sec. 11):
    * T1: C_0..C_4, r_1..r_3, g_1..g_3 identical to Wc, exactly.
    * T2: C_5 shift = delta^(3)(L) S(L), exact. S converges to 0.367187 with no ln L. C_5^Wcs(inf) = -38.800 +- 0.038
      (exact -38.8336). [Corrected 2026-10-14: -38.839 +- 0.028 with the ln^3 L / L tail; eighth entry.]
    * T3: R_3(chi_11, chi_22, chi_33) = -5e-5, -1e-5, 6e-4 at L = 14. The phi^2 descendants are not settled.
    * T4: R_4 of chi_aa is unchanged (exact identity) and still grows. The eps^4 leg window is open.
  * Supersedes the "Z^2 chi^2 channel / 2/3" hypothesis of README Sec. 10.5: delta_inf = -0.0159(2) is not 2/3 of the
    eps^2 defect. [Corrected 2026-10-14: wrong. delta_inf = -4/(81 pi), exactly 2/3 of the eps^2 defect. The mechanism is
    still the leg budget; why the factor is 2/3 is not derived. See the eighth entry.]
  * Code: brute_desc_tag.py, brute_desc_tag4.py, brute_legw.py, nm_legw.py, delta3.py, eps5/extrap_wcs.py; ce_wc
    schemes Wcs, Wcs3, Wcs4.
* 2026-10-13 (sixth entry, errata only; the eps^4 note, App. B):
  1. The growth of R_4(chi_11) in Wc/Wcs is about 0.028 ln L, not 0.0145 ln L (Sec. 0 row Wcs; README top update and
     Sec. 11.4).
  2. R_3(chi_11) in Wcs at L = 14 is -4.9e-5, not 5e-5 (README Sec. 11.4; fifth entry above).
  3. For chi_aa, "T3 passes"/"restored" is replaced by "at least about 95% of the defect removed; a zero limit is not
     excluded; the blind L = 16 test slightly favours a small negative remainder of about -0.0005" (Sec. 0, Sec. 2.5a;
     README). [2026-10-14: the remainder is a finite-L effect; the expected limit is zero; eighth entry.]
  4. delta_inf = -0.0160, range -0.0158 to -0.0165 over the fit families, instead of -0.0159 +- 0.0002. -4/(81 pi) is
     disfavoured but not excluded. [Corrected 2026-10-14: wrong; delta_inf = -4/(81 pi). See the eighth entry.] The
     non-monotone fit model is now flagged in fits/extrap_wcs_c5.txt (Sec. 2.5a; README Secs. 11.2, 11.6).
  5. The phi^2 descendants are "not settled at L <= 16" (was "L <= 14").
  6. README Sec. 10.6: the +0.007 estimate for C_5 is superseded; the derived window shifts C_5 by -0.006.
* 2026-10-13 (seventh entry): **new provisional rule Wcs4chi (Sec. 2.5b): the eps^4 chi mass window from a chi line.**
  * At eps^4 the zero-mode proxy of Sec. 2.5a fails, because the external zero mode joins the zero-mode clusters and a
    chi line does not. Two exact chi_11-line objects replace it:
    * the budget-free chi_11 line at cutoff L (leg part);
    * the chi-line function c1chi(l), which gives the spectator part X_4(L, N) = Delta c1chi^(4) - Delta c_1^(4).
      X_2 and X_3 vanish like 1/L; X_4(L, 2) tends to about +0.083.
  * Definition: D^(4) += (1/4){X_4(L, N_hat), M'_cc,0} + (1/2)[delta4chi X_0 + delta^(3) X_1]. delta4chi is calibrated
    so that chi_11 equals its budget-free line. R_4(chi_11) is then the budget-free value by construction.
  * Exact invariances: C_0..C_5, r_1..r_4, g_1..g_4, E_p through eps^4, and R_2, R_3 of every descendant are identical
    to Wcs. R_5 of chi_aa is unchanged.
  * Tests (README Sec. 12.3): chi_22 and chi_33 move from the Wcs values to within 0.0044 and 0.0100 of their own
    budget-free lines at L = 14 (95% and 90% of the gap closed). The chi_22 gap is not yet shrinking. The leg-only
    reduction A closes less (gaps 0.0076 and 0.017).
  * delta4chi grows like ln L, so the window shifts C_6 by about -0.010 ln L asymptotically. C_6(inf) cannot be
    assessed at L <= 16.
  * Code: brute_desc_chi4.py, delta4chi.py, p5_prepare_x4.py, p5_report.py; ce_wc schemes Wcs4X, Wcs4Xall (operator
    MpZ), tables_p5.py.
* 2026-10-14 (eighth entry, corrections only; source: large_L/README.md Secs. 4, 5, 7, by the large-L agent, verified by
  the coordinator):
  1. delta^(3)(L) to L = 16000 (large_L/tagchan.py; equal to the exact brute force for L <= 16 to 4e-16). It is not
     monotone: it reaches a minimum of -0.0159046 at L = 34, then rises. Its limit is
     delta_inf = -4/(81 pi) = -0.0157190 (free fits to 3e-11), and
     delta^(3)(L) = -4/(81 pi) - (1/(54 pi)) ln L/L + 0.013856/L + O(ln L/L^2).
     * The L^-2 extrapolations are wrong: -0.0159 +- 0.0002 (fifth entry) and -0.0160 with range -0.0158..-0.0165
       (sixth entry, item 4).
     * Also wrong: "-4/(81 pi) excluded" and "disfavoured".
     * The "2/3 of the eps^2 defect" is exact: R_3^Wc(chi_aa) -> 16/(81 pi) a w_aa (README Sec. 10.4).
  2. The single-leg responses d_in and d_out both tend to -4/(81 pi). Their difference falls like 1/L, and the (2,2)
     cross term vanishes. The chi_22 and chi_33 forms tend to the same limit, with offsets of about
     -(nu - 2) 0.0062/L. The linearized window of Sec. 2.5a is asymptotically exact. The README Sec. 11.2 statements
     about smaller single-leg responses and a persistent nonlinearity in the charge describe finite-L effects.
  3. T3 for chi_aa: the expected limit of R_3^Wcs is zero. The small negative values at L = 14, 16, and the remainder of
     about -0.0005 favoured by the blind L = 16 test (sixth entry, item 3), are finite-L effects of delta^(3)(L) lying
     on its falling branch.
  4. C_5:
     * The "free ln L -0.014..-0.059, +0.15..+0.55" caveat came from tail towers that stop at ln^2 L / L. C_5 needs
       ln^3 L / L.
     * With that tail the no-log model wins the blind tests, and the free ln L coefficient drifts toward 0 as L_max
       grows (-0.047 .. -0.013).
     * C_5^Wcs(inf) = -38.839 +- 0.028 and C_5^Wc(inf) = -38.833 +- 0.028 (large_L/fits/c5_fits.txt; parent refit
       fits/parent_check_largeL/refit_c5.txt: median -38.8386, range -38.861..-38.806). A small ln L (abs(b) <~ 0.01)
       is still not excluded at L <= 200.
     * The old protocol (eps5/extrap_wcs.py) gives -38.800 +- 0.038 on the same data.
     * delta_inf S_inf = -0.005772 (was -0.0058 +- 0.0001 and -0.0058..-0.0061).
  5. No definition changes. Sec. 2.5b (Wcs4chi) uses the exact delta^(3)(L), L <= 16, and does not depend on delta_inf.
