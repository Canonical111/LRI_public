# Reviews of the HT packages

Summaries of the code and results reviews of each package (reviewer, rounds, verdict, what changed). Raw review logs are not published.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### Reviews: d = 1 finite-coupling HT (solver, analysis, records)

The review logs and transcripts are not published. Below, "Codex" means the Codex CLI with model gpt-6-astra at
effort xhigh. "Host" means the Claude Code session that coordinated the work and built the code.

##### Plan review of the symmetry port and window correction (2026-10-02)

Four rounds, the same Codex session throughout.

- **Round 1: REVISE, 8 findings.**
  - Two were high: a lease takeover race, and child shutdown leaving orphans.
  - Six were medium.
- **Round 2: REVISE, 3 new findings.**
- **Round 3: REVISE, 2 findings.** The online lease protocol and the forced-shutdown resume were now accepted.
- **Round 4: APPROVED.** No material defects remained.

##### Code inspections (fresh Codex sessions)

- **Inspection 1, snapshot 4dfd833: REVISE, 12 findings (2 high).**
  - High: done-marker identity, and an unscoped break of unreadable leases.
  - Medium: retry semantics, memory reservation against the planner, an absolute 1e-11 gate, window with
    reflection 1, validation without a baseline, baseline concurrency and pinning, seed-dir normalization, shutdown
    latency, and legacy options dropped silently.
  - All were fixed in 8e15875.
  - **Overruled for the running campaign:** the host judged that none of the 12 findings changed the numerics of a
    fresh single-manifest campaign. prod1–7 therefore kept running on 4dfd833, with absolute seed paths and memory at
    least 2× the planner envelope, so the two findings that could have applied (INSPECT-04, -10) did not.
- **Inspection 2, snapshot 8e15875: REVISE, 8 findings (1 high).**
  - High: a relative baseline path could compare the package with itself.
  - The others: USR1 during child start-up, completions not bound to the runtime, a stale completion cache, the Slurm
    requeue incarnation, break_lease identity, and two helper-script issues.
  - All were fixed in e2ca07c.
  - **The e2ca07c fixes were not re-inspected** because the inspection budget (2 rounds) was used up.
  - Validation 569279 passed with baseline equality 0.0.
- **Basis-integration inspection, 33998bb (2026-10-07): REVISE, 2 medium findings.**
  - BASIS-01: `scripts/calibrate.py` omits nz from its output directory, so nz 16 and nz 24 calibration records can
    collide.
  - BASIS-02: `scripts/audit_basis_convergence.py` silently skips a missing input directory.
  - Both were **accepted and deferred, not fixed.** dens_v1 used neither script: explicit `--mem-gib` and
    `--est-seconds` replaced calibration, and the 16- versus 24-state comparison used the host's own script. The
    shipped commit still has both defects.
  - The inspection found no numerical defect in the projected Hamiltonian, the Jacobian, the cross-cutoff use, the
    checksum binding, the training gates or the launcher handoff.

##### Results checks (host)

- **Window acceptance.** The production window reproduced 63/63 prototype records: |ΔΔ_ε| ≤ 2.4e-10 and level-1
  violations to 6.8e-10.
- **Basis checks.**
  - dens24 − dens16 differences at N = 36/40 are at most 1.8e-9.
  - dens16 differs from the nz 48/56 references at N = 32 by at most 6.4e-7.
- **Blind re-implementation (2026-10-08).** It agrees with production to 1.3e-9 against nz 48 records and to 4.8e-9
  against nz 24/32 records (38 points). Its weak-coupling C2(N) matches the exact formula to 3e-7. See
  `lri_dressed_phi4_independent_check/REPORT.md`.
- **Held-out-cutoff test (2026-10-09).**
  - Fits on N ≤ 32 predict N = 34–40 to 2.3e-6.
  - The local exponent stays constant at Ds = 0.125 and 0.1 but rises at 0.075 and 0.05.
  - As a result, the status of 0.075 became "one-sided" and that of 0.05 "unstable". This was a host decision,
    recorded in the HT note.
- **No Codex results review** was run on the d = 1 finite-coupling numbers.

##### Public-release replay (2026-10-13)

