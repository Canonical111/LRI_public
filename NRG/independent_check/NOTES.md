# NOTES: independent bosonic NRG check

Written from `SPEC.md` only. No other NRG implementation, result or note was opened.

## Files

| file | content |
|---|---|
| `indep_nrg.py` | solver: star, Lanczos chain, NRG map, critical search, finite differences, window audit, h-agreement, `run_pipeline` |
| `selftest.py` | fast checks (a) to (g), about 10 to 15 s locally, exit status 0 iff all pass |
| `run_config.py` | runs one configuration id and writes `<outdir>/<id>.json` (default `out/` next to the script) |
| `cluster/run_all.sbatch` | one symmetry amdq job: self-test, then c1 to c8 in parallel, one single-threaded process each |
| `out/toy.json`, `out/toy40.json` | local smoke runs (not SPEC configurations) |

## How each SPEC item is implemented

- **Star (SPEC 2).** `star_unit`: bin weights and first moments are done analytically,
  w_m = ∫ω^s dω and ξ_m = ∫ω^{s+1}dω / w_m over (Λ^{-(m+1)}, Λ^{-m}]. γ_m² = 2α w_m; α drops out of the chain.
  Λ and s are parsed by mpmath from exact decimal strings ('2.5', '0.502'), so no float64
  representation error enters the chain. M = N + 80.
- **Chain (SPEC 3).** `lanczos` + `wilson_chain`: Lanczos on diag(ξ) from γ/‖γ‖, in mpmath at
  dps = ceil(30 + 1.3 N log10 Λ) + 10, **with full reorthogonalization (classical Gram-Schmidt applied twice)**.
  See ambiguity 1 below. The rescaled Λ^n ε_n and Λ^n t_{n-1} are converted to float64. Every run also
  repeats the chain with M+40 and with dps+40 and records the largest relative change of any rescaled
  coefficient (`chain.convergence_max_rel_change`).
- **NRG map (SPEC 4).** `nrg_step` / `nrg_flow`. Product basis index i·n_b + k (previous kept state i,
  new level k; numpy `kron` order). H = diag(A)⊗1 + e_n 1⊗b†b + c_n(Xᵀ⊗b + X⊗b†). At n=0, A = (−Δ/2, +Δ/2),
  X = σ_z = [[0,1],[1,0]], c_0 = λ_tot/2, e_0 = ε_0. At n≥1, A = Λ E^{(n−1)}, X = B_{n−1}, c_n = Λ^n t_{n−1},
  e_n = Λ^n ε_n. Product parity = parity(i)·(−1)^k. Each sector is diagonalized with
  `scipy.linalg.eigh(driver="evd")` (full diagonalization). The K lowest states per sector are kept (all if
  the sector is smaller). Energies are shifted by the global minimum over both sectors. B_n is built as
  ⟨kept|1⊗b|kept⟩, filling only the even–odd and odd–even blocks. g_n = E_0(odd) − E_0(even) is
  recorded at every step, and the 8 lowest shifted kept energies per sector are recorded for n ≤ 12.
- **Critical coupling (SPEC 5).** `find_alpha_c` follows the SPEC text line by line (bracket loops with 40
  tries and hi > 100 cut-off; bisection with max 48 iterations and the 5e−14·max(1,|mid|) test before each
  evaluation; final convergence check). α_c = (lo+hi)/2; an extra flow at α_c gives the terminal residual
  and the critical flow g_n. Every evaluation (α, f) is stored in `critical_search.history`.
- **Finite differences and audit (SPEC 6).** `fd_alphas`, `fd_derivative`: α± = α_c(1±h) in float64,
  D_n = (g_n(α+) − g_n(α−))/(2hα_c), for h = 1e−9, 1e−10, 1e−11. `window_audit` follows the SPEC rules:
  width, start range, skip rules, L_n = log(max(|D_n|, 1e−290)), least-squares line, y_t = c1/lnΛ,
  Δ_E = 1 − y_t, residual, variation, quality cuts 0.005/0.003, all windows listed, plus count, range and
  midpoint of the quality Δ_E values. `fd_agreement` gives the h-agreement ranges (ambiguity 8).
- **Output (SPEC 8.3).** `out/<id>.json` holds: config; rescaled chain (float64 and 30-digit strings) with
  M, dps and the convergence check; free flow g_n and target; the critical search (status, α_c, bracket,
  iterations, terminal residual, full history); the critical flow g_n, low levels for n ≤ 12, kept counts
  and highest kept energy per step; per h: α±, both denominators, D_n, g_n(α±); the window audit per h; the
  agreement per h; a compact `summary`; timing; environment (python, numpy, scipy, mpmath and its backend,
  `numpy.show_config(mode="dicts")` build dependencies with BLAS/LAPACK, threadpoolctl if importable, thread
  environment variables, Slurm ids, sha256 of the three scripts). Non-finite floats are written as `null`
  (only `t_rescaled[0]`, which is unused).

## Ambiguities and decisions

