# Integration candidate: optimized local basis (1.1.0rc1)

See **[INTEGRATION.md](INTEGRATION.md)** for the new opt-in saved-basis path,
new-release validation, symmetry training jobs, and selective convergence campaign.
The consistent-window Hamiltonian is unchanged. Experimental physical corrections
are not included. The material below is the original release documentation.

---

# Optimized dressed-phi4 Hamiltonian truncation for HPC

(Release notes for the symmetry/window revision are at the end of this file.)

This is an optimization of the **direct dressed-zero-mode phi4 solver**, not of
the spin-boson NRG calculation and not of the epsilon-coefficient recursion.
It retains the source Hamiltonian, product regulator, normal ordering, coupling
tuning, and float64 arithmetic. No thermal target or new matching term is added.

The reference is the `product_reference/` code in the supplied
`lri_extended_comparison_study.zip`. Unmodified copies are in `reference/`.

## Main changes

1. Replace full Kronecker Hamiltonians by exact, parity-packed matrix-free
   contractions. Dense local matrices and bath operators are stored separately.
2. Provide a **tensor** backend for speed at moderate cutoffs and a **ladder**
   backend whose storage avoids materializing W1,...,W4 at larger cutoffs.
3. Build bath states and ladder edges with exact integer rank/unrank, without a
   Python dictionary containing all partition tuples.
4. Reuse small reduced contraction matrices in the moving-subspace response
   Jacobian. Its local basis response is retained, not dropped.
5. Thread independent bath rows; avoid launching a thread team for very small
   standalone kernels. Distribute independent scans using Slurm arrays.
6. Validate outputs before publication/reuse/export; checkpoint Newton states,
   hold solver-owned locks, and retain source/dependency fingerprints.

7. **Opt-in full-vacuum window correction** (`--window vacuum`, default off), which removes most of the
   non-decaying descendant-identity violations of the raw product regulator. See **[docs/WINDOW.md](docs/WINDOW.md)**.
   `python -m lri_dressed identities` reports those identities for any accepted record.
8. **symmetry deployment** (`cluster/symmetry/`): frozen installs, staged validation receipts, calibration, a
   node-packing launcher (`scripts/pack_node.py`) with cross-node generation leases, and submit/status tools. See
   **[cluster/symmetry/README.md](cluster/symmetry/README.md)**.

See **[PERFORMANCE.md](PERFORMANCE.md)** for measured timings and their scope,
**[docs/ALGORITHM.md](docs/ALGORITHM.md)** for the exact factorization, and
**[docs/HPC.md](docs/HPC.md)** for deployment, claims, checkpoints and limitations.

## Install and validate

    python -m pip install -e '.[validation]'
    export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
    export NUMBA_NUM_THREADS=4
    export NUMBA_CACHE_DIR="$PWD/.numba_cache"
    git worktree add ../e637dfd e637dfd      # or any frozen copy of release e637dfd
    python scripts/validate_release.py --threads 4 --output validation/local.json --baseline ../e637dfd

A C compiler is not required for these Python/Numba sources. Standard compatible
NumPy/SciPy/Numba binary installations are needed. The exact tested versions are
in `requirements-tested.txt` and the validation/benchmark outputs. First use
compiles kernels; measured warm numerical times are NOT cold-start wall times.

## Run a point or a continuation scan

    python -m lri_dressed run \
      --bath-cut 16 --nz 24 --osc 192 --deltas .1 \
      --seed inputs/N16_z24_o192_d0.10000000.json \
      --threads 4 --memory-limit-gib 4 \
      --output-dir results/my_run --resume

For an independent scan with continuation:

    python -m lri_dressed run \
      --bath-cut 20 --nz 24 --osc 192 \
      --deltas .24 .225 .2 .175 .15 .125 .1 .075 .05 .025 .01 \
      --seed-dir inputs --threads 4 --memory-limit-gib 8 \
      --output-dir results/scan20 --resume

Only coupling coordinates from a seed are used. Its thermal value is not a fit
input. With no seed at a strongly coupled point, the driver follows intermediate
weak-to-strong continuation points as in the source. Those bridge solves cost
time and are not separately checkpointed; provide accepted seeds for campaigns.

`bath-cut` limits the total positive-mode level N. `nz` is the dressed local
state count **per parity**. `osc` is the independent auxiliary oscillator count.
These are not the old frozen energy cutoff or perturbative particle caps.
Endpoints x=0 and x=1/4 are excluded just as in the source direct solver.

### Backend selection

- `--backend tensor`: store bath W1..W4, never global Kronecker matrices. Usually
  fastest at the measured moderate cutoffs; W4 can still become large.
- `--backend ladder`: store only B and B-dagger. Normally ordered powers share
  annihilation intermediates, and reflection is projected only after a complete
  vertex. More sparse sweeps buy slower memory growth.
- `--backend auto` (default): tensor for bath-cut <=18, ladder above. This is a
  conservative release heuristic, not a universal hardware optimum. Both give
  the same finite Hamiltonian up to floating-point regrouping.

ARPACK remains the production eigensolver. A preconditioned block-solver trial
was slower in the tested case and was not promoted into the production path.
There is no automatic relaxation of an eigensolver tolerance.

The default eigensolver and tuning tolerances match the source. More stringent
explicit controls are available, for example:

    --eig-tol 1e-12 --tuning-tol 1e-11 --residual-tol 1e-9 --ncv 48

These change the configuration fingerprint. They improve numerical solve
resolution only, not automatically finite-cutoff or Hamiltonian-matching errors.

