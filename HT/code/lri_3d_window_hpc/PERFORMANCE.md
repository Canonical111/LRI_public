> Historical performance study (0.2.0rc1). The L18/L20 repair does not rerun
> these timings or claim these as newly measured speedups. Its new evidence is in
> REPORT_L18_L20.md and validation/l18_fix/. The benchmark validator checks the
> original records against their preserved source AND runs fresh current tests.

# 3D dressed-window HT: performance and correctness report

## Scope

This optimizes the **latest supplied 3D package**, not the older raw spherical
solver. It preserves the full-vacuum-window prescription, true SO(3) sectors,
normal ordering, local basis, float64 precision, physical state support, two primary
calibration conditions, and final numerical gates. No tail fitting or selected-tail
eigensolver is introduced. This is a local performance candidate, not a symmetry
cluster receipt or a new continuum curve.

## 1. Bottleneck-first profile

A warmed cProfile run of the supplied code at L=12, x=.6, local16 takes 27.618 s.
The following are **overlapping cumulative times**, not additive fractions. Python
profiling especially inflates Python-heavy setup, so these times identify bottlenecks
but are not used to claim speedup. Final repeated benchmarks below are unprofiled.

| Component | Profiled seconds | Fraction of profiled total |
|---|---:|---:|
| All sector eigensolves | 17.519 | 63.4% |
| Hamiltonian vector application | 12.759 | 46.2% |
| Window-spectrum calls | 12.333 | 44.7% |
| Bath/operator setup (`set_delta`) | 9.872 | 35.7% |
| Highest-weight SO(3) projection | 7.894 | 28.6% |
| Polar vertex construction | 1.932 | 7.0% |

The work therefore targets repeated angular setup/vertices and unnecessary roots
in the repeated eigensolves, not the inexpensive isolated local diagonalization.
Portable old/new profiles are in `results/benchmarks/*profile*.profile.txt`.

## 2. Repeated complete scalar calculations

Three serial independent processes per implementation and point; alternating
old/new order, one active thread, single-thread BLAS. The same original teacher
(16 retained functions per parity), prior-cutoff seed plus a declared small
perturbation, cutoff and tolerances are used in each pair. Timing includes numerical
setup, all lower/top vacuum fixed points, nonlinear retuning and five final roots
per scalar field parity. It excludes imports/JIT warmup, teacher training and angular
diagnostics. **Persistent static caching is disabled in this comparison.**

| L | x | Supplied median seconds [range] | Optimized median seconds [range] | Speedup |
|---:|---:|---:|---:|---:|
| 10 | 0.6 | 3.514 [3.511, 3.789] | 2.406 [2.392, 2.448] | 1.461x |
| 10 | 0.5182 | 5.424 [5.395, 6.093] | 3.864 [3.838, 3.950] | 1.404x |
| 12 | 0.6 | 21.281 [20.853, 22.130] | 13.761 [13.300, 13.785] | 1.547x |
| 12 | 0.5182 | 30.772 [30.238, 31.189] | 21.418 [21.049, 22.771] | 1.437x |

This is **1.40–1.55x faster**, about 29–35% less elapsed time in these cases.
It is not a universal speedup at every size or thread count.

| L | x | Supplied peak RSS median (MiB) | Optimized peak RSS median (MiB) |
|---:|---:|---:|---:|
| 10 | 0.6 | 223.34 | 219.90 |
| 10 | 0.5182 | 223.53 | 220.02 |
| 12 | 0.6 | 288.93 | 259.98 |
| 12 | 0.5182 | 290.64 | 260.60 |

The largest paired thermal-gap difference is **9.526e-14**;
the largest difference among ten final scalar gaps is **8.376e-13**.
The largest optimized tuning/eigenvector/vacuum residuals are 2.023e-11,
1.094e-12, and 5.879e-14, respectively.
These measure numerical agreement at fixed finite prescriptions, not physical error.
No root or final test is omitted to obtain the agreement: only the intermediate
Newton root request changes from three per parity to (one even,two odd).

## 3. Larger scalar setup and memory

Each entry is the median of three fresh warmed-JIT processes. It includes the
full ranked graph, true scalar projector and four bare vertices, not an eigensolve.
No disk cache is used. The underlying Fock states and scalar columns are unchanged.

| L | Full bath states | Scalar bath states | Supplied setup s | Optimized setup s | Ratio | Supplied / optimized peak RSS MiB |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 60,566 | 371 | 0.516 | 0.100 | 5.17x | 200.96 / 196.84 |
| 12 | 341,241 | 1,285 | 3.117 | 0.599 | 5.21x | 278.48 / 245.42 |
| 14 | 1,784,949 | 4,486 | 25.015 | 4.211 | 5.94x | 665.52 / 536.74 |

At L14, scalar vertex construction alone decreases from 12.156 s to 0.640 s
(about **19x**), and SO(3) projector construction from 12.637 s to 3.408 s.
The full graph construction itself was already ranked in the supplied code and
is not claimed as a new speedup. This release accelerates species grouping/J+
construction and removes polar quadrature via a rotational trace.
**No full nonlinear L14 curve point or L16 run is claimed.** The largest L14
operator here acts on 71,776 states per field parity.
Counted persistent operator-array storage remains almost unchanged for one top
operator; the setup RSS reduction comes principally from lower transient overhead.
Lower-cutoff window operators additionally avoid repeated auxiliary graphs/SVDs.

## 4. Matrix-vector application and thread scaling

Seven batches of 15 actions per fresh process. These are operator-only medians,
not repeated complete-solve speedups. The old and new paths both use tensor,
not a deliberately slow Gram baseline. Single-thread application improves only
modestly; two/four-thread scaling is not uniformly monotonic.

