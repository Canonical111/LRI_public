# Performance and numerical validation: 2D dressed-window HT

## Decision and scope

Optimization of the supplied `lri_2d_dressed_window_basis.zip`, with the same circle
modes, total-bath-level cutoff, local basis, Gaussian normal ordering, two primary
calibration equations, self-consistent full-vacuum window, and ordinary dense/ARPACK
eigensolvers. No fitting tails, selected interacting tails, new physical matching
kernel, thermal calibration, or lower floating-point precision are introduced.

**Measured result:** complete scalar window-and-retuning calculations are 1.74--2.41
times faster in the tested one-thread cases. Exact ranked basis construction and a
new sparse Gram backend reduce important large-space overheads. This is a locally
tested performance/HPC candidate, not a symmetry-validated production deployment,
a new continuum curve, or a distributed-memory eigensolver.

## 1. Bottleneck-first profile

A separately warmed cProfile run at L=10, x=.25, z=16 on the original tensor
backend takes 5.719 s including profiler overhead. Its cumulative measurements are:

| Component | Time | Fraction of profiled elapsed time |
|---|---:|---:|
| All sector eigensolves | 5.55 s | 97.1% |
| Hamiltonian `apply` | 4.33 s | 75.8% |
| Window-spectrum calls | 4.08 s | 71.4% |
| Local Hamiltonian evaluation (instrumented total) | 0.0045 s | 0.08% |

These are **overlapping cumulative times**, not additive slices. Eigensolves and
window calls contain Hamiltonian applications. Basis construction is small at L=10,
but its Python objects become a major memory cost when L is increased. Consequently
optimization focuses on the operator action, repeated window work, and scalable
basis representation, rather than the inexpensive local oscillator diagonalization.

The complete original and new profiles are `results/benchmarks/profile_*.json` and
`profile_*.profile.txt`. Profile timings are not used for the speed ratios below.

## 2. Repeated full scalar solves

Each row compares three serial, independent processes for each implementation,
alternating original/new order. Both use the same L, x, 16 density-selected local
functions, teacher input, initial coupling, tensor backend, one thread, eigentolerance
1e-12, independent eigenvector gate 1e-8, primary tuning tolerance 3e-11, and original
window fixed-point gate. Relevant kernels are warmed before the measured interval.

Timing includes basis/operator setup, all sub-cutoff and top vacuum fixed points,
primary retuning, and final five-root scalar validation. It excludes imports/JIT,
local teacher training and optional angular-descendant diagnostics. It is therefore
not the time for every possible step of a campaign from cold start.

| L | x | Original median s [range] | Optimized median s [range] | Speed ratio |
|---:|---:|---:|---:|---:|
| 10 | 0.126 | 14.298 [14.251, 14.431] | 8.205 [8.018, 8.660] | 1.74x |
| 10 | 0.25 | 6.419 [5.882, 6.528] | 3.381 [3.356, 3.583] | 1.90x |
| 12 | 0.25 | 32.306 [30.925, 34.250] | 13.385 [12.610, 14.351] | 2.41x |

The observed runtime reductions are about 43%, 47%, and 59%, respectively. No
physical approximation is exchanged for this gain. Floating-point accumulation
order and eigensolver histories can change, so equality is assessed by tolerance.

| L | x | Absolute thermal-gap difference | Largest difference among ten scalar levels (five per field parity) |
|---:|---:|---:|---:|
| 10 | 0.126 | 4.086e-14 | 4.487e-12 |
| 10 | 0.25 | 3.508e-14 | 4.379e-13 |
| 12 | 0.25 | 2.753e-14 | 3.313e-13 |

The largest window-table difference is 3.70e-11 **between separately retuned
solutions**, not a vacuum-equation residual. Coupling coordinates differ by up to
2.30e-11; every individual solution still passes the unchanged 1e-11 absolute
fixed-point gate. The largest optimized tuning and eigenvector residuals in this
comparison are 9.12e-13 and 1.15e-12.