1. **Lanczos needs full reorthogonalization.** This was found by testing, not assumed. The plain three-term
   recurrence is catastrophically unstable for this star, even at the SPEC precision. After a few steps the
   Ritz values lock onto the high-frequency modes. Rounding errors in those components are then amplified
   by about 1/t_n ~ Λ^n per step, so about Λ^{n²/2} overall. Measured for Λ = 3, s = 0.8 (plain vs
   reorthogonalized, first n with relative difference > 1e−12):
   - n = 13 at N = 30, 49 digits;
   - n = 16 at N = 60, 68 digits;
   - n = 33 even at 268 digits.

   At N = 60, 78 digits, plain Lanczos gives Λ^{59} ε_59 ≈ 1e28 instead of 1.00724. A full
   tridiagonalization of a 30-bin star at the default precision reproduces the star only with
   reorthogonalization: relative eigenvalue error 7e−59 with it and 7e3 without (self-test (a) guards this).
   With CGS2 reorthogonalization the rescaled coefficients converge to constants
   (Λ=3, s=0.8: Λ^nε_n → 1.0072396, Λ^n t_{n−1} → 0.7943533). Changing dps by +40 and M by +40 moves them by
   < 1e−55 and < 1e−43 respectively.
   **If the production code uses the plain recurrence at the SPEC precision, its chain is wrong beyond
   n ≈ 15. This is worth checking.** Cost: O(N²M) in pure-Python mpmath. For c6 (N = 250, M = 330,
   196 digits) I expect about 2 to 3 min per chain build (≈ 9 min with the two convergence re-runs);
   the other configurations take well under a minute.
2. **Precision.** dps = ceil(30 + 1.3 N log10 Λ) + 10 (the SPEC minimum + 10). It is verified per run by the
   dps+40 re-run.
3. **λ_tot.** Taken as sqrt(2α/(s+1)) in float64, as written in SPEC 3. The finite-M star norm differs by a
   factor (1 − Λ^{−M(s+1)})^{1/2}, i.e. by < 1e−60 here. This is recorded as `chain.norm_deficit`.
4. **Ordering of kept states.** [even kept ascending, odd kept ascending]. B_n has exact zeros in the
   same-parity blocks. Self-test (c) checks those zeros against the true matrix elements computed in the
   full Hilbert space.
5. **Truncation at degeneracies.** K is applied literally (no protection of multiplets cut by the
   truncation), as SPEC 4 states. If a level crossing happened exactly at the cut, g_n would be non-smooth in
   α. This was not seen in the toy runs (finite differences agree between h).
6. **Recorded levels.** These are shifted (global minimum subtracted), rescaled energies of step n, from the
   critical flow at α_c. The free flow's levels are stored too. If a sector keeps fewer than 8 states
   (n = 0 with n_b < 8), fewer are listed.
7. **Finite-difference denominator.** The SPEC formula 2hα_c is used literally with α± = α_c(1±h) in
   float64. The float increment α+ − α− differs from 2hα_c by up to about 1e−16/h relative (about 1e−5
   for h = 1e−11). Both are stored (`denominator_2h_alpha_c`, `actual_alpha_increment`). This factor does not
   depend on n, so it shifts L_n by a constant and leaves y_t unchanged.
