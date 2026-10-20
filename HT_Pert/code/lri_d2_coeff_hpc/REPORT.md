# Performance optimization of the 2D coefficient solver through C8

## Result

The direct perturbative coefficient engine has been optimized without changing
its total-bath-level regulator, primary tuning conditions, normal ordering,
coefficient order, or raw/consistent/literal vacuum prescriptions.

At cutoff **L=20**, fresh local, full-calculation benchmarks give:

- **6.01 times faster on one thread** than the original coefficient engine.
- **11.32 times faster using four threads** than the original one-thread engine.
- Median peak process memory **2.684 GiB -> 1.171 GiB**, a **56.4% reduction**.

The four-thread speedup over the optimized one-thread code itself is **1.88x**,
not 11.32x. All speed ratios below use the explicitly labelled comparator.

These are measured local results. They are not a benchmark on the user's HPC
cluster, a claim of MPI single-cutoff scalability, or a physical continuum-error
reduction. A new coefficient calculation at L=22 completed, but the Hamiltonian
matching and extrapolation questions are unchanged.

## 1. Source and unchanged problem

The source is the supplied `lri_2d_C8_perturbative_check.zip`, including its
unmodified independent exact-rational and finite-coupling oracles. Its extracted
contents are retained under `reference/lri_d2_perturbative_C8/`; the archive hash
is in `docs/PROVENANCE.json`.

We retain

\[
\epsilon=2s-2=2-4x,\qquad x=\Delta_\sigma=\tfrac12-\tfrac\epsilon4,
\]
\[
\Delta_\varepsilon=1-\frac\epsilon6+\sum_{n=2}^{8}C_n(L)\epsilon^n,
\qquad
H=N+\frac P2-\epsilon\frac P4+rM+gV+D.
\]

Here M is the angular average of :phi^2: and V the angular average of :phi^4:/12.
The physical scalar cutoff remains **N<=L**, with all required intermediate
angular sectors in each complete normal-ordered vertex. No individual-mode
physical regulator or new high-state counterterm is substituted.

Only the spin and shadow primary gaps x and 2-x determine r and g. No thermal
coefficient or tail fit is used in the solver. In the consistent scheme,

\[
D^{[\ell]}(N)=E_v(\ell)-E_v(\ell-N),
\]

and every sub-cutoff vacuum is calculated in its own corrected model at the SAME
outer coupling series. Its full expansion through eighth order is retained.
The raw and literal schemes remain separately identified. In particular, raw and
consistent agree through C3, and literal and consistent agree through C5, as in
the source. Those differences and their first nonzero orders are tested.

The optimized program is a **new coefficient branch**. It does not overwrite or
inherit a validation receipt from the uploaded nonperturbative HPC dispatcher.

## 2. Profiling first

A fresh cProfile run of the reference's existing envelope/reflection path at
L=16 found the following instrumented times:

| Phase | Seconds | Approximate fraction of profiled total |
|---|---:|---:|
| Basis/initialization | 4.868 | 29.8% |
| Lower-order wavefunction recursion | 5.095 | 31.2% |
| Energy moments for the stationary quotient | 6.218 | 38.1% |
| Upper coefficient recursion | 0.153 | 0.9% |

The total was 16.333 seconds **with profiling enabled**. This is not the
unprofiled speedup denominator in the next section. The profile counted **7,566
sparse matrix-vector calls**; complete Taylor-vertex applications accumulated
10.329 seconds, including their sparse operations. Repeated construction and
storage of degree-dependent sparse matrices were the second major issue.

The actual bottlenecks therefore motivated the graph and contraction changes
below. Coupling arithmetic or JSON serialization was not treated as the main
performance problem. The full profile is `results/reference_profile_L16.json`.

## 3. Measured full-run performance

Each row uses **three separate processes**, run sequentially on the same host.
Both the old and new algorithms warm imports/JIT/native compilation separately.
The timed calculation includes graph construction without disk-cache reuse,
wavefunctions, all required vacuum rows, energy moments, and coupling retuning.
Every run calculates the complete consistent-window degree-eight result.

