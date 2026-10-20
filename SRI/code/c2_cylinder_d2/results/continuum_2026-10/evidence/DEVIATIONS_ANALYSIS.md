# Deviations from the approved PLAN_ANALYSIS.md rev 7 (sha256 f76af1bf…)

## D1 — 2026-10-13, user-approved: A6-1 stages A and B run on symmetry instead of Expanse

- **Cause.** Expanse Lustre stopped serving two small metadata files of the published N=1024 grids (from about
  17:50 EDT on 2026-10-13; `stat` hangs in uninterruptible I/O):
  - `grids/N1024_o4_r4p5_srceebafa82d841/parallel_coeff4_K1025_o4_r4.5.json`
  - `grids/N1024_o4_r4_srceebafa82d841/grid_receipt.json`

  The 52 GB arrays in the same directories stat normally, which points to one unavailable storage target. The same
  probable cause holds for both files; nothing was submitted on Expanse in this round.
- **Change.**
  1. Both N=1024 grids (o4 r4.5 and o4 r4.0, sources eebafa82d841) are REBUILT on symmetry Intel (defq) nodes with
     the package's grid job, using the same parameters.
  2. The 9 rows of stages A and B run there against those grids.
  3. Everything else follows rev 7 unchanged: the rows, the auxiliary cutoffs, the DIAGNOSTIC pool and the ε_grid rule.
- **Why acceptable.**
  - The grid is a deterministic function of (N, oversample, radius_cost, sources).
  - The N=512 pilot showed that Expanse- and symmetry-built data agree to 6.9e-11 in the raw sums.
  - If the Expanse SHA256SUMS becomes readable, the rebuilt arrays are compared against it and the result is recorded.
- **User decision.** "okay do it on symmetry" (2026-10-13, about 20:45 EDT), after a symmetry survey: defq had
  12 idle nodes.
