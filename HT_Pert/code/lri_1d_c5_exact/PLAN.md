# PLAN: exact finite-cutoff C5(Λ) of the d = 1 LRI frozen-cutoff Hamiltonian truncation

Owner: HT1dPert session (Claude: coordinator + builder). Plan reviewer and final code inspector: Codex (`gpt-6-astra`,
effort `xhigh`, Fast mode via `--cli <HOME>/bin/codex-fast`). Requested by the user on 2026-10-12: "yes, start
the C5 plan with codex review".

## 1. Goal

Extend the validated exact-diagram-sum code for C4 (`<PROJECT>/lri_1d_c4_exact/`, plan
Codex-approved, production to Λ = 2000, all gates passed; called **C4P** below) to order ε⁵ and compute **exact
(float64-rounding-limited) C5(Λ)** in two schemes:

* **raw**: the plain truncated Hamiltonian (HT data: `ht_data.json` "raw" to Λ = 92, "thermal_d7" to Λ = 118);
* **Dconn**: raw + the complete consistent disconnected window, ΔC5^Dconn(Λ) at even Λ.

Target range: Λmax = 400 required, 500 stretch (HT data stop at 118). The tail of C5(Λ) currently limits every C5
extrapolation (HT-based Dconn fits miss the exact C5 = −731.1394766245398 by −0.66..+0.23 depending on the tail
model; the ε⁵ tails need Λ^{-1/2} log^k Λ with k up to 3). The C4 run showed that exact data to large Λ fix the tail
structure (frozen L2 fits predicted C4(2000) from Λ ≤ 1000 to 4e-10). The deliverable is exact C5(Λ) and a measured
tail; C6+ are out of scope.

Re-used design decisions of C4P (all validated there; not re-derived here): 1D bundle series S_n = (V_1 − 1)^n
(positive, no inclusion–exclusion), sphere parity N_s even in every slice, p-independent shell index
m = max_s(4N_s + δ_s + n_s) with the value for reference p at cumulative index cut4 − p (quarter grid, every cutoff in
one run), no Π-pruning, exact per-key rational functional weights (r, g, Π), key amplitude carrying (−1)^pow and
(δ+n)^q with shell weight 1/den^pow, mirror symmetry for reversal-symmetric words, staged Λmax ladder with overlap
gates, snapshot-sha-keyed validation/approval/gate records, gated Slurm submitter on symmetry.

## 2. Acceptance criteria

Gates are staged, with benchmarks separated from production:
* **benchmarks** (single-pattern timing/RSS jobs that write no checkpoints and no results: `run5.py bench`, submitter
  branch `bench`) may run at any Λ once A1–A3 and A6a–c pass locally/in validation; they produce the A7a measurements;
* **production with Λmax ≤ 160** (the validation runs) needs A1–A3 and A6a–c;
* **production with Λmax > 160** needs the validation PASS (A1–A5, A6a–c, A6e, A6d at 80 vs 160), the A9 marker, and
  the A7a benchmark record, all bound to the same snapshot sha (the submitter checks that the benchmark record names
  this snapshot and sizes workers from its measured peak RSS);
* A6d is staged with the production ladder; A8 is the analysis deliverable.

* **A1** exact rationals `inputs/exact_rational_validation.json` (Λ = 2, 4, 6, 8, 12): r5, g5, C5 and the regression
  of r2..r4, g2..g4, C2..C4 ≤ 1e-12 relative.
* **A2** exact variant rationals `inputs/exact5/*` (12 distinct cut4 = 8, 16, 24, 32, 33, 35, 43, 48, 49, 51, 64, 65):
  raw C5, r5, g5 and E_0^(5) = `vac_raw[-1][5]` ≤ 1e-12 relative at every file; Dconn C5 at the even integer cutoffs
  (cut4 = 8, 16, 24, 32, 48, 64) ≤ 1e-12 relative; the window pieces g2D C5 and g2D+g3W C5 at the same cutoffs
  ≤ 1e-12 relative; the bubble identity C5(g2D+g3W) − C5(g2D) = −2·dC4_g2D ≤ 1e-13 absolute; A4, B4, A5, B5 from the
  `vac_raw`/`vac_conn` jets at Λ = 2..16 ≤ 1e-12. Dconn at quarter phases: reported only.
