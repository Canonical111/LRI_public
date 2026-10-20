# Optimized local basis: integration candidate 1.1.0rc1

## Decision and scope

This adds a **saved, state-averaged local basis** to the supplied `e2ca07c` HPC
solver. It does not change the production vacuum-window model. The new path is
opt-in through `--local-basis`; without that option the original numerical
`DressedSolver`, `LocalProblem`, kernels, bath operators and window equations are
used. Raw, literal-window and consistent-window legacy commands remain available.
The new density path is deliberately restricted to `vacuum:consistent`, with one
exact Delta_sigma per item. Cross-delta basis transfer is rejected in this release.

The consistent window is evaluated by the existing finite-coupling fixed point,
not by an epsilon^5 polynomial. Its physical completeness is **not** asserted.
The individual-mode parent, midpoint profile, common energy rescaling, fitted
kinetic moment and experimental Schur corrections are **not** integrated here.

This is prepared for **new validation on symmetry**, not already validated on
that cluster. See `validation/basis_integration/` and `VALIDATION_BASIS.md` for the
actual local evidence and boundaries. Do not reuse the old validation receipt.

## Installation / review

Use a new checkout or extraction. Do not overwrite a live read-only installation
or an existing campaign. The full ZIP is the ready-to-validate distribution.
The accompanying review patch contains source, scripts, tests, documentation and
pinned reference source; it deliberately omits this run's numerical evidence and
the ZIP distribution manifest. After applying only the patch, the old
`MANIFEST.sha256` still describes the old distribution and must not be presented
as a validation of the new code. Use pytest and the staged release checks, then
publish the newly reviewed commit through the existing immutable-install workflow.
The manifest-verification command below applies to the complete ZIP. The accompanying patch applies to the supplied source
content at `e2ca07c`; two pinned source snapshots under `reference/` are used only
as independent regression oracles. No `.git` history or compiled binary is needed.

```bash
python -m pip install -e '.[validation]'
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
python scripts/verify_manifest.py
python -m pytest -q
```

Run the complete staged validation with external writable outputs:

```bash
python scripts/validate_release.py \
  --baseline "$PWD/reference/production_e637dfd" \
  --threads 1 --output "$PWD/runs/validation/receipt.json" \
  --workdir "$PWD/runs/validation/stages"
```

All six stages must pass: the entire test suite, saved seeds, the original pinned
raw baseline, calibration smoke, a new pinned e2ca07c raw/consistent/literal
comparison, and the optimized-basis end-to-end check. Skipping a stage can never
produce a passing receipt. The receipt binds source, execution/validation scripts,
reference source files, dependencies and runtime. Old receipts become stale.

On symmetry, commit the reviewed patch under a NEW revision and use the existing
freeze/install workflow. Site configuration in `cluster/symmetry/` is inherited
from the uploaded source and has not been rechecked remotely by this integration.

```bash
# Set CODE to the new immutable installation, not the old production revision.
CODE="$HOME/lri_dressed/code/<new-reviewed-commit>"
source "$CODE/cluster/symmetry/env.sh"
export LRI_CODE_DIR="$CODE"
export LRI_BASELINE="$CODE/reference/production_e637dfd"
mkdir -p <SCRATCH>/lri_dressed/logs
sbatch --export=ALL "$CODE/cluster/symmetry/validate.sbatch"
```

The local receipt shipped as evidence is **not a symmetry validation receipt**.
Set `LRI_RECEIPT` to the successful new on-cluster receipt before the next phases,
for example `export LRI_RECEIPT="$LRI_ROOT/validation/<new-validation-job>/receipt.json"`.
Replace the angle-bracket placeholders with actual reviewed commit/job identifiers.

## Phase 1: train and freeze the bases separately

Training uses only the top vacuum, sigma, shadow, and every lower-cutoff vacuum.
The local span is fixed during each inner coupling solve. An outer loop updates
it; all changed-coupling windows are recalculated. Thermal data never determine
weights, basis vectors, or stopping criteria. The inner solver may compute thermal
levels as unused outputs; the density-selection routine itself never requests them.

A direct single-process example (no scheduler required):

