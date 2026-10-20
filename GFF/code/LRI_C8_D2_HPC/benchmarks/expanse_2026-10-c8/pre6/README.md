# Expanse items before Stage 6 (2026-10-05): seed-log sync DONE; J-EXP-1 rerun PARTIAL (Lustre incident)

**Site rule** (user, 2026-10-05): "symmetry is back, so for the moment only use expanse if symmetry is not enough".
This workflow used Expanse only for its own two items: the two-log seed sync and the J-EXP-1 rerun (A-EXP-3). It ran
no other compute there. symmetry was only read: `cat` of its seed log and one `squeue`; nothing was written there.
No other site was used.

Every step goes through `scripts/p6x.sh`, run from the Mac. It uses the existing ControlMaster only, and every
session uses `-o BatchMode=yes`, so no login was opened. The steps are:
- `export`: one `git archive`, checked file by file;
- `seeds X`: Expanse-side merge with the export's `tools/seeds.py merge`, then a three-set check;
- `exp1 X`: the H7E-R admission on a fresh `squeue -A <ACCOUNT>`, then sbatch of the committed
  `stage5/fix/scripts/fxe_exp1.slurm` from the export;
- `harvest X ID`: copies the results back here.

## The export (one new export)

- **Export.** `$C8_DATA/pkg/99bbfddd0719`, the `git archive` of c8 head **99bbfdd**. That head includes the design
  agent's 23540b2 (F11, route (b)) and 99bbfdd (docs).
- **Check.** `../setup/export_check_99bbfddd0719.json`: 8,268 files equal to the archive, with no content or mode
  mismatch and no special file.
- **Later commits.** 3a250ea, the symmetry agent's job scripts, was committed after the export. It changes no code.
- **Lustre usage** (`admission/lfs_quota.txt`): 1,488,683 files before the export and 1,497,745 after, against a
  limit of 2,000,000.
- **No export was deleted.**

The export now holds this job's `bin/` and `build/` and the two hard-linked L8 packs. `fxe_exp1.slurm` refuses an
export that already has `bin/` or `build/`, so a rerun needs a fresh export of the head current at that time (see
"Owed").

## 1. The two-log seed sync: DONE

Three passes ran. Each pass read symmetry's log with `cat`, copied it to `$C8_DATA/work/p6x-seeds/` with a matching
sha256, and merged it into Expanse's log with the export's `tools/seeds.py merge`. The merge holds the log's lock,
appends only and removes or reorders nothing. The copies are in `seeds/`, the sha256 values in `seeds/sha256.txt`,
and each pass's check in `seeds/check_<ts>.json`.

**Pass 1, 18:43 UTC.**

| Log | Entries / distinct seeds | sha256 |
|---|---|---|
| symmetry `<SCRATCH>/c8-d2/forbidden_seeds.json` | 81 / 81 | `a0029b1f…` |
| Expanse `$C8_DATA/forbidden_seeds.json`, before | 78 / 78 | `65a577ef…` |
| Expanse, after (`"added": 3`) | 81 / 81 | `401af676…` |
| mirror `designs/forbidden_seeds.json` (99bbfdd) | 81 / 81 | `49cc4da6…` |

- The three seeds of `../../symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` were added:
  3225605224505469430, 7953283644819727315 and 3934799973789933184.
- After the merge, Expanse, symmetry and the mirror held the **same set of 81 seeds**. No seed was lost.
- The files' bytes differ: the layouts differ and merged entries carry `merged_from`/`merged_utc`. The sets are
  equal.

**Pass 2, 19:52 UTC.** It picked up the symmetry agent's pre-Stage-6 seeds, which were added on symmetry after
pass 1:
- `sweepdd-3a250eaa5918` (8928960886563889504);
- seven J-DES-5 re-check test plans (3721479578684861521, 1930224520990376273, 9114937416079647117,
  4822622752415520661, 1104217122141761050, 1203238993723355520, 6062999589438556073).

These 8 were merged into Expanse's log (`"added": 8`). Expanse and symmetry then held **the same 89 seeds**
(symmetry `e3afb8a4…`, Expanse `c1091d17…`). The mirror still held 81. The symmetry agent adds its seeds to the mirror
in its own commit, so this workflow did not change `designs/forbidden_seeds.json`.

The final state at the commit of this folder is in the section "Final seed state" below.

