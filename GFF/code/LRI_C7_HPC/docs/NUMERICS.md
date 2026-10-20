# Numerical contract, reproducibility and tests

## Unchanged scientific content

The delivered implementation uses the archived graph inventory, rational weights
as encoded in that input, cluster proposal, random transformations, Schwinger/
coordinate subtraction prescription, quadrature nodes and meromorphic weights.
All seven raw Laurent slots in both coupling and mass channels are retained.
No graph is discarded by a sampled-value threshold. Exact-zero filtering uses
the same supplied lists and channel condition as the original production.

L7 continuous evaluation still promotes at cancellation ratio <1e-7 to GNU
binary128 and then at ratio <1e-24 to Boost 100-decimal-digit arithmetic. Base
`long double` has at least 64 mantissa bits; tested x86 uses 80-bit extended
precision in 16-byte storage. Nonfinite intermediate outputs additionally trigger
promotion or a hard failure; they are never silently written as zero.

The default build uses `-fno-fast-math -ffp-contract=off`. The source rejects
`__FAST_MATH__`. Compiler options enabling unsafe algebraic reassociation are
outside this contract. GCC explicitly distinguishes such optimizations from
standards-preserving `-O3` [GCC].

## Deliberate numerical differences

1. **Compensated quadrature reduction.** To avoid full-grid storage, nodes are
   visited in tiles. Per-term Neumaier accumulation and a compensated final term
   sum replace the old uncompensated shared sum. This preserves every integrand
   term and node but changes rounding; bitwise equivalence to the old quadrature
   is not promised. Summation within a fixed optimized work unit is independent
   of tile size and worker assignment in the tested cases.
2. **Chunk boundaries.** Each block contributes `sum(value / total_graph_samples)`.
   Splitting a sum changes its last few rounding bits. The merger sums decimal
   roundtrips of extended-precision rows with 50 decimal digits, in canonical
   replicate/graph/sample order. It does not reduce partial sums through double
   precision. Final statistical covariance/affine assembly uses NumPy double,
   as did the original analysis.
3. **MP100 rounding order of edge powers.** The extreme-point test found a largest
   normalized MP100 difference of about 3.20e-59. It comes from the precomputed
   squared and cubed inverse distances (`v2=iv*iv`, `v3=iv*iv*iv` in
   `src/point.hpp`, line 20), which change the rounding order of these products
   under Boost expression templates. It does not come from the prefix trie, which
   keeps the original ordered products. Long-double and binary128 point values in
   that suite are bitwise identical to the original. Precision itself is not
   reduced.

These are explicitly flagged changes, not unannounced lower-precision shortcuts.
The program does not claim rigorously bounded floating-point error everywhere.

## Exact random-stream mapping

For graph g and replicate r, both samplers use the original 64-bit seed expression

```
seed + 0x9e3779b97f4a7c15*(r+1) + 0xbf58476d1ce4e5b9*(g+1)  (mod 2^64).
```

Threads, Slurm indices and task launch order are not included. The QMC worker
initializes the original per-graph digital shift, then reconstructs the Gray-code
state at the **global sample offset**. Blocks collectively cover precisely
`[0, total)`. No first point is dropped and no net is thinned. Each graph's total
is a power of two. A chunk is not itself treated as an independent net or error
replicate; the merger checks the full original net is complete [Sobol].

The power worker preserves the original MT19937_64 draws, including unused radial
random numbers, and seeks by discarding exactly `(2L-1)*begin` draws. Paired
quadrature degrees use the same `(seed, graph, replicate, sample)` tree. The
complete streams are differenced within replicate before covariance is computed.
Power seeking is linear in `begin`; it was not replaced with a different RNG.

The Sobol matrix exporter uses the same SciPy implementation as the reference and
checks its private matrix data against sixteen public `random_base2` outputs per
replicate before writing a net. Sixteen Gray-code points exercise only the
digital shift and direction-matrix columns 0–3. A change in those fails the
check, but a changed SciPy internal representation of the higher columns would
not be caught. Preserve the exported net for long-term exact reproduction. Before
planning with a different SciPy version, regenerate a net of an archived
campaign and compare it byte for byte.