* **A3** independent brute-force float64 RS at order 5 (`vendor/brute_rs_cut4.py` with pmax = 11 — pmax ≤ 10 is
  silently wrong at ε⁵ — and the direct order-5 recursion, not the quotient route) at every quarter cut4 = 4..128:
  E_p^(k) (p = 0..3, k = 2..5), r_k, g_k, C_k ≤ 1e-11 relative (1e-12 absolute where |value| < 0.1); the comparison
  count is asserted (28 per cutoff). This is the only reference at phase 1/2 and odd Λ.
* **A4** HT data: C5 vs "raw" (Λ ≤ 92) and "thermal_d7" (Λ ≤ 118): |ΔC5| ≤ 1e-9 (expected ≤ 3e-11; anything above
  1e-10 is investigated); C2..C4 regression ≤ 1e-11. Dconn C5 vs the S10 full-model Dconn C5 (`inputs/s10_dconn_C5.json`,
  vendored from `lri_1d_coefficient_flow_review`, even Λ ≤ 72) ≤ 1e-9.
* **A5** windows vs `inputs/dC_reconciled.json` on its actual 67 rows (asserted): ΔC5^Dconn ≤ 1e-11 absolute for
  Λ ≤ 100 and ≤ 3e-10 for 102 ≤ Λ ≤ 152 (documented reference noise); components: bubble ≤ 1e-13, rows5 and B5
  ≤ 1e-12 (also vs B's closed-form `top5.jsonl`, vendored, to Λ = 160), rows4, A4, B4 ≤ 1e-12, g2D ≤ 1e-12 for
  Λ ≤ 100 (vs `d5_all.json`, vendored); closed forms ΔR4 = H_odd(Λ−1)/2916 and ΔR5 (sec. 4.3) checked at every even
  Λ ≤ Λmax ≤ 1e-14 relative against the engine's own two-vertex/three-vertex evaluation; the odd-shell invariant (the
  p = 0 ε⁵ vacuum shells at cut4 − 1 and cut4 − 3 vanish at even Λ) holds to rounding.
* **A6** internal: (a) every five-vertex mirror pair gives identical shells (≤ 1e-13 relative) at Λmax = 24;
  (b) mirror-reduced vs full pattern set: C5 identical to ≤ 1e-12 relative at Λmax = 24; (c) the streaming 4D kernel
  equals the dense all-parity reference (C4P `build_rho_dense` generalised to four slices, then even part) to
  ≤ 1e-13 relative for random patterns and every bundle-presence class at N ≤ 40; the new bivariate jets equal mpmath
  derivatives of u_m(ε1)u_m(ε2) to ≤ 1e-13 up to total order 3; (d) staged Λmax overlaps |ΔC5| ≤ 1e-10 absolute
  (160 vs 240 before the 320 submission, 240 vs 320 before 400, 320 vs 400 before 500, final pair before acceptance);
  (e) C2..C4 of every C5 run equal the C4P production result (`results/a8b57b2e8475/c4_1d_L2000.npz`, sha256
  62720cf5…) to ≤ 1e-12 absolute on the common grid.
* **A7** production: (a) timed single-pattern benchmarks of the costliest five-vertex patterns at Λ = 240 and 400
  (wall, peak RSS; benchmark jobs are allowed before A7a exists, see the gate list) produce a snapshot-bound benchmark
  record that sizes the workers; (b) C5raw on the quarter grid cut4 = 0..4Λmax (tuned outputs NaN-masked for
  cut4 < 3, per-p X_p masked for cut4 < p, boolean `valid`), r5, g5, per-p X_p^(5), plus C2..C4; (c) the window pieces
  and C5Dconn on the even grid only (separate arrays; no interpolation, no reuse at other phases); provenance as C4P
  (numerics sha, snapshot sha, per-task producers, snapshot manifest).