### Inspect and export

    python -m lri_dressed status --input-dir results/scan20
    python -m lri_dressed export --input-dir results/scan20 --output accepted.json

Final files are checksummed envelopes. Export restores a flat list with the old
scalar keys and adds provenance. Root histories, eigenvector/orthogonality
residuals, local and bath edge diagnostics, measured times and allocation
information are retained. Edge probabilities are warnings, not energy-error
bounds. `timings` are cumulative over a reused solver instance; `seconds` and
`spectral_evaluations` refer to the current solve.

**Internal eigenvector layout has changed.** It is bath-major with local parity
inferred from total parity and bath occupation. Old warm-vector files and code
that assumes `reference.ix` or explicit global matrices require an adapter. Only
the scalar-result interface is intentionally preserved. Product-regulator
high-state matching code has not been ported to this internal layout here.

## Before requesting large nodes

    python -m lri_dressed plan --bath-cut 32 --nz 32 --osc 256

This performs exact integer counts without allocating the Fock space. The byte
envelope is conservative and uncalibrated, not an Expanse RSS measurement. Large
index arrays use int64 when required; counts beyond the supported integer range
are rejected. No physical cap is silently reduced to meet memory limits.

Run the target-cluster validation job and calibrate thread counts and memory
before a campaign. See `docs/HPC.md` and `slurm/`. Account and allocation expiry
are not copied from old reports. This separate `lri_dressed` namespace does not
replace the user's reviewed coefficient-campaign repository.

**Multi-node parallelism is across independent points/scan lanes. A single
large eigensolve is not MPI-distributed.** Multi-rank launches are rejected to
prevent accidentally replicating a large allocation. Threaded operator actions
do not parallelize all ARPACK orthogonalization or nonlinear-root work. There is
no claim of 32/64/128-core or Expanse speedup from the local four-CPU tests.

## Reproduce measurements

    python scripts/profile_reference.py
    python scripts/run_benchmark_grid.py
    python scripts/summarize_benchmarks.py

The benchmark grid skips already present result files; move `benchmarks/runs/`
aside to force fresh measurements. Every run starts a fresh process, uses the
same caps, delta, tolerances and deliberately perturbed saved coupling seed,
and times setup plus a real tuning solve. It excludes JIT warmup from that timer;
peak RSS includes the whole process. Reference code is unchanged. Run timing
jobs sequentially on an otherwise idle allocation.

For a specific larger point:

    python scripts/bench_once.py --impl ladder --N 24 --nz 24 --osc 192 \
      --delta .1 --threads 4 \
      --seed inputs/N16_z24_o192_d0.10000000.json \
      --out benchmarks/custom24.json

This benchmark intentionally perturbs the seed by (0.03,0.001) and does not
pretend to benchmark a complete weak-to-strong continuation campaign.

## Directory map

- `src/lri_dressed/`: exact basis, local problem, compiled kernels, operators,
  eigensolver/root solver, planning, validation/IO, and command line.
- `reference/`: unchanged dressed source, for regressions/profiling only.
- `inputs/`: supplied accepted coupling seeds; never thermal fit targets.
- `tests/`: independent matrix-action, spectrum, Jacobian, basis, integer-width,
  threading, result-integrity, lock, resume and allocation tests.
- `scripts/`: benchmarks, profiling, validation receipt, manifest and lane driver.
- `slurm/`: target-node validation and independent-lane job-array templates.
- `benchmarks/`: raw independent-process measurements, profiles, summary JSON/CSV.
- `results/`: validation receipts and selected new computation records.
- `docs/`: numerical algorithm and HPC integration/limitations.
- `provenance.json`: source-archive and reference-file checksums.
- `MANIFEST.sha256`: checksums of distributed files (excluding itself).

## Scientific scope

This release makes the SAME raw product-regulator calculation faster and smaller.
It does not establish the physical continuum curve, repair its endpoint mismatch,
identify all operator branches, or add complete effective-Hamiltonian matching.
A small tuned spin-gap residual remains a calibration check, not an independent
physical precision bound on the thermal dimension.

## Technical references

- SciPy `eigsh` matrix-free symmetric-eigenproblem API:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Numba row-parallel loops and race-condition considerations:
  https://numba.readthedocs.io/en/stable/user/parallel.html
- Slurm job-array interface:
  https://slurm.schedmd.com/job_array.html

The measurements and tests in this package, not those API pages, support the
reported speedups and numerical regression claims.


## Symmetry/window revision (2026-10)

- `--window none` (default) is numerically the original release: same operator, same ARPACK path. Equality with
  e637dfd to ≤ 1e-12 is a validation stage.
- `--window vacuum --window-mode consistent|literal` adds D(N) = Ev(cut) − Ev(cut − N) to the bath diagonal
  (docs/WINDOW.md). It is part of the configuration fingerprint.
- **Claims.**
  - Claims combine a node-local flock with a cross-node generation lease, because symmetry's BeeGFS has no global
    flock.
  - A point owned by a live process elsewhere makes `run` exit 73; a safe stop exits 75.
- **Fingerprints.** Receipts and pack manifests bind `release_sha256` (code, scripts, wrappers, tests, reference,
  inputs, dependency pins) as well as `source_sha256` (numerics). `validate_release.py` writes its receipt only after
  every stage passes.
- **Manifests.** `make_campaign.py` keeps its legacy lane mode for `slurm/scan_array.slurm`. `--pack` writes
  `lri-dressed-pack-v1` items for `scripts/pack_node.py`. `run_lane.py` rejects pack manifests and any lane carrying
  window or tolerance options.
