# Direct 2D long-range Ising curve with dressed circle-mode Hamiltonian truncation

This package implements fixed-parameter, nonperturbative diagonalization of the
**two-dimensional circle-mode** generalized-free-field plus phi^4 Hamiltonian.
It produces a finite-cutoff Delta_thermal versus Delta_sigma curve, not a proved
continuum result. The primary spin and shadow gaps are calibration inputs. The
thermal scalar is an untuned output. No coefficients of its epsilon expansion
are used by the tuning solver.

The physical long-range interval in this dimension is **1/8 < Delta_sigma < 1/2**,
not the one-dimensional interval 0 < Delta_sigma < 1/4. The separately marked
endpoint limits are (Delta_sigma, Delta_thermal)=(1/2,1) and (1/8,1).

Read `REPORT.md` for numerical results and limitations, and `docs/METHOD.md` for
all mode weights, normal ordering, projectors, coupling conventions and tuning.

## Directory map

- `code/d2dressed/`: new complete circle bath and scalar projectors, together with
  adapted local-basis, float64 matrix-free kernels and nonlinear solver.
- `code/scan.py`: complete fixed-parameter scans; atomic per-point JSON output.
- `code/diagnostics.py`: J=1 and J=2 spectra at the scalar-tuned couplings.
- `code/analyze.py`: accepted JSON -> CSV and numerical summary.
- `code/plot.py`: figures from accepted data only; no continuum fitting.
- `code/write_report.py`: report tables and validation summary.
- `tests/validate.py`: independent original-coordinate matrices, angular averaging,
  tensor/ladder actions, Jacobian, free limit, and reusable-basis immutability.
- `tests/weak_limit.py`: direct eigenvalues versus separately saved finite-cutoff
  perturbative polynomials at small epsilon; never used to tune the eigenproblem.
- `tests/verify_manifest.py`: artifact integrity verification.
- `inputs/d2_perturbative_coefficients.csv`: copied unchanged from the preceding
  two-dimensional perturbative calculation; comparison data only.
- `results/L6,L8,L10,L12/`: complete accepted primary-gap scans.
- `results/refine8z28,refine12z32/`: additional dressed/auxiliary resolution tests.
- `results/angular_L*.json`: untuned angular-sector spectra and spacing errors.
- `results/weak_limit.json`, `results/validation.json`: numerical validation.
- `results/curve_points.csv`, `results/SUMMARY.json`: regenerated data products.
- `figures/`: directly generated plots (PNG; SVG for the main curve).

No downloaded papers, temporary failed development scans, compiled caches, or
unrelated earlier research packages are included. The final data were generated
after correcting an in-place sparse-index sorting bug; the immutability and
fresh-basis spectrum tests now explicitly guard against it. Those invalidated
development outputs are not used or packaged.

## Dependencies

Python 3.11+ is recommended. Install the dependencies in `requirements.txt`:

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR="$PWD/.numba_cache"
```

The exact numerical library versions of the delivered run are recorded in
`results/environment.json`. No mixed precision, fastmath or amplitude pruning is
used. Numba compiles on first use. The sparse operator kernels parallelize over
output rows. The complete bath enumeration is guarded by a state count; raising
the guard for much larger cutoffs requires a fresh memory estimate.

## Fast saved-data reproduction

```bash
python tests/verify_manifest.py
python code/analyze.py
MPLBACKEND=Agg python code/plot.py
python code/write_report.py
```

These commands do not rerun the numerical eigenproblems. Lines on the graph join
actual data points. They are not fitted continuum curves or error bands.

## Numerical validation

```bash
python tests/validate.py
python tests/weak_limit.py
```

The first compares independent matrix constructions. The second repeats six
direct calculations at epsilon=.005,.01,.02 and L=4,8, then compares them with
the previous sixth-order **finite-cutoff** coefficients. The nonzero remainder
is not required to vanish: the direct solver includes higher perturbative orders.

## Reproducing the primary scans

```bash
python code/scan.py --bath-cut 6 --nz 20 --osc 160 \
  --output-dir reproduced/L6 --resume
