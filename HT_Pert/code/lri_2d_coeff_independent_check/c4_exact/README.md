# Exact finite-cutoff C_4(L) of the 2D LRI Hamiltonian truncation, L up to 2000, three window schemes

Model and conventions: `../SPEC.md` (GFF on the unit circle, x = 1/2 - eps/4, w_ab = (x)_a (x)_b/(a! b!),
M = <:phi^2:>, V = <:phi^4:>/12, level cutoff N <= L, J = 0, tuning E1 - E0 = x, E3 - E0 = 2 - x, observable
Delta_eps = E2 - E0 = sum C_n eps^n). Continuum target: C_4(2) = 5.048868431354847
(`../continuum/reference_values.csv`).

## Bottom line (status 2026-10-08 20:50 EDT: L <= 1000 complete; L_max = 2000 run in progress, jobs 571851/571862)

| scheme | C4(L=1000) | large-L behaviour (fits on exact data L <= 1000, `fits/fit_summary.txt`) | converges to 5.04887? |
|---|---|---|---|
| raw | 4.48069 | C4raw = C4cons - Delta_cons, Delta_cons = kappa L + lambda ln L + c exactly: kappa = 2.20729300e-4, lambda = -40/(81*864 pi); so C4raw ~ 5.002 - 2.2073e-4 L - 0.0264 ln L | no: linear divergence |
| consistent | 4.70061 | A + beta ln L + O(ln^2 L/L): beta = -0.0266 +- 0.0005, A = 5.003 +- 0.006 | no: log divergence |
| corrected | 4.83195 | beta = -0.0105 +- 0.0005 (central fits -0.01048, close to -8/(243 pi)), A = 5.022 +- 0.006 | no: residual log divergence |

corrected - consistent = mu ln L + nu + O(ln L/L) exactly (windows.py, to L = 20000): mu = 0.0160828726
(m = 2 part exactly 4/(81 pi), m = 4 part 0.000364), nu = 0.0187584. The zero-mode window removes that much of
the consistent scheme's log, but a residual -0.0105 ln L remains. Evidence: without a ln L term every tower fit
drifts with the window (A = 4.88-4.90 corrected, 4.66-4.69 consistent) and l^2/L coefficients come out at +8..+100
instead of the RG value -5/pi; with ln L the fits are stable and c2 ~ -1.4..-1.6; fitted on L <= 600 the log
model predicts 600 < L <= 1000 to 3e-9, every no-log model misses by 1e-7..9e-6; a ln^2 L term fits to ~1e-6.
Blind predictions for L = 1200..2000 from both families are recorded in `fits/blind_predictions_L1200_2000.json`
(they differ by 2-5e-6; data accuracy ~1e-11) for the running L = 2000 run.


---------------------------------------------------------------------------------------------------------

## 1. Files

| file | role |
|---|---|
| `c4lib.py` | diagram engine: zero-mode paths (exact rationals), line patterns, holomorphic-factorized chi densities, shell contractions, two-vertex chains with eps-derivatives |
| `c4_compute.py` | assembles r2, g2, r3, g3, X4_p = E_p^(4) - 2p r4 - p(p-1)/2 g4 and C_4 for raw/consistent/corrected, for every even L <= L_max at once (serial) |
| `c4_run.py`, `run_c4.sbatch` | production driver: every chain pattern is a task in a process pool, per-task checkpoint files, symmetry Slurm wrapper |
| `windows.py` | exact window shifts Delta_cons = C4cons - C4raw and Delta_zm = C4corr - C4cons to L = 20000 (two-vertex sums only, cancellation-free) |
| `validate_rs.py` (+ `.txt`) | vs `../rs_exact/results` exact rationals, L = 0..18: r2, g2, r3, g3, C2, C3, C4 raw/consistent, and (with `--full`) every E_p^(4) and E_v^(2)(l) |
| `validate_pkg.py` (+ `.txt`) | vs the production package (`../../results/*/d8`), L = 2..34; Delta C4 and dC4_zm vs `../continuum` |
| `brute_corrected.py`, `brute/` | brute-force exact (Fraction) RS with the zero-mode-aware window, built on `../rs_exact/ref_fraction.py` (imported read-only; a verbatim copy was used on the cluster), L = 0..12 |
| `validate_corrected.py` (+ `.txt`) | corrected scheme vs `brute/` (L <= 12) and vs `../zeromode_exact/results` (L <= 18) |
| `fitlib.py`, `fits_c4.py`, `fits/` | asymptotic fits; `fits/fit_summary.txt`, `fits/fit_table.csv`, `fits/blind_predictions_L1200_2000.json` |
| `make_csv.py`, `C4_by_L.csv` | the deliverable table: every even L, C4 raw / consistent / corrected (+ C2, C3, both window shifts) |
| `results/` | `c4_L600.npz`, `c4_L1000.npz`, `c4_L2000.npz` (cluster runs), `c4_L160_local.npz`, `windows_L20000.npz` |

