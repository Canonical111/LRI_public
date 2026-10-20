# Reproducing the HT_Pert results

How to rerun each package: environment, `make -f public.mk test` / `replay`, and the documented production reruns. `make test` and `make replay` in this folder run every package (see `Makefile`).

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### Reproduce: lri_1d_c4_exact

1. **Environment.** Python ≥ 3.10 with numpy, scipy, numba and mpmath (`requirements_lri_1d_c4_exact.txt`). Production
   ran with Python 3.11.4, numpy 1.24.3, scipy 1.10.1, numba 0.57.0 and MKL on symmetry (AMD EPYC 7532/7543, amdq).
2. **`make -f public.mk test`**, then **`make -f public.mk replay`**, then **`make -f public.mk smoke`**.
3. **Production rerun** (cluster).
   - `slurm/submit.sh` drives validation, benchmark and production (`slurm/README` comments).
   - Each stage is gated on the previous one: validation PASS at the snapshot sha, worst-case benchmark sizing, A6d
     overlap with the previous rung.
   - Copy the package to a read-only snapshot directory and set `C4_ROOT`, `C4_DATA` and the partition in
     `slurm/env.sh`.
   - Measured cost on one amdq node (64 cores, 256 GB):
     - Λmax = 400: 48 s;
     - Λmax = 1000: 7 min;
     - Λmax = 2000: 78 min with 9.7 GB per worker, 4 workers × 8 threads per socket.
   - Assembly takes a few minutes, one node.
   - `python3 c4_run1d.py run|assemble` also run directly: see the usage in `c4_run1d.py`.
4. **Fits.**
   - `fits/fits_c4_1d.py freeze|compare|check|explore`: the blind protocol, run in this order. freeze on the L1000
     result, then check against L2000.
   - `compare` is the only command that uses the known C4.

##### Decisions you must not make
- The blind records `fits/frozen/*.json` were frozen before any Λ > 1000 data existed (commit 16cf318). Do not refreeze
  them on newer data; `replay` checks their sha256.
- The fit bases, log options and lo values of the frozen records are fixed; the comparison with C4 is not an input.

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### Reproduce: lri_1d_c5_exact

1. **Environment.** Python ≥ 3.10 with numpy, scipy, numba, mpmath and pytest (`requirements_lri_1d_c5_exact.txt`).
   Production ran with Python 3.11.4, numpy 1.24.3, scipy 1.10.1, numba 0.57.0 and MKL on symmetry amdq (AMD EPYC
   7532/7543).
2. **`make -f public.mk test`**, then **`make -f public.mk replay`**, then **`make -f public.mk smoke`**.
3. **Production rerun.**
   - `slurm/submit.sh validate | bench | prod LMAX NNODES WPS BLOCK | assemble` (see `slurm/README_SLURM.md`). Every
     stage is gated:
     - validation PASS at the snapshot sha (`validate.slurm`: pytest including the slow tests, A1–A3, closed forms, and
       the Λmax = 80 and 160 rungs with gates);
     - benchmarks only after the validation's PRELIM marker;
     - workers sized from the worst-case benchmark task;
     - each rung's assembly gated on A4, A5, A6d against the previous rung and A6e against the exact-C4 result.
   - Measured cost on symmetry amdq (2 sockets × 32 cores, 256 GB):
     | Λmax | nodes × workers | wall per node |
     |---|---|---|
     | 240 | 2 × 8 | 43–45 min |
     | 320 | 3 × 8 | 1 h 14 min |
     | 400 | 4 × 8 | 2 h 10 min – 2 h 22 min, 14 GB per worker |
     | 500 | 5 × 6 | 4 h 52 min – 5 h 05 min, 35 GB per worker |
   - Total for the ladder 240–500: about 40 node-hours.
4. **Fits.**
   - `fits/fits_c5_1d.py freeze|compare|check|explore` is the blind protocol.
   - `fits/tail_fixedA_c5.py` runs the fixed-intercept tail fits.
   - `fits/constrained_c5.py` runs the constrained extrapolation; it needs the exact-C4 result.
   - The cited blind re-implementation (`fits/explore/constrained_L500/xchk/cfit_blind/`, `xfit.py` with
     `make_tasks*.py` and `run*.slurm`) reran its fits on one node: three jobs of about 2 min.

##### Decisions you must not make
- **Frozen blind records.** `fits/frozen/frozen_L320_*` were frozen before the L400 data existed (commit 6e15b08), and
  `frozen_L400_*` before the L500 data existed (commit 50143f0). Do not refreeze them; `replay` checks their sha256.
- **Constrained fit.** The selection thresholds of `constrained_c5.py` were set after its first run had printed the
  known C5 (`fits/explore/constrained_L500/NOTE.txt`). Quote its result with that caveat. The blind re-implementation's
  −731.13 ± 0.10 is the quoted uncertainty.
- **The known C5.** Use it only for comparison, never as a fit input, except in the explicitly labelled
  fixed-intercept fits.

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### Reproduce: lri_hpc_Hamitonian

All commands run from `HT_Pert/code/lri_hpc_Hamitonian`. The sibling `code/lri_eh_hpc` must be present (make variable
`EH`); the records are in `data/HT_1d/thermal_expanse` (make variable `DATA`).

##### 1. Environment
- Python ≥ 3.10 with numpy, scipy, numba and mpmath (`requirements_lri_hpc_Hamitonian.txt`); pytest is not needed.
- Production stacks:
  - solver records: SDSC Expanse, modules `cpu/0.21.2a gcc/13.3.0 python/3.11.9` plus a venv with numpy 2.3.5,
    numba 0.65.1, scipy 1.17.0 (AMD EPYC 7742; `cluster/expanse/env.sh`);
  - analysis: a personal desktop (Apple arm64), Python 3.10.12, numpy 1.24.4, scipy 1.11.1, mpmath 1.3.0,
    numba 0.57.1;
  - `analysis_original/`: the supplier's Linux container, Python 3.13.5, numpy 2.3.5, scipy 1.17.0.
- Tested with the acceptance stack Python 3.12.9, numpy 2.3.5, scipy 1.17.1, numba 0.68.0, mpmath 1.3.0 on symmetry
  (Intel Xeon Gold 6148 and AMD EPYC 7532, tree under node-local `/local1/<USER>/<job>/HT_Pert`), and with the analysis
  stack on the personal desktop (`TESTS_lri_hpc_Hamitonian.md`).
- numpy ≥ 2.4 raises a TypeError in `analysis/identity_checks/reconcile/refit_corrected.py` line 38; the re-pointed
  copy (`public/repoint.py`) then takes `.item()` of the same one-element array. Nothing else is version-specific.
- `make` exports `PYTHONDONTWRITEBYTECODE=1`, one BLAS/OpenMP thread, and `NUMBA_CACHE_DIR=.work/numba_cache`.

##### 2. Fast tests: `make -f public.mk test`
`public/run_tests.py`, four stages (`.work/test_lri_hpc_Hamitonian.txt`):
- `identity`: `analysis/extended/check_identity.py` (the extended model code and the saved Λ ≤ 50 rows are byte-identical
  to `analysis_original`; no model code redefined).
- `engines`: `public/engine_smokes.py`. `ht5.py 2 4` (independent engine through ε⁵) vs `ht5_out_2_4.json` within
  1e-11; `htb5_exact.py 16` (engine B in exact rationals) vs `exact5_c16.json`, identical apart from the run time;
  `topsum.py 8 16 32 64` vs `top_a.jsonl` within 1e-13 relative.
- `suite`: the package's `tests/run_all.py` (11 scripts: ranking and operators against the original reference
  scripts, solver vs reference at Λ = 4..32, uncapped full recursion at Λ = 4, 8, restart, simulated distribution,
  int64 shard of the Λ = 112 basis, acceptance gates, campaign planner, two-lane claims, overlap-checked merge of the
  extended analysis), on a copy in `.work/pkg` with a `GIT_SHA` file (the suite rewrites three files of `benchmarks/`,
  and `test_lane_claims` needs a frozen checkout). Needs ≥ 4 CPUs and flock on a node-local or POSIX file system.
- `regression`: the production validation V, `python -m lri_hpc` thermal d7 at Λ = 40, 50, φ⁶ d5 at 50, d3 at 128,
  then `cluster/expanse/check_regression.py` against `validation_data/` (|new − ref| ≤ 1e-7 + 2e-11 |ref|, gates).
- Cost: see `TESTS_lri_hpc_Hamitonian.md` (minutes on 4 cores, < 2 GB).

##### 3. Replay: `make -f public.mk replay`
`public/replay_hpcham.py` prints rows `a1.*` (`results_map.md`) and writes `.work/replay_lri_hpc_Hamitonian.{txt,json}`;
exit 1 on any FAIL. About 25 s. Steps:
1. Records: the 111 Expanse records and `plan.json`, the supplied Λ ≤ 50 rows. Fingerprint, checksum lists, gates,
   reach, basis count (`public/count_states.py`), raw fractions, the C2 tail amplitude.
