# Reproducing the d = 3 finite-coupling HT results

Three levels, from cheapest to complete. Commands run from `HT/code/lri_3d_window_hpc` unless stated.

## 1. Replay (seconds, any OS)

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

## 2. Test and smoke (minutes, one node)

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

## 3. Production rerun (cluster)

The production is a set of frozen campaigns. Each campaign's `manifest.json` in `data/HT_3d/campaigns/<name>/` holds
the exact argv of every step. The only paths in them are the production paths of the continuation inputs and the
static cache; map them to your own.

### Ladders N = 6 … 18 (campaigns grid18, grid18sri)

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

### N = 20 (campaigns l20x06, grid20, grid20sri)

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
