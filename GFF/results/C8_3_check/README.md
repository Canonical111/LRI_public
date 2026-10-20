# c8opt production prod1 (independent C8(3) code on Expanse)

Copied from Expanse `$C8OPT_ROOT=<SCRATCH>/temp_project/c8opt` on 2026-10-11 by C63d.

## Result

`runs/prod1/C8_result_54838171.json` (sha256 58de4f97…), produced by assembly job 54838171 (`assemble_streaming.py
--bootstrap 4096`):

- **C8(3) = 1600.98 ± 3.97** (sampling SE: the replicate covariance propagated through the fixed point; the bootstrap
  is diagnostic only). The package marks it `reportable_precision_established = False`, because no allowance for
  numerical controls has been assigned.
  - Power-free part 1602.61 ± 2.96; power correction −1.63 ± 2.64.
  - Campaign a 1603.53 ± 4.91, campaign b 1598.42 ± 6.24 (pull 0.64). Half streams 1599.79 and 1602.17.
- **Lower-order checks** against the references: C3 −1.41σ, C4 −1.55σ, C5 −0.10σ, C6 33.599 ± 0.014 against 33.5754
  (+1.73σ), C7 −220.40 ± 0.19 against −220.35 (−0.21σ). All |pull| < 3.
- **Comparison:** our c8d3 pilot gives 1619 ± 16, a pull of −1.09σ. The c8d3 production on symmetry is still running.

## Campaign

- Package LRI_C8_D3_OPT at d5deeb9.
- Allocation `allocations/prod1_2000.json`: 16 replicates and at least 4,096 points.
- Plan job 54822480: seed 1546835505427890396, 1,994 jobs, 37,121,687,552 evaluations.
- **Lanes 54823471** (6 compute nodes × 16 lanes × 8 threads, 12:43:34) finished 1,989 jobs. Lane 67 deferred two
  bundles at its deadline (jobs 417 and 1057–1060), so the job ended FAILED with srun exit 3; this was a clean stop.
- **The tail (user "go", 2026-10-11):**
  - index-only job 54838167 (`evidence/index_prod1tail.sh`, shared): `dispatch/prod1_tail`, 16 lanes, same bundling;
  - lanes 54838170 (1 node, 11:31) ran the 5 jobs;
  - assembly 54838171 (shared, 0:46).
- **Cost:** about 76.7 node-h, about 9,810 SU.
  - The lanes are 76.36 node-h (6 nodes × 45,814 s); the tail adds 0.19.
  - The shared plan, index and assembly jobs are about 0.11 node-h.
  - User decision 2026-10-10: about 9,000 SU, inside an 80 node-h reservation bound.
- `ledger.jsonl` and `seeds.jsonl` are the Expanse admission ledger and the seed registry.
- `dispatch/*/runs/` holds every lane summary.
- `graph_statistics_54838171.json` holds the per-graph costs measured on Expanse, usable for any later allocation.
