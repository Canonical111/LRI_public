# C8(3): the vendored order-8 assembly and power protocol (H2/H3)

Added 2026-10-04 with the vendoring commit (PLAN.md Stage V, component E.1). Since Stage 3a the worker is the
two-order C8 worker and `tools/` are the C8(3) tools; the sections "Order modes", "Class-B fields", "MP self-check"
and "Stage-3a gates" below describe them. The C7(3) contract after them ("Numerical contract") is kept as written
for a6ce987 and holds for the order-7 mode, with the differences noted there.

**Inputs (Stage 2a, component B).** `inputs/` holds the C8(3) inputs: the order-8 `two_loop.json` (7 B2 strings) and
`gamma_d3_8.txt` copied from the vendored `inputs_d3/`, C7(3)'s order-7 files in `inputs/order7/`, the unchanged
L3–L7 packs, the inventory (no `points`: the frozen C7(3) allocation and `primitive_reference.json` are gone, HD5)
and the manifest `c8-d3-hpc-inputs-1` (`docs/HPC.md` "Inputs"). Where the C7(3) contract below names
`inputs/inventory.json` `points`, `inputs/primitive_reference.json` or `inputs/gamma_d3_7.txt`, it describes
a6ce987's layout (kept as `tests/fixtures/c7_inputs/`, which `tests/check_inputs.py` refuses as a C7(3) manifest).
Since Stage 3a the inventory carries the inspect fields for L ≤ 7 (`make inputs-inspect`, `inspect/inspect.json`;
`inspect_complete` true).

- **Delivery.** `LRI_C8_shared/assembly/HANDOFF_assembly.json` is the only delivery of the shared order-8 assembly.
  - sha256 `f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437`, md5
    `b4bc3acf2f081abbed05a0dfcfa08568`, 5,712 bytes, 2026-10-03.
  - Its byte copy is `vendor/c8_assembly/HANDOFF_assembly.json`.
  - The pin stays at this HANDOFF (HD4). A revision is a new HANDOFF, a new C62d review and new pins in both packages.
- **Review.** C62d's H2 review is `LRI_C8_shared/inventory/reviews/order8_assembly_f5ff6a353371.json`.
  - Verdict ACCEPT_WITH_MINOR, with no required change for C63d.
  - Its step-0 decision `accepted_documentation_only_minor_fixes` holds for this HANDOFF version only.
  - The record's consumer-side duties go where PLAN F12 places them.
- **Pins.** Each file the HANDOFF lists is vendored under `vendor/c8_assembly/` at the sha256 the HANDOFF records:

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

- **Power-sector protocol (H3, HD10).** `vendor/c8_assembly/POWER_PROTOCOL.md`, sha256
  `95e91d2c77988e6da5f9066e3a1dc829111b728e8e9cc676fab66601e7958244`, is the registered reporting rule.
  - Δ_p C8 is reported and never assumed zero.
  - The null rows 3–7 and the order-8 row follow that file exactly.
  - They are implemented by the vendored `power_null_rows` and by the reporting of `tools/assemble.py`, which also
    adds the input guards and the PP8 marker (Stage 3a, E.2).
- **Interface notes** (`tools/VENDORED.json`, F12):
  - `loop7_gate` is an order-8 gate.
  - `jacobians` takes float or complex means only.
  - `power_null_rows` is compared on its numeric fields (delta, se, pull, flag), not on its layout, which differs
    from C7(2)'s `power_null_checks`.
  - `top_slot_gate` and `affinity_gate` skip missing loops silently, so `assemble.py` asserts coverage.
- **LRI_ROOT fixtures.** `vendor/c8_assembly_fixtures/` holds 50 byte copies, 555,995 bytes in all.
  - They are the external files that the vendored tests, `exact_check.py` and `prepare_low8.py` read through
    `LRI_ROOT`, as C63d's own open-audit run measured them.
  - The measured set equals C62d's. Each copy is pinned in `tools/VENDORED.json`: a `reference/SHA256SUMS_c8`
    entry or a git object.
