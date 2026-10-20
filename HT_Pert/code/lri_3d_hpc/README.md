# Optimized 3D Hamiltonian-truncation coefficients

This package computes the same finite-cutoff coefficients as the supplied
3D calculation, with optimized sparse applications, an exact stationary
energy-series formulation, lower-memory vertex construction, and OpenMP/MPI
execution. The original implementations are preserved in `reference/` and
the original SO(3) basis machinery is preserved in `vendor/ht3d/`.

The measured performance and full validation results are described in
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). The derivation of the exact
reformulation and the precision contract are in
[`docs/NUMERICS.md`](docs/NUMERICS.md). Construction stages and their memory
tradeoffs are explained in
[`docs/VERTEX_CONSTRUCTION.md`](docs/VERTEX_CONSTRUCTION.md).

## What is calculated

The expansion convention remains

\[
\Delta_{\mathcal E}=\frac32-\frac{\epsilon}{6}
 +\sum_{n=2}^{K} C_n(L)\epsilon^n,
\qquad x=\frac{3-\epsilon}{4},\quad \epsilon=2s-3.
\]

The Hamiltonian is the original Gaussian-normal-ordered
\(H=H_0+rM+gV\), with \(M=\int d\Omega\,{:}\phi^2{:}/(4\pi)\)
and \(V=\int d\Omega\,{:}\phi^4{:}/(48\pi)\). The bath regulator is
\(N_b=\sum(2n+\ell)n_{n\ell m}\leq L\); the local oscillator is retained
separately. The basis is the SO(3) scalar, inversion-even sector, with the
original field-parity organization and projector tolerances.

`--scheme consistent` includes the full specified self-consistent scalar
vacuum window, using the same top-cutoff coupling series in every lower
vacuum:

\[
D_\ell(N)=E_{\mathrm{vac},\ell}-E_{\mathrm{vac},\ell-N},\qquad D_\ell(0)=0.
\]

All window coefficients and their contributions through the requested
energy order remain included. In particular, the shorter wavefunction
series used by the stationary algorithm does not truncate the window at
fourth or fifth order. `--scheme raw` computes the original uncorrected
prescription. The two prescriptions are distinct results.

## Installation

The recorded environment is Linux, Python 3.12, NumPy 2.5.3, SciPy 1.17.0,
and Numba 0.68.0. The requirements files pin those versions. A C++17 compiler
with OpenMP is used for the native sparse kernels.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0
export HT3D_NATIVE_CACHE="$PWD/work/native-cache"
```

The native library is compiled locally on first use and cached atomically.
`CXX` can select the site's compiler. The default `--backend native` fails
if a compatible native library cannot be built. `--backend auto` allows
an explicit warning and a same-precision SciPy fallback. `--backend scipy`
is available for portability and comparisons.

For production MPI runs, load the HPC site's matching compiler, Python and
MPI modules, then build mpi4py against that MPI:

```bash
MPICC=mpicc python -m pip install --no-binary=mpi4py -r requirements-mpi.txt
```

The site's MPI and Slurm integration determine the correct launcher and
PMI/PMIx configuration. See the official
[mpi4py installation guide](https://mpi4py.readthedocs.io/en/stable/install.html)
and [Slurm MPI guide](https://slurm.schedmd.com/mpi_guide.html).

## Quick start

A small `fixtures/vertices_L4` store is included for a quick smoke test on
machines with the same long-double format. Stores with a different numerical
ABI are deliberately rejected; rebuild the fixture on such a machine.

```bash
python code/ht3d_coefficients.py solve \
  --store fixtures/vertices_L4 --output work/smoke_L4.json \
  --compare-reference results/reference_coefficients_L14.json
```

To build and solve the original largest validated cutoff:

```bash
python code/ht3d_coefficients.py preflight --cutoff 14 --order 8

python code/ht3d_coefficients.py build \
  --cutoff 14 --order 8 --store work/vertices_L14 --spill work/spill

python code/ht3d_coefficients.py solve \
  --store work/vertices_L14 --cutoff 14 --order 8 \
  --scheme consistent --threads 1 --output work/C8_L14.json \
  --compare-reference results/reference_coefficients_L14.json --progress