* **A8** analysis (blind protocol of C4P `fits/fits_c4_1d.py`: freeze/compare/check, exclusive creation, input
  restricted to the training range, high-precision coefficients): bases include Λ^{-1/2} log^k Λ for k ≤ 3 with
  conditioning reported; the leading log β is free in both schemes (no exact analogue of the C4 −1/17496 is known at
  ε⁵); fits frozen from Λmax = 320 (or the second-largest run) predict the largest run; diagnostic of the fitted
  Λ^{-1/2}·log Λ amplitude against the joint-model ω3 = 556.2 (`lri_hpc_Hamitonian/analysis/extended/analyze_joint.py`)
  using the exact C2..C4(Λ) of C4P for the e-series subtraction; the exact C5 is used only after freezing.
* **A9** Codex inspection of the final code (fresh session) with no unresolved high/medium finding before any
  Λmax > 160 submission (2 inspection rounds; any uninspected fix round is stated in the A9 marker).

## 3. Method

### 3.1 Fifth-order RS: generated, not hand-written
Port `rs.py` of the 2D eps5 code (`lri_2d_coeff_expanse/independent_check/residual_log/eps5/rs.py`, HT2dPert session)
verbatim: non-symmetric RS with intermediate normalisation, W1 = g1 V0 − (P − p)/4 (shift trick: E1 = g1 V_pp),
W_k = Σ_j (r_{k−j} M_j + g_{k−j} V_j), P atoms merged into slice operators R^pow (P − p)^q, single-vertex words dropped
(⟨p|V_j|p⟩ = ⟨p|M_j|p⟩ = 0 for j ≥ 1 since u_0 ≡ 1). The 1D Hamiltonian has the same W1 (H0 = N + P/4, −εP/4), so
the symbolic output is dimension-free. V_j, M_j are **ε-Taylor coefficients** [ε^j] (not derivatives): the whole C5
code uses this convention; the C4P derivative convention (`two_vertex_series`, `VddV_R` with g1·g1) is not reused.
Order 5: 192 multi-vertex words in 60 vertex sequences (K = 2: 25, K = 3: 25, K = 4: 9, K = 5: 1), 149 distinct
(sequence, slice-ops) evaluations, 89 mirror classes; slice ops (pow, q) ∈ {(1,0),(2,0),(2,1),(3,0..2),(4,0..3)};
polynomial prefactors 1, V_pp, V_pp², V_pp³, 2p, 2p·V_pp; coupling monomials up to quadratic in r2..r4, g2..g4.
E-symbols: E1 (shifted), E2 = X2 + 2p r2 + V_pp g2, E3 likewise; their single-chain parts become coupling × prefactor
terms; the 16 genuine **product terms** (11 structures, factors with K ≤ 3) are evaluated over key pairs exactly as
C4P `product_functional` (Σ_p w_p A_p B_p exact per key pair; cum[c − p] = cum[c] − top_p), with the polynomial
prefactor attached exactly to one factor; factors with K = 3 keep per-key records (cheap). The generated term list
is reproducible (hash recorded) and is validated at orders 2–4 by reproducing C4P's hand-written assembly to ≤ 1e-13
(A6e and a dedicated regression test).

