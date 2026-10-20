# One-dimensional long-range Ising: perturbative research compendium

> Public-release edit (2026-10-17): the passages on the compendium's own note are repointed to the SRI note
> (`public/RE-PINNED.json` records the original and published sha256 of this file). Everything else is verbatim.

## Start here

Read the SRI note of the public release, **`SRI/note/sri_short_range.tex`** (Sec. 2 and Appendices A to C): it holds
this compendium's derivations. The compendium's own note (`note/LRI_perturbation_compendium.tex` and its PDF) is not
shipped since 2026-10-17 (`public/NOT_SHIPPED.txt`); the few blocks of it that the public checks parse are kept in
`public/compendium_extract.json`.

The main convention is

```text
delta = 1-s = 2x,    x = Delta_sigma,
Delta_epsilon(x) = 1 + sum_{n>=1} C_n x^(n/2).
```

Thus C8 is the coefficient of **x^4**, not x^8.

### Current result and proof status

* The published starting theory and leading C1,C2 are credited to Benedetti,
  Lauria, Mazac, and van Vliet. Higher results are from the archived matched
  calculation, not additional coefficients attributed to their papers.
* C3–C7 have analytic reductions of their specified archived period expressions.
  Complete exact certificate data are included for C5, C6 and C7.
* The rational projection of C8 is **88**. The full numerical value is
  **247.3812048049935484073550747661...**.
* The compact C8 expression below is **numerically supported but not analytically
  proved**. No later complete certificate was produced by the interrupted proof
  attempts. Numerical relation recognition is not an analytic proof.

```text
C8 =? 88 - 178*zeta(2) + 110*zeta(3) + 113*zeta(4)
      + 4892*zeta(5) - 2376*zeta(2)*zeta(3)
      - (8630/3)*zeta(6) + 1872*zeta(3)^2
      - 12168*zeta(7) + 6048*zeta(2)*zeta(5)
      + 1536*zeta(3)*zeta(4).
```

The reported second numerical comparison has residual about 3.1e-86. This is
**not an interval bound**. Six other full C8 beta inputs enter that comparison
as inherited numerical records. See `documentation/REPRODUCTION.md` and the
SRI note's caveats (Sec. 2.9) and Appendix C.7 before interpreting the precision.

## Directory structure

```text
LRI_research_compendium/
  note/                  (not shipped; the derivations are in the SRI note, Appendices A to C)
  code/
    reproduce_summary.py Current coefficient/invariant tables and algebra checks
    reproduce.py         Named reproduction jobs
    prepare_workflows.py Recreate runnable original layouts in work/
    locate.py            Find a stored historical program/input by name
    archived/            Preserved Python, C/C++, shell and other source code
  data/
    coefficients.json    Current coefficient expressions, values and status
    archived/            Exact expressions, source blocks, terminal vectors,
                         certificate data, input records and numerical results
  outputs/
    tables/              Current CSV/JSON tables
    verification/        Fresh consolidation checks, including full C7 replay
    archived/            Labelled earlier verification outputs
  documentation/
    REPRODUCTION.md      Detailed commands, dependencies, regeneration and gaps
    SCRIPT_OUTPUT_MAP.md Which programs generate which results
    archived/            Earlier stage-note TeX and README sources
  reproduction/
    layout.json          Every retained original path -> its stored bytes
    MANIFEST.json        Immutable file hashes for this distribution
    source_archives.json Names/hashes of the archives used in consolidation
    omitted_files.json   Deliberate omissions and reasons
    environment.json     Actual consolidation toolchain/package versions
  references/            Bibliographic metadata for primary external sources
  run_checks.py          Default saved-expression and integrity verification
  requirements.txt       Symbolic and high-precision Python dependencies
  requirements-raw.txt   Optional direct-quadrature/raw-replay dependencies
  Makefile               Convenience targets
```

Identical historical inputs are stored **once**, not repeatedly in nested ZIPs.
`reproduction/layout.json` is the exact map back to the original executable
layouts. `prepare_workflows.py` makes ordinary independent copies into `work/`;
it does not modify the distributed inputs. This layout preserves relative
imports and old filenames without requiring the conversation or its sandbox.
To locate an expression or program:

```bash
python code/locate.py P6.expr
python code/locate.py verify_C7_certificate.py
```

`documentation/archived/` contains historical notes with their original status
statements. A note saying C7 or a subtask was unfinished is superseded by the
SRI note (Appendices A to C) and the registry, not an additional unresolved final result.

## Quick verification: standard library only

```bash
python run_checks.py
```

