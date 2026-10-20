# LRI Hamiltonian truncation: profiled CPU/HPC implementation

This package is a performance rewrite of the supplied `check_lri_C7.py`,
`compute_phi6.py`, and `check_lri_hamiltonian.py`. It evaluates the same finite-cutoff
Hamiltonian. It does **not** change the extrapolation ansatz or complete physical
Hamiltonian matching.

**Measured, local result:** thermal C0–C7 at cutoff 40 is about **2.03x faster on one
thread** and **4.21x faster on four threads** than the supplied single-thread code.
Peak resident memory falls from approximately **636 MiB to 434 MiB**. These are
three-run median, warm-kernel results; see `PERFORMANCE.md` for cold-start costs,
full measurement scope, larger runs, and limitations.

**Validation status:** the threaded CPU path has been regression-tested against
both original implementations, full perturbation recursions, and saved results
through cutoff 50. MPI row partitioning and collective semantics were tested
with a two-/three-rank in-process collective simulator. **No real MPI runtime or
multi-node hardware was available. The MPI backend is experimental until the
provided real-MPI smoke test passes on the target cluster.** No network scaling
claim is made.

## 1. What stays unchanged

* The cutoff is the frozen integer-quarter condition `4*N + P <= 4*Lambda`.
* The two couplings are fixed from the same phi and phi3 gaps.
* All necessary Taylor coefficients of `u_n(epsilon)` are retained.
* Sphere parity is projected only after a complete vertex. Auxiliary parity
  sectors remain present between ladder factors.
* Thermal degree 6/7 uses exactly the existing caps `P<=15`, `Q<=12`. Phi6 degree
  5 uses `P<=14`, `Q<=8`; degree 3 uses `P<=10`, `Q<=4`. Here Q counts nonzero-mode
  particles. No additional truncation has been introduced.
* Phi6 outputs include both `raw` and `vacuum_subtracted`, preserving the same
  isolated vacuum correction; the latter is not a fully matched Hamiltonian.
* All physical arithmetic is **float64**. There is no float32, mixed precision,
  approximate sparsification, or `fastmath` relaxation.

Horner factorization and block reductions regroup floating-point operations.
Results are therefore required to agree within tolerance, not universally
bit-for-bit. On the tested cutoff-40 run, optimized C/r/g were bitwise identical
across 1, 2 and 4 threads. That is an observation, not a portability promise;
MPI reductions and different hardware can change last bits.

## 2. Installation and first validation

Tested environment: Python 3.13.5, NumPy 2.3.5, Numba 0.65.1, SciPy 1.17.0 on
Linux. Exact versions are in `requirements-tested.txt`; broader dependency ranges
in `pyproject.toml` are not a matrix of tested environments.

From the extracted project directory:

```bash
python -m pip install -e '.[validation]'
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export NUMBA_CACHE_DIR="$PWD/.numba_cache"
python tests/run_all.py
```

Run the suite in an allocation with at least four CPU slots. The tests run in
separate processes, so the collective simulator does not replace mpi4py in
subsequent tests. SciPy is needed for original-code comparison; the optimized
solver itself does not use SciPy sparse matrices.

If your cluster has no external package access, provision the environment using
its normal software-management process. This archive does not bundle Python,
Numba, or an MPI implementation.

### JIT warmup matters

The first genuinely empty-cache run measured **6.63 seconds of warmup/JIT**, in
addition to imports and the main numerical workload. A cached fresh process
used about 0.2–0.3 seconds for the small warmup. The warmup overhead can make an
isolated small cold run slower than the original. Do not use only warm timing
numbers to estimate cold-job throughput.

To prewarm the common paths with no production output files:

```bash
export NUMBA_NUM_THREADS=4
python - <<'PY'
from lri_hpc.solver import compute
compute(4, 'thermal', 7)
compute(4, 'phi6', 5)
compute(4, 'phi6', 3)
PY
```

Use a writable persistent cache on a homogeneous node class, or prewarm once per
node on node-local scratch. Cache compatibility depends on Numba/Python/CPU;
recompilation after an environment or CPU change is normal. A read-only mmap
basis can also trigger an additional kernel specialization on first use.

## 3. Running the finite-cutoff calculation

### Thermal coefficients through seventh order

```bash
python -m lri_hpc --task thermal --degree 7 \
  --cutoffs 40 44 48 50 --threads 4 \
  --memory-limit-gib 8 --output-dir results/thermal --resume
```

