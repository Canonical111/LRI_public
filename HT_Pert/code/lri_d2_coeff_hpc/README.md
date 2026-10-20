# Optimized direct 2D LRI coefficients through C8

This package optimizes the **coefficient solver** in the supplied
`lri_2d_C8_perturbative_check.zip`. It does not alter the raw, consistent-window or
literal Hamiltonian prescriptions, the two primary tuning conditions, or the
floating-point precision. It is NOT the nonperturbative curve dispatcher.

Read `REPORT.md` for measured performance and numerical comparisons;
`docs/METHOD.md` for the exact graph/moment reorganizations and limitations.
The optimized program retains scalar angular momentum, reflection, all allowed
intermediate angular sectors, and the coefficient-specific particle support.

## Contents

| Path | Purpose |
|---|---|
| `src/lri_coeff/basis.py` | Exact charge-bounded enumeration, rank/graph, state/edge/memory planning |
| `src/lri_coeff/operators.py` | Complete normal-order vertices; annihilation-only moment identities |
| `src/lri_coeff/native.cpp`, `native.py` | Threaded fused jets, extended deterministic scalar reductions |
| `src/lri_coeff/kernels.py` | Independent Numba backend |
| `src/lri_coeff/engine.py` | Direct Taylor tuning and full consistent-window recursion |
| `src/lri_coeff/storage.py`, `cli.py` | Checked graphs/results, atomic ownership and checkpoint/resume |
| `scripts/` | Campaign generation, task execution, benchmark reproduction, result collection; cluster submission (`submit.py`), release (`make_release.py`), validation (`validate_cluster.py`) |
| `cluster/` | Expanse/symmetry job script, site environment, signal forwarding, venv setup (see `docs/CLUSTER.md`) |
| `tests/` | Numerical, precision, symmetry, cache and interruption checks |
| `results/` | Fresh benchmark/validation records and any completed larger-cutoff pilots |
| `reference/lri_d2_perturbative_C8/` | Unchanged supplied coefficient/source/oracle package and original data |
| `docs/PROVENANCE.json` | Original ZIP SHA-256 |

## Install

Python 3.10+ with compatible NumPy, SciPy and Numba versions. For the main native
backend, a C++17 compiler with OpenMP and extended long double is required. No
binary, unsafe fast-math flag or architecture-specific `-march=native` is shipped.
A new binary is compiled into a writable content-addressed cache on first use.
The local validation environment is recorded in `results/ENVIRONMENT.json` and
`requirements-tested.txt`. The latter pins this local package set; it is not a
claim that those exact wheels support every cluster Python installation.

```bash
python -m pip install -e '.[validation]'
# Alternatively, without installing this source tree:
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
export OMP_NUM_THREADS=4
export OMP_WAIT_POLICY=PASSIVE
# On an immutable release, choose writable caches explicitly.
export NUMBA_CACHE_DIR="${TMPDIR:-/tmp}/lri_numba_$USER"
export LRI_COEFF_NATIVE_CACHE="${TMPDIR:-/tmp}/lri_native_$USER"
```

`--threads` configures the CLI before numerical libraries initialize. In an
already-running Python process set the Numba ceiling before import. `--backend
numba` avoids the C++ dependency; it is a checked alternative, not the primary
performance result. Neither backend supports lower-than-reference precision.

## Validate first

```bash
python tests/verify_manifest.py             # before regenerating any outputs
python tests/run_all.py                 # separate native/JIT warmup, then tests
```

The retained reference package has its own tests and file manifest. New tests
compare against it; its existing cluster receipts do not validate this new
coefficient branch. The original exact-Fraction oracle can also be rerun via
`reference/lri_d2_perturbative_C8/code/exact_circle.py --help`.

## Plan before allocation

```bash
python -m lri_coeff plan --cutoffs 16 18 20 22 24 28 --degree 8 \
  --output resource_plan.json
```

Counts are exact; the live-array estimate includes a safety factor but is not a
measured peak on every platform. Do not lower particle support or numerical
precision to make a job pass the guard. Reassess larger-cutoff memory on the target
node. `--max-states` and `--memory-gib` must both allow the calculation.

## A coefficient calculation

