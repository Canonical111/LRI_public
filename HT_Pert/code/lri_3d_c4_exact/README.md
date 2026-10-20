# Exact finite-cutoff C_4(L) of the 3D LRI Hamiltonian truncation (lri_3d_hpc model), large L, window schemes

Model: the package `../lri_3d_hpc` (reference/perturbative.py, reference/taylor_vertices.py): GFF on S^2,
x = (3 - eps)/4, eps = 2s - 3; modes (n, l, m), level N = 2n + l, energy x + N; zero mode Z = local oscillator;
H = H0 + r M + g V (+ window D), M = int dOmega :phi^2:/(4 pi), V = int dOmega :phi^4:/(48 pi); bath cutoff
N_bath <= L; tuning E1 - E0 = x, E3 - E0 = 3 - x; Delta_E = E2 - E0 = 3/2 - eps/6 + sum C_n eps^n.
Continuum targets: C2(3) = (2 + 4 ln 2 - pi)/9, C3(3) = -0.353581520433, C4(3) = 1.22806354532762307997
(condensed note; LRI_C5_d3/inputs/three_dimension_addition.tex).

## Bottom line (2026-10-12; eps^5 item 6 added 2026-10-13)

1. **Exact calculator, validated.** C2(L), C3(L), C4(L) of the package's model, raw and consistent, are computed as
   exact diagram sums (float64 level sums with exact zero-mode amplitudes and exact Pi projections). They agree with
   the package through L = 20 (C4 to 8.9e-14) and, with a zero-mode-dependent eps^2 window, with the package's own
   reference RS solver (L <= 6, 1.2e-14). Full C4 reached **L = 600** (one symmetry node, 33 min); the two-vertex
   window shifts reached **L = 8000** (cancellation-free, ~1e-15).
2. **Both package schemes diverge at eps^4** (C2 and C3 converge to the continuum: C2 to 1e-16, C3 to ~5e-8):

   | scheme | C4(L = 600) | large-L form (coefficients from the exact window data) |
   |---|---|---|
   | raw | -8.4894 | consistent - 2.13504e-5 L^2 - 8.6967e-5 L - 1.074e-4 sqrt(L) - ... |
   | consistent (package) | -0.7485 | C4(3) - 7.4327e-5 L - (16/(729 sqrt(pi))) sqrt(L) ln L + 1.14e-3 sqrt(L) + O(1) |
   | + diagonal zero-mode window | +0.4238 | C4(3) - (32/(3645 sqrt(pi))) sqrt(L) ln L - 5.35e-4 sqrt(L) + O(1) |
   | + off-diagonal zero-mode window | +1.2085 | C4(3) - 3.614e-4 sqrt(L) + O(1) |
   | **+ chi-attached sunset window = W** | **+1.2174** | **C4(3) + O(1/L): no divergence** |

   16/(729 sqrt(pi)) = 10/(243 Gamma(7/2)) = 0.0123828, 32/(3645 sqrt(pi)) = 4/(243 Gamma(7/2)) = 0.0049531.
3. **The complete window of the 2D derivation also fixes 3D.** With every window of the 2D residual-log analysis
   (vacuum + full zero-mode Bloch window incl. Delta z = +-2 + leading-order chi-attached sunset window
   D_chi = -(1/2) r2'(L) {N, M'}), C4^W(L) converges with corrections starting at 1/L:

       C4^W(inf) = 1.22807 +- 0.00002     (continuum C4(3) = 1.2280635453)

   Stable towers give A - C4(3) = +1.5e-6 .. +3.4e-5 over Lmin = 80..300 (T4: +3.5e-6 .. +8.3e-6); a blind fit on
   L <= 400 predicts 400 < L <= 600 to 1.6e-8 with A - C4(3) = -7e-6; with A fixed at C4(3) every free extra
   divergent term is zero within the data (ln L: 6e-7, sqrt(L): 6e-8, L: 8e-10). Independently, fitting the
   zero-mode-windowed scheme alone with a free sqrt(L) term gives -3.616e-4, -3.608e-4, -3.617e-4 (Lmin = 100, 150,
   200), minus the chi window's +3.6136e-4: the residual divergence after the zero-mode window is exactly the
   chi-attached sunset window.
4. **Mechanism (same as 2D, one power worse).** The level cutoff limits each sub-bubble to L - (level of the
   spectators), while r, g and E_vac are tuned with the full budget. In 3D the sunset (mass) divergence is
   r2(L) = (6/(243 Gamma(7/2))) L^(3/2) + ... (fit 0.0074296570 vs 0.0074296571), so its deficit grows like
   L^(1/2) N_spectator: the 2D ln L terms become sqrt(L) ln L and sqrt(L), and the 2D finite chi-window shift
   (+0.0103) becomes a sqrt(L) divergence (+3.614e-4 sqrt(L)). Class by class (Sec. 5): L^2 from 1 chi x vacuum
   bubble (consistent window), L from 4 chi x 1-line zero-mode bubble (7.43267e-5, diagonal zero-mode window),
   sqrt(L) ln L only from 2 chi x zero-mode sunset, split 6 : 4 between Delta z = 0 and Delta z = +-2, matching the
   analytic 6/(243 Gamma(7/2)) and 4/(243 Gamma(7/2)) to 1e-9. The diagonal ("zeromode") window alone is not enough.