2. `public/repoint.py` makes the re-pointed copy `.work/tree` and the replay reruns there, unchanged: `table_rc.py`,
   `run_extended.py`, `diagnose_systematic.py`, `write_updated_results.py`, `explore_lower_edge.py`, `refit_rc.py`,
   `freelead2.py`, `refit_corrected.py`, `challenge-num/fit.py`, `identity_checks/A/{analyze,final_fit}.py`,
   `desc_profile.py`, `fit_phases.py`, `ident_data.py`, `fit_ident_rc.py`, `cmp_ident.py`; plus `public/omega3_eff.py`
   and `public/engine_agree.py`. Row `a1.reruns` compares 14 JSON outputs, the CSV and `UPDATED_RESULTS.md` with the
   shipped ones.
3. Every quoted number is computed from the shipped outputs by the rule of its row, and the fit readings are evaluated
   again on the rerun outputs; a row passes only if both give the quoted value.

##### 4. Small validation run (before any cluster time)
`make -f public.mk smoke`: production items thermal d7 Λ = 52, 60, φ⁶ d5 Λ = 52, d3 Λ = 136 with the shipped solver,
compared with their records (C, r, g, D6 within 1e-7 + 2e-11 |rec|, dimension and fingerprint exact, gates). Bitwise
on symmetry (Xeon Gold 6148, 4 threads) although production ran on AMD EPYC 7742 with 16-48 threads. 93 s, < 5 GB.

`make -f public.mk replay-full` (about 30 min on 8 threads) regenerates the closed-form top-level sums (`topsum.py`,
108 cutoffs Λ = 4..288) and the independent engine (`ht5.py` at Λ = 6..16, `runbig.py` at 18..28) and recomputes the
shift4 limit and the engine agreement (iii) from them.

##### 5. Production (cluster; documented, no target runs it)
1. **Solver campaign** (Expanse, 2026-09-29..10-01, about 1180 core-hours counted as allocated cores × elapsed time, of
   which about 250 were lost to three node failures). `cluster/expanse/` is the layer that ran; it hard-codes the
   production scratch path (`LRIHT_HOME`), account and allocation expiry (`campaign.EXPIRY`); set yours.
   - Validation: `cluster/expanse/submit_validate.sh` (tests, regression V, calibration; jobs 54520426 at f0a7084 and
     54521491 at e1690e8 were the gates of the two production revisions).
   - Submission: `cluster/expanse/submit_cutoffs.py --dry-run`, then for real; lanes run `cluster/expanse/run_lane.py`
     (`lane.slurm`), one exclusive claim per item; `cluster/expanse/status.py` reports; `export_results.py` exports.
   - Memory (peak RSS in the records): thermal 18 GiB at Λ = 72, 99 GiB at 88, 175 GiB at 94, 303 GiB at 100,
     605 GiB at 108, 971 GiB at 112, 1573 GiB at 118; φ⁶ d5 176 GiB at 122, 1466 GiB at 160; d3 140 GiB at 480,
     1454 GiB at 832. Above about 180 GiB the production used Expanse large-shared 2 TB nodes; cutoffs beyond thermal
     118, d5 160, d3 832 do not fit 2 TB under the calibrated memory model (`plan.json`, rejected items).
   - Per item: `python -m lri_hpc --task {thermal,phi6} --degree {7,5,3} --cutoffs L --threads N --output-dir D`;
     a generic Slurm template with placeholders is `public/slurm/item.sbatch` (it lists RSS and time per cutoff), and
     `public/slurm/acceptance.sbatch` runs test, replay and smoke of this package and of `code/lri_eh_hpc` on one node.
2. **Analysis** (single node, numerics on a re-pointed copy `.work/tree`, `lri_hpc` and `lri_eh` on `PYTHONPATH`; run
   `public/repoint.py --work .work` first). Measured on the personal desktop:
   - closed-form top-level sums: `identity_checks/challenge-num/topsum.py 4 6 … 288` (1015 s; `replay-full`) and
     `eps5_window/B/topsum5.py` for Λ = 4..152 (max 81 s at 152);
   - engine B ε⁵: `eps5_window/B/rowresp.py` (598 s), `capped5.py`, `driver5b.py` (full basis, minutes per cutoff),
     exact rationals `htb5_exact.py` (986 s in all), then `table5.py`;
   - engine A: `identity_checks/A/run_desc.py L` for L = 8..72 (1150 s), `eps5_window/A/run5.py` (1626 s),
     `c5tab.py`, `assemble_c5.py`;
   - window table and refits: `eps5_window/reconcile/table_rc.py`, `refit_rc.py`, `challenge-theory/freelead2.py`,
     `identity_checks/reconcile/refit_corrected.py` (seconds each; replayed);
   - phase test: `identity_checks/challenge-theory/offset_c4.py` per phase (about 1050 s each, 4 phases);
   - g²D tables: `code/lri_eh_hpc`, `make -f public.mk replay-full` (degree 5 to Λ = 118 in 40 s, degree 7 to 90 in
     7.5 min on 4 threads).

##### 6. Merge and checks
- New solver records go to a scratch copy of `data/HT_1d/thermal_expanse`; `analysis/extended/run_extended.py` merges
  them with the Λ ≤ 50 rows (overlap-checked; `tests/test_extended_merge.py`); then `make -f public.mk replay` on the
  scratch tree. The fingerprint row requires the shipped `lri_hpc/` source.

##### Decisions you must not make
- **The solver and its caps.** `lri_hpc/` (fingerprint c0c30783…) binds all 111 records. The caps (thermal P ≤ 15,
  Q ≤ 12; φ⁶ d5 14/8; d3 10/4) are exact at the order computed. The acceptance gates (shell ≤ 1e-10, tuning ≤ 1e-6)
  are rules; the quoted worst values 9e-14 and 9e-11 are measured maxima.
- **The pre-registered protocol.** Its thresholds (`write_updated_results.py`: window stability C4 2e-4, C5 5e-4;
  held-out 1e-3; the one-third tail rule) were written after the first new cutoff (Λ = 84) had been seen; the verdict
  is **unresolved** and no matching offset is claimed. Do not re-tune the thresholds.
- **Post hoc readings.** Every extrapolation beyond C3 (windows lo 40–70, bases A–F, the freed tail, the effective ω₃)
  was chosen after the data were seen; keep the words "post hoc". The selection rule of `public/omega3_eff.py`
  (|C5 − exact| ≤ 0.25, range rounded to 10) is fixed.
- **The window.** D^conn is defined with no fitted parameter (telescoping; HT note); do not substitute the isolated g²D
  (`lri_eh`) for it. The ε⁵ table rows Λ = 102..118 use engine B's exact top sums (`table_rc.py`), by design.
- **Tolerances** of the replay (the rows of `results_map.md`, and in `replay_hpcham.py`) are part of the result: fits
  with condition numbers up to 1e16 drift across numpy/BLAS builds (measured: 4e-6 relative in C5 between the
  production stack and the acceptance stack), so reruns are compared with stated tolerances and the quoted readings
  must hold on both.

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### Reproduce: lri_eh_hpc

All commands run from `HT_Pert/code/lri_eh_hpc`. `../lri_hpc_Hamitonian` (make variable `HPCHAM`) supplies the g²D
tables and their generator `gen_deltas.py`.

##### 1. Environment
- Python ≥ 3.10, numpy, numba (with llvmlite), scipy, pytest, mpmath (`requirements_lri_eh_hpc.txt`); sympy only for the
  package's validation extra. Linux/POSIX for the `flock` claims of the campaign tools (the tests use them).
- Supplier's tested stack (`requirements-tested.txt`, receipt): Python 3.13.5, numpy 2.3.5, numba 0.65.1,
  llvmlite 0.47.0, scipy 1.17.0, sympy 1.14.0, pytest 9.0.2. The g²D tables were made on a personal desktop with
  Python 3.10.11, numpy 1.23.5, numba 0.56.4.
- Tested with the acceptance stack Python 3.12.9, numpy 2.3.5, scipy 1.17.1, numba 0.68.0 on symmetry (Intel Xeon
  Gold 6148 and AMD EPYC 7532, tree under node-local `/local1/<USER>/<job>/HT_Pert`), `TESTS_lri_eh_hpc.md`.

##### 2. Fast tests: `make -f public.mk test`
`public/run_tests_eh.py`: `manifest` (102 files of `MANIFEST_SHA256.json`; files listed in `public/SCRUBBED.txt`
reported as scrubbed), `verbatim` (`scripts/verify_package.py`; SKIP only when something is listed in SCRUBBED.txt),
`validate` (`scripts/validate_release.py --threads 4` in a copy `.work/pkg`: pytest `tests/` (32 tests, including a
one- versus four-thread comparison and the independent SciPy oracle in `reference/original/`), then a gated degree-7
item at cutoff 20, then a sealed receipt `.work/pkg/validation/public.json`, which must carry the source fingerprint of
`BUILD_INFO.json`). Needs ≥ 4 CPUs; < 1 GB.