### 3.2 ε-jets (new: bivariate, total order ≤ 3)
log u_m(ε) = log u_m + a_m ε + b_m ε² + c_m ε³ + …, a_m = −(ψ(1/2+m) − ψ(1/2))/4, b_m = −(ψ'(1/2) − ψ'(1/2+m))/16,
c_m = −(ψ''(1/2+m) − ψ''(1/2))/96 (1D: x = (1 − ε)/2, single factor; no 2^m of the 2D jets). Line jet for χ modes
(m ≥ 1 only; the zero mode is excluded explicitly — the 2D `Modes` series includes m = 0 and relies on inclusion–
exclusion, a trap): ℓ(α, β)[m] = u_m² e_m^[α] e_m^[β], e^[k] = [ε^k] exp(log-jet). Bundle jets U(n, α, β) =
[ε_i^α ε_j^β] (Σ_{m≥1} u_m(ε_i) u_m(ε_j) y^m)^n by the 2D `Modes.U` recursion (no √, no D, no k-sum). Derivative
orders are distributed over the bundles incident to each vertex by all compositions (2D `_compositions` slot logic,
one side only); a vertex with order > 0 and no χ legs contributes zero. Needed: K = 2 total order ≤ 3, K = 3 total ≤ 2
(including V1V1 on the two ends of one bundle), K = 4 one first-order vertex, K = 5 none.

### 3.3 Zero mode, keys, shells — as C4P
Closed-path exact amplitudes; key δ = (r_s − p)_s; Q removes χ-free slices with δ_s = 0; the key amplitude carries
Wick count × vertex coefficients × path amplitude × Π_s (δ_s + n_s)^{q_s} (−1)^{pow_s}; shell weight 1/den^pow,
den = N_s + (δ_s + n_s)/4 (χ-free slices: den = δ/4, may be negative, ≠ 0 checked; χ slices den > 0 checked);
**physical** shell index m = max_s(4N_s + δ_s + n_s) ∈ [−3, 4Λmax] (the vacuum ⟨0|V R V|0⟩ path through four zero-mode
quanta has m = 4) and **storage** index i = m + MOFF (MOFF = 3), kept distinct everywhere: per-key shells are stored as
S_δ[i], i = 0..4Λmax + MOFF; the cumulative value for reference p at cutoff cut4 is cum_δ[i = cut4 − p + MOFF]; top-shell
corrections (functionals, products), vacuum windows (A4/B4: m = cut4, m ∈ (cut4 − 4, cut4]; B5: m ∈ {cut4 − 2, cut4})
and the odd-shell parity assertion (m = cut4 − 1, cut4 − 3) are all stated in physical m and converted with + MOFF in one
helper (as C4P `functional_from_reduced`, `Chain.top`); per-task reduction to per-p shells and exact-weight functional shells (r, g, Π) for
each needed prefactor (1, V_pp, V_pp², V_pp³, 2p, 2p·V_pp, and the window prefactors of sec. 4).

### 3.4 Densities
* K ≤ 3: C4P kernels (`density3_even` = T01e·diag(S02)·T12eᵀ) with bundle series replaced by jets where needed.
* K = 4: C4P `density4_stream` (scatter of 13, 14, 24; streaming over s1 blocks; in-place dgemm accumulation),
  one first-order vertex via the product rule over its bundles.
