# Reproducing the HT results

How to rerun each package: environment, `make -f public.mk test` / `replay`, and the documented production reruns. `make test` and `make replay` in this folder run every package (see `Makefile`).

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### Reproduce: d = 1 finite-coupling HT (lri_dressed_phi4_hpc, lri_dressed_phi4_hpc_analysis)

##### 1. Environment
- **Python:** 3.11, with numpy 2.3.5, scipy 1.17.0, numba 0.65.1 and pytest. These are the production versions
  (`requirements-tested.txt`, and the `runtime` field of every record).
- **Install:** `python -m pip install -e .` inside `code/lri_dressed_phi4_hpc`, or use `PYTHONPATH=src` as
  `public.mk` does.
- **Analysis:** `code/lri_dressed_phi4_hpc_analysis` needs only numpy and scipy.
- **Thread variables:** keep `OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=OMP_NUM_THREADS=1`. Numba threads are set per
  run.

##### 2. Test (minutes, one node)

```
make -C code/lri_dressed_phi4_hpc -f public.mk test           # validate_release.py, 6 stages, ~2-3 min
make -C code/lri_dressed_phi4_hpc_analysis -f public.mk test  # seconds
make -C code/lri_dressed_phi4_independent_check -f public.mk test
```

##### 3. Replay of every quoted number (no production rerun)

```
make -C code/lri_dressed_phi4_hpc_analysis -f public.mk replay      # 81 checks, ~1 min
make -C code/lri_dressed_phi4_hpc -f public.mk replay               # code <-> record binding, validator on 881 records
make -C code/lri_dressed_phi4_independent_check -f public.mk replay # blind-solver agreement, C2(N)
```

Each prints a PASS/FAIL table, writes it to `.work/`, and exits non-zero on any FAIL. Tolerances and estimators are
in `results/HT_1d/quoted_numbers.json`, `results_map.md`, and the docstring of `public/replay_ht1d.py`.

##### 4. Small validation run (before using cluster time)

```
make -C code/lri_dressed_phi4_hpc -f public.mk smoke   # one production item, N = 12, Ds = 0.2
# 10 s on the production runtime. On any other runtime it first retrains the Ds = 0.2 basis (about 3.5 min):
# basis artifacts are bound to the runtime that trained them.
```

##### 5. Production rerun (documented; not run in CI)

The production is campaign `dens_v1`, run on symmetry on 2026-10-07..09. Its manifests are
`data/HT_1d/dens_v1/campaigns/<campaign>/manifest.json`. Each item gives its exact command through
`lri_dressed.pack.command` (cutoff, nz = 16 or 24, osc 384, ladder backend, window vacuum/consistent, tolerances,
basis artifact and sha256, seed folder).

1. **Basis training.** The 13 trained artifacts ship in `data/HT_1d/dens_v1/bases/dens_v1/`, but they load only on
   the production runtime (Python 3.11.4, numpy 2.3.5, scipy 1.17.0, numba 0.65.1). On any other runtime, retrain
   them first:

   ```
   python -m lri_dressed train-basis --bath-cut 24 --delta <Ds> --teacher-nz 48 --keep 24 --osc 384 --backend ladder --threads 8 --output <artifact>
   ```

   This took about 10–20 min per Ds on one AMD node. `scripts/make_basis_training.py` and
   `cluster/symmetry/train_basis.sbatch` are the campaign versions. Index the artifacts with
   `scripts/index_bases.py`.
2. **Manifests.** Build them with `data/HT_1d/dens_v1/campaigns/make_dens_v1.sh`, after replacing its site paths
   (`$LRI_ROOT`, the install directory) by yours. It calls `scripts/make_campaign.py --pack` with the 13 Ds, even
   cutoffs 12–40, and the thread, memory and time classes below. The seeds are
   `data/HT_1d/dens_v1/seeds/dens_v1_all`.
