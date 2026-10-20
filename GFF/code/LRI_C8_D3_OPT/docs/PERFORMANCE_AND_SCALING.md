# C8 in 3D: measured CPU/HPC optimization

## Deliverable and scope

This is a source patch for the available **base `LRI_C8_D3_HPC.zip`**, not a new
coefficient determination. It preserves the input graphs, sampling nets,
importance rates, sample indices, regulator coefficients, fixed-point algebra,
precision promotion thresholds, and uncertainty analysis.

The subsequently mentioned refinement archive was not available in the current
files. Its source and specialized refinement workflow have **not** been validated
against these changes. The installer checks the three modified base files and
refuses to overwrite differing code. Porting onto another revision requires a
source merge and the same regression tests; bypassing that check is not advised.

The patch does not duplicate the 9.35 GB base dataset or contain prebuilt binaries.
Use it with the original base archive. `make optimized` writes a new executable,
`bin/c8d3_optimized`, leaving binaries referenced by older immutable campaigns
alone. **Do not run the default `make` target over an executable frozen into an
existing campaign.** Old targets remain for compatibility, but the separate
optimized target is the recommended deployment path.

## 1. What the measurements found

The archived pilot attributed approximately **80.5%** of its recorded integration
task time to eight-loop graphs. These records are task elapsed times, not hardware
performance-counter measurements. Instrumenting a rebuilt copy of the original
worker showed that high-precision fallback arithmetic, rather than Python or
random-point generation, dominated the selected eight-loop integration workloads.

Across the two profiled eight-loop fixtures, positive denominator-polynomial
summation accounted for approximately **83.6% of binary128-tier time** and
**52.6% of total sample-evaluation time**. The multiprecision tier was particularly
important in the power-containing sector. Accordingly, the principal kernel work
focused on exact binary128 summation and eliminating multiprecision allocation
and copying, not on changing the integral or its numerical precision.

Other measured costs were repeated graph parsing/preparation across short native
jobs, retaining all graphs in large invocations, and retaining Decimal
accumulators plus interval histories during final assembly.

The instrumented executable is retained for attribution only. **All speedups
below were measured using uninstrumented binaries.**

## 2. Achieved performance

The host reports an AMD EPYC 9V74 processor. The container was restricted to four
CPU-equivalents by its cgroup quota, despite a larger host CPU description. Builds
used GCC 14.2.0, Boost 1.83, GNU libquadmath and the existing GMP350 backend, on
x86-64 Linux. The existing 64-significand-bit `long double` tier was preserved.

### Integration throughput

The following are median native integration times from three runs, with execution
order alternated between variants. Loading and process startup are measured
separately in the JSON. These are fixed representative workloads, **not full
campaign timings**. Eight-loop fixtures contain six actual graphs per sector,
four replicates and 128 points per graph/replicate.

| Workload | Original, 1 thread (s) | Optimized, 1 thread (s) | Optimized, 4 threads (s) | Single-thread speedup | 1-to-4-thread speedup |
|---|---:|---:|---:|---:|---:|
| L6 free | 0.165653 | 0.159919 | 0.043757 | 1.036x | 3.655x |
| L6 power | 0.709293 | 0.667303 | 0.176569 | 1.063x | 3.779x |
| L7 free | 0.896754 | 0.795126 | 0.218297 | 1.128x | 3.642x |
| L7 power | 1.981727 | 1.933075 | 0.477767 | 1.025x | 4.046x |
| L8 free | 2.675423 | 2.266121 | 0.616520 | 1.181x | 3.676x |
| L8 power | 3.945431 | 3.624097 | 1.027676 | 1.089x | 3.526x |

For the eight-loop free sector, **1.181x throughput** corresponds to a **15.3%
reduction in integration time**, not an 18.1% reduction in time. For the eight-loop
power sector, the measured gain was 1.089x. Small three-loop fixtures were slightly
slower on one thread because fixed overhead matters there. This is not a claim
that every graph becomes faster.