5. **Open.** (i) The chi window is used in its leading-order linear form; in 3D r2 is not linear, so its
   exact (per-ordering) form may differ by a finite amount. The agreement with C4(3) to ~1e-5 suggests the
   difference vanishes or is small, but this is not derived. (ii) eps^5: see item 6. (iii) No production package
   change was made.
6. **eps^5 (Sec. 7, 2026-10-13).** Exact C5(L) in every scheme (raw, consistent, Zb, W2, W3m, Wb, Wc, Wcs), validated
   against the package (L <= 20, 2.2e-13) and an independent brute force with explicit window operators (L <= 14,
   ~2e-13); raw C5 to **L = 40**, exact window shifts to L = 600. With L <= 40:
   * **Wc (and Wcs) are consistent with C5(3)**: C5^Wc(inf) = -6.0 +- 0.3 against -5.850 (towers that pass the C4^W
     calibration and the blind test give A - C5(3) in [-0.44, -0.02]; full spread of all towers [-7.8, +18.5], without
     the unstable long tower [-6.85, -5.43]). This is a 5-7% test, not a confirmation: C5^Wc(40) is still 1.28 above
     the limit, and an L^-1/2 correction (not excluded at L <= 40) would move the limit 0.5-1.0 lower.
   * Wb and W2 diverge (as in 2D), consistent and raw diverge; Zb is also consistent at this resolution but Zb - Wc
     grows like L^2 (+2.2 at L = 600), so L <= 40 cannot separate them.
   * delta^(3)(L) grows (~ -0.005 sqrt(L); 2D: constant), so Wcs - Wc = delta3 S ~ -6.7e-4 sqrt(L): Wc and Wcs cannot
     both converge, but the difference (-0.0035 at L = 40) is far below the resolution.
   * T3 (chi_11, exact, L <= 16): R2 -> 0 in Wc; Wc R3 is flat at 0.022 and turns up at L = 16 because the external-leg
     budget grows like sqrt(L); Wcs tracks the budget-free legs (0.0152 vs 0.0156 at L = 16), but the budget-free R3
     itself falls only slowly (0.0204 -> 0.0156), so R3 -> 0 is not shown in 3D.
   * Beyond L = 40 the cost (~L^8.4) and memory (parallel-merge state lists ~L^4.5: 6.3 GB per worker at L = 40,
     18 GB at L = 56) need a new angular-channel representation; L = 56 was dropped.

---------------------------------------------------------------------------------------------------------

## 1. Files

| file | role |
|---|---|
| `c4lib3d.py` | diagram engine: mode tables (mpmath), Gauss-Legendre bundle partial waves, zero-mode paths (exact rationals), 3D angular reductions (2, 3, 4 vertices), cropped half-level grids, shell sums, `Lin` (exact zero-mode amplitudes) |
| `c4_compute3d.py` | assembly of r2, g2, r3, g3, C2, C3, C4 raw/consistent (`compute_exact`: every Pi/tuning projection on exact amplitudes) |
| `c4_run3d.py` | production driver (one task per mirror-reduced four-vertex pattern, process pool, checkpoints) |
| `windows3d.py` | C2(L), E_v^(2)(l), Delta_cons = C4cons - C4raw, Delta_zm (diagonal zero-mode window), cancellation-free, closed-form l = 0 densities, to L = 8000 |
| `offdiag3d.py` | full zero-mode window incl. Delta z != 0 (port of the 2D residual_log/offdiag_window.py), class-resolved, to L = 8000 |
| `dchi3d.py` | leading-order chi-attached sunset window of the 2D derivation, -(1/2) r2'(L) {N, M'}, its C4 shift |
| `brute_zm.py` | brute force with the package's own reference RS solver: raw, consistent and zero-mode-window C4 at small L |
| `validate_pkg.py` | comparison with the package results (reference L = 0..14, campaign L = 16..20) |
| `fitlib3d.py`, `fits_c4.py`, `fits/` | asymptotic fits, blind tests; `fits/fit_summary.txt` |
| `C4_by_L.csv` | deliverable table: every even L, C2, C3, C4 in every scheme, Delta_cons |
| `results/` | npz outputs (c4_L<Lmax>, windows_L8000, offdiag_L8000, dchi_L600, brute_zm_L6.json) |

## 2. Derivation

### 2.1 Fourth-order RS
Identical structure to the 2D project (../../lri_2d_coeff_expanse/independent_check/c4_exact/README.md Sec. 2.1):
H = H0 + eps W1 + eps^2 W2 + ..., W1 = -P/4 + g1 V (r1 = 0, g1 = 1/3), W2 = r2 M + g2 V + g1 V1 + D2,
W3 = r3 M + g3 V + g2 V1 + g1 V2 + r2 M1 + D3 (V_k = [eps^k] V(eps), through the mode amplitudes only);
E_p^(n) = X_p^(n) + 2p r_n + p(p-1)/2 g_n, r_n = -(X_1 - X_0)/2, g_n = -(X_3 - X_0 + 6 r_n)/3,
C_n = Pi[X^(n)], Pi f = f(2) - f(1) - (f(3) - f(0))/3. Only the eps^2 window D2 reaches C_4, through
g1^2 <V R D2 R V> (consistent: D2(N) = g1^2 [e(L) - e(L - N)], e(l) = <0|V R V|0>_l).
H0 = N_bath + x0 P_total, x0 = 3/4: slice denominators den = N + (3/4)(delta + n_lines). No intermediate state is
degenerate with |p>, p <= 3 (den = 0 needs an odd level, excluded by inversion parity).

