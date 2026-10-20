# Changelog

# C8(2) (branch c8; plan `LRI_C8_D2_HPC_loop/PLAN.md`, sha256 14493ca4…)

Identifiers in brackets are the plan's acceptance criteria, gates and jobs. No physical C8(2) value is produced
or claimed by any entry below.

## 2026-10-06: Stage-6 fix round 4 validated on symmetry: A-RPL-8, J-VAL-1, J-GEN-1, W2/W7/W8/W9/W22 on real nodes; the `dd+mp256` gate re-run for W18 and route (b) re-frozen [A-RPL-4/6/8, A-INV-1/2, A-FLAG-3, A-DES-5, A-ORC-1..13]

`numerical_change: false`; no `src/` change. Exports of 392ed22 (`pkg/392ed22d1d02`, jobs 570572-570579) and 900e590
(`pkg/900e5906522a`, jobs 570582-570583; a tests-only fix and corrected job scripts, the same executables), symmetry
only, 10 job records, 105.56 core-hours (`benchmarks/symmetry_2026-10-c8/s6fix4/`, README there).
- **A-RPL-8 PASS** (570572, again 570582): every executable byte-identical to fix round 3's (decimal `a18ce425…`, gmp
  `7741f733…`, `dd+mp256` `a46f3060…`, ...; the sanitizer builds equal after normalizing); every build record names its
  `build_directory` (W3).
- **J-VAL-1 PASS** (570583 on 900e590; `make test` exit 0: unit_orchestration 87 tests on Linux with the real worker,
  test_numerics_flags 14, test_native_guards 7/7, test_gmp_binding 16, ...; `validate.py --check --gate J-VAL-1` exit
  0; verify_result_tamper 206/206, combine_core 14/14, `assembly_checks --exact` 37/37). 570573 on 392ed22 stopped at
  `tests/test_numerics_flags.py` `w18_inputs`: `os.link` from the BeeGFS export to node-local `/tmp` failed (EXDEV),
  fixed in 900e590 (a symbolic-link fallback); every step before it and every extra step passed there.
- **W2 on real rows PASS** (570573): G-BK8 under row rule `c8-d2-bk8-row-rule-2`, `--check --gate G-BK8` exit 0, every
  test equal to fix round 3's 570535 record (MP rows' maximum normalized difference 0). **W22 PASS**: the full thread
  identity "passed" with its coverage, `--check` exit 0. R1's hostile-environment invariance PASS (24 rows, teams
  observed).
- **J-GEN-1 PASS** (570575): test_keys 146/146 with W6's malformed G-files in the plain, UBSan and ASan builds;
  test_regress 129/129; A-INV-2.
- **The `dd+mp256` gate PASSED again on the same build with a fresh F1 baseline** (570574): record
  `benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json`, sha256 `42e6d2d8…`, inputs
  manifest `3813f24a…` verified at the start and the end (W18); `check_gate` accepts it with the export's inputs and
  refuses 570536's for exactly the missing input identity; F1, F2 (4.25e-16) and F3 equal to 570536's apart from task
  timings; F4 ×2.574.
- **Route-(b) re-freeze** (570579): the four bundles' `design.json` byte-identical to 570539's; the gate entry carries
  the inputs manifest; the four test-only plans pass route (b) with `gate_gmp_library` [`4dc20a90…`]. A real gated
  claim of one block (index 101 of the 5e-4 plan, sharedq <NODE>) bound its worker to libgmp `4dc20a90…` (W8), saw no
  loader override (W7) and peaked at 66 MB against an `est_peak_bytes` of 625 MB (W9).
- **W9 before and after** (570578): one block of a 2,056,192-task index (`--pilot --points 512 --replicates 2
  --test-graphs all --bootstrap-chunk 8 --shards 1`): with the tools of b58e9b6 the claim peaked at 747 MB, 1.27× its
  own `est_peak_bytes` (587 MB); with this commit's at 70 MB, 0.11× the new estimate (640 MB). 570576 failed at its
  claims (the job's RSS wrapper; corrected script uploaded and committed in 900e590), 570577 was cancelled while pending.
- Tests after the runs: `unit_orchestration` `route_b_records` carries the 570579 bundles as the accepted ones;
  `test_numerics_flags` `coverage` accepts the 570574 record for the package's inputs only.
- Seeds: 8 new in symmetry's log and the mirror (118), pending for Expanse's
  (`benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`).
- Docs: README, NUMERICS.md, DESIGN.md, HPC.md and PERFORMANCE.md name the 570574 record and the 570579 bundles.

## 2026-10-06: Stage-6 fix round 4: the 21 findings of inspection round 4 (W1–W20) and the host's residuals (W22–W24) fixed and merged [A-RPL-4..7, A-KER-1, A-INV-2/3, A-ORC-1..13, A-DES-1/2, A-FLAG-3/6, A-PERF-1, A-PKG-1/2]

`numerical_change: false` and **no `src/` change**: the default and profile executables stay byte-identical (symmetry:
decimal `a18ce425…`, gmp `7741f733…`, `dd+mp256` `a46f3060…`). Inspection round 4 (eight Codex sessions S6-A..H on
945e526) returned REVISE with 21 findings (13 medium, 8 low; `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md`),
all accepted as W1–W20; the host added three residuals of its own (W22–W24). No earlier fix was reported broken. Four
owner groups fixed them in worktrees from 945e526 (G1 c820125, G2 469cd43, G3 29459d9, G4 392c9b9), merged into `c8`
as 99a575a, de5221a, 2720494 and 2d4b27e; the integration adds the cross-group needs, the same defect classes found
outside the groups' files, and the docs. Every fix has a test that fails on 945e526 (on 2d4b27e for the integration's)
and passes after. The symmetry validation of this head is the next entry.