The four-thread figures demonstrate local thread scaling only. No actual
multi-node or large-NUMA-node scaling experiment was possible here. Whole-campaign
speedup will depend on graph mix, promotion frequencies, job sizes, filesystem
behavior, and the deployment compiler/CPU.

### Native memory

A separate test processed the same **64 real eight-loop free-sector graphs**, the
same sample points and one worker thread in every variant.

| Variant | Peak RSS (MiB) | Simultaneously resident graphs |
|---|---:|---:|
| baseline-all-graphs | 225.61 | 64 |
| optimized-batch-1 | 22.82 | 1 |
| optimized-batch-4 | 33.48 | 4 |
| optimized-batch-8 | 46.49 | 8 |

Default batching reduced peak RSS by **4.85x** in that larger invocation. This is
**not** a 4.85x improvement over the original campaign's default eight-graph
blocks: those were already small. The new bound prevents memory from scaling
with every graph in a deliberately enlarged invocation.

Peak RSS includes graph data, parser temporaries, per-thread scratch and the
runtime. `peak_graph_vector_bytes` is an additional diagnostic of graph vector
storage only and must not be interpreted as total process memory.

### Complete archived-pilot assembly

The original and streaming assemblers both read all **1,526 archived native jobs**,
covering **24,173 active graphs**, two campaigns and eight replicates per campaign.

| Assembler | Peak RSS | Wall time |
|---|---:|---:|
| Original | 553.22 MiB | 16.04 s |
| Streaming | 221.84 MiB | 13.17 s |

This was **2.49x lower peak memory** and **1.22x faster** in one full-data comparison.
All common non-provenance result fields and all per-graph statistics were exactly
equal, including the coefficient vector, covariance matrices, campaign comparison
and sampling standard errors. This test used zero bootstrap resamples; the
original bootstrap implementation is reused unchanged but a nonzero full-pilot
bootstrap was not part of this particular comparison. These are regression
results for the archived pilot, not a replacement for the later reported refined
physical estimate.

### Native invocation packing

A checkpoint/dispatch fixture packed **64 original jobs into eight native
invocations**, while preserving all original scientific rows and checkpoint
identities. Three lanes were executed sequentially for the correctness test,
not as a cluster scaling measurement. A complete resume ran zero native
invocations. Its startup-dominated L3 timing improved from 0.305 s to 0.092 s;
that figure is not a production speedup forecast.

## 3. Implementation changes

### Exact positive binary128 polynomial addition

`src/positive_quad.hpp` specializes addition only when summing positive denominator
polynomials in the binary128 tier. It retains all 113 significant bits, aligns
integer significands with guard/round/sticky bits, and rounds to nearest,
ties-to-even. Addition order is unchanged. Nonpositive values, subnormals,
exceptional operands and possible overflow fall back to the compiler addition.
Signed forest sums, multiplication, square roots, division, exponentials,
logarithms and multiprecision precision are untouched. See `docs/QUAD_ADDER.md`
for the rounding argument and limitations.

The worker checks `FE_TONEAREST`. This specialization was tested on the stated
GNU/x86-64 environment; run the arithmetic and graph suites on every new
architecture/compiler. `CPPFLAGS=-DC8_REFERENCE_QUAD_ADD` switches back to the
compiler binary128 adder without removing the other optimizations. Build that as
a separate executable for comparison rather than replacing a frozen binary.

### Multiprecision allocation reuse and ordered bit traversal

The kernel reuses positive-sum storage instead of making an additional MP object
copy for each segment, keeps numerator and denominator scratch values alive, and
passes square-root inputs by const reference. Promoted scratch vectors grow as
needed but do not shrink between graphs. Memory therefore follows the largest
scratch requirement encountered by each thread rather than repeated allocation
churn. Set-bit traversal avoids tests of absent bits while retaining ascending
bit order, so the existing floating additions and sampler choice are preserved.

