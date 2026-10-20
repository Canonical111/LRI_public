# Full 1D coefficient cutoff flow, not another partial response block

This continuation computes the complete specified Dconn C2..C8 at all even
cutoffs 2..44, freezes old-data forecasts before generating the new high-order
points, and tests a separate full-leading-polynomial extraction attempt.

**The analytic large-Lambda leading polynomials of the full C6,C7,C8 are NOT
completed.** The new full coefficients, model forecast errors, and unsuccessful
free-tail extraction are published without claiming otherwise. The exact
half-order quotient changes numerical storage, not the Hamiltonian/model.

## Layout

```
code/ragged_quotient.py       exact half-order Dconn/raw recursion
code/freeze_forecasts.py     forecasts using ONLY the old input data
code/check_forecasts.py      test the frozen predictions on new data
code/leading_polynomial_probe.py  exploratory all-leading-log fits, no targets
code/analyze.py              consolidated tables and validation audit
code/plot.py                 plots from accepted numerical records
code/large_checks.py         independent-process largest-cutoff controls
vendor/                     unmodified ordinary, rational, and fit references
inputs/                     prior same-scheme finite data, gap inputs, protocol
results/new_coefficients/   completed direct coefficient records
results/                    all forecasts, extraction attempts, tests, tables
provenance/                 source hashes and experiment boundaries
```

No old thermal continuum C4..C8 value is supplied to either solver or fit.
The linked forecasts explicitly use analytic C2,C3 and separately determined
gap exponents as controls. They therefore do not independently measure those
inputs. The source reference values were visible historically; this is not
claimed blind research.

The series is epsilon=2s-1 about Delta_sigma=1/4, with a frozen free-energy
cutoff N+P/4<=Lambda and half-integer vacuum subproblems. Do not mix these records
with the dressed product-cutoff, individual-mode, or short-range-end series.

## Dependencies and precision

Python 3.10+, NumPy, SciPy, mpmath, Matplotlib. The reference and new coefficient
calculations use float64 matrix/vector arithmetic; selected scalar reductions
accumulate in longdouble. There is no lower-precision approximation or pruning.
Forecast fits use 70 digits and the unrestricted polynomial probes 80 digits.
Versions used locally are recorded in provenance/ENVIRONMENT.json.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.mplconfig"
```

## Verify and reproduce

Verify the archive before scripts overwrite timing/validation records:

```bash
python tests/verify_manifest.py
python tests/run_all.py
python code/check_forecasts.py
python code/leading_polynomial_probe.py
python code/analyze.py
python code/plot.py
```

For a small fresh calculation:

```bash
python code/ragged_quotient.py --cutoffs 2 4 8 12 16 24 --degree 8 --scheme dconn --out reproduced/small
```

For the complete new range, use independent processes for the largest points
so memory does not accumulate across runs:

```bash
for L in 26 28 30 32 34 36 38 40 42 44; do
  python code/ragged_quotient.py --cutoffs "$L" --degree 8 --batch 1 --out reproduced/new
 done
```

The new L=44 Dconn calculation completed locally in about 144 seconds with peak
process RSS about 2.39 GiB. Those are observed local figures, not HPC calibration
or guaranteed resource requirements. Larger than the 2.3-million-state guard
is intentionally rejected. The code is not a replacement for the production
cluster dispatcher or a separately reviewed MPI implementation.

To reproduce the old-data forecasts without overwriting the frozen evidence,
copy the package, remove ONLY the forecast JSON and its hash from that copy,
and run `python code/freeze_forecasts.py`. The script otherwise refuses to
replace an existing forecast. It reads none of the new coefficient files.

## What the tables mean

- `whole_model_coefficients.csv`: complete finite-cutoff model coefficients.
- `full_shell_increments.csv`: whole coefficient differences between consecutive
  even cutoffs, not fitted contributions of individual diagrams.
- `forecast_validation.csv`: 416 new high-order prediction comparisons across
  all 16 frozen models; none was selected for proximity to a continuum target.
- `leading_polynomial_probes.csv/json`: all attempts to determine the whole
  proposed leading polynomial from new full-model increments. They do not give
  stable continuum intercepts; the fitted numbers are NOT analytic tails.
- `highest_log_only_sign_test.csv`: a limited sign check on a conditional
  highest-log-only approximation, not a claim about the necessary UV reach.

Some development attempts exhausted this environment's memory or execution
allowance. Only completed JSON records enter the results. The final successful
memory path uses ragged wavefunction storage and a sequential Horner vertex.
`results/ATTEMPTS.json` retains the failed-run history.
