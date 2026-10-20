# Exact complete-window ("W") scheme for the 2D LRI Hamiltonian truncation through eps^8, and descendant identities

Model and conventions: `../SPEC.md` (GFF on the unit circle, x = 1/2 - eps/4, w_ab = (x)_a (x)_b/(a! b!),
M = <:phi^2:>_theta, V = <:phi^4:>_theta/12, level cutoff N <= l, J = 0 reflection-even sectors, primaries
|p> = (A_00^dag)^p/sqrt(p!)|0>, tuning E_1 - E_0 = x and E_3 - E_0 = 2 - x at cutoff L, C_n = [eps^n](E_2 - E_0)).
Window scheme: `../residual_log/WINDOW_SPEC.md` (READY 2026-10-08 23:09 EDT). Its changelog was re-checked at the
end of this work: an entry of 2026-10-09 changed the definition for channels z >= 5 (Sec. 2.10: partners projected
out of every window object). This is the point flagged below as ambiguous; **W here implements the changed
definition**, and the earlier literal reading is kept as the labelled alternative WB. Background:
`../residual_log/README.md`. Code reused from `../rs_exact`, `../zeromode_exact`, `../residual_log` was copied;
nothing there was modified.

## Bottom line

1. **Scheme W of WINDOW_SPEC.md (definition including the 2026-10-09 partner change) is implemented exactly through
   eps^8** for **L = 0, 2, ..., 16**: C_0..C_8, r, g, E_p (p = 0..3), and the window tables (claimed h^(k)_{z'z}(l),
   c_1, c_2, E_z(l)), all exact rationals verified on held-out primes (`results/complete_L<L>.json`). Alongside:
   W+V, WB (the earlier literal reading with the B-equation in the auxiliary channels), W2 (eps^2 windows only),
   WnoM, WM2/WM3 (diagnostics), the residual_log eps^2 window "complete2" (exact in 1/pi), and descendant channels
   in every scheme (`results/descendant_<scheme>_L<L>.json`).
2. **Checks pass**:
   (a) through eps^3, W = consistent = zeromode for C_0..C_3 and for r, g, E_p through eps^2; r_3, g_3, E_p^(3) differ
   only through D^M,(2) (W without D^M equals consistent exactly through eps^3); W+V changes C_3 at finite L, as the
   spec says; chi_aa energies of consistent and zeromode coincide through eps^3; descendant identities exact at
   eps^0, eps^1 in every scheme.
   (b) C_4 of W (and of W2) equals the WINDOW_SPEC Sec. 8 brute-force rationals exactly (L = 2..12, with r_0..3,
   g_0..3) and `w_spec_small_L.txt` to <= 6e-14 (L = 2..16); W equals the new reference program `brute_W5.py`
   (variant Wb) exactly for C_0..C_5, r_0..r_4, g_0..g_4 at L = 2, 4, 6, 8 (r_5, g_5 there lack D^M,(4)); complete2
   reproduces `C4W_by_L.csv` (C4_W, slope form of D^M) to <= 7e-14 at L = 0..14. WB differs from the reference by
   the partner terms (-2.7e-4 at L = 2, then +7.3e-5 ... +2.8e-5 for L = 4..16, ~ 5e-4/L).
   (c) The independent Fraction implementation agrees exactly (every C, r, g, E_p and descendant energy, orders
   0..8) for raw, consistent, zeromode, W, W+V, WB, W+VB at L = 2..10 (L = 2 on the Mac, 4..10 on symmetry).
   (d) Garbage outside the claimed (z, z', order) sets, compared residue by residue on every prime; particle caps + 2,
   z range + 2 and one more order per auxiliary channel: nothing changes (every scheme; L = 0..14 for the
   extension, 0..16 for garbage). Regression: raw, consistent, zeromode reproduce `../rs_exact` and
   `../zeromode_exact` exactly up to L = 16.
3. **Descendant identities** (sec. 8). The eps^1 identity holds exactly everywhere. First failing order:
   * raw: eps^2 (chi_aa: grows linearly in L; phi^2 descendant: ~0.23, constant);
   * consistent, zeromode: eps^2 (chi_aa: constant, -> 8 a w_aa/(27 pi) as derived in residual_log; phi^2
     descendant: slowly decreasing, p_eff ~ -0.3, not 1/L);
   * **W: eps^2 restored** (chi_11: R_2 = 0.0114/L; phi^2 descendant: 0.63/L), **eps^3 not restored**: chi_aa
     R_3 ~ +0.11 a w_aa, slowly growing (chi_11: 0.0251, 0.0269, 0.0283, 0.0296, 0.0307, 0.0317 for L = 6..16,
     p_eff = +0.24, i.e. ~0.009 ln L); the phi^2 descendant passes a minimum near L ~ 7 and grows (0.039 at L = 16);
     orders 4..8 are violated by larger, growing amounts;
   * WB: identical to W through eps^3 for the descendants; differences <= 4e-4 at eps^4..5, growing to ~1e-2..1 at
     eps^7..8 (small against the residuals themselves); same conclusions;
   * W+V: eps^2 restored (phi^2 descendant even 0.0057/L), eps^3 badly violated (chi_aa grows linearly, ~0.0055 L;
     phi^2 descendant ~0.82 constant); D^V also shifts C_4 by a finite amount (C_4(W+V) - C_4(W) = 0.484, 0.491,
     0.492 at L = 10, 12, 14), contrary to the expectation of WINDOW_SPEC Sec. 3 that its effect vanishes;
   * complete2 (eps^2 window only): eps^2 restored (0.0119/L), eps^3 grows linearly (no eps^3 windows).
4. **Completeness**: the WINDOW_SPEC window is complete at eps^2 (C_4 limit, descendant identities) but **not at
   eps^3**. The eps^3 defect of W on chi_aa is proportional to a w_aa = <chi_aa|{N, M'}|chi_aa>/8, the operator
   structure of a chi-attached mass window. Diagnostics (sec. 8.3): W without D^M leaves a constant 0.056 (chi_11);
   with D^M,(2) alone (WM2) the residual is 0.066 and grows; adding D^M,(3) shifts it by an almost L-independent
   -0.036. So D^zm is not the problem at eps^3; the chi-attached mass window is: D^M,(2) acting at third order (its
   hard-pair region, where Delta c_1^(2)(L, N) is used beyond its leading-order validity) produces a growing term,
   and D^M,(2) + D^M,(3) together do not cancel the eps^3 mass-type defect. A correct eps^3 chi-mass window (e.g. the
   exact budget-dependent two-loop sunset with spectators, interleaved vertices, the g_2(L) ~ ln L inherited by the
   c_1 window) is missing. D^V as defined is not a correct coupling window. Consequently C_5..C_8 of W (and of every
   scheme here) should not be trusted at the percent level.


---------------------------------------------------------------------------------------------------------

## 1. Files

| file | role |
|---|---|
| `ce_core.py` | structure (reflection-even J = 0 orbit basis sorted by (level, P), cutoff-l spaces are prefixes), vertex matrices M, V, M' = M - :Z^2:, V' = V - :Z^4:/12 as eps polynomials (from `zeromode_modular_orig.py`), zero-mode shift maps, exact block extraction, the similarity-frame generators L~_-1, Lbar~_-1, CRT / rational reconstruction |
| `ce_solver.py` | exact RS modulo a prime: general channel (any reference vector, degenerate subspace D0 with first-order lifting), schemes `Raw`, `DiagWindow` (consistent, zeromode), `Complete2` (residual_log eps^2 window, 1/pi as a formal parameter), `SchemeW` (WINDOW_SPEC W and W+V, all orders; `nopartner` = sec. 2.10 convention), the lock-step driver `run_mod` |
| `ce_run.py`, `ce_combine.py`, `merge_new.py` | driver (multiprocessing over primes, chunks, incremental per-prime output, garbage and extension variants), recombination of chunks, merge of the post-change reruns |
| `bookkeeping_W.py` | which auxiliary channels (z, order, cap), which h^(k)_{z'z} entries and c_1, c_2 orders can enter (path model with degenerate-partner refunds, sec. 5); tiers of the diagonal schemes |
| `ce_fraction.py` | independent second implementation in `fractions.Fraction` (check c) |
| `compare_regression.py`, `compare_frac_mod.py` | regression against `../rs_exact`, `../zeromode_exact`; Fraction vs modular |
| `export_results.py`, `make_tables.py`, `readme_tables.py`, `desc_overview.py`, `desc_summary.py`, `descendant_fits.py` | deliverables and tables (`results/complete_L<L>.json`, `results/descendant_<scheme>_L<L>.json`, `results/checks_summary.json`, `results/tables.md`, `results/readme_tables.md`, `results/descendant_overview.md`, `results/descendant_summary.md`, `results/descendant_fits.txt`) |
| `results/book_*.json`, `results/tiers_*.json` | bookkeeping (claimed sets) used by the runs |
| `raw_out/` | reconstructed solver outputs: `prod_L<L>.json` (all schemes; the W family of the earlier reading renamed WB, W+VB, W2B, WnoMB), `new*_L<L>.json` (post-change W family), `ext_L<L>.json` (closure extension), `c2t10_L<L>.json` (complete2), `diagB_L<L>.json` (WM2/WM3 of the earlier reading), `frac_*` (Fraction check), `main_L<L>.json` (first pass, 96 primes). Per-prime chunk files are on symmetry only |
| `jobs/`, `logs/` | Slurm scripts and logs (sec. 10) |
| `zeromode_modular_orig.py`, `ref_fraction_orig.py` | unmodified copies of the reused code |

## 2. The scheme implemented and how WINDOW_SPEC.md was read

H_l = P_l (H0 + r M + g V) P_l + D_l for every even l <= L, with one r(eps), g(eps) fixed at l = L.

* **W** (primary): D_l = D^zm_l + D^M_l.
  * Auxiliary channels (z, l): the RS series through |z> of H_l (self-consistent, all l, intermediate
    normalization <z|psi> = 1). For z >= 5 the degenerate partners are removed from the resolvent (spec 2.10 as
    changed on 2026-10-09; no B-equation). WB instead follows the branch eigenvector with the B-equation (sec. 3).
  * h(l) = X(l) Lambda(l) X(l)^-1, X_{z'z} = <z'|psi_z> in the monomial frame (spec 2.9), computed order by order by
    the recursion of spec 2.3 (`SchemeW.update`); the Fraction check computes it instead by explicit power-series
    inversion of X.
  * D^zm |z, chi> = sum_z' [h(l) - h(l - N)]_{z'z} |z', chi> for N >= 2 (acts on the zero-mode factor, chi
    untouched; in the orbit basis this is the same operator because the reflection acts on chi only).
  * D^M = (1/4) sum_{j=2}^k {Delta c_1^(j)(l, N_hat), M'_{k-j}}, c_1 = E_1 - E_0, Delta c(l, N) = c(l) - c(l - N);
    M'_i = eps^i part of M' in the similarity frame (spec 2.7, 2.9).
  * Order n (spec 2.7): RHS with D^(k<=n-1); tuning from the primaries; E^(n) of every channel; then h^(n), c^(n)
    (D^(n)); then psi^(n) with D^(n)|z> (only D^M, D^V contribute there; asserted: D^(n)|z> has no component on
    the reference, on P0 or on D0).
* **W+V**: W + D^V, D^V = (1/2) sum_j {Delta c_2^(j)(l, N_hat), V'_{k-j}}, c_2 = E_2 - 2E_1 + E_0.

**Degenerate partners in h (z >= 5): ambiguity found, then resolved by the spec change.** The READY version said both
"psi_z, X and h are those of the branch through |z>" (Sec. 2.10, with the B-equation) and, in Sec. 2.3, gave the
explicit eps^2 formula h^(2)_{z'z} = sum_{k in F_l\P0} <z'|W_1|k><k|W_1|z>/(E_z - E_k), which is 0/0 for the partner
states and which `brute_W.py` (the Sec. 8 reference) evaluates without them. The two differ: the branch eigenvector
has partner components psi_1^B = G_B T(l) (O(1) at first order, fixed by the B-equation) and W_1 psi_1^B feeds the P0
components of psi_2, e.g. at L = 2, h^(2)_{1,7}(2) - h^(2)_{1,7}(0) differs by -140/9; C_4 differs by -2.7e-4
(L = 2) to +4.1e-5 (L = 12). I implemented both and reported the discrepancy. The changelog entry of 2026-10-09
then fixed the definition: X(l), h(l) and the E_z(l) entering h are computed with the partners removed from the
resolvent (no B-equation) at every order. That is now **W** (`SchemeW(nopartner=True)`: in the auxiliary channels the
D0 solve is skipped, the partner components stay zero). The earlier literal reading is **WB** (B-equation in the
auxiliary channels; results of the first production runs, renamed). The descendant channels always keep their
B-equation (they are physical eigenvalues, not window objects). Frames: as in spec 2.9 (monomial frame); h^(1) is l
independent, D starts at eps^2. "Every z >= 0" is realized by the closed set of sec. 5, demonstrated by garbage and
extension tests.

Variants computed alongside (all exact): **W2** (W with D^(k>=3) = 0: spec 5.2), **WnoM** (W without D^M, check a),
**WM2/WM3** (D^M truncated at eps^2/eps^3; diagnostics), **WB, W+VB, W2B, WnoMB** (earlier reading), legacy **Wn,
W+Vn, W2n** (B-equation but explicit second-order h^(2); identical to W through eps^4), and **complete2** (the residual_log README eps^2 window, slope form
D^chi = -(g1^2/(3 pi)){N, M'_0} with naive h^(2); 1/pi carried as a formal parameter t, results are exact
polynomials in t, obtained from 8 evaluation points per prime with one point held out as a check).

## 3. Exact solver

Rayleigh-Schroedinger to eps^8 in the similarity (monomial) frame of `../rs_exact` (all matrix elements polynomial
in eps with rational coefficients), modulo primes q < 2^23: 208 primes for L <= 12 (200 for CRT + rational
reconstruction, bound ~690 digits each for numerator and denominator), 128 for L = 14, 16 (120 + 8, bound ~415
digits); every value is verified on the 8 held-out primes. The largest C, r, g, E_p have ~370 digits (num + den) at
L = 16, window-table entries ~680. All channels (primaries, auxiliary (z, l), descendants) advance in lock step.

General channel (any reference vector v at eps = 0): D0 = allowed states with H0(0) = E0. W_1 = -P/4 + g1 V_0 is
block diagonal over the (level, P) blocks of D0 (a 4-leg vertex cannot change P by 2 delta and level by -delta,
delta != 0: parity of the level for |delta| = 1, sign of the level change for |delta| = 2). The reference block
must have v as right eigenvector with simple eigenvalue E1 (left eigenvector u, u.v = 1); every other block must
have E1 - W_1|B invertible (proved per prime: invertible mod q implies invertible over Q). With intermediate
normalization u.psi_n = 0:
  * D0 part of the order-n equation fixes psi_{n-1}^{D0} = G P_c rhs_n|D0, G = (E1 - W_1|D0 + v u^T)^-1,
    P_c = 1 - v u^T (block-wise; for level-0 references this is exactly the B-equation of `../zeromode_exact`);
  * E^(n) = u . rhs_n; psi_n = (E0 - H0)^-1 rhs_n off D0.
Active channels (primaries and auxiliaries) do the D0 solve before the tuning (their r_n, g_n, D_n terms have no D0
component, asserted); descendant channels are finished last at each order, after r_n, g_n and D^(n) are known
(D^(n) acts on the descendant reference itself).

## 4. Descendant channels and branch identification

L~_-1 = sum (a+1) A^dag_{a+1,b} A_{ab}, Lbar~_-1 = sum (b+1) A^dag_{a,b+1} A_{ab} are the similarity-frame images
of L_-1, Lbar_-1 (S^-1 A^dag_{a+1,b} A_ab S carries sqrt(w_ab/w_{a+1,b}) = sqrt((a+1)/(x+a)), which cancels the
normalization sqrt((a+1)(x+a)) of L_-1); the eps = 0 descendant vectors are built with them, exactly.

* **odd: chi_aa = d^a dbar^a phi** (= A^dag_aa|0>, P = 1, level 2a), a = 1..L/2; identity E(chi_aa) - E_1 - 2a = 0.
  D0 = {A^dag_aa|0>} plus partner blocks (P, level) = (1 + 4j, 2a - 2j), j = 1..a (e.g. a = 1: |5>; a = 2: P = 5 at
  level 2 and |9>). W_1 does not couple the reference to any partner, E1 = -1/4 = E_1^(1), and E1 is not an
  eigenvalue of any partner block (all blocks invertible), so the branch is unique and its zeroth-order vector is
  exactly chi_aa.
* **even: (L_-1 Lbar_-1)^a phi^2**, a = 1, 2; identity E - E_2 - 2a = 0. a = 1: the reference block is
  {chi_11 (x) |1>, chi_10 chi_01} (P = 2, level 2); W_1 on it has the rational eigenvalues -1/6 and -1/2; the
  descendant v = chi_11|1> + chi_10 chi_01 (orbit coordinates (1, 1)) is the eigenvector of -1/6 = E_2^(1), the
  other one (eigenvalue -1/2) is the level-2 quasi-primary [phi phi]_{1,0}; u = (1/2, 1/2); partner block |6>.
  a = 2: reference block of dimension 4 (L >= 4), the descendant is the simple eigenvector of E1 = -1/6, partners
  at (6, 2) and (10, 0). All checked exactly in `Setup` (eigenvector property, nullity 1 left and right, u.v != 0).
  The identity holds exactly at eps^0 and eps^1 in every scheme (by this construction).

## 5. Bookkeeping: what can enter through eps^8 (`bookkeeping_W.py`)

Path model: an RS term is a path of insertions; nodes are (P, level); one order moves P by <= 4 (dP = -4 cannot
raise the level, dP = +4 cannot lower it); D^zm,(k) moves z by <= 4k; D0 nodes (partners, and the reference block of
the even descendants) carry G = O(1/eps): each visit refunds one order, an insertion between two D0 nodes costs
>= 2. Minimal effective orders by Bellman-Ford. D^zm,(k) at s -> s' is needed iff d(start -> s) + k + d(s' -> end)
<= order; the h recursion then requests X, E and lower h entries; closure over all requests.

The refunds matter: in a degenerate channel a path passing through a partner on the way down is one order cheaper
(found by the garbage test: X^(4)_{7,15} needs h^(2)_{14,18} via |15> -> z = 18 -> D^(2) -> z = 14 -> partner at
P = 11 -> |7>). Without descendants the model reproduces exactly the zeromode tier table of `../zeromode_exact`
(z <= 6 to eps^6, 7-10 to eps^4, 11-14 to eps^2).

| scheme set | channels | largest z per order of h^(k) (k = 1..8) | c_1, c_2 orders |
|---|---|---|---|
| W, W+V, primaries only | z = 0..20 (caps up to 22) | 18, 20, 18, 14, 10, 6, -, - | 2..7 |
| W, W+V, with descendants (used for all runs) | z = 0..21 (caps up to 23) | 20, 21, 19, 17, 13, 9, 5, 1 | 2..8 |
| zeromode with descendants | z = 0, 1 to eps^8; 2..6 to eps^6; 7..10 to eps^4; 11..14 to eps^2 | | |
| consistent with descendants | z = 0 to eps^8 | | |

## 6. Checks (per-L flags in `results/complete_L<L>.json` -> `checks`; all of them in `results/checks_summary.json`)

No check fails at any L. Details:

| check | outcome | L |
|---|---|---|
| regression: raw and consistent = `../rs_exact` (C, r, g, E_p, vacua); zeromode = `../zeromode_exact` (C, r, g, E_p, every tabulated E_z(l)) | identical | 0..16 |
| C_0 = 1, C_1 = -1/6, r_1 = 0, g_1 = 1/3; tuning identities at every order (asserted per prime) | yes | all |
| (a) W: C_0..C_3 = consistent = zeromode | identical | all |
| (a) W: r_n, g_n, E_p^(n) for n <= 2 = consistent; r_3, g_3, E_p^(3) differ | yes | all (difference for L >= 2) |
| (a) W without D^M = consistent through eps^3 (C, r, g, E_p) | identical | 0..14 |
| (a) first order at which C(W) differs from zeromode | 4 | L >= 2 |
| (a) W+V: C_3 differs from consistent at finite L (spec 2.8): -0.0375 (L = 2) ... -0.0270 (L = 14), ~ -0.14 ln L/L | yes | L >= 2 |
| (a) chi_aa energies: consistent = zeromode through eps^3; descendant identities exact at eps^0, eps^1 (all schemes) | yes | all |
| W2 (windows of order 2 only): C_0..C_4 = W; WB = W through eps^3 (C, r, g, E_p) | identical | all |
| (b) W and W2: C_4, r_0..3, g_0..3 = WINDOW_SPEC Sec. 8 brute force (`brute_W_L*.json`) | identical | 2..12 |
| (b) W: C_0..C_5, r_0..r_4, g_0..g_4 = `brute_W5.py` variant Wb (`brute/brute_W5_L*.json`) | identical | 2, 4, 6, 8 |
| (b) W: C_4 = `results/w_spec_small_L.txt` (large-L codes, floats) | <= 6.3e-14 | 2..16 |
| (b) complete2 at t = 1/pi: C_4 = `C4W_by_L.csv` (C4_W) | <= 7e-14 | 0..14 |
| (b) WB - W at C_4 (partner terms of h^(2), earlier reading) | -2.66e-4 (L = 2), +7.3e-5, +7.9e-5, +6.4e-5, +5.1e-5, +4.1e-5, +3.3e-5, +2.8e-5 (L = 4..16) | |
| (c) Fraction implementation = modular: every C, r, g, E_p, descendant energy (orders 0..8) | identical | raw, consistent, zeromode, WB, W+VB: 2..10; W, W+V: 2..10 |
| (d) garbage: window entries outside the claimed set (h, X, E, c_1, c_2 of the W family; E_z of zeromode, E_v of consistent) replaced by random residues; compared residue by residue on every prime | identical | 0..16 (W), 0..14 (others) |
| (d) caps + 2, z range + 2, one more order per auxiliary channel (W, W+V, zeromode, consistent, WB, W+VB); primary and descendant caps + 2 (all schemes incl. raw) | identical (on every value that reconstructs in both runs) | 0..14 |
| exactness: values reconstructed from 200 (L <= 12) or 120 (L = 14, 16) primes, verified on 8 held-out primes | yes, except some chi_aa energies with a >= 5 at orders >= 5 (listed per L in the JSON) | |

## 7. C_n

Full tables: sec. 9 (C_4..C_8 of W next to consistent, zeromode, W+V and WB) and `results/tables.md` (C_2..C_8,
13 digits, all schemes). Exact rationals: `results/complete_L<L>.json` (`C`, `r`, `g`, `E`; alternatives in
`alternatives`, the other schemes in `other_schemes_C`). Example (L = 2, scheme W): C_4 = 11011547/5598720,
C_5 = -879593527/80621568.

* C_4: W = the WINDOW_SPEC Sec. 8 values; it differs from the residual_log slope form of D^M (`C4W_by_L.csv`) by
  -8.7e-5 (L = 2) ... +1.0e-5 (L = 16), the c_1 vs slope difference documented in the spec; WB is higher by
  ~5e-4/L; W+V is higher by a finite ~0.49.
* C_5..C_8 of W differ strongly from consistent and zeromode (C_8 at L = 16: W 15925, consistent 14250, zeromode
  17149; WB 15937) and are not reliable beyond eps^4 (sec. 8).

## 8. Descendant identities

### 8.1 Definitions
R_n(L) = [E_desc - E_prim - 2a]^(n), computed from the exact energies of the descendant channel and of the primary
(p = 1 for chi_aa, p = 2 for the phi^2 descendants) in the same scheme and the same r, g. In the continuum
R_n = 0 at every order. Descendant energies: `results/descendant_<scheme>_L<L>.json` (exact `E`, `residual`, floats;
eps = 0 degenerate-space data: reference and partner blocks, u, v). R_0 = R_1 = 0 exactly in every scheme and at
every L (checked).

Classification: R_n restored if |R_n| decreases with L with effective exponent p_eff = d ln|R|/d ln L -> -1 (1/L);
violated otherwise (constant: p_eff -> 0; growing: p_eff > 0). `descendant_fits.py` adds descriptive least-squares
fits (results/descendant_fits.txt); with 6-8 exact points they are not extrapolations.

### 8.2 Summary (largest L available; values from the tables of sec. 9)

| scheme | descendant | R_2 at L_max (L R_2; p_eff) | eps^2 | R_3 at L_max (p_eff) | eps^3 | first failing order |
|---|---|---|---|---|---|---|
| raw | chi_11 | +0.1077 (+1.72; +0.67) | grows | +0.4232 (+0.82) | grows | eps^2 (grows) |
| raw | chi_22 | +0.1849 (+2.96; +0.78) | grows | +0.7799 (+0.88) | grows | eps^2 (grows) |
| raw | L Lbar phi^2 | +0.2292 (+3.67; +0.13) | constant | +0.4771 (+0.80) | grows | eps^2 (constant) |
| consistent | chi_11 | +0.02432 (+0.389; -0.03) | constant | +0.04071 (+0.06) | constant | eps^2 (constant) |
| consistent | chi_22 | +0.02748 (+0.44; -0.04) | constant | +0.04048 (-0.04) | constant | eps^2 (constant) |
| consistent | L Lbar phi^2 | +0.1459 (+2.33; -0.27) | slow decrease | +0.09469 (+0.38) | grows | eps^2 (slow decrease) |
| zeromode | chi_11 | +0.02432 (+0.389; -0.03) | constant | +0.04071 (+0.06) | constant | eps^2 (constant) |
| zeromode | chi_22 | +0.02748 (+0.44; -0.04) | constant | +0.04048 (-0.04) | constant | eps^2 (constant) |
| zeromode | L Lbar phi^2 | +0.09864 (+1.58; -0.39) | slow decrease | -0.03089 (-0.89) | restored (1/L) | eps^2 (slow decrease) |
| complete2 | chi_11 | +0.0008494 (+0.0119; -1.00) | restored (1/L) | +0.4089 (+0.75) | grows | eps^3 (grows) |
| complete2 | chi_22 | +0.001109 (+0.0155; -1.17) | restored (1/L) | +0.7275 (+0.83) | grows | eps^3 (grows) |
| complete2 | L Lbar phi^2 | +0.04501 (+0.63; -0.93) | restored (1/L) | +0.655 (+0.52) | grows | eps^3 (grows) |
| W | chi_11 | +0.0007142 (+0.0114; -0.97) | restored (1/L) | +0.03173 (+0.24) | grows | eps^3 (grows) |
| W | chi_22 | +0.0009149 (+0.0146; -1.11) | restored (1/L) | +0.03447 (+0.27) | grows | eps^3 (grows) |
| W | L Lbar phi^2 | +0.03962 (+0.634; -0.94) | restored (1/L) | +0.03864 (+1.68) | grows | eps^3 (grows) |
| WB | chi_11 | +0.0007142 (+0.0114; -0.97) | restored (1/L) | +0.03173 (+0.24) | grows | eps^3 (grows) |
| WB | chi_22 | +0.0009149 (+0.0146; -1.11) | restored (1/L) | +0.03447 (+0.27) | grows | eps^3 (grows) |
| WB | L Lbar phi^2 | +0.03962 (+0.634; -0.94) | restored (1/L) | +0.03864 (+1.68) | grows | eps^3 (grows) |
| W+V | chi_11 | +0.0007142 (+0.0114; -0.97) | restored (1/L) | +0.1573 (+0.51) | grows | eps^3 (grows) |
| W+V | chi_22 | +0.0009149 (+0.0146; -1.11) | restored (1/L) | +0.2137 (+0.75) | grows | eps^3 (grows) |
| W+V | L Lbar phi^2 | +0.0003571 (+0.00571; -0.97) | restored (1/L) | +0.8188 (-0.06) | constant | eps^3 (constant) |
| WnoM | chi_11 | +0.02443 (+0.342; -0.04) | constant | +0.05611 (+0.04) | constant | eps^2 (constant) |
| WnoM | chi_22 | +0.02764 (+0.387; -0.05) | constant | +0.05842 (-0.05) | constant | eps^2 (constant) |
| WnoM | L Lbar phi^2 | +0.104 (+1.46; -0.42) | slow decrease | +0.04349 (+0.37) | grows | eps^2 (slow decrease) |
| WM2 | chi_11 | +0.0008126 (+0.0114; -0.96) | restored (1/L) | +0.06749 (+0.15) | constant | eps^3 (constant) |
| WM2 | chi_22 | +0.001061 (+0.0149; -1.13) | restored (1/L) | +0.06988 (+0.10) | constant | eps^3 (constant) |
| WM2 | L Lbar phi^2 | +0.04492 (+0.629; -0.93) | restored (1/L) | +0.1463 (+0.42) | grows | eps^3 (grows) |

Notes: L_max = 16 (14 for complete2, WM2). "first failing order" = first n whose residual is not restored by the
p_eff rule (results/descendant_fits.txt has every order and descriptive fits). WB coincides with W through eps^3 for
the descendants (partners enter at eps^4). The phi^2-descendant eps^3 entry of W is classified from the last pair
(0.0309 -> 0.0386); it passed a minimum (0.0074) at L ~ 6-8. For chi_aa the eps^3 residual of W grows like
~0.009 ln L (p_eff = +0.24 stable over L = 6..16). WM2 grows more slowly (p_eff +0.10..+0.15).


### 8.3 Where the eps^3 defect comes from (diagnostics)

* a-dependence: for a << L/2 the eps^3 residual of chi_aa is proportional to a w_aa, the matrix element of
  {N, M'}/8 in chi_aa, in every scheme: R_3/(a w_aa) at L = 12 = 0.16, 0.15, 0.15 (consistent, a = 1, 2, 3),
  0.22, 0.21, 0.21 (W without D^M), 0.119, 0.114, 0.110 (W). Same structure as the eps^2 defect (8/(27 pi) a w_aa)
  that D^M,(2) removes: the eps^3 defect is a mass-type window on chi lines.
* order-by-order content: W2 (windows of order 2 only) grows linearly at eps^3 (the eps^3 vacuum window is
  missing); W without D^M leaves a constant 0.056 (chi_11); full W 0.030 growing. Hence D^zm is fine at eps^3 and the
  D^M family removes ~half of the remaining defect but leaves a growing part.
* WM2 / WM3 (D^M truncated at eps^2 / eps^3, D^zm complete): eps^3 residual of chi_11 for L = 4, 6, ..., 14:
  WM2 0.0581, 0.0602, 0.0624, 0.0643, 0.0660, 0.0675 (grows slowly); WM3 = W 0.0232, 0.0251, 0.0269, 0.0283,
  0.0296, 0.0307 (grows by similar increments); W without D^M 0.0560, 0.0552, 0.0552, 0.0554, 0.0558, 0.0561
  (nearly constant). So **the growth is introduced
  by D^M,(2) acting at third order** (paths <chi|V R D^M,(2)|chi>, D^M,(2) R V, and the r_3, g_3 it shifts; for hard
  intermediate pairs Delta c_1^(2)(L, N) ~ (dr_2/dl) N is the leading-order form, which is only an approximation for
  N ~ L), while D^M,(3) only shifts the residual by an almost L-independent -0.036 and D^zm leaves a constant. Even
  without the growth, D^M,(2) + D^M,(3) do not cancel the constant eps^3 defect of the D^zm-only scheme
  (0.056 -> 0.030 + growth). Same pattern for chi_22 and the phi^2 descendant (sec. 9, results/descendant_*).
  (`raw_out/new_L<L>.json`, `raw_out/new14_L14.json`, jobs 572114, 572116/7; the earlier reading gives the same
  eps^3 numbers, `raw_out/diagB_L<L>.json`, job 571981.)

## 9. Tables

### C_4 .. C_8: W next to consistent and zeromode (10 significant digits)

| L | n | W | consistent | zeromode | W+V | WB (earlier reading) |
|---|---|---|---|---|---|---|
| 0 | 4 | 1.366437196 | 1.366437196 | 1.366437196 | 1.366437196 | 1.366437196 |
| 0 | 5 | -6.614619889 | -6.614619889 | -6.614619889 | -6.614619889 | -6.614619889 |
| 0 | 6 | 39.57285833 | 39.57285833 | 39.57285833 | 39.57285833 | 39.57285833 |
| 0 | 7 | -275.2245058 | -275.2245058 | -275.2245058 | -275.2245058 | -275.2245058 |
| 0 | 8 | 2150.062544 | 2150.062544 | 2150.062544 | 2150.062544 | 2150.062544 |
| 2 | 4 | 1.966797232 | 1.705674601 | 1.818164598 | 2.192213339 | 1.966530938 |
| 2 | 5 | -10.91015157 | -9.812407443 | -10.9248081 | -12.076251 | -10.90653307 |
| 2 | 6 | 74.14294506 | 64.30971656 | 78.10159303 | 81.4552728 | 74.21937479 |
| 2 | 7 | -587.7995488 | -493.4204912 | -683.9272953 | -642.5806032 | -588.7459714 |
| 2 | 8 | 5239.992609 | 4262.496981 | 7117.341823 | 5720.252376 | 5249.970345 |
| 4 | 4 | 2.290026007 | 2.034869273 | 2.150709213 | 2.655960239 | 2.290099218 |
| 4 | 5 | -13.64248511 | -12.16437246 | -13.36502659 | -16.05162808 | -13.64061515 |
| 4 | 6 | 97.66008689 | 84.93272703 | 100.5979174 | 114.8908056 | 97.65663173 |
| 4 | 7 | -816.8231196 | -687.6901671 | -912.3856104 | -958.163386 | -818.2150476 |
| 4 | 8 | 7676.131377 | 6270.278878 | 9764.002061 | 8989.017576 | 7694.896365 |
| 6 | 4 | 2.54692975 | 2.306457231 | 2.418789752 | 2.981085297 | 2.547008315 |
| 6 | 5 | -15.56266097 | -14.03471505 | -15.19093161 | -18.93688177 | -15.5620985 |
| 6 | 6 | 115.2795692 | 101.6952407 | 117.0386989 | 141.3687488 | 115.2661869 |
| 6 | 7 | -994.6786223 | -852.7094596 | -1076.646374 | -1218.46745 | -995.793658 |
| 6 | 8 | 9640.592658 | 8045.252976 | 11586.71448 | 11789.99294 | 9660.642342 |
| 8 | 4 | 2.756257682 | 2.52761495 | 2.636508795 | 3.223981102 | 2.756321396 |
| 8 | 5 | -17.07972334 | -15.57203629 | -16.67024052 | -21.16997356 | -17.07961442 |
| 8 | 6 | 129.2737715 | 115.6286984 | 130.2708887 | 162.9755444 | 129.2621454 |
| 8 | 7 | -1139.477323 | -993.5587315 | -1208.849709 | -1438.298539 | -1140.403877 |
| 8 | 8 | 11276.00999 | 9600.803819 | 13033.07315 | 14213.49554 | 11294.47991 |
| 10 | 4 | 2.92884578 | 2.709091947 | 2.815282971 | 3.412665684 | 2.928896434 |
| 10 | 5 | -18.34156174 | -16.8671452 | -17.91344855 | -22.9659433 | -18.34162402 |
| 10 | 6 | 140.8845093 | 127.4533748 | 141.3915633 | 181.07098 | 140.8751146 |
| 10 | 7 | -1261.246123 | -1115.220116 | -1320.710265 | -1627.67091 | -1262.057048 |
| 10 | 8 | 12671.94036 | 10969.99341 | 14257.56689 | 16342.04039 | 12688.59982 |
| 12 | 4 | 3.073620977 | 2.860575563 | 2.964718121 | 3.56418269 | 3.073661784 |
| 12 | 5 | -19.41913439 | -17.97673045 | -18.97971177 | -24.45096156 | -19.41926431 |
| 12 | 6 | 150.8087152 | 137.6673562 | 150.9823734 | 196.5544914 | 150.8009136 |
| 12 | 7 | -1366.186258 | -1221.643713 | -1417.994995 | -1793.618768 | -1366.91925 |
| 12 | 8 | 13887.6034 | 12184.66667 | 15329.41687 | 18238.43973 | 13902.70866 |
| 14 | 4 | 3.196770498 | 2.988870685 | 3.091466305 | 3.68883878 | 3.196803972 |
| 14 | 5 | -20.35635065 | -18.94135543 | -19.90869535 | -25.70527879 | -20.35650584 |
| 14 | 6 | 159.4596806 | 146.6147476 | 159.3948899 | 210.0203408 | 159.4529378 |
| 14 | 7 | -1458.252352 | -1315.783194 | -1504.058135 | -1941.000101 | -1458.928383 |
| 14 | 8 | 14962.54826 | 13271.03548 | 16285.50352 | 19947.46621 | 14976.37458 |
| 16 | 4 | 3.30297211 | 3.099085521 | 3.200509276 | 3.793536602 | 3.303000047 |
| 16 | 5 | -21.18211748 | -19.78958174 | -20.72757832 | -26.78304695 | -21.18227935 |
| 16 | 6 | 167.113268 | 154.5451343 | 166.8696611 | 221.8944003 | 167.1072273 |
| 16 | 7 | -1540.137294 | -1399.877349 | -1581.137403 | -2073.386533 | -1540.769388 |
| 16 | 8 | 15924.71527 | 14250.13838 | 17149.0876 | 21502.93955 | 15937.48589 |

### C_4 of the variants (check b)

| L | W (= brute_W Sec. 8 for L <= 12) | WB (earlier reading) | WB - W | complete2 (slope form, t = 1/pi) | C4W_by_L.csv | W+V |
|---|---|---|---|---|---|---|
| 0 | 1.366437196227 | 1.366437196227 | +0.000e+00 | 1.366437196227 | 1.366437196227 | 1.366437196227 |
| 2 | 1.966797232225 | 1.966530937591 | -2.663e-04 | 1.966884466461 | 1.966884466461 | 2.192213339239 |
| 4 | 2.290026006867 | 2.290099217595 | +7.321e-05 | 2.290042077448 | 2.290042077448 | 2.655960238588 |
| 6 | 2.546929750085 | 2.547008315448 | +7.857e-05 | 2.546923269518 | 2.546923269518 | 2.981085297375 |
| 8 | 2.756257681882 | 2.756321395847 | +6.371e-05 | 2.756245037529 | 2.756245037529 | 3.223981101567 |
| 10 | 2.928845779641 | 2.928896433832 | +5.065e-05 | 2.928832263364 | 2.928832263364 | 3.412665684166 |
| 12 | 3.073620977141 | 3.073661784391 | +4.081e-05 | 3.073608283249 | 3.073608283249 | 3.56418269039 |
| 14 | 3.196770497664 | 3.196803972196 | +3.347e-05 | 3.196759090452 | 3.196759090452 | 3.688838779557 |
| 16 | 3.302972109849 | 3.303000047409 | +2.794e-05 | — | 3.302962022506 | 3.793536602297 |

### Descendant residual chi_11 = d dbar phi: E - E_1 - 2, orders 2..8

**raw**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.04745 | 0.05425 | 0.06258 | 0.07136 | 0.08032 | 0.08938 | 0.0985 | 0.1077 | 1.722 | +0.67 |
| 3 | 0.1227 | 0.1617 | 0.2044 | 0.2479 | 0.2917 | 0.3355 | 0.3793 | 0.4232 | 6.771 | +0.82 |
| 4 | -0.04545 | 0.02013 | 0.08525 | 0.149 | 0.2118 | 0.2741 | 0.336 | 0.3977 | 6.363 | +1.26 |
| 5 | 0.244 | 0.3957 | 0.53 | 0.6581 | 0.7826 | 0.9048 | 1.025 | 1.143 | 18.29 | +0.82 |
| 6 | -1.803 | -2.573 | -3.411 | -4.273 | -5.168 | -6.094 | -7.058 | -8.057 | -128.9 | +0.99 |
| 7 | 12.79 | 17.54 | 22.89 | 28.39 | 33.92 | 39.46 | 44.97 | 50.46 | 807.3 | +0.86 |
| 8 | -105.2 | -154.9 | -212.6 | -274.4 | -339.1 | -406.2 | -475.3 | -546.2 | -8739 | +1.04 |

**consistent**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.02894 | 0.02648 | 0.02554 | 0.02506 | 0.02477 | 0.02457 | 0.02443 | 0.02432 | 0.3891 | -0.03 |
| 3 | 0.04453 | 0.04007 | 0.03935 | 0.03941 | 0.03968 | 0.04002 | 0.04037 | 0.04071 | 0.6514 | +0.06 |
| 4 | -0.145 | -0.1413 | -0.1375 | -0.1349 | -0.1331 | -0.1317 | -0.1307 | -0.1299 | -2.079 | -0.05 |
| 5 | 0.1064 | 0.1644 | 0.197 | 0.2178 | 0.2323 | 0.2429 | 0.2509 | 0.2572 | 4.116 | +0.19 |
| 6 | -1.196 | -1.43 | -1.642 | -1.811 | -1.948 | -2.061 | -2.156 | -2.239 | -35.82 | +0.28 |
| 7 | 9.526 | 11.16 | 12.82 | 14.23 | 15.42 | 16.41 | 17.27 | 18.01 | 288.2 | +0.32 |
| 8 | -75.01 | -92.35 | -109.6 | -124.6 | -137.5 | -148.7 | -158.4 | -167 | -2671 | +0.39 |

**zeromode**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.02894 | 0.02648 | 0.02554 | 0.02506 | 0.02477 | 0.02457 | 0.02443 | 0.02432 | 0.3891 | -0.03 |
| 3 | 0.04453 | 0.04007 | 0.03935 | 0.03941 | 0.03968 | 0.04002 | 0.04037 | 0.04071 | 0.6514 | +0.06 |
| 4 | -0.1588 | -0.1519 | -0.1451 | -0.1404 | -0.1366 | -0.1335 | -0.1306 | -0.1279 | -2.046 | -0.16 |
| 5 | 0.06428 | 0.1373 | 0.1754 | 0.2003 | 0.2199 | 0.2369 | 0.2526 | 0.2678 | 4.285 | +0.44 |
| 6 | -1.61 | -1.763 | -1.935 | -2.076 | -2.191 | -2.285 | -2.364 | -2.43 | -38.88 | +0.21 |
| 7 | 12.4 | 14.01 | 15.34 | 16.46 | 17.41 | 18.23 | 18.93 | 19.55 | 312.8 | +0.24 |
| 8 | -114.7 | -132.4 | -146.1 | -157.7 | -167.8 | -176.7 | -184.6 | -191.8 | -3069 | +0.28 |

**complete2**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.005357 | 0.002897 | 0.001966 | 0.001483 | 0.001188 | 0.0009909 | 0.0008494 | 0.01189 | -1.00 |
| 3 | 0.1502 | 0.1874 | 0.2307 | 0.275 | 0.3197 | 0.3643 | 0.4089 | 5.725 | +0.75 |
| 4 | -0.01638 | 0.05419 | 0.1231 | 0.1894 | 0.2544 | 0.3186 | 0.3822 | 5.351 | +1.18 |
| 5 | 0.2689 | 0.4718 | 0.645 | 0.8126 | 0.9793 | 1.147 | 1.315 | 18.41 | +0.89 |
| 6 | -2.487 | -3.05 | -3.742 | -4.459 | -5.203 | -5.972 | -6.767 | -94.74 | +0.81 |
| 7 | 16.54 | 21.25 | 26.49 | 31.98 | 37.59 | 43.29 | 49.04 | 686.6 | +0.81 |
| 8 | -140.8 | -193.2 | -251.4 | -313.7 | -379.1 | -447.2 | -517.6 | -7247 | +0.95 |

**W**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.00463 | 0.002604 | 0.001808 | 0.001385 | 0.001122 | 0.0009424 | 0.0008126 | 0.0007142 | 0.01143 | -0.97 |
| 3 | 0.02192 | 0.02316 | 0.02512 | 0.02686 | 0.02834 | 0.02962 | 0.03074 | 0.03173 | 0.5076 | +0.24 |
| 4 | 0.01911 | 0.04062 | 0.05683 | 0.06835 | 0.07738 | 0.08482 | 0.09123 | 0.0969 | 1.55 | +0.45 |
| 5 | 0.07151 | 0.02862 | 0.01269 | 0.001076 | -0.00582 | -0.009515 | -0.01055 | -0.009638 | -0.1542 | -0.68 |
| 6 | -0.1568 | -0.1044 | -0.006959 | 0.08885 | 0.184 | 0.2755 | 0.3639 | 0.449 | 7.184 | +1.57 |
| 7 | 1.993 | 0.9483 | 0.4903 | 0.08489 | -0.2672 | -0.5777 | -0.8506 | -1.091 | -17.46 | +1.87 |
| 8 | -19.09 | -8.877 | -4.108 | -0.3672 | 2.916 | 5.867 | 8.546 | 11 | 176 | +1.89 |

**WB**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.00463 | 0.002604 | 0.001808 | 0.001385 | 0.001122 | 0.0009424 | 0.0008126 | 0.0007142 | 0.01143 | -0.97 |
| 3 | 0.02192 | 0.02316 | 0.02512 | 0.02686 | 0.02834 | 0.02962 | 0.03074 | 0.03173 | 0.5076 | +0.24 |
| 4 | 0.01915 | 0.0406 | 0.05683 | 0.06835 | 0.07738 | 0.08482 | 0.09123 | 0.0969 | 1.55 | +0.45 |
| 5 | 0.06869 | 0.02874 | 0.01277 | 0.00112 | -0.005795 | -0.009499 | -0.01054 | -0.00963 | -0.1541 | -0.68 |
| 6 | -0.1289 | -0.09942 | -0.005982 | 0.08897 | 0.1839 | 0.2753 | 0.3637 | 0.4487 | 7.179 | +1.57 |
| 7 | 1.758 | 0.841 | 0.4305 | 0.04716 | -0.2939 | -0.5984 | -0.8676 | -1.106 | -17.69 | +1.82 |
| 8 | -16.33 | -7.747 | -3.285 | 0.2225 | 3.363 | 6.224 | 8.844 | 11.25 | 180.1 | +1.80 |

**W+V**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.00463 | 0.002604 | 0.001808 | 0.001385 | 0.001122 | 0.0009424 | 0.0008126 | 0.0007142 | 0.01143 | -0.97 |
| 3 | 0.06693 | 0.08723 | 0.1014 | 0.1138 | 0.1252 | 0.1362 | 0.1469 | 0.1573 | 2.517 | +0.51 |
| 4 | -0.03184 | -0.1577 | -0.2749 | -0.3946 | -0.5209 | -0.6559 | -0.8005 | -0.9552 | -15.28 | +1.32 |
| 5 | 0.04023 | 0.3121 | 0.6989 | 1.123 | 1.577 | 2.064 | 2.584 | 3.14 | 50.24 | +1.46 |
| 6 | 0.3406 | -0.8613 | -2.975 | -5.697 | -8.938 | -12.69 | -16.98 | -21.81 | -348.9 | +1.88 |
| 7 | -2.16 | 0.04086 | 11.13 | 27.96 | 49.84 | 76.71 | 108.6 | 145.7 | 2332 | +2.20 |
| 8 | 11.4 | 25.36 | -24.26 | -123.5 | -268.7 | -460 | -699.1 | -988.6 | -1.582e+04 | +2.59 |

**WnoM**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.02894 | 0.02648 | 0.02554 | 0.02506 | 0.02477 | 0.02457 | 0.02443 | 0.342 | -0.04 |
| 3 | 0.06074 | 0.05598 | 0.05518 | 0.05519 | 0.05544 | 0.05577 | 0.05611 | 0.7856 | +0.04 |
| 4 | -0.04984 | -0.05652 | -0.05237 | -0.04814 | -0.04418 | -0.04041 | -0.03674 | -0.5144 | -0.62 |
| 5 | 0.3035 | 0.2869 | 0.3165 | 0.3415 | 0.3646 | 0.3871 | 0.4094 | 5.732 | +0.36 |
| 6 | -1.332 | -1.641 | -1.78 | -1.892 | -1.973 | -2.032 | -2.073 | -29.03 | +0.13 |
| 7 | 10.53 | 12.2 | 13.83 | 15.09 | 16.14 | 17.03 | 17.8 | 249.2 | +0.29 |
| 8 | -88.9 | -106.4 | -123.3 | -137.3 | -148.9 | -158.8 | -167.5 | -2345 | +0.34 |

**WM2**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.00463 | 0.002604 | 0.001808 | 0.001385 | 0.001122 | 0.0009424 | 0.0008126 | 0.01138 | -0.96 |
| 3 | 0.05804 | 0.05812 | 0.06024 | 0.06237 | 0.06429 | 0.06598 | 0.06749 | 0.9448 | +0.15 |
| 4 | -0.05428 | -0.0564 | -0.05076 | -0.0459 | -0.04175 | -0.03808 | -0.03473 | -0.4862 | -0.60 |
| 5 | 0.301 | 0.2867 | 0.3153 | 0.341 | 0.3658 | 0.3903 | 0.4149 | 5.808 | +0.40 |
| 6 | -1.35 | -1.624 | -1.736 | -1.821 | -1.879 | -1.917 | -1.94 | -27.16 | +0.08 |
| 7 | 10.58 | 12.17 | 13.69 | 14.85 | 15.8 | 16.61 | 17.3 | 242.2 | +0.27 |
| 8 | -89.3 | -106.1 | -122.2 | -135.5 | -146.5 | -155.8 | -163.9 | -2295 | +0.33 |

### Descendant residual chi_22 = d^2 dbar^2 phi: E - E_1 - 4, orders 2..8

**raw**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.07931 | 0.09456 | 0.112 | 0.13 | 0.1482 | 0.1665 | 0.1849 | 2.958 | +0.78 |
| 3 | 0.2849 | 0.3525 | 0.4351 | 0.5203 | 0.6065 | 0.6931 | 0.7799 | 12.48 | +0.88 |
| 4 | 0.1962 | 0.2537 | 0.3735 | 0.4984 | 0.6233 | 0.7478 | 0.8718 | 13.95 | +1.15 |
| 5 | 0.5076 | 0.6758 | 0.9537 | 1.216 | 1.466 | 1.708 | 1.944 | 31.11 | +0.97 |
| 6 | -3.688 | -4.783 | -6.288 | -7.955 | -9.718 | -11.56 | -13.49 | -215.9 | +1.15 |
| 7 | 23.2 | 31.58 | 40.53 | 50.15 | 60.13 | 70.28 | 80.52 | 1288 | +1.02 |
| 8 | -210.9 | -299.4 | -403.9 | -517.7 | -638.8 | -765.8 | -898 | -1.437e+04 | +1.19 |

**consistent**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.03301 | 0.02975 | 0.02871 | 0.02818 | 0.02785 | 0.02764 | 0.02748 | 0.4396 | -0.04 |
| 3 | 0.06828 | 0.04857 | 0.04398 | 0.04208 | 0.04116 | 0.0407 | 0.04048 | 0.6478 | -0.04 |
| 4 | -0.1322 | -0.1961 | -0.198 | -0.1948 | -0.1916 | -0.1888 | -0.1864 | -2.982 | -0.09 |
| 5 | 0.07575 | 0.07001 | 0.1503 | 0.2038 | 0.2384 | 0.2623 | 0.2794 | 4.47 | +0.47 |
| 6 | -1.738 | -1.621 | -1.786 | -1.986 | -2.165 | -2.317 | -2.447 | -39.15 | +0.41 |
| 7 | 13.44 | 14.95 | 16.14 | 17.41 | 18.61 | 19.69 | 20.66 | 330.5 | +0.36 |
| 8 | -109.9 | -123.8 | -140.1 | -154.9 | -168 | -179.8 | -190.3 | -3044 | +0.43 |

**zeromode**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.03301 | 0.02975 | 0.02871 | 0.02818 | 0.02785 | 0.02764 | 0.02748 | 0.4396 | -0.04 |
| 3 | 0.06828 | 0.04857 | 0.04398 | 0.04208 | 0.04116 | 0.0407 | 0.04048 | 0.6478 | -0.04 |
| 4 | -0.1595 | -0.2172 | -0.2177 | -0.2132 | -0.2088 | -0.2049 | -0.2016 | -3.225 | -0.12 |
| 5 | -0.02229 | -0.005487 | 0.07865 | 0.1349 | 0.1718 | 0.1983 | 0.2186 | 3.498 | +0.73 |
| 6 | -2.425 | -2.188 | -2.297 | -2.46 | -2.613 | -2.745 | -2.858 | -45.73 | +0.30 |
| 7 | 17.31 | 18.35 | 19.29 | 20.29 | 21.25 | 22.13 | 22.92 | 366.8 | +0.26 |
| 8 | -169.1 | -174.5 | -186.9 | -198.1 | -208.4 | -217.7 | -226.2 | -3619 | +0.29 |

**complete2**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|
| 2 | 0.006487 | 0.003224 | 0.002189 | 0.001655 | 0.001329 | 0.001109 | 0.01553 | -1.17 |
| 3 | 0.3213 | 0.3857 | 0.468 | 0.5536 | 0.6403 | 0.7275 | 10.19 | +0.83 |
| 4 | 0.2505 | 0.323 | 0.4442 | 0.5715 | 0.699 | 0.8261 | 11.57 | +1.08 |
| 5 | 0.7709 | 1.015 | 1.386 | 1.743 | 2.093 | 2.44 | 34.16 | +1.00 |
| 6 | -4.606 | -5.395 | -6.643 | -8.048 | -9.532 | -11.07 | -155 | +0.97 |
| 7 | 28.22 | 36.89 | 46.37 | 56.55 | 67.19 | 78.09 | 1093 | +0.98 |
| 8 | -268 | -358.7 | -468 | -586.6 | -712.4 | -844.4 | -1.182e+04 | +1.10 |

**W**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.005914 | 0.00297 | 0.002045 | 0.001562 | 0.001264 | 0.001061 | 0.0009149 | 0.01464 | -1.11 |
| 3 | 0.03673 | 0.02809 | 0.02896 | 0.03046 | 0.03193 | 0.03327 | 0.03447 | 0.5515 | +0.27 |
| 4 | 0.06447 | 0.04581 | 0.0594 | 0.07406 | 0.08678 | 0.09792 | 0.1079 | 1.726 | +0.72 |
| 5 | 0.07474 | 0.02525 | 0.04202 | 0.06297 | 0.08068 | 0.09759 | 0.1146 | 1.833 | +1.20 |
| 6 | -0.2562 | 0.05249 | 0.1885 | 0.2876 | 0.3763 | 0.4654 | 0.5551 | 8.882 | +1.32 |
| 7 | 2.673 | 1.215 | 0.4846 | 0.08668 | -0.1935 | -0.4126 | -0.6008 | -9.613 | +2.81 |
| 8 | -24.83 | -10.17 | -3.775 | 0.09742 | 2.894 | 5.113 | 6.974 | 111.6 | +2.32 |

**WB**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.005914 | 0.00297 | 0.002045 | 0.001562 | 0.001264 | 0.001061 | 0.0009149 | 0.01464 | -1.11 |
| 3 | 0.03673 | 0.02809 | 0.02896 | 0.03046 | 0.03193 | 0.03327 | 0.03447 | 0.5515 | +0.27 |
| 4 | 0.06447 | 0.04581 | 0.0594 | 0.07406 | 0.08678 | 0.09792 | 0.1079 | 1.726 | +0.72 |
| 5 | 0.07479 | 0.02524 | 0.04202 | 0.06297 | 0.08068 | 0.09759 | 0.1146 | 1.833 | +1.20 |
| 6 | -0.2595 | 0.05412 | 0.1891 | 0.2878 | 0.3764 | 0.4654 | 0.5551 | 8.882 | +1.32 |
| 7 | 2.7 | 1.183 | 0.4647 | 0.07107 | -0.2059 | -0.4228 | -0.6096 | -9.753 | +2.74 |
| 8 | -25.16 | -9.906 | -3.614 | 0.2597 | 3.036 | 5.236 | 7.082 | 113.3 | +2.26 |

**W+V**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.005914 | 0.00297 | 0.002045 | 0.001562 | 0.001264 | 0.001061 | 0.0009149 | 0.01464 | -1.11 |
| 3 | 0.07819 | 0.1042 | 0.1286 | 0.151 | 0.1725 | 0.1933 | 0.2137 | 3.42 | +0.75 |
| 4 | 0.01542 | -0.1518 | -0.3269 | -0.5181 | -0.7293 | -0.962 | -1.216 | -19.46 | +1.76 |
| 5 | -0.00321 | 0.1881 | 0.6272 | 1.186 | 1.83 | 2.554 | 3.357 | 53.71 | +2.05 |
| 6 | 0.6373 | -0.3144 | -2.925 | -6.715 | -11.57 | -17.46 | -24.42 | -390.7 | +2.51 |
| 7 | -4.071 | -5.794 | 6.077 | 28.04 | 59.26 | 99.72 | 149.7 | 2395 | +3.04 |
| 8 | 19.39 | 75.03 | 40.15 | -73.89 | -266.1 | -539.3 | -898.2 | -1.437e+04 | +3.82 |

**WnoM**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|
| 2 | 0.03301 | 0.02975 | 0.02871 | 0.02818 | 0.02785 | 0.02764 | 0.3869 | -0.05 |
| 3 | 0.08635 | 0.06643 | 0.06176 | 0.05982 | 0.05889 | 0.05842 | 0.8179 | -0.05 |
| 4 | -0.02477 | -0.09304 | -0.1001 | -0.09817 | -0.09498 | -0.09163 | -1.283 | -0.23 |
| 5 | 0.3287 | 0.2577 | 0.307 | 0.3534 | 0.3872 | 0.4142 | 5.798 | +0.44 |
| 6 | -1.754 | -1.855 | -1.969 | -2.108 | -2.237 | -2.342 | -32.79 | +0.30 |
| 7 | 14.59 | 15.62 | 16.8 | 17.97 | 19.05 | 20.02 | 280.3 | +0.32 |
| 8 | -128.2 | -139.7 | -154.3 | -167.6 | -179.5 | -190 | -2661 | +0.37 |

**WM2**

| n | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|
| 2 | 0.005914 | 0.00297 | 0.002045 | 0.001562 | 0.001264 | 0.001061 | 0.01486 | -1.13 |
| 3 | 0.08305 | 0.0687 | 0.06738 | 0.06785 | 0.0688 | 0.06988 | 0.9783 | +0.10 |
| 4 | -0.033 | -0.08338 | -0.08294 | -0.07608 | -0.0688 | -0.06178 | -0.8649 | -0.70 |
| 5 | 0.3168 | 0.3047 | 0.3859 | 0.4556 | 0.5128 | 0.5632 | 7.885 | +0.61 |
| 6 | -1.785 | -1.819 | -1.922 | -2.04 | -2.145 | -2.228 | -31.19 | +0.24 |
| 7 | 14.67 | 15.67 | 16.88 | 18.07 | 19.16 | 20.15 | 282 | +0.33 |
| 8 | -129.1 | -139.9 | -154.4 | -167.8 | -179.8 | -190.4 | -2666 | +0.37 |

### Descendant residual L_-1 Lbar_-1 phi^2: E - E_2 - 2, orders 2..8

**raw**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.3617 | 0.2717 | 0.2407 | 0.2279 | 0.2233 | 0.223 | 0.2253 | 0.2292 | 3.667 | +0.13 |
| 3 | 0.4147 | 0.2525 | 0.2559 | 0.2905 | 0.3343 | 0.3811 | 0.429 | 0.4771 | 7.634 | +0.80 |
| 4 | -1.097 | -0.6906 | -0.4482 | -0.2948 | -0.184 | -0.09539 | -0.01977 | 0.04796 | 0.7673 | sign change |
| 5 | 3.401 | 2.883 | 2.421 | 2.139 | 1.967 | 1.868 | 1.812 | 1.787 | 28.59 | -0.11 |
| 6 | -20.47 | -20.97 | -20.07 | -19.42 | -19.16 | -19.22 | -19.55 | -20.07 | -321.2 | +0.20 |
| 7 | 141.3 | 144.1 | 143.8 | 142.6 | 141.9 | 142.1 | 143.2 | 144.9 | 2319 | +0.09 |
| 8 | -1146 | -1204 | -1252 | -1290 | -1326 | -1366 | -1409 | -1457 | -2.332e+04 | +0.25 |

**consistent**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.3432 | 0.2439 | 0.2036 | 0.1816 | 0.1677 | 0.1582 | 0.1512 | 0.1459 | 2.334 | -0.27 |
| 3 | 0.3365 | 0.1309 | 0.09088 | 0.082 | 0.08226 | 0.08563 | 0.09004 | 0.09469 | 1.515 | +0.38 |
| 4 | -1.194 | -0.8478 | -0.6654 | -0.5718 | -0.5208 | -0.492 | -0.4761 | -0.4681 | -7.489 | -0.13 |
| 5 | 3.283 | 2.675 | 2.118 | 1.734 | 1.458 | 1.253 | 1.092 | 0.9607 | 15.37 | -0.96 |
| 6 | -19.83 | -19.8 | -18.27 | -16.92 | -15.9 | -15.14 | -14.58 | -14.18 | -226.9 | -0.21 |
| 7 | 138.1 | 137.7 | 133.7 | 128.5 | 123.5 | 119.2 | 115.6 | 112.6 | 1802 | -0.20 |
| 8 | -1116 | -1141 | -1150 | -1141 | -1126 | -1110 | -1094 | -1080 | -1.728e+04 | -0.10 |

**zeromode**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2946 | 0.1962 | 0.1561 | 0.1343 | 0.1204 | 0.1109 | 0.104 | 0.09864 | 1.578 | -0.39 |
| 3 | 0.2131 | 0.009941 | -0.03046 | -0.0402 | -0.04086 | -0.03837 | -0.03478 | -0.03089 | -0.4942 | -0.89 |
| 4 | -1.258 | -0.8162 | -0.576 | -0.4455 | -0.3663 | -0.3136 | -0.2763 | -0.2483 | -3.973 | -0.80 |
| 5 | 2.635 | 2.27 | 1.702 | 1.304 | 1.033 | 0.8467 | 0.7153 | 0.6227 | 9.962 | -1.04 |
| 6 | -18.22 | -16.14 | -13.5 | -11.43 | -9.909 | -8.774 | -7.918 | -7.261 | -116.2 | -0.65 |
| 7 | 132.6 | 111.8 | 94.5 | 81.19 | 71.07 | 63.29 | 57.22 | 52.4 | 838.4 | -0.66 |
| 8 | -1119 | -892.7 | -729.6 | -617.4 | -536.4 | -476 | -429.5 | -393.1 | -6290 | -0.66 |

**complete2**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2356 | 0.1372 | 0.0972 | 0.07532 | 0.0615 | 0.05198 | 0.04501 | 0.6301 | -0.93 |
| 3 | 0.6362 | 0.4696 | 0.4723 | 0.5086 | 0.5548 | 0.6044 | 0.655 | 9.17 | +0.52 |
| 4 | -1.048 | -0.5651 | -0.2867 | -0.1162 | 0.006212 | 0.1046 | 0.1896 | 2.654 | +3.85 |
| 5 | 2.638 | 2.445 | 1.997 | 1.753 | 1.639 | 1.607 | 1.626 | 22.76 | +0.07 |
| 6 | -22.34 | -20.29 | -18.65 | -17.54 | -16.97 | -16.8 | -16.93 | -237.1 | +0.05 |
| 7 | 163.1 | 147.3 | 139.5 | 134.5 | 131.5 | 130.3 | 130.5 | 1827 | +0.01 |
| 8 | -1370 | -1307 | -1288 | -1288 | -1301 | -1325 | -1358 | -1.902e+04 | +0.16 |

**W**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2338 | 0.1365 | 0.0968 | 0.07508 | 0.06134 | 0.05185 | 0.04492 | 0.03962 | 0.6339 | -0.94 |
| 3 | 0.1789 | 0.03041 | 0.007419 | 0.007936 | 0.01454 | 0.02266 | 0.03085 | 0.03864 | 0.6182 | +1.68 |
| 4 | -0.4367 | -0.04288 | 0.1745 | 0.2915 | 0.362 | 0.4085 | 0.441 | 0.4649 | 7.439 | +0.40 |
| 5 | 3.131 | 1.732 | 0.8671 | 0.2801 | -0.1225 | -0.4084 | -0.6198 | -0.7804 | -12.49 | +1.73 |
| 6 | -16.55 | -12.84 | -9.054 | -6.036 | -3.681 | -1.833 | -0.3634 | 0.8269 | 13.23 | sign change |
| 7 | 119.9 | 94.56 | 73.61 | 55.41 | 40.25 | 27.72 | 17.34 | 8.654 | 138.5 | -5.20 |
| 8 | -999.4 | -820.4 | -668.9 | -531.8 | -412.1 | -309.3 | -221.2 | -145.4 | -2327 | -3.14 |

**WB**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2338 | 0.1365 | 0.0968 | 0.07508 | 0.06134 | 0.05185 | 0.04492 | 0.03962 | 0.6339 | -0.94 |
| 3 | 0.1789 | 0.03041 | 0.007419 | 0.007936 | 0.01454 | 0.02266 | 0.03085 | 0.03864 | 0.6182 | +1.68 |
| 4 | -0.4369 | -0.04285 | 0.1745 | 0.2915 | 0.362 | 0.4085 | 0.441 | 0.4649 | 7.439 | +0.40 |
| 5 | 3.124 | 1.735 | 0.8681 | 0.2805 | -0.1223 | -0.4083 | -0.6198 | -0.7804 | -12.49 | +1.73 |
| 6 | -16.26 | -12.84 | -9.072 | -6.05 | -3.692 | -1.842 | -0.3715 | 0.8196 | 13.11 | sign change |
| 7 | 116.8 | 93.35 | 72.97 | 54.96 | 39.88 | 27.41 | 17.06 | 8.398 | 134.4 | -5.31 |
| 8 | -964.6 | -806 | -658.7 | -524.2 | -406 | -304.1 | -216.6 | -141.4 | -2262 | -3.20 |

**W+V**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L=16 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.002315 | 0.001302 | 0.0009042 | 0.0006923 | 0.0005608 | 0.0004712 | 0.0004063 | 0.0003571 | 0.005713 | -0.97 |
| 3 | 0.8367 | 0.9108 | 0.89 | 0.8662 | 0.8476 | 0.8342 | 0.8249 | 0.8188 | 13.1 | -0.06 |
| 4 | -1.156 | -2.513 | -3.233 | -3.702 | -4.065 | -4.382 | -4.678 | -4.965 | -79.45 | +0.45 |
| 5 | 2.388 | 7.968 | 12.02 | 15.11 | 17.65 | 19.88 | 21.91 | 23.84 | 381.5 | +0.63 |
| 6 | -2.64 | -29.4 | -54.77 | -76.69 | -96.27 | -114.5 | -132 | -149.1 | -2386 | +0.92 |
| 7 | 6.654 | 107.3 | 260.8 | 416.2 | 568.4 | 718.9 | 869.6 | 1022 | 1.635e+04 | +1.21 |
| 8 | -134.1 | -432.9 | -1296 | -2336 | -3463 | -4656 | -5907 | -7221 | -1.155e+05 | +1.50 |

**WnoM**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2946 | 0.1962 | 0.1561 | 0.1343 | 0.1204 | 0.1109 | 0.104 | 1.455 | -0.42 |
| 3 | 0.3254 | 0.1042 | 0.05678 | 0.04325 | 0.04022 | 0.04108 | 0.04349 | 0.6088 | +0.37 |
| 4 | -0.4826 | -0.3361 | -0.1458 | -0.03193 | 0.04212 | 0.09477 | 0.1347 | 1.886 | +2.28 |
| 5 | 3.611 | 2.419 | 1.939 | 1.615 | 1.41 | 1.288 | 1.22 | 17.07 | -0.35 |
| 6 | -19.05 | -16.74 | -13.82 | -11.66 | -10.03 | -8.783 | -7.809 | -109.3 | -0.76 |
| 7 | 139.1 | 123.5 | 110.2 | 98.25 | 88.39 | 80.49 | 74.14 | 1038 | -0.53 |
| 8 | -1157 | -1071 | -992.3 | -915.5 | -847.3 | -789.3 | -740.9 | -1.037e+04 | -0.41 |

**WM2**

| n | L=2 | L=4 | L=6 | L=8 | L=10 | L=12 | L=14 | L*R (last) | p_eff (last pair) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.2338 | 0.1365 | 0.0968 | 0.07508 | 0.06134 | 0.05185 | 0.04492 | 0.6288 | -0.93 |
| 3 | 0.2935 | 0.1417 | 0.119 | 0.1204 | 0.128 | 0.1372 | 0.1463 | 2.049 | +0.42 |
| 4 | -0.5301 | -0.3216 | -0.1593 | -0.0728 | -0.02295 | 0.008117 | 0.02841 | 0.3977 | +8.13 |
| 5 | 3.67 | 2.365 | 1.778 | 1.406 | 1.176 | 1.035 | 0.9505 | 13.31 | -0.55 |
| 6 | -19.36 | -16.48 | -13.24 | -10.84 | -9.057 | -7.701 | -6.659 | -93.23 | -0.94 |
| 7 | 140.1 | 122.2 | 106.8 | 93.02 | 81.77 | 72.74 | 65.46 | 916.5 | -0.68 |
| 8 | -1164 | -1062 | -968.9 | -879.3 | -800.1 | -732.6 | -676.1 | -9465 | -0.52 |



## 10. Cluster jobs

All heavy runs on symmetry (Slurm), work dir `<SCRATCH>/indep2d/complete_exact/{code,out,logs,jobs}`,
venv `~/indep2d_rs/venv` used read-only (Python 3.11, numpy 2.4.6, scipy 1.17.1). Every job: `--nodes=1 --exclusive`,
`--mem=240G`, names `indep2d-ce-*`. Logs copied to `logs/`, outputs to `raw_out/`. Jobs before 572114 computed the W family with the earlier
reading (B-equation in the auxiliary channels); those results are reported as WB, W+VB, W2B, WnoMB. Light runs on
the Mac (seconds):
L <= 4 development tests, the Fraction check at L = 2, 4, bookkeeping, exports, fits.

| job | name | partition / node | content | wall | outcome | log |
|---|---|---|---|---|---|---|
| 571939 | indep2d-ce-main | amddebugq <NODE> | L = 0..12, all schemes and variants + garbage, 96 primes (first pass; superseded by 571946) | 8:51 | completed | logs/indep2d-ce-main_571939.out |
| 571940 | indep2d-ce-main14 | amddebugq <NODE> | L = 14, all variants + garbage, 96 primes (old cache code); W+Vn, W2, W2n merged into prod_L14 | 51:05 | completed | logs/indep2d-ce-main14_571940.out, logs/time_main_L14.txt |
| 571943 | indep2d-ce-frac | amddebugq <NODE> | Fraction implementation, L = 4, 6, 8, 10 x {raw, consistent, zeromode, W, W+V} (check c) | 45:38 | completed | logs/indep2d-ce-frac_571943.out, logs/frac_<S>_L<L>.log |
| 571946 | indep2d-ce-prod | amddebugq <NODE> | production L = 0..12 (208 primes, garbage test, all variants); closure extension (ext) and complete2 (c2) L = 0..12 | 15:45 | completed | logs/indep2d-ce-prod_571946.out, logs/{prod,ext,c2}_L<L>.log |
| 571947, 571970, 571971 | indep2d-ce-prod14[c0,c1] | amddebugq <NODE>, <NODE> | L = 14 production, first attempts | 13:07, 12:05, 5:35 | cancelled (memory: per-(channel, order) D^zm cache) | logs/indep2d-ce-prod14*_*.out |
| 571948/9, 571954-57, 571972-79, 571985, 572011, 572012, 572020 | indep2d-ce-prod16*, -p14c2, -p16, -q16 | amddebugq / amdq | L = 16 (and one L = 14) submissions | 0 | cancelled before start (re-sized or superseded) | – |
| 572009, 572010 | indep2d-ce-p14c0/c1 | amddebugq <NODE>, <NODE> | L = 14 (LOWMEM attempt) | 1:46, 1:14 | cancelled for the cache fix | – |
| 571980 | indep2d-ce-c2ext14 | amddebugq <NODE> | complete2 with 10 t-points, L = 2..14; closure extension at L = 14 | 24:32 | completed | logs/indep2d-ce-c2ext14_571980.out, logs/{c2t10,ext}_L<L>.log |
| 571981 | indep2d-ce-diag | amddebugq <NODE> | diagnostic variants WM2, WM3, L = 2..12 | 2:19 | completed | logs/indep2d-ce-diag_571981.out |
| 572018, 572019 | indep2d-ce-q14c0/c1 | amddebugq <NODE>, <NODE> | L = 14 production, 128 primes in 2 chunks, garbage test (W, W+V, zeromode, consistent) | 8:14, 18:20 | completed | logs/indep2d-ce-q14c{0,1}_*.out |
| 572034, 572035 | indep2d-ce-q16c0/c1 | amddebugq <NODE>, <NODE> | L = 16, 128 primes in 2 chunks: raw, consistent, zeromode and the earlier reading (now WB, W+VB), garbage (WB) | 39:23, 32:40 | completed | logs/indep2d-ce-q16c{0,1}_*.out |
| 572036 | indep2d-ce-q18 | amdq | L = 18 (raw, consistent, zeromode, W) | – | cancelled before start (amdq queue; ~6 h of node time needed) | – |
| 572114 | indep2d-ce-newA | amddebugq <NODE> | rerun after the 2026-10-09 spec change: W, W+V, W2, WnoM, WM2, WM3 (+ garbage), L = 0..12, 208 primes | 12:02 | completed | logs/indep2d-ce-newA_572114.out, logs/time_new_L<L>.txt |
| 572115 | indep2d-ce-newext | amddebugq <NODE> | closure extension, W and W+V, L = 0..12 | 7:00 | completed | logs/indep2d-ce-newext_572115.out |
| 572116, 572117 | indep2d-ce-new14c0/c1 | amddebugq <NODE>, <NODE> | L = 14: W, W+V, WnoM, WM2 (+ garbage W, W+V), 128 primes | 15:29, 15:18 | completed | logs/indep2d-ce-new14c{0,1}_*.out |
| 572118 | indep2d-ce-newext14 | amddebugq <NODE> | closure extension, W and W+V, L = 14 | 19:01 | completed | logs/indep2d-ce-newext14_572118.out |
| 572119, 572120 | indep2d-ce-new16c0/c1 | amddebugq <NODE>, <NODE> | L = 16: W, W+V (+ garbage W), 128 primes | 24:24, 24:21 | completed | logs/indep2d-ce-new16c{0,1}_*.out |
| 572121 | indep2d-ce-newfrac | amddebugq <NODE> | Fraction implementation, W and W+V (new definition), L = 4..10 | 33:29 | completed | logs/indep2d-ce-newfrac_572121.out, logs/frac_W*_L<L>.log |

Memory note: per worker the W runs need ~1-3 GB at L = 12-14 (after the compact D^zm cache of sec. 3); the first
L = 14 attempts held a per-(channel, order) cache and ran out of memory with 48-64 workers (cancelled, rerun).