```bash
python -m lri_coeff run --cutoff 20 --degree 8 --scheme consistent \
  --threads 4 --memory-gib 4 --max-states 3000000 \
  --cache work/graphs --checkpoint work/checkpoints --resume \
  --output work/consistent_L20_d8.json

python -m lri_coeff run --cutoff 20 --degree 8 --scheme raw \
  --threads 4 --memory-gib 4 --max-states 3000000 \
  --cache work/graphs --checkpoint work/checkpoints --resume \
  --output work/raw_L20_d8.json
```

The two jobs can reuse the same immutable graph but never mix vacuum tables or
coefficient outputs. `--full-order` is a more expensive independent check at small
L. `--pmax` can only increase the proven support. Reflection/envelope ablations
remain available in the original reference engine, not hidden as new regulators.

A verified same-identity output is skipped; an invalid or different-identity file
is refused. Results are checksummed envelopes. Numerical arrays are under
`payload.result`: `C`, `r`, `g`, `energies`, `vacuum_coefficients`. Execution
metadata reports actual threads, elapsed seconds, RSS, cache use and resume state.

## Checkpoint and recovery

`--checkpoint-seconds` defaults to 300. Checkpoints are written at complete wave,
moment or quotient boundaries, and immediately at the next boundary after
SIGUSR1, SIGTERM or SIGINT. Exit 75 means a safe stop; repeat the SAME command
with `--resume`. Thread count may change. Source, backend, degree, scheme or
runtime-version changes do not silently reuse an old checkpoint.

If a process is killed before releasing `OUTPUT.json.lock`, the next writer exits
73. **No automatic stale-lock stealing is implemented.** Read `owner.json`, verify
on the cluster that the owning job/process has actually terminated, and only then
remove that particular claim. Unknown ownership should be treated as live. The
previous complete checkpoint remains available after a hard kill.

Do not modify graph-cache arrays. They are checksummed before memory-mapped reuse.
A corrupt cache is rejected; remove/rebuild it only when no job is using it.

## Multiple nodes: Expanse and symmetry

`docs/CLUSTER.md` is the runbook. In short: build a release tar from a clean commit, validate it on a
compute node of the chosen cluster, then submit one job per task:

```bash
python scripts/make_release.py --out dist/                      # local; copy to $LRI_COEFF_DATA/releases/
LRI_COEFF_SITE=expanse source cluster/site.sh                   # login node, in the unpacked release
python scripts/submit.py validate --release $LRI_COEFF_DATA/releases/<release>.tar --submit
python scripts/make_campaign.py --cutoffs 24 26 28 30 --schemes raw consistent \
  --output-root $LRI_COEFF_DATA/campaigns/c1 --manifest $LRI_COEFF_DATA/campaigns/c1/campaign.json
python scripts/submit.py campaign --release $LRI_COEFF_DATA/releases/<release>.tar \
  --manifest $LRI_COEFF_DATA/campaigns/c1/campaign.json          # dry run; add --submit
```

Each job requests the memory of its own task, stages the checksummed release on node-local disk, and uses
all physical cores of its allocation. Rerunning the same `submit.py campaign` command skips finished tasks
and resumes interrupted ones from their checkpoints.

**Multi-node scaling here is across independent cutoff/scheme/order jobs.** The
native sparse products parallelize within one node; a single cutoff still has to
fit that node. There is no tested MPI/domain-decomposed single-cutoff solver and
no claimed many-node benchmark. The source's nonperturbative campaign format is
explicitly rejected by the new coefficient task runner.

## Reproduce measurements and collect outputs

```bash
python scripts/run_benchmarks.py
python scripts/analyze_results.py
python scripts/plot_benchmarks.py
python scripts/collect.py --inputs work/consistent_L20_d8.json \
  work/raw_L20_d8.json --output work/coefficients.csv
```

Benchmarks are sequential, separate-process repetitions; compiled kernels warm
before the timed full coefficient solve. Warmup and memory are recorded. They
include graph construction, primary tuning, and every sub-cutoff vacuum solve.
No microbenchmark speedup is used as a full-run speedup.

Numerical tolerances are not continuum uncertainties. This package does not fit
the cutoff tails, repair uncomputed connected matching, or change any quoted
physical continuum coefficient.