### 2.2 Bath lines and angular integrals (3D)
phi = Z + chi. A bath line between vertices i, j carries u^[a]_{nl} u^[b]_{nl} (2l+1) P_l(Omega_i . Omega_j)
(a, b = eps-Taylor orders at its ends; u^2 = (x)_{n+l} (x - 1/2)_n/(n! (3/2)_{n+l}); at fixed N the sum over
l is the Gegenbauer polynomial C_N^(x)(t), generating function (1 - 2rt + r^2)^(-x)). A bundle of n lines at total
level N is B(N; t) = sum_l beta[N, l] P_l(t), beta from Gauss-Legendre projection of the product of the line series
(exact quadrature). Angular integrals:
* 2 vertices: beta[N, 0];
* 3 vertices (bundles 01, 02, 12): sum_l beta01 beta02 beta12 / (2l + 1)^2;
* 4 vertices: forests -> l = 0 parts; one cycle of length k -> single l channel, factor (2l + 1)^-(k-1);
  K4 minus an edge -> channels (l_c, l_d) with the Gaunt-combined array of the shared edge
  A_ab[a] = sum_l0 beta_ab[a, l0] int dt/2 P_l0 P_lc P_ld (quadrature, exact).
  K4 itself needs >= 6 lines and does not contribute to C_4: the zero-mode amplitude of a four-V chain with n bath
  lines has degree 8 - n in p and Pi kills degree <= 2 (verified: C4 agrees with the package).
Every slice level is even (inversion parity); in every angular channel each bundle has one level parity, so grids are
built in half-level coordinates on the cropped support only. The density does not depend on L; shell sums over the
maximal slice level give every cutoff at once.

### 2.3 Exact zero-mode projections
Every chain is kept as a list of (exact zero-mode amplitudes for p = 0..3, float level sum). Pi and the tuning
functionals act on the exact amplitudes before any float sum (`Lin` in c4lib3d.py), so the p-independent vacuum
bubbles (~ l^3) never enter C_n. Products (the -g1^4 <VRV><VR^2V> term) are taken key by key.