### Phi6 gap through fifth order, both prescriptions

```bash
python -m lri_hpc --task phi6 --degree 5 \
  --cutoffs 40 44 48 50 --threads 4 \
  --memory-limit-gib 8 --output-dir results/phi6 --resume
```

For the thinner third-order gap calculation, set `--degree 3`. The supported
thermal degrees are 6 and 7; supported phi6 degrees are 3 and 5. Unsupported
orders are refused instead of silently reusing insufficient particle caps.

One JSON result is written per cutoff, atomically. It contains coefficients,
couplings, source fingerprint, tuning residuals, an independent second-order
shell check, phase timings, resident-memory measurement, and per-rank halo
statistics when applicable. Full results contain **finite-cutoff** coefficients,
not extrapolated physical predictions.

### Check memory before allocating a large basis

```bash
python -m lri_hpc --task thermal --degree 7 \
  --cutoffs 50 60 80 100 --threads 1 --plan --memory-limit-gib 8
```

The count is exact, using a small suffix-count dynamic program, without building
the Fock graph. For the thermal caps:

| Lambda | States, including auxiliary parities |
|---:|---:|
| 40 | 668,530 |
| 50 | 3,096,673 |
| 60 | 11,900,137 |
| 80 | 117,687,411 |
| 100 | 796,157,247 |

The basis cardinality has not been changed. This remains an explicit-basis
algorithm with rapidly growing state count; distributing its rows is not a
removal of that combinatorial growth.

`--memory-limit-gib` is a **conservative per-rank working-set screen**, not an OS
RSS limit or proof of peak memory. It includes an allowance of 100 float64
vectors per local row plus edge/table allowances. The plan prints the vector
allowance separately. Interpreter/JIT memory, MPI buffers, filesystem page
cache, and halos also matter. Set the budget below the scheduler's per-rank
allocation and review measured peak RSS. Large allocations are refused before
materializing all row metadata when the initial vector screen already fails.

The basis count uses checked signed-int64 arithmetic. Counts that would overflow
are refused. State IDs use int32 only while safe, otherwise int64. CSR pointers
are int64. Mode and occupation storage is compact integer metadata, not a
reduction of numerical precision.

## 4. What was optimized

### 4.1 Exact rank/unrank instead of a Python state dictionary

The original builds a Python list of arbitrarily large packed state integers
and a dictionary mapping every state to its index. This was a dominant measured
cost. The new builder uses the same depth-first ordering of nondecreasing mode
lists, but computes each state's rank directly from exact suffix counts.

For positive modes at least s, with at most k further particles and integer
energy budget e, the count recurrence is

```
G[k,e,s] = G[k,e,s+1] + G[k-1,e-(4*s+1),s]
```

when the second term is admissible; the empty suffix is counted once. For
zero modes the corresponding recurrence is

```
Z[p,q,e] = G[min(p,q),e,1] + Z[p-1,q,e-1]
```

with invalid terms omitted. Cumulative sibling counts provide exact rank and
unrank operations. Reference zero-mode states retain IDs p. Each worker can
construct an arbitrary contiguous range of rows without generating previous
rows, or receiving a global dictionary from rank zero.

Count-table storage is O(q Lambda^2 + p q Lambda), separate from the Fock basis.
Row construction costs roughly O(D p log Lambda + E p), with fixed perturbative
particle caps p,q. The implementation is compiled and threaded. It replaces
Python-object overhead, not the required physical state space.

### 4.2 One compact graph, not a float-valued sparse matrix for every Taylor order

Edges store a neighbor ID, mode, and occupation. The coefficient
`sqrt(occupation) * u_mode[j]` comes from a small float64 lookup table. The
creation and annihilation graphs both use **row-gather** form; no concurrent
scatter or atomic update is needed.

At Lambda 40, the original unique sparse buffers occupy 223,083,308 bytes.
The new two-orientation edge buffers occupy 58,381,532 bytes, about **3.82x
smaller**, excluding the small coefficient lookup. This does not mean total
process RSS is 3.82x smaller: wavefunctions and the JIT runtime also consume
memory.

### 4.3 Fused polynomial ladder kernels

Taylor components are contiguous within each state. One compiled kernel walks
the edge list while accumulating all requested Taylor components, rather than
issuing a separate sparse matrix-vector product for every coefficient pair.
Exact-zero input components may be skipped; small nonzero numbers are never
thresholded. Known particle parity suppresses identically zero output rows;
sphere parity is **not** projected early.