- The replay (`lri_dressed_phi4_hpc_analysis/public/replay_ht1d.py`) recomputes every quoted number from the records.
- It found three paper values that the stated estimators do not reproduce, and one that was quoted beyond its
  reproducible precision. The paper was corrected on 2026-10-13:
  - **Ds = 0.05 range of the F1/F2 fits:** 0.6220–0.6225 became 0.6220–0.6224. The upper end had come from two F1
    fits that the rms cut rejects.
  - **Largest fit half-spread at Ds ≥ 0.15:** "below 3e-5" became "at most 3.3e-5".
  - **Basis error:** 3e-6 became 1e-6. The 3e-6 came from an exploratory basis test that is not shipped. The shipped
    production records give at most 6.4e-7.
- **eps-series difference at Ds = 0.249:** -3.6e-8 became -4e-8. Its second digit depends on the numpy/scipy version
  of the refit.
- Three "about"/"up to" statements are now checked against explicit estimators, written in `quoted_numbers.json`
  (the raw violations, the residual of order 0.01, the reduction factors).
- The computable part of the status labels is now checked: stable, unstable (fits fail the stability rule while
  Delta(N) still rises), and no limit (Delta(N) falls at N = 40).
- "final" versus "one-sided" at Ds = 0.075 remains a judgement. It rests on the local exponent: still rising at 0.075
  and levelling off at 0.125 and 0.1. The trends differ only modestly, and no simple threshold separates them
  robustly.
- At weak coupling (Ds = 0.249, 0.24) the local exponent also rises slowly, by 0.39 → 0.46 and 0.50 → 0.57. The
  implied bias, below 1e-5, is far below the stated total error of 1e-4 there.

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

_Same text as under `lri_dressed_phi4_hpc` above; the package ships an identical copy._

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

#### Reviews: lri_dressed_phi4_independent_check

There was no external code review. The package is itself a check of the production solver.

- **Self-checks.** 64 unit tests; grid verification of every point; two full retunes on altered grids, which moved
  Delta_eps by ≤ 5e-12.
- **Comparison.** The host compared the results point by point with the production reference, which had been
  extracted before the subagent reported.
- **Spec notes raised by the subagent.**
  - The "Ev(0) = 0" wording of the window documentation is equivalent to its shift-invariant definition; the
    numerical agreement confirms this.
  - r = O(eps^2) at weak coupling, which is sharper than the brief's O(eps).
  - Neither changed any number.

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### Reviews of lri_2d_window_hpc (summary; raw review logs are not published)

Roles: the Expanse layer, fixes and campaigns were planned and built by a Claude Code session (Claude Opus 5.5). Plan
reviews and final-code inspections were done by OpenAI GPT-6 astra through the Codex CLI (effort xhigh), each
inspection in a fresh session. The numerical package was delivered before this work as `lri_2d_window_hpc_optimized.zip`
(baseline commit 4afd379), written by OpenAI GPT-6 astra (model stated by the author, 2026-10-14); its `reference/` port
and `upstream/` implementation come from the earlier delivery `lri_2d_dressed_window_basis.zip`, also written by OpenAI
GPT-6 astra via ChatGPT (model stated by the author, 2026-10-14). See PROVENANCE.

##### Plan review (2026-10-07), 7 rounds
| Round | Verdict | Findings |
|---|---|---|
| 1 | REVISE | 8 (1 high, 6 medium, 1 low) |
| 2 | REVISE | 4 (3 medium, 1 low) |
| 3 | REVISE | 7 (3 high, 4 medium), on the plan and the draft code |
| 4 | REVISE | 8 (2 high, 5 medium, 1 low) |
| 5 | REVISE | 2 medium (malformed persisted values; graceful-stop drill) |
| 6 | **APPROVED** | none (plan revision 6) |
| 7 | REVISE | 1 medium (malformed claim/owner readers), fixed; not re-reviewed (round budget used) |

The planned budget was 5 rounds; the author granted two more after round 5.

##### Final-code inspections (fresh sessions)
| Inspection | Code | Verdict | Findings | Fixed in |
|---|---|---|---|---|
| 1 | 914141f | REVISE | 8 (1 high: IR-01; 6 medium; 1 low) | 62b0c45 |
| 2 | 62b0c45 | REVISE | 6 (1 high; 4 medium; 1 low) | a0eb92f |
| 3 | a0eb92f | REVISE | 4 (1 high: release/receipt binding; 3 medium: Jacobian-condition checkpoint, basis integrity exit code, drills) | **889a968** |

