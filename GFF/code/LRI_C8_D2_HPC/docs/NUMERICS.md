# C8(2): vendored order-8 assembly and power protocol (H2/H3)

Added 2026-10-03 with the vendoring commit (PLAN.md "On HANDOFF", checklist step 10(i)). The C8(2) kernel and
orchestration sections below supersede the retained C7(2) contract at the end of this file where they differ.

- **Delivery.** C63d's `LRI_C8_shared/assembly/HANDOFF_assembly.json`, sha256
  `f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437` (md5 `b4bc3acf2f081abbed05a0dfcfa08568`, 2026-10-03), is the only delivery of the
  shared order-8 assembly. Its byte copy is `vendor/c8_assembly/HANDOFF_assembly.json`.
- **Review.** C62d's H2 review `LRI_C8_shared/inventory/reviews/order8_assembly_f5ff6a353371.json`: verdict ACCEPT_WITH_MINOR, with the step-0
  decision `accepted_documentation_only_minor_fixes` for this HANDOFF version only (the final verifier round reported
  'ready' and 'minor-fixes' on documentation citations, and README.md and POWER_PROTOCOL.md were then edited by hand;
  every code, data and test file is byte-identical to the verified copy).
- **Pins.** Every deliverable the HANDOFF lists is vendored under `vendor/c8_assembly/` at the sha256 the HANDOFF
  records (no other hash is a pin):

  | File | sha256 | Bytes |
  |---|---|---:|
  | `order8_assembly.py` | `2127196f2c712700617834bf157b881b802bd32d67e6a5c8dbb17b1425bc1d77` | 28,520 |
  | `exact_check.py` | `e41f244bc9759ed4c74533d97b8b76c9b31052b224bbeef710f81ea1d8f104ea` | 27,361 |
  | `exact_check_results.json` | `c3e802345f05e6d4d58d9d3c86baee79c62b42b82c06e939e10929476d1d8dae` | 4,770 |
  | `prepare_low8.py` | `6923c89a3d081d84f530f75a3d90fb43daac8c69e9984170155a062a6315bee6` | 14,914 |
  | `POWER_PROTOCOL.md` | `95e91d2c77988e6da5f9066e3a1dc829111b728e8e9cc676fab66601e7958244` | 13,450 |
  | `README.md` | `9d130000ec14997d66cfc9fcf5875b12789ad1dae8cfb2d5e59d4fdc20ba8ca5` | 54,951 |
  | `tests/test_order8_assembly.py` | `f65617da63567e4f1dbc8ee9b71c28624d3ced742e7ee9e271f2029e96f32561` | 41,471 |
  | `inputs_d3/two_loop.json` | `6c31bf7fcea49e1c16b52c82ca117502932a0f6a890e5d58b4846b3cb91fbffc` | 569 |
  | `inputs_d3/gamma_d3_8.txt` | `f868fbe27855ea0474e633e221629d5c5c1011b7dd07c2d6a4df6853b4b7293d` | 3,112 |
  | `inputs_d3/checks.json` | `e73f42e2a9036333fbb6aeeef34a07963bb368b2addb42dcf78a92c362783b7e` | 4,829 |
  | `inputs_d2_check/two_loop.json` | `565c388025a414746541040c34660c942a88e364c5fcf4fe8093927b100b00ad` | 640 |
  | `inputs_d2_check/gamma_d2_8.txt` | `2ace6971bdbcf13bf15c74311443a302fd971923633e91261323a1283128fefd` | 3,362 |
  | `inputs_d2_check/checks.json` | `16731d14c564b3019d3ed6a77f948e4d8d2d0d91a33f4aef321260bfa27df41b` | 5,199 |

- **Power-sector protocol (H3).** `vendor/c8_assembly/POWER_PROTOCOL.md`, sha256
  `95e91d2c77988e6da5f9066e3a1dc829111b728e8e9cc676fab66601e7958244`, is the registered reporting rule (D13). It was registered before any C8 data and
  is never changed after data are seen (its requirement PP10). The reporting requirements PP1-PP10 listed by the H2
  review (checklist step 6) are implemented by `tools/assemble.py` with one A-ASM-5 test each (Stage 2b).
- **LRI_ROOT fixtures.** `vendor/c8_assembly_fixtures/` holds 50 byte copies (555,995 bytes) of the
  external files the vendored tests and `exact_check.py` read through `LRI_ROOT`, each pinned in
  `tools/VENDORED.json` (reference checksum entry, git commit, or a sha256 recorded first).
- **Exact gate.** `tests/fixtures/exact_check_keys.json` classifies the 40 keys of `exact_check_results.json`: 33
  exact, 6 float diagnostics with bounds, 1 provenance pattern (R09).
- **Checks.** `tests/check_vendored.py --standalone` and `tests/vendored_isolated.py` (A-ASM-1(a)); after Stage 2a,
  `tests/check_vendored.py` also checks the pins in `inputs/manifest.json` (A-ASM-1(b)).
