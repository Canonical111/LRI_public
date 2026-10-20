# Performance and validation report

All correction timings below are medians of **three independent processes per configuration**, in the local Linux container with a four-CPU quota. Compilation was warmed at cutoff 4 before the timed solver work. These are numerical-core timings: checkpoint I/O, process startup, and scheduler overhead are not included. Peak RSS includes the Python/Numba runtime. They are not Expanse measurements or predictions of 32/64-thread speedup.

## Paired correction solver

| Cutoff | Degree | Threads | Incoming addon (s) | Optimized (s) | Speedup | Incoming RSS (MiB) | Optimized RSS (MiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 7 | 1 | 10.876 | 5.498 | 1.98x | 609.6 | 572.5 |
| 50 | 7 | 2 | 6.468 | 3.012 | 2.15x | 609.6 | 572.6 |
| 50 | 7 | 4 | 5.411 | 2.323 | 2.33x | 609.5 | 572.4 |
| 60 | 7 | 4 | 14.823 | 6.828 | 2.17x | 1425.2 | 1340.9 |
| 118 | 5 | 4 | 4.425 | 1.931 | 2.29x | 675.9 | 590.8 |

The timing and RSS gains are incremental to the **already reduced correction-only basis** in the incoming addon. We do not count its earlier P<=11,Q<=8 reduction as a new optimization. State counts and asymptotic basis growth in this correction solver are unchanged. Most of the incremental gain comes from eliminating duplicated calibration/high-order arithmetic; memory savings are more modest (roughly 6--13% in these measurements).

At cutoff 50 the new one-to-four-thread speedup is about 2.37x. No scaling beyond four threads was measured locally. Larger-core/NUMA calibration must be repeated on the target node.

## Bottleneck evidence

`profile_old40.profile.txt` shows 248 ladder calls, two complete basis builds, and two calibrations. In that run, ladder applications accounted for about 50% of total time, inner products 17%, and basis construction 10%; calibration and quotient totals overlap those categories and must not be added again. The optimized degree-seven solver uses one basis/calibration and 140 ladder calls, with lower maximum operator-jet degrees. The diagonal correction is a fused lookup/contraction instead of repeated dense-diagonal allocations. Profiling therefore motivated the major changes rather than isolated scalar micro-optimizations.

## Matrix-free finite-parent tool

The following is a **single-run**, warmed comparison at retained cutoff 8, parent cutoff 16, degree 7, four threads—not a large-cluster scaling benchmark.

| Tool | Runtime (s) | Peak RSS (MiB) |
|---|---:|---:|
| Incoming dense Schur oracle | 5.5981 | 515.9 |
| Matrix-free state-specific elimination | 0.1320 | 180.7 |

The observed ratio is 42.4x in time and 2.85x in RSS. This avoids forming all parent-by-parent operator matrices, so its operator storage becomes O(parent states * perturbative order + edges), not O(parent states^2). It still constructs the finite parent basis and is not an analytic infinite-shell matching kernel.

An additional retained-16/parent-32 calculation completed on 163,724 basis states (including auxiliary parity sectors). Maximum parent-versus-matched energy-coefficient discrepancy: 2.18e-10; maximum ordinary-recursion versus parent Rayleigh-quotient thermal discrepancy: 2.91e-11. No physical continuum target was used.

## Correctness and operational validation

**32 tests pass** in the final source. They cover all supported degrees at multiple small cutoffs; original paired solver comparisons; independent SciPy seventh-order recursion; random-vector fused diagonal contractions; one/four-thread equality; exact planner edge counts; int64 edge signatures and exact rank/unrank round trips above 2^31; dense-versus-matrix-free Schur comparisons; malformed/nonfinite output; source/checkpoint mismatches; safe interruption and restart; attempt limits; stale atomic temporary files; exclusive locks surviving supervisor death; double-correction rejection; and a fully completed scalar checkpoint that performs no basis rebuild. Tests do not allocate a billion-state basis.

Across the repeated correction benchmarks the largest difference in delta_C, delta_r or delta_g is 1.09e-09. The regression tolerance is atol=1e-8, rtol=2e-11. No precision reduction or tolerance relaxation was used for speed. Exact fourth-order delta checks remain much smaller than the acceptance threshold of 1e-10. These are implementation checks, not physical error bars.

A final release validation receipt and a gated degree-seven cutoff-60 result are retained under `benchmarks/`. A two-item lane was also exercised locally through manifest creation, solver publication and read-only status inspection. Slurm itself was not available for execution, so site submission, affinity, signal propagation and shared-filesystem locking need the supplied cluster validation procedure. Single-cutoff MPI and GPU backends are not enabled.

## Reproduction

`bench_item.py` reproduces each fresh-process observation. `run_local.py` generates three replicates per configuration, skipping existing files. `summarize.py` rebuilds `SUMMARY.json`. The small reference addon is preserved under `reference/original/`; it does not substitute for the separately reviewed campaign repository. Use an empty NUMBA_CACHE_DIR to measure true cold startup separately.

`docs/ALGORITHM.md` explains the exact response algebra and the engineering memory envelope. `docs/INTEGRATION.md` explains the interface to the reviewed Expanse campaign. Matching physics, cutoff conventions, and the isolated fourth-order logarithm are unchanged.