##### 3. Replay: `make -f public.mk replay`
`public/replay_eh.py`, rows `a1.eh.*`, standard library plus mpmath, a few seconds; table also in
`.work/replay_lri_eh_hpc.txt`. No solver run.

##### 4. Small validation run: `make -f public.mk smoke`
`public/g2d_rerun.py --smoke`: `gen_deltas.py` (a copy, with this package on `PYTHONPATH`) at degree 5, Λ = 4..20 and
degree 7, Λ = 4..12; δC, δr, δg within 1e-12 max(1, |ref|) of the shipped tables, dimensions exact, package gates.

##### 5. Production
- **g²D tables**: `make -f public.mk replay-full` regenerates both tables completely (degree 5 Λ = 4..118, degree 7
  Λ = 4..90; on the personal desktop 39 s and 443 s of solver time with 4 threads, largest item 60 s at degree 7
  Λ = 90; on symmetry about 25 s and 670 s with 8 threads, `TESTS_lri_eh_hpc.md`) and compares them as in §4: they
  agree to 8.9e-16 and 9.3e-14. This is the production of these tables. The solver's memory guard must be raised for degree 7 above
  Λ ≈ 78 (`MEMLIM`, default 64 GiB in `replay-full`).
- **Package campaign tools** (`scripts/create_manifest.py`, `slurm/lane.sbatch`, `scripts/join_campaign.py`; README of
  the package): not used for any HT_Pert result. The package's README describes them; account and partition are left
  to the user.

##### 6. Merge and checks
The regenerated tables enter `code/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/table_rc.py` (the complete window
table); compare them with the shipped ones (they are bound by sha256 in other packages' records) rather than replacing
them.

##### Decisions you must not make
- Do not modify anything under `lri_eh/`: the fingerprint 2e2e8ca8… binds the receipt and the tables' provenance.
- The isolated g²D correction is one piece of the window. Do not present it as the complete window D^conn, as a
  physical effective Hamiltonian, or remove its log Λ/17496 term.
- K is a finite part of this isolated prescription (its value depends on the subtraction convention); the paper uses
  it only in the sum K + 0.0186910 for the complete window.

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### Reproduce: lri_c8_hpc

##### 1. Environment
- Python ≥ 3.10 with numpy, numba, scipy and pytest (`requirements_lri_c8_hpc.txt`). threadpoolctl, sympy and mpmath
  are optional.
- `replay` needs only the standard library.
- Production stack: symmetry module `anaconda3/2023.07-2`. That is Python 3.11.4, numpy 1.24.3, numba 0.57.0 (threading
  layer tbb), scipy 1.10.1, threadpoolctl 2.2.0, MKL and pytest 7.4.0. `slurm/symmetry_env.sh` refuses any other stack
  (exit 64).
- Tested also with the acceptance stack: Python 3.12.9, numpy 2.3.5, numba 0.68.0, scipy 1.17.1, on Intel Xeon Gold 6148
  and AMD EPYC 7543 nodes of symmetry, from trees under node-local `/local1` (`TESTS_lri_c8_hpc.md`).

##### 2. Fast tests: `make -f public.mk test`
- `public/verify_manifest_public.py` checks the 164 files of `MANIFEST_SHA256.json`. Files in `public/SCRUBBED.txt` are
  reported as scrubbed; nothing under `src/` may be listed.
- `public/run_tests_c8.py` copies the package to `.work/tree` and runs two steps there:
  - pytest `tests/`, complete and unfiltered with a fresh Numba cache, as the release validation does. Required:
    74 passed. The tests cover:
    - the independent SciPy eighth-order recursion at Λ = 2, 4, 6, 8, 12;
    - exact rationals;
    - stored vs ranked backends;
    - int64 kernels;
    - checkpoint and resume;
    - owners and locks;
    - a shimmed Slurm wrapper (nothing is submitted).
  - `scripts/regression_saved_grid.py --compare benchmarks/REGRESSION_GRID.json`. It recomputes all 38 original records
    (Λ ≤ 50); C8 must agree with the grid within 1e-7 + 2e-11 |ref|. It was bitwise (38 of 38) on both tested stacks.
- **The Numba threading layer is pinned**, as the production environment pins it (`slurm/symmetry_env.sh` forces tbb).
  The wrapper uses the caller's `NUMBA_THREADING_LAYER` if set, else tbb when it loads, else workqueue.
  - Every output records its runtime configuration, including the list of loaded BLAS/OpenMP libraries. Shard
    assembly and export refuse mixed configurations.
  - With Numba's default layer and no tbb, the order of that list depends on whether a process compiled its kernels
    or loaded them from the cache. Two tests (shard assembly, export of mixed thread counts) then fail. This was
    observed with Python 3.12.9 and numba 0.68.0 (symmetry jobs 574957, 574960).
  - The layer changes no number.
- Cost with the default `THREADS=4` on one exclusive node: 6 min on a Xeon Gold 6148 with the acceptance stack (job
  575032), 4 min with the production stack, 4.4 min on an AMD EPYC 7543 (job 575138); 1.2 GiB.

##### 3. Replay: `make -f public.mk replay`
- Every quoted number of the package is recomputed from the shipped records: rows `c8.*` of `results_map.md`, with
  their tolerances.
- About 1 s. The output is also written to `.work/replay_lri_c8_hpc.txt`.
- Two rows are RECORDED: `c8.validation` and `c8.original`, read from the self-hashed validation receipt.
  `make -f public.mk replay-full` recomputes them (default `THREADS=4`: 13 min on a Xeon Gold 6148, 9 min on an AMD
  EPYC 7543; 8.6 GiB): the export of the 42 outputs and the original-solver comparison at Λ = 60. Both were bitwise
  equal to the records with Python 3.12.9 on both CPUs (jobs 575032, 575137, 575138).

##### 4. Small validation run (before any cluster time)
- `make -f public.mk smoke` reruns the production item Λ = 52 (raw and vacuum_only, stored backend) and compares C, r,
  g and the energies with the shipped outputs.
  - On the production stack they agree bit for bit.
  - Elsewhere the package's cross-stack tolerance applies, atol 1e-7 + rtol 2e-11. It was also bitwise with Python
    3.12.9, numpy 2.3.5, numba 0.68.0, on the Xeon Gold 6148 and on an AMD EPYC 7543.
  - About 1.2 min (Intel) or 0.9 min (AMD) with the default `THREADS=4`, 1.6 GiB.
- On the target cluster, then run the package's own release validation on one compute node:
  `scripts/validate_release.py --full --threads <cores> --output <dir>/receipt.json`, or `slurm/submit_defq.sh validate`
  on symmetry. Production on symmetry took 464 s (job 569659).
  - It runs the manifest check, pytest with a fresh cache, the grid replay, the original solver vs the stored and
    ranked backends at Λ = 60 (both prescriptions), and a file-system probe.
  - `scripts/make_campaign.py` accepts only a passing full compute-node receipt for the current source digest and
    Python stack.
  - The receipt's first step is the original `tests/verify_manifest.py`. It fails on the six scrubbed files of the
    published tree and on any file you adapt, and then the receipt is `fail`. Run the release validation in a working
    copy with a rehashed manifest (section 5, step 0). For a plain check of the published tree use
    `public/verify_manifest_public.py` (`make test` does).

##### 5. Production (cluster)
The runbook is `docs/SYMMETRY.md` (symmetry defq) and `docs/HPC.md` (design).
- The package's `slurm/` is the verbatim symmetry layer: `symmetry_env.sh`, `defq_validate.slurm`, `defq_lane.slurm`
  and `submit_defq.sh`.
- On another cluster, adapt its module line and stack check (exit 64 on any other stack) and the `#SBATCH` lines, in
  a copy.
- Set `C8_ROOT`, `C8_DATA` and the partition yourself. The shipped data path is the authors' scratch path
  (`<SCRATCH>/lri_c8`), and `slurm/submit_defq.sh lanes` refuses an output directory outside `/mnt/beegfs/`.
0. **Working copy and manifest** (before the validation).
   - Copy `code/lri_c8_hpc` to a working directory outside the `HT_Pert` tree (say `$C8_ROOT`). Adapt `slurm/` and
     anything else you need there: the module line and stack check, the `#SBATCH` lines, the `C8_DATA` default, the
     `/mnt/beegfs/` check of `submit_defq.sh`. Change nothing under `src/`.
   - Then run `python3 public/rehash_manifest.py $C8_ROOT`. It recomputes the sha256 of the 164 files that
     `MANIFEST_SHA256.json` lists (same paths, same format as `scripts/update_manifest.py`, which needs a git checkout)
     and rewrites the working copy's manifest.
   - It refuses, and writes nothing, if the folder sits in the published layout (`../../data/HT_1d/c8` exists), if a
     listed file is missing, or if anything under `src/` changed: the source digest must stay dd811aca….
   - Without this step `tests/verify_manifest.py` fails on the scrubbed or adapted files, the receipt of step 1 is
     `fail`, and `make_campaign.py` refuses it ("Passing receipt for current source required"). With it the manifest
     step passes, and `src/` and the source digest are unchanged, so the new receipt, campaign and outputs carry the
     same digest as the shipped records.
   - Demonstrated on symmetry in the fix round (`TESTS_lri_c8_hpc.md`): scrubbed tree, adapted `submit_defq.sh`,
     rehash, `scripts/validate_release.py` status `pass`, `make_campaign.py` accepts the receipt.
1. **Validation**: `slurm/submit_defq.sh validate`. One exclusive node, about 8 min. It writes
   `$C8_DATA/validation/receipt_<src16>.json`.
2. **Campaign**:
   `scripts/make_campaign.py --cutoffs $(seq 52 2 92) --schemes raw vacuum_only --outer-backend auto --threads 40
   --memory-limit-gib 170 --receipt <receipt> --output <campaign.json>`.
   - The backend is `auto`: stored for Λ ≤ 88, ranked for Λ = 90 and 92.
   - The planner's conservative memory envelope admits items up to 170 GiB.
3. **Lanes**: `slurm/submit_defq.sh lanes <campaign.json> <out>`.
   - 42 exclusive-node array tasks, largest first, at most 8 at a time.
   - Each lane runs one solver process on 40 threads (numactl physcpubind + interleave), with `--mem=180G`.
   - Measured: 18.3 min of wall time for the whole array on 8 nodes; 8605.5 s of solver time in total (about 2.4
     node-hours).
   - Per item: from 7.4 s (raw Λ = 52, 1.6 GiB) to 825 s (raw, ranked) and 1028 s (vacuum_only, ranked) at Λ = 92.
   - Peak RSS by cutoff: Λ = 60 4.2 GiB, Λ = 72 18 GiB, Λ = 80 45 GiB, Λ = 88 107 GiB (stored), Λ = 92 105 GiB
     (ranked). Smaller machines can rerun the lower cutoffs.
4. **Export**: `python -m lri_c8 export --inputs <out>/accepted/<scheme>_L*_d8.json --output <exports>/<scheme>_L52-92.json`,
   for raw and vacuum_only.
5. **data.json**: `public/build_data_json.py <out.json> --data <data root> --thermal <lri_hpc_Hamitonian>/analysis/extended`.
   It must be byte-identical to `data/HT_1d/c8/extrapolation/data.json` (sha256 ccc77dfa…). With new exports, only
   the raw and vacuum_only tables can change.

Expect C, r and g bit for bit on the production stack: thread count and backend do not change any output bit. On another
stack, expect agreement within 1e-7 + 2e-11 |C|.

##### 6. Merge and checks
- `make -f public.mk replay` on the new records, after copying them to `data/HT_1d/c8` in a scratch tree.
  - The rows bind outputs, journals, campaign, exports and receipt to each other and to the source digest.
  - The sha256 rows will differ for a new campaign; the values must agree within the tolerance above.
- The C8 fits that use these data are in `code/lri_1d_dconn_refit`.

##### Decisions you must not make
- **Nothing under `src/lri_c8`** may be added or changed. The source digest dd811aca… gates `make_campaign`, `resume`
  and `export`, and it binds every record.
- **Allowed and needed: rehashing the manifest of a working copy.** After adapting files outside `src/` (or starting
  from the scrubbed published files), regenerate `MANIFEST_SHA256.json` in the working copy with
  `public/rehash_manifest.py` (section 5, step 0). It keeps the 164 listed paths and refuses any change under `src/`.
  Never rewrite the manifest of the published tree, and never rehash after editing `src/`.
- **Prescriptions.** `vacuum_only` is the isolated g²D term only. It is not the complete window D^conn and must not be
  labelled so. The quoted C8 extrapolation (`\HTpCeightOne`, HT_Pert note) uses D^conn from S10 (Λ ≤ 72) plus a
  model beyond; see `code/lri_1d_dconn_refit`.
- **Caps and acceptance.** The physical caps P ≤ 19, Q ≤ 16 and the solver's acceptance thresholds are part of the
  method. The thresholds are shell 1e-10, tuning 1e-6, low order 1e-7, and E3 − E0 = C within 1e-8 + 2e-14|C|.
  - The bounds quoted with the C8 table (1.6e-14, 7.9e-13, 1.95e-9) are measured maxima, not acceptance rules.
- **The superseded extrapolation.** The four-lens C8 extrapolation of 2026-10-04 (8.0655e6) is superseded and is not
  shipped. Do not quote it as the HT C8.
- **Scope of the comparison with the original solver.** On the cluster the original solver was compared only at
  Λ ≤ 60. Do not describe the Λ = 52..92 data as checked against it.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### Reproduce: lri_d1_full_coefficient_flow

1. **Environment.** Python ≥ 3.10 with numpy, scipy and mpmath (`requirements_lri_d1_full_coefficient_flow.txt`;
   matplotlib only for `code/plot.py`). Single-threaded BLAS (`public.mk` sets OPENBLAS/MKL/OMP_NUM_THREADS = 1).
   - The supplied archive was built with Python 3.13.5, numpy 2.3.5, scipy 1.17.0 (`provenance/ENVIRONMENT.json`).
   - Production ran on symmetry with anaconda3/2023.07-2: Python 3.11.4, numpy 1.24.3, scipy 1.10.1, 63-bit long
     double (x86). `slurm/symmetry_env.sh` refuses any other stack unless `S10_LOCAL_TEST=1`.
   - Long double differs between x86 (63-bit mantissa) and ARM (53-bit): fresh runs agree with the archive at
     about 1e-13 instead of 1e-15, still far inside the gate's rtol 1e-10.
2. **`make -f public.mk test`**, then **`make -f public.mk replay`**. On one Xeon Gold 6148 core of symmetry: test
   about 2 min, replay seconds (`TESTS_lri_d1_full_coefficient_flow.md`).
3. **Small validation run: `make -f public.mk smoke`.** It repeats the production gate's validation (Dconn L = 40,
   42, 44 and raw L = 44 against the archive, rtol 1e-10, exact counts) in about 10–13 min and 2.4 GiB. Run it before
   any cluster time.
