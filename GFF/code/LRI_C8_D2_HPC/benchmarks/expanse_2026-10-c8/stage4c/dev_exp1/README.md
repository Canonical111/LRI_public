# R4c `exp1` development on Expanse (Stage 4c; PLAN D1, A-FLAG-1/3/5; opt-in, off by default)

> **Integration note (2026-10-05, c8 5569c53).** Each profile now defines only `C8_NX_F1_CHECKS_<P>`;
> `src/numerics/numerics.hpp`'s `nx::f1_checks` (`C8_NX_F1_CHECKS`) runs those of every profile in a build (order
> exp1, mp256, dd), so the combination checks all three. The worker executables are unchanged by this
> (`docs/NUMERICS.md`, "Stage 4c gate").

Branch `flag-exp1` from the Stage-4c framework head 64287cb. Development evidence only: no record here is a gate
record (the F-gate runs are labelled "development run"). The gate agent's full-scale J-FLAG runs remain to be done.

## What exp1 does (`src/numerics/exp1.hpp`)

- **Change.** In a shifted call of the binary128 or MP tier (shift != 0), the exact path computes
  `xs_j = exp(T(lx_j) - T(shift)/L)` for every edge, i.e. E exponentials. exp1 computes `F = exp(-(T(shift)/L))`
  once and `xs_j = x_j * F`, where `x_j = exp(T(lx_j))` is the value the tier computes anyway.
  - binary128: `expq`, and the product `quadfast::mul` (libgcc's `__multf3` bit for bit);
  - every `boost::multiprecision` type: the type's `exp` and `operator*` (`gmp_float<350>`, and mp256's
    `gmp_float<77>` tier in a combination build);
  - any other type keeps the exact expression (A-FLAG-5: binary128 and MP only).
- **Untouched.** Direct calls (shift == 0) are untouched: `begin()` tests `shift` once and returns an inactive
  factor. The long-double first pass and every other statement are untouched too.
- **binary128 range guard.** The product is used only when `|shift/L| <= 5000` (per call) and `|lx_j| <= 5000`
  (per edge). Then `x_j`, `F` and `xs_j` lie inside binary128's normal range; any other edge takes the exact
  expression. MP has no range limit.
- **Accuracy argument.**
  - The rounding of `a = T(shift)/L` is common to both paths. It multiplies every `xs_j` by the same factor, so
    it scales the value as a whole and is not amplified by the numerators' cancellation.
  - The per-edge error, which the cancellation does amplify and the acceptance ratios guard, is a few ulps on
    exp1. On the exact path it is `(|lx_j - a| + a few)` ulps.
- **Hooks.** exp1 uses only the framework's hooks: `C8_NX_SHARED_BEGIN`, `C8_NX_XS_Q`, `C8_NX_XS_MP` and
  `C8_NX_PARAMS_EXP1`. `kernel.hpp` and `numerics.hpp` are unchanged.
  - The work of a shifted call lives in out-of-line, cold functions: `shifted_factor()`, and `mul_q()` for the
    binary128 product.
  - Per-thread counters (shifted calls, factored calls, exact-expression edges) feed `C8_NX_F1_CHECKS_EXP1`.
    `C8_NX_F1_CHECKS` names it only if no earlier profile of the build defines one; mp256 uses the same
    convention, and dd defines `C8_NX_F1_CHECKS` itself.
- **Defaults unchanged (A-RPL-8).** Every build left `bin/c8d2_decimal` 99a51c1d… and `bin/c8d2_gmp`
  1d2a2181… byte-identical: builds 54673634, 54673692, 54673767, 54673831, 54673845 and 54673869.
  - Final executables (export f327bb910151, build 54673845): `bin/c8d2_gmp_exp1` 0bf3f1a8…,
    `bin/c8d2_gmp_dd+mp256+exp1` 16005dfa…, the latter with the dd and mp256 stubs of this branch.
  - The results commit 18c216e changed only a comment in `exp1.hpp`. Its build 54673869 (export 18c216e27e4c)
    gives the same two executables, byte for byte.

