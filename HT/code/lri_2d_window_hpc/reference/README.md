# 2D dressed phi4 Hamiltonian truncation with a full-vacuum window

This is a direct, finite-Delta_sigma **2D research port** of the agreed numerical
setup: dressed zero mode, circle bath with total mode-level cutoff, a consistent
full-vacuum window, and optional state-averaged local functions. Standard
ARPACK/dense eigensolvers are retained. No selected interacting-tail solver,
extra energy scale, kinetic-moment fit, or individual-mode UV parent is used.

Read `REPORT.md` for the results and `docs/METHOD.md` for the equations, normalization,
regulator definition, Jacobian, and limitations. The window is tested as a finite
prescription, not asserted to be a complete effective Hamiltonian in 2D.

## Directory map

```
code/ht2d/           circle basis, exact vertices, local basis, window and solver
code/run.py          one direct raw/window/optimized-basis calculation
code/diagnostics.py  untuned A, A^2, BA ancestry and angular spectra
code/campaign.py     main scan, individual jobs and failure journal
code/refine.py       independent larger-local and larger-bath checks
code/weak_check.py   direct weak-limit validation, without coefficient fitting
code/analyze.py      accepted outputs -> CSV tables and summary
code/plot.py         CSV tables -> three figures, no continuum fits
inputs/              previous 2D values and Newton initial guesses
results/             full accepted numerical JSONs and teacher basis artifacts
results/tables/      curve, raw replays, local refinements and candidate Ward gaps
figures/             new plots (PNG/SVG)
tests/               independent numerical checks and saved-output acceptance audit
validation/          actual test outputs, environment, attempt logs and provenance
upstream/            original 2D implementation, relevant original 1D templates/docs
```

## Dependencies and arithmetic

Python 3.10+, NumPy, SciPy, Numba, pytest, Matplotlib. The tested versions are in
`validation/environment.json`. All numerical Hamiltonian work uses float64.
There is no fast-math, amplitude pruning, fitted thermal target or polynomial
fit in epsilon. `n_z` always means states **per local parity**. Auxiliary oscillator
resolution is a separate numerical parameter. Every q power is projected independently.

```
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.mplconfig"
```

Thread counts here provide reproducible local runs, not an HPC scaling claim.
The old 1D symmetry scheduler/lease integration has NOT been generalized to 2D
in this release. Use a single writer per output and independent directories for
parallel jobs. A copied 1D validation receipt does not validate this new code.

## Quick independent validation and regeneration

Verify the distribution before running scripts which intentionally rewrite their
validation records or plots:

```
python tests/verify_manifest.py
python -m pytest tests/test_port.py -q
python tests/validate_saved.py
python code/analyze.py
python code/plot.py
```

These tests check the new projected bath construction against original full
vertices, explicit angular averaging, both numerical backends, Gaussian normal
ordering, raw spectra, dense vacuum fixed points, moving and fixed-span
Jacobians, density selection, window retuning, and rejected invalid settings.
They do not require a physical descendant defect to vanish.

## One direct calculation

The only tuning conditions are Delta_sigma=x and Delta_chi=2-x. Delta_E is the
first excited even scalar gap. Main physical scan: 1/8<x<1/2.

```
# Raw 2D calculation, unchanged physical normalization.
python code/run.py --L 8 --x .3 --nz 24 --osc 192 --window none \
  --output reproduced/raw_L8_x030.json

# Fully self-consistent window; learn a basis with no thermal density target.
python code/run.py --L 6 --x .3 --nz 24 --osc 192 --window vacuum \
  --train-keep 20 --output reproduced/teacher_x030.json

# Transfer the learned physical span to a larger bath; recompute all vacua and tune.
python code/run.py --L 10 --x .3 --nz 16 --window vacuum \
  --basis reproduced/teacher_x030.json --output reproduced/window_L10_x030.json
```

A keep20 artifact supplies nested 12-,16-,20-state local spaces. It cannot supply
24 states. A larger `--nz` in a teacher means retraining, not padding the smaller
isometry. The `osc` of a supplied artifact is authoritative; its physical scale
and primitive span are fixed during the solve. Basis reuse across x is rejected.

Each run computes first and second angular/mixed candidate descendants by default.
`--first-only` restricts diagnostics to J=1; `--no-diagnostics` skips them and must
not be counted as a full-spectral check. These options do not change the tuned
Hamiltonian. An eigenstate with low translation-image overlap is explicitly
flagged ambiguous. A strong-coupling BA image sometimes picks the primary itself;
its flagged -2 spacing error is not an identified descendant.

`--resume` only accepts a matching complete output and recorded source/configuration.
It is not a mid-Newton restart and does not implement cross-node claim leases.
Use a fresh output path when any code, artifact or physical setting changes.
Source hash fields in historical records include the supporting scripts present
when that job ran; numerical modules are separately inventoried in provenance.

## Recompute the complete release campaign

```
python code/campaign.py
python code/refine.py
python code/weak_check.py
python code/analyze.py
python code/plot.py
```

Run in a fresh working copy with the published result JSONs moved aside, or edit
only the output directory in a personal campaign copy. The campaign driver skips
existing named outputs rather than overwriting published records. Its invocation
journal records success/failure, commands, elapsed times and separate logs. Failed
jobs never enter summary tables. The refinement driver requires the accepted main
teacher artifacts and rejects missing dependencies. It also reproduces the
separately labelled alternate-root control. See REPORT.md before interpreting it.

The accepted new main grid uses x=.495,.475,.45,.4,.35,.3,.25,.2,.15,.126. At each x:

* L=6 teacher, 24 local states, auxiliary 192; learn up to 20 local functions.
* L=8 and L=10 window solves with 16 optimized functions.
* L=10 independent nested-size solve with 12 optimized functions.
* L=10 raw comparison with 24 local states and auxiliary 192.

Selected L=12 and independent 32/256 moving-local refinements test larger bath
spaces and the learned local representation. Their exact configurations and
accepted status are in each result JSON; the original/refinement/continuation logs
and `stopped_attempts.json` record the execution history. The first refinement
script is archived separately, and the current driver uses the documented
adjacent-cutoff continuation for the final near-endpoint curve. Recorded timings are not
serial HPC performance benchmarks; some jobs ran concurrently in this session.

## Important scientific distinctions

1. This is the total-level *window* prescription, not the previous factorizing-UV
   cubic effective Hamiltonian. Corrections from those studies must not be stacked
   onto these records without a new matching derivation.
2. The large local-basis precision measures numerical agreement at fixed model
   and cutoff. It is not a physical continuum uncertainty.
3. The former 2D C2 and C3 checks remain low-order benchmarks. The new window's
   finite-coupling calculation is not a new verification of physical C4-C6.
4. Full conformal families are not established by the two tuned primary gaps.
   Untuned angular and mixed tests remain visible, including failed assignments.
5. No physical continuum curve or fitted uncertainty band is claimed here.
