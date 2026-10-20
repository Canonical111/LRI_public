# Pre-Stage-6 on symmetry (2026-10-05): the `dd+mp256` profile cost model and the J-DES-5 re-check (F11 fixed, route (b))

Site rule: symmetry only (user, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry is not
enough"); Expanse was not touched by this run. Everything ran from the git-archive export of **3a250eaa5918**
(`<SCRATCH>/c8d2/pkg/3a250eaa5918`; `setup/export_check_3a250eaa5918.json`: 8,272 files equal to the
archive). 3a250ea is the design agent's head 99bbfdd (F11 fix and route (b), tools 23540b2) plus this folder's job
scripts (`scripts/`), so its `tools/`, `src/` and `tests/` are 99bbfdd's. The L8 packs were re-hashed against the
export's `inputs/manifest.json` and hard-linked from `pkg/7a8aad783c31/inputs/packs` (`p6build.570239.0/l8_packs.json`).
The Mac-only recomputation that preceded this run is `../stage5/pre6/`.

## Verdicts

| Item | Job | Verdict |
|---|---|---|
| Build, A-RPL-8 | 570239 | **PASS.** `make`, `make gmp`: decimal `619ddf7d…` and gmp `2cc5e88e…` byte-identical to the Stage-5 symmetry build of 5d7586e; `make gmp NUMERICS=dd,mp256`: `bin/c8d2_gmp_dd+mp256` **`d5df32ac…`**, byte-identical to the build the `dd+mp256` J-FLAG gate passed (570208/570210), every default executable unchanged by it; `--describe`: numerics `dd+mp256`, not diagnostic, no development override, no stub; Boost 1.77 (`p6build.570239.0/identity.json`). |
| Profile cost sweep (route (b)) | 570240 | **PASS.** `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (sha256 `9b0dfec6…`): all 48,346 `campaign:sector:L:graph` keys, numerics identity `dd+mp256`, executable `d5df32ac…` (gated), AMD EPYC 7543 on <NODE> (J-SWEEP-2's node), the approval reference in the campaign manifest and in the model's note. Speedup over the exact symmetry model ×2.814 overall (equal points per graph), free L8 ×2.754, power L8 ×2.965 (below). |
| J-DES-5 re-check, exact path, F11-fixed `design.py` | 570241 | **PASS.** 1e-3: free L8 r 128 → 32, **1,738 lane core-hours** (5,188 at the sweep's η_node), SE 44.21 against 46: exactly the `../stage5/pre6/` projection (r, s and cost); 5e-4, 2.5e-4, 1.35e-4: `design.json` **byte-identical** to J-DES-5's (5,856 / 23,423 / 76,623). Plans of all four: every cap holds; plan directories deleted. |
| J-DES-5 re-check, route (b) `dd+mp256` | 570241 | **Works end to end; finding F13.** The four route-(b) freezes (approval, profile model, gate record 570210) and their plans (`--numerics dd+mp256 --approved-numerics-change`, executable gated) exit 0, every cap holds. Lane core-hours **923 / 3,322 / 13,289 / 33,978** (×0.531 / 0.567 / 0.567 / 0.443 of the exact freezes), but the re-optimized allocation over-delivers (SE 35.83 / 18.53 / 9.26 / 5.91) and costs 1.13-1.44× the exact allocation kept and re-costed under `dd+mp256` (669 / 2,309 / 9,236 / 30,067 at the exact SEs, which meet every target). |

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1 thread
per core; the Intel sharedq node: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on amdq +
amddebugq + amdpreq; the peak was 2 (570239 and 570240; `admission/h7_admission.jsonl`). amdq/amddebugq with
`--exclude=cn112`; no longq; sharedq `--no-requeue`; every job with `--mem` and `--time`; a survey before every sbatch
(`admission/squeue_before_*.txt`; the other <USER> jobs, `sri_eng_*` and `lri-prod2`, belong to other projects and
were not counted or touched). Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/3a250eaa5918/<run>/` (copies here, without the two cost-model files listed below).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570239 | build, A-RPL-8 (`scripts/p6build.slurm`) | amddebugq <NODE> (EPYC 7543) | COMPLETED | 0:44 | 0.78 |
| 570240 | `dd+mp256` profile cost sweep (`scripts/p6sweep.slurm`; `--nodelist=<NODE>`, afterok 570239) | amdq <NODE> (EPYC 7543) | COMPLETED | 7:11 | 7.66 |
| 570241 | J-DES-5 re-check: accounting, model install, 2 reports, 8 freezes, 8 test-only plans (`scripts/p6des.slurm`; afterok 570240) | sharedq <NODE> (Xeon Gold 6148, 8 CPUs) | COMPLETED | 1:01:48 | 4.12 |
| **total** | 3 records | | | | **12.56** |

Budget: 12.56 of this workflow's 120 core-hours; the development total goes from about 1,490 to about 1,503 of 5,000.

## The `dd+mp256` profile cost model (job 570240)

J-SWEEP-2's shape on the gated profile build: `slurm/sweep.sh … --points 512 --replicates 2 --threads 8 --cost-model
<J-SWEEP-1's model> --numerics dd+mp256 --approved-numerics-change "user check-in 2026-10-05: dd+mp256 approved for
production after the pilot (C62d PLAN-REVIEW-LOG)" --merge-jobs 32 --calibration <its own file>` on one whole amdq node,
8 × 8 NUMA slots, fresh seed 8928960886563889504. It was chunked with J-SWEEP-2's own chunking model (J-SWEEP-1's) and
pinned to J-SWEEP-2's node (<NODE>), so its plan is J-SWEEP-2's (24 indices, 96,692 tasks, 394 checkpoints) and only the
numerics and the seed differ. Wall 7:11 against J-SWEEP-2's 17:24; `accounting.py` complete (7.66 allocated, 2.02
busy, η_node 0.264). The calibration rows went to `p6sweep.570240.0/calibration_dd+mp256.json`, never to
`tools/calibration.json`.

