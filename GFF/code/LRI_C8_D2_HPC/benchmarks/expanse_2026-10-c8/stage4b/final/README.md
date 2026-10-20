# Stage 4b G4b on Expanse: the final J-VAL-2 and J-VAL-3 on the final default binary (branch `c8`, 2026-10-04)

The plan's G4b (PLAN.md, Stage 4b) asks for A-PERF-2 and A-RPL-1..7 exact on the final default binary, through a rerun
of J-VAL-2 and J-VAL-3. A-PERF-2 is the integration's (`../integration/`). This folder holds the reruns. Every gate
passed. Results and the Stage-4b summary are in `docs/PERFORMANCE.md`, "Stage 4b: default-path optimizations".
`scripts/summarize_final.py` recomputes the verdicts and numbers below from the records here into
`final_summary.json`. It also compares every record with its Stage-3 counterpart on the Stage-3 baseline.

**Commit under test.** b47b008: the integration's final head a2ef0a2 plus these job scripts. `src/` and the Makefile
are unchanged since the final candidate e7ef98d, and `src/` equals d46e736's (+R5 +R3a). The export is
`$C8_DATA/pkg/b47b0082c0f7`, and `../../setup/export_check_b47b0082c0f7.json` records it equal to `git archive`
(6,363 files). Before linking, the build job re-hashed the two L8 packs of the c17688158e2b export against the export's
`inputs/manifest.json` (`g4bbuild.54672150.0/l8_packs.json`: free `e5dd7271…`, power `3d77d0c4…`, equal). `make` then
re-hashed every pack again.

**Environment.** `~/c8d2/env_expanse.sh` `6f85cb50…` (recorded by every job), Spack GCC 13.3.0, Spack GMP 6.2.1, Boost
1.77 headers. All nodes are 2 × AMD EPYC 7742.

**Executables** (`g4bbuild.54672150.0/binaries.sha256`; `identity.json`: every one byte-identical to e7ef98d's build
54672108):

| Executable | sha256 |
|---|---|
| `bin/c8d2_decimal` | `99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf` |
| `bin/c8d2_gmp` | `1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa` |
| `bin/c8d2_gmp_prof`, `bin/c8d2_gmp_ratiohist` | `f338a547…`, `5d0b7c97…` |
| `bin/c8d2_inspect` | `63c194fd…` |
| `bin/ref/c7d2_decimal`, `bin/ref/c7d2_gmp` (`make c7ref`) | `4537dcfd…`, `6c829386…` (as in Stage 3) |
| `bin/c8d2_quad_differential`, `bin/c8d2_quad_ranges` | `3db26f74…`, `3d87f79c…` |
| `bin/baseline/c8d2_decimal`, `bin/baseline/c8d2_gmp` (Stage-3 copies, checked) | `3dbd51bb…`, `5c5328af…` |

**Scripts** (`scripts/`).
- `submit_final.sh` is the Mac driver. It makes the export and its check. Before every sbatch it runs H7E-R
  (`../../stage4a/scripts/h7_admit.py` on a fresh `squeue -A <ACCOUNT>`) and this workflow's own limit: at most 4 compute
  nodes and 8 shared jobs named `c8d2-g4b-*`.
- `final_build.slurm` does the pack re-hash, the builds (`make`, `make gmp inspect`, `make profile ratiohist`, `make
  c7ref`, `make quaddiff`), the Stage-3 baseline copies and the identity check.
- `g4b_val2.slurm` is J-VAL-2, exactly the plan's `make test-full OUTPUT=…`. The executables' sha256 are recorded
  before and after, and they are unchanged.
- `g4b_val3.slurm` is J-VAL-3 plus G-L8SELF and the quad differential. It refuses an unregistered L=2 seed.
- `summarize_final.py` writes `final_summary.json`.

**Admission records** (`admission/`): the H7E-R line before every sbatch (`h7e_r_admission.jsonl`), the squeue
snapshots, `submitted.txt`, the `lfs quota` lines before and after, and `sacct_g4b.txt`. The account had no running
normal-QOS job other than these, and every job started at once.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54672150 `c8d2-g4b-build` | `shared` 16 CPUs, 32 GB, <NODE>, 0:51 | Every executable built from scratch in the export (42 s) and byte-identical to the final candidate's build. The L8 packs equal the manifest. | `g4bbuild.54672150.0/` |
| 54672151 `c8d2-g4b-val2` | `compute` exclusive, <NODE>, 4:06 | **J-VAL-2 (`make test-full`) passed.** See below. | `g4bval2.54672151.0/` (`val2/` holds the records) |
| 54672152 `c8d2-g4b-val3` | `compute` exclusive, <NODE>, 14:26 | **J-VAL-3, G-L8SELF and the quad differential passed.** See below. | `g4bval3.54672152.0/` |

The Slurm logs are in `logs/`. Staged graphs, native outputs and temporary trees stayed on node-local
`/scratch/$USER/job_<id>`.

**J-VAL-2 (54672151): `make test-full`, 245 s.**
- **`validate.py --full`** passed every part: describe, 28 refusals, replay, invariance, inspector, class B and the
  diagnostic builds.
  - The replay covers the L=2 graph and all 3,773 L3–L7 kernels (3,774 in all) on both backends, at 2 × 64 points,
    seed 7738251. It used rate .8 with layout 0, and at L7 also rates .8/.9 with layouts 0/1/2.
  - **G-C7 (A-RPL-2) is exact** against `make c7ref` in all 39,048 rows per backend. That includes 22,212 rows with
    mp > 0, 1,074,943 binary128 points and 111,112 MP points.
  - **G-REF (A-RPL-1) is exact:** 7,548 rows per backend. Gmp is exact also in its 4,121 rows with mp > 0, where the
    rule allows 1e-30.
  - **G-JET (A-RPL-3) is exact:** 39,048 rows per backend, with the new slot finite.
  - **Chunks and layouts (A-RPL-6):** 24 cases. Chunks agree with whole tasks to at most 2.1e-18 normalized (the bound
    is 1e-12).
