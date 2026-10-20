# Reproducing the independent C8(3) check

Run everything from `GFF/code/LRI_C8_D3_OPT` with `make -f public.mk <target>`. Steps 1-3 need no cluster. Step 4 is
the production rerun, documented but not run in CI. Records live in `GFF/results/C8_3_check` (in git) and the bulk in
`GFF/data/C8_3_check` (hosted, `make -f public.mk fetch-data`; described in `GFF/data/C8_3_check/DATA.md`).

Ground rules:
- Never edit `tools/campaign.py`, `tools/sobol_net.py`, `tools/io_utils.py` (pinned by every campaign manifest),
  `tools/assemble.py`, `tools/assemble_streaming.py`, `tools/rg.py` (pinned by the result) or anything under `inputs/`
  (pinned by the manifest). The replay checks these hashes.
- `make test` runs in a copy (`.work/test`), because the package's tests rewrite `verification/*.json`.
- The records name the production cluster's paths in two places (`manifest.json`: the executable and allocation
  paths). They are part of the hashed record and are never resolved by any tool.

## 1. Environment

| need | production | also tested |
|---|---|---|
| Python | 3.11.9 with numpy 2.3.5, scipy 1.17.0, mpmath 1.3.0 | replay: 3.10.12 with numpy 1.24.4, scipy 1.11.1 (macOS arm64) |
| C++ (test and rerun only) | GCC 13.3.0, `-std=c++17 -fopenmp`, libquadmath | GCC 11.4.0 (symmetry builds); the delivered package: GCC 14.2.0 |
| headers and libraries | Boost 1.77 multiprecision headers, GMP 6.2.1 | Boost 1.83, GMP 6.3 (package README) |
| CPU | AMD EPYC 7742 (x86-64; `__float128` required) | AMD EPYC 7543, Intel Xeon Gold 6148 (tests only) |
| graph regeneration only | pynauty 2.8.8.1, sympy 1.14.0 | |

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install -r public/requirements.txt
export CPPFLAGS="-I<BOOST_ROOT>/include -I<GMP_ROOT>/include" LDFLAGS="-L<GMP_ROOT>/lib -Wl,-rpath,<GMP_ROOT>/lib"
```

## 2. Tests (`make -f public.mk test`, Linux x86-64 node, 32 cores / 64 GB, 2-3 min)

The steps of the production build job (`slurm/build.sh`), in a copy of the package:

| step | checks | production time (Expanse, 32 cores) |
|---|---|---|
| build | `bin/c8d3_optimized`, `c8d3_gmp`, `c8d3_baseline`, `point_checks_gmp`, `c7d3_reference`, `test_positive_quad` | 7-9 s |
| `bin/test_positive_quad` | 12,051,840 positive binary128 additions | 1 s |
| `make test-native` | same-sample regression of the C8 worker against the untouched C7 worker on C7 graphs (`reference_c7/`), array-boundary and split checks | 30 s |
| `make test-points` | 12 eight-loop graphs, four points each: the precision tiers (long double, binary128, multiprecision) against an independent 450-digit evaluation | 41 s |
| `tests/test_optimization.py` | optimized against baseline worker, 179 real graphs, identical rows and promotion counts | 17 s |
| `tests/test_hpc_dispatch.py`, `test_streaming_assembly.py` | dispatcher locks, deadlines, staging; streaming assembly equals the reference assembly | 8 s, 2 s |
| `tests/test_rg.py`, `test_campaign.py`, `test_allocate.py` | fixed point (exact checks), planner, allocation | 1-2 s each |

`make -f public.mk test-py` runs the last row and the streaming-assembly test without a compiler (seconds, any OS).
`make -f public.mk test-cluster` runs `tests/test_cluster.py` (the site admission layer with fake Slurm commands,
33 cases, 15-25 s, any OS; passed on macOS); it reads the delivered pilot's manifest, so it needs `fetch-data`. All 14 steps passed on three Expanse
builds (2026-10-09) and on a symmetry AMD EPYC 7543 build (2026-10-12).

## 3. Replay (`make -f public.mk replay`, about 3 s, 1 core, any OS)

`public/replay_check.py` reads `GFF/results/C8_3_check` and, when present, the main record
`GFF/results/C8_3/C8_result.json` (or `MAIN_RESULT=<path>`). It writes `.work/replay/replay_report.{txt,json}` and
exits 1 on any FAIL. Rows:

| row | what | tolerance and why |
|---|---|---|
| R0 | SHA-256 of the four records; result -> manifest, manifest -> allocation, manifest -> `inputs/*`, coverage certificate -> inventory; tool pins of the manifest (campaign, sobol_net, io_utils) and of the result (assemble, assemble_streaming, rg, io_utils) | exact |
| R1 | C0..C8, their standard errors and covariance, power-free part and correction with errors, their covariance, error by loop, lower-order pulls: recomputed from the stored means and covariances of the means with `rg.coefficients`, `rg.jacobians` and the propagation of `assemble.calculate()` | estimates rel 1e-12, errors rel 1e-10: same float64 code on the same stored inputs; only BLAS summation order can differ (observed: 4e-16 and 0) |
| R2 | `assemble.calculate()` itself on synthetic 16-replicate matrices with exactly the stored moments (both campaigns identical) | estimates rel 1e-11, errors rel 1e-8: the covariance is rebuilt by an eigen-decomposition (observed 3e-15 and 4e-10) |
| R3 | the quoted values, rounded as quoted: 1600.98 +- 3.97; max lower-order pull 1.73; C6 33.599 +- 0.014; C7 -220.40 +- 0.19; README pulls and power split | string equality at the quoted digits |
| R4 | campaigns: (P_a + P_b)/2 of the per-graph projected means equals J . means; each campaign recomputed to first order about the pooled fixed point from `graph_statistics_54838171.json` and compared with the stored campaign coefficient; then 1603.53 +- 4.91, 1598.42 +- 6.24, pull 0.64 | abs 1e-8; abs 1e-4 (observed 1.4e-6; loops 5-8 enter affinely at eighth order, the low loops' second-order terms are tiny); quoted digits |
| R5 | -0.40 combined SE from the main estimator (main record checked by hash and against the note's values) | quoted digits |
| R6 | 24,173 kernels per campaign = inventory; manifest graph hashes = inventory hashes; points = allocation, minimum 4,096; 16 replicates; rates 0.8/0.7; 48 group seeds = `campaign.derive_seed(base seed)`; base seed differs from the delivered pilot's; 1,994 jobs by the planner's rule; 2 x 16 x sum(points) = 37,121,687,552 evaluations (also the sum of the per-graph points) | exact |
| R7 | `tools/allocate.py` on the delivered pilot's graph statistics with a 2,000 core-hour budget and 16 replicates reproduces `prod1_2000.json` byte for byte (estimate 1999.99 core-hours of the pilot host) | exact; SKIP without the pilot bundle, FAIL in `make -f public.mk replay-full` |
| D | about 9,800 SU: 6 nodes x 45,814 s + 0.19 + 0.11 node-h = 76.66 node-h x 128 SU = 9,812 SU (inputs from the production README, i.e. Slurm accounting) | arithmetic only; the dates and node count are documented, not recomputed |

Not replayed, because they need the per-replicate matrices that only the native outputs contain: the campaign
standard errors (4.91, 6.24), the half streams (1599.79, 1602.17) and the bootstrap (SE 3.78). The replay reads them
from the record.

## 4. Production rerun (documented, not run in CI)

The production `prod1` ran on Expanse on 10 and 11 October 2026: plan job (4 cores, 1 h 41 min), lanes job on 6
exclusive 128-core AMD EPYC 7742 nodes with 16 lanes x 8 threads (12 h 44 min, 1,989 of 1,994 jobs; 5 jobs deferred at
the deadline), an index-only job and one more node for the 5 jobs (11 min), and the streaming assembly (46 s). Total
about 76.7 node-hours, about 9,800 service units. A rerun with a fresh seed needs about the same.

1. `make -f public.mk fetch-data` (graph payloads 9.15 GB unpacked; the pilot's statistics shape the lane bundles).
2. Templates in `public/slurm/` (placeholders `<ACCOUNT>`, `<PARTITION_SHARED>`, `<PARTITION_NODE>`, `<NODES>`,
   `<NODE_MEM>`, `<SCRATCH>`, `<NAME>`, `<FRESH_SEED>`, `<LANES>`; `public/slurm/README.md`): `build_test.slurm`,
   `plan.slurm` (the production options: `--purpose production --points 4096 --replicates 16 --threads 8
   --graph-block 32 --chunk-points 262144 --allocation ../../results/C8_3_check/allocations/prod1_2000.json`, index
   `--bundle-jobs 4 --target-core-seconds 1800`), `lanes.slurm` (`--signal=TERM@600`, `C8_DEADLINE_FACTOR=6`),
   optionally `index_tail.slurm`, then `assemble.slurm` (`assemble_streaming.py --bootstrap 4096`).
3. Compare the new `C8_result_<job>.json` with the shipped one: independent seeds give an independent estimate; it
   should agree within the combined sampling errors.

The production itself was submitted through the package's site layer (`tools/submit.py`, `slurm/{plan,run_hpc,
assemble}.sh`, `docs/CLUSTERS.md`), which applies one user's allocation, caps and node exclusions; it ships unchanged
as the record of what ran. The templates run the same science commands without it.

## 5. Decisions not to make on your own

- Do not combine this result with the main C8(3) value, or quote it with an allowance: the package assigns none.
- Do not reuse the production seed 1546835505427890396 or the pilot seed 7736323638330945148.
- Do not edit pinned tools or inputs; a changed byte invalidates the plan or the replay.