| L, J=0 | Threads | Supplied ms | Optimized ms | Supplied/new |
|---:|---:|---:|---:|---:|
| 12 | 1 | 2.776 | 2.615 | 1.06x |
| 12 | 2 | 1.672 | 1.670 | 1.00x |
| 12 | 4 | 1.233 | 0.912 | 1.35x |
| 14 | 1 | 18.101 | 16.549 | 1.09x |
| 14 | 2 | 6.697 | 7.643 | 0.88x |
| 14 | 4 | 7.845 | 7.199 | 1.09x |

For example the optimized L14 two-thread action is slower than the supplied
one at two threads. This adverse result is retained. The new L12 and L14 one-to-
four-thread speedups are approximately 2.87x and 2.30x; they do not demonstrate
efficiency on 32/64/128 cores. Memory bandwidth and ARPACK orthogonalization remain.
All 30 operator configurations, including J=1, are in the timing CSV.

## 5. Optional static cache

At L12 the first cache creation/setup takes 0.586 s; two fresh-process verified
warm reads take 0.052 and 0.049 s. At L14 the first creation takes 4.766 s; two
warm reads take 0.237 and 0.241 s. These include content-hash verification and
read-only mmap loading; first creation is not free.
Warm-cache L12 full solves at x=.6 have median 13.552 s (range 13.018–15.340 s).
This separate test is not interleaved with the uncached pairs, so it should not
be used to claim a small marginal solve-time advantage more precise than the spread.
The main benefit is avoiding repeated construction across campaign items.
No window/coupling/energy approximation is loaded from this cache. Gauge-bound
atomic publication, duplicate builders, corrupt entries, readonly arrays, exact-x
identity, restart and the local frozen-manifest workflow have explicit tests.
Shared-filesystem and multi-node cache performance remain unmeasured.

## 6. Correctness, profiling scope and limitations

The quick suite passes **62 cases**: 27 inherited tests and 35 new tests. The new
cases compare full angular quadrature with the rotational trace, homogeneous
subcutoff restrictions, both field parities, direct/refined magnetic sectors,
vacuum/Jacobian equations, minimal calibration roots, cache corruption/gauge/races,
and a real cached CLI -> frozen manifest -> output -> restart/reuse workflow.
The exact C2 shell check has maximum discrepancy 5.274e-16. Independent Gaussian
normal-ordering and rotation checks also pass. Additional larger-action, weak-
coupling and fully retuned angular comparisons are recorded separately in validation/.
The larger independent checks completed successfully:

| Check | Maximum observed discrepancy |
|---|---:|
| Ten latest-reference tensor action comparisons, including L14 and J=1,2,3 | 1.762e-12 absolute |
| Same actions, relative norm | 1.913e-15 |
| One/four-thread action differences | 0.000e+00 |
| Fresh retuned L8 scalar spectra, x=.6 and .5182 | 5.467e-13 |
| Corresponding full six-root J=0,1,2 spectra | 6.573e-13 |

An additional original/Gram/tensor comparison through L12 has relative norm
error 5.877e-16; six fresh weak-end raw/window solves preserve the expected
fourth-order onset of the window effect. They are not coefficient fits or physical
continuum determinations. These independent validations are not included in the
83 benchmark-record count.

83 benchmark records are audited: 24 full solves, 30 operator configurations,
18 setup runs, nine cache experiments and two profiles. Each contains source
module hashes, seed/input identity, runtime, thread configuration and measured RSS.
Intermediate development-stage timings are labelled separately and never merged
into final speed ratios. Two foreground validation invocations were interrupted
by tool execution allowances; neither is a passing test. Complete reruns are
recorded separately. No interrupted numerical output is promoted.

## 7. HPC readiness and remaining bottlenecks

Independent Slurm arrays can distribute points/local-size checks across nodes.
A **single** eigensolve remains on one node. There is no MPI decomposition, GPU
backend, or target-cluster scaling evidence. The existing one-writer claims,
Newton-boundary checkpoints, input/source binding and fail-closed crash recovery
are retained; cache preparation is a separate optional stage.
The tests/benchmarks ran on a Linux x86-64 VM with a four-CPU quota and 4 GiB
cgroup memory limit, not a symmetry compute node. Whole-process RSS includes
imports/JIT warmup, although the elapsed timing interval excludes them.
Train/diagnostic costs and memory must be added to real campaign budgets.
Combinatorial Fock growth, dense per-species nullspaces, sparse quartic fill,
Krylov-vector storage, bandwidth and sequential vacuum dependencies remain.
Code guards reject excessive state counts; the RSS estimate cannot guarantee
all transient peaks. Calibrate on the target architecture before increasing caps.

Official operational references (not sources of the new benchmark numbers):
- https://numba.readthedocs.io/en/stable/user/threading-layer.html
- https://slurm.schedmd.com/job_array.html

## Reproduction

Use README.md and cluster/README.md. Mathematical identities and invariants are
in docs/OPTIMIZATION.md. The original latest code is preserved in reference/baseline;
its data are reference inputs, not a new physical campaign. Distribution and
provenance validation must precede running scripts that rewrite measured records.

## Final distribution validation

A fresh ZIP extraction passed all 62 pytest cases, the independent physical
normalization/rotation/C2 driver, and the 83-record benchmark audit. Every code,
test, benchmark, preparation and cluster executable in the final source is
byte-identical to that tested extraction. The final archive is independently
checked for ZIP integrity and all manifest hashes. No JIT/compiler cache, binary
profile, static numerical disk cache or temporary output directory is shipped.
These are local validations, not a symmetry or shared-filesystem receipt.