## 2. The J-EXP-1 rerun (A-EXP-3): PARTIAL, cancelled during `make test` because Expanse's Lustre was failing

**Before submitting.**
- **Allocation:** active (`admission/expanse_client_*.txt`): 22,080,000 SU, 52,011 spent, valid until 2027-09-30.
- **Scheduler:** not in maintenance any more. There was no system-wide reservation (`scontrol show res`), and C63d's
  compute jobs had been running since 10:47 PDT.
- **Debug nodes:** both were drained by Bright's Lustre client check, which had drained many nodes at 11:31 PDT:
  - <NODE>: "lfs check: error: check 'expanse-OST0023-osc…': Input/output error";
  - <NODE>: the same error for OST0011, then "Lustre df is hung" at 12:05.
- **Survey:** `admission/survey_expanse_*.txt`.
- **H7E-R:** admitted (`admission/h7e_r_admission.jsonl`). With the new job: 1 c8d2 node, 1 c8d2 normal-QOS job, and
  2 running normal-QOS jobs on the account.

**Submission.** Job **54681003**, `c8d2-p6x-exp1`, submitted at 11:43:54 PDT (`admission/submitted.txt`):
`-A <ACCOUNT> -p debug -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
--exclude=<NODE>`.
- The time limit is **00:30:00, not 00:40:00**: the debug partition's MaxTime is 30 min. A longer request would pend
  forever with reason PartitionTimeLimit. 30 min is also the plan's J-EXP-1 line.
- The job pended while both debug nodes were drained. It started at 12:30:24 PDT on <NODE>, after that node was
  resumed.

**What it did** (`fxeexp1.54681003.0/`, `logs/c8d2-p6x-exp1_54681003.out`):
- **L8 packs: PASS.** Both packs of `pkg/7aac898add43` were re-hashed against the export's `inputs/manifest.json`
  (free `e5dd7271…`, power `3d77d0c4…`; equal) and then hard-linked.
- **Build: PASS.** `make && make gmp`, `make c7ref` and `make inspect` all succeeded.
- **A-RPL-8: PASS** (`identity.json`). The executables are byte-identical to the final default build:

  | Executable | sha256 |
  |---|---|
  | `bin/c8d2_decimal` | **`99a51c1d…`** |
  | `bin/c8d2_gmp` | **`1d2a2181…`** |
  | `bin/c8d2_inspect` | `63c194fd…` |
  | `bin/ref/c7d2_decimal` | `4537dcfd…` |
  | `bin/ref/c7d2_gmp` | `6c829386…` |

- **A-EXP-1 part: PASS.** `BOOST_LIB_VERSION` is `1_77` in all four build records. The node was an AMD EPYC 7742
  running GCC 13.3.0 (Spack). `env_expanse.sh` is `6f85cb50…`.
- **`tests/check_venv.py --strict`: PASS** (F2 on Expanse). numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0,
  pytest 9.1.1.
- **`make test`: started at 12:37:56 and did not finish.**
  - `validate.py` (the J-VAL-1 subset): **passed**. Parts: describe, bad_inputs, replay, invariance, inspector,
    class_b, diagnostics (`test/validate.json`).
  - `check_venv`: passed.
  - `unit_orchestration.py`: 12 groups PASS, then it stalled in `test_bootstrap_export`. That test copies the
    package tree off Lustre (`export_copy`, `shutil.copytree`). On the node it sat in state I at 5.7 % CPU, and its
    rchar grew by about 66 KB/s while it read `reference/LRI_C7_d2_progress/inputs/L6/G460.txt`.
  - The groups F1 (`lanes`, whole-node affinity), F3 (`f2_profile`) and F4 (`sanitize --capture-check`) and the
    commands after `unit_orchestration` were **not reached**.

