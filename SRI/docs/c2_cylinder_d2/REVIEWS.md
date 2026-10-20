# Reviews: c2_cylinder_d2

Summaries only; the raw review logs and transcripts are not shipped.

## The supplied study (2026-10-12)

- Three Claude Code agents reviewed the supplied cylinder-Hamiltonian study (theory, solver, numerics) before any
  cluster work. Findings: the formalism is valid and the counterterms are complete, with
  C2 = -pi^2/(4 b0) + h0/b0^2. An independent rebuild of the solver reproduced the fourth-order sums to about 1e-11.
  The numerics gave about -4.067 +- 0.004. The precision limit was the lambda -> 0 regulator extrapolation together
  with N -> infinity at small lambda, and the historical order-2 and order-3 regulator fits were saturated (as many
  parameters as points). The reviewers recommended larger cutoffs (N = 512 pilot, N = 768 and 1024 rows) and an
  analysis that works at any N.

## Cluster layer for SDSC Expanse and symmetry (2026-10-12..13)

- Built by a Claude Code subagent; inspected by Codex (OpenAI, gpt-6-astra, effort xhigh) in fresh sessions.
- Inspection 1: REVISE with 12 findings (task selection, staged-plan identity, checksum verification, queue reuse,
  failure reporting). All were fixed in fix round 1.
- Inspection 2: REVISE with 9 findings (R2-001..R2-009: a manifest-traversal path in the grid fetch, unverified
  nested records in collection, the source-compatibility scope of the merger, record length and finiteness checks,
  resource-option validation, the probe guard, array-element retries, grid pruning, an upload check). All were fixed
  in fix round 2. The budget of two inspections was then used up, so the round-2 fixes are **not Codex-inspected**.
  The author then chose the clusters for production, and no third inspection was run.
- Throughout, the scientific diff is confined to the configurable leading-tail cutoff (default 2048, as before).
  Old and new code give byte-identical outputs with defaults (`validate`, `analyze`, `analyze-recorded`, `demo`, the
  N = 12 task).
- Cross-site check: the N = 512 pilot runs on Expanse and on symmetry are replicas (raw partial sums 2e-15 relative).

## Arbitrary-N continuum analysis (2026-10-13..14)

- Plan reviews by Codex (gpt-6-astra, xhigh), seven rounds:
  - Round 1, REVISE, 9 findings: propagate the mixed-fit spread, a collapsed-cutoff term, extraction checks of the
    new smallest-lambda records, the preferred-fit selection and its fallback, the joint-fit error, the legacy
    reproduction, the provenance of the solver source set, and the omitted cross-N comparisons.
  - Round 2, REVISE, 5 findings: extraction checks must cover the fitted windows; worst-case sign patterns; the
    fallback must propagate consistently; duplicate fits must not count toward validation; roundoff enters E.
  - Round 3, REVISE, 1 finding: the extraction-check records would displace the primary points. This led to the
    PRIMARY and DIAGNOSTIC pools.
  - Round 4: APPROVED (plan rev 4).
  - The rev-4 build gave C2 = -4.06705 with E(C2) = 2.21. 99.9 % of that came from an L1 worst-case grid-extraction
    rule, which the measured, smooth extraction profiles showed to be unphysical.
  - Round 5, REVISE, on the post-hoc amendment rev 5. The transport of profiles to unmeasured points was not
    validated, and one point lacked coverage.
  - The author chose to measure every point (A6-1: 20 direct extraction comparisons). Round 6, REVISE: per-category
    tolerances for the legacy comparison, and a defined fallback for a failed row.
  - Round 7: APPROVED (plan rev 7, sha256 f76af1bf...; the rules are copied into every output as `meta.rules`).
- Deviation D1 (author-approved, 2026-10-13): an SDSC Expanse Lustre fault made two metadata files of the N = 1024
  grids unreadable. Both N = 1024 grids were therefore rebuilt on symmetry (Intel defq) with the same parameters, and
  the nine stage A/B rows ran there. Recorded in `results/continuum_2026-10/evidence/DEVIATIONS_ANALYSIS.md`.
- Codex inspection 1 of the analysis code: REVISE with 7 findings, R001..R007:
  - pool membership and distinct-grid comparisons;
  - fallback when the preferred fit is unavailable;
  - the report for the no-estimate branch;
  - NaN leaves in the legacy comparator;
  - legacy statements read from a receipt;
  - replica differences serialized;
  - Markdown table escaping.

  Codex confirmed that the stored result and the budget arithmetic are consistent, that all 138 input hashes match
  and that the closed form is not an input. All seven findings were fixed (fix round 1); no number changed.
- Codex inspection 2 (the last budgeted round): REVISE with 4 hardening findings, IR2-001..IR2-004:
  - bind the sidecar and source metadata to the records;
  - publish the result files atomically (generations with a CURRENT pointer);
  - do not let the legacy subprocess inherit LRI_TAIL_CUTOFF;
  - validate the legacy receipt schema.

  Codex verified the 160 input hashes, the sidecar and source associations of the 16 production and 25 diagnostic
  records, and the absence of a closed-form input. The author decided to fix these without re-inspection (2026-10-14).
  The fixes (commits 2b710fb, a24c874, 98e1935) are **uninspected**; no number changed.
- Result, closed 2026-10-14: C2 = -4.0670498 +- 0.0023580 (outcome branch 4, joint fit; extraction coverage 25 of 25
  points measured). The error is a linear sum of systematic diagnostics, 64 % of it the regulator model; it is not a
  standard deviation.

## This export (2026-10-15)

- Built by a Claude Code session; not reviewed by Codex. The simulated-export tests are in `TESTS_c2_cylinder_d2.md`.