4. **Production rerun** (cluster; `SYMMETRY_EXTENSION.md` has the full procedure).
   - Deploy the commit as a read-only snapshot and submit from it. `slurm/submit.sh` refuses a writable tree and
     exports the solver's sha256, and every job re-checks that sha256 on its node.
   - `slurm/submit.sh validate`: Dconn L = 40, 42, 44 and raw L = 44 against the archive. Production refuses to
     start until `code/check_validation.py` has recomputed these comparisons against the archive records pinned
     by sha256, for the same solver and the same Python/numpy/scipy.
   - `slurm/submit.sh production 46,48,...,72`: one cutoff per array task, one process per exclusive defq node.
   - Measured cost (symmetry defq, 2026-10-08; `seconds` and `maxrss_kib` of the records), 38.5 node-hours in all:
     - L = 46: 0.1 h, 3.5 GiB, 2.8 M states;
     - L = 60: 1.5 h, 28 GiB, 22.7 M states;
     - L = 72: 11.7 h, 117 GiB, 109.4 M states. L ≥ 74 is not expected to fit a 180 GB node with this
       implementation (SYMMETRY_EXTENSION.md).
   - Placeholders: set `S10_ROOT` (the snapshot) and `S10_DATA` (the output root; the shipped scripts name the
     original cluster path) and the partition in `slurm/*.slurm`.
5. **Checks after production.**
   - `public/make_dconn_minus_raw.py --data <data root>` writes the dC table, dC_k = C_k − raw_k for k = 6, 7, 8
     (raw from data/HT_1d/c8/extrapolation/data.json).
   - The replay rows s10.match and s10.dC678 compare the records with the exact ε^4/ε^5 windows.

##### Decisions you must not make
- The production gate is part of the result. Production records count only if they come from the snapshot whose
  solver sha256 (854fc763…) passed the validation against the archive, on the same Python/numpy/scipy stack.
- The archive records (results/new_coefficients, L ≤ 44) are the reference of the gate; they are pinned by sha256 in
  `code/check_validation.py` and in MANIFEST.sha256. Do not regenerate them in place: the package's own tests
  rewrite results/ and must run on a copy (public/run_tests_s10.py does).