- **Use (Stage 2b).** `tools/assemble.py` imports the module only after its sha256 equals the pin. It delegates
  `campaign_moments`, `sector_assembly` and `power_null_rows` to the module, and adds the following.
  - Hard gates at the data means: the top-slot rule for L = 3..8, the loop-7 entry, and the float affinity of loops
    5..8. Each gate first asserts full loop coverage.
  - The POWER_PROTOCOL report PP1-PP10. This includes the package-side PP8 marker (a flag at order 6, or order 5 at
    d=2, must be investigated), and guards against non-finite inputs and nonpositive SEs.
  - The lower-order checks C3..C7 against D11, `error_by_loop` (variance contributions and shares), the two
    campaigns, the half streams, the bootstrap and the coverage guard.
  - `tools/combine.py` combines batches of one design through it, and `tools/verify_result.py` recomputes and compares
    a result. The tests are `tests/assembly_checks.py` (A-ASM-2/4/5, `--exact` for R09), `tests/compat_2026.py`
    (A-ASM-3), `tests/verify_result_tamper.py` (A-ASM-7) and `tests/combine_core.py`.
  - **Verification on any BLAS kernel family (F6, Stage 5).** The assembly's matrix products and `np.convolve` run
    in the BLAS kernels the machine selects (OpenBLAS DYNAMIC_ARCH: AVX2 on the AMD nodes, AVX-512 on the Intel login
    nodes), so rounding-level leaves differ between machines. `verify_result.py` compares the affinity gate's
    `linear_response_residual[k]` within 64 eps M_k, M_k = |C_k(m)| + |C_k(m+delta)| + sum_L |J_L||delta_L| (the
    magnitudes the residual is a difference of; the largest spread measured is 6.5 eps M_k over 13 Stage-5 results
    recomputed on the Mac, and 0.47 for the smoke on a Cascade Lake login node), and gives the power null checks the
    gates' 1e-2 scale floor (rounding-level values match to 1e-12, the protocol's ORDER3_ROUNDING). A result assembled
    on one machine therefore verifies on any other; real mismatches still fail (`tests/verify_result_tamper.py`).
  - **Types first, tolerances from designated fields (Y11, Stage-6 fix round 2).** `verify_result.py` checks every
    field's type before it recomputes anything (`schema_problems`: scope, hashes, backend, numerics, design, status
    and the like are strings, flags booleans, counts integers, objects where objects belong, every stored number
    finite and not a boolean, in vectors, campaigns, the bootstrap and `error_by_loop` too; test-only metadata
    included). A tolerance scale comes only from designated scientific fields: at a block root the coefficient family
    (`C<n>_full`, `power_free_C<n>`, `power_correction`), inside the gates, lower-order checks and power null checks
    their siblings, elsewhere the leaf's own magnitude, so a metadata field turned into a large number (scope = 1e30)
    can no longer widen the tolerance of a changed coefficient. The variance identity also requires Cauchy-Schwarz
    (|cov(power_free, power_correction)| ≤ power_free_se × power_correction_se, power_free_se ≥ 0).
    `tests/verify_result_tamper.py` has 104 cases (23 new, 19 of them accepted by the old verifier); every stored
    c8-d2 result verifies as before.
  - **Pulls (R3, Stage-6 residual).** A pull p = (x − r)/σ, σ = √(s² + t²) (a power null or top row's delta/se, a
    lower-order row's (estimate − reference)/√(sampling_se² + reference_se²)) amplifies a rounding-level difference of
    x by 1/σ, so the old fixed relative tolerance refused results from other machines: the Stage-5 design-chain partial
    failed on the Mac with a null row's pull 4e-10 relative apart while its delta was 3.6e-15 apart, well inside its
    own tolerance. A pull's tolerance is now what its inputs' tolerances τ_x, τ_s imply,
    τ_x/σ_min + |p| σ (1/σ_min − 1/σ_max) with σ_min, σ_max the extremes of σ over s ± τ_s (`pull_bound`, derived
    in the module docstring; a brute-force check covers it), and every stored pull must also be the pull of its own
    stored inputs to 1e-12 relative (`pull_problems`), so a pull changed alone is refused however small the change.
    `tests/verify_result_tamper.py`: 175 checks (71 new; the old verifier refused 22 consistent cross-machine cases),
    including the design-chain partial as a fourth cross-machine fixture; all 15 stored c8-d2 results verify on the
    Mac.
  - **The covariance is a covariance (Z8, Stage-6 fix round 3).** The copied covariance was checked only for its shape
    and finite entries: covariance[3][8] = 1e30 with covariance[8][3] unchanged was accepted. `covariance_problems`
    (run in `schema_problems`, before anything is recomputed) works in correlation units, with t_k = max(√max(c_kk, 0),
    √(EPS·D)) and D the largest variance, and requires symmetry |c_ij − c_ji| ≤ COV_REL t_i t_j, a nonnegative diagonal
    c_kk ≥ −COV_REL t_k², and positive semidefiniteness: the smallest eigenvalue of T⁻¹ ((C + Cᵀ)/2) T⁻¹ at least
    −m·COV_REL with m = 9; a matrix with no positive variance but a nonzero entry, and a correlation matrix that
    overflows, are refused. COV_REL = 1e-10 (REL's value); the largest asymmetry of the 16 stored results is 11.5 eps.
    The same class (`sign_problems`): `power_difference_errors`, every campaign's `sampling_se` and the bootstrap's
    `full_se`/`correction_se` must be ≥ 0, and every `error_by_loop` variance ≥ −REL·Var(C8). `combine.py` refuses a
    combined covariance that is asymmetric or indefinite. The CLI records the sha256 of the bytes it verified (read
    once). `tests/verify_result_tamper.py` 206 checks (31 new: the finding, a 1e-6 asymmetry, symmetric correlations
    0.9/0.9/−0.9, a covariance in a zero-variance row, a coordinated negative variance, the negative statistics; an
    element moved by 0.5·COV_REL accepted, by 2·COV_REL refused), `tests/combine_core.py` 14; every stored result
    verifies as before.

# C8(2) native kernel (Stage 3, PLAN.md component C)

Added 2026-10-03. The worker is `src/c8d2_integrate.cpp` (renamed from `src/c7d2_integrate.cpp` with `git mv`) with
`src/kernel.hpp`; the executables are `bin/c8d2_decimal` and `bin/c8d2_gmp` (macro `C8_USE_GMP`). The default
numerics are C7(2)'s precision policy bit for bit (D1); `numerical_change: false` for the default path.

- **One order fixes every size.** `kernel.hpp` holds `LMAX=8`, `ORDER_MIN=7`, `ORDER_MAX=8`, `EMAX=2*LMAX=16`,
  `KMAX=ORDER_MAX-2=6`, `NLOGS=KMAX+1=7`, `NVALUES=2*NLOGS=14`, `DIMMAX=4*LMAX-1=31`, `MAXMASKS=16384` and
  `MAXTERMS=10000`, with static_asserts (32-bit subset masks; layouts 0/1 read u[0..2E-2]; the jet widths; the scratch
  arrays). Every array is sized from them: `Scratch::{x,xs,lx,lt,order}` and `PromotedScratch<T>::{x,xs}` by EMAX, the
  jet (`sample()`, the gamma logs, the Kahan sums) by NLOGS, the output row by NVALUES, the Sobol point by DIMMAX, and
  `ld lx[EMAX]` in `tests/point_checks.cpp`. No literal C7(2) size (6, 12, 14, 28) remains in `src/` or in
  `tests/point_checks.cpp` (`tests/unit_orchestration.py::test_literal_sizes`, A-KER-1). The larger arrays only add
  storage.
- **Orders.** The task header is `C8D2TASKS1 <order> <L> <nt>` with order in [7, 8], 2 <= L <= order and
  1 <= nt <= 100,000; K = order - L. Order 7 replays C7(2) (loops 2-7, K = 7-L) and is compared bit for bit with the
  C7(2) binaries (`make c7ref`); order 8 is production (loops 3-8 and the L=2 control at K=6).
- **Gamma rows.** Rows l = 2..order labelled order-l, each `label norm logs[0..order-2]` (exactly order-1 log tokens:
  6 at order 7, 7 at order 8), then end of file. An order-8 task given `gamma_d2_7.txt`, or the reverse, fails the
  label check; a trailing token, a short row or data after the last row are refused. The order-7 file is the pinned
  C7(2) copy `reference/c7d2_hpc_a55958f/inputs/gamma_d2_7.txt`.
- **Runtime guards** (exit 2, each with its message): a graph with more than EMAX propagators (its L > 8; checked
  before E = 2L is formed), a task L outside [2, order], an order outside [7, 8], K outside [0, KMAX], a net dimension
  above DIMMAX, a rate outside (0, 1] or not a full decimal token.
- **Rates.** The rate argument is C7(2)'s decimal in (0, 1] or, for R7 only, `@FILE`: one `graph rate` line for
  exactly the graphs of the task file (a missing, extra or duplicate graph, a trailing token or a value outside (0, 1]
  is refused). The JSON then says `"rate":"file"` and echoes each row's rate. The scalar path and its output are
  unchanged.
- **Output** (`c8-d2-hpc-native-1`): C7(2)'s fields plus `"order"`, `"numerics":"exact"` and `"max_rss_kb"`
  (`getrusage` at exit); the row width is 2(order+1-L).
- **Class-B tail fields** (plan addition (ii), agreed with C63d; their definition is C63d's, LRI_C8_D3_HPC_loop/PLAN.md
  C.3). Per row, with t = v_0 * jac the weight-free base integrand value at a point (before norm, the weights and the
  regulator jet): `tail_top`, the 16 largest |t| of the row's points in descending order (fewer if the row has fewer
  points), `tail_sum`, the long-double sum of |t| in point order, and `tail_argmax`, the global point index of the
  first largest |t|. They read v_0 after the Jacobian and change no other value: a build without them
  (`-DC8_NO_TAIL_FIELDS`, test only) writes every other field identically (`tests/validate.py`, class_b). Rows of one
  graph-replicate merge exactly: the 16 largest of the union, the sum of the sums, the argmax of the union (ties to the
  smaller index). t is weight-free so that zero-channel kernels (3w_B = w_A, where `max_abs` is 0) are seen too; at L8
  (K = 0) t differs from the top-slot combination norm (3w_B - w_A) v_0 by a constant factor, so the scale-free Hill
  and share statistics of `design.py report` are the same.
- **Builds.** `make` and `make gmp` (C7(2)'s commands with the new names; `OPTFLAGS ?= -O3`, `C8_REQUIRED` and the
  compile commands `override`), `make inspect`, and the diagnostic builds that `plan` refuses (`--describe` says
  `"diagnostic":true` with the kind): `make profile` (`bin/c8d2_gmp_prof`, `-DC8_TIER_TIMERS`, per-tier timers in the
  JSON), `make ratiohist` (`bin/c8d2_gmp_ratiohist`, `-DC8_RATIO_HISTOGRAM`, histograms of log10(|v|/err) at the two
  promotion tests and for every MP evaluation), `make sanitize` (`bin/c8d2_{decimal,gmp}_san`). The diagnostic hooks
  live in `src/diagnostics.hpp` and are empty in every other build. Two more diagnostic builds exist for tests only:
  `-DC8_NO_TAIL_FIELDS` (class B) and `-DC8_ORDER_TRACE` (A-KER-5, checkpoint review T-04: the parallel task loop
  records the uid each iteration runs; the JSON gains `"addends"` and `"execution_order"`; without the macro the
  preprocessed worker is the production one). `bin/c8d2_inspect` copies each graph to its thread's file in a private
  `mkdtemp` directory (0700, files 0600 created once with `O_EXCL|O_NOFOLLOW`), removed on every exit, terminating
  signals included (CK-K03). `make c7ref` builds the C7(2) reference binaries
  `bin/ref/c7d2_{decimal,gmp}` from `reference/c7d2_hpc_a55958f/` with C7(2)'s own Makefile. `NUMERICS` is `exact`
  for every one of these builds; the opt-in profiles are separate executables (`make gmp NUMERICS=<p>`, "Opt-in
  numerics profiles" below). The build record (`c8-d2-build-record-1`) records `NUMERICS`, the diagnostic kind, the
  profile sources (`numerics_sources`, null for every default build) and the executable's `--describe`.
- **Binary128 arithmetic (Stage 4b R3a).** `calculate_shared<Q>` computes its binary128 `+`, `-` and `*` with
  `src/quadfast.hpp`: inline integer code on 64-bit words that returns libgcc's `__addtf3`/`__subtf3`/`__multf3`
  result bit for bit in round-to-nearest-even, the rounding mode the kernel always runs in. The fast path covers
  normal operands with a normal, finite result; a zero, subnormal, infinite or NaN operand, an exact zero sum, and an
  underflowing or overflowing result are computed by libgcc itself (out-of-line calls with the same operands). The
  operation order is unchanged, and division, conversions, comparisons and `expq` are still libgcc's and
  libquadmath's. The dispatch is per statement with `if constexpr`, so the MP instantiations contain exactly the
  original statements. `numerical_change: false`. Proof obligations: `tests/quad_differential.py` (`make quaddiff`:
  the kernel's operand ranges through `tests/quad_ranges.cpp`, at least 10^9 random pairs per operation, edge lists,
  an injection self-test and an ASan+UBSan run, zero mismatches required) and A-RPL-1/2/5/7 exact. Since Stage-6 fix
  round 4 (W1) the 10^9 is a fixed constant (`MIN_PAIRS`; `--min-pairs` is gone): `coverage(record)` recomputes the
  run's size and scope from its record, the status is `passed` (exit 0), `failed` (1) or `development run (...)` (3)
  naming what is missing, and `quad_differential.py --check RECORD` is the acceptance check of a stored record.
- **Another GMP of the same version (Stage 4b R4f; opt-in, off by default).** `make -B gmp GMP_PREFIX=/abs/prefix` builds
  the GMP-linked executables (`bin/c8d2_gmp`, `make profile ratiohist sanitize probes`, and R3a's `bin/c8d2_quad_ranges`) against the GMP installed
  under that prefix: `-I<prefix>/include` right after the compiler, and `-L<prefix>/lib -Wl,-rpath,<prefix>/lib
  -Wl,--disable-new-dtags` first among the link words. The rpath is a DT_RPATH, which the loader searches before
  `LD_LIBRARY_PATH`, so `slurm/env_expanse.sh` (whose `LD_LIBRARY_PATH` lists Spack's GMP) cannot swap the library at
  run time. Without `GMP_PREFIX` every command is the delivered one, word for word (`tests/test_gmp_prefix.py`), and
  the executables are the default build's (on R4f's development base a785602 byte-identical to Stage 3, Expanse jobs
  54666319 and 54668998). `bin/c8d2_decimal` and `bin/c8d2_inspect` never link GMP. `make c7ref` ignores
  `GMP_PREFIX` but does link GMP: it builds the reference worker `bin/ref/c7d2_gmp` with the reference Makefile's plain
  `-lgmp` (the library the system's normal resolution finds), so that library's provenance matters to the replays (Z18,
  Stage-6 fix round 3; until then this paragraph and the Makefile said that c7ref never links GMP). A relative path, a path with spaces, or a prefix without `include/gmp.h` or
  `lib/libgmp.*` is refused. The mpn kernels of every GMP build compute exact integer results, and the mpf layer's
  truncations are fixed by the precision in limbs, not by the kernel or the tuning thresholds, so a correctly built
  GMP of the same version is expected to give the same mpf results bit for bit. That is checked, not assumed: a GMP_PREFIX
  build is used only after it passes A-RPL-1/2/3/7 exactly against the default build (`docs/PERFORMANCE.md`, "R4f").
  At the Stage-4b integration the knob was kept as opt-in: on Expanse the zen2 build of the final source (B2f) passed
  G-L8SELF, thread identity and the replay subset exactly, and was ×1.052 faster on the L8 sweep sample
  (`docs/PERFORMANCE.md`, "Stage 4b integration"). **Stage 5 (Expanse, 2026-10-05), withdrawn in Stage-6 fix round 2 (Y1): `GMP_PREFIX` is NOT cleared for production.** Job 54676895 (export 07ff5c1975e5; `benchmarks/expanse_2026-10-c8/stage5/exp/`) built the final source with `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2` (libgmp `4267ffeb…`; `bin/c8d2_gmp` `aa84cd45…`, the Stage-4b zen2 worker byte for byte) and ran the owed gates: the full J-VAL-2 (`make test-full GMP_PREFIX=…`: G-REF, G-C7 and G-JET exact on the L=2 graph and all 3,773 L3–L7 kernels, both backends, 22,212 rows with mp > 0 per backend in G-C7; chunks and layouts; class B; the diagnostic builds against the same prefix; point checks 2.1e-353), G-BK8 (decimal against the zen2 worker, exact in all 3,200 rows, 2,779 with mp > 0) and forced tiers (A-RPL-5, gates a–c). Each record equals G4b's record of the default build once the run-specific fields are removed, and on the L8 sweep sample (2,000 kernels × 2 × 512 points) every scientific field of the zen2 worker equals the default worker's. But the forced tiers, the point checks and the class-B builds compile precision tools of their own, and in that job they linked plain `-lgmp`, which resolved Spack's libgmp, not the zen2 library (inspection round 2, S6A2-01): those three records speak for Spack's GMP, not for the zen2 worker. The checks that ran the zen2 worker itself (G-REF, G-C7, G-JET, chunks and layouts, G-BK8, the sweep-sample equality) stand. Until the precision checks are re-run on Expanse with the tools bound to the zen2 library (`make test-full GMP_PREFIX=…`, which runs the point checks and `validate --full` with class B, and `tests/forced_tiers.py`, all through the Y1 binding below), owed together with the A-EXP-3 J-EXP-1 rerun, **`GMP_PREFIX` is not cleared for production on any site**: it stays opt-in and off by default. symmetry has no gated `GMP_PREFIX` build.
- **The precision tools are bound to the worker's GMP (Y1, Stage-6 fix round 2).** `tests/forced_tiers.py --worker`
  (default `bin/c8d2_gmp`), `tests/check_points.py --decimal-worker`/`--gmp-worker` (defaults `bin/c8d2_decimal`,
  `bin/c8d2_gmp`) and the class-B no-tail builds of `tests/validate.py` compile their tools through
  `tools/build_record.py` `bound_tool_command`. The worker's build record must describe the worker (its sha256) and be
  an exact-path production build of that backend (no numerics profile, diagnostic or development build); its
  `GMP_PREFIX` words go where the Makefile puts them (`common.cxx_command(..., gmp_prefix=...)`), and `bind_command`
  refuses a tool whose make flag variables, compiler (`--version` line, `__VERSION__`) or, for gmp, gmp.h (version,
  `__GMP_CC`, `__GMP_CFLAGS`) differ from the worker's. After the compile `check_linked` requires the tool and the
  worker to resolve, here, the libgmp whose sha256 the record names (refused when `ldd` gives no answer). A
  `GMP_PREFIX` in the environment that differs from the record's is refused before anything is compiled (make does not
  track the knob). The records carry the evidence: `gmp_binding` in the forced-tiers record, `binding` in each
  point-check result, `bindings` in the class-B record. `tests/numerics_flags.py`'s F1 tool and its executable must resolve the libgmp of
  the build record as well (`tool_gmp_library` in `baseline.json` and F1); `design.check_gate` was unchanged then, so
  the 570373 gate record was still accepted (fix round 3 requires this provenance in the gate record, Z19 below, and
  refuses 570373's). The same rule, applied at the integration: `tests/sanitize.py` builds its
  point_checks sanitizer tool with the `GMP_PREFIX` of `bin/c8d2_gmp_san`'s record and requires its libgmp, and
  `tools/perf_profile.py` builds the debug-info twin with the profiled worker's `GMP_PREFIX`. Tests:
  `tests/test_gmp_binding.py` (a fake toolchain; in `make test-python`), `tests/test_numerics_flags.py` `binding`.
  The build record of every gmp build now names the GMP it uses: `GMP_PREFIX`, `gmp_header` (gmp.h's `__GMP_CC` and
  `__GMP_CFLAGS`) and `gmp_library` (the libgmp that `ldd` resolves in the build environment, with realpath, sha256,
  `fat`, and the executable's RPATH/RUNPATH).
  - make does not track the knob's value, so switching `GMP_PREFIX` on or off needs `make -B` (or `make clean`).
  - `GMP_PREFIX` and `gmp_library` in `bin/c8d2_gmp.build.json` say which build is present, and `plan` copies the
    build record into the campaign.
- **Stage-6 fix round 3: the precision tools test the worker's own code, and the build shows every macro (Z1-Z4, Z19).**
  - **Z1 (S6A3-01).** Y1 bound the flags, compiler and GMP, not the code: `tests/forced_tiers.py` and
    `tests/check_points.py` compiled the kernel of the current checkout, so after an edit of `src/` without a rebuild,
    or with an older `--worker` of the same flags and GMP, their records named a worker whose code they had not tested.
    `tools/build_record.py` `bound_tool_command` now also makes a read-only snapshot of `src/` and the tool's sources
    (`<output>.snapshot`, `source_snapshot`), rebuilds the worker there with its build record's command in this
    environment (`reproduce_worker`) and requires the result to be byte-identical to the worker (sha256); the tool is
    compiled from the same snapshot. A stale worker, an older worker, or headers changed through the include environment
    (a Boost through `CPATH` or `CPLUS_INCLUDE_PATH`; `bind_command` also compares `BOOST_VERSION`) are refused before
    a point is evaluated, and the binding records `source_binding` (the snapshot's file digests, the reproduction, the
    include environment). The class-B builds of `tests/validate.py` go through the same function. Each precision tool
    run now first rebuilds its worker in the snapshot (1-3 minutes per worker on a cluster node).
  - **Z2 (S6A3-02).** `tests/forced_tiers.py` writes `"status": "passed"` only with the complete A-RPL-5 coverage
    (`coverage()`: scale 1 and the prescribed sample, both sectors, per sector the binary128 and MP quotas recounted
    from the levels, per (sector, L) the prescribed graphs and points per graph, no violation counter, and the Z1
    source binding); a `--sectors` subset (now only `free`/`power`, deduplicated) or a `--scale` run is a "development
    run (...)" naming what it lacks. `forced_tiers.py --check RECORD` exits 0 only for acceptance evidence; every
    consumer of a forced-tiers record uses it or `coverage()`. The stored-record summaries
    (`benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py`, `stage5/exp/scripts/s5e_summary.py`)
    judge their records by status and recomputed coverage (`forced_tiers_verdict`; those records predate Z1, so
    without its source-binding condition): every stored record has the complete coverage, and `--check` refuses each
    only for the missing Z1 binding.
  - **Z3 (S6A3-03).** `src/kernel.hpp` refuses, with `#error`, every `C8_NX_*` numerics hook defined from outside
    `src/numerics/` (all 16 names the sources consult), so a command line, `-include`, `-imacros`, `-Wp,-D` or a
    response file can no longer change promoted evaluations while `--describe` calls the build exact. The build record
    widens `parameter_overrides` (`-DNO_SUM_SHARING`, `-D`/`-U` inside `-Wp,...`, `-include`, `-imacros`,
    `-Xpreprocessor`, `@FILE`) and adds `macro_overrides`: the `C8_*` macros and source switches the compiler's own
    `-dM -E` probe of the options shows in effect beyond the Makefile's plain `-D` build and diagnostic words; either
    makes `development: true`. `gmp_target` refuses development records and records without `macro_overrides` (a
    record made before fix round 3: rebuild the worker). `production.py plan` (G2 and the integration) refuses for every
    plan a record with any macro override, and for a non-test plan a missing, unreadable or mismatched record (schema,
    executable name and sha256, backend, NUMERICS, a diagnostic kind, `required_flags_present` not true) or one whose
    `macro_overrides` is not a list: never copy a worker without its `.build.json`. Not changed (host decision): the
    `C8_QUADFAST_OBSERVE` test hook of `src/quadfast.hpp` and the `NO_SUM_SHARING` switch can still be defined from
    outside without a compile error (`tests/quad_ranges.cpp` defines the former legitimately), but the build record
    flags both, so a plan refuses such a build.
  - **Z4 (S6A3-04), the one `src/` change of the round.** `load_graph` started with an unassigned `n`: a truncated mask
    list left the stream failed and the next `f>>n` did not assign it, so `n` was compared and used for a resize
    before the truncation check (undefined behaviour on malformed input, reachable through the worker and the
    inspector). `M`, `T` and `n` now start at 0, and the stream is checked after the mask list, after each term's
    denominator size, id list and coefficient row, after the rate-table size and after the table; every failure throws
    `truncated graph: <path>`. Valid inputs give the same `Graph` bit for bit: `tests/test_native_guards.py` `loader`
    prints every loaded field with the loaders of this commit and of a42cfb7 on real G-files (the L=2 graph and the
    heaviest and lightest kernel of every (sector, L), L8 included on a cluster) and requires them byte-identical, and
    `tests/validate.py` `bad_inputs` refuses 14 truncations (`graph_truncations`) through the worker and the inspector.
    **Every executable that compiles `load_graph` changes** (the default and diagnostic workers, the inspector, the
    profile builds, `quad_ranges`), so the full exact replay ran on symmetry on the new executables (J-VAL-2, the exact
    parts of J-VAL-3, A-RPL-7 against the Stage-3 baseline and against a42cfb7's build), and the `dd+mp256` gate, the
    profile cost model and the route-(b) bundles were re-made on the new profile build
    (`benchmarks/symmetry_2026-10-c8/s6fix3/`). Not changed (`src/` rule; host decision): the frozen-grid reader of
    `src/c8d2_integrate.cpp` still reads an unassigned id on a truncated grid file (an optional input; production
    passes `-`).
  - **Z19 (S6H3-01).** A reused F1 baseline (`numerics_flags.py --f1-baseline`) skipped the GMP provenance: its
    `tool_gmp_library` must now say match with the sha256 the exact executable's build record names (want, tool and
    worker_now), and the exact executable must resolve that library here now (`reused_baseline_library`; no
    compatibility path for a baseline without the field). The record says whether the baseline was reused and copies
    its `tool_gmp_library` (`f1_baseline.reused`, `.tool_gmp_library`, `.reused_gmp_library`), and `design.check_gate`
    (`gate_gmp_library`) requires both F1 tools' provenance (the profile's `F1.tool_gmp_library`, the baseline's, and
    for a reused baseline the reuse check) and returns `gmp_library`, which `production.gate_evidence_missing` requires
    of a bundle's gate entry: the 570373 record (made before Y1) is refused for exactly that, and the bundles frozen
    with it (570379) cannot plan.
  - Tests: `tests/test_native_guards.py` (new; in `make test-python`: hooks, loader, syntax of every kernel unit; in an
    export without `.git`, `C8_GUARDS_OLD_TREE=<a42cfb7 export>` supplies the before-fix sources),
    `tests/test_gmp_binding.py` `source_binding`, `forced_tiers_coverage`, `forced_tiers_consumers`, `c7ref_note`,
    `tests/test_numerics_flags.py` `binding`, `coverage`, `macro_overrides`, `unit_orchestration` `z3_build_record`,
    `route_b_records`.
- **Stage-6 fix round 4: acceptance from recomputed coverage, the build directory, the gate's input set (W1-W3, W18,
  W22; no `src/` change).**
  - **W1 (S6A4-01)** `tests/quad_differential.py`: the fixed 10^9 minimum and `coverage()` (above, "R3a").
  - **W2 (S6A4-02)** `tests/validate.py`: G-BK8 compared only `values` on rows with MP points, so a changed `max_abs`,
    unbounded tail differences and a different `tail_argmax` were accepted. `compare(..., tails=True)` now requires on
    mp>0 rows `max_abs`, every `tail_top` entry and `tail_sum` within the normalized 1e-30 (`GMP_MP_TOLERANCE`),
    equal tail widths, and `tail_argmax` equal or a documented near tie (`TIE_POLICY`: the two candidates within the
    tolerance, counted in `tail_argmax_ties`); the tails of mp=0 rows exact; every row field must be covered by a rule
    (an unknown or missing field fails), a G-REF reference carries no tail fields, and the shared header fields must
    match. The record carries `row_rule` `c8-d2-bk8-row-rule-2`. The same class: `compare_exact`/`compare_jet` refuse
    uncovered fields, and A-RPL-6's `chunk_merge` requires the chunks to tile the task with quad and mp adding up and
    `max_abs` matching. `validate.coverage(record, gate)` recomputes whether a record is acceptance evidence for
    J-VAL-1, J-VAL-2, G-BK8, G-L8SELF or A-IN-6b (`--only` and the options choose what a run executes, so its status
    alone says only that what ran passed); `validate.py --check RECORD --gate NAME` exits 0 only for evidence, and
    every record carries `acceptance`. Records made before W2 lack the row rule (`row_rule=False` in the summaries).
  - **W3 (S6A4-03)** `tools/build_record.py`: a build record names `build_directory` (where make compiled), and the
    source binding (`reproduce_worker`) keeps relative words of the command and of the include environment meaning
    what they meant there: the snapshot is nested under private parents as deep as the words climb, and each name a
    word reaches outside the snapshot's `src/` is a symlink to the same name under the build directory; words are never
    rewritten (a compiler embeds the include path it found, in `__FILE__` for one). A record without `build_directory`
    is reproduced only without relative words, and with relative make flags a binding runs only from the worker's build
    directory. The integration applies the same to `tests/numerics_flags.py`'s X2 (the reproduction of both
    executables and the F1 tools, `mirror_relative`; one word given two meanings by two build directories is refused)
    and to the profiler's debug-info twin (`perf_profile.twin_directory`).
  - **W18 (S6H4-01)** the J-FLAG gate records the authenticated input set it ran on: `numerics_flags.py`
    `input_identity` records `inputs` (schema `c8-d2-gate-inputs-1`: the sha256 of `inputs/manifest.json`, every input,
    pack and vendored pin hashed against it with `prepare_inputs.verify` before anything is built or written,
    `complete` when no L8 pack is skipped) and verifies it again at the end (`verified_at_end`; a change fails the
    record); a fresh F1 baseline records it and a reused baseline of other inputs is refused. `design.check_gate(...,
    inputs_manifest_sha256)` (`gate_inputs`) requires the block, both verifications, completeness, equality with the
    expected manifest (the pilot's for a freeze, the plan's for production; by default the package's) and an F1
    baseline of the same inputs, and returns `inputs_manifest_sha256`, which a bundle's gate entry keeps;
    `production.gate_evidence_missing` requires it and `route_b` its equality with the bundle's, `gated_route` checks
    against the plan's own manifest. A revised inventory with unchanged graph counts and executables can no longer
    reuse an old gate. The 570536 record is refused for exactly the missing identity; the gate is re-run below.
  - **W22 (host)** `tests/thread_identity.py`: "passed" only when `coverage()` is complete (both default workers × both
    sectors, 64 tasks × 256 points on 32 graphs, identical, exactly 1/8/16/64 threads and the 8 × 8 lanes, every team
    the requested size); a run restricted by `--backends`, `--threads`, `--lanes` or `--lane-threads` is a development
    run (exit 3); an `--executable` run (a profile's F5) is judged by `coverage(gate='F5')` and gets its own status,
    never plain passed; `--check RECORD [--gate F5]`.
  - Tests: `tests/test_native_guards.py` `quad_coverage`, `bk8_compare`, `thread_coverage`, `summaries`;
    `tests/test_gmp_binding.py` `relative_paths`, `flags_relative`; `tests/test_numerics_flags.py` `coverage`,
    `w18_inputs`, `binding`; `unit_orchestration` `route_b_records`.
- **Gates and tests.** `tests/validate.py` (describe, refusals, G-REF, G-C7, G-JET, chunk and layout invariance with
  the tail merge, the inspector against the worker's own execution order (A-KER-5: `-DC8_ORDER_TRACE`, below) and the
  inspector's private temporary directory, class B, the diagnostic builds; `--bk8`, `--l2-control`, `--l8self`; since
  fix round 4 `--check RECORD --gate NAME`, W2),
  `tests/check_points.py` (450 digits, L3-L8), `tests/forced_tiers.py` (A-RPL-5), `tests/thread_identity.py`
  (A-RPL-6) and `tests/sanitize.py` (A-KER-4). The evidence of the Stage-3 runs is in
  `benchmarks/expanse_2026-10-c8/stage3/`.
- **The final default path after Stage 4b (G4b, 2026-10-04).** `numerical_change: false`. The default workers are
  +R5 +R3a: `src/` is d46e736's (R5a's parallel graph loading in `c8d2_integrate.cpp`, R3a's `quadfast.hpp` and its
  dispatch in `kernel.hpp`). R4a's MP-tier rewrite was exact but below A-PERF-2's bar and is reverted (ea59445), so the
  MP tier is again the Stage-3 expression-template code. R4f (`GMP_PREFIX`) is opt-in and not part of the default
  build. R3c, R6 and R4e were not attempted (`docs/PERFORMANCE.md`, "Stage 4b: default-path optimizations").
  - **Executables** (Expanse; Spack GCC 13.3.0, Spack GMP 6.2.1, Boost 1.77 headers; the delivered flags, no
    `-march`). Built from the export of b47b008 (G4b build 54672150), byte-identical to the integration builds of
    d46e736 (54669704) and e7ef98d (54672108):

    | Executable | sha256 | Stage 3 (`c8-stage3`) |
    |---|---|---|
    | `bin/c8d2_decimal` | `99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf` | `3dbd51bb…` |
    | `bin/c8d2_gmp` | `1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa` | `5c5328af…` |
    | `bin/c8d2_gmp_prof` (diagnostic) | `f338a547…` | `d1cc6551…` |
    | `bin/c8d2_gmp_ratiohist` (diagnostic) | `5d0b7c97…` | `c307f2a3…` |
    | `bin/c8d2_inspect` | `63c194fd…` | `034db6a1…` (changed by CK-K03, before Stage 4) |
    | `bin/ref/c7d2_decimal`, `bin/ref/c7d2_gmp` (`make c7ref`) | `4537dcfd…`, `6c829386…` | the same |
    | `bin/c8d2_quad_differential`, `bin/c8d2_quad_ranges` (R3a's test tools) | `3db26f74…`, `3d87f79c…` | new |
    | opt-in `bin/c8d2_gmp` with `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2` (R4f; not default) | `aa84cd45…` | |

    The worker hashes are new because the machine code changed (R5a, R3a, and GCC's inlining of some MP and
    long-double functions, `docs/PERFORMANCE.md`, "Stage 4b R3a"); every output is unchanged.
  - **G4b gates, all passed** (jobs 54672151 and 54672152;
    `benchmarks/expanse_2026-10-c8/stage4b/final/`):
    - J-VAL-2 (`make test-full`): G-REF, G-C7 (against `make c7ref`) and G-JET exact on the L=2 graph and all 3,773
      L3–L7 kernels, both backends, mp > 0 rows included; chunk and layout invariance; point checks L3–L8 at 2.1e-353
      (gmp350) and 1.8e-302 (decimal300) against 1e-280.
    - J-VAL-3: the L=2 control (Stage 3's registered seed), thread identity, G-BK8, G-L8SELF against the Stage-3
      baseline on both backends, forced tiers (A-RPL-5), R3a's differential test (2^32 pairs per operation, 0
      mismatches), merge scale and `assembly_checks --exact`.
    - With run-specific fields removed, the `validate_full`, `point_checks`, `l2_control`, `bk8`, `thread_identity`,
      `forced_tiers` and `l8self` records equal their Stage-3 counterparts (jobs 54637263 and 54637264), so the final
      default binary reproduces Stage 3's validation numbers exactly.

# Opt-in numerics profiles (Stage 4c framework; PLAN D1, A-FLAG-1..3, A-RPL-8)

D1: every numerics-changing speedup is an opt-in profile, off by default, validated against the exact path, and used
in a pilot or production campaign only with the user's approval at planning time. The framework below exists so that
the profile developers (R3b `dd`, R4b `mp256`, R4c `exp1`) can work in parallel; at the framework commit its three
profiles were **stubs** (no numerics change), and the default build, plans and executables are unchanged. Since the
Stage-4c integration on c8 (2026-10-05) all three are implemented (sections R3b, R4b and R4c below), and their
full-scale J-FLAG results are in "Stage 4c gate: J-FLAG results (A-FLAG-7)". R4d (`mpconv`) is not implemented
(host decision 2026-10-04: at most 0.11% of the time), so the all-profile combination is `dd+mp256+exp1`. R7 (rates)
is not a compile-time profile: its plumbing is Stage 3's `plan --rates` (A-FLAG-6).

- **Builds (A-FLAG-1).** `make gmp NUMERICS=<p>[,<p>...]` (or `<p>+<p>`) builds only `bin/c8d2_gmp_<name>`, where
  `<name>` is the profiles in the canonical order `dd`, `mp256`, `exp1` joined by `+` (`NUMERICS=exp1,dd` →
  `bin/c8d2_gmp_dd+exp1`; the combination is `bin/c8d2_gmp_dd+mp256+exp1`). The command is the gmp command with
  `-DC8_NUMERICS -DC8_NUMERICS_<P>...` after `-DC8_USE_GMP`, and the profile's own `NX_FLAGS_<p>` (empty for the stubs;
  e.g. `-mavx2 -mfma` for `dd`, A-FLAG-4) before the required flags, which stay last. The executable also depends on
  `src/numerics/*.hpp`, which no default target reads. Refused: an unknown profile, `mpconv`, `exact` mixed with a
  profile, a repeated or empty name, and every goal other than `gmp` (or the profile executable itself) while
  `NUMERICS` names a profile. With `NUMERICS` unset or `exact` every default command is the delivered one, word for
  word (`tests/test_numerics_flags.py`, `tests/test_gmp_prefix.py`). The build record carries the canonical name
  (`NUMERICS`) and `numerics_sources` (the `-DC8_NUMERICS*` options and the sha256 of every `src/numerics/*.hpp`).
  `tools/common.py` `numerics_name()` is the same canonical rule for the Python side.
- **Hooks (`src/kernel.hpp`, "Opt-in numerics hooks").** A profile build includes `src/numerics/numerics.hpp` twice:
  stage 1 after `exponential`/`absolute` (hook macros, helpers that need only the types) and stage 2 after
  `calculate_shared` (the tiers). The hooks are `C8_NX_SHARED_BEGIN(T)` (a statement at the top of
  `calculate_shared<T>`), `C8_NX_XS_Q(e)` and `C8_NX_XS_MP(e)` (xs_j of the binary128 tier and of every other
  `calculate_shared` type, given the exact expression `e`), `C8_NX_DESCRIBE(os)` (profile fields in `--describe` and in
  the native JSON), and, in `evaluate()`, `nx::promote()` in place of the binary128 → MP code for a point that fails
  the 1e-9 test. Without `C8_NUMERICS` each hook expands to exactly the exact path's tokens and the profile branches
  vanish, so the preprocessed default program is unchanged (A-RPL-8; checked below).
- **`src/numerics/numerics.hpp`.** Stage 1: `nx::Tier` (long double, double-double, binary128, mp256, mp350) and the
  thread-local `nx::last_tier` (the finer tier of the last promoted point, read by the F1 tool for F3), the profile
  name `nx::profile_name` (built from the macros in the canonical order; `--describe` and the native JSON say
  `"numerics":"<name>"`, which `production.py plan --numerics <name>` requires), `nx::describe` (`"numerics_params"`:
  per profile its `C8_NX_PARAMS_<P>` members, `{"stub":true}` when the profile defines none), and the profiles'
  stage-1 parts. Stage 2, in this order: `nx::mp_tier_exact` (the default MP tier's statements), `mp256.hpp`
  (`nx::mp256::tier`), `nx::mp_tier`, `nx::quad_tier` (the default binary128 tier's statements; a 1e-23 failure goes
  to `nx::mp_tier`), `dd.hpp` (`nx::dd::tier`, free to route to `nx::quad_tier` or `nx::mp_tier`), `nx::promote`.
  Every tier sets `f`, `lev` (1 for the middle tier, binary128 or dd; 2 for an MP tier: the worker's `quad` and `mp`
  counters keep counting promotions beyond the first pass and MP evaluations) and `nx::last_tier`. At the end of
  stage 2, `nx::f1_checks` (`C8_NX_F1_CHECKS`, used only by the F1 tool) runs every profile's own
  `C8_NX_F1_CHECKS_<P>` of the build in the order exp1, mp256, dd (dd's checks evaluate the point again, so they come
  last, and the state they leave is cleared): a combination build checks all of its profiles (integration, 5569c53).
- **The stubs** (framework commits 9870a68/241baca; replaced by the implementations on 2026-10-05). `dd.hpp`
  (`nx::dd::tier` = `nx::quad_tier`), `mp256.hpp` (`nx::mp256::tier` = `nx::mp_tier_exact`) and `exp1.hpp` (no hook
  defined) each described in their header comment what their developer implements. A profile
  executable whose profiles are all stubs computes the exact path's numbers; the build job checks its rows against
  `bin/c8d2_gmp`, and the F-gate harness holds it to strict identity.
- **Campaign plumbing (A-FLAG-2).** `production.py plan --numerics <name>` takes only the canonical name (it says
  which one otherwise) and, for anything but `exact` (or `--rates`), a non-blank `--approved-numerics-change "<user
  approval reference>"`; the manifest records `numerics`, `approved_numerics_change`, the executable
  `c8d2_gmp_<name>` and its sha256, and every group config records the profile. `status` prints `numerics <name>,
  rates identity <id> (approved numerics change: <ref>) -- OPT-IN NUMERICS CHANGE (D1)` (and the three fields in
  `--json`); a checkpoint whose native `numerics` differs from the manifest's is refused; `assemble` and `combine`
  print the profile, and `combine` refuses batches of different profiles; a design bundle pins the numerics of its
  pilot and `plan --design` refuses another (`tests/unit_orchestration.py` `exe`, `tests/test_pipeline.py`,
  `tests/combine_core.py`).
- **Development builds are never planned (A-FLAG-1; G4c fix D2, Stage 5).** A profile's parameters are fixed in a
  profile build. Overriding one makes a development (measurement) build, and `production.py plan` refuses it twice:
  - through `--describe`: dd's overrides need `-DC8_DD_DEVELOPMENT` and print `"development":true` (R3b below); any
    `-DC8_MP256_RATIO` (even to 1e-63) or `-DC8_EXP1_RANGE` now prints `"development":true` and
    `"overrides":["C8_MP256_RATIO"]` (or `C8_EXP1_RANGE`) in `numerics_params`; without an override neither field is
    printed and the headers preprocess to the gate build's tokens (`tests/test_numerics_flags.py` `overrides`);
  - through the build record: `tools/build_record.py` records `parameter_overrides` (every `-D`/`-U` of a `C8_*` macro
    other than the Makefile's build macros `C8_USE_GMP`, `C8_NUMERICS`, `C8_NUMERICS_<P>` and the diagnostic macros,
    e.g. `make gmp NUMERICS=mp256 CPPFLAGS=-DC8_MP256_RATIO=1e-60`, or a `C8_NX_*` hook on the command line) and
    `"development": true` when there is one; `plan` recomputes the list from the record's `compiler_options`, so a
    record written before the field existed is checked as well (`tests/unit_orchestration.py` `exe`).
  The default executables do not include `src/numerics/`, so they are unchanged (A-RPL-8).
- **F-gates (A-FLAG-3): `tests/numerics_flags.py`.** One run per profile on a cluster node, against `bin/c8d2_gmp`
  (its docstring has the details):
  - F1, on the A-RPL-5 point set (`forced_tiers.py`'s sample, nets and seeds; points per graph doubled until the exact
    path has 10^4 binary128-accepted and 10^3 MP points per sector). `tests/numerics_f1.cpp`, compiled with the build
    record's command of the executable under test (source swapped), evaluates every point with that build's own
    `evaluate()` (at factor = shift, so y = f·Z). The exact baseline (`--f1-baseline-only`, reusable with
    `--f1-baseline DIR` for the same `bin/c8d2_gmp`) stores per point an independent 450-digit value (forced_tiers'
    `independent()`), the exact path's value and tier, and the hash of the log-coordinates. Gate: relative error
    ≤ 1e-6 at every point, the same points, no sample()/evaluate() level mismatch, no `*_violations` counter of the
    profile's own F1 checks (`C8_NX_F1_CHECKS`, i.e. `nx::f1_checks`). Reported per (sector, L) and tier: relative and err-scaled error histograms next
    to the exact path's, the paired difference to the exact value, the tier transitions.
  - F2, a paired mini-campaign on identical streams: every graph of L3–L8 (all L7 and L8 kernels, and the cheap L3–L6
    ones so that the full C8 can be assembled), 4 replicates × 256 points, campaigns a (.8) and b (.9), each block of
    ≤ 256 tasks run by both executables back to back on one lane. dC8 = Σ ½ J8[L]·(profile − exact jets) with J8 the
    vendored assembly's complex-step Jacobian row (`assemble.jacobians`, design.py's module) at the exact loop means;
    SE_d² = Σ_c Var_rep/(4R). Gate: |dC8| + 3·SE_d ≤ 0.062 in total and per (sector, L ≥ 7), and every per-task
    normalized difference max_j |Δv_j|/max(1, |v_j|) ≤ 1e-9; the replicates double when a bound fails only by its
    SE. Reported: the per-task distribution, the nonlinear dC8 in the vendored module's exact Fraction mode, and the
    projection |dC8| + 3·SE_d·√(n_mini/n_prod) at 2^15, 2^18 and 2^21 points per graph and campaign.
  - F3: promotion fractions and their change per (campaign, sector, L) from F2's counters, and per finer tier from F1.
  - F4: the L8 sweep sample (G-L8SELF's 2,000 graphs, 2 × 512 points), 3 interleaved repeats of each executable in
    one node's lanes, the median lane-thread seconds per sector and the speedup; every repeat of one executable must
    give the same rows. F2's task seconds give an indicative ratio for every (campaign, sector, L).
  - F5: `tests/thread_identity.py --executable` on the profile executable (1, 8, 16, 64 threads and 8 × 8 lanes). Since
    fix round 4 (W22) such a run is judged by `thread_identity.coverage(record, gate='F5')` and recorded with its own
    F5 status, never as the default workers' A-RPL-6 "passed"; `thread_identity.py --check RECORD --gate F5` checks it.
  - **Stage-6 fix round 1 (X1-X3; harness only, no `src/` change).** X1: `f1_coverage()` recounts the F1 evidence
    (scale 1, both sectors, the prescribed graphs per (sector, L), points per graph = sample × 2^doublings in
    contiguous ranges, binary128 and MP counts against the need with `need_met` consistent, every baseline point
    evaluated by the profile); the F1 verdict requires it unless the run is a development run, a baseline-only run
    fails without it, `--sectors` other than `free,power` is a development option, and the record carries
    `F1.coverage`. X2: one read-only source snapshot (`src/` and `tests/numerics_f1.cpp` in the package layout);
    every executable an F1 tool stands for is rebuilt there with its build record's (Makefile, relative) command and
    must be byte-identical, and the F1 tools are compiled in the same snapshot; a non-Makefile command, a numerics
    source pin mismatch, a stale or foreign executable, or a reused baseline without a binding or bound through
    another source snapshot than the run's stops the run before any output; the record carries `build_binding`, `F1.tool_snapshot_sha256` and `F1.baseline_binding`. X3: every worker
    of `tests/thread_identity.py` (F5) and of F2/F4 runs with the inherited environment minus `OMP_*`, `GOMP_*` and
    `KMP_*` and with `OMP_DYNAMIC=false`, and F5 observes each run's and lane's team (`/proc/<pid>/task`, sampled every
    2 ms) and requires it to equal the request (fail closed when it cannot be observed); the record carries
    `F5.team_sizes_verified` and `F5.teams`. `design.check_gate` requires all three, so a record made before the fix
    round (570210) is refused and the gate was re-run (below).
  - `--self-test` runs the exact executable as its own profile and requires dC8 = 0 and every row, point and counter
    identical; a profile executable whose profiles are all stubs is held to the same identity. `--f1-scale`,
    `--f2-graphs`, `--f4-sample` and reduced F5 shapes make a development run, which never reports "passed".
- **Job scripts** (`benchmarks/expanse_2026-10-c8/stage4c/scripts/`, Mac driver `submit_s4c.sh` with the H7E-R
  admission and a per-agent share, `C8_S4C_TAG`): `precheck` (compile a working tree, no commit), `build` (export,
  default and profile builds, A-RPL-8, preprocessed identity, stub identity), `selftest`, `dev <p>` (development
  F-gates on 32 shared cores), `baseline` (the full-scale F1 baseline on one node) and `gate <p> <baseline>` (the
  full-scale J-FLAG run on one node). The commands: `benchmarks/expanse_2026-10-c8/stage4c/README.md`.
- **Evidence (Expanse, `benchmarks/expanse_2026-10-c8/stage4c/framework/`).** A-RPL-8 holds: the exports of 9870a68
  (build 54672480) and 241baca (54672538) give `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, the
  final default binary byte for byte; the preprocessed `src/c8d2_integrate.cpp` under each default build's options is
  token-identical to b47b008's (17 bytes of whitespace from the macro expansions differ). The four all-stub profile
  executables (`dd` `e2eb509f…`, `mp256` `70109ccc…`, `exp1` `388bd0d0…`, `dd+mp256+exp1` `864ece60…`) write rows
  identical to `bin/c8d2_gmp` on L7 and L8 blocks of both sectors at rates .8 and .9, MP points included. The
  self-test and the dd stub at development scales (54672484, 54672539): F1 identical at all 7,680 points of the
  baseline (exact path: largest relative errors 1.3e-10 long double, 3.5e-12 binary128, 1.0e-19 MP; bound 1e-6), F2
  dC8 = 0 exactly over 5,496 tasks with every task difference 0, F3 changes 0, F4 rows identical, F5 identical. The
  dd stub ran 1.2–1.8% faster than `bin/c8d2_gmp` in F4 (same numbers, different code shape): a profile's F4 gain of
  a few percent needs that layout control.
- **R7 rate maps: validation (A-FLAG-6; branch `flag-r7`, `benchmarks/expanse_2026-10-c8/stage4c/dev_r7/`).**
  - **Map.** J-SWEEP-1 stands in for the pilot (not a design pilot). The provisional map `98a215a8…` (free L8 and
    power L6–L8 at a .9 / b 1, the rest .8 / .9; rule in `dev_r7/scripts/r7_spec.py`) was measured by a sweep under
    the map and a fresh exact sweep (all graphs, 2 × 512 points, the same node) and a 32 × 512 complement.
  - **Agreement.** Unpaired, all per-(sector, L) contributions and the total within 3σ (largest |z| 2.06; total z
    −0.93).
  - **Variance × cost.** ×0.842 [0.810, 0.874] (continuous Neyman). Test-only freezes at the four targets with one
    η_node give ×0.823, ×0.875, ×0.875 and ×0.862 core-hours at 1e-3, 5e-4, 2.5e-4 and 1.35e-4.
  - **Status.** A development measurement on a stand-in pilot at 512 points. Before production, a pilot under the
    map (`plan --pilot --rates`, P ≥ 4096) and a fresh freeze must re-measure (R14).

## R3b: the double-double tier (profile `dd`; PLAN A-FLAG-3/4)

Opt-in only: `make gmp NUMERICS=dd` builds `bin/c8d2_gmp_dd` with `NX_FLAGS_dd = -mavx2 -mfma` (A-FLAG-4: these
flags in this profile only; `-ffp-contract=off` stays last, so every fused multiply-add is an explicit
`__builtin_fma`). The default executables never include `src/numerics/` (A-RPL-8). Code: `src/numerics/dd.hpp`.

**In brief** (development measurements on Expanse, details below): on the L8 sweep sample the profile runs ×1.39
faster than the exact path (free ×1.44, power ×1.28), with the cascade routing; the direct routing gives only ×1.09
and is not kept. Per call the dd tier is ×5.9–8.0 faster than the R3a binary128 tier on the same points. On the full
A-RPL-5 F1 set it takes 88% of the points the exact path accepts in binary128 (the rest are cascaded to binary128 by
their dd ratio, which predicts binary128's 1e-23 verdict without a single miss), with relative errors up to 5.2e-12
(binary128: 1.4e-11; bound 1e-6). The worst-case analysis gives |val − exact| ≤ 6.7e-28·err, i.e. relative error
≤ 6.7e-8 after the 1e-20 test; measured, dd agrees with binary128 to better than 1e-30·err.

**Where it acts.** A point that fails the long-double 1e-9 test goes to `nx::dd::tier` instead of binary128. It is
evaluated in double-double (dd, "double-word": hi + lo, two doubles, |lo| ≤ ulp(hi)/2, 106-bit significand) when
- (range) every |lx_j − shift/L| ≤ 300, evaluated as `evaluate()`'s moderate test with 300 in place of 500, and
- (products) no product underflows: every product of the prefix-shared monomial table (the intermediate prefixes
  included) lies in [2^-900, 2^900], and the dd value and error scale come out finite.

Otherwise the point stays on binary128: `nx::quad_tier`, the exact path's statements bit for bit, including its own
1e-23 test and MP promotion. The dd value is accepted when |val| ≥ `C8_DD_RATIO` × err (1e-20; the test fails
exactly when |val| < 1e-20·err, the binary128 test's form). A failure is routed by `C8_DD_ROUTING`:
- cascade (1, the profile default, see "Routing" below): |val| ≥ `C8_DD_CASCADE_LOW` × err (1e-23) goes to
  `nx::quad_tier` (binary128 with its 1e-23 test, then MP if that fails), and below it straight to `nx::mp_tier`;
- direct (0, a development build): every dd failure goes to `nx::mp_tier`.

Routing changes only the cost: every accepted value passed its own tier's test. An accepted dd value has
`lev` = 1 (the worker's `quad` counter counts promotions beyond the first pass) and `nx::last_tier` = `DD` (F3).
The parameters are fixed in a profile build; `-DC8_DD_RATIO`, `-DC8_DD_CASCADE_LOW`, `-DC8_DD_ROUTING` or
`-DC8_DD_GUARD` compile only together with `-DC8_DD_DEVELOPMENT`, and `--describe` then says `"development":true` in
`numerics_params.dd` (measurement variants only, never for a campaign). `-DC8_DD_PHASE_TIMERS` (also development
only) adds rdtsc counters of the dd phases for the F1 checks, with the same arithmetic. `--describe` lists
`dd_ratio`, `routing`, `cascade_low`, `range`, `guard`, `product_range`, `exp`, `sum`, `err` and `development`.

**What it computes.** Mathematically the binary128 tier's value f = (Σ_t n_t/U_t)/S with n_t = Σ_i c_i x_i, U_t the
sums of the degree-L monomials of xs_j = exp(lx_j − shift/L), S = Σ_j x_j, on the kernel's own tables (products,
segments, numerators, terms, in their order). One reformulation: the tier computes only the E exponentials xs_j and
uses them for the numerators and S too. Since x_j = exp(shift/L)·xs_j, the common factor cancels exactly between
every n_t and S, and between val and err. With shift = 0 (every lx_j in [−600, 0], the usual case) x_j = xs_j anyway.

- **Arguments.** lx_j and shift are long doubles (64-bit significands), converted to dd exactly. With shift = 0 the
  argument is lx_j, exact. Otherwise c = shift/L is one dd (`div_d`, ≤ 4u²|c|) for all j, and a_j = lx_j − c
  (`add`, ≤ 3u²|a_j|). The error of c is common to every j: it multiplies every xs_j by the same factor, every U_t by
  its L-th power and f by exp(L·δc). This is a uniform relative error of f of at most 4L·u²|c| (|c| ≤ 300 for
  `sample()`'s points, whose lx has a zero entry, so ≤ 1.2e-28), not amplified by the cancellation.
- **Exponential** (`exp_dd`, for −670 ≤ a ≤ 700). k = nearest(a/ln2). r = a − k·ln2 with ln2 = LN2_1 + LN2_2 + LN2_3:
  LN2_1 has 42 significant bits, so k·LN2_1 and a.h − k·LN2_1 are exact (Sterbenz: |r| < 0.5), and the remaining
  parts enter in dd. x = r/64 (exact). expm1(x) by its Taylor polynomial of degree 11 (Horner in dd, coefficients
  1/k! as dd; truncation < 3e-34 relative on |x| ≤ 0.00542). Six doublings expm1(2y) = expm1(y)·(2 + expm1(y)) keep
  the relative error of the small quantity expm1 instead of doubling it at each squaring. Finally exp(a) =
  2^k·(1 + expm1(r)). The constants are re-derived from mpmath by `tests/test_dd_profile.py`.
- **Monomials.** prod[j+1] = prod[parent]·xs[k] in dd (`mul`).
- **Denominators.** The prefix-shared segment sums are positive sums: `sum_positive` adds each addend's hi with an
  exact two_sum and collects the rounding errors and the addends' lo parts in a double, folded back (fast_two_sum)
  every 8 addends and at every segment end. Its critical path is one double addition per addend, instead of the nine
  dependent additions of a dd addition. A segment of n ≥ 8 addends runs in 4 independent lanes (GCC vector
  extensions, AVX2 in this build): lane 0 starts from the parent's value, lane i takes every 4th addend, each lane is
  folded after 8 of its addends, the lanes are combined by three accurate dd additions, and the last n mod 4 addends
  go through the scalar loop. The lanes lift the two_sum's throughput limit (8 additions per addend); the measured
  sums went from about 5.4 to 2.3–2.7 cycles per addend (below).
- **Numerators.** n_t = Σ_i c_i·xs_i with `mul_d` and the accurate dd addition (signed, may cancel). The error scale
  ab_t = Σ_i |c_i|·xs_i.hi is a double.
- **Value and error scale.** val = Σ_t n_t/U_t (dd division, accurate dd addition, in the kernel's term order); err =
  Σ_t ab_t/U_t.hi in double. The error scale is the binary128 tier's formula (Σ_t (Σ_i |c_i x_i|)/U_t, over S), in
  double precision: its relative error is at most (E + T + 2)·u ≤ 3.3e-14, which moves the 1e-20 threshold by that
  relative amount, a negligible change. The test compares |val.hi| with 1e-20·err (S > 0 cancels from both sides).
  Then f = val/S (dd division), converted to long double with one rounding (2^-64 relative, as the binary128 tier's
  conversion).

**Error analysis.** u = 2^-53, u² = 2^-106 ≈ 1.23e-32. The guards keep every operand and intermediate of the dd
arithmetic normal (products ≥ 2^-900, xs_j ≥ e^-300 ≈ 2^-433, low parts and error terms ≥ 2^-1006), so the
relative bounds below hold. Bounds for the dd operations (relative, of the exact result of the given operands) are
derived in the obvious way from the exact transformations (two_sum, fast_two_sum, two_prod with fma) and the few
rounded operations each algorithm adds. They agree with the sharper bounds of Joldes, Muller and Popescu (ACM TOMS
44(2), 2017) for the same algorithms:

| Operation | Bound (u²) | Measured max (u²), Mac/mpmath |
|---|---:|---:|
| `add` (accurate, any signs, JMP Alg. 6) | 3 | 1.38 |
| `add_d` | 2 | 0.99 |
| `mul` (fma cross terms, JMP Alg. 12) | 6 | 2.39 |
| `mul_d` (JMP Alg. 9) | 2 | 1.14 |
| `div` | 11 | 3.80 |
| `div_d` | 4 | 2.43 |
| `exp_dd`, −670 ≤ a ≤ 700 | 40 | 1.80 |
| `sum_positive`, n addends | 7.5n + 1 (n < 8), 7.5n + 29 (n ≥ 8, lanes) | 0.55n |

The `sum_positive` bound: per addend k at position j of a block of B = 8, the rounding of t_k = e_k + lo_k is at most
u|t_k| ≤ u²(T + h_k) and the rounding of the low accumulator at most u|c_k| ≤ u²(j + 2)T (T the exact total, h_k the
addend's hi; |e_k| ≤ u·s_k, |lo_k| ≤ u·h_k, and |c| ≤ u·s after each fold). Summed over a block of b ≤ B addends this
is u²T(b²/2 + 3.5b) + u²Σh, hence (B/2 + 3.5)n + 1 = 7.5n + 1 in units of u²T. The folds are exact. With lanes, each
lane obeys this bound on its own addends (≤ 7.5n + 4 together, every lane total ≤ T), the three combining additions
add ≤ 3·3u²T and the scalar tail of at most 3 addends ≤ 16u²T: ≤ 7.5n + 29 for n ≥ 8. Both are ≤ 11.2n. Along a
denominator's path of segments the bounds add, the parent's value being the next segment's start: a denominator of
n_t monomials has ε ≤ 11.2 n_t u².

The kernel, in units of the error scale E = Σ_t ab_t/U_t (the quantity the acceptance test compares |val| with), to
first order:

| Step | Bound | shift = 0 | shift ≠ 0, \|a_j\| ≤ 300 |
|---|---|---:|---:|
| xs_j (relative) | ε_x = 40u² + 3u²\|a_j\| | 40u² | 940u² |
| monomial of degree L ≤ 8 (relative) | ε_p = Lε_x + 6(L − 1)u² | 362u² | 7,562u² |
| U_t, n_t ≤ 4,032 monomials (relative) | ε_U = ε_p + 11.2 n_t u² | 45,520u² | 52,720u² |
| n_t (absolute, per ab_t) | ε_x + 2u² + 3·16u² | 90u² | 990u² |
| n_t/U_t (absolute, per ab_t/U_t) | ε_U + (n_t's) + 11u² | 45,621u² | 53,721u² |
| val = Σ_t over T ≤ 280 terms (absolute, per E) | + 3T u² | 46,461u² ≈ 5.7e-28 | 54,561u² ≈ 6.7e-28 |

So |val − val_exact| ≤ δ_dd·E with δ_dd ≤ 6.7e-28 for every point the guards admit, and an accepted value (|val| ≥
1e-20·E up to 3.3e-14 relative) has relative error ≤ 6.7e-28/1e-20 = 6.7e-8, plus the uniform parts (S: ≤ 1,000u²
relative; c: ≤ 1.2e-28; the long-double conversion 5.4e-20). In A-RPL-5's form: |f − f450| ≤ δ_dd·err ≤ 1e-26·err,
which is the dd analogue of binary128's |f − f450| ≤ 1e-29·err. Both imply relative error ≤ 1e-6 after their tests.
The same accounting for binary128 at its 1e-23 test (u_q = 2^-113, recursive summation ≈ (n_t + L)u_q ≈ 4e-31)
gives 4e-8. The dd tier at 1e-20 has a worst-case guarantee of the same order, and 11.9 digits survive its test at
the unit roundoff (P3, "Digits left"). The measured errors are far smaller (below).

**F1 checks** (`C8_NX_F1_CHECKS_DD`, run by `tests/numerics_f1.cpp` through `nx::f1_checks` after `evaluate()` at
every point, after the other profiles' checks of a combination build; a counter ending in
`_violations` fails F1). For every promoted point:
- its route (`dd_route_*`: accepted, guard_range, guard_products, guard_nonfinite, ratio_to_binary128, ratio_to_mp);
- the range guard against an independent recomputation: an out-of-range point that was not guarded, or an in-range
  point that was, is a violation;
- the guard forced: the point forced out of range, and separately forced through the product guard (template
  instances of the same tier code), must give exactly `nx::quad_tier`'s value (all 10 bytes), level and tier
  (binary128 or an MP tier: mp350, or mp256 in a combination build, whose binary128 failures go to mp256);
- the guard class of the point (`dd_guard_class_*`: every product in range; else every xs_j ≤ 1 with every
  denominator ≥ 2^-900; else neither), the data for the guard's scope;
- the decade of the dd ratio |val|/err with binary128's verdict on the same point (`dd_ratio_decade_<d>_binary128_
  pass|fail`), the data that fixes `C8_DD_CASCADE_LOW`; a dd-accepted point that binary128 would reject is a
  violation;
- for a dd-accepted point, |f_dd − f_q| in units of binary128's err, by decade, against 1e-26 (a violation above).

The F1 gate itself, the relative error ≤ 1e-6 against 450 digits at every point, is the harness's.

**Routing (host decision 2026-10-04: measure both, keep the faster).** The dd ratio |val|/err estimates the exact
ratio to within δ_dd ≤ 7e-28 absolute, so next to 1e-23 it predicts binary128's own 1e-23 test to a relative 7e-5:
a misroute needs the exact ratio within that band of 1e-23. `C8_DD_CASCADE_LOW` = 1e-23 is therefore the natural
choice, and the measured ratio data confirm it: on the full A-RPL-5 set (153,600 points, 96,018 promoted), every
dd-evaluated point whose dd ratio lies in [1e-23, 1e-22) passes binary128's test (2,664 points) and every one in
[1e-24, 1e-23) fails it (2,349). In every decade above 1e-23 all points pass, and in every decade below all fail
(`dd_ratio_decade_*`; 0.25-scale development run alike). With LOW = 1e-23 no cascaded point fails binary128 and no
point sent to MP would have passed it. A lower LOW would only add binary128 calls that fail, and a higher one would
send binary128-passing points to MP. Measured on one node (Expanse <NODE>, job 54673842, the final binary
`bin/c8d2_gmp_dd` `51614820…` of ab2a822), F4 on the L8 sweep sample (2,000 graphs, 2 × 512 points, 16 lanes × 8
threads, 3 interleaved repeats each, medians of lane-thread seconds):

| Executable | exact | profile | Speedup total | free | power | MP calls (exact 214,532) |
|---|---:|---:|---:|---:|---:|---:|
| `dd` (cascade, the profile default) | 1,210.0 | 871.7 | **×1.388** | ×1.442 | ×1.279 | 214,532 (+0%) |
| `dd_direct` (development, `C8_DD_ROUTING=0`) | 1,209.9 | 1,106.4 | ×1.094 | ×1.136 | ×1.006 | 324,136 (+51%) |

The cascade is 1.27× faster than the direct routing. The direct routing gains almost nothing in the power sector,
where its 51% more MP calls (P3 predicted +42–68% at 1e-20) cost about what the dd tier saves. **The cascade is the
profile default**; the direct routing stays available only as a development build. The same comparison with the
earlier scalar segment sums (job 54673764, <NODE>, `bin/c8d2_gmp_dd` `37cf09b7…`, export of dd17198) gave cascade ×1.306
(free ×1.347, power ×1.221) and direct ×1.040 (free ×1.074, power ×0.970). Every repeat of an executable wrote the
same rows (`rows_repeatable`); the exact path's medians agree within 0.1% inside each job and within 0.4% between
the two nodes.

**Per-call tier speed** (development build `dd_timers`: `-DC8_DD_PHASE_TIMERS`, the same arithmetic, rdtsc around one
dd evaluation and one binary128 `calculate_shared` on the same warm point, every promoted point of the full A-RPL-5
set, job 54673842):

| Block | Points | dd kcycles/call | binary128 kcycles/call | binary128/dd | dd phases: xs, products, sums, numerators, terms | Sums, cycles/addend |
|---|---:|---:|---:|---:|---|---:|
| free L7 | 19,597 | 55.8 | 371.1 | ×6.65 | 18, 23, 50, 7, 3% | 2.56 |
| free L8 | 13,228 | 183.6 | 1,462.9 | ×7.97 | 6, 20, 68, 3, 2% | 2.41 |
| power L7 | 40,493 | 38.8 | 227.5 | ×5.86 | 25, 23, 40, 9, 3% | 2.67 |
| power L8 | 22,700 | 105.9 | 814.9 | ×7.70 | 11, 23, 58, 6, 2% | 2.33 |

With the scalar segment sums (job 54673816) the ratio was ×4.07–4.33 and the sums took 56–83% of the dd time at
about 5.4 cycles per addend, the throughput limit of one two_sum per addend; the 4-lane sums brought the tier inside
the plan's expected ×4–8. The remaining dd time is mostly the sums, the dd products (about 23%) and, at L7, the
exponentials. On the L8 sweep sample the MP tier is now the largest share of the profile's time (it is unchanged by
dd with the cascade): R4b's target.

**Development results on Expanse** (evidence: `benchmarks/expanse_2026-10-c8/stage4c/dev_dd/`; development runs,
never "passed"; the full F-gates are the gate agent's J-FLAG-dd). Final binary: `bin/c8d2_gmp_dd` `51614820…`
(ab2a822, build 54673841).
- **A-RPL-8.** The exports of bb1a3c9 (build 54673689), dd17198 (54673763), b4ad81b (54673815) and ab2a822 (54673841)
  give `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, the final default binary byte for byte, and
  the preprocessed default program token-identical to b47b008's.
- **Accuracy test** (`tests/dd_accuracy.cpp`, 400,000 cases per row against 120 digits; jobs 54673690, 54673764,
  54673842). Largest relative errors in u²: `exp_dd` 2.21 on |a| ≤ 300, 2.33 on [−650, 700], 2.72 next to the
  reduction's edges (bound 40); the tier's argument with shift = 0 2.32 (exact argument), with shift ≠ 0 819 against
  the bound 40 + 3|a| + 5|c| (the arguments' own roundings); `add` 1.79 (3), `add_d` 1.00 (2), `mul` 3.74 (6), `mul_d`
  1.65 (2), `div` 5.48 (11), `div_d` 2.64 (4), `sum_positive` (4 lanes) 18.8 at n ≈ 4,096 (bound 30,770); the exact
  transformations exact. On the Mac (`tests/test_dd_profile.py`, mpmath, the same header): `exp_dd` 1.80, the
  operations as in the table above, `sum_positive` ≤ 0.55 per addend.
- **F1 on the full A-RPL-5 set** (153,600 points, job 54673842; the exact baseline computed in the job): development
  run (would pass), no violation. Tiers (exact path → dd): long double 57,582 → 57,582; binary128 79,909 → 9,289
  (cascaded) + 70,620 in dd; MP 16,109 → 16,109. Largest relative error: dd 5.2e-12, binary128 1.4e-11 (the exact
  path's own 1.4e-11), long double 5.1e-10, MP 1.0e-19 (bound 1e-6). The dd tier's largest err-scaled error against
  450 digits is 9.2e-29: the long-double roundings of f and y (a few 2^-64·|f|/err, with |f|/err below about 1e-9 at
  a promoted point), the same as for the exact path's binary128 points. dd against binary128 in dd precision is
  below 1e-30·err at every dd-accepted point (decades −31: 5 points, −32: 10,248, −33: 48,402, −34: 10,785, the rest
  below), more than 500 times inside the analytic δ_dd = 6.7e-28. Guard checks: 96,018 points forced out of range
  and 96,018 forced through the product guard each gave exactly binary128's value, level and tier; every promoted
  point of the set has every product in range (no natural guard trip: the A-RPL-5 points are all direct, shift = 0,
  with every |lx_j| ≤ 300); the routing data as above. Per (sector, L), the share of the exact path's
  binary128-accepted points that dd takes: free L7 92.9%, free L8 90.5%, power L7 87.9%, power L8 82.9%.
- **The non-dd code of the profile build is the exact path.** `dd_never` (development: `C8_DD_RATIO=1e300`,
  `C8_DD_CASCADE_LOW=0`, so every point continues to `nx::quad_tier`), built with the profile's `-mavx2 -mfma`, gives
  all 153,600 F1 points bit for bit equal to the exact baseline (jobs 54673764 and 54673842). In the `dd` build,
  115,157 points are identical (all but dd-accepted points whose long-double value differs).
- **0.25-scale development F1** (38,400 points, job 54673690, scalar sums, `dd`, `dd_direct`, `dd_dens`): the same
  picture (17,713 dd-accepted, 2,231 cascaded, 3,791 to MP; decades split at 1e-23). `dd_dens` (the denominator guard
  for xs ≤ 1) gives the same numbers as `dd`, since no point trips the product guard: the literal guard of A-FLAG-4
  stays.
- **Not run here** (the gate agent's J-FLAG-dd): F2 (the paired mini-campaign over all L3–L8 graphs, which also
  meets non-direct points), F5 (thread identity) and the full-scale F4 interleaving of the gate run.

## R4b `mp256`: the staged 256-bit MP tier (opt-in; A-FLAG-5; branch flag-mp256)

`src/numerics/mp256.hpp` (built by `make gmp NUMERICS=mp256`) replaces the stub. A point that reaches the MP tier is
first evaluated by `calculate_shared<MP77,true>`: the kernel's own shared-prefix evaluation (the exact tier's operation
sequence) at `gmp_float<77>`, with the binary128 tier's error estimate err = Σ_t Σ_j |c_tj x_j| / U_t / S. GMP rounds
the 257 requested bits up to whole limbs, so the values carry 320 significant bits (`--describe`
`"mpf_precision_bits":320`). The value is accepted when |v| ≥ `C8_MP256_RATIO` × err (1e-63; 77 − 63 = 14 digits
left, as binary128's 1e-23 leaves 11 of 34) and converted to long double by Boost, as in the exact tier; otherwise
the point is escalated to the unchanged 350-digit tier. Both give `lev = 2`. The process prints its accepted and
escalated counts on stderr at exit. For F1, `C8_NX_F1_CHECKS_MP256` (through `nx::f1_checks`) recomputes every MP-promoted
point at 77 and at 350 digits and counts decision, err-scaled (|v77 − v350| > 1e-69·err) and relative (> 1e-6)
violations, long-double identity and decade histograms.

Development results (Expanse, commit 10b19d9; `benchmarks/expanse_2026-10-c8/stage4c/dev_mp256/README.md`; the
full-scale J-FLAG gate run is the gate agent's):
- A-RPL-8: the default executables are `99a51c1d…`/`1d2a2181…`, the final default binary.
- F1 at full scale (153,600 points; 16,109 MP-promoted, 16,097 accepted at 77 digits, 12 escalated = 7.4e-4): no
  violation, and every value identical to the exact path's, bit for bit. Accepted points have |v77 − v350|/err77
  below 1e-96, against the 1e-69 bound.
- Heavy L8 blocks on one node (median of 3): ×1.403 (free) and ×1.516 (power); MP tier ×2.01 and ×2.10 per call,
  first pass and binary128 unchanged; escalations 1.69e-3 and 2.33e-3 of the MP evaluations; rows identical to the
  exact path's in every run.
- Development F2 (16 graphs per (sector, L ≥ 7)): dC8 = 0 exactly, every task difference 0. F4 (dev sample) ×1.44,
  F5 identical.
- In the 77-digit tier, mpf additions (a fixed per-call cost that does not shrink with the precision) and the
  worker's loop code take about 85% of the time, so the tier stays at about half the 350-digit cost.

## R4c `exp1`: one exponential per shifted call (opt-in; A-FLAG-5; branch flag-exp1)

`src/numerics/exp1.hpp` (built by `make gmp NUMERICS=exp1`) uses only the framework's hooks (`C8_NX_SHARED_BEGIN`,
`C8_NX_XS_Q`, `C8_NX_XS_MP`, `C8_NX_PARAMS_EXP1`). In a call of the binary128 or an MP tier with shift ≠ 0, the exact
path computes xs_j = exp(T(lx_j) − T(shift)/L) per edge (E exponentials); exp1 computes F = exp(−(T(shift)/L)) once and
xs_j = x_j·F, with x_j = exp(T(lx_j)) the value the tier computes anyway (binary128: `expq` and `quadfast::mul`; every
`boost::multiprecision` type, mp256's 77-digit tier included: its own `exp` and `operator*`). A direct call
(shift = 0) and the long-double first pass are untouched; the shifted-call work sits in out-of-line cold functions.
binary128 range guard: the product only when |shift/L| ≤ 5000 and |lx_j| ≤ 5000, else the exact expression for that
call or edge. The rounding of T(shift)/L is common to both paths and scales the value as a whole; the per-edge error,
which the cancellation amplifies and the acceptance tests guard, is a few ulps on exp1 (measured 1.35 ulps at L8
against 0.51 on the exact path). Its F1 checks (`C8_NX_F1_CHECKS_EXP1`) count shifted and factored calls; none is a
violation counter.

Development results (Expanse; `benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/README.md`, final binary
`bin/c8d2_gmp_exp1` `0bf3f1a8…`, unchanged by the integration):
- **exp1 never acts under the planned sampling.** A shifted point needs some lx_j < −600. No shifted point among
  5,734,400 evaluated worker points (L7 and L8, both sectors, rates .8 and .9; 95% bound 5.2e-7) nor among
  1,468,006,400 sampled log-coordinates (lowest lx_j about −100; 95% bound 2.0e-9). The reachability bound over all
  24,173 graphs (net bits ≤ 60) allows lx_j down to about −1,056 (campaign a) and −1,081 (b), but only when all 2L−1
  time coordinates sit near the net's smallest value: P(shifted) ≤ 1e-72 per point at rate .8 (1e-81.8 at L8,
  1e-84.3 at L7). The exponent scales with 600·rate·amin, so only R7 maps with much lower rates could change this.
- **Forced shifted points** (10,240 points, a tail of the sampling order lowered by 700–15,000): `evaluate()` throws
  exactly where the exact path throws, no tier decision changes, no new A-RPL-5 tier-bound violation, and no new F1
  violation within the precision policy's range |f450| ≥ 1e-274·(1 + err), where exp1 differs from the exact path by
  at most 1.2e-12 relative. Beyond that range (6,770 forced points whose value is below what the 350-digit tier
  resolves) the exact path itself fails F1 on 1,507; exp1 fails 7 more and passes 8 of those (counted, not gated; the
  gate was narrowed to the policy's range in 8e4ad72).
- **Speed.** Per shifted call binary128 −3…−14% and MP −13…−32%; direct calls within noise. On the L8 sweep sample
  F4 gave ×1.0075 with identical rows, i.e. code layout. Projected production change: 0.
- **Recommendation of the developer:** correct and composable, but inert; not worth approving.
- **Host sign-off (Stage 5, 2026-10-05).** The host signed off the exp1 forced-shift probe gate *restricted to the
  precision policy's range* |f450| ≥ 1e-274·(1 + err), because beyond it the exact path itself fails F1 (1,507 of the
  6,770 forced points below what the 350-digit tier resolves), so no profile can be gated there. exp1 is inert under
  the planned sampling (P(shifted) ≤ 1e-72 per point; no shifted point among 1.47e9 sampled log-coordinates), and it is
  **not recommended** for production.

## Stage 4c gate: J-FLAG results (A-FLAG-7)

**Integration** (branch c8, 2026-10-05). flag-dd, flag-mp256, flag-exp1 and flag-r7 merged in that order (c7aa396,
0d75f19, f4d7609, 5e19ca3; conflicts only in CHANGELOG, this file, `tests/test_numerics_flags.py` and the regenerated
manifests). Integration commit 5569c53: the F1-check chain `nx::f1_checks` (above; dd's forced-guard identity accepts
mp256's tier as an MP tier), and `production.py plan` refuses an executable whose `numerics_params` mark a profile
`"development":true` (dd's measurement variants). These edits change no worker executable: the profile executables
built from 5569c53 are the developers' final binaries byte for byte (dd `51614820…`, mp256 `9e884b1b…`, exp1
`0bf3f1a8…`); the combination is new, `bin/c8d2_gmp_dd+mp256+exp1` `6bc26966…`.

**A-RPL-8 on the integrated head** (build 54673898, export 5569c535dcfd): `bin/c8d2_decimal` `99a51c1d…` and
`bin/c8d2_gmp` `1d2a2181…`, byte-identical to the final default binary; the preprocessed default program is
token-identical to b47b008's. No A-RPL-1/2/7 rerun is needed.

**The gate runs** (Expanse, one exclusive node each, 2 × EPYC 7742; `tests/numerics_flags.py --profile P` at full
scale, so every record says `"passed"`, not "development run"; evidence `benchmarks/expanse_2026-10-c8/stage4c/gate/`):
the F1 baseline 54673899 (153,600 points with 450-digit references, need met in both sectors without doubling:
29,284 / 50,625 binary128-accepted and 3,541 / 12,568 MP points, free / power); dd 54673900, mp256 54673901,
dd+mp256+exp1 54673902, exp1 54673904 (with the F4 layout control, below). F2 ran 193,384 tasks per binary (every
L3–L8 graph, campaigns a and b, 4 × 256 points) with no replicate doubling; F4 ran 3 interleaved repeats of each
binary on the L8 sweep sample in 16 × 8 lanes; F5 at 1, 8, 16, 64 threads and 8 × 8 lanes.

| Profile | F1 (153,600 points; bound 1e-6) | F2 (\|dC8\| + 3 SE_d, bound 0.062; per task, bound 1e-9) | F3 (tiers, F1 set) | F4 L8 speedup: total (free / power) | F5 |
|---|---|---|---|---|---|
| `dd` | **pass**: 0 violations; dd-accepted max relative error 5.2e-12 (binary128 1.4e-11, long double 5.1e-10, MP 1.0e-19); 115,157 points identical to the exact value, the rest within 5.2e-12; F1 checks: 0 violations (96,018 points forced out of range and 96,018 through the product guard give binary128's value, level and tier exactly) | **pass**: total 4.2e-16 (dC8 1.3e-16, SE 9.8e-17; nonlinear 1.3e-16); per (sector, L ≥ 7) ≤ 3.5e-16; per task max 5.6e-14, 192,545 of 193,384 tasks identical | binary128 79,909 → dd 70,620 + binary128 9,289 (cascade); MP 16,109 unchanged; F2 quad and mp counters unchanged | **×1.389** (×1.443 / ×1.279) | **pass** |
| `mp256` | **pass**: every point identical to the exact path's; 16,097 of 16,109 MP points accepted at 77 digits, 12 escalated (7.4e-4); \|v77 − v350\|/err below 1e-96 (bound 1e-69); every accepted long double equal to the 350-digit one | **pass**: dC8 = 0 exactly, every task identical | MP350 16,109 → mp256 16,097 + mp350 12; counters unchanged | **×1.372** (×1.307 / ×1.555) | **pass** |
| `exp1` | **pass**: every point identical; 0 shifted points (exp1's counters) | **pass**: dC8 = 0 exactly, every task identical | unchanged | ×1.007 (×1.009 / ×1.002): code layout (control ×1.005) | **pass** |
| `dd+mp256+exp1` | **pass**: as dd and mp256 together (all three profiles' F1 checks ran through the chain: no violation) | **pass**: identical to dd's record (mp256 and exp1 change no value) | dd 70,620, binary128 9,289, mp256 16,097, mp350 12 | **×2.168** (×2.113 / ×2.304) | **pass** |

**Projected core-hours at the four targets** (relative SE of |C8| ≈ 4.6e4; `stage4c/gate/aflag7.json`, script
`stage4c/gate/scripts/aflag7_table.py`). The base is the only measured cost table of the final default binary: the
test-only freezes of R7's fresh exact sweep (all graphs, 2 × 512 points, one η_node 0.481, job 54673870), so σ² is
still the stand-in sweep's until the pilot (a new σ² scales the core-hours of every row and moves the ratios only
through the strata's cost shares). A profile changes the cost per point, not
the integrand (F2), so each stratum's allocated core-hours (r·s·C1) are divided by the profile's speedup: F4 per
sector for the L8 strata, F2's task seconds (both campaigns pooled) for L ≤ 7. The frozen allocation is kept
(re-optimizing the Neyman split changes the ratios by at most 0.011). F4's lane wall time includes start-up and graph
loading of 512-point tasks; with F2's integration-only task seconds for every stratum (closer to production's long
tasks) the ratios are dd ×0.657–0.663, mp256 ×0.756–0.764, combination ×0.428–0.432.

| Numerics | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---:|---:|---:|---:|
| default (exact path, final binary) | 7,118 | 10,512 | 42,047 | 137,883 |
| `dd` | 4,977 (×0.699) | 7,168 (×0.682) | 28,672 (×0.682) | 95,348 (×0.692) |
| `mp256` | 5,369 (×0.754) | 8,018 (×0.763) | 32,071 (×0.763) | 104,804 (×0.760) |
| `exp1` | 7,061 (×0.992) | 10,431 (×0.992) | 41,723 (×0.992) | 136,813 (×0.992) |
| `dd+mp256+exp1` | 3,325 (×0.467) | 4,791 (×0.456) | 19,162 (×0.456) | 63,975 (×0.464) |
| R7 map `98a215a8…` (rates, A-FLAG-6) | 5,859 (×0.823) | 9,202 (×0.875) | 36,809 (×0.875) | 118,912 (×0.862) |

- **exp1** never acts in production (no shifted point; R4c section), so its numbers equal the exact path's and its
  ×1.007 is the code-layout effect: the layout control (the framework's all-stub dd executable `e2eb509f…`, exact
  arithmetic, F4 in the same job 54673904) measured ×1.005 (×1.006 / ×1.005) with identical rows. Its projected
  change is 0; the table's ×0.992 is that layout.
- **R7** changes the integrand, so its row is measured, not projected: the fresh-under-map freezes against the exact
  freezes with the same η_node (continuous Neyman variance × cost ×0.842 [0.810, 0.874]), from J-SWEEP-1 as a
  stand-in pilot at 512 points; a pilot under the map must re-measure (R14). R7 with the numerics profiles was not
  measured together; the map changes promotion fractions, so the factors need not multiply.
- The combination is faster than the product of its parts (×2.17 against ×1.389 × ×1.372 = ×1.91): dd removes most
  of the binary128 tier's time and mp256 half of the MP tier's, two disjoint shares.
- The node of the mp256 run (<NODE>) ran the exact binary about 14% slower than the others (1,392 against
  1,206–1,223 lane-thread s); every speedup is measured within one job, exact and profile interleaved.
- **What changes numerically.** mp256 and exp1 reproduced the exact path bit for bit on every F1 point and every F2
  task; they are numerics changes only in principle (a value within about 1e-32 relative of a long-double rounding
  boundary could round differently in mp256; a shifted point, if one ever occurred, in exp1). dd changes values by at
  most 5.2e-12 relative per point and 5.6e-14 normalized per task, and C8 by 1.3e-16 in this paired campaign
  (projected to 2^21 points per graph: 1.4e-16, against 0.062).
- **Status.** Every profile passed F1, F2 and F5 (G4c's A-FLAG-3 part). R7 passed A-FLAG-6's statistical validation;
  its two open bullets were closed in Stage 5 (G4c fix D1): `design.py rates --rule one-step` chooses the rates from
  the pilot (the rule that derived the map above, moved from `dev_r7/scripts/r7_spec.py` into `tools/design.py`, its
  inputs recorded as `rate_rule` in the provisional `design_meta.json`; `--spec` stays the explicit alternative), and
  `tests/test_pipeline.py` part 3 shows a non-test plan accepting a fresh R7 bundle with `--approved-numerics-change`
  and the cost model under the map and refusing it without either (a scratch package with minimal non-test inputs).
  All remain off by default; using any of them (or R7) in a pilot or production campaign needs the user's approval at
  planning time (D1, A-FLAG-2). Development builds of a profile (parameter overrides) are refused by `plan` (above).

## User decision (2026-10-05): `dd` + `mp256` approved for production after the pilot

At the Stage-4 check-in (C62d PLAN-REVIEW-LOG, "USER DECISION (2026-10-05)") the user chose **"dd + mp256"**:
- **`dd+mp256` is approved for production campaigns AFTER the pilot.** Before its first use, a short J-FLAG gate of the
  exact `dd+mp256` build (`make gmp NUMERICS=dd,mp256`, `bin/c8d2_gmp_dd+mp256`; no `exp1`) runs on the production
  site (F1, F2, F5 as in "Stage 4c gate" above; its F4 measures the speedup that the cost table now borrows from the
  `dd+mp256+exp1` build). **The production site is symmetry** (the user's rule of 2026-10-05: "symmetry is back, so
  for the moment only use expanse if symmetry is not enough"), so the gate ran on one whole amdq node of symmetry, not
  on Expanse as first planned (`docs/HPC.md`, "Sites: symmetry first"). **It passed** (job 570210, 2026-10-05; next
  section): F1, F2, F5 pass with the same values as Stage 4c's Expanse records, and its F4 gives symmetry's own speedup,
  ×2.530 (F10: the speedups are site-dependent; the Stage-4c F4 values are Expanse's).
- **`exp1` (inert) and R7 (needs a real pilot under its map, R14) stay OFF.** `dd` or `mp256` alone was not chosen.
- **The smoke and the pilot stay on the exact path.** Every Stage-5 campaign ran exact; so does the planned pilot
  (`docs/HPC.md`, "Pilot runbook").
- **The approval reference** to pass as `production.py plan --numerics dd+mp256 --approved-numerics-change "<ref>"`
  (the manifest, `status`, `assemble` and `combine` record and print it) is, verbatim:

  `user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)`

Default builds, plans and executables are unchanged by this decision (`numerical_change: false` for the default path);
`dd+mp256` remains an opt-in numerics change that every production plan must name. Its accuracy record is the
combination's in the table above (F1 max relative error 5.2e-12 per point, C8 changed by 1.3e-16 in the paired F2
campaign, against the bound 0.062), and its projected cost ×0.452–0.467 of the exact path on Expanse and ×0.390–0.399
on symmetry (its own gate's factors) at every target (`docs/PERFORMANCE.md`, "Stage 5: the refined cost table"). A
design bundle pins the numerics its plans run under. A bundle frozen from the exact pilot gets `dd+mp256` by **route
(b)** (implemented in 23540b2; `docs/DESIGN.md`, "Route (b)"): `design.py freeze --numerics dd+mp256` with this
approval, a cost model measured under `dd+mp256` with the gated build and the gate record of the fix-round-3 re-run
below (570210's record is refused since Stage-6 fix round 1, 570373's since fix round 3: Z19 and the new build)
re-costs the design and keeps the
exact pilot's σ², which the gate's F2 (C8 moved by 4.25e-16) justifies, and keeps the cheaper of the re-optimized
design and the exact design re-costed (F13, fixed for Stage 6); `dd+mp256` is the only member of the allow-list
`production.APPROVED_PROFILES`, which every non-test plan enforces (`plan --pilot --numerics` and `plan --design` of a
route-(a) or route-(b) bundle), and no R7 map is approved (`production.APPROVED_RATES` is empty). **The tools enforce
"the pilot stays exact"** (Stage 6): a non-test `plan --pilot` under any numerics other than exact, or under a rate
map, is refused unless the user's go is a key of `production.APPROVED_PROFILE_PILOTS`, which is empty. **Every
non-test plan whose numerics are not exact runs a gated build:** route (b) through the bundle's gate records (the
executable must be a gate's profile executable), any other plan (route (a), an approved profile pilot) through
`plan --numerics-gate RECORD`, a passed full-scale J-FLAG gate record of the plan's own build; and `design.py freeze
--numerics` refuses a profile cost model measured with a build that none of its gate records passed. Route (a), a
second pilot under the profile, therefore needs the user's go in `APPROVED_PROFILE_PILOTS` and the gate record of the
build at every non-test plan.

**Expanse items (2026-10-05, after 32e5f2b).** None changes a numerical result or the default path. The **seed sync**
of the seeds added on symmetry into Expanse's log is **done** (the two logs and the mirror hold the same 90 seeds), and
the host deleted the obsolete exports with the user's approval (29 of 30, `pkg/d46e7360fe88` kept). The **J-EXP-1
rerun** (A-EXP-3: build, A-RPL-8 identity of the default executables `99a51c1d…`/`1d2a2181…` and `make test` on
Expanse's own toolchain; symmetry cannot substitute) is **partial**: job 54681003 passed the build, A-RPL-8 and the
first `make test` steps, then was cancelled when Expanse's Lustre failed; it is to be completed after Stage 6 on the
post-inspection commit. The `dd+mp256` gate is not among them: it ran on symmetry (below). Details: `docs/HPC.md`,
"Sites: symmetry first".

## The `dd+mp256` J-FLAG gate on symmetry (2026-10-05): PASS (record superseded by the re-run of 2026-10-06, below)

The gate the user required before the first production use of `dd+mp256` (A-FLAG-3 F1–F5 on the approved build, no
`exp1`), run on the production site. Evidence: `benchmarks/symmetry_2026-10-c8/stage5/close/` (README, job 570210,
`clflag.570210.0/jflag_dd+mp256/numerics_flags.json`; script `scripts/clflag.slurm`).

- **Build** (job 570208, export 68ee571ee614 = the F12-fixed head 08e728a plus job scripts; one amddebugq node, Ubuntu
  GCC 11.4.0, Boost 1.77, system GMP 6.2.1): `make gmp NUMERICS=dd,mp256` → `bin/c8d2_gmp_dd+mp256` **`d5df32ac…`**
  (`--describe`: numerics `dd+mp256`, not diagnostic, no development override, no stub). **A-RPL-8:** every default
  executable is byte-identical to the Stage-5 symmetry build (decimal `619ddf7d…`, gmp `2cc5e88e…`, the diagnostic and
  c7ref builds; the sanitizer builds after normalizing the embedded export path) and unchanged by the profile build.
- **Gate** (job 570210: one whole amdq node, <NODE>, 2 × EPYC 7543, 64 cores, 8 NUMA nodes; `tests/numerics_flags.py
  --profile dd+mp256 --seeds-log $C8_SEEDS` at full scale, status `"passed"`, 743 s, 13.2 core-hours). Its own exact F1
  baseline was computed on the node (153,600 points with 450-digit references). F2's 49 seeds (base 820262401) were all
  already in symmetry's log: none added.

| Gate | Result |
|---|---|
| F1 (bound 1e-6 per point) | **pass**: 0 violations; max relative error: long double 5.06e-10 (57,582 points), dd 5.18e-12 (70,620), binary128 1.43e-11 (9,289), mp256 1.02e-19 (16,097), mp350 4.61e-20 (12); 115,157 points identical to the exact value; dd's F1 checks pass |
| F2 (\|dC8\| + 3 SE_d ≤ 0.062, total and per (sector, L ≥ 7); per task ≤ 1e-9) | **pass**: total 4.25e-16 (dC8 1.31e-16, SE_d 9.77e-17); free L7 0, free L8 0, power L7 3.46e-16, power L8 1.81e-16; 192,545 of 193,384 tasks identical, max normalized difference 5.58e-14; no replicate doubling; projected to 2^21 points per graph 1.38e-16 |
| F3 | promotion fractions unchanged in every (campaign, sector, L); tiers as F1 |
| F4 (L8 sweep sample, 3 interleaved repeats, median lane-thread s, 8 × 8 lanes) | rows repeatable; **×2.530** total (free ×2.485, power ×2.644): exact 1,329.5, profile 525.4. F2's integration-only task seconds: ×2.68–×3.39 per (campaign, sector, L ≥ 7) |
| F5 | **pass**: identical at 1, 8, 16, 64 threads and as 8 × 8 lanes |

- **Same values on both sites.** The F1 record (totals, tiers, paired differences, profile checks) and the F2 record
  (gates, totals, per-task statistics, nonlinear dC8, projection) and F3's counters equal Stage 4c's Expanse record of
  `dd+mp256+exp1` (job 54673902, GCC 13.3, EPYC 7742) field by field, apart from exp1's own F1 counters, which this
  build does not have (F2 also equals dd's). The accuracy record of the approved build is therefore the one quoted in
  "User decision" above.
- **Speed is site-dependent (F10).** ×2.530 on symmetry (GCC 11.4) against ×2.168 for `dd+mp256+exp1` on Expanse
  (exp1 is inert): the exact binary is slower here (1,329.5 against 1,206.6 lane-thread s) and the profile faster
  (525.4 against 556.6). Every L7 and L8 ratio of F2 is higher on symmetry than on Expanse (a few cheap L ≤ 6 strata
  are lower). `docs/PERFORMANCE.md`'s symmetry `dd+mp256` rows still assume Expanse's factors (×0.456–0.467) and have not
  been recomputed with these.
- **Status.** `dd+mp256` is cleared for production on symmetry after the pilot, with the approval reference above; the
  default path is unchanged (`numerical_change: false`). The pilot stays exact. The gate of this build ran on symmetry
  only; Expanse's Stage-4c records are of the `dd+mp256+exp1` build (`fxe_flag.slurm`, the planned Expanse run, was
  not submitted).

## The `dd+mp256` J-FLAG gate re-run after Stage-6 fix round 1 (2026-10-06): PASS, the record `check_gate` accepts

Fix round 1 (X1-X3) made the gate record carry its F1 coverage, the build binding of the F1 tools to both executables
and the observed OpenMP team sizes, and `design.check_gate` requires them. The 570210 record above has none of the
three and is refused for exactly those reasons (its F1 coverage, recomputed from its own baseline, was complete). The
gate was therefore re-run with the fixed harness. Evidence: `benchmarks/symmetry_2026-10-c8/s6fix1/` (README, job
570373, `s1flag.570373.0/jflag_dd+mp256/numerics_flags.json`, sha256 **`2eaaebcf…`**; script
`scripts/s1flag.slurm`).

- **Build** (job 570371, export `c30bfc5f0bdf` = the merged fix-round head plus job scripts; amddebugq <NODE>, Ubuntu
  GCC 11.4.0, Boost 1.77, GMP 6.2.1). **A-RPL-8:** every default executable is byte-identical to the Stage-5 symmetry
  build (decimal `619ddf7d…`, gmp `2cc5e88e…`, the diagnostic, probe and c7ref builds; the sanitizer builds after
  normalizing the export path and build-id), and `make gmp NUMERICS=dd,mp256` gives the gated build **`d5df32ac…`**
  again (`src/` is unchanged).
- **Gate** (job 570373: one whole amdq node, <NODE>, 2 × EPYC 7543, 64 cores; `tests/numerics_flags.py --profile dd+mp256`
  at full scale, status `"passed"`, 758 s): a fresh F1 baseline (153,600 points), F1, F2 (its 49 seeds already in
  symmetry's log: none added), F3, F4, F5. `design.check_gate(record, 'dd+mp256', inputs/inventory.json)` passes in
  the job and on the Mac.
  - **X1, coverage:** complete (both sectors; L7 200 × 256 and L8 400 × 64 points per sector; binary128-accepted /
    MP points free 29,284 / 3,541, power 50,625 / 12,568, the need met without doubling; every point evaluated).
  - **X2, binding:** both executables rebuilt in the read-only source snapshot (`b48e0d2e…`) from their build records'
    commands reproduce `2cc5e88e…` and `d5df32ac…` byte for byte, and the F1 tools were compiled there (5-6 s each).
  - **X3, teams:** F5's observed teams equal the requests in every run (1, 8, 16, 64 threads) and every 8 × 8 lane, in
    both sectors; F2 and F4 ran with the sanitized OpenMP environment.
- **Same numbers as 570210:** F1's verdict and totals, F2's totals and per-task statistics (|dC8| + 3 SE_d = 4.25e-16,
  dC8 1.31e-16, SE_d 9.77e-17, max normalized task difference 5.58e-14) and F3 are equal field by field. F4 gives
  ×2.539 (free ×2.512, power ×2.673) against 570210's ×2.530 (timing only).
- **Use (until fix round 3).** This record was the `--numerics-gate` of route-(b) freezes (`docs/DESIGN.md`, "Route
  (b)"). The route-(b) bundles of pre6b were re-frozen with it on sharedq (job 570379): the same designs, byte for byte
  (`benchmarks/symmetry_2026-10-c8/s6fix1/`). Superseded by the next section: its build `d5df32ac…` is gone (Z4), and
  it predates the libgmp provenance that `check_gate` requires since fix round 3 (Z19).

## The `dd+mp256` J-FLAG gate on the fix-round-3 build (2026-10-06)

Stage-6 fix round 3 changed `src/kernel.hpp` (Z4: `load_graph`'s truncation checks; Z3: the refusal of external
`C8_NX_*` hooks), so every kernel executable changed, the profile build `bin/c8d2_gmp_dd+mp256` included, and the
gate ran again on the new build with the fix-round-3 harness (F1's libgmp provenance of both tools recorded, Z19).
The new gate record is the `--numerics-gate` of route-(b) freezes from now on; the profile cost model was re-measured
with the new build (`cost_models/gmp_symmetry_amd_c8_dd+mp256.json` replaced: `design.py freeze` refuses a model of
an executable that no gate passed) and the route-(b) bundles were re-frozen with both. Evidence:
`benchmarks/symmetry_2026-10-c8/s6fix3/` (README; script `scripts/s3flag.slurm`).

- **Build** (job 570533, export `997639178c1f` = 9976391, the fix-round-3 integration; amddebugq <NODE>, Ubuntu GCC
  11.4.0, Boost 1.77, GMP 6.2.1): decimal **`a18ce425…`**, gmp **`7741f733…`**, `make gmp NUMERICS=dd,mp256` →
  **`a46f3060…`** (`--describe`: numerics `dd+mp256`, no development option, no stub; build record `macro_overrides:
  []`); `make c7ref` still gives the plan's `e696d7f3…`/`7e3c8c92…`. The full exact replay on these executables
  passed (J-VAL-2, J-VAL-3's exact parts, A-RPL-7 against the Stage-3 baseline and against a42cfb7's build).
- **Gate** (job 570536: one whole amdq node, <NODE>; `tests/numerics_flags.py --profile dd+mp256` at full scale,
  status `"passed"`, 841 s): record `benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json`, sha256 **`a8de403771f7…`**;
  `design.check_gate` passes in the job and on the Mac and returns `gmp_library` {exact `4dc20a90…`, profile
  `4dc20a90…`, reused false}.
  - X1 coverage complete (free 29,284 / 3,541, power 50,625 / 12,568 binary128-accepted / MP points); X2 both
    executables rebuilt byte for byte in the source snapshot `f0c7137e…`; X3 every team observed; Z19 both F1 tools
    matched to the libgmp `4dc20a90…` their build records name (a fresh baseline).
  - **Same numbers as 570373 and 570210:** F1's verdict and coverage, F2's totals (|dC8| + 3 SE_d = 4.25e-16, dC8
    1.31e-16, SE_d 9.77e-17) and per-task statistics, F3's tiers and promotion counters equal field by field (only
    task timings differ). F4 ×2.517 (free ×2.477, power ×2.620) against ×2.539; the exact path's F4 median 1,335.6
    lane-thread s against 1,325.4 (+0.8%, another node): the exact worker's speed is unchanged, so the exact cost model
    `cost_models/gmp_symmetry_amd_c8.json` stays valid.
- **Cost model** (job 570538, J-SWEEP-2's shape on <NODE>): `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` sha256
  **`18e50440…`** (executable `a46f3060…`; replaces `9b0dfec6…`), ×2.785 over the exact model (free L8 ×2.719, power
  L8 ×2.944), ×1.010 of the replaced model's summed seconds.
- **Route-(b) re-freeze** (job 570539): the same choices as 570379 (1e-3 re-optimized; the exact design kept at 5e-4,
  2.5e-4, 1.35e-4, with counts, r and s equal); 639 / 2,251 / 9,002 / 29,473 lane core-hours (570379: 638 / 2,241 /
  8,963 / 29,328), every SE at its target, every test-only plan within every cap.

Stage-6 fix round 4 (W18) requires the gate record's authenticated input set, which the 570536 record predates
(`check_gate` refuses it for exactly that), so the gate runs again on the same, unchanged build `a46f3060…` with a
fresh F1 baseline, and the route-(b) bundles are re-frozen with the new record; the profile cost model `18e50440…`
stays (its executable is unchanged). Evidence: `benchmarks/symmetry_2026-10-c8/s6fix4/` (README; script
`scripts/s4flag.slurm`).

- **Build** (job 570572, export `392ed22d1d02`; again 570582 for `900e5906522a`): every executable byte-identical to
  fix round 3's (A-RPL-8; the sanitizer builds equal after normalizing the export path and build-id); every build
  record names its `build_directory` (W3).
- **Gate** (job 570574: one whole amdq node, <NODE>; full scale, a fresh F1 baseline, status `"passed"`, 846 s): record
  `benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json`, sha256
  **`42e6d2d80a48…`**; `design.check_gate(..., inputs manifest of the export)` passes and returns
  `inputs_manifest_sha256` `3813f24a…` (verified at the start and the end, complete) and `gmp_library` {exact, profile
  `4dc20a90…`, reused false}; the same check refuses 570536's record for exactly the missing input identity, and the
  new record for another inputs manifest. F1's verdict and coverage, F2's totals (4.25e-16) and per-task statistics,
  F3's tiers and counters equal 570536's apart from task timings; F4 ×2.574 (timing only).
- **Route-(b) re-freeze** (job 570579, sharedq <NODE>): the four bundles' `design.json` byte-identical to 570539's (the
  same choices and costs); `design_meta.json` differs only in the gate entry (now carrying `inputs_manifest_sha256`),
  the pinned tool versions, the time and the seeds; the four test-only plans pass route (b) and record
  `gate_gmp_library` [`4dc20a90…`]; a real claim of one block of the 5e-4 plan (index 101) bound its worker to that
  libgmp (W8), saw no loader override (W7) and peaked at 66 MB against an `est_peak_bytes` of 625 MB (W9).

# C8(2) orchestration and statistics (Stage 3, PLAN.md components D and E)

Added 2026-10-03. This section supersedes the C7(2) orchestration contract below wherever they differ (seeds, nets,
allocation, test results); the arithmetic of the default path is the kernel section above.

- **Groups.** 24 groups `<a|b>_<free|power>_L<3..8>` (D10); campaign weights fixed at 1/2, never fitted.
- **Seeds** (D9). The per-group native (digital-shift) and net seeds are the first 8 bytes, little endian, mod 2^63, of
  sha256(`c8-d2|<base seed>|<campaign>|<sector>|L<L>|<role>`), role native or net. There is no legacy seed scheme and
  no retained mode at order 8. `plan` refuses a base seed whose base or derived seeds collide with the C7(2) 2026
  seeds, the archived records' seeds, `--forbid-seeds-from` files (a non-test plan must pass `$C8_SEEDS`) or a design
  bundle's forbidden seeds (the pilot's).
- **Nets.** Campaign a 52-bit, campaign b 60-bit Sobol nets (as C7(2)); a stratum may not exceed 2^bits points. The
  export check (a)-(c) below runs over every reachable column m = ceil(log2 n), n the plan's (or the design's) largest
  per-graph count, for every order-8 shape (dimension 4L−1 = 7, 11, ..., 31; bits 52 and 60), with work bounded by
  the column count (a 2^40-point stratum at B = 128 and dimension 31 is checked without `fast_forward`).
- **Allocation sources** (D8). Exactly one: `--pilot [--points P]` (P per graph and replicate; P ≥ 4096 unless
  test-only) or `--design BUNDLE` (counts × s and replicates r of a frozen bundle, `docs/DESIGN.md`). Sampling never
  depends on the order of completion or on the hardware.
- **Rates** (R04). Default: the scalar rates .8 (campaign a) and .9 (campaign b), rates identity `default`. Opt-in (R7,
  with `--approved-numerics-change`): a frozen map `rates.json` (schema `c8-d2-rates-1`, a decimal string in (0, 1] for
  every graph of both campaigns, a ≠ b per graph, the inputs-manifest hash); its sha256 is the campaign's rates
  identity, recorded in the manifest, every group config and every checkpoint. The campaign's copy is the only one
  read: editing the source file after planning changes nothing; editing the campaign's copy makes run, status, merge
  and assemble refuse; a staged private copy is re-hashed before the native starts; each block gets a derived
  `@FILE` for exactly its graphs, and every row's echoed rate is checked against the map. `combine.py` refuses
  batches of different rates identities, and a non-test plan a cost model measured under another one (D15).
- **Results.** A test-only plan (`--test-graphs`) writes `C8_test_result.json`: every physical key null at the top
  level, the partial values under `test_partial`. `combine.py --test-only` combines test-only batches of a
  `--test-only` bundle the same way.
- **What is never an input to an estimate:** the pilot (its seeds are forbidden in production), the cost model and the
  calibration (planning only), the done markers of lane mode (hints; completeness is the checkpoint blocks).

# Numerical contract and validation (C7(2), retained; see the C8(2) sections above)

> Revision 2026-10-02 (`CHANGELOG.md`): no change to the integrand, the precision
> tiers and thresholds, either backend, the Sobol/digital-shift stream for a given
> (seed, net, layout, rate), the default allocation, the fixed-point assembly or
> the campaign weights. The only source change is the Boost compatibility hunk
> below; the opt-in allocation options change allocation, not numerics. Earlier
> benchmark numbers below are retained records; packaging checks are in
> `delivery/DELIVERY.md`.

## Unchanged scientific computation

The dimensional convention is epsilon = 2s - 2. All supplied finite-scheme
kernels, graph weights, mixed local-mass/logarithmic subtractions, projective
importance densities, and regulator Taylor coefficients are unchanged.
At loop L the worker evaluates the jet through order 7-L. In particular the
extra two-loop coefficient needed at seventh order is present. The full
physical assembly evaluates the regulator-dependent fixed point, not a
regulator-independent MS formula applied to finite-scheme constants.

Both sectors are evaluated:

    full = F(free + power)
    correction = F(free + power) - F(free)

The measured power correction is never set to zero. At loops 3--7 there are
2,790 power-free kernel classes and 721 mixed-power kernel classes with required
weights. At seven loops these are 2,298 and 590 respectively. The 44 seven-loop
primitive classes are included in the former. Exact graph/forest zeros remain
excluded according to the unchanged supplied inventory.

## Arithmetic choices

The portable/default optimized executable is `bin/c7d2_decimal`:

| Evaluation stage | Reference and default optimized code |
|---|---|
| First pass | long double, >=64 significant binary bits, exponent range >=16384 |
| Cancellation ratio below 1e-9 | GNU __float128 (binary128) |
| Quad ratio below 1e-23 | Boost cpp_dec_float<300> |

The comparison denominator and tiny floor in the original long-double test are
preserved. No forest term is dropped because it is numerically small.

`bin/c7d2_gmp` is an **explicit backend alternative**, not an invisible switch.
Its first two stages and promotion thresholds are identical. Only the last
stage changes to Boost `gmp_float<350>`, backed by the GMP library. The tested
reference declared 300 decimal digits and stored up to 328 with guard digits;
the alternative declares 350 (372 maximum digits in the tested type metadata).
Thus this option does not reduce arithmetic precision. It does change the
library and rounding/truncation behavior, and cannot promise identical results
for every possible input. Retain the decimal executable for compatibility
replays. Neither backend constitutes interval arithmetic.

All builds end with `-std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`
(the Makefile's non-overridable `C7_REQUIRED`); __FAST_MATH__ and insufficient
long-double types are rejected. `OPTFLAGS` (default `-O3`), `CPPFLAGS`,
`CXXFLAGS`, `LDFLAGS` and `LDLIBS` are hooks; with default settings the compile
command is exactly the delivered one, and the Python test helpers use the same
command (`common.cxx_command`). The delivery host used GCC 14.2.0; symmetry uses
GCC 11.4 with Boost 1.77 headers and GMP 6.2.1. Rebuild and test on target
hardware and freeze the compiler, Boost and GMP for a campaign.

Provenance of the build and of each node is recorded, not assumed:
- `make` writes `bin/<exe>.build.json`: compiler version, every flag variable,
  `BOOST_LIB_VERSION` and the GMP version as the preprocessor sees them with the
  same flags, `__OPTIMIZE__` (an unoptimized build warns and records
  `optimized: false`) and the executable sha256. `plan` records it.
- Every block runs from a job-private copy of the planned executable, verified
  against its sha256. Each checkpoint records the executable, inputs-manifest
  and net digests measured from the copies, plus the node's fingerprint: host,
  CPU model, glibc, the `ld.so` interpreter and every library `ldd` resolves
  (path and sha256), libgmp, libquadmath and libgomp included. `status` lists
  the distinct fingerprints per group. The native `--describe` output and the
  native schema `c7-d2-hpc-native-1` are unchanged.

**Boost versions (A-L18).** The 2026 Expanse build that failed at
`kernel.hpp:63/144` (`exponential<T>` deduced as a Boost expression template,
"could not convert boost::multiprecision::exp<detail::minus, ...>") was reported
as a Boost 1.86 failure. It was not: Expanse's `boost/1.86.0` module sets only
`BOOST_ROOT`, not `CPATH`, so that build compiled against the system **Boost 1.66**
in `/usr/include`. Measured with the real headers (Expanse debug jobs 54583692 and
54583699, GCC 13.3; symmetry job 567518, GCC 11.4; `benchmarks/symmetry_2026-10/`):

| Headers | Compiler | delivered `fb64c47` | this revision |
|---|---|---|---|
| Boost 1.66 (Expanse `/usr/include`) | GCC 13.3 | fails (both backends) | compiles |
| Boost 1.77 | GCC 11.4 (symmetry) | compiles | compiles; both binaries byte-identical to `fb64c47` and to the 2026 production (decimal `e696d7f3...`, gmp `7e3c8c92...`) |
| Boost 1.77 | GCC 13.3 (Expanse) | compiles (2026 builds, job 54545287) | not run |
| Boost 1.86 (`-I$BOOST_ROOT/include`) | GCC 13.3, GCC 11.4 | compiles | compiles |

This revision passes `T(T(logx[j])-T(shift)/g.L)` at line 144, so `exponential<T>`
is never instantiated on an expression template; the arithmetic is the same
subtraction of the same quotient, and the D1 byte identity confirms nothing
changed with Boost 1.77. The plan's A-L18 acceptance ("the original fails with
Boost 1.86 under GCC 11.4") rested on the misattribution and cannot hold; what is
demonstrated instead is the table above. Always check which Boost a build saw:
`bin/<exe>.build.json` records `BOOST_LIB_VERSION` (1_77 for the validated
symmetry builds).

## Changes in evaluation order

The shared product DAG and ordered-prefix denominator sums were already present
in the original *long-double* evaluator. This revision applies identical-order
sharing to the expensive binary128 and multiprecision evaluators too. Products
and each denominator/numerator are still evaluated in their original order;
identical subexpressions are cached within the point, not approximated. Scratch
objects are reused by a thread between samples. The discarded final MP error
sum was never read: only its value enters the returned integrand. Quad error
sums remain because they decide promotion.

The scientific values printed by both optimized executables were identical to
the original worker on all delivered matched-graph replay tests. This is an
observed regression result, not a universal bitwise-equivalence theorem for the
GMP option. Arbitrary sample chunks change where compensated partial sums are
combined; deterministic Decimal merging can differ in the last rounding bits
from a single continuous native accumulator. `--sum-mode legacy` disables native
compensation for diagnostic comparisons only.

The merger uses 50-digit Decimal arithmetic on textual native partials, then
converts completed replicate totals to NumPy float64 for the fixed-point,
complex-step Jacobian, covariance and bootstrap calculations. That final
precision boundary matches the existing analysis. It is explicitly not a
claim that all final analysis is 80-bit or multiprecision.

## Random-stream contract

The native point is a function of the frozen direction matrices, seed,
replicate, graph and absolute point index. Thread IDs, node IDs, chunk IDs,
array placement and completion order do not enter the stream. Gray-code seeking
starts directly at each interval's first point; it does not replay earlier
draws. Each stratum retains its original whole power-of-two net with midpoint
open-interval coordinates.

Campaign a uses 52-bit nets and campaign b **60-bit** nets (as delivered; the
archived reference used 52 bits everywhere). The long-double point map is exact
at 60 bits, and the native worker rejects a stratum larger than 2^bits.

**Sobol export check.** Only the scrambled direction integers are exported, from
SciPy's private `_sv` (the SciPy version is recorded); the digital shift the worker
applies is drawn natively (`std::mt19937_64`) from the group's native seed, and
SciPy's `_shift` is used only inside checks (a) and (b) below. A stratum of n points reaches
direction columns 0 ... m-1 with m = ceil(log2 n): 2^27 points use columns
0-26, the delivered maximum of 2^28 points (`a_power_L4`) columns 0-27. For
every replicate `make_net` checks every reachable column, with work
proportional to the number of columns, never to the sample index, and never
modifies the directions:
- (a) the public `random_base2(k)`, k = min(m, 16), equals the exported states at
  the same indices reconstructed by the package's Gray-code arithmetic (exact
  for bits <= 52, the top 53 bits at 60); at most 2^16 public points;
- (b) an identically seeded fresh engine has the same scrambled direction
  integers (columns 0 ... m-1, all bits, compared with the bytes read back from
  the written file) and the same shift;
- (c) SciPy-independent: in every dimension the direction integers of columns
  0 ... m-1 are nonzero, below 2^bits and linearly independent over GF(2)
  (a Sobol generating matrix is nonsingular, and linear scrambling multiplies it
  by a nonsingular matrix).
The tests check mutations of each kind (a low bit at 60 bits, an altered or
zeroed column, a column replaced by the XOR of two others), that exactly columns
0 ... m-1 are checked, that the archived 2026 production nets pass and are
reproduced byte for byte, and that a 2^40-point stratum (B=64, 27 dimensions,
60 bits) is checked without `fast_forward` in about 1.6 s.

**Seeds.** By default the per-group native (digital-shift) and net seeds are
`int.from_bytes(sha256("c7-d2|seed|campaign|sector|L<L>|role")[:8], "little") mod
2^63`, independent across groups and campaigns. `--seed-scheme legacy` reproduces
the delivered additive arithmetic exactly and refuses every known archived or
used seed: the seeds of the archived records and plans (and every base seed that
would reuse their shift or net seeds) and the 2026 campaigns 8885400701634497064,
326694507229394458 and 2765894070584243940.

The two sectors, two campaigns and loop orders use independent randomizations.
Within each sector/campaign/loop, graph totals are summed by replicate before
estimating covariance. Chunks and points within a single net are not treated
as independent uncertainty samples. Coupling/mass and Taylor-order covariances
are retained. Campaign weights are fixed at one half, not fitted to final data.

## Retained inputs

Default production recomputes all seven-loop primitives. In optional retained
mode their old scalar contribution is added once to C7, and the old variance
is added once to the full and power-free covariance. It cancels in their
difference. Bootstrap diagnostic draws one shared primitive uncertainty per
resample. Earlier complete C7 values and lower physical coefficients are never
used as fitting constraints. Known one- and two-loop jets remain input data.

## Actual tests

- `tests/validate.py` (exact replay gate, A-L6): each executable writes its own
  output file, deleted before each run; row counts, jet widths and identity
  tuples must match; decimal against the reference rebuilt with the same
  toolchain and flags must agree exactly (string equality of every value,
  counter and max_abs); gmp must have identical counters, exact equality in rows
  with mp = 0 and at most 1e-30 normalized difference in rows with mp > 0.
  Thread and split checks run for every built backend.
- `benchmarks/full_validation.json` (delivery record): all 3,511 required classes
  at loops 3--7, 56,176 matched samples, both arithmetic backends; printed
  scientific jets and promotion counts matched exactly. This is a finite point
  set, not exhaustive coverage of the integration continuum. On symmetry (GCC
  11.4, Boost 1.77, GMP 6.2.1) `validate.py --full` gave zero normalized
  difference for both backends with identical promotion counts (delivered code,
  job 566254) and, for this revision, passed the exact gate on all 3,511 kernels:
  every decimal row string-identical, every gmp row identical, including all
  1,814 rows with mp > 0 (job 567518, `benchmarks/symmetry_2026-10/`).
- Arbitrary 23-point chunks reconstruct complete 64-point strata across layouts
  0, 1 and 2. Maximum normalized split/unsplit change is recorded there; one
  versus four threads gives identical tested scientific rows at fixed chunks.
- `benchmarks/point_checks.json`: 140 independent 450-digit point checks per
  backend, including progressively extreme endpoints. Denominators are
  independently evaluated by exponentiating each monomial's log sum rather
  than using the optimized product DAG. Scaled discrepancy is below 1e-280;
  the observed maximum is about 1.85e-302 for decimal and 2.15e-353 for GMP.
  This normalizes by one plus the sum of absolute terms; it is not a relative
  error bound on a nearly cancelled zero.
- 96 synthetic regulator-jet cases: new fixed-point and Jacobian functions agree
  with the original analysis implementation.
- `benchmarks/workflow.json`: both primitive modes, all 20 group types,
  incomplete-coverage rejection, duplicate no-clobber publication, corrupt
  checkpoint rejection, and restart with changed thread counts. Tiny workflow
  subsets explicitly output `C7_full = null`.
- `benchmarks/staging.json`: relocated one-pack runtime and frozen cost model.
- `tests/unit_orchestration.py` (pure Python, fake worker and fake Slurm) and
  `tests/check_inputs.py` (inputs and the Neyman table regenerate byte-identically).
- `tests/compat_2026.py`: the pure assembly applied to the 20 `merged.json` replicate
  arrays of the 2026 symmetry production reproduces its `C7_result.json` (C7, SE,
  power correction, every coefficient) to relative 1e-12; measured maximum
  7.3e-16.
- `benchmarks/reassembled.json`: saved-data reconstruction of full, power-free
  and correction means/covariances. Maximum scalar difference from the
  authoritative record is about 9.1e-13; no graph integrations are rerun for
  this reassembly.

Replay gate: exact (decimal; gmp rows with mp = 0), 1e-30 normalized (gmp rows
with mp > 0). Chunk tests use |x-y|/max(1,|x|) <= 1e-12. These are regression
thresholds, not certified errors on C7.

## Lower-order checks and allocation options

`C7_result.json` reports, for C3-C6, the estimate, its sampling SE, the
reference, the reference SE and the pull (estimate - reference) / sqrt(SE^2 +
reference SE^2). C3-C5 references are the archived 13-digit values of the exact
special-function results (reference SE 0; longer evaluations differ by up to
1.8e-12, at C5, negligible against SEs >= 1e-6). The C6 reference is the
C6(2) production value 362.36647176375726 +/- 0.0007997306822612242; the
archived Monte Carlo value 362.3489137997967 +/- 0.15264446036381157 is kept as
a secondary entry. `power_differences[3..6]` get null-test pulls delta/SE (order
3 is reported as rounding when |delta| < 1e-12). |pull| > 3 is flagged and
printed as a diagnostic, not a hard gate. Reassembling the 2026 production
reproduces the manual pulls of its review: C3 -1.08, C4 +0.36, C5 -1.67, C6
+0.73, power differences +0.36, +0.60, +0.28.

`--power-divisor` and `--primitive-allocation neyman` (README, `docs/HPC.md`)
only change how many points independent strata receive. Each stratum's estimate
stays unbiased and is weighted exactly as before; the covariance assembly and
campaign weights are unchanged. The Neyman table is built from 16 archived
replicates per class (noisy); it is opt-in, and the projected primitive-block
SE it prints is labelled a projection.

Results of `--test-graphs` plans are written to `C7_test_result.json`; every
physical key is null and the partial values sit under `test_partial`.
The original physics derivation and graph-generation framework are retained;
this optimization is not an independent field-theoretic validation.

## External documentation

- SciPy Sobol balance and independent randomization:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
- GCC floating-point optimization contract:
  https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html
- Boost GMP multiprecision backend:
  https://www.boost.org/doc/libs/latest/libs/multiprecision/doc/html/boost_multiprecision/tut/floats/gmp_float.html