3. **Runs.** `cluster/symmetry/pack.sbatch` starts `scripts/pack_node.py` on whole nodes. Each node runs several
   items at once, and several nodes share one manifest through leases. Put your own partition, account, paths and
   memory into a copy of `pack.sbatch`, using the `<PARTITION>`, `<ACCOUNT>` and `<SCRATCH>` placeholders. The
   symmetry values were `--mem=245G` with `--exclusive` on 64-core AMD nodes, or `--mem=180G --cores 40` on 40-core
   Intel nodes. Items resume from Newton checkpoints after a walltime stop or a requeue.

| Campaign | Items | Threads / mem per item | Wall per item (record `seconds`, last process) |
|---|---|---|---|
| dens16_lo (N = 12–28) | 117 | 1 / 4 GiB | 1 s to 0.3 h (N = 28, Ds = 0.01) |
| dens16_mid (N = 30, 32) | 26 | 4 / 6 GiB | 45 s to 1.2 h |
| dens16_hi8 (N = 34, 36) | 26 | 8 / 8 GiB | 3 min to 6.3 h |
| dens16_hi16 (N = 38, 40) | 26 | 16 / 12 GiB | 5 min to 14.8 h; N = 40 at Ds = 0.01, 0.001 needed one continuation after a walltime stop |
| dens24_ctl (nz 24, N = 36, 40) | 8 | 16 / 12 GiB | 3.1 to 22.5 h; the two N = 40 items at Ds = 0.025, 0.01 did not finish (not quoted) |

The whole campaign took about 10^4 core-hours of exclusive nodes, including idle cores while the long N = 38–40 items
ran. The first campaign prod1–7 (code 4dfd833; only its records are used) took about 1.06×10^4 core-hours.

4. **Rows and analysis.** Run the replay. It rebuilds `dens_v1_rows.json` from your results with the field map of
   `campaigns/dump_dens_v1.py`, then reruns `dens_v1.py` and `dens_v1_holdout.py`.

##### Decisions you must not make

- The fit family (F1, F2, F3 × N_min = 12, 14, …, 24) and the acceptance rule are part of the result. Acceptance is
  rms < 3e-6, 0.2 < omega < 4, and |D_inf − Delta(N_max)| < 0.05. The stability rule is >= 5 accepted fits, median
  omega >= 0.45 and half-spread <= 2e-3.
- The quoted error is half the spread of the accepted fits: a model spread, not a confidence interval.
- The status labels (final, one-sided, unstable, no limit) and their rules are in `quoted_numbers.json`. Keep them.
- The window prescription (consistent, full vacuum, zero mode included) defines the model. A different prescription
  is a different model, not a check.

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

#### Reproduce: lri_dressed_phi4_hpc_analysis
Shared with the solver: ../lri_dressed_phi4_hpc/REPRODUCE_lri_dressed_phi4_hpc.md (sections 3 and 5.4). In short: `make -f public.mk test` (seconds), then `make -f public.mk replay` (about 1 min); a production rerun of dens_v1 produces new records from which the same replay rebuilds the rows and every quoted number.

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

#### Reproduce: lri_dressed_phi4_independent_check
1. Environment: Python >= 3.10, numpy, scipy (requirements). 2. `make -f public.mk test` (64 checks), 3. `make -f public.mk replay`, 4. `make -f public.mk smoke`. Production rerun: `python make_tasks.py` writes tasks/; each task runs `python indep_ht.py --task tasks/<t>.json --out results/raw_runs/<t>.json --log <log>` (one core each; the slurm/ scripts ran the 38 tasks packed on one node, about 2.5 h for the longest, N = 20 consistent at Ds = 0.01); then `python analyze.py results/raw_runs` rebuilds results/indep_results.json. Task files carry the cluster path of the run's results folder in "guess_from"; replace it by yours.

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### Reproduce: lri_2d_window_hpc (d = 2 finite coupling)

Run from `HT/code/lri_2d_window_hpc` on a Linux cluster node.

##### 1. Environment
Python 3.11 (production: 3.11.5) with the pins of `cluster/expanse/requirements-expanse.txt`: numpy 2.3.5,
scipy 1.17.0, numba 0.65.1, llvmlite 0.47.0, threadpoolctl 3.6.0, pytest 9.0.2. No compiler, MPI or GPU.
`public/requirements.txt` is the same list. Keep BLAS at one thread; Numba threads via `THREADS=` (default 4).

