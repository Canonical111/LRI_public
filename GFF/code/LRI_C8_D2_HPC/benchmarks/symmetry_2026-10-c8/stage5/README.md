# Stage 5 on symmetry (2026-10-05): final validation, sweeps, L8 smoke, drills, design chain, throughput drill, pilot plan

Symmetry (Perimeter) is the plan's native site; site deviation U1 says the final validation and the smoke are repeated
here. Everything below ran on the FINAL commit `5d7586e9f1ab` (c8 HEAD at the start of this run: the G4c fixes
`5ddf8ee` plus their site evidence), on the EXACT default path (D1): no `--numerics`, no `--rates`, no `GMP_PREFIX`,
no `CPPFLAGS`/`CXXFLAGS`/`LDFLAGS`/`OPTFLAGS` overrides, in every build, test, sweep, smoke, drill and plan.

**Verdict in one paragraph.** Every numerical gate is exact and green on symmetry: the C7(2) reference binaries
reproduce the plan's symmetry hashes, J-VAL-2 replays all 3,774 kernels (the L=2 graph and the 3,773 L3-L7 kernels)
exactly on both backends, J-VAL-3 (fresh L=2 seed, thread identity, G-BK8, G-L8SELF exact against the symmetry
Stage-3 baseline, forced tiers, the R3a differential, merge scale, `assembly_checks --exact` 37/37) passes, the
sanitizer runs are clean. The smoke, the twin, the requeue and time-limit drills, the sharedq lane drills, the design
chain and the throughput drill all ran on real Slurm inside the H7 cap. The run found **ten defects or gaps for the Stage-6
inspection** (none changes a default-path number; list under "Findings", F1-F10): three test-portability failures of
J-VAL-1 on a whole symmetry node (F1-F3), a sanitizer self-test that cannot see GCC 11's assertion message (F4),
CPU-vendor-dependent native rows from the x87 `expl`/`logl` (F5), a CPU-dependent `verify_result.py` gate through the
OpenBLAS kernels (F6), lane workers that leave their runtime directories behind when scancelled (F7), a recovery path
that stops at stale group tables and at the result's no-clobber rule (F8), no rchar record from `production.py
run` (F9; R07), and a Stage-4b speedup of x1.16-1.20 on symmetry against Expanse's x1.39 in the same measure (F10).
J-DES-5 (job 570114, run after this run's commit; `des5/README.md`) passed A-DES-5 and added an eleventh finding: the
1e-3 design over-allocates free L8 because its replicate count follows the free L8 primitives (F11, `tools/design.py`).

**Status after this run (2026-10-05).** F1-F9 were fixed in 86e15f4 (merged as e7e6589) and re-validated on symmetry
in the fix round (`fix/README.md`), which found **F12** (the pack over-read); F12 was fixed in d5dfd38 and the
close-out (`close/README.md`) passed A-ORC-13 on real Slurm with it, J-VAL-1 and the user-required `dd+mp256` J-FLAG
gate (570210). F10 is a documentation item (speedups per site). F11 is fixed in 23540b2, together with route (b) for
`dd+mp256` (`pre6/README.md`). The "Status" column of the findings table below says where each was closed. The
planned pilot predates every one of these tool changes and is re-planned after Stage 6 (`docs/HPC.md`, "Pilot
runbook").

## Setup

| Record | What |
|---|---|
| `setup/export_check_5d7586e9f1ab.json` | `git archive 5d7586e` into `<SCRATCH>/c8d2/pkg/5d7586e9f1ab`: 7,190 files equal to the archive in content and mode |
| `setup/export_check_b4273c59e911_c8-stage3.json` | `git archive c8-stage3` (b4273c5) into `pkg/b4273c59e911`: 4,968 files equal; the symmetry Stage-3 baseline is built there |
| `s5build.570026.0/` | job 570026 (amddebugq <NODE>, EPYC 7543, 1:07): the two L8 packs of `pkg/7a8aad783c31/inputs/packs` re-hashed against the export's `inputs/manifest.json` (free `e5dd7271…`, power `3d77d0c4…`, both equal) and hard-linked (`l8_packs.json`); `make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize && make c7ref`; the Stage-3 baseline `make bin/c8d2_decimal bin/c8d2_gmp` in its own export, byte-copied into `bin/baseline/`. `binaries.sha256`, `--describe` of every worker, every build record (BOOST_LIB_VERSION 1_77 in all), `identity.json` |
| `~/c8d2/venv` | `pytest==9.1.1` (Expanse's version) installed on 2026-10-05 after J-VAL-1 found it missing (`vendored_isolated` runs the vendored tests with pytest); `pip freeze` before/after in `setup/venv_freeze_{before,after}.txt` (only pytest and its four dependencies added) |

**Executables (Ubuntu GCC 11.4.0, Boost 1.77 headers, system GMP 6.2.1; differ from Expanse's GCC 13.3 builds by the
compiler only):**

| Executable | sha256 |
|---|---|
| `bin/c8d2_decimal` | `619ddf7d1cf94d6229c841cd3fbe22574045ec65a1b69f8b827f1e26f180895f` |
| `bin/c8d2_gmp` | `2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17` |
| `bin/ref/c7d2_decimal` (make c7ref) | `e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5` = the plan's symmetry hash |
| `bin/ref/c7d2_gmp` (make c7ref) | `7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3` = the plan's symmetry hash |
| `bin/baseline/c8d2_decimal` (tag c8-stage3) | `c121b1e65d540a0a1acc3a12cef5d6a13f7a1279b0a98f2f4e11df941dd08d93` |
| `bin/baseline/c8d2_gmp` (tag c8-stage3) | `23624153cd3e8b45cf8438658c905893689bb9707516038b4717a60c8c26d3a3` = the Stage-4a symmetry build of 7a8aad7 (job 569788) |

## Item verdicts

| Item | Job(s) | Verdict | Evidence |
|---|---|---|---|
| **J-VAL-1** (`make test`, command by command) | 570027 amdq <NODE> 13:45; follow-up 570033 amddebugq <NODE> 2:29 | **PASS with three test-portability defects (F1-F3)**. validate (52 parts), test_pipeline 16/16, ast_scan, test_regress, merge_scale 2x10^4, check_vendored, the delivery-verifier test, check_inputs, test_profiling, test_gmp_prefix, test_dd_profile, workflow and staging (both backends) pass; unit_orchestration 46 of 47 sub-tests pass (A-ORC-13 on the Linux fingerprint path included). Failed: (F1) unit_orchestration `lanes` (C8_LANES=2 on a 64-core affinity set gives 32-core lanes > the test plan's checkpoint_tasks=8, lanes.py refuses 64 as designed); it passes under `taskset -c 0-15` on the same node type (570033); (F2) vendored_isolated: the symmetry venv had no pytest; after installing pytest 9.1.1 it passes 10/10 (570033, A-ASM-1 cluster part green); (F3) test_numerics_flags `f2_profile`: `repr(numpy.float64)` under numpy 2.3.5 is `np.float64(…)`, which the fake worker cannot parse (`nf_dse_repro.log` in 570033); passes on the Mac (numpy 1.23.5). | `s5val1.570027.0/` (one log and record per command), `s5val1b.570033.0/` |
| **J-VAL-2** (`make test-full`) | 570028 amdq <NODE> 4:14 | **PASS**. `c7ref` hashes = the plan's e696d7f3…/7e3c8c92…; validate --full: replay of 3,774 kernels (L=2 + all 3,773 L3-L7) exact for G-REF, G-C7 and G-JET on both backends (every `max_normalized_difference_mp_rows` 0), invariance, inspector, class B, diagnostics; 450-digit point checks L3-L8 pass; check_inputs, workflow, staging pass; executables unchanged by make. | `s5val2.570028.0/` |
| **J-VAL-3** + **A-RPL-7 G-L8SELF** | 570029 amdq <NODE> 13:21 | **PASS, all exact**. L=2 control with the FRESH seed 2699695239531018284 (registered in both logs and the mirror before submission): 32 x 2^16 points, every slot within 4 SE (largest pull 1.43), wa/wb = 6 exactly, decimal and gmp identical; thread identity (1/8/16/64 threads and 8x8 lanes); G-BK8 (400 kernels per sector at L7 and L8); G-L8SELF against the symmetry Stage-3 baseline built from c8-stage3 (1,600 free + 400 power L8 kernels, 2 x 512 points, both backends): every scientific field exact; forced tiers; the R3a quad differential on the GCC 11.4 build (identical); merge_scale 1.25x10^6 rows; `assembly_checks --exact` 37/37. | `s5val3.570029.0/` |
| **J-VAL-4** (A-KER-4) | 570030 sharedq (stopped in the self-test), 570031 sharedq <NODE> 10:55 | **PASS with a self-test portability defect (F4)**. `tests/sanitize.py` (no `--selftest`): 144 worker runs and 2 x 176 point checks with the ASan/UBSan/_GLIBCXX_ASSERTIONS builds, all clean. The self-test probes, built with sanitize.py's own command (`scripts/s5val4_selftest.py`): each aborts with its own report (glibcxx `Assertion '__n < this->size()' failed` visible under a pty; ASan stack-buffer-overflow; UBSan signed overflow). `sanitize.py --selftest` itself fails on GCC 11.4: libstdc++ <= 12 prints the assertion on STDOUT (`__builtin_printf`) and aborts, so the piped run loses it. | `s5val4.570030.0/`, `s5val4b.570031.0/` |
| **J-SWEEP-2** (A-PERF-4) | 570032 amdq <NODE> 17:24; accounting 570034 | **PASS**. All 24,173 graphs, both campaigns, 2 x 512 points, seed 2594661941911898802, chunked with J-SWEEP-1's model, 8 x 8 NUMA slots, ledger-registered (role sweep) before any index, merged; the symmetry AMD cost model of the final binary: **48,346 keys**, CPU AMD EPYC 7543, executable `2cc5e88e…`, installed as `cost_models/gmp_symmetry_amd_c8.json` (with J-SWEEP-3's class factors); calibration rows written to a copy (`calibration.json`). accounting.py: 1 ledger job, 18.56 allocated core-h, busy 5.69, eta_node 0.306 (A-ORC-9 on real data). | `s5sweep2.570032.0/` (its `cost_model.json` in `raw_evidence.tgz`; the model with J-SWEEP-3's factors is `cost_models/gmp_symmetry_amd_c8.json` at the package root, sha256 `a1b6e5d2…`) |
| **J-SWEEP-3** (cpu_class_factors) | 570035 debugq <NODE> 1:04; control 570039 amdq <NODE> 0:39 | **PASS for the factors; finding F5**. J-SWEEP-2's plan arguments and seed restricted to `--test-graphs 168 --test-selection stratified` (1,008 L>=6 graphs per campaign; 2,203 keys), 2 x 20 socket-pinned slots on the Xeon Gold 6148: factors (Intel/AMD) a free L6/7/8 0.81/1.22/1.24, power 1.14/1.20/1.32; b free 0.86/1.18/1.21, power 1.12/1.17/1.29. The job's own row comparison step had a column-name bug (exit 3, after the factors were written); rerun with `scripts/s5sweep3_rows.py`: **4,034 of 4,406 rows differ from J-SWEEP-2 in the last digits** (relative ~1e-16; same task, seed, net, quad and mp counters). Control 570039 replanned the identical subset on AMD with the Intel run's process shape (2 x 20 threads): **identical to J-SWEEP-2, different from the Intel run**: the native rows depend on the CPU vendor (F5). | `s5sweep3.570035.0/`, `s5sw3amd.570039.0/` |
| **J-SMK-1** (plan smoke + twin) | 570040 sharedq 1:00 | **PASS**. The plan's command word for word (seed 7170939708808771305): 29 indices, 35,296 tasks, 156 checkpoints, estimate 15.39 core-h (max index wall 827 s); both plan jobs registered (role plan); seed in `$C8_SEEDS`. | `logs/c8d2-plan-smoke_570040.out` |
| **J-SMK-2 / A-SMK-1** | lanes 570052 (<NODE>, 13:09), 570053 (<NODE>, 9:09), merge 570054 (0:05) | **PASS, with the verify_result finding F6**. Admitted under C8_AMDQ_CAP=4 (amd_live 0, k 3); 8 lanes of 8 CPUs per node (`C8_LANES=numa`, EPYC 7543); no lane failure; status exit 0; 24 merged.json; `C8_test_result.json` with its `test_partial` block and the gate blocks (top_slot, loop7, affinity) and power_protocol; per-index peak RSS (native max_rss + Python ru_maxrss, measurement hook) at most **0.717 x est_peak_bytes** (29 indices; A-ORC-5). `verify_result.py` passes when OpenBLAS uses the AVX2 kernels of the node that assembled it (`OPENBLAS_CORETYPE=Zen` or `Haswell`) and fails on the Cascade-Lake login node's AVX-512 kernels: `/test_partial/gates/affinity/linear_response_residual[8]: 1.82e-12 differs from the recomputed 8.64e-12` (F6). | `smoke/` (`smk_check.json`, `smk2_submit.out`, `verify_result_blas_coretypes.txt`) |
| **J-DRL-1** (restart twin, A-ORC-8a) | 570065 (scancelled after 9:27), 570066 merge (cancelled pending), 570078 (11:59), merge 570079 | **PASS on the result, finding F7 on cleanup**. After the cancel the 8 claims were stale; `submit.sh --lanes 1` released them (8 lines "released stale claim … CANCELLED") and finished the campaign; **all 24 merged.json batches bitwise equal to the smoke's**, graph_replicates and graph_tails byte-identical (checkpoints: 18 from the cancelled job, 138 from the restart). With TMPDIR on BeeGFS, the 8 lane scratch directories and their `c8d2_runtime_*` directories (493 MB) were still there 30 s and 1 min after the cancel, and no index log shows a stop message: the runtime directories were NOT removed (F7). | `drl/drl1_*` |
| **J-DRL-2** (requeue, A-ORC-8b) | 570075 (attempt 1 REQUEUED after 4:27 by `scontrol requeue`; attempt 2 COMPLETED 20:38), merge 570076 | **PASS**. User requeue is allowed on symmetry; the restarted job (same id, restart 1) logged "released own stale claim … (job 570075, restart 0; now restart 1)" for its 5 claims and finished the 5 L8 indices; status complete, no failure. | `drl/drl2_*`, `logs/` |
| **J-DRL-3** (time limit, A-ORC-8c) | 570068 (C8_LANE_TIME=00:20:00, 4:39) | **PASS**. The worker ran the 20 indices that fit and skipped the 5 L8 indices (6.7k-11.9k estimated core-s, which do not fit 20 min on an 8-core lane); it ended with no killed index, no failure, no claim left. | `drl/drl3_submit.out`, `logs/` |
| **J-DRL-4..7** (sharedq lane drills, drill mode) | drA: 570042/570043, 570055; drB: 570045/570046 (held), 570047 (cancelled), 570049, 570050 | **PASS**. Lock: two concurrent `--lanes 1`, one submitted, the other exit 75 "nothing changed"; mixed mode: an array submit while the lanes were live exit 65, nothing submitted; status-line window: after deleting a checkpoint, `status` exit 1 names index 17 and prints `submit.sh --window 0:17` and the lane-mode recovery line; merge-only resubmit (`--lanes 0`): all 98 campaign outputs byte-identical; A-ORC-10: `--lanes 2 --hold` then `--lanes 1` left exactly ONE pending merge (570050) with afterany on all three workers, the superseded 570047 CANCELLED while pending; at most 4 sharedq jobs ran at once. | `drills/` |
| **J-DRL-8** (recovery of a completed index, A-ORC-12) | 570057, merges 570058 (FAILED), 570059 (FAILED after publishing) | **PARTIAL (F8)**. After deleting index 17's checkpoint and its group's merged.json: the queue rebuild removed the done marker and logged it in `lanes/done_invalidated.jsonl`; the lane recomputed the index (scientific fields equal to the saved checkpoint); status exit 0; **all 24 merged.json batches bitwise equal to the saved ones**. But the merge job failed twice: (1) the group's stale `graph_costs.csv` from the first merge (timings) is refused by the no-clobber copy ("Checksum mismatch"); after removing it (recorded), (2) the group merged, then `assemble` refused to overwrite `C8_test_result.json` because its `merged_sha256` of that group changed (the only difference, checked by a reassembly into the evidence folder). | `drills/drA_recovery_*` |
| **J-SMK-3** (design chain, A-DES-3, A-ASM-6/7 on real data) | freezes 570070 (refused), 570071, 570100; plans 570072/570073, 570101/570102; batches 570086+570087, 570092+570093 (K = 1 bundle), 570104+570105, 570107+570108 (K = 2 bundle); combine 570097 (refused), 570111 | **PASS (A-DES-3, A-ASM-6/7), with F6 on verification**. `design.py freeze --test-only` on the merged smoke ran end to end with sacct accounting (`accounting.py`: smoke 23.94 allocated core-h, eta_node 0.668). At `--target-rel 1e-3` the total-cap gate refused (design 5,071.9 core-h + spent > 5,000; minimum printed). At 1.5e-3: bundle `designs/test_smoke1` (K = 1; predicted SE 41.0, 2,705.7 core-h for the full design) and `designs/test_smoke1b` (`--batches 2`, design sha256 `029f8cd4…`, predicted SE 39.8); `plan --design … --test-graphs 256` in sharedq plan jobs (role plan): K = 1 batches 30 indices / 208,512 tasks / 25.16 core-h each, K = 2 batches 28 / 166,208 / 18.79; each batch run by one amdq lane worker, merged and assembled. `combine.py --test-only`: `--partial` with desc1 (C8 test value 89,864.9 +- 14.0) and final with desc1 + desc2 (89,856.0 +- 10.4, chi2 0.746 with 1 dof, "final combination of all 2 planned batches", numerics exact, rates default, the bundle's design sha256); `verify_result.py` passes on both combined results and on both batch results when it runs with the OpenBLAS kernels of the node that produced them, and fails otherwise (F6). Combining the two K = 1 batches was refused as designed (a K = 1 bundle has no partial and no two-batch final). The test values are those of a 256-graph test subset, not physical. | `design_smoke1/`, `design_smoke1_b/`, `design_smoke1b/`, `design_chain/` (K = 1), `design_chain_k2/` (combined results, `verify_combined.txt`) |
| **J-SMK-4** (throughput drill, A-PERF-3; A-ORC-13 real Slurm) | lane worker 570083 <NODE> 1:22:47 (`C8_LANES=numa`, 8 x 8, `C8_LANE_TIME=02:00:00`), merge 570084; P4 rerun 570099 (<NODE>, the same node); report 570109 | **A-PERF-3: 3 of 4 PASS, the throughput criterion PASS literally and 0.947 against the same-binary reference; A-ORC-13 real Slurm PARTIAL**. Plan: `--pilot --points 4096 --replicates 6 --test-graphs 4096 --test-selection stratified --threads 8 --checkpoint-tasks 256 --index-hours 0.25` (seed 4138143893052926446; replicates 6, not 4, so that the final binary still gives the plan's 70-90 core-h and >= 1 h of L8 work: 62 indices, 143,580 tasks, estimate 75.8 core-h). Measured over the lane job's whole allocation (W = 4,967 s): **busy = sum of task seconds / (64 W) = 0.906** (>= 0.90; 288,110 task seconds, 93.6% of them L8 = 1.17 h of the node); **per-block OpenMP efficiency**: all 397 L8 blocks >= 0.974 (weighted mean 0.991), 98.6% of all 587 blocks >= 0.95 (the rest are tiny L3-L5 blocks, minimum 0.70); **node throughput** 54.94 J-SWEEP-2 cost-model s per node-second = **1.133 x** the best P4 shape of Stage 4a (8x8, Stage-3 binary, re-expressed in the J-SWEEP-2 model: 48.49) and **0.947 x** the same P4 workload rerun with the final binary on the same node (58.02; shortfall: the drill's tasks run 5-6% slower than the sweep measured them, below); **median per-task speed** 0.951 (L8 0.937, P10-P90 0.88-0.98) of the J-SWEEP-2 model (within 10%; the sweep's L8 tail ran with half the slots idle, so its per-core speed is optimistic for a full node). A-ORC-13: rchar of all 62 `production.py run` processes recorded by the external hook (F9); **fingerprint_bytes identical, 7,007,827, in every run** (and in the smoke's); non-own bytes (rchar minus the index's task file, its staged pack members read once by staging and once by the native, its payloads, net and gamma) are a constant **29.80 MB** (+-0.01) in the ten L3-L5 runs (tasks.sqlite 24-74 KB), but grow with each run's own staged bytes from L6 on (about 0.7 extra bytes per staged member byte, also between indices of one group with one tasks.sqlite): the native reads its staged graph files more than once. That re-read is own data, but without a per-file breakdown the plan's smallest-vs-largest comparison (within 10% or 2 MB) cannot be made; computed as above it fails (29.8 MB vs 701.6 MB). | `smk4/` (`thru_report.json`, `rchar_fit.json`, `smk4_submit.out`), `s5p4.570099.0/` |
| **J-PIL-1** (pilot plan, symmetry form) | 570080 sharedq 0:37 | **PASS (nothing submitted)**. See "Pilot ready" below. | `logs/c8d2-plan-pilot_570080.out` |
| **J-DES-5** (A-DES-5, production-size dry run; A-PERF-4 base) | 570114 sharedq <NODE> 34:44 | **PASS (A-DES-5); finding F11**. `design.py freeze --test-only` on the merged J-SWEEP-2 sweep (all 24,173 graphs, η_node 0.306 from its own ledger, R10) at 1e-3, 5e-4, 2.5e-4 and 1.35e-4 (K = 1 each; 3,963 / 5,856 / 23,423 / 76,623 core-h at J-SMK-4's lane η_node 0.915), then `production.py plan --design` of each in the job, not submitted: 5.2-8.5 million tasks, 20,533-36,475 checkpoints, 351-6,424 indices, plan wall 307-678 s and peak RSS 0.84-1.31 GiB, merge 2 passes; every cap holds; the four plan directories deleted. F11: the 1e-3 freeze over-allocates free L8 (r follows the free L8 primitives' multiplier). Run by the docs agent after this run's commit; recorded here and in `des5/README.md`. | `des5/` (README, `s5des5.570114.0/`, `des5_summary.json`, `aperf4.json`) |
| **A-PERF-5** (owed: per (sector, L), L3-L7 included) | 570098 amdq <NODE> 1:49; P4 rerun 570099 | **Measured; finding F10**. Same node, same subset (J-SWEEP-3's arguments and seed: 2,203 keys, 168 graphs per (sector, L), half cheapest and half heaviest), final binary vs the symmetry Stage-3 baseline (c8-stage3, GCC 11.4), task seconds: free L3-L8 0.90 / 0.94 / 1.06 / 1.01 / 1.13 / **1.17**, power L3-L8 1.06 / 1.10 / 1.02 / 1.16 / 1.12 / **1.16**, total **1.157** (per campaign in `perf5.json`). Graphs without promotions gain nothing (free L8 light half 1.00); the heavy half of free L8 1.17, of power L8 1.15. The P4 L8 workload (uniform draw, with staging and load) on the same CPU model: 8x8 wall 325.1 s (Stage 4a, Stage-3 binary) -> 271.7 s (final binary) = **x1.197** node throughput. The same kernel-seconds measure on Expanse (Stage-5 Expanse run, J-SWEEP-2E against J-SWEEP-1, GCC 13.3, EPYC 7742) gives x1.390 overall, free L8 x1.444, power L8 x1.261; Stage 4b's x1.646 counted lane-thread seconds with loading. The opt-in profiles were not run here (D1: Stage 5 uses the default path only). | `s5perf5.570098.0/` (`perf5.json`, both subset cost models), `s5p4.570099.0/p4/p4.json` |

## Jobs and allocation

Every c8d2-* job of this run (`scripts/corehours.py`: `sacct -u <USER> -X --duplicates` since 04:50 EDT, ElapsedRaw x
physical cores; AMD EPYC nodes 64 cores and 1 thread per core, Intel nodes 2 threads per core; the requeued J-DRL-2
worker counted for both attempts; other <USER> jobs, another project's, are not counted). Logs: manual jobs in
`<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`), lane workers and merges in
`<campaign>/slurm_logs/lane-<id>.log` and `merge-<id>.log` (in `raw_evidence.tgz`). H7: every AMD submission was
admitted with at most 4 live c8d2- jobs on amdq + amddebugq + amdpreq (`admission/h7_admission.jsonl` for the manual
jobs, the `C8: admission` line of each `submit.sh` output for the campaign jobs); amdq always `--exclude=cn112`; no
longq; sharedq jobs `--no-requeue`.

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570026 | build (all targets + Stage-3 baseline) | amddebugq <NODE> | COMPLETED | 0:01:07 | 1.19 |
| 570027 | J-VAL-1 | amdq <NODE> | FAILED | 0:13:45 | 14.67 |
| 570028 | J-VAL-2 | amdq <NODE> | COMPLETED | 0:04:14 | 4.52 |
| 570029 | J-VAL-3 + A-RPL-7 | amdq <NODE> | COMPLETED | 0:13:21 | 14.24 |
| 570030 | J-VAL-4 (stopped in self-test, F4) | sharedq <NODE> | FAILED | 0:00:07 | 0.01 |
| 570031 | J-VAL-4 (sanitize + GCC-11 self-test helper) | sharedq <NODE> | COMPLETED | 0:10:55 | 0.73 |
| 570032 | J-SWEEP-2 | amdq <NODE> | COMPLETED | 0:17:24 | 18.56 |
| 570033 | J-VAL-1 follow-up (F1-F3) | amddebugq <NODE> | COMPLETED | 0:02:29 | 2.65 |
| 570034 | J-SWEEP-2 accounting | sharedq <NODE> | COMPLETED | 0:00:02 | 0.00 |
| 570035 | J-SWEEP-3 (Intel) | debugq <NODE> | FAILED | 0:01:04 | 0.71 |
| 570039 | J-SWEEP-3 AMD control (F5) | amdq <NODE> | COMPLETED | 0:00:39 | 0.69 |
| 570040 | J-SMK-1 plan smoke + twin | sharedq <NODE> | COMPLETED | 0:01:00 | 0.07 |
| 570042 | drA lane worker (lock drill) | sharedq <NODE> | COMPLETED | 0:00:33 | 0.01 |
| 570043 | drA merge | sharedq <NODE> | COMPLETED | 0:00:06 | 0.00 |
| 570045 | drB worker (held) | sharedq <NODE> | COMPLETED | 0:00:11 | 0.00 |
| 570046 | drB worker (held) | sharedq <NODE> | COMPLETED | 0:00:11 | 0.00 |
| 570049 | drB worker | sharedq <NODE> | COMPLETED | 0:00:14 | 0.00 |
| 570050 | drB merge | sharedq <NODE> | COMPLETED | 0:00:06 | 0.00 |
| 570052 | J-SMK-2 lane worker | amdq <NODE> | COMPLETED | 0:13:09 | 14.03 |
| 570053 | J-SMK-2 lane worker | amdq <NODE> | COMPLETED | 0:09:09 | 9.76 |
| 570054 | J-SMK-2 merge | amdq <NODE> | COMPLETED | 0:00:05 | 0.09 |
| 570055 | drA merge-only resubmit | sharedq <NODE> | COMPLETED | 0:00:06 | 0.00 |
| 570057 | J-DRL-8 recovery worker | sharedq <NODE> | COMPLETED | 0:00:02 | 0.00 |
| 570058 | J-DRL-8 merge (F8) | sharedq <NODE> | FAILED | 0:00:02 | 0.00 |
| 570059 | J-DRL-8 merge (F8) | sharedq <NODE> | FAILED | 0:00:05 | 0.00 |
| 570060 | plan drl23 | sharedq <NODE> | COMPLETED | 0:00:30 | 0.03 |
| 570061 | plan J-SMK-4 | sharedq <NODE> | COMPLETED | 0:00:32 | 0.04 |
| 570065 | J-DRL-1 twin worker (scancelled) | amdq <NODE> | CANCELLED by 70850 | 0:09:27 | 10.08 |
| 570068 | J-DRL-3 worker (20 min) | amdq <NODE> | COMPLETED | 0:04:39 | 4.96 |
| 570070 | J-SMK-3 freeze (cap refusal) | sharedq <NODE> | FAILED | 0:00:04 | 0.00 |
| 570071 | J-SMK-3 freeze test_smoke1 | sharedq <NODE> | COMPLETED | 0:00:08 | 0.01 |
| 570072 | plan desb1 | sharedq <NODE> | COMPLETED | 0:01:28 | 0.10 |
| 570073 | plan desb2 | sharedq <NODE> | COMPLETED | 0:01:28 | 0.10 |
| 570075 | J-DRL-2 worker (requeued) | amdq <NODE> | REQUEUED | 0:04:27 | 4.75 |
| 570076 | J-DRL-2 merge | amdq <NODE> | COMPLETED | 0:00:05 | 0.09 |
| 570075 | J-DRL-2 worker (requeued) | amdq <NODE> | COMPLETED | 0:20:38 | 22.01 |
| 570078 | J-DRL-1 restart worker | amdq <NODE> | COMPLETED | 0:11:59 | 12.78 |
| 570079 | J-DRL-1 merge | amdq <NODE> | COMPLETED | 0:00:05 | 0.09 |
| 570080 | J-PIL-1 plan pilot | sharedq <NODE> | COMPLETED | 0:00:37 | 0.04 |
| 570083 | J-SMK-4 lane worker | amdq <NODE> | COMPLETED | 1:22:47 | 88.30 |
| 570084 | J-SMK-4 merge | amdq <NODE> | COMPLETED | 0:00:06 | 0.11 |
| 570086 | desb1 worker | amdq <NODE> | COMPLETED | 0:28:52 | 30.79 |
| 570087 | desb1 merge | amdq <NODE> | COMPLETED | 0:00:07 | 0.12 |
| 570092 | desb2 worker | amdq <NODE> | COMPLETED | 0:28:47 | 30.70 |
| 570093 | desb2 merge | amdq <NODE> | COMPLETED | 0:00:06 | 0.11 |
| 570097 | combine (K=1 bundle; refused) | sharedq <NODE> | FAILED | 0:00:04 | 0.00 |
| 570098 | A-PERF-5 | amdq <NODE> | COMPLETED | 0:01:49 | 1.94 |
| 570099 | P4 rerun (final binary) | amdq <NODE> | COMPLETED | 0:04:33 | 4.85 |
| 570100 | J-SMK-3 freeze test_smoke1b (K=2) | sharedq <NODE> | COMPLETED | 0:00:08 | 0.01 |
| 570101 | plan desc1 | sharedq <NODE> | COMPLETED | 0:01:14 | 0.08 |
| 570102 | plan desc2 | sharedq <NODE> | COMPLETED | 0:01:14 | 0.08 |
| 570104 | desc1 worker | amdq <NODE> | COMPLETED | 0:20:48 | 22.19 |
| 570105 | desc1 merge | amdq <NODE> | COMPLETED | 0:00:07 | 0.12 |
| 570107 | desc2 worker | amdq <NODE> | COMPLETED | 0:20:53 | 22.28 |
| 570108 | desc2 merge | amdq <NODE> | COMPLETED | 0:00:07 | 0.12 |
| 570109 | J-SMK-4 report | sharedq <NODE> | COMPLETED | 0:00:04 | 0.00 |
| 570111 | combine (K=2) partial + final (FAILED: the script's own `--out` paths, below) | sharedq <NODE> | FAILED | 0:00:08 | 0.00 |
| 570114 | J-DES-5 (after this run's commit; `des5/`) | sharedq <NODE> | COMPLETED | 0:34:44 | 2.32 |
| **total** | 57 records of this run (`sacct -X --duplicates`; `corehours.json`) + J-DES-5 | | | | **338.82 + 2.32 = 341.14** |

**Symmetry total for this Stage-5 run: 338.82 core-hours** (amdq 332.94, amddebugq 3.84, sharedq 1.33, debugq 0.71),
**341.14 with J-DES-5** (2,084 s on the 4 physical cores of an 8-CPU sharedq allocation on the Intel <NODE>).

**Job 570111 is FAILED for a reason in its own script, not in the package.** `scripts/s5combine.slurm` passed paths
ending in `.json` as `combine.py --output` (`…/design_chain_k2/C8_partial.json` and `…/C8_final.json`). `--output`
names a directory: `combine.py` created it and wrote `C8_test_partial.json` and `C8_test_final.json` inside (both
combinations exit 0; the log prints their paths). The script's next step ran `verify_result.py` on the `--output`
path, which is that directory, and stopped with `IsADirectoryError` (exit 1), so the job ended FAILED. Both combined
results were then verified at their real paths (`design_chain_k2/verify_combined.txt`; F6 applies).

**H7 admission records and the partition a job ran on.** `admission/h7_admission.jsonl` records the first partition
of each job's `-p` list, not the one it started on. Two jobs listed two AMD partitions and started on the other one:
570033 (`c8d2-s5val1b`, recorded `amdq`) ran on amddebugq <NODE>, and 570039 (`c8d2-s5sw3amd`, recorded `amddebugq`)
ran on amdq <NODE>. Both partitions are in the H7 pool, so the cap was checked correctly. `admission/h7_ran_on.json`
gives every admitted job's recorded partition and its sacct partition and node.
With the G4c fix agent's 2.92 SU on Expanse, the Stage-5 share used so far is about 342 of 1,500; the development total
is about 921 + 342 = 1,263 core-hours of the 5,000 cap.

## Pilot ready (J-PIL-1, symmetry form; NOT submitted)

`slurm/plan.sh` in sharedq job 570080 ran

```bash
production.py plan <SCRATCH>/c8-d2/pilot1-20261005 --pilot --points 4096 --replicates 8 --threads 8 \
  --checkpoint-tasks 256 --index-hours 1.5 --backend gmp \
  --cost-model <SCRATCH>/c8d2/pkg/5d7586e9f1ab/cost_models/gmp_symmetry_amd_c8.json \
  --forbid-seeds-from <SCRATCH>/c8-d2/forbidden_seeds.json --seed 5945432546144395546