| Cutoff | Implementation | Threads | Median seconds | Observed range, seconds | Median peak RSS, GiB |
|---:|---|---:|---:|---:|---:|
| 16 | Original coefficient engine | 1 | 11.606 | 11.227-12.248 | 0.526 |
| 16 | Optimized | 1 | 2.388 | 2.367-3.192 | 0.319 |
| 16 | Optimized | 4 | 1.591 | 1.556-3.208 | 0.319 |
| 20 | Original coefficient engine | 1 | 150.025 | 139.199-164.853 | 2.684 |
| 20 | Optimized | 1 | 24.960 | 23.907-27.807 | 1.171 |
| 20 | Optimized | 4 | 13.258 | 13.042-20.183 | 1.171 |

The cutoff-16 speedups are 4.86x on one thread and 7.30x on four threads versus
the original one-thread code. Timing variation is visible; the medians are not
confidence intervals or promises of performance on another processor.

The host provided a four-CPU cgroup quota, five logical CPUs in the affinity
mask, and a 4 GiB memory limit. Versions/compiler are in `results/ENVIRONMENT.json`.
The historical 66-second L20 run quoted in the source report was on a different
execution context and is **not** the benchmark denominator.

All 18 full benchmark records, including coefficients, warmup, timings and RSS,
are retained in `results/benchmarks/`. The summary is
`results/benchmark_summary.csv`.

## 4. Exact changes responsible for the improvement

### 4.1 Generate only the already-allowed auxiliary space

The reference already proves the auxiliary bound N+|J|<=L. With the two chiral
charges A=sum a*n_ab and B=sum b*n_ab,

\[
N+|J|=2\max(A,B).
\]

The new basis builder generates A,B<=L/2 directly, rather than first constructing
a much larger bath space and filtering it. A dynamic-programming suffix count
supplies exact ranks for occupation multisets, reflected states and annihilation
children. A large Python dictionary of state tuples is unnecessary.

The original spatial-reflection orbit normalization and degree-dependent
particle support are retained. Multiple edges reaching the same reflected child
are all kept and summed, never discarded. New tests compare the matrices and
state counts with the original builder, including exact reflection fixed points.

This is not a change of the physical UV cutoff: the scalar endpoints are exactly
the old N<=L states. The existing envelope is a source result; the new work is
its direct ranked implementation.

### 4.2 Share graph connectivity across Taylor orders

The old engine stores a separate sparse graph for every mode-weight Taylor
coefficient. The optimized engine stores a mode-labelled graph once, plus the
small mode-Taylor table. Both orientations are stored as row-owned gather
structures. Index widths are chosen with explicit bounds; large indices are not
silently truncated to save memory.

For fixed perturbative degree the graph and vector work remain linear in their
actual sizes, but the duplicated graph traffic and allocations are removed. The
fundamental growth of the exact Fock space with L is **not** eliminated.

### 4.3 Fuse threaded Taylor sparse products

The native C++17/OpenMP path fuses graph traversal with the truncated Taylor
convolution and the required Horner additions. Both annihilation and creation
are gathers: each output row belongs to one worker, with no atomics or concurrent
scatter accumulation. No intermediate scalar-angular projector is inserted.

An exactly zero leading input jet can be skipped. There is no small-amplitude
threshold, pruning, or approximate compression. The alternative Numba backend
independently implements the same contractions and passes the same small tests.

### 4.4 Avoid creation passes in the energy-moment stage

For the real scalar wavefunction jets, normal ordering gives

\[
\begin{aligned}
\langle M\rangle
 &=2\langle\psi,B^2\psi\rangle+2\langle B\psi,B\psi\rangle,\\
\langle V\rangle
 &=\frac{2\langle\psi,B^4\psi\rangle
 +8\langle B\psi,B^3\psi\rangle
 +6\langle B^2\psi,B^2\psi\rangle}{12}.
\end{aligned}
\]

Products are Taylor convolutions. These identities remove creation-operator
passes from the energy moments and permit streaming with at most three large
annihilation work arrays live. Explicit original vertices and random input jets
independently validate the identities.

