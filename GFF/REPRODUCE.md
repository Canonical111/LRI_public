# Reproducing the GFF results

How to rerun each package: environment, `make -f public.mk test` / `replay`, and the documented production reruns. `make test` and `make replay` in this folder run every package (see `Makefile`).

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `GFF/`. The values themselves are in `note/README.md` and the note.

- C0-C5 in closed form, d = 1: `lri_numerical_resolution`, `lri_psi_complete_update`, `lri_fixed_hypergeometric_update`
- C0-C5 in closed form, general d: `lri_general_special_functions_update`, `lri_general_closed_update`, `lri_general_periodization_update`
- Closed forms of L2, K2 and C5(2): `LRI_C5_d2_simplify`, `LRI_C5_d2_proof`
- d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d: `lri_d3_reduction_update`, `lri_d3_matrix_update`, `LRI_C5_general_d`, `LRI_C5_d3`
- C6(1) and its analytic representation: `LRI_C6_1D_HPC`, `C6_research_note`, `LRI_C6_closed_form_review`
- Finite kernels, power compensation, C6(2) and C6(3): `lri_C6_d2_complete_update`, `lri_C6_d3_complete_update`, `LRI_C6_D2_HPC`, `LRI_C6_D3_HPC`
- Full C7(1), C7(2), C7(3): `LRI_C7_HPC`, `LRI_C7_D2_HPC`, `LRI_C7_D3_HPC`
- Full C8(1), C8(2), C8(3) and the independent checks: `LRI_C8_HPC`, `LRI_C8_D2_HPC`, `LRI_C8_shared`, `LRI_C8_D2_HPC_optimized`, `LRI_C8_D3_HPC`, `LRI_C8_D3_OPT`

## C0-C5 in closed form, d = 1

### `lri_numerical_resolution`

Folder: `code/lri_numerical_resolution/`.

#### REPRODUCE fragment: lri_numerical_resolution (one-dimensional analytic C5, graph control)

##### 1. Replay (CI; no compiler)

    make -C code/lri_numerical_resolution -f public.mk test     # ~1 s
    make -C code/lri_numerical_resolution -f public.mk replay   # ~25 s

One core and Python >= 3.10 with `public/requirements.txt` (mpmath, sympy, numpy). Measured on one core of an
Apple M1 Max: test 0.8 s, replay 25 s (69 checks, 0 FAIL) with Python 3.10.12, mpmath 1.3.0, sympy 1.12,
numpy 1.24.4, and again with mpmath 1.2.1, sympy 1.11.1, numpy 1.23.5. Every regenerated record agreed with
the shipped one in every numeric field (deviation 0); only `elapsed_seconds` and the refresh flag differ. A personal desktop
or an Expanse debug node needs no special settings (single-threaded BLAS is set by the replay).

##### 2. Production rerun of the raw graph integrals (hours; not in CI)

The shipped raw records were produced by the package README's "Full integral regeneration" on an Intel Xeon
Platinum 8573C (AVX-512, 4 threads, Debian, g++ 14.2.0, Python 3.13.5, NumPy 2.3.5, mpmath 1.3.0, SymPy 1.14.0;
`verification/records/environment.json`). Requirements: Linux x86-64, a C++17 compiler with OpenMP, a 64-bit
long-double significand (`--method scalar`), AVX-512F (`--method combined-simd`; the driver reads
`/proc/cpuinfo`). An AMD EPYC Rome/Milan node (Expanse) has no AVX-512: there only the scalar method runs, much
more slowly (the degree 22 and 24 combined runs have no scalar counterpart in the record). Runtimes from the
production logs (not exported): lower loops at degree 32, 8 min for both cutoffs; scalar degree 18, 21 min;
combined degree 18, 22, 24: 10, 8, 12 min plus 15-23 s set-up each; about 1 h wall, 4 core-hours. The weight array
at degree 24 is about 2.3 GB.

Slurm template (placeholders `<ACCOUNT>`, `<PARTITION>`, `<SCRATCH>`, `<REPO>`):

```bash
#!/bin/bash
#SBATCH --job-name=c5d1-graph
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>        # Intel node with AVX-512F
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=<SCRATCH>/c5d1-graph-%j.out
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
run=<SCRATCH>/c5d1-graph-$SLURM_JOB_ID
cp -r <REPO>/GFF/code/lri_numerical_resolution "$run" && chmod -R u+w "$run" && cd "$run"
python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt
python verification/run_lower.py 32                     # writes verification/records/lower_{span,maxgap}_32.json
python verification/regenerate_graph_audit.py
python verification/enumeration_audit.py
python verification/run_sector.py --method scalar --order 18 --threads 4
for N in 18 22 24; do python verification/run_sector.py --method combined-simd --order $N --threads 4; done
cp verification/work/scalar/amplitude5_*.json verification/records/
cp verification/work/combined-simd/combined5_*.json verification/records/
python verification/audit.py --refresh-reference
# compare the new raw records and the audit with the published ones (tolerance, not bitwise)
python - <<'EOF'
import sys; sys.path.insert(0, 'public')
from pathlib import Path
import replaylib as r
pub = Path('<REPO>/GFF/code/lri_numerical_resolution/verification/records')
for f in sorted(Path('verification/records').glob('*5_*.json')) + [Path('verification/records/resolution_audit.json')]:
    n, dev, probs = r.compare_records(r.load(f), r.load(pub / f.name), 1e-12, ('elapsed_seconds',))
    print(f.name, n, 'fields, max scaled deviation', r.mp.nstr(dev, 3), 'problems:', probs[:2])
EOF
```

The tolerance 1e-12 (relative to max(1, |value|)) is an expectation, not a tested bound: thread reductions and
libm change the last bits of the long-double and double-double kernels, and the C5 residuals of interest are
6e-13 to 3e-11. `make -f public.mk replay` in the rerun folder would compare the rerun with itself, so use the
snippet above. This rerun has not been repeated since September 2026.

### `lri_psi_complete_update`

Folder: `code/lri_psi_complete_update/`.

#### REPRODUCE fragment: lri_psi_complete_update (check of the compact master K)

There is no production campaign. `make replay` reruns every computation behind the shipped records, unchanged,
in a fresh copy under `.work/pkg/`:

    make -C code/lri_psi_complete_update -f public.mk test     # ~2 s: symbolic_checks.py, coefficient_values.py, complex_check.py
    make -C code/lri_psi_complete_update -f public.mk replay   # ~15 s: test + numerical_checks.py (110-digit master)

One core, Python >= 3.10 with mpmath and SymPy (`public/requirements.txt`). Measured on one core of an Apple M1
Max: test 1.8 s (22 checks), replay 13 s (28 checks, 0 FAIL), with mpmath 1.3.0/SymPy 1.12 and with mpmath
1.2.1/SymPy 1.11.1. All regenerated records agreed with the shipped ones in every numeric field (only
`elapsed_seconds` differs). The original scripts accept other precisions (`numerical_checks.py --digits N`,
N >= 30), but the shipped records are those at the default precisions, which the replay uses.

Not reproduced here: the 240-digit 4F3(1) inputs in `verification/wheel_inputs.json` come from the bundle package
`Fpm_simplification` (not exported); the same values are recomputed from scratch at 80 and 70 digits by the
replays of `lri_numerical_resolution` and `lri_fixed_hypergeometric_update`.

### `lri_fixed_hypergeometric_update`

Folder: `code/lri_fixed_hypergeometric_update/`.

#### REPRODUCE fragment: lri_fixed_hypergeometric_update (check of the five-value P5)

There is no production campaign. The shipped record is the output of one run of the verifier at 100 digits
(with its built-in 125-digit control), which `make replay` repeats unchanged in a fresh copy under `.work/pkg/`:

    make -C code/lri_fixed_hypergeometric_update -f public.mk test     # ~3 s (verifier at 40 digits)
    make -C code/lri_fixed_hypergeometric_update -f public.mk replay   # ~6 s (verifier at 100 digits)

The direct command is `python code/verify_fixed_hypergeometric.py --digits 100 --output <file>` (do not let it
overwrite `verification/fixed_hypergeometric_checks.json`). One core, Python >= 3.10 with mpmath and SymPy.
Measured on one core of an Apple M1 Max: test 2.5 s (22 checks), replay 6 s (28 checks, 0 FAIL), with mpmath
1.3.0 and with mpmath 1.2.1; the 100-digit record was reproduced in every numeric field.

## C0-C5 in closed form, general d

### `lri_general_special_functions_update`

Folder: `code/lri_general_special_functions_update/`.

#### Reproducing C0..C5 at general dimension (three bundle packages)

