# Independent check of the 3D dressed-window HT solver

Date: 2026-10-08. Scope: package `lri_3d_window_hpc` (releases 33ef4f3 / ccd055a, numerics unchanged since the zip), as run in the Expanse campaigns `grid18`, `grid18sri`, `l18x06`.

Correction (2026-10-18): the model statement under A said "an exact zero-mode oscillator". The zero mode is not
treated exactly; the line now says how it is truncated. A1 compares two such truncations (the 16-state trained basis
and K = 16 or 24 local eigenstates). Nothing else in the report has changed.

**Question (user):** is the solver correctly calculating what we want?

There are two separate questions here:

- **A.** Does the code compute the finite model it claims to compute? That model is:
  - the Hamiltonian H0 + r⟨:φ²:⟩ + (g/12)⟨:φ⁴:⟩ on S² in Gaussian normal ordering;
  - bath truncated at N_b ≤ L; the zero mode is kept in a finite basis of n_z = 16 states per parity (not limited by
    the level cutoff), and the full Hamiltonian, its couplings to the bath included, is diagonalized on the product;
  - J=0, inversion-even sectors;
  - the self-consistent vacuum window;
  - (r, g) tuned so that Δσ = x and Δχ = 3 − x.
- **B.** Does that finite model, as L grows, give the continuum Δε(Δσ) of the 3D long-range Ising model?

## Verdict

**A: yes, verified.** A clean-room re-implementation reproduces the package everywhere it was tested:
- cutoffs L = 6, 8, 10 and 12, with x from 0.7499 down to the short-range point 0.518149;
- the window and raw schemes;
- the scalar sector and the J=1 and J=2 diagnostic sectors.

It agrees to between 1e-13 and 3e-12 at fixed couplings, and to ≤ 2e-11 after independent tuning. The non-perturbative results also agree with the separate perturbative package (C_n(L) through ε⁸) to the size of the ε⁹ remainder, at every cutoff L = 6–14.

**B: only partly.**
- The finite model has the right weak-coupling content:
  - C0 and C1 are exact;
  - the exact formula for C2(L) converges to the continuum value C2(3);
  - C3(L) extrapolates consistently with the continuum.
- At L ≤ 18 the curve is not yet close to the continuum, at a level well above its apparent cutoff convergence:
  - At x = 0.7, where the resummed ε-expansion fixes the continuum to about ±3e-5, HT(L18) lies 2.1e-4 below it. Every L-extrapolation of L8–L18 lands 2.4–3.1e-4 below.
  - At x = 0.725 the extrapolations miss by 2.5–6e-5, against a continuum uncertainty of 3e-7.
  - In both cases the sequence is still moving away from the continuum at L18.
- At the short-range point the curve drifts away from the bootstrap value as L grows: 1.41292 at L8, 1.41864 at L18, against 1.4126253. Near x_SR the convergence is expected to be logarithmically slow (the crossover operator σχ is nearly marginal there), so this is not by itself a contradiction. It does mean the endpoint cannot be read off finite-L data.

In short, the numbers are right for the finite model. The open issue is the L → ∞ limit, not the code.

## A. Code verification

### A1. Clean-room solver

The code is in `independent_check/` (`indep_ht3d.py`, `indep_spin.py`). It was written from the physics definition only: the formulas in docs/METHOD.md, re-derived. It never reads or imports `code/ht3d`. It deliberately uses different methods:

| Step | Package | Independent solver |
|---|---|---|
| Fock basis | species blocks, rank/unrank graph | sorted mode-index tuples, all M, complex Condon–Shortley Y_lm |
| J=0 (and J=1, J=2 highest-weight) states | SVD null space of J₊ (gesdd → gesvd fallback) | dense `eigh` of the Casimir J₊ᵀJ₊ per species block (spectrum J(J+1), gap ≥ 2) |
| scalar vertices ⟨:B^k:⟩ | north-pole evaluation | evaluation at an arbitrary generic point (θ, φ) = (1.1, 0.7), checked against (2.3, −1.9) |
| J=1/J=2 vertices | polar Gauss at azimuth 0 with M selection | full-sphere Gauss–Legendre × offset trapezoid |
| local zero mode | 16-state density-trained basis from an L6 teacher | the lowest K eigenstates of the current local Hamiltonian in a 400-level number basis (K = 16 and 24) |
| window fixed point | Newton with the p0 derivative | bracketed Brent root at each sub-cutoff |
| tuning | safeguarded Newton in θ variables | `scipy.optimize.root` (hybr) in (r, g), started 2% (L10/L12) or 8% (L8) away from the package's couplings |

