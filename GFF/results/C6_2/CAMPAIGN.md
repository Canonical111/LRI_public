# C6(2) production campaign, M = 8192 (28 September 2026)

Public record of the production behind C6(2) = 362.366 ± 0.004 (note Sections 1, 24.6 and 33). It is a rewrite of the
campaign log kept during the run, without user, node, account or archive identifiers; numbers and times are unchanged.
Times are US Pacific (PDT). Code: `GFF/code/LRI_C6_D2_HPC/` at git commit 6aaf656. Records: `GFF/data/C6_2/` (plan,
configs, merged records; the complete run directory is hosted) and `GFF/results/C6_2/C6_result.json`.

## Code and environment

- **Package.** The production copy of the package was byte-identical to git commit 6aaf656 in all 21 code files, and
  `tools/checksums.py verify` passed (1,595 listed files, 0 missing, 0 changed, 0 unlisted). The frozen plan pins the
  hashes of the five tools that planning, merging and assembly use and of `inputs/manifest.json`; all equal 6aaf656.
- **Cluster.** SDSC Expanse, shared partition, AMD EPYC 7742 nodes. Modules `cpu/0.21.2a gcc/13.3.0 boost/1.86.0`;
  Python 3.11 with numpy 1.26.4 and scipy 1.17.1 in a virtual environment.
