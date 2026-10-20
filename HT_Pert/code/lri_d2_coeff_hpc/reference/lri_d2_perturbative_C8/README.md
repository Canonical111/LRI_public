# 2D LRI thermal coefficients through C8

Direct perturbative coefficients for the Hamiltonian and total-bath-mode regulator
in the supplied `lri_2d_window_hpc_optimized.zip`. This is a separate coefficient
branch, not a modification of the uploaded finite-coupling solver or its dispatcher.

**Computed:** raw and consistent-window coefficients at every even L=0..20 through
epsilon^8; selected literal controls; independent exact-Fraction results at L=0,2,4,6;
and unexpanded validation against the actual uploaded solver. **Not computed:**
a controlled continuum C3..C8 limit, complete high-state counterterms, or a new
nonperturbative physical curve. See REPORT.md and docs/METHOD.md.

## Conventions

    epsilon = 2s-2 = 2-4 Delta_sigma
    Delta_E = 1-epsilon/6 + C2 epsilon^2 + ... + C8 epsilon^8
    e_ab = x+a+b, j_ab=a-b, u_ab^2=(x)_a (x)_b/(a! b!)
    H = N+xP + r average(:phi^2:) + g average(:phi^4:)/12 + D

The cutoff is N<=L. It is NOT the frozen 1D energy cutoff, and it is NOT an
individual-mode 2D parent. The two calibrated gaps are x and 2-x. No thermal
coefficient determines a coupling. Normal ordering precedes angular projection.
A perturbatively sufficient Gaussian local basis replaces the finite-coupling
moving/density-selected local basis; it is not a fitted Taylor series in epsilon.

## Layout

```
code/                 direct Taylor and independent Fraction engines; analysis
code/analytic_checks.py exact C2/vacuum sums and the first window correction
code/plot.py          regenerate plots from the coefficient CSV
results/coefficients/ direct floating-point records, including r,g and vacuum rows
results/exact/        independent rational C0..C8 records
results/envelope_replays/ unreduced-vs-reduced auxiliary-space comparisons
results/*.csv         coefficient, window-shift and support-check tables
results/*validation.json, test_run.json  independent test records
docs/METHOD.md        model, symmetry proof, recursion, analytic checks, limitations
inputs/               original source hashes and byte-level inventory
upstream/             unmodified uploaded 2D package, including its own tests/data
vendor_reference/     attributed 1D algorithm snapshots (not imported as 2D physics)
figures/              PNG and SVG plots generated from accepted records
```

The existing upstream numerical points and timings are historical inputs, not new
runs. New records are at the root `results/` only. Publication includes small
original benchmark logs needed by the upstream manifest; Python/Numba caches,
compiler objects, and incomplete execution logs are omitted. Failed development
attempts are summarized in `results/attempts.json`, not used as data points.

## Dependencies and numerical precision

Python 3.10+, NumPy, SciPy, Numba, mpmath, Matplotlib, pytest, threadpoolctl. The actual versions
used are in results/ENVIRONMENT.json. The new engines use no finite-difference
or polynomial fit to obtain coefficients. Main arrays are float64, as in the
uploaded code; some contractions use extended longdouble accumulation. A separate
Fraction implementation supplies exact small-cutoff coefficients.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=1
export MPLBACKEND=Agg
```

## Verify and regenerate

```bash
# Check immutable delivery BEFORE tests rewrite numerical validation records.
python tests/verify_manifest.py
python upstream/lri_2d_hpc_optimized/tests/verify_manifest.py

# Fresh exact, full-vs-half-order, symmetry, source-algebra and uploaded-solver checks.
python tests/run_all.py
python code/analytic_checks.py
python code/analyze.py
python code/plot.py
```

`run_all.py` recalculates exact records at L<=6 and twelve finite-epsilon spectra
using the unmodified source. It does NOT rerun the largest coefficient campaign
or every historical upstream benchmark. The retained validation reports specify
which checks were run. An additional 46 selected original tests (`test_port.py`,
`test_optimized.py`) passed in a disposable copy. Their four-thread comparison
requires `NUMBA_NUM_THREADS=4`; an initial one-thread-cap attempt failed that
environment check and is recorded in `upstream_selected_validation.json`.

## Recalculate direct coefficients

Use a new output directory to force fresh calculation. Existing filenames are
otherwise skipped. Each process owns its output filename; this research wrapper
is not a cross-node lease/claim system.

```bash
python code/circle_jets.py --cutoffs 0 2 4 6 8 10 12 14 16 18 \
  --degree 8 --scheme consistent --out reproduced/consistent
python code/circle_jets.py --cutoffs 0 2 4 6 8 10 12 14 16 18 \
  --degree 8 --scheme raw --out reproduced/raw

# L20 was separately resource-checked: approximately 2.7--2.8 GiB process peak locally.
python code/circle_jets.py --cutoffs 20 --degree 8 --scheme consistent \
  --max-states 2500000 --out reproduced/consistent
python code/circle_jets.py --cutoffs 20 --degree 8 --scheme raw \
  --max-states 2500000 --out reproduced/raw

# Independent order/support check (P<=15,Q<=12 rather than P<=19,Q<=16).
python code/circle_jets.py --cutoffs 20 --degree 7 --scheme consistent \
  --max-states 2500000 --out reproduced/degree7
```

L=0 is a local-only control. It is not a production nonperturbative input.
The default exact angular envelope and reflection reduction can be disabled with
`--no-envelope` and `--no-reflection` for small validation runs. The envelope
N+|J|<=L concerns auxiliary ladder states, not a new physical scalar cutoff.
The ordinary (non-stationary) recursion is available as `--full-order`.

For the independent exact-coordinate oracle:

```bash
python code/exact_circle.py --cutoffs 0 2 4 6 --degree 8 \
  --schemes raw consistent literal --out reproduced/exact
```

Its basis is separately enumerated, uses no spatial-reflection or angular-envelope
reduction, and does not invoke circle_jets. The exact numbers are finite-cutoff
coefficients of the declared model, not continuum numbers.

## Output map

| Producer | Main outputs |
|---|---|
| `circle_jets.py` | `results/coefficients/<scheme>_L<L>_d<degree>.json` |
| `exact_circle.py` | `results/exact/<scheme>_L<L>_d<degree>.json`, including rational coefficients |
| `analytic_checks.py` | `results/analytic_checks.json` |
| `analyze.py` | `coefficients_C0_C8.csv`, `window_shifts.csv`, `degree_support_checks.csv`, `SUMMARY.json` |
| `test_coefficients.py` | `coefficient_validation.json` |
| `test_finite_uploaded.py` | `finite_uploaded_validation.json` |
| `test_local_algebra.py` | `local_algebra_validation.json` |
| `plot.py` | `figures/C8_cutoff.*`, `figures/window_changes.*`, `figures/C2_control.*` |

All scripts are run from the bundle root unless an absolute path is supplied.
No table of physical C6,C7,C8 is required. No external download is needed beyond
installing dependencies. Changing an output prefix does not change the model.

## Next scientific step

The large coefficient changes between L16,L18,L20 are UV/systematic effects,
not numerical uncertainty. The uploaded scalar window is not a proof of complete
connected matching. Its exact fourth-order difference itself has a growing
linear term and a logarithm; raw and window pieces must be treated in one scheme.
The 1D asymptotic coefficients cannot be reused. Use these complete finite 2D
arrays and exact small-cutoff checks as the reference for a separately derived
2D high-state matching and cutoff-extrapolation study.