- The dC table subtracts the HT raw coefficients of the C8 campaign (data.json, sha256 ccc77dfa…), not S10 raw runs;
  the delta-stage outputs record its sha256 (3105e037…).

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### Reproduce: lri_1d_dconn_refit

1. **Environment.** Python ≥ 3.10 with numpy and mpmath (`requirements_lri_1d_dconn_refit.txt`); python-flint for the
   joint lens and the key-fit refit. Single-threaded BLAS (`public.mk` sets it).
   - The stages ran with three stacks:
     - delta stage: Python 3.10.12, numpy 1.24.4, mpmath 1.3.0 on the authors' personal desktop (macOS, arm64);
     - joint lens: a symmetry venv with Python 3.11.3, numpy 2.4.6, mpmath 1.4.1 and python-flint 0.9.0;
     - model-independent lens: symmetry anaconda3/2023.07-2 (Python 3.11.4, numpy 1.24.3, mpmath 1.3).
   - Tested here: Python 3.12.9, numpy 2.3.5, mpmath 1.3.0, python-flint 0.9.0 (symmetry, Xeon Gold 6148;
     `TESTS_lri_1d_dconn_refit.md`).
2. **`make -f public.mk test`** (with `FLINT_PY=<python that imports flint>` for the key fits), then
   **`make -f public.mk replay`**.
   - `test` rebuilds the delta stage from its inputs on a re-pointed copy in `.work/rt`: `check_inputs`,
     `build_delta --extra-dconn <dC table> --tag delta_v1_hi72`, `regen_variants`, `smooth_central`, `check_outputs`
     and `validate_hi72` (seq, hold, noise). It compares every rebuilt table and validation record with the shipped
     `delta/out`, bitwise or within 1e-9 field-scaled (relative to the largest |x| of the list that holds the
     number, or to the number itself; no absolute floor).
   - It then reruns the model-independent lens's `headline.py` and `final72.py` from the shipped intermediate outputs
     (bitwise or 1e-12 field-scaled).
   - With `FLINT_PY` it refits 12 named key fits of the joint lens (o7, hi = 118) with the shipped `scan.py`, against
     the shipped summaries at 1e-9 relative.
3. **Full refit** (cluster; not a make target). The scripts name the cluster workspace and the venv by absolute paths;
   edit those lines (`W=`, `PY=`, `R=` in the sbatch/sh files), or run the Python entry points directly with the
   environment variables below.
   - **Delta stage** (seconds to a minute on one core; `test` already does it). Copy its five hi = 72 tables to the
     workspace: `delta_v1_hi72_corrected.json` and `variants_full_hi72.json`, plus the run-1 tables
     `delta/archived_out_delta_v1/delta_v1_corrected.json` and `run1/joint/out/variants_full.json`.
   - **Joint scans**, with `DCONN_CORRECTED`, `DCONN_VARIANTS_FULL`, `DCONN_OLD_CORRECTED`, `DCONN_OLD_VARIANTS_FULL`
     set to those four files:
     - `joint/code/scan.py o8` and `o7` (the five datasets; `joint/cluster/run_scan_shared.sbatch`);
     - the weighted pair with `JOINT_DATASETS=dconn_w` and output suffix `_w`.
     - Measured on symmetry sharedq (4 workers each): o8 640 s (186,624 fits), o7 302 s (129,600), o8_w 287 s
       (46,656), o7_w 137 s (32,400).
   - **Joint post-processing:** `joint/cluster/post_r72.sh` (tabulate, analyze_low/c8 per dataset, analyze_r72,
     propagate, checks, summary, noise). About 6 min; give it 15 GB of RAM, because tabulate builds a 615 MB cache.
   - **Model-independent grids:** `model-independent/code/run_list72.sbatch` with `runlist72_main.txt`,
     `runlist72_q.txt` and `runlist72_qfloor.txt` (exclusive node, mpmath 50 digits, about 35 s per run on 40 cores),
     then `members_*`, `summarize.py`, `headline.py`, `compare72.py` and `final72.py` (`MI_PRIMARY=run2_fmedoid`).
   - **Compare** with the shipped summaries. The arb and mpmath intercepts were bit-identical when the verifier redid
     them. Floating-point post-processing should agree to about 1e-12. The 'stat' column may differ by about 1.6e-5
     relative between CPU vendors, which changes no cut.
   - **Verifier** (optional, cited check): `verify/code/` with `jmc.sbatch` (symmetry job 572083, 17.6 min on 8 cores).

##### Decisions you must not make
- **The windows and selections are post hoc** and fixed as run: lower edges, hi = 118 (C4..C7) and hi = 92 (C8), the
  floor and stat criteria, the noise weights of dconn_w, and the C8 calibration window |C6 rel| ≤ 1e-4,
  |C7 + 322550| ≤ 82.
  - The code hard-codes C7 = −322550 ± 41 and the old C8 reference 8,066,723. The paper's C7 uncertainty is now ±40 and
    its C8 reference 8,059,767. Keep the run's values for a rerun; the deviation macros compare with the current
    references.
- **The quoted ranges are unions with stated rounding** (`results_map.md`). Components: fixed A–F from the unweighted
  dataset dconn, floor+stat from the weighted dataset dconn_w, MI from the model-independent lens.
  - C4: central values, 3 decimals, nearest (outward identical).
  - C5: freed tail and floor+stat 16–84, 2 decimals, nearest (outward would give −730.96 at the upper end).
  - C6: three lenses, integers, nearest (outward identical).
  - C7: three lenses (model-independent widened by ±6), outward to tens.
  - `\HTpCeightOneUncal`: five-family 16–84 union, 3 decimals, nearest; the `\HTpCeightOneCalRange` reconstruction:
    outward to 3 decimals.
  - Do not substitute other families or datasets (the weighted fixed A–F would give a C7 lower end of −322,900; row
    rf.C7w prints it as information).
- **The blind forecast** (`delta/archived_out_delta_v1/frozen_forecast_L46_72.json`, self-hashed) was frozen before the
  Λ = 46..72 data existed. Never refreeze it.
- **The exact dC6..dC8 at Λ ≤ 72 are data, not model.** Do not smooth or refit them in the primary datasets. The s46
  variant is a labelled sensitivity.
- `\HTpCeightOneCalRange` and the "unchanged" reading of `\HTpCeightOneUncal` are the stage's judgements (INFO rows).

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### Reproduce: lri_d1_fullblock_tail_response

1. **Environment.**
   - Python ≥ 3.10 with numpy, scipy, sympy and mpmath (`requirements_lri_d1_fullblock_tail_response.txt`).
     matplotlib is needed only for `code/plot.py`.
   - public.mk sets the thread variables to 1 and `MPLBACKEND=Agg`.
   - `tests/validate.py` and `code/phase_response_shell.py` need x86-64 80-bit long double
     (`np.finfo(np.longdouble).nmant >= 63`). They stop with "Extended longdouble required" on Apple arm64; the test
     target SKIPs `validate.py` there with a message.
   - The package was generated with Python 3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0, mpmath 1.3.0 and
     matplotlib 3.10.8 on x86-64 Linux (`results/ENVIRONMENT.json`).
2. **Fast tests.** Run `make -f public.mk test` (seconds).
3. **Replay.** Run `make -f public.mk replay` (about 15 s; rows fb.* of `results_map.md`).
   - `make -f public.mk replay-full` adds float reruns of all 13 full-J response records (about 3.5 min, one core; 209 s on symmetry Intel).
   - Tolerances:
     - manifest, exact-rational reruns and stated values: exact;
     - float response reruns: ≤ 1e-12 scaled, |Δ|/max(1, |record|);
     - annulus rows: ≤ 1e-8 relative. Platform drift measured 3e-10 on Apple arm64 against the package's x86-64
       records; the REPORT table is checked to its 9 decimals.
4. **Small validation run.** None is needed beyond `test`; every stage takes seconds on one core.
5. **Full regeneration of the package's records** (optional; not needed for any quoted statement).
   - These are the package's own commands (its README, "Validate and regenerate").
   - They rewrite `results/`, so run them on a copy, never in the shipped tree:
     ```bash
     cp -r . <TMP>/fullblock_copy && cd <TMP>/fullblock_copy && rm -rf public public.mk .work   (a copy outside the repository)
     python tests/verify_manifest.py
     python tests/run_all.py                    # x86-64 only (validate.py)
     python code/response.py --cutoffs 2 4 6 8 12 16 20 24 28 --channels phi6 phase number full --schemes dconn --degree 8
     python code/response.py --cutoffs 2 4 6 8 --channels phi6 phase number full --schemes raw --degree 8
     python code/exact_response.py --cutoffs 2 4 --degree 8
     python code/phase_response_shell.py --cutoffs 2 4 8 16 32 64 128 256 512 1024 4096 16384 65536 262144   # x86-64
     python code/phase_finite_part.py --N 256 --order 6 --dps 50
     python code/phase_finite_part.py --N 512 --order 6 --dps 55
     python code/mixing_asymptotics.py
     python code/analyze.py && python code/plot.py
     ```
   - Measured cost in the authors' environment, from the records' `seconds` fields:
     - responses and exact records: about 6 min in all, with μ = 28 at 64–74 s per channel and 100,104 states;
     - shells: under 3 s;
     - finite parts: about 35 s each.
   - Then compare the regenerated files with `MANIFEST.sha256` or with the shipped `results/`. Float records may differ
     in the last digits across platforms.
