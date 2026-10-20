# Full-vacuum window correction (opt-in)

`--window vacuum [--window-mode consistent|literal]`. The default `--window none` is the unchanged raw regulator; it
executes the original arithmetic. Its equality with release e637dfd to ≤ 1e-12 is checked by
`scripts/baseline_equality.py`.

## Why

In the continuum 1d LRI CFT every descendant spacing E(∂ⁿO) − E(O) = n is exact. The raw product regulator
violates these spacings, and the violation does not decay with the bath cutoff:

| δ | v1(σ), cut 8 → 20, raw | with the consistent window |
|---|---|---|
| 0.2 | +0.0035 → +0.0031 | +0.0012 → +0.0008 |
| 0.1 | +0.067 → +0.065 | −0.005 → −0.004 |
| 0.05 | +0.164 → +0.154 | −0.016 → −0.013 |

Further points:
- Changing nz from 24 to 32 to 40 changes these numbers by < 4e-6, so they do not come from zero-mode truncation.
- A bath state of level N can carry vacuum fluctuations of the bath only up to level cut − N. The energy of that
  missing vacuum window is the artifact.
- Bath-only vacua remove only 10–75 % of it. They miss the zero-mode tadpole (g/2)⟨q²⟩, which cancels the −g/2 in A.
- The full vacuum, zero mode included, removes 75–100 % of v1(σ) and most of v1(shadow).
- Evidence: `lri_dressed_phi4_hpc_loop/evidence/` (symmetry jobs 568998 and 569040; 123 prototype records).

## Definition

- **Vacuum energies.** Ev(L) is the vacuum energy (field-even, reflection-even) of the same product Hamiltonian at
  bath cutoff L, with the same δ, θ, nz, osc and local basis.
  - Normal-ordered W_j never pass through a level above both endpoints, so H(L) is exactly the N ≤ L projection of
    H(cut).
  - Ev of an odd L equals Ev(L − 1). Ev(0) = 0.
- **Window shift.** Every bath state of level N, in both field parities and both reflections, gets the bath-diagonal
  shift D(N) = Ev(cut) − Ev(cut − N), with D(0) = 0.
- **`literal`:** Ev(L) is the lowest eigenvalue of H(L).
- **`consistent`** (default): Ev(L) is the lowest eigenvalue of H(L) + D_L, built from the corrected lower levels.
  - The scalar fixed point s = λ_min(s) is solved by Newton with F′ = −p₀, where p₀ is the bath-N = 0 weight of the
    vacuum vector. F is concave, so Newton converges monotonically after at most one step.
  - At the cutoff itself, s is the ground energy of the main problem.
  - This is the analogue of the consistent "Dconn" of the frozen-cutoff analysis. The literal construction
    double-counts the bubble-bubble class there.
- **Tuning.** The tuning conditions are unchanged. The Newton Jacobian adds Σ_N w_k(N) ∂D(N)/∂θ by
  Hellmann–Feynman on the stored vacuum vectors.
  - literal: ∂Ev = ⟨∂H⟩;
  - consistent: ∂Ev(L) = (⟨∂H⟩ − Σ_{N>0} w_N ∂Ev(L − N)) / p₀.
  - It agrees with finite differences to ~1e-8.
- **Robustness.** A window fixed point that fails at an extreme line-search trial point rejects that trial and does
  not abort the solve.

## Records and checks

- **Result records.** `window: "vacuum"` and `window_correction` = {mode, D_by_N, Ev, iteration counts, fixed-point
  residuals, timing}.
- **Configuration fingerprint.** It contains `window`, `window_mode`, `window_tol` and `window_maxiter`, so raw and
  corrected results are never mixed.
- **`validate_result` checks:**
  - the window table is complete, with D(0) = 0;
  - every fixed-point residual is ≤ 5 × tol × max(1, |Ev|).
- **Diagnostic.** `python -m lri_dressed identities --result R --output O` reports v1 and v2 for σ, the shadow and ε
  at the stored θ, with overlaps and ambiguity flags. It uses the free L₋₁ with the dressed a₀ and is a diagnostic
  only.

## Not included

- Connected or folded window classes, a zero-mode window, and any other matching.
- Residual identity violations remain:
  - at δ = 0.1, about −0.004 for σ;
  - at δ = 0.05, about −0.05 for ε;
  - at δ = 0.2, those that decay with the cutoff.

  They are reported, not hidden.

## Cost

- The window costs about 1.3–2× a raw tuning solve at cut ≤ 12, measured on symmetry.
- Sub-cutoff operators are stored for each δ, at about 1.5–2× the cut-level bath storage for tensor and little for
  ladder.
- `plan --window vacuum` includes them.