## Checkpoint integrity

Each worker checkpoint (`c7-campaign-2`) carries `provenance.payload_sha256`: the
SHA-256 of a canonical serialization of its scientific content. That content is
mode, L, degree, seed, rate and inventory count, and for each row
uid/replicate/graph/begin/end/total/quad_calls/mp_calls plus the 14 values as
`str(Decimal)`, parsed with `parse_float=Decimal`. Timings, profile, host,
command and temporary paths are excluded. The digest is written inside the
checkpoint, and the one file is published with the temp file, fsync and
no-clobber hardlink protocol. There is no sidecar, so a checkpoint either does
not exist or exists complete with its digest.

On reuse, at merge and in `campaign.py verify`, the digest is recomputed from the
parsed file. A mismatch is committed corruption and fails loudly with the path;
an unparsable file cannot be one of ours, since publication is atomic, and also
fails. Neither is ever reused silently. A concurrent duplicate worker that loses
the publication race validates the winner, digest included. Recovery is an
explicit operator step, `campaign.py quarantine DIR IDENTITY`, which moves the
file to `checkpoints/quarantine/`, logs it and invalidates an existing audit; the
next `run` recomputes it deterministically and the next merge reuses the identical
merged outputs and republishes the audit. Legacy `c7-campaign-1` campaigns, whose checkpoints have no
digest, are still merged without this check.

Identity criteria, tested with interruptions during the C++ run, between its
exit and publication, after publication and by SIGTERM:

- a checkpoint **reused** without recomputation stays byte-identical;
- a **recomputed** checkpoint (after an interruption or a quarantine) has an
  identical canonical payload and `payload_sha256`; timing, profile, command and
  host fields may differ;
- merged `N*.json` outputs contain only scientific content plus the manifest
  hash, and are byte-identical whatever the recomputation history.

## Completed validation

`benchmarks/validation.json` records the actual regression suite:

- Original-versus-optimized raw graph jets at L5, L6 and L7 in both integration
  modes. Largest normalized continuous difference ~3.8e-21; largest degree-three
  power difference ~4.32e-11, with scale `max(1,abs(reference),abs(new))`. The
  absolute floor matters for cancelled poles. Fallback counts match exactly.
- One/two/four-thread executions produce identical optimized work rows. Power
  tile sizes 1, 7, 128 and 512 produce identical optimized rows in the tested cases.
- Three-shard QMC execution with sample chunks and restart merges to the
  unsplit result within 4.88e-18 normalized difference. Paired two-shard power
  execution agrees within 9.81e-20. Covariance is computed from two test
  replicates, not from the number of shards/checkpoints.
- Duplicate task IDs, attempted output clobber, negative shard index, missing
  checkpoints, and a corrupted checkpoint seed are rejected. A successful
  resume leaves checkpoint hashes unchanged.
- 608 independently coded point comparisons span long-double, binary128 and
  MP100, including logarithmic cluster ratios approaching -500.
- All **4,812 graph classes and 253,903 forest terms**, L2–L7, satisfy the sparse
  representation constraints (support, order, edge exponents and term degree).
- Native-to-portable decimal weight conversion yields identical integration
  outputs on this platform. Regenerating 560 L3/degree-four weights at 100 digits
  reproduces the original long-double array exactly.
- The 21-stream full production plan has valid paths, counts and paired degrees;
  continuous graph allocations exactly match the archived design. This is a
  plan validation, not a full new production run.
- Saved-data reassembly exactly reproduces archived full C7 and its sampling SE.

That record predates the 2026-09-25 review fixes, which added the following
checks. The first two run in `make test`; none of their results are in
`benchmarks/validation.json`.

- `tests/validate.py`: the QMC original-versus-optimized tolerance is tightened to
  1e-18 (the 21-digit print floor); original-versus-optimized power rows at
  degrees 1 and 5 for L5–L7; `campaign.py verify`, merge idempotency after
  deleting `audit.json`, and file modes 0644 under umask 022; and reproduction of
  every archived `final_analysis.py` diagnostic (below).