- **Exact gate.** `tests/fixtures/exact_check_keys.json` classifies the 40 leaves of `exact_check_results.json`.
  - 33 are exact, 6 are float diagnostics with bounds, and 1 is a provenance pattern.
  - The bounds `exact_check.py` does not assert are taken from the delivered tests: float_vs_exact < 1e-13, and
    `d2_order5_lower_part` within 1e-15 of −1.0775357715447757.
- **Checks** (A-ASM-1).
  - `tests/check_vendored.py --standalone` and `tests/vendored_isolated.py` cover A-ASM-1(a), on the Mac at G-H2 and
    with `--in-place --no-review-record` on Expanse (J-E2, J-VAL-1).
  - `tests/check_vendored.py` without `--standalone` also checks the pins in `inputs/manifest.json` (A-ASM-1(b), from
    Stage 2a on). Its read-rule spies cover `prepare_inputs.verify()` and `make inputs`.
  - `test_order7_production_reassembly`'s ≤ 8-ulp assertion (test `:134`) depends on numpy and CPU. A lone failure
    there is environmental only if A-ASM-3 passes on the same stack in the same job; it is then recorded with its
    ulp count.

# Order modes, class-B fields and the MP self-check (C8(3) Stage 3a; PLAN C)

## Order modes

- **One worker, two orders** (`bin/c8d3_{gmp,decimal}`, `src/c8d3_integrate.cpp`). The task file header
  `C8D3TASKS1 <order> <L> <nt>` selects the order; C7(3)'s `C7D3TASKS1 <L> <nt>` is read as order 7 (HD3, input
  only). K = order − L, and a row holds 2(order + 1 − L) values (the b jet, then the c jet).
- **Order 7** replays C7(3): loops 2–7, K = 7 − L, `inputs/order7/gamma_d3_7.txt` (A-RPL-1: bitwise equal to the
  unchanged C7(3) worker `bin/ref/c7d3_*`, `make c7ref`; A-RPL-7: the run1 and archived-campaign replays).
- **Order 8** is production: loops 3–8 plus the L = 2 control, K = 8 − L, `inputs/gamma_d3_8.txt`. Order 7 with L = 8
  is refused. The gamma table has rows labelled order − l with exactly order − 1 logs, and nothing after the last row.
- **Unchanged default path** (C.9; `tests/native_static.py` checks it against `reference/src` = a6ce987 `src/`):
  `rates()`, `prepare()` (apart from the `#ifndef C8_TEST_UNGUARDED_INDEX` pair), `calculate_reference`,
  `calculate_products`, `calculate_shared` (apart from the A-L18 hunk, with which Boost ≥ 1.86 compiles),
  `sample()`'s arithmetic, every arithmetic statement of `evaluate()`, the stream mixing, the Kahan step, `max_abs`,
  the value assignment and the in-block order by points × addends. The checked G-file reader loads valid files to
  the same values as a6ce987's reader and refuses malformed ones (exit 2, naming the file).

## Class-B fields (C.3)

- **The tail quantity** is t = v_0·jac: v[0] after the Jacobian, before the normalization, the weights and the
  regulator jet. Per row: `tail_top` (the 16 largest |t|, descending, printed at `max_digits10`; an equal value never
  displaces an earlier one), `tail_sum` (Σ|t| in point order, long double) and `tail_argmax` (the global point index of
  the first largest). `max_abs` is unchanged and is 0 for zero-channel kernels (s_G = 4, 3w_B = w_A), whose t is not.