**Installed model.** `make_cost_model.py`'s output (`p6sweep.570240.0/cost_model.json`, sha256 `34e4ba8b…`, kept on
BeeGFS) with only its `note` extended by the approval reference and the gate (note is one of `make_cost_model.py`'s
volatile fields; every other field checked equal, `p6des.570241.0/cost_model_install.json`): **`9b0dfec6…`**, installed
as `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`; the freezes and plans below used these bytes. It has no Intel
`cpu_class_factors` (production is AMD only, F5). It is valid for the `d5df32ac…` build; another profile build (a
`src/` change, another compiler or site) needs its own sweep and gate.

**Speedup per (sector, L)** (`p6_tables.md`): the exact symmetry model's seconds per point (J-SWEEP-2, `a1b6e5d2…`, the
same node) over the profile's, summed over the graphs of both campaigns; the gate's factor k is 570210's (F4 at L8, F2's
task seconds at L ≤ 7; `../stage5/pre6/`):

| Sector, L | Graphs (a+b) | Speedup, equal points | At the 1e-3 allocation | Per graph: median (P10-P90) | Gate k |
|---|---:|---:|---:|---|---:|
| free L3-L6 | 10 / 32 / 152 / 790 | ×1.197 / ×0.994 / ×0.985 / ×1.048 | | ×0.99-1.10 | ×0.90-1.09 |
| free L7 | 4,882 | **×2.778** | ×2.526 | ×2.61 (1.08-3.23) | ×2.728 |
| free L8 (all) | 32,128 | **×2.754** | ×2.546 | ×2.68 (1.11-3.11) | ×2.485 |
| free L8, primitives | 496 | ×1.003 | | ×1.00 (0.99-1.02) | |
| power L3 / L4 | 2 / 6 | ×1.115 / ×1.464 | | | ×1.228 / ×1.322 |
| power L5 | 40 | ×2.354 | ×2.197 | ×2.24 (1.54-2.99) | ×2.393 |
| power L6 | 214 | ×3.294 | ×3.027 | ×3.19 (2.36-3.78) | ×3.160 |
| power L7 | 1,418 | **×3.448** | ×3.344 | ×3.39 (2.78-3.79) | ×3.344 |
| power L8 | 8,672 | **×2.965** | ×2.983 | ×3.03 (2.69-3.51) | ×2.644 |
| all | 48,346 | ×2.814 | | | |

- Free L3-L6 and the free L8 primitives have almost no promoted points, so ×1.0 is expected (their tasks are very
  short; free L3's 10 graphs carry timer noise); the power sector gains from L4 on (×1.46 at L4, ×2.35-3.45 at
  L5-L8). Campaigns a and b agree at L7-L8 to 3% (`p6_tables.json`).
- At L8 the sweep gives ×2.754 (free) and ×2.965 (power) against the gate's F4 ×2.485 and ×2.644. F4 measures
  lane-thread seconds of an L8 sample including graph loading, which the profile does not shorten; the model counts
  native task seconds per point. The same gate's F2 integration-only task seconds give ×2.68-3.39 per (campaign,
  sector, L ≥ 7) (`../stage5/close/README.md`), in line with the sweep; the cost tables use the sweep's model.