```

The builder sets the Taylor-vertex degree to `order - 2`. The default local
occupation ceiling covers \(3+4\lfloor K/2\rfloor\); for \(K=8\), this is
occupation 19, represented by `nz=10` per local parity. A larger `--nz` may
be supplied. An insufficient local ceiling or vertex Taylor order is refused.

The reference JSON contains all original even cutoffs from 0 through 14,
both prescriptions, and all coefficients through \(C_8\). Validation compares
`C`, `r`, `g`, every seed energy, and every subcutoff vacuum energy. The
default scaled-error tolerance is `5e-13`; all reported actual errors are
recorded separately from that acceptance threshold.

## Choosing an execution layout

| Layout | Appropriate use | Principal limit |
|---|---|---|
| One process, one thread | Small cutoffs; a reproducible starting point | One core's arithmetic throughput |
| One process, OpenMP | Large sparse operators on a shared-memory node | Small operators and serial preparation work |
| MPI ranks plus OpenMP | A single case whose sparse operators need several nodes | Replicated vectors and row-gather communication |
| Scheduler arrays | Many cutoffs, prescriptions, or construction tasks | Shared-storage throughput and the number of independent tasks |

`--threads` is the maximum requested native thread count. Tiny sparse
products use one thread when their conservative work estimate is below
10,000 nonzeros times right-hand sides. `--serial-work-threshold 0` disables
that policy; the environment variable `HT3D_SERIAL_WORK_THRESHOLD` also sets
it. Dispatch counts are recorded in result metadata.

Benchmark 1, 2, 4 and 8 threads on the target system. A faster isolated
sparse kernel does not imply the same speedup for a full coefficient run.
The saved measurements include examples of this distinction. Passive
OpenMP waiting helped small-kernel overhead on the validation host.

Local oscillator products use the exact band structure by default
(`--local-mode banded`, or `local_mode='banded'` in the Python solver).
The parity-organized quartic blocks have at most five diagonals. Cached
weights contract a read-only sliding-window view of a two-dimensional
padded input, reducing the local work from \(O(n_b n_z^2)\) to
\(O(n_b n_z b)\), with \(b\leq5\), without constructing a three-dimensional
temporary or changing precision. General band contractions are selected
for long-double batches with at least 128 input rows; float64 and smaller
batches use dense multiplication. Identity and diagonal blocks have direct
paths, and bath terms with local \(q_0\) use a global identity addition.
`--local-mode dense` provides a control for the remaining local matrix
products. The numerical contract and array-aliasing details are documented
in [`docs/NUMERICS.md`](docs/NUMERICS.md).

For a single case across four MPI ranks:

```bash
mpiexec -n 4 python -m mpi4py code/ht3d_coefficients.py solve \
  --mpi --store work/vertices_L14 --cutoff 14 --threads 1 \
  --scheme consistent --output work/C8_L14_mpi4.json --progress
