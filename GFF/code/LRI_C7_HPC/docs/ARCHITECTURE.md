# Implementation and migration map

## Source map

| File | Responsibility |
|---|---|
| `src/common.hpp` | Checked CLI/work inventory, selective graph loading, ordered-prefix representation, original cluster proposal and deterministic seed mapping, atomic sparse output with build metadata |
| `src/point.hpp` | Continuous LD/binary128/MP100 point functions, literal oracle, Sobol state reconstruction and unchanged precision escalation |
| `src/power.hpp` | Small quadrature weights, regularized geometry plan, tiled weight-signature evaluation and compensated meromorphic contraction |
| `src/c7_integrate.cpp` | Longest-work-first OpenMP task scheduling, thread-local scratch, exception propagation and profiling output |
| `tools/campaign.py` | Immutable campaign plan, checksummed checkpoint worker with affinity guard, payload digests, `verify`/`quarantine`, deterministic disk-backed complete-coverage idempotent merge |
| `tools/production.py` | Complete 21-campaign C7 plan (optional `--design`, `--refine7` check campaigns), self-contained input snapshot, Slurm-index lookup and idempotent full assembly |
| `tools/assemble.py` | Archived affine maps, frozen controls, paired covariance, one retained primitive input, archived diagnostics, pre-registered allowance, pairing/overlap/primitive/legacy guards |
| `tools/combine.py` | Verified combination of independent fresh-seed batches of one frozen design, inter-batch χ² |
| `tools/design.py` | Pre-registered per-campaign Neyman allocation from the archive and a pilot, written as a `--design` file |
| `tools/toolchain.py` | One compile-command builder (`CXX`, `CPPFLAGS`, `CXXFLAGS`, `LDFLAGS`, required flags, GCC 8 `-lstdc++fs`, `RPATH=1`) for every helper that compiles C++ |
| `tools/prepare_inputs.py` | Byte indices and native-to-portable quadrature weight export |
| `tools/regenerate_weights.py` | Original meromorphic Chebyshev rule generated as portable decimal text |
| `tools/profile.py`, `tools/benchmark.py` | Actual baseline phase profiling and alternating matched-sample benchmark suite |
| `tests/validate.py`, `tests/test_points.cpp`, `tests/check_quad.py` | Automated regression with the real binary, extreme point oracle and independent binary128 original-code replays (three-way with `--reference-ld`) |
| `tests/test_pipeline.py` | Pure-Python pipeline, restart, guard, combine and template tests with a fake integrator |
| `tests/compare_binaries.py` | Bitwise identity of the kernels against a baseline git commit |
| `tests/make_validation_inputs.py`, `tests/check_weights.py`, `tests/check_degree.py` | Separate degree-7 validation input directory with checked `.bin` conversions; precision, moment and shipped-degree checks of regenerated weights; original-versus-optimized jets at a new degree |

The old programs remain under `reference/code`. `tools/build_reference.py` makes
a temporary build copy and removes only hard-coded `num_threads(2/4)` clauses so
reference comparisons can use the same thread count. All numerical expressions
in those comparison programs remain the original ones.

## Why not one enormous MPI program?

The scientific independent units are graph/replicate streams. Their only coupling
is deterministic final summation and statistical covariance. Independent workers
plus a checked final merge avoid synchronous communication and replicated global
B×G×14 outputs. OpenMP handles shared-memory work inside each worker. Slurm arrays
handle node placement and retries. MPI is neither needed nor claimed to have been
benchmarked; an external MPI/job-pool launcher can dispatch distinct `run --index`
commands without altering the kernels.

## Data contracts

`C7TASKS1` rows carry global scientific indices and original full-stream counts.
The JSON work result stores 14 long-double roundtrips, fallback counts and timing
per row. It includes loop, degree, seed, rate, precision metadata, a `build`
record (compiler and Boost version) and, once committed, immutable provenance.
Tasks do not supply an alternative graph numbering scheme.

`C7IDX1` maps canonical graph IDs to byte offsets in a checksummed text inventory.
It is not a new serialization of the mathematics. Missing indices fall back to a
scan, but production should use generated indices. `C7WEIGHTS1` is portable decimal
text of the same meromorphic weights; `.bin` files remain untouched.