### Bounded native graph batches

The native worker loads at most `C8_GRAPH_BATCH` graph objects at once (default 8).
The input task list may be larger. Tasks in a loaded batch are scheduled by
estimated cost using the existing independent-task OpenMP model. Shared graph
data are read-only during integration; each thread has its own scratch.
`C8_LOAD_THREADS` optionally parallelizes graph loading, default 1 and no greater
than the compute thread count. Sample indices, per-task Kahan order and emitted
scientific row order do not depend on scheduling.

### Packed, restartable Slurm lanes

`tools/hpc_dispatch.py` constructs a separate immutable index over an existing
frozen campaign. It bundles only jobs with the same sampling group and graph
set, retains their original tasks and net chunks, and distributes bundles using
longest-processing-time scheduling. Pilot per-graph task costs can inform the
allocation. Without costs, the weight is the number of integrand evaluations.

One Slurm task executes one lane. A lane stages verified input files in private
scratch and reuses a bounded file cache. The cache is **per lane**, not a
cross-rank shared cache. Its graph-count limit is a soft inter-bundle limit:
active bundle files are never evicted. Working memory and scratch must still
accommodate the active bundle. Files are hash-checked on staging, inputs are
assumed immutable during use, and provenance checks reject mismatches.

The native invocation can serve several original chunks using one graph load.
Tasks are not coalesced arithmetically. Original per-job `.native.json` and
`.done.json` outputs are published for the existing assembler, and completed
checkpoints are skipped on resume. Locks are never silently stolen: after a
hard kill, verify that the owner is no longer running before removing a stale
lock. If a process fails during a bundle, unfinished jobs remain rerunnable;
a larger bundle increases the maximum work lost before checkpoint publication.

The launcher binds processes/threads to cores, limits unrelated BLAS threading
and uses one native process per lane without an MPI library. The lane schedule
is static. Pilot-informed balancing reduces expected imbalance but cannot
eliminate stragglers or supply dynamic work stealing across nodes.

### Streaming final assembly

`tools/assemble_streaming.py` reuses the unchanged scientific functions from
`tools/assemble.py`. It verifies monotone chunk coverage as it reads and retires
Decimal buffers once graph sums can be committed in the **original graph order**.
The 50-digit Decimal addition order is preserved. It does not retain one interval
object for every completed chunk.

The standard campaign planner produces the supported order. Valid but nonstandard
out-of-order chunk plans are explicitly rejected; use the original assembler for
those plans. Missing, overlapping or duplicated scientific work is not tolerated.
Float64 graph/replicate arrays remain available for the original covariance and
per-graph statistics analysis.

## 4. Scaling limits that remain

Let N be evaluations, G the graph count, B the resident-graph bound, T native
threads, R replicates, K coefficient-vector length and J planned jobs.

* Integration remains O(N) times the graph's kernel cost. This patch reduces
  constants; it does not change the statistical algorithm or asymptotic QMC
  convergence. Fixed-net outputs are not a basis for promising an error versus
  core-hours law.
* Native graph storage follows B graphs, not all G graphs in an invocation.
  Thread scratch remains O(T) times the largest required scratch size. Parsed
  tasks/output records still consume O(tasks in the invocation); the dispatcher
  caps task counts per bundle. Small B can limit useful thread occupancy.
* The subset-rate dynamic program still has a 2^(2L) state space. Forest and graph
  enumeration still grow rapidly with loop order. No polynomial-complexity
  solution to that combinatorial growth is claimed.
* Streaming assembly removes per-chunk interval histories and long-lived Decimal
  graph buffers. It still retains graph/replicate numerical arrays, approximately
  O(G R K), and provenance/job metadata O(J). Extremely large plans may therefore
  need a later disk-backed manifest/statistics format, not just more threads.
