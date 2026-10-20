# Stage-6 fix round 1 on symmetry (2026-10-06): the merged head validated

Site rule: symmetry only (user, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry is not
enough"); Expanse, personal desktops were not touched. Everything ran from the git-archive export of
**c30bfc5f0bdf** (`<SCRATCH>/c8d2/pkg/c30bfc5f0bdf`; `setup/export_check_c30bfc5f0bdf.json`: 8,655 files
equal to the archive in content and mode). c30bfc5 is the merge of the four fix-round-1 groups (G1 5b8caf5, G2 38b47ee,
G3 73501f1, G4 824fa75, merged as 2741bc2, 8494fd2, cd7e5de, 997eb6a) plus the integration fixes and this folder's
`scripts/`; `src/` is e88bf4f's (unchanged since 5d7586e). The two L8 packs were re-hashed against the export's
`inputs/manifest.json` and hard-linked from `pkg/7a8aad783c31/inputs/packs` (`s1build.570371.0/l8_packs.json`). The
Mac side of the integration is `../../mac_2026-10-c8/s6fix1int/`.

## Verdicts

| Item | Job(s) | Verdict |
|---|---|---|
| Build, **A-RPL-8** | 570371 | **PASS.** Every default and diagnostic executable is byte-identical to the Stage-5 symmetry build of 5d7586e (decimal `619ddf7d…`, gmp `2cc5e88e…`, prof, ratiohist, inspect, c7ref `e696d7f3…`/`7e3c8c92…`, quad differential and ranges, interleave probe); the two sanitizer builds equal 5d7586e's once the export path and build-id are normalized (31 and 32 differing bytes). `make gmp NUMERICS=dd,mp256` gives **`d5df32ac…`**, the gated build, and leaves every default executable unchanged; `--describe` and the build record: numerics `dd+mp256`, no override, no stub; Boost 1_77 everywhere. |
| **X3 on real Linux** (thread identity with the observed teams) | 570371 | **PASS.** `tests/thread_identity.py` (both backends, L8 free and power blocks): rows identical at 1, 8, 16, 64 threads and 8 × 8 lanes, and every observed team (`/proc/<pid>/task`) equals the request (1, 8, 16, 64; eight lanes of 8), `team_sizes_verified: true`, 109 s. Again for gmp with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true` inherited: the harness strips them, the same teams are observed (integration 8.9 s at 1 thread, 1.13 s at 8), rows identical, 32 s. The assumption G3 could test only with fakes (the libgomp team = the worker's task count) holds. |
| **J-GEN-1** (A-INV-1/2; X5, X6 on x86-64) | 570374 | **PASS.** `slurm/gen/regress.slurm` from the export (sharedq <NODE>, GCC 11.4): `gen/test_keys.py` 97/97 (X6: the crafted invalid class files exit 2 from `test_keys --generator` and the three generators with no output; classes1..8 pass the validation), `test_run_l8` 5/5, `test_verify_inventory` 25/25, `test_regress` 86/86, `test_handoff_inventory` 17/17, `check_sources` passed; `regress.py --threads 1,8` at L3–L7: A-INV-2 PASSED (free L3–L6 rate-line files only, 492; free L7 and power L3–L7 identical; headers agree with the rows). Its record passes `regress.h1_problems` (X5: loops 3..7, threads 1 and 8, `coverage.h1` true) on the Mac. |
| **J-VAL-1** (`make test` on a whole amdq node) | 570372 | **PASS.** `tests/check_venv.py --strict` passes; `make test OUTPUT=…` exits 0 in 1,106 s as one command: validate (52 tests), check_venv, **unit_orchestration 49 groups / 61 tests, 0 failed, on Linux with the real worker** (X8 `runtime_identity` with the real `ldd` and library hashes; the A-ORC-13 claim spy, which now also sees `runtime_identity.json` read; X9-X13, X21), test_pipeline 3 parts / 27 tests (X1, X10, X14, X15), ast_scan (27 files) and ast_scan over gen/ and tests/ (44 files), 0 findings, test_regress 86/86, test_handoff_inventory 17/17 (X5), merge_scale, check_vendored 28/28 (X7), vendored_isolated 10/10 `--in-place`, the delivery-verifier test (X20 and the symlinked-directory case), check_inputs 16/16 with 2 skips as before (no `.git`, no inventory tree; the six X4 repair checks pass), test_profiling 15, test_gmp_prefix 7, test_numerics_flags 11/11, test_dd_profile 8/8, sanitize `--capture-check`, workflow, staging; then `assembly_checks.py --exact` 37/37, `verify_result_tamper.py` 81/81 (X16) and `compat_2026.py` exit 0 (max relative difference 0.0); executables unchanged by `make test`. |
| **X8 on real Slurm** (runtime identity) | 570376, 570377 | **PASS.** Details below. 570375, the first attempt, stopped at its plan (`ValueError: at least 2 replicates`: the script asked for 1); the corrected script (`--replicates 2`, now in `scripts/s1x8.slurm`) was uploaded read-only to `<SCRATCH>/c8d2/work/s1-c30bfc5f0bdf/` outside the export (`s1.sh upload`, both sha256 `b39384e2…` in `admission/submitted.txt`) and run as 570376 and 570377; nothing was planned or added by 570375. |
| **dd+mp256 J-FLAG gate re-run** (X1–X3) | 570373 | **PASS** at full scale, and **`design.check_gate` accepts its record** (in the job and on the Mac); 570210's record is refused for exactly the three missing-evidence reasons. Details below. |
| **Route-(b) re-freeze** with the new gate record | 570379 | **PASS.** The four route-(b) freezes (`--numerics dd+mp256`, the approval, the profile cost model `9b0dfec6…`, `--numerics-gate` the 570373 record) at 1e-3, 5e-4, 2.5e-4 and 1.35e-4 give **the same designs as pre6b's (570302), `design.json` byte for byte** (counts, r, s, K, η_node, cost and SE equal; route (b) keeps the re-optimized design at 1e-3 and the exact design at the three tighter targets, as before); `design_meta.json` records the new gate (`2eaaebcf…`). Their test-only plans (`production.py plan --design … --numerics dd+mp256`, J-DES-5's sizing, not submitted) all exit 0 with every cap holding, `numerics_route` route b, the gate `2eaaebcf…`, `executable_gated: true`, `cost_model_numerics` `dd+mp256` (X10), the bundle pinned in `<campaign>/design_bundle` (X9), and the same tasks / checkpoints / indices as pre6b's plans; all four plan directories deleted. |
| X13 on real Slurm | none | Not run: reproducing the stale-snapshot interleaving needs two lanes racing on one failing index, which a cheap real-Slurm job cannot force. The Mac test `unit_orchestration` `lane_fail_recheck` replays it and ran on Linux in J-VAL-1. |

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1 thread
per core; the Intel sharedq nodes: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on amdq +
amddebugq + amdpreq; the peak was 3 (570371-570373 from 22:08:28 to 22:12:07, two of them pending on the build;
`admission/h7_admission.jsonl`). amdq/amddebugq with `--exclude=cn112`; no longq; sharedq `--no-requeue`; every job
with `--mem` and `--time`; every job named `c8d2-*`. Each started at once on idle nodes (the survey before each sbatch:
`admission/squeue_before_*.txt`; the other <USER> jobs, `sri_eng_*`, belong to another project and were not counted
or touched). Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/c30bfc5f0bdf/<run>/` (copies here, without the five large files listed in
`large_files.sha256`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570371 | build, A-RPL-8, thread identity (X3) (`scripts/s1build.slurm`) | amddebugq <NODE> (EPYC 7543) | COMPLETED 0:0 | 3:46 | 4.02 |
| 570372 | J-VAL-1 (`scripts/s1val1.slurm`, afterok 570371) | amdq <NODE> (EPYC 7543) | COMPLETED 0:0 | 18:43 | 19.96 |
| 570373 | `dd+mp256` J-FLAG gate re-run (`scripts/s1flag.slurm`, afterok 570371) | amdq <NODE> (EPYC 7543) | COMPLETED 0:0 | 12:40 | 13.51 |
| 570374 | J-GEN-1 (`slurm/gen/regress.slurm` of the export) | sharedq <NODE> (Xeon Gold 6148) | COMPLETED 0:0 | 3:40 | 0.24 |
| 570375 | X8 part a, first attempt (its plan refused 1 replicate; nothing planned) | sharedq <NODE> | FAILED 3:0 | 0:02 | 0.00 |
| 570376 | X8 part a (the corrected `scripts/s1x8.slurm`, uploaded) | sharedq <NODE> | COMPLETED 0:0 | 0:45 | 0.03 |
| 570377 | X8 part b (`--exclude=<NODE>`) | sharedq <NODE> (Xeon Gold 6148) | COMPLETED 0:0 | 0:19 | 0.01 |
| 570379 | route-(b) re-freeze and its test-only plans (`scripts/s1des.slurm`, afterok 570373) | sharedq <NODE> | COMPLETED 0:0 | 32:24 | 2.16 |
| **total** | 8 records | | | | **39.93** |

Budget: 39.93 of this task's 80 core-hours. Symmetry's total in this workflow goes from 495.7 to 535.6 core-hours.

## X8: the runtime identity on real Slurm (570376 on <NODE>, then 570377 on <NODE>)

A tiny test-only campaign `<SCRATCH>/c8-d2/x8-c30bfc5f0bdf` (`--pilot --test-graphs 1 --test-selection
cheapest --points 256 --replicates 2 --threads 2 --shards 1`, the exact symmetry cost model, fresh seed
5596940901639240691; 24 indices, one per group; never a result) on sharedq, so its CPU-vendor pin is Intel (both nodes
Xeon Gold 6148). Another library stack was made real: a byte copy of the `libgmp.so.10` that ldd resolves
(`/lib/x86_64-linux-gnu/libgmp.so.10`, `4dc20a90…`) with one zero byte appended (`df848006…`), first on
`LD_LIBRARY_PATH` (`s1x8a.570376.0/altlib.txt`: ldd resolves it).

| Step | Expected | Result |
|---|---|---|
| a1: run index 0 (<NODE>) | exit 0, the pin published | 0; `runtime_identity.json` key `04f1e51d…` |
| a2: run index 1 under the other libgmp | 64 before any block | 64: "this node (<NODE>) runs the executable with another run-time library stack than the campaign's first claim (index 0 on <NODE>): runtime identity 3d0c0a03… vs 04f1e51d…, differing in library libgmp.so.10 … Nothing run (exit 64)"; `claim_io` status "runtime identity refused", no native launch |
| a3: run index 0 under the other libgmp | 64 (the pin is checked before run-skip) | 64, the same message; every checkpoint unchanged |
| b1: run index 1 with the node's own libraries on **<NODE>** (another host and job) | 0 | 0 (same identity key) |
| b2: every other index, index 0 again (all blocks valid, run-skip accepts <NODE>'s checkpoint); `status` | 0 | 0 for all 24; status 0; the pins unchanged; checkpoints: <NODE> 1, <NODE> 23, one runtime key `04f1e51d…` (`checkpoint_hosts.json`) |
| b3: pin moved aside; run index 0 under the other libgmp | nonzero at run-skip | 1: it published that stack's pin, then "checkpoint was produced under another runtime library stack (runtime identity 04f1e51d…, the campaign's 3d0c0a03…; host <NODE>): its libraries differ from the campaign's (X8)" |
| b3: with that pin, `merge --jobs 2`, `merge --jobs 1`, `merge --serial` | nonzero, nothing published | 1, 1, 1; no `merged.json` |
| b4: the original pin restored, `merge --jobs 2` | 0 | 0; 24 groups merged |

The checkpoints' fingerprints from the two hosts differ only in `host` and the Slurm ids. The campaign stays on
BeeGFS as evidence (a test campaign, never assembled into a result).

## The dd+mp256 J-FLAG gate re-run (570373)

One whole amdq node, <NODE> (2 × EPYC 7543, 64 cores, 8 NUMA nodes), Ubuntu GCC 11.4.0, Boost 1.77, GMP 6.2.1;
`tests/numerics_flags.py --profile dd+mp256 --seeds-log $C8_SEEDS` at full scale in the export built by 570371, the
exact binary `2cc5e88e…` and the profile `d5df32ac…` checked before and after (`s1flag.570373.0/{before,after}.sha256`).
Wall 758 s. Record `s1flag.570373.0/jflag_dd+mp256/numerics_flags.json`, sha256 **`2eaaebcf…`**; `check_gate.json`.
- **Status `"passed"`**, verdicts F1, F2, F4 rows and F5 true, no development option.
- **X1 (coverage):** `F1.coverage` complete: scale 1, both sectors, L7 200 graphs × 256 points and L8 400 × 64 per
  sector, every point evaluated by the profile; binary128-accepted / MP points free 29,284 / 3,541 and power 50,625 /
  12,568 against the need of 10,000 / 1,000 (no doubling). These equal the counts G3 recomputed from 570210's baseline.
- **X2 (binding):** a fresh F1 baseline (153,600 points, 450-digit references); the read-only source snapshot
  `b48e0d2e…`; both executables rebuilt there from their build records' commands reproduce `2cc5e88e…` and `d5df32ac…`
  byte for byte (5 s each), and `numerics_f1_exact` and `numerics_f1_profile` were compiled there. The assumption G3
  could test only with fakes (byte-identical rebuilds from a snapshot in another directory) holds.
- **X3 (teams):** F5's teams equal the requests in every run and lane of both sectors (1, 8, 16, 64; 8 × 8),
  `team_sizes_verified: true`.
- **Same numbers as 570210.** F1's verdict and totals (0 violations), F2's totals and per-task statistics
  (|dC8| + 3 SE_d = 4.25e-16: dC8 1.3129e-16, SE_d 9.774e-17; 192,545 of 193,384 tasks identical, max normalized
  difference 5.58e-14) and F3 are equal field by field. F4: ×2.539 (free ×2.512, power ×2.673; exact 1,325.4, profile
  522.0 median lane-thread s) against 570210's ×2.530 (timing only).
- **Seeds:** F2's 49 seeds (base 820262401) were all present in symmetry's log ("0 added, 49 present").

## The route-(b) re-freeze (570379)

sharedq <NODE> (8 CPUs, 15 GB), the export's own `bin/` (`2cc5e88e…`, `d5df32ac…`; checked first, with `check_gate` on
the new record). Inputs as pre6b: the J-SWEEP-2 sweep `sweep2-5d7586e9f1ab` (exact, all 24,173 graphs, η_node from its
ledger), the profile cost model `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`, the approval reference of
2026-10-05. Each bundle is compared (`../pre6b/scripts/p6b_compare.py`) with pre6b's bundle of the same target
(`<SCRATCH>/c8d2/work/p6bdes-77fab7153c0e/bundles/b_<T>`).

| Target | Freeze | Same design as pre6b (570302) | `design.json` bytes | Plan: tasks / checkpoints / indices (pre6b) | Plan wall | Caps |
|---|---|---|---|---|---|---|
| 1e-3 | 16 s, re-optimized branch | counts, r, s, K, η_node, cost, SE equal | equal | 2,135,296 / 8,378 / 70 (the same) | 191 s | all hold |
| 5e-4 | 15 s, exact design kept | equal | equal | 5,356,096 / 21,035 / 205 (the same) | 541 s | all hold |
| 2.5e-4 | 8 s, exact design kept | equal | equal | 5,652,416 / 22,513 / 767 (the same) | 528 s | all hold |
| 1.35e-4 | 8 s, exact design kept | equal | equal | 6,395,520 / 26,191 / 2,470 (the same) | 626 s | all hold |

The bundles stay on BeeGFS in `<SCRATCH>/c8d2/work/s1des-c30bfc5f0bdf/bundles/` (`s1des.570379.0/bundles.tgz`
and `bundles.sha256` here); they are test-only bundles of the sweep, as pre6b's were. The production bundles are
frozen from the pilot (`docs/DESIGN.md`, "After the pilot"), with the 570373 record as `--numerics-gate`.

## Site changes

`~/c8d2/env.sh` (X11): `export C8_SITE=symmetry C8_AMDQ_CAP=4` became `export C8_SITE=symmetry` and `export
C8_AMDQ_CAP="${C8_AMDQ_CAP:-4}"` (2026-10-06, about 02:02 UTC, before the first job of this round, 570371, was
submitted at 02:08 UTC). Old sha256 `e5fdb68c…` (kept as
`~/c8d2/env.sh.bak-20261005-x11`), new `d1e900e9…` (recorded by every job's `env.sha256`). Sourced under `set -euo
pipefail` it gives 4 by default and keeps an explicit `C8_AMDQ_CAP=5`.

## Seeds

Five fresh seeds, drawn on the Mac (`secrets.randbits(63)`) and checked against the mirror (`setup/seed_precheck.txt`),
then in the jobs against symmetry's live log (`tools/seeds.py check`, derived group seeds included), each added with a
label after its plan: 5596940901639240691 (the X8 campaign, 570376) and 8254371171828472440, 4667087343024846102,
7487298389697020166, 1291125770599527451 (the four route-(b) test-only plans, 570379). The gate added none (F2's 49
seeds were present).
- symmetry's log afterwards: 103 seeds (`seeds/s1_symmetry.json`, sha256 `5d34d873…`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (98 → 103, the same set; a
  second merge adds nothing; `seeds/sha256.txt`).
- Expanse's log does not hold them yet: they are appended to `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the
  next two-log sync (no Expanse session was opened, by the site rule).

## Files

`scripts/` (`s1.sh`: export, sub, upload; `s1build.slurm`, `s1val1.slurm`, `s1flag.slurm`, `s1x8.slurm`,
`s1des.slurm`; J-GEN-1 used `slurm/gen/regress.slurm` from the export), `setup/` (export check, seed pre-checks),
`admission/` (the `squeue` snapshots, the H7 lines, every sbatch and the one upload), `logs/`, `sacct.txt`, `seeds/`,
`large_files.sha256`, and one folder per job run: `s1build.570371.0/`, `gen1.570374.0/`, `s1val1.570372.0/`,
`s1flag.570373.0/`, `s1x8a.570375.0/` (the refused first attempt), `s1x8a.570376.0/`, `s1x8b.570377.0/`,
`s1des.570379.0/`.
