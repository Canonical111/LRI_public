# Slurm layer for lri_1d_c5_exact (symmetry)

Adapted from the Codex-inspected C4P layer (`lri_1d_c4_exact/slurm/`). Every safety property of that layer is kept;
the C5 changes are listed at the end. Data root `C5_DATA=<SCRATCH>/lri_1d_c5`, job-name prefix `l1c5-`.

| file | role |
|---|---|
| `env.sh` | module `anaconda3/2023.07-2`, stack check (python 3.11.4, numpy 1.24.3, scipy 1.10.1, numba 0.57.0), thread variables = 1, the pinned A6e reference (`C5_C4REF`, `C5_C4REF_SHA256`), socket helpers `c5_numa S` / `c5_cores S` |
| `validate.slurm` | the validation job (one node): tests, A1–A3, closed forms, Λmax = 80 and 160 runs, gates, `PASS` |
| `bench.slurm` | benchmark job (A7a): `run5.py bench` on socket 0, writes `bench_L<L>.json` |
| `node.slurm` | one node of a run: two socket-bound `run5.py run` drivers |
| `assemble.slurm` | assembly + gates A4, A5, A6d, A6e; writes the result and the gate record |
| `submit.sh` | the only entry point: gated, mutex-serialised submission from the login node |

## Deploy (read-only snapshot)
```bash
# on the Mac, from a committed tree (commit = short sha)
git -C ~/Documents/<PROJECT>/lri_1d_c5_exact archive --format=tar --prefix=<commit>/ <commit> \
  | ssh symmetry 'mkdir -p ~/lri_1d_c5 && tar -x -C ~/lri_1d_c5 && chmod -R a-w ~/lri_1d_c5/<commit>'
ssh symmetry 'cd ~/lri_1d_c5/<commit> && bash slurm/submit.sh validate'
```
`submit.sh` refuses a writable snapshot. Every job re-computes `python run5.py sha --kind snapshot` on its node and
stops (exit 64) if it differs from the sha computed at submission (`C5_EXPECT_SHA`).

## Commands
```bash
slurm/submit.sh validate                        [partition]   # env: C5_VAL_WPS (2), C5_VAL_BLOCK (8), C5_VAL_TIME (12:00:00)
slurm/submit.sh bench   LMAX "THREADS..."       [partition]   # env: C5_TASKS ("worst"), C5_BLOCK (8), C5_TIME (08:00:00)
slurm/submit.sh assemble LMAX                   [partition]   # recovery: re-run a rung's assembly (orphan result moved aside)
slurm/submit.sh prod    LMAX NNODES WPS BLOCK   [partition]   # env: C5_TIME (24:00:00), C5_ASM_PART, C5_ASM_TIME (04:00:00), C5_BENCH_L
```
Partition: default `amdq` when it has idle nodes outside active reservations, else `defq`; an explicit partition must
be one of `amdq amddebugq largememq defq debugq longq` (whole-node, non-preemptible: all jobs are `--no-requeue`).
`--mem` 245G (AMD), 180G (Intel), 370G (largememq); `debugq`/`amddebugq` cap the time at 1 h. `C5_ASM_PART` puts the
assembly job on another allowed partition (the C4 assembly once waited behind a full amdq). Each branch prints a
survey line (idle unreserved nodes vs nodes needed: start now or queue) and the log paths.