- **Counters:** `nondirect` (points with shift ≠ 0) and `nonmoderate` (points on `calculate_reference<ld>`).
- **The merge** (`production.py merge`, D.13) writes per group, beside the byte-unchanged `graph_replicates.csv`:
  - `graph_tails.csv`: `replicate,graph,points,tail_sum,tail_argmax,tail_n,tail_top_1..tail_top_16`; `tail_sum` is the
    exact `Decimal` sum of the rows' sums (no rounding), `tail_top` the 16 largest of the union, the argmax that of
    the union (ties to the smaller point index);
  - `graph_promotions.csv`: `replicate,graph,quad,mp,nondirect,nonmoderate,mp_checked,mp_alarm,mp_min_log10,`
    `mp_hist_0..mp_hist_17` (summed; `mp_min_log10` the minimum, `null` without checked points);
  - `graph_prefixes.csv` for nested graphs (D.3, R06).

  `tools/tails.py` is an independent in-memory merge of the same rows; `tests/workflow.py` requires every group's two
  files to equal it byte for byte, and `tests/class_b.py` compares it with a hand merge of real chunked rows.
- **Scope.** The tail thresholds and actions apply to L8 only (RECON action 1); L ≤ 7 fields are diagnostics.

## MP self-check (C.4)

- With `--mp-check on` (every MP point) or `stride16` (MP points whose global index ≡ 0 mod 16), the MP evaluation is
  `calculate_shared<MP,true>`: the same value operations with separate error accumulations, so values and counters
  are bitwise those of the unchecked evaluation (A-KER-7, `tests/class_b.py`).
- The row then carries `mp_checked`, `mp_hist` (18 bins of x = log10(|v|/err) at the MP tier: x ≥ −20, [−40,−20), …,
  [−340,−320), x < −340; the plan's last bin "< −320" is read as "< −340", since [−340,−320) is already a bin),
  `mp_min_log10` (`"-inf"` for an exact zero at the MP tier) and `mp_alarm` (points with x < −320, i.e. fewer than 30
  of 350 digits left). Under `--mp-check off` the worker omits these four fields; the tools read them as 0, 18 zeros,
  null and 0.
- The alarm level −320 is calibrated on gmp350. decimal300's floor is near −300 to −328, so the decimal test backend
  may sit in the [−340,−300) bins without an alarm meaning lost digits.
- `plan` defaults to `--mp-check on`.

## Identity (A-KER-3)

- `--describe` (schema `c8-d3-build-1`) reports orders [7, 8], lmax 8, kmax 6, numerics `exact`, `diagnostic`, Boost
  and the backend's `gmp` block: `{"applicable":true, header_version, runtime_version, library}` for the GMP build (the
  library actually loaded, found with `dl_iterate_phdr`; `--describe` exits 3 and the worker refuses to run when
  `gmp.h` and the loaded libgmp differ), `{"applicable":false}` for the decimal build.
- `tools/buildinfo.py` writes `bin/<binary>.buildinfo.json` (schema `c8-d3-buildinfo-1`, with `tools/libprobe.py`'s
  readelf, `env -i ldd`, `LD_DEBUG=libs` and library-version probe); `tests/check_build.py` applies A-KER-3's
  backend-specific rules.
- `production.py plan` refuses a GMP worker whose runtime `gmp` block differs from its build record (the record's
  `describe.gmp`), a GMP worker without the block, a decimal worker whose `gmp.applicable` is not false, and
  diagnostic, sanitizer and self-test builds; `run` and `merge` refuse a block whose worker reported a runtime `gmp`
  block other than the planned build's (`tests/integration_3a.py`).

## Stage-3a gates (L ≤ 7; PLAN A-KER, A-RPL)