## 2. Derivation

### 2.1 Fourth-order Rayleigh-Schroedinger with several perturbation orders
Write H(eps) = H0 + eps W1 + eps^2 W2 + eps^3 W3 + eps^4 W4 with H0 = N + P/2 and (r1 = 0, g1 = 1/3 from order 1)

    W1 = -P/4 + g1 V
    W2 = r2 M + g2 V + g1 V' + D2
    W3 = r3 M + g3 V + g2 V' + (g1/2) V'' + r2 M' + D3
    W4 = r4 M + g4 V + ...                        (V' = dV/deps through w_ab(x(eps)) only; likewise M')

Inserting V_pert = sum_k eps^k W_k into the standard RS functionals E^(1..4)[V_pert] and collecting eps^4
(R = Q_p/(p/2 - H0), <.> = <p|.|p>, E1 = -p/4 + g1 V_pp):

    E4 = <W4> + 2<W1 R W3> + <W2 R W2> + 2<W1 R (W1 - E1) R W2> + <W1 R (W2 - <W2>) R W1>
         + <W1 R (W1 - E1) R (W1 - E1) R W1> - <W1 R W1><W1 R^2 W1>.

Outer W1's reduce to g1 V (P is diagonal and R kills |p>), inner ones to g1 (V - V_pp) - (P - p)/4.
Diagonal parts of everything on |p> are eps independent (w_00 = 1): <p|M|p> = 2p, <p|V|p> = p(p-1)/2,
<p|V'|p> = <p|M'|p> = <p|V''|p> = 0, D(level 0) = 0. Hence E_p^(n) = X_p^(n) + 2p r_n + p(p-1)/2 g_n, and the
tuning (x has no eps^n term for n >= 2) gives r_n = -(X_1 - X_0)/2, g_n = -(X_3 - X_0 + 6 r_n)/3 and

    C_n = Pi[X^(n)],   Pi f = f(2) - f(1) - (f(3) - f(0))/3,

