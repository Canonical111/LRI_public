# PLAN: exact finite-cutoff C4(Λ) of the d = 1 LRI frozen-cutoff Hamiltonian truncation, Λ up to 2000

Owner: HT1dPert session (Claude, coordinator + builder). Plan reviewer and final code inspector: Codex
(`gpt-6-astra`, effort `xhigh`). Requested by the user on 2026-10-12: "start the C4 port with codex review".

## 1. Goal

Port the exact large-cutoff diagram-sum method of the 2D project
(`lri_2d_coeff_expanse/independent_check/c4_exact/`, README sec. 2; read-only source, owned by another session)
to the 1D LRI Hamiltonian truncation, and compute **exact (float64-rounding-limited) C4(Λ)** for every cutoff
Λ ≤ Λmax = 2000 (stretch; 1000 required), in two schemes:

* **raw**: the plain truncated Hamiltonian (the quantity of the HT campaigns, `data.json` "raw"/"thermal_d7");
* **Dconn**: raw + the complete consistent disconnected-vacuum window, ΔC4^Dconn(Λ) = dC4_g2D(Λ) + shift4(Λ)
  (definitions as in `lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json`, sec. 4 below).

The HT data stop at Λ = 118 (C7) / 92 (C8). Their tails decay like Λ^{-1/2} log^k Λ, which is why C5..C8
extrapolations are tail-model limited. Exact C4(Λ) to Λ ≈ 2000 (17× further) lets the C4 tail structure be
measured directly: which powers/logs are present, and whether the "ω3" (J-channel, Λ^{3α-2}-type) second channel
is visible at C4. That is the analogue of what the 2D C4 run achieved (fits to ~1e-7 there). C5 (five-vertex chains,
cf. the 2D `residual_log/eps5`) is a later, separate step and **not** part of this plan.

Acceptance criteria. Gates are staged: A1–A5, A6a–c and A9 must hold before any Λmax > 400 submission; A6d is
staged with the production ladder (see A6d); A7/A8 are the production deliverables.

* **A1** exact rationals `lri_ht_c8_symmetry/lri_c8_hpc/inputs/exact_rational_validation.json`
  (Λ = 2, 4, 6, 8, 12): r2, r3, r4, g2, g3, g4, C2, C3, C4 agree to ≤ 1e-12 relative.
* **A2** exact variant rationals: every `exact5_c*.json` in `lri_hpc_Hamitonian/analysis/eps5_window/B/` and
  `.../reconcile/exactL2/` (12 distinct cut4 = 8, 16, 24, 32, 33, 35, 43, 48, 49, 51, 64, 65; c16 exists in both):
  raw C2, C3, C4, r2..r4, g2..g4 at every file (including the quarter cutoffs 8.25, 8.75, 10.75, 12.25, 12.75,
  16.25) ≤ 1e-12 relative; Dconn C4 at the even integer cutoffs (cut4 = 8, 16, 24, 32, 48, 64) ≤ 1e-12 relative.
* **A3** independent brute-force float64 Rayleigh–Schrödinger (sec. 6, V3), every quarter cutoff
  cut4 = 4..48 (Λ = 1..12): every E_p^(k), p = 0..3, k = 2, 3, 4, and r_k, g_k, C_k (k ≤ 4) agree to
  ≤ 1e-11 relative (absolute 1e-12 when |value| < 0.1).
* **A4** HT data `lri_ht_c8_symmetry/results/2026-10_symmetry/extrapolation/data.json`: C4 vs "raw" (Λ ≤ 92) and
  "thermal_d7" (Λ ≤ 118), C2 and C3 likewise: max |Δ| reported; gate |ΔC4| ≤ 1e-8 (the HT float64 data are
  expected at ~1e-10; a larger deviation is a defect of one side and blocks production until explained).
