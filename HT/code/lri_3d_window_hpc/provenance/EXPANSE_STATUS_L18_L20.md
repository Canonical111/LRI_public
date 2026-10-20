# 3D dressed-window HT on Expanse: status, and what is missing for L18/L20

*2026-10-07.*
- Repo: `Agent_LRI/lri_3d_window_hpc` (local git). Baseline `b5f6e1f` is the unmodified zip; the final release is
  `e895443`.
- Review log: `lri_3d_window_hpc_loop/PLAN-REVIEW-LOG.md`.
- Expanse data: `/expanse/lustre/scratch/zzheng8/temp_project/ht3d`.

## 1. Summary

- **Ready up to L16.** Points are validated on Expanse, run as resumable per-x jobs, and are cheap:
  - one x up to L16 costs about 1.2 SU, and one L16 point about 1 SU (8–11 min, 5.2 GiB);
  - the whole 15-point grid to L16 is about 20–40 SU.
- **L18 is blocked by a numerical failure in the inherited solver.**
  - The scalar SO(3) projector (`code/ht3d/basis.py`, `_ranked_highest_weight`) builds each species block's null
    space with a dense SVD (`scipy.linalg.null_space`, LAPACK gesdd).
  - At L18 that SVD raises "SVD did not converge".
  - This happened in the setup probe, before any eigensolve.
- **L20 has never been attempted.** Everything about it below is extrapolation and needs a probe.
- **Nothing in the numerical code has been changed yet.** All work so far is the Expanse site layer. Fixing L18 is
  the first change that touches the numerics, with the provenance consequences listed in §4.3.

## 2. What was done

### 2.1 Scope rule kept so far
- **No numerical change:** `code/ht3d/*`, `code/*.py` and `inputs/prior_3d_points.json` are unchanged, so
  `ht3d.hpc.source_hash()` is identical to the baseline.
- **Manifest intact:** no file listed in `MANIFEST.sha256` was modified, and `tests/verify_manifest.py` still
  verifies all 615 original files.
- **New files:** 21 files, +2181 lines, all under `cluster/expanse/`, plus `tests/test_expanse_lanes.py`,
  `EXPANSE.md` and `.gitignore`.

### 2.2 Components (`cluster/expanse/`)

| File | What it does |
|---|---|
| `env.sh` | Module stack (cpu/0.21.2a, gcc/13.3.0, python/3.11.9, slurm), pinned venv, single-thread BLAS, node-local Numba cache; every step checked. |
| `requirements-expanse.txt` | Exact pins (numpy 2.3.5, scipy 1.17.0, numba 0.65.1, …). |
| `make_release.py`, `install.sh`, `stage.sh` | Deterministic release tarball + `RELEASE.sha256`; one-file install on Lustre; per-job node-local staging with full checksum, fail-closed (74). |
| `receipt.py`, `validate.sbatch` | On-node validation receipt (see 2.4). |
| `lanes.py`, `child.py`, `lane.sbatch` | One Slurm array element runs a cutoff ladder for one x (L6 teacher → L8 → … with seeds chained), resumable via `--resume`. |
| `campaign.py` | `freeze` / `submit` / `status` / `recover` / `resubmit`. |
| `probe.py`, `probe.sbatch` | Setup-only size probe (graph, projector, vertices; per-stage peak RSS). |
| `calib_report.py` | Per-step time/RSS/Newton/matvec table plus per-attempt SU. |
| `specs/` | `smoke.json`, `calibration.json` (stage 1, ≤ L14), `calibration_L16.template.json`. |

### 2.3 Defects found and fixed (all from review or on-node evidence)

**Plan review** (Codex, 5 rounds, APPROVED in round 5): 27 findings, R01–R27, all accepted and built.
- *Binding and integrity:*
  - never modify manifest files (R01);
  - validate a predecessor from a single byte snapshot (R04);
  - external inputs by role (R10);
  - validate the earlier campaign before a continuation (R21);
  - deterministic runtime identity (R03, R27).