Requirements: Python >= 3.10 with numpy, scipy, sympy and mpmath (`requirements.txt`). No compiler, no GPU, no network,
no hosted data. macOS or Linux; one core is enough.

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r GFF/requirements.txt   # or this unit's requirements.txt
cd GFF/code/lri_general_special_functions_update && make -f public.mk replay && make -f public.mk test
cd ../lri_general_closed_update                  && make -f public.mk replay && make -f public.mk test
cd ../lri_general_periodization_update           && make -f public.mk replay && make -f public.mk test
```

Each target prints a PASS/FAIL table, writes it to `public/out/{replay,test}.json` with the Python and library versions,
and exits 1 on any FAIL. The delivered scripts write their records in place, so the targets run them in copies under
`public/out/work/` (logs in `public/out/work/*/logs/`); nothing shipped is modified. `make -f public.mk clean` removes
`public/out/`.

| Package | replay | test (includes replay) |
|---|---|---|
| lri_general_special_functions_update | 78 rows, about 5 s | 115 rows, about 2.5 min (graph reduction about 1 min) |
| lri_general_closed_update | 35 rows, about 25 s | about 4 min (full Horn compiler 2.4 min, 0.25 GB; compiler check 1 min) |
| lri_general_periodization_update | 30 rows, about 10 s | 34 rows, about 50 s |

Times are one core of a macOS arm64 laptop; a cluster core is similar or slower by up to 2x.

##### What replay recomputes

- special-functions: the exact fixed-point assembly of the saved graph rows (SymPy; `sum4.py`, `sum5.py`,
  `exact_audit.py`, which asserts the general C4, C5, their d = 1 specialization and the cancellation of the mass Gamma
  terms), C0..C5 at d = 1, 2, 3 from the saved masters (`assemble_results.py`, mpmath 50 digits), the Lagrange inversion
  of C1..C3 (`symbolic_checks.py`); then the note's formulas symbolically and every quoted number at its printed digits.
- closed: the 60-digit identities (Q2, Z2, K-term identities, P5 residues), the 336 insertion-prefactor checks, the K_d
  cancellation polynomial and the Horn arrays of Q, P4, L, Z, K; Q2 and the Horn counts.
- periodization: the exact algebra of the d = 2 factorization, the 55/70/60-digit d = 2 chain, the parameter templates;
  P4(2), P5(2), B7, and the d = 2 closed forms of C4(2), C5(2), L2 (owned by closed_forms_2) evaluated with this P4(2), P5(2).

##### Production rerun (full regeneration)

These are analytic and high-precision computations; the whole "production" reruns inside `make -f public.mk test` of the
three packages, on one core in about 7 minutes (about 0.1 core-hour), and reproduces every exact and mpmath record byte for
byte (timing fields aside). Nothing needs a scheduler. On a Slurm cluster, if wanted:

```bash
#!/bin/bash
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:30:00
#SBATCH --output=<SCRATCH>/gff_general_c0c5_%j.out
set -euo pipefail
cd <SCRATCH>/LRI_public/GFF/code
for p in lri_general_special_functions_update lri_general_closed_update lri_general_periodization_update; do
  make -C "$p" -f public.mk test PY=python3
done
```

The steps that regenerate the inputs, for reference (run in a copy; each writes into its own folder):

| Package | Command (from the package folder) | Regenerates | Time |
|---|---|---|---|
| special-functions | `python3 code/general_special/derive_A.py` | `A_regular.json` (regular parts of the jets; seeded) | 2 s |
| | `python3 code/general_special/collect.py 3 0 8` (then `4 0 27`, `5 0 129`) | the graph residue rows | 1 s, 4 s, 60 s |
| | `python3 code/general_special/sum4.py; python3 code/general_special/sum5.py; python3 code/general_special/exact_audit.py` | `sum4.json`, `sum5.json`, `exact_checks.json` | 2 s |
| | `python3 code/general_special/spectral_evaluate.py` | `spectral_master_values.json` (masters at d = 2, 3, 4) | 7 s |
| | `python3 code/general_special/assemble_results.py` | `coefficient_values_new.json` | 1 s |
| | `python3 code/graph_inventory.py --output X; python3 code/inventory_checks.py X --output Y` | graph inventory through five loops | 7 s |
| closed | `python3 code/general_closed/horn_compiler.py --out DIR` | the seven Horn arrays (gzip; compare decompressed) | 2.4 min |
| periodization | `python3 code/general_periodization/horn_templates.py` | `arrays/primitive_r{3,4,7}.json` | 1 s |

Two inputs have no generating script in the delivery: `code/general_special/primitive_recheck.json` (the d = 3 value of
P5, 240.34031775909176; the 50-digit value of the d = 3 unit agrees to 3.4e-14 relative) and
`code/general_special/reference_d1_coefficients.json` (the d = 1 periods and C0..C5 to 70 digits, from the d = 1
packages). `code/general_special/check_A_d1.py` needs an absent folder of the delivering session and is not run.

### `lri_general_closed_update`

Folder: `code/lri_general_closed_update/`.

_same as the section above (one text for the whole unit)._

### `lri_general_periodization_update`

Folder: `code/lri_general_periodization_update/`.

_same as the section above (one text for the whole unit)._

## Closed forms of L2, K2 and C5(2)

### `LRI_C5_d2_simplify`

Folder: `code/LRI_C5_d2_simplify/`.

#### Reproducing the d = 2 closed forms of L2, K2 and C5(2)

All targets run from the package folder with `make -f public.mk <target>`. GFF/Makefile calls
`make -C code/<pkg> -f public.mk <target>`. The targets need:
- Python >= 3.9 with mpmath >= 1.2.1 and sympy >= 1.11 (`requirements.txt`);
- no compiler and no hosted data.

Times were measured on macOS (Apple silicon, 10 cores, heavily loaded at the time); a cluster core is similar.

##### Test and replay

```bash
cd GFF/code/LRI_C5_d2_simplify
make -f public.mk test      # 30 s wall, 48 s CPU: factorizations byte for byte, all 50 sums and identities at 18 digits,
                            # the proof fragment's exact checks, closed forms at 30 digits      -> 11 PASS
make -f public.mk replay    # 4 s: the production assembly on the stored 70-digit sums, the recorded residuals,
                            # L2, K2, C5(2) at 80 digits against every quoted decimal, the independent spectral record
                            #                                                                    -> 70 PASS
cd ../LRI_C5_d2_proof
make -f public.mk test      # 8 s: the cited exact checks and the C5(2) algebra                  -> 5 PASS
make -f public.mk replay    # 11-18 s: test, the 75-digit elliptic cross-check, the W4(2;2x) spectral fit,
                            # the 3F2 value at tau = 3/10, and the recorded check outputs        -> 23 PASS
```

Each replay writes a PASS/FAIL table to stdout and `public/out/replay.json`, and exits 1 on any FAIL. All work happens
in copies under `public/out/work/`, and no shipped file is modified. `replay` of LRI_C5_d2_simplify needs the sibling
`../LRI_C5_d3/wf_d2check/d2check_results.json`, which C63d's unit ships.

##### Optional checks

```bash
cd GFF/code/LRI_C5_d2_proof && make -f public.mk replay-wl
```
- Mathematica 14 or 15 with `wolframscript`. Runs `laurent_K2.wl` (cited by the note), `jgamma_series.wl`,
  `check_series.wl` and `checks_all.wl` in work copies, one kernel at a time.
- `python3 public/replay_wl.py review_L2_singlesums_numerics_r0/s3_modes.wl` adds the long 1e-82 check.

```bash
make -f public.mk checks
```
- In `LRI_C5_d2_proof`: the other numerical checks cited by the proofs.
- In `LRI_C5_d2_simplify`: the prover scripts of the three further proofs. `proof/K2-parseval/e2check.py` uses `NP`
  processes (default 8; it ran in 384 s on 8 cores).

##### Production rerun (not in CI)

The production is one run of `parallel_eval.py 70`:
- 50 single sums at 80 working digits by Euler-Maclaurin, in a process pool sized `os.cpu_count()`;
- then the assembly and ten identity checks.

The original ran as symmetry job 567346 on one exclusive 64-core amdq node in 1852 s (33 allocated core-hours). It
requested 200G of memory; the real use was not recorded and is small (50 mpmath processes). `make -f public.mk rerun70`
runs it in `public/out/work/parallel_eval/` and compares the 50 new sums with `confirm_dps70.json` (relative 1e-65).

```bash
#!/bin/bash
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION>
#SBATCH -N 1
#SBATCH --exclusive              # 64 cores or more; the pool uses every core of the node
#SBATCH --mem=32G
#SBATCH -t 02:00:00
#SBATCH -J c5d2-rerun70
#SBATCH -o <SCRATCH>/c5d2-rerun70-%j.out
set -euo pipefail
cd <SCRATCH>/GFF/code/LRI_C5_d2_simplify       # a checkout of the public repository
export OMP_NUM_THREADS=1
python3 -m venv <SCRATCH>/venv && <SCRATCH>/venv/bin/pip install -r <SCRATCH>/GFF/requirements.txt   # or module python
make -f public.mk rerun70 PY=<SCRATCH>/venv/bin/python
```

Each sum runs in one process and the longest takes about 31 min, so with 50 or more cores the wall time is about
31 min; with fewer cores it grows roughly in proportion (the computation is at most 50 x 1852 s, about 26 core-hours).
A 100-digit run is not useful: the K2 sums take more than 5 h each.

The other cluster runs behind the shipped records are not needed for any quoted number beyond what `replay` checks.
Their scripts ship next to their outputs:

| Run | Script | Record |
|---|---|---|
| job 567960, 2 cores, 60 digits | `proof/L2-fourier/c5d2_l2fourier_dps60.slurm` | `check_*_dps60.log` |
| job 567967, 8 cores, 384 s | `proof/K2-parseval/e2check.slurm` | `e2check-567967.out` |
| job 568067 | `review_L2_structural_numerics_r0/spec_job.sh`, `spec_job.py` | `spec_*.json`: the moments behind "2x10^-70" |
| the reviewers' Mathematica runs | `review_K2_d1template_numerics_r0/run.sb` | `logs/` |
| the independent spectral evaluation | C63d, `GFF/code/LRI_C5_d3/wf_d2check` | its own REPRODUCE |

### `LRI_C5_d2_proof`

Folder: `code/LRI_C5_d2_proof/`.

_same as the section above (one text for the whole unit)._

## d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d

### `lri_d3_reduction_update`

Folder: `code/lri_d3_reduction_update/`.

#### Reproduce: lri_d3_reduction_update (d = 3 half-shift reduction)

**Inputs.** None besides the code: the period formulas use fixed rational parameters, and no stored period value is read
by the formula side or by the spectral side.

**Full regeneration = `make -f public.mk replay`.** The replay reruns the package's own three commands (README_d3_reduction.md,
"Reproduction") in a copy under `.work/pkg/`:

```sh
python code/general_d3/check_exact.py      # 25 exact identities, 288 Horn coefficients -> exact_algebra.json, horn_arrays.json   (< 1 s)
python code/general_d3/verify_d3.py        # periods at 55 and 90 digits, identities at 75, literal hyper calls at 40 -> period_values.json,
                                           # identities.json, literal_hypergeometric.json, environment.json                       (about 65-80 s)
python code/general_d3/check_spectral.py   # fresh Gamma-kernel integrals at 45 and 60 digits -> fresh_spectral.json             (about 110-155 s)
```

Then it compares every number with the delivered records and with the note. These scripts regenerate every record in
`verification/general_d3/` except `comparison_summary.json`. That file holds two differences of the other records, which
the replay recomputes, and C2–C4(3) assembled with the new periods by a script that is not in the package. The replay
compares these three only with the note's Section 1 table; they are reproduced by the general-d entries of GFF. The package's 140-page note
revision (`long_range_ising_complete.tex`) is not shipped: its d = 3, periodization and general-d chapters are the
condensed note's Sections 19, 18 and 17 (`GFF/note/`). No number needs it.

**Machine.** One core, under 1 GB, about 4 minutes in all; a laptop is enough. No Slurm job is needed. On a cluster:

```sh
srun -A <ACCOUNT> -p <PARTITION> -c 1 --mem=2G -t 00:20:00 make -C code/lri_d3_reduction_update -f public.mk replay
```

**Expected output.** `.work/REPLAY.md` with 69 PASS, 0 FAIL and 1 INFO (the 28 files of `public/dropped_paths.txt`). With mpmath 1.3.0 the reruns were bitwise equal to the
delivered records (local test, 2026-10-13). The tolerances allow a different last guard digit, 10^-(dps-10) or wider; see
`results_map.md`.

### `lri_d3_matrix_update`

Folder: `code/lri_d3_matrix_update/`.

#### Reproduce: lri_d3_matrix_update (rank-two identification)

**Inputs.** None for the exact checks and the 100-digit recomputation. The optional catalogue search reads
`verification/fresh100_input.json` (the 100-digit Q_3 that defines its target).

**Full regeneration = `make -f public.mk replay` (+ `search`).** The replay reruns the package's own commands (README.md,
"Reproduction") in a copy under `.work/pkg/`:

```sh
python code/rank_two_checks.py verification/rank_two_checks_rerun.json   # 1107 exact checks + 90-digit partial sums   (about 1 s)
python code/recompute_d3_periods.py                                       # Q_3, P_4(3), P_5(3) at 100 digits           (about 15-25 s)
python code/scalar_catalog_search.py                                      # optional (make ... search): 6479-entry PSLQ  (about 1 min)
```

Then it compares the outputs with `verification/rank_two_checks.json`, `fresh_primitive_values.json` and
`scalar_catalog_search.json`. The package's 144-page note revision and its rank-two appendix are not shipped:
the appendix is the condensed note's Section 19, subsections 19.5-19.7 (`GFF/note/`). No number needs them.

**Machine.** One core, under 1 GB; under 2 minutes with the search. No Slurm job is needed. On a cluster:

```sh
srun -A <ACCOUNT> -p <PARTITION> -c 1 --mem=2G -t 00:10:00 make -C code/lri_d3_matrix_update -f public.mk replay
```

**Expected output.** `.work/REPLAY.md` with 22 PASS, 0 FAIL and 1 INFO (the 5 files of `public/dropped_paths.txt`)
(replay), and 3 PASS with the same INFO row for `search`. Reruns were bitwise
equal to the delivered records with mpmath 1.3.0.

### `LRI_C5_general_d`

Folder: `code/LRI_C5_general_d/`.

#### Reproducing LRI_C5_general_d (generic-dimensional reduction of 𝓛_d, Z_d and 𝒦_d; note Sections 20 and 21)

The package has no Monte Carlo and no production campaign. Every number is a deterministic multiple-precision evaluation
in mpmath; the 𝒦_d position-space values use Arb through python-flint. Reproducing the package therefore means rerunning
scripts that take seconds to hours.

All commands below run from `GFF/code/LRI_C5_general_d/` and need the sibling `GFF/code/LRI_C5_d3/`. Requirements are
in `requirements.txt`: Python ≥ 3.10, mpmath, sympy; python-flint only for `smoke-Kd`. Outputs go to `public/out/`, and
shipped files are never modified.

##### 1. Test (about 90 s, one core, any OS)

    make -f public.mk test

This runs the package's own checks unchanged and judges each by the numbers it prints. The checks:

- the product-form top-mode check, `foundation/check_topG.py`;
- the jet engine against plain sums and Cauchy circles;
- the printed closed-form coefficients of the 𝓛_d formula against sympy;
- the sympy derivations of the residue functional, the three-node formula, the pole-node weights and the two-node form;
- P4 and 𝓛_d at 20 digits against the closed form (d = 2) and the spectral reference (d = 1.5);
- Z_d by exact jets at 30 digits against the 90-digit record.

The result is a PASS/FAIL table in `public/out/test.json`. Verified on 2026-10-13: 12/12, 93 s.

##### 2. Replay (about 45 s, one core, any OS)

    make -f public.mk replay            # Section 20 (public/replay.py) and Section 21 (public/replay_K_d.py, C63d)
    make -f public.mk replay-records    # the record part only (seconds)

**Section 20.** `public/replay.py` runs 115 checks in four parts.

1. **Bindings.** It checks the md5 that the package's records pin on its code, and the SHA-256 of every record it reads.
   The expected hashes are in `../../results/closed_forms_general/reduction_d/expected.json`.
2. **Note text.** It checks that every quoted TeX string occurs in `../../note/long_range_ising_condensed.tex`.
3. **Fast recompute.** In a copy of the package, `public/out/work/`, it reruns the package's own scripts:
   - `review/joint/numerics-end-to-end/e2e.py` gives C5(1), C5(2), C5(3) end to end; its report must equal the shipped
     one byte for byte.
   - The path-fixed `public/e2e_k3_public.py` gives the three-node 𝒦_d column.
   - `specialize/check_d3.py 50` (d = 3 dictionary) and `foundation/check_topG.py` must reproduce their logs.
   - `specialize/check_special.py` (d = 1, 2 identities) saves its log, which the package did not keep.
   - `review/lemmaG-numeric/{summarize,compare_external}.py` rebuild the probe summaries.
   - `public/check_DL_Phat.py` checks the 𝔇_L identity.
4. **Quoted numbers.** It recomputes every number Section 20 quotes for this package, plus the cross-checks of C5(1..3),
   𝓛₃, d_H and d_a printed elsewhere in the note and in earlier versions of the paper. Each is compared at its printed digits by the rule
   in `expected.json`.

Output: a PASS/FAIL table on stdout and in `public/out/replay.json`.

**Section 21.** `public/replay_K_d.py` (C63d) runs 70 checks of every quoted 𝒦_d number from the stored records. Its
report is `public/out/replay_K_d/REPLAY_K_d.md`. `make -f public.mk smoke-Kd` adds a rerun of the position-space code at
40 digits; this needs python-flint and takes about 15 s.

Verified on 2026-10-13 in a mock export of the release (Python 3.10.11, mpmath 1.2.1, macOS): 115/115 and 70/70 in about
30 s of CPU, with both the gmpy2 and the pure-Python mpmath backend (`MPMATH_NOGMPY=1`).

##### 3. Replay-full: recompute the Section 20 records (R1; about 1 core-hour, a cluster node)

    SLURM_CPUS_PER_TASK=16 make -f public.mk replay-full          # PSLQ=1 adds the two PSLQ probes

This reruns, in `public/out/work_full/`:

- the 60-digit samples (`dump_samples.py`), then `e2e.py` on them;
- the C5 assembly at 8 dimensions (`c5_assembly.py 50`);
- the pole-node check (`check_taylor.py 30`);
- the five-Horn validation at 50 and 70 digits (`L/run_validation.py`);
- the exact-jet and Cauchy Z_d engines at 60 and 90 digits (`Z/z_jets.py`, `Z/z_cauchy.py`);
- the re-analyses `Z/compare_refs.py` and `Z/check_formulas.py`.

Each recomputed record is compared field by field with the shipped one, ignoring run times and paths, by a precision-aware
rule:

- value fields agree to dps−10 digits of the size of their record entry;
- the deviation fields of the C5 assembly stay below the bounds the note prints;
- the PSLQ probes keep their conclusion.

The records were written with mpmath's gmpy2 backend and reproduce string for string with it. The pure-Python backend
moves the last guard digits, so near-vanishing fields (the M1 block at the resonant d = 4/3, the vanishing dW) differ by
a large relative amount at the same 1e-58 absolute level (symmetry run 1, CLUSTER_CHECKS.md).

Two records were written against the 45-digit reference strings that `references/reference_values.json` held before its
50-digit rebuild (2026-10-03 01:21), so their deviations from the references shrink when recomputed: the `dev_*_ref`
fields of `c5_assembly_dps50.json` (to ≤ 3.7e-50) and `Z/results/compare_refs.log`.

The longest single task is one dimension of `dump_samples.py`, which took 183 s on a symmetry amdq node. Slurm template
(`<ACCOUNT>`, `<PARTITION>`, `<SCRATCH>` are placeholders):

    #!/bin/bash
    #SBATCH -A <ACCOUNT>
    #SBATCH -p <PARTITION>
    #SBATCH -N 1 -c 16 --mem=32G
    #SBATCH -t 01:00:00
    #SBATCH -J c5gend_r1
    #SBATCH -o <SCRATCH>/c5gend_r1_%j.out
    cd <SCRATCH>/GFF/code/LRI_C5_general_d
    export SLURM_CPUS_PER_TASK=16
    make -f public.mk replay-full PY=python3

Expected wall time on 16 cores is 10–15 min (about 1 core-hour). With PSLQ=1, the 80- and 110-digit PSLQ probes add a
few minutes. The production used whole 64-core nodes, where each job took 5–60 s.

##### 4. Independent checks and reference values (R2; documented, not automated; about 170 core-hours)

These regenerate the records of the cited independent checks. Each script ships with its job script (`*.slurm`,
`*.sbatch`; the cluster paths in them are scrubbed). Arguments are as in the job logs next to the records.

| what | command (from the package folder) | cost (production) | compare with |
|---|---|---|---|
| spectral references `references/reference_values.json` | `cd refvals; python3 hp_general_d.py ref2_b_<d>.json <d> 56 60 60 72 b <rho> <rho_off>` and the `_t` (τ-circle) runs, for d = 0.8, 1.25, 1.5, 2.5, 2.75 (settings in the `.out` logs; `HPG_NUTAIL=1`, the analytic large-ν tail, is required for d < 2); then a path-fixed copy of `build_refjson.py`, whose `OUT` is absolute in the original | 18 runs, 4 163 s of exclusive 64-core node time (about 74 core-h) | `references/reference_values.json` to its stated digits (44–50) |
| foundation validation | `cd foundation; python3 run_validation.py val50.json 50 refs center offdiag spectral circles` (env `CIRCLE_DS=1,2,3,1.5,2.5,0.8,1.25,2.75 MCIRC=96`); `valx`, `sample_jets.py` | 346 s + 496 s + 52 s on 64 cores (about 15 core-h) | `foundation/results/*.json` |
| top-mode probe, wheels | `cd review/topmode-numeric; python3 run_probe.py <tag> 50 60 16 1/16 128 <configs>` (see `probe.slurm` and `logs/`) | about 25 core-h on 8-core nodes | `results/probe_*.json` |
| top-mode probe, product form | `cd review/lemmaG-numeric; while read l; do python3 run_case.py $l --np 8 --outdir ../results; done < list_main1.txt` (and `list_main2/3`, `list_fine*`), then `summarize.py`, `compare_external.py` | about 50 core-h (6.5 h on 8 cores) | `results/*.json`, `summary*.json` |
| three-node 𝒦_d jets | `cd review/joint/numerics-end-to-end; PYTHONPATH=../../../K_general/R_part python3 kjet3.py 1.5,2.5,3 0.08 48 30 400 72 k3_jets.json` | 30 min on 8 cores | `k3_jets.json` |
| review codes | `review/formula-from-text/circle_driver.py` (M = 1e5, 255–666 s per d), `review/foundation-rigor/run_cases.py`, `review/{L,Z}-rigor/*.py` | minutes to hours each | the logs in the same folders |
| 𝒦_d production (C63d) | `K_general/` (see C63d's notes in REVIEWS.md and PROVENANCE.md) | | `public/expected_K_d.json` |

Scripts that carry absolute paths (`foundation/make_tables.py`, `foundation/analyze_val.py`, `Z/quick_check.py`,
`refvals/build_refjson.py`, `review/topmode-numeric/{summarize,run_probe}.py`,
`review/joint/numerics-end-to-end/table_rounding.py`) need a path edit in a copy before they run. None of them is used
by `test`, `replay` or `replay-full`.

### `LRI_C5_d3`

Folder: `code/LRI_C5_d3/`.

#### Reproducing C5(3) and the d = 3 masters (GFF/code/LRI_C5_d3)

Run every command from `GFF/code/LRI_C5_d3`. Nothing here writes into the shipped files: the public targets work in
`.work/` (git-ignored). When you rerun a production step, use a copy of the package, because several original scripts
write their outputs into the current directory under the names of the shipped records.

##### 1. Environment

| need | used in production (2026-10-02) | tested for the release (2026-10-13) |
|---|---|---|
| Python | 3.x on the cluster nodes, 3.10 locally | 3.10.12 |
| mpmath | 1.3.0 (gmpy2 backend recommended for speed) | 1.3.0 |
| SymPy | 1.x (assemble_c5_d3.py, test) | 1.12 |
| python-flint (Arb) | 0.x (k3flint.py, LLL batteries) | 0.9.0 |

`pip install -r requirements.txt`. Single-core scripts do not need BLAS. Set `OPENBLAS_NUM_THREADS=1` as the job
scripts do.

##### 2. Tiers

1. `make -f public.mk test` (2 s): exact d = 3 identities and Horn arrays (`inputs/general_d3/check_exact.py`), and the
   SymPy specialization of gs:C5 and C4 to d = 3.
2. `make -f public.mk replay` (4 s): the package's scripts are rerun on the shipped records and their outputs compared
   byte for byte. Then every quoted number is recomputed and compared with `../../results/closed_forms_3/LRI_C5_d3_quoted.json`.
   Exit status 1 on any FAIL; table in `.work/replay/REPLAY_c5_d3.md`. Tolerances:
   - one unit in the last quoted digit for strings marked `\ldots` in the TeX;
   - correct rounding for table entries;
   - two significant digits for quoted deviations;
   - byte identity for regenerated records. For the reruns it falls back to the stated numeric tolerance if another
     mpmath version changes the last printed digit.
   One check needs the sibling package `../LRI_C5_general_d`: K3 against the 100-digit position-space value. It is
   SKIPped if that package is absent.
3. `make -f public.mk smoke` (15 s): fresh Q3, P4(3), P5(3) at 90 digits and a fresh K3 to about 10⁻¹¹⁰.

##### 3. Production chain (documented, not run in CI)

The production ran on one Slurm cluster with 64-core AMD EPYC nodes, plus a workstation. Templates with placeholders are in
`public/slurm/`. Measured wall times are given below; the total is about 120 core-hours.

| step | command (as run) | output | wall time |
|---|---|---|---|
| P0 primitive periods Q3, P4(3), P5(3) | `python inputs/general_d3/verify_d3.py` (bundle code; writes `verification/general_d3/` two levels up) | `period_values.json` (55 and 90 digits) | 5 s + 15 s for the periods; the identity and literal checks take longer |
| P1 spectral masters, run A | `hp_masters_d3.py run_A_dps50.json 50 64 44 64` (`slurm/c5d3_masters.slurm`) | `run_A_dps50.json` | 471 s, 64 cores |
| P2 spectral masters, run B | `hp_masters_d3.py run_B_dps56.json 56 80 52 72` | `run_B_dps56.json` | 657 s, 64 cores |
| P3 run C, b-circle | `hp_part.py run_C_b.json 110 128 110 72 b 0.02` (`slurm/c5d3_part.slurm`) | `run_C_b.json` | 1593 s, 64 cores |
| P4 run C, τ-circle | `hp_part.py run_C_t.json 110 128 110 72 t 0.02` | `run_C_t.json` | 3548 s, 64 cores |
| P5 run C combined | `hp_combine.py run_C_b.json run_C_t.json run_C_combined.json` | `run_C_combined.json` (K3, L3, Z3 to about 96 digits) | 1 s |
| P6 43-digit masters, PSLQ | `pslq_d3.py run_A_dps50.json run_B_dps56.json <BUNDLE>` | `masters_d3.json`, stdout = `pslq_d3.log` | 3 s |
| P7 C5(3) | `compute_c5.py <BUNDLE>` | `c5_value.json` | 1 s |
| K1 K3 to 430 digits | `cd wf_K3; python k3flint.py 1450 400 8000 330 500 run_hp3.json` and `... 1480 360 10000 300 560 run_hp4.json` | `run_hp3.json`, `run_hp4.json` → `K3_value.json` | about 100 s each, one core |
| K2 K3 integer relations | `cd wf_K3; python final_battery.py 420` (reads `K3_value.json`, `consts_480.json`, `lvals_440.json`) | `pslq_K3_results_420.json` | about 20 s of LLL (pslq_K3.log) plus building the constants |
| L1 L3 circles | `cd wf_L3; python pieces.py pA_dps170.json 170 280 116 208 0.04 64` and `pB_dps170.json 170 320 128 240 0.05 64` (`slurm/wf_job.slurm`) | `pA_dps170.json`, `pB_dps170.json` | 130 s and 120 s, 64 cores |
| L2 L3 constants | `python final_form.py pA_dps170.json L3_final_values.json; python tdform.py pA_dps170.json` (and `final_form.py pB_dps170.json L3_final_values_runB.json`) | `L3_final_values.json` | 1 s |
| L3 lattice reduction | `python battery_final.py 155` (and 125) | `battery_final_dig155.json`, `_dig125.json` | not recorded |
| Z1 Z3 circles | `cd wf_Z3; python zcircle.py circA2.json 260 560 170 120 0.001 0` and `circB2.json 270 700 210 128 0.0015 0.0123` | `circA2.json`, `circB2.json` | 215 s and 163 s, 64 cores |
| Z2 Z3 data | `python derive.py circA2.json derived_circA2.json` (and B2) | `derived_circ*.json`; `Z3_values.json` was assembled from these, rounded to 250 digits | 1 s |
| Z3 PSLQ on 𝔱₃'' | `python pslq_z3.py derived_circA2.json derived_circB2.json perB.json` | `pslq_z3_results.json` | not recorded (Slurm jobs) |

`<BUNDLE>` is a directory containing `lri_d3_reduction_update/verification/general_d3/period_values.json`. Use either the
exported `GFF/code/lri_d3_reduction_update` placed under such a directory, or a directory with a link to
`inputs/general_d3/period_values.json` at that path; `public/replay_c5_d3.py` does the latter.
`assemble_c5_d3.py <BUNDLE>` also needs
`lri_d3_matrix_update/code/general_special/coefficient_values_new.json` (the archived 11-digit nonprimitive values; kept in the public
export of that package by the bundle_d3 entry); it prints the symbolic d = 3 assembly that `make test` checks independently.

`wf_L3/L3_final_values.json` also carries `m0_mu1_weighted_h4_0`, `definitions` and `formulas`. These were added by
`check_m0.py` and by hand. The replay compares only the fields that `final_form.py` and `tdform.py` write.

##### 4. What a result must satisfy

- C5(3): the high-precision assembly and `c5_value.json` agree with the 50 quoted digits.
- The d = 3 form and the general form of gs:C5 agree exactly (SymPy) and numerically (better than 10⁻¹⁵⁰).
- K3 from runs hp3 and hp4 agree to better than 10⁻⁴³⁰.
- K3, L3 and Z3 agree with the spectral runs A/B (43 digits) and C (about 96 digits).
- The printed reduced forms of Q3, Z3, S'(3/2), L3 and P4(3) hold with the stored values to the stored precision.

##### 5. Decisions not to make alone

- Do not quote more digits of C5(3) than 50 without an independent P5(3) beyond 10⁻⁵³.
- Do not present the integer-relation results as independence proofs. They are bounds in the stated bases.
- The general-b half-shift steps behind the L3 and Z3 formulas are derived but not written out. Do not call them proved.

## C6(1) and its analytic representation

### `LRI_C6_1D_HPC`

Folder: `code/LRI_C6_1D_HPC/`.

#### Reproducing C6(1) (`GFF/code/LRI_C6_1D_HPC`)

Work from `GFF/code/LRI_C6_1D_HPC`. Follow the steps in order. Steps 1–3 need no cluster.

##### 1. Environment

- Python 3.10 or later with mpmath (1.2 or 1.3), numpy and sympy (`public/requirements.txt`).
  - Tested: Mac arm64 with Python 3.10.11, mpmath 1.2.1, numpy 1.23.5, sympy 1.11.1.
  - The production ran with Python 3.11.4, numpy 1.24.3 and mpmath 1.3.0 (module `anaconda3/2023.07-2` on
    symmetry).
- For `smoke` and the production: x86-64 Linux with AVX2 and FMA (`-march=x86-64-v3`), g++ 11 or later with OpenMP.
  The production used gcc 11.2.0.
- The 80-bit long double is required by the engine `bin/c6sum_ld` and by the long-double half of `rerun-lower`. It
  exists only on x86-64; on arm64 `long double` is binary64.

##### 2. Tests and replay (minutes, one core)

```sh
make -f public.mk test      # about 10 s
make -f public.mk replay    # about 40 s
```

What `replay` does (expected: 124 PASS, 0 FAIL, 0 SKIP, 1 FLAG):
- **Integrity.** It checks every hash binding between the shipped records, level files and run files.
- **Bitwise regeneration.** It reruns `tools/assemble.py`, `tools/rounding.py` and `tools/analyze.py` on
  `GFF/data/C6_1/levels`, and regenerates byte for byte:
  - `assembled.json`, `rounding.json` and `decision_N22.json`;
  - the three earlier decisions, from the level sets as they stood at N* = 16, 18 and 20;
  - `C6_final.json`, after undoing the one documented diagnostic change of commit ee2e013 (see PROVENANCE).
- **Merge.** `tools/merge.py` re-merges all 62 levels from the 84 run files.
- **Weights.** `tools/weights.py` regenerates all 21 weight tables with the manifest hashes.
- **Results-review records.** It rebuilds the RR-001 propagation (`tools/lowercmp.py`) and the RR-002 C7
  cross-check (`tools/c7_crosscheck.py`), and replays the exact RG-algebra check and the lower-degree assembly
  records.
- **Quoted numbers.** It compares every number quoted in note Sections 1, 1.2 and 22 and in `REPORT.md` at its
  printed precision. `results_map.md` maps each number to its record.

The FLAG marks the note sentence "From M = 24 onward, successive changes of C6 are below 1e-11" (Sec 22.4). The
records give up to 4.35e-9, which is U5/2. A FLAG is not a failure.

The RR-002 rows need `C7_final.json` of `LRI_C7_HPC` (sha256 `b44b3a13…`). It is searched at
`../../results/C7_1/` and `../LRI_C7_HPC/results/2026-09_expanse_v2/`; set `C7_FINAL=<path>` to point elsewhere.
If it is absent, those rows are SKIP.

Tolerances:
- **bitwise** (sha256) for every regenerated record. These are deterministic: mpmath at fixed precision, IEEE
  float64, and identical bytes on Mac arm64 and on symmetry x86-64.
- **printed** for quoted numbers: the record value must round to the printed digits.
- The algebra check falls back to symbolic equality if another sympy version prints the polynomial in another term
  order.

##### 3. Optional checks on x86-64 Linux (passed on symmetry: smoke 7 PASS, rerun-lower 3 PASS)

```sh
make -f public.mk smoke THREADS=<cores>   # 1-3 min (estimate; not yet run)
make -f public.mk rerun-lower             # about 30 s
```

**`smoke`** builds the engines with the package Makefile in `.work/smoke/pkg`. It then:
- enumerates the five-loop graphs: `graphs6.bin` must have the approved sha256;
- generates `w_5_12` with the manifest hashes;
- reruns L5 M = 12 (H and J modes) with `c6sum_ld` and `c6sum`;
- compares the result with the production long-double levels, to 1e-14 relative for long double (the V11
  cross-vendor tolerance) and 1e-9 for double (the V4b tolerance).

**`rerun-lower`** repeats RR-001: `tools/lowercheck.py` at degree 28 in long double and in float64.
- Long double must reproduce `lower28_ld.json` to 1e-15 relative.
- float64 is platform dependent: Mac arm64 gives 2.5e-12 relative to the symmetry run, and |R6_f64 − R6_ld| =
  8.0e-9 instead of 5.95e-8.
- U must stay at 4.9e-7.

##### 4. Production rerun (Slurm)

###### Cost and nodes

The production used whole 64-core nodes of symmetry's `amdq` partition (dual AMD EPYC 7532/7543, 64 threads,
`--exclusive --mem=180G`; the engines need a few GB). Validation also used one 40-core Intel Xeon Gold 6148 node
for the cross-vendor gate V11. At most 12 nodes ran concurrently.

| Stage | Command | Node-hours (64-core) | Core-hours | Wall time on symmetry |
|---|---|---|---|---|
| validation (gates V1–V11) | `cluster/validate_all.sh` | about 10 | about 600 | 0.9 h |
| A: L6 N = 6–16, L5 M = 12–40, calibration, replicates | `cluster/production.sh A` | 10.4 | 660 | 2.6 h on ≤ 12 nodes |
| N = 18 | `cluster/production.sh N=18` | 6.6 | 420 | 1.3 h on ≤ 11 nodes |
| N = 20 | `cluster/production.sh N=20` | 10.8 | 690 | 1.5 h |
| N = 22 | `cluster/production.sh N=22` | 16.7 | 1070 | 2.5 h |
| **production total** | | **44.5** | **≈ 2,850** | 7.9 h |

The production node-hours come from the per-sector timings in `GFF/data/C6_1/runs` (44.3). Slurm accounting gives
44.489 (`resources_N22.json`). The validation figure is the operator's estimate in REPORT.md; no record of it
ships. Budget about 3,500 core-hours in total, plus restarts. The stopping rule also caps the campaign:
production above 400 node-hours, or a projected next degree above 36 h on 12 nodes, ends it.

###### Site setup

The scripts in `cluster/` are the ones that ran on symmetry (Slurm 21.08). Their site lines are:
- the campaign directory `/mnt/beegfs/…/lri_c6_1d`;
- the modules `gcc/11.2.0 anaconda3/2023.07-2`;
- the partitions `amdq`, `defq`, `debugq`, `amddebugq` and `sharedq`;
- `--mem=180G`.

Do not edit `cluster/`. Instead, make a site copy:

```sh
cp public/slurm/site.env.example site.env    # fill in <SCRATCH>, <ACCOUNT>, <MODULES>, <PARTITION>,
                                             # <DEBUG_PARTITION>, <SHARED_PARTITION>, PART_XARCH, MEM, RECON_FILE
python public/slurm/adapt.py site.env <SCRATCH>/lri_c6_1d/code/rev1
ln -sfn rev1 <SCRATCH>/lri_c6_1d/code/current
export C6_CODE=<SCRATCH>/lri_c6_1d/code/current
```

`adapt.py` changes only the lines listed in `SITE_CHANGES.txt` of the copy, and refuses if a pattern does not match.
It also adds `cluster/analyze_stage.sh`. Two gates may be dropped, and a dropped gate must be reported with the
result:
- **`V3_all_N6_vs_recon_compensated`** is dropped unless `RECON_FILE` is given. Its recon record was never copied
  off symmetry. The gate `V3_all_N6_vs_reference` against the shipped record remains.
- **The cross-architecture job and its four V11 gates** are dropped unless `PART_XARCH` names a partition whose CPU
  vendor differs from `PART_MAIN`.

###### Run

```sh
# 1. validation: a fresh attempt; writes <SCRATCH>/lri_c6_1d/validation/APPROVED.json only if every gate passes
bash $C6_CODE/cluster/validate_all.sh
# 2. stage A (degrees 6-16 are unconditional)
bash $C6_CODE/cluster/production.sh A
# 3. when all stage-A jobs have finished: final-mode analysis at N* = 16 and the stopping decision
sbatch -p <SHARED_PARTITION> -o <SCRATCH>/lri_c6_1d/logs/%x_%j.out \
       --export=ALL,C6_CODE=$C6_CODE,N=16 $C6_CODE/cluster/analyze_stage.sh
# 4. if decisions/decision_N16.json says continue: next degree, then analyse it; repeat until 'stop'
bash $C6_CODE/cluster/production.sh N=18      # then analyze_stage.sh with N=18, production.sh N=20, ...
```

- `production.sh N=<n>` refuses to run without a matching "continue" decision at n − 2.
- On symmetry an operator driver (`ops/driver.sh`, not part of the package) ran steps 3–4 automatically. It
  called only the scripts above.
- The original run continued at 16, 18 and 20 and stopped at 22.

###### Compare with the published result

```sh
make -f public.mk compare-rerun RERUN=<SCRATCH>/lri_c6_1d/analysis/C6_N22.json
```

The comparison requires:
- the same N* = 22, stopped by rule (a);
- each C6^χ(N) within 4ρ(N) of the published value (different executables change the sums only at the rounding
  level);
- the headline within U = 4.9e-7.

Report the result; do not repair a disagreement (AGENTS.md rule 4).

###### Decisions you must not make

These are fixed by the pre-registration (`GFF/results/C6_1/PLAN.md` Sec 4.5 and 4.6) and are part of the result:
- the estimator and the allowance with its six terms;
- ρ(N) with its calibration (N = 6, 8, 10) and the mod-10 subset;
- the stopping rule (N ≥ 16; rules (a)–(d));
- the L5 degrees M = 12, 16, …, 40 and the M = 40 replicate;
- the gate tolerances.

Also:
- Do not quote an extrapolated value.
- Do not reuse levels from another campaign or validation attempt.
- Do not mix executables within one campaign.

### `C6_research_note`

Folder: `code/C6_research_note/`.

#### Reproduce: analytic representation of C6(1)

Packages: `GFF/code/C6_research_note` (the calculation) and `GFF/code/LRI_C6_closed_form_review` (its independent
review). Comparison targets: `GFF/results/C6_1/analytic/quoted_numbers.json`. The graph-sum record used for the
comparison is the one of `LRI_C6_1D_HPC` (`C6_final.json`); the replay looks for it at `GFF/results/C6_1/C6_final.json`
and at `GFF/code/LRI_C6_1D_HPC/results/2026-09_symmetry/C6_final.json`, or takes `GRAPH_SUM=<path>`.

There is no production campaign: every computation of this package runs in seconds to minutes on one core.

##### 1. Environment

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r GFF/code/C6_research_note/requirements.txt      # mpmath==1.3.0 sympy==1.14.0 matplotlib==3.10.8
    pip install numpy scipy                                        # only for the review's rerun (two-fold integrals)

The package was run with Python 3.13.5 on Linux (`provenance/environment.json`); the review with Python 3.10.12,
mpmath 1.3, sympy 1.12, scipy 1.11, numpy 1.24. The public targets were tested with Python 3.10.12, mpmath 1.3.0,
sympy 1.12. The `note` target needs pdflatex with the packages listed in the package README.

##### 2. Test and replay (any machine, seconds)

    make -C GFF/code/C6_research_note -f public.mk test
    make -C GFF/code/C6_research_note -f public.mk replay
    make -C GFF/code/LRI_C6_closed_form_review -f public.mk test
    make -C GFF/code/LRI_C6_closed_form_review -f public.mk replay

Expected: `C6_research_note public test: PASS 13 FAIL 0`, `C6_research_note public replay: PASS 29 FAIL 0`
(28 PASS and 1 SKIP if the graph-sum record is not found; the pinned value is then used),
`LRI_C6_closed_form_review test: PASS 2`, `replay: PASS 9`. The tolerances are in `results_map.md` and in the tables.

##### 3. Fresh run of the final method (cluster node, minutes)

`rerun-final` copies the package to `.work/rerun/pkg`, runs `code/reproduce_final.py` without `--resume` (22 tasks:
7 core numerical/interval tasks, 12 exact algebra tasks, 3 Barnes comparisons), reruns `code/make_outputs.py` on the
fresh records and compares every task output with the shipped one: bitwise for the exact dyadic certificates, 1e-30
relative for floating values, timing fields ignored.

    make -C GFF/code/C6_research_note -f public.mk rerun-final          # or: sbatch public/slurm_rerun_final.sbatch

Cost: 1 core, < 1 GB, about 2-4 min (70 s of task time on the delivering sandbox; the longest task, `complete_refined`,
12 s there). About 0.05 core-hours. Expected: `PASS 27 FAIL 0 INFO 1`.

##### 4. Fresh run of the review's checks (cluster node, 10-25 min)

    make -C GFF/code/LRI_C6_closed_form_review -f public.mk rerun        # or: sbatch public/slurm_rerun.sbatch

`public/rerun_checks.py` copies `checks/` to `.work/checks`, deletes the recorded outputs in the copy, rewrites the
reassembly path of the two `assemble.py` copies to `$C6_REASSEMBLY`, runs the 49 commands (reconstructed from the
names of the recorded outputs; the review did not record command lines) and then the same replay on the fresh outputs.
The 17 algebra scripts and a few others have no recorded outputs; for them only the exit status is checked and their
stdout is kept in `.work/checks/` for reading. Two `gvals_meijerg.py` values are expected to time out after 50 s
(mpmath `meijerg` for G6 and G8 at 20 digits, as recorded); this is not a failure. Cost: 1 core, < 2 GB, about 0.4
core-hours. Expected: `rerun_report: PASS 9 FAIL 0`.

##### 5. Slurm templates

`GFF/code/C6_research_note/public/slurm_rerun_final.sbatch` and
`GFF/code/LRI_C6_closed_form_review/public/slurm_rerun.sbatch` have placeholders `<ACCOUNT>`, `<PARTITION>`,
`<SCRATCH>`; they request 1 core and 4 GB with a 30 min or 1 h limit (use the site's rule where it differs, e.g. no time
limit on a personal desktop). Submit from the package folder.

##### Decisions you must not make

- Do not change the 22-task selection of `code/reproduce_final.py`, the precisions or tail parameters of the stage code,
  or the tolerances of the verifiers.
- Do not regenerate `MANIFEST.sha256` or `provenance/source_manifest.json`; they are the delivered integrity records.
- Do not treat the interval certificate as a proof of the physical coefficient: it encloses the reduced expression as
  stated, conditional on the identities the package uses and on its stated tail allowance for M7.

### `LRI_C6_closed_form_review`

Folder: `code/LRI_C6_closed_form_review/`.

_no separate text._

## Finite kernels, power compensation, C6(2) and C6(3)

### `lri_C6_d2_complete_update`

Folder: `code/lri_C6_d2_complete_update/`.

#### Reproducing the d = 2 power-sector compensation (GFF/code/lri_C6_d2_complete_update)

Everything runs on one machine with Python ≥ 3.8 and mpmath, sympy, networkx (`requirements.txt`). No compiler, no
scheduler and no hosted data are needed. Every target writes only under `public/out/`.

```bash
cd GFF/code/lri_C6_d2_complete_update
python3 -m venv .venv && . .venv/bin/activate && pip install 'mpmath>=1.2' 'sympy>=1.11' 'networkx>=2.8'   # versions checked: requirements.txt
make -f public.mk test      # ~3 s: SHA256SUMS binding, two-loop jets, 192 fixed-point checks, KLT checks
make -f public.mk replay    # ~5 s: 64 rows; exit 1 on any FAIL; table on stdout, public/out/replay.json
make -f public.mk regen     # ~4 min, 4 processes: regenerate every power-sector counterterm, recompute Delta_p
make -f public.mk regen-cold  # kite jets recomputed as well (about 6-7 min on symmetry)
```

`replay` reruns the delivered scripts of `reproduction/` in a writable copy:
- `power_cancellation.py` in both Cauchy settings;
- `audit_analytic_extension.py`, `check_gamma_coverage.py`, `klt_checks.py`, `fresh_two_loop_mom.py`,
  `check_mom_lagrange.py`.

It compares each output field by field with `GFF/results/C6_2/power_compensation/`, then checks each number the note
quotes at its printed digits (Secs 24.1–24.3, 25.1–25.3). Three optional rows (SKIP if absent) tie the result to other
packages:
- `GFF/code/LRI_C6_D2_HPC/inputs/two_loop.json` and that package's byte copies of the power records;
- `GFF/results/C6_2/C6_result.json`;
- the explicit sixth-order power correction in `GFF/results/C7_2/C7_result.json`.

Override paths with `make -f public.mk replay C6=... C7=... HPC=... RESULTS=...`.

`regen` reruns the original chain from the classified graph inventory:
1. `sp_ms.py 90`;
2. `sp_exact.py`;
3. `check_gamma_coverage.py`;
4. `position_ms.py`;
5. `position_kite_leaf_ms.py` with `KNODES/KDPS/KRAD` = 32/45/.02 and 48/55/.016;
6. `power_cancellation.py` in both settings, then `audit_analytic_extension.py`.

Each regenerated record is compared with the shipped one. `regen-cold` first deletes the 164 cached kite jets.

##### Production

There is no production campaign. The quantities are deterministic special-function and exact-arithmetic evaluations:
`regen-cold` is the full recomputation from the graph inventory. The graph inventory itself
(`classified_inventory.json`) was generated in earlier packages of the research archive and is shipped as an input. Its
six-loop part agrees with the inventory that the C6(2) and C7(2) packages use: the C7(2) builder regenerates and matches
all 492 kernels of loops 3–6 (`GFF/code/LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/verification/legacy_mapping.json`).

Slurm is not needed. On a cluster, wrap `regen-cold` in a single-node job with 4 CPUs:
`sbatch -A <ACCOUNT> -p <PARTITION> -N 1 -c 4 --mem=4G -t 02:00:00 --wrap 'make -f public.mk regen-cold'`, run from a copy
of this folder under `<SCRATCH>`. The expected cost is under 2 core-hours.

##### Tolerances

- All reruns were string-identical to the delivered records under both stacks checked (Python 3.10.11 with mpmath 1.2.1,
  sympy 1.11.1, networkx 2.8.4; Python 3.10.12 with mpmath 1.3.0, sympy 1.12, networkx 2.8.8). Only wall-clock `seconds`
  and one prose `scope` field differed.
- On symmetry (Python 3.12.9, mpmath 1.3.0, sympy 1.14.0, networkx 3.7), test, replay and the warm regen were
  string-identical. After the cold kite recomputation, three diagnostic fields moved at rounding level (CLUSTER_CHECKS.md).
- Value fields (counterterms, Laurent coefficients, sums, jets) pass if string-identical, or if
  |new − recorded| ≤ 10^−(dps−10) × the magnitude of their record entry (the largest |value| of the graph, loop or
  record they belong to; dps is the record's working precision). A near-zero combination such as the vanishing simple
  pole of L5G121 is thus compared at the precision of its graph. Without gmpy2 (pure-Python mpmath), after a cold kite
  recomputation, or under another Python hash seed (the audit sums over a set), last digits move at this level
  (CLUSTER_CHECKS.md). Diagnostic fields (route and root discrepancies, symbolic-vs-numeric errors, KLT errors, Delta_p; `DIAG` in
  `public/common.py`) pass when the new value is at most max(100 × recorded, 1e-40, the note's bound, 1e-30 for
  Delta_p); the row reports the value.
- Quoted numbers are compared after half-even rounding to the printed digits.

### `lri_C6_d3_complete_update`

Folder: `code/lri_C6_d3_complete_update/`.

#### Reproduce: lri_C6_d3_complete_update (d = 3 power-sector compensation, audit subset)

**Inputs.** All shipped:
- the six-loop graph inventory with rational weights and power-subgraph flags (`inputs/classified_inventory.json` and
  its vendored copy);
- the power-free forest-kernel lists (`inputs/forest_L2..6.txt`);
- the Gamma jets to be checked (`records/gamma_jets.json`).

**Full regeneration of every quoted number = `make -f public.mk replay`.** The replay reruns, in a copy under
`.work/pkg/`, the package's own commands (README.md, "Reproduce the analytic power-target audit" and "Independent
numerical and algebraic checks"):

```sh
POWER_DPS=90 CORE_U0=101 CORE_U1=-37 POWER_OUTPUT=power_ms_d3_shifted.json python code/power_ms_d3.py     # about 20-30 s
python code/analyze_power.py power_ms_d3_shifted.json
POWER_DPS=75 CORE_U0=0 CORE_U1=0 POWER_OUTPUT=power_ms_d3_complete.json python code/power_ms_d3.py        # about 15-40 s
python code/analyze_power.py power_ms_d3_complete.json
POWER_Q=7 POWER_P4=11 POWER_KAP=5 POWER_Z=13 CORE_U0=-17 CORE_U1=29 POWER_DPS=65 \
  POWER_OUTPUT=power_ms_d3_arbitrary_masters.json python code/power_ms_d3.py                                # about 15-25 s
POWER_Q=7 POWER_P4=11 python code/analyze_power.py power_ms_d3_arbitrary_masters.json
python code/check_mom_d3.py; python code/check_unknown_core.py; python code/power_assembly_polynomial.py
python code/check_gamma_d3.py; python code/two_loop_d3.py; python code/check_core_propagation.py; python code/check_coverage.py
```

The package README writes the 75- and 90-digit outputs as `power_replay_75.json` and `power_replay_90.json`. The
replay uses the record names instead, so that `check_core_propagation.py` and `check_coverage.py` read the reruns. It
then compares everything with `records/` and with the note.

**Machine.** One core, under 1 GB, about 2 minutes. No compiler, no Slurm job needed. On a cluster:

```sh
srun -A <ACCOUNT> -p <PARTITION> -c 1 --mem=2G -t 00:15:00 make -C code/lri_C6_d3_complete_update -f public.mk replay
```

**Expected output.** `.work/REPLAY.md` with 68 PASS, 0 FAIL. With mpmath 1.3.0 all 931 per-graph numbers of each audit
were bitwise equal to the delivered records.

**Not reproducible from the release (by design).** The first full C6(3) Monte Carlo estimate of this package (33.50 ± 0.6,
14 September 2026) is superseded and not quoted by the note. Its sampler and batch data are not shipped. They remain in
the research bundle and in `LRI_C6_D3_HPC` at 1c6dfb3, under `reference_d3/`. The quoted C6(3) is reproduced by
`GFF/code/LRI_C6_D3_HPC`.

### `LRI_C6_D2_HPC`

Folder: `code/LRI_C6_D2_HPC/`.

#### Reproducing C6(2) (GFF/code/LRI_C6_D2_HPC)

All commands run in `GFF/code/LRI_C6_D2_HPC/`. Placeholders: `<ACCOUNT>`, `<PARTITION>`, `<SCRATCH>` (a shared
file system visible from all compute nodes), `<PYTHON>` (Python >= 3.10 with `requirements.txt`).

##### 1. Replay (minutes of human time, about 1 s of CPU; any OS)

    make -f public.mk replay PY=<PYTHON>

Recombines the 8 merged records of `../../data/C6_2/run-20260928-m8192/` with the production's assembler
(`tools/assemble.py` at 6aaf656, 4,096 bootstrap resamples), compares every field of `../../results/C6_2/C6_result.json`,
and recomputes the numbers the note quotes for C6(2): the value and allowance, the campaign table, the pulls (campaigns,
previous estimator, C3-C5, the C7(2) by-product from `../../results/C7_2/C7_result.json`), the error budget, the
bootstrap, the sample design, the zero C6 projection of the 28 floor-sampled kernels, and the recorded thread-identity
check. Output: a PASS/FAIL table on stdout and `public/out/replay.json`; exit 1 on any FAIL. Three rows are SKIP: the
task tables, Sobol nets and checkpoints are hosted and are checked by `remerge`.

**Tolerances.** Merging is exact (decimal sums at 50 digits; `remerge` reproduces the merged records byte for byte).
The assembly is float64 numpy, so its last bits depend on the numpy and BLAS build, and the replayed result is not
bit-for-bit identical in general (on macOS with numpy 1.24 and 1.26 C6 is identical and the SE one ulp off; with numpy
1.23 C6 is 3e-16 relative off). Replay therefore uses: relative 1e-12 for the headline fields (C6, its SE, coefficients
and their SEs, campaigns, jet means, error by loop, the estimates in the lower-order checks); relative 1e-7 for other
numbers above 1e-9 (covariances, pulls and the bootstrap, where cancellation amplifies rounding: up to 1.8e-10 seen);
absolute 1e-22 for entries below 1e-9 (covariances of the low orders, smallest nonzero 1.6e-15); exact for strings and
hashes; the 17-digit estimator of Section 1 to relative 1e-12; every other quoted number at the digits the note prints.
Checked with numpy 1.23.5, 1.24.4 and 1.26.3 (Python 3.10/3.11, macOS arm64): 75 PASS, 3 SKIP, 0 FAIL each.

##### 2. Integrity (seconds; any OS)

    make -f public.mk integrity PY=<PYTHON>

Checks every released file listed in `SHA256SUMS_HPC.json` (the package's list at 6aaf656; `benchmarks/` and a stray
duplicate list are not released, and the six files whose account and scratch-path examples were scrubbed, also named
in `public/SCRUBBED.txt`, are reported, not failed; `SCRUBBED.txt` may not name `src/`, `inputs/`, `reference/`, the
Makefile or the five tools the plan pins) and all 787 files of `reference/SHA256SUMS.json`.

##### 3. Tests (x86-64 Linux node, 8-16 cores)

    module load <gcc 13 or later> <boost>          # g++ with OpenMP and libquadmath; Boost.Multiprecision headers
    python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
    make -f public.mk test PY=python3              # about 1 min (a personal workstation, 8 cores: 3 s build + 25 s; Expanse, 16 cores: 7 s + 52 s)
    make -f public.mk test-all PY=python3          # + test-workflow, test-points, test-levels, test-e2e: about 2 min more
    make -f public.mk smoke PY=python3             # the workflow test alone (a tiny campaign through the real worker)

The kernel requires a `long double` with at least 64 significant bits and the extended exponent range (x86-64); it does
not compile on arm64. On other machines `make -f public.mk test-python` runs the pure-Python suites (about 40 s of CPU on
macOS with numpy 1.24.4 and scipy 1.11.1). `test` compares the new kernel with the original code of `reference/code/`,
built in a temporary folder; expected: all 492 kernels agree to normalized differences below 9e-20 with equal binary128
and 300-digit fallback counts. The executable built on Expanse with GCC 13.3 has sha256 5818340b35b39430...; other
toolchains give other hashes, which is expected (the plan pins the hash only for running its own campaign).

##### 4. Re-merge from the hosted run (about 20 s, 0.8 GB of disk)

    make -f public.mk fetch-data                   # prints where the archive is; unpack to ../../data/C6_2/hosted/
    make -f public.mk remerge PY=<PYTHON>

Checks the 1,038 hosted files against `../../data/C6_2/hosted_run-20260928-m8192.sha256`; checks that the shipped
records equal the hosted ones; copies the run to `public/out/remerge/work/` without its merge outputs; runs the unmodified
`tools/production.py status` (996 of 996 blocks) and `tools/production.py merge`; compares the 8 `merged.json` and 8
`graph_replicates.csv` byte for byte with the shipped ones; runs the unmodified `tools/assemble.py --bootstrap 4096
--output ...` (which also checks the task tables) and the replay on the re-merged copy, with the assembler's output
compared field by field. Checked on macOS (numpy 1.26.3): all files byte-identical, 16 s.

##### 5. Production rerun (not part of CI)

The production used 428 array elements of 64 cores (8 GB each, at most 2:10:00), 12,535 core-hours in about 4 hours with
64 elements at a time. A new campaign needs a fresh seed; it gives a statistically equivalent, not identical, result.

    # once per site: an environment script for the jobs (modules + the venv), e.g. from slurm/expanse_env.sh.example
    export C6_ENV_SETUP=<SCRATCH>/c6_env.sh && source $C6_ENV_SETUP
    make clean && make && make test
    export C6_PACKAGE=$PWD C6_RUN=<SCRATCH>/c6-d2/run-$(date +%Y%m%d)
    python3 tools/production.py plan "$C6_RUN" --seed $(python3 -c 'import secrets; print(secrets.randbits(63))') \
      --replicates 64 --multiplier 8192 --primitive-points 65536 --chunk-points 8388608 \
      --threads 64 --checkpoint-tasks 1024 --shards 200
    C6_SBATCH_ARGS="-A <ACCOUNT> -p <PARTITION>" slurm/submit.sh --mem=8G
    python3 tools/production.py status "$C6_RUN"   # committed/total blocks; exit 0 when complete
    # a failed element: scancel the pending merge, then (same environment)
    C6_SBATCH_ARGS="-A <ACCOUNT> -p <PARTITION>" slurm/resubmit.sh --mem=8G

`slurm/merge.sh` (submitted by `submit.sh` with `afterok`) merges the groups and writes `C6_result.json` with 4,096
bootstrap resamples. Keep `-c`, `--time` and `--mem` out of `C6_SBATCH_ARGS` (it is also applied to the merge).

**Warnings for new campaigns with this code (6aaf656).** Four defects of the submission and merge layer were found after
the production (they did not affect it): there is no per-campaign submission lock (submit one window at a time and do not
run `submit.sh` and `resubmit.sh` concurrently); two merges running at once can crash while writing `merged.json` (run
one merge); the SQLite URI is not escaped and Slurm expands `%` in log paths (use a campaign path without `#`, `?` or
`%`). The release ships the code as it ran.

**Thread-identity check** (the preflight of Section 24.6; one node of 64 cores, about 2 minutes):

    W=<SCRATCH>/c6-d2/threadcheck
    for d in A B; do python3 tools/production.py plan $W/$d --seed <any> --replicates 4 --multiplier 64 \
      --primitive-points 65536 --chunk-points 65536 --threads 64 --checkpoint-tasks 1024 --shards 4; done
    # indices of shard 0 of a_L6 and b_L6 from $W/A/manifest.json ("jobs"), then for each index i:
    python3 tools/production.py run $W/A --index $i --threads 64 --max-blocks 1
    python3 tools/production.py run $W/B --index $i --threads 16 --max-blocks 1
    # compare the checkpoint rows of A and B in the fields uid rep graph begin end total values quad mp max_abs:
    # all equal (the production's check: 2,048 rows, 152,717 binary128 promotions)

**Re-running archived blocks bit for bit** (optional; needs the hosted run and an executable with the plan's sha256
5818340b..., which the Expanse toolchain above produced): copy the hosted run directory, delete one checkpoint
`groups/<g>/checkpoints/s<shard>_p<part>.json`, run `python3 tools/production.py run <copy> --index <job> --threads 64`
(it recommits only the missing block), and compare the scientific row fields of the new checkpoint with the original.
With any other executable `run` refuses the plan.

**Boost headers.** On Expanse the `boost/1.86.0` module sets only `BOOST_ROOT`, and the build adds no `-I`; the
production may therefore have compiled against the system Boost headers. Check with
`echo '#include <boost/version.hpp>' | g++ -E -x c++ - | grep -m1 'boost/version.hpp'` in the same environment.

### `LRI_C6_D3_HPC`

Folder: `code/LRI_C6_D3_HPC/`.

#### Reproducing C6(3) (fragment for GFF/REPRODUCE.md)

Package `GFF/code/LRI_C6_D3_HPC` (commit `1c6dfb3`), records `GFF/results/C6_3/`, hosted data `GFF/data/C6_3/`.
Run every target from the package folder: `make -f public.mk <target>`. Nothing is written outside `.work/` and
`bin/` (and the `reference` link made by `setup`).

**Prerequisite: `GFF/code/LRI_C6_D2_HPC` must be present.** The two packages share one byte-identical `reference/`
tree (the archived refinement and baseline calculation, 148 MiB). `make -f public.mk setup`, which every target runs
first, creates the link `reference -> ../LRI_C6_D2_HPC/reference`. The paths the package records are relative
(`reference/...`, e.g. in `inputs/manifest.json`), so the link changes no hash: `tests/check_inputs.py` regenerates
`inputs/` through it byte for byte.

##### 1. Environment

| need | production (Expanse, 2026-09-29) | also tested |
|---|---|---|
| Python | 3.11.9 | 3.10.12 (replay, pure-Python tests; macOS arm64) |
| numpy, scipy, mpmath | 1.26.4, 1.17.1, 1.3.0 | numpy 1.24.4, scipy 1.11.1 |
| sympy, networkx | (point checks only) | 1.14.0, 3.6.1 (delivery) |
| C++ | GCC 13.3 with OpenMP and libquadmath, Boost headers (`cpu/0.21.2a gcc/13.3.0 boost/1.86.0`) | GCC 13.3 (personal desktop, Ubuntu), GCC 14.2 (delivery) |

- `pip install -r requirements.txt` (version floors). The worker builds only with GCC on GNU/Linux (`make`); the
  numerical flags `-fopenmp -ffp-contract=off -fno-fast-math` are always appended. No binary is shipped.
- The production binary has sha256 `2f897044df1aa6ed91ca5cd70d2c1af6287a77bca16dfcad108386fcae60c698` (Expanse,
  GCC 13.3, default flags). The baseline and final sources build to this identical binary. The package `Makefile`
  passes no Boost include path, so on Expanse the compiler may take the system Boost headers rather than the module's.
  The binary hash, not the module list, identifies the production build.
- The assembly is float64 with BLAS-dependent last bits. Recomputations agree with `C6_result.json` to about 1 ulp
  (33.57542664131542 on Apple arm64 vs 33.57542664131543 on Expanse). The replay tolerances allow for this.

##### 2. Tests

| target | runs | node | measured |
|---|---|---|---|
| `test-python` | `public/verify_shipped.py`; the package's `make test-python`: archived assembly (four archived campaigns to 1e-12), inputs regeneration (501 files byte-identical), legacy seed replay of an archived net, dimension and normalization checks (80-digit), orchestration with a fake worker (13 groups of checks) | any OS, 1 core | 72 s (Apple M-series) |
| `test` | the same plus the C++ build and `tests/validate.py` (new worker vs the original code on all graphs, random access, threads, frozen grid, rejected inputs, fixed point vs the archived assembly) | Linux, 2–16 cores | build 7 s + 62 s on 16 cores (Expanse shared, 32 GB) |
| `smoke` | `tests/workflow.py`: tiny campaigns through plan, run, merge and assembly with the real worker; restart, duplicates, failures, tampering | Linux | 35 s on 16 cores |
| `test-all` | `test` plus workflow, high-precision point checks (`test-points`), forced binary128/300-digit tiers (`test-levels`), original code vs the full pipeline (`test-e2e`), and the replay of the eight archived production streams (385,744,896 samples; fallback counts equal, refinement-only C6(3) = 33.560840352429125 to 1e-13, bitwise on Expanse and on a personal desktop) | Linux, 16 cores, 32 GB | about 6 min (Expanse job 54510646) |

A Slurm template is `public/slurm/test_all.slurm` (placeholders `<ACCOUNT>`, `<PARTITION>`, `<LOAD_MODULES>`,
`<VENV>`, `<GFF>`). The expected outputs on the reference platform are the logs in
`benchmarks/expanse_2026-09/logs/validation_54510646/`.

##### 3. Replay (`make -f public.mk replay`, about 2 s, one core, any OS)

`public/replay_c6_3.py` reads `../../results/C6_3/results_run-20260929-m8192` and writes `.work/replay/REPLAY_C6_3.md`
(PASS/FAIL table) and `.work/replay/C6_result_replayed.json`. It exits 1 on any FAIL. Rows (52 in all):

- **A. Records.** `production.verify_base`: the four tools and `inputs/manifest.json` match the hashes frozen in
  `manifest.json`. Every group's `config.json` matches its manifest hash. `production.validate_merged` checks each
  `merged.json` (schema, plan hash, config hash, payload hash, `graph_replicates.csv` hash). The `merged.json` hashes
  and the manifest hash equal those recorded in `C6_result.json`. The task databases are checked only with the full
  run directory (SKIP otherwise).
- **B. Design.** 5/16/76/395 kernel classes; the ten primitives included; every stratum equal to the frozen
  allocation × 2¹³; the points per replicate; 6,320,161,816,576 samples; 64 replicates; seeds, layout, rate, grid and
  summation mode; 52/60 bits; weights ½; 458 × 64 jobs; the planned cost and projected SE; the 1e-9/1e-23 fallback
  thresholds in `src/kernel.hpp`.
- **C. Estimator.** `assemble.evaluate`, the package's own entry point, with the bootstrap of the production
  (4096 draws, fixed seed). For this call only, `production.group_of` is replaced by a copy that skips the absent
  task databases. Checked: C6 and SE against the note (relative 1e-12, and the printed digits); every field of
  `C6_result.json` (relative 1e-9; the bootstrap mean shift, a difference of two O(30) numbers, to 1e-12 absolute);
  the campaign values, error budget, C0–C2, the C3–C5 estimates, and the bootstrap.
- **D. Reporting rule.** 4 × SE = 0.00047, giving the Amendment 1 allowance 0.0005 (decimal arithmetic) and the
  registered allowance 0.001; reported value 33.5754 ± 0.0005.
- **E. Gates.** a/b 1.66; bootstrap ratio 0.973; 0.30 previous SE; pulls −1.69, −1.09, +0.92 with |pull| ≤ 4; the
  reference constants equal the note's C3–C5.
- **F. Precision statements.** SE / projection 0.54; previous SE / SE 204; 0.52 refinement SE from the refinement-only
  estimate.
- **G. Superseded estimates.** Recomputed with `assemble.combine` from the archived records in `reference/`, compared
  with `reference/verification/method_precision_results.json` (relative 1e-12) and the note's digits: refinement-only,
  refinement A and B, the previous four-campaign estimator, baseline A and B. The cited archived-stream replay record
  is checked (status, samples, fallbacks, bitwise flag), and its replayed value is compared with the recomputation.
  The two previous-estimator diagnostics (Lagrange 5e-14, delete-one bias below 6.5e-8) are read, not recomputed.
- **H. Independent comparison.** The C7(3) by-product and its −0.79 pull. It is read from
  `../../results/C7_3/run1-20260930-m4096/C7_result.json` (`C7_RESULT=` to override), or from the note's
  values if that file is absent.

Tolerances: hashes, counts and design values are compared exactly. Recomputed floats get a relative tolerance of 1e-12
(estimator, SE) or 1e-9 (all other fields), well above the 1–4 ulp CPU dependence and far below every printed digit.
Quoted numbers are compared at the printed precision.

**Full replay from the checkpoints** (`make -f public.mk replay-full`, needs `fetch-data`; 53 s on one core of a
symmetry Intel node, 2026-10-19: 60 PASS, 0 FAIL, with the tarball fetched from a stand-in for the Zenodo record). The target extracts the run directory
into `.work/full/`, rebuilds every `merged.json` and `graph_replicates.csv` from the 1060 checkpoints with
`tools/production.py merge` in a scratch copy, and requires their sha256 to equal the production ones. It then runs
every row above, including the task-database hashes, and calls `assemble.load_campaign` unpatched.

##### 4. Production (documented, not run in CI)

The production ran on SDSC Expanse (AMD EPYC 7742, shared partition) on 2026-09-29, from 07:08 to 10:14 PDT:
- one preflight element and an array of 457 elements, with 64 CPUs and `--mem=8G` each, at most 64 running at once,
  then one merge job (1 min 30 s);
- plan estimate 9,653 core-hours; Σ native block wall time × 64 threads ≈ 1.04 × 10⁴ core-hours;
- peak RSS 121 MB per element;
- 1,402,407,967 binary128 and 185 300-digit promotions.

The recipe is `public/slurm/production_example.sh` (placeholders `<GFF>`, `<ENV_SCRIPT>`, `<SCRATCH>`, `<DATE>`,
`<FRESH_SEED>`, `<ACCOUNT>`, `<PARTITION>`):
1. Build on the target architecture and run `make -f public.mk test` there.
2. `tools/production.py plan RUN --seed <fresh> --replicates 64 --multiplier 8192 --chunk-points 8388608 --threads 64
   --checkpoint-tasks 1024 --shards 200` on a compute node. This gives 458 jobs and the cost estimate. The plan
   refuses a reused directory and any archived seed in legacy mode.
3. `C6_SBATCH_ARGS="-A <ACCOUNT> -p <PARTITION>" slurm/submit.sh --mem=8G`, then `tools/production.py status RUN`.
   Recover with `slurm/resubmit.sh` after cancelling the pending merge. Release elements held with
   `launch_failed_requeued_held` with `scontrol release`. `docs/HPC.md` is the runbook.
4. The merge job writes `RUN/C6_result.json` (`production.py merge`, then `assemble.py --bootstrap 4096`).

A rerun uses a fresh seed: it gives an independent estimate of the same quantity, not the same digits. The production
seed 3864037981285414462 is recorded in `manifest.json`. The group Sobol nets also depend on SciPy's scrambling
(production: SciPy 1.17.1; each net's sha256 is in `config.json`). The rerun's `C6_result.json` can be passed to the
replay (`RESULTS=RUN`). Its binding and recomputation rows must pass; its quoted-digit rows will differ by design.

##### 5. Decisions you must not make

- The reporting rule in `results/C6_3/CAMPAIGN.md` is fixed:
  - the estimator is the frozen equal-weight a/b combination;
  - the allowance is 4 × SE rounded up to a multiple of 0.0001 (Amendment 1; the step registered before the result
    was 0.001);
  - the gates are checked and flagged, never used to tune or select.
- The bootstrap is a diagnostic only.
- Lower-order pulls never alter C6.
- The allowance is a sampling allowance only. Do not narrow it, and do not present it as covering the analytic
  power-sector compensation or the framework.
- Never rebuild or replace the executable or the inputs inside a campaign. Never reuse a seed.

## Full C7(1), C7(2), C7(3)

### `LRI_C7_HPC`

Folder: `code/LRI_C7_HPC/`.

#### Reproducing C7(1)

Three levels, from cheap to expensive. Paths are relative to `GFF/code/LRI_C7_HPC/` unless stated.

##### 1. Saved-data replay (no integration)

```bash
make -f public.mk replay          # Tier 1, git only: about 5 s, one core, < 1 GB
make -f public.mk fetch-data      # merged records from the Zenodo data record (338 MB tar.gz, 0.97 GB unpacked) into ../../data/C7_1
make -f public.mk replay-full     # Tier 2: tools/combine.py on the records, about 7 min, one core, < 2 GB
```

Expected: Tier 1 ends with `214 checks: PASS 210, WARN 1, RECORDED 2, SKIP 1` (the SKIP disappears when
`GFF/results/C6_1/C6_final.json` is present; the WARN is one digit of the REPORT that is truncated, not rounded).
Tier 2 expects `combined_assembly.json` and `C7_final.json` byte-identical to `GFF/results/C7_1/`, as on Expanse and on
symmetry Intel nodes. Where the platform's floating point differs in the last bits (symmetry AMD nodes: C7_full and
sampling_se by 1 ulp) it compares the JSON trees instead: floats to 1e-12 relative, the two fields that assemble.py forms as differences of nearly equal numbers (applied_zero_pole_control_C7, lower_order_checks[].difference_over_sampling_se) to 1e-12 of their inputs, bootstrap WARN within 5%.
All three runs end with `C7(1) Tier 2 replay: 14 checks, 0 FAIL`.

##### 2. Tests

```bash
make -f public.mk test            # = rm -rf build/validation && make test
```

x86-64 Linux with GCC ≥ 9 (`__float128`, libquadmath, OpenMP), Boost multiprecision headers, Python ≥ 3.8 with numpy ≥
1.24, scipy ≥ 1.9, mpmath ≥ 1.2. Pass Boost and RPATH as for the build, e.g.
`make -f public.mk test CPPFLAGS=-I$BOOST_ROOT/include RPATH=1`. Run it as a batch job on a 16-core node (about
10–20 min; the Expanse test job used `--cpus-per-task=16 --mem=16G -t 00:45:00`):

```bash
sbatch -A <ACCOUNT> -p <PARTITION> --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=16G -t 00:45:00 \
    --output=<SCRATCH>/logs/c7-test-%j.log \
    --wrap "source <ENV_SETUP> && make -C <GFF>/code/LRI_C7_HPC -f public.mk test"
```

`tests/compare_binaries.py --baseline c21b9e8` (bitwise kernels against the delivered source) and
`tests/regenerate_original_baseline.py` need the package's git history, which the public copy does not contain; they
are not part of `make test`.

##### 3. Full production rerun (about 2.6×10^5 core-hours)

What ran (September 2026, SDSC Expanse, Slurm 23.02.7, `shared` partition, GCC 13.3, Boost 1.86, Python 3.11 venv):

| Step | Tool | Size | Cost |
|---|---|---|---|
| build | `make RPATH=1 CPPFLAGS=-I$BOOST_ROOT/include` | | |
| pilot (design input, optional) | `production.py plan --multiplier 1 --refine7 ...` then `tools/design.py --pilot ... --archive <assemble.py --original output>` | 28 elements | about 25 core-h |
| 399 batches (b001–b400 except b215) | `production.py plan` with `--design ../../results/C7_1/design_v1.json --refine7 --extra-inputs inputs_extra --threads 16`, array of `cluster/production.slurm`, then `cluster/merge.slurm` (afterany) | 55 elements × 16 CPUs, 16 GB, ≤ 3 h each | about 640 core-h per batch, 2.5×10^5 in all |
| direct primitive P1 | `campaign.py plan --mode qmc --L 7 --selection primitive --points 8388608 --replicates 64 ...`, array of `cluster/campaign.slurm`, `campaign.py merge` | 16 elements × 16 CPUs | about 20 core-h |
| final combination | `combine.py batches/b* --primitive primitive/P1 --output final/v2 --jobs 16` (output two levels below the tree root) | 1 job × 16 CPUs, 1 h 49 min | about 30 core-h (60 with the trial combinations) |

The driver `public/slurm/rerun_production.sh` performs these steps with placeholders `<ACCOUNT>`, `<PARTITION>`,
`<SCRATCH>`, `<ENV_SETUP>`, `<GFF>`:

```bash
export ACCOUNT=<ACCOUNT> PARTITION=<PARTITION> W=<SCRATCH>/c7_hpc C7_ROOT=<GFF>/code/LRI_C7_HPC C7_ENV_SETUP=<ENV_SETUP>
bash public/slurm/rerun_production.sh            # FIRST=1 LAST=400 SKIP=215 by default
```

Site notes:
- Keep the production tree on a durable filesystem shared by all nodes; node-local scratch only for the temporary block
  files (`SLURM_TMPDIR`). On Lustre, avoid copying the campaign trees file by file.
- `MaxArraySize` below the element count needs `C7_INDEX_OFFSET` (see `../README.md`).
- The templates pass `--cpus-per-task` to `srun`; on Slurm 22.05–23.02 a step without it gets one CPU.
- Submit in waves (the production kept at most 20 batches active) and resubmit a failed element once with
  `--array=<id>`; the merge fails closed until every checkpoint exists, then is idempotent.

Seeds and identity of the streams. Batch k uses `int.from_bytes(sha256(b"C7-expanse-2026-09:batch:k")[:8], "little")`,
P1 uses the tag `C7-expanse-2026-09:primitive` and matrix seed `seed ^ 0x17219317`. With these seeds, the same Sobol nets
(SciPy version as recorded in each manifest) and the same executable build (sha256 33bab738...), every replicate value,
and so every number in `C7_final.json`, is reproduced exactly. The file hashes still differ unless the absolute
executable path is the same too, because each campaign manifest records that path and every merged file embeds the
manifest's SHA-256. A different compiler or CPU changes the long-double rounding at about 1e-15 relative, far below the
sampling error. `SEED_TAG=<other>` gives an independent rerun of the same frozen
design; an independent determination should also refreeze the design from a new pilot.

Expanse rerun of the archive build and the Tier 2 replay (one job; run by the maintainer on 2026-10-13 as Slurm job 54901438:
archive 68 min on Lustre, Tier 1 214 checks without FAIL, Tier 2 14 checks PASS in 409 s from the unpacked tarball):

```bash
sbatch public/slurm/archive_and_replay.sbatch     # 1 node, 4 CPUs, 16 GB, -t 04:00:00; about 1-2 h
```

### `LRI_C7_D2_HPC`

Folder: `code/LRI_C7_D2_HPC/`.

#### Reproducing C7(2) (GFF/code/LRI_C7_D2_HPC at git commit fb64c47)

All commands run in `GFF/code/LRI_C7_D2_HPC`. Placeholders: `<ACCOUNT>`, `<PARTITION>`, `<SCRATCH>` (a file system that
every compute node sees), `<HOME>`.

##### 1. Replay the published numbers (any machine, about 4 s)

    python3 -m pip install numpy            # tested: numpy 1.23.5, 1.26.3, 2.4.4 (production: 2.3.5)
    make -f public.mk replay

Inputs: `../../data/C7_2/run1-20260930-m4096/`, `../../results/C7_2/`, `../../results/C6_2/C6_result.json`, and
`reference/` in this package. Output: a PASS/FAIL/SKIP table (108 PASS, 2 SKIP expected: the production executable and
the hosted per-graph tables are not needed) and `public/out/replay.json`. Exit status 1 on any FAIL.

What it does: verifies the plan's bindings (manifest hash in the result, the four tools pinned by the plan equal the
shipped `tools/`, inputs manifest and cost model as pinned, the 20 configurations and merged records by hash, payload hash
and identity), runs the delivered `tools/assemble.py evaluate()` with only the executable check and the 20
`graph_replicates.csv` hash checks bypassed, compares all 277 fields with `../../results/C7_2/C7_result.json`, recomputes
every number of note Sections 1 and 28 (and the C6(2) by-product quoted in Section 26.6) at the printed digits, reads the coverage
and check records of the method, and re-runs `tools/reassemble_reference.py` (the previous calculation from its archived
records). Tolerances are in the header of `public/replay_c7d2.py` (headline fields 1e-12 relative; cancellation-limited
fields such as the power correction 1e-7 relative or 1e-12 |C7| absolute).

##### 2. Test (one Linux x86-64 node)

    module load <compiler, Boost >= 1.77 headers, GMP, Python >= 3.10>      # see public/slurm/env.sh.example
    python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
    make -f public.mk test        # about 3-5 min with 4-8 cores
    make -f public.mk test-full   # about 5-8 min more; needs GMP

`setup` (run by `test`) rebuilds `inputs/packs/` from `reference/` and checks it. If the Boost headers are not on the
default include path, add `CPATH=<boost>/include`. Boost 1.66 does not compile the kernel. Records go to `public/out/`.
`make -f public.mk test-python` (about 10 s) is the part that runs anywhere.

Bitwise check of the production binary (optional): with GCC 11.4, Boost 1.77 headers and GMP 6.2.1 on x86-64 (the
production toolchain), `make gmp && sha256sum bin/c7d2_gmp` gives `7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3`;
`replay` then turns its executable row from SKIP into PASS.

##### 3. Production rerun (about 8,900 core-hours)

The 2026 production: 1,280 work indices, 2,048 checkpoint blocks, 1.09e12 samples; 28 whole-node jobs of 6.4-6.6 h
(14 nodes with 64 AMD EPYC cores, one 64-thread lane each; 14 with 2 x 20 Intel cores, two socket-bound lanes each);
merge and assembly in one exclusive node job (200 GB requested; 20 group merges in parallel, assembly 4.8 s).

    export C7_PACKAGE=$PWD C7_ENV_SETUP=<HOME>/c7d2_env.sh            # from public/slurm/env.sh.example
    make -f public.mk setup && make && make gmp
    export C7_RUN=<SCRATCH>/c7-d2/run1 C7_COST=../../data/C7_2/run1-20260930-m4096/cost_model.json
    export C7_SEED=$(python3 -c 'import secrets; print(secrets.randbelow(2**63))')
    bash public/slurm/plan.sh                                          # plan + RUN/lanes/queue.txt
    for i in $(seq 1 28); do sbatch --export=ALL public/slurm/node.slurm; done   # edit <PARTITION>, <ACCOUNT> first
    python3 public/slurm/status.py "$C7_RUN"                           # exit 0 when every block is committed
    sbatch --export=ALL --dependency=afterany:<node job ids> public/slurm/merge.slurm

`merge.slurm` merges each group once (the fb64c47 merge is not idempotent; never rerun a merged group) and writes
`$C7_RUN/C7_result.json` with `tools/assemble.py --bootstrap 4096`. To check the new run's records against its own result,
run `python3 -B public/replay_c7d2.py --data $C7_RUN --results $C7_RUN` (the binding and recombination rows apply; with a
fresh seed the estimate is statistically independent, so the rows that compare with the note's printed digits will differ). With seed
8885400701634497064 and a byte-identical `bin/c7d2_gmp`, every checkpoint is reproduced (results do not depend on the
thread count), so the merged records and the result equal the shipped ones.

A failed or timed-out work index keeps its claim directory `RUN/claims/<index>`: remove it and submit another node job.
The package's own templates `slurm/run_array.sh` and `slurm/merge.sh` (job arrays) also work but were not used in 2026.

### `LRI_C7_D3_HPC`

Folder: `code/LRI_C7_D3_HPC/`.

#### REPRODUCE fragment: C7(3) (`code/LRI_C7_D3_HPC`, `results/C7_3`, `data/C7_3`)

For `GFF/REPRODUCE.md`. Run every command from `GFF/code/LRI_C7_D3_HPC` unless stated; paths are relative.

##### 1. Environment

- Python ≥ 3.10 with `public/requirements.txt` (numpy, scipy, mpmath, sympy). The production used Python 3.11, numpy
  2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0. `replay` was also run with Python 3.10.12 and numpy 1.24.4.
- For anything that builds the worker: x86-64 Linux, GCC with C++17, OpenMP and libquadmath (the production used GCC
  11.4), GMP (6.2.1), and the **Boost 1.77** headers. `src/kernel.hpp` does not compile with Boost ≥ 1.86. If the Boost
  headers are not on the default path, pass `BOOST_INC=<dir containing boost/>` (on Spack-module sites
  `BOOST_INC=$BOOST_ROOT/include`; such modules often set no include path). Never add fast-math flags; the package
  Makefile builds with `-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`.
- The package Makefile calls `python3` from `PATH`; activate the environment first.

##### 2. Replay (no compiler, no hosted data)

```bash
make -f public.mk replay        # about 10 s on one core
```

It checks the hash chain from the run1 manifest to the shipped code, inputs, configs and merged records, recomputes
`results/C7_3/run1-20260930-m4096/C7_result.json` with the production assembly (4de9412), recomputes the consistency gates
with the re-verification tool (a6ce987) and compares them with `results/C7_3/run1_report_bb9d2ca.json`, and compares
every number the note quotes for C7(3) at its printed precision. Output: a PASS/FAIL table on stdout and in
`.work/replay/REPLAY.md`; exit 1 on FAIL. Expected (2026-10-13): 128 PASS, 0 FAIL, 2 SKIP, 2 CITED on a fresh checkout; after `setup` the pack row passes too
(129 PASS, 1 SKIP: the `graph_replicates.csv` digests, which `reverify` checks). CITED marks two numbers whose record is a
text (`results/C7_3/results_map.md`). Tolerances: `results/C7_3/results_map.md`.

##### 3. Tests

```bash
make -f public.mk test [BOOST_INC=...]   # < 10 min on a 64-core x86-64 node
make -f public.mk checksums              # seconds
```

`test` first runs `setup`: it unpacks the 10 kernel packs from `public/kernels/inputs_packs.tar.gz` (321.8 MB unpacked)
and checks them against `inputs/manifest.json`, then cuts the 3,511 single-graph files of `reference/inputs/` out of the
packs and checks each against `inputs/inventory.json` and `SHA256SUMS`. Then it runs the production commit's own
`make test`: it builds `bin/c7d3_gmp`, runs `tests/validate.py` (the worker against the original d=3 worker built from
`reference/src`, on up to 16 graphs per loop and sector, every promotion count equal and values within 1e-13
normalized; 1 and 4 threads give identical rows and re-chunked streams agree within 1e-12; assembly identical to
the original on 96 random jets) and `tests/workflow.py` (two tiny campaigns through plan, run, restart, corruption refusal, merge and assembly).
On symmetry (AMD EPYC 7532, 64 cores, job 566376) the two took 18 s and 12 s after the builds. `checksums` verifies every
present file against the delivery's `SHA256SUMS` and `reference/DELIVERY_MANIFEST.json`.

##### 4. Specialist checks (hosted data)

```bash
make -f public.mk fetch-data             # the two hosted files from the Zenodo data record into data/C7_3/ (147 MB)
make -f public.mk test-full              # + every graph, 450-digit point checks, reassembly of the previous result
make -f public.mk archived-replay        # the cited replay of 168,528 archived rows; 95 s at 64 threads
make -f public.mk indep-rows ROWS='[["production_a","power",3,0,0]]'   # independent mpmath check of archived rows
make -f public.mk reverify               # tools/report.py (a6ce987) on the full run1 directory
make -f public.mk smoke                  # rerun run1 job indices 0, 320, 192 and compare with run1's checkpoints
```

- `test-full`, `archived-replay` and `indep-rows` need `data/C7_3/reference_records.tar.gz` (the raw records of the
  previous calculation); `make -f public.mk records` unpacks it into `reference/records/` and checks all 784 files against
  `SHA256SUMS`.
- `reverify` and `smoke` need `data/C7_3/run1-20260930-m4096_full.tgz` (129,966,618 bytes, sha256 08969c10…, the
  value in `results/C7_3/run1-20260930-m4096_full.tgz.sha256`). It is unpacked into `.work/` (535 MB).
- `smoke` re-plans run1 with its seed, flags and cost model; the Sobol nets are identical only with SciPy 1.17.1, and
  the comparison script says so if they differ. Rows must have the same coordinates and promotion counts and agree bit
  for bit or within 1e-10 normalized (run1 mixed CPU types; across them rows differ by up to 2.0e-11).
- Pass criteria and expected values: `results/C7_3/results_map.md`.

##### 5. Production rerun (documented, not run in CI)

Run1 used the production commit's tools with these flags (`results/C7_3/CAMPAIGN.md`). A rerun must use a NEW seed.

```bash
make -f public.mk setup boost-check && make gmp       # bin/c7d3_gmp; record its sha256
export C7_PACKAGE=$PWD C7_RUN=<SCRATCH>/c7-d3/run2    # a new directory on a shared filesystem
python3 tools/production.py plan "$C7_RUN" --seed <NEW_SEED> --backend gmp --replicates 64 --multiplier 4096 \
    --primitive-mode recompute --primitive-points 1024 --shards 64 --threads 64 --checkpoint-tasks 1024 \
    --chunk-points 1048576 --cost-model reverify_a6ce987/cost_models/gmp_symmetry_epyc7532.json
NJOBS=$(python3 -c 'import json,os;print(len(json.load(open(os.environ["C7_RUN"]+"/manifest.json"))["jobs"]))')  # 1280
JID=$(sbatch --parsable -A <ACCOUNT> -p <PARTITION> --cpus-per-task=64 --mem=<MEM> --time=02:00:00 \
      --array="0-$((NJOBS-1))%<CONCURRENCY>" slurm/run_array.sh)
sbatch -A <ACCOUNT> -p <PARTITION> --dependency=afterok:$JID slurm/merge.sh     # merge 20 groups, assemble --bootstrap 4096
```

- **Seeds.** Never reuse run1's base seed 4805754955154533039, the pilot's 3272672730315656627, the previous
  calculation's 300317001, 307401711, 307901733, 302774989 (and the README examples 2026093003, 481771). The delivered
  planner derives the group seeds by fixed arithmetic offsets from the base seed; it does not refuse a used seed.
- **Templates.** `slurm/run_array.sh` and `slurm/merge.sh` are the delivered ones; their `#SBATCH` lines (8 CPUs, 4 GB,
  2 h) are examples and the options above override them. Sites with a smaller MaxArraySize submit several arrays with
  `C7_ARRAY_OFFSET` and make the merge depend on all of them (docs/HPC.md).
- **Resources.** 1,280 job indices (20 groups × 64 shards). The plan's cost model estimates 184.9 hours of 64-thread
  work on AMD EPYC 7532 (about 11,800 core-hours); the heaviest index takes about 48 min at 64 threads. Run1 held 28
  exclusive nodes (14 AMD EPYC 7532/7543/8534P with 64 cores, 14 Intel Gold 6148 with 40 cores) for 8 to 10 hours,
  about 10,500 node core-hours. Run1 used whole nodes with lane scripts adapted from the C7(2) campaign (one 64-thread lane
  per AMD node, two socket-bound 20-thread lanes per Intel node); they are not published, and the array route above is
  the package's documented one. Per-index memory at 64 threads was not measured: use whole nodes, or measure `<MEM>`
  with a pilot.
- **Cost model for other hardware.** Plan a pilot with `--multiplier 1 --replicates 8` (run1's took 4.7 min on one
  64-core node), run all its indices, then `python3 tools/make_cost_model.py PILOT_RUN costs.json` and plan with
  `--cost-model costs.json`. A cost model only places tasks on shards; it never changes sample counts or random streams.
- **Determinism.** Rows are independent of the thread count, chunking and node, but bit-reproducible only on the same
  CPU type. Do not rebuild `bin/c7d3_gmp` during a campaign: the plan pins its sha256.

##### 6. Merge and checks

`slurm/merge.sh` runs `production.py merge` (refuses incomplete groups) and `assemble.py --bootstrap 4096`, which writes
`C7_result.json` with the delivered tool's stale C6 reference. Then judge the result with the reporting rule's gates:

```bash
python3 reverify_a6ce987/tools/report.py "$C7_RUN" --output run2_report.json
```

It re-verifies the campaign by data identity and prints the gates: C3-C6 pulls (C6 against the 2026-09-29 C6(3)
production), power differences at orders 3-6 against zero, the a/b campaign pull, the bootstrap/covariance SE ratio and
the archived value in archived SE. Run1's values are in `results/C7_3/run1_report_bb9d2ca.json`.

##### Decisions you must not make

- The reporting rule (`results/C7_3/CAMPAIGN.md`): the estimator is the frozen a/b combination with its sampling SE;
  the allowance is 4 × SE rounded up to 0.01; the bootstrap is a diagnostic; the gates are checks, never constraints, and
  a |pull| > 3 is reported without changing C7(3).
- The design: equal campaign weights; 64 replicates; the frozen per-graph allocation × 2^12; complete power-of-two
  Sobol nets (chunks are not replicates); both sectors integrated explicitly; no lower-order coefficient imposed.
- The arithmetic: the GMP350 backend, the promotion thresholds 1e-9 and 1e-23, the strict compiler flags.

## Full C8(1), C8(2), C8(3) and the independent checks

### `LRI_C8_HPC`

Folder: `code/LRI_C8_HPC/`.

#### Reproducing C8(1) (GFF/code/LRI_C8_HPC)

Three levels, from cheapest to most expensive. Run everything from `GFF/code/LRI_C8_HPC/`.

##### 1. Tests (about 7 min wall, 2 cores; personal desktop: 6 min 37 s)
    make -f public.mk test
`tests/test_c8_tools.py` (verbatim) requires the seven-slot Jacobian to equal the archived C7 affine map bit for bit;
that holds on some platforms (the Mac, numpy 1.23-1.24) and fails by one unit in the last place on others (a personal desktop, numpy
1.26.4; symmetry AMD EPYC 8534P, anaconda numpy 1.24.3).
`public/test_tools_portable.py` repeats the same checks at 1e-15 of the row scale. `tests/test_pipeline8.py` runs plan,
run, merge, assemble and combine with a fake integrator, including the frozen-bundle, partial-combination, extension and
loop-five rejections, and the lane runner. It runs with the Slurm job variables removed, because the lane runner
names its worker after `SLURM_JOB_ID`: inside a job the test's 'local' claims belong to another job and it would wait
for their 30-minute staleness.

##### 2. Replay of every quoted number (about 20 s wall, 1 core, 0.3 GB; personal desktop, Python 3.12.3, numpy 1.26.4)
    make -f public.mk replay
- `public/replay8.py` copies `GFF/data/C8_1/c8_hpc` to `.work/`, decompresses the nine-vertex inventory, and runs the
  package's own `tools/combine8.py` (and through it `tools/assemble8.py`) for the three quoted combinations:
  K = 4 (b1-b4), the A1 interim (b1-b9, inclusion set of the A1-close record) and the final K = 14 (`--extension
  runs/ext1/extension.json --closed`).
- The commands are the production ones (`cluster/a3/a3_close.slurm`, `cluster/symmetry/a1_close_combine.sh`).
- The only substitution is the campaign verification: the checkpoints are not shipped, so their re-validation is
  skipped. Every other check (manifest, audit, merged-output sha256, merged headers, frozen design, seeds, coverage
  guard) runs unchanged.
- `public/verify8.py` compares the outputs with `GFF/results/C8_1/` and checks 122 quoted numbers. It writes
  `.work/verify_c8.tsv` and exits 1 on any FAIL.

Reproducibility of the bytes:
- All three `combined_assembly.json` files are bitwise identical to the published ones on every platform tried. The
  K = 4 `C8_final.json` is bitwise identical on a personal desktop (numpy 1.26.4, OpenBLAS) but not on symmetry AMD nodes (anaconda
  numpy 1.24.3: last-bit differences, max 1.3e-11 relative in a derived field).
- In the A1 and K = 14 results, 36 float fields differ in their last bits (at most 1e-15 relative; derived
  differences such as C5 minus exact by up to 2.3e-13 absolute). Those files were produced with numpy 1.24 on
  symmetry. C8_full, the sampling SE and the bootstrap SE are identical. The check is 1e-12 relative plus 1e-9
  absolute.
- Result: 122 PASS, 0 FAIL, 3 INFO (checks updated to the public edition of the note, 97dd353).

##### 3. Production rerun (not run in CI)
The production used SDSC Expanse (b1-b4, b12-b14: `shared` partition, elements of 16 AMD EPYC 7742 cores, 24 GB) and
the symmetry cluster (b5-b11: whole Intel Xeon Gold 6148 nodes, 40 cores, `cluster/symmetry/lane8.slurm`). The
calculation used about 9x10^4 physical core-hours (1.4x10^5 as charged, counting hyperthreads on symmetry), including
development, the exact low-loop stage and the pilot. One batch of 498 elements costs about 6.5x10^3 physical core-hours (A1-A3: 64.6x10^3 for b5-b14).

Build (x86-64 Linux, GCC with libquadmath, Boost headers):

    make CPPFLAGS=-I$BOOST_ROOT/include RPATH=1        # bin/c8_integrate
    make inputs                                         # index files of inputs8 (decompress L8_coord.txt.xz first)

The shipped Slurm scripts carry the production account and partition in `#SBATCH` lines. Command-line options override
them: always submit with `sbatch --account=<ACCOUNT> --partition=<PARTITION>` and set
`C8_ENV_SETUP=public/slurm/env_template.sh` (filled in). Steps (README.md of the package, Workflow 1-6):
1. Weights:
   `sbatch --account=<ACCOUNT> --partition=<PARTITION> cluster/weights8.slurm`
   with `C8_ROOT=$PWD` and `C8_OUT=<SCRATCH>/weights8`. One 16-core job, about 1 h. The sha256 of every weight file
   must equal the `input_sha256` entries of the shipped manifests.
2. Exact stage for loops 2-4 and loop 5:
   `tools/production8.py plan <SCRATCH>/runs/exact8 --unit designs/exact8_unit.json --design designs/exact8_design.json --seed <S> ...`,
   then `sbatch --array=0-<n-1> cluster/production8.slurm`. Loop 5 (`designs/exact8_L5_*`) is its own campaign.
   It is deterministic, so the merged vectors must equal `GFF/data/C8_1/c8_hpc/runs/exact8_L5/exact_L5/merged/`.
3. Pilot and `cluster/postpilot8.slurm`. These regenerate the affine map, the frozen controls and the frozen design.
   With the original pilot seeds they reproduce `analysis/v1` and `designs_frozen/prod4_34000`. A rerun with new seeds
   is a new calculation.
4. Production, per batch:
   `tools/production8.py plan <SCRATCH>/runs/prod/bK --unit <BUNDLE>/unit_production.json --design <BUNDLE>/design.json --design-meta <BUNDLE>/design_meta.json --seed <NEW_SEED>`
   (498 work elements), then `sbatch --array=0-497 cluster/production8.slurm` and `cluster/merge8.slurm`.
   Use new seeds: the shipped seeds 80840001-80840014 reproduce the published streams only on the same processor type.
5. Result:
   `tools/combine8.py <batches> --affine analysis/v1/full_affine8.json --exact5 .../N14.json .../N12.json --design-meta designs_frozen/prod4_34000/design_meta.json --output <OUT>`
   (`--extension` for planned extension batches, docs/EXTENSION_A1.md).
- Seeds and pilot or control-training seeds are checked. `combine8.py` refuses a batch planned against another design
  or reusing a forbidden seed.
- Whole-node lanes as on symmetry: `cluster/symmetry/` (`plan_ext.py`, `lane8.slurm`, `tools/lane8.py`).

### `LRI_C8_D2_HPC`

Folder: `code/LRI_C8_D2_HPC/`.

#### Reproducing C8(2) (GFF/code/LRI_C8_D2_HPC, GFF/code/LRI_C8_shared)

All commands run in `GFF/code/LRI_C8_D2_HPC` unless stated. `PY=python3` must have numpy (and, for the tests, scipy,
mpmath, sympy, pytest; `requirements.txt`).

##### 1. Replay (no hosted data; about 10 s on any machine)

```bash
make -f public.mk replay PY=python3          # 192 PASS, 0 FAIL, 3 SKIP; public/out/replay.json
```

It verifies the batch records (plan, cost model, design bundle, 24 group configs and merged records, with the package's
own checks), recombines the 24 groups with `tools/assemble.combine` and `tools/combine.combine_batches`, compares every
field with `GFF/data/C8_2/.../C8_result.json` and `GFF/results/C8_2/C8_final.json`, runs `tools/verify_result.py` on the
records, and recomputes every number of Sections 1, 28 (the C7(2) by-product) and 31 of the note at its printed digits:
the allowance, the pilot comparison, inputs and assembly checks, the inventory table, the design, the numerics gate,
the production schedule and core-hours (from the scheduler records), the campaign split, the variance table, the tail
counts (recounted from the tail table), the weight-boundedness verification, the nested and double-lift tests, the
lower-order and power null checks. The three SKIP rows say what cannot be recomputed here (the group tables are hosted;
native bit-for-bit replays; the development core-hours).

##### 2. Tests

```bash
make -f public.mk setup PY=python3           # 5 s: reference trees (hard links, checked) and the L7 packs (rebuilt, checked)
make -f public.mk test-quick PY=python3      # about 2 min
make -f public.mk test PY=python3            # about 30 min: the package's test-python without L8 packs
(cd ../LRI_C8_shared && make -f public.mk test PY=python3)   # seconds
```

`test` needs a C++17 compiler with Boost and GMP headers (host-compiled checks); it runs on Linux and macOS. `setup` needs
`GFF/code/LRI_C7_D2_HPC/reference/` (the C7(2) unit). After `setup`, `make -f public.mk verify-lists` checks all 10,871
files the package lists (byte for byte, except the files the release scrubbed, `public/SCRUBBED.txt`, which it checks
for presence).

The package's own cluster validation (J-VAL-1) builds the kernels and needs the L8 packs:

```bash
make -f public.mk fetch-data                 # prints DATA.md part (a); put the four tars in ../LRI_C8_shared/inventory/inventory8_d2/payload/
(cd ../LRI_C8_shared && make -f public.mk verify PY=python3)   # the pinned tree, all four levels
make -f public.mk jval1 PY=python3           # setup, setup-l8 (make inputs-l8), make inspect c7ref, make test
```

on a whole Linux x86-64 node (about 40 min on 64 cores; GCC >= 11 with OpenMP and libquadmath, GMP 6.2.1, Boost 1.77
headers). `make test-full` (J-VAL-2: all 3,773 L3-L7 kernels on both backends against the C7(2) executables, and 450-digit
point checks) is the full exact replay.

##### 3. Tail screen and variance analysis from the group tables (`replay-tails`)

```bash
make -f public.mk fetch-data                 # DATA.md part (a): c8d2_prod1_tables.tar over ../../data/C8_2/prod1-.../,
                                             # c8d2_pilot1_records.tar into ../../data/C8_2/pilot1-20261006-ba68f401e46e/
make -f public.mk replay-tails PY=python3    # about 15 min, 8 GB
```

It checks every table against its pinned sha256, reruns `tools/design.py report` (with the raised caps of job 571296) and
the post-production analysis, and compares the tail table byte for byte and the analysis field by field.

##### 4. Production rerun (documented, not run in CI)

The production is one Slurm campaign per batch in lane mode (whole nodes split into 8 lanes of 8 threads). Placeholders:
`<ACCOUNT>`, `<SCRATCH>` (a shared file system visible from all nodes), `<PARTITION>` (whole AMD nodes; one CPU vendor per
campaign: the package refuses a claim on another vendor), `<NODES_EXCLUDED>`.

Node size of the original run: AMD EPYC 7543, 64 cores, 245 GB usable memory, a 24-hour wall limit (hence two rounds).
Largest lane peak memory 1.5 GB; merge peak below 2 GB.

1. Build and validate (one whole node, about 1 h): `make && make gmp && make inspect && make c7ref`, then
   `make gmp NUMERICS=dd,mp256` (the opt-in profile executable `bin/c8d2_gmp_dd+mp256`), `make -f public.mk setup setup-l8`,
   `make test` (J-VAL-1). Copy the package to `<SCRATCH>/pkg/<commit>` (the campaigns pin the tools of that copy).
2. Site environment: `slurm/env.sh.example` -> `~/c8d2/env.sh` (sets `C8_SEEDS`, `C8_DATA`, the AMD-pool cap and
   `C8_SBATCH_ARGS="-p <PARTITION> -A <ACCOUNT> --exclude=<NODES_EXCLUDED>"`); `tools/seeds.py init` creates the seed log;
   reserve the seeds of this release (`designs/forbidden_seeds.json`; the production used 6274393056071737300 and the pilot
   3049594997687674958) and draw fresh ones.
3. Cost model of the exact path (one node, `slurm/sweep.sh`, `docs/HPC.md` "The first sweep"), the exact pilot (about
   230 core-hours on 3 nodes):
   `sbatch ... slurm/plan.sh <SCRATCH>/pilot1 --pilot --points 4096 --replicates 8 --cost-model <CM> --forbid-seeds-from "$C8_SEEDS" --seed <fresh>`,
   then `C8_RUN=<SCRATCH>/pilot1 slurm/submit.sh --lanes 3`.
4. The numerics gate of the profile executable on the production hardware (`tests/numerics_flags.py --profile dd+mp256`,
   full scale; about 15 core-hours; `benchmarks/symmetry_2026-10-c8/s6fix4/scripts/s4flag.slurm`) and the profile's cost model
   (`slurm/sweep.sh ... --numerics dd+mp256`).
5. Design (route (b), `docs/DESIGN.md`): `tools/design.py freeze --pilot <SCRATCH>/pilot1 --target-rel 2.5e-4 --numerics dd+mp256
   --approved-numerics-change "<approval>" --cost-model <CM_dd+mp256> --numerics-gate <gate record> --seeds-log "$C8_SEEDS" --out <BUNDLE>`
   (the original bundle is `GFF/data/C8_2/prod1-.../design_bundle/`: predicted SE 11.50 with the safety factor 1.5;
   14,465 lane core-hours).
6. Plan in a plan job (about 10 min, 1 GB): `sbatch ... slurm/plan.sh <SCRATCH>/prod1 --design <BUNDLE> --numerics dd+mp256
   --approved-numerics-change "<approval>" --cost-model <CM_dd+mp256> --backend gmp --threads 8 --checkpoint-tasks 256
   --index-hours 1.5 --forbid-seeds-from "$C8_SEEDS" --seed <fresh>` (1,129 work indices, 6.19 million tasks, 12,025
   estimated core-hours).
7. Run: `C8_AMDQ_CAP=9 C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 C8_MERGE_TIME=02:00:00 C8_RUN=<SCRATCH>/prod1 slurm/submit.sh --lanes 8`;
   after the wall limit, `slurm/submit.sh --lanes N` for the remainder (the original needed 6 more nodes for 4.4-5.6 h).
   Monitor with `tools/production.py status <SCRATCH>/prod1`.
8. Result: `tools/production.py status` (exit 0), `tools/verify_result.py <SCRATCH>/prod1/C8_result.json`,
   `tools/accounting.py <SCRATCH>/prod1`, `tools/combine.py <SCRATCH>/prod1 --output <OUT>` (K = 1: `C8_final.json`),
   `tools/design.py report --pilot <SCRATCH>/prod1 --max-checkpoints 100000000 --max-tasks 2000000000` (the tail screen).

Cost of the original: pilot 226.9 core-hours (3 nodes, 1.3 h); production 13,453.8 allocated core-hours (8 nodes for
22.4-23.0 h, then 6 nodes for 4.4-5.6 h; 28.7 h from submission to the final merge); validation, gates, sweeps and the tail
check together about 2,000 core-hours. A rerun with fresh seeds reproduces C8(2) within its sampling error, not bit for
bit; the exact path (no `NUMERICS`) gives the same estimand at about 2.7 times the cost (route (b) costs 0.37 of it).

### `LRI_C8_shared`

Folder: `code/LRI_C8_shared/`.

_same as the section above (one text for the whole unit)._

### `LRI_C8_D2_HPC_optimized`

Folder: `code/LRI_C8_D2_HPC_optimized/`.

#### Reproducing the independent check of C8(2) (GFF/code/LRI_C8_D2_HPC_optimized)

All commands run in `GFF/code/LRI_C8_D2_HPC_optimized/`.

##### 1. Replay (seconds, any machine)

    python3 -m pip install numpy scipy mpmath        # versions: requirements.txt
    make -f public.mk replay

The production's own assembler (`tools/assemble.py`, pinned by the plan) recombines the 24 merged group records of the
production and of the pilot; both results are compared field by field with `GFF/results/C8_2_check/*/C8_result.json`, and
the 65 numbers the note quotes for this check (Sections 1, 28, 31.1 and 31.7) are recomputed and compared at the printed
digits, including the comparison with the main calculation (`GFF/results/C8_2/C8_final.json`) and with C7(2)
(`GFF/results/C7_2/C7_result.json`). Output: a PASS/FAIL table, `public/out/replay.json`.

Tolerances: headline fields 1e-12 relative; all other fields 1e-7 relative where |reference| > 1e-9, else 1e-12 absolute
(differences of nearly equal numbers). Verified: numpy 2.3.5 / Python 3.11.9 (Expanse; the production's environment) and
numpy 1.23.5 / Python 3.10 (macOS): 65/65 PASS on both, headline fields within 4e-16, all fields within 3.6e-9.

##### 2. Tests (a few minutes, one Linux x86-64 node)

Requirements: g++ >= 9 with OpenMP and libquadmath, Boost headers (multiprecision), GMP, Python >= 3.10 with numpy,
scipy, mpmath. On a cluster, load the compiler, Boost and GMP and put their include and library paths in `CPATH`,
`LIBRARY_PATH` and `LD_LIBRARY_PATH` (`slurm/env_expanse.sh` shows one way).

    make -f public.mk test        # about 80 s: the package tests, in a copy under $TMPDIR
    make -f public.mk fixtures    # about 1.5 min: 52 fixture cases, optimized kernel = reference kernel bit for bit

`test` runs in a copy on node-local disk because one cache test needs sub-second file timestamps (Lustre has one-second
timestamps). Verified on Expanse (AMD EPYC 7742, GCC 13.3.0, Boost 1.77, GMP 6.2.1), 2026-10-13: `fixtures` PASS (52 cases,
science digest 366421b2…, the same as the delivered sandbox), `replay` 65/65.

##### 3. Re-merge from the checkpoints (about 6 min on 8 cores)

    make -f public.mk fetch-data                       # the 1.7 GB campaign directory (DATA.md, part a)
    make -f public.mk remerge                          # needs about 2 GB of scratch space under public/out/

Re-merges all 24 groups from their 4,000-odd checkpoint files with `tools/production.py merge` (Decimal summation in a
fixed order) and compares every new `merged.json` with the shipped one byte for byte; then recomputes the kernel time
from the checkpoint rows. Verified on Expanse, 2026-10-13: 24/24 identical; 25,585.3 kernel core-hours (0.967 of the
attempt core-hours, 0.965 of the allocated core-hours).

##### 4. A production rerun (about 26,500 core-hours; documented, not run in CI)

1. Unpack the original package (DATA.md, part a) somewhere outside `GFF/code/` and attach its graph packs:
   `python3 tools/attach_inputs.py <unpacked>/LRI_C8_D2_HPC/inputs --mode symlink` (verifies all twelve packs).
2. Build on the target nodes: `make -j gmp` (one binary per campaign; record its sha256).
3. Pilot (32 replicates per campaign, 96 work indices; 172 core-hours on 3 nodes):
   `python3 tools/production.py plan <SCRATCH>/c8d2-check/pilot1 --seed <fresh 63-bit integer> --backend gmp
   --purpose pilot --replicates 32 --loop-points 3:16384,4:4096,5:2048,6:1024,7:512,8:256 --threads 128
   --checkpoint-tasks 4096 --checkpoint-graphs 64 --shards 32`, run its work indices as in step 6, merge, then
   `python3 tools/make_cost_model.py <pilot dir> <pilot analysis>/cost_model.json` and
   `python3 tools/inspect_result.py <pilot dir> --top 25 --output <pilot analysis>/inspect.json`.
4. Allocation: `python3 tools/pilot_allocation.py <pilot dir> alloc.json --target-core-hours 28500 --replicates 64`
   (forecast SE 14.97 for the production's pilot).
5. Production: `python3 tools/production.py plan <SCRATCH>/c8d2-check/prod1 --seed <fresh seed> --backend gmp
   --purpose production --replicates 64 --allocation alloc.json --cost-model <pilot>/cost_model.json --threads 128
   --shards 128 --checkpoint-tasks 4096 --checkpoint-graphs 64 --checkpoint-seconds 76800` (plan on node-local disk and copy:
   planning on Lustre took 17 min against 10 s). This gives 342 work indices.
6. Run: one whole-node runner per node, `slurm/node_runner.sh` through `tools/site_submit.py runners` (Slurm options:
   `-A <ACCOUNT> -p <PARTITION> -N 1 --exclusive -t 32:00:00`), until every index is done; the production used 11 nodes for
   16.3-20.1 h each (207 node-hours, 26,526 core-hours). Then `tools/site_submit.py merge` (or
   `python3 tools/production.py merge <dir> --workers 8` on 8 cores, about 5 min).
7. Compare: `python3 tools/inspect_result.py <dir> --top 25 --output inspect.json`, then the comparison of `public/replay.py`
   (`--data`/`--results` pointing at the new campaign).

Seeds must be fresh and must not collide with those of the main calculation (`GFF/code/LRI_C8_D2_HPC` seed registry).

### `LRI_C8_D3_HPC`

Folder: `code/LRI_C8_D3_HPC/`.

#### Reproducing C8(3)

C8(3) = 1602.6 ± 3.9 (estimator 1602.6052229663408, sampling SE 0.9516489064069612; the allowance is 4 SE rounded up to a
multiple of 0.1, fixed after the result; the paper rounds the same 4 SE = 3.807 by the PDG rule to 1603 ± 4). Run every command from `GFF/code/LRI_C8_D3_HPC/` with `make -f public.mk`.
The package's own `Makefile`, `docs/HPC.md` (runbook), `docs/PRODUCTION_RUNBOOK.md`, `docs/NUMERICS.md` and
`docs/PERFORMANCE.md` ship verbatim and stay authoritative for the cluster procedures; this file says which parts a
reproduction needs.

Ground rules:
- Never edit `results/C8_3/`, the production evidence under `benchmarks/symmetry_2026-10-c8/production/`, `inputs/`,
  `vendor/`, `reference/` or `tools/`: the result pins the tools, the vendored assembly, the inputs and the references by
  sha256, and the replay checks those pins.
- The records name the cluster paths, user and nodes on which they were written. Nothing resolves them.
- The sampling SE is a standard error; the ±3.9 allowance is an empirical rule, conditional on finite variance, not a
  confidence interval and not a bound on shared systematic errors.

##### 1. Environment

| need | production | also tested |
|---|---|---|
| Python | 3.11.3, NumPy 2.3.5, SciPy 1.17.0, mpmath 1.3.0, SymPy 1.14.0 (`requirements-tested.txt`) | replay and `test`: 3.10.12 with NumPy 1.24.4, SciPy 1.11.1 (macOS arm64) |
| C++ | GCC 11.4 (symmetry), GCC 13.3 (Expanse); `-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math` (the Makefile refuses other floating-point flags) | |
| libraries | Boost 1.77 headers (`BOOST_ACCEPT=<version>` for another), GMP 6.2.1, libquadmath, OpenMP | |
| CPU | AMD EPYC 7543 (production, pinned by `slurm/site.sh`); EPYC 7742 (Expanse development) | results agree across CPU types to ≤ 2.0e-11 normalized per row (docs/NUMERICS.md) |

`pip install -r requirements.txt` (floors: numpy 1.24, scipy 1.10, mpmath 1.3, sympy 1.12). No GPU.

##### 2. Tests

| target | needs | node, time | what |
|---|---|---|---|
| `make -f public.mk test` | Python only | 1 core, 4 GB; 7 min measured on an Apple M-series core (allow 15–20 min on a cluster core) | 20 pure-Python tests: assembly and statistics (`assembly_checks --exact`, `compat_run1`: the order-8 assembly rebuilds C7(3) run1 at order 7), the result verifier against tampering, the design and pilot-report tools, the margin probe, `integration_3a` (worker contract), orchestration on the fake worker (`workflow --fake`, `staging --fake`, seven `unit_orchestration` cases), `cost_refresh_test`, `thru_report_test` (through `public/thru_report_test_portable.py`: with Python ≥ 3.12, whose `sum()` of floats rounds differently, three re-derived floats differ from the committed record by one unit in the last place, and the same test is rerun with float equality to relative 1e-12), static scans |
| `make -f public.mk fetch-data TIER=rerun` then `test-native` | toolchain; L7 and L8 packs | one 64-core node, 32 GB; about 5 min | the package's `make test-native` (`make gmp decimal c7ref inspect test-builds`, `validate.py` (identity; order 7 bit for bit against the unchanged C7(3) worker on a subset; order 8 against order 7 on the shared slots; bad inputs), `class_b.py`), `check_build.py --selftest`, `gen3/test_gen3.py`; passed on an Intel Xeon Gold 6148 (symmetry job 574351) |
| `fetch-data TIER=test` then `test-replay` | toolchain; L7 packs; the two C7(3) reference tars | one 64-core node; build 3 min + 1 min | the 168,528 archived C7(3) production rows replayed with the C8 worker in order-7 mode, C7(3) rebuilt to 1e-12 (note Sec 32.2; J-RUN1 570390 gave 1.0e-15). Rows must match the archive to 1e-10 normalized. On AMD EPYC 7532, 7543 and 7742 they match to 1.01e-11, identically on all three. An Intel Xeon Gold 6148 gives 1.44e-10, from x87 expl/logl rounding. When only that row check fails, the target reruns the same test with a row tolerance of 1e-8 (`public/test_replay_portable.py`) and prints both tolerances. C7(3) still had to agree to 1e-12, and did: 4.1e-15 on Intel (job 574359). |
| `fetch-data TIER=rerun` then `test-full` | as test-native | one 64-core node, about 45 min | the package's own `make test` plus `check_vendored.py --no-review-record` |

On Expanse and symmetry the fake-Slurm tests of `make test-python` (`test_submit`, `test_ledger`, `test_pipeline`,
`prefix_check` and fifteen `unit_orchestration` cases) refuse to run by design (exit 64 or 1, recorded `SITE_REFUSED` in the
production export's val1 571477: 38 PASS, 19 SITE_REFUSED, 0 FAIL). Run `test-full` elsewhere (a workstation) or accept
those refusals. The full native validation (`make test-native-full`, every kernel) is J-VAL-2 (`C8_JOB=val2 slurm/native_job.sh`).

##### 3. Replay (`make -f public.mk replay`, CI tier)

1 core, 2 GB, about 20 s (40 s with the hosted tables). Writes `.public_out/replay/REPLAY.md` (the PASS/FAIL table),
`replay.json`, the recombined result and the rerun N-trend. Exit 1 if any row FAILs.

| step | checks | tolerance |
|---|---|---|
| P | every shipped file against the package's `SHA256SUMS` (4fbd1bae; lines of files the export excludes are counted, the merged note of `public/dropped_paths.txt` is reported as INFO, any other missing file fails); the 118 evidence files of 6dd4a75a against `public/SHA256SUMS.evidence_6dd4a75a`; the tools, vendored assembly, POWER_PROTOCOL, inputs manifest, two-loop input and references that `C8_result.json` pins | sha256 |
| R | `results/C8_3` against `SHA256SUMS.symmetry`; result → manifest → 24 configs, cost model, design bundle; every `merged.json`'s self-hash, plan binding and shape; every group's scientific identity | sha256, exact |
| A | the 24 merged batch arrays reassembled with the package's own `tools/assemble.py` (vendored order-8 assembly, bootstrap 4,096 with seed 70530413) and compared with every field of `C8_result.json`; `tools/verify_result.py` on the result file | rel 1e-10 (the package's own), C8 and its SE rel 1e-12 (measured 2.8e-16 and 0) |
| T | `tail_ntrend/ntrend.py` rerun on the committed pilot report, `prod_tails.csv` and the result | JSON equality |
| H | with `fetch-data TIER=replay`: `graph_replicates.csv` pins; `ab_split/ab_split.py` rerun (identical text to `report.txt`); the tail monitor's variance shares | sha256, byte-identical, rel 1e-10 |
| N | about 180 numbers of the abstract and Sections 1 and 32, each at its printed precision | half a unit of the last printed digit, unless the row says otherwise |

Expected outcome (macOS arm64, 2026-10-13): **0 FAIL**, 3 NOT RUN without the hosted tables, and:
- **KNOWN (platform):** off the production CPU class, `verify_result.py` stops at `hard_gates.affinity.linear_response_residual`,
  a rounding-level diagnostic of the affinity gate (production 3.0e-14 at order 7, here 1.4e-13; gate threshold 1e-10).
  Every other field is compared in step A. On x86-64 with `OPENBLAS_CORETYPE=Zen` (set by the target) the production bits
  are expected (C62d F6; the production verified with exit 0 on symmetry, `prod1/c8d3_prod1_verify.json`).
- **ERRATUM (2):** two printed numbers of the note edition fa71533 that the records do not support at the printed
  precision: the Sec 32.4 error-table entry power-free L = 4 (printed 0.011; record 0.0105 → 0.010) and the upper end
  of "medians of 0.82 to 0.88" in Sec 32.5 (record 0.875 → 0.87). The corrected values are checked strictly.

`verify_result.py RUN` (directory mode, which also re-validates every per-graph CSV table of the 24 groups) needs the
complete run tree, which is not published; the shipped `prod1/c8d3_prod1_verify.json` is its output on symmetry.

##### 4. Production rerun (documented, not run in CI)

The production is one campaign of 1,941 work indices (25,714 checkpoint blocks) on 24 groups (2 campaigns × 2 sectors ×
L = 3..8), 365,441,318,912 kernel samples, allocated by the frozen design bundle
`benchmarks/symmetry_2026-10-c8/production/prod1/production/design_prod/` (design A: target SE 1, predicted 0.87,
15,492 core-h). It took **15,102 core-hours** on symmetry (lanes 14,970, merges 106, plan and probes the rest): 8 lane
jobs at a time, each a whole 64-core AMD EPYC 7543 node running 8 lanes of 8 threads, 2026-10-09 to 10-12.

Steps (placeholders `<ACCOUNT>`, `<PARTITION>`, `<SCRATCH>`, `<ROOT>`; full commands in `docs/PRODUCTION_RUNBOOK.md`
P.3–P.8 and `prod1/production/prod_plan_job.sh`):
1. **Site.** Copy `slurm/sites/<expanse|symmetry>/env.sh.example` to `~/c8d3/env.sh` and set `C8_ROOT=<ROOT>`,
   `C8_STORE=<ROOT>/store`, `C8_SEEDS=<ROOT>/seeds.log`, the account and partition. Another site needs its entry in
   `slurm/site.sh` (CPU pin, scratch) and `tools/slurm_submit.py` (admission rules); see docs/HPC.md.
2. **Inputs.** `make -f public.mk fetch-data TIER=rerun` (L7 packs into `inputs/packs/`, the L8 packs into
   `data/C8_3/store/packs/` and linked by `make link-l8`), then `make all` and `python3 -B tools/prepare_inputs.py verify`.
3. **Build and cost model.** `make -j gmp` on a compute node of the target CPU. The planner requires a cost model measured
   on this very binary and CPU (HD11): unless `bin/c8d3_gmp` is byte-identical to the production binary (sha256
   e9b6f6c3…; GCC 11.4 on EPYC 7543) and `cost_models/gmp_symmetry_epyc7543_c8.json` applies, first measure one with the
   calibration refresh (`C8_JOB=sweep2 slurm/native_job.sh`, i.e. J-SWEEP-2, or `tools/sweep.py --refresh <model>`;
   docs/HPC.md "Stage 5: the calibration refresh"; one node). The cost model only shapes the work indices; the per-graph sample counts come from the design bundle.
4. **Plan** (one node, 2 h limit): `slurm/plan.sh <ROOT>/runs/<run> --design <bundle> --approved-fallback '<reference>'
   --threads 8 --index-hours 1 --backend gmp --mp-check on --cost-model <model> --forbid-seeds-from $C8_SEEDS --seed <S>`.
   `--seed 7204841255549554256` (the production seed) reproduces the production's sample points; a fresh seed
   (`python3 -c "import secrets;print(secrets.randbits(63))"`, checked by `tools/seeds.py check`) gives an independent
   campaign.
5. **Lanes and merges** through `tools/slurm_submit.py lanes N` (one whole node per lane job; merges `-c 64 --mem=240G`,
   time from the manifest's `scale.suggested_merge_time`); repeat rounds until `tools/production.py status <run>` prints
   "complete: every checkpoint block is committed". The final merge writes `<run>/C8_result.json`.
6. **Verify:** `OPENBLAS_CORETYPE=Zen python3 -B tools/verify_result.py <run>` (exit 0), then compare with
   `results/C8_3/C8_result.json`. With the production seed on EPYC 7543 the merged batches are expected bit for bit;
   on another CPU type each row may differ in the last bits (≤ 2.0e-11 normalized), far below the SE.

Slurm templates with placeholders: the job scripts in `slurm/` (`plan.sh`, `lane_worker.sh`, `merge.sh`, `run_array.sh`,
`native_job.sh`, `common.sh`, `site.sh`) are submitted by `tools/slurm_submit.py` with the options of
`slurm/sites/<site>/profiles.sh`; the site values (account, partition, scratch, CPU pin) live in `env.sh` and `site.sh`.

###### Regenerating the inputs (alternative to fetching the packs)

The L7/L8 packs were built from the published d=3 payload, which is not hosted (9.2 GB). To rebuild it:
1. **H1**, the shared nine-vertex inventory: `GFF/code/LRI_C8_shared` (C62d) at `inventory/inventory8_d2`, pin
   `C8_H1_PIN = 46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099`; its non-payload files are in git,
   its `payload/*.tar` hosted there. Copy it with J-H1-COPY (`slurm/h1_copy.sh`) to `$C8_STORE/h1/46341a3c0f11/`.
2. **The frozen C7(2) d=2 inputs** (3,774 files, about 303 MB: `LRI_C7_d2_progress/inputs/L2..L7` and
   `power_mass/inputs/L3..L7`): they ship once, byte-identical, in `GFF/code/LRI_C7_D2_HPC/reference/` (C62d's export at
   fb64c47). Stage 0's copy (`c7d2_frozen`) is taken from there and verified against `gen3/pins/c7d2_frozen_d2.sha256`.
3. **J-GEN-D3** (`slurm/gen_d3.sh`, which runs `gen3/run_d3.sh`): the d=3 rate conversion and C63d's gates, publishing
   `$C8_STORE/d3_payload/46341a3c0f11/` with `MANIFEST_d3.json` sha256
   `70af9d2242439bc1f3f24a2bcb97466e7717aa87fb50fc538232935e6b038aca` (= `inputs/d3/MANIFEST_d3.json`).
4. `make inputs-l8 D3PAYLOAD=$C8_STORE/d3_payload/46341a3c0f11 D3PIN=70af9d22… STORE=$C8_STORE`: it verifies the payload
   (`gen3/verify_d3.py --pin`), writes the L8 packs into the store, rebuilds the L7 packs (C7(3) members from
   `reference/inputs/`, hosted tar, plus the 143 + 119 new kernels from the payload) and checks every member against
   `inputs/d3/MEMBERS_d3.sha256`; `make inputs` and `tests/check_inputs.py` then compare all inputs byte for byte.
docs/HPC.md, sections "d=3 payloads" and "Inputs", give the job sizes (Expanse) and gates.

##### 5. Checks a result must pass

The gates applied by the production, and to any rerun: the three hard assembly gates (top slot and loop 7 at rtol 1e-12,
affinity 1e-10; a failure stops the assembly), coverage of all 24 groups and every inventory graph, lower-order pulls
C3–C7 and the b̂₃ᵖ(0) control (|pull| > 3, resp. 4, would be reported, never used to change C8), the power null rows of
orders 4–7, the campaign a/b pull and the bootstrap/covariance SE ratio (flags only), and the tail monitor (an L8 graph
with two-campaign Hill ξ̂ > 0.44 listed, with more than 3% of its group's variance flagged for review).

##### 6. Decisions you must not make on your own

Ask the author before:
1. changing the allowance rule (4 × SE rounded up to 0.1) or quoting the estimator digits as physical digits;
2. combining this result with the independent check, or with a rerun, or topping it up (`tools/combine_results.py` at
   e8468c96 exists but never ran and is not in this export);
3. re-planning with another design, target SE, rate multipliers, sample counts or a reused seed other than the
   documented exact rerun;
4. dropping or re-weighting graphs, groups or campaigns, or changing the tail-monitor thresholds after seeing data;
5. editing any hash-bound file (`results/C8_3`, the evidence, `inputs/`, `vendor/`, `tools/`, `references/`), or
   regenerating `SHA256SUMS`/`DELIVERY_MANIFEST.json` to make a check pass;
6. spending production compute (a rerun is about 15,000 core-hours).

### `LRI_C8_D3_OPT`

Folder: `code/LRI_C8_D3_OPT/`.

#### Reproducing the independent C8(3) check

Run everything from `GFF/code/LRI_C8_D3_OPT` with `make -f public.mk <target>`. Steps 1-3 need no cluster. Step 4 is
the production rerun, documented but not run in CI. Records live in `GFF/results/C8_3_check` (in git) and the bulk in
`GFF/data/C8_3_check` (hosted, `make -f public.mk fetch-data`; described in `GFF/data/C8_3_check/DATA.md`).

Ground rules:
- Never edit `tools/campaign.py`, `tools/sobol_net.py`, `tools/io_utils.py` (pinned by every campaign manifest),
  `tools/assemble.py`, `tools/assemble_streaming.py`, `tools/rg.py` (pinned by the result) or anything under `inputs/`
  (pinned by the manifest). The replay checks these hashes.
- `make test` runs in a copy (`.work/test`), because the package's tests rewrite `verification/*.json`.
- The records name the production cluster's paths in two places (`manifest.json`: the executable and allocation
  paths). They are part of the hashed record and are never resolved by any tool.

##### 1. Environment

| need | production | also tested |
|---|---|---|
| Python | 3.11.9 with numpy 2.3.5, scipy 1.17.0, mpmath 1.3.0 | replay: 3.10.12 with numpy 1.24.4, scipy 1.11.1 (macOS arm64) |
| C++ (test and rerun only) | GCC 13.3.0, `-std=c++17 -fopenmp`, libquadmath | GCC 11.4.0 (symmetry builds); the delivered package: GCC 14.2.0 |
| headers and libraries | Boost 1.77 multiprecision headers, GMP 6.2.1 | Boost 1.83, GMP 6.3 (package README) |
| CPU | AMD EPYC 7742 (x86-64; `__float128` required) | AMD EPYC 7543, Intel Xeon Gold 6148 (tests only) |
| graph regeneration only | pynauty 2.8.8.1, sympy 1.14.0 | |

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install -r public/requirements.txt
export CPPFLAGS="-I<BOOST_ROOT>/include -I<GMP_ROOT>/include" LDFLAGS="-L<GMP_ROOT>/lib -Wl,-rpath,<GMP_ROOT>/lib"
```

##### 2. Tests (`make -f public.mk test`, Linux x86-64 node, 32 cores / 64 GB, 2-3 min)

The steps of the production build job (`slurm/build.sh`), in a copy of the package:

| step | checks | production time (Expanse, 32 cores) |
|---|---|---|
| build | `bin/c8d3_optimized`, `c8d3_gmp`, `c8d3_baseline`, `point_checks_gmp`, `c7d3_reference`, `test_positive_quad` | 7-9 s |
| `bin/test_positive_quad` | 12,051,840 positive binary128 additions | 1 s |
| `make test-native` | same-sample regression of the C8 worker against the untouched C7 worker on C7 graphs (`reference_c7/`), array-boundary and split checks | 30 s |
| `make test-points` | 12 eight-loop graphs, four points each: the precision tiers (long double, binary128, multiprecision) against an independent 450-digit evaluation | 41 s |
| `tests/test_optimization.py` | optimized against baseline worker, 179 real graphs, identical rows and promotion counts | 17 s |
| `tests/test_hpc_dispatch.py`, `test_streaming_assembly.py` | dispatcher locks, deadlines, staging; streaming assembly equals the reference assembly | 8 s, 2 s |
| `tests/test_rg.py`, `test_campaign.py`, `test_allocate.py` | fixed point (exact checks), planner, allocation | 1-2 s each |

`make -f public.mk test-py` runs the last row and the streaming-assembly test without a compiler (seconds, any OS).
`make -f public.mk test-cluster` runs `tests/test_cluster.py` (the site admission layer with fake Slurm commands,
33 cases, 15-25 s, any OS; passed on macOS); it reads the delivered pilot's manifest, so it needs `fetch-data`. All 14 steps passed on three Expanse
builds (2026-10-09) and on a symmetry AMD EPYC 7543 build (2026-10-12).

##### 3. Replay (`make -f public.mk replay`, about 3 s, 1 core, any OS)

`public/replay_check.py` reads `GFF/results/C8_3_check` and, when present, the main record
`GFF/results/C8_3/C8_result.json` (or `MAIN_RESULT=<path>`). It writes `.work/replay/replay_report.{txt,json}` and
exits 1 on any FAIL. Rows:

| row | what | tolerance and why |
|---|---|---|
| R0 | SHA-256 of the four records; result -> manifest, manifest -> allocation, manifest -> `inputs/*`, coverage certificate -> inventory; tool pins of the manifest (campaign, sobol_net, io_utils) and of the result (assemble, assemble_streaming, rg, io_utils) | exact |
| R1 | C0..C8, their standard errors and covariance, power-free part and correction with errors, their covariance, error by loop, lower-order pulls: recomputed from the stored means and covariances of the means with `rg.coefficients`, `rg.jacobians` and the propagation of `assemble.calculate()` | estimates rel 1e-12, errors rel 1e-10: same float64 code on the same stored inputs; only BLAS summation order can differ (observed: 4e-16 and 0) |
| R2 | `assemble.calculate()` itself on synthetic 16-replicate matrices with exactly the stored moments (both campaigns identical) | estimates rel 1e-11, errors rel 1e-8: the covariance is rebuilt by an eigen-decomposition (observed 3e-15 and 4e-10) |
| R3 | the quoted values, rounded as quoted: 1600.98 +- 3.97; max lower-order pull 1.73; C6 33.599 +- 0.014; C7 -220.40 +- 0.19; README pulls and power split | string equality at the quoted digits |
| R4 | campaigns: (P_a + P_b)/2 of the per-graph projected means equals J . means; each campaign recomputed to first order about the pooled fixed point from `graph_statistics_54838171.json` and compared with the stored campaign coefficient; then 1603.53 +- 4.91, 1598.42 +- 6.24, pull 0.64 | abs 1e-8; abs 1e-4 (observed 1.4e-6; loops 5-8 enter affinely at eighth order, the low loops' second-order terms are tiny); quoted digits |
| R5 | -0.40 combined SE from the main estimator (main record checked by hash and against the note's values) | quoted digits |
| R6 | 24,173 kernels per campaign = inventory; manifest graph hashes = inventory hashes; points = allocation, minimum 4,096; 16 replicates; rates 0.8/0.7; 48 group seeds = `campaign.derive_seed(base seed)`; base seed differs from the delivered pilot's; 1,994 jobs by the planner's rule; 2 x 16 x sum(points) = 37,121,687,552 evaluations (also the sum of the per-graph points) | exact |
| R7 | `tools/allocate.py` on the delivered pilot's graph statistics with a 2,000 core-hour budget and 16 replicates reproduces `prod1_2000.json` byte for byte (estimate 1999.99 core-hours of the pilot host) | exact; SKIP without the pilot bundle, FAIL in `make -f public.mk replay-full` |
| D | about 9,800 SU: 6 nodes x 45,814 s + 0.19 + 0.11 node-h = 76.66 node-h x 128 SU = 9,812 SU (inputs from the production README, i.e. Slurm accounting) | arithmetic only; the dates and node count are documented, not recomputed |

Not replayed, because they need the per-replicate matrices that only the native outputs contain: the campaign
standard errors (4.91, 6.24), the half streams (1599.79, 1602.17) and the bootstrap (SE 3.78). The replay reads them
from the record.

##### 4. Production rerun (documented, not run in CI)

The production `prod1` ran on Expanse on 10 and 11 October 2026: plan job (4 cores, 1 h 41 min), lanes job on 6
exclusive 128-core AMD EPYC 7742 nodes with 16 lanes x 8 threads (12 h 44 min, 1,989 of 1,994 jobs; 5 jobs deferred at
the deadline), an index-only job and one more node for the 5 jobs (11 min), and the streaming assembly (46 s). Total
about 76.7 node-hours, about 9,800 service units. A rerun with a fresh seed needs about the same.

1. `make -f public.mk fetch-data` (graph payloads 9.15 GB unpacked; the pilot's statistics shape the lane bundles).
2. Templates in `public/slurm/` (placeholders `<ACCOUNT>`, `<PARTITION_SHARED>`, `<PARTITION_NODE>`, `<NODES>`,
   `<NODE_MEM>`, `<SCRATCH>`, `<NAME>`, `<FRESH_SEED>`, `<LANES>`; `public/slurm/README.md`): `build_test.slurm`,
   `plan.slurm` (the production options: `--purpose production --points 4096 --replicates 16 --threads 8
   --graph-block 32 --chunk-points 262144 --allocation ../../results/C8_3_check/allocations/prod1_2000.json`, index
   `--bundle-jobs 4 --target-core-seconds 1800`), `lanes.slurm` (`--signal=TERM@600`, `C8_DEADLINE_FACTOR=6`),
   optionally `index_tail.slurm`, then `assemble.slurm` (`assemble_streaming.py --bootstrap 4096`).
3. Compare the new `C8_result_<job>.json` with the shipped one: independent seeds give an independent estimate; it
   should agree within the combined sampling errors.

The production itself was submitted through the package's site layer (`tools/submit.py`, `slurm/{plan,run_hpc,
assemble}.sh`, `docs/CLUSTERS.md`), which applies one user's allocation, caps and node exclusions; it ships unchanged
as the record of what ran. The templates run the same science commands without it.

##### 5. Decisions not to make on your own

- Do not combine this result with the main C8(3) value, or quote it with an allowance: the package assigns none.
- Do not reuse the production seed 1546835505427890396 or the pilot seed 7736323638330945148.
- Do not edit pinned tools or inputs; a changed byte invalidates the plan or the replay.
