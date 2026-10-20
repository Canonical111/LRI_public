# Authorship record (14 October 2026)

The project author states that OpenAI GPT-6 Astra (via ChatGPT) wrote both supplied two-dimensional C2
studies: the closed-form final-method study (`reference/original_study/C2_final_method.tex`, empty
`\author{}`) and the cylinder-Hamiltonian study (`LRI_C2_complete.zip`) on which this repository is based.
Recorded in `provenance/original_study_source_map.json` (`authorship`) and in the README. Documentation
only; no code, data or result changed.

# Continuum analysis, plan revisions 6/7 and deviation D1 (13-14 October 2026; not yet inspected)

## What changed

`LRI_C2_expanse_loop/PLAN_ANALYSIS.md` rev 7 (sha256 f76af1bf..., Codex-approved) replaces two parts of the rev-4
build below; every other rule, selection and central value is unchanged.

* Extraction uncertainty (A5-1, A6-1). The rev-4 L1 rule (sum_n |v_n| |delta_n| over sign patterns, with
  inheritance to points without a comparison) is superseded. On each selected spectral window the SIGNED
  full-coverage profile delta = primary - check is split into a least-squares cubic s and a residual rho, and
  eps_grid = max over the selected fits and over every full-coverage comparison of |v.s| + sum|v||rho|. All 25
  primary points now have a direct comparison covering n <= N (20 new rows, plan
  `cluster/analysis_checks_plan_rev6.json`), so nothing is inherited, transported or continued; the partial
  N=384 archived overlap is reported only. A point without a comparison would reuse its frozen rev-4 value
  (R6-002); none did. The rev-4 L1, the plain signed shift and max|rho| are still reported per point and through
  the budget weights (not in E). Limitation (in REPORT.md): a grid difference does not bound an error that both
  grids share.
* Legacy identity (A6-2, R6-001). The legacy outputs are byte-identical to the identical 11-case policy run on the
  scripts and data of the pristine commit 474487c on the same machine (all three JSONs). Against the shipped
  reference every leaf is classified (exact; values and residuals 1e-4; representative C2 1e-8; condition numbers
  gated at 10% relative; unclassified leaves fail): macOS passes with 2.2e-5, 4.5e-10 and 1.5%.
* The rev-4 outputs are archived in `results/continuum_2026-10/evidence/rev4/` (from d942b3c).

## Deviation D1 (user-approved, `LRI_C2_expanse_loop/DEVIATIONS_ANALYSIS.md`, copy in the results evidence)

Expanse Lustre stopped serving two small metadata files of the published N=1024 grids (stat hangs; from about
17:50 EDT on 2026-10-13), so stages A and B of the completion plan ran on symmetry instead: both N=1024 grids
(o4 r4.5 and o4 r4.0, sources eebafa82d841) were rebuilt there with the package's grid job and the nine rows ran
against them. Nothing was submitted on Expanse in rev 6/7 (0 SU). The rebuilt arrays could not be compared with the
Expanse ones (their checksums are on the unreadable Lustre); the measured profiles are consistent with the
Expanse-built checks (max|delta| 2.4e-7 to 1.4e-6 on the rebuilt r4.5 grid vs 5.5e-7 to 2.6e-6, and 1.8e-5, 4.2e-5 on
the rebuilt r4.0 grid vs 3.3e-5, 7.1e-5, falling smoothly with lambda). Left on Expanse for later cleanup: login01
pids 1327889 and 1305942 (stuck in Lustre I/O) and probe files `~/c2_*probe*.txt`.

## Cluster work (symmetry defq, no SU; details in `evidence/m4d_rev6_symmetry/jobs.txt`)