The author granted the third inspection. **The fix-round-3 edits (889a968, the production code) were not inspected by
Codex.** They touch the release/receipt binding, the checkpoint of the Jacobian condition before the line search (iterates
and stopping decisions unchanged), the exit code of a basis-integrity failure, and the drill scripts. 110 tests and a
replay of the package's reference points (max |Δ| ≤ 1.1e-12, including x = 0.35, N = 8) passed on Expanse for this
release (validation receipt of 2026-10-07).

##### Host finding HF-01 (numerics)
The optimized package's ground-only top-window fixed point, followed by a re-check, aborted deterministically at
x = 0.35, N = 8 (any thread count). Fix (62b0c45): when the re-check misses the unchanged gate, continue with the
reference algorithm's k0-root iteration. The acceptance gate is unchanged; x = 0.35, N = 8 then reproduces the reference
to 3e-13. Reviewed in inspection 2.

##### Opt-in finite-difference Jacobian (afe69ab; shipped as public/afe69ab.diff)
Built after the production Newton solves at N = 24, Δσ = 0.125 and 0.126 stalled. Codex inspection: REVISE (2 findings:
metadata of the executed Jacobian; order of the metrics writer), fixed in afe69ab, then **APPROVED** by a fresh
inspection. It changes only the Newton direction when `--jacobian fd` is given; `DensitySolver.spectrum`, the residual,
the gates and every production record are unaffected. The valley scan ran on this release but calls only `spectrum`.

##### Overruled recommendations
None. Every plan and inspection finding was accepted and fixed.

##### Not reviewed by Codex
- The fix-round-3 edits of 889a968 (above).
- `public/scan_valley.py` (the N = 24 valley scan), `public/valley_expanse/`, and the public layer (`public.mk`,
  `public/replay_d2.py`, `public/smoke_check.py`, `public/verify_manifest.py`). The valley scan's smoke run at N = 8
  recovered the production root to 1e-11 with f1 = −4e-12; at N = 24 its first evaluation at the best Newton point
  reproduced the residual of the stalled FD-Newton run (|f2| bit-identical at Δσ = 0.126).
- The results: the finite-N statements and the fold estimate were not given a separate results review.

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

#### Reviews of lri_2d_window_indep (summary)

No Codex review. The check's independence rests on how it was written: the model was implemented from the method
description alone, without importing or reading the production code, with different numerics (README). It is not blind:
the writer was the Claude Code session that had ported the production package. Its
self-tests (`test_indep.py`) check the vertices against a brute-force Fock-space construction at N = 5 and the eigen-
solver against dense diagonalization; it then reproduced the production record at Δσ = 0.25, N = 8 to 4e-14 before the
cluster runs.

What the coordinator verified: the agreement is limited by the independent zero-mode truncation K, not by either code
(the differences fall with K: at N = 16, Δσ = 0.125, 6e-9 at K = 24 against 1e-12 at K ≥ 32; at N = 22, K = 32 they
grow about 9× per step with one sign); re-tuning from shifted seeds returns to the production root.

Overruled recommendations: none.

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### Reviews: d = 3 finite-coupling HT (lri_3d_window_hpc, lri_3d_window_indep)

This file summarises the reviews of both packages; it replaces the raw review logs, which are not exported. Reviewer
is OpenAI GPT-6 astra through the Codex CLI at effort xhigh; host and builder is Claude Code (Claude Opus 5.5).

##### 1. Expanse port (claudex loop, 2026-10-07)

Scope (author): review the supplied package, make it suitable for Expanse, have it reviewed by Codex. The numerical
source was out of scope and was not changed.

- **Plan review, 5 rounds, APPROVED in round 5.** 27 findings (R01–R27; 5 high, 22 medium), all accepted. Main
  themes:
  - immutable releases bound by sha256;
  - a validation receipt as a precondition of every campaign;
  - frozen campaign manifests with effective-argv validation;
  - continuation only from validated records;
  - safe stop and resume at Newton boundaries;
  - claims and recovery that never run a step twice;
  - accounting from Slurm billing.
  The reviewer worked statically and did not inspect the Expanse receipts, drills or calibration.