**Why it was cancelled.** Expanse's Lustre was failing on the compute nodes during the run.
- The build took **430 s against 33 s** in Stage 5's J-EXP-1 (54676864: the same build commands, on the same node, <NODE>).
- `validate.py` took about 100 s against 71 s.
- At 12:51 PDT about 9 minutes of the 30-minute limit were left. The rest of `make test` takes about 15 minutes even
  at Stage-5 speed (Stage 5's command-by-command timings, 54676898), so the job could not finish in time.
- **It was cancelled at 12:51:14 PDT** (`sacct.txt`: CANCELLED, 20:50 elapsed) instead of being left to run into
  TIMEOUT. That saved about 20 SU.
- Afterwards <NODE> was drained again, for OST0008 I/O errors. <NODE> was draining for OST0005, and 653 nodes
  had a Lustre drain reason (`admission/lustre_state_after_job.txt`).

**Cost.** 1,250 s × 128 cores = **44.4 SU**. The workflow budget was 40 SU. The overrun comes from the slow build
under the Lustre fault, and an exclusive node bills 128 core-hours per hour. No other Expanse job ran.

**Verdict for A-EXP-3 (J-EXP-1).**
- The build half of J-EXP-1 passes on the current head: A-RPL-8 and Boost 1.77.
- The `make test` half is **still owed**: F1, F3 and F4 on Expanse's whole node with GCC 13.3.
- symmetry's whole-node J-VAL-1 passed F1-F4 in 570165 and 570211 (`make test` exit 0, export 68ee571). Since
  68ee571, only 23540b2 has changed code: `tools/design.py`, `tools/production.py`, `tools/sweep.py` and
  `tests/test_pipeline.py` (F11 and route (b)). It touched neither `src/` nor the test groups of F1-F4.
- The G5 re-check treats an open A-EXP-3 as a gap the plan allows (failure mode 23). It does not block symmetry or
  Stage 6.

## Owed on Expanse

**`make test` of J-EXP-1, once Lustre is healthy again.** Check that `sinfo -p debug` shows the debug nodes idle with
no Lustre drain reason. Then, from the head current at that time:

```
bash benchmarks/expanse_2026-10-c8/pre6/scripts/p6x.sh export
bash benchmarks/expanse_2026-10-c8/pre6/scripts/p6x.sh exp1 $C8_DATA/pkg/<sha12>
```

- Expected wall time is about 20 min, which is about 43 SU.
- `pkg/99bbfddd0719` cannot be reused as it is (its `bin/` and `build/` exist), and it is not deleted here.
- Any seed added on symmetry after the final pass below also needs `p6x.sh seeds <export>` before any plan on Expanse.

## Final seed state (pass 3, 19:53:52 UTC; `seeds/check_20261005T195346Z.json`)

Pass 3 ran after the symmetry agent's jobs had ended (it had no live `c8d2-` job at 15:53 EDT). It merged the one
seed added since pass 2: 2092184474969307125, the J-DES-5 re-check's route (b) plan at 1.35e-4.

| Log | Entries / distinct seeds | Bytes | sha256 |
|---|---|---:|---|
| symmetry | 90 / 90 | 27,189 | `d4c732233045c2b6b61f6470e6226074385c185e3ca143e8fe7585498a453aa9` |
| Expanse | 90 / 90 | 23,115 | `e8efb7661390350cf45a99257b83a3ca6734f801e9bbed55f7f8284f2ffed31d` |
| mirror `designs/forbidden_seeds.json` (99bbfdd) | 81 / 81 | 29,027 | `49cc4da6eb4f4e40be422b1e823777ebd7e20453b0da5a7f1f99d9c450dafab3` |

- **Expanse and symmetry are the same set of 90 seeds.** No seed was lost in any pass, and all three
  PENDING_EXPANSE_SYNC seeds are in Expanse's log.
- **The mirror lacks exactly the symmetry agent's 9 pre-Stage-6 seeds:** 8928960886563889504, 3721479578684861521,
  1930224520990376273, 9114937416079647117, 4822622752415520661, 1104217122141761050, 1203238993723355520,
  6062999589438556073 and 2092184474969307125. The symmetry agent mirrors them with its evidence commit
  (`tools/seeds.py merge` of symmetry's log into `designs/forbidden_seeds.json`). The mirror has no seed that either
  log lacks.
- `../../symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` is marked synced.

## Files

| Path | Content |
|---|---|
| `scripts/p6x.sh` | The Mac driver (export, seeds, exp1, harvest) |
| `admission/` | Survey, allocation, `lfs quota`, the squeue snapshot and H7E-R record, the sbatch line, the Lustre state after the job |
| `seeds/` | Copies of the logs before and after each pass, the merge outputs, the checks and the sha256 values |
| `fxeexp1.54681003.0/` | The job's evidence directory: pack check, build log and records, identity, check_venv, the partial `make_test.log`, `test/validate.json` and `test/check_venv.json` |
| `logs/c8d2-p6x-exp1_54681003.out` | The Slurm log |
| `sacct.txt` | `sacct -j 54681003 --duplicates` |