* The dispatcher reduces repeated native startup and input staging, but preserves
  original per-job checkpoint files. Shared filesystem metadata load therefore
  still grows with J. Avoid unnecessarily tiny chunks. Each lane reads the
  campaign metadata; there is no distributed manifest service in this patch.

On many-core nodes, start with several moderate-size processes rather than one
process spanning all NUMA domains. Keep enough independent tasks inside each
resident batch to occupy its threads. Treat `C8_GRAPH_BATCH`, threads per lane,
chunk size and bundle size as memory/throughput/restart tradeoffs to benchmark on
the actual node. No unmeasured universal optimum is hard-coded.

## 5. Correctness evidence

The delivered compact records are in `verification/performance/`.

| Check | Result |
|---|---|
| Positive binary128 arithmetic | 12,051,840 cases: 12,051,344 non-NaN bitwise matches and 496 matching-NaN outcomes |
| Baseline/optimized real-graph regression | 179 actual graphs; 40,448 fixed sample points per implementation; exact emitted scientific vectors, maximum contributions and both promotion counters |
| Promotion coverage | 10,407 binary128 promotions and 1,658 MP promotions in the real-graph regression |
| Schedule and memory variants | Identical results for 1 thread/batch 1 and 4 threads/batch 3 with 2 loaders |
| Independent high-precision point reference | 48 points on 12 actual forests against a 450-digit reference; accepted long-double results within the existing tolerance |
| C7 compatibility | 2,432 overlapping-jet samples, including both promotions; exact shared coefficients and counters |
| RG algebra | Seven original tests passed |
| Full archived-pilot assembly | All common scientific fields and all graph statistics identical |
| Mixed-size, multichunk streaming fixture | Exact arrays and graph statistics; incorrect ordering/missing work rejected |
| Packed dispatcher | Exact scientific rows; complete resume skips all work; checkpoint, staged-input and dispatch tampering rejected |

Exact agreement refers to fixed test inputs and the stated build; it is not a
claim of formal verification of the entire implementation or universal
cross-platform bitwise reproducibility. NaN checks do not compare payload bits.
Tests cover real high-loop graphs, but not all graph/sample combinations.

The tested compiler flags were `-O3 -std=c++17 -fopenmp -ffp-contract=off
-fno-fast-math`. No `-ffast-math`, lowered precision, relaxed promotion threshold,
changed importance distribution, truncated forest, graph exclusion or smaller
sample count was used for a performance claim.

## 6. Installation and reproducible use

Extract the optimization ZIP beside an extracted base C8 archive. Run the check
before applying. The installer validates every payload hash and all files it
would modify; incompatible existing files cause a refusal before any edits.
Backups are retained, and reapplying the same patch is idempotent. Install only
into an idle checkout, not one another process is editing.

```bash
python3 LRI_C8_D3_optimization/apply_optimization.py /path/LRI_C8_D3_HPC --check
python3 LRI_C8_D3_optimization/apply_optimization.py /path/LRI_C8_D3_HPC
cd /path/LRI_C8_D3_HPC
make optimized baseline points reference
make test-optimization
OPENBLAS_NUM_THREADS=1 python3 tests/test_native.py \
  --binary "$PWD/bin/c8d3_optimized" \
  --output verification/performance/c7_compatibility_local.json
```

Dependencies are the base package's dependencies. The new Python orchestration
uses the standard library and the existing scientific stack; it does not add
MPI. The benchmark also uses Linux `/usr/bin/time` for peak RSS.

### Plan a new campaign

Use a fresh seed and a new run directory. The numbers below illustrate the
commands, not a statistical precision guarantee or a universally optimal HPC
configuration. A frozen allocation trained on an independent pilot is supported
by the existing `--allocation` option.

