# Stage-6 fix round 3 on symmetry (2026-10-06): the new executables validated, the dd+mp256 gate, cost model and route (b) re-made

Site rule: symmetry only (user, 2026-10-05: "symmetry first"); Expanse, personal desktops were not
touched. Fix round 3 has one `src/` change (Z4: `load_graph`'s truncation checks; with Z3's compile-time refusal of
external `C8_NX_*` hooks, both in `src/kernel.hpp`), so every executable that compiles `load_graph` changed and the
full exact validation ran on the new executables (host note in `LRI_C8_D2_HPC_loop/artifacts/s6_fix3_dispositions.md`).

**Exports.** Everything ran from git-archive exports, each checked file by file (`setup/export_check_<sha12>.json`):
- **`997639178c1f`** = 9976391, the integration and docs commit (the four group merges, the cross-group fixes, these
  job scripts): 9,548 files equal to the archive in content and mode. Jobs 570533-570539.
- **`b58e9b6f4afd`** = b58e9b6, 9976391 plus a tests-only fix found by J-VAL-1 here (the hermetic fake toolchain of
  `tests/test_gmp_binding.py`, below): 9,560 files equal. Jobs 570540-570542. Its build (570540) gives every
  executable of 570533 byte for byte (the two sanitizer builds differ in 32 bytes each, the embedded export path and
  the GNU build-id, and are equal once both are normalized: `s3build.570540.0/sanitizer_vs_570533.json`), so the
  J-VAL-2/3, A-RPL-7, gate, sweep and re-freeze results of the first export hold for it.

The two L8 packs were re-hashed against each export's `inputs/manifest.json` (free `e5dd7271…`, power `3d77d0c4…`) and
hard-linked from `pkg/7a8aad783c31/inputs/packs` (`s3build.*/l8_packs.json`). The Codex round-3 worktrees
(`LRI_C8_D2_HPC_s6r3_{A..H}`) were not touched.

## The new executables (symmetry, Ubuntu GCC 11.4.0, Boost 1.77, GMP 6.2.1; job 570533, again 570540)

| Executable | sha256 now | a42cfb7's build (570514) | |
|---|---|---|---|
| `bin/c8d2_decimal` | **`a18ce425fbb81a0182e15f675a984c36ef9505ce8d90ffb2629590f08112f2bc`** | `619ddf7d…` | changed (Z4) |
| `bin/c8d2_gmp` | **`7741f733fb888fd40f4bce733e41c44c76a73640d350a725ffa85be928c5ef41`** | `2cc5e88e…` | changed |
| `bin/c8d2_gmp_dd+mp256` (`make gmp NUMERICS=dd,mp256`) | **`a46f3060a27f4d5e3af19023fc5bb67a7ca2dc6c4242e671ef4bdb9427254c8c`** | `d5df32ac…` | changed |
| `bin/c8d2_gmp_prof` | `3fb9e777ab09d8ca832e57281677ebdc50fcc8c442feb9b630135e5128977675` | `69e990c0…` | changed |
| `bin/c8d2_gmp_ratiohist` | `01aef195ee01f868d2a46b57274af36c9590f30b67d09ca47e082f528b4bebcb` | `4f4638a2…` | changed |
| `bin/c8d2_inspect` | `3836197913ea7d2a90dac9b70c0b57d7637c86bb922a35b367c265c0d1cf335a` | `10fe8133…` | changed |
| `bin/c8d2_quad_ranges` | `ffa7a1921e1797ef4b739d8aac857b64bcb341a29c8c851a86fea703ab7a1a45` | `f616b70b…` | changed |
| `bin/c8d2_interleave_probe` | `a68411110498d7858ebe715ea56d2196f75da4b49581c5fe7b8867b4ab703802` | `b0acd9fb…` | changed |
| `bin/c8d2_decimal_san`, `bin/c8d2_gmp_san` | `eb527ea0…`, `e7adff0e…` (570533; 570540: `91786e1c…`, `4683cba6…`, path and build-id only) | `c4013f99…`, `b0e5a786…` | changed |
| `bin/ref/c7d2_decimal`, `bin/ref/c7d2_gmp` (`make c7ref`) | `e696d7f3…`, `7e3c8c92…` | the same | **the plan's hashes** |
| `bin/c8d2_quad_differential` (only `quadfast.hpp`) | `1e7a8d34…` | the same | unchanged |

