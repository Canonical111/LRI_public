# C7(2) production, 2026-09-30: campaign log

Public rewrite of the production log kept by the Claude Code session (C62d) that ran the campaign. User names, scratch
paths, host names and archive locations are left out; Slurm job numbers are kept because the evidence files name them.

## Code and plan of action

- **Code.** `LRI_C7_D2_HPC` as delivered on 2026-09-30, committed unchanged as git commit `fb64c47` (`verify_delivery
  --strict`: 4,405 payload files). Exported here as `GFF/code/LRI_C7_D2_HPC`.
- **Parallel track (user decision).** The production ran with the unchanged delivered code while a multi-agent review of
  the same code ran (see `REVIEWS.md` in the package). The result was to be kept only if the review cleared the numerics;
  it did (no critical or high finding).
- **Cluster.** An attempt on another cluster the same day was not scheduled in time (its jobs never left the queue apart
  from a few light shards) and was cancelled; none of its data enter the result. Its pilot (M = 1, R = 8, gmp, 64 threads)
  supplied the per-graph cost model that the production used for task placement only (`cost_model.json`, sha256
  `e4ecf4b3…`). The production ran on the symmetry cluster of the Perimeter Institute.

## Environment and build (Slurm job 566254, one AMD EPYC 7532 node, 64 physical cores)

- System GCC 11.4, the cluster's Boost 1.77 module (headers only), system GMP 6.2.1, Python 3.11 venv with numpy 2.3.5,
  scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0.
- Binaries: `bin/c7d2_decimal` sha256 `e696d7f3…`, `bin/c7d2_gmp` sha256 `7e3c8c92…24df5` (used for the production;
  `--describe`: gmp350, 372 maximal digits).
- All seven delivered test suites passed: validate (20 s), validate --full over all 3,511 graph kernels against the
  original executable for both backends (123 s), check_points (450-digit references, 43 s), workflow (13 s), staging (4 s),
  reassemble_reference (3 s), delivery verifier (1 s). Records: `evidence/buildtest-566254/`, summary
  `evidence/buildtest-566254.out`.
- Thread identity: the seven-loop groups run at 64 and at 16 threads gave 5,776 identical rows (0 mismatches),
  including 31,663 promotions to the GMP tier.

## Plan (job 566257)

`tools/production.py plan RUN --seed 8885400701634497064 --backend gmp --replicates 64 --multiplier 4096
--primitive-mode recompute --primitive-points 16384 --shards 64 --threads 64 --checkpoint-tasks 1024
--chunk-points 1048576 --cost-model <pilot cost model>`: 20 groups (campaigns a and b, power-free and power sectors,
loops 3-7), 1,280 work indices, 1,094,688,178,176 kernel samples. Plan wall time 23 s. The frozen plan is
`GFF/data/C7_2/run1-20260930-m4096/manifest.json` (sha256 `968799a4…`).

## Execution

- 28 whole-node worker jobs (566259-566286), 14 on AMD nodes (one 64-thread lane each) and 14 on Intel nodes (two
  socket-bound 20-thread lanes each), 24 h limit. Lanes claimed work indices heaviest first with an atomic directory
  claim and ran the package's own `production.py run`. Scripts: `GFF/code/LRI_C7_D2_HPC/public/slurm/` (paths replaced by
  variables).
- All 1,280 indices and 2,048/2,048 checkpoint blocks completed, with no failed claim. The node jobs ran 6.4-6.6 h each
  (14:22 to about 20:50 EDT); 8,892 task core-hours (about 11,500 estimated at plan time).
- Merge and assembly job 566287: all 20 group merges succeeded; the job then exited 1 on a bug in the wrapper (a stray
  `grep` under `set -e`), not in the package or the data. The assembly was rerun as job 566530
  (`tools/assemble.py RUN --bootstrap 4096`, 4.8 s). The wrapper was fixed on 2026-10-01; `public/slurm/merge.slurm` is
  the fixed version.

## Result (2026-09-30 21:05 EDT)

| Quantity | Estimate | Sampling SE |
|---|---:|---:|
| C7(2) | -3876.1260927949925 | 0.52445 |
| power-free part | -3876.0701 | 0.5225 |
| power correction | -0.05603 | 0.04586 |
| campaign a | -3875.320 | 0.727 |
| campaign b | -3876.932 | 0.757 |
| half streams | -3876.489, -3875.763 | |

Error by loop (in units of C7): power-free L7 0.519, power L7 0.044, power-free L6 0.059; everything else below 0.02.
The SE projected from the pilot was about 0.7.

Provenance of `C7_result.json`: written by `tools/assemble.py --bootstrap 4096` in job 566530 (COMPLETED, binary
`7e3c8c92…`), schema `c7-d2-hpc-result-1`, `test_only` false, recompute mode; its 20 `merged_sha256` entries equal the
sha256 of the 20 `groups/*/merged.json` and its `source_manifest_sha256` equals the plan's.

## Checks (a |pull| above 3 would have blocked the result)

| Check | Value | Pull |
|---|---|---:|
| C3 against the exact -0.8748500126526 | -0.87485136212 +- 1.25e-6 | -1.08 |
| C4 against the exact 5.048868431355 | 5.04887929612 +- 3.01e-5 | +0.36 |
| C5 against the exact -38.83364589623 | -38.8344913344 +- 5.07e-4 | -1.67 |
| C6 against the C6(2) production 362.36647176 +- 0.00080 | 362.3727456 +- 0.0085778 | +0.73 |
| power difference, order 3 | -1.1e-16 +- 6.6e-17 | rounding |
| power difference, order 4 | 5.4e-8 +- 1.5e-7 | +0.36 |
| power difference, order 5 | 1.10e-5 +- 1.85e-5 | +0.60 |
| power difference, order 6 | 3.30e-4 +- 1.18e-3 | +0.28 |
| campaign a against b | -3875.320 +- 0.727 vs -3876.932 +- 0.757 | 1.54 |
| bootstrap SE / covariance SE | 0.52219 / 0.52445 = 0.996 | |
| previous calculation -3953.634 +- 76.731 | | +1.01 |
| previous power correction 1.750 +- 5.424 | | -0.33 |
| three-loop power jet b3p(0) against -4 | -3.99999979 +- 0.00000042 | +0.50 |
| [z]b3p against the quadrature 18.6743207750 | 18.6743200 +- 0.0000021 | -0.36 |

The `lower_order_checks` block inside `C7_result.json` still compares C6 with the archived 362.3489 and has no pulls
(review finding M2); the table above, recomputed by `make -f public.mk replay`, is the one the note quotes.

**Reported value.** The previous calculation used four sampling SEs rounded up (310 for 4 x 76.7), checked against the
half-stream displacements. The same rule gives 4 x 0.52445 = 2.098, which exceeds both half-stream deviations (0.36), so
**C7(2) = -3876.1 +- 2.1** (rounded up to a multiple of 0.1). Scope: sampling error only; the graph construction, local
self-energy subtraction and renormalization argument are inherited, not independently validated.

## Results review (2026-10-01)

OpenAI Codex (gpt-6-astra, xhigh) reviewed a dossier of this result and approved it in round 1 with no findings; see
`REVIEWS.md` in the package.

## Correction (2026-10-02): the compile failure was Boost 1.66, not Boost 1.86

On the other cluster the Boost 1.86 module set only `BOOST_ROOT`, not an include path, so the first build there compiled
against the system Boost 1.66 and failed. With the real Boost 1.86 headers the delivered kernel compiles; with Boost 1.66 it
does not. The production used Boost 1.77 and is unaffected: its binaries equal the later fix-loop builds byte for byte.