This checks all distributed hashes, rebuilds the necessary portable layouts,
reassembles all 64 P6 terminal outputs, checks the literal full-Jacobian C8
assembly on its numerical inputs, and verifies the exact P8/Kv and J9 scalar
maps. It also checks the independent rational sums giving 88. Missing data
raises an error; an absent scalar is never interpreted as zero.

It verifies **saved exact expressions and assembly**, not every raw kink
integration. Exact arithmetic applied to numerical input strings does not
remove the numerical integration uncertainty. It does not prove the C8 zeta
conjecture.

After intentional edits, `--skip-hashes` omits only the immutable distribution
hash check, not mathematical checks. Do not use Python `-O`: assertions are part
of the archived verifiers.

## Symbolic algebra and tables

Reference platform: Linux, Python 3.13.5. The standard-library checks have no
third-party requirements. For symbolic/numerical work:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python code/reproduce_summary.py
python run_checks.py --algebra
```

These regenerate `data/coefficients.json`, `outputs/tables/thermal_coefficients.csv`,
`outputs/tables/invariants.json`, and `outputs/verification/summary_algebra.json`.
The eighth coefficient remains labelled **candidate** in every regenerated table.

## Exact period certificates

```bash
python code/reproduce.py --task certificates
```

This materializes the proof inputs and runs the complete C5, C6 and C7
certificate verifiers, as well as the independent C7 input map. No floating-point
period values, SymPy, modular arithmetic, or external zeta tables are used in
these certificate checks. C7 is substantially larger than the earlier proofs:
588,878 source rows, including a weight-six identity with all product terms.

Progress residuals can grow before cancelling; they are exact finite algebra,
not numerical convergence. Success means the complete final residual is empty.
The complete C7 verification was freshly replayed during this consolidation.
There is **no C8 certificate command**, because that proof is not complete.

## Numerical replay

A compiler with C++17/OpenMP and GMP development headers is required for the GMP
backend. The independent Python Decimal evaluator is supplied too. On a Debian-
family Linux system the native prerequisites are typically `build-essential`
and `libgmp-dev`; package installation is separate from this archive.

```bash
python code/reproduce.py --task c8-saved
python code/reproduce.py --task c8-numerical
python code/reproduce.py --task c8-positive-check
```

`c8-saved` repeats scalar/input checks and the numerical candidate recognition.
`c8-numerical` freshly reevaluates the **entire full P6 period expression** at the
two recorded precisions, without reading a previous numerical period table.
It does not freshly reintegrate the defining ordered-domain kernel or all other
C8 beta coefficients. `c8-positive-check` independently reevaluates a complete
positive-weight lower-moment divergence comparison from the full C8 package.

Outputs go to the generated `work/` stage directories and
`outputs/verification/replayed/`. Details and exact filenames are in
`documentation/SCRIPT_OUTPUT_MAP.md`.

## Raw integrals and reproducibility limits

```bash
python -m pip install -r requirements-raw.txt
python code/prepare_workflows.py --workflow p6-source --rebase-scratch
python code/prepare_workflows.py --workflow p8-source --rebase-scratch
```

Use the dependency-ordered commands in `documentation/REPRODUCTION.md`, not an
old scratch path copied from a historical report. All native binaries must be
rebuilt; none is distributed. Defining kernels, source blocks, full scalar
expressions, necessary start checkpoints and final outputs are included.
Regenerable sequential stages, expanded hash buckets, caches, transient logs,
and duplicate ZIPs are omitted. Selected large start/terminal inputs are retained
because they are needed for independent saved-expression or raw-stage replay.

**Important limitations:** not every historical stage is fully replayable from
raw inputs without additional regeneration. Some F2 coverage metadata refers to
258 unavailable intermediate files. Six earlier full C8 beta inputs are retained
as numerical records rather than separately restored complete exact expressions.
The SRI note (Appendix H) and the reproduction guide identify these gaps. This archive includes the
surviving code/data and clearly separates supported replay levels; it does not
claim an end-to-end fresh raw derivation that the surviving record cannot support.

## The note

The compendium's note is not part of the public release. Its derivations are Appendices A to C of the SRI note, which
builds with `make note-pdf` from `SRI/`.

## Evidence and open problems

The SRI note distinguishes: published input, exact project integral expressions,
exact period certificates, numerical comparisons, conjectures, and physical
assumptions. The C8 candidate must still be proved by reconstructing a common
exact input map and checking a complete weight-seven identity, including product
terms. No general formula for all C_n is validated. The rational trace prediction
160 and several fixed Gamma/digamma/Borel generators were rejected by direct
coefficient tests.

The mathematical period checks do not independently prove the proposed LRI
duality, closure of the two-coupling description at all orders, or the absence of
additional counterterms. An independent high-order field-theory or bootstrap
check remains scientifically valuable.