`make gmp NUMERICS=dd,mp256` leaves every default executable unchanged; `--describe` of the profile: numerics
`dd+mp256`, not diagnostic, no development option, no stub. **Every build record has `macro_overrides: []`** (Z3: the
compiler's own probe finds no `C8_*` macro or source switch beyond the Makefile's `-D` words), no parameter override,
`development: false`, the production builds `required_flags_present: true`, Boost 1_77 everywhere
(`s3build.570533.0/identity.json`). The Stage-3 baseline (`c121b1e6…`/`23624153…`, built from tag c8-stage3 in
`pkg/b4273c59e911` by job 570026) and a42cfb7's default build (`619ddf7d…`/`2cc5e88e…`, `pkg/a42cfb718e69`) were
byte-copied into `bin/baseline/` and `bin/prev/` after their sha256 were checked.

## Verdicts

| Step | Job | Verdict |
|---|---|---|
| Build and identity | 570533 (amddebugq <NODE>, 2:01) | **PASS** (the table above). |
| **Z4 on the real node** | 570533 | **PASS.** `tests/test_native_guards.py` with `C8_GUARDS_OLD_TREE=pkg/a42cfb718e69`: `loader`: the loaders of this commit and of a42cfb7 print **byte-identical `Graph` states** for 24 real G-files (the L=2 graph, and the heaviest and lightest kernel of each of the 12 (sector, L), **L8 included**, with x86's 80-bit long double), and all 42 truncations (3 files × 14 cases) are refused with `truncated graph: <path>` (the pattern-initialization part is skipped: GCC 11 has no `-ftrivial-auto-var-init`); `hooks`: 91 injections refused by `#error` in all 15 kernel units, and a42cfb7 accepting the finding's injection; `syntax`: every kernel unit with the Makefile's flags. `tests/validate.py --only bad_inputs`: 56 refusals, among them the **28 truncations** (14 through the worker, 14 through the inspector), each exit 2 with `truncated graph`. |
| **J-VAL-2** (`make test-full`) | 570535 (amdq <NODE>) | **PASS, exact.** `validate --full`: G-REF, G-C7 and G-JET on the L=2 graph and all 3,773 L3-L7 kernels (3,774), both backends, against `make c7ref` (`e696d7f3…`/`7e3c8c92…`): every rule exact (replay 74 s); invariance, inspector, class B (now through the Z1 snapshot binding), diagnostics; **450-digit point checks L3-L8** pass (max scaled error decimal300 1.8e-302, gmp350 2.1e-353), each tool compiled from a source snapshot in which its worker was rebuilt byte for byte (Z1, `source_binding.reproduction.reproduced` true for both); check_inputs, workflow, staging pass; executables unchanged. |
| **J-VAL-3, exact parts** | 570535 | **PASS.** `thread_identity.py`: rows identical at 1, 8, 16, 64 threads and 8 × 8 lanes, both backends, both sectors, every team observed (`team_sizes_verified`). `validate.py --bk8` (G-BK8): 400 kernels per sector at L7 and L8, decimal against gmp, 3,200 rows, max normalized difference of the mp rows 0, **equal field by field to Stage 5's 570029**. `forced_tiers.py --worker bin/c8d2_gmp` (A-RPL-5) through the Z1 binding (the worker reproduced from the snapshot in 4.7 s): status `passed`, coverage complete (free 29,284 binary128 / 3,541 MP, power 50,625 / 12,568, no doubling), gates a-c; `forced_tiers.py --check` exits 0 (Z2); the per-sector results **equal fix round 2's 570416 record** apart from timings and the binding. Not rerun: the L=2 control (statistical) and merge_scale (no kernel arithmetic changed). |
| **A-RPL-7 G-L8SELF** | 570535 | **PASS, exact.** `validate.py --l8self bin/baseline` (the symmetry Stage-3 baseline of tag c8-stage3): the L8 sweep sample, 1,600 free + 400 power kernels × 2 × 512 points, both backends: every scientific field exact (762,395 / 359,972 binary128 points, 114,648 / 99,884 MP points; the same counts as 570029). |
| **Extra: against a42cfb7's build** | 570535 | **PASS, exact.** The same comparison with `bin/prev` (`619ddf7d…`/`2cc5e88e…`): every scientific field exact on both backends. So Z4 leaves every valid input's output unchanged bit for bit. |
| **J-VAL-1** (`make test`) | 570534 (failed), **570541** (amdq <NODE>, 22:31) | **PASS on b58e9b6.** The first run (export 997639178c1f) stopped in `make test-python` at `tests/test_gmp_binding.py` `source_binding`: symmetry's `env.sh` puts the Boost 1.77 module on `CPATH`, which the test's fake toolchain inherited, so its fake worker was built against the host's Boost and the expected refusal text (`'107400' for the worker`) did not match (`'107700'`): a test-portability defect (`../../mac_2026-10-c8/s6fix3int/`, "hermetic"). Everything that ran before it passed (validate 52 tests with the Z4 truncations; unit_orchestration 67 groups / 79 tests on Linux with the real worker; test_pipeline 35; ast_scan 0 findings; test_regress 97; check_vendored 35; check_inputs 22; test_profiling 19; test_gmp_prefix 8); `make test` stopped there, so test_omp_launch, test_numerics_flags, test_dd_profile, the sanitize capture check, test_native_guards, workflow and staging had not run. After the fix (b58e9b6, `World.env` drops inherited include-path variables), 570541: **`make test` exit 0 as one command** (1,305 s): validate 52, unit_orchestration 79 tests / 0 failed, test_pipeline 35, ast_scan 0 findings (tools 27 files, gen+tests 47), test_regress 97/97, test_handoff_inventory 17, merge_scale, check_vendored 35/35, vendored_isolated 10/10, the delivery-verifier test, check_inputs 22/22, test_profiling 19, test_gmp_prefix 8, **test_gmp_binding 14**, test_omp_launch 5, **test_numerics_flags 12**, test_dd_profile 8, sanitize capture, **test_native_guards 3/3**, workflow 2, staging 2; then `assembly_checks --exact` 37/37 (`assembly_checks.json`), **verify_result_tamper 206/206** (Z8), **combine_core 14/14**, compat_2026 (max relative difference 0.0); executables unchanged; the A-RPL-6 invariance with hostile inherited OpenMP controls: 24 rows, every team observed (`teams.json`). |
| **J-VAL-4** (A-KER-4, sanitizers) | 570542 (sharedq <NODE>, 22:03) | **PASS.** Stage 5's `stage5/scripts/s5val4.slurm` from the export of b58e9b6 (`make -q` finds the sanitizer builds current): `tests/sanitize.py --selftest`: all 144 ASan/UBSan/`_GLIBCXX_ASSERTIONS` worker runs (the new `load_graph` code included) and both point-check tools clean, the three self-test probes abort with their own reports (on a pty), and the capture check sees the report under a pty only, as designed. Not required by this round's task, run because `src/` changed. |
| **J-GEN-1** (`slurm/gen/regress.slurm`) | 570537 (sharedq <NODE>, 4:37) | **PASS.** `gen/test_keys.py` 115/115, `test_regress` 97/97 (Z5's 7 new checks of `check_gfile`), `test_run_l8`, `test_verify_inventory`, `test_handoff_inventory`, `check_sources`; A-INV-2 at L3-L7 with 1 and 8 threads: free L3-L6 rate-line files only, free L7 and power L3-L7 identical (`gen1.570537.0/`). |
| **The `dd+mp256` J-FLAG gate** on the new profile build | 570536 (amdq <NODE>, 14:03) | **PASS; `design.check_gate` accepts the record** (in the job and on the Mac). Details below. |
| **The `dd+mp256` profile cost sweep**, re-measured | 570538 (amdq <NODE>, 7:28) | **PASS.** The model of the new build: 48,346 keys, numerics `dd+mp256`, executable `a46f3060…`; installed as `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (sha256 **`18e50440…`**). Details below. |
| **Route-(b) re-freeze** with the new gate and model | 570539 (sharedq <NODE>, 33:52) | **PASS.** Four freezes and their test-only plans; every SE at its target, every cap holds. Details below. |

## The `dd+mp256` J-FLAG gate (job 570536)

One whole amdq node (<NODE>, 2 × EPYC 7543, 64 cores, 8 NUMA nodes); `tests/numerics_flags.py --profile dd+mp256
--seeds-log $C8_SEEDS` at full scale (`scripts/s3flag.slurm`), the exact binary `7741f733…` and the profile `a46f3060…`
checked before and after. Wall 841 s. Record `s3flag.570536.0/jflag_dd+mp256/numerics_flags.json`, sha256
**`a8de403771f75f42f63964d027b8254f4af76db82f066219b438794b04f7c3da`** (`check_gate.json`).
- **Status `"passed"`**, verdicts F1, F2, F4 rows, F5 true, no development option.
- **X1 coverage:** complete; binary128-accepted / MP points free 29,284 / 3,541, power 50,625 / 12,568 (the need met
  without doubling), every point evaluated by the profile.
- **X2 binding:** a fresh F1 baseline; both executables rebuilt in the read-only source snapshot (`f0c7137e…`) from
  their build records' commands reproduce `7741f733…` and `a46f3060…` byte for byte (5 s each); the F1 tools compiled there.
- **X3 teams:** F5's observed teams equal the requests in every run and lane (`team_sizes_verified: true`).
- **Z19 libgmp provenance (new):** `f1_baseline.reused` false, the baseline's `tool_gmp_library` and the profile's
  `F1.tool_gmp_library` each matched (tool and executable now) to the libgmp `4dc20a90…` both build records name;
  `check_gate` returns `gmp_library` {exact `4dc20a90…`, profile `4dc20a90…`, reused false}.
- **Same numbers as 570373 (and 570210):** F1's verdict and coverage, F2's totals (|dC8| + 3 SE_d = 4.25e-16: dC8
  1.3129e-16, SE_d 9.774e-17, resolved) and per-task statistics, F3's tiers and promotion counters are **equal field
  by field**; only F3's task timings differ (`vs_570373.json`). F4: ×2.517 (free ×2.477, power ×2.620) against
  570373's ×2.539 (timing only); the **exact path's** F4 median 1,335.6 lane-thread s against 570373's 1,325.4 (+0.8%,
  another node): Z4's load-time checks do not change the exact worker's speed, so the exact symmetry cost model
  `cost_models/gmp_symmetry_amd_c8.json` (J-SWEEP-2, `a1b6e5d2…`) stays valid (`production.load_cost_model` binds the
  numerics, backend and rates identity, not the executable, so nothing refuses it either).
- **Seeds:** F2's 49 seeds (base 820262401) were all present in symmetry's log ("0 added, 49 present").

## The profile cost model (job 570538) and its install (570539)

J-SWEEP-2's shape on the new profile build (`scripts/s3sweep.slurm`, template `pre6/scripts/p6sweep.slurm`):
`slurm/sweep.sh … --points 512 --replicates 2 --threads 8 --cost-model <J-SWEEP-1's model> --numerics dd+mp256
--approved-numerics-change "<the 2026-10-05 approval>" --merge-jobs 32`, fresh seed 7431507595541975415, one whole amdq
node (<NODE>; 570240 ran on <NODE>), 24 indices, 96,692 tasks; wall 7:28; `accounting.py` complete (7.96 allocated
core-hours, η_node 0.257). Model: 48,346 keys, numerics `dd+mp256`, executable `a46f3060…`, AMD EPYC 7543.
Installed by 570539 with only its `note` extended by the approval and the gate (every other field checked equal;
`s3des.570539.0/cost_model_install.json`): **`cost_models/gmp_symmetry_amd_c8_dd+mp256.json` sha256
`18e50440e6496192fe4e2811b3e8aac56cd09ca9a9e923a9281b46074e0c7054`**, replacing `9b0dfec6…` (job 570240, build
`d5df32ac…`, whose bytes stay as the 570241 evidence copy `../pre6/p6des.570241.0/gmp_symmetry_amd_c8_dd+mp256.json`).
New over replaced, summed seconds per point: ×1.010 overall; L8 ×1.005-1.013, L7 ×0.988-0.994, the cheap L3-L6
groups ×0.91-1.26 (millisecond tasks: timing noise). Speedup over the exact model (`a1b6e5d2…`): ×2.785 overall (was
×2.814), free L8 ×2.719 (×2.754), power L8 ×2.944 (×2.965), free L7 ×2.796, power L7 ×3.483.

## The route-(b) re-freeze (570539)

sharedq <NODE> (8 CPUs, 15 GB), the export's own `bin/` (`7741f733…`, `a46f3060…`; checked first, with `check_gate`
on the new record). Inputs as 570379's: the J-SWEEP-2 sweep `sweep2-5d7586e9f1ab` (exact, all 24,173 graphs, η_node
from its ledger), the approval reference of 2026-10-05; the new profile model and the gate record 570536. Each bundle
was compared (`../pre6b/scripts/p6b_compare.py`) with 570379's bundle of the same target (old model `9b0dfec6…`, gate
570373). Lane core-hours at J-SMK-4's η_node 0.9146.

| Target | Route-(b) choice | SE (target) | Lane core-h (570379) | Design vs 570379 | Test-only plan: tasks / checkpoints / indices (570379) | Plan wall | Caps |
|---|---|---|---:|---|---|---|---|
| 1e-3 | re-optimized | 46.00 (46.00) | 639 (638) | r, K, η_node equal; counts and s differ (cost ×1.0008, SE ×1.0000004) | 2,135,296 / 8,372 / 71 (2,135,296 / 8,378 / 70) | 219 s | all hold |
| 5e-4 | exact design kept | 23.00 (23.00) | 2,251 (2,241) | counts, r, s, K equal; cost ×1.0044 | 5,356,096 / 21,035 / 205 (the same) | 563 s | all hold |
| 2.5e-4 | exact design kept | 11.50 (11.50) | 9,002 (8,963) | equal; cost ×1.0044 | 5,652,928 / 22,652 / 770 (5,652,416 / 22,513 / 767) | 535 s | all hold |
| 1.35e-4 | exact design kept | 6.21 (6.21) | 29,473 (29,328) | equal; cost ×1.0050 | 6,398,976 / 26,347 / 2,483 (6,395,520 / 26,191 / 2,470) | 648 s | all hold |

Every plan exits 0 with `numerics_route` route b, the gate `a8de4037…`, `executable_gated: true`,
`cost_model_numerics` `dd+mp256`, the bundle pinned in `<campaign>/design_bundle`; route (b) re-checks the bundle's gate
entry including fix round 3's `gmp_library`. All four plan directories were deleted. The bundles stay on BeeGFS in
`<SCRATCH>/c8d2/work/s3des-997639178c1f/bundles/` (`s3des.570539.0/bundles.tgz`, `bundles.sha256`); they
are test-only bundles of the sweep, as before. The production bundles are frozen from the pilot (`docs/DESIGN.md`,
"After the pilot") with the 570536 record as `--numerics-gate` and this cost model.

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1
thread per core; the Intel sharedq node: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on
amdq + amddebugq + amdpreq; the peak was 4 (570533-570536 at 06:27:54, three of them pending on the build; then
570534-570536 and 570538; `admission/h7_admission.jsonl`). Before the first submission: 14 idle amdq and 18 idle
amddebugq nodes, no live `c8d2-` job. C63d's `c8d3-*` jobs and the other <USER> jobs (`sri_eng_*`) were neither
counted nor touched. amdq/amddebugq with `--exclude=cn112`; no longq; sharedq `--no-requeue`; every job with `--mem`
and `--time` and a `c8d2-` name. Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/{997639178c1f,b58e9b6f4afd}/` (copied here without the six large files listed in
`large_files.sha256`: the F1 baseline's reference values, F2's rows, the sweep's raw model, whose installed form is
`cost_models/gmp_symmetry_amd_c8_dd+mp256.json`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570533 `c8d2-s3build` | build, identity, the Z4 checks (`scripts/s3build.slurm`) | amddebugq <NODE> | COMPLETED | 2:01 | 2.15 |
| 570534 `c8d2-s3val1` | J-VAL-1 on 997639178c1f (`scripts/s3val1.slurm`) | amdq <NODE> | FAILED 1:0 (the test defect above) | 21:27 | 22.88 |
| 570535 `c8d2-s3val23` | J-VAL-2, J-VAL-3's exact parts, A-RPL-7, the comparison with a42cfb7 (`scripts/s3val23.slurm`) | amdq <NODE> | COMPLETED | 16:13 | 17.30 |
| 570536 `c8d2-s3flag` | the `dd+mp256` J-FLAG gate (`scripts/s3flag.slurm`) | amdq <NODE> | COMPLETED | 14:03 | 14.99 |
| 570537 `c8d2-gen1-regress` | J-GEN-1 (`slurm/gen/regress.slurm` of the export) | sharedq <NODE> | COMPLETED | 4:37 | 0.31 |
| 570538 `c8d2-s3sweep` | the profile cost sweep (`scripts/s3sweep.slurm`) | amdq <NODE> | COMPLETED | 7:28 | 7.96 |
| 570539 `c8d2-s3des` | accounting, model install, 4 freezes, 4 test-only plans (`scripts/s3des.slurm`, afterok 570536 and 570538) | sharedq <NODE> | COMPLETED | 33:52 | 2.26 |
| 570540 `c8d2-s3build` | build of b58e9b6 (identical executables) | amddebugq <NODE> | COMPLETED | 2:00 | 2.13 |
| 570541 `c8d2-s3val1` | J-VAL-1 on b58e9b6 | amdq <NODE> | COMPLETED | 22:31 | 24.02 |
| 570542 `c8d2-s3val4` | J-VAL-4 (`stage5/scripts/s5val4.slurm` of the export) | sharedq <NODE> | COMPLETED | 22:03 | 1.47 |
| **total** | 10 records | | | | **95.47** |

Budget: 95.47 of this task's 220 core-hours. Symmetry's total in this workflow goes from 565.9 + 23.7 (s6res2) =
589.6 to 685.1 core-hours.

## Seeds

Five fresh seeds, drawn on the Mac (`secrets.randbits(63)`) and checked against the mirror (`setup/seed_precheck.txt`),
then in the jobs against symmetry's live log: 7431507595541975415 (the profile sweep, registered by `tools/sweep.py`
itself, Y13) and 8540795342523536361, 5408404967237961878, 5547428742305252863, 8750737914650074664 (the four
route-(b) test-only plans, added with labels after each plan). The gate added none.
- symmetry's log afterwards: 110 seeds (`seeds/s3_symmetry.json`, sha256 `7f19432f…`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (105 → 110, the same set;
  a second merge adds nothing; `seeds/sha256.txt`).
- Expanse's log does not hold them yet: they are appended to `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the
  next two-log sync (no Expanse session was opened, by the site rule).

## After the runs (the evidence commit)

- `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` replaced by the installed bytes (`18e50440…`); the docs name the new
  executables, the 570536 record and the model.
- `tests/test_gmp_binding.py` `forced_tiers_consumers` (the integration's Z2-consumer test) assumed that every stored
  `forced_tiers.json` predates Z1; this folder adds the first one made with the source binding
  (`s3val23.570535.0/forced_tiers.json`). The test now requires such a record to pass `forced_tiers.py --check`
  (complete with the binding) and every older one to fail it for the missing binding only (5 records). A tests-only
  change after the runs: J-VAL-1 (570541) ran the previous form, which did not see this record; the new form passes on
  the Mac (`../../mac_2026-10-c8/s6fix3int/`, the final suite).

## Files

`scripts/` (`s3.sh`: export, sub, upload; `s3build.slurm`, `s3val1.slurm`, `s3val23.slurm`, `s3flag.slurm`,
`s3sweep.slurm`, `s3des.slurm`), `setup/` (both export checks, the seed pre-check), `admission/` (the `squeue`
snapshots, the H7 lines, every sbatch), `logs/`, `sacct.txt`, `seeds/`, `large_files.sha256`, and one folder per run:
`s3build.570533.0/`, `s3val1.570534.0/` (the stopped run), `s3val23.570535.0/`, `s3flag.570536.0/`, `gen1.570537.0/`,
`s3sweep.570538.0/`, `s3des.570539.0/`, `s3build.570540.0/`, `s3val1.570541.0/`, `s5val4.570542.0/`.