## Records (all bound to the full snapshot sha `<sha>`; `<sha12>` = its first 12 hex digits)
| path under `$C5_DATA` | written by | content |
|---|---|---|
| `validation/<sha>/PASS` | validate.slurm (atomic) | `PASS <date> job <id> snapshot_sha <sha>`, checks, run configuration, both gate records |
| `validation/<sha>/{pytest,v1,v3,v7}.txt`, `gates.txt` | validate.slurm | step outputs |
| `validation/<sha>/A9_APPROVED` | the coordinator, by hand | must contain `snapshot_sha <sha>` (or `snapshot_sha=<sha>`) with the full sha; states any uninspected fix round |
| `validation/<sha>/bench_L<L>.json` | bench.slurm (atomic, merged) | `snapshot_sha, Lmax, host, partition, peak_rss_GB, jobs[], runs[]` (per run: task, threads, block, seconds, `peak_rss_GB` = max of run5's getrusage and `/usr/bin/time -v`, both kept) |
| `results/<sha12>/c5_1d_L<L>.npz` | assemble.slurm (temporary name, then rename) | result (INTERFACES.md schema) |
| `results/<sha12>/gates_L<L>.txt` | assemble.slurm (atomic) | gate record, below |
| `results/<sha12>/gatelogs_L<L>/<gate>.txt` | assemble.slurm | validator outputs |
| `cache_L<L>_<numerics sha12>/` | node.slurm (`run5.py run`) | task checkpoints (reused after a TIMEOUT) |

Gate record:
```
snapshot_sha <sha>
result <path> sha256 <sha256>
PASS A4                         # validate/v4_ht.py RESULT; "SKIP A4 (...)" when Lmax < 118
PASS A5                         # validate/v5_windows.py RESULT; "SKIP A5 (...)" when Lmax < 152
PASS A6d_<prev>_vs_<L> prev_sha256=<..> cur_sha256=<..>    # validate/v6_overlap.py PREV RESULT
PASS A6e c4ref_sha256=<..> cur_sha256=<..>                  # validate/v6_overlap.py --c4ref RESULT --c4npz $C5_C4REF
```
A6d is PASS only if the validator passes, the previous result is the file named in its own gate record, and both
sha256 values appear in the validator's output. A6e is FAIL unless `$C5_C4REF` exists with the pinned sha256
`62720cf5…` (C4P `results/a8b57b2e8475/c4_1d_L2000.npz`); it is passed as `--c4npz` (the validator's default is a
Mac path) and both sha256 must appear in the validator's output.

## Gates
* **validate**: refused if `validation/<sha>/PASS` exists (remove it by hand to re-validate) or `l1c5-validate` is
  live, or if the A6e reference is missing/changed. The job runs, bound to socket 0 and stopping at the first failure:
  `C5T_SLOW=1 pytest -q validate/test_*.py`, `v1_exact.py`, `v3_brute.py --cut4max 128`, `v7_closed.py --Lmax 2000`,
  then node + assembly at Λmax = 80 (A6e) and 160 (A4, A5, A6d_80_vs_160, A6e). `PASS` needs both gate records of
  this snapshot without FAIL and with every listed PASS line.
* **bench**: needs `validation/<sha>/PRELIM` (A1–A3, A6a–c; written by the validation job) or `PASS`; no checkpoints,
  no results; one live `l1c5-bench-L<L>` per Λmax (the record is merged); default task: run5.py's designated
  worst-case task (`run5.py worstspec --Lmax L`), the only runs that count for the sizing.
* **assemble** (recovery): same gates as prod except the sizing; refused while the rung's jobs are live or its gate
  record exists; an orphan result (published by an interrupted assembly without its gate record) is moved to
  `results/<sha12>/orphan/` after checking that its provenance names this snapshot. The assembly runs every gate on
  a pending file and publishes the result and then the gate record, each by an atomic rename.
* **prod** `LMAX ∈ {240, 320, 400, 500}`: `PASS`, `A9_APPROVED`, the previous rung's gate record
  (240 ← `gates_L160` A6d_80_vs_160; 320 ← `gates_L240` A6d_160_vs_240; 400 ← `gates_L320` A6d_240_vs_320;
  500 ← `gates_L400` A6d_320_vs_400) with this snapshot's sha, no FAIL, PASS A4, A5, A6e (pinned reference) and the
  A6d line whose two sha256 equal the result files on disk; no result/gate record for LMAX yet; no live
  `l1c5-L<L>` / `l1c5-L<L>-asm`; and the memory sizing below. The array (`l1c5-L<L>`, one task per node) is followed
  by `l1c5-L<L>-asm` (`afterok`, `--kill-on-invalid-dep=yes`) with `C5_PREV` = previous rung.
* **sizing** (prod): runs of the designated worst-case task only (worst_case true, spec_sha = `run5.py worstspec
  --Lmax Lb`), from the record `bench_L<Lb>.json` of this snapshot with `Lb ≥ LMAX`, by default the largest such `Lb`
  (`C5_BENCH_L` selects another); `peak` = max `peak_rss_GB` over its runs with `block ≥ BLOCK`; refused unless
  `2 × WPS × peak ≤ 0.85 × node memory` (Intel 191, AMD 256, largememq 384; RSS in GiB). The submitter prints the
  record, peak, need, limit and the largest admissible WPS; it warns if the threads per worker exceed the benchmarked
  ones.

## Jobs and logs
* `l1c5-validate`: `$C5_DATA/logs/l1c5-validate_<job>.out`; per-part `logs/run_L{80,160}_<job>/part{0,1}.log`.
* `l1c5-bench-L<L>`: `logs/l1c5-bench-L<L>_<job>.out` (run5 JSON lines + `time -v` RSS).
* `l1c5-L<L>`: `logs/l1c5-L<L>_<array>_<i>.out`; per-part `logs/run_L<L>_<array>/part<k>.log` (part = 2·node +
  socket; `/usr/bin/time -v` at the end); `l1c5-L<L>-asm`: `logs/l1c5-L<L>-asm_<job>.out`.
* node layout: per socket one `run5.py run` driver under `numactl --cpunodebind=<NUMA domains of the package>
  --membind=<same>` with WPS workers × (physical cores of the package / WPS) threads (Intel 20, AMD 32 cores per
  package; AMD packages are four NUMA domains). No OMP_PROC_BIND (several workers share one socket's cpuset).
* Resume after a TIMEOUT or node failure: the assembly is cancelled by `--kill-on-invalid-dep`; resubmit the same
  `prod` line (checkpoints in `cache_L<L>_<numerics sha12>` are validated and reused).

## Changes relative to the C4P layer
C5 names and paths; ladder 80/160 (validation) → 240 → 320 → 400 → 500 with A9 + PASS + benchmark record for every
rung; gate A6e (pinned C4P reference) at every assembly; explicit required-gate lists (C4 checked only "no FAIL" and
the A6d line); A6d bound to the previous rung's own gate record and to the validator's printed sha256; result
written under a temporary name; validators, tests and assembly bound to socket 0 (C4: 20 unbound threads); sizing
check from the benchmark record; benchmark record merged atomically; partition whitelist and reservation-aware amdq
pick; survey line; validation refuses an existing PASS; both sockets sized before either driver starts.
