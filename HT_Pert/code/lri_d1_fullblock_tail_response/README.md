# 1D high-order HT tails: full low-bath response and overlap mixing

This continuation retains the frozen energy regulator E0=N+P/4 and the source's
self-consistent disconnected vacuum window Dconn. It does NOT implement another
nonperturbative product-cutoff model or fit a thermal reference coefficient.

## What is new

1. The leading three-contraction UV kernel now includes arbitrary fixed low bath
   states, not only zero-mode external states. The extra same-power operator is
   `-{N,:q^2:}/2`, in addition to the particle-step phase operator.
2. Complete low-space linear responses to `eta*g(epsilon)^2*O` are calculated
   through epsilon^8, including vacuum feedback and primary retuning, through
   mu=28. Raw and Dconn are kept separate.
3. The first phase response has a complete all-low-bath convolution reduction,
   calculated through mu=262144. Its sqrt(mu), log(mu)^2, log(mu), AND subtracted
   finite part are independently derived, not fitted. The finite part is given
   by convergent sums/integrals, not extrapolation of the cutoff data.

The auxiliary low cutoff mu is NOT the outer high-state cutoff Lambda. These
results determine response and overlap-subtraction pieces, not the entire
physical C6,C7,C8 leading-tail polynomials. There is no new continuum C8 estimate.
Read `REPORT.md` and `docs/METHOD.md` for the exact scope and derivation.

## Structure

- `code/response.py`: normalized sparse Taylor response through order eight.
- `code/exact_response.py`: independent exact-rational small-space implementation.
- `code/annulus.py`: direct finite-annulus validation of the new low-bath kernel.
- `code/phase_response_shell.py`: complete V--Jphase--V low-state response;
  direct/extended-precision FFT variants.
- `code/phase_finite_part.py`: convergent regularized sums and endpoint integrals.
- `code/mixing_asymptotics.py`: exact topology sum for the overlap coefficients.
- `code/assemble_response.py`: explicit two-cutoff assembly of the calculated
  low responses with the two-vertex high factors; labelled partial, not a full tail.
- `code/analyze.py`, `code/plot.py`: tables/figures of calculated data.
- `vendor/window_jets.py`: unchanged upstream basis/ladder helper.
- `results/`: new responses, exact fractions, finite-part evaluations, validations.
- `inputs/PROVENANCE.json`: hashes and origins of numerical source files.
- `tests/`: independent numerical and algebraic checks.

## Dependencies

Python 3.10+, NumPy, SciPy, SymPy, mpmath, Matplotlib. Matrix responses are float64;
exact-rational comparisons and extended longdouble shell sums are separate
checks. Shell drivers reject a platform where longdouble has fewer than 63
explicit mantissa bits. No fast-math, amplitude pruning or fitted epsilon jets
are used. Tested versions are in results/ENVIRONMENT.json.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MPLBACKEND=Agg
```

## Validate and regenerate

```bash
# Check the untouched archive first; tests subsequently rewrite validation JSON.
python tests/verify_manifest.py
python tests/run_all.py
python code/analyze.py
python code/plot.py
```

The four validation drivers re-run exact-vs-numerical responses, source identities,
finite-annulus checks, analytic overlap algebra, and independent finite-epsilon
matrices. Full large-mu campaign replay is separate:

```bash
python code/response.py --cutoffs 2 4 6 8 12 16 20 24 28 \
  --channels phi6 phase number full --schemes dconn --degree 8
python code/response.py --cutoffs 2 4 6 8 \
  --channels phi6 phase number full --schemes raw --degree 8
python code/exact_response.py --cutoffs 2 4 --degree 8

python code/phase_response_shell.py \
  --cutoffs 2 4 8 16 32 64 128 256 512 1024 4096 16384 65536 262144
python code/phase_finite_part.py --N 256 --order 6 --dps 50
python code/phase_finite_part.py --N 512 --order 6 --dps 55
python code/mixing_asymptotics.py
```

`--direct` on phase_response_shell evaluates the convolutions without FFT. It
is useful for cross-checking small cutoffs, NOT for mu=262144. `--N` in the
finite-part code is the summation split for an already convergent regularized
formula, not the physical mode cutoff.

The large-mu shell result is ONLY the first phase susceptibility. It is not a
complete degree-eight Fock calculation at that scale. The reference low-state
Taylor engine stores all subcutoff-vacuum wavefunctions and their derivatives;
it has explicit state and wave-array guards. It is not an MPI/production HPC
release. Fixed model and particle support must be revalidated in an optimized
port; increasing/removing a guard is not an optimization.

## Interpretation

The exact response tensors provide a way to determine how an independently
calculated high-state operator changes the high-order thermal series. They are
not determined from desired C6,C7,C8 values. Conversely, observing a divergent
low-space response does not prove that the final thermal coefficient diverges:
hard/soft overlap terms must cancel in a fully matched result. The new analytic
subtractions locate part of that required cancellation.

All second-order high-kernel tests use finite annuli, so the power-divergent
mass term is never silently assigned an infinite finite value. Dconn remains
only the specified consistent disconnected-window model. Correct expansion of
that model is not an all-order proof of CFT matching.
