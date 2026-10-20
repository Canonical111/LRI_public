# Specification: independent bosonic NRG for the sub-ohmic spin–boson model

You are writing an independent check of an existing solver. The point is **code independence**: implement everything
below from this specification only. Do **not** read, import or copy any existing implementation. In particular, do not
open:
- `<PROJECT>/lri_spin_boson_hpc*` (any folder with this prefix);
- `<PROJECT>/NRG/lri_nrg_1d/` (code, data, results or note);
- any Python package named `lri_spin`.

Work only inside `<PROJECT>/NRG/independent_check/`. Allowed dependencies: numpy, scipy, mpmath
(standard library otherwise).

## 1. Model (units ω_c = 1)

H = −(Δ/2) σ_x + Σ_j ω_j b_j† b_j + (σ_z/2) Σ_j λ_j (b_j + b_j†), with spectral density
ρ(ω) = Σ_j λ_j² δ(ω − ω_j) = 2α ω^s on 0 < ω ≤ 1. Tunnelling Δ = 0.1 always.

## 2. Logarithmic discretization (star)

For ratio Λ > 1, bins I_m = (Λ^{−(m+1)}, Λ^{−m}], m = 0, 1, …, M−1. Each bin becomes one mode with
- weight γ_m² = ∫_{I_m} ρ(ω) dω,
- frequency ξ_m = ∫_{I_m} ω ρ(ω) dω / γ_m².

Use M large enough that chain coefficients up to the needed site are converged (M ≥ N + 80 is safe).

## 3. Wilson chain

Tridiagonalize the star by Lanczos, starting from the normalized vector γ_m / ‖γ‖ on diag(ξ_m). This gives on-site
energies ε_n (n = 0, 1, …) and hoppings t_n between sites n and n+1. Then
- λ_tot = ‖γ‖ = sqrt(2α/(s+1)),
- H = −(Δ/2)σ_x + (λ_tot/2) σ_z (b_0 + b_0†) + Σ_n ε_n b_n†b_n + Σ_n t_n (b_n† b_{n+1} + h.c.).

The coefficients shrink like Λ^{−n}. Do the Lanczos in mpmath with enough digits: at least
30 + 1.3 N log10(Λ) decimal digits. Then convert the **rescaled** coefficients Λ^n ε_n and Λ^n t_{n−1} (both O(1)) to
float64. Note that the Lanczos coefficients do not depend on α (α only scales λ_tot).

## 4. Iterative diagonalization (the finite numerical map)

Parameters: Λ, s, n_b (oscillator levels per site), K (states kept per parity sector), N (number of chain sites
0 … N−1), α.

**Basis.**
- Spin: the σ_x eigenbasis, state 0 with σ_x = +1 (energy −Δ/2) and state 1 with σ_x = −1 (energy +Δ/2). In this
  basis σ_z = [[0,1],[1,0]].
- Oscillator: b truncated to levels 0 … n_b−1, b|k⟩ = sqrt(k)|k−1⟩.
- Field parity: P = σ_x ⊗ Π_n (−1)^{b_n†b_n}. Spin state 0 has parity +1 ("even"), spin state 1 parity −1 ("odd").

**Step n = 0** (spin + site 0, not rescaled):
H_0 = −(Δ/2)σ_x ⊗ 1 + ε_0 1 ⊗ b†b + (λ_tot/2) σ_z ⊗ (b + b†).

**Step n ≥ 1** (rescaled energies; the factor Λ^n multiplies all chain terms of this step):
H_n = Λ · diag(E^{(n−1)}) ⊗ 1 + (Λ^n ε_n) 1 ⊗ b†b + (Λ^n t_{n−1}) (B_{n−1}† ⊗ b + B_{n−1} ⊗ b†).
- E^{(n−1)} are the kept, shifted eigenvalues of step n−1.
- B_{n−1} is the annihilation operator of the site added at step n−1, written in the kept eigenbasis of step n−1 (a
  real matrix; it connects only states of opposite parity).
- The parity of a product state (kept state i, new-site level k) is parity(i)·(−1)^k.

**Diagonalize and truncate.** In each step, diagonalize H_n separately in the even and odd parity sectors. In each
sector keep the K lowest eigenstates, or all of them if the sector has ≤ K states. Shift all kept energies by
subtracting the global minimum over both sectors. Build B_n, the new site's b, in the kept basis for the next step.

**Observable.** Record at every step n = 0 … N−1 the parity gap g_n = E_0(odd) − E_0(even), i.e. lowest odd-sector
energy minus lowest even-sector energy at that step. Also record the 8 lowest kept energies of each sector for
n ≤ 12.

## 5. Critical coupling (exact convention)

1. **Target and residual.** Compute the free chain (α = 0) with the same (Λ, s, n_b, K, N). Set
   target = 0.3 · g_{N−1}(α=0) and f(α) = g_{N−1}(α) − target.
2. **Bracket.** Start with lo = 0.01, hi = 2.0 and evaluate flo = f(lo), fhi = f(hi).
   - Repeat up to 40 times: if flo > 0, stop; else lo ← lo/2 and re-evaluate flo.
   - Repeat up to 40 times: if fhi < 0, stop; else hi ← 2·hi; if hi > 100, stop; else re-evaluate fhi.
   - Require flo > 0 > fhi.