```

Each rank stores its own sparse rows, with the seed row replicated for
energy contractions. The row partition is balanced using the largest
zeroth-order quartic bath vertex. An entire Taylor-Hamiltonian application
is accumulated locally, then its disjoint row blocks are gathered once.
There are no floating-point MPI reductions. Couplings and all current
vacuum/primary energy coefficients are broadcast from rank zero at each
order to keep the recurrence schedule identical.

Wavefunctions remain replicated. This implementation primarily distributes
matrix memory and sparse computation; it is not a fully distributed-vector
solver. At small lower cutoffs some ranks own no rows. For many independent
cases, distributing whole cases is often a better use of a large allocation
than adding ranks to one small solve.

The MPI tests use genuine two- and four-process communication on one host.
Cross-node performance, interconnect scaling, and Slurm execution must be
measured on the target cluster; the package does not claim those were tested
in this environment.

## Slurm examples

**On SDSC Expanse and Perimeter's symmetry use [`cluster/`](cluster/RUNBOOK.md) instead:** a
validated two-site layer (pinned environment, staged releases, validation receipts, a
restartable stage runner and a safe submit wrapper). The `hpc/` files below are generic
starting points for other sites.

`hpc/solve_openmp.sbatch` and `hpc/solve_mpi.sbatch` contain complete example
jobs. Export the package, vertex, cutoff and output locations first:

```bash
export HT3D_ROOT="$PWD"
export HT3D_STORE="$PWD/work/vertices_L14"
export HT3D_CUTOFF=14
export HT3D_OUTPUT="$PWD/work/C8_L14_slurm.json"
sbatch hpc/solve_openmp.sbatch
```

Adjust the scheduler's partition/account, time, memory and core allocation
for the site and cutoff. The example resource requests are starting values,
not predictions for larger cutoffs. The MPI example uses one rank per node
and OpenMP within each rank; one rank per NUMA domain is another layout to
measure on suitable hardware.

Large vertex construction can be split into four dependency stages:

1. Prepare the Fock graph, SO(3) projectors and projected inputs once.
2. Build each particle sector's annihilation images independently.
3. Assemble each bath power/Taylor-order pair independently; order eight
   has 28 such tasks.
4. Validate the completed tasks and publish the final vertex store.

```bash
export HT3D_INPUTS="$PWD/work/prepared_L14"
export HT3D_STORE="$PWD/work/vertices_L14_cluster"
bash hpc/submit_pipeline.sh
```

The submission script creates `afterok` dependencies between the stages.
The task runner verifies and reuses completed image/matrix tasks. Individual
commands are also available in `code/taylor_pipeline.py`; `tasks --path ...`
lists the particle sectors and matrix-task mapping. Consult
[Slurm's array documentation](https://slurm.schedmd.com/job_array.html) for
site-specific array limits and concurrency caps.

## Memory, storage and larger cutoffs

Vertex stores use separate `.npy` CSR buffers, shared index patterns where
they are exactly identical, a JSON manifest, source fingerprints, file
checksums and numerical-ABI information. Loading uses read-only memory
maps. A larger stored cutoff can supply a smaller solve. The MPI loader
copies only the rows it owns rather than creating complete smaller-cutoff
matrices on every rank.

The streamed builder writes temporary coordinates to scratch and assembles
one Taylor matrix at a time. Its default also caches selected CSR layouts
to reduce repeated conversions. `build --no-layout-cache` trades some
construction speed for lower memory. See the construction measurements for
both choices. Scratch storage must have room for the intermediate files;
the final store size alone is not the required temporary-disk capacity.

The inherited graph/projector preparation still runs in one process.
`preflight` reports exact **graph-array** counts without constructing that
graph. These are not total peak-memory estimates:

| Cutoff | Full bath states | Graph arrays only |
|---:|---:|---:|
| 14 | 1,784,949 | 0.142 GiB |
| 16 | 8,778,392 | 0.745 GiB |
| 18 | 40,968,710 | 3.694 GiB |
| 20 | 182,727,113 | 17.411 GiB |
| 22 | 783,193,597 | 78.507 GiB |
| 24 | 3,240,244,094 | 429.050 GiB |

Projectors, SVD workspace, images, sparse vertices and state vectors are
additional. The default two-million-state and 2 GiB graph-array guards
therefore stop at the original tested scale. For larger runs, set
`--max-states` and `--max-bytes` explicitly after budgeting resources.
The staged Slurm preparation takes those values from `HT3D_MAX_STATES` and
`HT3D_MAX_BYTES`. No state cap or arithmetic precision is silently reduced.

The basis dimension still grows rapidly with cutoff. Streaming and MPI
improve storage and distribute work; they do not change that dimension.
At very large cutoffs the next architectural bottleneck is the single-node
graph/projector stage. Matrix-free vertices, a graph restricted directly
to the necessary magnetic sectors, or distributed projector blocks would
be further projects requiring their own numerical validation.

## Precision and reproducibility

The default remains `numpy.longdouble`. On the validation machine this is
a 64-bit significand in a 16-byte storage slot: x87 extended precision,
approximately 19 decimal significant digits. NumPy names it `float128` on
this platform; that name does **not** mean IEEE binary128. The native and
MPI paths explicitly check this numerical ABI. The original SO(3)
projectors still originate in float64 and are promoted afterward.

`--dtype float64` is an explicit diagnostic choice. Stores made in one
arithmetic format cannot silently be loaded as another. The native build
disables fast-math and floating-point contraction. More reported decimal
digits, a higher cutoff and a higher-precision projector calculation are
separate issues.

Result JSON files preserve coefficient values as decimal strings and
record the input manifest hash, source hashes, settings, library/compiler
metadata, native dispatch counts, timings, peak RSS per rank and validation
errors. Only rank zero writes a final MPI result. Publication is atomic,
and an output lock prevents simultaneous writers.

`--resume` reuses an identical **completed** coefficient job. It verifies
any newly requested reference comparison before accepting the result.
It does not resume an interrupted wavefunction recurrence from an
intermediate order; that solve restarts from order one. Construction tasks
are separately restartable because each completed task is published
atomically. Source, parameter, precision or incomplete-cache mismatches
are reported rather than accepted silently.

`--trust-staged-arrays` explicitly skips full file hashing after an
independently verified staging step; shape, precision and source checks
remain active. MPI performs one checksum pass on rank zero by default,
then other ranks open the same immutable store. Keep software and numerical
ABIs consistent across ranks.

## Tests and benchmarks

Examples of the supplied checks:

```bash
python tests/check_native_backend.py --output work/native_check.json
python tests/check_stationary_independent.py --output work/stationary_check.json
python tests/check_optimized_solver.py --backend native --output work/solver_check.json
python tests/check_local_bands.py --output work/local_bands_check.json
mpiexec -n 4 python -m mpi4py tests/check_mpi_backend.py --output work/mpi_check.json
```

To repeat the final comparison against all 16 saved cases (even cutoffs
0 through 14, both prescriptions, through order eight), use the L14 store:

```bash
python tests/check_saved_coefficients.py --store work/vertices_L14 \
  --threads 8 --output work/coefficient_grid_check.json
```

The included `results/final_coefficient_validation.json` records a maximum
scaled discrepancy of `6.591949208711866959e-17` for that complete grid.

Run each script with `--help` for its fixture/cache options. Additional
tests cover vertex-store corruption and stale caches, staged construction,
driver validation, completed-job reuse and scheduler-script syntax.
[`check_local_bands.py`](tests/check_local_bands.py) covers both floating
types, both local parities, oscillator powers zero through four, empty and
read-only input batches, and the 127/128-row dispatch boundary. Supplying
`--store` and a covered `--cutoff` also compares dense and banded full
coefficient, energy, wavefunction and window series for both prescriptions.

`benchmarks/benchmark_solver.py` performs a fresh-process solver comparison
and optionally writes cProfile data. It validates all energy and coupling
series against the original coefficient JSON. `--store` uses the new
format. `--trusted-pickle` is solely for the original locally generated
cache; never use that option with an untrusted file.

For scientific use, repeat measurements on the actual allocated nodes,
record both wall and CPU time, and compare the resulting coefficients
before increasing resources. The benchmark JSON files retain the timing
samples rather than presenting kernel speedups as cluster speedups.
