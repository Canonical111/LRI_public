# Effective-Hamiltonian correction: optimized HPC addon

This is a standalone, namespaced addon for the isolated `g(eps)^2 D(eps)`
correction in `lri_effective_hamiltonian_campaign_update.zip`.
It does **not** replace `lri_hpc_Hamitonian`, reproduce its later reviewed Expanse
code, complete physical Hamiltonian matching, or refit continuum C6/C7.

**What changed:** the raw and corrected calculations share one basis and one
calibration; an exact perturbative response computes the paired differences
without subtracting two complete seventh-order spectra. Low-order operator jets
are used wherever sufficient, annihilation powers are streamed, diagonal jets
are contracted without dense temporaries, and all physical arithmetic stays
float64 with `fastmath=False`. The correction-only particle caps are unchanged.

Read `PERFORMANCE.md` for measured speed and memory, and `docs/ALGORITHM.md` for
the algebra and its scope. Local validation is not a cluster benchmark.

## Directory map

| Directory/file | Purpose |
|---|---|
| `lri_eh/numerics.py` | Direct-response correction solver, degrees 4--7 |
| `lri_eh/_core/` | Isolated copy of the retained ranked basis/operator kernels; not installed as `lri_hpc` |
| `lri_eh/runtime.py`, `runner.py` | Validation, checksums, exclusive claims, atomic outputs, scalar checkpoints and bounded attempts |
| `lri_eh/planner.py`, `campaign.py` | Exact state/edge planning and fresh-process per-node lanes |
| `lri_eh/finite_shell.py` | Matrix-free finite-parent Schur validation/research tool |
| `lri_eh/exact.py` | Independent exact/float evaluation of delta C4 |
| `scripts/validate_release.py` | Runs tests plus gated smoke, then issues a source/dependency-bound receipt |
| `scripts/create_manifest.py` | Requires receipt; balances cutoff items into homogeneous lanes |
| `scripts/join_campaign.py` | Strict join to expanded, gated raw JSON; refuses double application/missing cutoffs |
| `slurm/` | Generic validation and lane templates; supply current account, partition and resources |
| `tests/` | Numeric, full-recursion, matrix-free, restart, provenance, locking, gate, and int64 tests |
| `reference/original/` | Unmodified incoming addon/core and independent SciPy oracle needed by tests |
| `data/reference_corrections.json` | Retained incoming numerical differences used for comparison |
| `benchmarks/` | Portable benchmark drivers and retained local measurements/validation |
| `docs/ALGORITHM.md`, `docs/INTEGRATION.md` | Derivation, limits, deployment checklist |
| `requirements-tested.txt` | Exact locally tested dependencies (Python 3.13.5) |
| `MANIFEST_SHA256.json` | Archive integrity manifest; generated caches/temp files are excluded |

## Installation and validation

Linux/POSIX is required by the `flock` claim implementation. Python >=3.10 with
compatible NumPy and Numba is required. SciPy/pytest are needed for validation;
SymPy is included in the validation extra for future analytic checks.

```bash
cd lri_eh_hpc
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[validation]'
# Or, on Python 3.13, install requirements-tested.txt before the editable install.
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
export NUMBA_CACHE_DIR="${TMPDIR:-/tmp}/lri-eh-numba-$USER"
mkdir -p "$NUMBA_CACHE_DIR" logs validation
python scripts/validate_release.py --threads 4 --output validation/local.json
```

The validation suite needs at least four available CPUs because it explicitly
compares one- and four-thread results. Do not use the supplied local receipt as a
substitute for validation in the actual target environment. Changing source or
Python/NumPy/Numba/llvmlite versions invalidates receipts and old checkpoints.

The package is self-contained for tests. No conversation files, raw HPC results,
external repository paths, or hidden environment variables are needed.

## Run one correction item

