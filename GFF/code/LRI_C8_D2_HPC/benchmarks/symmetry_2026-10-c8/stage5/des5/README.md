# J-DES-5 on symmetry: the design at production size, dry run (2026-10-05) [A-DES-5; A-PERF-4]

Job 570114 `c8d2-s5des5` (sharedq <NODE>, Intel Xeon Gold 6148, `-c 8 --mem=15G -t 06:00:00 --no-requeue`; script
`scripts/s5des5.slurm`, measurement helper `scripts/des5_measure.py`, both run from
`<SCRATCH>/c8d2/jobs/stage5/des5/`). Export `pkg/5d7586e9f1ab` (the final commit's tools; `design.py`
`034b51ee…`, `production.py` `237dda88…`), exact default path. Log `<SCRATCH>/c8d2/logs/c8d2-s5des5_570114.out`
(copy in `s5des5.570114.0/`). Survey before submission: sharedq 1 idle and 1 mixed node, no <USER> sharedq job; it
started at submission (sharedq is outside the H7 cap; `admission/`).

**What ran** (PLAN job table J-DES-5):
1. `tools/accounting.py` on the merged J-SWEEP-2 campaign `<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab` (its
   self-registered ledger entry, R10) and on the lane campaigns J-SMK-4 (`smk4-20261005`) and the J-SMK-3 batches
   `desc1`/`desc2`, for the lane-mode η_node of the refined cost table.