| job | what | node | elapsed | MaxRSS |
|---|---|---|---|---|
| 574330 | stage C rows 5+6 (N=512 pilot grid, 7 lambdas) | <NODE> | 0:20:51 | 21.4 GB |
| 574331 | stage C row 7 (N=512 pilot grid, 4 lambdas) | <NODE> | 0:20:55 | 10.7 GB |
| 574363 | grid N1024_o4_r4 (16 workers) | <NODE> | 2:37:25 | 115.8 GB |
| 574364 | grid N1024_o4_r4p5 (16 workers) | <NODE> | 2:43:25 | 113.6 GB |
| 574425_3 | stage B row 3: (1, 0.0625) | <NODE> | 0:33:36 | 51.0 GB |
| 574428_4 | stage B row 4: (2, 0.075) | <NODE> | 0:33:46 | 51.5 GB |
| 574434_0 | stage A row 0: (1, 0.0875), (1, 0.1) | <NODE> | 1:19:58 | 50.8 GB |
| 574436_1 | stage A row 1: (2, 0.125), (2, 0.15) | <NODE> | 1:03:25 | 51.5 GB |
| 574438_2 | stage A row 2: (3, 0.125), (3, 0.15), (3, 0.175) | <NODE> | 1:33:31 | 51.7 GB |

574425_4 and 574427_4 were cancelled by their submitter while pending (no truly idle defq node; six "idle" nodes
were another user's reservation). Rows were submitted one at a time, only onto truly idle nodes, so no job of
this task waited on defq. Task SU total is unchanged: 252.0 (318.9 if the rev-4 NODE_FAIL attempts are charged).

## Result (outcome branch 4, extraction coverage complete)

h0 = -3.413609 +- 0.003794, **C2 = -4.06705 +- 0.00236**; per order C2 = -4.06739 +- 0.0101, -4.06653 +- 0.0042,
-4.06622 +- 0.0035 (E_r = 0.0162, 0.0067, 0.0056 in h0); all order pairs consistent; joint fit accepted with 22
distinct admissible variants. E_joint components in h0: regulator model 2.44e-3, eps_prop 6.5e-4, eps_mix 3.4e-4,
eps_round 1.4e-4, eps_grid 1.2e-4 (rev-4 L1 on the same profiles 3.05, not in E), eps_coll 9.9e-5, eps_tailcut
4e-9. The central values are unchanged from rev 4; only E changed (rev 4: E(C2) = 2.21). These are numerical
diagnostics, not rigorous bounds.

## Fix round 1 (Codex inspection 1 of fa3858a..e4f9e91: 7 findings, all fixed; not yet inspected)

* R001: a merged index is accepted for a pool only if its plan is an approved one (`APPROVED_PLANS`: the production
  plan and the PILOT's earlier `cluster/expanse/expanse_plan.json` at cef281f for PRIMARY; the two
  analysis-check plans for DIAGNOSTIC), each record's plan sha256 and name match, and its task receipt (verified
  against SHA256SUMS) names the same plan and configuration. A record in both pools is refused, and an extraction
  comparison counts only between different grids (N, oversample, radius_cost), never a record with itself.
* R002: a preferred fit that the preferred window cannot support (fewer points than parameters) is recorded as
  unavailable and rejected; the fallback and the "insufficiently validated" rule then apply.
* R003: the outputs are built in a hidden temporary directory and moved into place only after REPORT.md is written;
  a no-estimate run (branch 1) renders the exclusion reasons and the no-estimate outcome.
* R004: a non-finite numerical leaf (NaN, infinity) fails the legacy comparison explicitly.
* R005: `run --legacy-receipt` reports the inspected legacy receipt (platform, python, numpy, sha256, pass/fail);
  without one the report states that legacy validation was not performed. The legacy receipt now records the
  numpy and scipy versions.
* R006: replica differences (max raw-chain and finite-cutoff h) are serialized and shown in a cross-site section.
* R007: pipes are escaped in every Markdown table cell and header, and a row with the wrong number of cells raises;
  the regenerated REPORT.md has 17 tables whose rows all have the header's cell count.

The final analysis was rerun with the same inputs plus the legacy receipt. Every leaf of the three JSON outputs,
excluding meta, is identical to the outputs of 2a70f5e; the only additions are the new fields
(`evidence/fix_round1/numerical_identity.json`). No cluster job was run.

## Fix round 2 (uninspected; user decision 2026-10-14)

The second and final Codex inspection (IR2-001 to IR2-004) found four integrity and edge-case defects; the
user chose to fix them without a further inspection, so these fixes are NOT inspected.

* IR2-001: a merged index is bound to the contents it names. The sidecar must be the record's own
  (`<record stem>_analysis.json`), and its embedded order, lambda and N, and its leading-tail order and lambda,
  must match the raw record. The science-source digest is recomputed from the verified task receipt's
  `source_hashes` and must equal both the index field and the expected set (eebafa82d841...). All 41 production
  and extraction-check records satisfy this.