- **Native and precision harness (G1; `benchmarks/mac_2026-10-c8/fx4g1/`).**
  - **W1** (S6A4-01) `tests/quad_differential.py`: `--min-pairs` removed; the minimum is the fixed `MIN_PAIRS = 10^9`
    (PLAN R3a). `coverage(record)` recomputes the size and scope from the record (the six default range blocks, the
    kernel windows, at least 10^9 pairs per operation over four streams, every edge category, the 2^22-pair injection
    and sanitizer runs); status `passed` (exit 0), `failed` (1) or `development run (...)` (3); `--check RECORD`. Test:
    `tests/test_native_guards.py` `quad_coverage`.
  - **W2** (S6A4-02) `tests/validate.py` `compare(..., tails=True)` (G-BK8): on mp>0 rows `max_abs`, every `tail_top`
    entry and `tail_sum` within the normalized 1e-30, equal widths, `tail_argmax` equal or a documented near tie
    (`TIE_POLICY`); mp=0 tails exact; every row field covered by a rule; G-BK8 records carry `row_rule`
    `c8-d2-bk8-row-rule-2`. The same class: `compare_exact`/`compare_jet` refuse uncovered fields; the A-RPL-6
    `chunk_merge` requires tiling, quad/mp sums and `max_abs`. `validate.coverage(record, gate)` and `--check RECORD
    --gate J-VAL-1|J-VAL-2|G-BK8|G-L8SELF|A-IN-6b`; every record has an `acceptance` field. Test: `test_native_guards`
    `bk8_compare`.
  - **W3** (S6A4-03) `tools/build_record.py`: records name `build_directory`; `reproduce_worker` keeps the meaning of
    relative compiler, `-I`/`-L` and include-environment words by mirroring them into a snapshot nested under private
    parents (`snapshot_root`, `mirror`), never rewriting them (a compiler embeds the path it found); a binding with
    relative make flags is refused outside the worker's build directory. Test: `tests/test_gmp_binding.py`
    `relative_paths`.
  - **W22** (host) `tests/thread_identity.py`: `passed` only for the full configuration (both workers × both sectors,
    1/8/16/64 threads and 8 × 8 lanes, every team observed); restricted runs are development runs (exit 3); an
    `--executable` run (a profile's F5) gets its own status (`coverage(gate='F5')`); `--check RECORD [--gate F5]`.
    Consumers: `stage4b/final/scripts/summarize_final.py` (`thread_identity_verdict`, `validate_verdict`,
    `quad_differential_verdict`). Tests: `test_native_guards` `thread_coverage`, `summaries`.
- **Orchestration and generator (G2; `benchmarks/mac_2026-10-c8/fx4g2/`).**
  - **W4** (S6R4-B-01) one strict G-file reader in `gen/regress.py` (`gfile_text`, `parse_gfile`): LF, spaces and
    printable ASCII only, plain decimals, the loader's header bounds (2 ≤ L ≤ 8, 1 ≤ M ≤ 16384, 1 ≤ T ≤ 10000);
    `gen/gates.py` `check_gfile` uses it. **W5** (S6R4-B-02) `regress.judge` compares raw bytes for "identical" and
    decodes without newline translation (CRLF is a structure difference). **W6** (S6R4-B-03)
    `gen/check_edge_forests.cpp` checks every extraction and bounds allocations; a malformed file is that graph's
    failure, caught inside the OpenMP loop. Tests: `gen/test_regress.py` (W4, W5), `gen/test_keys.py`
    `edge_forest_gfile_checks` (W6, also under UBSan and ASan).
  - **W7** (S6-C-R4-01) `common.loader_overrides`: a claim (and the lane worker, before any claim) refuses
    `LD_PRELOAD`, `LD_AUDIT`, `LD_DYNAMIC_WEAK` and `DYLD_*` with exit 64; the fingerprint records `preload_order`
    (`/etc/ld.so.preload` in load order) and `loader_env` (`GLIBC_TUNABLES`), part of the runtime identity when not
    empty (ordinary identities unchanged). Test: `unit_orchestration` `w7_loader`.
  - **W8** (S6-C-R4-02) `production.gate_gmp_binding`: a gated executable runs only with the libgmp its J-FLAG gate
    validated (`gmp_library.profile`); the plan records `numerics_route.gate_gmp_library` and a non-test plan refuses a
    build record of another libgmp; every claim checks before any pin or block (exit 64), and run-skip, the duplicate
    check and all merges validate checkpoints against it. Test: `unit_orchestration` `w8_gmp_binding`.
  - **W9** (S6-C-R4-03) a claim copies its task file into its private runtime verified against the manifest pin and
    streams it one block at a time (`snapshot_tasks`, `snapshot_blocks`); `stage_runtime` streams too; the plan writes
    task files in pieces; `est_peak_bytes` adds min(tasks, checkpoint_tasks) × 16 KiB and 2 KiB per job entry and per
    inventory row. Test: `unit_orchestration` `w9_stream`, `chunking`, `claim_io`.
  - **W11** (S6D-R4-02, production side) `production.calibration_row` uses a row only under the numerics and rates
    identity it was measured with. Test: `unit_orchestration` `w11_calibration`.
  - **W23** (host) `assemble`/`combine` read `design_meta.json` once from bytes verified against the pinned sha256; the
    same "check, then re-read" class fixed in the inventory, inputs manifest, rate map, seeds, order-8 module,
    two-loop, serial merge and lane cost model readers. Test: `unit_orchestration` `w23_no_reread`.
  - **W24** (host) `route_b_records` covers the four 570539 bundles (frozen bytes, plans, gates, libgmp `4dc20a90…`).
- **Design, calibration, gates and delivery (G3; `benchmarks/mac_2026-10-c8/fx4g3/`).**
  - **W10** (S6D-R4-01) `tools/calibrate.py` `measure` validates every checkpoint (`production.validate_checkpoint`,
    the block streamed from its authenticated task file) before reading a timing; invalid timings refuse (exit 2).
  - **W11** (calibrate/sweep side) a calibration file holds one measurement identity (`identity`);
    `tools/calibration.json` accepts only exact, default-rate rows; `sweep.py --rates`/`--numerics` needs its own
    `--calibration`.
  - **W12** (S6D-R4-03) `design.py`: the minimum-batch search runs past 64 up to `--batches K`; "search limit" and
    "infeasible" are told apart; an explicit `--batches` allocation is checked against every cap.
  - **W13** (S6D-R4-04, S6G4-01) `tools/verify_delivery.py`: the manifest lists `result_records` (every delivered JSON
    of schema `c8-d2-hpc-result-1`, sticky); both modes run `tools/verify_result.py` on each (needs numpy) and fail on
    a problem, an unlisted or unparsable record.
  - **W18** (S6H4-01) `tests/numerics_flags.py` records `inputs` (the inputs manifest sha256, every input, pack and
    vendored pin verified before anything is built and again at the end, complete), fresh F1 baselines record it, a
    reused baseline of other inputs is refused; `design.check_gate(..., inputs_manifest_sha256)` (`gate_inputs`) requires
    it equal to the pilot's (freeze) or the plan's, and returns `inputs_manifest_sha256`. **The 570536 record is
    refused** for exactly the missing identity.
  - **W20** (S6H4-03) `tools/seeds.py reserve`: F2 checks and appends its seeds in one locked transaction; a sweep
    registers likewise and pre-checks its seed before planning.
  - Tests: `tests/test_pipeline.py` `w10_calibration_checkpoints`, `w11_rates_calibration`, `w12_batches`,
    `route_b_synthetic`, `pilot_exact_gated_nontest`, `w20_sweep_seed`; `tests/test_numerics_flags.py` `coverage`,
    `w18_inputs`, `binding`, `w20_seeds`; `tests/test_delivery_verifier.py` (7 W13 cases).
- **Test harness and profiling (G4; `benchmarks/mac_2026-10-c8/fx4g4/`).** **W14** (S6E-R4-01) `Owned` retains the
  process group each registered child leads and finds its members after the leader is reaped. **W15** (S6E-R4-02) the
  in-process launch-boundary case registers the child in an `Owned` scope before the signal. **W19** (S6H4-02)
  `tools/perf_profile.py`: without perf, P1 runs the release worker on every requested block and binds its rows to the
  profiler's per block; P3 runs the release worker (`--worker-exe`) on every (block, rate) and requires its rows equal to
  the ratio-histogram build's. `tests/test_profiling.py` `tool()` kills a timed-out tool's whole process group. Tests:
  `unit_orchestration` `w14_group_cleanup`, `w15_launch_cleanup`; `test_profiling` `perf_binding`, `p3_binding`,
  `perf_expect`, `tool_cleanup`.
- **Integration (cross-group needs and the same defect classes elsewhere; tests fail on 2d4b27e,
  `benchmarks/mac_2026-10-c8/s6fix4int/`).**
  - W18 (G3 → G2): `production.gate_evidence_missing` requires a gate entry's `inputs_manifest_sha256`; `route_b`
    requires every gate entry's to equal the bundle's (and its exact pilot's); `gated_route` checks the gate against
    the plan's own inputs manifest (`check_gate(..., im_sha)`), not the package's. The 570539 bundles are refused for
    exactly the missing input set, and plan once it is added. Tests: `unit_orchestration` `route_b_records` (G3's
    `gate_doc` patch; new refusals), `w8_gmp_binding` (`route_b_bundle` carries the input set).
  - W8 with W10: `calibrate.measure` passes `gate_gmp_binding`, so a gated campaign's checkpoints of another libgmp
    are refused there as in the merges. Test: `unit_orchestration` `w8_gmp_binding`.
  - W10's class in `tools/accounting.py`: the busy time of a group that is not merged yet counts only checkpoints
    `validate_checkpoint` accepts; an invalid one makes the accounting incomplete (η_node unavailable). Test:
    `unit_orchestration` `ledger` (a changed `integration_seconds`, a foreign checkpoint).
  - W3's class: `tests/numerics_flags.py` X2 (`relative_of`, `snapshot_levels`, `mirror_relative`): the reproduction
    and the F1 tool keep the meaning of relative build words (a snapshot nested as deep as they climb, each mirrored;
    one word with two build directories refused); `tools/perf_profile.py` `build_twin` compiles relative make flags in
    the worker's build directory (`twin_directory`) or builds no twin. Test: `test_gmp_binding` `flags_relative`.
  - W4's class: `gen/kirchhoff.py` (A-INV-3(h)) reads the stored kernel with `regress.gfile_text`/`parse_gfile`; a
    malformed G-file is that kernel's failure. Test: `gen/test_regress.py` `kirchhoff_checks`.
  - W15's class: `test_omp_team`'s in-process 30 s worker is registered in an `Owned` scope by the launch seam, which
    also waits until it runs (G4's note: under load the 0.5 s deadline stopped it before its log line).
  - W2/W22 consumers: `stage5/exp/scripts/s5e_summary.py` judges G-BK8, G-L8SELF and J-VAL-2 by `validate_verdict`
    (recomputed coverage; same verdicts on the stored zen2 records). Test: `test_native_guards` `summaries`.
  - G1's `tests/test_omp_launch.py` patch: its stand-in worker writes `max_abs`, which W2's `chunk_merge` compares.
- **Docs.** W16 (`docs/DESIGN.md`: a production batch is planned in a plan job, `slurm/plan.sh`), W17 (README,
  `docs/HPC.md` sweep, pilot and probe examples, `docs/DESIGN.md` freeze examples: the site environment sourced in the
  submitting shell before `C8_SEEDS`/`C8_DATA` are expanded, guarded and quoted; test `unit_orchestration`
  `w17_doc_env`), and every W item in README.md, NUMERICS.md, HPC.md, DESIGN.md and PERFORMANCE.md.
- **Residuals (not changed).** `slurm/plan.sh` adds a test-only plan's seed after planning with `seeds.py add` (twins
  share a seed by design, so it is not a refusing reservation; a non-test plan registers atomically, Z15); a
  checkpoint's `runtime` block (host, CPU model, Slurm ids) is outside its payload digest, so the cost model's CPU
  models and the accounting's Slurm ids are provenance, not authenticated (they set lane deadline factors and the
  completeness check, never a number); the gate records only libgmp, not libquadmath, libm or libgomp (the X8 pin keeps
  them consistent within a campaign).

## 2026-10-06: Stage-6 fix round 3: the new executables validated on symmetry; the `dd+mp256` gate, cost model and route (b) re-made [A-RPL-1..7, A-KER-1/4, A-INV-1/2, A-FLAG-3, A-DES-5, A-ORC-1..13]

`numerical_change: false` for valid inputs (proved exact here). Exports of 9976391 (`pkg/997639178c1f`, jobs
570533-570539) and b58e9b6 (`pkg/b58e9b6f4afd`, jobs 570540-570542; tests-only change, the same executables), symmetry
only, 10 job records, 95.47 core-hours (`benchmarks/symmetry_2026-10-c8/s6fix3/`, README there).
- **New executables** (570533): decimal `a18ce425…`, gmp `7741f733…`, `dd+mp256` `a46f3060…` (prof `3fb9e777…`,
  ratiohist `01aef195…`, inspect `38361979…`); `make c7ref` gives the plan's `e696d7f3…`/`7e3c8c92…`; every build
  record `macro_overrides: []`. 570540 rebuilt them byte for byte from b58e9b6 (the sanitizer builds equal after
  normalizing the export path and build-id).
- **Z4 on the real node:** the loaders of this commit and of a42cfb7 give byte-identical `Graph` states on 24 real
  G-files of all 12 (sector, L), L8 included; 42 truncations refused in the harness, 28 through the worker and the
  inspector (`validate --only bad_inputs`).
- **J-VAL-2 PASS** (570535): G-REF, G-C7, G-JET exact on all 3,774 kernels, both backends; point checks L3–L8 (1.8e-302,
  2.1e-353) through the Z1 binding. **J-VAL-3 exact parts PASS**: thread identity with observed teams, G-BK8 (equal to
  570029 field by field), forced tiers through the Z1 binding (`--check` exit 0; equal to 570416's results).
  **A-RPL-7 PASS**: G-L8SELF exact against the symmetry Stage-3 baseline, and the same L8 comparison against a42cfb7's
  build exact.
- **J-VAL-1**: 570534 stopped at `tests/test_gmp_binding.py` `source_binding` (the inherited `CPATH`, fixed in b58e9b6,
  previous entry); **570541 PASS** (`make test` exit 0: unit_orchestration 79 tests on Linux with the real worker,
  test_native_guards 3/3, test_gmp_binding 14, test_numerics_flags 12, ...; `assembly_checks --exact` 37/37,
  verify_result_tamper 206/206, combine_core 14/14, compat_2026). **J-VAL-4 PASS** (570542: 144 sanitizer worker runs
  and both point-check tools clean, the self-test probes abort). **J-GEN-1 PASS** (570537: test_keys 115/115,
  test_regress 97/97 with Z5's checks, A-INV-2).
- **The `dd+mp256` gate PASSED on the new build** (570536): record
  `benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json`, sha256 `a8de4037…`,
  accepted by `design.check_gate` with the Z19 libgmp provenance (`gmp_library` exact and profile `4dc20a90…`); F1, F2
  (4.25e-16) and F3 equal to 570373's field by field; F4 ×2.517.
- **Profile cost model re-measured** (570538): `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` sha256 `18e50440…`
  (executable `a46f3060…`; replaces `9b0dfec6…`, kept as `benchmarks/symmetry_2026-10-c8/pre6/p6des.570241.0/`'s
  copy), ×2.785 over the exact model, ×1.010 of the replaced one. The exact model `gmp_symmetry_amd_c8.json` stays
  (no executable binding; the exact worker's F4 time +0.8%).
- **Route-(b) re-freeze** (570539): the same choices as 570379 (counts, r, s equal at 5e-4, 2.5e-4, 1.35e-4); 639 /
  2,251 / 9,002 / 29,473 lane core-hours; four test-only plans within every cap, deleted.
- `tests/test_gmp_binding.py` `forced_tiers_consumers`: a stored forced-tiers record made with the Z1 binding (this
  run's, `s3val23.570535.0/forced_tiers.json`) must pass `--check`, the older ones fail it for the missing binding
  only (the test had assumed every stored record predates Z1; tests-only, after the runs).
- Seeds: 7431507595541975415 (the sweep) and 8540795342523536361, 5408404967237961878, 5547428742305252863,
  8750737914650074664 (the plans) in symmetry's log and the mirror (110), pending for Expanse's
  (`benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`).

## 2026-10-06: Stage-6 fix round 3: the 22 findings of inspection round 3 (Z1–Z22) fixed and merged [A-KER-1/3, A-RPL-1..7, A-INV-3, A-ORC-1..13, A-ASM-7, A-DES-1/2/6, A-FLAG-2/3, A-PERF-1, A-PKG-1/2]

`numerical_change: false` for every valid input, but **the executables change**: Z4 adds truncation checks to
`src/kernel.hpp`'s `load_graph` and Z3 a compile-time refusal of external `C8_NX_*` hooks (the round's only `src/`
change, allowed by the host for these two items), so every executable that compiles `load_graph` (the default,
diagnostic and profile workers, the inspector, `quad_ranges`) has a new sha256. Valid inputs load into the same
`Graph` bit for bit (`tests/test_native_guards.py` `loader` against a42cfb7's loader); the full exact replay on the
new executables (J-VAL-2, J-VAL-3's exact parts, A-RPL-7) is the symmetry validation of this round (next entry).
Inspection round 3 (eight Codex sessions S6-A..H on the tree of a42cfb7) returned REVISE with 22 findings (13 medium,
9 low; `LRI_C8_D2_HPC_loop/artifacts/s6_fix3_dispositions.md`), all accepted; no earlier fix was reported broken. Four
owner groups fixed them in worktrees from a42cfb7 (G1 5c8779e, G2 f241669, G3 c082065, G4 7b54923), merged into `c8`
as 6ad5635, 256f4f8, d20262e and f3d0dc2; the integration adds the cross-group needs and the docs. Every fix has a
test that fails on a42cfb7 (on f3d0dc2 for the integration's) and passes after.

- **Native and precision harness (G1).**
  - **Z4** (S6A3-04) `src/kernel.hpp` `load_graph`: `M`, `T`, `n` start at 0; the stream is checked after the mask
    list, each term's denominator size, id list and coefficient row, the rate-table size and the table; every failure
    is `truncated graph: <path>`. Test: `tests/test_native_guards.py` `loader` (42 truncations refused; the old loader
    byte-identical on valid files and, with a pattern-initialized `n`, refusing a short mask list for the wrong reason);
    `tests/validate.py` `bad_inputs` gains 14 truncations through the worker and the inspector (`graph_truncations`).
  - **Z3** (S6A3-03, native side) `src/kernel.hpp` refuses all 16 `C8_NX_*` names from outside `src/numerics/` with
    `#error`; `tools/build_record.py`: `parameter_overrides` also flags `NO_SUM_SHARING`, `-D`/`-U` inside `-Wp,...`,
    `-include`, `-imacros`, `-Xpreprocessor`, `@FILE`; `macro_overrides` (the compiler's `-dM -E` probe); either sets
    `development`; `gmp_target` refuses development records and records without `macro_overrides`. Tests:
    `test_native_guards` `hooks` (91 cases), `test_numerics_flags` `macro_overrides`.
  - **Z1** (S6A3-01) `build_record.bound_tool_command`: a read-only source snapshot, the worker reproduced there byte
    for byte (`reproduce_worker`), the tool compiled from it, `source_binding` recorded; `bind_command` compares
    `BOOST_VERSION`. Applies to `forced_tiers.py`, `check_points.py`, `validate.py` class B. Test: `test_gmp_binding`
    `source_binding` (a stale worker, Boost 1_83 through `CPATH`, a patched Boost through `CPLUS_INCLUDE_PATH` refused).
  - **Z2** (S6A3-02) `tests/forced_tiers.py` `coverage()`, status "passed" only with complete coverage, `--sectors`
    restricted and deduplicated, `--check RECORD`. Test: `test_gmp_binding` `forced_tiers_coverage`.
  - **Z18** (S6G3-01) the Makefile's GMP_PREFIX comment: `make c7ref` ignores `GMP_PREFIX` but links GMP. Test:
    `test_gmp_binding` `c7ref_note`.
  - **Z19** (S6H3-01) `tests/numerics_flags.py` `reused_baseline_library`: a reused baseline's `tool_gmp_library` must
    match the exact executable's recorded libgmp, which the executable must resolve now. Test: `test_numerics_flags`
    `binding`.
- **Orchestration (G2).** **Z3** (plan side) `production.read_build_record`: a non-test plan refuses a missing,
  unreadable or mismatched record (schema, executable name and sha256, backend, NUMERICS, diagnostic,
  `required_flags_present`). **Z5** (S6R3-B-01) `gen/gates.py` `check_gfile` reads tokens as the loader (`gfile_ints`,
  `MASK_TOKEN`, `TERM_TOKEN`, `INT_RANGE`). **Z6** (S6-C-R3-01) `common.fingerprint` hashes absolute-path `ldd`
  entries, the interpreter once, and refuses unexplained lines. **Z7** (S6-C-R3-02) `tools/slurm_submit.py` follows
  sbatch's memory precedence, removes reset `SBATCH_MEM_*` from a job's environment, refuses exclusive pairs and an
  array `--mem-per-cpu`, and preflights every job. **Z11** (S6D-R3-04) `seeds.py init` under the lock, published with
  `common.publish`. **Z13** (S6E-R3-01) `tests/unit_orchestration.py` `Owned` and `fifo_go` (unconditional cleanup of
  owned process groups, detached sessions and FIFOs). **Z15** (S6R3-F-02, code side) a non-test `production.py plan`
  registers its seed in its first `--forbid-seeds-from` log under the log's lock before publishing (`seeds.register`;
  manifest `seed_log`). Tests: `unit_orchestration` `z3_build_record`, `z6_ldd_absolute`, `z7_mem_env`,
  `z11_seeds_init`, `z13_cleanup`, `z15_plan_seed`; `gen/test_regress.py` `gfile_gate_checks`
  (`benchmarks/mac_2026-10-c8/fx3g2/`).
- **Design and verification (G3).** **Z8** (S6D-R3-01) `tools/verify_result.py` `covariance_problems` (symmetric,
  nonnegative diagonal, PSD in correlation units, COV_REL 1e-10) and `sign_problems`; `combine.py`'s covariance
  checks; the CLI records the verified bytes' sha256. **Z9** (S6D-R3-02) `design.read_bundle` (one verified,
  schema-aware reader for report, freeze `--rates-bundle`, rates `--source-bundle`). **Z10** (S6D-R3-03) the bundle's SE
  at its frozen margin and imputation, labelled projections. **Z12** (S6D-R3-05) `nested_alpha` per-graph ratios,
  `check_nested` (`NESTED_IDENTITY`). Tests: `verify_result_tamper` 206 (31 new), `combine_core` 14, `test_pipeline`
  `z9_synthetic`, `z9_cli`, `z9_class_cli`, `z10_synthetic`, `z10_cli`, `z12_nested`
  (`benchmarks/mac_2026-10-c8/fx3g3/`).
- **Profiling (G4).** **Z20** (S6H3-02) P1 fails on a release/tier-timer row mismatch (and the fallback binds its mini
  block). **Z21** (S6H3-03) `--expect-sha256` checked in every mode before any output (P3 included), 8-64 hex digits;
  `benchmark.py --interleave-probe` binds it. **Z22** (S6H3-04) `--keep-perf-data` moves perf.data into
  `<output>/perf_data/`. Tests: `test_profiling` `perf_binding`, `perf_expect`, `perf_keep`, `e2e_perf`
  (`benchmarks/mac_2026-10-c8/fx3g4/`).
- **Integration (cross-group needs; tests fail on f3d0dc2, `benchmarks/mac_2026-10-c8/s6fix3int/`).**
  - Z3 (G1 → G2): `read_build_record` refuses for every plan a record listing macro overrides (even with
    `development` edited to false) and for a non-test plan one whose `macro_overrides` is not a list (null: no probe;
    absent: a record made before this round). Test: `unit_orchestration` `z3_build_record` (4 new cases).
  - Z19 downstream (G1 → G3): `numerics_flags.py` records `f1_baseline.reused` and the baseline's `tool_gmp_library`;
    `design.check_gate` (`gate_gmp_library`) requires both F1 tools' libgmp provenance and, for a reused baseline, the
    reuse check, and returns `gmp_library`; `production.gate_evidence_missing` requires it of a bundle's gate entry.
    The 570373 record (and the 570379 bundles frozen with it) are refused for exactly that. Tests:
    `test_numerics_flags` `coverage`, `binding`; `unit_orchestration` `route_b_records`.
  - Z9's class (G3's note on G2's reader): `production.read_bundle` parses counts with `design.parse_counts` (shared
    with `design.read_bundle`). Test: `unit_orchestration` `z9_plan_counts` (9 malformed counts files with re-pinned
    digests refused by `read_bundle` and by `plan`; before, all accepted).
  - Z2's consumers: the stored-record summaries (`stage4b/final/scripts/summarize_final.py`,
    `stage5/exp/scripts/s5e_summary.py`) judge forced tiers by status and `coverage()` (`forced_tiers_verdict`;
    `coverage(..., source_binding=False)` for records that predate Z1). Test: `test_gmp_binding`
    `forced_tiers_consumers` (every stored record complete but for the Z1 binding).
  - `tests/test_pipeline.py` part 3 (G2's patch): fake build records for the fake workers and profile copies, fresh
    seeds for the refusal cases after an accepted plan registered its seed (Z15). The F13 record test reads the
    replaced profile cost model from the job's evidence copy (`pre6/p6des.570241.0/gmp_symmetry_amd_c8_dd+mp256.json`,
    9b0dfec6…), since `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` is re-measured on the new build.
  - `tests/test_native_guards.py`: `C8_GUARDS_OLD_TREE=<export of a42cfb7>` supplies the before-fix sources in an
    export without `.git` (the cluster runs the loader comparison on real L8 files that way).
  - `tests/unit_orchestration.py`: `0.and` → `0. and` (Python 3.11's SyntaxWarning, noted in s6res2).
  - `tests/test_gmp_binding.py`: the fake toolchain is hermetic (`World.env` drops the inherited `CPATH`,
    `CPLUS_INCLUDE_PATH` and the other `build_record.INCLUDE_ENV` variables). Found by J-VAL-1 on symmetry (job
    570534): `env.sh`'s Boost module puts Boost 1.77 on `CPATH`, so G1's `source_binding` test built its fake worker
    against the host's Boost and expected the wrong version in the refusal. Test: the suite with an inherited `CPATH`
    (fails on 9976391, passes after).
- **Docs.** Z14 (DESIGN.md: tail confirmation from a report with the higher-point campaign as `--pilot`), Z15 (README
  quickstart, HPC.md seed log, plan jobs and pilot runbook, DESIGN.md batches, `slurm/plan.sh`), Z16 (README: plans in
  plan jobs), Z17 (HPC.md: the symmetry pilot probe), Z18 (NUMERICS.md), and every other Z item in NUMERICS.md,
  HPC.md, DESIGN.md, PERFORMANCE.md and README.md; the gate, build and cost-model references that the new executables
  supersede point to `benchmarks/symmetry_2026-10-c8/s6fix3/`.
- **Not changed (host decisions):** the frozen-grid reader of `src/c8d2_integrate.cpp` still reads an unassigned id on a
  truncated grid file (`src/` rule; the grid is optional, production passes `-`); `C8_QUADFAST_OBSERVE` and
  `NO_SUM_SHARING` compile from outside without an error (the build record flags both); the sanitizer's point_checks
  tool is not reproduced byte for byte from a snapshot (its `-g` builds embed the directory).

## 2026-10-06: Stage-6 residuals after fix round 2 (R1–R3, and the class-reader reservation) [A-RPL-6, A-KER-4, A-RPL-5, A-ASM-7, A-INV-1]

`numerical_change: false` (no `src/` change; every default and profile executable is unchanged; the generator binaries
change in bytes only: their outputs on classes3..6 are byte-identical before and after on the Mac). The fix-round-2
verifier left three residuals of the same classes; each fix has a test that fails on a57e07f and passes after
(`benchmarks/mac_2026-10-c8/s6res2/`, README there). Mac only, no job.
- **R1** (Y2's class in the harnesses) `tests/validate.py`: every native launch gets `harness_env` (`common.omp_child_env`,
  unbound: no inherited `OMP_*`, `GOMP_*`, `KMP_*`, `OMP_NUM_THREADS` = the run's own thread count, `native_threads`);
  the A-RPL-6 `invariance` runs (1 against 4 threads) go through `team_run`: `omp_child_env(threads)` and the team
  observed with `common.TeamWatch`, a team other than the request or none observable failing the check; each record
  carries `teams_observed`, `team_sizes_verified` and `omp_environment`. With `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true`
  inherited, a57e07f ran both runs serially and recorded `thread_identical: true`. The same class elsewhere:
  validate's refusal and inspector runs, `tests/forced_tiers.py` and `tests/numerics_flags.py`'s F1 tool (through
  `validate.run`, with their thread count), `tests/quad_differential.py` `run_json` and `tools/prepare_inputs.py`
  `inspect_pack`. `common.omp_child_env` gains `bind=False` for launches that run concurrently without disjoint CPU
  sets (they would all bind to the first cores of one mask); its bound form is unchanged. Not changed: one-thread
  launches (`tests/check_points.py`'s point_checks has no parallel region; the C7-era `tools/profile.py` and
  `tools/benchmark_memory.py`; `gen/test_keys.py`), compiles and `--describe` probes. Test: new
  `tests/test_omp_launch.py` (5 tests, a stand-in worker and a simulated `/proc`; in `make test-python`).
- **R2** `tests/sanitize.py`: `ENV` = `common.omp_child_env(4)` plus `ASAN_OPTIONS` and `UBSAN_OPTIONS` (it was the
  inherited environment plus `OMP_NUM_THREADS=4`); the record carries `omp_environment`. Test: `test_omp_launch`
  `sanitize_env`.
- **R3** `tools/verify_result.py`: a pull p = (x − r)/σ amplified a rounding-level difference of its input by 1/σ, so
  the Stage-5 design-chain partial (`benchmarks/symmetry_2026-10-c8/stage5/design_chain_k2/C8_partial.json/
  C8_test_partial.json`) failed on the Mac (`null_rows[1]/pull` 4e-10 relative apart, its delta 3.6e-15 apart). A
  pull's tolerance is now the bound its inputs' tolerances imply (`pull_bound`: τ_x/σ_min + |p| σ (1/σ_min − 1/σ_max),
  derived in the module docstring), for the power null rows, the top row and the lower-order rows with their
  secondaries, and every stored pull must be the pull of its own stored inputs to 1e-12 (`pull_problems`), so a pull
  changed alone is refused however small the change. All 15 stored c8-d2 results verify on the Mac (one failed
  before). Test: `tests/verify_result_tamper.py` 175/175 (71 new: a brute-force check of the bound; consistent
  cross-machine moves accepted, 22 of them refused by a57e07f; inputs beyond their tolerance and pulls changed alone,
  inside or beyond the bound, rejected; the design-chain partial as a fourth cross-machine fixture).
- **Low** `gen/c8gen.hpp` `read_classes` reserves at most `CLASS_RESERVE_CAP` (2^16) rows up front, so a header NG up to
  INT_MAX ends in the InputError of its first missing row instead of an allocation of NG rows. Test: `gen/test_keys.py`
  (115/115 with g++-16; 3 new: an ASan build of test_keys and the hostile NG = 2^31−1 file with and without
  `--generator` under `max_allocation_size_mb=256`, which aborted in `read_classes` on a57e07f).
- Docs: `README.md`, `docs/HPC.md` (OpenMP teams), `docs/NUMERICS.md` (pulls).

## 2026-10-06: Stage-6 fix round 2: the merged head validated on symmetry [A-RPL-8, A-INV-1/2, A-RPL-5, A-ORC-1..13, A-PERF-3]

`numerical_change: false`. Export of e914701 (`pkg/e914701b042b`), symmetry only, jobs 570414-570425 (9 records, 30.28
core-hours; `benchmarks/symmetry_2026-10-c8/s6fix2/`, README there).
- **A-RPL-8 PASS** (570414): every default and diagnostic executable byte-identical to the Stage-5 build (decimal
  `619ddf7d…`, gmp `2cc5e88e…`), the profile build `d5df32ac…`.
- **J-GEN-1 PASS** (570417): `gen/test_keys.py` 112/112 with the Y3 UBSan part on GCC 11.4 (the key 2^72−1 refused with
  exit 2 by all four sanitized programs, no report); A-INV-2 at L3–L7 with `builder_env`.
- **J-VAL-1 PASS** (570415): `make test` exit 0 (unit_orchestration 60 groups / 72 tests with the real worker on Linux,
  Y15's atomic-plan test included; test_pipeline 29; ast_scan 0 findings; test_gmp_binding 10; check_vendored 35/35;
  check_inputs 22/22), `assembly_checks --exact` 37/37, `verify_result_tamper` 104/104, `compat_2026` 0.0.
- **Y1 PASS** (570416): `forced_tiers.py --worker bin/c8d2_gmp` and `check_points.py` through the binding with the
  default GMP (no prefix; tool and worker resolve libgmp `4dc20a90…`); the sanitizer point_checks tool and the
  profiler's twin bound (the twin's allocated sections equal the worker's). The zen2 re-run stays owed on Expanse.
- **Y2 PASS** with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true` inherited: P4 8x8 and 1x64 `team_sizes_verified` (570416);
  direct and `run_array.sh` claims verified 4 of 4 (570418); a real drill-mode `submit.sh --lanes 1` lane worker and
  merge (570420/570421, both jobs inheriting the controls): 21 of 24 checkpoints verified, 3 workers of 13–18 ms
  unobservable ('unverified', by design), none smaller; status exit 0, 24 groups merged (570425; 570422, the first
  check, required every verdict verified and failed on those three).
- **Y6 PASS**: a failing `ldd` on the first claim exits 64 with nothing pinned or run (570418); complete fingerprints on
  amdq <NODE>/<NODE> and sharedq <NODE>. **Y7 PASS**: the cgroup v1 job limit read on both allocations (245 GiB, 15 GiB).
  **Y13 PASS**: the sweep is refused in a job without a seed log and registers its seed right after its plan.
- Seeds: 5949820605861326415 and 5638617719944467077 in symmetry's log and the mirror (105), pending for Expanse's
  (`benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`).

## 2026-10-06: Stage-6 fix round 2: the 16 findings of inspection round 2 (Y1–Y16) fixed and merged [A-RPL-5, A-KER-4, A-INV-1/2, A-IN-3, A-ASM-1/7, A-ORC-1..13, A-DES-1/5/6, A-PERF-3, A-PKG-1/2]

`numerical_change: false` (no `src/` change; the default path is bit for bit the same, and every default executable
is the Stage-5 build; the generator binaries change in bytes only, their outputs on classes1..7 are byte-identical).
Inspection round 2 (six Codex sessions on the tree cb762c4f of 2ae3db7) returned REVISE with 17 findings, 16 distinct
(`LRI_C8_D2_HPC_loop/artifacts/s6_fix2_dispositions.md`), all accepted; no round-1 fix was reported broken. Four owner
groups fixed them in worktrees from 2ae3db7 (G1 20cc644, G2 2bde93d, G3 96a0e7b, G4 8544e41), merged into `c8` as
0b7c180, 3070654, d7b5290 and 696db78; the integration adds the cross-group needs and the same defect classes found
nearby, and G5 the docs. Every fix has a test that fails on 2ae3db7 (on 696db78 for the integration) and passes after.

- **Precision tools, design, verification (G3).**
  - **Y1** (S6A2-01) The precision tools are bound to the GMP of the worker they speak for. `common.cxx_command` takes
    `gmp_prefix` (the Makefile's GMP_INC/GMP_LINK words in the Makefile's places; `common.gmp_prefix_words`).
    `tools/build_record.py`: `worker_record`, `gmp_target` (the worker's build record must describe it and be an
    exact-path production build; GMP_PREFIX, compiler, flags, gmp.h version and configuration, libgmp sha256; an
    environment `GMP_PREFIX` other than the record's is refused), `bind_command` (same make flags, compiler and gmp.h),
    `check_linked` (tool and worker resolve the recorded libgmp; no `ldd` answer is a refusal), `bound_tool_command`,
    `verify_tool`. Applied in `tests/forced_tiers.py --worker` (record `gmp_binding`), `tests/check_points.py
    --decimal-worker/--gmp-worker` (each result's `binding`; both backends bound before anything is staged),
    `tests/validate.py` class B (`bindings`), and `tests/numerics_flags.py`'s F1 tool (`tool_gmp_library`);
    `design.check_gate` unchanged (the 570373 record is accepted). **`GMP_PREFIX` is NOT cleared for production**:
    job 54676895's forced tiers, point checks and class-B builds linked Spack's libgmp, so the zen2 clearance is
    withdrawn until those checks are re-run on Expanse with the bound tools, with the A-EXP-3 J-EXP-1 rerun
    (`docs/NUMERICS.md`, "Builds"). Test: new `tests/test_gmp_binding.py` (a fake toolchain), `test_numerics_flags`
    `binding`.
  - **Y9** (S6D-R2-01) `tools/accounting.py` `missing_checkpoints`: checkpoints missing from merged groups make the
    accounting incomplete (exit 4); `design.py` `eta_node` assumes an efficiency only for test-only designs, and a
    production freeze or report refuses missing checkpoints, checkpoints without a Slurm id, or no Slurm-id checkpoint.
    Test: `tests/test_pipeline.py` part 3 `y9_y10_nontest` (all checkpoints removed: accepted with exit 0 on 2ae3db7).
  - **Y10** (S6D-R2-02, design side) `design.py` `check_options` (production: replicates powers of two in [32, 128],
    `--min-points` a power of two ≥ 4,096, margin ≥ 1; test-only: replicates powers of two ≥ 2; every size, chunk,
    time and target checked) before anything is designed, and `check_allocation` before a bundle is published. Test:
    `test_pipeline` `y10_options` (16 refusals; `--min-replicates 1 --max-replicates 1` froze on 2ae3db7).
  - **Y11** (S6D-R2-03) `tools/verify_result.py`: field types checked before any recomputation (`field_types`,
    `META_TYPES`; finite non-boolean numbers everywhere); tolerance scales only from designated fields
    (`scale_keys`); Cauchy-Schwarz in the variance identity. Test: `tests/verify_result_tamper.py` 104 cases (23 new,
    19 accepted by the 2ae3db7 verifier, among them scope = 1e30 with C8_full + 1).
- **Orchestration (G2).**
  - **Y2** (S6A2-02, S6-C-R2-02) `common.omp_child_env` (no inherited `OMP_*`, `GOMP_*`, `KMP_*`; the requested team,
    `OMP_DYNAMIC=FALSE`, close binding on cores, one BLAS thread) for every native launch: `production.py run` (direct,
    array, lane, sweep), `lanes.py`, `sweep.py`, `benchkit.omp_env`/`run_watched` (P4, `perf_profile.py`,
    `numerics_flags`), `benchmark.py`'s legacy mode; `run_array.sh` unsets the controls. `common.TeamWatch` watches an
    ELF worker's team on Linux (`/proc/<pid>/task`): no team after 60 s of wall time with 30 s of CPU time stops the
    worker and the claim exits 64 (nothing of the block kept; a lane releases and stops). Checkpoints record
    `runtime.omp_team`, `status` counts `omp_teams`, and a P4 shape is accepted only with every block verified
    (`team_sizes_verified`). Tests: `unit_orchestration` `omp_env`, `omp_team`, `bench_team`.
  - **Y6** (S6-C-R2-01) `common.elf_kind`, `fingerprint_problems`: a dynamic ELF worker's fingerprint must be complete
    (ldd answered, every library and the interpreter hashed, the CPU vendor from `/proc/cpuinfo`; the vDSO excepted)
    before any pin or block, else exit 64 ("incomplete runtime fingerprint"). Test: `fp_complete`.
  - **Y7** (S6-C-R2-03) `lanes.cgroup_memory_limit`: the minimum finite limit over the cgroup and every visible
    ancestor; malformed `/proc/self/cgroup` lines skipped. Test: `cgroup_min` (2ae3db7 returned 64 GiB under a 16 GiB
    job).
  - **Y8** (S6E-R2-01) `campaign_runtime_key` raises on a first checkpoint with a missing or malformed fingerprint
    (`common.fingerprint_malformed`); None only without checkpoints; the pinned path refuses a malformed one. Test:
    `fp_first` (merges with `--jobs 1`, `--jobs 2`, `--serial`).
  - **Y10** (production side) `production.bundle_replicates`: the twelve entries, integers ≥ 2, powers of two in [32,
    128] unless the bundle is test-only, checked at `plan --design` before anything else. Test: `bundle_reps`.
  - **Y12** (S6D-R2-04) `sweep.check_existing` compares the requested identity (seed, backend, numerics, threads,
    points, replicates, rates identity, cost basis, shards, checkpoint size) with the frozen one. Test:
    `sweep_resume` (default to map, map to default, map to another map, chunk, shards, checkpoint tasks).
  - **Y13** (S6R2-F-01) `tools/sweep.py` adds its base seed to `--seeds-log` (default `$C8_SEEDS`) right after the plan,
    before the ledger and any index; inside a Slurm job a missing log is refused before planning; `slurm/sweep.sh`
    passes the log; `slurm/plan.sh` adds the planned campaign's seed and still registers the ledger when the add
    fails. Tests: `sweep_seed`, `plan_seed`.
- **Generator, inputs, vendoring (G1).**
  - **Y3** (S6R2-B-01) `gen/c8gen.hpp` `validate_generator_classes()`: the decoding pass only sums edge counts and
    degrees; D_G is formed after every structural check, in the builders' order, with `checked_mul`. Test:
    `gen/test_keys.py` 112 checks (15 new: the key 2^72−1 at n=9 in the plain driver and the three programs, and a
    UBSan part building all four with `-fsanitize=undefined -fno-sanitize-recover=undefined`; on 2ae3db7 the sanitized
    build stops with "signed integer overflow" at `c8gen.hpp:194`). Outputs on classes1..7 byte-identical (3,810 files).
  - **Y4** (S6R2-B-02) `tools/vendor_assembly.py`: `VENDORED.json`, `vendor/c8_assembly` and the fixtures root are
    refused when they exist or are symlinks (dangling included), `destination()` checks the metadata path, and the
    metadata is staged and written last, exclusively; a failed write removes everything the run created. Test:
    `tests/check_vendored.py` 36/36 (`--standalone` 33/33; 4 of the 5 new cases fail on 2ae3db7).
  - **Y5** (S6R2-B-03) `tools/prepare_inputs.py` `build_l8`: a pack target that is not a regular file is refused
    before building; `install_all` installs both packs or neither (originals kept aside and restored on failure).
    Test: `tests/check_inputs.py` step 5, 23/23 (5 of the 6 new checks fail on 2ae3db7).
- **Test tools (G4).** **Y14** (S6E-R2-02) `tests/ast_scan.py` checks each lambda as its own scope (parameters and
  walrus targets, in evaluation order, at every level) and comprehensions as their own scopes (a loop variable read
  before its clause; subscript and attribute loop targets read their base; module- and class-level comprehensions).
  83 self-test probes (23 new, 16 wrong on 2ae3db7); a random-program comparison misses 273–298 functions per seed with
  the old scanner, none now. **Y15** (S6E-R2-03) `tests/unit_orchestration.py` `test_atomic_plan`: SIGKILL only to a
  live, paused plan in its write phase (staging holds a group, target absent), death by SIGKILL asserted, the same
  arguments rerun to a complete campaign, the plan reaped on every failure path; the old test passed three broken
  plan variants, the new one fails all four. Evidence `benchmarks/mac_2026-10-c8/fx2g4/`.
- **Integration** (the cross-group needs; evidence `benchmarks/mac_2026-10-c8/s6fix2int/`, each new test run on
  696db78 in `before_696db78/`).
  - `Makefile` `test-python` runs `tests/test_gmp_binding.py` (Y1's test was in no target).
    `tests/test_gmp_prefix.py` `targets`: every `tests/test_*.py` and `gen/test_*.py` is run by `make test-python`,
    `test-full` (`make -n`) or J-GEN-1.
  - Y1's defect class elsewhere: `tests/sanitize.py` builds its point_checks sanitizer tool with the `GMP_PREFIX` of
    `bin/c8d2_gmp_san`'s build record, where `GMP_SAN_CMD` puts it, and requires the recorded libgmp (`pc_tool`,
    `verify_pc_tool`); `tools/perf_profile.py` builds the debug-info twin with the profiled worker's `GMP_PREFIX`
    (`twin_gmp_prefix`). Tests: `tests/test_gmp_binding.py` `sanitize`, `perf_twin`.
  - Y2's defect class elsewhere: `tools/perf_profile.py` `run()` watches the team of a direct worker run (tier timers,
    ratio histograms, plain and serial runs; `native_result` refuses a watched run without a verified team; runs
    wrapped by perf or ltrace are recorded as not watched). Test: `tests/test_profiling.py` `perf_team`. The generator
    programs: `gen/regress.py` `builder_env` (also `gen/gates.py`'s `check_edge_forests`), and `gen/run_l8.sh` and every
    `slurm/gen/*.slurm` unset inherited `OMP_*`/`GOMP_*`/`KMP_*` controls before any builder, so an inherited
    `OMP_THREAD_LIMIT=1` cannot make A-INV-2's 1-versus-8-thread identity compare two serial runs. Tests:
    `gen/test_regress.py` 90/90 (4 new), `gen/test_run_l8.py` 6/6 (1 new).
  - Docs as tests: `tests/unit_orchestration.py` `doc_examples` replays the lane example of `docs/HPC.md` on the fake
    scheduler with the symmetry template's default cap (Y16) and requires `--seeds-log` in every documented direct
    `tools/sweep.py` command (Y13); `tests/test_gmp_binding.py` `docs` refuses any README/docs paragraph that calls
    `GMP_PREFIX` cleared without "NOT" (Y1).
  - `tests/ast_scan.py` (Y14) over the merged tree: 176 files, 0 findings.
- **Docs (G5).** **Y16** (S6R2-F-02) the lane example of `docs/HPC.md` starts with one worker and adds one (2 + 2 = 4
  AMD-pool jobs), with the admission arithmetic. **Y13** the documented sweep command (`docs/DESIGN.md`) passes
  `--seeds-log "$C8_SEEDS"`; `docs/HPC.md` "The seed log", "The cost-model sweep" and "Plan jobs" describe who
  registers which seed. **Y1** `docs/NUMERICS.md` "Builds", `docs/PERFORMANCE.md` (R4f rows, "GMP_PREFIX on Expanse")
  and `docs/HPC.md` (owed with A-EXP-3): NOT cleared for production; the binding is described. Y2, Y6, Y7, Y8, Y12 in
  `docs/HPC.md`; Y2 for the profiles in `docs/PERFORMANCE.md`; Y9, Y10 in `docs/DESIGN.md`; Y11 in `docs/NUMERICS.md`;
  Y3–Y5 in `README.md`.
- Pinned tools changed (`production.py`, `common.py`, `lanes.py`, `sweep.py`, `prepare_inputs.py`, `design.py`,
  `accounting.py`, `verify_result.py` and others): campaigns planned at 2ae3db7 or earlier see a tool-hash change. The
  pilots are re-planned after Stage 6 anyway.
- Not fixed, observed by G1: `read_classes()` reserves capacity for a declared NG up to INT_MAX before reading rows;
  not undefined behaviour, but on a host with a strict memory limit a hostile header could end in `bad_alloc` instead
  of an input error. No test could make it fail on the Mac.

## 2026-10-06: Stage-6 fix round 1, verifier residuals: four LOW items closed before inspection round 2 [A-FLAG-3, A-DES-1, A-ASM-1, A-PKG-1]

`numerical_change: false` (no `src/` change; no design number changes; Mac only, no job). The fix-round-1 verifier
(READY) listed four LOW residuals; each now has a test that fails on bc23eee and passes after.

- **Route (b) needs the current gate evidence** (`tools/production.py` `gate_evidence_missing`, called by `route_b`
  for every plan of a route-(b) bundle, before anything else is described): every gate entry of the bundle must carry
  the X1–X3 evidence `design.check_gate` returns since fix round 1 (`F1_coverage` of free and power with at least
  10,000 binary128-accepted and 1,000 MP points each, `source_snapshot_sha256`, `F5_team_sizes_verified` true). A
  bundle frozen before the fix with the 570210 record (pre6b, job 570302) is refused, naming the job; the four bundles
  re-frozen with the 570373 record (job 570379) plan, non-final and final. Test: `tests/unit_orchestration.py`
  `route_b_records` (10 synthetic cases × 3 call modes, the 4 real pre6b bundles with `test_only` forced false × 2,
  the 4 real 570379 bundles accepted).
- **A reused F1 baseline is tied to the source snapshot** (`tests/numerics_flags.py`, right after the snapshot and
  before any build or output: the baseline binding's `snapshot_sha256` must equal this run's snapshot;
  `tools/design.py` `gate_binding`: `F1.baseline_binding.snapshot_sha256` must equal `build_binding.snapshot.sha256`).
  Test: `tests/test_numerics_flags.py` `binding` (a baseline bound through another or no snapshot is refused with no
  output; the same baseline from this snapshot gets past the check) and `coverage` (two `check_gate` refusals; the
  real 570373 record is accepted).
- **`tests/ast_scan.py`**: an annotated assignment without a value and with an attribute or subscript target loads the
  target's base and index (`a[i]: int` evaluates `a` and `i`); a name target binds and loads nothing. Self-test: 5 new
  probes (3 found by the old analyser 0 times).
- **`tools/vendor_assembly.py`** executes the vendored `order8_assembly.py` from its staged, HANDOFF-checked bytes and
  checks the used names (and records their signatures) **before the first write**; a module that lacks a name or fails
  to execute leaves nothing written. Test: `tests/check_vendored.py` sandbox, 2 new cases (both modes).
- `production.py` is a pinned tool (its hash changes again; the pilots are re-planned after Stage 6 anyway).

## 2026-10-06: Stage-6 fix round 1: the 23 findings of inspection round 1 (X1–X23) fixed, merged and validated on symmetry [A-FLAG-3, A-INV-1/2/3, A-IN-3, A-ASM-1/7, A-ORC-1..13, A-DES-1/5/6, A-PKG-1/2]

`numerical_change: false` (no `src/` change: every default executable and the gated `dd+mp256` build are
byte-identical to the Stage-5 symmetry builds, A-RPL-8 below). Inspection round 1 (six Codex sessions on c8-rb..e88bf4f)
returned REVISE with 28 findings, 23 distinct (`LRI_C8_D2_HPC_loop/artifacts/s6_fix1_dispositions.md`), all accepted.
Four owner groups fixed them in worktrees from e88bf4f (G1 5b8caf5, G2 38b47ee, G3 73501f1, G4 824fa75), merged into
`c8` as 2741bc2, 8494fd2, cd7e5de and 997eb6a; the integration commit c30bfc5 adds the cross-group fixes; G5 is this
entry and the docs. Every fix has a test that fails on e88bf4f (or, for the integration fixes, on 997eb6a) and passes
after it.

- **Design, statistics and the J-FLAG harness (G3).**
  - **X1** `tests/numerics_flags.py` `f1_coverage()`: scale 1, the prescribed sample and need, both sectors, the f1_ids
    graphs per (sector, L), points per graph = sample × 2^doublings in contiguous ranges, binary128 and MP counts
    recounted from the stats against the need with `need_met` consistent, every baseline point evaluated by the
    profile. The F1 verdict requires it (development runs excepted); a baseline-only run fails without it; `--sectors`
    other than `free,power` is a development option; the record carries `F1.coverage`. `design.check_gate` requires it
    (`gate_f1_coverage`: L7 200 × 256, L8 400 × 64 points, need 10,000 / 1,000).
  - **X2** `snapshot()`/`bind()`: one read-only source snapshot; every executable an F1 tool stands for is rebuilt there
    from its build record's (Makefile, relative) command and must be byte-identical; the F1 tools are compiled in the
    same snapshot; a non-Makefile command, a numerics-source pin mismatch, a stale or foreign executable or an unbound
    reused baseline stops the run before any output. The record carries `build_binding`, `F1.tool_snapshot_sha256`,
    `F1.baseline_binding`; `check_gate` requires them (`gate_binding`).
  - **X3** (harness only) `tests/thread_identity.py`: the child environment drops `OMP_*`, `GOMP_*`, `KMP_*` and sets
    `OMP_DYNAMIC=false`; each run's and lane's team is observed (`/proc/<pid>/task` every 2 ms) and must equal the
    request (fail closed when unobservable); records `team_observed`, `teams_observed`, `team_sizes_verified`. F5
    passes only with every block verified (`F5.team_sizes_verified`, `F5.teams`); F2/F4 use the same sanitized
    environment; `check_gate` requires it.
  - **The 570210 gate record is refused** by the fixed `check_gate`, for exactly the three missing-evidence reasons (its
    F1 coverage, recomputed from its baseline, is complete); the gate was re-run on symmetry (below).
  - **X10** (make_cost_model side) `class_factors` refuses a model of other numerics, or of none (CLI exit 3).
  - **X14** `design.py` `own_inputs`: for a `c8-d2` pilot, `--inventory` and `--two-loop` must have the sha256 its
    verified inputs manifest pins, and `--selection` is refused; `report`/`freeze` exit 2 and create nothing.
  - **X15** `tools/accounting.py`: `TERMINAL_STATES`, `REQUEUE_STATES`, `state_of`, `live_states`; the current sacct
    attempt of every job and array element must be terminal and every earlier one terminal or a requeue state (a
    PENDING array range is live; a range cancelled before start covers its elements at zero time); otherwise the
    accounting is incomplete (hours lower bounds, `eta_node` null, `design.eta_node` refuses, CLI exit 4).
  - **X16** `tools/verify_result.py`: `dimension` 2, `epsilon` `2s-2` and `assembly.half_d` 1 compared leaf by leaf with
    their types.
  - Tests: `tests/test_numerics_flags.py` 11/11 (new `coverage`, `binding`, `f5_team`, `pure` cases);
    `tests/test_pipeline.py` part 2 (X10, X14, X15; route (b) refusals for no coverage, one sector, an unmet quota);
    `tests/verify_result_tamper.py` 81/81 (12 new); evidence `LRI_C8_D2_HPC_loop/artifacts/s6_fix1_g3_logs/`.
- **Orchestration (G2).**
  - **X8** `common.runtime_identity()`/`runtime_identity_key()` (glibc, the ELF interpreter's and every ldd-resolved
    library's sha256 by soname, whether ldd answered; not the host, Slurm ids, CPU model or library paths). The first
    claim publishes `RUN/runtime_identity.json` (no-clobber); a claim under another identity exits 64 before any block
    (`claim_io` status "runtime identity refused"); `validate_checkpoint(..., runtime_key)` is enforced in run-skip, the
    duplicate check, `merge --jobs 1|N` and the serial merge; a campaign without the pin is held to its first
    checkpoint's identity; a pin whose key is not its identity's hash is refused; `status` (`--json`) reports it;
    `lanes.py`'s exit-64 message names the vendor and the library stack.
  - **X9** `read_bundle` keeps the verified bytes; `plan --design` writes `<campaign>/design_bundle` (manifest
    `design.pinned_copy`); `production.design_bundle()` takes `--bundle DIR`, else the pinned copy, else the planned
    path, each checked against the pinned `design_meta.json` sha256; `assemble.py` and `combine.py` gain `--bundle`.
  - **X10** `production.load_cost_model(numerics=, exceptions=)`: a non-test plan refuses a cost model whose numerics
    differ from the plan's or that records none ("cost model numerics identity"); a test-only plan keeps it with a
    warning (`cost_model_numerics_exception`); the manifest records `cost_model_numerics`.
  - **X11** `slurm/env.sh.example`: `export C8_AMDQ_CAP="${C8_AMDQ_CAP:-4}"` (a default only); the installed
    `~/c8d2/env.sh` on symmetry was edited the same way (2026-10-06; old `e5fdb68c…` kept as
    `env.sh.bak-20261005-x11`, new `d1e900e9…`).
  - **X12** `slurm_submit.Context.selection(role)`: every sbatch (and its `--test-only` preview) gets explicit
    `--partition` and `--account` (user option, `SBATCH_*`, `C8_ACCOUNT`, then the Expanse defaults), before the
    trailing `--time`; an effective account other than the admitted one is refused (64); the ledger records both.
  - **X13** `lanes.index_failures()`; `cmd_lane` rechecks the failure count under its claim and releases it, launching
    nothing, at `C8_LANE_MAX_FAILURES`.
  - **X21** `benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh`: rounds of snapshot, local union of all three
    logs, merge into each under its lock; exit 0 only when one snapshot shows all three equal, exit 1 after
    `C8_SEEDSYNC_ROUNDS` (5) listing what each lacks.
  - Tests: `tests/unit_orchestration.py` gains `runtime_identity`, `bundle_relocation`, `cost_numerics`,
    `amd_cap_template`, `acct_partition`, `lane_fail_recheck`, `seedsync` (49 groups, all pass on the Mac).
  - Tool hashes changed (`production.py`, `common.py`, `assemble.py`, `lanes.py`, `slurm_submit.py`): campaigns planned
    at e88bf4f or earlier cannot claim with the new tools; merging/assembling them needs `--accept-tool-change` and
    combining their batches `--bundle DIR`. The planned pilots are re-planned after Stage 6 anyway.
- **Generator, inputs and vendoring (G1).**
  - **X4** `tools/prepare_inputs.py --l8 [--folder DIR]` (`make inputs-l8`): checks the manifest and every input that
    must not change (L3–L7 packs, small inputs, `inventory.json`, vendored pins; the L8 packs need not exist or be
    valid), refuses a test-fixture manifest, writes both packs to temporary files (fsync) checked against their pins
    and counts, installs them only when both match, and verifies with both L8 packs required. A corrupt or truncated
    pack is now repaired; on any failure the existing packs are left unchanged.
  - **X5** `gen/regress.py` `loops_arg`/`threads_arg` (exit 2 before building), `coverage`, `h1_problems`;
    `gen/gates.py` `summary_problems`; `gen/publish_inventory.py` and `gen/handoff_inventory.py` require complete
    evidence; `slurm/gen/regress.slurm` runs `test_handoff_inventory.py`. The Stage-1 A-INV-2 record (Expanse
    54631551) is refused (it predates CK-K02); 54658874 and this round's J-GEN-1 record (570374) pass.
  - **X6** `gen/c8gen.hpp` `validate_generator_classes()`/`read_generator_classes()`: `build_free`, `build_power` and
    `check_edge_forests` validate class files before any output and any OpenMP region; `test_keys --generator`.
    Output unchanged (old/new binaries byte-identical on classes1..7 on the Mac; J-GEN-1 on symmetry below).
  - **X7** `tools/vendor_assembly.py --expect-read-set-sha256` (current read set `7b14f50a…`); every destination path
    checked before the first write (relative, canonical, unique ignoring case, no file/directory clash, inside its
    vendor root without symlinks, not present; reference copies under `reference/`); exclusive creation. It reproduces
    `vendor/` byte for byte from the real HANDOFF.
  - Tests: `gen/test_keys.py` 97/97, `gen/test_regress.py` 86/86, `gen/test_handoff_inventory.py` 17/17,
    `tests/check_vendored.py` 29/29 (26/26 `--standalone`), `tests/check_inputs.py` 17/17; evidence
    `LRI_C8_D2_HPC_loop/artifacts/s6_fix1_g1_evidence/`.
- **Static scan and delivery test (G4).** **X17–X19** `tests/ast_scan.py`: match-pattern captures are bindings; only the
  left operand and first comparator of a chained comparison always run; a handler's except-as name is unbound on
  every way out (end, break, continue) before an enclosing finally; plus seven same-class corrections (dict
  evaluation order, augmented assignment, decorators before defaults, class keywords, walrus in nested defaults, assert
  binds nothing, an unreachable handler statement counted once). **X20** `tests/test_delivery_verifier.py`: six
  unsafe or noncanonical paths, each in an otherwise consistent package, fail both modes with exactly their own error,
  and a control without the path checks passes them; every negative case asserts its exact error list. Evidence
  `benchmarks/mac_2026-10-c8/fx1g4/` (17 of the 24 new probes miscounted by the e88bf4f analyser; random-function fuzz:
  0 missed unbound names against 84–91 per seed).
- **Integration (c30bfc5).**
  - G3's patch to `tests/unit_orchestration.py` `route_b_records` (the synthetic gate record carries the X1–X3 evidence;
    5 more refusals): it fails against the fixed `check_gate` without it.
  - G4's analyser over `gen/*.py` and `tests/*.py` found 20 possibly-unbound reads (correlated conditions; 18 new in G1
    and G3 code, 2 pre-existing in `tests/validate.py`): `gen/regress.py`, `tests/numerics_flags.py` and
    `tests/validate.py` restructured so every read is definitely bound; `make test-python` now also runs
    `tests/ast_scan.py gen/*.py tests/*.py` (20 findings on 997eb6a, 0 now) and `gen/test_handoff_inventory.py`.
  - `tools/verify_delivery.py` `safe_file` checks every component of a listed path for a symlink (G4's observation: a
    listed `sub/x` through a symlinked directory `sub` passed default mode); `tests/test_delivery_verifier.py` adds the
    case (both modes), which fails on the old verifier.
- **Docs (G5).** **X22** `docs/HPC.md` pilot runbook: the submit snippets name no Stage-5 export or campaign; they use
  `C8_PACKAGE`/`C8_RUN` set in step 1 for the approved export and the freshly planned campaign, behind a `${…:?}`
  guard; the Stage-5 plans are a reference table only. **X23** `README.md`: the Mac quickstart is
  `C8_ALLOW_NO_L8=1 make test-python`, and clusters build the L8 packs and never set it. Every X item is documented in
  `README.md`, `docs/HPC.md`, `docs/DESIGN.md` and `docs/NUMERICS.md`.
- **Symmetry validation** (`benchmarks/symmetry_2026-10-c8/s6fix1/`, export c30bfc5f0bdf, jobs 570371-570379, 39.93
  core-hours; symmetry only, inside H7: at most 3 live c8d2 AMD-pool jobs).
  - **A-RPL-8 (570371): PASS.** Every default and diagnostic executable is byte-identical to the Stage-5 symmetry build
    (decimal `619ddf7d…`, gmp `2cc5e88e…`; sanitizer builds after normalization); `make gmp NUMERICS=dd,mp256` gives
    the gated `d5df32ac…`.
  - **X3 on Linux (570371): PASS.** `tests/thread_identity.py`: rows identical, every observed team equal to the request
    (1, 8, 16, 64; 8 × 8 lanes), also with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true` inherited.
  - **J-GEN-1 (570374): PASS.** test_keys 97/97 (X6), test_regress 86/86, test_handoff_inventory 17/17, A-INV-2 at
    L3–L7 with threads 1 and 8; its record passes `regress.h1_problems` (X5).
  - **J-VAL-1 (570372): PASS.** `make test` exit 0 in 1,106 s (unit_orchestration 49 groups / 61 tests on Linux with the
    real worker, X8 with the real `ldd`), assembly_checks 37/37, verify_result_tamper 81/81, compat_2026.
  - **X8 on real Slurm (570376, 570377): PASS.** A tiny test campaign on two sharedq nodes: a claim under a libgmp copy
    with one byte appended exits 64 naming `libgmp.so.10`; with the pin moved aside, run-skip refuses the other stack's
    checkpoint and `merge --jobs 2`, `--jobs 1` and `--serial` refuse; another host with the same libraries is
    accepted; the restored campaign merges. X13 was not run on real Slurm (its race cannot be forced cheaply; the Linux
    unit test ran in J-VAL-1).
  - **The `dd+mp256` J-FLAG gate re-run (570373): PASS**, record `2eaaebcf…`, accepted by the fixed `check_gate`: F1
    coverage complete (X1), both executables reproduced byte for byte in the source snapshot (X2), every F5 team
    verified (X3); F1, F2 (|dC8| + 3 SE_d = 4.25e-16) and F3 equal to 570210's field by field; F4 ×2.539. It replaces
    570210's record as the route-(b) `--numerics-gate`.
  - **Route-(b) re-freeze (570379): PASS.** The four freezes with the new record give pre6b's designs byte for byte;
    their test-only plans (not submitted, deleted) hold every cap, record the gate, the pinned bundle copy (X9) and
    `cost_model_numerics` (X10).
  - `~/c8d2/env.sh` edited for X11 (`e5fdb68c…` → `d1e900e9…`). Five new seeds in symmetry's log and the mirror (98 →
    103), pending for Expanse's (`stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`). Symmetry total 535.6 core-hours.
- **Mac** (`benchmarks/mac_2026-10-c8/s6fix1int/`): `C8_ALLOW_NO_L8=1 make test-python` passes on c30bfc5's tree (counts
  there), and `tools/verify_delivery.py --write` then `--strict` pass before each commit.

## 2026-10-05: Stage-6 policy fix: the pilot stays exact, every non-exact non-test plan runs a gated build; freeze enforces a gated profile cost model [A-FLAG-2, A-FLAG-6, A-DES-1, A-PKG-2]

`numerical_change: false` (no `src/` change; the default path, every exact plan and every design's numbers are
unchanged). Mac only, no job. Closes the MEDIUM-LOW policy gap and the LOW items of the last pre-Stage-6 verifier
(`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "Design-tool fixes before Stage 6"), per the user's decisions of 2026-10-05
(`dd+mp256` for production after the pilot; the smoke and the pilot stay exact; `exp1` and R7 off).

- **`tools/production.py` `plan`.**
  - **The pilot stays exact.** A non-test `--pilot` under any numerics other than exact, or under `--rates`, is refused
    unless its key (numerics, rates identity) is in the new allow-list `APPROVED_PROFILE_PILOTS` ({(profile or exact,
    'default' or the map's sha256): user approval reference}), which is **empty**: a profile pilot (route (a)) or an
    R7 measurement pilot needs the user's explicit go. It comes after the `APPROVED_PROFILES` and `APPROVED_RATES`
    checks, which still apply. Test-only pilots (J-FLAG gates, sweeps, the smoke) are unchanged.
  - **A gated build for every non-test plan whose numerics are not exact.** Route (b) as before (the executable must
    be a profile executable of one of the bundle's gate records). Every other such plan (a route-(a) bundle, an
    approved profile pilot) needs the new `--numerics-gate RECORD` (repeatable): each record passes
    `design.check_gate` (a passed, full-scale J-FLAG gate of the profile's production build, F2 over every graph of the
    plan's inventory), no record twice, and the plan's executable must be one of the gated builds
    (`gated_route`). The manifest's `numerics_route` records it (route `a` or `pilot`, the gates, the plan approval,
    the pilot's go). `--numerics-gate` is refused on an exact plan and on a route-(b) bundle (which carries its own
    gates); in a test-only plan it is optional and, when given, must cover the build. `production.py` is a pinned
    tool: the planned pilots are re-planned after Stage 6 anyway.
- **`tools/design.py`.** `freeze --numerics P` (route (b)) refuses a profile cost model whose executable is not one of
  the `--numerics-gate` records' gated builds (`cost_model.executable_gated`, recorded before, now enforced; the
  symmetry model and the 570210 gate are both `d5df32ac…`). Documented (docstrings, `OPTIMIZER`, `docs/DESIGN.md`
  rules 4 and 6): the prune pass stops at the first best halving that fails a cap (a halving adds no task, checkpoint
  or replicate, so only a greedy design that already misses a cap reaches it); "never costlier than either rule"
  holds at a fixed batch count K, and the minimum K is that of the optimized design (it may be smaller than the old
  tool's; J-DES-5 has K = 1); a route-(b) bundle that keeps the exact design records the exact search and K_min, the
  re-optimized branch in `route_b_choice`. No design number changes.
- **Tests.** `tests/test_pipeline.py` (24): new `pilot_exact_gated_nontest` (10 refusals: a non-test `dd+mp256`
  pilot refused with and without a gate; with `APPROVED_PROFILE_PILOTS` monkeypatched refused without a gate, with
  another build's gate and with a failed gate, accepted with the gate; a non-test route-(a) `dd+mp256` bundle refused
  without a gate and with another build's, accepted with the gate; `--numerics-gate` refused on an exact plan and on
  a route-(b) bundle; a test-only `dd+mp256` pilot accepted without a gate and refused with another build's); the
  R7 non-test measurement pilot now also needs `APPROVED_PROFILE_PILOTS` (refused with `APPROVED_RATES` patched
  alone; the wrapper patches both); route (b) in process gains the refusal of an ungated profile cost model (22).
  `tests/unit_orchestration.py`: new `route_b_records` (every refusal branch of `production.route_b`'s record and
  final checks, of `design.check_gate`'s schema, mode, status, development, verdict, F2-total, describe, build-record,
  sha256 and full-scale checks, and of `gated_route`).
- **Mac suites** (`benchmarks/mac_2026-10-c8/s6policy/`): `make test-python` with the Mac Python, all passed (counts
  there).
- **Docs:** `docs/DESIGN.md` (rules 4 and 6, "Route (b)", the decision step and table, tests), `docs/NUMERICS.md`
  (user decision), `docs/PERFORMANCE.md`, `docs/HPC.md` (pilot runbook), `README.md`,
  `benchmarks/symmetry_2026-10-c8/stage5/pre6/README.md` (the gate rule now holds for every non-exact non-test plan).

## 2026-10-05: Pre-Stage-6b on symmetry: the fixed `design.py` of 77fab71 confirmed on J-DES-5's real data (F13, F11 follow-up) [A-DES-5, A-PERF-4]

`numerical_change: false` (no tool, test or `src/` change; evidence and docs only). Job 570302 on symmetry sharedq
(4.1 core-hours) from the export of 77fab71 itself, the job scripts staged outside it; evidence
`benchmarks/symmetry_2026-10-c8/pre6b/` (README, `p6b_tables.py` → `p6b_tables.json`, `p6b_tables.md`).

- **Executables:** `make gmp` and `make gmp NUMERICS=dd,mp256` on an Intel sharedq node give `2cc5e88e…` and the gated
  `d5df32ac…`, byte-identical to 570239's AMD builds.
- **Exact freezes** (`design.py freeze --test-only` on J-SWEEP-2, J-DES-5's arguments): 1,702 / 5,740 / 22,961 /
  74,573 lane core-hours at SE 46.00 / 23.00 / 11.50 / 6.21 (570241: 1,738 / 5,856 / 23,423 / 76,623); base counts
  unchanged.
- **Route-(b) freezes** (`dd+mp256`, profile model `9b0dfec6…`, gate 570210): a freeze keeps 638 (re-optimized) / 2,241
  / 8,963 / 29,328 (the exact design kept) lane core-hours, every SE at its target (570241: 923 / 3,322 / 13,289 /
  33,978; its exact allocation kept: 669 / 2,309 / 9,236 / 30,067); ×0.375-0.393 of the new exact path.
- All eight designs equal the Mac recomputation of 77fab71 (`tests/test_pipeline.py`, `jdes5_records`: r, s, branch,
  cost and SE; relative difference ≤ 8e-15). Every per-graph cap holds in every bundle (the kept exact designs under
  the profile's costs included) and in all eight test-only plans (`production.py plan --design`, not submitted;
  route-(b) plans `executable_gated: true`); all plan directories deleted.
- **Docs:** `docs/PERFORMANCE.md` (the Stage-6 rows of the measured table now measured, both route-(b) branches),
  `docs/DESIGN.md` (the F13 table marked confirmed on symmetry), `README.md`, `docs/HPC.md` (8 seeds pending for
  Expanse), `benchmarks/symmetry_2026-10-c8/README.md` (pre6b row; total 495.7 core-hours), `stage5/README.md` (F13
  row), `pre6/README.md`.
- **Seeds:** eight new seeds (one per plan) in symmetry's log (98) and the mirror `designs/forbidden_seeds.json` (90 →
  98); pending for Expanse's log in `benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`.

## 2026-10-05: Before the Stage-6 inspection: F13 and the F11 follow-up fixed in `design.py` (the integer optimizer, route (b)'s keep-cheaper); the allow-lists bind every non-test plan; A-PKG-2 docs refresh [A-DES-1/2/5/6, A-FLAG-2, A-FLAG-6, A-PKG-2]

`numerical_change: false` (no `src/` change; the default path's numerics and the design's predicted SE are unchanged in
kind: every design's SE is computed exactly from its own integer allocation). Mac only, no job. The pre-Stage-6
verifier's findings: F13, the F11 non-monotone case, the allow-list scope gap and the docs items.

- **`tools/design.py` `optimize()` (F13, F11 follow-up).** The integer allocation is searched from both split rules,
  the F11 rule (r from the smallest multiplier) and the Stage-5 rule (r from the largest): split, the greedy loop
  (unchanged), then for a target a **prune pass** (halve one stratum's allocation r·s wherever the predicted SE still
  meets the target, the halving saving the most first, to a fixed point), then a **bounded local lattice search** over
  the power-of-two allocations (boxes of a_k·2^d, |d| ≤ 2, around the split point and the incumbent, recentred after
  every improvement, at most 32 boxes, each solved exactly by meet in the middle: least cost with SE ≤ target, or
  least SE within a budget), every candidate confirmed by `evaluate_design` and held to every per-batch cap
  (`caps_check`, memoized; at most 16 cap failures per box). The better start is kept (F11 on ties), so a design is
  never costlier (or, for a budget, less precise) than either old rule's greedy design; deterministic; the predicted SE
  exact. `design_meta.json` records both starts (`optimizer`). `split()` takes the rule as a parameter (default F11).
- **Route (b) keeps the cheaper (F13, the verifier's option (b)).** `design.py freeze --numerics P` designs both ways:
  the re-optimized design (base counts and allocation from the profile model's c_g) and the exact path's design (its
  base counts, r, s and K) re-costed under the profile; the exact one is kept only when it meets the target (or
  budget) and every cap under the profile's costs and is strictly cheaper (more precise). `design_meta.json` records
  both (`route_b_choice`); `report --numerics P` prints the branch per target.
- **J-DES-5's strata** (the committed records of 570241; lane core-hours): exact path 1,738 / 5,856 / 23,423 / 76,623 →
  **1,702 / 5,740 / 22,961 / 74,573**; route (b) 923 / 3,322 / 13,289 / 33,978 → re-optimized 638 / 2,554 / 10,215 /
  31,371 (the verifier's lattice optimum near its split), the new exact allocation kept 646 / 2,241 / 8,963 / 29,328,
  a freeze keeps **638 / 2,241 / 8,963 / 29,328** (re-optimized at 1e-3, kept at the others); every SE at its target.
- **Allow-list scope (`tools/production.py` `plan`).** Every NON-test plan refuses numerics outside
  `APPROVED_PROFILES` = {`dd+mp256`} (`plan --pilot --numerics P`, `plan --design` of a route-(a) or route-(b)
  bundle), with or without `--approved-numerics-change`, and refuses `--rates` unless the map's sha256 is in the new
  `APPROVED_RATES` (empty: R7 stays off). Test-only plans (gates, sweeps) are unchanged. `production.py` is a pinned
  tool: the planned pilots are re-planned after Stage 6 anyway.
- **`tests/test_pipeline.py`** (23 tests): `check_optimizer` replaces the r-rule check (every target bundle: the
  target met, never costlier than either old rule's greedy design recomputed by hand, no cheaper feasible single
  halving or halve-one-double-another move); a randomized property test (2,000 seeded random stratum sets at a target,
  600 at a budget; the old F11 rule alone is costlier than the Stage-5 rule in 16 of them, the optimizer never);
  `jdes5_records` (the table above from the committed records, the keep-cheaper choice by hand); route (b)'s choice
  recomputed independently with both branches exercised (`check_route_b_choice`), in process and on the command line;
  the A-FLAG-6 non-test acceptance with `APPROVED_RATES` monkeypatched (a wrapper) and the unpatched non-test plans
  under the map refused; `allow_list_nontest` (non-test `plan --pilot --numerics dd | mp256 | exp1 | dd+exp1 |
  dd+mp256+exp1` and route-(a) `plan --design` under `dd` and `dd+mp256+exp1` refused; a test-only `dd` plan accepted).
- **Mac suites** (`benchmarks/mac_2026-10-c8/f13fix/`): `test_pipeline.py` 23/23, `unit_orchestration.py` 41 groups /
  53 tests, `ast_scan`, `test_regress`, `merge_scale`, `check_vendored`, `vendored_isolated`, `test_delivery_verifier`,
  `check_inputs`, `test_profiling`, `test_gmp_prefix`, `test_numerics_flags`, `test_dd_profile`, `sanitize
  --capture-check`, `check_venv`: all passed.
- **Docs (A-PKG-2 refresh after 32e5f2b):** `README.md` status (seed sync done; J-EXP-1 rerun partial, job 54681003,
  A-EXP-3 to be completed after Stage 6 on the post-inspection commit; F13 fixed; allow-lists), `docs/DESIGN.md` (rule
  4, the F11 follow-up, F13 with the corrected cause and the table, the allow-list scope, tests), `docs/PERFORMANCE.md`
  (F13 cause, Stage-6 rows), `docs/HPC.md` (Expanse items, the pinned-tool changes), `docs/NUMERICS.md` (Expanse items,
  route (b)), `benchmarks/symmetry_2026-10-c8/README.md`, `pre6/README.md` (cause corrected, fixed),
  `stage5/README.md` (F13 row, F11 follow-up), `stage5/pre6/README.md` (the profile sweep has run; the "can only do
  better" sentence), this file (the 32e5f2b entry below; the F13 cause corrected).

## 2026-10-05: Pre-Stage-6 on symmetry: the `dd+mp256` profile cost model and the J-DES-5 re-check (F11 fixed, route (b)); finding F13 [A-RPL-8, A-DES-5, A-PERF-4/5]

`numerical_change: false` for the default path (no tool, test or `src/` change). Jobs 570239-570241 on symmetry from
the export of 3a250ea (99bbfdd plus the job scripts `benchmarks/symmetry_2026-10-c8/pre6/scripts/`), 12.6 core-hours;
evidence `benchmarks/symmetry_2026-10-c8/pre6/` (README).

- **Build, A-RPL-8 (570239): PASS.** decimal `619ddf7d…` and gmp `2cc5e88e…` byte-identical to the Stage-5 build;
  `bin/c8d2_gmp_dd+mp256` `d5df32ac…`, the build the J-FLAG gate 570210 passed.
- **`cost_models/gmp_symmetry_amd_c8_dd+mp256.json`** (new, `9b0dfec6…`): the route-(b) cost model, a J-SWEEP-2-shaped
  sweep of the gated profile build on J-SWEEP-2's node (570240; all 48,346 keys, numerics identity `dd+mp256`, the
  approval reference in the campaign manifest and the model's note). Speedup over the exact symmetry model ×2.814
  (free L8 ×2.754, power L8 ×2.965, free L7 ×2.778, power L7 ×3.448).
- **J-DES-5 re-check (570241), exact path, F11-fixed `design.py`:** 1e-3 now 1,738 lane core-hours (SE 44.21 of 46),
  exactly the Mac projection; 5e-4 / 2.5e-4 / 1.35e-4 `design.json` byte-identical to J-DES-5's. Route (b): four
  freezes (approval, profile model, gate 570210) and their test-only plans run end to end with the gated executable;
  every cap holds in all eight plans; all plans deleted.
- **Finding F13 (`tools/design.py` `optimize()`, for Stage 6):** the route-(b) freezes cost 923 / 3,322 / 13,289 /
  33,978 lane core-hours and over-deliver the SE (35.8 / 18.5 / 9.3 / 5.9), 1.13-1.44× the exact allocation kept and
  re-costed under `dd+mp256` (669 / 2,309 / 9,236 / 30,067, ×0.385-0.394 of the exact path, meeting every target).
  Cause (as corrected by the pre-Stage-6 verifier's replay): the split starts 2.2-9.9% short of the target; at 1e-3,
  5e-4 and 2.5e-4 the greedy loop doubles free L7, power L6 and power L5 and then free L8 (about half the cost,
  +48-56%) to close a remaining SE gap of 0.57% (1e-3) or 2.64% (5e-4, 2.5e-4); at 1.35e-4 free L6 and then free L7
  (+20%) close 1.76%, and free L8 is not doubled. Not changed here (fixed in the entry above).
- **Docs:** `docs/PERFORMANCE.md` (measured table, F13, the A-PERF-5 column from the profile model; the "route (b) can
  only do better" sentence corrected), `docs/DESIGN.md` (F13 note under "Route (b)"; the profile model exists),
  `README.md` status, `benchmarks/symmetry_2026-10-c8/README.md` (pre6 row, total 491.6 core-hours),
  `stage5/pre6/README.md` (the corrected sentence).
- **Seeds:** nine new seeds (the sweep and eight plans) in symmetry's log (90) and the mirror `designs/forbidden_seeds.json`
  (81 → 90); Expanse's log already holds them (the Expanse workflow's sync at 19:53:52Z, 32e5f2b).

## 2026-10-05: Expanse before Stage 6: the two-log seed sync done; the J-EXP-1 rerun partial (Lustre incident) [A-EXP-3, D9] (32e5f2b)

`numerical_change: false`. Expanse only, for its own two items; symmetry read only (`benchmarks/expanse_2026-10-c8/pre6/`,
driver `scripts/p6x.sh`; 44.4 SU).

- **Export** `pkg/99bbfddd0719` (git archive of 99bbfdd; 8,268 files equal). No export deleted.
- **Seed sync: DONE.** Three passes of `tools/seeds.py merge` into Expanse's log (symmetry's log only read): 78 → 81
  (the 3 seeds of `PENDING_EXPANSE_SYNC.txt`) → 89 → 90 (the symmetry agent's 9 pre-Stage-6 seeds). Expanse
  (`e8efb766…`) and symmetry (`d4c73223…`) hold the same 90 seeds; the mirror got them in d8ba6a2.
  `PENDING_EXPANSE_SYNC.txt` marked synced.
- **J-EXP-1 rerun (A-EXP-3): PARTIAL.** Job 54681003 on debug (`-t 00:30:00`, the partition's limit), <NODE>: the
  build, A-RPL-8 (decimal `99a51c1d…`, gmp `1d2a2181…`, inspect and c7ref identical), Boost 1_77 in every build
  record, `check_venv --strict`, `validate` and 12 `unit_orchestration` groups passed; cancelled after 20:50 because
  Expanse's Lustre was failing (debug nodes drained by Lustre health checks; the build took 430 s against 33 s). F1,
  F3, F4 of `make test` not reached; owed after Stage 6 on a fresh export.

## 2026-10-05: Docs before the Stage-6 inspection: G5 status, F11 fixed (23540b2), route (b), symmetry's own dd+mp256 factors, Expanse items [A-PKG-2, A-PKG-4, A-PERF-4/5, A-DES-4]

`numerical_change: false`. Docs and Mac evidence only (no tool, test or `src/` change); no job.

- **README.md status block** (the G5 re-check's D1): G5 passes except the Expanse-owed items; F1-F10 and F12 fixed and
  validated (86e15f4, d5dfd38; `stage5/fix/`, `stage5/close/`); F11 fixed in 23540b2; the `dd+mp256` gate passed
  (570210) and route (b) is implemented; symmetry first; owed on Expanse: the J-EXP-1 rerun and the seed sync (the
  export deletion is done). Layout rows of `design.py` and `sweep.py`.
- **docs/DESIGN.md**: rule 4 and "F11" (the smallest-multiplier rule, its variance-cost argument and effect); "Route
  (b)" (commands, allow-list, cost model, σ kept, gate record, what is recorded, report); `plan --design` and
  `combine` for route (b); the post-pilot decision step (gate passed; route (b) implemented, route (a) still possible);
  defaults and tests.
- **docs/PERFORMANCE.md**: the symmetry `dd+mp256` row on symmetry's own gate factors (1,581 / 2,298 / 9,193 / 30,503
  core-hours, ×0.392-0.399, for J-DES-5's freezes); a table of the F11-fixed 1e-3 design (1,738 lane core-hours on
  symmetry, 1,640 SU on Expanse; `dd+mp256` 678 and 742); the A-PERF-5 `dd+mp256` column on symmetry with the measured
  factors. Evidence: `benchmarks/symmetry_2026-10-c8/stage5/pre6/` (`pre6_tables.py`, Mac, from committed records).
- **docs/HPC.md**: the pilot runbook names 86e15f4, d5dfd38 and 23540b2 as the pinned-tool changes since the pilots
  were planned; the 570210 record as the route-(b) gate; the Expanse export deletion done. **docs/NUMERICS.md**: the
  user-decision paragraph (route (b), symmetry's factors) and the Expanse items.
- **benchmarks**: `symmetry_2026-10-c8/README.md` (a section with the status of `stage5/fix`, `stage5/close` and
  `stage5/pre6`), `stage5/README.md` (a Status column for F1-F11 and an F12 row), `stage5/des5/README.md` (η_node is
  busy over WORK core-hours: a work column; F11 fixed), `expanse_2026-10-c8/README.md` and `stage5/fix/README.md` (the
  29 exports deleted by the host on 2026-10-05 with the user's approval, `pkg/d46e7360fe88` kept because job 54669708
  read it, Lustre 1,651,026 → 1,474,822 files; a status table of the Expanse items), `mac_2026-10-c8/pre6/` (the Mac
  suite of 23540b2).

## 2026-10-05: F11 fixed (design.py split: r from the smallest multiplier); route (b) for the approved dd+mp256 profile [A-DES-1/2/6, A-FLAG-2, D1, D15]

`numerical_change: false` for the default path: no file under `src/` changed, no executable, native row or exact
design rule other than the split changed. Changed: `tools/design.py` (not pinned by plans), `tools/production.py`
(pinned: campaigns planned with the earlier tools are re-planned, as the pilot already must be), `tools/sweep.py`,
`tests/test_pipeline.py`. Made and tested on the Mac only; no job.

- **F11 (J-DES-5).** `design.split()` gave a (sector, L) the replicates r of its LARGEST stratum multiplier, so at 1e-3
  the cheap free L8 primitives (multiplier 176.8) set r = 128 for the dominant free L8 stratum (35.1): 2.98x the
  continuous Neyman cost. r is now the largest power of two in [min, max replicates] not above the group's SMALLEST
  positive multiplier. With s >= 1, r is a floor on every stratum's allocation; r <= min m forces nothing, and every
  stratum gets r x pow2_round(m/r) = pow2_round(m), its best power-of-two allocation (the variance-cost optimum among
  power-of-two designs); a stratum forced to rho = r/m would inflate variance x cost by 1 + w(1-w)(rho-1)^2/rho. Only
  free L8 has two strata; every other (sector, L) keeps its r. On J-DES-5's strata the 1e-3 design costs 1,738 instead
  of 3,963 lane core-hours on symmetry (SE 44.2 against 46); 5e-4, 2.5e-4, 1.35e-4 are unchanged. The predicted SE
  stays exact (computed from r and s; `report --bundle` recomputes it from the counts). The recorded rule text says so.
- **Route (b)** (host decision 2026-10-05): `design.py freeze --numerics P --approved-numerics-change REF --cost-model
  M --numerics-gate RECORD` freezes a bundle from an EXACT default-rate pilot under an approved profile.
  `production.APPROVED_PROFILES` is the allow-list, the user-approved set {dd+mp256} with its approval reference; any
  other profile is refused by freeze, report and plan, as is a c8-d3 pilot. The cost model must be measured under P
  (numerics identity = P, the pilot's backend and rates identity, every inventory graph); every graph's cost is the
  model's, so the base counts, multipliers, cost and caps are re-costed, while sigma^2, eta_omp and eta_node stay the
  exact pilot's (justified by the F2 gate: |dC8| + 3 SE_d = 4.25e-16 for dd+mp256, job 570210). The gate record must be
  a passed full-scale J-FLAG record of P's production build (status passed, no development option or parameter
  override, F1/F2/F5 passed, F2 over every inventory graph). `design_meta.json` records `profile_recost`: profile,
  approval, allow-list and reference, each gate (path, sha256, Slurm job, gated profile and exact executables, F2
  totals), the exact pilot's identity and the cost model's sha256 and identity; the bundle's numerics is P.
  `design.py report --numerics P --cost-model M` prints the re-costed table.
- **plan --design of a route-(b) bundle** (`production.route_b`): needs `--numerics P --approved-numerics-change`
  (unchanged rule) and a `--cost-model` whose numerics identity is P; refuses a profile outside the allow-list (before
  any executable is described), a bundle whose numerics differ from its pilot's without a complete record, a
  development build (unchanged) and, non-test, an executable that none of the bundle's gates passed. The manifest
  records `numerics_route` (profile, allow-list reference, both approvals, gates, exact pilot, both cost models, the
  executable and whether it was gated). `combine.py` still refuses mixing exact and profile batches.
- **sweep.py --numerics P** (opt-in, needs `--approved-numerics-change`) measures a cost model under a profile; it
  must name its own `--calibration` file (calibration rows carry no numerics key) and a rerun checks the numerics.
- **Tests** (`tests/test_pipeline.py`, 20 records, 16 before): F11's rule checked independently on every target bundle (A-DES-1,
  d = 3, imputed subsample, route (b)); a synthetic full-size pilot reproducing F11 (old rule 2.85x, fixed 1.09x the
  independently recomputed continuous optimum); route (b) in process (non-uniform re-costing recomputed independently,
  sigma kept, 21 refusals), test-only on the command line through combine, and non-test through plan (acceptance with
  every piece; refusals without the approval, with a cost model of another identity, a profile outside the set, a
  development build, an ungated build, an exact plan, a bundle without the record).

## 2026-10-05: Stage-5 close-out on symmetry: F12 confirmed on real Slurm, J-VAL-1, the dd+mp256 J-FLAG gate PASSES [A-ORC-13, R07, J-VAL-1, A-RPL-8, A-FLAG-3]

`numerical_change: false`. No code changed: job scripts (`benchmarks/symmetry_2026-10-c8/stage5/close/scripts/`,
68ee571), evidence and docs only. Symmetry only (user rule 2026-10-05); Expanse not touched. 55.1 core-hours (jobs
570208-570212; `benchmarks/symmetry_2026-10-c8/stage5/close/README.md`).

- **Build and A-RPL-8** (570208, export 68ee571ee614 = 08e728a plus the job scripts): every default and diagnostic
  executable byte-identical to the Stage-5 symmetry build (decimal `619ddf7d…`, gmp `2cc5e88e…`; sanitizer builds after
  normalizing the embedded path); `bin/c8d2_gmp_dd+mp256` `d5df32ac…` (`make gmp NUMERICS=dd,mp256`) leaves them
  unchanged.
- **A-ORC-13 on real Slurm with the F12 fix (570212): PASS without correction.** The fix round's 22 claims, on a fresh
  campaign `io-68ee571ee614` (seed 3934799973789933184): all records `c8-d2-claim-io-2` with the exact read path;
  `tools/claim_io.py` exit 0, non-own bytes 29.85 MB (a_free_L3) against 30.31 MB (b_free_L8), difference 0.46 MB
  against 2.28-2.99 MB (before the fix: 694-706 MB at L8). A b_free_L8 claim reads 671 MB less.
- **J-VAL-1 on the fixed tools (570211): PASS.** `make test` exit 0; unit_orchestration 41 groups / 53 tests; Linux
  `pack_reads`: rchar across `stage_graphs` = member bytes; assembly checks 37/37, tamper 69/69, compat exit 0.
- **The user-required `dd+mp256` J-FLAG gate (570210, one amdq node, GCC 11.4): PASS** at full scale. F1 0 violations
  (dd max 5.18e-12); F2 |dC8| + 3 SE_d = 4.25e-16 against 0.062, per task max 5.58e-14; F3 unchanged; F5 identical;
  F1/F2/F3 records equal Stage 4c's Expanse `dd+mp256+exp1` record field by field (apart from exp1's counters). F4 on
  symmetry ×2.530 (free ×2.485, power ×2.644). `dd+mp256` is cleared for production on symmetry after the pilot
  (`docs/NUMERICS.md`, "The `dd+mp256` J-FLAG gate on symmetry"). No F2 seed added (49 present).
- **Seeds.** One new seed, 3934799973789933184, in symmetry's log and the mirror; appended to
  `stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the owed Expanse sync.
- **Docs.** `docs/NUMERICS.md` (gate section, user-decision status), `docs/HPC.md` (F12 confirmed; gate passed; Zen 2
  label of symmetry's EPYC 7532), `docs/PERFORMANCE.md` (gate-pending labels; the symmetry `dd+mp256` row still uses
  Expanse's factors).
- **Still owed:** on Expanse only (J-EXP-1 rerun, seed sync, deletion of the 30 exports; `docs/HPC.md`, "Sites:
  symmetry first").

## 2026-10-05: F12, the claim's pack over-read, fixed (d5dfd38); symmetry-first site rule recorded [A-ORC-13, A-ORC-7, R07, A-EXP-3]

`numerical_change: false`. No file under `src/` changed: the executables, every native row and every staged byte are
unchanged. Changed: `tools/production.py`, `tools/stage_runtime.py` (pinned: a campaign planned with the earlier tools
must be re-planned), `tools/claim_io.py`, `tests/unit_orchestration.py`, the docs. Made and tested on the Mac only.

- **F12 (found by the post-merge real-Slurm A-ORC-13 run on symmetry, job 570170;
  `benchmarks/symmetry_2026-10-c8/stage5/fix/`).** `production.stage_graphs` read each block's pack members with
  `open(pack,'rb')`, `seek`, `read`: Python's buffer is the file system's `st_blksize` (524,288 bytes on BeeGFS), and a
  buffered read after a seek refills one whole buffer, so a claim read up to 512 KiB of neighbouring pack data per
  member (0.70 bytes per staged byte at L8, about 0.7 GB of extra reads per L8 index) that its own-bytes count did not
  include, and `tools/claim_io.py` failed (22.8 MB against 694-699 MB). Now `production.read_member` reads exactly
  `length` bytes at `offset` with `os.pread` in a loop over short reads (no Python buffer; chunks of at most 1 GiB), and
  `stage_graphs` returns the bytes it read, which the claim records as its own `staged_members` bytes; the sha256
  checks and the staged files are unchanged. `stage_runtime.py`'s member copy (array mode, `C8_STAGE=1`) reads the
  same way. The `claim_io` record's schema is now `c8-d2-claim-io-2`; `tools/claim_io.py` reports the runs per pack
  read path (`pack_reads`) and names records of `c8-d2-claim-io-1` (buffered) in `notes`, and its docstring, the
  production docstrings and `docs/HPC.md` drop Stage 5's wrong explanation (the native re-reading its staged files:
  the native reads its copies once, 1.0008 bytes per staged byte at L8).
- **Tests.** New `pack_reads` (unit_orchestration): every `os.pread` counted on a fake pack whose members sit around
  and above 512 KiB (bytes read = member bytes, every read inside a member, short reads, end of file, a truncated pack
  refused with its descriptor closed); the control replays the pre-fix read through a 512 KiB `BufferedReader` over a
  counting raw file and matches the F12 replay model exactly; on Linux, rchar across `stage_graphs` must equal the
  member bytes. `staging` counts the shared-pack bytes `stage_runtime` reads; the A-ORC-13 spy (`claim`) counts
  `os.pread` and requires the pack to be opened only with `os.open` and its bytes to equal the claim's own staged
  bytes; `claim_io` checks the schema and the read-path report. `pack_reads`, `staging` and `claim` fail with the
  pre-fix read swapped in. Evidence: `benchmarks/mac_2026-10-c8/f12fix/`.
- **Owed on symmetry:** the A-ORC-13 real-Slurm rerun with the fixed tools (about 15 core-hours) and J-VAL-1 on the
  fixed commit. Owed on Expanse (`docs/HPC.md`, "Sites: symmetry first"): the J-EXP-1 rerun, the seed sync, the
  user-approved deletion of the 30 obsolete exports. The `dd+mp256` J-FLAG gate runs on symmetry.

## 2026-10-05: Stage 6 fixes of the G5 verifier's defects F1-F9 and the A-PERF-4 calibration [A-ORC-8a, A-ORC-12, A-ORC-13, A-SMK-1, A-EXP-3, A-PERF-4, A-ASM-7]

`numerical_change: false`. No file under `src/` changed (D1): the default executables, every native row and every
merged batch are unchanged. Changed: `tools/` (production, lanes, assemble, verify_result, common: pinned tools, so a
campaign planned with the earlier tools must be re-planned), `tests/`, `slurm/`, the docs and the active calibration.
Every change was made and tested on the Mac only; the cluster reruns it needs are listed at the end.

- **F8 (A-ORC-12): recovery of a completed index merges and assembles.** `merged.json` is a group's commit point
  (`production.py` `_publish_copy`): a table without a `merged.json` is uncommitted and a different one is replaced
  atomically and reported (`graph_costs.csv`, timing only, changes whenever a block is recomputed; a changed scientific
  table is reported as such), while a committed table must stay identical. `merged.json` records the digests of the
  bytes the merge published. `assemble.publish_result` (also behind `combine.py`) supersedes a result whose only change
  is `merged_sha256` (scientific content unchanged), keeping the old bytes as `<name>.superseded.<sha12>.json`, and
  still refuses any other difference. New test `recovery_merge` (unit_orchestration): J-DRL-8 run unattended through
  `slurm/merge.sh` on fake Slurm with a recompute of other timings; it fails on the earlier code at exactly the two
  Stage-5 points ("Checksum mismatch" on `graph_costs.csv`; "exists and differs") and passes now.
- **F7 (A-ORC-8a): stop signals in lane mode.** `lanes.py` `StopGuard`: the worker forwards SIGTERM (SIGINT, SIGHUP)
  to its lanes and each lane to its `production.py run` (started in its own session), which stops its native worker
  and removes its runtime; the lane removes its scratch and exits 143 with its claim left stale and no failure record.
  Bounded waits: the worker `C8_LANE_STOP_SECONDS` (25 s, below KillWait 30 s), a lane 0.8 × that, then the run's
  session or the lane is killed and the worker removes any lane scratch of its job left in `$TMPDIR`. New test
  `lane_sigterm` (fakes; SIGTERM to the worker alone, as slurmstepd delivers it): exit 143 in 0.03 s, nothing left in
  `$TMPDIR`, no native worker alive, claims stale, the same job id then finishes the campaign; with a native that
  ignores SIGTERM the run is killed after 3.2 s and the scratch still goes. It times out on the earlier code.
- **F9 (A-ORC-13 real Slurm, R07): rchar per claim.** Each `production.py run` logs `claim_io {json}` at exit: rchar
  of `/proc/self/io`, the native launches' own rchar (the delta across each launch), `fingerprint_bytes` and
  `fingerprint_rchar`, the claim's own bytes per category, and `non_own_bytes` (with and without the fingerprint).
  New `tools/claim_io.py` evaluates the plan's smallest-vs-largest-group comparison from the logs. Deviation (recorded
  in `docs/HPC.md`): the native re-reads its staged graph files, so its reads are measured and subtracted as own work
  instead of the staged members once. Tests: `claim_io` (record arithmetic with a stand-in counter, the tool's pass,
  fail and undecided cases, a lane campaign's records) and the A-ORC-13 spy test (the `/proc/self/io` reads, 6 for a
  one-block claim, are a measurement class; on Linux the two campaigns' non-own bytes must agree within max(10%, 2 MB)).
- **F6 (A-SMK-1): `verify_result.py` on any BLAS kernel family.** `linear_response_residual[k]` is compared within
  64 eps M_k (M_k the magnitudes the residual is a difference of, from the gate's own perturbation); the largest spread
  measured is 6.5 eps M_k (13 Stage-5 results recomputed on the Mac, of which the earlier verifier rejects 8 there) and
  0.47 for the smoke on the symmetry login node. The power null checks get the gates' 1e-2 scale floor. New checks in
  `tests/verify_result_tamper.py` (69/69): three real Stage-5 results (`tests/fixtures/verify_result_cross_machine/`)
  verify here, a product order changed verifies, a residual moved by 8 eps M_8 verifies, by 2 x the bound or 1e-6 |C8|
  is rejected, and the null-check floor accepts rounding-level and rejects larger changes; the tamper cases still fail.
- **F5 (operations): one CPU vendor per campaign.** The first claim pins the vendor (with family and model) in
  `$C8_RUN/cpu_vendor.json`; every checkpoint records its claim's CPU (`runtime.cpu`); a claim on another vendor stops
  before any block (exit 64, both vendors named); a lane worker refuses (64) before any claim; a refused lane releases
  its claim and stops; `status` prints the pin. The vendor comes from the fingerprint's one read of `/proc/cpuinfo`
  (`common.cpu_identity`), outside `fingerprint_key`. `slurm/env.sh.example` drops `-p amdq,defq`; `docs/HPC.md`
  corrects "Nothing depends on the node" and explains the x87 `expl`/`logl` dependence. Test `cpu_vendor`.
- **F1:** `test_lanes` runs pinned to at most 16 CPUs (`at_most_cpus`, restored). **F3:** `repr(float(delta))` in
  `tests/test_numerics_flags.py`. **F2:** pytest in `requirements.txt` (and 9.1.1 in `requirements-tested.txt`); new
  `tests/check_venv.py` (G0's venv check with `--strict`; first step of `make test-python`). **F4:** `tests/sanitize.py`
  runs its self-test probes on a pseudo-terminal (stdout and stderr), so GCC <= 12's assertion text is captured; new
  `--capture-check` (a Python probe that loses its report on a pipe and shows it on the pty), also in `make test-python`.
- **A-PERF-4:** `tools/calibration.json` holds the symmetry J-SWEEP-2 rows of the final binary (`d85dd7c0…`); the
  Expanse J-SWEEP-2E rows are the pinned copy `cost_models/calibration_expanse_amd_c8.json` (`5b039f8e…`), because the
  schema has one row per (backend, campaign, sector, L) and no site key (`docs/PERFORMANCE.md`). The R18 regeneration
  test stays green.
- **Cluster reruns owed** (none run here): J-VAL-1 (`make test`, whole amdq node) and J-EXP-1 (Expanse debug) for
  F1-F4 and the Linux paths of F5/F9 in `unit_orchestration`; `sanitize.py --selftest` on GCC 11.4 (F4); the smoke
  result re-verified on the symmetry login node (F6); a scancelled lane-worker drill (F7, A-ORC-8a); J-DRL-8 (F8);
  a J-SMK-4-type run evaluated with `tools/claim_io.py` (F9); a cross-vendor refusal drill (F5); the final J-VAL-3
  assembly checks on the final commit. Both planned pilots pin the earlier tools and must be re-planned with fresh
  seeds on a new export.

## 2026-10-05: Stage 5 close-out: J-DES-5, the refined cost table, the pilot runbook, the decision step, H6, the user's numerics decision [A-DES-4/5, A-PIL-2, A-PERF-4/5, A-PKG-2, H6]

`numerical_change: false`. Documentation and evidence only: no file under `tools/`, `src/`, `tests/` or `slurm/`
changed. G5 is still not met (findings F1-F11 are owed; `benchmarks/symmetry_2026-10-c8/stage5/README.md`).

- **J-DES-5 (A-DES-5), symmetry job 570114** (sharedq, 2.32 core-hours): `design.py freeze --test-only` on the J-SWEEP-2
  sweep at 1e-3, 5e-4, 2.5e-4 and 1.35e-4, and `production.py plan --design` of each bundle in the job, never
  submitted; plan directories deleted. K = 1 at every target; 5.2-8.5 million tasks, 20,533-36,475 checkpoints,
  351-6,424 indices, plan wall 307-678 s, peak RSS 0.84-1.31 GiB; every cap holds
  (`benchmarks/symmetry_2026-10-c8/stage5/des5/`).
- **Finding F11 (new, `tools/design.py`, not fixed here):** a (sector, L) gets the replicates of its largest stratum
  multiplier, so at 1e-3 the free L8 primitives set r = 128 for the whole free L8 group: the 1e-3 bundle over-delivers
  (SE 32.6 against 46) at about 2.3× the cost of r taken from the costliest stratum. Tighter targets are within 1.10×
  of the continuous Neyman optimum.
- **`docs/PERFORMANCE.md`, "Stage 5: the refined cost table" (A-PERF-4):** projected core-hours per site at the four
  targets from J-DES-5's freezes, κ measured on each site, σ² still projected; the default path (symmetry 3,963 /
  5,856 / 23,423 / 76,623 core-hours; Expanse 3,748 / 5,487 / 21,949 / 72,125 SU at J-SMK-4's lane η_node 0.915), the
  continuous Neyman bound, the approved `dd+mp256` (×0.456–0.467), `dd` and `mp256` alone, and `exp1` and R7 as not
  approved. **A-PERF-5** per (sector, L) and site with the opt-in profiles over Stage 3. **F10:** speedups quoted per
  site (×1.390 Expanse GCC 13.3, ×1.157 symmetry GCC 11.4, kernel seconds; Stage 4b's ×1.646 is Expanse's sweep sample
  with loading). The open item `tools/calibration.json` (still C7(2)'s rows) is recorded there.
- **`docs/DESIGN.md` (A-DES-4):** the defaults table, F11 as a known issue, and "After the pilot": the report, the
  heavy-tail flags, the user's decisions with the decision table (target, numerics, sites and batches, tails), the
  freeze and the batches; how a `dd+mp256` production gets its bundle with the current tools (a profile pilot, or a
  tool change).
- **`docs/HPC.md`, "Pilot runbook" (A-PIL-2):** both sites' planned pilots, the re-plan with a fresh seed when a
  pinned tool changes (expected after the G5 fixes), the H11 window with C63d (announcement, the DECISIONS line
  re-splitting 16/40 against 6/14, the 5-minute start-latency probe first), the submit lines (Expanse one node with
  `--exclude=<NODE>`; symmetry `--lanes 3`), the checks during and after the run.
- **`docs/NUMERICS.md`, "User decision (2026-10-05)":** `dd+mp256` approved for production after the pilot, after a
  short J-FLAG gate of the exact `dd+mp256` build; `exp1` and R7 off; the smoke and the pilot exact; the approval
  reference text for `--approved-numerics-change`.
- **README** status (Stages 1-5 run, G5 not yet met, pilot planned); **evidence nits:** the Stage-5 README explains
  570111's FAILED state (its script gave `combine.py --output` a `.json` path, then verified that directory), and
  `admission/h7_ran_on.json` records the partition each admitted job ran on (570033 amddebugq, 570039 amdq).
- **H6 delivered to C63d:** `LRI_C8_shared/inventory/HANDOFF_design.json` (written by
  `benchmarks/symmetry_2026-10-c8/stage5/h6/write_handoff_design.py`: design.py and its runtime closure with sha256s,
  CLI, input interface, `--schema-prefix` rule, outputs, the tests covering a c8-d3 prefix, J-DES-5, known issues) and
  `NOTE_C62d_to_C63d_2026-10-05_H6.md`.
- **`designs/forbidden_seeds.json`:** J-DES-5's four seeds synced from symmetry's log into Expanse's log and the
  mirror; 78 seeds in each, equal sets.

## 2026-10-05: Stage 5 on symmetry: final J-VAL-1..4, J-SWEEP-2/3, L8 smoke, drills, design chain, throughput drill, pilot planned [A-RPL-1..7, A-IN-6(b), A-KER-4, A-PERF-3..5, A-SMK-1..4, A-ORC-8..13, A-DES-3, A-ASM-6/7, A-PIL-1]

`numerical_change: false`. No code changed: every job ran from the `git archive` export of 5d7586e
(`<SCRATCH>/c8d2/pkg/5d7586e9f1ab`) on the exact default path. Evidence:
`benchmarks/symmetry_2026-10-c8/stage5/` (README: verdicts, the job table, 338.82 core-hours in 57 job records).

- **Exact gates on symmetry (GCC 11.4):** `make c7ref` gives the plan's e696d7f3…/7e3c8c92…; J-VAL-2 replays the L=2
  graph and all 3,773 L3-L7 kernels exactly on both backends; J-VAL-3 with a fresh L=2 seed, G-BK8, thread identity,
  forced tiers, the R3a differential, merge scale and `assembly_checks --exact` pass; G-L8SELF is exact against the
  symmetry Stage-3 baseline built from `c8-stage3`; the sanitizer runs are clean.
- **`cost_models/gmp_symmetry_amd_c8.json` (new):** the symmetry cost model of the final default binary (J-SWEEP-2,
  job 570032 on <NODE>, EPYC 7543; 48,346 keys) with J-SWEEP-3's Intel Xeon Gold 6148 class factors (job 570035).
- **Real Slurm:** the L8 smoke (2 nodes, 8 x 8 lanes) and its restart twin (all 24 merged batches bitwise equal), the
  requeue and time-limit drills, the sharedq lane drills (lock, mixed mode, status window, merge-only resubmit,
  `--lanes 2` then `--lanes 1`), the recovery drill, the design chain through `combine.py --partial` and a two-batch
  final, and the throughput drill (busy 0.906, L8 blocks OpenMP >= 0.974, median task speed 0.95 of the sweep).
- **J-PIL-1 (symmetry):** `pilot1-20261005` planned (179.9 core-hours, 39 indices), not submitted; submit line in the
  Stage-5 README.
- **Findings for Stage 6 (not fixed here), F1-F10 in the Stage-5 README:** native rows differ between Intel and AMD
  CPUs (x87 `expl`/`logl`); recovering a completed index stops at the group's stale tables and at the result's
  no-clobber rule; a scancelled lane worker leaves its runtime directories; `verify_result.py` depends on the OpenBLAS
  kernels; `production.py run` logs no rchar (R07); the default binary is x1.16 (kernel seconds) faster than Stage 3
  on symmetry against x1.39 on Expanse; `test_lanes` (whole node), `test_numerics_flags` (NumPy 2), `vendored_isolated`
  (pytest missing from the symmetry venv and from `requirements.txt`; installed there) and `sanitize.py --selftest`
  (GCC <= 12 prints the assertion on stdout) fail on symmetry for reasons outside the numerics.
- **`designs/forbidden_seeds.json`:** the union of both seed logs (74 seeds), this run's 12 new seeds included.

## 2026-10-05: Stage 5 on Expanse: J-EXP-1..4, the GMP_PREFIX gates, J-SWEEP-2E, the Expanse pilot planned [A-EXP-3, A-PERF-5, J-PIL-1E]

`numerical_change: false`. No code changed: 07ff5c1 adds job scripts to 5d7586e. Evidence:
`benchmarks/expanse_2026-10-c8/stage5/exp/`.

- **`cost_models/gmp_expanse_amd_c8.json` (new):** the Expanse cost model of the final default binary (J-SWEEP-2E,
  job 54676908 on <NODE>; 48,346 keys). A first run on <NODE> showed that node 14% slow on L7/L8 work; Expanse
  pilot and production jobs exclude it.
- **A-PERF-5 per (sector, L)** for the default path (`docs/PERFORMANCE.md`, "Stage 5 on Expanse"): ×1.390 overall,
  L8 ×1.444 (free) and ×1.261 (power), in kernel seconds.
- **`GMP_PREFIX=zen2` cleared for production on Expanse:** the full J-VAL-2, G-BK8 and forced tiers on the zen2 worker
  `aa84cd45…` pass, with records equal to the default build's (`docs/NUMERICS.md`, "Builds").
- **J-EXP-1..4 (A-EXP-3).** The debug build is the final default build. `make test` found two test-portability
  defects, not fixed here: `tests/unit_orchestration.py` `test_lanes` fails on a node with more than 16 CPUs (its
  `C8_LANES=2` lanes exceed the test plan's 8 checkpoint tasks), and `tests/test_numerics_flags.py` `f2_profile`
  fails under NumPy 2 (`repr` of a NumPy float64; fix `repr(float(delta))`, checked in a copy). Every other test
  passes. The shared 2-element array with its merge, the debug lane worker and the mandatory compute lane job each
  completed a test campaign through merge and assembly.
- **J-PIL-1E:** the Expanse pilot planned (36 indices, 170.3 core-hours, about 205 SU on one node); nothing submitted.
- **`designs/forbidden_seeds.json`:** the union of both seed logs (68 seeds), the six new Expanse seeds included.

## 2026-10-05: Stage 5, the G4c verifier's fixes and the site preparation [A-FLAG-1, A-FLAG-6, D9; G4c follow-ups]

`numerical_change: false`: the default executables do not include the changed headers (A-RPL-8 is re-checked on
Expanse below), and a profile build without a parameter override preprocesses to the gate build's tokens.

- **D1 (A-FLAG-6), `tools/design.py`.** `design.py rates --rule one-step` chooses the rates from the pilot: the rule of
  `benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts/r7_spec.py` (per (sector, L), r = W_b²/W_a² of the Neyman
  variance × cost at .9 over .8; step up below 1 − band, step down above 1/(1 − band), keep otherwise or with fewer
  than `--min-graphs` graphs; `--step` 0.1, `--band` 0.10, `--min-graphs` 100, `--boot` 1000) is now
  `design.one_step_rule`. A pilot under a map and a step that leaves (0, 1] are refused. `--spec` stays the explicit
  alternative (exactly one of the two). The provisional bundle's `design_meta.json` records `rate_rule` (the rule,
  its parameters, the pilot's identity and every stratum's graphs, W, V, C, ratios, bootstrap interval and decision;
  for `--spec`, the file, its sha256 and content). Tests (`tests/test_pipeline.py`): every branch on a synthetic
  pilot against hand values; the command line on the fake pilot against an independent recomputation from the
  merged tables, with its refusals; **part 3**, a non-test plan of a fresh R7 bundle on a scratch package with
  minimal non-test inputs (two graphs per (sector, L), the fixture's L8 packs, no `test_fixture`): accepted with
  `--approved-numerics-change` and the cost model under the map, refused without the approval, with the default
  cost model (D15), without a cost model and without the map.
- **D2 (A-FLAG-1).** `-DC8_MP256_RATIO` and `-DC8_EXP1_RANGE` overrides make `--describe` (and the native JSON) say
  `"development":true` with `"overrides":[...]` (dd's overrides already needed `-DC8_DD_DEVELOPMENT`).
  `tools/build_record.py` records `parameter_overrides` (every `-D`/`-U` of a `C8_*` macro other than the build and
  diagnostic macros) and `"development"`; `production.py plan` refuses such a build record, recomputing the list
  from `compiler_options` for older records. Tests: `tests/test_numerics_flags.py` `overrides` (the headers
  preprocessed with and without overrides; without, token-identical to 5569c53's; `make -n` with `CPPFLAGS`
  overrides), `tests/unit_orchestration.py` `exe` (plan refuses mp256, exp1 and combination development builds via
  `--describe`, and override build records, old and new).
- **D3 (D9).** `tests/numerics_flags.py` registers its F2 campaign (base seed and the native and net seeds of all
  24 groups, fixed labels) in `--seeds-log` (default `$C8_SEEDS`) before F2 starts; it refuses a run without a log
  and seeds already logged under another source; a rerun on the same base adds nothing (`tests/test_numerics_flags.py`
  `f2_seeds`). `tools/seeds.py merge FROM... [--log]` makes a log the union of logs (never drops or reorders an
  entry; reads the first symmetry log's `"entries"` layout); `docs/HPC.md` states the two-log rule.
- **D5.** `docs/NUMERICS.md` (R4c): the host signed off exp1's probe gate restricted to the precision policy's range
  |f450| ≥ 1e-274·(1 + err); exp1 is inert under planned sampling (P(shifted) ≤ 1e-72) and not recommended.
- **Mac suites** (`make test-python`, Mac Python, `C8_ALLOW_NO_L8=1`): all pass
  (`benchmarks/expanse_2026-10-c8/stage5/g4cfix/mac/`).
- **Expanse check** (job 54676839, `shared` 16, 2.92 SU; `benchmarks/expanse_2026-10-c8/stage5/g4cfix/`): on 5ddf8ee
  the default executables are `99a51c1d…`/`1d2a2181…` (A-RPL-8) and the profile builds without overrides equal the
  gate export's byte for byte; the mp256, exp1 and dd override builds say `"development":true` and are refused by
  plan's checks; `design.py rates --rule one-step` on J-SWEEP-1 reproduces the Stage-4c map and r7_spec.py's record
  (1e-12); the F2 seed 820262401 and its 48 derived seeds are in the Expanse seed log (7 → 56 entries).
- **Sites.** symmetry `~/c8d2/env.sh` is the template's symmetry block (old `0122a133…` kept as
  `env.sh.bak-20261003`, new `e5fdb68c…`); the symmetry seed log is the union of both sites' logs (56 seeds) and so
  is `designs/forbidden_seeds.json`.
- **D6, the Expanse export pruning: surveyed, not executed.** 9 exports kept (the host's five, plus four whose
  baseline directory or executable a later job read), 30 listed for deletion (187,277 entries) with the check's work
  directory; the deletion was refused by the session's permission classifier and is left to the user
  (`benchmarks/expanse_2026-10-c8/README.md`, "Stage 5").

## 2026-10-05: Stage 4c integration on c8 and the J-FLAG gates [A-FLAG-1..5, A-FLAG-7, A-RPL-8, A-PERF-5 for the opt-in profiles]

`numerical_change: false` for the default path: A-RPL-8 holds on the integrated head (build 54673898, export
5569c535dcfd: `bin/c8d2_decimal` `99a51c1d…`, `bin/c8d2_gmp` `1d2a2181…`, the final default binary byte for byte;
preprocessed default program token-identical to b47b008's). Every opt-in profile is a numerics change (D1), off by
default; R4d (`mpconv`) was not implemented (host decision).

- **Merged** flag-dd, flag-mp256, flag-exp1 and flag-r7 (in that order; the entries below are theirs). Conflicts only
  in this file, `docs/NUMERICS.md`, `tests/test_numerics_flags.py` and the manifests.
- **Integration fixes** (5569c53). `src/numerics/numerics.hpp`: `nx::f1_checks` (`C8_NX_F1_CHECKS`) runs every
  profile's own `C8_NX_F1_CHECKS_<P>` of a build (exp1, mp256, then dd, whose checks re-evaluate the point; their
  state is cleared afterwards), so the combination checks all three (before, dd's unconditional macro replaced the
  others'); dd's forced-guard identity accepts mp256's tier as an MP tier. `tools/production.py plan` refuses an
  executable whose `--describe` marks a profile `"development":true` (dd's measurement variants), tested with the
  fake worker's new `C8_FAKE_DEVELOPMENT=1`. No worker executable changed: dd `51614820…`, mp256 `9e884b1b…`, exp1
  `0bf3f1a8…` as built by their developers; the combination `6bc26966…`.
- **J-FLAG at full scale** (Expanse, one exclusive node per run: baseline 54673899, dd 54673900, mp256 54673901,
  dd+mp256+exp1 54673902, exp1 54673904): every profile **passed** F1 (153,600 points, no violation, no profile-check
  violation), F2 (193,384 paired tasks; dd and the combination |dC8| + 3 SE_d = 4.2e-16, per-task max 5.6e-14; mp256
  and exp1 dC8 = 0 exactly, every task identical) and F5. F4 on the L8 sweep sample: dd ×1.389, mp256 ×1.372,
  exp1 ×1.007 (code layout; all-stub control ×1.005), dd+mp256+exp1 ×2.168.
- **A-FLAG-7 table** (`docs/NUMERICS.md`, "Stage 4c gate"): projected core-hours at 1e-3, 5e-4, 2.5e-4 and 1.35e-4 on
  the final default binary's test-only freezes (7,118 / 10,512 / 42,047 / 137,883): dd ×0.68–0.70, mp256 ×0.75–0.76,
  exp1 ×1 (layout only), dd+mp256+exp1 ×0.46–0.47, R7 ×0.82–0.88 (measured, A-FLAG-6). `docs/PERFORMANCE.md`,
  "Stage 4c": F4 and the per-(sector, L) speedups (A-PERF-5).
- **Tools.** `benchmarks/expanse_2026-10-c8/stage4c/gate/` (evidence, `scripts/aflag7_table.py`,
  `scripts/fetch_gate.sh`); `submit_s4c.sh gate` takes a second run in the same job (`C8_S4C_ARGS2`,
  `C8_S4C_NAME2`), used for the layout control. 66.1 SU; Stage 4c in all 205.1 SU of its 900.
- **Open for G4c** (the host's call): A-FLAG-6's statistical validation passed (R7 entry below), but two of its bullets
  stay open: `design.py rates` takes an explicit `--spec` (the choice rule is `dev_r7/scripts/r7_spec.py`), and a
  non-test plan accepting a fresh R7 bundle needs a non-test pilot under the map.

## 2026-10-05: Stage 4c R3b: the double-double profile `dd` (branch flag-dd) [A-FLAG-1..4, A-RPL-8; development evidence]

`numerical_change: false` for the default path (A-RPL-8 checked on four exports: `bin/c8d2_decimal` `99a51c1d…`,
`bin/c8d2_gmp` `1d2a2181…`). Opt-in only: `make gmp NUMERICS=dd` → `bin/c8d2_gmp_dd` (`51614820…` on Expanse).
Details: `docs/NUMERICS.md`, "R3b: the double-double tier".

- **Tier** (`src/numerics/dd.hpp`, `NX_FLAGS_dd = -mavx2 -mfma`). Double-word arithmetic with explicit fma; a dd
  exponential (k·ln2 reduction with a three-part ln 2, Taylor degree 11 on r/64, six expm1 doublings); the positive
  segment sums as a compensated sum in 4 lanes; guards |lx_j − shift/L| ≤ 300 and every product in [2^-900, 2^900]
  (else the exact binary128 tier, bit for bit); acceptance |val| ≥ 1e-20·err; a dd failure cascades to binary128 when
  |val| ≥ 1e-23·err and goes to MP below. Error analysis: |val − exact| ≤ 6.7e-28·err for every admitted point.
- **Routing measured** (host decision 2026-10-04): cascade ×1.388 against direct dd → MP ×1.094 on the L8 sweep sample
  (F4, one node, median of 3); the cascade is the default, the direct routing a development build only.
- **Checks.** F1 checks of the profile (routes, the range guard against a recomputation, the guards forced, the
  dd-ratio decades against binary128's verdict, dd against binary128); `tests/dd_accuracy.cpp` (Expanse, 120 digits);
  `tests/test_dd_profile.py` (Mac, mpmath; in `make test-python`); `tests/test_numerics_flags.py` now takes each
  profile's `NX_FLAGS_<p>` from the Makefile and accepts the implemented dd header. Development jobs and evidence:
  `benchmarks/expanse_2026-10-c8/stage4c/dev_dd/` (F1 on the full A-RPL-5 set passed as a development run; the
  `dd_never` variant reproduces the exact path at every point; 24.0 SU).

## 2026-10-05: Stage 4c R4b `mp256`: staged gmp_float<77> MP tier (opt-in, branch flag-mp256) [A-FLAG-1/3/5, A-RPL-8]

`numerical_change: false` for the default path (A-RPL-8: `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp`
`1d2a2181…` unchanged on Expanse). The opt-in profile `mp256` is a numerics change (D1): only `make gmp NUMERICS=mp256`
builds it, and only `plan --numerics mp256 --approved-numerics-change` uses it.

- **`src/numerics/mp256.hpp`.** The MP tier first evaluates `calculate_shared<MP77,true>` (gmp_float<77>, 320-bit
  significands, the binary128 tier's error estimate), accepts when |v| ≥ `C8_MP256_RATIO` (1e-63) × err, and
  otherwise escalates to the unchanged 350-digit tier. `--describe` reports its parameters; the process reports its
  accepted and escalated counts on stderr; `C8_NX_F1_CHECKS` checks every MP-promoted point of F1 at 77 and 350
  digits.
- **Tests.** `tests/test_numerics_flags.py` checks the implementation in place of the stub.
- **Development evidence** (`benchmarks/expanse_2026-10-c8/stage4c/dev_mp256/`): F1 at full scale passes with every
  value identical to the exact path's (escalations 7.4e-4); heavy L8 blocks ×1.403/×1.516, MP tier ×2.0/×2.1,
  escalations 1.7e-3/2.3e-3, rows identical; development F2 dC8 = 0 exactly.

## 2026-10-05: Stage 4c R7 (opt-in rate maps): A-FLAG-6 test gaps closed, the statistical validation on Expanse [A-FLAG-6]

`numerical_change: false` for the default path (no kernel or default-plan change; R7 stays opt-in behind `plan
--rates` / `sweep.py --rates` with `--approved-numerics-change`).

- **`design.py rates` on a pilot planned with older tools.** It refused a pilot whose pinned tools changed after
  planning (J-SWEEP-1 was planned with the Stage-3 tools), although `freeze` and `report` accept such a pilot and
  record the change. It now accepts it the same way and records `accepted_tool_changes` (and the pilot) in the
  provisional bundle's `design_meta.json`. The map itself depends only on the inputs manifest, the inventory and the
  spec.
- **Tests (`tests/test_pipeline.py`, A-FLAG-6 bullets not covered before):** the source bundle is byte-unchanged by
  `design.py rates`; per-graph spec entries; a spec giving one graph equal a and b rates is refused before anything is
  created; the tool-change case above; the sweep under the map (`sweep.py --rates`, its labelled allocation) feeds a
  fresh freeze that equals the independent recomputation from the sweep and is not the default sweep's allocation;
  `freeze --rates-bundle` of another map is refused for both measurements made under the first.
- **Validation (Expanse, export ebf01f62e833; A-RPL-8 holds; 54.3 SU):** `benchmarks/expanse_2026-10-c8/stage4c/dev_r7/`.
  - **Map.** J-SWEEP-1 stands in for the pilot (not a design pilot). A one-step rule (`dev_r7/scripts/r7_spec.py`)
    gives the provisional map `98a215a8…`: free L8 and power L6–L8 go to a .9 / b 1, every other stratum stays at
    .8 / .9.
  - **Measurement.** The sweep under the map and a fresh exact sweep (all graphs, 2 × 512, the same node), plus a
    32 × 512 complement (`plan --pilot --rates` and its exact twin).
  - **Agreement.** All per-(sector, L) contributions and the total agree within 3σ, unpaired: largest |z| 2.06 in the
    sweeps and 1.59 in the complement; total z −0.93 (linear) and −0.66 (nonlinear C8).
  - **Variance × cost.** Down by about 16%: Neyman ×0.842 [0.810, 0.874]; test-only freezes at the four targets with
    one η_node ×0.82–0.88.
  - **R14/R19 on real data.** Fresh freeze (`--rates-bundle`), the provisional bundle refused by `plan --design`, the
    fresh bundle accepted by a test-only plan under the map and refused without `--rates`.
  - **Caveat.** A freeze's η_node from accounting includes the sweep's plan step: Lustre contention made the map
    sweep's plan step about 11 minutes longer. `plan --rates` itself is as fast as the default plan.

## 2026-10-05: Stage 4c framework: opt-in numerics profiles, hooks, campaign plumbing and the F-gate harness [A-FLAG-1..3, A-RPL-8]

`numerical_change: false` for the default path: the default executables, commands and plans are unchanged. The three
profiles exist as **stubs** (no numerics change) so that R3b `dd`, R4b `mp256` and R4c `exp1` can be developed in
parallel; R4d `mpconv` is not implemented (host decision 2026-10-04). Details: `docs/NUMERICS.md`, "Opt-in numerics
profiles".

- **Builds (A-FLAG-1).** `make gmp NUMERICS=<p>[,<p>...]` builds only `bin/c8d2_gmp_<name>` (canonical order `dd`,
  `mp256`, `exp1`, joined by `+`; the combination is `bin/c8d2_gmp_dd+mp256+exp1`) with `-DC8_NUMERICS
  -DC8_NUMERICS_<P>` and the per-profile `NX_FLAGS_<p>`; unknown names, `mpconv`, `exact` mixed in, repeats and every
  goal but `gmp` are refused. Default commands are word for word the delivered ones. The build record adds
  `numerics_sources` (the profile macros and the sha256 of `src/numerics/*.hpp`).
- **Hooks.** `src/kernel.hpp` gains `C8_NX_SHARED_BEGIN(T)`, `C8_NX_XS_Q(e)`, `C8_NX_XS_MP(e)`, `C8_NX_DESCRIBE(os)`
  and, in `evaluate()`, `nx::promote()` for profile builds; `src/numerics/numerics.hpp` (included at two stages only
  under `C8_NUMERICS`) defines the tier chain `nx::mp_tier_exact` → `nx::mp256::tier` → `nx::mp_tier` →
  `nx::quad_tier` → `nx::dd::tier` → `nx::promote`, the tier codes for F3, the profile name and the
  `"numerics_params"` of `--describe`. Without `C8_NUMERICS` every hook expands to the exact path's own tokens.
- **Plumbing (A-FLAG-2).** `common.numerics_name()` (the Makefile's rule); `plan --numerics` takes the canonical name
  only and a non-blank `--approved-numerics-change`; `status` prints the profile, the rates identity and the approval
  (also in `--json`). Tests: `unit_orchestration.py` (`exe`: a fake profile campaign planned, run, refused with a
  foreign-numerics checkpoint, merged and assembled).
- **F-gates (A-FLAG-3).** `tests/numerics_flags.py` with `tests/numerics_f1.cpp`: F1 (450-digit references on the
  A-RPL-5 point set, reusable baseline), F2 (paired mini-campaign over L3–L8, dC8 through the vendored Jacobian,
  doubling of replicates, projection), F3, F4 (interleaved speed on the L8 sweep sample), F5 (thread identity, new
  `tests/thread_identity.py --executable`); `--self-test`, strict identity for all-stub profiles, development labels.
  Mac tests: `tests/test_numerics_flags.py` (in `make test-python`); the fake worker reports the profile of its file
  name and can inject a relative change (`C8_FAKE_PROFILE_DELTA`).
- **Job scripts** (`benchmarks/expanse_2026-10-c8/stage4c/scripts/`): `submit_s4c.sh` (admission, per-agent share,
  `precheck`, `build`, `selftest`, `dev`, `baseline`, `gate`), `s4c_precheck.slurm`, `s4c_build.slurm` with
  `s4c_identity.py` (A-RPL-8, preprocessed-program identity, stub identity), `s4c_flags_shared.slurm`,
  `s4c_flags_node.slurm`. Commands for the developers and the gate agent: `benchmarks/expanse_2026-10-c8/stage4c/README.md`.
- **Expanse evidence** (`benchmarks/expanse_2026-10-c8/stage4c/framework/`; 3.19 SU in six `shared` jobs).
  - **A-RPL-8 passed** on the exports of 9870a68 (54672480) and 241baca (54672538): `bin/c8d2_decimal` `99a51c1d…`
    and `bin/c8d2_gmp` `1d2a2181…`, byte-identical to the final default binary; the preprocessed default program is
    token-identical to b47b008's. Two working-tree pre-checks (54672436, 54672441) showed the same before the commit.
  - **Stub identity:** `bin/c8d2_gmp_{dd,mp256,exp1,dd+mp256+exp1}` write `bin/c8d2_gmp`'s rows exactly.
  - **Self-test** (54672484, 54672539; development scales): `--self-test` and the dd stub pass F1 (7,680 points
    identical), F2 (dC8 = 0 exactly, 5,496 tasks with zero difference), F3 (no change), F4 (rows identical) and F5.
- 241baca: the harness's float comparisons no longer raise a Python 3.11 `SyntaxWarning`; `test_numerics_flags.py`
  compiles the harness with that warning as an error.

## 2026-10-04: Stage 4b G4b: final J-VAL-2 and J-VAL-3 on the final default binary [G4b; A-RPL-1..7, A-IN-6(b), A-ORC-6, A-ASM-4]

`numerical_change: false`. No source change: `src/` stays d46e736's (+R5 +R3a), and no physical value is produced.
The write-up is in `docs/PERFORMANCE.md`, "Stage 4b: default-path optimizations", and `docs/NUMERICS.md`. The evidence
is in `benchmarks/expanse_2026-10-c8/stage4b/final/`.

- **Job scripts** (b47b008): `final_build.slurm`, `g4b_val2.slurm`, `g4b_val3.slurm`, the Mac driver
  `submit_final.sh`, and `summarize_final.py`, which writes `final_summary.json`.
- **Build (Expanse 54672150).** From the `git archive` export of b47b008 (6,363 files equal). Every executable is
  byte-identical to e7ef98d's build: `bin/c8d2_decimal` `99a51c1d…`, `bin/c8d2_gmp` `1d2a2181…`, and `make c7ref`
  `4537dcfd…`/`6c829386…`. The L8 packs were re-hashed against the manifest before they were hard-linked.
- **J-VAL-2 (54672151), `make test-full`: passed.**
  - G-REF, G-C7 and G-JET are exact on the L=2 graph and all 3,773 L3–L7 kernels, both backends, mp > 0 rows included
    (39,048 G-C7 rows per backend).
  - Chunks and layouts agree, and the point checks L3–L8 reach 2.1e-353 and 1.8e-302 against 1e-280.
  - `check_inputs`, `workflow` and `staging` passed.
- **J-VAL-3 (54672152): passed.**
  - The L=2 control used Stage 3's registered seed; its largest pull is 1.22.
  - Thread identity holds at 1, 8, 16, 64 threads and 8 × 8 lanes.
  - G-BK8 and G-L8SELF are exact, the latter against the Stage-3 baseline on both backends.
  - Forced tiers (A-RPL-5) and the R3a differential (2^32 pairs per operation, 0 mismatches) passed.
  - Merge scale passed at 1,249,792 rows, and `assembly_checks --exact` passed 37/37.
- **Against Stage 3.** With run-specific fields removed, the records of `validate --full`, the point checks, the L=2
  control, G-BK8, thread identity, forced tiers and G-L8SELF equal those of the Stage-3 baseline (jobs 54637263 and
  54637264).
- **Docs.**
  - PERFORMANCE has a new Stage-4b summary: per optimization the change, gates, speedup and decision; R4e no-go; R6
    not attempted (bound about 0.8%); R3c not attempted (IPC 3.04); and the speedup per (sector, L) where measured,
    free L8 ×1.721 and power L8 ×1.473, which starts A-PERF-5.
  - NUMERICS records the final hashes and the G4b gates.
  - The Expanse README has a G4b section.
  - `LRI_C8_shared/PERF_NOTES.md` has a [C62d] entry with the R3a patch hashes (H5).
- **Cost.** 39.77 SU on Expanse. Stage 4b in all used 375.6 SU of its 1,300.

## 2026-10-04: Stage 4b integration on c8: J-OPT gates and the A-PERF-2 decisions [A-PERF-2; A-RPL-1/2/3/6/7 per step]

`numerical_change: false`: every cumulative step is exact against the Stage-3 baseline. No physical value. The numbers
are in `docs/PERFORMANCE.md`, "Stage 4b integration", and the evidence is in
`benchmarks/expanse_2026-10-c8/stage4b/integration/`.

- **Merges, in plan order.**
  - 138d486 `opt-r5` (R5a, R5b).
  - d46e736 `opt-r3a`.
  - bc0bedc `opt-r4a`.
  - 7b9aa9c `opt-r4f`.
  - In each merge, CHANGELOG, PERFORMANCE, NUMERICS and the Expanse README conflicts kept both sides.
  - `Makefile` kept R3a's `quadfast.hpp` dependency and R4f's `C8B_GMP_PREFIX`.
  - `DELIVERY_MANIFEST.json` and `SHA256SUMS` were regenerated.
- **Integration fix.** R3a's GMP-linked `bin/c8d2_quad_ranges` now takes the `GMP_PREFIX` words, like the other
  GMP-linked commands. Without the knob it is unchanged, word for word. `tests/test_gmp_prefix.py` now covers both
  quaddiff tools.
- **Gates (Expanse), all passed.**
  - Builds and `validate.py` default parts: 54669703–06.
  - G-L8SELF and thread identity per step: 54669707 (+R5, +R3a) and 54669708 (+R4a, and the zen2 builds B2f and B4,
    which also ran the replay subset).
  - The R4f merge's default build is byte-identical to +R4a's.
- **Speed (A-PERF-2), job 54669709.** One node, L8 sweep sample, 16 × 8 lanes, median of 3, interleaved.
  - R5a ×1.154: kept.
  - R5b: the defaults are P4's best shapes, so it is kept.
  - R3a ×1.426: kept.
  - R4a ×1.0093: **reverted** (ea59445, code only).
  - R4f ×1.052 over the kept default: kept as the opt-in `GMP_PREFIX` knob.
  - IPC of the R3a binary is 3.04, so R3c is not attempted.
- **Total.** The default path is ×1.646 faster than Stage 3 on the sample (free ×1.72, power ×1.47). With the zen2 GMP
  it is ×1.731.
- **Final candidate e7ef98d** (jobs 54672108 and 54672109).
  - `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…` are byte-identical to +R3a's, and the zen2 worker
    `aa84cd45…` to B2f.
  - `validate.py` default parts, G-L8SELF, thread identity and the quad differential (2^32 pairs per operation, 0
    mismatches) all passed. The zen2 worker passed G-L8SELF, thread identity and the replay subset.
  - The full J-VAL-2/3 is next.
- **Cost.** 85.8 SU on Expanse.

## 2026-10-04: Stage 4b development, R5a and R5b (branch opt-r5) [A-PERF-2 pending; A-RPL-6/7 development runs]

**Integration outcome:** kept (R5a ×1.154 on the L8 sweep sample, job 54669709; R5b defaults equal P4's best shapes).

`numerical_change: false`: the default path stays bit-for-bit identical (G-L8SELF exact on the full L8 sample, both
backends; thread identity; all 4,018 P4 rows identical). The worker binaries change: `c8d2_decimal` `b36bf334…` and
`c8d2_gmp` `f4ad369c…` on Expanse (Spack GCC 13.3), so the Stage-3 hashes no longer apply to bin/. No physical value.
Numbers and evidence: `docs/PERFORMANCE.md`, "Stage 4b development: R5a and R5b", and
`benchmarks/expanse_2026-10-c8/stage4b/dev_r5/`.

**R5a, parallel graph loading** (`src/c8d2_integrate.cpp`).
- The block's graphs load in an OpenMP `parallel for schedule(dynamic,1)` over the ascending graph ids, into a
  pre-sized vector, so the lane's pinned threads first-touch them.
- Each slot keeps its own error, and the lowest id's error is thrown: the error the serial loop threw first. `loaded`
  maps each id to its slot, and nothing else changed.
- Expanse: the load share of node time at 16x8 fell from 1.349% to 0.203% (P4 workload, one run each). Throughput
  rose by 1.7%, about 1.4% net of a page-cache effect on staging; this is below A-PERF-2's 3% bar, and the J-OPT gate
  decides. Peak RSS per lane rose by 4%.

**R5b, scheduling defaults** (`tools/lanes.py`, `tools/sweep.py`).
- With `C8_LANES` unset, AMD NUMA nodes are split into lanes of at most the plan's `--threads` cores. This gives the
  P4-best shapes 8 × 8 on symmetry and 16 × 8 on Expanse compute (previously 8 × 16 there).
- Explicit `numa`, `socket` and `n`, the Intel default and drill mode are unchanged.
- `worker_lanes()` holds the worker's lane decision, and the worker log names the shape.
- The sweep's default process slots use the same rule at its `--threads`.
- Plan defaults are unchanged and now tested: `--threads 8`, `--checkpoint-tasks` 256, 60 s tasks bounded by 120 s,
  and 1.5 h indices.
- `tests/unit_orchestration.py` has a new test `p4_defaults` (fake sysfs trees for symmetry, Expanse, Intel and an
  uneven node; the checkpoint cap; width validation; the sweep's slots).
- Docs: `docs/HPC.md`, `slurm/lane_worker.sh`, `slurm/sweep.sh`.

**Evidence** (Expanse, 37.67 SU in total):
- 54666182 (`shared`): the build and the validation;
- 54666183 (`compute`): the bench, G-L8SELF and thread identity;
- 54666372 (`compute`): the lane-shape probe on the real topology (16 × 8 by default at `--threads 8`, NUMA-aligned).

## 2026-10-04: Stage 4b R3a, inline binary128 add/sub/mul (branch `opt-r3a`, development) [A-PERF-2 evidence; J-OPT-R3a]

**Integration outcome:** kept (×1.426 on the L8 sweep sample, job 54669709; IPC 3.04, so R3c is not attempted).

Default path, bit for bit: `numerical_change: false`. No physical value.

**Code.**
- `src/quadfast.hpp` (new): correctly rounded binary128 addition, subtraction and multiplication on 64-bit words. They
  equal libgcc's `__addtf3`/`__subtf3`/`__multf3` in round-to-nearest-even for normal operands with a normal, finite
  result. Every other case is computed by libgcc itself, through out-of-line calls on the same operands.
- `src/kernel.hpp`: `calculate_shared<Q>` uses them for every binary128 `+`, `-` and `*`, in the same order, through a
  per-statement `if constexpr`. The MP instantiations keep their original statements, and division, conversions,
  comparisons and `expq` are unchanged.
- `Makefile`: `src/quadfast.hpp` joins the worker, inspector and probe dependencies. `make quaddiff` builds
  `bin/c8d2_quad_differential` and `bin/c8d2_quad_ranges` with the worker's flags.
- `tests/quad_differential.{cpp,py}` and `tests/quad_ranges.cpp`: the kernel's operand ranges, at least 10^9 random
  pairs per operation (2^32 by default) over four streams, the edge lists, an injection self-test and an ASan+UBSan run.
  Zero mismatches are required.

**Results (Expanse, final version add273b; `docs/PERFORMANCE.md`, "Stage 4b R3a").**
- Differential: 4,294,967,296 random pairs per operation and 901,761 / 901,761 / 1,350,672 edge pairs, with 0
  mismatches. The injection is detected and the sanitizer run is clean.
- G-L8SELF is exact on both backends (2,000 L8 kernels, 2 × 512 points), and the replay subset passes.
- heavy_free_L8 and heavy_power_L8 rows are identical to the Stage-3 baseline's.
- Speed-up, median of 3 at 64 pinned threads: ×1.442 (heavy free L8) and ×1.331 (heavy power L8). The binary128 tier
  is ×2.16–2.20 faster per call.
- IPC 3.08 (baseline 2.71), so R3c is not attempted.
- MP and long-double source statements are unchanged. Their machine code differs only where GCC's unit-wide inlining
  budget moves; that is documented, and the exact gates cover their numerics.
- A first version (908bd9d: ×1.220 / ×1.184, equally exact) is superseded.

**Evidence.**
- `benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/`: job scripts, admission records, `round1_908bd9d/`,
  `round2_add273b/`, `dev/`, `logs/` and `r3a_summary.json`.
- `benchmarks/expanse_2026-10-c8/setup/export_check_{908bd9de0265,add273b9ecc7}.json`.
- Cost: 94.5 SU in 16 jobs.

## 2026-10-04: Stage 4b R4a, the MP tier without temporaries (branch opt-r4a; development, for the gate) [A-PERF-2, A-RPL-7]

**Integration outcome: reverted** (ea59445, code only). A-PERF-2 measured ×1.0093 on the L8 sweep sample (job 54669709), below
the 3% bar. It was exact in every gate.

Default-path change, exact. `numerical_change: false`. No physical value. The evidence is in
`benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/README.md`.

**Code.** In the gmp build, `calculate_shared<MP,false>` and `<MP,true>` (`src/kernel.hpp`, under `#ifdef C8_USE_GMP`)
forward to `calculate_shared_gmp`.
- The temporaries are per-thread and preallocated.
- The in-place mpf calls are the Boost 1.77 expression templates' value-producing calls, one for one and in order.
- Only lifetime calls and exact same-precision copies are gone: init2/clear of temporaries, and `T v=sums[parent]`,
  `sums[j+1]=v`, `numerator[j]=n`, `abs_numerator[j]=ab` and `xs[j]=x[j]` at shift 0. The copy elision is the
  host-approved deviation.
- The MP exponentials and the decimal backend are unchanged. The decimal worker is byte-identical to Stage 3
  (`3dbd51bb…`).

**Exactness.** All on Expanse:
- An LD_PRELOAD mpf tracer shows the same value-producing and query calls, with identical operands and results. This
  holds on one MP point (72,999 records) and in digest traces on L7/L8 heavy graphs, release and ratio-histogram builds.
- A differential test against the verbatim pre-R4a body is bitwise on 16,384 points, 4,095 of them with shift ≠ 0.
- G-L8SELF is exact on both backends.
- The replay subset (G-REF, G-C7, G-JET) is exact, mp > 0 rows included.
- The heavy L8 blocks have identical rows in all 12 timing runs.

**Speed: below the 3% bar.**
- MP tier: ×1.018 (micro-benchmark).
- Heavy L8 blocks at 64 threads, socket-paired: +0.6% (free) and +1.2% (power).
- The median of 3 is +2.4% and +2.8%, but it carries a 2% socket bias.
- About +0.55% is expected over the L8 population.
- A-PERF-2 therefore asks for the revert, and the gate decides.
- A prefetch variant gave ×1.010 on the MP tier and was not kept.

**Cost and jobs.** Expanse jobs 54666232, 54666291 and 54666315: 41.3 SU.

## 2026-10-04: Stage 4b R4f (development probe): GMP 6.2.1 built for the node, behind `GMP_PREFIX` [host deviation R4f; A-PERF-2]

**Integration outcome: kept as the opt-in knob.** A-PERF-2 measured ×1.052 over the kept default on the L8 sweep sample
(job 54669709). It was exact in G-L8SELF, thread identity and the replay subset (54669708).

Branch `opt-r4f` (worktree `LRI_C8_D2_HPC_wt_r4f`). Opt-in only: without `GMP_PREFIX` every build command and every
binary is the Stage-3 one (`numerical_change: false`). No physical value.

**Code.**
- `Makefile`: `GMP_PREFIX=<absolute prefix>` builds the GMP-linked executables (`bin/c8d2_gmp`, the gmp diagnostic and
  sanitizer builds, the probe) against that GMP: `-I<prefix>/include` first among the compile words, and
  `-L<prefix>/lib -Wl,-rpath,<prefix>/lib -Wl,--disable-new-dtags` first among the link words. The DT_RPATH is
  searched before `LD_LIBRARY_PATH`, so `env_expanse.sh`'s Spack GMP cannot replace the library at run time.
  - Refused: a relative path, spaces, or a prefix without `include/gmp.h` or `lib/libgmp.*`.
  - `bin/c8d2_decimal`, `bin/c8d2_inspect` and `make c7ref` ignore the knob.
- `tools/build_record.py`: every gmp build records `GMP_PREFIX`, `gmp_header` (`__GMP_CC`, `__GMP_CFLAGS`) and
  `gmp_library`: the libgmp that `ldd` resolves in the build environment, with realpath, sha256 and `fat`, and the
  executable's RPATH/RUNPATH.
- `tests/test_gmp_prefix.py` (in `make test-python`, 7 tests):
  - the dry-run commands, unchanged without the knob and with it, and the refusals;
  - the build-record parsers;
  - the R4f job scripts, and dry runs of the R4f bench driver with the fake worker and fake perf.

**Probe on Expanse** (`benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/`; `docs/PERFORMANCE.md`, "Stage 4b R4f").
- **What the package links.** Spack's GMP 6.2.1 is a generic x86-64 build: Spack's forced autoreconf replaces GMP's
  `config.guess`. It runs the k8 kernels (`mpn_mul_basecase` without `mulx`/`adx`) and is not fat. Ubuntu's
  `libgmp10` on symmetry is `--disable-fat` on amd64 as well (from its `debian/rules`).
- **The two builds.** GMP 6.2.1 from gmplib.org (sha256 = Spack's pin; good release signature), built `--enable-fat`
  and `--host=zen2-pc-linux-gnu`. `make check` passes 197/197 for each.
- **Exactness, both variants.** The default build is byte-identical to Stage 3. The replay subset (G-REF, G-C7,
  G-JET) and G-L8SELF are exact. All 9 runs of each heavy L8 block (2.5 million MP points) give one rows digest, which
  equals Stage 4a's.
- **Speed** (medians of 3 on one node, heavy_free_L8 / heavy_power_L8 at 64 threads):
  - host ×1.0375 / ×1.0423;
  - fat ×1.0247 / ×1.0248.
- **Where the gain comes from.** The MP tier gets ×1.10–1.13 per call (host) and ×1.068 (fat), mostly from
  `mpn_mul_basecase`. The first pass and binary128 are unchanged.
- **Layout control (job 54668998).** The Spack GMP behind an rpath of the zen2 prefix's length gives a worker 4 bytes
  away from the host worker's. Its MP tier and its perf shares equal the baseline's (within 0.3%), so the gain is the
  library's, not the 0x30-byte code shift's.
- **Projection.** ×1.023–1.037 (host) and ×1.016–1.020 (fat) on the whole L8 population.
- **Cost.** 76.5 SU on Expanse:
  - jobs 54666319–24: 66.0;
  - the cancelled first submission 54666273–82: 0.8;
  - the control 54668998: 9.7.

## 2026-10-04: Stage 4a profiles on the Stage-3 baseline, and their write-up [A-PERF-1; J-PROF-1..4, J-GEN-3]

Profiling, evidence and documentation only. Nothing changed in `src/`, the default numerics or the worker binaries
(`numerical_change: false`). No physical value.

**P1 parser fix (651c56f; delivery manifest 7a8aad7).** RHEL 8's perf 4.18 appends `IPC [IPC Coverage]` columns to the
symbol reports, and the first parser did not strip them. The job's own `p1.json` therefore classified every symbol as
"other".
- `tools/benchkit.py` now drops the IPC tail. It classifies symbols without their version, `@plt` and `__GI_`
  decorations (a PLT stub counts with its target), and adds fenv, PLT-stub and per-DSO binary128 tallies.
- `tools/perf_profile.py p1-reparse --input P1DIR` rebuilds the summaries offline from the saved report texts into
  `p1_reparsed.json` and never overwrites `p1.json`.
- `tests/test_profiling.py` covers the IPC layout, a captured Expanse excerpt and the reparse: 15/15 pass.

**Profiles run (site deviation U1).**
- On Expanse, from the export of c176881:
  - build 54661715, in which the Stage-3 binaries `5c5328af…` and `3dbd51bb…` and both diagnostic builds came out
    byte-identical;
  - P1 54661716, P2 54661717, P3 54661718 and P4 54661719;
  - a half-node P4, 54661771, with the symmetry shapes on socket 0.
- On symmetry: P4 569788 on amddebugq <NODE>, from the export of 7a8aad7, with the worker built there by GCC 11.4.
- Cost: 178.8 SU on Expanse (the session's Expanse total is now 310.0 SU) and 26.1 core-hours on symmetry.

**J-GEN-3 (A-INV-4 on Intel), symmetry debugq 569770.** The L7+L8 inventory build on a Xeon Gold 6148 with GCC 11.4
gives a `MEMBERS.sha256` byte-identical to the published `inventory8_d2`: 24,839/24,839 members, and both builder
inventories identical. 2.29 CPU-h.

**Evidence committed.**
- Expanse: `benchmarks/expanse_2026-10-c8/stage4a/` (one directory per job, `logs/`, `admission/`,
  `stage4a_runner_summary.json`) and `setup/export_check_c17688158e2b.json`.
- symmetry: `benchmarks/symmetry_2026-10-c8/` (`jgen3/`, `setup/export_check_7a8aad783c31.json`, `stage4a/`).
- perf.data and the staged graphs stayed on node-local scratch, and no `raw_evidence.tgz` was needed (about 1.5 MB in
  all).

**Write-up.**
- `benchmarks/expanse_2026-10-c8/stage4a/writeup/derive_stage4a.py` (standard library) recomputes every headline
  number from the raw evidence, with its own perf-report parser and categories, into `stage4a_derived.json`. The output
  is the same under Python 3.9 and 3.10, and it agrees with the runners' summaries.
- `docs/PERFORMANCE.md` has a new section, "Stage 4a: profiles on the Stage-3 baseline (2026-10-04)". It covers:
  - the tier split, measured on the heavy blocks, with a population model from J-SWEEP-1;
  - the distribution of µs per point (P5);
  - time per function (P1);
  - IPC and the lock-step probe (P2);
  - the margins at the 1e-9 and 1e-23 tests (P3);
  - the lane shapes on Expanse (full and half node) and on symmetry (P4), with memory per lane and the load + staging
    share;
  - the Stage-4b/4c decision table.
- The tools section gains `p1-reparse`.

**Headline numbers.**
- **Tier split, heavy L8 blocks.** First pass / binary128 / MP: free 5.3 / 56.9 / 34.7% and power 4.0 / 48.0 / 42.1%.
  The model for all of L8 gives 7.8 / 61.5 / 30.7% (campaign a).
- **Symbols.** `__addtf3` is 33–53% of samples, and `__divtf3` 0.5–1.1% (1.0–2.2% of the binary128 tier).
  `calculate_reference<long double>` and the shift loop are 0%.
- **IPC.** 1.01 / 1.04 for the first pass. About 2.8 for the promoted tiers (the heavy block runs at 2.71).
- **Probe.** 1.098 with 2 points: 1.03 promotion-free, 1.17 heavy.
- **Lanes.** The best shapes are symmetry 8x8 (63.42 cost-model s per node-second) and Expanse 16x8 (113.45).
- **Load + staging.** 1.22% and 1.42% at those shapes.

**Decisions** (in `docs/PERFORMANCE.md`):
- R5a: go, low priority; the gate decides.
- R5b: `--threads 8`, `C8_LANES=numa` on symmetry and `C8_LANES=16` on Expanse.
- R3a: add and mul; div excluded.
- R3c: no-go on the baseline.
- R4a: small unless copies are elided.
- R6: go by the IPC rule, but a revert is likely.
- R4e: no-go.
- `C8_DD_RATIO` 1e-20 and `C8_MP256_RATIO` 1e-63.
- No binary pack.
- The per-job graph cache and the persistent worker stay not planned.

**Shared folder (outside git).**
- `LRI_C8_shared/inventory/PACK_FORMAT_PROPOSAL.md` (H4): not needed, at 1.22–1.48% against the 2% trigger. sha256
  `7343fb6a…`, md5 `6a030338189175bdbcde065df39c8781`.
- `LRI_C8_shared/PERF_NOTES.md`: an entry dated 2026-10-04 and tagged C62d.

**READMEs.**
- `benchmarks/expanse_2026-10-c8/README.md` has the Stage-4a section, the allocation total (310.0 SU; about 340
  core-hours across sites) and a corrected `env_expanse.sh` hash history. `b3f044da…` is the file through Stage 3 part
  A, and `6f85cb50…` the file since ef5a2b6.
- `benchmarks/symmetry_2026-10-c8/README.md` is new: the environment, the exports, the J-GEN-3 and P4 rows with their
  core-hours, and a note that `~/c8d2/env.sh` there still lacks `C8_SITE` and `C8_SEEDS`.

## 2026-10-04: Stage 4a profiling tools (P1–P4) [A-PERF-1 tooling; J-PROF-1..4]

Profiling only: no change to `src/`, to the default numerics or to the default worker binaries (the Makefile's worker
commands are unchanged; a new `probes` target builds a separate micro-benchmark). No physical value.
- `tools/prepare_benchmarks.py --order 8` writes the frozen workloads `benchmarks/fixtures8/` (committed: task files,
  Sobol nets, manifest with every sha256, the cost-model pin and the selection rules; seed 2026100408): heavy L7 blocks
  of 1,024 tasks and heavy L8 blocks of 256 tasks (P1), promotion-free free-sector L7/L8 blocks (P2), uniform-draw
  L7/L8 blocks (P3) and the P4 workload `p4_L8` (~330 s of ideal node time on 128 cores; `--fraction 0.5` for 64
  cores). `--check` rebuilds and compares; `--stage-check DIR` stages every fixture graph from the packs. The order-7
  (C7(2)) path is unchanged except that its `prepare_inputs.prepare` import moved into the function, because C8(2)'s
  prepare_inputs has no `prepare()` and the module-level import made the whole module unimportable.
- `tools/benchkit.py`: fixtures and staging, NUMA-aligned CPU sets for N×T lane shapes, LPT shares and blocks, run
  identity, and the parsers (perf report/stat/annotate, addr2line, ltrace -c, numa_maps, numastat, ratio histograms).
- `tools/perf_profile.py p1|p2|p3`: P1 (perf record/report shares, top 40, tier timers on the other socket, source
  lines through a code-identical `-g` twin; fallback tier timers + ltrace), P2 (perf stat IPC on promotion-free blocks)
  and P3 (ratio histograms per (sector, L, rate)).
- `tools/benchmark.py --lane-shapes` (P4) and `--interleave-probe` (P2 fallback); the C7(2) matched-benchmark mode is
  unchanged. `benchmarks/probes/interleave_probe.cpp` (`make probes`): calculate_products against 2 and 4 points in
  lock-step, results bit-identical.
- Job scripts `benchmarks/expanse_2026-10-c8/stage4a/scripts/` (build, prof1..prof4, `submit_prof_expanse.sh`,
  `h7_admit.py`: H7E-R before every sbatch) and `benchmarks/symmetry_2026-10-c8/stage4a/scripts/` (P4 on amddebugq,
  `submit_prof4_symmetry.sh` with the H7 check).
- `tests/test_profiling.py` (in `make test-python`): shapes and refusals, parsers on captured perf text, P3 summaries,
  the committed fixtures and their byte-identical rebuild, admission snapshots, script directives, the order-7 function,
  and end-to-end runs of every driver with the fake worker, a fake perf and fake diagnostic builds.
- `docs/PERFORMANCE.md`: "Stage 4a: profiling tools and frozen workloads".

## 2026-10-04: Checkpoint review fixes

The Stage-3 checkpoint Codex review (three sessions K, O and T on c8 601b102; artifacts in
`LRI_C8_D2_HPC_loop/artifacts/ckpt_{K,O,T}/`) returned REVISE with 20 findings. No physical value; no change to the
native arithmetic, the default numerics, the merge's summation order or any merged table (every merge test compares
the published tables byte for byte with the serial reference).

### Tools: O01–O11, CK-K01 = O05, T-01 = O02

Each line: finding → fix → regression test (each test fails on 601b102 and passes here).
- **O01 (high)**: cached phase-2 runs were trusted on their `#end` footer → `tools/production.py`: a complete
  intermediate run is reused only after `_verify_run` shows it is exactly the merge of its inputs (the inputs' row count,
  (rep, graph, begin) order, nothing after `#end`, and the order-independent digest Σ BLAKE2b_k(line) mod 2^256 equal
  to the sum over its inputs; phase 1 computes the digests of its fresh runs from the validated checkpoints, so the
  expectation never comes from a stored file, and the key k is drawn afresh by each merge and never stored, so an edit
  made before the merge cannot be crafted to keep the sum, as an unkeyed sum would allow by a generalized-birthday
  search); a run that fails is reported and rebuilt ("N rebuilt after failing verification") →
  `tests/unit_orchestration.py` `merge_cached_runs_verified_rebuilt_on_tamper_O01_...`: a changed value digit, two
  rows swapped, a row removed and a row after `#end` in a cached run each detected, rebuilt, tables equal to the
  serial reference; the same run verifies under its own merge key only.
- **O02 = T-01 (medium)**: phase 1 held a whole shard's rows → `_phase1` streams the per-index task file in blocks
  (`iter_job_blocks`: pin checked before the first block, re-hashed while parsed), sorts each checkpoint block into a
  spill run and merges the spills with the same fan-in F (several passes above F blocks); nothing that outlives a block
  is allocated per block (seconds in flat arrays, spill names made after the loop). A merge process holds one block plus
  F rows → `tests/merge_scale.py` memory scaling: fixed block (256 tasks) and fan-in (16), 8× the rows per shard, one
  shard and four: tracemalloc peak growth ≤ 2 MB (measured 0) and peak-RSS growth ≤ 16 MB (measured 4.4 MB and
  1.7 MB), byte-identical to the serial merge; the unit test above also merges shards of many blocks under fan-in 2.
- **O03 (medium)**: the planner ran the LPT before the task caps → `plan` checks `--max-tasks`, the login-node guard,
  lower bounds of the checkpoint blocks and projected files, and the merge projection before any task-sized array, then
  the exact counts after the LPT → `chunking_sizing_estimates_per_campaign_caps`: `_lpt` made a trap for the
  `--max-tasks`, `--max-checkpoints`, Expanse file and login-node refusals; the exact post-LPT block refusal kept.
- **O04 (high)**: merges dropped the extra options (partition overrides, AMD cap) → `tools/slurm_submit.py`: per-role
  effective options (`user_tokens(role)`): a merge keeps every user option but its own memory, CPUs and name (its time
  stays the user's `--time` if given, else `C8_MERGE_TIME`); admission counts each role on its own partitions; the
  ledger records each job's own partition and account →
  `submission_roles_merge_keeps_overrides_admission_and_ledger_per_role_O04`.
- **O05 = CK-K01 (medium)**: `slurm/lane_worker.sh` carried `#SBATCH --exclusive`, which a drill cannot cancel → the
  directive is removed; `--exclusive` is added by the submitter for normal lane workers only; before every `sbatch` the
  job's effective options (script directives, then `SBATCH_*` inputs, then the command line; `effective_options`) are
  checked against its role (normal lane exclusive with `C8_LANE_MEM`; drill lane never exclusive, `-c
  C8_LANE_CPUS`, `--no-requeue`; merge never exclusive with its own CPUs and memory; the admitted partition), else 64
  → `lane_drill_mode_shapes_and_refusals_effective_options_no_exclusive_directive`: no `--exclusive` in the directives
  plus command line of a drill worker or merge, a directive added to the script refused (64, nothing submitted), the
  precedence.
- **O06 (high)**: accounting computed η_node from whatever sacct returned → `tools/accounting.py` fails closed: an sacct
  line that does not parse, a ledger job without a record, a ledger array element without one, or fewer records than
  the attempts shown by the ledger and the checkpoints' `SLURM_RESTART_COUNT` make it incomplete (reasons listed,
  η_node null, hours as lower bounds, exit 4); `design.py` refuses to report or freeze on it (a complete η_node above 1
  is still capped at 1, conservative, and recorded) → `ledger_..._incomplete_fails_closed`: each case against its
  complete counterpart, the design refusal, the CLI exit 4.
- **O07 (high)**: submissions continued after a job was accepted without `TimeLimit=UNLIMITED` → `sbatch()` raises
  `Unverified` (70) carrying the job id and every job accepted so far; `lanes N` stops at once (no further worker, no
  merge, no cancellation), likewise an unverified merge, and arrays stop before their merge; the recovery (`--lanes 0`,
  `resubmit.sh`) waits on every live job → `unverified_job_stops_the_submission_recovery_waits_on_every_live_worker_O07`.
- **O08 (medium)**: a superseded merge was cancelled from a stale snapshot → `cancel_if_pending`: `scontrol hold` (refused
  for a started job), the state read again (a started one released and left alone), then `scancel --state=PENDING`;
  the outcome is a ledger note → `superseded_merge_cancelled_only_while_pending_by_the_scheduler_O08` (a merge that
  starts during the submission is left alone; a scheduler accepting the hold of a started job; a pending one held and
  cancelled); the fake squeue/scancel/scontrol model `--state`, hold and release.
- **O09 (medium)**: a resumed sweep failed on its own published cost model → `make_cost_model.py --reuse-identical`
  keeps an existing model equal to the one recomputed from the campaign's merged tables (all fields but
  `derived_utc` and `note`) and refuses another by name (exit 3); `sweep.py` uses it, then completes the calibration →
  `tests/test_pipeline.py` `O09_sweep_finalization_resumes_reuses_its_model_refuses_another`.
- **O10 (medium)**: `verify_result.py` compared some fields with themselves → the variance identity Var(C_full) =
  power_free_se² + power_correction_se² + 2 power_free_correction_covariance (to 1e-10 of its largest term; measured
  residuals ≈ 1e-16); for combinations the count, dof, chi-square, final and status recomputed from the stored per-batch
  values (`combination_status`, shared with `combine.py`); closed schemas for the batches block, the combination
  fields and `test_partial`; every test_partial key null at the top level; an assembled result's `final` consistent;
  the docstring now says what is recomputed, identity-checked and schema-checked → `tests/verify_result_tamper.py`
  (54 checks, 32 new: identity edits, test_partial additions and deletions, ten edits each to a final and a test-only
  combination, a partial marked final).
- **O11 (medium)**: `design.py`'s reuse parameters did not reach the pilot reader or the bundle schemas →
  `--dimension D --schema-prefix c8-dD --half-d D/2` must agree and name the pilot (`<prefix>-production-1` of
  dimension D); every schema read or written follows the prefix (group configs, merged tables, bundles, rate maps, the
  report); a c8-d2 pilot is verified as `production.py` does, another package's pilot through the campaign interface
  (pinned configs, validated merged tables) with `--inventory`/`--two-loop` (and `--selection`) required at the sha256
  its inputs manifest lists; `accounting.py` reads the prefix from the manifest; `production.group_of`,
  `validate_merged` and `validate_rates` take the schema → `tests/test_pipeline.py`
  `O11_C8-3_command_line_freeze_report_rates_on_a_c8-d3_pilot_...` (freeze, report and rates on a c8-d3 view of the
  fake pilot with the documented C8(3) command line, η_node from its ledger, the d = 3 Jacobian; refusals for the
  default parameters, an inconsistent half-d or prefix, missing or foreign inputs, a d = 2 pilot as d = 3, a d = 2 plan
  of the c8-d3 bundle) and A-DES-6 (the d = 3 bundle schema; inconsistent parameters refused).
- Documentation: `docs/HPC.md` (phase-1 streaming, verified merge restart, per-role options and admission, effective
  option checks, conditional cancellation, the O07 stop, accounting completeness, sweep restart), `docs/DESIGN.md`
  (the H6 interface table, η_node completeness), `docs/PERFORMANCE.md` (merge memory), the tools' docstrings.

### Kernel and tests: CK-K02, CK-K03, T-02 to T-06

Each line: finding → fix → regression test (each fails on 601b102 and passes here). The production workers are
unchanged: built from 601b102 and from this tree (GCC 11.4, x86-64; development check on a personal desktop, job 267),
`c8d2_decimal` and `c8d2_gmp` are byte-identical, and the inspector's output on every L3–L6 graph of both sectors is
identical. The validate.py parts below ran there on L6, and the real builders at L3–L6 (threads 1 and 2, job 268)
pass the stricter `gen/regress.py` with the verdict counts of the Expanse J-GEN-1 record (free: rate-only 5, 16, 76,
395 files; power: identical; no relabelling; every header equal to its row). Owed on the cluster:
`tests/validate.py --only inspector` (L7/L8, part of J-VAL-1) and the full J-GEN-1 re-run (L3–L7, threads 1 and 8).
- **CK-K02 (medium)**: A-INV-2's free L ≤ 6 relabelling exception compared only masks and terms, so a G-file with a
  changed weight passed (G1 has an identity permutation), and the rate-only rule accepted a rate table of another
  size → `gen/regress.py`: `parse_gfile` checks the kernel's structure (masks of L edges in [0, 2^E), term shapes,
  2^E = 2^(2L) on its line and as the rate-table size); `legacy_relabel_equal` requires the header (magic, L, id, wa,
  wb, M, T), the 2^E line and the rate-table size identical, only mask, term and rate-value parts differing, the masks
  and terms different as they stand (an order difference alone, an identity permutation or a recorded automorphism
  proves nothing) and equal after the recorded permutation; the per-file verdict is `judge()`; every G-file header is
  checked against its own inventory row (`header_inventory_mismatches`, new and frozen trees) → new
  `gen/test_regress.py` (42 checks; `make test-python`, J-GEN-1): weight, id, rate-size and 2^E edits refused with and
  without a relabelling, a true relabelling (free L4 G2, either direction) accepted, reorderings refused, header-row
  mismatches reported, and end to end `regress.py --loops 3` with fake builders: the reviewer's wa-only edit of free
  L3 G1.txt and a rate table one entry short fail A-INV-2 (both passed on 601b102).
- **CK-K03 (medium)**: the inspector wrote predictable `TMPDIR/c8d2_inspect.<pid>.<thread>.txt` files, truncating
  through symlinks → `src/c8d2_inspect.cpp`: a private `mkdtemp` directory (0700) under `$TMPDIR` holding one file per
  thread, created once before the parallel loop with `O_CREAT|O_EXCL|O_NOFOLLOW` (0600) and rewritten in place per
  graph; files and directory removed on normal exit, on errors (exit 2) and on the terminating signals (an
  async-signal-safe handler; ignored signals stay ignored; previous dispositions restored) → `tests/validate.py`
  `inspector_private_tempdir` (part `inspector`): with a fresh TMPDIR, a normal run and an error exit leave it empty;
  during a long run it holds one directory `c8d2_inspect.XXXXXX` (0700, this user) with only `g<k>.txt` (0600);
  SIGTERM and SIGUSR1 kill the run and leave nothing; an ignored SIGHUP stays ignored. The 601b102 inspector fails it
  (its files sit in TMPDIR and survive a kill).
- **T-02 (medium)**: `tests/vendored_isolated.py` wrote `"passed": true` from its `finally` block when a step raised →
  the record passes only when every step ran (`completed`), an exception or interruption is a failed check with its
  `error`, and the exit status follows the record → `tests/unit_orchestration.py` `drivers`: `--in-place` in a tree
  with `.git`, a tree without the HANDOFF and a HANDOFF whose counts do not parse each give `passed: false`,
  `completed: false` and the error (601b102: `passed: true`, no checks).
- **T-03 (medium)**: `--only` ignored unknown names (vacuous "passed") → `tests/unit_orchestration.py` (table `TESTS`,
  `selection()`) and `tests/test_pipeline.py` (`PARTS`) refuse an unknown name or an empty list before any setup
  (exit 2), fail a run that executes nothing, and record `requested` and `executed`; `tests/validate.py` refuses a run
  that selects nothing (`--only` empty or `none` without `--bk8`/`--l2-control`/`--l8self`) and records `executed` →
  `drivers`: eight bad selections refused fast with no record, validate's two, and a valid selection's record (601b102:
  exit 0, "passed", zero tests, in all three drivers).
- **T-04 (low)**: A-KER-5 compared a copy of the worker's comparator (`tests/order_key.cpp`) with a Python copy →
  `src/c8d2_integrate.cpp` gains the diagnostic build `-DC8_ORDER_TRACE` (kind `order_trace`, refused by `plan`;
  `tools/build_record.py` knows it): the parallel task loop records the uid each iteration runs, and the JSON gains
  `"addends"` and `"execution_order"`; without the macro the preprocessed worker is unchanged (the release binaries
  above are byte-identical). `tests/order_key.cpp` is removed. `inspector_order` (record `inspector_execution_order`)
  builds the trace worker and checks inspector = inventory = worker addends, the executed order = the order predicted
  from the inventory, and the trace rows = `bin/c8d2_decimal`'s → on a personal desktop, the worker with its comparator
  reversed and with the loop ignoring the order each fail it ("executed order differs"); the old harness could not see
  either.
- **T-05 (low)**: `tests/ast_scan.py` carried names deleted in a finally block past it → the flow analysis carries
  assignments and deletions through finally blocks on the normal exit and on breaks and continues leaving them, checks
  a finally block and the handlers against the weakest state reaching them (deletions in the try included), iterates
  loop heads to a fixed point over the body's end and every continue, reports a `del` of a possibly unbound name,
  handles `del (a, b)`, and lets a match without an irrefutable case match nothing → 17 new self-test probes (deletion
  in finally, through break and continue, in loop bodies, on continue paths, in while bodies, before handlers and
  finally, tuple deletion, match cases); 13 of them fail on 601b102's analysis, which also flagged a correct match.
  tools/ still scans clean (24 files, 0 findings).
- **T-06 (low)**: the `SLURM_MEM_PER_NODE` assertion ended in `or True` → `test_lane_units` mocks
  `cgroup_memory_limit` to None and asserts the exact limit (2048 MiB → 2^31 bytes, `SLURM_MEM_PER_NODE`), the
  non-numeric and absent cases, the cgroup's precedence and the guard's lanes at that limit; `test_lanes` runs the lane
  worker with no visible cgroup (a fake `/proc`): a `SLURM_MEM_PER_NODE` of 1.5 lanes' largest `est_peak_bytes` runs 1
  of 2 lanes and one below a lane refuses (64) → with `memory_limit` mutated to ignore `SLURM_MEM_PER_NODE`, both tests
  fail; the 601b102 test passed.
- Documentation: `docs/NUMERICS.md` (the trace build, the inspector's private directory, A-KER-5), `README.md`
  (`gen/test_regress.py`), the scripts' docstrings; `Makefile` `test-python` and the J-GEN-1 scripts run
  `gen/test_regress.py`.

### After the independent verification: O11 residual, test robustness

The verification of ffbc8af (`benchmarks/expanse_2026-10-c8/ckpt_fix/verdict.json`) found O11 partial and two test
weaknesses. Each line: finding → fix → regression test (each fails on ffbc8af and passes here).
- **O11 residual**: the η_node path of `design.py` went through `tools/accounting.py` and `tools/ledger.py`, which
  accepted only `c8-d2-ledger-1` records, so a C8(3) Slurm pilot with its `c8-d3-ledger-1` ledger was refused at
  freeze and report; the O11 test hid this because its d = 3 view kept the copied c8-d2 ledger → the ledger and
  accounting schemas follow the same schema prefix as `design.py --schema-prefix`: `ledger.py` (`schema(prefix)`,
  `check_campaign`, `read`/`jobs`/`register` and the CLI's `--schema-prefix`, default `c8-d2`) writes and reads
  `<prefix>-ledger-1` records only for a `<prefix>-production-1` campaign; `accounting.py --schema-prefix` reads that
  ledger and the `<prefix>-group-1`/`-merged-1` tables and writes `<prefix>-accounting-1`; `design.py` passes its
  prefix to both on every η_node path (the ledger is checked even for a local or `--eta-node` pilot). A mismatch (a
  campaign of another prefix, or any ledger record of another prefix) is refused, never skipped
  (`ledger.SchemaMismatch`: `design.py` exit 2, `accounting.py` exit 2, `ledger.py` exit 64) →
  `tests/test_pipeline.py` `O11_..._its_c8-d3_ledger_eta_node_...`: the d = 3 view replaces the copied ledger by the
  same allocations registered with `ledger.py register --schema-prefix c8-d3`; freeze and report take η_node from it
  (= the hand value, source `tools/accounting.py`); `accounting.py --schema-prefix c8-d3` gives a
  `c8-d3-accounting-1` record equal in jobs, hours and η_node to the c8-d2 pilot's; refused: the default prefix on the
  c8-d3 campaign (accounting, ledger list and register), the c8-d2 ledger under the c8-d3 campaign and one c8-d2
  record appended to its c8-d3 ledger (freeze, report, accounting, register; nothing published, ledger unchanged), a
  c8-d3 ledger under a c8-d2 pilot (freeze) and registering it with `--schema-prefix c8-d3`. On ffbc8af the test fails
  at the ledger writer (no `--schema-prefix`); with only the new `ledger.py`, ffbc8af's `design.py freeze` refuses the
  c8-d3 ledger ("is not a c8-d2-ledger-1 record").
- **Flaky `signals` (run_array.sh launch boundary, stage 0)**: a real race, not only a short wait. A TERM that reaches
  the background job between its fork and the exec of Python, while it is still a copy of the shell, can be lost
  (measured with the Mac's bash 3.2 on a minimal copy of `on_signal`: 64 of 300 launches under load ran on after the
  TERM). The job then ran until
  `on_signal`'s KILL after 30 s, which leaves its `c8d2_runtime_*` behind: the leftover of the failures on canonical
  (job 269) and the Mac reproduction → `slurm/run_array.sh` repeats TERM every 0.5 s to the jobs still running
  (production.py ignores a repeated TERM once it is stopping; 0 of 300 ran on in the same reproduction). A smaller
  window in `production.py run` is closed too: the job-private runtime is created with stop signals deferred (as a
  native launch is), so a signal between its `mkdtemp` and the `try` that removes it can no longer leave it behind →
  `tests/unit_orchestration.py` `signals`: a new shell case `lost_term0` starts the job with TERM ignored (a wrapper
  that execs Python) and sends the boundary TERM only then, so the first TERM is lost every time; it must exit 143
  with the job gone, no "killed" line and the scratch empty. ffbc8af fails it exactly as canonical did (KILL after
  30 s, `c8d2_runtime_*` left); here it passes in seconds. The waits are longer (native start 180 s, script 180 s,
  job gone and scratch empty 30 s each, the native child 60 s), the assertions unchanged.
- **macOS `merge_scale` RSS margin**: on macOS the peak RSS grew 12.4 MB in one shard against the 16 MB bound
  (the allocator; the Python heap flat; Linux 1.4 MB) → `tests/merge_scale.py`: the RSS bound's default is per platform
  (`RSS_GROWTH_MB`): 16 MB on Linux and every platform but macOS (unchanged, strict), 48 MB on macOS, where the
  tracemalloc gate (2 MB, every platform) is the exact one; the record states the bound, its platform and its source
  (`memory_scaling.rss_bound`). A phase 1 that keeps a shard's rows (601b102: about 530 bytes per extra row) exceeds
  48 MB in one shard at 4 → 32 points, and the tracemalloc gate catches it in four shards.
- Documentation: `docs/DESIGN.md` (ledger and accounting rows of the H6 table, the prefix rule), `docs/HPC.md` (the
  ledger prefix, the per-platform RSS bound), `docs/PERFORMANCE.md`, the tools' and tests' docstrings.

## 2026-10-04: Stage 3, part B: six low-severity review fixes (design tails, merge restart, admission parsing, A-ORC-13 notes)

No physical value; no change to the native arithmetic, the default numerics, any merged table or any design count.
- **`tools/design.py` tail rule, now C63d's** (`LRI_C8_D3_HPC_loop/PLAN.md` C.3 and E.6, `RECON.md` §6.3.6,
  `recon/cost_d3/tail_calib.py`):
  - the screen (ξ̂ > 0.38 or largest share > 0.05) and the confirmation (two-campaign mean ξ̂ > 0.44 at ≥ 32,768
    points) apply to **L8 graphs only**; L ≤ 7 statistics are reported as diagnostics (a per-(sector, L) summary in
    the report, every row in `--tails-out`), with no threshold and no "screened"/"confirmed" label. The stratum P8 flag
    (action 5, > 1.196 with ≥ 500 graph-campaigns) likewise applies to L8 strata only, as C63d's E.6 item 3 states for
    actions 1–5;
  - a replicate with fewer than 16 tail values, a 16th |t| ≤ 0, `tail_sum` ≤ 0 or a non-finite value makes the
    graph-campaign entry "undefined (<reason>)", with no mean over the remaining replicates; an L8 graph undefined in
    either campaign is listed and counted under `tails.undefined` and never compared with a threshold;
  - the sector P8 of the R = 16 switch (action 4) pools Var(Q) over the sector's **L8 graph-campaigns at 4,096 points
    per replicate**, not over all loops. This design flow has no separate stage A; the pilot's 4,096-point L8
    graph-campaigns are the closest equivalent (documented in `docs/DESIGN.md`); L8 graph-campaigns at other point
    counts and every L ≤ 7 graph are left out and counted (`excluded_L8_other_points`, `excluded_L_le_7`);
  - `--tails-out` gains the columns `use` (`thresholds`/`diagnostic`) and `status`.
- **`tools/production.py` merge: phase 2 resumable per output run, as the plan says.** The intermediate runs moved from
  the job's `TemporaryDirectory` to the persistent per-campaign work directory `<campaign>/merge_work` (`--work-dir
  BASE`: `BASE/c8d2_merge_<manifest sha256 prefix>`). Each run is named by a hash of its inputs' identities (the
  phase-1 runs' sha256s, then the earlier pass's names), written to a unique temporary file, fsynced and renamed; a
  rerun reuses every complete run (`_complete_run`) and prints how many. A group's runs are removed only after its
  `merged.json` is published (or found published and valid), the directory once empty. Phase-1 runs and the final
  pass stay job-private under `--scratch`. Outputs remain byte-identical to `--serial`.
- **`tools/slurm_submit.py` admission:** squeue's format is now `%i|%T|%P|%q|%D|%u|%j` (the job name, the only free
  text, last) split at the first six `|`, so names containing `|` are counted; a line that still does not parse
  refuses admission (exit 69, nothing submitted) instead of being skipped.
- **A-ORC-13 notes** (`docs/HPC.md` "Reads per claim", the test's docstring and comment): a claim also makes constant
  libc/OpenSSL reads (`/proc/sys/crypto/fips_enabled`, `locale.alias`, `zoneinfo`), independent of the task count and
  invisible to the Python-level spy; `rchar` on real Slurm includes them.
- **Tests.** `tests/unit_orchestration.py`: `merge_phase2_resumes_from_complete_runs_after_interrupt` (a merge killed
  mid-group with one torn output, rerun reuses every complete run, total − k recomputations, byte-identical to the
  serial merge, work directory removed; for the default and `--work-dir`), and
  `admission_squeue_job_names_with_pipes_counted_unparsable_line_refused` (the fake squeue prints the new format).
  `tests/test_pipeline.py`: `A-DES_tails_L8_thresholds_L7_diagnostics_undefined_sector_P8_L8_4096` (every expected
  value computed independently). `docs/HPC.md` (merge restart, admission format), `docs/DESIGN.md`, `slurm/merge.sh`
  header.

## 2026-10-03: Stage 3, part B: orchestration, design and statistics (components D, E, F) [A-ORC-1..7, A-ORC-9..13, A-ASM-5/6/7, A-DES-1/2/6]

No physical value; nothing in this part changes the native arithmetic or the default numerics.
- **`tools/production.py`** (generalized from C7(2)): 24 groups (D10) with hashed seeds and the forbidden-seed registry
  (D9); exactly one allocation source (D8: `--pilot [--points P]`, `--design BUNDLE`; a design bundle is read first,
  so a provisional rates bundle is refused before any other check, R19); `--test-graphs N|all` with
  `--test-selection cheapest|stratified`; three cost bases (a measured campaign-keyed cost model, calibrated proxy
  rows, the first-sweep bootstrap with the labelled preliminary proxy, R13); chunks of 60/c_g seconds as powers of two
  in [256, n_g]; index sizing from `--index-hours` with an exact LPT per group (R05); every cap (tasks, checkpoints,
  the Expanse file cap, task seconds, the Sobol period) checked before anything is created, then an atomic publication.
  Per-index task files `groups/<g>/tasks/s<shard>.tsv` pinned in the manifest by sha256 and size; `run --index` reads
  only its own file and never `tasks.sqlite` or `vendor/` (R07, A-ORC-13); the real host fingerprint with its bytes
  counted (`fingerprint_bytes`; R17, R20). Frozen rate maps (R04) and the rates identity in manifest, configs and
  checkpoints. `merge --jobs N [--fan-in F]`: per-shard sorted runs, an external merge with F = min(64,
  RLIMIT_NOFILE − 32), refused when F < 2, byte-identical to `--serial`; it prints the phase-1 and phase-2 rows per
  second; `graph_tails.csv` and `graph_costs.csv` per group. `status --fast`, `recover`, `tag`.
- **`tools/lanes.py`** (port of LRI_C7_D3_HPC@a6ce987 with the plan's changes): NUMA/socket lanes, the memory guard,
  the CPU-class deadline factor, `UNLIMITED` per time policy, done markers as hints with queue generations and the
  claim-holder reconciliation (R03), bounded scans, drill mode, attempt identities in failure and log names.
- **`tools/slurm_submit.py`**, `slurm/submit.sh`, `slurm/resubmit.sh`, `slurm/lane_worker.sh`, `slurm/run_array.sh`,
  `slurm/merge.sh`, `slurm/plan.sh` and the new `slurm/sweep.sh`: one guarded submission path for arrays and lanes,
  repeated `lanes N` with merge replacement (A-ORC-10), admission counting every new job (R12) with the site lock,
  the symmetry AMD-pool cap (H7) and the Expanse rule H7E-R; memory and wall-time policies; the allocation ledger.
- **`tools/ledger.py`, `tools/accounting.py`** (R10), **`tools/seeds.py`** (D9), **`tools/sweep.py`** (J-SWEEP),
  `tools/make_cost_model.py` and `tools/calibrate.py` (campaign-keyed rows, the bootstrap proxy regenerated only from
  the pinned C7(2) calibration, R18), `tools/stage_runtime.py` (members only).
- **`tools/design.py`** (component E; port of C8(1)'s design8.py): report, freeze and rates (`docs/DESIGN.md`).
  `tools/combine.py` end to end on campaign directories (and `--test-only`); `tools/assemble.py` with the per-stratum
  coverage guard.
- **Tests** (component F): `tests/unit_orchestration.py` (38 tests), `tests/test_pipeline.py` (new), `tests/ast_scan.py`
  (new), `tests/merge_scale.py` (new), `tests/pkgcopy.py` (the shared package copy), `tests/workflow.py` and
  `tests/staging.py` (ported to the C8 worker and 24 groups), `tests/test_delivery_verifier.py` (R16 symlink cases),
  `tests/check_vendored.py` (the vendor/ rule now also for `plan` and `run --index`), `tests/fake_worker.py` (order 8,
  class-B fields, `@FILE`). `make test-python` runs the pure-Python set; `make test` adds the native subset, workflow
  and staging.
- **Docs.** `docs/HPC.md` and `docs/DESIGN.md` (new), the orchestration contract in `docs/NUMERICS.md`; the C7(2)
  `HPC.md` and `PERFORMANCE.md` moved to `docs/c7_historical/`. `tools/verify_delivery.py`: schema
  `lri-c8-d2-hpc-delivery-1`, a tracked symlink refused by `--write`, the L8 packs and `build/` excluded as build
  outputs.
- Removed: `tools/primitive_allocation.py` and `tools/reassemble_reference.py` (C7(2)-only; C8 has no retained mode
  and `tests/compat_2026.py` covers the 2026 reassembly). `slurm/env_expanse.sh` exports `C8_SEEDS`.

**Fixes after the first Expanse runs** (moved tag; jobs 54641703 and 54641705 on export `81aa977`):
- `tests/unit_orchestration.py`: the A-ORC-13 claim test allowed the import opens of the main package copy's tools only;
  on Linux the claim runs from the real-executable copy, whose `tools/__pycache__` lookup it then flagged (job 54641703).
  It now allows the claim package's own tools, and keys the probe pipe without its descriptor number. The R13/R18
  tests set the pre-sweep state they assume (the pinned C7(2) calibration) in their package copy, so they no longer
  depend on the package's active `tools/calibration.json`; the R18 test asserts that the update changes the active file
  and records whether it was C7(2)'s. The done-marker test asks for lanes of at most 8 CPUs, and the driver runs every
  test to the end and exits 1 on any failure (commit `81aa977`).
- `tests/merge_scale.py`: the plan of about 3.9 * 10^6 tasks must run inside a Slurm job (production.py refuses it
  elsewhere), so the test keeps `SLURM_JOB_ID` for its plan step (job 54641705 failed at the plan).
- The Stage-3b job scripts put temporary package copies on the node-local NVMe and run the `make test` list command by
  command (each to the end, with its own record).

**Fixes after the second Expanse runs** (moved tag; jobs 54643233 and 54643234 on export `1d25d9e`):
- `tools/production.py` merge, found by `tests/merge_scale.py` at 1.25 × 10^6 rows on Linux (job 54643234):
  - the parallel merge was not byte-identical to the serial reference: `integration_seconds_sum` and
    `thread_seconds_sum` in `merged.json` were float sums in shard-completion order (serial: block order). Both paths now
    sum the per-block values with `math.fsum` (correctly rounded, so independent of any order);
  - with RLIMIT_NOFILE = 48 and 16 merge processes, a forked worker started with the pool's descriptors open and hit
    EMFILE in phase 2. The merge pool now spawns its workers (no inherited descriptors), as on macOS.
- `slurm/run_array.sh`: the signal trap gives the launched child 30 s after TERM, then KILL, instead of an unbounded
  `wait` (the launch-boundary test once timed out on Expanse, job 54643233; it passed 6 times in isolation, job
  54643327). The test now writes the script's output to a file, runs it in its own session and, on any failure,
  reports the return code, the launched process and the process table.
- `tests/unit_orchestration.py` (A-ORC-13 on Linux, job 54643233): the read spy also counts the probe's pipe when
  `subprocess` reads it with `os.read` (`communicate` with a timeout, the `ldd` probe); `/proc/cpuinfo` is read live
  (its MHz fields change), so its sizes in the two campaigns need only agree within 1%. With both, the Linux claim with
  the real `bin/c8d2_gmp` passes (job 54643327).

**Plan additions agreed with C63d** (recorded here as the plan asks):
- (i) **H7E-R**, the Expanse disjoint reservation (`LRI_C8_shared/inventory/DECISIONS.md`, 2026-10-03): at most 11
  running / 27 submitted normal-QOS `c8d2-*` jobs, the whole <ACCOUNT> account at most 32 running, at most 32 live
  shared-partition jobs and 4 compute nodes during development; a pilot window re-splits it only through a DECISIONS
  line (`C8_EXP_*` with `C8_ADMISSION_REF`). It replaces the plan's earlier Expanse rule in A-ORC-11: the fake-squeue
  test now admits `lanes 1` at 25 submitted and refuses it at 26 (largest N 0), instead of 52/53.
- (ii) **Per-graph heavy-tail diagnostics**: the native class-B fields (part A) and `design.py report`'s Hill rule
  (C63d's thresholds), with `--tails-out`.

**Deviations and interpretations** (for the G3 review):
- A-ORC-13: the manifest and the group config hold per-index numbers (tasks, blocks, bytes, estimates), so their sizes
  differ by digits between the 10^3- and 10^6-task campaigns; the test requires one whole read of each, the same
  structure with numbers and digests blanked, and a size difference below 5%, and exact equality for every other
  campaign-data file and for the platform class.
- A-ASM-6: `plan --design` pins the bundle's numerics and rates identity, so two batches of one bundle cannot differ in
  them; `test_pipeline.py` reaches those two refusals of `combine` on the loaded batch records of real campaigns with
  one field changed, and refuses a batch of the fresh rates bundle against a batch of the source bundle by design.
- A-FLAG-6 "a non-test plan accepts it": on the test fixture only test-only plans exist; `test_pipeline.py` shows a
  test-only plan accepting the fresh bundle under the map and the D15 check accepting the sweep's cost model for a
  non-test plan under the map (and refusing it for a default one).
- A-ORC-7 "Records": the profile and benchmark records of the Stage-4 tools (still C7(2)) are not yet generalized.
- A-ORC-5 (L8 smoke RSS) and A-ORC-8 (real-Slurm restart drills) belong to Stages 5 and the drills; A-ORC-6's 10^6-row
  merge is the cluster run of `tests/merge_scale.py`.

## 2026-10-03: Stage 3, part A: the native kernel (component C) [A-KER-1..5, A-RPL-1..6, A-IN-6(b)]

No physical value; the default numerics are C7(2)'s bit for bit (`numerical_change: false`), and no optimization is
included (Stage 4).
- **`src/kernel.hpp`.** One order fixes every size: the constants block (`LMAX=8`, `ORDER_MIN/MAX=7/8`, `EMAX=16`,
  `KMAX=6`, `NLOGS=7`, `NVALUES=14`, `DIMMAX=31`) with its static_asserts sizes every array. `sample()` returns and
  takes `std::array<ld,NLOGS>`. The GMP macro is `C8_USE_GMP`. The EMAX guard of `load_graph` is tested on L before
  E = 2L is formed. `evaluate()` carries diagnostic hooks that are empty in every production build
  (`src/diagnostics.hpp`, new: per-tier timers and ratio histograms).
- **`src/c8d2_integrate.cpp`** (`git mv` of `src/c7d2_integrate.cpp`).
  - Task header `C8D2TASKS1 <order> <L> <nt>` (order 7 or 8, 2 <= L <= order), K = order - L.
  - Gamma rows l = 2..order with labels order-l and exactly order-1 logs, then end of file (D7).
  - Net dimension <= DIMMAX. The scalar rate must be a full decimal token in (0, 1].
  - The R7 `@FILE` rate map: exact coverage of the task file's graphs, `"rate":"file"` and a per-row echo.
  - Native schema `c8-d2-hpc-native-1` with `order`, `numerics` and `max_rss_kb`. `max_rss_kb` is the VmHWM of
    `/proc/self/status`, because `getrusage`'s maximum also counts the forking Python parent's pre-exec image on
    Linux; `max_rss_source` says which one was used.
  - `--describe` reports `c8-d2-build-1`, orders [7,8], lmax 8, kmax 6, emax 16, dimmax 31, numerics `exact`,
    `diagnostic` (with the kind for profile, ratiohist, sanitizer and no-tail builds) and `tail_top`.
- **Plan addition (ii), native side: the class-B tail fields** (agreed with C63d; the definition is C63d's
  LRI_C8_D3_HPC_loop/PLAN.md C.3). Per row, with t = v_0 * jac at each point (the weight-free base integrand, so
  zero-channel kernels are seen too): `tail_top` (the 16 largest |t|, descending), `tail_sum` (the long-double sum in
  point order) and `tail_argmax` (the global index of the first largest |t|). No existing value changes; a test-only
  build without them (`-DC8_NO_TAIL_FIELDS`) writes every other field identically. `tools/design.py report` (Hill
  rule) is a separate part of Stage 3.
- **Makefile.** `bin/c8d2_{decimal,gmp}` with C7(2)'s commands (`C8_REQUIRED`, `C8B_*` record variables); `NUMERICS`
  (only `exact` until Stage 4c); `make profile`, `make ratiohist`, `make sanitize`; `make c7ref` builds
  `bin/ref/c7d2_{decimal,gmp}` from `reference/c7d2_hpc_a55958f/` with C7(2)'s own Makefile; `make test`/`test-full`
  take `OUTPUT=<dir>` for the records. `tools/build_record.py` writes `c8-d2-build-record-1` with `NUMERICS`, the
  diagnostic kind and the executable's `--describe`.
- **Tests.**
  - `tests/validate.py` (rewritten): describe (A-KER-3), the refusals (A-KER-1/2 and the native part of A-FLAG-6),
    G-REF, G-C7 and G-JET (A-RPL-1/2/3; `--full` for all 3,773 L3-L7 kernels and the L2 graph, the 262 new L7
    kernels staged from the packs), chunk and layout invariance at L7 and L8 with the tail merge (A-RPL-6), the
    inspector ordering key on 100 kernels (A-KER-5, `tests/order_key.cpp`), class B, the diagnostic builds; `--bk8`
    (A-RPL-4), `--l2-control` (A-IN-6(b)) and `--l8self DIR` (the G-L8SELF machinery of A-RPL-7). Its Sobol test
    nets are written by its own checked SciPy export, independent of `tools/production.py`.
  - `tests/check_points.py` (450 digits, L3-L8, staged from the packs), `tests/forced_tiers.{cpp,py}` (A-RPL-5),
    `tests/thread_identity.py` (A-RPL-6), `tests/sanitize.py` with `--selftest` (A-KER-4).
  - `tests/unit_orchestration.py`: the literal-size grep and constants check (A-KER-1), and the build tests renamed
    to the C8 executables, macro and Makefile variables.
- `tools/common.py`: `environment_record` lists `bin/c8d2_{decimal,gmp}`.
- Still on C7(2) interfaces, for the other Stage-3 parts: `tools/production.py` (it no longer imports since Stage 2a),
  `tests/fake_worker.py`, `tests/workflow.py`, `tests/staging.py` and the Stage-4 tools `tools/benchmark.py`,
  `tools/benchmark_memory.py`, `tools/prepare_benchmarks.py` and `tools/profile.py`.

## 2026-10-03: Stage 2b, the assembly on the vendored module [G2b]

- `tools/assemble.py` (rewritten for order 8; `combine(ar, order=7)` kept for A-ASM-3).
  - It imports `vendor/c8_assembly/order8_assembly.py` only at its pinned sha256, and calls its `campaign_moments`,
    `sector_assembly` and `power_null_rows`.
  - Hard gates (ArithmeticError, exit 3): the top-slot rule for L = 3..order, the loop-7 entry at order 8, and the
    float affinity of loops 5..order. Each asserts full loop coverage first, because the vendored gates skip absent
    loops (H2 review).
  - The POWER_PROTOCOL report PP1-PP10 of the H2 review (step 6). The package-side PP8 marker covers order 6, and order
    5 at d=2. Non-finite inputs are refused, and a nonpositive SE in a null row is flagged.
  - Lower-order checks C3..C(order-1) against D11, with the C7(2) production reference.
  - `error_by_loop` as each (sector, L) variance contribution and its share; they sum to Var(C8).
  - The campaigns, the half streams and the bootstrap (seed 70530413).
  - `coverage_guard`: all 24 groups; every group's graph set equals the inputs inventory's; with a bundle, the counts
    equal the bundle's counts × s, read from digest-checked `counts/*` files.
  - `test_only_view`, and `coefficients`/`jacobians` wrappers at d=2.
- `tools/combine.py` (C8(2), replacing the C8(1) port): it combines the batches of one frozen design. It requires the
  same bundle, inputs manifest, numerics profile and rates identity, distinct group seeds, and the bundle's batch
  count (`--partial` for fewer). It concatenates the replicates, reports the per-batch C8 and the chi-square, and runs
  `verify_result` before a no-clobber publication.
- `tools/verify_result.py` (new; C7I-02, C7I-11). It recomputes the coefficients, power differences, gates,
  lower-order checks, null rows and SEs from a result's own fields. It requires exact key sets for the other blocks,
  and compares the whole tree: floats to 1e-10 relative of their sibling scale (with a 1e-2 floor inside the gates),
  every other leaf identical, and no key added or deleted.
- Tests:
  - `tests/assembly_checks.py`: A-ASM-2 bitwise against C7(2)'s `assemble.py` and `analyze.py`; A-ASM-4, plus
    `--exact` with the R09 key gate; A-ASM-5 with PP1-PP10 one test each.
  - `tests/compat_2026.py` (A-ASM-3): the 2026 production reproduced to 7.3e-16 relative; C7 is 6 ulp off on the Mac,
    numpy 1.23.5.
  - `tests/verify_result_tamper.py` (A-ASM-7, with the coverage guard).
  - `tests/combine_core.py`. A-ASM-6 on real campaign directories is Stage 3.
- `tests/vendored_isolated.py` passes `--confcutdir` at the export. pytest 9.1.1 on Expanse otherwise builds directory
  nodes from `/` and fails listing `/expanse/lustre/scratch`.
- C7(2)-era users of the old interfaces now fail until Stage 3 generalizes them: `tests/validate.py`,
  `tests/unit_orchestration.py`, `tests/workflow.py`, `tools/reassemble_reference.py`, and the `production.py`/`merge.sh`
  pipeline (C7 manifest schema).

## 2026-10-03: Stage 2a, the inputs [G2a]

- `tools/make_lowloop.py`.
  - `gamma_d2_8.txt`: 7 rows × 9 tokens. It is byte-identical to C63d's `inputs_d2_check` copy, which is a cross-check
    only.
  - `two_loop.json` holds 7 B2 strings; b_{2,6} = −266.520967961359381732252192619089800949020036…
  - `verification/two_loop_extension8.json`.
  - `--verify` passed 16/16 on the Mac and on Expanse (J-IN-1, job 54632984): the order-7 byte regression, the Cauchy
    check of every ℓ (1.09e-51), the two contours (3.08e-66) and the reference contour (7.71e-68) [A-IN-1, A-IN-2,
    A-IN-6(a)].
- `tools/prepare_inputs.py` (generalized).
  - The L7 packs hold every finite kernel (2,441 and 709). The L8 packs (16,064 and 4,336; not in git) come from the
    published tree by `selection.json` and `MEMBERS.sha256`.
  - The inventory rows carry the `bin/c8d2_inspect` fields.
  - The manifest pins the twelve packs, the inventory8_d2 MANIFEST and the vendored assembly (from
    `tools/VENDORED.json`).
  - `make inputs` covers L3-L7; `make inputs-l8 INVENTORY=...` builds the L8 packs.
  - `src/c8d2_inspect.cpp` (`make inspect`) and the component-C limits in `src/kernel.hpp` it needs: the constants,
    the EMAX arrays and the L <= 8 header guard.
- `tests/check_inputs.py`.
  - On Expanse (J-IN-2b, job 54633090): 26/26, with every generated file byte-identical, both L8 packs present and
    the inspector fields included [A-IN-3, A-IN-4, A-IN-5].
  - On the Mac: 27/27 with the inspector fields SKIPPED (no x86-64 build). The Mac's own L8 pack rebuild hits the same
    pins.
- Generated by J-IN-2a (job 54632985) and committed: `inputs/inventory.json`, `inputs/manifest.json`, the L7 packs and
  `tests/fixtures/inputs_mini`. The C7(2)-only inputs are removed.
- A-ASM-1 re-run in full on the G2a commit, after the early HANDOFF (R15).
  - `check_vendored.py` (a)+(b): 15/15 on the Mac and 14/14 on the cluster export.
  - `vendored_isolated.py`: 10/10 on the Mac.
- C63d acknowledged the gamma columns (B1) on 2026-10-03 (DECISIONS.md).

## 2026-10-03: Stage 1 on Expanse; inventory8_d2 published and handed off (H1)

- From an export of `36043bb` (`benchmarks/expanse_2026-10-c8/setup/export_check_36043bbc2117.json`: 4,706 files
  equal to `git archive`).
- **J-GEN-1** (job 54631551) passed A-INV-1 and A-INV-2. All 2,441 free L7 and all 840 power L3–L7 G-files are
  byte-identical to the frozen C7(2) files.
- **J-GEN-2** (job 54631552, one compute node, 128 threads) passed every A-INV-3 gate at the plan's numbers and
  published the tree with `MANIFEST.json` sha256 `46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099`.
- **A-INV-4 on Expanse** (job 54631553) reproduced `MEMBERS.sha256` and the builder inventories on a second compute
  node at 64 threads. The architecture check (symmetry Intel, J-GEN-3) is pending.
- **Copies** on Expanse (job 54631581) and on the Mac, each verified against the pin; a second publication is
  refused.
- `LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json` written by `gen/handoff_inventory.py` (new `--note` option),
  and C63d notified (`NOTE_C62d_to_C63d_H1.md`). Evidence: `benchmarks/expanse_2026-10-c8/` [G1].

## 2026-10-03: the assembly HANDOFF, vendored (On HANDOFF, H2 checklist step 10)

- **Delivery.** C63d's `LRI_C8_shared/assembly/HANDOFF_assembly.json` (sha256 `f5ff6a353371…`) passed C62d's H2
  review (`LRI_C8_shared/inventory/reviews/order8_assembly_f5ff6a353371.json`, ACCEPT_WITH_MINOR, verdict-gate
  decision `accepted_documentation_only_minor_fixes` for this HANDOFF version only).
- `vendor/c8_assembly/`: the 13 deliverables the HANDOFF lists, byte-identical at its sha256s, and the HANDOFF copy
  [A-ASM-1, R01]. `vendor/c8_assembly_fixtures/`: 50 pinned byte copies (555,995 bytes) of the external files the
  vendored tests and `exact_check.py` read through `LRI_ROOT`, the read set measured by the review's open-audit run;
  regular files only [R16].
- `tools/vendor_assembly.py` writes both trees and `tools/VENDORED.json` from exactly the HANDOFF list (it refuses a
  changed folder, an unreviewed HANDOFF and an existing vendored set). `VENDORED.json` holds the pins, the fixture
  provenance (25 reference copies at their checksum entries, 3 `git show` of `LRI_C7_D3_HPC@a6ce987`, 22 files with
  the sha256 recorded first), the review verdict and verdict gate, and the structured signatures of the 11 names the
  package uses.
- `tests/fixtures/exact_check_keys.json` (checklist step 7, R09): 33 exact keys, 6 float diagnostics and 1 provenance
  pattern. From the review's minor notes: the live-RECON md5 key is provenance, matched by pattern; the float_vs_exact
  errors take the delivered tests' 1e-13 bound and `d2_order5_lower_part` the test's 1e-15 window, since
  `exact_check.py` asserts neither; `module_md5` is exact.
- `docs/NUMERICS.md` starts with the C8(2) pins (HANDOFF, every file, POWER_PROTOCOL.md).
- `tests/check_vendored.py` (`--standalone`: A-ASM-1(a); default: also A-ASM-1(b), the input-manifest pins) and
  `tests/vendored_isolated.py` (a `git archive` export outside <PROJECT>, or `--in-place` on a cluster export; the
  vendored tests with and without `LRI_ROOT` at the HANDOFF's counts, `exact_check.py`, an open-audit hook, an
  unchanged export) are written in this step, as PLAN "On HANDOFF" requires when the HANDOFF precedes Stage 3.
- The HANDOFF arrived before Stage 2a completed (an early HANDOFF): `inputs/manifest.json` is unchanged here, and
  A-ASM-1(b) is deferred to G2a [R15].

## 2026-10-03: Stage 1 fixes, and Expanse as the development site (deviation U1)

- **Site deviation U1** (user decision of 2026-10-03, recorded in `LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`).
  - Symmetry's compute partitions have been down since 13:06 EDT. Development, validation and profiling compute
    therefore run on SDSC Expanse (account <ACCOUNT>) now. The package stays symmetry-ready; the final validation (J-VAL)
    and the smoke are repeated on symmetry once it is back.
  - Expanse sharing with C63d mirrors H7: during development at most 4 whole `compute` nodes per session at a time
    (normal QOS), the `shared` partition outside that cap, the two sessions together never above 22 running or 54
    submitted normal-QOS jobs of the whole account, and pilots or production only in an agreed window.
  - `slurm/env_expanse.sh`, installed as `~/c8d2/env_expanse.sh`: Spack GCC 13.3.0, Boost 1.77 headers by path
    (the boost modules set only `BOOST_ROOT`), Spack GMP 6.2.1, and a python/3.11.9 venv `~/c8d2/venv` (numpy 2.3.5,
    scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, pytest 9.1.1). Data live on Lustre under `$C8_DATA`.
  - `slurm/gen/expanse_{regress,build_l8,crossnode}.slurm` mirror the symmetry job scripts, which are unchanged:
    J-GEN-1 on `shared`, J-GEN-2 on one whole `compute` node (128 threads), and A-INV-4 as a rebuild on a second,
    different compute node at 64 threads. Every Expanse compute node is an AMD EPYC 7742, so on Expanse A-INV-4 is a
    node and thread-count check. The symmetry Intel run (J-GEN-3) adds the architecture check later.
  - Evidence goes to `benchmarks/expanse_2026-10-c8/`, in the layout of `benchmarks/symmetry_2026-10-c8/`.
- **Fix: the free rate line** (found by the independent Stage-1 verifier, 2026-10-03).
  - `gen/build_free.cpp` wrote the parity-rule rate line with a trailing space. The frozen free L7 files, which were
    rated with the same rule, have none. A-INV-2 requires all 2,441 free L7 G-files byte-identical, rate lines
    included, and A-IN-3 an L7 payload byte-identical to the reference files.
  - The free builder now joins the rate tokens with single spaces and writes no trailing space, which is exactly the
    frozen free L7 format. The power builder is unchanged: its frozen files keep the C7(2) builder's trailing space.
  - `gen/regress.py` counts the free L3–L6 rate lines that differ only in that trailing space separately
    (`rate_whitespace_only`).
- **Fix: a byte-exact checksum hierarchy** (same verifier) [A-INV-5, R02].
  - `gen/verify_inventory.py` hashed SHA256SUMS after a universal-newline text read. A newline turned into CR, or CRLF
    line ends, therefore passed step 2.
  - It now hashes and parses both checksum lists from their exact bytes: UTF-8, one LF per row, no control
    character. `gen/publish_inventory.py` writes MEMBERS.sha256, SHA256SUMS and MANIFEST.json as bytes.
  - `gen/test_verify_inventory.py` adds six newline mutations (25 checks). Five of them pass the previous verifier,
    which is the negative control.
- The symmetry chain 569661–569664 (export of fd8532e) stays queued, as the user asked. It runs the generator without
  these two fixes: its J-GEN-1 would fail A-INV-2 on the free L7 rate lines, and its tree would differ from the one
  built here in every free rate line. A symmetry repetition needs an export of this commit or a later one.

## 2026-10-03: Stage 1, the d=2 payload generator (component A)

- `gen/c8gen.hpp` (new): `Key = unsigned __int128`, the checked decimal `readu128`/`parse_u128` (refuses an empty
  token, a non-digit and overflow beyond 2^128, naming the token), `u128s`, `NV = 9`, `NP = 36` with
  `static_assert(2*NP <= 128)`, and `read_classes` (header `n NG` with 1 <= n <= 9, exactly NG rows of exactly
  `key aut orbit`, keys within the 2n(n-1)/2 bits of an n-vertex class, no trailing tokens; errors name the file,
  the row and the token) [A-INV-1].
- `gen/build_free.cpp`, `gen/build_power.cpp`: the reference builders with only the planned hunks: key type,
  reader, `"key"` printed by `u128s`, `deg[NV]`, `p[NV]`, `num_threads(4)` removed (OpenMP default), and in the free
  builder the parity rate floor `max(|S| odd ? 1 : 2, twice[s])*.5L` of the power builder. One optional output is
  added for gate A-INV-3(b): with a third argument the builder writes its subgraph classification (id, key, aut,
  orbit, D_G, s_G, log and power vertex masks in order) in C8(1)'s `L*_inventory.txt` format. G-files and
  `inventory.json` are unchanged.
- `gen/check_edge_forests.cpp`: the same hunks plus `adj[NV]`, `seen[NV]`, `low[NV]` and the vertex loop bound.
- `gen/Makefile` (`make -C gen` into `bin/gen/`, the frozen kernels' flags `-O3 -std=c++17 -fopenmp
  -fno-fast-math -ffp-contract=off`, a `<exe>.build.txt` record per binary), `gen/test_keys.cpp` and
  `gen/test_keys.py` [A-INV-1].
- Gate scripts: `gen/regress.py` (L3-L7 regression with `--explain` and the legacy-relabelling diagnosis)
  [A-INV-2]; `gen/gates.py` (A-INV-3 (a)-(k) with L7 controls); `gen/kirchhoff.py` (port of
  `validate_kirchhoff.py`: paths as arguments, `range(3,9)`, the A-INV-3(h) sample with seed 8812, a process pool;
  the exact arithmetic unchanged); `gen/coverage.py` (port: the s_G = 4 rule only at L = 8, every class assigned
  once, selection lists); `gen/forest_counts.py` (new, independent: compatible log-subgraph families from C8(1)'s
  masks) [A-INV-3].
- Publication: `gen/publish_inventory.py` (the acyclic checksum hierarchy payload -> `MEMBERS.sha256` ->
  `SHA256SUMS` -> `MANIFEST.json`, atomic publication by one rename that refuses an existing target, verified
  copies, and the member listing for the cross-node check), `gen/verify_inventory.py` (the four-step verification
  with `--pin`), `gen/test_verify_inventory.py` [A-INV-5, R02].
- Jobs: `gen/run_l8.sh` (build, gates, publication; `set -euo pipefail`, every step in the foreground) with
  `gen/test_run_l8.py` (an injected failing gate stops it before publication) [A-INV-1];
  `slurm/gen/regress.slurm` (J-GEN-1), `slurm/gen/build_l8.slurm` (J-GEN-2), `slurm/gen/crossnode.slurm` (J-GEN-3).
- H1: `gen/handoff_inventory.py` writes `LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json` (MANIFEST.json
  sha256 and md5, date, gate summary with evidence, the D4 pipeline statement, the checksum hierarchy, the r2
  procedure, empty fields for C63d's pin and gates 1-7) and refuses unless every published copy verifies against the
  pin, every A-INV record is green, a refused second publication is recorded and DECISIONS.md logs C63d's C1
  acknowledgment; `gen/test_handoff_inventory.py` [A-INV-5].

## 2026-10-03: Stage 0, repository and review base

- Clone of `LRI_C7_D2_HPC@a55958f` (tag `c8-base`), branch `c8`; the `origin` remote is removed, so commits stay
  local [A-PKG-3].
- Review base `c8-rb` (60fef98): the C7(2) package plus verbatim external sources and data, every file a byte
  copy of its pinned source: `reference/c8d1_inputs8/` (LRI_C8_HPC@78e6a8a), `reference/c7d2_hpc_a55958f/`,
  `reference/c7d2_production_2026/`, `reference/SHA256SUMS_c8`, and the sources to be ported at their new paths
  (`gen/build_free.cpp`, `gen/build_power.cpp`, `gen/check_edge_forests.cpp`, `gen/kirchhoff.py`,
  `gen/coverage.py`, `gen/zero_dim_check.py`, `tools/lanes.py`, `slurm/lane_worker.sh`, `tools/design.py`,
  `tools/combine.py`, `tests/test_pipeline.py`).
- `gen/SOURCES.json` records every source pin (repository, commit, path, sha256, bytes); `gen/check_sources.py`
  verifies the reference copies, `reference/SHA256SUMS_c8`, the port copies in `c8-rb` and, with `--origins`,
  the originals [G0].
- `README.md` restarted for C8(2); the C7(2) README is kept as `docs/c7_historical/README_C7.md`.

# C7(2) history (unchanged)

## 2026-10-02: review fixes and the C6 job-handling layer (on top of fb64c47)

Acts on the review of 2026-09-30 (`LRI_C7_D2_HPC_review/REVIEW.md`, findings M1-M4
and L1-L21) under the plan `LRI_C7_D2_HPC_loop/PLAN.md`. Identifiers in brackets
are the plan's acceptance criteria.

**Unchanged:** the integrand; both precision tiers, thresholds and backends; the
Sobol/digital-shift stream for a given (seed, net, layout, rate); the default
frozen allocation; the fixed-point assembly; the campaign weights; the native
`--describe` output and schema `c7-d2-hpc-native-1`. No physical C7(2) value is
produced or changed. Campaigns planned by the delivered tools (schema
`c7-d2-production-1`, e.g. the 2026-09-30 symmetry production) are handled only
by a checkout of `fb64c47`; this revision refuses them with that advice [D7].

### Native code
- `src/kernel.hpp:144`: `exponential(T(T(logx[j])-T(shift)/g.L))`, so
  `exponential<T>` is never instantiated on a Boost expression template (L18)
  [A-L18]. Only `src/` change. Validated: Boost 1.77 builds of both backends are
  byte-identical to `fb64c47` and to the 2026 production binaries (symmetry job
  567518) [D1].
- **Correction (host finding H1).** The 2026 compile failure that L18 and A-L18
  attribute to Boost 1.86 came from the system **Boost 1.66**: Expanse's
  `boost/1.86.0` module sets only `BOOST_ROOT`, not `CPATH`. Measured: with real
  Boost 1.86 headers both `fb64c47` and this revision compile (Expanse GCC 13.3,
  jobs 54583692/54583699; symmetry GCC 11.4, job 567518); with Boost 1.66
  `fb64c47` fails and this revision compiles. A-L18's acceptance text ("the
  original fails with Boost 1.86 under GCC 11.4") rested on that misattribution
  and cannot hold; the hunk is kept for Boost 1.66 compatibility, and the docs
  and `slurm/env.sh.example` now say how to check which Boost a build sees
  (`BOOST_LIB_VERSION` in `bin/*.build.json`; `CPATH=$BOOST_ROOT/include`).

### Build (L17, L13, L21)
- Makefile: `OPTFLAGS ?= -O3`, `CPPFLAGS`/`CXXFLAGS`/`LDFLAGS`/`LDLIBS` hooks; the
  numerical flags (`C7_REQUIRED`) and the compile commands are `override`
  variables, so the command line cannot drop them; default settings give the
  delivered compile commands; `.DELETE_ON_ERROR` removes an executable whose
  build-record step failed. Rebuilds when the Makefile changes; `test` now runs
  validate, unit_orchestration, check_inputs, workflow and staging; `test-python`
  added [A-L17].
- `tools/build_record.py`: `make` writes `bin/<exe>.build.json` from the exact
  compile command it ran (passed as arguments): compiler, the make flag variables,
  `BOOST_LIB_VERSION` and GMP version probed with the command's own flags,
  `__OPTIMIZE__` (unoptimized builds warn and record `optimized: false`), whether
  every required flag is present, sha256; `plan` records it and refuses a stale one
  (advice: `make clean && make` or `make -B`) [A-L13, A-L17].
- `tools/common.py`: Python >= 3.10 check (also in every Slurm script) [A-L21];
  `cxx_command` shared by `check_points.py`, `benchmark.py`, `profile.py` and
  `validate.py` [A-L17]; host and library fingerprint [A-L13].

### Integrity (M1-related L10, L15, L16)
- Job-private runtime: `run` copies the executable, `gamma_d2_7.txt` and the net
  into a mode-0700 `mkdtemp` (`--scratch`, `SLURM_TMPDIR`, `TMPDIR`, `/tmp`),
  stages graph members per block from the pack, verifies every copy, runs only
  the copies and removes the directory also after errors. Checkpoints record
  `runtime = {executable_sha256, inputs_manifest_sha256, net_sha256,
  fingerprint}`; run-skip and merge reject mismatches. `merge` and `assemble` no
  longer need `bin/` (L10, L15) [A-M1].
- `plan` verifies every file listed in `inputs/manifest.json`, the ten packs
  included, before creating anything (L16) [A-L16].

### Allocation (M1, M3; opt-in, D2)
- `--power-divisor K`: power counts `max(4, points x M x P / K)`; refusal names
  the strata that would fall below 4; the manifest records K; `plan` prints the
  projected core-hour change [A-M1alloc].
- `--primitive-allocation {uniform,neyman}` (default uniform):
  `tools/primitive_allocation.py` builds `inputs/primitive_allocation_c7d2.json`
  from the archived primitiveA/B records (per-class SD of the linearized C7
  contribution, seconds per point); Neyman counts are powers of two for the
  uniform point budget; budgets below primitive_points x M = 64 are refused
  before anything is created; `--points` still overrides; retained mode ignores
  it with a warning; `plan` prints the projected primitive-block SE of the counts
  it uses and of the other allocation at the same budget, labelled hypothetical
  [A-M3].
- Measured 2026 production shares (power 59.9% of task CPU for 0.76% of
  Var(C7); primitives 14.4% for 7.4e-5) and MC-scaling projections, including the
  plan's recipe `--power-divisor 16 --primitive-allocation neyman` (SE x
  sqrt(core-hours) 33.8 against 49.5) and the recommended
  `--power-divisor 16 --primitive-allocation neyman --primitive-points 512`
  (28.5: one third of the core-hours for the same SE; the primitive saving comes
  from the smaller budget, Neyman adds under 1%), in README and `docs/HPC.md`;
  derivation `benchmarks/symmetry_2026-10/production_shares.py` [A-ALLOC-DOC].

### Throughput (M4, L4)
- Frozen per-shard order `pos` (estimated cost descending, then uid); blocks are
  consecutive `pos` ranges; default `--checkpoint-tasks 512`; `plan` and `run`
  refuse threads > checkpoint_tasks and warn below 16 x threads [A-M4].
- `--shards N` for the most expensive group, others in proportion to estimated
  core-seconds (`--shard-policy uniform` kept); estimates per group and in total,
  the largest shard's wall time and a suggested `--time`; proxy path with
  `tools/calibration.json` (gmp rows from the 2026 production's 64-thread AMD
  lanes on EPYC 7532 and 7543 nodes; decimal rows from symmetry job 567667 on an
  EPYC 7543 node, with the backend ratio checked on matched hardware by job 567730;
  every row with job ids, hosts, threads and CPU models) or measured path with
  `--cost-model` (validated in full before anything is created); a
  missing row gives `estimate: unavailable`; zero-task groups get no jobs [A-L4].
- `tools/calibrate.py`: derives and merges calibration rows from a finished
  campaign; refuses a selection that misses any (sector, L) of the run, and drops
  a backend's `unavailable` note only when all its rows are filled.
- Measured block throughput (symmetry job 567668, five L7 shards, 64 threads,
  1024-task blocks): busy cores 0.909-0.947 (target >= 0.80), OpenMP efficiency
  0.956-0.968 [A-M4].

### Operations (L1-L3, L11, L12)
- Resumable, fail-closed merge: valid `merged.json` skipped, invalid never
  overwritten, concurrent publication accepted only if canonically identical;
  idempotent `C7_result.json` (L1) [A-L1].
- `production.py status` (`--json`, `--exclude`, `--max-array`), `tag`, `recover`,
  `check-sbatch-args`; `tools/slurm_submit.py` behind `slurm/submit.sh`,
  `slurm/resubmit.sh` and the status lines: allowlists, cluster-selector refusal,
  environment filtering, no shell splicing, offsets, positive limits, the campaign
  lock (exit 75), a queue snapshot before every submission so no entry point
  duplicates live work (65/69), skipping of committed indices (L2) [A-L2].
- `C7_TIME_POLICY` `finite` (default) or `unlimited` (`--time=0` last, other
  `--time` refused, `TimeLimit=UNLIMITED` verified, exit 70) [A-TIME].
- `slurm/run_array.sh`/`merge.sh`: `--nodes=1 --ntasks=1`, commented site options,
  `set -eo pipefail` before `C7_ENV_SETUP` then `set -u`, Python check,
  `C7_INDEX_OFFSET`, OMP exports, scratch; arrays <= `C7_MAX_ARRAY` with an
  `afterok` merge; `slurm/env.sh.example` for symmetry and an Expanse-type stack;
  no node-local `C7_RUN` in the docs (L3) [A-L3].
- Read-only SQLite opens via a percent-encoded `file:` URI (L11) [A-URI]; `%` in
  the campaign path escaped in Slurm `--output` patterns [A-PCT].
- A run that finds its block already published logs `verified duplicate` (L12)
  [A-L12]. `run` without `--index` outside a Slurm array refuses.
- `run --max-blocks N` (commit at most N new blocks, then stop) and `status --all`
  (also list complete indices) are new. `status` (and `--json`) report pinned
  tools that changed since planning, and every Slurm submission then refuses (64),
  because the work and merge jobs would refuse them.
- Published files (checkpoints, merged records, results, manifests, CSV tables)
  now get mode 0666 minus the umask (0644 under umask 022) instead of
  `mkstemp`'s 0600: readable by other users of a shared filesystem unless the
  umask is stricter.

### Seeds and pinned tools (L8, L9)
- Per-group seeds from SHA-256 of (seed, campaign, sector, L, role), domain
  `c7-d2`, by default; `--seed-scheme legacy` is the delivered arithmetic and
  refuses archived seeds, the 2026 seeds and every base that would reuse their
  shift or net seeds; docs use a placeholder seed (L8) [D6].
- `merge` and `assemble` refuse a changed pinned tool unless
  `--accept-tool-change`, which records planned and current hashes (L9) [D10].

### Reporting (M2, L19)
- Lower-order checks with estimate, SE, reference, reference SE and pull from
  both SEs; C6 against the C6(2) production 362.36647176375726 +/-
  0.0007997306822612242 with the archived 362.3489 +/- 0.153 as a secondary
  entry; null tests of `power_differences[3..6]`; `assemble.py` prints all pulls
  and flags |pull| > 3 as a diagnostic (M2) [A-M2].
- `--test-graphs` results go to `C7_test_result.json` with every physical key null
  and the partial values under `test_partial` (L19) [A-L19].
- `assemble.combine` is the pure assembly; applied to the 2026 production's
  merged batches it reproduces its `C7_result.json` to 7.3e-16 relative
  [A-COMPAT].

### Sobol export check (L5)
- 60-bit campaign-b nets documented. `make_net` checks every reachable direction
  column (m = ceil(log2 max count)): public-API points (at most 2^16), a fresh
  identically seeded engine compared with the bytes read back from the file, and
  a SciPy-independent GF(2) rank check; no `fast_forward`; a 2^40-point stratum
  checks in about 1.6 s [A-L5].

### Tests and records (L6, L7, L14)
- `tests/validate.py`: distinct fresh output per executable, row/jet/identity
  checks, exact equality for decimal and for gmp rows with mp = 0, <= 1e-30 for gmp
  rows with mp > 0 [A-L6]; thread and split checks for every backend [A-L14].
- `tests/unit_orchestration.py` with `tests/fake_worker.py` and fake
  squeue/sbatch/scontrol; `tests/check_inputs.py`; `tests/compat_2026.py`;
  `tests/fixtures/production_nets` (archived 2026 nets); `workflow.py` and
  `staging.py` for every backend, with URI-reserved paths and a zero-task group.
- Tests and tools write records only to `--output` or temporary directories; the
  records carry host, compiler and flags, `--describe` and executable hashes
  [A-L7].

### Package
- Schemas `c7-d2-production-2`, `c7-d2-group-2`, `c7-d2-hpc-result-2` [D7].
- `tools/verify_delivery.py --write` regenerates `DELIVERY_MANIFEST.json` and
  `SHA256SUMS` over every git-tracked file as it is on disk (run it right after
  `git add -A`); `--strict` ignores build outputs and caches
  [A-PKG]. `.gitignore` added. `reference/` unchanged.

### Cluster validation (`benchmarks/symmetry_2026-10/`, commit 572a956)
- Symmetry job 567518: D1 byte identity; `make test`; `make test-full` (3,511
  kernels, both backends, exact gate; all 1,814 gmp rows with mp > 0 identical);
  `--strict`. Real-Slurm drills 1-4 (smoke, recovery, lock, status line), drill 5
  (decimal calibration, job 567667) and drill 6 (throughput, job 567668).
  Expanse jobs 54583692/54583699: the Boost versions (H1 above).

### Fix round 1 (host review HR1-HR16, HR18, HR26 and host finding H1)
- Tests no longer depend on the shipped decimal calibration being empty: the
  unavailable path runs against an edited copy, and shipped rows must be null or
  fully sourced (HR1). Status reports and Slurm submission refuse changed pinned
  tools (HR2). `override` compile commands, exact command in the build record,
  `.DELETE_ON_ERROR` (HR3, HR4). `calibrate.py` selection guard and test (HR11).
  New tests: largest-shard wall time and suggested `--time` (HR12); `build_record.py`
  optimized true/false and required flags, node fingerprint contents on Linux in
  `workflow.py` (HR13); checkpoint block contents by `pos` and the 512 default
  (HR14); merge `afterok` lists the new arrays and live tasks (HR18); the Sobol-period
  refusal now precedes the campaign directory (HR26, with a test).
- Docs: measured primitive variance share and the projection table (HR5, HR6);
  the kept `SBATCH_*` variables (HR7); `--max-blocks`, `status --all`, file modes
  (HR8); Boost wording (HR9, H1); historical verification records marked in the
  manifest (HR10); only `_sv` is exported, the shift is native (HR15); C3-C5 are
  the archived 13-digit values, which differ from longer evaluations by up to
  1.8e-12 (HR16); decimal calibration and throughput numbers.

### Fix round 2 (Codex inspection 1, R1-R5)
- R1: `LDFLAGS`/`LDLIBS` follow the required numerical flags in the compile-and-link command, so they now accept
  only link words (`-L*`, `-l*`, `-Wl,*`, `-pthread`, `-static*`, `-rdynamic`, `-fuse-ld=*`, `*.a`, `*.so`, `*.o`);
  anything else stops `make` (and `common.cxx_command`) with a message. `build_record.py` probes every compiler option
  of the actual command, wherever it sits (all words but the source, `-o` and link words), and
  `required_flags_present` also requires `-ffp-contract=off`/`-fno-fast-math` to be the last of their kind,
  `_OPENMP` defined and no `__FAST_MATH__`/`__FINITE_MATH_ONLY__`. Default compile lines unchanged.
- R2: `production.py run` handles SIGTERM, SIGINT and SIGHUP: it terminates and reaps the native child, removes the
  job-private runtime and exits 128+signal (143 for TERM); checkpoints publish atomically, so the interrupted block
  is redone by the next run. `slurm/run_array.sh` runs Python in the background, forwards TERM/INT/HUP to it and
  removes its staging directory; SIGKILL, node failure and an expired KillWait cannot be cleaned up (documented).
- R3: the manifest's primitive record, the plan output and the projections follow the counts really used:
  `--points` gives a budget of 44 x points x multiplier and the SE of those counts, with no Neyman comparison; a
  uniform or Neyman plan records its budget, the actual points per replicate, the projected SE of its counts and the
  other allocation at the same budget, labelled hypothetical.
- R4: `--cost-model` is validated in full whenever it is given (type, schema, dimension, order, backend, a non-empty
  map of `sector:L:graph` keys to positive finite seconds); one validated flag drives every later decision.
- R5: CPU attributions corrected (<NODE>-<NODE> and <NODE> are AMD EPYC 7532; <NODE>-<NODE>, including <NODE> of the
  decimal calibration and <NODE> of validation job 567518, are AMD EPYC 7543); `tools/calibration.json` notes and new
  `cpu_models` fields (numbers unchanged); `calibrate.py` records the fingerprints' CPU models per row; the backend
  ratio now comes from matched hardware (job 567730, `benchmarks/symmetry_2026-10/backend_ratio/`).

### Fix round 3 (Codex inspection 2, IR2-01 and IR2-02)
- IR2-01: the queue snapshot (and the lock's owner record) use the account of the process's real uid
  (`pwd.getpwuid(os.getuid())`, the identity sbatch submits under; the numeric uid if it has no passwd entry), never
  `USER`, `LOGNAME` or `getpass`. The fake-Slurm suite now runs with `USER`/`LOGNAME` naming another valid account,
  its fake `squeue` really filters by `-u`, and the tests assert the queried account and that live jobs still stop
  duplicate submissions.
- IR2-02: launching a native worker and registering it are atomic with respect to TERM/INT/HUP: during the launch the
  handler only records the signal (blocking the signals would be inherited by the worker) and raises it once the
  worker is registered; `stop_children()` in `run`'s cleanup terminates and reaps every registered worker before the
  runtime is removed. `run_array.sh`'s `on_signal` stops every background job (`jobs -p`), also one whose pid is not
  yet in `child`. Deterministic tests: TERM delivered right after the worker is created (test seam), and TERM to
  `run_array.sh` between the background launch and `child=$!` (with and without staging).

### Known limitations / deferred
- HR17: the concurrent-merge test does not force the publication collision; the different-content refusal is untested.
- HR19: the estimate-unit tests sum the planner's own cost column instead of recomputing it from the inventory or cost model.
- HR20: no test of a window that mixes committed and missing indices; the refusal-message checks are loose.
- HR21: the `C7_INDEX_OFFSET` unit check cannot detect an ignored offset (drill 4 covered it on symmetry).
- HR22: the thread-count restarts in `workflow.py`/`staging.py` recompute nothing (`validate.py` holds the real thread checks).
- HR23: the fresh-net Sobol test checks 20 columns and no full byte comparison for the ten planner shapes.
- HR25: one calibration rate per (sector, L) blends primitive and non-primitive free-L7 costs (estimates biased up to about 30%; documented).
- HR27: `verify_delivery --write` hashes the working tree, so it must follow `git add -A` with no unstaged edits.
- HR28: `run_array.sh` neither honours nor rejects the old `C7_ARRAY_OFFSET` (only direct sbatch use is affected).
- By plan: no per-loop multipliers, no L3-L5 control mode (L20, documented as a manual procedure), no per-block locks
  (A-L12), no production campaign.
