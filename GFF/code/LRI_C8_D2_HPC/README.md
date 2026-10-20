# C8(2): eighth-order coefficient of the d=2 long-range Ising model (HPC package, in development)

This package computes the thermal coefficient C8(2) "just like C7(2)", one order higher, with C2–C7(2) as
built-in checks. It is a generalization of the Codex-approved C7(2) package `LRI_C7_D2_HPC@a55958f`.

## Production result (2026-10-07)

**C8(2) = 45,990.00 ± 8.22** (estimated sampling SE; relative 1.79e-4, against the 2.5e-4 target of ±11.5).

How to quote it:

> C8(2) = 45,990.0 ± 8.2, where the uncertainty is the estimated sampling standard error. Boundary analysis, supported by
> a multi-prime randomized cancellation verification of all 24,173 integrated kernels, supports finite second moments at
> both production rates and bounded weights for all L7 and L8 kernels. The 4,832 L8 tail warnings are consistent with
> bounded, sharply peaked weights. The variance-inflation calculations are sensitivity scenarios, not error bounds.

The full wording and evidence are in `benchmarks/symmetry_2026-10-c8/production/tailcheck/README.md`, section 1.

How it was computed:
- `C8_final.json` from `tools/combine.py` on the single planned batch (K = 1);
- `verify_result.py`: problem_count 0;
- numerics `dd+mp256` by route (b);
- one symmetry batch: 6.19 million tasks on 8 + 6 EPYC 7543 nodes in two rounds, merge 571153.

Checks:
- **Hard gates.** All pass.
- **Lower orders**, against the C6(2) and C7(2) production values: C3 +1.04, C4 +1.58, C5 +0.39, C6 −0.34, C7 +0.97.
- **Power null rows.** At most +0.47. The power correction is −1.27 ± 2.92.
- **Campaigns a and b.** They agree at 0.44σ.
- **The exact pilot** (45,620 ± 214) is 1.73σ away.

Cost:
- **13,454 allocated core-hours**, η_node 0.983;
- that is ×0.93 the design's 14,465. The plan estimated 12,025 core-hours of work and the busy time was ×1.10 of it.