```bash
python3 tools/campaign.py plan runs/c8_high_precision \
  --purpose production --seed 680432977503981207 \
  --points 4096 --replicates 16 \
  --threads 8 --graph-block 8 --chunk-points 1024 \
  --executable "$PWD/bin/c8d3_optimized"

python3 tools/hpc_dispatch.py index \
  runs/c8_high_precision runs/c8_dispatch \
  --lanes 32 --bundle-jobs 4 \
  --statistics results/pilot_20261008/graph_statistics.json \
  --target-core-seconds 1800
```

The soft cost bound is an estimate from recorded pilot task times, not a guaranteed
wall-clock duration. It does not split or modify an already-frozen job. The
example's bundle-job cap bounds packing to four original jobs at a time.

### Launch on Slurm

This example allocates 4 nodes, 8 lanes per node and 8 CPU cores per lane. Adapt
account, partition, memory, time, environment and node topology to the site.
The index's lane count must equal Slurm's total task count.

```bash
export C8_PACKAGE="$PWD"
export C8_DISPATCH="$PWD/runs/c8_dispatch"
export C8_GRAPH_BATCH=8
sbatch --nodes=4 --ntasks=32 --ntasks-per-node=8 \
  --cpus-per-task=8 slurm/run_hpc.sh
```

`C8_ENV_SETUP` may point to a site-specific shell script that loads modules,
activates the environment and selects node-local `TMPDIR`. Verify that `TMPDIR`
is truly node-local; a path on a shared filesystem defeats staging's purpose.
`C8_PYTHON` selects the interpreter. Default OpenMP placement is `cores` with
`close` binding. No Slurm job was submitted as part of this optimization.

For a single local lane, the same code path can be tested with:

```bash
python3 tools/hpc_dispatch.py run runs/c8_dispatch \
  --lane 0 --threads 8 --scratch /your/node-local/scratch
```

Running only lane 0 does not complete a 32-lane plan. Run every lane once or
resume the complete Slurm allocation before assembly; coverage checks will refuse
an incomplete campaign.

### Assemble and rebenchmark

```bash
OPENBLAS_NUM_THREADS=1 python3 tools/assemble_streaming.py runs/c8_high_precision \
  --bootstrap 1024 \
  --output runs/c8_high_precision/C8_optimized_result.json \
  --graph-statistics runs/c8_high_precision/graph_statistics.json

python3 tools/benchmark_optimization.py --repeats 3 --threads 1 2 4
make profile
python3 tools/profile_optimization.py
```

Performance tests regenerate selected regression records. The supplied records
remain in the patch ZIP as the original measurement snapshot. Use a fresh
executable path and a fresh plan for changed compiler flags or numerical backends.
Preserve original physical outputs and manifests rather than merging them with
benchmark fixtures.

## 7. Source/evidence map

* `baseline/src/`: rebuilt original worker and separately instrumented original.
* `src/positive_quad.hpp`, `src/kernel.hpp`, `src/c8d3_integrate.cpp`: exact kernel
  and bounded native execution changes.
* `tools/hpc_dispatch.py`, `slurm/run_hpc.sh`: immutable packed dispatch and launch.
* `tools/assemble_streaming.py`: alternative reader using original RG/statistics.
* `tools/benchmark_optimization.py`, `tools/profile_optimization.py`: reproducible
  uninstrumented timing and instrumented bottleneck attribution.
* `tests/*optimization*`, `tests/test_positive_quad.cpp`, `tests/test_hpc_dispatch.py`,
  `tests/test_streaming_assembly.py`: frozen fixtures and numerical/workflow checks.
* `verification/performance/final_benchmark.json`, `profile_summary.json`,
  `assembly_comparison.json`, and other test JSONs: raw compact evidence. Full
  archived native pilot records remain in the base archive rather than this patch.
* `PATCH_MANIFEST.json`: original/new file hashes, base archive hash and payload
  identity. `SHA256SUMS`: package checksums.

Compiler and scheduler behavior should be checked against the deployment site's
GCC “Optimize Options” and Slurm “srun”/“sbatch” manuals. The measured gains above
come from the included local experiments, not external benchmark claims.