```

and registered the plan job (role plan); the fresh seed was checked against `$C8_SEEDS` before and appended after, and
synced into Expanse's log and the mirror. Printed estimate: **179.9 core-h** (the plan's central projection was about
220, range 120-360; below 300, so `--replicates 8` stays), 39 indices, 386,768 tasks, 1,534 checkpoints, maximum index
wall 4,796 s on an 8-core lane, projected merge 34 s, 1,875 projected files. The exact submit line (it waits for the
user's authorization and an amdq window agreed with C63d, H7/H11; inside the window `C8_AMDQ_CAP` is set to the
agreed node count, 4 workers + the merge = k 5):

```bash
export C8_ENV_SETUP=$HOME/c8d2/env.sh C8_PACKAGE=<SCRATCH>/c8d2/pkg/5d7586e9f1ab C8_RUN=<SCRATCH>/c8-d2/pilot1-20261005
C8_AMDQ_CAP=<agreed window, >= 5> C8_SBATCH_ARGS="-p amdq --exclude=cn112" C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes 4
```

The campaign pins the tools of 5d7586e. If Stage 6 changes a pinned tool, `submit.sh` refuses this campaign (64): the
pilot is then re-planned from the new export with the same command and a fresh seed.

The pilot runbook for both sites (the H7/H11 window, the probe, the submit lines, the checks after the run) is
`docs/HPC.md`, "Pilot runbook"; it advises `--lanes 3` here (3 nodes give the same 1.33-h wall as 4 at 256 instead of
341 core-hours, and 3 workers + the merge fit k = 4; `pilot/pilot_lanes.json`). The fixes owed for F1-F9 change pinned
tools, so this campaign will have to be re-planned.

## Findings for the Stage-6 inspection

| # | Severity | Where | Finding | Evidence | Suggested fix | Status (2026-10-05) |
|---|---|---|---|---|---|---|
| F5 | high (reproducibility contract) | `src/kernel.hpp` first pass (`expl`, `logl`, lines 186, 250, 259, 268, 272) | The native rows depend on the CPU vendor. Same binary, task, seed, net, quad and mp counters: Intel Xeon Gold 6148 rows differ from AMD EPYC 7543 rows in the last digits (relative ~1e-16 in the merged jets; 4,034 of 4,406 graph-replicate rows), while an AMD rerun with the Intel run's process shape reproduces the AMD rows exactly. glibc's x86-64 `expl`/`logl` use the x87 `f2xm1`/`fyl2x` instructions, whose last-bit results are microcode-specific. AMD Zen 2 (Expanse 7742) and Zen 3 (symmetry 7532/7543) agree with each other (Stage 4a). Statistically irrelevant, but: "nothing depends on the node" (docs/HPC.md) is false across vendors; a duplicate run of one block on the other vendor stops with "Conflicting duplicate execution"; twin/restart bitwise identity holds only within a vendor; `-p amdq,defq` lanes (suggested in `slurm/env.sh.example` and docs/HPC.md for 180G lanes) would mix vendors in one campaign. | `s5sweep3.570035.0/rows_vs_sweep2.json`, `s5sw3amd.570039.0/rows_vs_sweep2_amd.json` (identical), `rows_vs_sweep3_intel.json` (differs) | Pin a campaign to one CPU vendor (record the vendor in the manifest at the first claim and refuse the other), and drop the mixed-partition advice; a vendor-independent exp/log in the first pass would change the default numerics (D1) and is a later decision. | **Fixed** in 86e15f4 (the first claim pins the CPU vendor; another vendor exits 64; the mixed-partition advice dropped); **PASS** on symmetry, job 570184 (`fix/README.md`) |
| F8 | high (A-ORC-12 on real Slurm) | `tools/production.py` merge (`_publish_copy`), `tools/assemble.py` | Recovery of a completed index (the plan's J-DRL-8: delete one checkpoint and the group's merged.json, `submit.sh --lanes 1`) recomputes the index exactly and the new merged.json batches equal the old ones, but the merge job fails twice: the group's stale `graph_costs.csv` (timings) from the first merge is refused by the no-clobber copy ("Checksum mismatch"), and after it is removed the merge publishes and `assemble` refuses to overwrite `C8_test_result.json`, whose only change is that group's `merged_sha256`. | `drills/drA_recovery_*`, `logs/` of 570058/570059 (in `raw_evidence.tgz`) | Treat merged.json as the commit point: group tables without a merged.json are uncommitted and may be replaced; let assemble supersede a result whose scientific content is unchanged (keep the old one as `*.superseded.<sha>`), or document the files an operator must remove. | **Fixed** in 86e15f4 (merged.json is the commit point; assemble supersedes a result whose only change is `merged_sha256`); J-DRL-8 **PASS unattended**, 570175-570179 (`fix/`) |
| F7 | medium | `slurm/lane_worker.sh` (`exec python3 lanes.py worker`), `tools/lanes.py` worker | A scancelled lane worker leaves its lane scratch directories and every `c8d2_runtime_*` directory behind (493 MB with TMPDIR on BeeGFS, still there 1 min after the cancel), and no index log shows a stop message: the worker has no SIGTERM handling, so when the batch process exits slurmstepd SIGKILLs the lanes and their `production.py run` children before their cleanup runs. A-ORC-8(a) expects the runtime directories removed. Claims are left stale as expected, and the restart works. | `drl/drl1_before_cancel.txt`, `drl1_after_cancel.txt`, `drl1_leftovers.txt` | Forward SIGTERM from the worker to the lanes and wait for them (bounded, below KillWait 30 s), as `run_array.sh` does with its trap. | **Fixed** in 86e15f4 (SIGTERM forwarded to the lanes); J-DRL-1 **PASS**, nothing left 30 s after scancel, 570172/570182/570183 (`fix/`) |
| F6 | medium | `tools/verify_result.py` (affinity gate `linear_response_residual`) | Verifying the smoke's result on the Cascade-Lake login node fails: `linear_response_residual[8]` 1.82e-12 recorded vs 8.64e-12 recomputed. The residual is at rounding level and OpenBLAS (DYNAMIC_ARCH) picks AVX-512 kernels there; with `OPENBLAS_CORETYPE=Zen` or `Haswell` (the assembling node's kernels) it verifies. | `smoke/verify_result_blas_coretypes.txt` | Compare rounding-level residuals against a tolerance (they are already gated by a bound), or recompute them without BLAS; pin `OPENBLAS_CORETYPE` in assemble and verify. | **Fixed** in 86e15f4 (rounding-level residuals bounded); **PASS** on the login node (`fix/fxf6.login/`) |
| F9 | medium | `tools/production.py run` | R07/A-ORC-13 (real Slurm) and the J-SMK-4 spec say every `production.py run` logs its `/proc/self/io` rchar at exit; the package does not. J-SMK-4 measured it with an external `sitecustomize` atexit hook on `PYTHONPATH` (`scripts/rchar_hook/`, not part of the package; it also recorded the run's own and its children's peak RSS for A-ORC-5). | `scripts/rchar_hook/sitecustomize.py` | Log `rchar` (and `ru_maxrss` self/children) in the index log at the end of `run`. | **Fixed** in 86e15f4 (`claim_io` line, `tools/claim_io.py`); A-ORC-13 PARTIAL in the fix round (570170, cause F12), **PASS** after the F12 fix, 570212 (`close/`) |
| F10 | medium (performance claim, not correctness) | Stage-4b result (R3a), symmetry toolchain | The default binary's speedup over the Stage-3 baseline is smaller on symmetry: x1.157 in kernel seconds on the stratified subset (free L8 x1.17, power L8 x1.16; L3-L6 0.90-1.16) and x1.197 node throughput on the P4 L8 workload, against x1.390 in kernel seconds on Expanse (free L8 x1.444, power L8 x1.261; GCC 13.3, EPYC 7742) and Stage 4b's x1.646 (lane-thread seconds with loading). Same binaries on the same node in each symmetry comparison. Planning is unaffected: the symmetry cost model (J-SWEEP-2) is measured with the final binary, and the pilot estimate (179.9 core-h) uses it. | `s5perf5.570098.0/perf5.json`, `s5p4.570099.0/p4/p4.json`, `stage4a/prof4.569788.0/p4/p4.json` | Profile the binary128 tier on symmetry (GCC 11.4 inlining of `src/quadfast.hpp` against GCC 13.3's; `/usr/bin/g++-12` exists there) before quoting Stage-4b speedups for symmetry. | **Docs**: speedups quoted per site (`docs/PERFORMANCE.md`, d8f9305); symmetry's own `dd+mp256` factors measured by the gate 570210 (`pre6/`) |
| F1 | low (test) | `tests/unit_orchestration.py` `test_lanes` | The test's lane worker runs with `C8_LANES=2` on the job's whole affinity set; on a 64-core node that is two 32-core lanes, more than the test plan's checkpoint_tasks=8, and lanes.py refuses (64) as designed. Passes under `taskset -c 0-15` on the same node type. The plan's J-VAL-1 is a whole-node job. | `s5val1b.570033.0/lanes_full.log`, `lanes_taskset16.json` | Mock `sched_getaffinity` (or use C8_LANES sized to the plan) in the test. | **Fixed** in 86e15f4; J-VAL-1 **PASS** on a whole amdq node, 570165 and again 570211 (`fix/`, `close/`) |
| F2 | low (environment) | `requirements.txt`, symmetry `~/c8d2/venv` | `tests/vendored_isolated.py` runs the vendored assembly tests with pytest, but `requirements.txt` does not list pytest and the symmetry venv had none (Expanse's has 9.1.1). Installed here; then 10/10. | `s5val1.570027.0/vendored_isolated.log`, `s5val1b.570033.0/vendored_isolated.json` | Add `pytest` to `requirements.txt` (test requirement) and to the G0 venv check. | **Fixed** in 86e15f4 (pytest in `requirements.txt`, `tests/check_venv.py`); J-VAL-1 **PASS**, 570165, 570211 |
| F3 | low (test) | `tests/test_numerics_flags.py` `test_f2_profile` | `repr(delta)` of a `numpy.float64` is `np.float64(…)` under numpy >= 2 (both sites' venvs have 2.3.5), which `tests/fake_worker.py` cannot parse; passes on the Mac's numpy 1.23.5. | `s5val1b.570033.0/nf_dse_repro.log` | `repr(float(delta))`. | **Fixed** in 86e15f4 (`repr(float(...))`); J-VAL-1 **PASS**, 570165, 570211 |
| F4 | low (test) | `tests/sanitize.py --selftest` | GCC <= 12's libstdc++ prints a failed `_GLIBCXX_ASSERTIONS` check on stdout with `__builtin_printf` and aborts; piped, the buffered text is lost, so the probe aborts (SIGABRT) with no visible report and the self-test fails on symmetry's GCC 11.4. Under a pty the report is there. | `s5val4.570030.0/`, `s5val4b.570031.0/selftest_gcc11.json` | Run the probes under a pty or `stdbuf -o0`, or accept SIGABRT plus the report on either stream. | **Fixed** in 86e15f4 (probes on a pty); J-VAL-4 **PASS**, 570166 (`fix/`) |
| F11 | medium (cost; found by J-DES-5 after this run's commit) | `tools/design.py` `split()` | The replicates r of a (sector, L) follow the largest stratum multiplier of the group. At free L8 the 248 primitives are their own cheap stratum: at 1e-3 their continuous Neyman multiplier is 176.8 against 35.1 for the other free L8 graphs, so the group gets r = 128 and the dominant stratum (83% of the cost) runs at 128 replicates where 32 would do. The 1e-3 freeze overshoots (SE 32.63 against 46.0) at 2.98x the continuous Neyman cost; 5e-4 and tighter are within 1.10x. With r taken from the group's costliest stratum (recomputed with design.py's own optimize(), which reproduces the frozen design exactly), 1e-3 costs 1,738 instead of 3,963 lane core-hours (SE 44.2). No numerics change; the design's SE prediction is right, only its cost is too high. | `des5/README.md`, `des5/aperf4.json` (`continuous`) | Choose r from the group's costliest stratum (or the smallest multiplier) and let the cheaper stratum take s > 1; re-run A-DES-1/2/6 and J-DES-5's 1e-3 freeze. A design.py change re-issues H6 (new sha256 for C63d). | **Fixed** in 23540b2 (r from the group's SMALLEST multiplier: `docs/DESIGN.md`, rule 4 and "F11"); recomputed on these freezes: 1e-3 costs 1,738 lane core-hours (SE 44.2), the other targets unchanged (`pre6/`). Follow-up (pre-Stage-6 verifier): with the greedy loop after it the F11 split could end costlier than the Stage-5 split (418 of 20,000 random stratum sets, up to x1.84; not on J-DES-5's strata); fixed with F13 (both splits searched, the cheaper kept) |
| F12 | high (A-ORC-13 on real Slurm; found in the fix round) | `tools/production.py` `stage_graphs` | The pack members were read through Python's default buffer, on BeeGFS the 512 KiB `st_blksize`, so an L8 claim read about 0.70 bytes of neighbouring pack data per staged byte (671 MB per b_free_L8 claim). | `fix/README.md` ("F12"), `fix/fxio.570170.0/claim_io_overread.json` | Read members exactly (`os.pread`). | **Fixed** in d5dfd38; A-ORC-13 **PASS** with no correction, 570212 (0.46 MB against a 2.28 MB tolerance; `close/`) |
| F13 | medium (cost; found by the pre-Stage-6 re-check, `../pre6/`, job 570241) | `tools/design.py` `optimize()` (the greedy target loop) and route (b) | Route-(b) freezes re-optimize the allocation under the `dd+mp256` cost model and over-deliver (SE 35.83 / 18.53 / 9.26 / 5.91 against 46 / 23 / 11.5 / 6.21) at 923 / 3,322 / 13,289 / 33,978 lane core-hours, 1.13-1.44x the exact allocation kept and re-costed (669 / 2,309 / 9,236 / 30,067). The split starts 2.2-9.9% short of the target; at 1e-3, 5e-4 and 2.5e-4 the greedy loop doubles free L7, power L6 and power L5, then free L8 (about half the cost, +48-56%) to close a remaining SE gap of 0.57% or 2.64%; at 1.35e-4 free L6 and then free L7 (+20%) close 1.76%. No numerics change; the SE prediction is right, the cost too high. | `../pre6/README.md` ("Finding F13"), `../pre6/p6_tables.md` | (a) keep the exact allocation in route (b), (b) freeze both ways and keep the cheaper, or (c) a better integer step in `optimize()` (the verifier: a prune pass and a lattice search). | **Fixed** for the Stage-6 inspection: `optimize()` searches from both split rules with a prune pass and a bounded lattice search; route (b) designs both ways and keeps the cheaper feasible design (`docs/DESIGN.md`, rule 4 and "Route (b)"). On these strata: exact 1,702 / 5,740 / 22,961 / 74,573, route (b) 638 / 2,241 / 8,963 / 29,328 lane core-hours (`tests/test_pipeline.py`, `jdes5_records`); **confirmed on symmetry** by the real freezes and test-only plans of 77fab71 (job 570302, `../pre6b/`): the same designs, every cap holds |

**What the findings mean for the next steps.** None blocks the pilot on symmetry's amdq: the pilot runs on one CPU
vendor (AMD), its estimate comes from the measured symmetry model, and the scientific results of every drill were
bitwise reproducible within AMD. F5 rules out mixing Intel and AMD nodes in one campaign until the package enforces
it. F7 and F8 matter for operators (scratch leaks after a cancel; manual removal of stale tables before re-merging a
recovered group). F1-F4 make a whole-node J-VAL-1 and the sanitizer self-test fail on symmetry for reasons outside
the numerics. F9 and F10 are measurement and claim gaps.

## Deviations from the plan's commands (all recorded; none touches the default numerics)

1. **Builds once.** Every executable was built once in `s5build` (amddebugq), and the J-VAL jobs only record the hashes
   before and after (the template's `make -j16 && make gmp && make c7ref && make inspect` would rebuild `bin/ref`
   (`make c7ref` deletes it) while other J-VAL jobs read it). `make test`/`make test-full` still run their `make all
   gmp` prerequisite; nothing was rebuilt.
2. **J-VAL-1/2** were submitted with `-p amdq,amddebugq -t 01:00:00` (template: amdq, 2 h and 4 h) so that either pool
   could start them; both ran on amdq nodes in 13:45 and 4:14. J-VAL-1's commands ran one by one (as Expanse's), each
   with its own record. **J-VAL-4** ran on sharedq (allowed).
3. **Order.** J-SWEEP-2 waited for J-VAL-2 (afterok) and J-VAL-1 (dependency relaxed to afterany once J-VAL-1's only
   failures were the test-portability ones, F1-F3), and ran beside J-VAL-3.
4. **J-SWEEP-3**: "a stratified subset of 1,000 graphs" = `--test-graphs 168 --test-selection stratified` (1,008 L >= 6
   graphs per campaign); `tools/sweep.py` plans `--test-graphs all` only, so the subset was planned with `production.py
   plan` and run by `scripts/s5sweep3_driver.py`, which calls the package's own `sweep.run_indices` (2 x 20 socket
   slots) and `production.py merge`; the job's inline row comparison keyed a wrong column and was rerun as
   `scripts/s5sweep3_rows.py` (the factors had been written first). The J-SWEEP-2 seed is reused, as the plan says;
   no new seed.
5. **Measurement hook.** The smoke (J-SMK-2) and the throughput drill (J-SMK-4) ran with `PYTHONPATH=scripts/rchar_hook`
   and `C8_RCHAR_DIR` exported: a `sitecustomize` that, at the exit of each `production.py run` only, writes rchar and
   the peak RSS of the process and of its children (F9). It changes no argument, file or result (the twin, without the
   hook, reproduces the smoke's batches bitwise).
6. **J-DRL-1**: the first twin worker ran with `TMPDIR` on BeeGFS so that its runtime directories could be observed;
   its pending merge was scancelled first (otherwise it would have started on the incomplete campaign).
7. **J-DRL-2/3** used a dedicated test campaign `drl23-20261005` (the smoke's arguments with `--index-hours 0.5`, so
   that the 20-minute worker meets L8 indices that cannot fit); J-DRL-3 ran first, J-DRL-2 finished the campaign. The
   pending merge of J-DRL-3's worker was held, then scancelled by hand, because a held merge still counts in the H7
   snapshot (admission would have refused J-DRL-2's k = 2).
8. **Drill plans** `drA`/`drB` (2-thread, 8 points, 2 graphs per group, 4 shards) were made on the login node in
   about 30 s each, as C7(2)'s drills were; every bigger plan ran in a sharedq job (`slurm/plan.sh`, role plan).
9. **J-SMK-3**: `--spent-core-hours` is the smoke's own `accounting.py` allocation (24 core-h; the plan's
   "<accounting.py>"). At `--target-rel 1e-3` the freeze was refused by the total-cap gate (design 5,071.9 core-h
   > 5,000) and printed its minimum, so the chain uses `--target-rel 1.5e-3`. The first bundle (`test_smoke1`, the
   minimum K = 1) cannot be combined as the plan asks (combine refused `--partial` with 1 of 1 batches and a final of 2
   batches); its two runs (`desb1`, `desb2`) still show plan --design, run, merge and assembly on real data. The chain
   was then redone from `test_smoke1b` frozen with `--batches 2` (`desc1`, `desc2`).
10. **J-SMK-4** used `--replicates 6` (plan: 4) and `--index-hours 0.25`: with the final binary, 4 replicates give only
    50 core-h (0.8 h of the node), below the plan's 70-90 core-h and its ">= 1 h of L8 work".
11. **Site environment**: pytest 9.1.1 installed into `~/c8d2/venv` (F2).
12. **Extra jobs**: the J-VAL-1 follow-up 570033, the AMD control run of J-SWEEP-3 (570039), A-PERF-5 (570098) and the
    final-binary P4 rerun (570099); all small.

## Seeds (two-log rule)

Every seed drawn here was checked with `seeds.py check` before use, appended to symmetry's `$C8_SEEDS` (`seeds.py add`;
the L=2 control with a label), then merged into Expanse's log and the package mirror `designs/forbidden_seeds.json`
(`scripts/seedsync.sh`; copies and sha256 of both logs after each sync in `seeds/`). The final sync leaves all three
equal as sets.

| Seed | Source |
|---|---|
| 2699695239531018284 | J-VAL-3 L=2 control (registered before submission) |
| 2594661941911898802 | J-SWEEP-2 `sweep2-5d7586e9f1ab` (also J-SWEEP-3, its AMD control and A-PERF-5, which replay its points) |
| 7170939708808771305 | smoke `smoke1-20261005` and its twin (same seed, as the plan says) |
| 2275922613980863695, 2978713193726166216 | lane drills `drA`, `drB` |
| 6667030105805103523 | J-DRL-2/3 `drl23-20261005` |
| 4138143893052926446 | J-SMK-4 `smk4-20261005` |
| 5737719287186326076, 287617163400718873 | J-SMK-3 batches `desb1`, `desb2` (bundle test_smoke1, K = 1) |
| 7957166119201623584, 7778561403992804589 | J-SMK-3 batches `desc1`, `desc2` (bundle test_smoke1b, K = 2) |
| 5945432546144395546 | J-PIL-1 `pilot1-20261005` (planned, not run) |
| 1622484431365770882, 360900140661632644, 472750174076464236, 2207948997111408550 | J-DES-5 dry-run plans at 1e-3, 5e-4, 2.5e-4, 1.35e-4 (test-only, never submitted, deleted); added to symmetry's log by job 570114 and synced into Expanse's log and the mirror afterwards (`seeds/06_des5_*.json`: 78 seeds in each, equal sets) |

## Files

- `README.md` (this file); `setup/` (export checks); `admission/` (every `squeue` snapshot before a manual sbatch, the
  H7 admission lines `h7_admission.jsonl`, `submitted.txt` with every sbatch/scontrol/scancel of this run);
  `logs/` (the Slurm logs of the manual jobs; lane-worker and merge logs are in the campaigns, packed in
  `raw_evidence.tgz`); `scripts/` (every job script and helper, as run from `<SCRATCH>/c8d2/jobs/stage5/`).
- One folder per job (`s5build.570026.0/` … `s5perf5.570098.0/`) and per drill family (`smoke/`, `drl/`, `drills/`,
  `design_smoke1*/`, `design_chain/`, `smk4/`); `seeds/`.
- `raw_evidence.tgz`: the small files of every campaign (manifest, ledger, cost model, Slurm and lane logs, lane state,
  group configs, merged.json, the test result) and the hook records; checkpoints, task databases and task files stay
  on BeeGFS under `<SCRATCH>/c8-d2/`.
- The symmetry cost model `cost_models/gmp_symmetry_amd_c8.json` (J-SWEEP-2 + J-SWEEP-3 factors, sha256 `a1b6e5d2…`) is
  committed at the package root, as the plan's smoke and pilot commands name it.
- Added by the docs agent after this run's commit (2026-10-05): `des5/` (J-DES-5, A-DES-5, with the A-PERF-4 table
  `aperf4.json`), `close/` (A-PERF-5 per (sector, L) and site, opt-in profiles included: `aperf5_table.py`,
  `aperf5.json`, `aperf5_table.md`), `pilot/` (the symmetry pilot's lane schedule, `pilot_lanes.py`/`.json`), `h6/`
  (`write_handoff_design.py`, which writes `LRI_C8_shared/inventory/HANDOFF_design.json`), `admission/h7_ran_on.json`,
  `seeds/06_des5_*.json` and `logs/c8d2-s5des5_570114.out`.