python code/scan.py --bath-cut 8 --nz 20 --osc 160 \
  --output-dir reproduced/L8 --resume
python code/scan.py --bath-cut 10 --nz 24 --osc 192 \
  --seed-dir reproduced/L8 --output-dir reproduced/L10 --resume
python code/scan.py --bath-cut 12 --nz 24 --osc 192 \
  --deltas .495 .475 .45 .425 .4 .375 .35 .325 .3 .275 .25 .225 .2 .175 .15 .13 .126 .1251 \
  --seed-dir reproduced/L8 --point-timeout 180 \
  --output-dir reproduced/L12 --resume
```

The per-point wall limit is configurable and is only an operational guard; its
expiry produces a `FAILED_...json`, not a replacement numerical point. Resume
checks the recorded settings, implementation version and residual gates. This
prototype has atomic outputs but does not implement the earlier reviewed HPC
campaign's exclusive-claim/locking infrastructure. Avoid concurrent writers to
the same directory. Independent cutoffs are separate processes; there is no
single-point MPI implementation here.

Tuning is performed by safeguarded Newton iterations. Different continuation
seeds can change iteration counts and final roundoff. Final residual and expanded
spectrum checks must pass. A failed point is never interpolated or silently
replaced by a perturbative estimate. No physically important tolerance is relaxed
when attempting a difficult point.

## Refinements and untuned tests

```bash
python code/scan.py --bath-cut 8 --nz 28 --osc 224 \
  --deltas .45 .3 .2 .126 --seed-dir results/L8 \
  --output-dir reproduced/refine8
python code/scan.py --bath-cut 12 --nz 32 --osc 256 \
  --deltas .4 .2 .126 --seed-dir results/L12 --point-timeout 180 \
  --output-dir reproduced/refine12
python code/diagnostics.py --raw results/L10 \
  --deltas .495 .45 .4 .3 .2 .126 \
  --output reproduced/angular_L10.json
```

The `angular` solver argument means the circle momentum J. At J=0 the physical
scalar space is additionally projected even under a<->b reflection. Nonzero-J
calculations are diagnostics at the same scalar-tuned couplings, not additional
fits. Their level labels are candidate descendants followed from weak coupling;
there is no nonperturbative OPE-resolved state identification in this package.

## Scientific limitations

1. No completed 2D product-regulator high-state matching is included. In
   particular, the old d=1 vacuum correction and d=2 total-energy correction
   are NOT copied into this different regulator.
2. The scalar gap is an output of a two-coupling finite Hamiltonian, not a theorem
   about the target dilatation operator. The exact primary calibration cannot
   validate untuned dimensions.
3. Neighboring-cutoff agreement is not an uncertainty band. Stronger-coupling
   descendant errors and the short-range endpoint comparison remain important
   failures. The continuum endpoint is not imposed on the plotted data.
4. This is the two-dimensional classical long-range critical family, not a
   one-dimensional quantum transverse-field chain or the spin-boson bath model.
5. Direct eigenvalues, epsilon-polynomial truncation errors, cutoff errors,
   local/auxiliary basis errors and physical matching uncertainties are distinct.

## Provenance

The local zero-mode solver and factorized kernels are adapted from the supplied
`lri_dressed_phi4_hpc_optimized.zip`. The circle modes and normalizations follow
`lri_2d_phi4_ht_verification.zip`. This is a dimension-specific port: it changes
the mode degeneracies and weights, rotational and reflection projections,
expansion parameter, and shadow condition. It is not a parameter substitution
in the old one-dimensional code. Both angular projection and comparison to the
previous d=2 perturbative calculation have independent tests.

External primary references, used for physics comparisons only:
- C. Behan et al., arXiv:1703.03430, long-range critical exponents near crossover.
- C. Behan et al., arXiv:1703.05325, detailed operator dictionary and exact 2d Ising data.
- T. Horita, H. Suwa and S. Todo, arXiv:1605.09496, 2d classical crossover tests.
