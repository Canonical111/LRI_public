# Stage-5 close-out on symmetry (2026-10-05): F12 on real Slurm, J-VAL-1, the dd+mp256 J-FLAG gate

Site rule: symmetry only (user, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry is not
enough"). Expanse was not touched. Everything ran from the git-archive export of **68ee571ee614**
(`<SCRATCH>/c8d2/pkg/68ee571ee614`; `setup/export_check_68ee571ee614.json`: 8,140 files equal to the
archive). 68ee571 is the F12-fixed head 08e728a (tools d5dfd38) plus this folder's job scripts (`scripts/`), so its
`tools/`, `src/` and `tests/` are 08e728a's. The L8 packs were re-hashed against the export's `inputs/manifest.json` and
hard-linked from `pkg/7a8aad783c31/inputs/packs` (`clbuild.570208.0/l8_packs.json`). The A-ORC-13 run, the plan and
J-VAL-1 reuse the fix round's committed scripts `../fix/scripts/{fxplan,fxio,fxval1}.slurm` unchanged, from this export.

(`aperf5.json`, `aperf5_table.md` and `aperf5_table.py` in this folder are the A-PERF-5 cost table of the earlier
Stage-5 close-out, d8f9305; they are unrelated to the jobs below.)

## Verdicts

| Item | Job | Verdict |
|---|---|---|
| Build, A-RPL-8 | 570208 | **PASS.** Every default and diagnostic executable is byte-identical to the Stage-5 symmetry build of 5d7586e (decimal `619ddf7d…`, gmp `2cc5e88e…`, prof, ratiohist, inspect, c7ref `e696d7f3…`/`7e3c8c92…`, quad differential and ranges, interleave probe); the two sanitizer builds equal 5d7586e's once the export path and the GNU build-id are normalized (32 differing bytes each, as in the fix round). `make gmp NUMERICS=dd,mp256` built `bin/c8d2_gmp_dd+mp256` **`d5df32ac…`** and left every default executable unchanged; `--describe`: numerics `dd+mp256`, not diagnostic, no development override, no stub; the build record says NUMERICS `dd+mp256`, no parameter override. Boost 1.77 everywhere. |
| **A-ORC-13 real Slurm** (F9, F12) | plan 570209, run 570212 | **PASS, with no replay correction.** `tools/claim_io.py` exit 0 on all 22 claims. |
| **J-VAL-1** on the fixed tools | 570211 | **PASS.** `make test` exit 0 (1,349 s); unit_orchestration 41 groups / 53 tests, 0 failed, including `pack_reads`' Linux rchar check. |
| **dd+mp256 J-FLAG gate** (A-FLAG-3 F1-F5) | 570210 | **PASS** at full scale (`"status": "passed"`, no development option): F1, F2, F4 rows, F5 all true; F4 speedup **×2.530** on symmetry. |

## Jobs

`sacct -X --duplicates` (`sacct.txt`, queried 13:16 EDT; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC:
64 cores, 1 thread per core; the Intel sharedq node: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-`
jobs on amdq + amddebugq + amdpreq; the peak was 3 (570210, 570211, 570212 from 12:54:24 to 13:05:56;
`admission/h7_admission.jsonl`). amdq/amddebugq with `--exclude=cn112`; no longq; sharedq `--no-requeue`; every job
with `--mem` and `--time`. Every job started at once on idle nodes (survey before each sbatch:
`admission/squeue_before_*.txt`). Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/68ee571ee614/<run>/` (copies here, without the two large files listed in
`large_files.sha256`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570208 | build (`scripts/clbuild.slurm`) | amddebugq <NODE> (EPYC 7543) | COMPLETED | 1:24 | 1.49 |
| 570209 | plan of the A-ORC-13 campaign (`fix/scripts/fxplan.slurm`) | sharedq <NODE> | COMPLETED | 0:32 | 0.04 |
| 570210 | dd+mp256 J-FLAG gate (`scripts/clflag.slurm`) | amdq <NODE> (EPYC 7543) | COMPLETED | 12:24 | 13.23 |
| 570211 | J-VAL-1 (`fix/scripts/fxval1.slurm`) | amdq <NODE> (EPYC 7543) | COMPLETED | 22:46 | 24.28 |
| 570212 | A-ORC-13 claim_io run (`fix/scripts/fxio.slurm`) | amddebugq <NODE> (EPYC 7532) | COMPLETED | 15:06 | 16.11 |
| **total** | 5 records | | | | **55.1** |

## A-ORC-13 on real Slurm with the F12 fix (F9, F12)

Campaign `<SCRATCH>/c8-d2/io-68ee571ee614`, planned (job 570209) with exactly the arguments of the fix round's
`io-2b3a9233353d` and a **fresh seed 3934799973789933184** (62 indices, 143,580 tasks, the same index numbering;
`campaigns/io-68ee571ee614/manifest.json`). `scripts/slots.py` picked the same 22 claims by (group, shard) as job 570170:
six b_free_L8 indices (38-43), a_free_L8 (6), and 15 indices of the L3-L6 groups, in J-SMK-4's lane shape (8 NUMA
slots of 8 cores, `production.py run --index I --threads 8`); all 22 exited 0 (`fxio.570212.0/slots.txt`). The campaign
is a test campaign and is never merged; its first claim pinned it to AuthenticAMD on <NODE>
(`campaigns/io-68ee571ee614/cpu_vendor.json`).

`tools/claim_io.py` (`fxio.570212.0/claim_io.json`): 22 records, all schema `c8-d2-claim-io-2` (`pack_reads`: exact 22,
buffered 0), `fingerprint_bytes` identical in all 22 (7,006,591, one key), smallest group a_free_L3 (24,576-byte
tasks.sqlite) against the largest b_free_L8 (2,117,632 bytes, ×86.2):

| Variant | a_free_L3 | b_free_L8 (6 runs) | Largest difference | Tolerance | |
|---|---:|---:|---:|---:|---|
| non-own bytes | 29,851,289 | 30,306,139-30,306,535 | 455,246 | 2,985,129 | pass |
| without the fingerprint (bytes) | 22,844,698 | 23,299,548-23,299,944 | 455,246 | 2,284,470 | pass |
| without the fingerprint (rchar) | 22,809,397 | 23,264,247-23,264,643 | 455,246 | 2,280,940 | pass |

**Verdict: pass (exit 0), with no replay correction.** All 22 runs lie within 29.85-30.31 MB of non-own bytes. In the
fix round (tools of 2b3a923, job 570170) the same claims gave 29.8 MB against 701.3-705.8 MB (a_free_L8 648.2 MB) and
passed only after the replayed over-read was subtracted. Per b_free_L8 claim, rchar fell from 2,610,311,346 to
1,939,323,495 bytes (−671 MB, the over-read that `../fix/scripts/claim_io_overread.py` predicted), while the claim's own
staged-member bytes (953,253,897) and the native rchar (953,986,210, 1.0008 bytes per staged byte; a_free_L8 1.0011)
are unchanged. The claim process now reads 1.034 bytes per staged byte apart from the native, which is its constant
non-own reads; before the fix it read 1.74.

Node note: amddebugq placed this run on <NODE>, an EPYC 7532 (Zen 2, family 23); the fix round's run was on <NODE>, an
EPYC 7543 (Zen 3, family 25). The L8 claims took 852-905 s here against 763-805 s there; this is the node, not the read
path (the claim reads 671 MB less). Both are AuthenticAMD, so the F5 vendor pin allows both; AMD Zen 2 and Zen 3 rows
agree (J-SWEEP-3's AMD control, `docs/HPC.md`).

## J-VAL-1 on the F12-fixed tools (570211)

The fix round's `fxval1.slurm`, unchanged, on a whole amdq node (numpy 2.3.5, pytest 9.1.1): `tests/check_venv.py
--strict` passes; `make test OUTPUT=…` exits 0 in 1,349 s as one command (validate, check_venv, unit_orchestration,
test_pipeline, ast_scan, test_regress, merge_scale, check_vendored 16/16, vendored_isolated 10/10 `--in-place`, the
delivery-verifier test, check_inputs 10/10, test_profiling, test_gmp_prefix, test_numerics_flags 8/8, test_dd_profile,
sanitize `--capture-check`, workflow, staging); then `assembly_checks.py --exact` 37/37, `verify_result_tamper.py`
69/69 and `compat_2026.py` exit 0; executables unchanged by `make test`. unit_orchestration ran **41 groups / 53 tests,
0 failed**, on Linux with the real worker. Its F12 test `pack_reads` (30 members, 3,748,335 bytes): 30 `os.pread`
calls (929 with short reads), bytes read = member bytes, and **on Linux rchar across `stage_graphs` = 3,748,335 = the
member bytes** (a default `open()` over the same members read 3,809,280 with the node-local file system's 4,096-byte
`st_blksize`; the 512 KiB buffered control read 8,388,608, as the over-read model predicts). The F5 (`cpu_vendor`), F7
(`lane_worker_sigterm`: 0.04 s and 3.23 s), `staging`, `claim` and `claim_io` tests pass. Records: `fxval1.570211.0/`
(`exits.txt`, `make_test.log`, `test/*.json`).

## The dd+mp256 J-FLAG gate (570210)

The gate the user required before the first production use of dd+mp256 (user check-in 2026-10-05: "dd+mp256 approved
for production after the pilot (C62d PLAN-REVIEW-LOG)"; no exp1). One whole amdq node, <NODE> (2 × EPYC 7543, 64
cores, 8 NUMA nodes), Ubuntu GCC 11.4.0, Boost 1.77, GMP 6.2.1. `tests/numerics_flags.py --profile dd+mp256 --seeds-log
$C8_SEEDS` at full scale; the exact binary `bin/c8d2_gmp` `2cc5e88e…` and the profile `bin/c8d2_gmp_dd+mp256`
`d5df32ac…` were checked against the build before and after (`clflag.570210.0/{before,after}.sha256`: identity ok).
Wall 743 s. Record: `clflag.570210.0/jflag_dd+mp256/numerics_flags.json`.

- **Seeds.** F2 uses the gates' fixed base seed 820262401; its 49 seeds were all already in symmetry's log ("0 added, 49
  present"; the record's `log_sha256_after` is `0983419e…`, the log as it was before the gate; the later `a0029b1f…`
  in `seeds_log_after.sha256` is the A-ORC-13 plan's add, below). Nothing to sync.
- **F1 baseline** (computed in the run on this node): 153,600 points with 450-digit references, need met without
  doubling (`f1_baseline/baseline.json`; the four reference files stay on BeeGFS, sha256 in `large_files.sha256`).
- **F1: pass.** 0 violations, 0 failed profile checks; per tier (points, max relative error against 450 digits): long
  double 57,582 (5.06e-10), **dd 70,620 (5.18e-12)**, binary128 9,289 (1.43e-11), **mp256 16,097 (1.02e-19)**, mp350
  12 (4.61e-20); 115,157 points identical to the exact path's value, the rest within 5.18e-12; transitions binary128 →
  dd 70,620, binary128 → binary128 9,289, mp350 → mp256 16,097, mp350 → mp350 12, long double unchanged; dd's F1
  checks (96,018 points forced out of range and through the product guard) pass.
- **F2: pass.** 193,384 tasks per binary (every L3-L8 graph, campaigns a and b, 4 replicates × 256 points), 8 × 8
  NUMA-aligned lanes, no replicate doubling, 505 s. Total |dC8| + 3 SE_d = **4.25e-16** (dC8 1.31e-16, SE_d 9.77e-17)
  against 0.062; per (sector, L ≥ 7): free L7 0, free L8 0, power L7 3.46e-16, power L8 1.81e-16; the nonlinear dC8
  of the full assembly at the two loop means 1.31e-16 (a cross-check of the linear map). Per task: 192,545 of 193,384
  identical, max normalized difference **5.58e-14** against 1e-9. Projected to 2^21 points per graph: 1.38e-16.
- **F3.** Promotion fractions unchanged in every (campaign, sector, L) (quad and mp changes 0); the tier split is F1's.
- **F4 (speed, informational; rows pass).** The L8 sweep sample (2,000 graphs, 2 × 512 points), 3 interleaved repeats
  of each binary in 8 × 8 lanes, median lane-thread seconds: exact 1,329.5 (free 950.1, power 378.3), profile 525.4
  (free 382.3, power 143.1): **×2.530 total (free ×2.485, power ×2.644)**. Each binary's rows identical across its
  repeats. F2's integration-only task seconds give ×2.68-×3.39 per (campaign, sector, L ≥ 7).
- **F5: pass.** Rows identical at 1, 8, 16, 64 threads and as 8 × 8 lanes (L8 free and power blocks).

**Same numbers as Expanse.** The F1 record (totals, tiers, paired differences, profile checks), the F2 record (gates,
totals, per-task statistics, nonlinear dC8, projection) and F3's counters equal Stage 4c's dd+mp256+exp1 record on
Expanse (GCC 13.3, EPYC 7742; `../../../expanse_2026-10-c8/stage4c/gate/s4cgate.54673902.0/`) field by field, apart
from exp1's own seven F1 counters, which this build does not have; F2 also equals Stage 4c's dd record. The speedup is site-dependent (F10): ×2.530 here (GCC 11.4,
EPYC 7543) against ×2.168 for dd+mp256+exp1 on Expanse (exp1 is inert). In lane-thread seconds the exact binary is
slower here (1,329.5 against 1,206.6) and the profile faster (525.4 against 556.6); the cause was not investigated.

## Seeds

One new seed, checked before use against the mirror and symmetry's live log (`tools/seeds.py check`: not forbidden,
derived group seeds included; symmetry's log holds Expanse's log as of the last two-log sync, and nothing ran on Expanse
since), added to symmetry's log by the plan job (`seeds.py add`): **3934799973789933184** (campaign
`io-68ee571ee614`). The mirror `designs/forbidden_seeds.json` was merged from symmetry's log after the add
(`seeds/cl_symmetry.json`, 81 entries, equal seed sets; sha256 in `seeds/sha256.txt`). Expanse's log does not yet hold
it: it is appended to `../fix/seeds/PENDING_EXPANSE_SYNC.txt` for the owed two-log sync. The gate added no seed.

## Files

`scripts/` (cl.sh, clbuild.slurm, clflag.slurm, slots.py; committed in 68ee571 before the export), `admission/`
(the `squeue` snapshot before every sbatch, the H7 lines, every sbatch), `setup/`, `logs/`, `sacct.txt`,
`clbuild.570208.0/` (identity.json, binaries, describe, build records, make logs), `clflag.570210.0/` (the gate record
and its f1/f2/f4/f5 records, the F1 baseline's baseline.json and nets), `fxval1.570211.0/`, `fxio.570212.0/` (index
logs, claim_io.json, slots.txt), `campaigns/io-68ee571ee614/` (manifest, vendor pin), `seeds/`, `large_files.sha256`
(F2's `rows.csv.gz` and the four F1 reference files, which stay on BeeGFS).