6. **Merge and checks.** Nothing to merge.

##### Decisions you must not make
- **Do not identify the auxiliary low cutoff μ with the outer HT cutoff Λ.** Do not use Eq. (3) at μ = Λ as a
  complete tail. METHOD Secs. 1, 3 and 6 rule both out.
- **Do not present the J-channel amplitude 2/(3√π), or B, as verified physical C4 tail coefficients.** The review rated
  the J sign and normalisation only "plausible" (`REVIEWS.md`). Nor quote the post hoc "J-informed" C4 misses: they
  were never part of this package and have no public replay.
- **Do not edit the shipped files.** They are bound by `MANIFEST.sha256`. Files the maintainer scrubbed are listed in
  `public/SCRUBBED.txt`, and only those may differ.
- **Keep the memory and state guards** of `code/response.py`. The package says that raising or removing a guard is not
  an optimisation.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### Reproduce: lri_d2_coeff_hpc

Run from `HT_Pert/code/lri_d2_coeff_hpc`. Linux x86-64; Python ≥ 3.10 with numpy, scipy, numba, pytest, mpmath,
threadpoolctl (`public/requirements.txt`; the production used Python 3.11.4, numpy 2.3.5, scipy 1.17.0, numba 0.65.1,
g++ 11.4). BLAS at one thread.

1. `make -f public.mk verify-manifest` (seconds): the three checksum lists (package, reference, reference/upstream);
   files scrubbed for publication (listed in `public/SCRUBBED.txt`) are checked for presence only.
2. `make -f public.mk test` (≈ 2 min, `THREADS=4`): `tests/run_all.py` on a scratch copy: native/JIT warmup, then
   61 pytest tests (numerics against the delivered exact oracle, storage, checkpoint/resume, cluster layer). Expected
   `61 passed`.
3. `make -f public.mk smoke` (≈ 1 min): reruns L = 6, eighth order, consistent and raw, and compares C, r, g, E_p and
   the vacuum tables with `data/HT_2d/prod/check_small_symmetry/d8/*_L6.json` (scaled tolerance 1e-12).
4. `make -f public.mk replay` (seconds, standard library only): `public/replay_prod.py`, checks p2.prod.* of
   results_map.md (8 checks): the 41 record and 3 campaign-manifest self-hashes, the solver source digest = every record's `source_digest`, the two
   coefficient tables = the records, the sha256 of the two tables cited by HT, the cutoff range (L = 2..34 raw and
   consistent, 2..14 literal), eighth order, and the two validation receipts.

##### Production (documented; measured cost)
The records were produced with the cluster layer of this commit (runbook `docs/CLUSTER.md`):
`scripts/make_release.py` → release tar (sha256 2e2edf6c…), `scripts/submit.py validate` (receipt), then
`scripts/make_campaign.py` + `scripts/submit.py campaign` (one job per (scheme, L)):
- symmetry, campaign prod1, L = 16..30 even, raw + consistent, degree 8: 16 jobs (571628–571643) on amdq, whole AMD
  nodes; the largest (L = 30 consistent) 7.4 min, peak RSS 87 GiB. Validation 571623 (61 tests + L = 22 replay).
- SDSC Expanse, campaign prod2, L = 32, 34: 4 jobs (54765966–68, 54771256); L = 34 consistent 48 min, 463 GiB (a
  large-memory node). Validation 54765932, bitwise equal to symmetry.
- check_small_symmetry, L = 2..14, all three schemes: seconds each.
A single L ≤ 30 point is `python -m lri_coeff run --cutoff L --degree 8 --scheme consistent --threads 64
--memory-gib 200 --output out.json` (README "A coefficient calculation"); plan memory first with `python -m lri_coeff
plan`. Total production cost: a few node-hours.

##### Decisions you must not make
- Do not lower the particle support or the floating-point precision to make a job fit (the guard refuses it).
- The window prescriptions are those of the delivered package; the paper's continuum values do not come from them.
- Tolerances of the replay and smoke are as shipped.

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

#### Reproduce: lri_2d_coeff_independent_check

Run from `HT_Pert/code/lri_2d_coeff_independent_check`. Python ≥ 3.10. Replay and replay-full need numpy and mpmath;
test needs numpy, scipy, mpmath, numba and **python-flint** (`public/requirements.txt`; python-flint has wheels for
Linux x86-64 and macOS). The cluster runs used Python 3.11.4 with numpy 2.x, scipy 1.17, mpmath 1.4, numba 0.68 and
python-flint 0.9.0; the local runs numpy 1.24–2.3. BLAS at one thread.

1. `make -f public.mk verify-snapshot` (seconds): sha256 of the snapshot's files (`public/SNAPSHOT.sha256`; files
   listed in `public/SCRUBBED.txt` were scrubbed for publication and are checked for presence only).
2. `make -f public.mk test` (≈ 1.6–1.8 min on one node with `WORKERS=16`, ≈ 3 min with `WORKERS=4`): `public/test_p2.py` reruns every code at small cutoff in a
   scratch copy (`.work/tree`) and compares with the shipped outputs:
   - exact equality: rs_exact L = 4 (three schemes), ce_wc L = 4 (Wcs and Wc, every value);
   - float64 codes, tolerances 1e-11 to 1e-14 as printed: continuum L ≤ 30, c4_exact Lmax 30, the window-shift codes,
     tagchan Lmax 100, and the C5 production engine at Lmax 12, both `large_L/lib` and `large_L/lib_opt`.
   - t.cauchy: `cauchy/tests.py`, the self-tests of the Cauchy solver (two-point function, operators against brute force,
     Hellmann–Feynman derivatives at 256 bits, numpy backend), 18–21 s. It **needs python-flint**: the Cauchy solver is
     one of the two clean-room solvers of the cited check (HT_Pert note, Sec. 4.2); without python-flint t.cauchy FAILs
     with "install python-flint".
3. `make -f public.mk smoke` (≈ 30 s): the two exact reruns of step 2.
4. `make -f public.mk replay` (≈ 10 s): `public/replay_p2.py`, 64 checks p2.* (results_map.md). Each recomputes a
   quoted number from the shipped records and prints PASS/FAIL with the value, the expected value and the tolerance.
   Exit 1 on any FAIL.