- *Concurrency and recovery:*
  - serialized, owner-rechecked stale-claim recovery (R02);
  - exact individual job ids (R06);
  - submission intent journaled before sbatch, with liveness checked by job name (R11);
  - locked, no-overwrite freeze (R22).
- *Signals:*
  - no window in which a stop can kill a starting runner or child (R05, R23).
- *Spec correctness:*
  - per-cutoff and window overrides honoured (R13, R19);
  - effective argv validated, so runner-owned options cannot be smuggled in (R20);
  - outputs confined to the campaign directory (R14);
  - integer memory only (R26);
  - cache dir on all steps (R25);
  - one array per resource group (R08).
- *Accounting:*
  - memory-aware SU, requeue attempts included, UTC queries (R07, R15, R24).
- *Calibration design:*
  - L16 only as a measured continuation (R16, R18);
  - a real setup probe (R17).

**Code inspection** (two fresh Codex sessions): 10 findings, IR01–IR10, all fixed.
- IR01 (high): the receipt could pass with skipped or collect-only tests or `PYTHONOPTIMIZE`. It now runs under
  `python -E` with PYTEST_* scrubbed, and requires collected = executed (JUnit), 0 skipped, and fresh validator
  reports with passed=true.
- IR02: suspended jobs now count as live.
- IR03: stale lane-failure records are retired.
- IR04: a single canonical cache path.
- IR05: malformed records are reported invalid instead of crashing status.
- IR06: status shows claim owner and checkpoint.
- IR07 (high): inherited `HT3D_MANIFEST` could redirect a submission. Fixed with an explicit sbatch environment;
  the runner also refuses un-journaled job names.
- IR08: the sparse-parallel threshold is bound into the runtime identity.
- IR09: `--L`/`--x` cannot be overridden.
- IR10: stop recheck right before launch; the child exits 75 before claim or solver setup.

**Found by me on-node or in tests and fixed:**
- **Child killed at interpreter shutdown:** a re-forwarded stop killed a finished child, because CPython resets
  handlers at shutdown. The child now ignores stop signals after it returns.
- **Billing scale:** Expanse's billing TRES is cpu=3600, mem=1800/G with MAX_TRES, so SU/h = billing/3600.
  Verified on four job shapes; measured SU equals the estimate in every job since.
- **Two test-isolation bugs** that only show on a fresh Expanse node: NUMBA_NUM_THREADS changed in-process, and
  the Slurm job identity leaked into the tests.

### 2.4 Evidence on Expanse (final release e895443)
- **Validation receipt 54742071: PASSED.**
  - verify_manifest, the release checksum, pytest (122 collected = 122 executed, 0 failed, 0 skipped), and
    validate_physics / _numerics / _large / _benchmarks with fresh reports.
- **Smoke test against the shipped baseline** (x = 0.6): L8 and L10 Δ_thermal agree to 8e-14, and the scalar gaps
  to 2e-13.
- **Drills** (live Slurm jobs):
  - stop mid-L14 → exit 75 with a checkpoint → resubmit completes;
  - stop during staging → "stop requested before launch", exit 75;
  - a duplicate job with the same journaled name → exit 73 (output claim);
  - an un-journaled job name → exit 74;
  - recovery refuses while squeue still lists the owner.
- **Calibration** (x = 0.6 / 0.5182):

  | Cutoff | Matrix dim | Time per point | Newton | Matvecs | Peak RSS | Driver estimate | SU per point |
  |---|---|---|---|---|---|---|---|
  | L12 | 41,120 | 17–24 s | 5–6 | 3.2k–5.3k | 0.25 GiB | 0.76 GiB | ~0.02 |
  | L14 | 143,552 | 67–138 s | 5–6 | 3.5k–6.0k | 0.85 GiB | 1.95 GiB | ~0.1 |
  | L16 | 506,080 | 456–640 s | 5–6 | 4.1k–6.7k | 5.2 GiB | 8.54 GiB | 0.86–1.08 |

  - 8 threads give no gain over 4 at L14. At L16, 8 threads are up to 1.4× faster at the same SU.
  - Results are identical between the 4- and 8-thread runs.
  - Δ_thermal(L16) = 1.434394 (x = 0.6) and 1.417898 (x = 0.5182).