which annihilates every polynomial of degree <= 2 in p (the projector of `../continuum/exact_low_orders.py`).
Expanded, with chains written right-to-left (first vertex acts first), "s" a slice operator:

    (a) 2 g1 [ r3 <V R M> + g3 <V R V> + g2 <V R V'> + (g1/2) <V R V''> + r2 <V R M'> ]
    (b) r2^2 <M R M> + g2^2 <V R V> + g1^2 <V' R V'> + 2 r2 g2 <M R V> + 2 r2 g1 <M R V'> + 2 g1 g2 <V R V'>
    (c) 2 g1 sum_{X = M (r2), V (g2), V' (g1)} coef_X [ g1 <V R V R X> - g1 V_pp <V R^2 X> - (1/4) <V R (P-p) R X> ]
    (d) g1^2 [ r2 (<V R M R V> - 2p <V R^2 V>) + g2 (<V R V R V> - V_pp <V R^2 V>) + g1 <V R V' R V> + <V R D2 R V> ]
    (e) g1^4 [ <VRVRVRV> - V_pp (<V R^2 V R V> + <V R V R^2 V>) + V_pp^2 <V R^3 V> ]
        - (g1^3/4) [ <V R (P-p) R V R V> + <V R V R (P-p) R V> - 2 V_pp <V (P-p) R^3 V> ] + (g1^2/16) <V (P-p)^2 R^3 V>
    (f) - g1^4 <V R V> <V R^2 V>

r3, g3 come from X^(3) = 2 g1 [r2 <VRM> + g2 <VRV> + g1 <VRV'>] + g1^3 (<VRVRV> - V_pp <VR^2V>) - (g1^2/4)<V (P-p) R^2 V>,
which must be complete for p = 0, 1, 3 (not only its Pi-surviving part). D enters C_4 only through
<V R D2 R V> (D is diagonal and vanishes on |p>), and only its eps^2 part D2 matters:

* raw: D2 = 0;
* consistent: D2(N) = E_v^(2)(L) - E_v^(2)(L - N), E_v^(2)(l) = g1^2 <0|VRV|0>_l = -(l+2)(l+4)/864 (verified for
  every l, exactly in `brute/` and to 2e-16 in `validate_rs.txt`);
* corrected: D2(z, N) = E_z^(2)(L) - E_z^(2)(L - N), E_z^(2)(l) = 2z r2 + g2 z(z-1)/2 + g1^2 <z|VRV|z>_l, so
  D2 = g1^2 [e_z(L) - e_z(L-N)], e_z(l) = <z|VRV|z>_l; z = p + delta <= 7 for the states reached from |p>.
  No second-order denominator vanishes for any |z> (V cannot connect |z> to its degenerate partners, which exist
  for z >= 5 at levels N >= 2 with P = z - 2N): checked exactly in `brute_corrected.py` for z <= 7, L <= 12.

### 2.2 Zero mode times non-zero modes
phi = Z + chi with Z = a + a^dag (the (0,0) oscillator, weight 1 at every eps). Normal ordering factorizes:
V = sum_m [C(4,m)/12] :Z^{4-m}: (x) <:chi^m:>_theta, M = sum_m C(2,m) :Z^{2-m}: (x) <:chi^m:>_theta.
A K-vertex chain is a sum over chi line patterns n_ij (lines between vertices i < j, m_i = sum_j n_ij <= 4 or 2)
of [Wick count prod m_i! / prod n_ij!] x [vertex coefficients] x [zero-mode path sum] x [chi level sum].
Zero-mode path p = r_0 -> r_1 -> ... -> r_K = p, vertex i applying :Z^{k_i}: with j_i creations:
amplitude prod C(k_i, j_i) prod_{i<K} r_i! / prod_i m_i! (m_i = intermediate after the annihilations), an exact
rational because every r_i! appears twice under square roots on a closed path. Slice s carries n_s chi lines and
zero-mode number r_s; its denominator is den_s = (r_s - p)/2 + n_s/2 + (chi level of the slice), R = -1/den,
and Q removes the slices with n_s = 0 and r_s = p.

### 2.3 Holomorphic factorization of the chi sums (the key to large L)
w_ab = v(a) v(b), v(a) = (1/2)_a / a!, so W(y, ybar) = sum w_ab y^a ybar^b = V_1(y) V_1(ybar), V_k(y) = (1-y)^{-k/2}
(J = a - b, level = a + b). A bundle of n lines between two vertices has weight
(W - 1)^n = sum_{k=0}^{n} C(n,k) (-1)^{n-k} V_k(y) V_k(ybar). theta-averaging every vertex imposes J conservation,
which (no external chi lines) is equivalent to J = 0 in every slice, i.e. holomorphic level = antiholomorphic level
=: sigma_s in every slice; the slice level is 2 sigma_s. Hence the J-resolved density of a pattern is

    R_n(sigma_1..sigma_{K-1}) = sum_{k <= n} c_k(n) rho_k(sigma)^2,  c_k = prod_b C(n_b,k_b)(-1)^{n_b-k_b},
    rho_k(sigma) = [z^sigma] prod_bundles V_{k_b}( prod_{slices s crossed by b} z_s ),

with no angular-momentum loop left: the two-loop J sums of e.g. K4-minus-an-edge patterns become a square.
For K = 4 (slices 1..3) the long bundles 13, 14, 24 are a scatter (each (a, u, b) hits one sigma), the local
bundles 12, 23, 34 are convolutions along one axis (Toeplitz GEMMs). eps-derivative vertices: for a single
first-derivative vertex i (V', M'), R' = sum_k c_k sum_{b incident to i} rho_k^{(d b)} rho_k with
d/deps V_k = (k/4) log(1-y) V_k (the line weight is sqrt(w(eps) w(0)), whose derivative is w'/2). Two-vertex
chains with V'' or V'V' use the per-mode Taylor series of sqrt(v(a;eps1) v(a;eps2)) to second order
(v(a;eps) = v(a) exp(-(h1/4) eps - (h2/32) eps^2 + ...), h1 = psi(1/2+a) - psi(1/2), h2 = psi'(1/2) - psi'(1/2+a)).

### 2.4 One run gives every cutoff
The densities do not depend on L; the cutoff only restricts every slice level, max_s 2 sigma_s <= L. Each
zero-mode path contributes sum_sigma R(sigma) prod_s g_s(sigma_s) with g_s = (-1)^pow (r_s - p + n_s)^q /
den_s^pow; accumulating by M = max_s sigma_s (shell sums) and taking a cumulative sum gives the value at every
even L <= L_max at once. The D2 window terms depend on L explicitly and are evaluated separately for each L (1D).

### 2.5 Pruning by Pi, mirror symmetry
The zero-mode amplitude of a path is a polynomial in p of degree (number of zero-mode legs)/2; for the
four-V chain this is 8 - n (n = number of chi lines). Pi kills degree <= 2, so only patterns with n <= 5
contribute to C_4 (384 of the 641 four-vertex patterns; 237 of them couple all three slices). This was verified: the full
pattern set and the pruned set give the same C_4 (to 1e-13), and the full set reproduces every individual
E_p^(4) of `rs_exact` (sec. 3). Every other chain is kept complete (cheap; and r3, g3 need it). Time reversal
maps a four-vertex pattern to its mirror with an identical contribution (checked for all 168 pairs to 5e-16),
so 216 representatives are computed.

### 2.6 Window shifts without cancellation (windows.py)
Delta_cons = Pi[g1^2 <V R D2^cons R V>] and Delta_zm = Pi[g1^2 <V R (D2^corr - D2^cons) R V>] are double sums
over the outer state (chi number m, zero-mode shift delta, level 2 sigma) and the inner bubble (m', delta').
The naive form e_z(L) - e_z(L - N) cancels ~L^3 between e_z ~ L^2 and the Pi-surviving O(1/L) pieces
(1e-4 relative noise in the m = 4 part at L = 10^4). windows.py applies Pi in exact rational arithmetic to the
zero-mode polynomials Q_{m,delta}(p) [Q_{m',delta'}(p + delta) - Q_{m',delta'}(0)] before multiplying by the
single-signed level sums W(L) = sum_sigma h(sigma) sum_{t < sigma} ds(L/2 - t); the result agrees with the
full computation to 6e-13 for L <= 1000 and is clean (fit residuals 1e-15) to L = 20000.

### 2.7 Cost and precision
Four-vertex chain: O(N^4) GEMM work per configuration (N = L_max/2; 5216 configurations before the mirror
reduction), O(N^3) per contraction, memory two N^3 arrays per worker. Wall time on one 40-core Intel node:
L_max = 600: 51 s; L_max = 1000: 4 min; L_max = 2000: ~80-90 min (running; 7 workers x 5 threads, memory-limited). Everything is float64 with pairwise/BLAS
summation; all chi sums are single-signed except the k-alternation inside R_n. Rounding is measured by
overlapping runs of different sizes on different machines: Mac L <= 160 vs cluster L_max = 600: <= 6.5e-13
relative; L_max = 600 vs 1000: <= 6.7e-12 absolute; L_max = 1000 vs 2000: pending. The largest single terms grow ~20 L (vs C_4 ~ 5),
so the cancellation in the assembly is ~4 10^3 at L = 1000.

## 3. Validation

| check | range | worst deviation | file |
|---|---|---|---|
| r2, g2, r3, g3, C2, C3 vs rs_exact exact rationals | L = 0..18 | 3.4e-15 (C3: 1.3e-14) relative | `validate_rs.txt` |
| C4 raw and consistent vs rs_exact | L = 0..18 | 1.1e-13 relative (6.6e-14 with all patterns) | `validate_rs.txt` |
| every E_p^(4) - 2p r4 - p(p-1)/2 g4 (p = 0..3, raw, all 641 four-vertex patterns) vs rs_exact | L = 0..18 | 2.1e-14 relative | `validate_rs.txt` |
| E_v^(2)(l) = -(l+2)(l+4)/864 | every l <= 18 (float), l <= 12 (exact) | 2.2e-16; exact | `validate_rs.txt`, `brute/` |
| C2, C3, C4 raw and consistent, r3, g3 vs the package (float64) | L = 2..34 | 1.1e-13 relative (C4) | `validate_pkg.txt` |
| consistent - raw (Delta C4) and corrected - consistent (dC4_zm) vs `../continuum` | L = 2..30 | 2.8e-15 / 7e-15 absolute | `validate_pkg.txt` |
| corrected C4 vs brute-force exact RS (`brute_corrected.py`, Fraction arithmetic) | L = 0..12 | 1.1e-13 relative | `validate_corrected.txt` |
| corrected C4 vs `../zeromode_exact/results` (independent exact solver, other agent) | L = 0..18 | 1.1e-13 relative | `validate_corrected.txt` |
| brute raw/consistent == rs_exact; brute corrected C4 == zeromode_exact C4 | L = 0..12 | exact rational identity | `validate_corrected.txt` |
| pruned (<= 5 lines) vs full four-vertex pattern set | L <= 18 | same C4 to 1e-13 | `validate_rs.txt` |
| mirror pairs of four-vertex patterns | all 168 pairs, L = 40 | 5.5e-16 | sec. 2.5 |
| windows.py (cancellation-free) vs full run | L <= 1000 | 6e-13 absolute | sec. 2.6 |
| overlap of runs with different L_max / machines | see sec. 2.7 | <= 6.7e-12 absolute | |

The brute-force check computes E_z^(2)(l) from auxiliary exact RS channels |z> (z <= 7, every l <= L) and confirms
that none of their first-order intermediate states is degenerate with |z>.


## 4. Asymptotics
See the bottom line above and `fits/fit_summary.txt` (all fits, out-of-sample tests, window asymptotics),
`fits/fit_table.csv`, `fits/c4_vs_L.png`. To update after the L = 2000 run:
`rsync symmetry:<SCRATCH>/indep2d/c4_exact/results/c4_L2000.npz results/ && python3 make_csv.py && python3 fits_c4.py && python3 plot_c4.py`
(fits_c4.py section 4 then compares the blind predictions with the L = 2000 data).

## 5. Cluster jobs (symmetry, logs in <SCRATCH>/indep2d/c4_exact/logs/)
| job | name | what | state |
|---|---|---|---|
| 571826 | indep2d-c4-test600 | L_max = 600 + brute L = 10, 12 | outputs complete; FAILED only on a final cosmetic `tail` (fixed) |
| 571827 | indep2d-c4-L1000 | cancelled while pending, resubmitted to debug queues | CANCELLED |
| 571829 | indep2d-c4-L1000 | L_max = 1000 | COMPLETED (3:58) |
| 571850 | indep2d-c4-L2000 | L_max = 2000, part 1 (101/556 tasks checkpointed) | TIMEOUT (by design) |
| 571851 | indep2d-c4-L2000c | continuation from cache_L2000 | RUNNING at hand-off |
| 571862 | indep2d-c4-L2000d | second continuation (exits at once if the result exists) | PENDING (dependency) |