```bash
python -m lri_eh plan --degree 7 --cutoffs 50 60 80 100 118 \
    --memory-limit-gib 192
python -m lri_eh run --degree 7 --cutoff 60 --threads 4 \
    --memory-limit-gib 4 --output-dir runs/corrections --resume
```

Outputs are under `runs/corrections/{accepted,checkpoints,claims,attempts,events}/`.
When all four reference components are already checkpointed, restart performs only scalar extraction and does **not** rebuild the basis. `seconds` records the current attempt, not total campaign core-hours; use scheduler accounting for total cost.

The solver exports `delta_C`, `delta_r`, and `delta_g`, not incomplete raw spectra
from its smaller paired-difference basis. All four gaps are retuned in the
response calculation. No high-order physical target enters.

`--memory-limit-gib` is a guard against a conservative allocation estimate, not an
OS memory reservation. The Slurm request must cover it. The planner now counts
edges exactly and uses a response-specific vector envelope, instead of the old
coarse 100-vector/oversized-edge estimate. Validate actual RSS at progressively
larger cutoffs on the target node. Do not extrapolate four-core timings to 64 cores.

For repeated small tasks, `python -m lri_eh warmup --threads 4` compiles all
supported degrees and both edge-index-width signatures into the selected cache.
The numerical work in `benchmarks/` is timed after warmup; cold compilation is
reported separately. Node-local caches avoid excessive shared-filesystem traffic.

## Run across nodes with Slurm lanes

This release uses **one threaded process per cutoff item**, with independent
items assigned to lanes/job arrays across nodes. It does not offer validated
single-cutoff MPI or GPU execution. The retained `_core` has historical MPI
utilities, but they are not enabled by the new correction entry point. The
runner rejects a multi-rank launch rather than replicate huge allocations silently.

First run the validation job on the target cluster:

```bash
export EH_ROOT="$PWD"
mkdir -p logs validation
sbatch --account="$ACCOUNT" --partition="$VALIDATION_PARTITION" \
    slurm/validate.sbatch
# After it passes, use the actual receipt validation/<job-id>.json below.
```

Create a campaign only after the target validation passes and resources have been
calibrated. This example covers the original campaign's 52--118 thermal grid;
192 GiB is a planner envelope for this correction, NOT a measured Expanse RSS.

```bash
python scripts/create_manifest.py --degree 7 --cutoffs $(seq 52 2 118) \
    --lanes 2 --threads 32 --memory-limit-gib 192 \
    --validation-receipt validation/ACTUAL_VALIDATION_JOB.json \
    --output-dir runs/eh_d7 --manifest campaign.json
export EH_MANIFEST="$PWD/campaign.json"
sbatch --account="$ACCOUNT" --partition="$PARTITION" \
    --cpus-per-task=32 --mem=192G --time=04:00:00 \
    --array=0-1%2 slurm/lane.sbatch
```

Account, partition, allocation expiry, QOS and wall time are deliberately not
hard-coded. A homogeneous Slurm array must use the same CPU/memory settings for
all its lanes. Separate low-memory and high-memory groups into different manifests
if a common request would waste resources. The scheduler script checks that its
allocation covers the manifest; it binds a single job step to the allocated CPUs.

Every item is a fresh process, so allocator/JIT state from previous cutoffs does
not accumulate indefinitely. Each solver—not only its supervisor—holds its flock
claim for the whole item. A killed supervisor does not permit a duplicate solver.

## Restart, acceptance and failure semantics

* Before publishing, reusing, or exporting a result, require finite, correctly
  sized arrays; unchanged coefficients through order three; C2 shell residual
  <=1e-10; response/raw-low-order tuning residuals <=1e-6; and independent delta C4
  residual <=1e-10. Gates recompute delta C4 rather than trusting a stored residual.
* Results/checkpoints are sealed with a payload SHA-256 and tied to the source,
  numerical prescription, cutoff, degree, and dependency versions. A checksum is
  an integrity check, not cryptographic authentication against a malicious writer.