### 2.5 Known gaps in what was done
- **Not re-inspected:** the IR07–IR10 fixes (`630a217`) and the test-only fix (`e895443`). The inspection budget of
  2 rounds was used.
- **Stale-claim tombstone not exercised live:** Slurm's follow-up TERM always let the killed step checkpoint and
  release its claim. The path is covered by unit tests only.
- **Optional static cache untested on Expanse:** `--cache-dir` (graph/projector/vertex reuse across x) has not been
  exercised on Lustre.

## 3. Grid agreed so far
0.7499, 0.745, 0.74, 0.725, 0.7, 0.675, 0.65, 0.625, 0.6, 0.575, 0.55, 0.535, 0.525, 0.52, **0.518149** (replaces
0.5182).
- 0.518149 is 1.9e-7, about 8σ, above Δσ_SR = 0.518148806(24), so it is still on the long-range side
  (s = 1.963702).
- There are no shipped seeds at that exact x. Its L6 teacher will start from the 0.5182 L6 couplings via
  `--guess`, in its own one-x campaign.

## 4. What is missing for L18

### 4.1 The blocker
- **Where:** `code/ht3d/basis.py:353` (ranked path; the legacy path has the same call at line 264):
  ```python
  Q=np.eye(len(inds)) if not len(target) else null_space(jp,rcond=5e-13)
  ```
- **What this code does:** for every species block it forms the dense J+ block `jp` (targets × sources) and takes
  its full null space by SVD to get the highest-weight (scalar) states.
- **What happened:** probe job 54739261 at x = 0.6 failed with `numpy.linalg.LinAlgError: SVD did not converge`
  after 190 s, at 6.3 GiB peak RSS, in the projector stage. The L18 graph itself was built.
- **Not yet known:**
  - which block failed, and its size and conditioning;
  - the L18 graph size and time (the probe that failed predates per-stage records);
  - whether the failure is only gesdd's convergence (gesvd usually succeeds) or genuine ill-conditioning.
- **Also affected:** the same routine builds the spin-1 and spin-2 projectors used by diagnostics, so
  `--diagnostics first/all` at L18 needs the same fix.

### 4.2 Fix options (to be decided and reviewed)
1. **Minimal (recommended first):** on `LinAlgError`, retry `null_space(jp, rcond=5e-13, lapack_driver='gesvd')`.
   - Blocks where gesdd converges keep the exact current projector, so L ≤ 16 stays bit-identical.
   - Only failing blocks change path. The existing residual and orthogonality gates (`|J+Q|`, `|QᵀQ − 1|` ≤ 1e-10)
     still check the result.
2. **Robust alternative:**
   - Compute the kernel from `eigh(jpᵀ jp)` (or `jp jpᵀ`) using the known su(2) spectrum: the non-zero eigenvalues
     j(j+1) − m(m+1) are bounded away from 0, so the gap is exact.
   - This is cheaper and well conditioned. But it changes the null-space gauge at every L, so results agree only
     to roundoff, not bitwise, and static-cache entries are invalidated.
3. **Needed only if blocks become too large at L20:**
   - sparse or iterative null spaces;
   - a finer species decomposition (more conserved labels per block) to keep the dense blocks small.

### 4.3 Consequences of any fix (provenance and validation)
- **New identity:** `basis.py` is part of `source_hash()` and of the static-cache implementation hash. Any change
  means a new source identity and a new release and receipt. Old campaigns cannot be resumed across it; the
  runner refuses them.
- **Manifest check:** `MANIFEST.sha256` lists `code/ht3d/basis.py`, so `verify_manifest` will fail by design. To
  decide:
  - (a) keep the original manifest and verify all files except an explicit list of intentionally changed ones;
    or
  - (b) cut a new versioned distribution manifest (0.2.1) and keep the original one as provenance.
- **Benchmark audit:** `tests/validate_benchmarks.py` checks the shipped benchmark records against the current
  `basis.py` hash, so it will fail as well. Either regenerate the benchmark records on Expanse, or record that
  stage as expected-stale for the listed files. Either way, the receipt gate needs an explicit rule.