### 2.4 Windows (two-vertex sums, cancellation-free)
E_v^(2)(l) = g1^2 e(l) = -(l + 2)(l + 4)(l + 6)/7776 exactly (cf. 2D: -(l + 2)(l + 4)/864).
The l = 0 multi-line densities have the closed form
(1/2) int dt (1 - 2rt + r^2)^(-kx) = [(1 + r)^a - (1 - r)^a]/(4r(1 - kx)), a = 2 - 2kx,
evaluated in mpmath (the quadrature route loses ~N^(5/4) eps to the oscillatory angular integral: 1e-11 at L = 300).
Zero-mode windows (2D residual_log Sec. 2.2): D_l(z -> z') = g1^2 sum_{k: l - N < level(k) <= l}
<z'|V|k><k|V|z>/(E_z - E_k) inserted into every outer state of chi level N; z' = z is the "zeromode" scheme of the 2D
project, z' != z the off-diagonal part.

## 3. Validation

| check | range | worst deviation | where |
|---|---|---|---|
| C2, C3, r2, g2, r3, g3, all E_p^(2), E_p^(3) vs package (long double) | L = 0..20 | 6e-17 (C2), 2e-15 (C3), 1.7e-13 (r3, g3; package-side precision) | `validate_pkg.py` |
| C4 raw and consistent vs package | L = 0..20 | 8.9e-14 | `validate_pkg.py` |
| raw, consistent and zero-mode-window C4 vs package reference solver with a zero-mode window (brute_zm.py) | L = 0..6 | 1.2e-14 | `results/brute_zm_L6.json` |
| Delta_cons: full engine vs windows3d (independent route) | L <= 300 | 9e-11 | fits_c4.py header |
| diagonal part of offdiag3d vs windows3d Delta_cons + Delta_zm | L <= 400 | 4e-15 | |
| l = 0 bundle densities: closed form vs mode tables (m = 1) | L <= 300 | bitwise | |
| C2 limit (fit, L <= 8000) vs (2 + 4 ln 2 - pi)/9 | | 1.4e-16 | fits |
| C3 limit (fit, L <= 600) vs C3(3) | | ~2e-7 | fits |
| run-to-run overlap (different L_max, quadrature) | | see Sec. 4 | |

## 4. Data (`C4_by_L.csv`: every even L <= 600)

| L | C3 | C4 raw | C4 consistent | C4 zm (diag) | C4 zm (full) | C4 W |
|---|---|---|---|---|---|---|
| 20 | -0.3298433574 | 0.72930667 | 0.74000784 | 0.86391725 | 0.96775787 | 0.96887651 |
| 50 | -0.3447990385 | 0.66991572 | 0.72832578 | 0.94489878 | 1.10522068 | 1.10757595 |
| 100 | -0.3495939963 | 0.34843041 | 0.57162335 | 0.91736625 | 1.16145474 | 1.16497936 |
| 200 | -0.3517882293 | -0.62097116 | 0.25186994 | 0.80833464 | 1.19091682 | 1.19599242 |
| 300 | -0.3524573205 | -1.98225432 | -0.03285699 | 0.70120679 | 1.20038484 | 1.20662549 |
| 400 | -0.3527733320 | -3.74306249 | -0.29015320 | 0.60212959 | 1.20476454 | 1.21198092 |
| 500 | -0.3529552243 | -5.91054591 | -0.52715016 | 0.51009709 | 1.20712838 | 1.21520183 |
| 600 | -0.3530726157 | -8.48937310 | -0.74850669 | 0.42384281 | 1.20850347 | 1.21735055 |

C4 raw / consistent peak at L ~ 28 / 32 (0.7393 / 0.7592) and then fall. Precision: the full engine reproduces
itself between runs with different L_max (different quadratures) to 7e-10 (C4, L <= 300) and Delta_cons agrees
with the cancellation-free route to 5e-9 at L <= 600 (the loss is the oscillatory angular quadrature, ~N^(5/4) eps).
The zero-mode and chi window columns use the cancellation-free two-vertex and three-vertex codes.

## 5. Window classes (`fits/window_classes.txt`, fits 1600 <= L <= 8000, residuals <= 3e-14 except vacuum 9e-12)

| class (outer chi lines x inner bubble) | C4 shift at L = 8000 | leading terms |
|---|---|---|
| 1 chi x vacuum bubble (consistent window) | 1367.08 | 2.13504e-5 L^2 + 8.6967e-5 L - 5.09e-4 sqrt(L) |
| 4 chi x 1-line zero-mode bubble, Delta z = 0 | 0.5806 | 7.43267e-5 L - 1.61e-4 sqrt(L) |
| 2 chi x zero-mode sunset, Delta z = 0 | 4.7499 | 0.00742966 sqrt(L) ln L - 0.013687 sqrt(L)  [6/(243 G(7/2)) = 0.0074296571] |
| 2 chi x zero-mode sunset, Delta z = +-2 | 3.1623 | 0.00495311 sqrt(L) ln L - 0.009172 sqrt(L)  [4/(243 G(7/2)) = 0.0049531047] |
| 1 chi x zero-mode sunset (Delta z = 0 / +-2) | 0.329 / 0.292 | 3.674e-3 / 3.267e-3 sqrt(L) |
| 3 chi x 2-line bubble (Delta z = 0 / +-2) | 0.814 / 0.543 | 9.119e-3 / 6.080e-3 sqrt(L) |
| all other classes | < 4e-4 | convergent |
| chi-attached sunset window (leading order, dchi3d) | (L = 1000) 0.0115 | 3.6136e-4 sqrt(L) + O(1) |

No class has a ln L term (all fitted ln L coefficients <= 1.5e-5). Derivation of the sqrt(L) ln L coefficients
(2D README Sec. 2.3 with 3D densities): the sunset density is rho_3(n) -> n^(3/2)/Gamma(7/2) at even n, so the
window of the nested sunset at outer level N is -(L^(1/2) N)/(2 Gamma(7/2)) per unit level; the soft 2-chi outer
weight is 1/N^2 (rho_2 -> 1), so the window sum is -L^(1/2) ln L/(4 Gamma(7/2)); the zero-mode amplitude 20 p^3
splits 12 (Delta z = 0) + 8 (Delta z = +-2), with g1^4 c2 c3 = 1/243 and Pi(p^3) = -2. Hence 6/(243 G(7/2)) and
4/(243 G(7/2)). The same constant is the L^(3/2) coefficient of r2.

## 6. Cluster jobs (symmetry; work dir <SCRATCH>/ht3d_c4exact, venv there, logs in logs/)

| job | partition | what | state |
|---|---|---|---|
| 573801, 573802 | debugq | timing L = 60, 100, 140 | done (573801 FAILED after its outputs on a script typo) |
| 573804 | debugq | full L = 200, 300 | COMPLETED (34 s, 174 s) |
| 573805, 573806, 573808 | debugq | windows3d/offdiag3d L = 4000 / 8000 | 573808 COMPLETED (Gegenbauer-route 573805/6 superseded) |
| 573807 | preq | full L = 600 | cancelled (multiprocessing /dev/shm failure on <NODE>) |
| 573810, 573815 | preq | full L = 600 / 1000 (unsplit) | cancelled: K4-minus-edge tasks ~L^6, single-worker |
| 573812, 573817 | debugq | dchi3d L = 600, 1000 | COMPLETED |
| **573841** | preq | **full L = 600 (split K4-minus-edge tasks)** | **COMPLETED, 1953 s** |
| 573842 | defq | full L = 1000 | cancelled by me after 17 min (estimated 15-20 h; not needed for the conclusion); its partial cache is in cache/L1000 |

Reproduce: `sbatch -p preq --exclude=<NODE> -t 06:00:00 --export=ALL,LS=600,W=20,TH=2 run_L.sbatch` (in the work dir;
L = 1000 needs ~15-20 h on one 40-core node), `win2.sbatch` (LM=8000), `dchi.sbatch` (LM), then locally
`python3 fits_c4.py && python3 window_classes.py`.

---------------------------------------------------------------------------------------------------------

## 7. eps^5 in 3D: exact C5(L) in every scheme, windows Wc and Wcs (2026-10-12/13)

Task: transcribe the 2D residual_log Secs. 9-11 (WINDOW_SPEC 2.2a rule Wc, 2.5a rule Wcs) to the 3D model; exact C5(L)
validated against the package and an independent brute force; the largest affordable L; asymptotics; descendant
identity (T3). Code in `eps5/`, analysis in `fits/fits5_summary.txt`, `fits/t3_summary.txt`.

### 7.1 Code

| file | role |
|---|---|
| `eps5/engine.py` | 3D diagram engine with the API of the 2D eps5 engine: modes (n, l, m) with eps-Taylor tables to order 3, line patterns, exact zero-mode paths; partial-wave reduction of any K <= 5 pattern (series, parallel with (l1 l2 l; 000)^2, degree-1 vertex -> l = 0, K4 core -> T = prod_v (3j 000)_v {6j} (-1)^(sum l) from an exact integer Racah sum); channel groups streamed with one bundle pre-summed and built on completion; the 7-line 5-vertex patterns reduced to cached 4-vertex boxes (K4 + pendant/isolated vertex: diagonal slice embedding + l = 0 line; series vertex: phantom-edge box resolved by l) |
| `eps5/rs.py`, `chains.py`, `assemble.py`, `windows5.py`, `windowsW.py`, `schemeW.py`, `bloch.py` | ported from 2D (model independent: RS words, Pi, tuning, decorated window words, Bloch h = X Lambda X^-1, schemes W2 W3m W3e Wb Zb Wc), x0 = 3/4 patched in |
| `eps5/prod5.py` | C2..C5(L) for every L <= Lmax, raw and every scheme (`--raw_only`, `--pclass sp`, `--shard`) |
| `eps5/delta5.py` | exact scheme shifts dC5^S = C5^S - C5^raw (window sums only) |
| `eps5/legw3d.py` | S(L), the C5 response to (1/2) X_0 at eps^3: C5^Wcs = C5^Wc + delta^(3)(L) S(L) |
| `eps5/brute3d_W5.py` | independent brute force on the package's reference operators (perturbative.BareSeries, build_taylor_vertices) with every window as an explicit operator (raw W2 W3m Wb Wc Zb Wcs) |
| `eps5/brute3d_tag.py` | tagged phi channel: c1tag(L; nu), delta^(3)(L) |
| `eps5/brute3d_desc.py`, `brute3d_tagchi.py` | descendant identity for chi_11 by scheme; chi_11 with its external legs tagged (budget-free nu = (0,0), charged (2,2) = Wc, single leg) |
| `eps5/validate5.py`, `regress5.py`, `regress_boxes.py` | package / brute-force validation; regression of a new run against stored npz files and of cached boxes |
| `eps5/fits5.py`, `t3.py` | asymptotics, extrapolation with calibration, descendant analysis |
| `eps5/prof5.py`, `prof_heavy.py`, `memprobe.py`, `memprobe_box.py` | cost and memory model |

3D choices (no alternative was needed except where stated): chi_11 is the (n = 1, l = 0) quantum (level 2, the
scalar descendant Box phi), so delta^(3) = (1/4)[c1^(3)(L - 2) - c1tag^(3)(L; 2, 2)] keeps the 2D form; X weights a
chi leg by its level N = 2n + l; the Bloch recursion uses (z - z')/2 -> x0 (z - z'); zero denominators from
degenerate zero-mode partners (z >= 9) are dropped in every window object (WINDOW_SPEC 2.10), and the 2D partner terms
of E_z^(3) (below 2e-6 in 2D) are not included. The tagged chi channel (budget-free external legs) is the
alternative, exact slice-resolved definition of the leg window and is used as the T3 reference.

### 7.2 Validation (all passed)

| check | range | worst deviation |
|---|---|---|
| raw and consistent C2..C5 vs package (reference L <= 14, campaign L = 16..20) | L = 0..20 | C5 2.2e-13 (scaled), C4 5.9e-14 (`results/eps5/validation_L20.txt`) |
| W2, W3m, Wb, Wc, Zb (C2..C5) vs brute force with explicit window operators | L = 2..14 | C5 ~2e-13 |
| Wcs - Wc = delta^(3) S: legw3d S(L) vs brute force (Wcs at delta3 = 1 minus Wc) | L = 2, 4, 6 | all digits |
| delta5 shifts vs prod5 differences | L <= 20 | 5.9e-13 |
| shifts, run with Lmax = 600 vs Lmax = 200 (different quadratures) | L <= 200 | dC5 1.4e-9 (r5 1.4e-6 of 1e4) |
| tagged chi channel with nu = (2,2) vs real chi_11 in Wc (R2, R3) | L = 6..14 | 4e-16 |
| c1tag(L; 0, 0) = c1(L) through eps^3 | L <= 6 | exact |
| engine speed-ups (exact Racah, streaming, K4 / series reductions) vs the pre-optimization engine, densities | random patterns L = 8, 10 | <= 1e-15 |
| regression of the memory-fixed engine (code 3b7f80d) vs the stored L = 20 run, all 144 arrays (C, r, g of 12 schemes) | L = 0..20 | 5.1e-13 absolute (W3e C5; C5 ~ -4.4: 1.2e-13 relative); C4 3.4e-14; `--pclass sp` run 1.5e-13 (`results/regress/`) |
| cached L = 40 reduced boxes (11, from code af96c59 and later) recomputed with code 3b7f80d (574030) | L = 40 | bitwise identical |
| all 34 reduced boxes used by the final L = 40 run (574287) recomputed with its code d45be4c, one box per process on a defq node (574365) | L = 40 | 34/34 bitwise identical (max relative deviation 0) |
| final L = 40 run vs the L = 20 run, raw C2..C5 | L <= 20 | C5 6.8e-13, C4 8.9e-14 |

### 7.3 C5(L) to L = 20 (exact; `results/c5_L20.npz`)

| L | raw | consistent | Zb | W2 | Wb | Wc | Wcs (delta3 exact) |
|---|---|---|---|---|---|---|---|
| 10 | -2.7037661 | -2.6954162 | -3.1544274 | -3.4768412 | -3.2245381 | -3.1704028 | -3.1714249 |
| 12 | -2.8814865 | -2.8708672 | -3.3337698 | -3.6844495 | -3.4250359 | -3.3535541 | -3.3548388 |
| 14 | -3.0372714 | -3.0241600 | -3.4910338 | -3.8742847 | -3.6042768 | -3.5144027 | -3.5159233 |
| 16 | -3.1732333 | -3.1574130 | -3.6288891 | -4.0475313 | -3.7649364 | -3.6557091 | -3.6574449 |
| 20 | -3.3981844 | -3.3763152 | -3.8594320 | -4.3539820 | -4.0433066 | -3.8927062 | -3.8948097 (delta3(20) modelled) |

Continuum C5(3) = -5.85035142. C5^Wc(20) - C5(3) = +1.96 (C4^W(20) - C4(3) = -0.26): the finite-cutoff corrections
at eps^5 are 8x larger than at eps^4. At L <= 20 no extrapolation is meaningful (Sec. 7.6: the full tower spread is
-1.3 .. +0.6, and the same protocol on C4^W at L <= 20 misses C4(3) by up to 0.10).

### 7.4 Scheme shifts to L = 600 (exact window sums, `results/dC5_L600.npz`)

dC5^S(L) = C5^S - C5^raw:

| L | 20 | 40 | 100 | 200 | 400 | 600 |
|---|---|---|---|---|---|---|
| consistent | +0.0219 | +0.0640 | +0.2997 | +1.0391 | +3.7854 | +8.2059 |
| Zb | -0.4612 | -0.5142 | -0.6620 | -0.4954 | +1.5856 | +5.9456 |
| W2 | -0.9558 | -1.4293 | -3.0308 | -6.0173 | -13.4451 | -23.1254 |
| Wb | -0.6451 | -0.9804 | -2.4160 | -5.9260 | -17.0952 | -33.9477 |
| Wc | -0.4945 | -0.5754 | -0.8071 | -0.8446 | +0.5200 | +3.7311 |

By window class (differences of schemes, `fits5`/class fits, 150..250 <= L <= 600), every class grows like L^2, one
power of L^(1/2) beyond C4 (whose consistent window grows like L^2 with 2.1e-5; at C5 the classes carry L^2 and
L^(3/2) ln L): leading coefficients (spread over fit windows and even/odd L/2)

| class | L^2 coefficient |
|---|---|
| eps^2 vacuum window (consistent2 - raw) | -(5.7 +- 0.3)e-5 |
| eps^3 vacuum window (consistent - consistent2) | +(8.4 +- 0.6)e-5 |
| eps^2 diagonal zero-mode window (zeromode2 - consistent2) | +(3.4 +- 0.2)e-4 |
| eps^2 off-diagonal Bloch window (Z2 - zeromode2) | -(2.0 +- 0.4)e-4 |
| eps^3 Bloch window (Zb - Z2) | -(3 +- 3)e-5 |
| D^M,(2) (W2 - Z2), D^M,(3) (W3m - W2), outer reference (Wc - Wb) | not determined (large compensating L^(3/2) ln L terms) |
| Wc - raw (total) | +(1 .. 4.6)e-4 |

The fits are limited by the precision of the long shift run: the oscillatory angular quadratures lose accuracy
like ~L^4 eps, so the shifts are good to ~1e-9 at L = 200 and ~1e-7 at L = 600 (the fit residuals). No class
coefficient could be identified in closed form at this precision (the C4 sqrt(L) ln L coefficients 6/(243 Gamma(7/2))
were identified from data good to 1e-14). The divergent terms of raw C5 must cancel those of each convergent scheme;
raw C5 at large L is the bottleneck (7.5).

### 7.5 Raw C5 to L = 40: cost, memory, largest L

Raw C5(L) for every even L <= 40 (`results/c5raw_all_L40.npz`, job 574287, code d45be4c, one exclusive defq node,
20 workers, 1 h 45 min, resuming the cached task results of the earlier partial runs). Its L <= 20 values agree with
the L = 20 run to 6.8e-13 (C5) and 8.9e-14 (C4). All 34 reduced 4-vertex boxes it used were recomputed independently
with the same code (574365): 34/34 bitwise identical.

Cost model (`prof5.py`, `prof_heavy.py`): 9808 VVVVV patterns dominate; the 155 patterns with seven single lines
(K4 + pendant, K4 + doubled edge, subdivided K4, series-parallel K_{2,3}-like) dominate those. Their angular channels
grow like L^5.4 (6j weights couple six partial waves) and each channel group needs a box of slice levels, so the
direct cost is ~L^9.4. The reductions to cached 4-vertex boxes (Sec. 7.1) bring it to ~L^8.4 (one 3D box per
distinct reduced graph: 34 at L = 40, 0.1 to 1.3 h each on one core).

Memory (diagnosis of the OOM jobs 574027, 574028; `memprobe.py`, `results/regress/memprobe_L12_20.txt`): the
largest object is the list of states of an intermediate (non-final) parallel merge in the angular reduction of the
seven-line series-parallel patterns (exact Fraction weights and the partial wave of every internal edge). It has
31,948 entries at L = 12 and 326,150 at L = 20 (~L^4.5), i.e. ~7e6 at L = 40 and ~3e7 at L = 56, about 0.8 KB per
entry with the merge dictionary. Measured largest worker: 6.3 GB at L = 40 (574027: 6 workers on 16 GB died when
three such tasks overlapped; tasks 6406-6440 were running) and 18.0 GB at L = 56 (574028: 60 workers, 193 GB in
total). The K4 and phantom boxes themselves stay below 0.5 GB at L = 16 (`memprobe_box.py`). A second, latent path
(a lazy channel stream listed when other factors had more than one entry) was removed (`ReIter`, d45be4c).
L = 56 would need <= 9 workers per node (~40 h); it was dropped. Going beyond L = 40 needs a compact (array) state
representation for the parallel merges and a cheaper K4/series reduction; not attempted.

### 7.6 C5 per scheme to L = 40, extrapolation, C4^W calibration, blind tests (`fits/fits5_summary.txt`)

C5^S(L) = raw(L) + exact shift (shifts to L = 600, Sec. 7.4); Wcs = Wc + delta3(L) S(L):

| L | raw | consistent | Zb | W2 | Wb | Wc | Wcs |
|---|---|---|---|---|---|---|---|
| 24 | -3.574509 | -3.545774 | -4.043653 | -4.618287 | -4.278255 | -4.082950 | -4.085369 |
| 28 | -3.714982 | -3.678588 | -4.193840 | -4.851144 | -4.482031 | -4.238852 | -4.241547 |
| 32 | -3.828514 | -3.783684 | -4.318396 | -5.060206 | -4.663034 | -4.368910 | -4.371851 |
| 36 | -3.921415 | -3.867386 | -4.423202 | -5.250982 | -4.827153 | -4.479074 | -4.482238 |
| 40 | -3.998246 | -3.934267 | -4.512477 | -5.427501 | -4.978621 | -4.573616 | -4.576983 |

C5(3) = -5.85035. At L = 40 Wc is still 1.28 above it (C4^W: 0.147 above C4(3) at L = 40).

Wcs: delta3(40) from four models of the L = 6..16 data is -0.0229 .. -0.0267, so C5^Wcs(40) - C5^Wc(40) = -0.0030 ..
-0.0035 (model spread 5e-4); the extrapolated Wcs limits differ by 0.005 between the models.

Fits A + tower, Lmin in {8, 10, 12, 16}, Lmax in {32, 40}; entries are A - exact. Same protocol on C4^W(L <= 40):

| tower | C4^W calibration | C4^W blind (fit <= 28, predict 30..40: error) | C5^Wc | C5^Wc blind (fit <= 28: error) | C5^Zb |
|---|---|---|---|---|---|
| A: 1/L, ln L/L, L^-3/2, L^-2 | -0.011 .. +0.009 | +0.006 (2.7e-4) | -0.169 .. -0.017 | -0.183 (1.2e-3) | +0.05 .. +0.28 |
| D: L^-1/2, 1/L, L^-3/2, L^-2 | -0.036 .. +0.009 | -0.003 (2.4e-4) | -0.395 .. -0.033 | -0.437 (1.9e-3) | -0.08 .. +0.40 |
| E: 1/L, L^-3/2 | -0.002 .. +0.006 | -0.004 (2.2e-3) | +0.173 .. +0.423 | +0.470 (6.2e-2: fails) | +0.29 .. +0.51 |
| C: L^-1/2, 1/L, L^-3/2 | +0.010 .. +0.062 | +0.071 (1.4e-3) | -1.00 .. -0.54 | -1.08 (1.2e-2) | -0.78 .. -0.22 |
| B: 1/L .. L^-5/2 with logs | -0.55 .. +5.3 (unstable) | +0.71 | -1.97 .. +24.4 | +2.56 | unstable |

* Towers A and D pass both the C4^W calibration (within 0.036) and the C5 blind test (prediction error <= 2e-3 over
  30 <= L <= 40). They give **C5^Wc(inf) - C5(3) between -0.44 and -0.02** (all windows, blind fits included; median of
  tower A -0.10). On C4^W these towers miss by up to 25% of the remaining correction at L = 40; scaled to C5^Wc
  (remaining correction 1.28) that is +-0.3. Hence **C5^Wc(inf) = -6.0 +- 0.3 (L <= 40), consistent with
  C5(3) = -5.850**; Wcs gives the same within 0.01.
* Full spread over all towers and windows: [-7.82, +18.5] (tower B is unstable on C4^W as well); without B,
  [-6.85, -5.43]. Tower E fails the C5 blind test; tower C (an L^-1/2 term) is biased on C4^W (which has no such term)
  but would put the limit 0.5 .. 1.0 below C5(3). The local ratio d(L)/d(L-4) of Wc at L = 40 is 0.858, between a
  1/L tail (0.81) and an L^-1/2 tail (0.854); C4^W shows 0.828 at L = 40 and becomes 1/L only for L >~ 100. L <= 40
  cannot exclude an L^-1/2 term in C5^Wc.
* Divergence tests (A fixed at C5(3), tower A plus one free divergent term, Lmin 10): Wc b sqrt(L) = -7.3e-3,
  b ln L = -2.0e-2, b L = -5.9e-4 (the sqrt(L) term amounts to 0.046 at L = 40, 3.6% of the remaining correction; the
  convergent C4^W gives -4.8e-4, 2% of its correction). Zb: +8.2e-3 (same size, other sign). Wb: -0.20 (diverges).
* Other schemes: Wb and W2 diverge (towers A, D: -2.5 .. -7.2; the D^M,(3)/Bloch combination without the outer
  reference, as in 2D); consistent diverges (+1.1 .. +3.5, drifting with Lmin); raw diverges (its shifts to the
  convergent schemes grow like L^2). Zb is consistent with C5(3) at L <= 40 too (towers A, D: -0.08 .. +0.40, drifting
  upward with Lmin while Wc drifts toward 0), but Zb - Wc is +0.06 at L = 40 and +2.2 at L = 600 (exact shifts):
  Zb and Wc cannot both converge, and L <= 40 cannot tell them apart. The C4 result (without the chi window the
  zero-mode-windowed scheme has a sqrt(L) divergence, Sec. 1) favours Wc.

### 7.7 delta^(3)(L) and Wcs

delta^(3)(L) (tagged phi channel, exact, `results/tag/`): +0.006274, +0.000368, -0.003309, -0.006067, -0.008327,
-0.010273, -0.012001, -0.013569 for L = 2..16. Unlike 2D (delta -> -0.0159 like L^-2), it keeps growing: increments
-0.00276, -0.00226, -0.00195, -0.00173, -0.00157 (L = 8..16) fall between the ln L and the sqrt(L) laws and approach
sqrt(L). Fits for L = 6..16: -0.00502 sqrt(L) + 0.0026 + 0.0157/sqrt(L) (residual 1e-7), or with a ln L term
-0.0034 sqrt(L) - 0.0050 ln L + 0.0141. This is the 3D power counting: the chi mass window per unit level is
r2'(L) ~ sqrt(L) (r2 ~ L^(3/2)), and the leg-budget part of the eps^3 self-energy inherits it.
S(L) converges (0.1227, 0.1296, 0.1327, 0.1341, 0.1345 at L = 10, 20, 40, 100, 400; the pair-creation and
annihilation parts grow separately and cancel), so C5^Wcs - C5^Wc = delta^(3) S ~ -6.7e-4 sqrt(L): -0.0021 at
L = 20, about -0.004 at L = 40, -0.02 at L = 1000. Hence Wc and Wcs cannot both converge at eps^5 in 3D; the
difference is ~100x below the resolution of any C5 extrapolation reachable here, so the C5 test (T2) cannot decide
between them. Beyond L = 16 delta^(3) is modelled (4 models; the spread of C5^Wcs from the model choice is <= 0.005).

### 7.8 Descendant identity (T3) for chi_11 (exact, `fits/t3_summary.txt`)

R_n(L) = [eps^n](E(chi_11) - E(phi) - 2):

| L | Wc R2 | Wc R3 | Wcs R3 | budget-free R2 | budget-free R3 | leg = Wc - budget-free (R3) | -delta3/2 |
|---|---|---|---|---|---|---|---|
| 6 | 0.007758 | 0.023695 | 0.022040 | 0.013056 | 0.020352 | 0.003343 | 0.001654 |
| 8 | 0.006869 | 0.022762 | 0.019729 | 0.011769 | 0.018910 | 0.003853 | 0.003033 |
| 10 | 0.006229 | 0.022293 | 0.018130 | 0.010808 | 0.017823 | 0.004470 | 0.004164 |
| 12 | 0.005740 | 0.022075 | 0.016938 | 0.010053 | 0.016960 | 0.005115 | 0.005137 |
| 14 | 0.005351 | 0.022004 | 0.016004 | 0.009439 | 0.016248 | 0.005756 | 0.006001 |
| 16 | 0.005031 | 0.022028 | 0.015244 | 0.008926 | 0.015646 | 0.006382 | 0.006784 |

raw and W2: R3 = 0.81, 0.83 at L = 14 and growing. Tagged nu = (2,2) reproduces Wc to 4e-16 (the tagging is exact).
* R2 -> 0 in Wc (fit a + b/sqrt(L) + c/L: a = -0.0002) and with budget-free legs: D^M,(2) is right at eps^2, as in 2D.
* Wc R3 is flat at 0.022 for L = 8..16 and turns up at L = 16 (0.022075, 0.022004, 0.022028 at L = 12, 14, 16) while
  the leg part (charged minus budget-free) grows (0.0033 -> 0.0064, like sqrt(L)): Wc's eps^3 remainder contains the
  growing leg budget, as in 2D but one power worse, compensated at these L by the slowly falling budget-free part.
* The linearized Wcs window reproduces the leg part from L ~ 10 on (-delta3/2 vs leg: 0.00416 vs 0.00447, 0.00514 vs
  0.00512, 0.00600 vs 0.00576, 0.00678 vs 0.00638 at L = 10..16), so Wcs R3 tracks the budget-free R3 (0.01524 vs
  0.01565 at L = 16); from L ~ 12 on it slightly overcorrects (the linearization at charge 2 grows a little faster than
  the leg part).
* The budget-free R3 itself falls slowly (0.0204 -> 0.0156 for L = 6..16); fits give a limit 0.003 .. 0.015, so L <= 16
  cannot show R3 -> 0 in 3D (in 2D the budget-free R3 fell like 0.07/L). T3 is therefore **not decided** in 3D: the
  structure (leg budget = the growing part; Wcs = budget-free) is confirmed, convergence is not.