- `tests/test_pipeline.py`, pure Python with a fake integrator: plan/run/merge/
  verify/combine and index handling, all four binding-policy branches, the
  interruption and quarantine criteria above, concurrent duplicate workers,
  manifest-exact coverage, relocation with the original inputs removed, the
  stream-overlap and legacy-archive guards, combine rejections, the
  component reconciliation, and the Slurm template's `C7_INDEX_OFFSET` and
  `--cpus-per-task`.
- `tests/compare_binaries.py` (run separately; needs the git history): builds the
  baseline commit's and the current `src/` with one command line and requires
  identical decimal text of every row value and identical fallback counts on
  QMC L5–L7, power L5–L7 at degrees 1, 3, 5, 6 and thread/tile variants. Only
  the added `build` header key may differ.

`tools/assemble.py --original` now also reproduces the archived power levels,
resolution sequence, lower-order checks, spurious-pole z-scores, half-splits,
raw uncontrolled C7 (−355177.43) and applied zero-pole control (−31772.12),
to a largest relative difference of 2.1e-15 in the tested environment (the test
tolerance is 1e-9). The bootstrap SE differs because its resampling seed and
ordering differ (5606.8 versus the archived 5677.9). The allowance policy reproduces the archived 24000.

A separate **fresh binary128 original-code replay** on the archived L7/degree-three
stress selection gives normalized raw differences below 1.11e-13. The maximum
absolute change in the projected C7 contribution, evaluated in 50-digit
`Decimal` arithmetic from the saved rows, is 1.65e-13. The earlier statement
"below 1.34e-14" (1.33e-14 in `initial_fresh_quad_comparison.json`) had been
computed after rounding the rows to double. The replay still reads the same
native extended-precision weights; it is not a new arbitrary-precision
quadrature-weight construction. Logs and data are retained in
`benchmarks/replay_*` and `benchmarks/initial_fresh_quad_comparison.json`. These
records predate the delivered binary and carry no executable hash, so they
document the method and its size of effect, not the shipped executable.
`tests/check_quad.py` now records the SHA-256 of every executable it runs and
accepts `--inputs`, `--counts` and `--reference-ld`. The last also runs the
original long-double program, so original LD, optimized LD and binary128 are
compared three ways on one fixture. Accuracy is judged per element (replicate,
graph, slot) against that element's binary128 value; the per-slot maxima are only
diagnostics, because they can hide a regression in a small-magnitude row. Two
criteria are reported, and `--criterion` chooses which one sets the exit status:

- `strict` (the default, plan A5 as written): every element's optimized error is
  at most the original's.
- `rounding-floor` (a proposed amendment, set after the degree-3 run below): a
  genuine element may also be within 64·2^-64 of its own binary128 magnitude, about
  3.5e-18 relative. A structurally zero element, whose binary128 magnitude is below
  1e-12 of its row's largest slot, must stay below 1e-15 of that maximum.

Run it again on the target architecture with:

```bash
python3 tests/check_quad.py --out "$C7_WORK/c7-quad-check" --L 7 --degree 3
```

Degree-five replay fixtures also exist. A more expensive replay is appropriate
when raising quadrature degree or targeting errors far below the present level.
These are deterministic correctness checks, not statistical confidence intervals
or an independent field-theory derivation.

## Native binary inputs and portability

The original `.bin` files store native x86 extended values. The worker checks
size, endian and mantissa format before reading them. On a compatible x86
machine, convert once with

```
python3 tools/prepare_inputs.py reference/inputs --portable-weights
```

This writes decimal roundtrips with no loss of the stored values. Do this BEFORE
planning a campaign. A `.txt` representation added after planning a `.bin` job is
rejected because it would silently override the planned input.

On another supported GNU platform, use portable text, or generate new weights
in a **separate** directory:

```
python3 tools/regenerate_weights.py --out "$C7_WORK/weights100" --L 7 \
    --degrees 1 3 5 6 --dps 100
```

Higher-degree generation must be checked at increased precision
(`tests/check_weights.py`, next section). Do not assume 100 digits is sufficient
for every possible interpolation degree. Changing weight files or executable is a
new campaign, not a valid resume of the old one. Other architectures and
compilers were not benchmarked or certified here.