##### 2. Test (≈ 5 min, 4 cores)
`make -f public.mk test`: checks `MANIFEST.sha256` (it predates the Expanse-layer changes to `code/ht2d/hpc.py` and
`solver.py`, which are checked against `public/MANIFEST_889a968_changes.txt`; files changed by the public placeholder
scrub are listed in `public/SCRUBBED.txt` and reported), then runs the package's suite (tests/test_port.py, test_optimized.py, test_hpc.py,
test_expanse.py: original 16 numerical cases against the reference port and the earlier implementation, operators,
ranking, restart, manifests and the Expanse campaign layer) on a scratch copy, because test_port rewrites
`validation/independent_metrics.json`. Expected: 110 passed (symmetry, Intel Xeon Gold 6148: 4 min).

##### 3. Smoke (≈ 2 min)
`make -f public.mk smoke`:
- reruns the prod1 point Δσ = 0.25, N = 8, nz = 16 from the shipped teacher and seed and compares with
  `HT/data/HT_2d/prod1/chains/x0.250/L8_z16.json`: Δ_E and gaps to 1e-10, couplings θ to 1e-8;
- runs `public/scan_valley.py` at N = 8, Δσ = 0.126 from θ1 moved by 0.002: the secant on f2 = 0 must return to the
  production root (θ1 to 1e-8, f1 to 1e-9).

##### 4. Replay (≈ 1 min, no solver)
`make -f public.mk replay` runs `public/replay_d2.py` and prints a PASS/FAIL table (names as in `results_map.md`):
record integrity (self-hash, gates, source hash = this code), points.csv = records, nz convergence, every finite-N
statement of the HT note, the 13 largest-N values of Fig. fig:cmp2d3d and their five-decimal cells in Table tab:num2,
the valley scan (no root, minima, fold), and the weak-coupling check against the consistent-scheme ε series: 31 checks.
Exit status 1 on any FAIL.

##### 5. Production rerun (documented; not a make target)
Cost of the shipped records: ≈ 10.8k core-hours (Expanse, 64 cores per chain; N = 24 points take 0.6–11 h, up to
24 GiB). The two stalled N = 24 attempts at Δσ = 0.125, 0.126 and their restarts cost several thousand more; do not
repeat them (there is no root, Sec. 6). Ask before spending more than the stated cost.

Option A, as in production (Expanse-style Slurm layer): see `cluster/expanse/README.md`. Build a release tarball
(`cluster/expanse/make_release.sh`), install the frozen env (`install_env.sh`), validate (`validate.sbatch`), freeze a
campaign from a request (the prod1 request is reproduced by `HT/data/HT_2d/prod1/spec.json`: 13 chains + 3 references,
ladder 8…24, nz 16 main with nz 20/12 checks, `eig_tol 1e-12, residual_tol 1e-8, tuning_tol 3e-11, ncv 40, maxiter 50,
backend tensor`), submit, then `collect.py`. Account, partition and paths are placeholders in the shipped drivers; put
your own values there.

Option B, point by point: for each chain, run `code/hpc_run.py` at N = 8, 10, …, 24 with the settings recorded in each
record's `configuration` (basis = the chain's input in `HT/data/HT_2d/prod1/inputs/<chain>/`; seed = the previous N's
record, or the chain's initial seed at N = 8), e.g.
`python code/hpc_run.py --L 10 --x 0.25 --nz 16 --backend tensor --window vacuum --window-mode consistent
 --basis <basis> --seed <L8 record> --diagnostics all --threads 64 --memory-limit-gib 56 --output L10_z16.json`.
A rerun agrees with the records to about 1e-12 on the same CPU family (replays on Expanse: ≤ 1.1e-12).

##### 6. The valley scan (N = 24, Δσ = 0.125, 0.126; ≈ 3.0k core-hours)
`git apply public/afe69ab.diff` is not needed for the scan (it calls only `DensitySolver.spectrum`, unchanged), but it
reproduces the exact release used. For each (Δσ, θ0) in the shipped outputs:
`python -E -s public/scan_valley.py code <basis> <Δσ> 24 64 out.json <θ0> <θ1 guess>` (64 cores, ≈ 60 GB, 3–5 h;
guesses in `public/valley_expanse/gen.py`). Bases: `inputs/x0.125/L6_z24.json`, `inputs/x0.126/teacher_L6_x0.126.json`.