- **Regression requirements:**
  - L ≤ 16 bit-identical with option 1, or within roundoff with option 2, against the existing calibration
    outputs (L8–L16, x = 0.6 and 0.5182);
  - a unit test that forces the fallback path;
  - the inherited physics, numerics and large validators.

### 4.4 Resource settings L18 will need (extrapolated, ×5–7 time and ×4–6 memory per +2 in L)
- **Size:**
  - full bath states ≈ 41M (L16: 8.78M) → `--max-bath-states` ≥ 50M;
  - scalar states ≈ 56k → matrix dim ≈ 1.8M;
  - bare-vertex nnz ≈ 170M (L16: 21M).
- **Memory:**
  - peak RSS ≈ 25–35 GiB;
  - the driver's guard estimate ≈ 35–40 GiB, and it over-estimates by 1.6–2.3×;
  - so `--memory-limit-gib` about 40 and `--mem` 48G. `max_basis_bytes` = memory_limit/4 is then large enough for
    the graph.
- **Time and cost:**
  - about 40–75 min per point;
  - with 48G the charge is set by memory (24 core-equivalents), so use 16–24 cores, which is free in SU;
  - about 20–30 SU per point, about 300–450 SU for the 15-point grid.
  - This supersedes the earlier rough "~250 SU" figure.
- **Signal lead:** a stop only lands at a Newton boundary, so `lead_s` should exceed one Newton step (estimated
  10–15 min at L18). Otherwise a wall-time stop loses up to one step, which is resumable.
- **Static cache:** the graph and projector are x-independent. Building them once in a shared static cache and
  reusing them across the 15 lanes would save the repeated projector cost, which grows quickly. This needs a
  Lustre test (atomic rename, concurrent readers) first.

### 4.5 Steps to an L18 calibration
1. Implement option 1 plus a fallback unit test. Decide the manifest and benchmark-audit rule (4.3).
2. Review: Codex plan check and inspection of that change.
3. Build a new release and run its Expanse receipt.
4. Regression: re-run calibration L8–L16 (bit-identical check) and the smoke test.
5. Probe L18 (and L20; see §5) with per-stage records: graph, projector (including the largest block and the
   fallback count), vertices, peak RSS.
6. Freeze an L18 continuation from the validated L16 records (x = 0.6 and 0.518149), sized from the probe. Measure
   time, RSS and SU, then do the final L18 budget.

## 5. What is missing for L20 (nothing measured; pure extrapolation)
- **Size:**
  - full bath states ≈ 190M, so the graph alone is probably 15–25 GB;
  - scalar states ≈ 200k → matrix dim ≈ 6.4M;
  - vertex nnz ≈ 1–1.5 B. That is close to the int32 index limit (2.1 B), which needs a check of the scipy and
    numba kernels' index widths.
- **Memory:** probably 150–250 GiB. That is at or beyond the `shared` partition's 243G, so likely a whole
  `compute` node (240G) or `large-shared`.
- **Time and cost:** about 4–9 h per point. A whole node costs about 128 SU/h, so roughly 0.5–1k SU per point and
  8–15k SU for 15 x. That is still small against the 22.08M SU allocation.
- **Projector feasibility is the real unknown.** Dense SVD per species block scales as n³ in time and n² in
  memory. At L20 the largest blocks may make the current algorithm infeasible regardless of the L18 fix, which may
  force option 3.
- **Before any L20 budget:**
  1. a setup-only probe at L20 (after the L18 fix) recording the block-size distribution, projector time and
     memory;
  2. then one L20 point at x = 0.6 as a continuation from validated L18.

## 6. Open decisions for you
1. **Fix option** for the projector (4.2). Recommendation: option 1 first.
2. **Provenance rule** for the changed numerical file (4.3 a or b), and how the receipt treats the stale benchmark
   audit.
3. **Side checks and diagnostics** for production. The baseline used nz12 and a raw replay at L10, with
   `--diagnostics all`. Spin-2 diagnostics at L18 also depend on the fix.
4. **Order of work:** run the 15-point grid to L16 now (about 20–40 SU) while the L18 fix is developed, or wait.