- **`check_points.py`:** 172 checks per backend on 43 kernels at L3–L8. The largest scaled MP error is 2.1e-353
  (gmp350) and 1.8e-302 (decimal300), against the bound 1e-280.
- **`check_inputs.py`:** 10/10 checks passed, with 2 skipped (the git-only C7(2) member check and the regeneration from
  `inventory8_d2`, as in J-VAL-1).
- **`workflow.py` and `staging.py`** passed with the real workers.

**J-VAL-3 (54672152).**
- **A-IN-6(b), the L=2 control:** passed, 3 s. It uses the registered Stage-3 seed `7082694491065029298` (`seeds.py
  check`: forbidden, i.e. in the log), so no new seed was drawn or registered. Rates .8 and .9, 32 replicates × 2^16
  points, both backends. The largest pull is 1.22, against the bound of 4 SE. The worst row gap is 1.1e-19 and the worst
  replicate gap 4.8e-20, against 2^-60.
- **A-RPL-6, thread identity:** identical at 1, 8, 16 and 64 threads and as 8 lanes × 8 threads. That holds for free
  and power L8 blocks of 64 tasks × 256 points, on both backends, 121 s.
- **A-RPL-4, G-BK8:** L7 and L8, 400 kernels per sector, 2 × 256 points, 26 s. Decimal against gmp gives identical
  counters and exact values in every row, including the 2,779 rows with mp > 0 (96,064 MP points).
- **A-RPL-7, G-L8SELF:** the L8 sweep sample (1,600 free and 400 power kernels, 2 × 512 points), 149 s. It is exact
  against the Stage-3 baseline in every scientific field on both backends. Each backend has 3,200 + 800 rows, 762,395
  + 359,972 binary128 points and 114,648 + 99,884 MP points.
- **A-RPL-5, forced tiers:** passed, 120 s. Per sector the sample is 200 L7 kernels × 256 points and 400 L8 kernels × 64
  points, with no doubling needed.
  - free: 29,284 points accepted in binary128 and 3,541 MP points; power: 50,625 and 12,568.
  - (a) Long-double accepted: |f − f450| ≤ 3.3e-18·err_ld. Binary128 accepted: ≤ 1.05e-33·err_q.
  - (b) MP: ≤ 1.3e-352 (gmp350) and ≤ 3.7e-313 (decimal300).
  - (c) Zero decision mismatches.
- **R3a's proof on this build, `quad_differential.py`:** passed, 27 s at 128 threads.
  - 2^32 random pairs per operation, of which 4,286,346,880 / 4,286,350,062 / 3,849,357,005 took the fast path for
    add / sub / mul.
  - Edge lists of 901,761 / 901,761 / 1,350,672 pairs.
  - The injection self-test detected its flipped results, and the ASan+UBSan run was clean.
  - 0 mismatches everywhere.
- **A-ORC-6, merge scale** (`merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16`): passed, 402 s.
  - 1,249,792 rows in 16 shards. The parallel merge is byte-identical to the serial one.
  - Peak RSS is 37.8 MiB per merge process and 68.4 MiB serial (bound 1 GB).
  - Phase 1 runs at 618,874 rows/s (16 processes), phase 2 at 81,516 rows/s.
  - The 500-shard cases (RLIMIT_NOFILE 48 with 3 passes, `--fan-in 2` with 9 passes) are byte-identical, and
    RLIMIT_NOFILE 33 is refused.
  - The 4 → 32-point memory section grows RSS by 0.49 MiB in 1 shard and in 4.
- **A-ASM-4, `assembly_checks.py --exact`** (cluster part): 37/37 checks, 15 s. That includes the 33 exact keys of
  `exact_check.py` and its 6 float diagnostics. The verdict is the same as on the Mac and in Stage 2b/3b.

**Against Stage 3** (`final_summary.json`, "vs_stage3"). The same tests on the Stage-3 baseline are jobs 54637263 and
54637264. After removing run-specific fields (seconds, environment, commands and paths, the executables' digests),
every compared record is equal: `validate_full` (50 tests), `point_checks`, `l2_control`, `bk8`, `thread_identity`,
`forced_tiers` and `l8self`. Two exceptions are not compared. The inspector tests changed in the checkpoint review:
`inspector_order_key` became `inspector_execution_order` (T-04), and `inspector_private_tempdir` is new (CK-K03). Both
passed here. So the final default binary reproduces Stage 3's validation records number for number, including the
L=2 control's means and pulls and the forced-tier error maxima.

**Allocation.** 39.77 SU in all (`admission/sacct_g4b.txt`): build 0.23 (`shared`, the larger of 16 CPUs and 32 GB/1.95
GB, for 51 s), J-VAL-2 8.75 and J-VAL-3 30.79 (`compute`, 128 SU per node-hour). At most 2 compute nodes and 1 shared
job of this workflow were live at a time. No job is still live.

**Lustre.** <USER> went from 1,312,567 to 1,319,443 files, a count shared with C63d's session. Nearly all of the 6,876
new files are the export (6,363) and its builds.
