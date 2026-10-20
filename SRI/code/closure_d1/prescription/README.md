# Normalized interval prescription and local renormalization

## Result and scope

This package gives a **formal, coefficientwise analytic prescription theorem** for
zero-field endpoint perturbation theory of the one-dimensional long-range Ising
dual. It addresses a gap not closed by merely counting two bulk counterterms.

The key argument is:
1. Construct local subtractions on operator-valued kernels, before choosing probes.
2. A collision at a fixed interval endpoint loses the free center coordinate and
   can diverge only in the reference dimension-zero sector.
3. The invariant dimension-zero sector is scalar. Endpoint UV factors therefore
   cancel in the common vacuum-normalized responses.
4. Reference probes outside the support do not have insertion UV divergences.
5. Exact current resummation and normal ordering generate the recorded source
   factors and finite-response Jacobian.
6. The local beta function is a solution of that Jacobian equation; formal
   invertibility makes it the unique solution, up to finite bulk coordinates.

This does not assert that a Wilsonian action contains only two terms, prove the
lattice duality, prove convergence/resummation at fixed delta, validate supplied
NRG data, or independently recompute the old high-order kink integrals. It also
does not resolve the separate exact C8 zeta-certificate problem.

## Directory structure

- `note/interval_prescription_equivalence.tex`: standalone mathematical note.
- `note/interval_prescription_equivalence.pdf`: compiled note.
- `code/check_prescription.py`: exact algebraic and low-order supplementary checks.
- `data/derived_response_recurrence.json`: generated recurrence through b9 and h8.
- `verification/checks.json`: completed exact checks and scope.
- `verification/VERIFICATION_REPORT.md`: distinction between proof and computations.
- `requirements.txt`: dependency for the supplementary checker.
- `MANIFEST.json`: SHA-256 digests of distributed files except itself.

## Running

Python 3.10+ and SymPy are needed for the supplementary checks. Tested here with
Python 3.13 and SymPy 1.14.0; no native extensions or old research archive required.

```bash
python -m pip install -r requirements.txt
python code/check_prescription.py
```

The script overwrites only its generated JSON outputs. It verifies matrix selection
rules through nine insertions, the uniqueness of the scalar endpoint channel,
normal-ordering and source identities, the response equations through g^9/h8,
the elementary cutoff integrals at arbitrary length, and simple spectator/RG
identities. These checks are NOT substitutes for the analytic forest induction.

Compile the source with a normal LaTeX distribution:

```bash
cd note
pdflatex -interaction=nonstopmode -halt-on-error interval_prescription_equivalence.tex
pdflatex -interaction=nonstopmode -halt-on-error interval_prescription_equivalence.tex
pdflatex -interaction=nonstopmode -halt-on-error interval_prescription_equivalence.tex
```

No external bibliography or figure files are needed. The source specifies all
normalizations and references used in the argument.
