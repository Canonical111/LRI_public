# Shipped cost models

**Site-named models (Stage 5).** The measured model of the final binary on each site is
`gmp_<site>_<cpu>_c8.json`, the name `slurm/site.sh`'s `c8_site_cpu` gives as `$C8_SITE_MODEL` together with the site's
pinned CPU: `gmp_expanse_epyc7742_c8.json` (Expanse, `AMD EPYC 7742 64-Core Processor`) and
`gmp_symmetry_epyc7543_c8.json` (symmetry, `AMD EPYC 7543 32-Core Processor`; every symmetry AMD job is pinned to that
CPU, docs/HPC.md "CPU pin"). Symmetry's model arrives with J-SWEEP-2's data-only commit (`slurm/native_job.sh sweep2`,
docs/HPC.md "Stage 5"); that commit adds a paragraph here (job, node, CPU, model sha256, executable sha256,
`scheduled_with`, PREV). A Mac test (`tests/integration_3a.py`) checks that each site's committed model names the site's
pinned CPU.

- **`gmp_expanse_epyc7742_c8.json`** (C8(3), Stage 3b, J-SWEEP-1): the first measured cost model of this package
  (schema `c8-d3-cost-model-1`, order 8, gmp, `--mp-check on`, 48,346 keys `campaign:sector:L:graph`, sha256
  `fc78fc8f…`). Written by `tools/make_cost_model.py` from the bootstrap-basis sweep `$C8_ROOT/runs/sweep1-20261005`
  (`tools/sweep.py`, `--pilot --points 512 --replicates 2 --test-graphs all`, both campaigns, 8 NUMA lanes x 16 threads,
  Expanse job 54676977 on <NODE>, AMD EPYC 7742, 2026-10-05). Its executable is `bin/c8d3_gmp` sha256
  `24adff54…` (code commit 8b87782; the `c8-stage3` baseline, `reference/baseline_c8_stage3.json`). It is the measured
  basis (HD11) of every role-`campaign` plan on that binary; a changed binary needs `tools/sweep.py --refresh` (D.14).
  Placement and estimates only; sample counts and random streams never depend on it. The sweep's summary (per-group
  seconds per point, promotion rates, the pilot cost it implies) is
  `benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/cost_summary.json`.

The C7(3) model below is kept for reference (`tools/cost_summary.py --symmetry-model` compares with it at L <= 7).

In C8, `production.py plan` has no default cost model: a role-`campaign` plan needs `--cost-model PATH` naming a
measured model whose executable sha256 matches the binary, whose CPU model matches the plan host's and whose
`mp_check` matches the plan's (HD11; `cost_models/$C8_SITE_MODEL` of the site, checked on each export by J-BLD with
`tools/cost_identity.py check --host-cpu --mp-check on`), and the tools refuse anything else. The symmetry file below is an order-7 model for another
binary and CPU; it is kept only as the reference for `tools/cost_summary.py --symmetry-model`. A cost model only affects
placement and estimates: shard sizes, block order, per-index time estimates, the suggested wall time, and the
lane-mode time guard. It never affects sample counts or random streams.

- **`gmp_symmetry_epyc7532.json`.** It is byte-identical to `<SCRATCH>/c7-d3/pilot-566376/costs.json` on
  symmetry, written by `tools/make_cost_model.py`.
  - Hardware: symmetry amddebugq node <NODE>, AMD EPYC 7532 (2 × 32 cores), GCC 11.4 -O3, `bin/c7d3_gmp` sha256
    635428f9….
  - Pilot: job 566376, 2026-09-30, delivered tools. Every group at M=1 and R=8, 64 threads, 1024-task blocks,
    65536-point chunks, primitives at a flat 16384 points; 120 checkpoint files and 3511 graphs.
  - The values are per-task wall seconds per point under 64-thread load. The run1 campaign (M=4096, R=64) was placed
    with it. The estimate-to-measured ratio of the shipped lane mode is in `benchmarks/symmetry_2026-10/`.
- **`gmp_symmetry_epyc7543_c8.json`, refreshed after Stage 6 fix round 2 (C8(3), 2026-10-07).** It is byte-identical to
  the model that `slurm/native_job.sh sweep2` wrote, as it appears in
  `benchmarks/symmetry_2026-10-c8/stage6_ad983e8/sweep2_570900/` (sha256 `01b67d0a…`).
  - Job 570900 ran on an AMD EPYC 7543 node under the CPU pin, on export ad983e8 (K₅, the final code of fix round 2,
    whose pinned tools equal K₆ a914db2's). It ran in C62d's H11 production window as one of C63d's agreed 3.
  - Executable: `bin/c8d3_gmp` sha256 `e9b6f6c3…`, the Stage-6 binary, unchanged since fix round 1. `mp_check` is on,
    and the model has 48,346 keys.
  - Plan role `cost_refresh`. `scheduled_with` is **measured** (PLAN:3932: only pinned tools changed). PREV is fix
    round 1's model (sha256 `554bb1d6…`, job 570664, the same executable), itself prior_model at F = 2 from Stage 5's
    `0fc934e7…`.
  - The seed was reserved in symmetry's seed log before the sweep ran (S2-002). The lanes are `numa`, 8 × 8.
  - Plans and lanes on symmetry use this model. HD11 compares the plan host's EPYC 7543 and this executable.
- **`gmp_expanse_epyc7742_c8.json`, refreshed in Stage 6 (C8(3) S6-SWEEP2-exp, 2026-10-07).** It is byte-identical to the
  model that `slurm/native_job.sh sweep2` wrote, as recorded in
  `benchmarks/expanse_2026-10-c8/stage6/ev_ad983e83c5d9/sweep2_54712666/` (sha256 `d92ebbfc…`).
  - Job 54712666 ran on Expanse compute node <NODE> (AMD EPYC 7742, GCC 13.3, Spack GMP 6.2.1 by RPATH), on export
    ad983e8 (K₅, whose pinned tools equal the final code K₆ a914db2's).
  - Two earlier attempts are superseded, not lost:
    - 54709504 hit its 1:00 wall after a 45-min Lustre export copy;
    - 54710244 completed on K₃, but fix round 2 changed pinned tools after it.
  - Executable: `bin/c8d3_gmp` sha256 `61d291eb…`, the Expanse build of the Stage-6 source (S1-04/S1-05). Its G-L8SELF
    rows equal the Stage-3 binary's exactly, both backends (X2 54709473). `mp_check` is on, and the model has 48,346
    keys.
  - `scheduled_with` is **prior_model** at F = 2. PREV is Stage 5's Expanse model (sha256 `56df9d61…`, executable
    `b7db88c1…`, job 54694976).
  - The seed was reserved in Expanse's seed log before the sweep ran (S2-002). The lanes are 16 × 8.
- **Other backends, hardware or a changed binary.** Measure with `tools/sweep.py` (a test-only `cost_sweep` on the
  bootstrap basis, or `--refresh` with a prior model as scheduling data, D.5/D.14), then `tools/make_cost_model.py
  SWEEP_RUN costs.json`, check it with `tools/cost_identity.py check`, and plan with `--cost-model costs.json`.
