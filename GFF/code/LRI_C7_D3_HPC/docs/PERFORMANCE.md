# Measured performance

Fresh matched-sample measurements on the supplied d=3 code. Both compared workers use GMP350, identical strict compiler flags, graphs, seeds, Sobol matrices and intervals. Each row is the median of three runs. These are selected costly workloads, not a full production or multi-node benchmark.

| Sector | Loop | Version | Threads | Wall seconds | Integration seconds | Peak MiB |
|---|---:|---|---:|---:|---:|---:|
| free | 6 | reference | 1 | 3.4619 | 3.4391 | 8.02 |
| free | 6 | gmp | 1 | 3.3936 | 3.3694 | 7.89 |
| free | 7 | reference | 1 | 3.1427 | 3.0665 | 23.52 |
| free | 7 | gmp | 1 | 3.2690 | 3.1848 | 23.53 |
| free | 7 | gmp | 2 | 1.6563 | 1.5788 | 23.52 |
| free | 7 | gmp | 4 | 0.9715 | 0.8914 | 23.52 |
| power | 6 | reference | 1 | 9.1300 | 9.1105 | 7.27 |
| power | 6 | gmp | 1 | 9.0068 | 8.9867 | 7.41 |
| power | 7 | reference | 1 | 5.8096 | 5.7419 | 20.52 |
| power | 7 | gmp | 1 | 5.8130 | 5.7468 | 20.52 |
| power | 7 | gmp | 2 | 3.0685 | 3.0010 | 20.50 |
| power | 7 | gmp | 4 | 1.6672 | 1.5991 | 20.52 |

## What changed

The baseline already shares products, denominator prefixes, numerators and promoted scratch. Those are not new gains. The tested candidate reuses absolute quotients for sign-definite numerators. It showed no consistent single-thread gain, so the production header is restored byte-for-byte from the original GMP350 implementation. The candidate is retained only in experiments/quotient_reuse; variant `gmp` in the benchmark table denotes that candidate, not the final production default. No kernel speedup is claimed for the default. The exploratory exponential-factor cache is NOT included.

The fresh profile is benchmarks/profile/profile_summary.json; the inherited preceding profile remains separately labelled benchmarks/baseline_profile.json. Instrumented timing includes clock overhead.

## Memory and workload scope

The memory demonstration evaluates the same 590 power kernels monolithically and in blocks of 32 tasks. Peak native RSS is 486.72 MiB versus 31.19 MiB. This is not a comparison to the original driver's already-blocked default, and one point per stratum is not a scientific estimate. For a small existing graph block, memory gains may be absent.

The controller bounds graph storage by active tasks and uses disk-backed planning and merging. Evaluation work remains proportional to sample count and kernel complexity. Exponential growth in graph/rate-table complexity with loop order is not removed; the implementation supports loops 2--7 only.

## Limits

Local CPU quota and software versions are recorded in benchmarks/matched/benchmarks.json. No NUMA, GPU or actual multi-node benchmark is claimed. Benchmark on the destination cluster before choosing process/thread layout. A structural task-cost model can miss expensive precision promotions; tools/make_cost_model.py can freeze measured pilot costs for placement without altering sampling weights.

## Sources

- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
- https://slurm.schedmd.com/job_array.html
- https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html
- https://www.boost.org/doc/libs/latest/libs/multiprecision/doc/html/boost_multiprecision/tut/floats/gmp_float.html


## Final production default: local thread scaling

The default worker and header are byte-identical to the original scientific worker. These measurements characterize its OpenMP execution under the new workflow, not a newly invented kernel speedup.
| Sector | Threads | Integration seconds | Speedup vs one thread |
|---|---:|---:|---:|
| free | 1 | 3.1169 | 1.00 |
| free | 2 | 1.5782 | 1.97 |
| free | 4 | 0.8385 | 3.72 |
| power | 1 | 5.6418 | 1.00 |
| power | 2 | 2.8566 | 1.98 |
| power | 4 | 1.5439 | 3.65 |