Each output row is owned by one thread. `fastmath=False` is explicit. Scalar
inner products use fixed 4096-row blocks and `math.fsum` on the block partials,
then a small MPI reduction when distributed. Changing MPI partition boundaries
can change floating-point grouping; this is covered by tolerance tests, not a
claim of globally reproducible summation.

### 4.4 Nine ladder sweeps instead of seventeen per vertex

Writing C=B-dagger, the quartic vertex is evaluated in ordered Horner form:

```
V psi = (C^4 + 4 C^3 B + 6 C^2 B^2 + 4 C B^3 + B^4) psi / 12
M psi = [C(C + 2B) + B^2] psi
```

The operators are not commuted. Common intermediates are reused. This needs
four annihilation and five creation applications, versus seventeen total in
the original combined M/V implementation. Parity projection happens last.

### 4.5 Shorter lifetimes for large arrays

Only the three calibration references are retained during low-order tuning.
Reference-vertex vectors are stored sparsely. After tuning, scalar quotient
components are computed and checkpointed one reference at a time; those
wavefunctions are then released. The thermal and phi6 reference states are
constructed after the calibration wavefunctions have been released.

The Rayleigh-quotient calculation streams successive B^j psi arrays rather than
keeping five full high-order series simultaneously. The vacuum correction
reuses a small cumulative shell table and materializes one diagonal coefficient
at a time.

## 5. Cluster execution

### Recommended first: independent-cutoff Slurm arrays

```bash
sbatch slurm/array.slurm
```

The template covers cutoffs 40–64 and limits concurrent array tasks. Edit its
CPU count, memory, array range, environment activation, and output paths for the
site. Independent cutoffs do not communicate and are the simplest way to use
multiple nodes efficiently. The template requests eight CPUs as an example;
local measurements cover only one, two, and four. Benchmark rather than assume
a linear gain from larger thread counts.

The CLI pins BLAS threads to one before numerical imports and gives the CPU
team to Numba. Avoid running several multithreaded ranks on the same cores.

### Experimental: distribute one cutoff over MPI ranks

Install mpi4py against the cluster's supported MPI environment. Then run:

```bash
mpiexec -n 1 python tests/mpi_smoke.py
mpiexec -n 2 python tests/mpi_smoke.py
mpiexec -n 4 python tests/mpi_smoke.py
```

These are real-MPI tests to run **on the target system**; they were not run in
the delivery environment. They compare C/r/g and both phi6 prescriptions to
the bundled original solver and full small-cutoff recursions.

After those tests pass:

```bash
sbatch slurm/distributed.slurm
```

The template starts one MPI rank per node with a threaded local kernel team.
The site's `srun --mpi=...` option and MPI modules may need adjustment. **Always
supply `--mpi` for a single distributed calculation.** Without that flag,
processes are independent and must not write the same output/checkpoint files.

Implementation details:

* Each rank constructs and stores only its owned basis rows and edge rows.
  Small suffix tables are replicated, not the full basis or wavefunctions.
* Static, unique neighbor requests establish separate creation/annihilation halo
  plans. Requested wavefunction values are packed across all Taylor components.
* The hot path uses buffer-based `Alltoallv`; there is no full-vector allgather or
  Python-object serialization of wavefunctions. Scalar coefficient reductions
  use `Allreduce`.
* Halos are currently **blocking**, without communication/computation overlap.
  Latency, halo volume, rank imbalance, and MPI behavior have not been measured
  on a network. Inspect `ranks[*]` timings/halo counts before adding more nodes.
* A conservative legacy-MPI count check refuses transfers above signed-int32
  count/displacement limits rather than overflowing. Extremely large messages
  require more ranks; chunked/large-count collectives are not implemented here.

Memory is approximately local vectors O(K D/R), local edges O(E/R), replicated
small count tables, and the actual halos. Halo storage/traffic does **not** have
a demonstrated 1/R bound. The code is therefore a distributed-memory
implementation, not evidence of ideal strong scaling.

The simulator validates ownership, request ordering, and numerical collective
semantics only. It cannot validate mpi4py's target ABI, MPI progress/failure
behavior, thread initialization, scheduler binding, or network throughput.

## 6. Checkpoints and optional basis caching

By default the CLI writes scalar phase checkpoints below the output directory.
They record completed coupling calibration and each completed reference's
quotient components. `--resume` skips completed outputs and reconstructs only
unfinished references after an interruption. Configuration and source hashes
must match. A mismatch is refused, not silently reused.