**Structural checks** (all pass):
- Gegenbauer identity C_k^x(μ) = Σ(2l+1)u²P_l(μ): 1.4e-15.
- Number of scalar states: 3, 10, 33, 110 and 1285 at L = 2, 4, 6, 8 and 12. These equal the perturbative package's `scalar_bath_states` and the original report's 1285 at L12.
- The scalar vertices do not depend on the evaluation point: ≤ 4e-13 at L12. This checks rotational invariance of the J=0 basis and the phase conventions.
- Imaginary parts ≤ 7e-15; inversion selection is exact.
- Free spectrum (r = g = 0): even states 0, 2x, 4x, …; odd states x, 3x, x+2, 5x. Exact.

**Fixed-coupling replay** at the package's tuned (r, g). The table gives the maximum |Δ_thermal(indep) − Δ_thermal(package)|. Δσ and Δχ also reproduce x and 3 − x to ≤ 2.1e-11.

| L | scheme | x values | max diff | notes |
|---|---|---|---|---|
| 6 | window | 0.6 | 4e-12 | the package's L6 record is its teacher run |
| 8 | window | 0.7499, 0.725, 0.7, 0.65, 0.6, 0.55, 0.518149 | 6e-13 | local basis K = 16 and K = 24 agree |
| 10 | window | the same 7 values | 3e-13 | |
| 10 | raw | 0.7499, 0.7, 0.6, 0.518149 | 2e-12 | |
| 12 | window | 0.7499, 0.7, 0.6, 0.55, 0.518149 | 3e-13 | |
| 8 | J=1, J=2 (both field parities, 6 levels each) | 0.6, 0.518149, 0.7 | 3e-12 | checks the descendant diagnostics |

**Independent tuning.** The table gives the maximum |ΔΔ_thermal| and the agreement of the tuned couplings.

| L | scheme | x values | max |ΔΔ_thermal| | couplings |
|---|---|---|---|---|
| 6 | window | 0.6 | 5e-12 | r, g to 1e-10 |
| 8 | window | all 7 | 4e-12 | r, g to 10–12 digits |
| 10 | window | all 7 | 1.9e-11 | r, g to ≤ 3e-11 |
| 10 | raw | 4 | 4e-12 | r, g to ≤ 2e-11 |
| 12 | window | 0.7499, 0.7, 0.6, 0.55, 0.518149 | 3e-13 | r, g to ≤ 5e-12 |

These differences are at the package's own tuning tolerance (3e-11).

At L12, x = 0.7499, scipy's `root` returns success = False, but the residual is 2.8e-14 and both couplings and Δ match the package (ΔΔ = 2e-15). This is the usual hybr "no further progress" stop when r ≈ 7e-8; it is not a disagreement. The first L12 runs at x = 0.7499, 0.55 and 0.518149 used an 8% + 0.01 displaced start and hit NaN in the local diagonalisation. They were rerun from a 2% multiplicative start.

The trained 16-state local basis gives the same answer as 16 or 24 local eigenstates, to 1e-13. The local truncation is therefore converged at these cutoffs, consistent with the package's nz12 side check.

### A2. Cross-check with the perturbative package (lri_3d_hpc)

This compares the non-perturbative Δ(x; L) from the grid with Σ_{n≤8} C_n(L) εⁿ, using the reference coefficients `results/reference_coefficients_L14.json`, at the same cutoff and in the same scheme.