```bash
python -m lri_dressed train-basis \
  --bath-cut 16 --delta .025 --teacher-nz 48 --keep 24 --osc 384 \
  --backend ladder --threads 1 \
  --seed inputs/N16_z24_o192_d0.02500000.json \
  --output runs/bases/x0025.json --memory-limit-gib 8 --resume
```

One artifact with `keep=24` also supplies a nested `--nz 16` span. It does NOT
allow `--nz 32`; train a separate larger artifact for that test. A new teacher
or auxiliary size requires new training. No fixed value of 16 or 24 is assumed
sufficient throughout the campaign.

For the proposed initial grid, generate a request on the target runtime:

```bash
python scripts/make_basis_training.py \
  --deltas .24 .1 .05 .025 .01 --bath-cut 16 \
  --teacher-nz 48 --keep 24 --osc 384 --threads 1 --backend ladder \
  --basis-dir "$LRI_ROOT/bases/basis_pilot_v1" \
  --out "$LRI_ROOT/bases/basis_pilot_v1_request.json" --memory-limit-gib 8

export LRI_BASIS_MANIFEST="$LRI_ROOT/bases/basis_pilot_v1_request.json"
# LRI_CODE_DIR and LRI_RECEIPT refer to the newly validated installation.
sbatch --array=0-4 --export=ALL \
  --output="$LRI_ROOT/logs/basis_%A_%a.out" \
  "$CODE/cluster/symmetry/train_basis.sbatch"
```

The five-point grid is proposed, not cluster-validated here. Existing scalar
couplings are starting guesses only. The request freezes their values, so a later
edit to a seed file cannot change a pending training job. The `.sbatch` resource
requests are starting allocations, not timing/RSS predictions. Increase the
allocation after calibration where necessary; no numerical cap is auto-reduced.

Training writes a checksummed `local-basis` envelope, a safe-boundary checkpoint,
and a claim/lease beside it. A partial artifact is never published as accepted.
`--resume` either restores the candidate span and Newton state, finalizes a
complete checkpoint, or reuses an identical accepted artifact. SIGUSR1/TERM/INT
are honoured at selection/Newton/publication boundaries, not inside LAPACK or a
long window eigensolve. Allow enough warning time. Exit 73 means owned elsewhere;
75 means checkpointed stop. Do not manually delete live leases.

## Phase 2: index, calibrate and run the fixed bases

After training, freeze an index using ONLY final basis files, not checkpoint or
failure JSONs. The generated filenames begin with `x` and end with the request
configuration digest. They do not have a `.checkpoint.json` suffix.

```bash
# Explicitly list the five FINAL artifact paths reported by the training jobs.
python scripts/index_bases.py --files /path/to/final_x024.json /path/to/final_x010.json \
  /path/to/final_x005.json /path/to/final_x0025.json /path/to/final_x001.json \
  --output "$LRI_ROOT/bases/basis_pilot_v1_index.json"
```

Do not use a broad `*.json` glob that includes checkpoints. The index is
checksummed and versioned; duplicate delta entries and overwritten indices are
rejected. Artifacts are bound to exact delta, source and dependency runtime;
cutoff transfer is explicit and allowed, but has no automatic accuracy guarantee.

A single point:

```bash
python -m lri_dressed run --bath-cut 24 --deltas .025 --nz 16 --osc 384 \
  --window vacuum --window-mode consistent --backend ladder --threads 1 \
  --local-basis /path/to/final_x0025.json \
  --output-dir runs/basis_point --memory-limit-gib 8 --resume
```

The artifact's final theta is used when no seed/guess is supplied. There is no
implicit cross-delta continuation for this path. The result embeds the full
artifact, so later `identities --result ...` can reproduce the span even when the
original basis file is relocated. No old eigenvector or vacuum table is reused
across incompatible bases.

Calibrate complete point solves using the new representation:

```bash
python scripts/calibrate.py --cuts 24 28 --nz 16 --osc 384 \
  --deltas .1 .05 .025 .01 --windows vacuum:consistent --backends ladder \
  --threads 1 --concurrent 1 \
  --basis-index "$LRI_ROOT/bases/basis_pilot_v1_index.json" \
  --workdir "$LRI_ROOT/calibration/basis_k16_v1" \
  --output "$LRI_ROOT/calibration/basis_k16_v1.json"
```