A phase in progress must be recomputed after interruption; this is not a dense
wavefunction checkpoint/restart mechanism. Per-rank wavefunction checkpoints
and restart in the middle of a ladder sweep are not implemented.

Optional rank-local basis caches are uncompressed `.npy` arrays:

```bash
python -m lri_hpc --task thermal --degree 7 --cutoffs 50 --threads 4 \
  --basis-cache /path/to/node-local/scratch/lri-basis \
  --output-dir results/thermal --resume
```

Basis keys include cutoff, both particle caps, rank, and rank count. Memory
mapping avoids an extra eager read copy. Cache directories are published by
atomic rename; partial directories are ignored. Metadata/schema/array shapes
and dtypes are checked. The cache is not a cryptographic integrity certificate;
use reliable storage and rerun regressions when moving environments. Use shared
storage for durable scalar checkpoints and node-local storage for large basis
caches when possible.

## 7. Validation and diagnostics

`tests/run_all.py` covers:

1. Exact state order and both ladder matrices against the original, including a
   mode-index-above-255 fixture with small particle caps.
2. Random-vector ladder jets, vertex actions, and Rayleigh quotient components.
3. Thermal degrees 6/7 and phi6 degrees 3/5 at cutoffs 4,8,12,24,32; both phi6
   prescriptions and all r/g coefficients are compared.
4. Full seventh-/fifth-order recursions at cutoffs 4 and 8.
5. mmap cache reads, partial scalar restart, stale checkpoint rejection, and
   preflight memory refusal.
6. Two-/three-rank simulated collectives.

Production regression comparisons use

```
abs(new - original) <= 1e-7 + 2e-11 * abs(original)
```

This is a test threshold, not a certified bound on future numerical error.
Observed discrepancies are substantially smaller; see `PERFORMANCE.md`.
A second-order shell identity is evaluated independently on every production
run. A discrepancy greater than 1e-10 is treated as an error.

`ranks[*].phase_seconds['ladder']` includes halo time; `vertices` includes its
ladder calls. These are nested measurements: **do not add all phase fields**.
Peak RSS includes imports and JIT work, is Linux KiB in the supplied measurements,
and is process-local; summing rank RSS can count shared pages more than once.

## 8. Export and integration with the existing extrapolation code

```bash
python export_results.py results/thermal --task thermal --degree 7 \
  --prefix exported/thermal_runs
python export_results.py results/phi6 --task phi6 --degree 5 \
  --prefix exported/phi6_runs
```

The list JSONs retain `cutoff`, `C`, `r`, `g`, and the phi6 `raw` /
`vacuum_subtracted` records used by the previous analysis loader. Point the
existing analysis scripts at these exported JSONs. CSVs are also produced for
inspection; the phi6 CSV includes both gap and thermal coefficient columns.

No least-squares weighting, logarithmic-tail model, continuum target, or
matching parameter was changed in this optimization. Faster and larger
finite-cutoff calculations do not remove the physical matching error discussed
in the supplied research note.

## 9. Reproducing performance measurements

```bash
OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=4 python benchmarks/benchmark.py \
  --impl original --task thermal --cutoff 40 --output original40.json
OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=4 python benchmarks/benchmark.py \
  --impl optimized --task thermal --cutoff 40 --threads 4 --output optimized40.json
```

Use independent processes and several repeats on reserved nodes. This script
separates import/warmup time from the workload and records RSS. Set a new empty
`NUMBA_CACHE_DIR` to measure genuinely cold compilation. Do not compare a
profiled original run to an unprofiled optimized run.

`benchmarks/profile_reference.py` produces cProfile records for bottleneck
identification. The new solver's per-phase timings identify the next bottlenecks.
For real multi-node scaling, hold the cutoff fixed, vary rank/thread counts,
and report elapsed time, peak RSS per node, halo volume/time and coefficient
residuals together. Neither synthetic collectives nor CPU-local timings provide
network performance evidence.

## References for implementation mechanics

* Numba parallel loops and race conditions: https://numba.readthedocs.io/en/stable/user/parallel.html
* Numba numerical performance / fastmath: https://numba.readthedocs.io/en/stable/user/performance-tips.html
* mpi4py buffer communication: https://mpi4py.readthedocs.io/en/stable/tutorial.html
* Slurm job arrays: https://slurm.schedmd.com/job_array.html

These document the programming mechanisms, not the physical validity of the
Hamiltonian or a guarantee of performance on another machine.