* IR2-002: each run is published as an immutable generation `results/continuum_2026-10/generations/<UTC>_<pid>_<hex>/`
  (written as a hidden `.partial` directory, renamed when complete, files read-only), and the one-line file
  `CURRENT` is switched to it by a single atomic rename, under an O_CREAT|O_EXCL writer lock (`.writer.lock`; a
  second writer is refused). `CURRENT` is the source of truth. The top-level `REPORT.md` and JSON files are
  convenience copies of the current generation: each is replaced atomically after the switch, each names its
  generation (`meta.generation`, first lines of REPORT.md), `continuum_driver.py check` verifies them byte for byte
  against `CURRENT`, and `continuum_driver.py sync` restores them if a run was interrupted between copies.
  `evidence/` stays in place.
* IR2-003: the recorded-legacy subprocesses run with `LRI_TAIL_CUTOFF=2048` forced (the literal of the pristine
  474487c scripts; the scripts at HEAD read the variable), so an inherited value cannot change the policy; the
  historical commands `analyze` and `analyze-recorded` keep inheriting the caller's environment. The receipt
  records `tail_cutoff_forced`.
* IR2-004: the legacy receipt is schema-checked before any verdict: exactly the three legacy files with an explicit
  boolean for each in both the same-platform and the tolerance checks, pristine commit 474487c, the 11-case
  policy without (3, 0.35), the rev-7 tolerances, one comparison per file and the platform (python, platform,
  numpy). The report states PASSED, FAILED or INCOMPLETE (never PASSED for an incomplete receipt), or that legacy
  validation was not performed.

Tests (36 in total): a swapped lambda=0.0625 sidecar and tampered source digests are refused (planted indexes and
the real production index); an interrupted write leaves the previous generation current, a hidden partial
generation is never current, a second writer is refused, a new generation leaves the old one unchanged, and a
damaged top-level copy is detected and restored; an inherited LRI_TAIL_CUTOFF=8192 leaves the legacy outputs
byte-identical to the staged pristine run; incomplete and malformed receipts are INCOMPLETE and render as such.