- `tests/validate.py`: identity; G-C7 (A-RPL-1: order 7 bitwise equal to `bin/ref/c7d3_*` on the L2 graph and all
  3,511 C7(3) kernels, both backends; the record holds the C8 rows' `nondirect` totals); the G-C7 shift case (the
  A-L18 hunk runs only at shift ≠ 0, which rates .8/.7 never reach: one-point tasks at rate .02 on L3/L5/L7 kernels
  of both sectors, c7ref against C8 order 7 exact with ≥ 1 MP point at shift ≠ 0 per (sector, L)); G-JET (A-RPL-2);
  the bad-input cases (A-KER-1); both orders at L2; random access. `--bk8` (A-RPL-3) and `--l2-control` (A-IN-6) are
  the J-VAL-3 parts. From Stage 3b `tests/thread_identity.py` (A-RPL-6: L8 blocks at 1/16/64/128 threads and as NUMA
  lane processes; chunk splits and layouts at L7 and L8) and `tests/prefix_check.py --real` (A-DES-8 (e)).
- `tests/class_b.py` (A-KER-6 (a)–(e), A-KER-7; (e) also on one new zero-channel L7 kernel per sector from the
  published d=3 payload with `--d3-payload --d3-pin`), `tests/check_points.py` with `tests/point_checks.cpp` (A-RPL-5; the
  C7(3) point-check gates below, hard at L ≤ 7; `--contract` for L8), `tests/forced_tiers.py` (A-RPL-4),
  `tests/sanitize.py` (A-KER-4), `tests/inspect_check.py` (A-KER-5; the worker part on ≥ 100 graphs), `tests/run1_replay.py` (A-RPL-7 G-RUN1) and
  `tests/archived_stream_replay.py` (the C8 worker in order 7; C7 rebuilt with `assemble.combine(order=7)`).
- Every test reads its graphs from the packs through `tools/members.py` (inventory offset, length and sha256; the L2
  control graph by its pinned sha256).

## The accuracy contract at L7 and L8 (A-RPL-4, A-RPL-5; Stage 3b)

The scaled error of a tier output f is s = |f − f450|/err450 (err450 the 450-digit Σ|terms| of the point; MP scaled
by 1 + err450). Bounds from the worst-case rounding at the largest L8 op count A_max = 108,652 (PLAN, "The accuracy
contract"): long double s ≤ 1e-14, binary128 s ≤ 1e-28, MP ≤ 1e-280, and the conversion of the binary128 and MP outputs
to long double correctly rounded (≤ 2^−64 ≈ 5.42e-20 relative). A-RPL-5 keeps C7(3)'s gates (and the long-double
relative ≤ 1e-9 at accepted points) hard at L ≤ 7; at L8 any breach of an A-RPL-4 or A-RPL-5 bound is a
precision-contract finding (reported to the user, Stage 5 waits; never tuned away). **Stage 3b found none.**