## Result 1: in production, exp1 never acts

Nothing in this sample produced a shifted point. A shifted point needs some `lx_j < -600`; the sampled points
never go below -100.

| Measure (probe, run 54673787) | Points | Shifted |
|---|---:|---:|
| `census`: `sample()` + `evaluate()` of the exp1 build. L8 sweep sample (1,600 free / 400 power graphs) and 400 L7 graphs per sector; 1,024 points each; rates .8 and .9 | 5,734,400 (3,091,491 binary128 calls, 471,714 MP calls) | 0 (95% bound 5.2e-7) |
| `lxcensus`: the log-coordinates only (`sample()`'s statements, checked bit for bit against `sample()`); 2^18 points per graph, same graphs and rates | 1,468,006,400 | 0 (95% bound 2.0e-9); min_j lx_j >= -100.0 everywhere |
| F1 subset (A-RPL-5 point set at scale 0.25; exp1's counters) | 38,400 (47,470 binary128 calls, 7,582 MP calls in 54673787) | 0 |

**Why (`bound`, every one of the 24,173 graphs of L3–L8).**
- `sample()` sets `lx` of the edge picked at step k to a sum of `log(u_i)/alpha[S_i]`.
- The native nets have bits <= 60, so `|log u| <= 61 ln 2`.
- The DP over sampling chains gives a deterministic reach of `|min lx| <= 1,056` (campaign a: rate .8, 52 bits)
  and `<= 1,081` (b: .9, 60 bits).
- A shifted point is therefore not impossible in principle (24,147 graphs for a; 24,164 for b). But it needs all
  2L-1 time coordinates near the net's smallest value at once.
- With independent uniform u, every step's rate is at least `rate * amin`, where `amin` >= 0.425 is the smallest
  file rate over all graphs and subsets. This gives `P(shifted) <= P(Gamma(2L-1) > 600 rate amin)` <= 10^-72 per
  point at rate .8; at L7 and L8 the bound is 10^-84.3 and 10^-81.8.
- The exponent scales with the rate (`600 rate amin`), so exp1 could matter only under R7 maps with much lower rates.

## Result 2: accuracy

**F1 subset** (`numerics_flags.py --profile exp1 --parts F1 --f1-scale 0.25`; 54673787 and, on the final binary,
54673847). Development run, would pass.
- All 38,400 points are identical to the exact baseline's values, and every tier transition is diagonal.
- Largest relative errors: long double 1.86e-10, binary128 6.06e-12, MP 1.03e-19, against the 1e-6 bound.
- exp1's counters: 0 shifted points.

**Forced shifted points** (`forced`; the same 10,240 points in 54673787, 54673836 and 54673847).
- Each sampled point (64 graphs per (sector, L ∈ {7, 8}), 8 points each) has a tail of its sampling order lowered
  by D = 700, 2000, 4500, 9000 or 15000, the way a tiny u would.
- The exact build stores its values and independent 450-digit references, and the exp1 build compares.
- **Gate passed on the final binary:**
  - `evaluate()` throws exactly where the exact path throws.
  - Every tier transition is diagonal: exp1 never changes a tier decision.
  - No new A-RPL-5 tier-bound violation on any point: binary128 `|q - ref| <= 1e-29 err`, MP
    `|m - ref| / (1 + err) <= 1e-280`.
  - No new F1 violation within the policy's range.
  - Every exp1 `xs_j` is within its bound of `exp(lx_j - shift/L)`.
- **The policy's range.** It is `|f450| >= 1e-274 (1 + err)`, where A-RPL-5 (b) implies F1's 1e-6. Natural points
  stay within `|val|/err >= 1e-131`.
  - In range, exp1's paired difference to the exact value is at most 1.2e-12, at binary128-accepted points.
  - Beyond it (6,770 forced points, where the true value vanishes below MP resolution), neither path has a
    guaranteed relative accuracy. The exact path breaks F1 on 1,507 of them. exp1 breaks 7 more and passes 8 that
    the exact path breaks. These are counted, not gated.
  - The first run (54673787) gated F1 on every point and exited 1 on those 7. The rule was then restricted to the
    policy's range (commit 8e4ad72).
- **xs_j errors.**
  - binary128: max 1.35 ulps for exp1 against 0.51 for the exact path at L8, where `T(shift)/8` is exact.
  - At L7 both reach 1,756 ulps, the common `|a|`-scaled rounding of `T(shift)/7`.
  - MP: within 0.014 eps of `numeric_limits` on both paths.

## Result 3: speed

| Measure | free | power | total |
|---|---:|---:|---:|
| F4 L8, full sweep sample (16x8 lanes, 3 interleaved repeats), final binary 54673847: exact / exp1 lane-thread s | 848.8 / 842.0 (x1.0082) | 369.0 / 366.8 (x1.0060) | 1217.8 / 1208.7 (**x1.0075**) |
| F4 L8, first binary 54673787 | x1.0075 | x1.0090 | x1.0078 |
| F4 L7 (100 graphs per sector), 54673847 | x1.0212 | x0.9974 | x1.0024 |

- Rows are identical between the binaries and between repeats. Since no point is shifted, both binaries do the
  same arithmetic, so the ~0.8% is code layout. Compare the framework's all-stub dd: x1.013–1.018 at development
  scale.

**Per call (`timing`, 54673847; 4 interleaved rounds; minimum of 3 calls per point; 256 points per variant):**

| (sector, L) | direct calls: binary128 / MP | shifted (D = 700, 2000): binary128 | shifted: MP |
|---|---|---|---|
| free L7 | -2.0% / -3.5% | -13.8%, -14.2% | -29.5%, -31.4% |
| free L8 | +0.3% / +0.7% | -2.8%, -3.6% | -12.7%, -15.7% |
| power L7 | -0.7% / -0.1% | -12.9%, -12.8% | -30.5%, -32.4% |
| power L8 | -1.4% / -0.8% | -6.0%, -5.7% | -18.3%, -22.1% |

- On direct calls the difference is noise. An earlier version, with the factor and product inline and a counter on
  every call, timed +0.2…+2.8% in 54673787; the final version moved that work out of line.
- A shifted call saves 3–14% in binary128 and 13–32% in MP. Multiplied by a shifted fraction of 0 (<= 10^-72 per
  point), the projected change in production core-hours is 0 at every target.

## Recommendation

exp1 is correct and composes with dd and mp256, but under the planned sampling it is inert. It gives no
production gain, so there is no reason to approve it. If approved anyway, it changes no number in practice.

## Jobs and cost (`sacct.txt`)

| Job | What | Result |
|---|---|---|
| 54673615, 54673616 | working-tree pre-check; the probe's compile check | defaults identical; profile executables, F1 tools and probe compile |
| 54673634, 54673692, 54673767, 54673831, 54673845, 54673869 | builds of 6eedd3f, 4eb79cd, 3e9d664, 8e4ad72, f327bb9, 18c216e | A-RPL-8 holds each time; exp1 0bf3f1a8… from f327bb9 on |
| 54673635 | smoke | FAILED: `tools/common.dump` never overwrites; the probe writes one file per part since 4eb79cd |
| 54673693, 54673768 | smokes | passed |
| 54673787 | node: bound, census, forced, timing, F1 (0.25), F4 L8 | probe exit 1 (the 7 beyond-range points above); F1 and F4 development runs would pass |
| 54673836 | forced rerun with the policy-range gate (shared) | passed |
| 54673847 | node, final binary: forced, timing, F1 (0.25), F4 L8, F4 L7 | passed |

Total 94,620 core-seconds = 26.3 SU (2 compute-node runs of 7:22 and 3:18; 12 shared jobs).

Commands: `scripts/submit_exp1.sh` (`probecheck`, `smoke`, `node`; H7E-R admission and the exp1 agent share).
`scripts/exp1_probe.py` documents the probe.