* **K = 5 (new streaming 4-slice kernel).** Slices 1..4, bundles b01, b12, b23, b34 (local), b02, b13, b24, b03, b14, b04.
  Split at the middle vertex 2: the crossing bundles b03, b04, b13, b14 enter only through x = ℓ03 + ℓ04 (slice 1),
  y = ℓ04 + ℓ14 (slice 4) and t = ℓ03 + ℓ04 + ℓ13 + ℓ14 (slices 2 and 3):
  C(x, y, t) = Σ_u S04[u] S03[x−u] S14[y−u] S13[t−x−y+u] (3D, O(N⁴), numba);
  Lft(a, b) = [z1^a z2^b] S01(z1) S02(z1 z2) S12(z2), Rgt(c, d) = [z3^c z4^d] S23(z3) S24(z3 z4) S34(z4) (2D, GEMM);
  ρ(N1, N2, N3, N4) = Σ_{x,y,t} C(x,y,t) Lft(N1 − x, N2 − t) Rgt(N3 − t, N4 − y), evaluated as
  (A) P(N1, N2, y, t) = Σ_x Lft(N1 − x, N2 − t) C(x, y, t) — per (t, N2) a Toeplitz GEMM, outputs N1, N2 even only;
  (B1) Q(N1, N2, w, v) = Σ_u S24[u] P(N1, N2, w − u, v − u) — diagonal convolution as a GEMM on sheared views;
  (B2) ρ = Σ_{v,w} S23[N3 − v] S34[N4 − w] Q(·, ·, w, v) — two even-row Toeplitz GEMMs.
  N2 is a final index never summed later, so the kernel **streams over blocks of even N2**; memory ≈ H⁴·8 B (output)
  + O(block·H·N²) temporaries, H = Λmax/2 + 1 (13 GB at Λ = 400, 32 GB at 500). Work ≈ α N⁵ multiply–adds per
  pattern, α ≈ 1 (A ≈ N⁵/4, B1 ≈ N⁵/2, B2 ≈ 0.2 N⁵) before triangular savings; patterns without crossing bundles
  factorise (ρ = Lft ⊗ Rgt, O(N⁴)); patterns with empty slices reduce to the K ≤ 4 machinery. All sums are of positive
  terms. Correctness: A6c against the dense reference for every bundle-presence class.
* Shell contraction 4D: numba, parallel over N1, bounded per-chunk buffers (as C4P `_shell3`), cost ≈ T̄·H⁴ per
  pattern (T̄ ≈ 12 keys).
* Cost estimate (to be replaced by A7a measurements): 6795 mirror representatives × α N⁵ ≈ 1 node-hour at Λ = 200,
  8 at 300, 36 at 400, 110 at 500 (at ≈ 1 TFLOP/s per node); K ≤ 4 negligible.

### 3.5 Assembly
Generic: for every word, coefficient monomial (r_k, g_k evaluated as float arrays on the quarter grid, computed
order by order from the same run) × exact functional shells of the word's chain with the word's prefactor, summed
with `math.fsum`; products via sec. 3.1; r_n = F_r, g_n = F_g, C_n = F_Π of X^(n), n = 2..5. Per-p X_p for diagnostics
and A3. Missing word values are a hard error (the 2D code skipped them silently).

## 4. Window (Dconn) at ε⁵ — definitions to reproduce (even Λ only)
From `lri_hpc_Hamitonian/analysis/eps5_window/` (SUMMARY.txt, A/eng5.py, A/assemble_c5.py, B/topsum5.py,
B/rowresp.py, B/table5.py, reconcile/table_rc.py) and `lri_eh_hpc/lri_eh/` (exact.py, numerics.py):
ΔC5^Dconn = dC5_g2D + dC5_bubble + dC5_rows4 + dC5_rows5 with Ec self-consistent and the outer couplings r(Λ), g(Λ)
at every sub-cutoff (fh = floor to the half-integer grid, integer quarter units, never float floors).

### 4.1 Pieces and how they are computed
* **bubble** = −2·dC4_g2D(Λ) = −2·fast(Λ) (exact identity g1³W = −2 g1² D0 pointwise; checked in rationals).
* **g2D** = T1 + T2 + T3 + T4:
  T2 = Π⟨ψ1|2g1g2D0|ψ1⟩ = 6 g2(Λ)·fast(Λ); T4 = 6 C2(Λ)·Δg4^{g2D}(Λ), Δg4^{g2D} = F_g of the per-p ε⁴ window term
  g1²⟨VRD2RV⟩_p (C4P two-vertex window machinery with the w_g functional; Π(v1) = 6 C2 and Π(m1) = 0 at even Λ);
  T1 = Π⟨ψ1|g1²D1|ψ1⟩ (two-vertex window sum with the ε¹ bubble shells e1, from the p = 0 V1V0 and (P−p)R² vacuum
  chains, cross-checked against the closed shell density d1(E) = −(1/6)(1/E − 2H_E + 2)); T3 = 2Π⟨ψ1|g1²D0|ψ2⟩.
  Key simplification (derived in recon; to be verified, not assumed): at even Λ, D0 on a slice with free energy
  E0 = N_s + P_s/4 is −(1/6)(N_s/2 + [P_s ≥ 5] + [P_s ≥ 13]), independent of Λ and affine in N_s; with
  N_s = den − (δ+n)/4 a D0 insertion with R^k becomes a combination of existing slice operators (R^{k−1}, R^k) with an
  exact per-key, per-slice constant. T3 is therefore a set of two- and three-vertex chains with modified slice ops.
