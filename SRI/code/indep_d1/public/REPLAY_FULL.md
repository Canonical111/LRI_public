# indep_d1: production rerun and raw data

Printed by `make -f public.mk replay-full` and `make -f public.mk fetch-data`. Paths are relative to `code/indep_d1/`.

## Production rerun

The quoted numbers rest on engine runs of about 22,300 allocated core-hours (2026-10-03 to 2026-10-07), almost all on
the symmetry cluster's `amdq` partition (whole 64-core AMD EPYC nodes); about 700 core-hours of cheap groups, checks and
tier A ran on a 16-core personal desktop (the tier-B/C runs on the personal desktop carry the directory suffix `_can`).
A rerun reproduces them from the shipped job definitions: every
`engine/runs/<run>/*.cfg` fixes the moment, eps power, sector range, lattice size N, Korobov generator, seed, shift
count and channels of one chunk, and `manifest.json` lists the chunks of each job.

| run | role | jobs / chunks | engine cpu core-h |
|---|---|---|---|
| `prod_6digit` | phase 2: the 116 order-D4 raw scalars (C5..C7) | 75 / 86 | 2,169 |
| `prod_6digit_topup1` | phase 2 top-up: Q6_E, A7_v, A7_base, A5_vE at higher N | 4 / 7 | 371 |
| `poles1` | phase 2 check only: negative eps powers for the pole-cancellation test | 45 / 45 | 64 |
| `c8tierA`, `c8tierA_topup1` | phase 3 (C8 tier A: W, S, L3, M21, M12, N2, Ndelta) | 22 / 22 | 153 |
| `c8tierB_s0.01_r1`, `c8tierB_s0.01_can`, `c8tierB_s0.01_topup1` | phase 4 tier B (U, Kv): Q8_v, Q6_vE, A7_d (heavy) and 16 cheaper groups | 25 / 60 | 7,983 |
| `c8tierC_s3_r2`, `c8tierC_s3_can`, `c8tierC_s3_topup1` | phase 4 tier C (J9): A9 (44 chunks at N = 8009), A7_E (9 chunks), Z8 and 11 cheaper groups | 22 / 73 | 10,107 |

Allocated totals (sacct, including planning, strict re-checks, probes and the C9 pole checks): phase 2 2,942.9 + 99.8
(`engine/PRODUCTION_TIER1.md`, `assembly/README.md`), tier A 183.1 on the personal desktop (`engine/PRODUCTION_C8.md`
sections 1-3), tiers B and C 19,126.8 amdq-equivalent (`engine/PRODUCTION_C8.md` section 13j; the engine's ledger is
not exported), assembly check run 10.6.

Steps (symmetry, `amdq`; the original phase-2 driver `engine/slurm/submit_production.sh` contains the project's own
paths and is documentation, the tier-B/C drivers are not exported; the generic loop below does the same):

1. Build the engine on a compute node: `bash engine/slurm/build.sh` (g++ 11.4, `-O3 -march=x86-64-v3 -std=c++17
   -fopenmp -ffp-contract=off`). The production binary had md5 `ec238e0fa37b` (source md5 `edfa65dce4d6`).
2. For each run directory above, run its chunks with all physical cores of a node:
   `bash engine/slurm/run_list.sh engine/runs/<run> engine/runs/<run>/cfglist.txt <first> <last>` (one Slurm array
   task per chunk; `engine/slurm/production_symmetry.sbatch` is the template: `--exclusive`, `--mem=240G`, `-p amdq`).
   The heavy chunks take 2-3 h each on a 64-core node (Q8, Q8_v, A9); the C8 tier-C array needs about 10k core-hours.
   `c8tierC_s3_r2/manifest.json` lists the chunks used (A7_E chunks 1-8 at N = 16001, files `*_N16001.cfg`); the eight
   `A7_E_k0_c00[1-8].cfg` at N = 22637 were planned and not run.
3. Collect and merge (from `engine/`): `python3 py/campaign.py collect runs/<run> [--need specs/production_C8_need.json]`
   for every run; `python3 py/merge_runs.py runs/prod_6digit runs/prod_6digit_topup1 --tag final`, the same for
   `c8tierA` (+ `c8tierA_topup1`), `c8tierB_s0.01_r1` (+ `_can`, `_topup1`) and `c8tierC_s3_r2` (+ `_can`, `_topup1`)
   with `--need specs/production_C8_need.json`; then `python3 tests/merge_tiers_C8.py` writes
   `runs/c8tiersABC/framework_input_final.json` (`engine/PRODUCTION_C8.md` sections 7, 12e and 13i).
4. Compare the new chunk outputs with `public/RAW_SHA256SUMS.txt` (the engine is deterministic for a given cfg and
   binary: `make test` reruns four chunks and finds them bitwise identical on symmetry) and the merged
   `framework_input_final.json` files with the shipped ones (their `producer` fields hold absolute paths, so compare
   the `scalars`, not the sha256).
5. `make -f public.mk replay-raw RAW=<the rerun tree>` rebuilds `public/pooled_sector_record.json` from the new chunk
   outputs and reruns the whole assembly on them.

The archive-free checks that are not part of `replay` (the pilot and probe runs `c8val`, `c8conv`, `c8kplus1`,
`c8probeBC`, `c8chkBC`, `c8chkBC_N4001`, `c8chkA7`, `kplus1`, `conv1`, the strict re-checks, `validate_C8.py`,
`direct_C8.py`) are described in `RESULTS.md`, `RESULTS_C8.md` and `engine/PRODUCTION_C8.md`; their specs are in
`engine/specs/` and their outputs are kept in the project archive (not exported).

## End of production rerun

## Raw chunk outputs

The per-sector, per-replicate engine outputs `engine/runs/<run>/*.cfg.json` of the eleven runs of the table above
(293 files, 131 MB) are not in the repository. Their sha256 are listed in
`public/RAW_SHA256SUMS.txt`. `replay` does not need them: `public/pooled_sector_record.json` holds their exact
sufficient statistics (per job, the per-replicate totals and the sum over sectors of the replicate covariance), built
by `public/make_pooled_record.py` with the verbatim `assembly/pooled_errors.job_sector_values()`.

Hosting: the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), file `SRI__indep_d1__raw_engine_outputs.tar.gz` (30,749,940 bytes, sha256
`8d98a6a0d5f18a91...`; `public/HOSTED.json`). `make -f public.mk fetch-data` downloads it (or takes `FILE=<archive>`),
checks it, unpacks it into `.work/raw` (files at `.work/raw/engine/runs/<run>/*.cfg.json`) and checks every file
against `public/RAW_SHA256SUMS.txt`; then run `make -f public.mk replay-raw RAW=.work/raw`: it checks the sha256 list, rebuilds the pooled record and compares it with
the shipped one, and reruns every step of `replay` on the raw outputs with the verbatim `pooled_errors.py`.

## End of raw chunk outputs