##### Decisions you must not make
- Do not extrapolate the d = 2 sequences to N → ∞ or quote a continuum Δ_E: the paper reports finite-N behaviour only.
- Do not rerun N = 24 at Δσ = 0.125, 0.126 expecting a root; the valley scan shows f1 > 0 on f2 = 0.
- Keep the gates (tuning residual ≤ max(1e-10, 5 tuning_tol), eigenvector residual ≤ residual_tol, window fixed point
  ≤ 1e-11) and the replay tolerances as shipped.

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

#### Reproduce: lri_2d_window_indep

Run from `HT/code/lri_2d_window_indep`. Python 3.11 with numpy and scipy (runs: Python 3.11.4, numpy 2.3.5,
scipy 1.17.0; `public/requirements.txt`). BLAS at one thread.

1. `make -f public.mk test` (≈ 1 min): `test_indep.py`; prints `ALL PASS`.
2. `make -f public.mk smoke` (≈ 1 min): reruns two shipped comparisons (Δσ = 0.25 and 0.125, N = 8, K = 24, with the
   J = 1, 2 spectra) against the shipped records; checks the levels against the shipped outputs (1e-10) and Δ_E
   against the production record (1e-11).
3. `make -f public.mk replay` (seconds): `public/replay_indep.py`, PASS/FAIL table (names i2.* as in results_map.md):
   output count, binding of every embedded production value to the shipped record, Δ_E agreement at N = 12/16 (K ≥ 32),
   18, 20, 22, all levels and the vacuum-energy table, and re-tuning from shifted seeds.
4. Full rerun (documented): `python run_check.py ../../data/HT_2d/prod1/chains OUT 56` (143 tasks; symmetry AMD node,
   64 cores, 240 GB requested; 1 h 06 min), then `python run_check.py ../../data/HT_2d/prod1/chains OUT 12 --followup`
   (12 tasks, K = 32/40 at N = 18–22; the N = 22 tasks take ≈ 11 h each, ≈ 5 GB). `summarize.py OUT` prints the
   tables. The shipped drivers are the two `.sbatch` files (paths are placeholders).