* **rows4** = 2 C2(Λ)(3A4 − B4) (ρ5A = 6C2, ρ5B = −2C2 derived; ρ5A = −3ρ5B checked), A4 = Ec^(4)(Λ) − Ec^(4)(Λ − 1/2),
  B4 = Ec^(4)(Λ) − Ec^(4)(Λ − 1): raw parts from the p = 0 ε⁴ top shells of the same run (A4: shell m = cut4 only;
  B4: m ∈ (cut4 − 4, cut4]); self-consistency part ΔR4 = H_odd(Λ − 1)/2916 for both.
* **rows5** = −B5/3, B5 = raw p = 0 ε⁵ vacuum top shells m ∈ {cut4 − 2, cut4} (odd shells must vanish: A5) + ΔR5;
  A5 drops out of C5.
* ΔR5 = Σ_{odd E ≤ Λ−1} (g1²/(6E))[g2/9 − 1/27 + (1/54)(1/(Λ−E) − 2H_{Λ−E} + 2)] + (1/27)⟨ψ1|ψ2^(4)⟩ with
  ⟨ψ1|ψ2^(4)⟩ = (g1²/6)Σ 1/E² + (g1 g2/6) H_odd(Λ−1) − (g1²/6)Σ (H_E − 1)/E − g1³ Σ_{N1,N2 even ≤ Λ−2}
  (min(N1,N2) + 1)/((N1+1)²(N2+1)) (derived in recon, agrees with exact rationals at Λ ≤ 8 and B's dX5 to 6e-17):
  implemented as a closed form AND as the engine's cancellation-free window sum; the two must agree (A5).
* Pitfalls guarded by tests: literal vs self-consistent Ec (literal carries a spurious log); the two different
  "4.4e-4 log Λ" terms; outer couplings at sub-cutoffs; even Λ only; A's continued windows at Λ = 102..118 and B's
  fitted ρ coefficients are not used as references.

## 5. Implementation layout (new repo `lri_1d_c5_exact/`, git; C4P stays frozen)
* `lib5/series.py` (1D jets, bundle jets U), `lib5/paths.py` (zero-mode paths, patterns, mirror maps; copied from
  C4P/2D with attribution), `lib5/density.py` (K ≤ 4 from C4P; K = 5 streaming kernel; dense reference),
  `lib5/shells.py` (1D shells K ≤ 5), `lib5/keys.py` (key amplitudes, reductions, functionals, key-pair products).
* `rs5.py` (verbatim 2D `rs.py` + term-list hashing), `words5.py` (catalogue: words → chains, prefactors, coupling
  monomials, products; mirror classes), `assemble5.py` (orders 2–5 on the quarter grid), `windows5.py` (sec. 4).
* `run5.py` (driver: `run/assemble/list/bench/sha`; one task per (chain class, pattern representative); checkpoints
  keyed by numerics sha with producer provenance; static multi-node partition; heavy-first scheduling by a real cost
  model, not a constant).
* `validate/` (A1–A6 validators + pytest), `fits/` (A8), `inputs/` (vendored references with MANIFEST sha256:
  exact rationals, exact5, dC_reconciled, ht_data, top5.jsonl, d5_all.json, S10 Dconn C5, the C4P L2000 npz hash),
  `vendor/` (brute RS, exact_fast), `slurm/` (C4P layer: env, validate, bench, node, assemble, gated submit.sh; job
  prefix `l1c5-`).

## 6. Verification (proof commands)
* local (seconds): `pytest -q validate/test_*.py` (jets vs mpmath, kernels vs dense at N ≤ 40, mirror at Λmax = 24 in
  the slow set, rs term list hash and orders 2–4 regression vs C4P), `python validate/v1_exact.py` (A1, A2),
  `python validate/v3_brute.py --cut4max 64` (A3 subset);
* cluster validation job (symmetry, one node): slow tests, A3 to cut4 = 128, ΔR4/ΔR5 closed forms to 2000, Λmax = 80
  and 160 runs with assembly, A4, A5, A6d(80 vs 160), A6e;
* production ladder Λmax = 240 → 320 → 400 (→ 500), each gated by A6d against the previous result, A9 before 240.

## 7. Production
symmetry (amdq first if idle; defq/debugq otherwise; one BLAS process per socket, NUMA-bound; worker count from A7a
peak RSS); data under `<SCRATCH>/lri_1d_c5/`; read-only snapshots `~/lri_1d_c5/<commit>` from `git archive`.
Multi-node arrays with a static partition; per-task checkpoints; assembly job after the array; staged gate records
bound to the snapshot sha and both result hashes.

## 8. Non-goals / constraints
No C6; no edits to other sessions' trees (2D eps5 code, eps5_window, lri_eh_hpc, C4P) — copy/vendor with attribution
and sha256. No multi-minute numerics on the Mac. Dconn at fractional phases, literal Dfull and the other 2D window
schemes: not produced.

## 8b. Pre-review evidence (prototype, not part of the build)
The middle-split K = 5 density (sec. 3.4, steps C, Lft/Rgt, A, B1, B2) was prototyped in plain numpy and compared with a
brute-force all-parity reference (sequential shifted products on the full 4D box, then even part): 75 random
all-occupied VVVVV patterns at N = 6, 9, 12 (68 non-empty): worst relative deviation 2.6e-16.

## 9. Assumptions ledger
| # | assumption | source / how verified |
|---|---|---|
| 1 | model, cutoff, parity, tuning, conventions of C4P | C4P PLAN.md (Codex-approved), production gates |
| 2 | rs.py output is dimension-free for H0 = N + P/4 | W1 identical; validated by orders 2–4 regression vs C4P (A6e) and A1–A3 |
| 3 | jets a, b, c | mpmath tests (A6c) |
| 4 | Dconn ε⁵ decomposition, ρ5A = 6C2, ρ5B = −2C2, bubble identity, D0 affine form, ΔR5 closed form | eps5_window SUMMARY/B/table_rc; recon derivations checked in rationals at Λ ≤ 16; re-verified by A2/A5 |
| 5 | brute RS exact at order 5 needs pmax ≥ 11 | recon: pmax 9/10 wrong, 11 and 15 agree with the exact rational at cut4 = 48 |
| 6 | HT C5 noise ≈ 3e-12 | C8X noise.json; LRI_HT_note |

## 10. Risks
* K = 5 kernel cost/memory (mitigation: measured A7a; Λmax set by measurement, 400 required only if ≤ ~50 node-hours;
  otherwise 320 with the user's agreement).
* Assembly size and conventions (Taylor vs derivative, shift trick, product terms): mitigated by the generated term
  list, orders 2–4 regression vs C4P, A1–A3.
* Float64 cancellation at ε⁵ (larger divergent pieces): exact per-key functionals, fsum, A6d overlaps quantify it.
* Window derivations from the recon (D0 affine form, ΔR5): gated by A2/A5 against independent references.