Full-solve peak RSS does not decrease at these small sizes: medians rise from
about 197--204 MiB to 206--212 MiB because of numerical/cache/runtime storage.
The larger-space storage results below are a different comparison, not a claim
of a universal memory reduction.

## 3. Larger Hamiltonian applications and thread scaling

At L=16, x=.25, z=16, the full bath has 160,188 states and the scalar bath has
6,781 states. Each field-parity operator acts on 108,496 states. The table uses
five batches of fifteen actions per configuration; each configuration runs in a
separate process. These are operator-only medians, not full-solve timings.

| Implementation/backend | 1 thread, ms | 2 threads, ms | 4 threads, ms | Counted operator arrays, MiB | 1-thread process peak RSS, MiB |
|---|---:|---:|---:|---:|---:|
| original tensor | 30.440 | 24.735 | 14.326 | 44.86 | 291.50 |
| original ladder | 178.268 | 146.742 | 149.908 | 27.52 | 402.25 |
| optimized tensor | 9.698 | 4.918 | 3.593 | 50.99 | 260.30 |
| optimized gram | 22.008 | 11.906 | 8.192 | 25.72 | 233.92 |

The optimized tensor path is fastest in this measured L=16 comparison. The Gram
path trades some speed for about **49.6% less counted operator-array storage than
optimized tensor**, and avoids forming the projected quartic W4. It is about
8.10x faster than the old ladder at one thread and 18.30x at four; that latter
comparison is relevant to the original automatic large-L choice, **not to every
original CLI run**, which could explicitly use tensor.

Both new backends achieve about 2.7x operator speedup from one to four threads at
L=16. The original tensor-to-new-tensor speedups are about 3.14x at one thread and
3.99x at four. No 32/64-core or multi-node strong scaling was measured.

Operator-array counts include the basis representation and stored sparse factors;
Python objects and temporary vectors are not all represented by that metric.
Peak RSS is reported separately and includes process imports/warmup. Gram image
construction can still require transient memory, and the many-body state count
continues to grow rapidly. Full results for L=12,14,16 are in
`results/tables/operator_timings.csv`.

Auto selects tensor through L=12 and Gram above. This is a conservative memory
policy, not an empirically universal fastest choice. Use explicit `--backend tensor`
when its measured speed and memory fit; use Gram when projected-vertex fill becomes
expensive. Calibrate the crossover on the target machine.

## 4. Exact ranked bath construction

One independent construction per implementation and cutoff, after small-signature
warmup. These construction timings are **single measurements**, not three-run
medians or full diagonalizations.

| L | Full bath states | Original s | Ranked s | Original peak RSS, MiB | Ranked peak RSS, MiB |
|---:|---:|---:|---:|---:|---:|
| 12 | 15,582 | 0.050726 | 0.001741 | 187.60 | 184.95 |
| 16 | 160,188 | 0.700403 | 0.027791 | 234.06 | 196.20 |
| 18 | 477,988 | 2.189028 | 0.083248 | 346.38 | 224.67 |
| 20 | 1,371,843 | 6.371973 | 0.224064 | 649.73 | 308.29 |

At L=20 the construction is about 28.4x faster and process high-water RSS is
about 52.5% lower. Numeric array bytes alone rise slightly because rank/tree tables
are explicit; the much larger Python tuple list and dictionary disappear. The
original DFS state order and ladder edges remain exact, as independently tested.
**No full nonperturbative L=20 curve point is claimed.**

## 5. Correctness and larger-space checks

The final local suite has **54 passing cases**: 16 inherited independent numerical
cases plus 38 new ranking/backend/cache/resource/restart/manifest cases. The
original Gaussian normalization, reflection/angular averaging, dense vacuum
fixed point, moving/fixed local response and original raw replay tests remain.

Additional checks outside the pytest count:

- Ten large action comparisons cover L=12 (J=0,1,2) and L=16 (J=0,1), both field
  parities, with original tensor versus new Gram. Largest absolute vector-entry
  difference 4.263e-13; largest relative norm difference
  5.131e-16. One/four-thread differences were zero in these tests.
- Two fresh all-diagnostic window solves at L=8, x=.3 and .126 compare with the
  saved original spectra. Largest scalar and angular-spectrum differences are
  5.667e-13 and 1.225e-12.
- An audit checks all 62 new benchmark records: 18 full scalar solves, 36 operator
  configurations and eight basis constructions. Two warmed profiles are separate.

These establish agreement for the tested finite problems. They do not establish
a physical continuum error, complete conformal-family identification, an all-orders
matched Hamiltonian, or global branch uniqueness. Strong-coupling continuation
and alternate-root diagnostics must be preserved.

## 6. What was deliberately not traded for speed

No basis states, angular intermediates, particle sectors, or physical amplitudes
were dropped. Float64 is retained. The local density basis is the same source
input in each timing pair. No thermal or descendant value is fitted. No tolerance
is loosened; final five-root residual/orthogonality tests and the window gate remain.

The top vacuum fixed point requests only its required ground eigenpair, then
computes the requested excited roots and rechecks the fixed point. Exactly equal
local matrices allow vacuum-table/small-dense caching; any changed matrix invalidates
it. This is not a lagged or approximate window scheme.

## 7. HPC capability and limitations

The new driver provides same-request checksummed restart, atomic output publication,
fail-closed single-writer claim directories and Newton-boundary signal handling.
Frozen Slurm manifests run independent x/L/local-size/seed checks across nodes.
Input contents are rechecked in the consuming process. There is no scheduler
submission, cross-node lease test, or target-cluster performance claim in this work.

An individual ARPACK problem still fits on one node. Parallelism within a node
is row-owned sparse contractions. Across nodes it is independent calculations,
not MPI domain decomposition. Remaining bottlenecks include Fock-space growth,
ARPACK orthogonalization, memory bandwidth and sequential vacuum dependencies.

The driver gives exact basis dimension/array guards and an additional heuristic
RSS estimate; this cannot guarantee all transient allocation peaks. Slurm memory
limits and target-machine calibration are still required. A hard crash leaves a
claim requiring verified offline recovery. Checkpointing is not inside ARPACK
or an unfinished vacuum fixed point; configure sufficiently early stop signals.

## 8. Reproduction and provenance

Use `README.md`, `cluster/README.md` and `docs/OPTIMIZATION.md` for exact commands
and algebra. The original code/input archive is retained as a comparison oracle.
Every benchmark stores its settings, runtime and numerical module hashes. Later
changes forward explicit basis-memory/state guards to all sub-cutoffs and harden
HPC source/input binding; they do not change the timed numerical contractions,
window equations or thresholds at the measured defaults. The final validation
covers those changes. `validation/PROVENANCE.json` inventories the exact hash
differences instead of silently rewriting the original timing records.

The profile and benchmark processes ran on a Linux x86-64 VM with a four-CPU
quota, not a dedicated symmetry compute node. Environment/affinity/cgroup/BLAS
details are in `validation/ENVIRONMENT.json`. Training and JIT costs are excluded
from reported solve speed ratios and must be added to a campaign cost estimate.

The rectangular CSR bug encountered during development was fixed and independently
retested before accepting the released parallel benchmarks. Rejected seed and
interrupted runs are disclosed in `validation/DEVELOPMENT.md`; none are accepted
physical points or benchmark records.

## Final distribution check

A clean ZIP extraction passed all 54 tests and the 62-record benchmark audit.
Every shipping Python script in code, cluster, tests and benchmarks is identical
to that clean tested tree. The final archive includes this check as evidence;
no temporary pytest/JIT/Numba caches or platform-specific binaries are shipped.
This is still local validation, not a target-cluster release receipt.