| x (ε) | L | difference | size of the ε⁸ term |
|---|---|---|---|
| 0.7499 (4e-4) | 6–14, window and raw | ≤ 4e-14 | 3e-25 |
| 0.745 (0.02) | 6–14 | ≤ 1.2e-11 | 1e-11 |
| 0.74 (0.04) | 6–14 | 4.5–7.4e-10 | 3e-9 |
| 0.725 (0.1) | 6–14 | 1.3–2.1e-6 | 4e-6 |

The differences are exactly the expected ε⁹ remainder. The two packages share the vendored `ht3d` basis and vertex code, so this test covers:
- the non-perturbative parts: the local oscillator, window recursion and tuning;
- the window scheme at order ε⁴–ε⁵ (raw and window differ by 5.4e-10 at x = 0.745 and L10, and the agreement is ≤ 1.2e-11, within the 3e-11 tuning tolerance).

The basis and vertex code are covered by A1 instead.

## B. Physics: approach to the continuum

### B1. Finite-L ε-coefficients against the continuum

C_n(∞) are the diagrammatic d=3 values from the condensed note:
- C2 = (2 − π + 4 log 2)/9;
- C3 = −0.353582, C4 = 1.228064, C5 = −5.850351;
- C6 = 33.5754(5), C7 = −220.35(13).

| n | C_n(14), window | increments L8→10→12→14 | extrapolation (L^-p, p = ½ / 1 / free) | continuum |
|---|---|---|---|---|
| 2 | 0.17974 | +7.4e-4, +4.8e-4, +3.4e-4 | → 0.18122 exactly (rational formula, tail −40/(243√π) L^-3/2) | 0.18122 |
| 3 | −0.31962 | −0.0100, −0.0072, −0.0054 | −0.378 / −0.357 / −0.371 | −0.35358 |
| 4 | 0.69677 | +0.043, +0.033, +0.025 | 0.968 / 0.867 / 1.035 | 1.22806 |
| 5 | −3.0242 | −0.20, −0.18, −0.15 | −5.73 / −4.43 / no convergence | −5.8504 |
| 6 | 14.909 | +1.08, +0.96, +0.85 | 30.8 / 23.0 / no convergence | 33.575 |

What this shows:
- C2 is proven to converge to the right continuum value, and C3 is consistent with it.
- C4–C6 at L14 are only 45–57% of their continuum values and converge like L^-½ or slower.
- C4 extrapolates 16–30% low, so it is not yet clear whether the finite model reproduces the continuum at order ε⁴. The 1D HT showed the same symptom at a much smaller level (a C4 offset of −0.19% at Λ ≈ 100).
- Running the perturbative package (lri_3d_hpc) to L16–L20 is the cheapest decisive test.

### B2. Non-perturbative curve against the resummed ε-expansion

The resummation is Borel–Padé of the series through C7: 29 approximants, with Borel–Leroy b = 0–4 and Padé orders of total degree 4–5. The spread across approximants is quoted as the uncertainty.

| x | ε | continuum (BP) | HT L18 | L18 − continuum | L16→18 step | L-extrapolations − continuum |
|---|---|---|---|---|---|---|
| 0.745 | 0.02 | 1.4967365 | 1.4967362 | −2.8e-7 | +4.9e-8 | −2.8e-7 … +3e-8 |
| 0.74 | 0.04 | 1.4936033 | 1.4936022 | −1.1e-6 | +1.1e-7 | −1.2e-6 … −4.6e-7 |
| 0.725 | 0.1 | 1.4848769(3) | 1.4848591 | −1.8e-5 | −7.4e-7 | −6.3e-5 … −2.5e-5 |
| 0.7 | 0.2 | 1.47214(3) | 1.4719290 | −2.1e-4 | −5.5e-6 | −3.1e-4 … −2.4e-4 |
| 0.675 | 0.3 | 1.4612(4) | 1.4605027 | −6.7e-4 | +2.0e-5 | unstable |
| 0.65 | 0.4 | 1.452(2) | 1.4505070 | −1.1e-3 | +1.1e-4 | unstable |