* **A5** windows: shift4(Λ) vs `dC_reconciled.json` "shift4" on that file's actual 67-row grid (even Λ ≤ 152;
  the file has no rows at Λ = 130, 132, 134, 138, 140, 142, 146, 148, 150 — the validator iterates the file's rows,
  asserts there are exactly 67, and the engine's values at the 9 missing cutoffs are reported without a reference):
  ≤ 1e-12 absolute;
  ΔR4(Λ) = H_odd(Λ-1)/2916 (sec. 4) to ≤ 1e-14 relative for Λ ≤ 2000; the engine's own two-vertex
  g2D window sum vs the closed form `fast(Λ)` ≤ 1e-12 absolute for even Λ ≤ 400.
* **A6** internal consistency: (a) every four-vertex mirror pair gives identical shells (≤ 1e-13 relative) at
  Λmax = 40; (b) mirror-reduced and full pattern sets give the same C4 at Λmax = 40 (≤ 1e-13); (c) the
  streaming density kernel equals a direct reference implementation (dense, unblocked, all parities, then
  parity-masked) to ≤ 1e-13 relative for random patterns at N ≤ 60; (d) runs with different Λmax agree at
  common cutoffs to ≤ 1e-11 absolute in C4, staged: Λmax = 200 vs 400 before the Λmax = 1000 submission;
  400 vs 1000 before the 2000 submission; 1000 vs 2000 before the 2000 outputs are accepted.
* **A7** production outputs, two grids, no interpolation or reuse of even-Λ formulas at other phases:
  (i) raw quantities (C2, C3, C4, r2..r4, g2..g4, per-p X_p^(2..4)) on the quarter grid; storage index
  cut4 = 0..4Λmax, but physical tuned outputs exist only for cut4 ≥ 3 (all references |p⟩, p ≤ 3, need
  p ≤ cut4; the E3 - E0 tuning is undefined below): rows cut4 < 3 are NaN-masked in every export and a boolean
  `valid` array is stored; per-p X_p is masked for cut4 < p;
  (ii) window/Dconn quantities (dC4_g2D, ΔE0raw^(4) window, ΔR4, shift4, C4Dconn) on the even grid
  Λ = 2, 4, …, Λmax only (separate arrays keyed by Λ). With provenance (code SHA, environment, input hashes, job
  ids), archived locally.
* **A8** first asymptotic analysis (sec. 8): fits with out-of-sample checks; the exact C4 = 45.42488010356 is
  used only as a test, never as an input.
* **A9** Codex inspection of the final code (fresh session) with no unresolved high/medium finding before the
  Λ > 400 production submission.

## 2. Model (verified against `lri_hpc_Hamitonian/reference/check_lri_hamiltonian.py`)

* Modes n = 0, 1, 2, … ; u_n(ε)² = ((1-ε)/2)_n / n! (u_0 = 1 at every ε). B = Σ_n u_n a_n, C = B†, φ = B + C.
  Zero mode Z = a_0 + a_0†; non-zero modes χ (n ≥ 1). N = Σ n a_n†a_n (level), P = Σ a_n†a_n (all quanta).
* H(ε) = N + P/4 - εP/4 + r(ε) M + g(ε) V, M = :φ²: = C² + 2CB + B², V = :φ⁴:/12 = (1/12) Σ_j C(4,j) C^j B^{4-j};
  r, g start at order ε; r1 = 0, g1 = 1/3.
* Truncation: 4N + P ≤ cut4 := 4Λ, frozen at ε = 0. The vertices act on the truncated Fock space and are then
  projected on N even ("sphere parity", applied after each complete vertex). Because the truncated space is
  downward closed and the vertices are normal ordered, P_Λ V P_Λ is exactly the restriction of V; with the parity
  projection every intermediate state of a chain starting at N = 0 has N even.
* References |p⟩ = (a_0†)^p/√p! |0⟩, p = 0..3, E_p^(0) = p/4. Tuning E1 - E0 = (1-ε)/4, E3 - E0 = (3+ε)/4.
  Observable E2 - E0 = Σ C_k ε^k. At order k ≥ 2: E_p^(k) = X_p^(k) + 2p r_k + p(p-1)/2 g_k, so
  r_k = -(X1 - X0)/2, g_k = -(X3 - X0 + 6 r_k)/3, C_k = Π X^(k), Π f = f(2) - f(1) - (f(3) - f(0))/3.
