# Release evidence and development snapshots

## Records for the released default

`final_release_checks.json` is the release-level index. It binds the final source,
build records, numerical checks, workflow checks, and final performance evidence.
The released defaults enable exact rate palettes, persistent promoted scalars,
and the positive binary128 denominator-addition specialization. Grow-only
promoted vectors are disabled unless explicitly enabled at compile time.

| Record | Scope |
|---|---|
| `performance_summary.json` | Final default's controlled timing, memory, and thread scaling; separately identified development attribution |
| `final_native_release_checks.json` | 52 native cases at one and two threads; all 104 candidate outputs exact and telemetry verified |
| `final_default_kernel_checks.json` | Final source/build identities and freshly rerun direct/reference numerical tests for both backends |
| `final_default_kernel_points.json` | Independent 450-digit point and Taylor checks, with physical graph hashes |
| `hpc_scheduler_tests.json` | Pure task-layout, stream-validation, and cache tests |
| `hpc_cli_tests.json` | Real plan creation and mocked Slurm CPU/affinity/source-pin tests; no real scheduler submission |
| `optimized_graph_scheduling.json` | 368 native task replays across 24 groups, on the final GMP binary |
| `optimized_hpc_workflow.json` | Restart, corruption refusal, cache/staged native execution, and exact serial/parallel merging |
| `hpc_schedule_model_comparison.json` | Placement/checkpoint replay of one saved production task table; modeled cost, not a new native timing |
| `attach_inputs_checks.json` | Seven bounded tests of verified input attachment and atomic no-clobber publication |

The final numerical worker was built with GCC 13.3, Boost 1.74, GNU OpenMP,
libquadmath, and the recorded GMP dependencies. Its exact compiler commands and
source identities are in `bin/*.build.json`. Native binaries are intentionally
not packaged; rebuild on the destination cluster before planning new work.

The final native comparison ran concurrently with other correctness checks.
Its timing fields are not performance evidence. Controlled timing is identified
separately in `performance_summary.json`, with repeat ranges and limitations.

## Earlier development evidence

`kernel_optimization_checks.json` describes the earlier combined snapshot with
grow-only vectors enabled. It is preserved unchanged. Its `src/kernel.hpp` hash
is an as-tested identity, not the current default source identity. Matching
frozen candidate sources are under `optimization_work/kernel_candidates/`.
Likewise, earlier timing and attribution directories retain their actual binary
identities. They must not be presented as measurements of the final default.

The direct-test certificate recorded a benchmark-driver snapshot before a
later fix to the standalone baseline builder's metadata serialization. The
exact recorded script is preserved at
`optimization_work/final_default_validation_sources/benchmark_native.py`.
The adjacent `benchmark_native_source_mapping.json` verifies the mapping and
unchanged direct/replay execution functions. The numerical source and worker
binaries were unaffected by that metadata-only fix.

The baseline profiler instruments copied original sources. Its stage clocks
and allocation counters have measurable overhead. Use it to identify stages,
and use uninstrumented comparisons to measure speedups. The original kernel
and worker are included under `optimization_work/baseline_profile/original/`,
with their identities checked against `optimization_work/baseline_identity.json`.
The included baseline builder reproduced the original executable byte-for-byte
in this environment; other toolchains should compare the scientific outputs.

Absolute paths in saved reports describe where those checks originally ran.
The bundled frozen fixtures and `--baseline`/`--source` overrides allow replay
from another location. Full graph packs and historical production checkpoints
remain in the original C8 package. The optimized source release contains no new
full C8 sampling campaign and no revised sampling uncertainty.

## Archive verification

`RELEASE_MANIFEST.json` lists the packaged paths, sizes, and SHA-256 hashes.
The builder reads every archived member, checks CRCs, and verifies its digest
against that manifest before publishing the ZIP. Symlinks and full graph packs
are excluded. `tools/attach_inputs.py` connects an installation to the unchanged
full graph packs only after complete input-manifest and pack verification.
