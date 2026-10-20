# Pre-Stage-6b on symmetry (2026-10-05): the fixed design tool of 77fab71 on J-DES-5's real data

Site rule: symmetry only (user, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry is not
enough"); Expanse, personal desktops were not touched. One sharedq job (570302) ran from the git-archive
export of the fix commit **77fab7153c0e** itself (`<SCRATCH>/c8d2/pkg/77fab7153c0e`;
`setup/export_check_77fab7153c0e.json`: 8,480 files equal to the archive). This folder's scripts are not in that
export: `scripts/p6b.sh stage` copied `p6bdes.slurm` and `p6b_compare.py` to `<SCRATCH>/c8d2/jobscripts/pre6b/`
(read-only; the sha256 on both sides in `setup/staged_scripts.sha256`, and the job hashed them again in
`p6bdes.570302.0/inputs.sha256`). What changed in 77fab71: `tools/design.py` `optimize()` searches the integer
allocation from both split rules with a prune pass and a bounded lattice search, and a route-(b) freeze keeps the
cheaper feasible of its re-optimized design and the exact design re-costed under the profile (F13 and the F11
follow-up; `docs/DESIGN.md`, rule 4 and "Route (b)"). The Mac recomputation that came with the fix is
`../../mac_2026-10-c8/f13fix/` (`tests/test_pipeline.py`, `jdes5_records`); the run it re-checks is `../pre6/` (job 570241).

## Verdicts

| Item | Verdict |
|---|---|
| Export | **PASS.** 8,480 files, contents and modes equal to `git archive 77fab71`. |
| Executables (needed by `production.py plan`: `--describe`, build record) | **Byte-identical to 570239's**, although built on an Intel sharedq node (<NODE>, Xeon Gold 6148) instead of AMD <NODE>: `make -j8 gmp` → `bin/c8d2_gmp` `2cc5e88e…`, `make -j8 gmp NUMERICS=dd,mp256` → `bin/c8d2_gmp_dd+mp256` **`d5df32ac…`** (the build the `dd+mp256` J-FLAG gate 570210 passed); the default executable unchanged by the profile build; Ubuntu GCC 11.4, Boost 1.77 (`identity.json`). The two L8 packs were re-hashed against the export's `inputs/manifest.json` and hard-linked from `pkg/7a8aad783c31` (`l8_packs.json`). |
| Exact freezes (`design.py freeze --test-only`, J-DES-5's arguments) | **PASS.** 1,702 / 5,740 / 22,961 / 74,573 lane core-hours at SE 46.00 / 23.00 / 11.50 / 6.21 (targets 46 / 23 / 11.5 / 6.21): ×0.980 / 0.980 / 0.980 / 0.973 of the 570241 freezes (1,738 / 5,856 / 23,423 / 76,623). r, s, the start kept, cost and SE equal the Mac recomputation exactly (relative difference 0 in cost and SE); base counts equal J-DES-5's and 570241's at every target. Every bundle's cap record holds (the per-graph caps the Mac could not check). |
| Route-(b) freezes (`--numerics dd+mp256`, the approval, `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` `9b0dfec6…`, the 570210 gate record) | **PASS.** The freeze keeps **638** (re-optimized) / **2,241** / **8,963** / **29,328** (the exact design kept) lane core-hours, every SE at its target: ×0.692 / 0.674 / 0.674 / 0.863 of the 570241 route-(b) freezes (923 / 3,322 / 13,289 / 33,978) and ×0.954 / 0.970 / 0.970 / 0.975 of 570241's exact allocation kept (669 / 2,309 / 9,236 / 30,067), i.e. ×0.375 / 0.390 / 0.390 / 0.393 of the new exact path. Both branches, the branch chosen and the costs equal the Mac recomputation (relative differences ≤ 8e-15); the kept exact design passes every cap under the profile's costs. `design.py report --numerics dd+mp256` prints the same branch per target. |
| Plans (`production.py plan --design <bundle> --test-graphs all`, J-DES-5's sizing; not submitted) | **PASS.** All eight exit 0; every cap holds (`measure_<R>_<T>.json`, `all_caps_hold`); route-(b) plans record `numerics_route` with the executable `d5df32ac…` and `executable_gated: true`, the exact plans none; all eight plan directories deleted (`deleted.txt`, `plans_after.txt`). |

## Job

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × AllocCPUS / ThreadsPerCore (<NODE>: 2
threads per core). sharedq with `--no-requeue`, `--mem=15G`, `-t 02:00:00`; sharedq is outside the H7 AMD-pool cap, no
AMD partition and no longq were used; a `squeue -u <USER>` snapshot before the sbatch (`admission/`; the other
<USER> jobs, `sri_eng_*` and `lri-prod2`, belong to other projects and were not counted or touched). Log:
`<SCRATCH>/c8d2/logs/c8d2-p6bdes_570302.out` (copy in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/77fab7153c0e/p6bdes.570302.0/` (copy here; the seed log it saved is `seeds/p6b_symmetry.json`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570302 | packs, `make gmp`, `make gmp NUMERICS=dd,mp256`, 2 reports, 8 freezes, 8 test-only plans (`scripts/p6bdes.slurm`) | sharedq <NODE> (Xeon Gold 6148, 8 CPUs) | COMPLETED | 1:01:17 | **4.09** |

Budget: 4.09 of this task's 15 core-hours; symmetry's total in this workflow goes from 491.6 to 495.7 core-hours.
Timings: both builds 36 s and 38 s; the reports 18 s (exact) and 31 s (`dd+mp256`, which designs both branches per
target); each freeze 5.6-11.1 s at 0.2 GiB (570241: 5-6 s); the plans 132-641 s at 0.40-1.31 GiB.

## Results (`p6b_tables.md`, from `p6b_tables.py`)

Lane core-hours are each freeze's own (η_node 0.306 of the J-SWEEP-2 sweep, as `design.py` takes it from the ledger)
× 0.306 / 0.9146 (J-SMK-4's lane η_node; the allocation does not depend on η_node). "570241" is `../pre6/`'s freeze of
the 23540b2 tool at the same target; "Mac" is the fix's recomputation from 570241's committed strata.

| Target | Route | SE (target) | r: free L8 / power L8 | s: free L8 / prim / power L8 | Core-h (freeze) | **Lane core-h** | 570241 | Mac | Plan: tasks / checkpoints / indices (570241) | Plan wall, RSS | Caps |
|---|---|---:|---|---|---:|---:|---:|---:|---|---|---|
| 1e-3 | exact | 46.00 (46.00) | 32 / 32 | 1 / 1 / 1 | 5,083 | **1,702** | 1,738 | 1,702 | 2,111,808 / 8,324 / 161 (2,136,768 / 8,419 / 164) | 173 s, 0.40 GiB | all hold |
| 1e-3 | route (b), re-optimized | 46.00 (46.00) | 32 / 32 | 1 / 8 / 1 | 1,906 | **638** | 923 | 638 | 2,135,296 / 8,378 / 70 (2,135,328 / 8,378 / 96) | 132 s, 0.40 GiB | all hold |
| 5e-4 | exact | 23.00 (23.00) | 128 / 32 | 1 / 4 / 1 | 17,139 | **5,740** | 5,856 | 5,740 | 5,365,152 / 21,148 / 496 (5,365,152 / 21,266 / 505) | 366 s, 0.84 GiB | all hold |
| 5e-4 | route (b), exact design kept | 23.00 (23.00) | 128 / 32 | 1 / 4 / 1 | 6,690 | **2,241** | 3,322 | 2,241 | 5,356,096 / 21,035 / 205 (5,356,224 / 21,142 / 296) | 510 s, 0.84 GiB | all hold |
| 2.5e-4 | exact | 11.50 (11.50) | 128 / 64 | 4 / 16 / 2 | 68,556 | **22,961** | 23,423 | 22,961 | 5,890,112 / 23,793 / 1,937 (5,892,288 / 23,878 / 1,976) | 475 s, 0.89 GiB | all hold |
| 2.5e-4 | route (b), exact design kept | 11.50 (11.50) | 128 / 64 | 4 / 16 / 2 | 26,761 | **8,963** | 13,289 | 8,963 | 5,652,416 / 22,513 / 767 (5,666,496 / 22,547 / 1,128) | 548 s, 0.84 GiB | all hold |
| 1.35e-4 | exact | 6.21 (6.21) | 128 / 128 | 16 / 64 / 2 | 222,654 | **74,573** | 76,623 | 74,573 | 8,511,360 / 36,207 / 6,254 (8,545,280 / 36,475 / 6,424) | 641 s, 1.31 GiB | all hold |
| 1.35e-4 | route (b), exact design kept | 6.21 (6.21) | 128 / 128 | 16 / 64 / 2 | 87,564 | **29,328** | 33,978 | 29,328 | 6,395,520 / 26,191 / 2,470 (6,664,448 / 28,372 / 2,859) | 595 s, 0.90 GiB | all hold |

**Route (b)'s two branches** (`route_b_choice` in each route-(b) `design_meta.json`; lane core-hours, SE):

| Target | Re-optimized | Exact design kept, re-costed under `dd+mp256` | Chosen | 570241 route-(b) freeze | 570241 exact allocation kept |
|---|---:|---:|---|---:|---:|
| 1e-3 | **638** (46.00) | 646 (46.00) | re-optimized | 923 (35.83) | 669 (44.21) |
| 5e-4 | 2,554 (23.00) | **2,241** (23.00) | exact design kept | 3,322 (18.53) | 2,309 (22.61) |
| 2.5e-4 | 10,215 (11.50) | **8,963** (11.50) | exact design kept | 13,289 (9.26) | 9,236 (11.31) |
| 1.35e-4 | 31,371 (6.21) | **29,328** (6.21) | exact design kept | 33,978 (5.91) | 30,067 (6.08) |

- **The optimizer on real data** (`design_meta.json`, `optimizer`; third table of `p6b_tables.md`). Both starts end at
  the same design at every target and the F11 start is kept (the tie rule). At 1e-3 (exact) the F11 start's greedy
  design is 570241's (1,738, SE 44.21) and 25 prune steps take it to 1,702; the Stage-5 start's greedy design is
  J-DES-5's (3,963, SE 32.63) and 14 prune steps and 2 lattice moves take it to the same 1,702. At the three tighter
  targets the greedy designs are 570241's and J-DES-5's (the same there), and 9 prune steps plus 1-3 lattice moves
  (2-4 boxes) give 5,740 / 22,961 / 74,573. Route (b) at 1e-3: greedy 923 (F11 start; 570241's) or 835 (Stage-5
  start) → 638 after 32 or 29 prune steps and one lattice move.
- **Caps on real data.** The bundle cap records and the plans agree: tasks per campaign at most 4.44 × 10^6 (cap 5 ×
  10^7), checkpoints at most 36,207 (cap 2 × 10^5), r ≤ 128, predicted task seconds at most 60.0 (cap 120), projected
  merge at most 837 s (cap 12 h), largest index wall 5,400 s (the 1.5-hour sizing), Sobol periods. The kept exact
  designs also hold every cap under the profile's costs (`kept_exact_allocation.caps_ok`). Caps do not bind at these
  sizes, as the fix expected.
- **What changed against 570241.** Exact path: the base counts are unchanged (equal to J-DES-5's and 570241's at every
  target); only r and s move, and the SE now sits at the target instead of below it (no slack; the variance margin ×1.5
  is unchanged). Route (b): at 1e-3 the re-optimized design keeps 570241's base counts and r and changes s; at the
  three tighter targets the freeze keeps the exact path's base counts (the profile's own base counts put more graphs
  at the 4,096-point floor, `docs/DESIGN.md`, "Route (b)"). The route-(b) plans have 14-32% fewer indices than
  570241's route-(b) plans (cheaper designs at the same 1.5-hour sizing) and 57-61% fewer than the exact plans at the
  same target.
- **Not re-checked here:** budget mode (`--budget-core-hours`) was not exercised on real data (the Mac's randomized
  test covers it); the numbers carry the sweep's σ² (2 replicates × 512 points per graph) and move with the pilot's.

## Seeds

Eight fresh seeds, drawn on the Mac (`secrets.randbits(63)`), checked before the sbatch against symmetry's live log
with the export's `tools/seeds.py check` (`setup/seed_precheck.txt`; log `d4c73223…`, 90 seeds) and again in the job
(`seed_check_<R>_<T>.txt`, derived group seeds included), each added with a label after its plan (`seeds_add.txt`):
exact 646681868424905773, 4389531996626061086, 1555153655230592368, 4030516215308314467; route (b)
6634384558034372355, 1010815034822057179, 1211354083646889487, 8838276593323891731.
- symmetry's log afterwards: 98 seeds (`seeds/p6b_symmetry.json`, sha256 `7b515f1b…`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (90 → 98, the same set;
  `seeds/sha256.txt`).
- Expanse's log does not hold them yet: they are listed in `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the next
  two-log sync (no Expanse session was opened, by the site rule).

## Files

`scripts/` (`p6b.sh`: export, stage, sub; `p6bdes.slurm`; `p6b_compare.py`), `setup/` (export check, staged-script
sha256, seed pre-check), `admission/` (the `squeue` snapshot and the sbatch line), `logs/`, `sacct.txt`,
`p6bdes.570302.0/` (node, gcc, `l8_packs.json`, make logs, `binaries*.sha256`, `profile.sha256`, `describe/`,
`build_records/`, `identity.json`, `inputs.sha256`, both reports, the 8 `design_*`/`design_meta_*`, `compare_*`
(against 570241's bundles and J-DES-5's), `freeze_*`/`plan_*` output, GNU time records, `measure_*`, `route_*`, gzipped
plan manifests, `du_plan_*`, `bundles.tgz` with `bundles.sha256`, seed records), `seeds/`, and `p6b_tables.py` →
`p6b_tables.json`, `p6b_tables.md` (Mac, seconds):

```bash
python3 -B benchmarks/symmetry_2026-10-c8/pre6b/p6b_tables.py --package . --des benchmarks/symmetry_2026-10-c8/pre6b/p6bdes.570302.0 \
  --out benchmarks/symmetry_2026-10-c8/pre6b/p6b_tables.json --markdown benchmarks/symmetry_2026-10-c8/pre6b/p6b_tables.md
```

The eight bundles stay on BeeGFS in `<SCRATCH>/c8d2/work/p6bdes-77fab7153c0e/bundles/`; the export
`pkg/77fab7153c0e` (with its `bin/` and the hard-linked L8 packs) stays too.