8. **"Largest n where it agrees with the neighbouring h to 1e−4 relative".** The relative difference is
   rel_n = |D_n(h) − D_n(h')| / max(|D_n(h)|, |D_n(h')|), with neighbours taken in the list
   (1e−9, 1e−10, 1e−11); 1e−10 has two. For each (h, h') the JSON gives:
   - the largest n with rel_n < 1e−4 (pointwise);
   - every contiguous agreement run and the longest one;
   - the full rel_n array.

   As an extra that the SPEC does not ask for, it also gives the same analysis for the local log-slope
   L_n − L_{n−1} (`extra_log_slope`). That test ignores factors that do not depend on n (see Observations).
9. **Window floors.** floor(0.13 N) and floor(0.76 N) are computed exactly as (13N)//100 and (76N)//100,
   to avoid float edge cases. They agree with float evaluation for all SPEC N.
10. **s.** s = 1 − 2Δσ is computed with `Decimal`, quantized to 6 decimals and normalized ('0.8', '0.502',
    '0.998'). That string goes to mpmath and `float()`.
11. **Failure handling.** If no bracket is found, the JSON is still written with `status = bracket_failed`
    and the exit status is 2. If the bisection fails its final width test, the run is flagged
    (`bisection_not_converged`, exit 2), but the finite differences and audit are still done at the
    midpoint.

## Tests performed (`selftest.py`, all pass, about 10 to 15 s)

- (a) Full tridiagonalization (N = M) of 10-bin stars (Λ = 3, 2.5, 2; s = 0.8, 0.502, 0.998; 60 digits)
  and 30-bin stars at the production precision rule. Checks:
  - eigenvalues of the chain matrix = ξ_m (relative error ≤ 3e−50);
  - squared first components × ‖γ‖² = γ_m²;
  - ‖γ‖² = 2α(1 − Λ^{−M(s+1)})/(s+1) exactly;
  - the N = 40 chains are converged under M+40 and dps+40.
- (b) Untruncated NRG vs exact diagonalization of the full Kronecker-product chain Hamiltonian. The
  unshifted NRG energies are divided by Λ^n and given the running offset, then compared sector by sector
  (full Hamiltonian split by the parity operator). Agreement is ≤ 7e−15 in three cases:
  - Λ=3, s=0.8, α=0.3, n_b=4, N=3 (dim 128);
  - Λ=2.5, s=0.502, α=0.07, n_b=3, N=4;
  - Λ=2, s=0.998, α=0, n_b=3, N=4.

  The run also asserts that H never couples parity sectors.
- (c) B_n parity structure, with and without truncation (K = ∞, 5, 7). The kept states are composed back
  into the full Hilbert space, Φ_n = (Φ_{n−1}⊗1)U_n. Checks:
  - they are orthonormal;
  - P Φ = (label) Φ exactly;
  - the true ⟨i|b_n|j⟩ vanish between equal parities;
  - B_n equals Φ_nᵀ b_n Φ_n to ≤ 3e−15.
- (d) Critical search on a tiny system (Λ=3, s=0.8, n_b=4, K=8, N=16): converges in 46 iterations, with
  terminal residual 3e−13. D_n(1e−6) and D_n(1e−7) agree to 4e−8 relative, and |D_n| grows along the
  flow.
- (e) Two identical flows are bitwise identical.
- (f) Window geometry for N = 65 (w = 12, starts 8..36) and N = 250 (w = 32, starts 32..157). A synthetic
  pure power law gives Δ_E = 0.3 in every window. Windows containing g_n ≤ 0 are skipped, and a 1 % bump
  in g fails the variation cut in exactly the windows that contain it.
- (g) Bracket and bisection on analytic residuals: roots 0.3, 0.003 (lo halving), 5 and 37.3 (hi doubling)
  are found to < 5e−14 relative, and a root at 1000 gives `bracket_failed`.

## Toy end-to-end runs (local, about 10 s each)

`toy` (Λ=3, s=0.8, K=16, n_b=6, N=30):
- α_c = 0.44159093314332809, bracket width 2.8e−14, 46 iterations, f(α_c) = −6.6e−10;
- critical plateau g ≈ 0.1899; free-chain g_{N−1}(0) = 0.574250, target 0.172275;
- 56 flows, 0.09 s/flow.

With N = 30 only 2 windows exist (starts 8, 9), and neither passes the cuts (variation 0.015 and 0.0095,
residual 0.014 and 0.009). Their Δ_E are 0.546088 and 0.545171, the same for all three h to 1e−6.

`toy40` (same, N = 40): α_c = 0.44159087373603123. 6 of 10 quality windows, with Δ_E ∈ [0.543603, 0.543969]
and midpoint 0.543786, identical for all h. h-agreement:
- 1e−9 vs 1e−10: n ≤ 35;
- 1e−10 vs 1e−11: n = 3..39.

## Observations

- **Rounding floor of D_n.** In `toy`, D_n(1e−10) and D_n(1e−11) differ by an almost n-independent
  2e−4 relative, so the strict 1e−4 test reports no agreement. The local log-slopes agree to < 1e−4
  for n ≥ 2. The interpretation: float64 rounding in the first steps acts like a tiny shift of α
  (≈ 1e−15 relative). The flow amplifies that shift exactly like the h perturbation, which gives a
  constant relative error ~1e−15/h in D_n. It moves c_0, not the slope. The `extra_log_slope`
  diagnostic shows this directly.
- At α_c the flow leaves the plateau at the end by construction: f(α_c) ≈ 0 means g_{N−1} = 0.3 g_{N−1}(0).
  This is why the windows stop at 0.76 N.

## Known limitations

- The chain is O(N²M) in pure-Python mpmath (no gmpy2 needed). c6 is the slowest (minutes). Use
  `--no-chain-check` to skip the two convergence re-runs if time matters.
- The NRG is plain float64 with full diagonalization of each sector, with no multiplet-aware truncation
  and no checkpointing. Estimated cost per flow on one core: c5 (sector dim 1024) ≈ 40 s;
  c6 (480, N = 250) ≈ 13 s; c1 to c4, c7, c8 ≈ 6 to 16 s. About 56 flows per configuration, so all
  should finish in well under 1 h. Memory is under 0.3 GB per process.
- The selftest runs inside the Slurm job and aborts it on failure. It takes seconds.

## Cluster command

`cluster/run_all.sbatch` (submit with `WORK` set to the cluster copy of this directory,
e.g. `sbatch --chdir="$WORK" "$WORK/cluster/run_all.sbatch"`). For each id in c1 to c8 it runs, in parallel:

    python -u "$WORK/run_config.py" <id> --outdir "$WORK/out" > "$WORK/logs/<id>.log" 2>&1 &

after `source /etc/profile.d/modules.sh; module load python/3.13-mamba` and with
`OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=1`. It first runs
`python -u "$WORK/selftest.py" > "$WORK/logs/selftest.log"`.