- Expanse has no profile model yet: its `dd+mp256` rows in `docs/PERFORMANCE.md` remain projections from Stage 4c's
  gate.

## The J-DES-5 re-check (job 570241)

J-DES-5's arguments (`../stage5/des5/README.md`) on the merged J-SWEEP-2 sweep (`sweep2-5d7586e9f1ab`, exact, all
24,173 graphs; η_node 0.306 from its own ledger), with the F11-fixed `design.py` (`33db74b1…`): `design.py freeze
--test-only --target-rel T` (exact) and the same with `--numerics dd+mp256 --approved-numerics-change "<ref>"
--cost-model cost_models/gmp_symmetry_amd_c8_dd+mp256.json --numerics-gate
benchmarks/symmetry_2026-10-c8/stage5/close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json` (route (b)), at T =
1e-3, 5e-4, 2.5e-4, 1.35e-4; then `production.py plan --design <bundle> --test-graphs all` with J-DES-5's sizing (gmp,
8 threads, 256 checkpoint tasks, 1.5-hour indices) and a fresh seed each, the exact plans with the exact symmetry model,
the route-(b) plans with `--numerics dd+mp256 --approved-numerics-change "<ref>"` and the profile model; none
submitted, each measured (`des5_measure.py`) and then deleted (`deleted.txt`; `plans_after.txt` lists an empty
`plans/`). Each freeze took 5-6 s.

Core-hours are the freeze's own (η_node 0.306 of the sweep, as `design.py` takes it from the ledger) and at J-SMK-4's
lane η_node 0.9146 (× 0.306 / 0.9146; the allocation does not depend on η_node, a uniform cost scale). K = 1 is the
minimum batch count everywhere:

| Target | Route | SE (target) | r: free L8 / power L8 | s: free L8 / primitives / power L8 | Core-h (freeze) | **Lane core-h** | Projection (`../stage5/pre6/`) | Plan: tasks / checkpoints / indices | Plan wall, RSS |
|---|---|---:|---|---|---:|---:|---:|---|---|
| 1e-3 | exact, F11 fixed | 44.21 (46.00) | 32 / 32 | 1 / 8 / 1 | 5,188 | **1,738** | 1,738 | 2,136,768 / 8,419 / 164 | 169 s, 0.40 GiB |
| 1e-3 | route (b) `dd+mp256` | 35.83 (46.00) | 32 / 32 | 2 / 4 / 1 | 2,756 | **923** | 678 | 2,135,328 / 8,378 / 96 | 133 s, 0.41 GiB |
| 5e-4 | exact | 22.61 (23.00) | 128 / 32 | 1 / 8 / 1 | 17,484 | **5,856** | 5,856 | 5,365,152 / 21,266 / 505 | 494 s, 0.84 GiB |
| 5e-4 | route (b) | 18.53 (23.00) | 128 / 32 | 2 / 4 / 1 | 9,919 | **3,322** | 2,298 | 5,356,224 / 21,142 / 296 | 458 s, 0.84 GiB |
| 2.5e-4 | exact | 11.31 (11.50) | 128 / 64 | 4 / 32 / 2 | 69,934 | **23,423** | 23,423 | 5,892,288 / 23,878 / 1,976 | 552 s, 0.89 GiB |
| 2.5e-4 | route (b) | 9.26 (11.50) | 128 / 64 | 8 / 16 / 2 | 39,677 | **13,289** | 9,193 | 5,666,496 / 22,547 / 1,128 | 528 s, 0.86 GiB |
| 1.35e-4 | exact | 6.08 (6.21) | 128 / 128 | 16 / 64 / 4 | 228,776 | **76,623** | 76,623 | 8,545,280 / 36,475 / 6,424 | 666 s, 1.31 GiB |
| 1.35e-4 | route (b) | 5.91 (6.21) | 128 / 128 | 16 / 64 / 4 | 101,448 | **33,978** | 30,503 | 6,664,448 / 28,372 / 2,859 | 626 s, 0.94 GiB |

- **The F11 fix on real data.** The 1e-3 freeze is the one `../stage5/pre6/` computed on the Mac (r, s and cost to
  1e-6): free L8 r = 32, the primitives s = 8, 1,738 instead of J-DES-5's 3,963 lane core-hours, at SE 44.21 instead of
  32.63 (target 46). The other three exact `design.json` files are byte-identical to J-DES-5's, and their counts are
  equal at every target (`compare_des5_<T>.json`). The 1e-3 plan is smaller too: 2.1 million tasks, 164 indices and
  9,135 projected files, against 5.2 million, 351 and 21,810.