5. `make -f public.mk replay-full` (≈ 1 min): `public/replay_full.py` reruns the shipped fit and parent-check scripts
   (asymptotics_C2_C3, fits_c4, fits_final, delta3_fits, legw_logs, c5_fits300, refit_c5_300, parent_check_wcs/*,
   parent_check_p5/verify_p5) on a scratch copy and compares their outputs with the shipped ones number by number.
   `c4_exact/fits_c4.py` (verbatim) skips every `results/c4_L*.npz` whose absolute path contains the substring
   "local" (meant for `c4_L160_local.npz`), so under a checkout such as `/local1/...` or `/usr/local/...` it would
   find no input. replay-full therefore runs that script from a copy in a fresh directory whose path has no "local"
   (`$HTP_NOLOCAL_TMP` if set, else the system temporary directory, `/tmp`, `/var/tmp`, `/dev/shm` or the home
   directory) and FAILs with a message if none qualifies; set `HTP_NOLOCAL_TMP` then.

##### Production (documented reruns; measured cost; all on the symmetry cluster, whole nodes)
`public/slurm/run.sbatch.in` is a template: `sbatch -p <PARTITION> --mem=<MEM> --time=<TIME>
public/slurm/run.sbatch.in <SUBDIR> "<ARGS>"` (from this folder; sets `RS_EXACT_DIR=rs_exact`).
| output (shipped) | command (in SUBDIR) | cost |
|---|---|---|
| `rs_exact/results/*.json` | `fast_modular.py --L L --K 16 --nprimes N --ncheck M --procs 24 --out out/fast_L<L>.json` (N, M as in each result's `precision_note`; driver `run_fast.sbatch`), then `export_results.py`; `ref_fraction.py` is the Fraction reference (rs_exact/README.md) | L = 18: 17 min on a 64-core AMD node |
| `cauchy/results/*.json` | `run_points.py`, `make_results.py` (cauchy/README.md; python-flint) | L = 8: ≈ 8 min per contour point, 64 in parallel |
| `continuum/exact_C2_C3.csv` | `exact_low_orders.py --L 2,4,…,600 --out exact_C2_C3.csv` | minutes |
| `c4_exact/results/c4_L2000.npz` | `c4_run.py --Lmax 2000 --workers 7 --cache cache_L2000 --out results/c4_L2000.npz` (5 threads per worker) | 80–90 min on a 40-core Intel node |
| `c4_exact/results/windows_L20000.npz` | `windows.py --Lmax 20000 --out results/windows_L20000.npz` | minutes |
| `residual_log/results/offdiag_L20000.npz`, `nm_L8000.npz`, `legw/legw_L1000.npz` | `offdiag_window.py --Lmax 20000`, `nm_window.py --Lmax 8000`, `nm_legw.py --Lmax 1000` (with `--out`) | minutes each |
| `residual_log/C4W_by_L.csv` | `make_csv.py` (from the three files above) | seconds |
| `residual_log/results/eps5/dC5_L1000_all.npz` | `eps5/delta5.py --Lmax 1000 --workers 26 --cache dcache --out ../results/eps5/dC5_L1000_all.npz` | ≈ 35 min, one AMD node |
| `residual_log/large_L/results/c5_L300.npz` | 12 shards `large_L/lib_opt/prod5.py --Lmax 300 --workers 3 --raw_only --shard i/12 --cache CACHE --out X`, then the assembly `large_L/lib/prod5.py --Lmax 300 --workers 3 --raw_only --cache CACHE --out results/c5_L300.npz` | ≈ 55 node-hours with lib_opt on 40-core Intel nodes, 180 GB (4 workers per node ran out of memory; 3 fit). The unmodified engine `lib` costs about 5–10× more (the first attempt used 130 node-hours for 40 % of the tasks). |
| `residual_log/large_L/results/tag3_L16000.npz`, `tag3nu_L4000.npz` | `tagchan.py --Lmax 16000 --out …`; `tagchan.py --Lmax 4000 --single --nus 4,6,8,16 --out …` | 11 min, 18 GB; < 1 min |
| `residual_log/results/tag/*.json` | `brute_desc_tag.py`, `brute_desc_tag4.py` (exact tagged channels, L ≤ 16) | minutes to an hour per L at L = 16 |
| `residual_log/ce_wc/out_*/*.json` | `ce_wc/ce_run.py --L L --schemes Wcs --delta3=<exact δ⁽³⁾(L)> --desc odd:all,even:1-2 --procs 24 --out …` (δ⁽³⁾ rationals: `out_wcs/*.json` meta, or the tagged-φ files); Wc likewise; Wcs4X with `--x4file x4/x4_L<L>.json` (`p5_prepare_x4.py`) | L = 16: ≈ 10 min, 6.6 GB on an AMD node |
| `complete_exact/results/*.json` | `complete_exact/ce_run.py` (complete_exact/README.md) | L = 16: tens of minutes |
Note: `c4_exact/fits_c4.py`, `make_csv.py` and `plot_c4.py` ignore any `c4_L*.npz` whose absolute path contains
"local" (see step 5); run them from a path without that substring.
The shipped `residual_log/jobs/*.sbatch`, `large_L/jobs/*.sbatch` and the `*.sbatch` of the subfolders are the drivers as
they ran (their cluster paths are history; use the template).

##### Decisions you must not make
- The fit protocols are fixed: C4^W = median of the 9 no-log fits (towers T22, T22+l3/L, T23 × Lmin 200/300/400),
  uncertainty half the spread; C5 = median of the 15 no-log fits with the ln³L/L tail (k1 = 3, k2 = 0..2,
  Lmin 30..100) at L ≤ 300, uncertainty half the range. The tower family was chosen by blind tests (fit L ≤ 200,
  predict 202..300), not by agreement with the continuum value. Do not add or drop towers or windows to move a value.
- The windows contain no fitted parameter; do not tune δ⁽³⁾, S or any window coefficient.
- A residual ln L in C5 is not excluded (|b| ≲ 0.01, shift ≈ 0.1); keep that caveat with the value.
- C6..C8 are not reproduced in d = 2; do not quote extrapolations of them.

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### Reproducing the d = 3 exact-sum numbers (lri_3d_c4_exact)

Run everything from `HT_Pert/code/lri_3d_c4_exact` with relative paths. The sibling `../lri_3d_hpc` (the production
package; its reference operators and reference results) and `../../data/HT_3d/pert3d/results` (its campaign records)
must be present, as they are in the repository. Order: environment, `test`, `replay`, production.

##### 1. Environment

Python >= 3.10 with numpy, scipy, numba and mpmath (`public/requirements.txt`); `replay` needs only numpy. Production:
CPython 3.12.9, numpy 2.5.3, scipy 1.17.0, numba 0.68.0, mpmath 1.3.0 on the symmetry cluster; the analysis scripts
(fits) ran on a personal desktop. Caches (numba, the engine's task cache) go to node-local temporary storage.

##### 2. `make -f public.mk test` (1-3.5 min, 0.25 GB, up to 8 worker processes)

`public/run_tests.py` recomputes the sums from scratch at small cutoffs and compares (scaled difference
|a - b| / max(1, |b|)):

| Stage | Recomputes | Compared with | Tolerance |
|---|---|---|---|
| windows | `windows3d.py --Lmax 400` | `results/windows_L8000.npz` | 1e-12 |
| offdiag | `offdiag3d.py --Lmax 200` | `results/offdiag_L400.npz` | 1e-12 |
| dchi | `dchi3d.py --Lmax 120` | `results/dchi_L120.npz` | 1e-10 (r2, about 10 in size, summed on another platform: 2e-11) |
| c4 | `c4_run3d.py --Lmax 40` | `results/c4_L600.npz` | 1e-9 (production at Lmax = 600, other angular quadrature) |
| c4_vs_pkg | `validate_pkg.py` on it | the package, L <= 20 | 1e-12 |
| c5 | `eps5/prod5.py --Lmax 12`, every scheme | `results/c5_L20.npz` | 1e-12 |
| c5_vs_pkg | `eps5/validate5.py` on it | the package (L <= 12), the brute force (`results/brute`) | 1e-12 |
| delta5, legw | `eps5/delta5.py --Lmax 20`, `eps5/legw3d.py --Lmax 40` | `results/dC5_L200.npz`, `results/eps5/legw_L400.npz` | 1e-11 |
| brute_W5 | `eps5/brute3d_W5.py --L 4` (package operators, explicit windows) | `results/brute/brute_L4.json` | 1e-12 |
| brute_zm | `brute_zm.py --cutoffs 0 2 4` (package reference solver) | `results/brute_zm_L6.json` | 1e-12 |

Measured on the symmetry cluster (2026-10-14; Python 3.12.9), 11/11 stages passed in each run:

| Job | Node | Stack | `make test` |
|---|---|---|---|
| 575156 | Intel Xeon Gold 6148 | numpy 2.5.3, scipy 1.17.0, numba 0.68.0 | 74 s |
| 575157 | AMD EPYC 7532 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 83 s |
| 575158 | AMD EPYC 7532 | numpy 2.5.3, scipy 1.17.0, numba 0.68.0 | 67 s |
| 575159 | Intel Xeon Gold 6148 (8 of 40 cores, shared node) | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 197 s |

##### 3. `make -f public.mk replay` (about 3 s, numpy only)

`public/replay_exact3d.py` copies the package to `.work/replay/pkg`, reruns `fits_c4.py`, `eps5/fits5.py`, `eps5/t3.py`
on the shipped results, recomputes every quoted number with the rule in `results_map.md`, and repeats the validation
against the package. 14/14 passed on the four nodes above and on a personal desktop (numpy 1.24).

Platform note: `fits/fit_summary.txt` is reproduced byte for byte on the platform that wrote it (a personal desktop).
On the cluster, nine lines differ in their last digits: ill-conditioned subleading coefficients of the window-shift
fits, the C2 fit at the 1e-16 level, and the C3 fit with Lmin = 300, which moves by about 1e-9. None of these changes a
quoted number beyond its stated uncertainty. The C3 central value moves by at most 3e-10 against its uncertainty of
2e-8, and on some platforms its ninth decimal rounds to -0.353581480. The replay therefore checks the quoted lines with
stated tolerances (FITS-QUOTED) and the C3 central value to 1/10 of its uncertainty.

##### 4. Production rerun

All on the symmetry cluster. Times are for one node or for an 8-core share of one; the jobs are listed in
`PROVENANCE.md`.

```
python3 c4_run3d.py --Lmax 600 --workers 20 --threads 2 --cache <node-local> --out results/c4_L600.npz      # 33 min, one node
python3 windows3d.py --Lmax 8000 --out results/windows_L8000.npz; python3 offdiag3d.py --Lmax 8000 --out results/offdiag_L8000.npz
python3 dchi3d.py --Lmax 1000 --out results/dchi_L1000.npz
python3 fits_c4.py                                                                                          # seconds; writes fits/fit_summary.txt
cd eps5
python3 prod5.py --Lmax 20 --workers 8 --cache <node-local> --out ../results/c5_L20.npz                     # every scheme; ~10 min x 4 shards (--shard)
python3 prod5.py --Lmax 40 --raw_only --workers 20 --cache <node-local> --out ../results/c5raw_all_L40.npz  # 1 h 45 min, one 80-thread node, ~6 GB per worker
python3 delta5.py --Lmax 600 --workers 8 --cache <node-local> --out ../results/dC5_L600.npz                 # 3 h, 8 cores
python3 legw3d.py --Lmax 400 --out ../results/eps5/legw_L400.npz
python3 fits5.py; python3 t3.py                                                                             # seconds
```

Memory grows like L^4.5 in the 7-line parallel merges of `prod5.py` (about 6.3 GB per worker at L = 40, 18 GB at
L = 56), and the cost grows like L^8.4. Going beyond L = 40 needs a new angular-channel representation (README Sec. 7.5).

##### Decisions you must not make

- The windows: the complete window W for C4 and Wc for C5, as defined in the d = 2 package and applied unchanged.
  The chi window stays in its leading-order linear form.
- The extrapolation rules: tower T4 and the 12 fit windows for C4 (value = median, uncertainty = half-range including
  the blind fit); the mean and half-range of the three windows for C3; for C5, towers A and D with the calibration on
  C4^W (provisional; Table 2 of the paper marks it so in its caption). PDG rounding.
- The continuum values the deviations are measured against are those of the paper's Table 1 (`tab:pt`).

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### Reproducing the d = 3 perturbative HT numbers (lri_3d_hpc)

Run everything from `HT_Pert/code/lri_3d_hpc` with relative paths. Order: environment, `test`, `replay`, the small
validation run, production.

##### 1. Environment

- `replay`: Python >= 3.9, standard library only, any OS.
- `test`, `smoke` and production: Linux x86-64 (the arithmetic is x87 80-bit long double; other long-double formats
  are refused), a C++17 compiler with OpenMP (`CXX`, default `c++`), Python 3.12 with `public/requirements.txt`
  (numpy, scipy, numba, threadpoolctl). The production stack was CPython 3.12.9, numpy 2.5.3, scipy 1.17.0,
  numba 0.68.0, llvmlite 0.50.0, g++ 13.3.0; `cluster/requirements.lock` pins it with hashes.
- The compiled kernel library and the numba cache are built in node-local temporary storage (`TMPDIR`), as in
  production. On a parallel file system the library's atomic publish can fail (BeeGFS: `EBUSY`); do not point
  `HT3D_NATIVE_CACHE` there.

##### 2. `make -f public.mk test` (about 2 min, 1 GB, 4 threads)

`public/run_tests.py`: the package's own checks as the production validation receipt ran them, without the
site-specific stages:

1. every file against `RELEASE_MANIFEST.json`, the files in `public/SCRUBBED.txt` excepted;
2. `tests/check_*.py`: native kernels, stationary against recurrence energy series, optimized against reference solver
   (cutoffs 0, 2, 4, orders 2..8), banded local products, vertex store, the stage driver on the L4 fixture;
3. the shipped L4 fixture solved in both schemes against the original code at 1e-16;
4. an L = 14 vertex store built from scratch and solved at every even cutoff 0..14, both schemes, both strategies
   (32 cases), against the original code's results within 5e-13 and with every recursion residual <= 1e-16.
   This reruns the L = 14 check that the HT_Pert note quotes for d = 3 (about 1e-14).

`MPIEXEC=<launcher taking -n N> make -f public.mk test` adds the 2- and 4-rank MPI tests (mpi4py built against the
site MPI; not part of the default target).

Measured on the symmetry cluster (2026-10-14, the simulated export of this folder, 12/12 stages passed in each):

| Job | Node | Stack | `make test` | L14 grid vs original code | recursion residual |
|---|---|---|---|---|---|
| 574907 | Intel Xeon Gold 6148 | production (numpy 2.5.3, scipy 1.17.0, numba 0.68.0) | 106 s | 6.6e-17 | 6.9e-18 |
| 574908 | Intel Xeon Gold 6148 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 127 s | 6.6e-17 | 6.9e-18 |
| 574909 | AMD EPYC 7532 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 112 s | 1.16e-14 | 1.4e-17 |
| 574910 | AMD EPYC 7532 | production | 92 s | 1.16e-14 | 1.4e-17 |

All used Python 3.12.9 and g++ 11.4, with peak memory about 1 GB. The difference between Intel and AMD, about 1e-14,
comes from the float64 SO(3) projector (BLAS, libm). It is the same as in production: the Expanse stores differ from
the reference by up to 1.25e-14.

##### 3. `make -f public.mk replay` (about 1 s)

`public/replay_pert3d.py` recomputes every quoted number from the shipped records (`results_map.md`): the integrity of
the records and of the chain code -> store -> gate -> solve -> result, the table `HT_Pert/results/HT_3d/SUMMARY.md`,
the ratios C_n(20)/C_n (n = 2..8), the 60.26 % C4 ratio read by `HT/`, the L = 14 gates (recomputed from the gate
records and the reference file), the L = 16 recurrence crosscheck and the cross-store check. It prints a PASS/FAIL
table (17 rows), writes it and `ratios_L20.csv` to `.work/replay/`, and exits 1 on any FAIL. 17/17 passed on all four
nodes above.

##### 4. Small validation run (`make -f public.mk smoke`, seconds)

The shipped L4 fixture, consistent scheme, against the original code at 1e-16. Before using cluster time, also build
and solve one small cutoff by hand:

```
python3 code/ht3d_coefficients.py build --cutoff 12 --order 8 --store .work/stores/L12 --spill .work/spill
python3 code/ht3d_coefficients.py solve --store .work/stores/L12 --cutoff 12 --order 8 --scheme consistent \
  --threads 4 --output .work/C8_L12.json --compare-reference results/reference_coefficients_L14.json
```

##### 5. Production rerun (L = 16, 18, 20)

The production ran through the package's two-site layer, `cluster/` (`cluster/RUNBOOK.md`), on SDSC Expanse. That
layer has staged and authenticated releases, a validation receipt per node class, campaigns frozen to a release and an
environment, a restartable stage runner (prepare, images, matrix, finalize, verify, gate, solve, crosscheck) and a
submit wrapper. The same layer was validated on the symmetry cluster. For other sites, `hpc/` has the supplier's
generic Slurm examples (not used in production), and `public/slurm/test.slurm` runs `make test` on one node.

Measured cost of the production campaign (Expanse AMD EPYC 7742; per stage, from `HT_Pert/data/HT_3d/pert3d/records`):

| L | scalar bath states | store | prepare (projector) | images (sum) | matrix (sum; peak) | solve per scheme | job, request | charge |
|---|---|---|---|---|---|---|---|---|
| 16 | 15,815 | 2.6 GiB | 6.4 min, 1.5 GiB | 36 min, 0.8 GiB | 12 min; 3.4 GiB | 16 s, 3.9 GiB | 18.5 min on 16 cores, 32 GB | about 10 SU |
| 18 | 55,859 | 22 GiB | 13.5 min, 7.3 GiB | 28 min, 4.7 GiB | 69 min; 26 GiB | 73 s, 31 GiB | 36 min on 64 cores, 200 GB | about 60 SU |
| 20 | 196,585 | 177 GiB | 10.0 h, 39 GiB | 42 min, 32 GiB | 15.2 h; 209 GiB | 546 s, 244 GiB | 10.2 h on 64 cores, 200 GB, then 3.4 h on 64 cores, 1700 GB (large-shared) | about 2480 SU |

In total, about 2550 SU. The L = 20 projector is the bottleneck: 9.9 h with 77 gesdd -> gesvd fallbacks, all
repaired. L = 22 is not feasible this way: it needs about 18 times the SVD work and about 1.5 TB per k = 4 matrix task.
Ask before spending more than this.

##### Decisions you must not make

- The quoted scheme is `consistent`, the vacuum window D_L(l) = E_v(L) - E_v(L - l). Order 8, x87 long double, nz = 10
  local states per parity. `raw` is shipped for comparison only.
- Acceptance: gates against `results/reference_coefficients_L14.json` at 5e-13 (scaled error over C, r, g, all seed
  energies and subcutoff vacua); recursion residual <= 1e-16; crosscheck <= 1e-15. These are the production
  tolerances.
- The denominators of the ratios are the paper's Table 1 values (`tab:pt`; `GFF/note/README.md`): C2..C5 exact, C6..C8 the
  reported estimators. The ratios are rounded to 3 decimals.
- No extrapolation from this package: three cutoffs and no complete window. The paper's extrapolated d = 3 values come
  from `../lri_3d_c4_exact`. Do not add one here.