Measured column: J-VAL-3 54676975 `forced_tiers.py` (every point in all three tiers and a 450-digit value, at the
points each tier accepts) and J-VAL-2 54676971 `check_points.py` (4 sample points of the first two and the two costliest
kernels per (sector, L)). Neither tool runs the production binaries. Each compiles its own test executable in the job,
from the Stage-3b `src/kernel.hpp` (with `src/stream.hpp` for forced_tiers) and with the Makefile's flags (`-O3
-std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`, no `-march`; Spack GCC 13.3.0, GMP 6.2.1). `forced_tiers.py`
built `tests/forced_tiers.cpp` as `forced_tiers_gmp`, sha256 `e01ffd5a…` (MP backend gmp; `val3/forced_tiers.json`
`build`). `check_points.py` built `tests/point_checks.cpp` once per backend: gmp `c828394b…`, decimal `61cb8449…`
(`val2/check_points.json`, each result's `build`). These executables share the kernel source and the strict flags
with `bin/c8d3_gmp` `24adff54…` and `bin/c8d3_decimal` `5a4d4088…` (src/ unchanged since Stage 3a), so the numerics
carry over to them. The values below were measured on the test executables, not on those two binaries:

| Sample | Points (ld / binary128 / MP) | ld s max | binary128 s max | MP s max | conversion max (q / MP) | ld relative max | decisions |
|---|---|---|---|---|---|---|---|
| forced, free L7 (200 kernels, 256–1,024 points) | 76,445 / 39,453 / 1,350 | 3.10e-18 | 7.61e-34 | 2.48e-367 | 5.40e-20 / 5.41e-20 | 1.37e-10 | 0 mismatches |
| forced, power L7 (200 kernels, 256 points; 228, 1357, 318, 3754 included) | 10,780 / 30,877 / 9,543 | 7.84e-19 | 7.33e-34 | 9.62e-367 | 5.41e-20 / 5.41e-20 | 2.02e-10 | 0 |
| forced, free L8 (400 kernels, 64–128 points) | 30,429 / 17,079 / 1,196 | 4.73e-18 | 9.76e-34 | 1.06e-367 | 5.40e-20 / 5.36e-20 | 2.78e-10 | 0 |
| forced, power L8 (400 kernels, 64 points) | 3,645 / 14,530 / 7,425 | 1.02e-18 | 1.32e-33 | 1.68e-366 | 5.39e-20 / 5.38e-20 | 2.44e-10 | 0 |
| point checks L3–L7 (hard), both backends | 110 ld-accepted of 140 | 3.14e-17 | (sharing bitwise) | 3.2e-353 (gmp), 2.8e-302 (decimal) | — | 3.77e-16 | — |
| point checks L8 (contract mode), both backends | 20 ld-accepted of 32 | 1.67e-19 | (sharing bitwise) | 7.1e-357 (gmp), 2.0e-306 (decimal) | — | 3.47e-15 | — |

Every count of A-RPL-4 was met (≥ 10^4 binary128-accepted and ≥ 10^3 MP points per sector and loop; the free sector
needed the per-graph doubling rounds). The worst ld s at L8 (4.7e-18) is 2,100× below its bound, the worst binary128 s
(1.3e-33) 7.6e4× below; G-BK8 (A-RPL-3) found decimal and gmp rows identical at L7 and L8 (normalized difference 0 on
every row with MP points). The tool records every breach with its point (graph, replicate, index, tier, value,
evaluate()'s level, the 450-digit value) so that a finding would be reported precisely; there was none to record.

# Numerical contract

Dimension 3, ε = 2s−3, complete C0–C7 finite-scheme assembly.
- **Kernel.** The forest kernel contains U_F^(3/2), the critical edge measure x^(−1/4), r(3,z), and all regulator
  Taylor coefficients through z^(7−L). No power correction is assumed zero: both sectors are integrated.
- **Inherited assumption.** The original graph and local-subtraction construction is an inherited scientific
  assumption. These software checks are not an independent field-theory derivation.

## Arithmetic (unchanged)

- **Code identity.** At a6ce987 `src/kernel.hpp` and `src/c7d3_integrate.cpp` were byte-identical to
  `reference/src`, the original d=3 production worker. Since Stage 3a the default path is unchanged in the sense of
  "Order modes" above, and `make c7ref` builds the unchanged worker for the replay gates.
- **Precision tiers.**
  - The first tier is long double (64-bit significand on x86-64).
  - Binary128 promotion happens when |v| < 1e-9 Σ|terms|.
  - Promotion to Boost GMP350 (default) or decimal300 (`make decimal`, lower final-tier precision) happens below
    1e-23.
  - No threshold, forest term or endpoint contribution is relaxed or removed.
- **Build.** The default build command equals the delivered one (`-O3 -std=c++17 -fopenmp -ffp-contract=off
  -fno-fast-math`). User flags can add to it but cannot drop the strict flags. Boost 1.77 headers are tested;
  Boost ≥ 1.86 fails to compile the kernel and is refused by `make`.
- **Summation and assembly.**
  - Task accumulation is compensated.
  - Checkpoint partials are merged deterministically with 50-digit Decimal arithmetic. Rechunking may change the
    last rounding bits.
  - `--sum-mode legacy` exists for reference comparisons.
  - The fixed-point and covariance assembly keeps the original NumPy float64 formula. `tests/assembly_checks.py`
    shows it equals the delivered assembly in every field.

## CPU dependence (measured)

Results are reproducible bit for bit on one CPU type, independent of thread count: on AMD at 64 vs 16 threads, 0
of 5,776 rows differ. They are not reproducible across CPU types.

- **Measurement (symmetry job 566410).** Identical L7 work on Intel Gold 6148 and AMD EPYC 7532: 5,393 of 5,776
  rows differ, by ≤ 2.0e-11 normalized (power L7) and ≤ 1.6e-13 (free L7).
- **Counts.** The binary128 and GMP promotion counts are identical.
- **Likely cause.** CPU-dependent last bits of glibc's x87 long-double `expl`/`logl`, amplified by the accepted
  cancellation.
- **Size.** About 1e-7 of the statistical error: no bias.
- **AMD generations.** Symmetry's AMD nodes are EPYC 7532 (Zen 2) and 7543 (Zen 3), both AVX2, plus one EPYC 8534P
  (Zen 4, AVX-512; cn112). All give the same native results: the archived replay has an identical 96.15% bitwise
  fraction and an identical 1.0e-11 maximum on a 7532, a 7543 and the 8534P.
- **Float64 assembly.** It is also reproducible only per instruction-set level. NumPy/OpenBLAS choose SIMD kernels
  at run time.
  - Run1 was assembled on <NODE> (7532). Reassembled on <NODE> (7543) it is bitwise equal.
  - On cn112 (8534P, AVX-512) it differs by 4 ulp in C7 (1.1e-13, relative 5e-16).
  - So `assemble.py` keeps an existing result that differs only by such rounding, and says so. Three conditions:
    - every non-float leaf is identical, including all data, input, reference and tool hashes;
    - every float agrees to relative 1e-10 of the largest magnitude in its vector;
    - the result's stored gates equal the gates recomputed from its own fields.
    Anything else is refused and never overwritten.
  - `report.py` reports whether the recomputation is bitwise. It accepts relative ≤ 1e-12 on C7, SE and the
    coefficients, and refuses anything else.
- **Records.** Every checkpoint records its node and CPU model. Plans and reports record the host, the libc and the
  resolved libraries.
- **Practice.** Mixed node types are allowed. Use one CPU type when a bitwise rerun is wanted.

## Statistics

- **Statistical units.** Complete randomized graph-summed replicates are the statistical units, never chunks or
  Sobol points.
- **Groups.** Two campaigns (a: rate 0.8, 52-bit nets; b: rate 0.7, 60-bit nets) are independent, weighted ½ each,
  with independent nets and digital shifts per group.
- **Covariance.** All mass, coupling and Taylor-order covariance is retained.
- **Allocation (frozen).** It is the archived joint Neyman allocation over both sectors (`inputs/inventory.json`
  `points`, from `reference/inputs/allocation.json`), times `--multiplier`, for every stratum. Zero targets are
  raised to 4.
  - **Seven-loop primitives.** The 44 primitive classes use their own frozen counts (64–2048), like all other strata.
    The delivered flat `--primitive-points` is removed: at its default 16384 it spent 15.6% of the CPU on 0.03% of
    the variance.
  - **Power sector.** The d=3 allocation balances the sectors (power: about 20–24% of the CPU for about 24–28% of
    the variance), so there is no power-sector multiplier.
- **Retained mode** (`--primitive-mode retained`). It adds the archived seven-loop primitive mean and its shared SE,
  0.2788, once. That SE is a floor no campaign size reduces, so retained mode is unsuitable for large campaigns.
  - The seven-loop primitives are never integrated in retained mode, even with `--points`.
  - Retained mode needs `--max-loop 7`.
  - The a/b gate leaves the shared SE out, since it cancels in the difference.
- **Seeds.** Hashed per-group seeds are the default: SHA-256 of (seed, campaign, sector, L, role).
  - `--seed-scheme legacy` was the delivered arithmetic (C7(3); `tests/legacy_seeds.py` was removed in Stage 3a, and
    the HD6 registry refuses run1's seeds, `tests/unit_orchestration.py` A-ORC-1).
  - The archived records used a third arithmetic, that of the original driver (`tests/archived_replay.py`).
- **Consistency gates.** `assemble.py` and `report.py` report pulls but never use them as constraints.
  - The gates: C3–C5 against the published values; C6 against 33.57542664131543 ± 0.00011855 (the C6(3) M=8192
    campaign, 2026-09-29; the older 33.5682 ± 0.024 is listed as secondary); power differences at orders 3–6 against
    zero; the a/b campaigns; the bootstrap/covariance SE ratio (within ±20%); and the archived C7(3).
  - |pull| > 3 is flagged.
  - The references and their sources are in `references/lower_order_d3.json`, which is hashed into every result.

## Sobol nets

- **Construction.** The nets are SciPy scrambled Sobol (LMS + digital shift), exported as generator matrices.
- **Verification of every exported net**, in time independent of the point counts:
  - **Public API.** The Gray-code reconstruction of the first 2^10 points (columns 0–9) equals SciPy's
    `random_base2(10)` as float64.
  - **Structure.** For every coordinate and every k ≤ bits, the leading k×k block of the GF(2) generator matrix is
    nonsingular. Unscrambled Sobol is unit upper triangular and LMS is unit lower triangular, so this
    per-coordinate stratification property must hold. A flipped or duplicated column fails.
  - **Native access.** `tests/validate.py` checks that the worker's random access and splits reconstruct one net.
- **Coverage limit.** Columns ≥ 10 are not compared value by value with SciPy's public API, and bits below 2^−53 of
  a 60-bit net are not compared at all.

## Validation gates

- **`tests/validate.py`** (A-L6, A-L14). Each executable writes a distinct, pre-deleted output, and row counts, jet
  widths and identity tuples must match. Compared with the original worker built here with the same command:
  - gmp is **bitwise** equal (values and promotion counters);
  - decimal has exactly equal counters, exactly equal values on rows without a GMP/decimal promotion, and normalized
    |x−y|/max(1,|x|) ≤ 1e-13 on rows with one.
  - Random-access splits must agree to 1e-12 normalized, and thread counts must give identical rows, for every built
    backend.
  - Because `reference/src` equals `src/`, this shows build determinism and backend agreement; it is not an
    independent check.
- **`tests/archived_stream_replay.py`** (`make test-replay`; the independent check of the d=3 port). It replays all
  168,528 rows of the archived production campaigns on their archived nets, tasks and seeds:
  - coordinates and promotion counters must be exactly equal;
  - values must agree to ≤ 1e-10 normalized (≤ 1.0e-11 measured on AMD EPYC 7532, 7543 and 8534P);
  - the C7(3) and SE rebuilt from the replayed rows must equal the published values to relative ≤ 1e-12.
- **`tests/check_points.py`**. It checks every tier against an independent 450-digit evaluation:
  - MP tier: error scaled by Σ|terms| ≤ 1e-280;
  - binary128 sharing: bitwise equal to the reference formula;
  - long-double tier, at every point it accepts: relative error ≤ 1e-9 and error scaled by Σ|terms| ≤ 1e-14.
    Measured on symmetry: 110 accepted points, max relative 2.2e-16, max scaled 3.1e-17.
- **Archive reassembly.** `tests/compat_run1.py` (A-ASM-3: run1's 20 merged groups with `assemble.combine(order=7)`)
  and `tests/archived_stream_replay.py` reassemble the published C7(3) values (`tools/reassemble_reference.py` was
  dropped in Stage 3a, PLAN D.1); the archived records reassemble to relative 1.6e-15 of the published C7(3).
