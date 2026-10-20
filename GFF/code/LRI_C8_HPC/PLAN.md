# C8(1) of the 1D long-range Ising model: plan (2026-10-02)

Convention ε = 2s − 1; Δ_E = Σ C_n(1) εⁿ. Known: C2–C5 exact, C6 = 14331.68703277 ± 4.9e-7 (exact all-graph
sums), C7 = −322550 ± 41 (SE 10.09, this package's parent `LRI_C7_HPC`). Ratio extrapolation suggests C8 ≈ +8×10⁶
(about 10 %).

**User constraints:** budget 10–50k core-hours on SDSC Expanse (account yun124), "short on time". Target: about
0.1 % relative (allowance ≲ 10⁴), not C7-level precision.

## Method (unchanged from C7, extended by one order)
The finite coordinate-space scheme, forest kernel, binary-cluster trees, meromorphic radial Chebyshev quadrature,
zero-pole control variates, telescoping paired refinements and affine assembly are those of the reviewed C7(1)
package (`reference/C7_1d_full_calculation.tex`, `docs/`). C8 needs:
- **one more Taylor slot per channel (NW = 8)**: loop vectors hold 16 values, slot i ↔ z^(i−(L−1));
- **loops up to 8 (nine vertices)**: 36 vertex pairs, 128-bit packed multiplicity keys;
- **the affine map at order 8**: C2..C8 are affine in the jets of loops ≥ 5 (two loop-≥5 insertions first enter at
  order 9); K from loops ≤ 4; J_L = ∂C/∂v_L (complex step).

## Inputs (`inputs8/`, `gen/`)
- Generators (`gen/`) are the C7 generators generalized to 9 vertices. Regression: regenerating L1–L7 gives
  byte-identical inventories, forest arrays, exact-zero lists, forest polynomials and articulation sets.
- L8: 26,540 classes (7,231 power, 248 primitive, 3,908 exact zeros), 2.5 M coordinate terms. The exact forest
  certificate (bare-series Lagrange inversion as a rational polynomial identity) passes for L = 1..8.
- Every power-free articulation class is an exact zero at L = 5..8, so no extra exclusion is needed (C7 excluded
  that set; here it is empty).
- Order-eight weights (`tools/regenerate_weights.py`, 100 digits, `C8WEIGHTS1`) and Γ jets (8 values).

## Kernel (`src/`)
- C7 kernel with NW = 8, MAX_L = 8, 128-bit keys; new `--mode exact` (deterministic sum over all (L+1)!/2 × Cat_L
  ordered trees, weight 2 per reflection pair, as the archived exact tree quadrature); `--quad-bits 113` replays the
  radial contraction in binary128 on identical weights/trees.
- Validation (`tests/c8_vs_c7.py`, Expanse job 54592375, exact Decimal parsing): weights equal C7's in slots
  r = −1..6 bitwise; power mode bitwise equal to the C7 binary in all seven shared slots at L5–L7, degrees 1, 3, 5, 6;
  QMC within 7.7e-17; exact L4/N20 within 1.6e-17 of the row scale of the archived C7 exact record; binary128 replay
  at L7/N6 and L8/N6 within 6.9e-17 and 2.5e-17 of the row scale. `tests/bench8.py`: L8 costs and an L8/N5 replay
  (2.0e-17).

## Calculation
1. **Exact stage** (`designs/exact8_unit.json`, `designs/exact8_L5_unit.json`): exact all-tree quadratures of loops
   2, 3, 4 at degrees 12/16/20/24 and loop 5 at degrees 6/8/10/12/14. K uses degree 24 (done: C2 exact, C3 and C4
   within 1.3e-12 and 1.1e-9 of their exact values; the degree-20→24 change of K is 1.5e-3 in C8).
   `tools/affine8.py` builds K and J5..J8 and checks C2..C4 against exact values, the top-loop channel rule (C8
   depends on loop 8 only through 3c8−b8, checked numerically: ratio −3) and the deterministic C5 sequence against
   the exact C5. Loop 5 enters C8 deterministically (no sampling), with its last degree step in the allowance.
2. **Pilot** (`designs/pilot8_unit.json`, independent seeds, never in the estimate): all sampled campaigns of loops
   6–8 at unit size: free A/B (QMC, rates .8/.7, uniform power-of-two points), power coarse A/B (degree 1), paired
   refinements 1→3, 3→5, 5→6, 6→7, 7→8 and the check 8→9 (about 1.1k core-hours). Used for (a) the zero-pole controls (`tools/controls8.py`, C7 ridge recipe on the
   coarse campaigns), (b) per-graph Neyman counts and (c) the per-campaign Neyman design for the budget
   (`tools/design8.py`).
3. **Production**: K = 4 fresh-seed batches of the frozen design (`tools/production8.py`, Slurm arrays on
   `shared`, 16-core elements); `tools/combine8.py` combines them, with the inter-batch χ².
4. **Assembly** (`tools/assemble8.py`): mean = K + J5 v5(N5) + Σ weight·(stream @ M), M = controlled map (power) or
   J (free), paired levels differenced within replicates; coverage guard (each active class exactly once per level);
   resolution sequence; lower-order checks C3–C6 against exact values, C7 against −322550 ± 41; spurious-pole
   z-scores; half splits; bootstrap; uncontrolled estimator; post hoc truncation assessment (measured check step plus
   geometric tail).
5. **Top degree**: the benchmark (`tests/bench8.py`, Expanse job 54591957) gives, per replicate with one tree per
   active L8 power graph, 1.8/5.2/14 core-hours at degrees 5/6/7 (≈32 and ≈67 at 8/9), so the estimator runs to
   degree **8** (levels 1→3→5→6→7→8) with an **8→9 check** that never enters the estimate. C7 stopped at degree
   6, and its truncation dominated its error; two more degrees address exactly that. L8 binary128 replay at
   degree 5: long double differs by ≤ 2.0e-17 of the row scale.

## Pre-registered result and allowance
- Quote C8 = estimator ± allowance, allowance = ceil_2sf(max(4·SE, 2|R8|+4·SE_R8, 2|R9|+4·SE_R9,
  half-split shift, 2|loop-5 last degree step|) + 0.01). Empirical, not a rigorous bound.
- Report alongside, post hoc: the truncation-aware value (check step + geometric tail with ratio R_check/R_D,
  100 % tail uncertainty), the lower-order checks, χ², controls effect.
- Flags: deterministic C5 differs from exact by > 1e-6 relative; C6 differs from exact by > 3 SE (expected to be
  explained by the radial truncation, as in C7).

## Budget (core-hours)
Development/validation ≤ 2k; exact stage ≈ 250; pilot ≤ 5k; production the rest, total ≤ 50k.

## Acceptance
- Code: regression tests above pass; Codex code inspection of `src/`, `tools/`, `gen/`, `tests/`, `cluster/`.
- Run: all campaigns verified/merged; coverage guard passes; C2–C5 deterministic checks pass; result reported with
  the allowance and the post hoc assessment.