3. **Bisection.** iteration = 0. While iteration < 48:
   - mid = (lo+hi)/2;
   - if hi − lo < 5e−14 · max(1, |mid|), stop;
   - fm = f(mid); if fm > 0 then lo = mid, else hi = mid;
   - iteration += 1.

   After the loop, require hi − lo < 5e−14 · max(1, |(lo+hi)/2|); otherwise report failure.
4. **Result.** α_c = (lo+hi)/2. Record α_c, the final bracket, the iteration count and the terminal residual
   f(α_c).

## 6. Relevant eigenvalue y_t from finite differences

At α_c compute flows at α_c(1 ± h) and the derivative D_n(h) = [g_n(α_c(1+h)) − g_n(α_c(1−h))] / (2 h α_c) for each
n, using h ∈ {1e−9, 1e−10, 1e−11}. On the critical plateau log|D_n| grows linearly in n with slope y_t ln Λ.

**Window audit** (apply to each h separately, with L_n = log|D_n| and g_n the critical flow at α_c):
- **Windows.** Width w = max(12, floor(0.13 N)). Starts run over range(max(8, floor(0.13 N)), floor(0.76 N) − w), and
  the window is n = start … start+w−1.
- **Skip** a window if any g_n ≤ 0 or any L_n is not finite. Use log(max(|D_n|, 1e−290)).
- **Fit.** Least-squares line L_n ≈ c_1 n + c_0 over the window. Then
  - y_t = c_1 / ln Λ and Δ_E = 1 − y_t;
  - residual = max |L_n − (c_1 n + c_0)|;
  - variation = (max g − min g)/|mean g| over the window.
- **Quality windows** have variation < 0.005 and residual < 0.003. Report every window (start, Δ_E, residual,
  variation), the number of quality windows, and their Δ_E range [min, max] and midpoint.

For small h the finite difference is limited by rounding (≈ 1e−16/h relative error). For large h it turns nonlinear
once h·α_c·Λ^{y_t n} is no longer small. Comparing the three h values shows where D_n is trustworthy; report, per h,
the largest n where it agrees with the neighbouring h to 1e−4 relative.

## 7. Configurations to run (on the cluster, not locally)

| id | Δσ | s = 1−2Δσ | Λ | K | n_b | N |
|---|---|---|---|---|---|---|
| c1 | 0.1 | 0.8 | 3 | 64 | 10 | 65 |
| c2 | 0.05 | 0.9 | 3 | 64 | 10 | 80 |
| c3 | 0.01 | 0.98 | 3 | 64 | 10 | 105 |
| c4 | 0.2 | 0.6 | 3 | 64 | 12 | 65 |
| c5 | 0.249 | 0.502 | 3 | 64 | 16 | 65 |
| c6 | 0.001 | 0.998 | 3 | 48 | 10 | 250 |
| c7 | 0.1 | 0.8 | 2 | 64 | 10 | 103 |
| c8 | 0.15 | 0.7 | 2.5 | 64 | 10 | 78 |

(s must be the exact decimal 1 − 2Δσ rounded to 6 digits, e.g. 0.502, 0.998.)

## 8. Deliverables

1. **`indep_nrg.py`**: the solver (chain, NRG map, critical search, finite-difference derivative, window audit).
2. **`selftest.py`**: fast checks (seconds) that run locally:
   - (a) the Lanczos chain reproduces the star: the eigenvalues of the tridiagonal chain matrix equal ξ_m, and the
     squared first components times ‖γ‖² equal γ_m², for small M;
   - (b) for a tiny system that is not truncated (e.g. Λ=3, s=0.8, α=0.3, n_b=4, N=3, K large enough to keep
     everything), the NRG spectrum at the last step (unshifted, divided by the scale factor) equals exact
     diagonalization of the full chain Hamiltonian built from Kronecker products;
   - (c) the B_n parity structure;
   - (d) the finite-difference derivative is consistent between two h on a small system.
3. **`run_config.py`**: runs one configuration id and writes `out/<id>.json` with
   - the rescaled chain coefficients,
   - α_c, bracket, iterations, terminal residual,
   - the critical flow g_n for all n,
   - low levels for n ≤ 12,
   - D_n for each h,
   - the window audit for each h,
   - the agreement range per h,
   - timing and the library versions (numpy, scipy, mpmath, BLAS from `numpy.show_config()` or threadpoolctl if
     present).
4. **`cluster/run_all.sbatch`**: one Slurm job for the symmetry cluster, which runs the 8 configurations in parallel
   on one node, one process each, with OPENBLAS_NUM_THREADS = 1:
   `#SBATCH -p amdq --exclude=cn112 -N1 --exclusive --mem=64G -t 12:00:00 --no-requeue`; environment
   `source /etc/profile.d/modules.sh; module load python/3.13-mamba` (it has numpy, scipy, mpmath); paths relative to
   a directory `$WORK` given as an environment variable. Do **not** submit it; the coordinator will.
5. **`NOTES.md`**: any ambiguity you resolved and how; what you tested; known limitations.

Keep local runs to seconds (self-tests and tiny configurations only). The real configurations run on the cluster.
