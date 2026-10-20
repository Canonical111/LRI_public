# G5 fixes re-validated on symmetry (2026-10-05)

The fix branch `fix-g5` (86e15f4: F1-F9 and the A-PERF-4 calibration, no `src/` change) was merged into `c8` as
e7e6589; the job scripts of this folder are 2b3a923. Everything below ran from the git-archive export of
**2b3a9233353d** (`<SCRATCH>/c8d2/pkg/2b3a9233353d`, `setup/export_check_2b3a9233353d.json`: 7,932 files
equal to the archive) on the **exact default path**: no `--numerics`, no `--rates`, no `GMP_PREFIX`, no compiler flag
override. The L8 packs were re-hashed against the export's `inputs/manifest.json` and hard-linked from
`pkg/7a8aad783c31/inputs/packs` (`fxbuild.570164.0/l8_packs.json`).

**Verdict.** F1, F2, F3 (J-VAL-1), F4 (J-VAL-4), F5 (vendor refusal), F6 (login-node verification), F7 (J-DRL-1
cleanup) and F8 (J-DRL-8, unattended) PASS on real Slurm. **F9 is PARTIAL:** every claim now logs its `claim_io` line
and `fingerprint_bytes` is identical in all 22 runs, but `tools/claim_io.py` still FAILS the plan's comparison (22.8
MB against 694-699 MB). The cause is new and exactly quantified (**F12**, below): `production.stage_graphs` reads the
pack through Python's default buffer, which on BeeGFS is the 512 KiB `st_blksize`, so a claim reads about 0.70 bytes
of neighbouring pack data per staged byte at L8. The native worker reads its staged files exactly once (native rchar
per staged byte 1.0008), so the fix round's "the native re-reads its staged files" explanation was wrong. With the
over-read replayed and subtracted, the comparison passes (0.98 MB against a 2.23 MB tolerance). F12 needed a `tools/`
change, left to Stage 6; it is fixed in d5dfd38 (below), and the real-Slurm rerun with the fixed tools is owed.

## Jobs