The first job ran an earlier `run_check.py` (sha256 9b882311…); the shipped one (8b877b6f…, the follow-up's) adds only
the `--followup` task list and a memory field: `public/run_check_9b882311_to_8b877b6f.diff`.

##### Decisions you must not make
- Do not compare at K = 24 for Δσ ≤ 0.15 beyond N = 12 and call a difference a production error: K = 24 is not converged
  there (the replay prints these values as a NOTE).
- Tolerances of the replay are as shipped.

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### Reproducing the d = 3 finite-coupling HT results

Three levels, from cheapest to complete. Commands run from `HT/code/lri_3d_window_hpc` unless stated.

##### 1. Replay (seconds, any OS)

```
make -f public.mk replay                     # or, from HT/:  make replay
```

`public/replay_ht3d.py` checks the integrity of the 105 shipped records and recomputes every quoted d = 3 number:

- records: sha256 against `data/HT_3d/MANIFEST.sha256`, each record's self-hash, the seed and basis hash chain, and the
  numerical source hash against the shipped `code/`;
- the finite-N table, rebuilt and compared byte for byte with `results/HT_3d/finite_L_table.csv`;
- the rows of `results_map.md`.

It prints a PASS/FAIL table, writes it to `.work/replay/`, and exits 1 on any FAIL. The C4-RATIO row reads C₄(L = 20)
from HT_Pert's record (`HT_Pert/results/HT_3d/SUMMARY.md`, or `PERT_SUMMARY=<path>`), and is SKIP if that file is
absent.

The independent-solver check has its own replay: `make -C ../lri_3d_window_indep -f public.mk replay`.

##### 2. Test and smoke (minutes, one node)

```
make -f public.mk test     # MANIFEST.sha256, pytest (158 tests), five validators; 3.5-4.3 min
make -f public.mk smoke    # re-solve N = 8, 10 at Ds = 0.7 and 0.518149 from the shipped teacher/seed records; ~25 s
```

- **test** runs the stages of the Expanse validation receipt (`cluster/expanse/receipt.py`), without its release
  stage, which needs the release tarball. Receipt 54779486 (Expanse, AMD EPYC 7742, 2026-10-09) passed these stages
  on the same code. The public tree passed `make test` on symmetry on 2026-10-13: AMD EPYC 8534P in 3.5 min (job
  574386) and Intel Xeon Gold 6148 in 4.3 min (job 574390), with Python 3.12.9 and the pinned versions.
- **smoke** runs the point driver with the configuration stored in each record and the same continuation inputs. The
  new ΔE, r and g must match the record to 1e-9. On Expanse the production nodes were reproducible bitwise: repeated
  N ≤ 16 ladders agreed 24/24 bitwise. On another CPU or BLAS, expect agreement to about 1e-12: on symmetry, with
  Python 3.12.9, the four points matched the Expanse records to at most 1.5e-12 on Intel Xeon Gold 6148 (2026-10-13,
  job 574437) and on AMD EPYC 8534P (2026-10-14, job 574420), with the same differences on both.

Template: `public/slurm/test_smoke.slurm`.

##### 3. Production rerun (cluster)

The production is a set of frozen campaigns. Each campaign's `manifest.json` in `data/HT_3d/campaigns/<name>/` holds
the exact argv of every step. The only paths in them are the production paths of the continuation inputs and the
static cache; map them to your own.

###### Ladders N = 6 … 18 (campaigns grid18, grid18sri)

Each lane is one Ds, run in the order teacher → window_L8 → … → window_L18:

1. **teacher_L6**: a moving-local solve at N = 6 with n_z = 24 local states and a 192-level oscillator. It trains the
   20-state density basis (`--train-keep 20`). Diagnostics: first.
   - At Ds = 0.518149 the teacher starts from `--guess -0.3087960012193629 -1.9510919330003222`, the N = 6 couplings of
     Ds = 0.5182 in `inputs/prior_3d_points.json`.
2. **window_L8 … window_L18**: the density basis with n_z = 16, vacuum window, consistent mode, tensor backend.
   - Each step is seeded from the previous record (`--seed`) and uses the teacher's basis (`--basis`).
   - Diagnostics: `all` (J = 1, 2) at N ≤ 16, `first` (J = 1) at N = 18.
   - Bath-state limits: 10,000,000 at N = 16 and 50,000,000 at N = 18.
   - Memory guard: 58 GiB.
3. **Side steps** after N = 10: `window_L10_k12` (n_z = 12) and `raw_L10` (no window, n_z = 20, oscillator 160).
   `raw_L10` is shipped because the independent check compares against it.

Production resources were 16 cores and 64 GB per lane on Expanse `shared`. An N = 18 step took 34–74 min at
38.5 GiB peak RSS. The two arrays charged 587.7 SU (Slurm accounting).

###### N = 20 (campaigns l20x06, grid20, grid20sri)

Each N = 20 point continues its Ds lane: `--seed` is the N = 18 record and `--basis` is the teacher.
- Bath-state limit: 200,000,000.
- Scalar only (`--diagnostics none`) for 14 points.
- `first` (J = 1) for Ds = 0.6 (l20x06).

**Static cache first.** At N = 20 the bath graph (about 18 GB) and the scalar SO(3) projector take about 9 h of
single-threaded LAPACK. They do not depend on Ds and were built once into an immutable cache, `--cache-dir`:

```
HT3D_SETUP_ARGS="--L 20 --x 0.6 --spins 0 --execute --stop-after vertices --max-bath-states 200000000 \
  --memory-limit-gib 180 --cache-dir <SCRATCH>/ht3d/static_cache/<tag>" sbatch -c 4 --mem=192G cluster/expanse/setup_probe.sbatch
```

- A spin-0 build without a cache (job 54748336) took 9.0 h at 92 GiB peak on an Expanse large-shared node.
- The production cache job (54762506) also asked for spin 1. It built the graph, the spin-0 projector, the spin-0
  vertices at Ds = 0.6 and the spin-1 projector, then ran out of memory (224 GB) on the spin-1 vertices. Spin 1 is
  needed only for J = 1 diagnostics.
- The SVD fallback of the 0.2.1rc1 repair fired 62 times at N = 20 (gesdd → gesvd), every time with the exact
  nullity and residual ≤ 1e-14. See `FIX_L18_L20.md`.

**Points.** The vertices depend on Ds (cache key `x_hex`), so every point builds its own spin-0 vertices. That took
19 min at 97 GiB peak with 4 threads in the cache job, and it sets the peak memory of a scalar-only point.
- Scalar-only points took 27–104 min at 84–87 GiB peak RSS. They ran on Expanse `shared` with 32 cores and 240 GB,
  and charged 1757 SU.
- The driver's memory guard estimates 258 GiB at N = 20. That estimate is a planning heuristic, so these points used
  the campaign opt-in `guard_cap_gib` = 270 with a written reason (commit b330ee7).
- The Ds = 0.6 point with J = 1 diagnostics took 239 min at 328 GiB. It ran on large-shared with 1000 GB and charged
  997 SU.

**Expanse route.** `EXPANSE.md` and `cluster/expanse/README.md`: install a release tarball (`cluster/expanse/make_release.py` on a
git checkout of this folder), pass the receipt (`validate.sbatch`), freeze the campaign from a spec
(`campaign.py freeze`), then `campaign.py submit`.

**Any other Slurm cluster.** Run `code/hpc_run.py` per step with the argv from the manifests: the replacement paths
for `--basis`, `--seed`, `--cache-dir` and a new `--output`. Each record is accepted only if it passes the
driver's own gates (`ht3d.hpc.validate_record`: tuning residual, eigenpair residuals, window fixed point). A rerun
must reproduce the shipped ΔE to within the tuning tolerance (3e-11), up to BLAS-level differences.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

#### Reproducing the d = 3 independent-solver check

From `HT/code/lri_3d_window_indep`:

1. **Replay (seconds).** `make -f public.mk replay` recomputes from the 23 shipped comparison records:
   - INDEP-TUNED: max |ΔE(indep, tuned) − ΔE(production)| = 1.89e-11, quoted as 2e-11;
   - INDEP-FIXED: ≤ 1.7e-12 at the production couplings, K = 16;
   - INDEP-RESID: every independent tuning converged to ≤ 1e-12;
   - INDEP-PKG: the production values each comparison used equal the shipped production records in
     `HT/data/HT_3d/campaigns` and `indep_extract.json`. The raw-scheme comparisons use the `raw_L10` side-step
     records, which are shipped for this reason.
2. **Test (about 10 s; passed on symmetry, AMD and Intel, 2026-10-13).** `make -f public.mk test`:
   - the Gegenbauer identity behind the mode weights;
   - the J = 0 state counts 3, 10, 33, 110 at N = 2, 4, 6, 8, equal to those of the perturbative package;
   - rotation invariance of the vertices;
   - the free spectrum;
   - one production point at fixed couplings (N = 8, Ds = 0.7) to 1e-10.
3. **Rerun.** Each comparison is one `run_compare.py` call; `tasks.txt` lists the Expanse array (N, scheme, Ds).
   - The first runs of three L12 tunings (Ds = 0.7499, 0.55, 0.518149) started 8% + 0.01 away from the production
     couplings and failed with NaN in the local diagonalisation.
   - They were rerun with the 2% multiplicative start that `run_compare.py` now uses, in jobs 54771132, 54771237
     and 54772616.
   - Wall time per comparison, from the records' `seconds` (Expanse `shared`, 4–8 cores, 16–24 GB requested):
     - N = 8 window: 0.7–3.3 min;
     - N = 10: 0.5–0.8 min raw, 2.4–3.4 min window;
     - N = 12 window: 6–8 min setup, 9 min to 3.1 h in all.
