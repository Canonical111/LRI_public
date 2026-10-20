# Validation evidence (SDSC Expanse, 2026-10-02)

**Authoritative run: job 54592375, code copy 846dafb (src identical to 4666608), numbers parsed exactly as Decimal:**
- `c8_vs_c7_T1-T5_job54592375.json`: T1 weights bitwise; T2 power mode bitwise equal to the C7 binary in all seven
  shared slots at L5, L6, L7, degrees 1, 3, 5, 6 (0 mismatches); T3 QMC max relative difference 7.7e-17 (L5), 0 (L6),
  6.7e-17 (L7); T4 exact L4/N20 vs the archived C7 exact record 1.6e-17 of the row scale; T5 binary128 replay L7/N6
  6.9e-17 and L8/N6 2.5e-17 of the row scale. Exit status 0 (every check passed).
- `bench8_job54592375.json`: cost model rerun and the L8/N5 binary128 replay, 2.0e-17 of the row scale.

Earlier runs (superseded; their comparisons parsed JSON through binary64, Codex finding C8-R05), code copy = commit 4666608, binary sha256 8547b415...:

- `c8_vs_c7_T1_job54591847.json`: T1, order-eight weights vs C7 native weights (slots r=-1..6 bitwise) and Gamma jets.
- `c8_vs_c7_T2-T5_job54591898.json`: T2 power mode vs the C7 binary (bitwise, L5-L7, degrees 1-6); T3 QMC vs C7
  (<= 1.4e-16 relative); T4 exact L4/N20 vs the archived C7 exact record. NOTE: this run used the first T4
  criterion (relative per slot), which flagged pole slots that are cancellation residues (~1e-15 of quantities that
  vanish exactly); every physical slot agrees to the last printed digit (z^0..z^3 both channels). The criterion was
  then changed to "relative to the row scale" (tests/c8_vs_c7.py). T5 binary128 replay at L7/N6.
- `bench8_job54591957.json`: per-tree/per-point cost model at L6-L8 and the L8/N5 binary128 replay (4.5e-19 of the
  row scale).
- `affine8_L234.json`: K and J5..J8 from the exact L2-L4 quadratures at degree 24 (campaigns exact8/exact_L2..L4,
  Expanse job 54591923), C2-C4 checks and the top-loop channel rule (ratio -3).