What this shows:
- For x ≥ 0.74 the remaining cutoff error at L18 is 6–10 times the last L step; at x = 0.725 and 0.7 it is 24 and 38 times.
- At x = 0.7–0.725 the sequence is moving away from the continuum; it must turn around at larger L, which is what the slowly converging C4+(L) predict.
- Standard L-extrapolations (geometric, or power laws with p = ½, 1, 3/2, or free p, fitted to L12–L18) are biased low by 2.4–3.1e-4 at x = 0.7.
- So at moderate x, L ≤ 18 data alone do not determine Δε to better than a few 1e-4. The bias is probably larger at stronger coupling, where it cannot be calibrated.

### B3. Monte Carlo

The 3D LRI MC evaluation (P1, 2026-09-30) accepts only one point: x = 0.7, Δε = 1.47314 ± 0.00118 (stat) ± 0.00230 (sys). This is consistent with both HT (1.47193) and the continuum series (1.47214), so it does not discriminate between them. The other MC points are cross-check-failed or model-limited, and near the SR end they are dominated by crossover finite-size drift (for example, 1.449 at x = 0.525 for the L 64→128 pair).

### B4. Short-range endpoint

At x = 0.518149 the cutoff sequence is:

| L | 8 | 10 | 12 | 14 | 16 | 18 |
|---|---|---|---|---|---|---|
| Δ_thermal | 1.41292 | 1.41455 | 1.41592 | 1.41701 | 1.41789 | 1.41864 |

The bootstrap value is 1.41262528(29). The increments shrink only by a factor of about 0.85 per +2 in L, and extrapolations give 1.423–1.433.

- The original raw report already notes that the SR limit is not reproduced. The window scheme does not change that.
- Behan et al.: at x_SR the coupling σχ is marginal, so the approach to the endpoint is logarithmic, and any finite-L value there is not an endpoint measurement.

### B5. Conformal diagnostics (the package's own, verified in A1)

**Spacing errors** of free-charge descendants, which should vanish in a conformal theory (window scheme):

| descendant | x = 0.518, L6 → L18 | x = 0.6, L6 → L18 | x = 0.7 |
|---|---|---|---|
| σ, J=1 | 0.030 → 0.013 | 0.024 → 0.018 | 0.0033 → 0.0049, slowly rising |
| ε, J=1 | 0.095 → 0.021 | 0.075 → 0.043 | |
| χ, J=1 | | 0.07 at L18 | |

The original raw code had a σ J=1 spacing error of 0.24 at L10 for x = 0.518. The window scheme therefore improves conformality greatly at strong coupling, but at weak coupling the error (about 0.12 ε²) is not yet decreasing with L.

**Stress-tensor candidate** at x_SR (lowest even J=2 state), which should approach 3:

| L | 8 | 10 | 12 | 14 | 16 |
|---|---|---|---|---|---|
| Δ | 3.095 | 3.089 | 3.084 | 3.079 | 3.075 |

It moves slowly toward 3 in the window scheme; the raw code moved away from 3 (3.275 at L8, 3.302 at L10).

## Implications for the L20 decision

1. L20 adds one cutoff to a sequence whose remaining error is dominated by slow, possibly non-monotone convergence. A single extra cutoff will not settle the L → ∞ limit by itself.
2. Before spending about 5k SU on an L20 grid, calibrate the extrapolation where the answer is known:
   - Weak coupling: at x = 0.7–0.745, any extrapolation ansatz must reproduce the resummed ε-expansion (known to ≤ 3e-5). Today none does at x = 0.7 or 0.725.
   - Run the perturbative package to L16–L20 to see whether C4(L) → 1.228.
3. The planned single L20 point at x = 0.6 remains useful as a probe of the sequence's shape.

## Files

- `independent_check/`:
  - code: `indep_ht3d.py` (scalar solver), `indep_spin.py` (J=1/J=2), `run_compare.py`, `t_spin.py`, `t_basic.py`;
  - sbatch files and per-task JSON results;
  - the package records extracted for the comparison (`indep_extract.json`).
- Expanse: `$HT3D_DATA/indep/` holds the logs and results of:
  - the comparison array 54766121;
  - the debug jobs 54766593 (spin sectors), 54767650 (L8) and 54768468 (L10 re-tunes).