* No intermediate state other than |p⟩ is degenerate with |p⟩ (den = N + (δ + n)/4 > 0 for N ≥ 2 even; pure
  zero-mode states have den = δ/4 ≠ 0), so R = Q_p/(p/4 - H0) with Q_p = 1 - |p⟩⟨p|.

## 3. Method

### 3.1 Fourth-order RS assembly — unchanged from 2D
H(ε) = H0 + εW1 + ε²W2 + ε³W3 + ε⁴W4 with H0 = N + P/4, W1 = -P/4 + g1 V, W2 = r2 M + g2 V + g1 V',
W3 = r3 M + r2 M' + g3 V + g2 V' + (g1/2) V'' (primes: ε-derivatives through u_n(ε)), and the 2D README
sec. 2.1 formula for E4 and its expansion into chains (a)–(f) carries over **verbatim** (the derivation never used
the dimension: diagonal parts of V', M', V'' on |p⟩ vanish because u_0 ≡ 1 and normal ordering). The same chain
list as `c4_compute.py` is used: two-vertex chains (VV with slice ops R, R², R³, (P-p)R², (P-p)R³, (P-p)²R³;
MV, MM; V'V, V''V, V'V', M'V, MV'), three-vertex chains (VVV with R R, R² R, R R², (P-p)R² R, R (P-p)R²;
MVV, VMV, V'VV, VV'V) and the four-vertex VVVV with R R R. X^(3) is kept complete for every p.

### 3.2 Zero mode — unchanged from 2D
Exact rational closed-path amplitudes (`zero_mode_paths`): for fixed slice shifts δ_s = r_s - p the key amplitude
A_p(δ) = (Wick count) × (vertex coefficients) × (zero-mode path amplitude, a polynomial in p: falling factorials)
× Π_s (δ_s + n_s)^{q_s} (-1)^{pow_s}. **Convention (single place):** the sign (-1)^pow of R^pow = (-1/den)^pow and
the particle factor (P - p)^q = (δ_s + n_s)^q of each slice operator live only in A_p(δ) (as in the 2D
`chain_pattern`); the slice weight in the shells is only g_s = den_s^{-pow}. The Q projector removes slices with
n_s = 0 and δ_s = 0 (p-independent). Pure zero-mode slices (n_s = 0) may lie below the reference (δ_s < 0,
den_s = δ_s/4 < 0): allowed, only den_s ≠ 0 is required; χ slices always have den_s ≥ 2 - 1/2 > 0 (checked).

### 3.3 χ densities — 1D specifics (the main change)
* Line weight of one χ line of level m ≥ 1: u_m², generating function V_1(y) - 1 = (1-y)^{-1/2} - 1 (positive
  coefficients). A bundle of n lines between vertices i < j crossing slices i..j-1 has series
  S_n(y) = (V_1(y) - 1)^n, computed by repeated convolution of the positive series (no binomial/alternating
  k-expansion, no squaring: there is no antiholomorphic factor and no angular momentum in 1D).
* Density of a pattern: ρ(N_1..N_{K-1}) = [z^N] Π_bundles S_{n_b}(Π_{s crossed} z_s), **restricted to even N_s in
  every slice** (sphere parity). ρ ≥ 0 entrywise, so all density sums are single-signed.
* One first-ε-derivative vertex i (V', M' in three-vertex chains): product rule over the bundles incident to i,
  d S_n = n S_{n-1} · dV, dV(y) = Σ_{m≥1} u_m² a_m y^m, a_m = -(ψ(1/2+m) - ψ(1/2))/4 (= (1/4) log(1-y) V_1 —
  both forms are implemented and cross-checked). Each derivative term is single-signed (negative).