## Degree-6 to 7 refinement check

The archived estimator ends at degree 6. To test quadrature convergence, a
production may add the paired campaigns `power_refine7_L{5,6,7}`
(`production.py plan --refine7 --extra-inputs inputs_extra`): degrees 6 and 7 at
the refine6 allocation (8, 2 and 1 trees per graph; 8, 8 and 4 replicates),
rate 0.8, power selection. They have `role: "check"` in `assembly.json`. Their
level R7 = N7 − N6 is reported under `check_levels` and enters the headline
allowance below. It is **never** added to the estimate or its covariance.

New degree-7 weights `cw_L{5,6,7}_N7.txt` are generated with
`tools/regenerate_weights.py` at 100 and, separately, 150 digits. They are
admitted only after these checks:

- (a) every 100-digit value agrees with the 150-digit value to ≤1e-90 relative
  (absolute for values below 1e-90), and both round to the same long double;
- (b) exact monomial moment checks, the formula of
  `reference/code/check_meromorphic_weights.py` extended to N=7 over every axis,
  edge count, monomial and power: largest normalized error ≤1e-80;
- (c) regenerating degree 6 with the same tool reproduces the shipped
  `cw_L*_N6.bin` exactly after long-double rounding;
- (d) `tests/make_validation_inputs.py OUT` builds a **separate** validation input
  directory: copies of `reference/inputs`, `cw_L{5,6,7}_N7.bin` converted on x86
  from the 100-digit decimals with `numpy.longdouble` and checked value by value
  against the exactly rounded decimal, and `quad_replay_L7_N7.txt` with the
  selection of `quad_replay_L7_N3.txt`. On it, the original `reference_power`
  (which reads only `.bin`) and `bin/c7_integrate` (which reads the `.txt`) must
  agree at rounding level, ≤1e-13 of slot scale, on small L5–L7 workloads
  (`tests/check_degree.py --inputs OUT --degree 7`);
- (e) a binary128 replay at degree 7 on that selection
  (`tests/check_quad.py --inputs OUT --degree 7 --reference-ld`) compares the
  optimized and original long-double results with binary128 element by element.
  Results of the 2026-09-26 per-element run at L7 (112 elements):
  - In aggregate the optimized code is more accurate: projected C7 error 2.8e-12
    against 1.9e-11.
  - 9 elements fail the strict criterion. Two of them (graph 3205, replicate 0,
    slots 6 and 13) have optimized errors 18× the original's, 4.2e-14 relative; they
    are strongly cancelling elements where the reordered summation loses accuracy.
    Four more (graph 790, slots 4, 5, 11, 12) are at 82–187 units of 2^-64
    relative, at most 2.2× the original. These six also fail the rounding floor.
  - The cause is summation order, not the weights. The C++ parse of the decimal
    weights is bit-identical to the checked `.bin` values, and a run on the `.bin`
    weights gives identical results.
  - Degree 3 on the archived stress selection: 5 strict failures, all at or below
    27.6 units of 2^-64 (1.5e-18 relative), and no rounding-floor failures;
    projected C7 error 1.0e-13 vs 3.5e-12.

  Plan A5 ("no less accurate than the original") is therefore not met element by
  element. The deviations, at most 4.2e-14 relative per tree sample, are about
  1e-10 of the C7 sampling noise. The degree-7 weights themselves are validated
  by (a)–(d).

`tests/check_weights.py` runs (a)–(c). The admitted 100-digit files are stored
with their provenance in `inputs_extra/`; `reference/` is not modified. Passing
these checks shows that the weights implement the same rule at degree 7. It does
not by itself bound the quadrature error of degree 6.

## Pre-registered allowance

`tools/assemble.py` reports two allowances with all their components
(`allowance.candidates`):

```
headline_2sf      = ceil_2sf(max(4·SE, 2|R6|+4·SE_R6, 2|R7|+4·SE_R7, max half-split shift) + 0.01)
archived_ceil1000 = ceil_to_1000(max(4·SE, 2|R6|+4·SE_R6, max half-split shift) + 0.01)
```