The stationary Rayleigh quotient and its half-order wavefunctions were **already
present in the source**. This release improves their evaluation; it does not
claim that coefficient-reduction principle as a new discovery.

Reference-state zero-degree images are also cached. In raw and consistent
modes, the top vacuum is identical to the p=0 primary, so its duplicate
calculation is reused. Literal mode deliberately does not use that alias,
because the two vacuum Hamiltonians differ there.

## 5. Numerical precision and correctness

Main arrays remain float64. Products are formed in double as in the original
engine, and scalar polynomial sums use extended long double. The native compile
flags include `-fno-fast-math -ffp-contract=off`; no fast-math or explicit
precision reduction is used. Platforms without the required long-double
significand are rejected. This release does **not** implement arbitrary-precision
large-vector calculation; an independently exact Fraction oracle is retained
for small cutoffs.

Fixed-size reduction blocks are combined in the same order regardless of worker
count. The one-/four-thread native benchmark coefficient arrays, coupling
arrays, energies and full vacuum tables are **bitwise identical on the tested
platform**. The Numba thread-replay tests also pass. Cross-engine bitwise equality
is not claimed: algebraically regrouped sums have different rounding histories.

Across the full benchmark comparisons against the supplied coefficient records:

| Quantity | Maximum absolute difference | Maximum scaled difference |
|---|---:|---:|
| Thermal C0..C8 | 6.91e-11 | 9.75e-15 |
| Mass-coupling series r | 8.55e-11 | 5.13e-14 |
| Quartic-coupling series g | 2.50e-10 | 4.73e-14 |
| All four energy series | 8.64e-11 | 6.06e-14 |
| Entire sub-cutoff vacuum table | 8.62e-11 | 1.82e-13 |

Scaled difference means abs(new-reference)/max(1,abs(reference)), maximized over
all entries. These are implementation discrepancies, not physical uncertainty
bounds. The two primary acceptance conditions and finite-value gates are not
relaxed.

The fresh local test suite contains **43 passing tests**. Coverage includes:

* Raw, consistent, literal; coefficient degrees 2..8; exact-rational saved oracles;
  original ordinary full-order recursion; enlarged particle support; exact C2,
  second-order vacuum and fourth-order window formulas.
* Full vertex/moment matrices; symmetry/rank counts; all required intermediate
  angular sectors; native versus Numba; thread determinism; invalid-input and
  state/memory guards.
* Cache corruption, complete checkpoint stages, changed-thread restart, identical
  output reuse and conflicting-output refusal. Two local campaign processes run
  concurrently against a shared graph cache. An actual SIGUSR1 interrupts a
  calculation safely; a later command resumes it and releases its output claim.

The original source's full nonperturbative cluster-launcher suite is NOT rerun
or represented by these tests. A fresh ZIP extraction verified all delivery and reference manifest entries,
then passed all 43 tests again. Native/JIT warmup is recorded separately. See
`results/validation.json` and `results/fresh_extraction_validation.json`.

## 6. A completed larger-cutoff pilot

The optimized engine completed L=22, above the supplied degree-eight dataset's
maximum L20. This is a real new numerical calculation, not an uncomputed planner
entry or a forecast from the earlier fit.

The degree-eight auxiliary space contains **6,174,565 states and 35,585,486
ladder edges**. The consistent four-thread CLI run, without a graph-cache hit,
took **50.31 seconds** with **2.691 GiB peak RSS**. The raw run took 30.69 seconds
and used a cached graph, so its timing is not a fair same-work speed comparison
with the uncached consistent run. Only one run of each pilot was performed.

| Coefficient at L22 | Raw | Consistent window |
|---|---:|---:|
| C2 | 0.301379191751 | 0.301379191751 |
| C3 | -0.744557299242 | -0.744557299242 |
| C4 | 3.348877077722 | 3.353578728509 |
| C5 | -21.829601143496 | -21.826864490559 |
| C6 | 173.819161001652 | 173.866419807853 |
| C7 | -1606.588212767431 | -1607.156699359119 |
| C8 | 16689.697999218293 | 16695.057341185784 |