* Writes use same-directory atomic rename with file and directory fsync. Claims
  are never unlinked/recreated while workers might be running. Confirm flock and
  rename semantics on the actual shared filesystem before production.
* Small scalar checkpoints are saved after calibration and each reference-state
  contribution. Completed references are reused; dense wavefunctions are not
  written to shared storage. Work in the interrupted phase must be recomputed.
* SIGTERM/SIGINT/SIGUSR1 request a stop at a safe checkpoint boundary. A compiled
  kernel must return before Python can handle the signal; a warning is not a
  guarantee that a long phase completes before wall time. SIGKILL/node failure
  loses that phase but leaves the last completed atomic checkpoint.
* Exit 73 means a live claim, 75 means a checkpointed interruption, and 65 means
  an acceptance/provenance failure. Other exceptions are nonzero failures. The
  lane stops on failure (except a busy claimed item); it never fabricates success.
* There is no automatic infinite retry loop. At most three attempts/item are
  permitted by default, persisted even across node death. Deterministic errors
  block automatic reuse. Inspect events before explicitly increasing the budget or
  moving to a new reviewed source/output directory. A warning exit requires
  resubmission of the same manifest; `--requeue` only requests Slurm support for
  scheduler-managed requeue cases such as eligible node failures.

## Export and attach corrections to the reviewed campaign

```bash
SRC=$(python -m lri_eh source)
python -m lri_eh export --expected-source "$SRC" \
    --inputs runs/eh_d7/accepted/*.json --output vacuum_corrections_d7.json
python scripts/join_campaign.py \
    --raw /path/to/analysis/extended/thermal_new.json \
    --corrections vacuum_corrections_d7.json --degree 7 \
    --expected-raw-source c0c30783db5d \
    --expected-correction-source "$SRC" --output thermal_partial_vacuum.json
```

Use the actual reviewed raw fingerprint; the prefix above is from the supplied
campaign report, not the new addon fingerprint. The raw JSON must retain source
and tuning diagnostics. Compact CSVs cannot establish these gates. Missing fields
are reported, never inferred from a filename or reconstructed from a fit summary.

The bridge refuses missing/duplicate cutoffs, insufficient degrees, nonfinite
input, wrong source, failed gates, and already corrected data. With `--degree 5`,
C6/C7 are omitted rather than silently left uncorrected. Output is labelled
**PARTIAL** matching. A degree-seven campaign update needs a degree-seven correction
at every requested cutoff. No missing correction is interpolated.

## Reproduce the measurements and finite-parent tests

```bash
python benchmarks/bench_item.py --backend new --cutoff 50 --degree 7 \
    --threads 4 --memory-limit-gib 4 --output /tmp/eh_new50.json --profile
python benchmarks/bench_item.py --backend old --cutoff 50 --degree 7 \
    --threads 4 --memory-limit-gib 4 --output /tmp/eh_old50.json --profile
python benchmarks/run_local.py       # skips already retained benchmark files
python benchmarks/summarize.py
python research/run_finite_shell.py --low 16 --parent 32 --degree 7 \
    --threads 4 --memory-limit-gib 3 --output /tmp/shell_16_32.json
```

For fresh repeated benchmarks, move `benchmarks/results/` aside first. The incoming
old solver is retained unchanged in `reference/original/` and is never used as a
production replacement for your reviewed campaign repository.

The matrix-free finite-shell tool reproduces the energy-dependent Schur recursion
for selected reference states. It retains the full finite parent basis, but never
forms parent-squared dense Hamiltonians. The dense original remains the small
validation oracle. This is not yet a scalable analytic infinite-shell correction,
not a source of tighter physical C6/C7 error bars, and not an MPI matching backend.

## Scientific limitation

The isolated vacuum correction includes `delta C4 ~ log(Lambda)/17496 + ...`.
The missing connected/folded matching terms are still needed. Faster and more
accurate evaluation of this one contribution must not be presented as a completed
physical effective Hamiltonian or as a vanishing-tail continuum extrapolation.