2. `tools/design.py report --test-only` on the sweep (the target table at the sweep's η_node) and again with
   `--eta-node` = J-SMK-4's.
3. `tools/design.py freeze --pilot <sweep> --test-only --target-rel T --seeds-log $C8_SEEDS --out
   <SCRATCH>/c8d2/work/des5-5d7586e9f1ab/bundles/des5_T` for T = 1e-3, 5e-4, 2.5e-4, 1.35e-4: η_node from the
   sweep's ledger (R10), costs from the campaign's own checkpoints, i.e. the campaign-keyed costs of the final binary
   (R05). No `--total-cap`: the dry run measures sizes; the budget is the user's decision.
4. For each bundle, `production.py plan … --design <bundle> --test-graphs all --cost-model
   cost_models/gmp_symmetry_amd_c8.json --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5
   --forbid-seeds-from $C8_SEEDS --seed <fresh>` under GNU `time -v` (a test-only plan of every graph: a test-only
   bundle is accepted only by test-only plans), NOT submitted; `des5_measure.py` recorded the plan; the seed went into
   symmetry's `$C8_SEEDS` with a label; the plan directory was then deleted (A-DES-5). The four seeds were synced into
   Expanse's log and the package mirror afterwards (`../seeds/06_des5_*.json`; the two-log rule).

## Results [A-DES-5: PASS]

The job finished with status 0 in 34:44 (08:18:52 to 08:53:35 EDT). Every freeze and every plan exited 0, every cap
held, and all four plan directories were deleted (`deleted.txt`; `plans_after.txt` lists an empty `plans/`). The four
bundles stay in `<SCRATCH>/c8d2/work/des5-5d7586e9f1ab/bundles/` (532 KB packed in `bundles.tgz` here;
`bundles.sha256`). Summary: `des5_summary.json` (`scripts/des5_summary.py s5des5.570114.0 des5_summary.json`, Mac).

**η_node** (`tools/accounting.py`, all four complete, every ledger job with its sacct record). η_node is busy thread
core-hours over **work** core-hours (the work roles lane, array and sweep); the allocated core-hours also count the
plan and merge jobs (overhead):

| Campaign | Kind | Allocated core-h | Work core-h | Busy thread core-h | η_node = busy / work |
|---|---|---:|---:|---:|---:|
| `sweep2-5d7586e9f1ab` (J-SWEEP-2) | self-registered sweep, one amdq node, 17:24 | 18.56 | 18.56 | 5.69 | **0.306** (used by the freezes, R10) |
| `smk4-20261005` (J-SMK-4) | 8 × 8 lanes, one amdq node, 1:22:47 | 88.44 | 88.30 | 80.76 | **0.915** (the lane-mode value of the cost table) |
| `desc1-20261005`, `desc2-20261005` (J-SMK-3) | one amdq lane worker each, 0:21 | 22.39, 22.48 | 22.19, 22.28 | 19.93, 19.95 | 0.898, 0.896 |

The sweep's η_node is low because a 17-minute job of 176 short indices carries its plan, its tail and its merge
inside the allocation. The freezes take it as `design.py` must (non-test freezes have no override), so their core-hours
are about 3× what lane-mode production would allocate; `docs/PERFORMANCE.md` ("Stage 5: the refined cost table")
re-expresses them at J-SMK-4's 0.915.

**The four freezes** (each 5.4 s, peak RSS 190 MiB; `design_<T>.json`, `design_meta_<T>.json`, `freeze_<T>.stdout`).
K = 1 is the minimum batch count at every target (`batches_minimum` 1, caps `ok` and `task_ok`). Core-hours are the
freeze's own (η_node 0.306) and at the lane η_node 0.915:

| Target (rel) | Target SE | Predicted SE (margin 1.5) | K | r: free L8 / power L8 | s: free L8 / power L8 | Core-h (η 0.306) | Core-h (η 0.915) | L8 share |
|---|---:|---:|---:|---|---|---:|---:|---:|
| 1e-3 | 46.0 | **32.63** | 1 | 128 / 32 | 1 / 1 | 11,832 | 3,963 | 0.93 |
| 5e-4 | 23.0 | 22.61 | 1 | 128 / 32 | 1 / 1 | 17,484 | 5,856 | 0.63 |
| 2.5e-4 | 11.5 | 11.31 | 1 | 128 / 64 | 4 / 2 | 69,934 | 23,423 | 0.63 |
| 1.35e-4 | 6.21 | 6.08 | 1 | 128 / 128 | 16 / 4 | 228,776 | 76,623 | 0.77 |

**The four plans** (`production.py plan --design`, test-only, never submitted; `measure_<T>.json`, the plan's
manifest gzipped as `plan_manifest_<T>.json.gz`, `time_plan_<T>.txt`, `du_plan_<T>.txt`). Plan wall is the job's
clock around the command (GNU time agrees within a second); the sharedq node is an Intel Xeon Gold 6148, 8 cores:

| Target | Tasks (a / b) | Checkpoints | Indices | tasks.sqlite (largest group) | Per-index task files (largest) | Manifest | Plan wall | Plan peak RSS | Task core-h (estimate) | Largest index wall | Merge passes (projected) | Projected files | Plan dir |
|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| 1e-3 | 5,221,600 (2,610,656 / 2,610,944) | 20,533 | 351 | 455 MiB (180 MiB) | 351, 141 MiB (1.3 MiB) | 188 KiB | 307 s | 0.84 GiB | 3,582 | 5,383 s | 2 (583 s) | 21,810 | 629 MiB, 425 files |
| 5e-4 | 5,365,152 (2,683,328 / 2,681,824) | 21,266 | 505 | 469 MiB (180 MiB) | 505, 147 MiB (714 KiB) | 259 KiB | 497 s | 0.84 GiB | 5,291 | 5,385 s | 2 (583 s) | 23,005 | 650 MiB, 579 files |
| 2.5e-4 | 5,892,288 (2,970,624 / 2,921,664) | 23,878 | 1,976 | 521 MiB (186 MiB) | 1,976, 171 MiB (181 KiB) | 930 KiB | 547 s | 0.89 GiB | 21,164 | 5,400 s | 2 (590 s) | 30,030 | 728 MiB, 2,050 files |
| 1.35e-4 | 8,545,280 (4,463,616 / 4,081,664) | 36,475 | 6,424 | 723 MiB (250 MiB) | 6,424, 264 MiB (78 KiB) | 2,961 KiB | 678 s | 1.31 GiB | 69,247 | 5,400 s | 2 (837 s) | 55,971 | 1,026 MiB, 6,498 files |

- **Caps (A-DES-5 "every cap holds"):** tasks per campaign ≤ 5 × 10^7 (largest 4.46 × 10^6), checkpoint blocks
  ≤ 2 × 10^5 (largest 36,475), replicates ≤ 128, predicted task seconds ≤ 120 (largest 60.0), projected merge ≤ 12 h
  (largest 837 s), every count within its Sobol net's period (2^52 for a, 2^60 for b), and the bundle's own cap
  record (`caps.ok`, `caps.task_ok`): all true at every target (`all_caps_hold` in each `measure_<T>.json`).
- The task count grows slowly with the target (5.2 → 8.5 million) because the planner fills 60-second tasks: a tighter
  target mostly makes tasks longer, and the index count follows the core-hours (351 → 6,424 indices of up to 1.5 h at
  8 threads). Above 1,000 indices `submit.sh` splits arrays into offset windows (printed by the plan); lanes are
  unaffected.
- Every plan suggests index time limits of 2:15 h (`suggested_time_seconds` 8,100-8,160), 3.1-3.2 GB of memory per
  index and a 1-hour merge limit.
- **Lustre / BeeGFS:** a 1.35e-4 plan holds 6,498 files at planning time and projects 55,971 by the end of its run
  (checkpoints 36,475, task files 6,424, lane markers and logs 12,848). On Expanse about five such batches fill the
  agreed 300,000-file session budget, and the shared quota (2 M files) stood at 1.6 M on 2026-10-05.

**The report** (`report_sweep_eta.{json,stdout}` and `report_lane_eta.{json,stdout}`, 8 s, 276 MiB): the same four
rows at η_node 0.306 and 0.915. With 2 replicates per graph the per-stratum kurtosis, skewness, max|z|, largest share
and P8 are null, and the L8 tail screen is empty because the sweep's 512 points per replicate are below the screen's
4,096 (the L ≤ 7 diagnostics are printed). The pilot's 8 replicates at 4,096 points make all of them defined.

**Finding F11 (new; `tools/design.py` `split()`; for the Stage-6 inspection):** the replicates r of a (sector, L)
follow the LARGEST stratum multiplier of the group. At free L8 the 248 primitives form their own stratum, cheap and
with a large multiplier: at 1e-3 the continuous Neyman multipliers are 176.8 for the primitives and 35.1 for the other
free L8 graphs, so the group gets r = 128 and the dominant stratum (83% of the cost) runs at r × s = 128 where 32
would do. The 1e-3 freeze therefore overshoots (SE 32.63 against 46.0) at 2.98× the continuous Neyman cost; at 5e-4
and tighter the group's multipliers are ≥ 128 anyway and the frozen designs are within 1.10× of the continuous optimum.
Recomputed on the Mac with `design.py`'s own `optimize()` (which reproduces the frozen 1e-3 design exactly) and `r`
taken instead from the group's costliest stratum: 1e-3 then costs 5,188 core-hours at η 0.306 (1,738 at 0.915; SE
44.2) instead of 11,832 (3,963), and the other three targets are unchanged. The fix is a `tools/design.py` change (and
a new H6 sha256); until then the 1e-3 rows of the cost table overstate the cost of that target by about 2.3×.
**Fixed in 23540b2:** r now follows the group's SMALLEST multiplier, which the variance-cost optimum selects
(`docs/DESIGN.md`, rule 4 and "F11"); on these freezes it coincides with the costliest stratum, and `../pre6/`
recomputes the 1e-3 design (1,738 lane core-hours, SE 44.2) and confirms that the other three are unchanged.

**Cost.** 2,084 s on 4 physical cores (8 hyperthreads on the Intel sharedq node) = **2.32 core-hours**; sacct
`570114|c8d2-s5des5|sharedq|<NODE>|COMPLETED|00:34:44`.

**Files.** `s5des5.570114.0/`: the job's evidence folder as written on symmetry
(`<SCRATCH>/c8d2/evidence/5d7586e9f1ab/s5des5.570114.0/`) plus the job log; `scripts/` (the job script and
measurement helper as run, sha256 `867df706…` and `81ee76a8…`, `des5_summary.py`, and `aperf4_table.py` for the
refined cost table); `admission/` (the sharedq survey and the sbatch line); `des5_summary.json`; `aperf4.json` and
`aperf4_table.md` (A-PERF-4, `docs/PERFORMANCE.md`).
