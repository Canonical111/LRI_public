# Released default: bounded native benchmark

The released default has no resolved serial runtime improvement. Median integration times are about 5% lower at two and four threads and about 4% lower at eight threads, with overlapping timing ranges at four and eight threads. Median peak RSS is 14.6–16.3% lower across the measured thread counts. These are fixed-stratum measurements, not a complete production campaign forecast.

The table compares identical frozen point workloads. Every run passed the exact scientific-output check.

The primary workload has 10 free-L8 graphs, 16 replicates, 160 tasks and 20,480 points per execution. Grow-only storage is disabled in this measured candidate.

| Threads | Baseline seconds, median [range] | Candidate seconds, median [range] | Baseline/candidate | Candidate scaling from 1 thread |
|---:|---:|---:|---:|---:|
| 1 | 31.3963 [29.7765, 31.7945] | 31.5348 [28.0362, 31.5480] | 0.996× | 1.000× |
| 2 | 16.6904 [16.4945, 17.3771] | 15.8634 [15.1577, 16.1334] | 1.052× | 1.988× |
| 4 | 8.7870 [8.6338, 9.5060] | 8.3244 [8.3115, 8.7322] | 1.056× | 3.788× |
| 8 | 4.7793 [4.6179, 4.9206] | 4.6032 [4.4256, 4.7891] | 1.038× | 6.851× |

| Threads | Baseline/candidate peak RSS, MiB | Baseline/candidate child CPU, seconds | Baseline/candidate CPU per integration-wall second |
|---:|---:|---:|---:|
| 1 | 49.23 / 41.56 | 31.501 / 31.701 | 1.00 / 1.00 |
| 2 | 50.27 / 42.07 | 33.636 / 31.875 | 2.01 / 2.01 |
| 4 | 52.53 / 44.20 | 35.307 / 33.621 | 4.02 / 4.03 |
| 8 | 56.61 / 48.32 | 35.699 / 33.655 | 7.47 / 7.52 |

wait4 measures each native child's own CPU and peak RSS. CPU seconds include graph loading and output; CPU/integration-wall is therefore an approximate upper bound on CPU concurrency during integration. Affinity IDs are available logical CPUs, not a count of dedicated physical cores.

Near-full task wall occupancy with lower CPU concurrency and many involuntary switches at high thread counts is consistent with scheduling/preemption constraints; the benchmark does not identify a particular quota or hardware topology.

## Attribution and defaults

- **Scaled-alpha palette.** Enabled: exact scaled-alpha representation substantially reduces graph storage. The incremental timing attribution is noisy.
- **Reusable GMP scalars.** Enabled: removes measured repeated GMP scalar allocations while retaining only a few scalar objects per thread. The incremental timing gain is unresolved.
- **Grow-only vectors.** Opt-in: no demonstrated incremental benefit; its median was slightly slower with overlapping ranges. Retaining prior high-water vector objects is not justified as a default by this evidence.
- **Positive binary128 addition.** Enabled: dominant baseline hotspot, exact-bit helper tests, full native/direct regression coverage, and measured combined-default comparison. No claim of an independently resolved gain from the short attribution alone.

Every short incremental attribution had overlapping measured timing ranges. The observed combined table is the application measurement; the individual ratios must not be multiplied together.

## Limits

- Three counterbalanced repetitions provide measured ranges, not a formal confidence interval.
- Hard graph and promotion strata are useful for regressions and hotspot diagnosis; their runtime mix differs from a complete production campaign.
- An available affinity set is not evidence of exclusive physical cores; high-thread-count gains must be interpreted with child CPU and context-switch evidence.
- Peak RSS includes allocator/library/process overhead; cumulative GMP allocation traffic is not resident memory.

The raw comparison and per-run resource records remain in optimization_work/scaling_release/comparison.json. The authoritative structured summary is optimization_work/performance_summary.json.

## Historical configuration

The historical grow-enabled snapshot used an earlier native driver and a separate measurement window. Grow retention, telemetry/code layout, CPU scheduling and other window-dependent effects are confounded. Its 15.9% serial throughput gain is not a demonstrated gain for the released default and must not be attributed solely to grow retention.