The legacy receipt was regenerated (still PASSED: byte-identical to the pristine run, within the rev-7
tolerances), and the final analysis was rerun with the same inputs into the first generation,
20261015T000632Z_99019_1e66b9. Leaf by leaf, excluding meta and the fields added in fix rounds 1 and 2, the three
JSON outputs are identical to 2a70f5e and to 38b2aad: 0 changed and 0 removed (against 38b2aad only the new
receipt's sha256 inside legacy_validation differs; `evidence/fix_round2/numerical_identity.json`). No cluster job
was run.

## Tests

`code/continuum/test_continuum.py` 36 (after fix round 2; 32 after fix round 1, 23 before), `cluster/sitekit/test_sitekit.py` 84 (2 skipped, GNU only),
`cluster/expanse/test_expanse.py` 4, `cluster/symmetry/test_symmetry.py` 7, `cluster/test_cluster.py` 9: all pass on
macOS; `scripts/verify_manifest.py` passes.

# Arbitrary-N continuum analysis (13 October 2026; not yet inspected)

## Scope and status

Implements the approved plan `LRI_C2_expanse_loop/PLAN_ANALYSIS.md` rev 4
(sha256 bf30ba3c...) in `code/continuum/` and runs it on the archived records,
the 16 production records (one science-source set eebafa82d841...) and new
cluster evidence. Nothing under `code/hamiltonian/` changed and no file was added
there (the production source hash is asserted by a test); `scripts/run.py` gained
a `continuum` sub-command that only forwards to the new driver. The proposed
closed form of C2 is used nowhere; every selection rule is a constant in
`code/continuum/continuum_analysis.py` (`RULES`, committed in edf70d5 before the
final inputs existed) and is written into every output. The LaTeX note was not
edited. Results: `results/continuum_2026-10/` (`REPORT.md` first).

## Result (pre-declared outcome table, branch 4: joint fit validated)

h0 = -3.413609, C2 = -4.06705; per order C2 = -4.06739 / -4.06653 / -4.06622
(r = 1/2/3; h0 differences <= 1.9e-3). The quoted uncertainty under the plan's
rules is E(h0) = 3.56, E(C2) = 2.21, and it is 99.9% the extraction component
eps_grid: the plan's L1 worst case sum_n |v_n| |delta_n| (R2-002) multiplies the
measured raw-sequence differences (5e-7 to 7e-5) by the influence-row norms of
the selected spectral fits (sum_n |v_n| up to 2.4e5). The measured signed effect
of the same grid differences on h(lambda) is 7e-7 to 6e-5, and, propagated
through the joint fit (illustrative only), -6.0e-5 in h0. Without eps_grid the
joint E would be 3.7e-3 in h0 (2.3e-3 in C2), dominated by the regulator-model
spread (2.4e-3). This is reported as found; changing the extraction rule is a
plan decision, not made here.

## Cluster work

* M1/M2b auxiliary inputs: symmetry job 574247 (defq, <NODE>; amdq had no idle
  node, defq had 15), 6 min 9 s, no SU; mixed sums at 16384 for the 14 archived
  (r, lambda), two_point at 400000/800000 and A_face at tail 8192 (800000 and
  400000 norms) and 2048 (800000 norms) for all 25 (r, lambda). Where they overlap
  the production records, the recomputed two_point and A_face agree to ~1e-13
  relative and the mixed sums to ~1e-15 relative (another CPU). A first copy queued on Expanse shared (54898609)
  never started and was cancelled (0 SU).
* M4d extraction checks (`cluster/analysis_checks_plan.json`, DIAGNOSTIC pool):
  Expanse variant grid N1024_o4_r4 (54898601, 40 min) and rows 54898602_0-2
  ((1,0.075), (2,0.1), (3,0.1) on the published N=1024 r4.5 grid) and
  54899013_3-4 ((1,0.05), (2,0.0625) on the variant grid). Node <NODE> failed
  during rows 3-4 (NODE_FAIL after 53 and 47 min; Slurm requeued them, completed
  on <NODE>). An earlier submission of rows 3-4 on shared (54898607) never
  started and was cancelled. Total 252.0 SU, or 318.9 SU if the failed attempts
  are charged (ceiling 600). Details: `results/continuum_2026-10/evidence/`.

## Findings beyond the numbers

* A1 legacy mode runs the unmodified historical scripts under the recorded
  policy (11 transseries cases, raw-fit fallback for (3, 0.35), no new guards).
  It is structurally identical to `data/hamiltonian/reference` and byte-identical
  to `scripts/run.py analyze` on the same machine, but it is NOT byte-identical to
  the reference on macOS (nor, per `results/expanse/regression_expanse`, on an
  Expanse node): ill-conditioned lstsq leaves differ (value leaves up to 2.2e-5,
  representative C2 by 4.5e-10). Byte identity holds only on the platform that
  produced the reference; the test asserts it when C2_LEGACY_EXPECT_BITWISE=1.
* The radius-cost-4.0 variant differs from the production grid by 3.3e-5 and
  7.1e-5 in the raw sums at N=1024, 30-60 times the N=768-vs-1024 (both 4.5)
  differences; one comparison cannot say which grid carries the difference.
* The order-1 regulator-model spread (1.5e-2 in h0) comes from admissible
  {2,3,4} fits without the logarithm; the admissibility residual limit is set by
  the largest eps_spec in the window, here (1, 0.125) at N=256 (lambda N = 32).
* Five primary points lie below the lambda*N science minimum (flagged only).
* `submit.py` raised after submitting the first two jobs when the third sbatch hit
  the large-shared MaxSubmitPU = 4, so that submission has no record; and the
  sitekit names array receipt directories by the array job id, so later
  elements overwrite earlier ones (the per-row job receipts are complete). Both
  are pre-existing package behaviour, reported, not changed.

## Tests

`code/continuum/test_continuum.py` (17 tests), `cluster/sitekit/test_sitekit.py`
(84, 2 skipped GNU-only), `cluster/expanse/test_expanse.py` (4),
`cluster/symmetry/test_symmetry.py` (7), `cluster/test_cluster.py` (9) pass on
macOS (CPython 3.13.5, tested versions); `scripts/run.py analyze` and
`analyze-recorded` are byte-identical between fa3858a and this revision on the
same machine; `scripts/verify_manifest.py` passes for the regenerated manifest.

# Expanse revision (12 October 2026)

## Scientific status

The physics and numerics are unchanged: no matrix element, denominator,
counterterm, tail coefficient or conversion was modified, no preserved input
under `data/` changed, and no new value of C2 is claimed. The result remains
approximately C2 = -4.07. Only a smoke test and an N=512 pilot were run on
Expanse; the P1 (N=768) and P2 (N=1024) production stages were not launched.

## Changes to scientific code (configuration only)

The leading-tail auxiliary cutoff, previously the literal 2048, is now a
parameter whose default is 2048:

| File | Change | sha256 before -> after |
|---|---|---|
| `code/hamiltonian/exact_leading_tail.py` | `configured_tail_cutoff()` reads `LRI_TAIL_CUTOFF` (default 2048); `evaluate` unchanged | `3da70ce2...` -> `5641cdf9...` |
| `code/hamiltonian/reproduce.py` | `--tail-cutoff` (default `LRI_TAIL_CUTOFF` or 2048) for the diagnostic sidecar | `c9f78386...` -> `4341a4de...` |
| `code/hamiltonian/analyze_extended.py` | uses the configured cutoff; reuses a `leading_N384_*` record only if its cutoff matches (all shipped ones are 2048) | `8c4d973c...` -> `ff79902e...` |
| `code/hamiltonian/tail_transseries_fit.py` | uses the configured cutoff to select/evaluate the tail record | `a1c942a2...` -> `e9803a9c...` |

`cluster/run_task.py` accepts the optional plan keys `tail_cutoff` and
`stage`; rows without them give exactly the previous commands, and launched
tasks take the tail cutoff only from the plan (recorded in the task receipt).

Regression (`cluster/expanse/regression.sh`, evidence in
`results/expanse/regression_*`): `validate`, `analyze`, `analyze-recorded`,
`demo` and the N=12 cluster smoke task were run with the pristine package
(commit 474487c) and the new code under the same interpreter. All outputs are
byte-identical, except the timing fields `seconds`/`elapsed`, which are the
only differing leaves, on macOS arm64 (CPython 3.13.5, tested versions) and on
an Expanse node (Linux x86-64, CPython 3.13.5, tested versions; job 54887001).
Against the shipped `results/` (made on another Linux machine) the Expanse run
differs only at floating-point level: continuum h0/C2 estimates by at most
2.9e-10, while individual ill-conditioned model variants and diagnostics
(condition numbers up to ~1e17) differ by more; the macOS run shows the same
pattern. Bit identity across machines was never claimed.

## Additions

* `cluster/expanse/`: pinned environment (`setup_env.sh`), one-tarball staging
  with two checksum layers (`make_tarball.sh`), grid/task/probe job scripts on
  node-local NVMe with atomic, re-verified Lustre publishing (`*.sbatch`,
  `lib.sh`), resource monitor and receipts (`jobtools.py`), checked and
  throttled submission (`submit.py`), collection (`collect.sh`), comparisons
  (`compare.py`, `regression.sh`), the auxiliary-cutoff benchmark
  (`aux_cost_probe.py`), 31 tests (`test_expanse.py`) and a README with exact
  commands, monitoring, cleanup and SU estimates.
* `cluster/expanse/expanse_plan.json`: PILOT (N=512), P1 (N=768: orders 1-3)
  and P2 (N=1024: orders 1-2) rows with lambda*N >= 50/60/75, mixed cutoff
  16384 (was 4096), tail cutoff 8192 (was 2048), oversample 4 / radius 4.5,
  plus Expanse resource profiles and the pilot calibration.
  `cluster/extension_plan.json` is unchanged.
* `cluster/test_cluster.py`: one more test (optional plan keys).
* README section 9 and `cluster/README.md` point to the Expanse layer.

## Work run on Expanse (account <ACCOUNT>, 20.4 SU)

* Probe (job 54886830, large-shared): standard nodes have a 916 GB node-local
  NVMe shared by co-located jobs, large-shared nodes 2.9 TB; auxiliary cutoff
  cost and convergence at lambda=0.05, order 1 (`results/expanse/probe`). The
  selected mixed-sum median moves by 1.2e-7 from 16384 to 32768 (602 s, 43 GB
  per lambda) and the tail coefficient by 3.3e-5 from 8192 to 16384 on
  |A| = 3.07e5, which fixed the plan's cutoffs.
* Smoke chain (N=12, `cluster/smoke_plan.json`): tarball staging, checksum
  verification, grid job, Lustre publish, dependent task job, publish and
  `collect.sh`, through `submit.py` (`results/expanse/smoke`).
* PILOT (grid job 54886938, task job 54886939_0, large-shared, 16 cores): grid
  305 s, 22.2 GB anonymous peak; task 486 s for one lambda, 10.9 GB peak,
  1.5 busy cores. Its raw partial sums agree with the archived N=384 record
  (same oversample/radius family) on all 384 shared cutoffs to 4.4e-7
  absolute (1.2e-11 relative), and with the N=256 record to 1.1e-6
  (`results/expanse/pilot`). This is a grid-consistency check, not a
  continuum error bound.

## Multi-site extension (symmetry), 13 October 2026

The launch layer was split into site-independent code (`cluster/sitekit/`:
job scripts, driver, monitor, receipts, publishing, collection, the new
`merge_records.py` and `transfer_grid.sh`) and thin site folders
(`cluster/expanse/`, `cluster/symmetry/`: `profile.json`, environment set-up,
wrappers, tests). The plan became site-neutral (`cluster/production_plan.json`,
rows identical to the former `cluster/expanse/expanse_plan.json`, so the task
names and the published Expanse pilot are unchanged; the pilot's Lustre
directory was renamed from `outputs/expanse_plan` to `outputs/production_plan`).
Receipts now record the site, node, CPU vendor/model, package topology and
thread settings. Symmetry jobs follow the cluster rules (amdq first with defq as
fallback, `--exclude=cn112`, whole nodes packed one pinned process per package,
<= 12 h of the 24 h wall, BeeGFS + `/local1`, `c2ham-` job names, no
longq/preemptible queues). Scientific code is untouched by this step.

Checks: the Expanse regression (job 54887135) and N=12 smoke chain (jobs
54887136, 54887137_0) were rerun with the refactored package
(`results/expanse/refactor_check`); old and new outputs remain identical. On
symmetry (`results/symmetry`): the pinned environment was built from module
python/3.13-mamba (CPython 3.13.3, exact package versions); a node probe
(574034) found `/local1` to be a 568 GB rotating disk on the Intel debug node;
the N=12 smoke chain ran end to end (574035, 574036_0, numactl-pinned); the
Expanse and symmetry smoke records merge cleanly, their raw partial sums
agreeing to 5.5e-12 (about 3e-15 relative). The symmetry N=512 pilot (574037,
574038) and an AMD-node probe (574042) were queued on amdq, which was fully
allocated; they ran later (see the fix-round-1 section). The debug smoke
grid job preempted one preemptible preq job of another campaign (requeued by
Slurm).

## Fix round 1 (Codex inspection 1, 13 October 2026)

All 12 findings (2 high, 10 medium) were fixed in wrapper code; nothing under
`code/` or `data/` and no scientific default changed (commits acf5c7f,
432b2b0, 1e20419, e9f933d).

* R001: `submit.py` binds a submission to the uploaded tarball (login copy
  identical to the tarball; tarball/plan/source sha256 exported) and every job
  re-checks the binding after staging, before computing (exit 65).
* R002: every reserved `LRI_*` variable is set explicitly (empty when unused),
  `sbatch` gets no inherited `LRI_*`, and row jobs use an explicit
  `LRI_ROW_MODE` (array: `SLURM_ARRAY_TASK_ID` only; packed: `LRI_ROWS`).
* R003, R006: `cluster/sitekit/manifests.py` defines "complete" (non-empty,
  well-formed manifest that verifies, no unlisted files, required receipts and
  records); used by `submit.py`, the job scripts, `transfer_grid.sh`,
  `collect.sh` and `merge_records.py`; corruption stops with an error.
* R004, R005: queued work is identified by destination and task identity
  carried in `--comment`, not by job name.
* R007: merged records carry source hashes, plan sha256 and configuration;
  pairs are classified replica / variant / incompatible.
* R008: clean tarballs are reproducible byte for byte.
* R009: the Expanse normal-QOS guard counts running and pending jobs of the
  account against 22, without override.
* R010, R011, R012: probe and regression failures propagate; probe resources
  and overrides are validated like grid and task resources.

Two defects were found while validating the round on Expanse and fixed:
symmetry's Slurm path is appended rather than prepended (Expanse also has
`/cm/shared/apps/slurm/current/bin`, which hid the tests' fake squeue), and
`run_task.py` now treats an empty `LRI_WORKERS` as unset (grid jobs 54887413
and 54887415 failed on `int('')`). Expanse checks with the fixed code
(0.2 SU): N=12 smoke chain (54887425, 54887426_0); row selection with
`LRI_ROWS=0 LRI_TASK_INDEX=0 LRI_ROW_MODE=packed LRI_WORKERS=99` exported in
the submitting shell (54887427, 54887428_1: row 1 ran, as requested);
negative binding jobs (54887434_0, 54887435_0: exit 65); live duplicate
refusal and grid-job reuse; probe (54887438); regression (54887464, old and
new outputs identical). Tests pass on macOS and on both login nodes
(`results/fix_round1`). No symmetry job was submitted in this round (no idle
nodes).

The queued symmetry jobs had meanwhile finished. The AMD probe (574042,
<NODE>) found only 84 GB of node-local `/local1` on AMD nodes, so the N=768 and
N=1024 grids now run on Intel `defq` nodes (or are copied from Expanse). The
symmetry pilot (574037/574038, <NODE>, AMD EPYC 7543) agrees with the Expanse
pilot (EPYC 7742) to 6.9e-11 in the raw partial sums (2.1e-15 relative, all
512 cutoffs); the two-point, planar, curvature and tail constants are
bit-identical and the sidecar's finite-cutoff h agrees to 1.0e-9
(`results/symmetry/pilot`). Per lambda the AMD node was 2.8 times faster than
Expanse.

## Fix round 2 (Codex inspection 2, 13 October 2026; not yet inspected)

All 9 findings (1 high, 7 medium, 1 low) were fixed in wrapper code (commit
4508309); nothing under `code/` or `data/` and no scientific default changed.
Each fix has a regression test in `cluster/sitekit/test_sitekit.py`; the 16
new or changed tests fail on f264986.

* R2-001: no file name is taken from an unvalidated manifest. `lib.sh`
  copies `SHA256SUMS` first, validates the snapshot (`manifests.py names`),
  copies only those plain names, then requires a complete grid
  (`lri_fetch_grid`, which replaces `lri_fetch_dir`); `lri_publish_dir` and
  `transfer_grid.sh` follow the same order. `verify_dir` rejects unlisted
  subdirectories as well as files.
* R2-002: `collect.sh` indexes exactly the records listed by
  `manifests.py verify-rows` (`--records-from`); stray or nested files in a
  plan directory fail the collection.
* R2-003: every record must carry valid source hashes and a plan sha256, and
  a collection with more than one scientific source set fails unless
  `--allow-mixed-sources` is given.
* R2-004: one semantic validator (`collect_records.validate_record`: finite
  sequences of the declared lengths, cutoffs, order, lambda, file name) is
  used by the collector and by `merge_records.py`; the merger also checks the
  row's mixed and collapsed cutoffs.
* R2-005: resource values must be positive integers before anything is
  submitted.
* R2-006: probes count against the Expanse normal-QOS ceiling.
* R2-007: array jobs carry per-row tokens (`lri1;a=<row>:<tokens>`) and
  each `squeue -r` element is matched only to its own row.
* R2-008: rows are decided first and a grid is considered only if an
  unfinished row needs it; a finished stage submits nothing.
* R2-009: `make_tarball.sh --upload` fails if an existing remote code copy
  does not verify or cannot be created.

Checks (`results/fix_round2`): tests pass on macOS and both login nodes; the
local regression reproduces the old outputs exactly. Expanse (about 0.05 SU):
N=12 smoke chain (54888236, 54888237_0); R2-001 on the cluster: a held row
job (54888258_0) whose grid manifest listed `../../lri_c2/cluster/run_task.py`
stopped at the grid fetch with exit 74 and copied nothing. The grid was moved
to symmetry with `transfer_grid.sh`, and one smoke row ran there on an idle
`amddebugq` node (574051_0, <NODE>). Both sites' records were collected with
the new `collect.sh` and merged as replicas (max difference 0).

## Limitations

The arbitrary-N continuum analysis is still not generalised (see
`cluster/README.md`, section 5); new records are fixed-regulator inputs only.
Resource projections for N=768/1024 scale the pilot and are not measurements.
`analyze_fine.py` still selects mixed-sum fits with Nmin >= 2048, so at the new
mixed cutoff the fixed-lambda sidecar includes more fit windows; the raw
records keep every partial sum for a later analysis. The LaTeX note and its
PDF were not edited: their cluster section describes the previous revision,
and its statement that the sidecar uses tail cutoff 2048 now describes the
default of a configurable parameter. MANIFEST.sha256 was regenerated for the
new file set (scripts/verify_manifest.py passes).

# Cluster-readiness documentation revision

## Scientific status

This revision preserves the same scientific result and input records. It does
not claim a larger production run, a new fourth-order coefficient, a uniform
remainder proof, or additional physical precision. The Hamiltonian result remains
approximately C2 = -4.07. The 51-decimal-place arithmetic certificate still
applies only to the proposed closed expression.

`REVISION_SOURCE.json` identifies the prior reproducibility ZIP, verifies its
manifest, and compares every retained file in `code/` and `data/` byte-for-byte.
The original four archive lineages remain in `SOURCE_INVENTORY.json`; earlier
packaging notes and results are retained as historical provenance.

## Additions

The LaTeX note now consolidates the later cluster discussion as a full section:
ordered limits, independent error sources, proposed cutoff/regulator campaigns,
array allocation formulas, computational scaling, safe concurrent operation,
coefficient-cache reuse, resource-configurable launching, analysis limitations,
and precision acceptance criteria. The source remains one standalone file with
embedded references and tables. The main README and `cluster/README.md` explain
how all launch, validation, analysis, and documentation outputs are produced.

New software is confined to `cluster/`:

* `run_task.py` validates plans, generates reusable Ising grids, and stages one
  independent task under locks. CPU settings are runtime options; no memory,
  scheduler, allocation or wall-time requirement is imposed.
* `resource_estimate.py` reports two known allocations, not peak RAM or timings.
* `collect_records.py` indexes all arbitrary-cutoff/grid variants and optionally
  compares raw overlap boxes, without silently selecting a continuum result.
* `slurm_array.sh` is an optional allocation-neutral adapter.
* `test_cluster.py` exercises the new non-physical orchestration logic.

`extension_plan.json` is a **proposed, unexecuted configuration** for N=512/768/1024,
not new numerical data. `smoke_plan.json` is a deliberately tiny integration test.
The historical arbitrary-N analysis refactor is **not** claimed completed. Its
hard-coded routes/windows and auxiliary cutoffs are documented explicitly.

## Work actually rerun

`results/revision/` contains fresh finite scientific validation, saved-data
analysis, exact arithmetic certification, eight wrapper unit tests, exact array
size estimates, and one tiny N=12 cached-grid integration record. The completed
task skip path and raw-record collector were exercised as well. Serial and
two-worker generation of the same tiny N=12 grid agreed exactly in this test;
this is not a large-grid performance benchmark. The original
large production sequences were **not** recalculated. No scheduler was contacted
and no cluster job or multi-node performance benchmark was run.

The standalone note was compiled by copying only its .tex file into a temporary
directory and running pdfLaTeX three times. The build receipt records warnings.
All pages were rendered for layout inspection; no renders are included in the
final package. The delivered archive was extracted and its checksums and small
reproduction commands checked in that clean tree.

## Exclusions and limitations

No generated coefficient arrays, memory maps, Python bytecode, temporary staging
trees, writer locks, LaTeX auxiliaries, render previews, virtual environments,
font files, or duplicate source archives are delivered. Raw cutoff sequences,
auxiliary leading-tail input records, reference analyses and validation receipts
are intentional scientific or reproduction data, not discarded scratch.

Prepared-cache validation checks completion, source provenance, metadata and
array shape/size, not every byte on every consumption. Keep cache files immutable
and use an external archival checksum procedure if full large-array integrity is
required. A hard-killed process may leave a stale lock: determine that no writer
is alive before removing it. Task restart is coarse-grained, not per-lambda
checkpointing.

The optional Slurm adapter is syntax checked only. Actual memory, CPU, disk,
permissions and scheduling behavior must be tested on the intended cluster.