- **Executable.** Built with `make clean && make` (`-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`,
  libquadmath): sha256 5818340b35b39430e250a254cad774e8125b6e1cfb0c070657b2ad4db6a38cf9, byte-identical to the build of
  the originally delivered sources with the same toolchain. Which Boost headers the compiler used (the module's or the
  system's) was not recorded.

## Plan

- **Command** (job 54508982, 101 s):
  `production.py plan RUN --seed 2710966291516060156 --replicates 64 --multiplier 8192 --primitive-points 65536
  --chunk-points 8388608 --threads 64 --checkpoint-tasks 1024 --shards 200`. The seed is fresh (`secrets.randbits(63)`);
  group seeds are SHA-256 hashes of (seed, campaign, loop, role).
- **Jobs.** 428 array elements of 64 threads: a_L3 0, a_L4 1, a_L5 2–13, a_L6 14–213, b_L3 214, b_L4 215,
  b_L5 216–227, b_L6 228–427.
- **Size.** 7,229,621,141,504 kernel samples; estimated 12,972 core-hours; suggested wall time 2:10:00 per element;
  projected primitive-block SE 0.00030 (frozen Neyman split).
- **Projected total SE.** About 0.0015, from Monte Carlo scaling of the archived fresh-only run (variance proportional to
  1/N, so SE proportional to 1/√N; randomized QMC may do better).
- **Code audit before the run.** All integer paths are 64-bit and the per-task accumulation is exact.

## Reporting rule (written before any production result)

1. **Primary estimate.** The frozen equal-weight a/b combination (`C6_result.json`, fields `C6` and
   `sampling_standard_error`). The bootstrap is diagnostic only.
2. **Quoted allowance.** 4 × SE, rounded up (to 0.01 as first proposed; see "Quoted value").
3. **Consistency gates**, checked and never used to tune or select:
   - campaigns a and b: |C6_a − C6_b| / √(se_a² + se_b²) ≤ 3 (otherwise report both, flag, and widen the allowance to
     cover |a − b|/2);
   - bootstrap SE within ±20% of the covariance SE;
   - agreement with the previous estimator 362.3489 ± 0.1526 (SE) within 3 of its SE;
   - C3–C5 pulls against the reference constants in `tools/assemble.py`: |pull| ≤ 4 (a larger pull is flagged,
     investigated and reported; it does not alter the C6 estimate).

## Preflight (16:47–17:07)

- **Thread identity** (job 54508994). Two throwaway plans from the same seed; one a_L6 and one b_L6 block of 1,024
  tasks each, run at 64 and at 16 threads. All 2,048 rows agree in every scientific field (`uid rep graph begin end
  total values quad mp max_abs`), including 152,717 binary128 promotions and one 300-digit promotion. Peak memory 46 MB.
  Record: `preflight/threadcheck-54508994.out`.
- **Production preflight** (element 14 = a_L6 shard 0, array 54508993). The first block (the 1,024 most expensive
  tasks) committed after 1,010 s of integration against about 1,500 s estimated; summed task-seconds 64,176, so core
  utilisation 0.993; MaxRSS 118 MB; 3.9 million binary128 and 9 300-digit promotions.

## Execution and completion

- **Release (17:13).** `slurm/resubmit.sh --mem=8G` excluded the running element 14 and submitted the other 427 indices
  as one array (`0-13,15-427%64`); the merge job (`slurm/merge.sh`) ran `afterok` on that array and on element 14. The
  per-user cap of 64 concurrent jobs on the shared partition limited the campaign to 64 elements at a time.
- **Launch failures.** Four array tasks (a_L6 shards) failed at launch on the node side before writing any log. Slurm
  requeued and held them; they were released with `scontrol release` and ran later. Nothing had run, so nothing was
  repeated or lost.
- **Element times.** a_L6 26–28 min, a_L5 about 40 min; element 14 took 25:54.
- **Completion (20:43).** All 428 elements and the merge completed; 996 of 996 checkpoint blocks; no failure logs.
  Wall time 16:48–20:43 including the preflight; 12,535 core-hours billed against 12,972 estimated (the native
  integration time recorded in the merged records is 12,467 core-hours).

## Result

| | C6(2) | Sampling SE |
|---|---:|---:|
| Campaign a | 362.366720219382 | 0.000975607 |
| Campaign b | 362.36622330813486 | 0.001267465 |
| Combined (frozen equal weights) | **362.36647176375726** | **0.0007997306822612242** |

Error by loop: L3 5.2e-6, L4 1.13e-4, L5 3.65e-4, L6 7.02e-4 (L6 includes the ten recomputed primitive kernels); no
shared retained input. The realized SE is about half the projected 0.0015; a single comparison does not determine a
convergence rate, and the replicate covariance, not the projection, is reported.

## Checks against the rule

| Check | Value | Gate | Outcome |
|---|---|---|---|
| Campaigns a and b | 362.366720 ± 0.000976 vs 362.366223 ± 0.001267, pull 0.31 | ≤ 3 | pass |
| Bootstrap SE (4,096 resamples) / covariance SE | 0.00080124 / 0.00079973 = 1.002; bootstrap mean − estimate −1.3e-5 | within ±20% | pass |
| Previous estimator 362.3489 ± 0.1526 | pull 0.12 | ≤ 3 | pass |
| C3 | −0.87485005169 ± 4.0e-8 vs −0.87485001265, pull −0.97 | ≤ 4 | pass |
| C4 | 5.0488639843 ± 2.9e-6 vs 5.0488684314, pull −1.54 | ≤ 4 | pass |
| C5 | −38.833726187 ± 7.5e-5 vs −38.833645896, pull −1.07 | ≤ 4 | pass |

A later, independent cross-check: the seventh-order production (`GFF/results/C7_2/C7_result.json`), which integrates
the power sector explicitly instead of using the analytic compensation, gives C6(2) = 362.3727456 ± 0.0085778 as a
by-product, +0.73 combined standard errors from this estimate. It shares the graph and renormalization framework.

## Quoted value

4 × SE = 0.0032. Rounded up to 0.01 as first proposed, this gives 362.37 ± 0.01. On 1 October 2026 the author chose to
round up to a multiple of 0.001 instead: **C6(2) = 362.366 ± 0.004**. Note Section 24.6 states that the four-SE rule
was fixed before the result and the rounding step refined afterwards. Scope: sampling uncertainty only; the retained
analytic power-sector compensation and the finite-kernel framework are outside this campaign.

## Re-assembly and its precision

The campaign log recorded that a re-assembly of the copied run "reproduces C6 and SE bit for bit". Re-checked for the
release (13 October 2026): the merge step (`tools/production.py merge`) sums the checkpoint rows as decimal strings at
50 digits and reproduces every `merged.json` and `graph_replicates.csv` byte for byte. The assembly step
(`tools/assemble.py`) is float64 numpy; on other numpy builds it reproduces the result to about 1e-15 relative, not bit
for bit (with numpy 1.24 and 1.26 on macOS, C6 is identical and the SE differs in the last bit). `make -f public.mk
replay` uses the tolerances stated in `GFF/code/LRI_C6_D2_HPC/public/replay.py`.

## Code defects found later (29 September 2026)

The three-dimensional sibling package's review found four defects of the submission and merge layer that 6aaf656 shares:
no per-campaign submission lock; a concurrent merge can crash while writing `merged.json`; the SQLite URI is not escaped
(`#`, `?`, `%` in the path); `%` in the campaign path is expanded in Slurm `--output`. This campaign is not affected:
its path contains none of those characters, the submissions were sequential (one window, then one resubmission), and
exactly one merge ran. A new campaign with this code should submit once at a time, run one merge, and use a plain path.

## Archive and review

The complete campaign tree (the run directory and the thread-check runs; 1,524 files, 421 MB) was archived on 29 September 2026 in two
independent copies, each verified file by file (size and MD5). The release hosts the run directory without its Slurm
logs (`GFF/data/C6_2/DATA.md`). An independent results review (OpenAI Codex, gpt-6-astra) approved the result and its
write-up in the note in its second round on 1 October 2026 (`GFF/code/LRI_C6_D2_HPC/REVIEWS.md`).