- **Route (b) end to end.** Every route-(b) bundle records `numerics` `dd+mp256` and `profile_recost`: the approval,
  the allow-list reference, the gate 570210 (`99e42907…`, profile executable `d5df32ac…`), the exact pilot and the cost
  model `9b0dfec6…` with `executable_gated: true` (`design_meta_p6b_<T>.json`). Every route-(b) plan records
  `numerics_route` with the plan's approval, the executable `d5df32ac…` and `executable_gated: true` (`route_p6b_<T>.json`;
  the test-only plans record the check, a non-test plan enforces it). The exact plans record none.
- **Caps.** Tasks per campaign ≤ 5 × 10^7 (largest 4.46 × 10^6), checkpoints ≤ 2 × 10^5 (largest 36,475), r ≤ 128,
  predicted task seconds ≤ 120 (largest 60.0), projected merge ≤ 12 h (largest 837 s), Sobol periods, and each
  bundle's own cap record: all hold in all eight (`measure_<N>.json`, `all_caps_hold`). Route-(b) plans have 41-56%
  fewer indices than the exact ones at the same target (shorter tasks at the same 60-second task sizing).

## Finding F13 (`tools/design.py`, `optimize()`; for the Stage-6 inspection)

**What.** A route-(b) freeze re-optimizes the allocation with the profile's costs and over-delivers: SE 35.83 / 18.53 /
9.26 / 5.91 against targets 46 / 23 / 11.5 / 6.21, at ×1.74 / 1.57 / 1.57 / 1.17 its own continuous Neyman bound
(the exact path: ×1.31 / 1.10 / 1.10 / 1.05). It therefore costs **more** than keeping the exact freeze's allocation
(its counts, r and s) and only re-costing it under `dd+mp256`, which meets every target at the exact SE:

| Target | Exact freeze (SE) | Exact allocation re-costed under `dd+mp256` (SE) | Route-(b) freeze (SE) | Route (b) / kept | Continuous bound, `dd+mp256` | Route (b) with a cheapest-sufficient last step (SE) |
|---|---:|---:|---:|---:|---:|---:|
| 1e-3 | 1,738 (44.21) | **669** (44.21) | 923 (35.83) | ×1.38 | 529 | 835 (40.12) |
| 5e-4 | 5,856 (22.61) | **2,309** (22.61) | 3,322 (18.53) | ×1.44 | 2,117 | 2,968 (20.61) |
| 2.5e-4 | 23,423 (11.31) | **9,236** (11.31) | 13,289 (9.26) | ×1.44 | 8,467 | 11,874 (10.31) |
| 1.35e-4 | 76,623 (6.08) | **30,067** (6.08) | 33,978 (5.91) | ×1.13 | 29,038 | 33,640 (5.93) |

(lane core-hours on symmetry; `p6_tables.md`, third table.) The kept allocation re-costed with the measured model
(×0.385 / 0.394 / 0.394 / 0.392) confirms `../stage5/pre6/`'s gate-factor projection (678 / 2,298 / 9,193 / 30,503)
to 1.5%.

**Cause** (corrected after the pre-Stage-6 verifier's replay; the greedy loop re-run on these strata gives the same
steps). `optimize()` splits the continuous multipliers into powers of two, then doubles the `s` of the most efficient
stratum (variance removed per cost added) until the target is met. Under `dd+mp256` the split starts 2.2-9.9% short of
the target (SE 49.66 against 46 at 1e-3, 25.28 against 23 at 5e-4, 12.64 against 11.5 at 2.5e-4, 6.35 against 6.21 at
1.35e-4). At 1e-3, 5e-4 and 2.5e-4 the loop doubles free L7, power L6 and power L5 first (SE 46.26 and 23.61 after
them), then free L8, the stratum with about half the cost, which adds 48% (1e-3) and 56% (5e-4, 2.5e-4) to the design
to close a remaining gap of 0.57% (1e-3) or 2.64% (5e-4, 2.5e-4). At 1.35e-4 it doubles free L6 and then free L7
(+20%) to close a gap of 1.76%, and free L8 is not doubled. Free L8's multiplier is 1.2 r, so its power-of-two
allocation can only be r or 2r.

