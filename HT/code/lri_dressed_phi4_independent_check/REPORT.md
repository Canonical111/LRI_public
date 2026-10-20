# Independent check of the dressed zero-mode φ⁴ HT solver (2026-10-08)

## Verdict

The production solver computes the intended Hamiltonian, window and tuning correctly.

- A blind re-implementation was written from the physics definition, without reading any production code, results or
  analysis. It reproduces production at all 38 test points:
  - Δ_ε agrees to ≤ 1.3e-9 where production used nz48, or at δ ≥ 0.2;
  - Δ_ε agrees to ≤ 4.8e-9 where production used nz24/32 at strong coupling. That residual is production's zero-mode
    truncation: the 16-state density basis at the same point agrees with this check to 6e-14.
  - The excited levels and the tuned (g, r) agree to the same level.
- The comparison covers raw, consistent window and literal window, at δ = 0.249 … 0.01 and N = 12, 16, 20. The full
  table is in `results/comparison_vs_production.txt`.
- The weak-coupling expansion is reproduced: Δ_ε = 1/2 − ε/6 + C2(N) ε² + …, with C2(N) equal to the exact rational
  formula to ≤ 3e-7 for N = 0 … 16.

The check is of the computation, not of the physics prescription. It confirms that the solver solves the stated model
(the product-regulator Hamiltonian plus the full-vacuum window) to about 1e-9. It does not say whether that model
converges to the continuum CFT at small Δσ, which is the open question from the dens_v1 campaign.

## Method

The subagent was given only two spec sections: WINDOW.md "Definition" and ALGORITHM.md "Hamiltonian and packed
layout". It worked as follows.

1. It derived H from the GFF radial quantization (DERIVATION.md):
   - u_n² = (2δ)_n/n!;
   - normal ordering that includes the zero mode;
   - the sphere-average vertex;
   - the reflection-even sector.
2. It implemented its own solver in `indep_ht.py`:
   - a sinc-DVR zero mode (production uses an oscillator basis plus a dressed local basis);
   - an independent bath Fock space;
   - the literal and consistent windows;
   - Newton tuning with Hellmann–Feynman Jacobians, continued from weak coupling.
3. It ran 64 unit tests and checked every point on 1.5× finer and 1.5× wider grids. Δ_ε moved by ≤ 4.4e-11. Two
   points were fully retuned on the altered grids and moved by ≤ 5e-12.
4. Runs were on symmetry: jobs 571688 (amdq) and 571710 (defq). Logs are in `results/logs/` and in
   `<SCRATCH>/lri_dressed/independent_check/logs/`.

## Spec notes raised by the check

1. **"Ev(0) = 0" wording in WINDOW.md.** The check defines Ev(0) as the lowest field-even zero-mode eigenvalue, which
   is invariant under a constant shift. Production subtracts the local even ground energy from h_z, so Ev(0) = 0 with
   all Ev(L) measured from the same zero (DENSITY_BASIS.md). The two are equivalent, and the consistent-window
   agreement to 1e-9 confirms it numerically. Only the wording in WINDOW.md is terse.
2. **r at weak coupling.** g = ε/3 + O(ε²) and r = O(ε²); the first-order r vanishes. This is sharper than the brief's
   "r = O(ε)", not a contradiction.
3. **The window acts only at O(ε⁴).** Consistent − raw scales as ε^4.05–4.1, so C2 and C3 are unaffected by the
   window.

## Selected numbers (Δ_ε, consistent window)

| δ | N | independent | production (nz) | difference |
|---|---|---|---|---|
| 0.2 | 20 | 0.4826990785 | 0.4826990618 (24) | +1.7e-11 |
| 0.1 | 20 | 0.5267875102 | 0.5267875102 (48) | −1.3e-11 |
| 0.05 | 20 | 0.6188624494 | 0.6188624494 (48) | −1.5e-11 |
| 0.025 | 20 | 0.7110287555 | 0.7110287549 (48) | +5.9e-10 |
| 0.01 | 20 | 0.8133131277 | 0.8133131265 (48) | +1.2e-9 |

The full per-point results, levels, window tables and convergence data are in `results/indep_results.json` and
`results/tables.md`.

---

## Subagent's report (verbatim summary)

All 38 points were tuned to max|F| ≤ 9e-13, and every point passed grid verification in its first round.

- **Precision floor.** At δ ≤ 0.025, r and g reach 10³–10⁴, which puts a float64 floor of about 1e-11 to 4e-11 on
  Δ_ε.
- **Branch tracking.** The continuations never needed step bisection. E_even2 − E_even1 and E_odd2 − E_odd1 stay
  ≥ 0.50 along every chain, so there is no level-crossing ambiguity.
- **Two code versions.** Two code versions were used (`code_version` field). They differ only in the grid chooser and
  the refinement-acceptance rule; the physics is identical.
- **Zero mode.** A < 0 for δ ≲ 0.2, a double-well zero mode; for example A = −22.6 at δ = 0.01, N = 12, raw.
- **Opposite N-trends at δ = 0.01.** Raw Δ_ε rises with N (0.8238 → 0.8261), while consistent Δ_ε falls
  (0.8157 → 0.8133). This matches the production drift found in dens_v1.