`manifest.json` (`schema: c7-campaign-2`) freezes worker inputs, RNG plan, block
placement and degree pairs. Its `inputs` path is relative to the campaign
directory when the inputs lie inside the enclosing production directory, and
absolute otherwise; the executable is an absolute path plus SHA-256, which a
`run --executable` override must still match. Each checkpoint's `provenance`
holds the manifest hash, checkpoint identity, the executable digest checked
before that invocation, the task-plan hash, command, host, threads, binding
policy, `payload_sha256` and `runtime_libraries` (resolved path and SHA-256 of
libquadmath, libgomp, libstdc++, libgcc_s, libm and libc from `ldd`, where
available). Legacy `c7-campaign-1` campaigns are still merged; their checkpoints
have no digest. `merged/N*.json` holds only scientific content plus the manifest
hash (`method: c7_hpc_complete_stream_merge`, `complete: true`, counts, seed,
rate, replicates). `merged/audit.json`, written last, lists every checkpoint
hash, output hash and complete-stream statistics.

`production.json` (`schema: c7-production-2`) records the batch `label`, seed,
global multipliers, the design file (content and SHA-256), the resolved
per-campaign settings, `refine7`, the job list and the executable with its hash.
The production directory is self-contained: `inputs/` is a copied snapshot of
every hashed input (plus `--extra-inputs` weights), `full_affine_assembly.json`
is a copy of the affine map, and all internal paths are relative.

`assembly.json` fixes stream weights, reference inputs, the retained primitive
mean/error and a `primitive_guard` inventory. Each source has a unique `name`, a
canonical `campaign`, a `level` (`free`, `coarse`, `refine3`, `refine5`,
`refine6`, or the check level `refine7`), a `role` (`estimator`, or `check`,
which is reported but never added to the mean or covariance), L, kind, weight,
`path` and an optional lower-degree `subtract`. `legacy_archive: true` admits an
archived record only when its SHA-256 equals its entry in
`reference/SHA256SUMS`; pairing is then validated from the archived metadata.
Result files identify sources by name, path relative to the config directory
and content SHA-256, never by an absolute path. Changing these contracts needs a
new campaign.

`tools/combine.py` compares a canonical scientific configuration of each batch,
as sorted JSON, for byte equality. It contains, per campaign, schema, mode, L,
degrees, rate, replicates, counts, selection, inventory count, the
`input_sha256` map, executable SHA-256, tile and scratch size; the source list
(name, campaign, level, role, L, kind, weight, path, subtract); the affine-map
SHA-256; the retained primitive and its guard; the design and its SHA-256; the
per-campaign settings; `refine7`; and the production executable SHA-256. Seeds,
matrix seeds and net hashes, absolute paths, timestamps and labels may differ.
The combined configuration (`combined_assembly.json`) uses batch-qualified source
names such as `b007/power_refine3B_L7` with weight divided by the number of
batches.

## From original drivers to cluster jobs

The archived `run_tree_production.py` launches one large process for each L.
The new `production.py plan` creates the same A/B, L5/L6/L7 allocations as separate
campaigns, with parallel stream blocks and explicit checkpointing. New seeds are
used for new measurements; pass a specific original net/seed to `campaign.py plan`
for literal point replay.

The archived power drivers call a different executable for each degree. The new
plan holds both degrees of each refinement in the same campaign. Each checkpoint
uses the same work file for the pair. A timeout between degrees only requires
rerunning the missing degree; the existing complete output is verified and reused.

The original `final_analysis.py` remains a historical reproduction program. The
new assembler reproduces its C7 mean, covariance and diagnostics, and applies an
allowance policy fixed in advance (NUMERICS.md) mechanically: a headline rounded
up to two significant figures that includes the optional degree-7 check, and the
archived `ceil_to_1000` literal. That is not a new convergence argument. The updated
streams have to justify their own quadrature/replicate stability through the
reported levels, checks and inter-batch scatter.

## Profile-guided future work

Per-work-unit durations and fallback counts can identify expensive graph strata
on the actual cluster. A new independently trained cost allocation can then be
frozen for a fresh campaign; do not alter allocations midway through accepted
production. `tools/design.py` does this only at campaign level, from a pilot's
per-row thread seconds; per-graph allocations stay frozen. `--profile`
accumulates geometry/weight/contraction and precision-tier seconds per thread.
Their sum is work time, not wall time in a parallel run.

Potential further improvements include NUMA-local process sizing, larger-grain
I/O checkpoints, cost-aware power-degree task placement, and a specialized
low-degree cache. The tested cache and power-prefix prototypes did not win and
were not enabled. A new quadrature algorithm, cancellation identity, lower-rank
compression or GPU port would require separate correctness/precision studies.
They are not silently bundled into this performance refactor.

## Provenance

All original reference files are verified byte-for-byte against the delivered
`LRI_1d_C7_full_numerical.zip`. New graph indices and the HPC manifest are additional
files only. The original TeX/PDF note and previously accepted raw production
streams are not rewritten. See `benchmarks/reference_preservation.json` and the
package SHA-256 manifest.