**Effect and options** (not changed by this run: `tools/design.py` is a pinned tool and its change belongs to Stage 6).
`../stage5/pre6/` and `docs/PERFORMANCE.md` said a route-(b) freeze "can only do better" than the kept allocation; on
this pilot it does worse by 13-44%. A cheapest-sufficient last step (take the cheapest single doubling that meets the
target) recovers 1-11% (last column) and changes the exact path by at most 0.4%. That is not the limit: the verifier's
search over doubling and halving near route (b)'s own split reaches 638 / 2,554 / 10,215 / 31,371 and a prune pass
alone 816 / 2,892 / 11,305 / 32,011, so most of the gap is the greedy loop, not the factor-2 granularity. Ways to close
it, for the host and Codex at Stage 6: (a) route (b) keeps the exact freeze's allocation and re-costs only the costs
and the chunking (the SE stays the exact bundle's); (b) freeze both and keep the cheaper design that meets the target;
(c) the cheapest-sufficient last step in `optimize()`, for both paths. With the pilot's own σ² the numbers move, but
the mechanism (a dominant, power-of-two-rounded L8 stratum) does not.

**Fixed for the Stage-6 inspection** (2026-10-05, `docs/DESIGN.md`, rule 4 and "Route (b)"): `optimize()` now searches
from both split rules with a prune pass and a bounded lattice search, and a route-(b) freeze designs both ways
(option (b)) and keeps the cheaper feasible one. On these strata (lane core-hours; `tests/test_pipeline.py`,
`jdes5_records`): exact 1,702 / 5,740 / 22,961 / 74,573; route (b) re-optimized 638 / 2,554 / 10,215 / 31,371 (the
verifier's lattice optimum); the new exact allocation kept 646 / 2,241 / 8,963 / 29,328; a freeze keeps **638 /
2,241 / 8,963 / 29,328**, every SE at its target. Confirmed on symmetry by this run's eight freezes and plans repeated
with 77fab71 (job 570302, `../pre6b/`): the same designs, every cap holds.

## Seeds

Nine fresh seeds, each checked before use against symmetry's live log with the export's `tools/seeds.py check`
(derived group seeds included) and refused by nothing: the sweep's 8928960886563889504 (added by `slurm/sweep.sh`) and
one per plan, added with a label after the plan (`p6des.570241.0/seeds_add.txt`): exact 3721479578684861521,
1930224520990376273, 9114937416079647117, 4822622752415520661; route (b) 1104217122141761050, 1203238993723355520,
6062999589438556073, 2092184474969307125.
- symmetry's log afterwards: 90 seeds (`seeds/p6_symmetry.json`, sha256 `d4c73223…`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (81 → 90, the same set;
  `seeds/sha256.txt`).
- Expanse's log: the concurrent Expanse workflow's two-log sync at 2026-10-05T19:53:52Z read exactly this symmetry log
  (`d4c73223…`) and left Expanse's log at 90 seeds, the same set (its `benchmarks/expanse_2026-10-c8/pre6/seeds/` and
  the "synced" line of `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`, that workflow's records). Nothing is pending.

## Files

`scripts/` (p6.sh, p6build.slurm, p6sweep.slurm, p6des.slurm; committed in 3a250ea before the export), `admission/`
(the `squeue` snapshot before every sbatch, the H7 lines, every sbatch line), `setup/` (the export check), `logs/`,
`sacct.txt`, `p6build.570239.0/` (identity.json, binaries, describe, build records, make logs), `p6sweep.570240.0/`
(manifest, status, calibration rows, sweep output, seed checks; `cost_model.json.sha256` for the raw model on BeeGFS),
`p6des.570241.0/` (accounting, `cost_model_install.json`, both reports, the 8 `design_*`/`design_meta_*`, `measure_*`,
`route_*`, plan outputs and gzipped plan manifests, `compare_des5_*`, `bundles.tgz` with `bundles.sha256`, seed
records; its copy of the installed model is the package's `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`),
`seeds/`, and `p6_tables.py` → `p6_tables.json`, `p6_tables.md` (Mac, seconds):

```bash
python3 -B benchmarks/symmetry_2026-10-c8/pre6/p6_tables.py --package . --sweep benchmarks/symmetry_2026-10-c8/pre6/p6sweep.570240.0 \
  --des benchmarks/symmetry_2026-10-c8/pre6/p6des.570241.0 --out benchmarks/symmetry_2026-10-c8/pre6/p6_tables.json \
  --markdown benchmarks/symmetry_2026-10-c8/pre6/p6_tables.md
```

The sweep campaign `<SCRATCH>/c8-d2/sweepdd-3a250eaa5918` (690 files) and the eight bundles in
`<SCRATCH>/c8d2/work/p6des-3a250eaa5918/bundles/` stay on BeeGFS.