- **Inspection round 1** (fresh session, base b5f6e1f, head c78d257): REVISE with IR01 (high), IR02–IR05 (medium) and
  IR06 (low). All were accepted and fixed in 679b7c1:
  - a scrubbed-environment receipt with JUnit and fresh-report gates;
  - all-state squeue liveness;
  - retiring lane failures once their step has a valid output;
  - one canonical cache directory;
  - isolation of malformed records;
  - checkpoint and claim detail in `status`.
- **Inspection round 2** (fresh session, head 679b7c1): REVISE with IR07 (high) and IR08–IR10 (medium). All were
  accepted and fixed in 630a217:
  - explicit sbatch environment and journaled job names;
  - the sparse threshold in the runtime identity;
  - L and x owned by the campaign expansion;
  - a stop recheck before launch.
  e895443 then fixed a test fixture. **Fix round 2 and the fixture fix were not independently inspected**, because
  the two-round inspection budget was used up.
- **Live evidence on Expanse:**
  - receipts passed (final e895443: 122/122 tests and all validators);
  - stop/kill/duplicate drills A, C2 and D passed; drill B's stale-claim tombstone path was covered by unit tests
    only;
  - calibration campaigns matched the shipped baseline (N = 8, 10 to 8e-14);
  - repeated ladders were bitwise identical.

##### 2. L18/L20 projector repair (2026-10-08)

The author supplied a patch that adds a verified gesvd retry after a failed gesdd null-space SVD. It was applied
unmodified (33ef4f3).

- **Inspection 3** (fresh session, base e895443; the author approved a third round): REVISE with one medium finding.
  The repair was judged consistent by static inspection.
  - **L18-01:** `benchmarks/run.py` and `worker.py` would overwrite historical benchmark records that the audit pins.
    **Deferred, not fixed.** The receipt and the campaigns never run the benchmark tooling, and changing the patch's
    distribution files was left to the author. A runbook caveat was added instead (7de47eb).
- Receipt 54745249 passed, with 156 tests and the `validate_l18_fix` stage. Ladders N ≤ 16 rerun on the repaired
  code were bitwise identical to the earlier ones (24/24 records).

##### 3. Not reviewed

- ccd055a (large-shared partition support) and b330ee7 (the `guard_cap_gib` opt-in, used by grid20 and grid20sri).
  Both change only `cluster/expanse/` and tests. Receipts 54762738 and 54779486 passed, and the numerical source hash
  is unchanged.
- The production results themselves: no separate results review. They are cross-checked by the independent solver
  (Sec. 4) and by the perturbative package. The latter is described in the independent-check report, Sec. A2, and is
  not quoted in the paper.
- `public/bp_x07.py`, the public tooling (`public.mk`, `public/*`), and this export.

##### 4. Independent check (2026-10-08)

The author asked for "a fully independent check of the solver, to make sure it is correctly calculating what we
want". Claude Code wrote a clean-room solver (`lri_3d_window_indep`) from the method description only. It uses
deliberately different methods:
- a complex Y_lm Fock space with all M;
- the J = 0 space from the Casimir;
- vertices evaluated at a generic sphere point;
- a number-state local basis;
- Brent window fixed points.

It agrees with the production records:
- at fixed couplings to ≤ 3e-12 (N = 8–12, both schemes);
- after independent tuning to ≤ 1.9e-11 (23 comparisons);
- in the J = 1, 2 sectors to 3e-12.

The same report also concluded that **the finite model is computed correctly, but N ≤ 18 is not yet close to the
continuum**. At Ds = 0.7 the values move away from the resummed ε series, and standard N-extrapolations are biased
low. The paper therefore reports finite-N values only (the N = 20 column of Table tab:num3), and quotes no
extrapolated d = 3 value.

The check was not reviewed by Codex.

##### Recommendations overruled or left open

- **L18-01** (Sec. 2): deferred by the author's choice, with a runbook caveat.
- **Calibrate the N-extrapolation before an N = 20 grid.** Claude Code recommended a calibration at weak coupling,
  with the perturbative package run to L = 16–20, before spending on an N = 20 grid. The author first ran one N = 20
  point (Ds = 0.6), then the scalar-only grid on Claude Code's recommendation. The perturbative runs to L = 20 were
  done in parallel (HT_Pert); they give the 60 % C₄ ratio quoted in the HT note.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

_Same text as under `lri_3d_window_hpc` above; the package ships an identical copy._