**The heavy-tail rule** (C63d's, confirmation at ≥ 32,768 points per replicate) flagged 4,832 L8 graphs as "possible
infinite variance". The tail check (2026-10-07, revised 2026-10-08 after Codex's verification) found these to be tail
warnings, not established infinite variance:
- A multi-prime randomized cancellation verification covers all 24,173 kernels: 4 random primes in [2^61, 2^62) and 2
  random points per prime per graph, 0 failures, union-bound error estimate ≤ 10^−53, 9 archived controls passing.
  With the boundary analysis, it supports finite second moments at both rates and bounded weights for every L7 and L8
  kernel.
- The Hill estimate falls with N in every class.
- A fresh nested-N test of the selected main groups is stable: slopes of N·Var over 2^12..2^17 of −0.018
  [−0.051, +0.030] for confirmed free L8 and −0.062 [−0.110, +0.060] for confirmed power L8.
- The 380 double-lift power L8 graphs (0.058% of the measured variance) show rare-peak sampling effects. Inflating their
  variance ×18.9 / ×45 / ×335 gives an SE of 8.26 / 8.32 / 8.97, as sensitivity scenarios, not bounds.
- Every graph stays in the estimand.

Evidence: `benchmarks/symmetry_2026-10-c8/production/result/README.md` and
`benchmarks/symmetry_2026-10-c8/production/tailcheck/README.md`.

**Status (2026-10-06): Stages 1–5 have run; G5 passes except A-EXP-3 (the J-EXP-1 rerun on Expanse). The Stage-6 Codex
inspection returned REVISE four times: round 1 with 23 distinct findings (X1–X23), round 2 with 16 (Y1–Y16), round 3
with 22 (Z1–Z22), round 4 with 21 (W1–W20; with the host's residuals W22–W24). Fix rounds 1–4 fixed all of them (four
owner groups each, an integration and the docs, merged on `c8`; `CHANGELOG.md`, "Stage-6 fix round 1" to "4"). Fix
round 4 has no `src/` change; its merged head passed on symmetry (`benchmarks/symmetry_2026-10-c8/s6fix4/`, jobs
570572-570583, 105.6 core-hours): A-RPL-8 (every executable byte-identical), J-VAL-1, J-GEN-1, G-BK8 under the new row
rule (equal to fix round 3's), the full thread identity, a real gated claim, a claim's memory on a 2-million-task
index (747 MB, 1.27× its estimate, before W9; 70 MB, 0.11×, after), and the `dd+mp256` gate re-run that W18 requires
(job 570574, record `42e6d2d8…`, the same F1/F2/F3 values) with the route-(b) bundles re-frozen (job 570579, the same
designs). Rounds 1 and 2 had no `src/` change, and each merged head
was validated on symmetry (`benchmarks/symmetry_2026-10-c8/s6fix1/`, 39.9 core-hours; `s6fix2/`, 30.3 core-hours);
the fix-round-2 verifier's residuals R1–R3 were fixed and validated there too (`s6res2/`). **Fix round 3 has one
`src/` change** (Z4: `load_graph` refuses truncated G-files; with Z3's compile-time refusal of external `C8_NX_*`
hooks), so every kernel executable changed (symmetry: decimal `a18ce425…`, gmp `7741f733…`, `dd+mp256` `a46f3060…`;
`make c7ref` unchanged). The full exact validation passed on the new executables on symmetry
(`benchmarks/symmetry_2026-10-c8/s6fix3/`, jobs 570533-570542, 95.5 core-hours): J-VAL-2 (all 3,774 kernels exact
against c7ref, point checks), J-VAL-3's exact parts (G-BK8, forced tiers through the new binding, thread identity),
A-RPL-7 against the Stage-3 baseline and the same L8 comparison against a42cfb7's build, all exact; J-VAL-1, J-VAL-4
and J-GEN-1 pass. The `dd+mp256` gate passed again on the new profile build (job 570536, record `a8de4037…`, the same
F1/F2/F3 values), its cost model was re-measured (`18e50440…`) and the route-(b) bundles re-frozen (job 570539). The
pilot is planned (Stage 5) but must be re-planned after Stage 6, and is not submitted. `GMP_PREFIX` is NOT cleared for
production (Y1: its zen2 precision checks are re-run on Expanse together with A-EXP-3).**
- **Stage-6 fix round 4 (W1–W24; no `src/` change).** Acceptance is recomputed coverage, not a status word:
  `quad_differential.py` has a fixed minimum of 10^9 pairs per operation (`--min-pairs` removed; exit 0 passed, 1
  failed, 3 development run; `--check`, W1); `thread_identity.py` says "passed" only for its full configuration and
  gives an `--executable` run its own F5 status (W22); `validate.py --check RECORD --gate J-VAL-1|J-VAL-2|G-BK8|
  G-L8SELF|A-IN-6b` recomputes a record's coverage, and G-BK8 bounds `max_abs`, the tail fields and `tail_argmax` of the
  MP rows with every row field covered by a rule (W2). Build records name their `build_directory`, and the source
  bindings keep relative compiler, include and library words meaning what they meant there (W3; also the J-FLAG
  harness and the profiler's twin). The generator reads G-files strictly as the loader does (W4: ASCII, the loader's
  header bounds; W5: raw-byte identity; also `gen/kirchhoff.py`) and `check_edge_forests` checks every extraction (W6).
  A claim refuses `LD_PRELOAD`, `LD_AUDIT` and `LD_DYNAMIC_WEAK` (exit 64; `/etc/ld.so.preload`'s order and
  `GLIBC_TUNABLES` enter the runtime identity, W7). A gated profile executable runs only with the libgmp its gate
  validated, checked by every claim, merge and `calibrate.py` (W8). A claim streams its task file one block at a time
  and `est_peak_bytes` counts one block of rows and the plan metadata (W9). `calibrate.py` validates every checkpoint
  before it reads a timing (W10; the accounting's busy time of unmerged groups too) and a calibration row serves only
  its own numerics and rates identity (W11). `design.py` searches past 64 batches when `--batches` asks (W12).
  `verify_delivery.py` runs `verify_result.py` on every delivered C8 result record (W13). The test harness owns
  process groups after their leader exits and the in-process launch cases (W14, W15). Docs: a production batch is
  planned in a plan job (W16); the examples source the site environment before expanding `C8_SEEDS` or `C8_DATA`
  (W17). **A J-FLAG gate record carries the authenticated input set it ran on** (W18; `check_gate` compares it with the
  pilot's or plan's inputs manifest, route (b) with the bundle's), so the 570536 record is refused and the gate ran
  again (job 570574). Without perf, P1 runs the release worker on every block, and P3 binds the ratio-histogram build to the
  release worker (W19). F2 reserves its seeds in one locked transaction (W20). `assemble.py` and `combine.py` read the
  bundle metadata once from verified bytes (W23); the 570539 bundles are under test (W24).
- **Stage-6 fix round 3 (Z1–Z22).** The precision tools test the worker's own code: forced tiers, point checks and
  class B are compiled from a source snapshot in which the worker is first rebuilt byte for byte (Z1), and a forced-tiers
  record says "passed" only with the complete A-RPL-5 coverage (`forced_tiers.py --check`, Z2). External `C8_NX_*`
  hooks no longer compile, every build record lists the macros in effect (`macro_overrides`), and a non-test plan
  needs a valid build record of its executable (Z3; never copy a worker without its `.build.json`). `load_graph`
  refuses truncated G-files instead of reading an unassigned value (Z4: the one `src/` change; valid inputs give the
  same outputs bit for bit). The generator's G-file gate reads tokens as the loader does (Z5); preloaded libraries are
  part of the runtime identity (Z6; since fix round 4 a claim refuses `LD_PRELOAD` outright, W7); inherited `SBATCH_MEM_*` follow sbatch's precedence and every job is checked
  before the first submission (Z7); `verify_result.py` requires a symmetric positive semidefinite covariance and
  nonnegative SEs (Z8); `design.py report --bundle` verifies the bundle and reports its SE at its own frozen settings
  (Z9, Z10); `seeds.py init` takes the lock (Z11); nested α keeps each graph's point ratio (Z12); the subprocess tests
  clean up on every path (Z13). Docs: tail confirmation runs a report with the higher-point campaign as `--pilot`
  (Z14); **a non-test `production.py plan` registers its own seed** (Z15); production-size plans run in plan jobs
  (Z16); the symmetry pilot window starts with a probe (Z17); `make c7ref` does link GMP (Z18). A reused F1 baseline
  must name its libgmp, and `check_gate` requires both F1 tools' libgmp provenance (Z19: the 570373 record is
  refused). The profiler fails P1 when the release and tier-timer rows differ (Z20), checks `--expect-sha256` in
  every mode before any output (Z21) and keeps `--keep-perf-data` (Z22).
- **Stage-6 residuals after fix round 2 (R1–R3).** The test harnesses launch their native programs in the controlled
  OpenMP environment too: `tests/validate.py` (its A-RPL-6 1-against-4-thread runs also observe their teams and fail
  without the requested one), `tests/sanitize.py`, `tests/forced_tiers.py`, `tests/numerics_flags.py`'s F1 tool,
  `tests/quad_differential.py` and `tools/prepare_inputs.py`'s inspector (R1, R2). `verify_result.py` gives a pull the
  tolerance its inputs' tolerances imply and requires it to be the pull of its own stored inputs (R3; the Stage-5
  design-chain partial now verifies on the Mac). The generator's class reader no longer reserves a hostile header's NG
  rows up front (low).
- **Stage-6 fix round 2 (Y1–Y16).** The precision tools (forced tiers, point checks, class B; at the integration also
  the sanitizer's point_checks tool and the profiler's debug-info twin) are bound to the GMP of the worker they speak
  for, and `GMP_PREFIX` is NOT cleared for production (the Stage-5 clearance is withdrawn) until the zen2 precision
  checks are re-run on Expanse (Y1). Every native launch gets one controlled OpenMP environment, and a worker that does not show its
  requested team is stopped (Y2; the generator programs too). The generator checks edge counts before forming any
  product (Y3); `tools/vendor_assembly.py` refuses a symlinked `VENDORED.json` and removes what it wrote when a write
  fails (Y4); `make inputs-l8` installs both packs or neither (Y5). A production worker's runtime fingerprint must be
  complete (Y6); the lane memory limit is the minimum over the cgroup hierarchy (Y7); a first checkpoint without a
  fingerprint makes the merges refuse (Y8). A production design never assumes an efficiency (Y9); the allocation
  options and a bundle's replicates are checked against the production bounds (Y10); `verify_result.py` checks types
  first and takes tolerances from designated fields only (Y11). A sweep resumes only the campaign it was asked for
  (Y12) and registers its seed right after its plan (Y13). `tests/ast_scan.py` checks lambda and comprehension scopes
  (Y14), the atomic-plan test observes the write phase (Y15), and the lane example of `docs/HPC.md` fits the default
  AMD-pool cap (Y16).
- **Stage-6 fix round 1 (X1–X23).** The J-FLAG gate record must now carry its F1 coverage, the build binding of its F1
  tools to both executables and the observed OpenMP team sizes (X1–X3): the 570210 record lacks them and is refused
  by `design.py check_gate`, so the `dd+mp256` gate was re-run on symmetry with the fixed harness and the route-(b)
  bundles re-frozen with the new record (`benchmarks/symmetry_2026-10-c8/s6fix1/`). A campaign also pins its run-time
  library stack (`RUN/runtime_identity.json`, X8), carries a copy of its design bundle (X9), and checks the cost
  model's numerics in every non-test plan (X10). The other items: `make inputs-l8` repairs corrupt L8 packs (X4); H1
  and publication accept only complete regression and gate evidence (X5); the generator validates class files before
  any output (X6); `tools/vendor_assembly.py` contains its paths and authenticates the read set (X7); an explicit
  `C8_AMDQ_CAP` survives `env.sh` (X11); `--account`/`--partition` reach every sbatch (X12); the lane failure limit is
  rechecked under the claim (X13); a c8-d2 pilot's `--two-loop`/`--inventory` overrides are authenticated (X14);
  accounting is incomplete while any allocation is live (X15); `verify_result.py` checks dimension, epsilon and half_d
  (X16); `tests/ast_scan.py` and the delivery test close their blind spots (X17–X20); `seedsync.sh` exits nonzero until
  the three seed logs agree (X21); the runbook and quickstart (X22, X23).
- Stages 1–3: the inventory handed off (H1), the vendored assembly (G-H2), the order-8 inputs (G2a/b), the native
  kernel (Stage 3A: `bin/c8d2_{decimal,gmp}` replay C7(2) bit for bit at order 7) and the orchestration, design and
  statistics (Stage 3B, tag `c8-stage3`; `docs/HPC.md`, `docs/DESIGN.md`; `benchmarks/expanse_2026-10-c8/README.md`).
- Stage 4: the profiles (G4a); the default-path optimizations R5a, R5b and R3a (G4b; the default binary is
  `numerical_change: false`); the opt-in numerics profiles `dd`, `mp256`, `exp1` and their combination and the R7 rate
  maps (G4c). All are off by default. **The user approved `dd+mp256` for production after the pilot** (2026-10-05);
  `exp1` and R7 stay off (`docs/NUMERICS.md`, "User decision").
- Stage 5: the final validation, sweeps, L8 smoke, drills, design chain and throughput drill on symmetry, J-EXP-1..4
  and J-SWEEP-2E on Expanse, and the production-size design dry run J-DES-5
  (`benchmarks/symmetry_2026-10-c8/stage5/README.md`, `benchmarks/expanse_2026-10-c8/stage5/exp/README.md`). Every
  exact numerical gate passed on both sites. The cost models of the final binary are
  `cost_models/gmp_symmetry_amd_c8.json` and `cost_models/gmp_expanse_amd_c8.json`; the refined cost-versus-target
  table per site is in `docs/PERFORMANCE.md`, "Stage 5: the refined cost table".
- **G5 findings.** F1–F10 and F12 are fixed and validated: F1–F9 in 86e15f4 (merged as e7e6589), re-validated on
  symmetry (`benchmarks/symmetry_2026-10-c8/stage5/fix/`); F12, the pack over-read found there, in d5dfd38, with
  A-ORC-13 passing on real Slurm (job 570212) and J-VAL-1 passing (570211) on it
  (`benchmarks/symmetry_2026-10-c8/stage5/close/`); F10 is documentation (speedups quoted per site);
  `tools/calibration.json` holds symmetry's J-SWEEP-2 rows (86e15f4). **F11 is fixed in 23540b2**: `tools/design.py`
  takes each (sector, L)'s replicates from its smallest multiplier, and the 1e-3 design costs 1,738 instead of 3,963
  lane core-hours on symmetry (`docs/DESIGN.md`, "F11"). **F13 and the F11 follow-up are fixed for the Stage-6
  inspection**: `design.py`'s integer allocation is searched from both split rules with a prune pass and a bounded
  lattice search (never costlier than either old rule; J-DES-5's exact designs 1,702 / 5,740 / 22,961 / 74,573 lane
  core-hours), and a route-(b) freeze keeps the cheaper of its re-optimized design and the exact design re-costed
  (`docs/DESIGN.md`, rule 4 and "Route (b)"); confirmed on symmetry with the real freezes and test-only plans of
  77fab71 (job 570302, `benchmarks/symmetry_2026-10-c8/pre6b/`: the same designs, every cap holds). **The allow-lists now bind every non-test plan**: numerics outside
  `production.APPROVED_PROFILES` = {`dd+mp256`} and any R7 map (`APPROVED_RATES` is empty) are refused; a non-test
  pilot runs exact at the default rates (`APPROVED_PROFILE_PILOTS` is empty: the smoke and the pilot stay exact); and
  every non-test plan whose numerics are not exact runs only a build a passed full-scale J-FLAG gate record covers
  (route (b): the bundle's gates; otherwise `plan --numerics-gate`). Status per
  finding: `benchmarks/symmetry_2026-10-c8/stage5/README.md`, "Findings".
- **`dd+mp256`.** The approved build's J-FLAG gate **passed** on symmetry (job 570210: F1 dd max error 5.18e-12, F2
  |dC8| + 3 SE_d = 4.25e-16, F4 ×2.530), and passed again with the Stage-6 fix-round-1 harness (job 570373, the same
  build `d5df32ac…`, the same F1/F2/F3 values, F4 ×2.539). Fix round 3 replaced that build (Z4) and requires the
  libgmp provenance in the record (Z19), so the gate ran again on the new build `a46f3060…` and **passed** (job 570536,
  record `benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json`, sha256 `a8de4037…`: F1, F2 and F3 equal to 570373's field by field, F4 ×2.517); that record
  was the one `design.check_gate` accepted until fix round 4, and the profile cost model below was re-measured with
  the new build (job 570538, `18e50440…`; `benchmarks/symmetry_2026-10-c8/s6fix3/`). Fix round 4 (W18) requires the
  authenticated input set in the record, which 570536's predates, so the gate ran once more on the same build with a
  fresh F1 baseline and **passed** (job 570574, record `benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json`, sha256 `42e6d2d8…`, inputs manifest
  `3813f24a…`; F1, F2 and F3 equal to 570536's apart from task timings, F4 ×2.574): that record is the one `check_gate`
  accepts now, and the route-(b) bundles were re-frozen with it (job 570579; the same designs). Production from the exact pilot is **route (b)**, implemented in 23540b2:
  `design.py freeze --numerics dd+mp256` re-costs the exact pilot's design with a cost model measured under the
  profile and keeps the pilot's variance; `plan --design` still needs `--approved-numerics-change` and a gated build
  (`docs/DESIGN.md`, "Route (b)"). Measured on symmetry before Stage 6 (`benchmarks/symmetry_2026-10-c8/pre6/`, jobs
  570239-570241, 12.6 core-hours): the profile cost model `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (×2.81 over
  the exact model; L8 ×2.75 free, ×2.97 power); the exact allocation re-costed with it costs ×0.385–0.394 of the exact
  path at every target, but the 23540b2 route-(b) freeze re-optimized the allocation and cost ×0.44–0.57,
  over-delivering the SE (**finding F13**, now fixed: on J-DES-5's strata a freeze keeps 638 / 2,241 / 8,963 / 29,328
  lane core-hours, ×0.375–0.393 of the new exact path). The F11-fixed 1e-3 freeze measured 1,738 lane core-hours
  (`docs/PERFORMANCE.md`).
- **Sites: symmetry first** (user rule, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry
  is not enough"). On Expanse (32e5f2b, `benchmarks/expanse_2026-10-c8/pre6/`): the **two-log seed sync is done**
  (Expanse, symmetry and the mirror `designs/forbidden_seeds.json` hold the same 90 seeds; the 8 seeds symmetry's
  pre-Stage-6b check added since, the 5 of Stage-6 fix round 1 and the 2 of fix round 2, 105 in its log and the
  mirror, are pending for Expanse's, listed in
  `benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`); the **J-EXP-1 rerun
  (A-EXP-3) is partial**: job 54681003 passed the build, A-RPL-8, `check_venv --strict`, `validate` and 12
  `unit_orchestration` groups, then was cancelled after 20:50 of its 30 minutes because Expanse's Lustre was failing
  (debug nodes drained by Lustre health checks); F1, F3 and F4 of `make test` were not reached. A-EXP-3 is to be
  completed after Stage 6, on the post-inspection commit (a fresh export). The user-approved deletion of the obsolete
  Expanse exports is done (29 of 30; `benchmarks/expanse_2026-10-c8/README.md`).
- The pilot is planned on both sites and NOT submitted. It waits for Stage 6, the user's authorization and a window
  agreed with C8(3). The tool changes above (86e15f4, d5dfd38, 23540b2 and the Stage-6 fix of `production.py`'s
  allow-lists) change pinned tools, so it will be re-planned with a fresh seed (`docs/HPC.md`, "Pilot runbook"). After
  it: `docs/DESIGN.md`, "After the pilot".
- The design tool is handed to C8(3) (H6): `LRI_C8_shared/inventory/HANDOFF_design.json`. `tools/design.py` changed
  in 23540b2 (F11 and route (b)) and again for Stage 6 (F13: the optimizer, route (b)'s keep-cheaper); the handoff is
  re-issued after Stage 6.

No physical C8(2) value is produced or claimed
by this package at any stage of the plan; the plan ends with a validated package, an L8 smoke campaign and a
planned (not submitted) pilot.

- **Contract.** `LRI_C8_D2_HPC_loop/PLAN.md` (revision r3, sha256 `14493ca4…`, approved by Codex plan review
  round 4). The plan's stages, gates (G0, G1, G-H2, G2a/b, G3–G6) and acceptance criteria (A-*) govern every
  change. Loop artifacts (reviews, build summaries) live in `LRI_C8_D2_HPC_loop/`, outside this checkout.
- **History.** `git log`: tag `c8-base` (= C7(2) at a55958f), tag `c8-rb` (review base: the C7(2) package plus
  verbatim external sources and data), then the C8(2) work. Commits are local only; the repository has no remote.
- **Documentation.** `docs/HPC.md` (cluster runbook: lanes, arrays, admission, ledger, seeds, sweeps, the pilot
  runbook), `docs/DESIGN.md` (pilot → Neyman design, defaults, targets, budgets, batches, rate maps, the post-pilot
  decision step), `docs/NUMERICS.md` (the vendored
  assembly, the native kernel, the orchestration contract, then the retained C7(2) contract), `docs/PERFORMANCE.md`.
  The C7(2) documents are in `docs/c7_historical/` (`README_C7.md`, `HPC_C7.md`, `PERFORMANCE_C7.md`), and the C7(2)
  part of `CHANGELOG.md`. The C7(2) benchmark and profiling tools (`tools/benchmark*.py`, `tools/prepare_benchmarks.py`,
  `tools/profile.py`) are generalized in Stage 4: Stage 4a adds the order-8 fixtures (`benchmarks/fixtures8/`,
  `prepare_benchmarks.py --order 8`), `tools/perf_profile.py` (P1–P3), `tools/benchmark.py --lane-shapes` (P4) and
  `--interleave-probe`, and the job scripts (`docs/PERFORMANCE.md`, "Stage 4a").

## Method (unchanged from C7(2))

The C7(2) finite zero-momentum scheme and mixed local-mass-forest kernel; loop L carries its Taylor jet
through z^(8−L) (z^5 at L=3 down to z^0 at L=8); the power sector is integrated explicitly and
Δ_pC8 = F8(f+p) − F8(f) is reported. Default numerics are the C7(2) precision policy, bit for bit wherever the
kernel is unchanged; every numerics-changing speedup is an opt-in flag, off by default.

Workload at L3–L8 (both sectors): 24,173 kernels, 7× C7(2); L8 alone has 16,064 power-free kernels (248
primitive) and 4,336 power kernels.

## Layout

| Path | What |
|---|---|
| `gen/` | The d=2 payload generator (component A): 128-bit class keys, n=9, the parity rate rule; regression, gate and publication scripts for the shared inventory `inventory8_d2/` |
| `gen/SOURCES.json` | Pins of every external source copied into the review base; `gen/check_sources.py` verifies them |
| `reference/c8d1_inputs8/` | C8(1) class lists 1..8, the L7/L8 inventories and verification sets (LRI_C8_HPC@78e6a8a), byte copies |
| `reference/c7d2_hpc_a55958f/` | The C7(2) sources and inputs the replay gates and `make c7ref` need, byte copies |
| `reference/c7d2_production_2026/` | Manifest, group configs, merged records and result of the 2026 C7(2) production |
| `reference/SHA256SUMS_c8` | sha256 of every file in the three directories above (paths relative to `reference/`) |
| `reference/LRI_C7_d2_progress/`, `reference/power_mass/` | The original C7(2) free and power sector packages (unchanged; `reference/SHA256SUMS`) |
| `vendor/c8_assembly/` | C63d's order-8 assembly, byte copies of every file `HANDOFF_assembly.json` lists, plus the HANDOFF; never an input (PLAN "One rule governs reads of vendor/") |
| `vendor/c8_assembly_fixtures/` | The `LRI_ROOT` tree of the vendored tests: pinned byte copies of the external files they read |
| `tools/VENDORED.json` | The vendored pins, the fixture provenance, the review record and the interface signatures (`tools/vendor_assembly.py` writes it) |
| `inputs/` | The order-8 inputs (Stage 2a): `gamma_d2_8.txt`, `two_loop.json` (7 B2 strings), `verification/`, the L3–L7 packs (L8 packs built by `make inputs-l8 INVENTORY=...`, not in git), `inventory.json` and `manifest.json` |
| `tools/make_lowloop.py`, `tools/prepare_inputs.py`, `src/c8d2_inspect.cpp` | The input generators (`make inputs`, `make inputs-l8`, `make inspect`) |
| `tools/assemble.py`, `tools/combine.py`, `tools/verify_result.py` | The assembly on the vendored module (Stage 2b) |
| `src/c8d2_integrate.cpp`, `src/kernel.hpp`, `src/quadfast.hpp`, `src/diagnostics.hpp` | The order-7/8 native worker (Stage 3, component C; `docs/NUMERICS.md`; `quadfast.hpp`: the binary128 tier's inline add/sub/mul, Stage 4b R3a): `make`, `make gmp`, `make profile ratiohist sanitize`, `make c7ref` |
| `src/numerics/` | The opt-in numerics profiles (Stage 4c, PLAN D1/A-FLAG): `numerics.hpp` (hooks, tiers, profile name) and the profile headers `dd.hpp` (R3b double-double tier), `mp256.hpp` (R4b staged 77-digit MP tier) and `exp1.hpp` (R4c one exponential per shifted call), each a **numerics change** (D1): built only by `make gmp NUMERICS=<p>[,<p>...]` as `bin/c8d2_gmp_<p>`, used only by `plan --numerics <p> --approved-numerics-change`; full-scale J-FLAG results and projected core-hours in `docs/NUMERICS.md`, "Stage 4c gate: J-FLAG results (A-FLAG-7)"; the default build never includes them |
| `tests/numerics_flags.py`, `tests/numerics_f1.cpp` | The A-FLAG-3 F-gates of a profile (F1 accuracy against 450 digits, F2 paired mini-campaign dC8, F3 promotions, F4 speed, F5 thread identity; `--self-test`); job scripts and the Mac driver in `benchmarks/expanse_2026-10-c8/stage4c/scripts/` |
| `tests/quad_differential.py`, `tests/quad_differential.cpp`, `tests/quad_ranges.cpp` | R3a's proof: `src/quadfast.hpp` against libgcc bit for bit on the kernel's operand ranges, random pairs and edge lists (`make quaddiff`) |
| `tests/validate.py`, `tests/check_points.py`, `tests/forced_tiers.py`, `tests/thread_identity.py`, `tests/sanitize.py` | The native gates (A-KER, A-RPL, A-IN-6(b)) |
| `tools/production.py` | Plan (24 groups; `--pilot` or `--design`), run one index, status, recover, merge (`--jobs`, bounded fan-in) |
| `tools/claim_io.py` | The real-Slurm reads-per-claim comparison (R07, A-ORC-13) from the `claim_io` lines `production.py run` logs at exit |
| `tools/lanes.py`, `tools/slurm_submit.py`, `slurm/*.sh` | Lane mode, arrays, the guarded submission path with the admission rules (H7E-R on Expanse, the AMD-pool cap on symmetry), the job templates (`lane_worker.sh`, `run_array.sh`, `merge.sh`, `plan.sh`, `sweep.sh`, `submit.sh`, `resubmit.sh`) |
| `tools/sweep.py`, `tools/make_cost_model.py`, `tools/calibrate.py` | The cost-model sweep (bootstrap first, R13; `--numerics P` measures an approved profile's model for route (b)), the campaign-keyed cost model (it records the campaign's numerics and rates identity) and calibration |
| `tools/ledger.py`, `tools/accounting.py`, `tools/seeds.py` | The allocation ledger, sacct accounting and η_node (R10), the forbidden-seed log (D9) |
| `tools/design.py` | Pilot → Neyman design: report (targets, strata, tails), freeze (bundles; r per (sector, L) from its smallest multiplier, F11; the integer allocation searched from both split rules with a prune pass and a bounded lattice search, F13; route (b): `--numerics dd+mp256` from the exact pilot, re-costed, the cheaper of the re-optimized and the kept exact design), rates (provisional maps) |
| `tools/stage_runtime.py` | Node-local staging of one index (pack members only) |
| `tests/unit_orchestration.py`, `tests/test_pipeline.py`, `tests/merge_scale.py`, `tests/ast_scan.py`, `tests/workflow.py`, `tests/staging.py` | The orchestration, design and pipeline tests (component F) |
| `tests/check_venv.py` | The Python environment check (G0 with `--strict`; first step of `make test-python`) |
| `tests/test_numerics_flags.py`, `tests/test_dd_profile.py`, `tests/dd_accuracy.cpp` | The Stage-4c framework on the Mac: the profile builds (`make -n`), the hook contract and the profile headers, the F-gate harness on fake workers, the job scripts; the dd profile's double-word arithmetic against mpmath (Mac) and 120 digits (`dd_accuracy.cpp`, Expanse) |

Verify the reference copies: `cd reference && sha256sum -c SHA256SUMS_c8` (macOS: `shasum -a 256 -c`), and all
pins including the review base: `python3 -B gen/check_sources.py`. The delivery: `python3 -B tools/verify_delivery.py
--strict` checks every payload file against `DELIVERY_MANIFEST.json`/`SHA256SUMS` and, since fix round 4 (W13), runs
`tools/verify_result.py` on every delivered C8 result record the manifest lists (`result_records`; numpy needed).

## Quickstart

```bash
make && make gmp && make inspect && make c7ref        # bin/c8d2_{decimal,gmp}; the L8 packs: make inputs-l8 INVENTORY=...
# make inputs-l8 also repairs a corrupt or truncated L8 pack (X4): it checks every input that must not change, rebuilds
# both packs into temporary files and installs them only when both match their pins (prepare_inputs.py --l8 [--folder DIR]);
# a pack target that is not a regular file is refused first, and the two are installed all or nothing (Y5)
# optional (R4f): make -B gmp GMP_PREFIX=/abs/gmp-prefix  # the gmp worker against another GMP 6.2.1; NOT cleared for
#                                                        # production (Y1; docs/NUMERICS.md, "Builds")
# opt-in numerics (Stage 4c; off by default, D1): make gmp NUMERICS=dd   # bin/c8d2_gmp_dd; plan --numerics dd needs --approved-numerics-change
C8_ALLOW_NO_L8=1 make test-python                     # the Mac: pure-Python tests (orchestration, pipeline, scans, merge scale, vendored
                                                      # assembly). A checkout has no L8 packs, and check_inputs refuses that without
                                                      # C8_ALLOW_NO_L8=1; on a cluster build the packs (make inputs-l8) and never set it
make test                                             # J-VAL-1 on a cluster: native subset, the above, real-worker workflow and staging
# 1. the first cost-model sweep (one whole node; docs/HPC.md): slurm/sweep.sh ... --bootstrap-chunk 512 --shards 8
# 2. a pilot with the measured cost model, planned in a plan job (never on the login node: production-size plans
#    refuse to run without SLURM_JOB_ID), run in lanes, merged. A non-test plan registers its own seed in its first
#    --forbid-seeds-from log ($C8_SEEDS) before it publishes the campaign (Z15); then sync the other site's log and the
#    mirror (docs/HPC.md, "The seed log"). Wait for the plan job to succeed before submitting workers.
#    First source the site environment in THIS shell (W17): it sets C8_SEEDS, which the commands below expand before
#    anything is submitted; the guard stops here if it or the export or the campaign path is unset.
source ~/c8d2/env.sh                                  # symmetry; Expanse: source ~/c8d2/env_expanse.sh
: "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?the export}" "${RUN:?the new campaign directory}"
sbatch [site options: docs/HPC.md, "Plan jobs"] --export=ALL,C8_PACKAGE="$C8_PACKAGE" "$C8_PACKAGE/slurm/plan.sh" "$RUN" \
  --pilot --points 4096 --replicates 8 --cost-model CM --forbid-seeds-from "$C8_SEEDS" --seed <fresh>
C8_RUN="$RUN" "$C8_PACKAGE/slurm/submit.sh" --lanes 2  # workers + one merge; production.py status "$RUN"
# 3. the design and its batches
python3 -B tools/design.py report --pilot "$RUN"
python3 -B tools/design.py freeze --pilot "$RUN" --out BUNDLE --target-rel 2.5e-4 --seeds-log "$C8_SEEDS"
sbatch [site options] --export=ALL,C8_PACKAGE="$C8_PACKAGE" "$C8_PACKAGE/slurm/plan.sh" BATCH_1 \
  --design BUNDLE --cost-model CM --forbid-seeds-from "$C8_SEEDS" --seed <fresh>    # 5-8 million tasks: a plan job
# after the plan job succeeded (and the seed sync): lanes, merge, then
python3 -B tools/assemble.py BATCH_1 && python3 -B tools/combine.py BATCH_1 ... BATCH_K --output OUT
```

## The inventory generator (Stage 1)

Generation and its regressions run on x86-64 Linux only (symmetry): long double prints differently on arm64.

```bash
make -C gen                     # bin/gen/{build_free,build_power,check_edge_forests,test_keys}
python3 -B gen/test_keys.py     # A-INV-1: the checked 128-bit reader; the generators' semantic validation (X6, test_keys --generator);
                                # a UBSan part (Y3; about 10 s, needs -fsanitize=undefined; --no-ubsan is a recorded skip)
python3 -B gen/regress.py --classes reference/LRI_C7_d2_progress/reference --threads 1,8 --explain   # A-INV-2
python3 -B gen/test_regress.py  # A-INV-2's comparison logic without the builders (any platform; also in make test-python)
```

The generator programs (`build_free`, `build_power`, `check_edge_forests`) read class files through
`read_generator_classes` (Stage-6 X6): before any output and before any OpenMP region, each file must have 2 ≤ n ≤ 9,
NG ≥ 1, exactly 2L edges, every vertex degree ≤ 4, a connected graph, aut, orbit ≥ 1 with aut·orbit = n!, D_G computed
without overflow and no repeated key; an error names the file, the row and the defect (exit 2). Since Stage-6 fix
round 2 (Y3) the decoding pass only adds up edge counts and degrees: no product is formed before the edge-count,
degree, connectivity and aut/orbit checks pass, and D_G is computed in the builders' order with checked
multiplication, so a hostile key (2^72−1 at n=9) is refused with exit 2 instead of a signed overflow. The generator
programs run in a controlled OpenMP environment (`regress.builder_env`; `gen/run_l8.sh` and the `slurm/gen/` scripts
unset inherited `OMP_*`, `GOMP_*` and `KMP_*` controls), so an inherited `OMP_THREAD_LIMIT` cannot turn A-INV-2's
thread-identity check into a comparison of two serial runs (Y2's class, integration). `regress.py` refuses
an empty, reversed, repeated or out-of-range `--loops` (3..7) or `--threads` before building anything, and records its
`coverage`; the H1 handoff (`gen/handoff_inventory.py`) and `gen/publish_inventory.py` accept only complete evidence
(`regress.h1_problems`: loops 3..7, at least two thread counts including 1, every build, sector row and control;
`gates.summary_problems`: exactly the eleven gates, all true, each with its passed record), so an A-INV-2 record from
before CK-K02's header-row check (Expanse 54631551) is refused and a new H1 revision cites 54658874 or a newer J-GEN-1
record (X5). The structural G-file gate (`gen/gates.py` `check_gfile`, A-INV-3(j)) reads tokens as the native loader
does (Z5, Stage-6 fix round 3): masks are plain ASCII decimals in [0, 2^E) with L edges, in ascending order, and term
entries plain decimals within the loader's int range (`gfile_ints`); a negated mask, `+m`, `0_m`, a coefficient of 2^31
or `1_0` passed before. Since fix round 4 one strict reader serves the gate, `regress.py` and A-INV-3(h)'s
`gen/kirchhoff.py` (`regress.gfile_text`, `parse_gfile`): only LF, spaces and printable ASCII (a no-break space, a tab,
CR or U+001C between tokens is refused, W4), the loader's header bounds (1 ≤ M ≤ 16384, 1 ≤ T ≤ 10000), and A-INV-2's
"identical" compares raw bytes (CRLF is a difference, W5); `check_edge_forests` checks every extraction of an existing
file and fails that graph on a malformed one (W6).

The Slurm jobs are `slurm/gen/regress.slurm` (J-GEN-1), `slurm/gen/build_l8.slurm` (J-GEN-2: L7+L8 build, gates
A-INV-3, staged publication) and `slurm/gen/crossnode.slurm` (J-GEN-3: Intel rebuild, A-INV-4). The layout and
checksum hierarchy of the published tree are documented in `gen/publish_inventory.py` and recorded in each tree's
`MANIFEST.json`; `gen/verify_inventory.py --pin <MANIFEST sha256>` verifies a copy.

## Shared work with C8(3) (session C63d)

- `LRI_C8_shared/inventory/` (owner: this package): `inventory8_d2/`, `HANDOFF_inventory8_d2.json`,
  `DECISIONS.md`.
- `LRI_C8_shared/assembly/` (owner: C63d): the order-8 assembly, delivered by `HANDOFF_assembly.json` (sha256
  `f5ff6a35…`, 2026-10-03) and reviewed by C62d (`LRI_C8_shared/inventory/reviews/order8_assembly_f5ff6a353371.json`,
  ACCEPT_WITH_MINOR). It is vendored byte-identically under `vendor/c8_assembly/`, pinned in `tools/VENDORED.json`
  and `docs/NUMERICS.md`; `tests/check_vendored.py` and `tests/vendored_isolated.py` check it (A-ASM-1). A
  re-vendoring runs `tools/vendor_assembly.py --agent-lri DIR --expect-sha256 <HANDOFF sha256>
  --expect-read-set-sha256 <reviewed external read set sha256>` (Stage-6 X7; the current read set is `7b14f50a…`,
  the value `tools/VENDORED.json` records): the read set is authenticated before it is parsed, every destination path
  is checked before the first write (relative and canonical, unique ignoring case, inside its vendor root with no
  symlink on the way, not already present) and files are created exclusively. Since Stage-6 fix round 2 (Y4) the
  metadata file `tools/VENDORED.json` is checked like every other destination (contained, no symlink on the way, a
  dangling symlink included) before anything is read, staged with the other files and written last, exclusively; if
  any write fails, every file and directory the run created is removed.