This measures full CLI setup and fixed-basis solves. Training has a separate cost
in the artifacts. Report both costs; a threefold vector-size reduction is not a
threefold end-to-end speedup. Old energy-basis calibration is not reused for a
density-basis item. Initially use a small calibration allocation, not all nodes.

Freeze and submit the overlap campaign through the existing node-packing layer:

```bash
python scripts/make_campaign.py --pack --campaign density16_overlap_v1 \
  --bath-cuts 24 28 --nz 16 --osc 384 --deltas .1 .05 .025 .01 \
  --windows vacuum:consistent --split points --backend ladder --threads 1 \
  --basis-index "$LRI_ROOT/bases/basis_pilot_v1_index.json" \
  --calibration "$LRI_ROOT/calibration/basis_k16_v1.json" \
  --out "$LRI_ROOT/campaigns/density16_overlap_v1/manifest.json"

python cluster/symmetry/submit.py \
  --campaign "$LRI_ROOT/campaigns/density16_overlap_v1" \
  --receipt "$LRI_RECEIPT" --nodes 1 --time 15:30:00
```

Repeat with `--nz 24` and its OWN calibration/manifest. A calibration mismatch
fails rather than silently adopting old timings. For uncalibrated pilot items,
explicit `--mem-gib`/`--est-seconds` reservations are supported by the inherited
manifest generator; they must not be represented as measured resources.

## Phase 3: local convergence first, then extend the bath

Compare 16 and 24 optimized states with selected original 48/56-state solves at
the SAME delta, total-level cutoff, auxiliary size and window prescription. Use
the unchanged original path by simply omitting `--local-basis`. Those references
are finite models, not the physical answer. Also compare low gaps and overlap
assignments, not only the thermal primary.

```bash
python scripts/audit_basis_convergence.py \
  --input-dirs /path/to/density16/results /path/to/density24/results /path/to/reference/results \
  --thermal-tol 1e-6 --gap-tol 1e-5 --output runs/local_convergence.json

python -m lri_dressed identities --result /path/to/result.json \
  --k 12 --threads 1 --output runs/identities.json
```

The audit refuses missing larger-original references. Its tolerances are a
proposed local-error budget, not continuum uncertainties. Use tighter checks at
the weak end. Only after the overlap and cost tests pass should L=32,36,40 be
scheduled selectively. Retrain/enlarge the artifact if local differences grow.
Do not rerun all 678 old campaign points simply because the implementation changed.
Keep the physical model's remaining descendant defects visible.

## Safety and output changes

* With no basis option, old numerical arrays remain unchanged in the checked
  pinned regressions. Numerical fingerprints necessarily change in this release.
  Old results remain readable as provenance/initial guesses; old checkpoints and
  completion records do not certify the new source or new basis.
* Density result configuration includes the artifact checksum. Pack item digests,
  expected CLI checksums, checkpoints, and completion validation bind it too.
  Editing/replacing a basis after freezing the campaign makes pending work fail
  closed, not silently run another Hamiltonian subspace.
* The original `lease.py` and `pack_node.py` shutdown/liveness implementation is
  preserved. The new training path uses the same solver-owned claim/lease primitive.
  No MPI, GPU, untested physics, or automatic precision/cap reduction is introduced.
* Primitive scale and U are fixed during inner solves. The HF/window Jacobian
  retains off-diagonal local density. q^j and a0 are projected separately.
  `local_retained_edge_weights` describes high local ENERGIES inside the span,
  not the discarded density weight; both notions are labelled in the output.
* `local_auxiliary_residual` on the density path is an eigensolve residual inside
  the fixed span. It is not an omitted-span error estimator.

## Files to review

`src/lri_dressed/density.py` contains the new numerical path;
`local_basis.py` the artifact/compatibility rules; `basis_training.py` the outer
training/restart driver. CLI, pack identity, manifests, calibration, staged
validation and descendant diagnostics have small conditional integration changes.
`solver.py`, `local.py`, `window.py`, `basis.py`, `operators.py`, `kernels.py`,
`lease.py`, and the packing launcher's safety machinery retain their uploaded bytes.

The root README and original reports remain historical source documentation;
this file and `docs/DENSITY_BASIS.md` describe the new option.