`sacct -X --duplicates` (`sacct.txt`, queried 12:17 EDT; times below are EDT, the cluster's clock); core-hours =
ElapsedRaw x physical cores (AMD EPYC: 64 cores, 1 thread per core; the Intel sharedq nodes: 2 threads per core, so
AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on amdq + amddebugq + amdpreq at any time (the peak, 4, was reached
twice: 11:40:03-11:40:11, fxval1, fxio, the twin's first worker and its pending merge until that merge was cancelled,
and from 11:52, fxval1, fxio and the twin restart's worker and merge; `admission/h7_admission.jsonl` and the
`C8: admission` lines of `drl1/submit*.out`); amdq/amddebugq always `--exclude=cn112`; no longq; sharedq
`--no-requeue`. Logs: manual jobs `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); lane workers and
merges `<campaign>/slurm_logs/` (copies in `campaigns/` and `drl1/`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570164 | build (`fxbuild.slurm`) | amddebugq <NODE> | FAILED (3; see below) | 1:06 | 1.17 |
| 570165 | J-VAL-1 (`fxval1.slurm`) | amdq <NODE> | COMPLETED | 15:43 | 16.76 |
| 570166 | J-VAL-4 (`fxval4.slurm`) | sharedq <NODE> | COMPLETED | 11:16 | 0.75 |
| 570167 | plan, restart twin | sharedq <NODE> | COMPLETED | 0:32 | 0.04 |
| 570168 | plan, A-ORC-13 campaign | sharedq <NODE> | COMPLETED | 0:36 | 0.04 |
| 570169 | plan, J-DRL-8 drill drR | sharedq <NODE> | COMPLETED | 0:47 | 0.05 |
| 570170 | A-ORC-13 claim_io run (`fxio.slurm`) | amddebugq <NODE> | FAILED (1 = claim_io.py fail, F12) | 13:25 | 14.31 |
| 570172 | J-DRL-1 twin worker (scancelled after 10:00) | amdq <NODE> | CANCELLED by 70850 | 10:00 | 10.67 |
| 570173 | its merge (cancelled while pending, as in Stage 5) | amdq | CANCELLED | 0 | 0 |
| 570175, 570176 | J-DRL-8 drR worker and merge (complete the campaign) | sharedq <NODE> | COMPLETED | 0:43, 0:06 | 0.01 |
| 570178, 570179 | J-DRL-8 recovery worker and merge (unattended) | sharedq <NODE> | COMPLETED | 0:01, 0:06 | 0.00 |
| 570182 | J-DRL-1 restart worker | amdq <NODE> | COMPLETED | 9:48 | 10.45 |
| 570183 | J-DRL-1 merge | amdq <NODE> | COMPLETED | 0:06 | 0.11 |
| 570184 | F5 vendor refusal (`fxvendor.slurm`) | sharedq <NODE> (Intel) | COMPLETED | 0:02 | 0.00 |
| **total** | 16 records | | | | **54.4** |

Job 570164 exited 3 only because its identity check compared the sanitizer builds byte for byte: every production
and diagnostic executable is byte-identical to the Stage-5 build of 5d7586e (decimal `619ddf7d…`, gmp `2cc5e88e…`,
prof, ratiohist, inspect, c7ref `e696d7f3…`/`7e3c8c92…`, quad differential and ranges, interleave probe), and the two
sanitizer builds differ in 32 bytes: the absolute build directory, which ASan embeds once, and the GNU build-id that
follows from it. They are equal once both are normalized (`fxbuild.570164.0/sanitizer_identity.json`). No job depended
on 570164's exit status; the later jobs were submitted after this check.

## Items

| Item (finding) | Job(s) | Verdict | Evidence |
|---|---|---|---|
| **J-VAL-1** (F1, F2, F3; A-ASM-1 cluster part) | 570165, a whole amdq node (64 cores, numpy 2.3.5) | **PASS.** `tests/check_venv.py --strict` passes (pytest 9.1.1 ≥ 7). `make test OUTPUT=…` exits 0 in 926 s as one command: validate, check_venv, unit_orchestration 40 groups / 52 tests with 0 failed (test_lanes pinned to 16 CPUs; on the Linux paths `lane_worker_sigterm…_F7` stops in 0.04 s and 3.23 s, `cpu_vendor…_F5`, `claim_io…`, `recovery_of_a_completed_index…_F8`, and the A-ORC-13 spy with the real worker), test_pipeline, ast_scan, test_regress, merge_scale, check_vendored, vendored_isolated `--in-place`, the delivery-verifier test, check_inputs, test_profiling, test_gmp_prefix, test_numerics_flags 8/8, test_dd_profile, sanitize `--capture-check`, workflow and staging. Then on the final commit: `assembly_checks.py --exact` (A-ASM-4 cluster part), `verify_result_tamper.py` and `compat_2026.py` exit 0. Executables unchanged. | `fxval1.570165.0/` (`exits.txt`, `make_test.log`, `test/*.json`) |
| **J-VAL-4** (F4; A-KER-4) | 570166 sharedq (Intel 6148, GCC 11.4) | **PASS.** `tests/sanitize.py --selftest`: 144 sanitizer worker runs and the 2 point-check builds clean; the three self-test probes abort with their reports captured on the pty: glibcxx `Assertion` (`/usr/include/c++/11/array:188`), ASan stack-buffer-overflow, UBSan signed overflow. `--capture-check`: the probe's report is lost on a pipe and seen on the pty. | `fxval4.570166.0/sanitize.json` |
| **J-DRL-1** (F7; A-ORC-8a) | 570172 (scancel at 10:00), 570182, 570183 | **PASS.** The twin of the Stage-5 smoke, re-planned from the new export with the smoke's arguments and seed 7170939708808771305 (the plan is identical to the smoke's: 29 indices with the same task-file pins, the same groups, cost model and executable; only the four changed tool hashes differ). Worker with `TMPDIR` on BeeGFS so the login node can see its scratch: before the cancel 8 `c8d2_lane_570172_*` directories, each with its `c8d2_runtime_*`, 464,559,525 bytes; **30 s and 60 s after `scancel`: nothing left (0 bytes)**. The worker log: "SIGTERM forwarded to 8 lane(s)", every lane "index … stopped by signal 15 (run exit 143); claim left for release-stale … scratch removed", lane exit codes 143 x 8; the 8 index logs say "run: stopped by signal 15; native work stopped, job-private runtime removed". 8 claims stale, no failure record. `submit.sh --lanes 1` released the 8 stale claims and finished: **all 24 merged.json batches bitwise equal to the Stage-5 smoke's** (planned with the earlier tools), `graph_replicates.csv` and `graph_tails.csv` byte-identical; checkpoints 23 from the cancelled job, 133 from the restart; status 0; the result differs from the smoke's only in `merged_sha256` and `source_manifest_sha256` (new tool pins). | `drl1/` (`before_cancel.txt`, `after_cancel_30s.txt`, `after_cancel_60s.txt`, `worker_log_tail.txt`, `drl1_twin_compare.json`, `submit1.out`, `submit2.out`, the lane and merge logs) |
| **J-DRL-8** (F8; A-ORC-12) | 570175/570176, then 570178/570179 | **PASS, unattended.** Drill drR (2-thread test plan, 96 indices, seed 7953283644819727315, sharedq drill mode) completed with its merge and assembly; copies kept of the 24 merged.json, index 17's checkpoint (`a_free_L7/s000001_p000000.json`) and the result; that checkpoint and `a_free_L7/merged.json` deleted; `submit.sh --lanes 1` (no manual step after it). The queue rebuild logged index 17 in `lanes/done_invalidated.jsonl`; the lane recomputed it (job 570178; scientific fields equal); **merge job 570179 COMPLETED**: "a_free_L7: replaced the uncommitted graph_costs.csv (no merged.json; … timing only)" and assemble "superseded: scientific content unchanged, merged_sha256 changed for a_free_L7; previous result kept as C8_test_result.superseded.8a8fd8ed8a26.json" (byte-equal to the saved result; the new result differs only at `/merged_sha256/a_free_L7`); **all 24 batches bitwise equal to the saved ones**; status 0; `verify_result.py` passes. | `drl8/` (`drl8_verdict.json`, `merge-570179.log`, `sums_after.txt`, `sacct.txt`), `drl8_saved/` |
| **F6** (A-SMK-1 verification) | login node <NODE> (Xeon Silver 4214R, AVX-512) | **PASS.** The new `verify_result.py` verifies the Stage-5 smoke result (assembled on AMD) and its twin on the login node (`verified: true`, 0 problems); the Stage-5 tool on the same node still reports the original `linear_response_residual[8]: 1.8189894035458565e-12 differs from the recomputed 8.640199666842818e-12`. The J-DRL-1 twin's and drR's results also verify on the login node. | `fxf6.login/` |
| **F5** (one CPU vendor per campaign) | 570184 sharedq (Intel 6148) on the A-ORC-13 campaign, pinned to AuthenticAMD by its first claim (index 6 on <NODE>, job 570170) | **PASS.** `production.py run --index 49` (an index never run) exits **64** before any block, naming both vendors ("this node (<NODE>) has CPU vendor GenuineIntel …, but the campaign's first claim (index 6 on <NODE>) ran on AuthenticAMD …"); `lanes.py worker` exits **64** before any claim; every file of the campaign unchanged (size and mtime); `status` prints "cpu vendor: AuthenticAMD …, pinned by the first claim (index 6 on <NODE>)". The drR drill (sharedq) is pinned GenuineIntel by its own first claim, and the twin AuthenticAMD. | `fxvendor.570184.0/vendor_refusal.json`, `campaigns/*/cpu_vendor.json` |
| **A-ORC-13 real Slurm** (F9, R07) | 570170, one amddebugq node | **PARTIAL (finding F12).** Campaign `io-2b3a9233353d`: J-SMK-4's plan arguments with seed 3225605224505469430 (62 indices, 143,580 tasks, 75.8 core-h if run in full). Run here: **22 claims, 13.4 min of one node (14.3 core-h)**, in J-SMK-4's lane shape (8 NUMA slots of 8 cores, `production.py run --index I --threads 8`): six b_free_L8 indices (38-43), one a_free_L8 (6), and 15 indices of the L3-L6 groups. Every run logged `claim_io`; `fingerprint_bytes` = 7,007,827 in all 22 (one fingerprint key). `tools/claim_io.py` (smallest group a_free_L3, 24,576-byte tasks.sqlite, against the largest b_free_L8, 2,117,632 bytes, ×86.2): non_own_bytes 29.8 MB against 701.3-705.8 MB, and 22.8 MB against 694.3-698.7 MB without the fingerprint (tolerance 2.28 MB): **fail (exit 1)**. Cause (F12) and the corrected comparison below. | `fxio.570170.0/` (`logs/idx*.log`, `claim_io.json`, `claim_io_overread.json`, `slots.txt`) |

## F12 (new): the pack reads in `stage_graphs` over-read by Python's buffer

`production.stage_graphs` stages each block's graph members with `open(pack,'rb')`, `f.seek(offset)`,
`f.read(length)`. Python sizes that file's buffer from the file system's `st_blksize`, which is 524,288 bytes on
BeeGFS (`os.stat(...).st_blksize`, both L6 and L8 packs). After a seek outside the buffer, `read(length)` reads the
whole buffer blocks of `length` directly and then refills one 512 KiB buffer, so the claim process reads up to 512 KiB
of neighbouring pack data per non-adjacent member. Those bytes are pack data read for the claim's own members, but
`_own('staged_members', …)` counts only the member lengths, so they land in `non_own_bytes`.

`scripts/claim_io_overread.py` replays CPython's BufferedReader seek and read rules over every block's sorted members
(inventory offsets and lengths, the export's own `job_rows` and `blocks_of_rows`) and predicts the over-read per run:
6.71e8-6.75e8 bytes per b_free_L8 index, 6.18e8 for a_free_L8, 6.1e7-6.3e7 for free L6, 4.2e6 for power L6, 0.4-1.5e6 at
L3-L5. Subtracted from the measured values, the non-own bytes of all 22 runs lie in 20.7-23.3 MB (without the
fingerprint's rchar), and the plan's comparison passes in all three variants: smallest 22.28 MB against largest
23.26 MB, difference 0.98 MB against a tolerance of 2.23 MB (`claim_io_overread.json`, `corrected_passed: true`).
The measured native rchar is 1.0008 (b_free_L8) and 1.0011 (a_free_L8) bytes per staged byte: the native reads its
staged copies once.

Suggested fix (a `tools/production.py` change, Stage 6): open the pack unbuffered (`buffering=0`, which reads exactly
`length` bytes per member) or count the bytes the buffered reader actually reads as own data; then rerun this
`fxio.slurm` subset (about 15 core-h) and `tools/claim_io.py`. The over-read also costs I/O: about 0.7 GB of extra
BeeGFS reads per L8 index, 1.7 times the members' bytes.

**Fixed in d5dfd38 (Mac; `docs/HPC.md`, "F12").** `stage_graphs` now reads each member with
`production.read_member` (`os.pread` in a loop over short reads, no Python buffer), so a claim reads exactly its
members' bytes; `stage_runtime.py`'s member copy reads the same way; the staged bytes and their sha256 checks are
unchanged; the claim's own staged-member bytes are the bytes read, and its `claim_io` record has schema
`c8-d2-claim-io-2` (the 22 records here are `c8-d2-claim-io-1`, which `tools/claim_io.py` now names as buffered). Mac
evidence: `benchmarks/mac_2026-10-c8/f12fix/`. **Done on symmetry (2026-10-05, `../close/`):** this A-ORC-13 run
repeated with the fixed tools (export 68ee571ee614, campaign `io-68ee571ee614` with a fresh seed, job 570212) PASSES
`tools/claim_io.py` with no correction (29.85 MB against 30.31 MB), and J-VAL-1 on that export (job 570211) passes.

## Seeds

Two new seeds, each checked before use against symmetry's log (which holds every seed of Expanse's log as of the last
two-log sync, `../seeds/06_des5_expanse.json`, 14:09 UTC; the live Expanse log could not be read, see below) and the
mirror, then added to symmetry's log by its plan job (`seeds.py add`): 3225605224505469430 (A-ORC-13 campaign `io-2b3a9233353d`) and
7953283644819727315 (drill `drills-2b3a9233353d/drR`). The restart twin reuses the smoke's seed 7170939708808771305
by design (logged since J-SMK-1). The mirror `designs/forbidden_seeds.json` holds both. **Expanse's log does not yet
hold them:** Expanse's Lustre stopped answering on the login node during this workflow (`../../../expanse_2026-10-c8/stage5/fix/README.md`),
so the two-log sync is owed (`../scripts/seedsync.sh` once Expanse answers). Both seeds are listed for that sync in
`seeds/PENDING_EXPANSE_SYNC.txt`; `seeds/fx_symmetry.json` is symmetry's log after the two adds (80 entries).

## Files

`scripts/` (the job scripts as exported, plus `drl1_cancel.sh` and `claim_io_overread.py`, written after the export:
the latter was uploaded to `<SCRATCH>/c8d2/work/fx-2b3a9233353d/` with its sha256 in
`admission/submitted.txt`), `admission/` (an `squeue` snapshot before every manual sbatch, the H7 lines, every sbatch
and scancel), `setup/`, `logs/`, one folder per job, `drl1/`, `drl8/`, `drl8_saved/`, `fxf6.login/`, `campaigns/`
(manifests, vendor pins, Slurm logs and results of the three campaigns). The campaigns themselves stay on BeeGFS under
`<SCRATCH>/c8-d2/` (`smoke1-20261005-twin-2b3a92`, `io-2b3a9233353d`, `drills-2b3a9233353d/drR`).
