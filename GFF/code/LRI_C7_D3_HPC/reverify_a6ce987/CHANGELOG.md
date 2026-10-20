# Changelog

## 2026-10-01 — archived-value gate follows the reporting rule (C7(3) results review, finding C7-RESULT-02)

- `assemble.gate_checks` now flags the archived C7(3) when the difference exceeds 3 archived SE (`in_archived_se`),
  as the reporting rule states. The combined-uncertainty pull is still reported, as a diagnostic only. Before, the
  combined pull was flagged, which could miss a difference above 3 archived SE when the new SE is not negligible.
- A regression check in `tests/unit_orchestration.py` covers the boundary (±3.1 and 2.9 archived SE with equal SEs).
- Run1's gate values are unchanged (+1.90 archived SE, no flags).

## 2026-10 — symmetry-ready release (fixes of the C7(3) and C7(2) reviews)

Native numerics are unchanged: `src/` is byte-identical. On the same toolchain the default build gives byte-identical
binaries (on symmetry: gmp `635428f9…`, decimal `24b2b941…`). `reference/` and `inputs/` are byte-identical.
Campaigns planned with the delivered tools (`c7-d3-production-1`, e.g. run1) cannot be run or merged by these tools.
They are re-verified and reported with `tools/report.py`.

**Integrity.**
- Every native call runs from a verified job-private copy of the executable, gamma table and Sobol net. Checkpoints
  record the runtime digests and the node and CPU, and merge and restart reject mismatches (L10).
- Assembly inputs are verified against the campaign's inputs manifest, with no import-time load (L15, plan review
  C7P-02).
- Plans verify every input file, packs included, and self-test the executable (L16).
- Only data-determining tools are pinned. `assemble.py` and `report.py` hashes are recorded as provenance (L9).
- URI-safe SQLite paths and `%`-escaped Slurm log paths (L11).

**Throughput.**
- Cost-ordered checkpoint blocks, defaults of 64 threads with 1024-task blocks, and a thread guard and warning (M4).
- Seconds-scaled shards (L4).
- The shipped symmetry cost model gives core-hour, wall-time and suggested `--time` estimates, and a projected SE
  (L2).
- Parallel group merges.

**Operations.**
- Resumable, concurrency-safe merge and idempotent result publication (L1).
- `production.py status|recover|tag|check-sbatch-args`, and one guarded submitter `tools/slurm_submit.py` with
  allowlists, environment filtering and a campaign lock (L2, L3).
- `slurm/merge.sh` no longer aborts on success (the run1 `grep` defect).
- Merges have their own wall time (`C7_MERGE_TIME`, default 1 h; found by the symmetry smoke drill, where the 2 h
  script default exceeded the debug partitions' limit). `--lanes 0` submits a merge for live lane workers.
- `run` refuses a missing index (L3).
- `verified duplicate` logging (L12).

**Lane mode (new).** Whole-node, claim-based workers for exclusive partitions:
- atomic claim files carrying their owner, and requeue reclaim;
- stale-claim release by owner state, a failure limit and a remaining-time guard;
- a merge that waits on every live worker;
- array mode and lane mode are never mixed.

**Statistics.**
- Seven-loop primitives use their frozen Neyman counts, and `--primitive-points` is removed (M3).
- Scored lower-order gates: the C6 reference updated to the 2026-09-29 C6(3) campaign; power differences; a/b;
  bootstrap; the archived C7 (M2, D3-3).
- Test-only results go to `C7_test_result.json` with every physical field under `test_partial` (L19).
- `--max-loop` prefix plans (L20).

**Seeds and nets.**
- Hashed per-group seeds by default. `--seed-scheme legacy` reproduces run1 and refuses used seeds (L8).
- Bounded public-API and GF(2) structure checks of every exported net (L5).

**Report tool (new).** `tools/report.py` gives a read-only re-verification of finished campaigns, the delivered
schema included, by data identity, with all gates.

**Tests and evidence.**
- `make test-replay` replays the archived production streams (D3-2).
- Strict replay gates: gmp bitwise, and decimal exact without MP promotion (L6).
- Every backend gets the thread and split tests (L14).
- Point checks cover the long-double tier (L7).
- Tests write records only with `--output`; records carry host, CPU and executable hashes (L7, L13).
- New tests: orchestration with a fake worker, legacy and archived seeds, assembly equivalence, delivered-tools
  campaigns.

**Build.**
- `OPTFLAGS`/`CPPFLAGS`/`LDFLAGS`/`LDLIBS` with non-droppable strict flags, the Boost ≥ 1.86 refusal and per-binary
  build info (L17, L18).
- Python ≥ 3.10 checks (L21).

**Fixes from the Codex code inspection (round 1).**
- Retained mode never integrates the seven-loop primitives, even with `--points` (they were counted twice), and it
  needs `--max-loop 7`.
- The retained a/b pull excludes the shared primitive SE.
- The cross-CPU result tolerance compares every float (scaled by its vector) and checks that the stored gates are
  consistent with the result's own fields.
- The report handles results with `bootstrap: null`.
- Build info parses flag values robustly, and a failed build-info step deletes the binary (`.DELETE_ON_ERROR`).
- Flags that override STRICT are refused in every user variable.
- The archived replay verifies the gamma table and every graph payload.
- Test and benchmark records carry the compiler and executable identity.
- Resumed lane indices are excluded from the throughput gate.

**Fixes from the Codex code inspection (round 2).**
- A result missing its gates, or with them moved, is refused.
- Lanes never exceed the plan's `checkpoint_tasks`. The default split adds lanes; a too-wide `C7_LANES` refuses
  before any claim.
- A lane stops after 3 consecutive failures.
- Each attempt writes its own log, and the throughput gate requires a single complete attempt.
- Benchmark and profile records carry the host, compiler and executable identity.

**Fixes from the Codex code inspection (round 3).**
- The lane worker's remaining-time query removes inherited `SQUEUE_*` filters.
- Slurm's answer takes precedence; `C7_LANE_SECONDS` is only the fallback.

**Fix from the Codex code inspection (round 4).** The wall-time check for plans without a cost model now reads
option names, never option values: a value such as `--job-name -trial` no longer counts as `-t`.

**Docs.**
- README, HPC, NUMERICS and PERFORMANCE are rewritten: the symmetry recipe, lane mode, CPU dependence (D3-1), Boost
  1.77, and the correct pack size (251 MB).
- `tools/write_delivery.py` regenerates the delivery manifest.
