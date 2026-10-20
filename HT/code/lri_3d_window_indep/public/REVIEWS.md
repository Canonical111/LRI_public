# Reviews: d = 3 finite-coupling HT (lri_3d_window_hpc, lri_3d_window_indep)

This file summarises the reviews of both packages; it replaces the raw review logs, which are not exported. Reviewer
is OpenAI GPT-6 astra through the Codex CLI at effort xhigh; host and builder is Claude Code (Claude Opus 5.5).

## 1. Expanse port (claudex loop, 2026-10-07)

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

## 2. L18/L20 projector repair (2026-10-08)

The author supplied a patch that adds a verified gesvd retry after a failed gesdd null-space SVD. It was applied
unmodified (33ef4f3).

- **Inspection 3** (fresh session, base e895443; the author approved a third round): REVISE with one medium finding.
  The repair was judged consistent by static inspection.
  - **L18-01:** `benchmarks/run.py` and `worker.py` would overwrite historical benchmark records that the audit pins.
    **Deferred, not fixed.** The receipt and the campaigns never run the benchmark tooling, and changing the patch's
    distribution files was left to the author. A runbook caveat was added instead (7de47eb).
- Receipt 54745249 passed, with 156 tests and the `validate_l18_fix` stage. Ladders N ≤ 16 rerun on the repaired
  code were bitwise identical to the earlier ones (24/24 records).

## 3. Not reviewed

- ccd055a (large-shared partition support) and b330ee7 (the `guard_cap_gib` opt-in, used by grid20 and grid20sri).
  Both change only `cluster/expanse/` and tests. Receipts 54762738 and 54779486 passed, and the numerical source hash
  is unchanged.
- The production results themselves: no separate results review. They are cross-checked by the independent solver
  (Sec. 4) and by the perturbative package. The latter is described in the independent-check report, Sec. A2, and is
  not quoted in the paper.
- `public/bp_x07.py`, the public tooling (`public.mk`, `public/*`), and this export.

## 4. Independent check (2026-10-08)

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

## Recommendations overruled or left open

- **L18-01** (Sec. 2): deferred by the author's choice, with a runbook caveat.
- **Calibrate the N-extrapolation before an N = 20 grid.** Claude Code recommended a calibration at weak coupling,
  with the perturbative package run to L = 16–20, before spending on an N = 20 grid. The author first ran one N = 20
  point (Ds = 0.6), then the scalar-only grid on Claude Code's recommendation. The perturbative runs to L = 20 were
  done in parallel (HT_Pert); they give the 60 % C₄ ratio quoted in the HT note.
