# Performance and correctness report

## What was benchmarked

Source: unchanged `product_reference` dressed-phi4 code from the supplied extended
comparison archive. Both implementations retain the same Hamiltonian, normal
ordering, bath cutoff, local caps, float64 arithmetic and root/eigen tolerances.
Every benchmark uses delta=0.1 and starts from the same saved coupling pair plus
(0.03,0.001), requiring four full spectral evaluations in the reference grids.
It is a setup-plus-real-tuning benchmark, not just a matrix-vector microbenchmark,
and not a whole weak-to-strong continuation campaign.

Each row summarizes three independent processes. The timed interval excludes
Numba compilation/warmup but includes basis and delta-operator setup. Peak RSS is
the largest process peak across those repetitions and includes warmup/imports.
The harness imports common runtime/thread controls in both implementations.
The execution environment exposes five CPUs but has a four-CPU cgroup quota and
a 4 GiB memory limit. BLAS is one-threaded. These are NOT Expanse measurements.

## Measured table

| Bath cutoff | Local/auxiliary | Backend | Threads | Median s | Min–max s | Max peak MiB | Speedup vs original |
|---:|---:|---|---:|---:|---:|---:|---:|
| 12 | 20/160 | reference | 1 | 6.106 | 5.960–6.133 | 295.7 | 1.00x |
| 12 | 20/160 | tensor | 1 | 1.169 | 1.144–1.174 | 185.5 | 5.22x |
| 12 | 20/160 | tensor | 2 | 0.823 | 0.811–0.840 | 185.5 | 7.42x |
| 12 | 20/160 | tensor | 4 | 0.620 | 0.603–0.664 | 185.5 | 9.84x |
| 12 | 20/160 | ladder | 1 | 1.074 | 1.054–1.116 | 185.4 | 5.69x |
| 12 | 20/160 | ladder | 4 | 1.074 | 1.073–1.109 | 185.3 | 5.69x |
| 16 | 24/192 | reference | 1 | 68.055 | 66.620–68.276 | 1115.9 | 1.00x |
| 16 | 24/192 | tensor | 1 | 9.442 | 9.277–9.584 | 190.6 | 7.21x |
| 16 | 24/192 | tensor | 2 | 6.015 | 5.978–6.113 | 190.5 | 11.31x |
| 16 | 24/192 | tensor | 4 | 4.265 | 4.218–4.799 | 190.6 | 15.96x |
| 16 | 24/192 | ladder | 1 | 5.912 | 5.744–5.964 | 194.7 | 11.51x |
| 16 | 24/192 | ladder | 4 | 5.920 | 5.782–5.984 | 194.7 | 11.50x |

At bath 16, the fastest measured latency uses the four-thread tensor backend,
about 16x faster than the original and about 83% lower peak RSS. The one-thread
ladder backend is about 11.5x faster than the original. At this point, one-thread
ladder minimizes measured core-time, whereas four-thread tensor minimizes
latency. Across a large grid, independent single-thread items may therefore
provide better throughput if memory permits. No node-scale throughput is claimed
without measuring the target node.

The standalone ladder kernels remain serial below the work threshold. Thus more
requested threads do not necessarily help the moderate-cutoff ladder case. This
is intentional avoidance of thread-launch overhead, not a discarded calculation.

## Bottlenecks

`reference_profile.txt` records a 6.032 s profiled bath-12 tuning solve. About
5.076 s (84.1%) was in global sparse Hamiltonian-vector multiplication; matrix
assembly/slicing was a further roughly 9–10%. Basis and zero-mode preparation were
small in that case. This motivated Kronecker-free operator actions first, not
micro-optimization of unrelated analysis scripts.

For a final four-thread tensor bath-16 repetition, operator actions account for
about 2.89 s of the 4.27 s elapsed. Lanczos iteration/orthogonalization and its
serial overhead are now a substantial remaining fraction. More operator threads
alone cannot eliminate that fraction. A tested preconditioned block-eigensolver
trial was slower and is not enabled in the release.

## Larger low-memory backend runs

These are single runs, not repeated speedup estimates. No original-code timing
is claimed where the original was not run at the same setting.

| Bath cutoff | Local/auxiliary | Threads | Setup+tuning s | Peak MiB | Thermal gap (finite regulator only) |
|---:|---:|---:|---:|---:|---:|
| 20 | 24/192 | 4 | 28.215 | 215.3 | 0.525961549821 |
| 24 | 24/192 | 4 | 93.254 | 299.8 | 0.526379154031 |

The bath-24 run includes every allowed bath partition and both field-parity
sectors. It materializes neither the global Hamiltonian nor quartic bath matrices.
Its gap is not a continuum prediction, and these timings must not be extrapolated
as a tested large-node or MPI scaling law.

## Numerical comparisons

The largest gap difference across the repeated benchmark comparisons was **5.81e-11**. The largest absolute coupling difference was **5.38e-09**; coupling sensitivity differs from gap sensitivity.

At seven supplied accepted coupling points, spanning delta=0.0001 to 0.24, recomputation of both five-level spectra differed by at most **2.92e-13**. These are finite-matrix regression tests, not physical error bars.

The automated suite tests exact state ranks and edge counts, reflection/field
parities, both operator backends, reduced expectation contractions, the moving
local-basis Jacobian against both reference and full spectral differences, tuned
spectra at three couplings, actual int64 CSR kernels, serial/thread equality,
invalid inputs, record corruption, duplicate claims, source/config mismatch,
checkpoint recovery and safe-boundary interruption. Current local result: **26
passing tests**. A separate manifest/receipt/lane smoke test completed and reused
an accepted result.

Tests use explicit absolute/relative tolerances (not rounding or plotted
agreement). Representative spectrum assertions are atol=2e-9, rtol=2e-9 against
independent finite-matrix/reference results; observed differences are much
smaller. The production residual and tuning gates are unchanged from the source,
with an additional orthogonality gate. All physical values remain float64.

## Reproducing the table

Move `benchmarks/runs/` aside before rerunning:

    python scripts/run_benchmark_grid.py
    python scripts/summarize_benchmarks.py

Run jobs sequentially on an otherwise idle allocation. `bench_once.py` supports
custom fixed caps and thread counts. `jit_warmup_seconds` is recorded separately
in every JSON. A first cold run must pay compilation cost; do not compare only
the warm numerical timer with a cold reference wall time.

Peak-memory numbers include the runtime and cannot be interpreted as the number
of stored matrix bytes alone. The planner's envelopes are deliberately
conservative, uncalibrated estimates, separate from these measurements.
