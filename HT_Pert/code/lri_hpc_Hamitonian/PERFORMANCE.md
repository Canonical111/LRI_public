# Performance and correctness report

## Measured thermal C0–C7 at Lambda=40

Unprofiled, three independent fresh processes per configuration. The timed workload follows a cutoff-4 warmup; imports/warmup are measured separately. Peak RSS includes those phases. No basis-cache reuse was used in these timing comparisons.

| Implementation | Threads | Median seconds | Min–max seconds | Median peak RSS (MiB) | Speedup vs original |
|---|---:|---:|---:|---:|---:|
| original | 1 | 6.891 | 6.884–7.431 | 635.5 | 1.00x |
| optimized | 1 | 3.392 | 3.376–3.398 | 434.0 | 2.03x |
| optimized | 2 | 2.249 | 2.239–2.282 | 434.0 | 3.06x |
| optimized | 4 | 1.638 | 1.530–1.781 | 434.1 | 4.21x |

The environment had a four-CPU cgroup quota (five CPUs in affinity), Linux, Python 3.13.5, NumPy 2.3.5, Numba 0.65.1 and SciPy 1.17.0. This is not a dedicated HPC-node or network benchmark. See `benchmarks/environment.json`.

## Larger runs (single observations)

| Task | Cutoff | Implementation | Threads | Seconds | Peak RSS (MiB) |
|---|---:|---|---:|---:|---:|
| thermal | 50 | optimized | 4 | 7.570 | 1310.0 |
| phi6 | 50 | original | 1 | 13.853 | 1081.8 |
| phi6 | 50 | optimized | 1 | 6.284 | 671.0 |
| phi6 | 50 | optimized | 4 | 3.197 | 670.8 |

The original thermal cutoff-50 process was killed while the shared 4 GiB cgroup recorded an OOM kill. Background services consumed part of that limit. No isolated-process peak RSS or speedup is inferred for the failed run. The optimized cutoff-50 result was compared with the supplied saved coefficients instead.

## Cold-start cost

An empty-cache process required 6.627 seconds for cutoff-4 warmup/JIT, 0.168 seconds of imports, and 1.662 seconds for the cutoff-40 calculation. Thus an isolated cold job at this modest size can be slower than the original; persistent caches or multiple cutoffs per allocation are important. The warm speedup figures do not include this one-time cold compilation.

## Bottlenecks and changes

At cutoff 40, cProfile recorded 11.746 seconds for the original, including 6.613 seconds in Fock-space construction and 4.338 seconds in `linear_series`. That is approximately 56% and 37%, respectively. These profiled timings identify bottlenecks; they are not the baseline in the speedup table.

The main changes are exact compiled state ranking (no Python big-integer state dictionary), compact structural edge buffers, fused float64 polynomial ladder kernels, ordered Horner vertices (9 sweeps rather than 17), particle-parity pruning of identically zero rows, streamed quotient intermediates and staged reference-state lifetimes.

The original unique sparse buffers at cutoff 40 total 223,083,308 bytes; the new edge buffers total 58,381,532 bytes, a factor of 3.82 smaller. Total RSS improves less because vectors, metadata, imports and the JIT runtime remain.

## Correctness measurements

All locally implemented regression scripts pass. The solver was compared with the original thermal degrees 6/7 and phi6 degrees 3/5 at cutoffs 4,8,12,24,32, both phi6 prescriptions, full recursions at 4/8, and larger/saved results at 40/50. The test threshold is atol=1e-7, rtol=2e-11; observed residuals are not rigorous error bounds.

The largest observed thermal coefficient difference among the final cutoff-40/50 benchmark comparisons with the supplied saved table was about 1.52e-9. At cutoff 50 the C7 difference was about 2.91e-10. The phi6 cutoff-50 comparison with the freshly rerun original differs by at most about 2.04e-10 in D6; r/g and thermal coefficients differ by less than 6e-12.

At cutoff 40, optimized C/r/g arrays were bitwise identical at 1,2,4 threads. This does not assert bitwise equality to the original or across MPI rank layouts/hardware. Float64 and all Taylor orders are retained, and fastmath is disabled; algebraic/reduction regrouping changes last bits.

## MPI status

The implementation stores distributed rows and exchanges only static neighbor halos via buffer Alltoallv. No full wavefunction allgather is used. Two-/three-rank simulated collectives passed numerical and ownership tests (maximum differences around 7.3e-11 thermal and 5.3e-10 phi6). Those simulations do not test real MPI, networking, MPI ABI compatibility or multi-process failures.

No real MPI runtime was available; an installation attempt could not reach the package index. The MPI path is explicitly experimental. Run `tests/mpi_smoke.py` with 1/2/4 actual ranks, then benchmark fixed-cutoff scaling on the target cluster before production. Blocking halos, rank load balance and memory bandwidth remain subjects for real-cluster profiling.

## Scope

No extrapolation model, coefficient target or Hamiltonian matching prescription was changed. The state count and physical truncation are unchanged. Larger finite-cutoff calculations improve the available data; they do not by themselves resolve the previously identified matching error.

All raw measurements and comparisons are included in `benchmarks/`; `PERFORMANCE_SUMMARY.json` is the machine-readable summary.