SE is the sampling SE of C7. R6 is the C7 contribution of the refine6 level
(N6 − N5, summed over L5–L7 through the adjusted map), R7 that of the refine7
check level (N7 − N6), each with its SE. The half-split shift is the larger
change of C7 when every estimator stream is replaced by the first, or by the
second, half of its replicates. `ceil_2sf` rounds up to two significant figures;
the archived literal is the `final_analysis.py` policy, which rounds up to a
multiple of 1000. Without refine7 sources the R7 term is absent. On the archive
both give 24000, set by 4·SE = 23447.

The policy is fixed in advance, independent of the new values, and applied
mechanically. It is an empirical error policy, not a mathematical enclosure. The assembler flags a "systematic
tension" when the C5 or C6 lower-order check differs from its reference by more
than 3 SE; the allowance is not changed silently.

## Primitive sector: retained input or direct campaign

The 44 seventh-order primitive classes are the classes with `primitive && !power`. The inventory flag `primitive`
alone only means "no subdivergences"; the 20 power-containing classes that carry it are ordinary power-sector
classes. The sector enters C7 in exactly one of two ways:

- **Retained input** (the archived design): the earlier period estimate, −696147.45 ± 25.37, is added once. No
  source, whether free or power, may support a guarded class.
- **Direct campaign**: `campaign.py plan --mode qmc --L 7 --selection primitive` integrates the classes with the
  same coordinate-space sampler as every other graph. `combine.py --primitive DIR` adds that verified campaign as
  one unit-weight free source of level `primitive`. It replaces the retained input, which is reported as
  `retained_primitive_crosscheck` together with the z of direct minus retained.

`assemble.py` enforces the choice:
- source metadata must match the verified manifest (kind↔mode, loop, degrees, selection↔level);
- in retained mode no L7 source supports a guarded class;
- in direct mode exactly one primitive source supports exactly the 44 classes, and no other source supports any;
- the weighted coverage of every guarded class must be exactly 0 or 1.

Archived power records without counts are accepted only as authenticated power-only streams. The inter-batch χ² is
centred on the combined estimate with the retained primitive swapped back in, so it does not change when the
input is replaced. A 2^14-point, 32-replicate probe gave −696202.8 ± 46.9, consistent with the retained value
(z = −1.0).

## Statistical and scientific boundaries

The provided full assembler preserves the archived fixed controls and affine
coefficient map. The original primitive mean and standard error are used exactly
once. Raw graph/jet/campaign correlations are preserved by forming the complete
replicate first. A multilevel refinement is a correlated paired difference, not
an independent evaluation of each level.

Besides the estimate, the assembler reports the uncontrolled estimator (J instead
of the adjusted map for power streams) with its SE, and the applied zero-pole
control term per L and in total with SEs, so the size of the frozen controls is
visible.

Do not put overlapping random streams into `assembly.json` as independent inputs.
Do not refit allocations or controls using accepted production data without an
appropriate independent-training protocol. The assembler rejects a file used
twice anywhere, as a primary or a subtraction and including check sources
(compared by resolved path and content SHA-256). A paired subtraction must have
the lower degree and, for new campaign outputs, be complete, verified against its
campaign's audit, and share manifest, rate, seed, replicates and counts. Legacy
records are accepted only through `--original` or `legacy_archive: true`, and
only if their SHA-256 equals the entry in `reference/SHA256SUMS`. With a retained
primitive, the L7 continuous sources must give zero samples to every L7 class
flagged primitive in the inventory. Estimator components, the affine constant and
the primitive must reconcile with the total mean and covariance to 1e-9
relative. These guards still cannot infer every correlation in arbitrary
user-made configurations.

Narrower sampling error does not prove a smaller quadrature error. Degree-six
convergence (probed empirically, not proved, by the degree-7 check), inherited
lower inputs, primitive uncertainty, and shared graph/
renormalization assumptions remain separate. The optimized package does not
claim new C7 digits merely because the old-data analysis was reproduced.

### Primary documentation

[GCC] GNU compiler optimization options:
https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html

[Sobol] SciPy Sobol engine and balance-property warnings:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