* Two-vertex chains with ε-derivatives of total order ≤ 2 (V'V, V''V, V'V', M'V, MV'): per-mode Taylor series
  u_m(ε1) u_m(ε2) = u_m² exp(a_m(ε1+ε2) + b_m(ε1²+ε2²) + O(ε³)), a_m as above, b_m = -(ψ'(1/2) - ψ'(1/2+m))/16;
  bundle = d1! d2! [ε1^d1 ε2^d2] (W - 1)^n with W - 1 the χ-only bivariate series (direct powers, no alternation).
  (2D used x = 1/2 - ε/4 and two factors; 1D has x = 1/2 - ε/2 and one factor: coefficients a = -h1/4,
  b = -h2/16 instead of -h1/8, -h2/64. These constants are re-derived and unit-tested against finite differences
  of u_m(ε)u_m(0) computed with mpmath.)

### 3.4 Cutoff, shells and all cutoffs in one run — 1D specifics
* Slice s of a path has n_s χ lines, χ level N_s, zero-mode number r_s = p + δ_s; energy above the reference
  den_s = N_s + (δ_s + n_s)/4; shell weight g_s = 1/den_s^pow (sign and (δ_s + n_s)^q are in A_p(δ), sec. 3.2).
  Sanity value: vacuum ⟨0|VRV|0⟩ at Λ = 1 is -1/6, E0^(2) = g1²(-1/6) = -1/54.
* The cutoff 4N_s + r_s + n_s ≤ 4Λ for every slice ⇔ m(N, δ) + p ≤ cut4 with the **p-independent**
  m(N, δ) = max_s (4N_s + δ_s + n_s) (integer, quarter units, m ≥ -3).
* Per (chain, pattern, key δ): shell array S_δ[m] = Σ_{N: m(N,δ)=m} ρ(N) Π_s g_s(N_s) for m = -3..cut4max
  (stored with offset +3). These do not depend on Λ or p. Cumulative cum_δ[c] = Σ_{m ≤ c} S_δ[m].
* Value of the chain for reference p at cutoff cut4: X_p(cut4) = Σ_δ A_p(δ) cum_δ[cut4 - p]. One run therefore
  gives every quarter-integer cutoff Λ = cut4/4 ≤ Λmax, for every p.

### 3.5 Cancellation control: exact linear functionals per key (new w.r.t. 2D)
r_k, g_k, C_k and the window quantities are linear functionals F_w = Σ_p w_p X_p with rational w
(w_r = (1/2, -1/2, 0, 0), w_g = (-2/3, 1, 0, -1/3), w_C = Π = (1/3, -1, 1, -1/3)). They are evaluated as
  F_w(cut4) = Σ_δ [Σ_p w_p A_p(δ)] cum_δ[cut4] - Σ_δ Σ_p w_p A_p(δ) Σ_{j=0}^{p-1} S_δ[cut4 - j],
with the bracket in exact rational arithmetic. The large divergent parts (vacuum ~Λ, disconnected/nested
bubbles, all patterns with ≥ 6 lines whose A_p(δ) has degree ≤ 2) enter only through their top three shells.
Polynomial prefactors in the RS formula (2p, V_pp = p(p-1)/2, V_pp²) are multiplied into A_p(δ) exactly before
the functional. Products of two p-dependent chains (term (f) -g1⁴⟨VRV⟩⟨VR²V⟩) are expanded over key pairs with
cum[cut4 - p] = cum[cut4] - top_p, so Σ_p w_p A A' cum cum' is formed with exact Σ_p w_p A_p A'_p and the
cross terms with top shells. Couplings r2, g2, r3, g3 are float functionals evaluated the same way; per-p values
X_p (for A3 and for the vacuum window) are also produced (they are not cancellation-free and are not used for C4).

### 3.6 Four-vertex density kernel (memory/cost at Λmax = 2000)
Slices 1..3, bundles 12 (slice 1), 23 (2), 34 (3) local; 13 (1,2), 24 (2,3), 14 (1,2,3) long. Grid N_s ≤ Λmax
(= N), outputs only at even N_s ((N/2+1)³ ≈ 1.0e9 doubles = 8 GB at N = 2000). Streaming over blocks of s1
(the slice-1 level before the bundle-12 convolution):
  1. X0b[s1∈block, s2, s3] = scatter of the long bundles (numba; each (a = level of 13, u = level of 14,
     b = level of 24) hits s1 = a+u, s2 = a+u+b, s3 = u+b), restricted to s2 ≤ N;
  2. Y = T23_even · X0b (batched GEMM along s2, output rows N2 even only);
  3. Z = Y · T34_evenᵀ (GEMM along s3, output N3 even only);
  4. R[N1 even ≥ lo, :, :] += T12_even[:, block] · Z (GEMM, rows restricted by lower-triangularity).
  T_even are the even rows of the lower-triangular Toeplitz matrices of S_{n_b}. Step 4 accumulates **in place**
  (dgemm with beta = 1 on the Fortran-contiguous transposed view of R; no temporary of the size of R; a row-chunked
  fallback if BLAS would copy), and each density is released before the next pattern is built. Memory per
  worker ≈ 8 GB (R) + block·(N+1)²·8 B (X0) + block·H·(N+1)·8 B (Y) + block·H²·8 B (Z) ≈ 8 + 1.8 GB at
  block 32, 8 + 3.6 GB at block 64 (vs 32 GB for the 2D-style full X1 array). **Worker counts for production are
  sized from measured peak RSS** (`/usr/bin/time -v` / sacct MaxRSS of a timed single-pattern run at the target
  Λmax), not from this estimate. Work ≈ 0.44 N⁴ multiply–adds per
  pattern for dense blocks, less with the triangular row/column restrictions (~1.4e13 MAC at N = 2000).
  Patterns whose slice has no lines (n_s = 0) reduce to 2D/1D densities (generic K = 2, 3 code path).
  Shell contraction: numba-parallel over N1, per key, O((N/2)³ · #keys).
* Mirror symmetry: VVVV with R R R is reversal symmetric; one representative per mirror pair (373 of 641
  patterns; 321 representatives have all three slices occupied) is computed and doubled (keys mapped by
  reversal; checked by A6a/b).
* Cost estimate: ~321 × 1.4e13 MAC ≈ 9e15 flop for the four-vertex chain at Λmax = 2000, i.e. a few node-hours
  on 40-core Gold 6148 nodes at ≈1 TFLOP/s sustained. The estimate is validated by timed runs at Λmax = 400 and
  1000 before the 2000 run is sized. Three-vertex chains are O(N³) and negligible.

## 4. Window (Dconn) at ε⁴ — definitions to reproduce
From `eps5_window/SUMMARY.txt`, `reconcile/table_rc.py`, `B/rowresp.py`, `A/c4shift.py`, `lri_eh/exact.py`:
* Dconn_m = Ec(Λ) - Ec(fh(Λ - E0_m)) (fh = floor to the half-integer grid), Ec(x) = vacuum energy of
  H_x + D^[x] (self-consistent, same outer couplings r, g as the cutoff-Λ problem).
* ΔC4^Dconn(Λ) = dC4_g2D(Λ) + shift4(Λ) at even Λ:
  - dC4_g2D(Λ) = Π[g1² ⟨V R D2 R V⟩], D2_m = g1²[e(Λ) - e(Λ - E0_m)], e(λ) = ⟨0|VRV|0⟩_λ. Closed form
    `fast(Λ)` (O(Λ), exact formula; vendored with attribution). The engine also computes it as a two-vertex
    window sum (cancellation-free, as 2D `window_sum`) for A5.
  - shift4(Λ) = -B4/3, B4 = Ec^(4)(Λ) - Ec^(4)(Λ-1) = ΔE0raw^(4)(Λ) + ΔR4(Λ). The reference rows: X1 = X2 =
    Ec(Λ) - Ec(Λ-1/2), X3 = Ec(Λ) - Ec(Λ-1), X0 = 0, so Π gives -B4/3.
  - ΔE0raw^(4)(Λ) = Σ of the p = 0 shells m ∈ {cut4-3, …, cut4} of the full ε⁴ vacuum assembly (only the VVVV
    middle slice with P = 8 at E = Λ and P = 6 at E = Λ - 1/2 contributes; checked, not assumed).
    No subtraction of large cumulative sums.
  - R4(x) = g1⁴ Σ_b |V_b0|²/E_b² [e(x) - e(x - E_b)] (b: 4-quanta states). ΔR4(Λ) = -g1⁴ Σ_b w_b de(Λ - E_b)
    is computed from the two-vertex shells and must equal H_odd(Λ-1)/2916 (so Dconn - literal = -H_odd(Λ-1)/8748,
    the known relation; verified against B's exact Dconn vs Dfull_raw rationals at cut4 = 16).
* Window values at non-even cutoffs (phases 1/4, 3/4) are **out of scope** (raw C4 is produced at every quarter
  cutoff; Dconn only at even Λ).

## 5. Implementation layout (new repo `lri_1d_c4_exact/`, git)
* `c4lib1d.py` — engine: series (S_n, derivatives, Taylor jets), zero-mode paths (from 2D, attributed),
  patterns/mirror maps, density kernels (reference + streaming), shell contraction, chain → per-key records
  {δ: (A_p(δ) exact, S_δ float array)}.
* `functionals.py` — exact per-key functionals, key-pair products, per-p values.
* `c4_compute1d.py` — assembly of r2, g2, r3, g3, r4, g4, C2, C3, C4 (all quarter cutoffs) + window pieces;
  serial path for small Λmax.
* `c4_run1d.py` — production driver: one task per (chain, pattern representative), process pool, per-task
  checkpoint files (atomic rename, content hash of task spec + code SHA in the file), static task partition over
  array indices for multi-node runs (no reliance on cross-node flock — BeeGFS locks are node-local), final assembly.
* `windows1d.py` — ΔR4, own dC4_g2D window sum, vendored `fast` (`vendor/exact_fast.py`, copied verbatim).
* `validate/` — `v1_exact.py` (A1, A2), `v3_brute.py` + `vendor/brute_rs_cut4.py` (A3: copy of
  `check_lri_hamiltonian.FockSpace/initial_wavefunctions` generalised to an integer cut4 and RS order 4; diff
  documented), `v4_ht.py` (A4), `v5_windows.py` (A5), `test_kernels.py` (A6a–c, unit tests of series and
  derivative constants), `v6_overlap.py` (A6d).
* `slurm/` — environment script and sbatch files for symmetry (module anaconda3/2023.07-2: numpy 1.24.3 + MKL,
  numba 0.57, scipy 1.10.1; whole-node exclusive; P computed per the hpc-clusters rule 7; memory-sized worker
  count), `submit.sh` with survey, start/queue statement, duplicate check.
* `results/`, `fits/`, `README.md` (method, validation table, run log, provenance).

## 6. Verification (proof commands; all cheap ones local, ≥ 1 min ones on the cluster)
* `python3 -m pytest -q validate/test_kernels.py` (A6a–c, series/derivative unit tests) — local, seconds.
* `python3 validate/v1_exact.py` (A1, A2; Λmax = 17) — local, seconds.
* `python3 validate/v3_brute.py --cut4max 48` (A3) — local if ≤ 1 min, else symmetry debugq.
* `python3 validate/v5_windows.py --Lmax 152` (A5; needs the p = 0 vacuum shells at Λmax = 152) and
  `python3 validate/v4_ht.py` (A4, Λmax = 118..152) — symmetry, one node, ≤ 1 h.
* Timed production runs Λmax = 400, 1000 (symmetry), A6d overlap, then Λmax = 2000.
Expected: every gate above passes; anything else is reported with its numbers, not waved through.

## 7. Production
Venue: symmetry (data under `<SCRATCH>/lri_1d_c4/`, code snapshot under `~/lri_1d_c4/<sha>`); partition
chosen by a live survey (amdq if idle and its MKL GEMM rate is acceptable in a 1-minute benchmark, else defq).
Order: Λmax = 400 (validation + timing) → 1000 → 2000, each on whole exclusive nodes, multi-node via a static task
partition, each a separate result file (`results/c4_1d_L{Λmax}.npz` + JSON summary with provenance). Before the
first Λ > 400 submission: Codex inspection (A9). Log paths reported per the hpc-clusters rules; no shell timeouts.

## 8. First analysis (after A7)
`fits/fits_c4_1d.py`: C4raw(Λ), C4Dconn(Λ) at even Λ. The goal is to **measure the total tail**: which columns
Λ^{-j/2} log^k Λ (j ≤ 4, k ≤ 3) are required, their coefficients with fit-window/model spread, and design-rank /
condition checks for every basis. Fit windows Λ ∈ [Λlo, 1000]; blind predictions for 1000 < Λ ≤ 2000 are recorded
(hashed file) before the Λmax = 2000 data are read; the intercept is compared with C4 = 45.42488010356 only after
the fits are frozen. Window asymptotics (dC4_g2D known analytically: log Λ/17496 + K - 16/(2187√(πΛ)) - …;
shift4 → 0.018691) are fitted separately. **No channel identification** (e.g. a J-channel Λ^{3α-2} term, whose
ε-expansion produces the same Λ^{-1/2} log^k columns) is claimed from free-amplitude fits: such a test needs an
independently derived ε⁴ template with fixed coefficients, which is out of scope here; the deliverable is the
measured total tail coefficients, to be compared later with any derived template.

## 9. Non-goals / constraints
* No C5 in this plan. No change to other sessions' directories (2D `c4_exact`, `lri_eh_hpc`, `lri_hpc_Hamitonian`):
  code and data are copied/vendored with attribution and sha256.
* No heavy computation on the Mac (memory rule: multi-minute numerics go to clusters).
* Dconn at fractional phases, literal Dfull, g2D+g3W variants: not produced (only checked where cheap).

## 9b. Pre-review prototype (status at plan round 3)
A prototype `c4lib1d.py` + `c4_compute1d.py` was written while round 1 ran (not yet inspected; it will be rebuilt or
kept and fully inspected per sec. 6/A9). With the R1 convention fix it already passes A1 (Λ = 2, 4, 6, 8, 12:
r2..r4, g2..g4, C2..C4 ≤ 2e-14 relative) and the raw part of A2 at all 13 exact files (cut4 = 8, 16, 24, 32, 33,
35, 43, 48, 49, 51, 64, 65; ≤ 2e-14), and the streaming kernel equals the dense reference (≤ 1.1e-15, N ≤ 64,
blocks 1/5/64, in-place accumulation). Window prototype (`windows1d.py`): shift4 equals dC_reconciled to ≤ 3e-17
at every even Λ ≤ 40, ΔR4 = H_odd(Λ-1)/2916 to 1e-19, own g2D window sum = fast(Λ) to 1e-16.

## 10. Assumptions ledger (sources)
| # | assumption | source / how verified |
|---|---|---|
| 1 | cutoff 4N + P ≤ 4Λ, P counts all quanta, frozen at ε = 0 | `check_lri_hamiltonian.py` docstring and `FockSpace.visit` |
| 2 | parity projection N even after complete vertices | same file, `vertices()` (`m[:,~even]=0`) |
| 3 | u_n² = ((1-ε)/2)_n/n!, u_0 = 1 | `square_root_jets` |
| 4 | tuning E1-E0 = (1-ε)/4, E3-E0 = (3+ε)/4; C0 = 1/2, C1 = -1/6 | `compute()` targets; exact JSON C0, C1 |
| 5 | RS chain formula and zero-mode algebra dimension independent | 2D README sec. 2.1–2.2; re-checked by A1–A3 |
| 6 | shift4 = Dconn - g2D = -B4/3 with self-consistent Ec | `table_rc.py`, `B/rowresp.py`; B's exact rationals at cut4 = 16: Dconn - Dfull_raw = -H_odd(3)/8748 |
| 7 | dC4_g2D = fast(L) exactly | `lri_eh/exact.py` (exact rational `exact(L)` vs `fast(L)`) and table_rc's assertion |
| 8 | HT raw C4 data precision ~1e-10 | to be measured by A4 (not assumed) |

## 11. Risks
* Memory/time at Λmax = 2000 (mitigation: streaming kernel, measured scaling at 400/1000; fall back to Λmax ≈ 1400).
* MKL on AMD nodes (benchmark; use defq Intel otherwise).
* Float64 assembly cancellation (mitigated by sec. 3.5; quantified by A6d and by comparing with the naive per-p
  assembly).
* Misreading of the window definition (gated by A2 Dconn rationals and A5 table at 76 cutoffs).