An independent degree-seven run has different particle support and uses three
rather than four wavefunction orders. Its first seven coefficients agree with
the degree-eight run to **2.41e-14 scaled**. C2 agrees with its exact sum within
3.33e-15, and the raw/consistent C4 difference agrees with the independent window
formula within 4.09e-15.

**C8 at L22 does not have a same-cutoff independent original-engine replay in this
release**, because of the latter's greater memory cost. The broader reference,
rational and order-support tests are reported separately, not substituted for
such a replay. These values remain finite-regulator coefficients, not improved
continuum estimates. No fit is made here.

`results/scale_pilot.csv` maps the accepted checksummed pilot envelopes.

## 7. HPC scaling and safeguards

The release supplies shared-memory threading within an item and Slurm arrays
across independent cutoffs, prescriptions and coefficient orders. It never
shares a mutable coupling or vacuum table between different items.

**There is no MPI/domain-decomposed single-cutoff solver.** The largest graph and
work arrays of one cutoff must still fit one node. Scaling throughput across
nodes is not the same as distributing one calculation's memory. Neither actual
Slurm jobs nor inter-node filesystem semantics were tested in this environment.
Run a small target-cluster validation before a large campaign.

The planner obtains exact states and edge counts before constructing the graph.
Its memory model estimates conservative live arrays with a safety margin:

| L, degree eight | Exact auxiliary states | Recommended memory estimate |
|---:|---:|---:|
| 20 | 2,397,430 | 1.53 GiB |
| 22 | 6,174,565 | 3.58 GiB |
| 24 | 15,488,787 | 8.71 GiB |
| 28 | 90,647,313 | 51.06 GiB |

Only through L22 was actually run. Higher estimates are planning outputs, not
measured peaks or a license to remove safety guards without resource checks.
Use separate arrays for different memory classes to avoid allocating the
largest envelope to every small item.

Operational additions are deliberately conservative:

* Content-addressed native compilation and graph caching; checksums verified
  before read-only graph reuse. Graph structure can be reused across schemes,
  but coefficient and vacuum data cannot.
* Atomic output-directory ownership; no unsafe automatic stale-lock stealing.
  A killed job can leave a claim requiring manual recovery after confirming
  termination. A conflicting writer returns 73.
* Complete, checksummed coefficient-boundary checkpoints and atomic publication.
  SIGUSR1/TERM/INT request safe stop at the next complete boundary and return 75.
  Resume validates source, numerical settings, backend and runtime identity.
  Changing only thread count is allowed.
* The coefficient campaign format is explicitly separate from the supplied
  nonperturbative dispatcher. The submission helper is dry-run by default.

These mechanisms improve reproducibility and job hygiene. They are not a
reviewed cross-node lease service, and signals, filesystem atomicity and recovery
must be drilled on the target cluster. On resume, execution seconds record the
current invocation, not prior interrupted work. The inherited
`stored_wavefunction_entries` statistic counts logical channel entries, including
a reused top-vacuum channel; RSS and the planner separately describe allocations.

## 8. Reproduction and release boundary

Start with `README.md`. It provides installation, state/memory planning, single
runs, checkpoint/restart, job-array generation, dry-run submission, benchmarks,
and output collection. `docs/METHOD.md` derives the graph/moment changes.

The benchmark supervisor launches every measurement in a separate process,
warms each implementation independently, and validates full output arrays. The
three L22 pilots are run separately. Source fingerprints bind accepted benchmark
records to the delivered numerical source.

The old coefficient package remains available as an independent reference and
for symmetry-ablation tests. Historical reports are not relabelled as new
measurements. Compiled objects, graph caches, abandoned checkpoints, interpreter
caches and failed temporary profiles are excluded from the release.

**Recommendation:** deploy this as an independently validated coefficient branch.
First replay overlapping L16/L20 items on the target cluster with the same
schemes and thread settings; then extend cutoffs using the planner. The numerical
optimization is ready for that trial, while physical high-state matching and
continuum uncertainties remain separate scientific tasks.
