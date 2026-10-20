# Reviews of the MC protocols, code and results

Summaries of every review (reviewer, rounds, verdict, what changed, what was overruled). Raw review logs are not published.
Reviewer: OpenAI Codex (gpt-6-astra) unless stated. "Approved" means the reviewer found no unresolved material defect in that exact
revision (bound to its SHA-256).

Codex ran at reasoning effort xhigh where the logs record it. Plan reviews used one continued reviewer session per protocol; code
inspections used a fresh reviewer session per round. The builder and coordinator sessions were Claude (Anthropic). The three
simulation engines were written by GPT-6 astra (OpenAI, via ChatGPT); the fit pipelines, protocols, evaluators and analyses by Claude.

## Summary table

| subject | reviewer | rounds | final verdict | open at the end |
|---|---|---|---|---|
| d=1 campaign plan and v1 rules | Codex | 5 plan + 2 code | REVISE; run on the author's override | rev 6 unreviewed; fixes uninspected |
| d=1 protocol v2 (FIT_PLAN) | Codex | 5 plan + 3 code | APPROVED at rev 4 | scan addendum and last fixes unreviewed |
| d=1 protocol v3: plan | Codex | 11 | APPROVED at rev 14, after N1/N0 data | none in the plan text |
| d=1 protocol v3: code | Codex | 23 | REVISE each round; 114 findings accepted | fix round 23 uninspected |
| d=1 campaign report | Codex | 3 | APPROVED | reproduction not re-run by the reviewer |
| d=1 independent audit | Codex | 1 + follow-up | no physics-path defect; 6 findings | F3, F4 not in the code; 0.15/0.175 open |
| d=2 protocol | Claude, then Codex | 1 + 3 | REVISE; never approved | rev 5 frozen, round-3 fixes unreviewed |
| d=3 protocol | Codex | 7 | APPROVED at rev 5; amendment REVISE | one-line fix of round 7 unreviewed |
| d=2,3 results (data sufficiency) | Codex | 1 | advisory | none |
| Amendment P1: plan | Codex | 4 | APPROVED at rev 4 | none |
| Amendment P1: code | Codex | 2 | REVISE; 8 findings fixed | round-2 fixes uninspected |
| Engine lri_cluster (d=1) | Claude | 1 + pilot | no defect found | none recorded |
| Engine lri_1d_precision (d=1) | Claude; Codex | benchmark + check; 2 code | no finding on the integration | none recorded |
| Engine lri_precision_v2 (d=2,3) | Claude | 1 | no physics-path defect | 8 minor findings (fixes not recorded) |
| Release package (2026-10-07) | none | 0 | not reviewed; reproduction check | two platform-sensitive d=1 labels |
| Pre-release review (2026-10-13) | Claude Opus 5.5 agents | 5 lenses + verification | accepted, mostly implemented | not-blocking list |

## d = 1

### Campaign plan and v1 rules (EXPANSE_PLAN), 2026-09-14
- Subject: the submission plan of the two-point campaign (Δσ = 0.0625, 0.1) with its pre-registered v1 acceptance rules.
- Plan: 5 rounds, all REVISE; 22 findings (EXP-001…022), all accepted. Examples: a minimum number of valid bootstrap draws,
  local-fit quality in the quotient criterion, a σ_sys definition that could not certify itself, completion checks against the manifest.
- After round 5 the author ran revision 6 without approval (an explicit unreviewed-specification override).
- During the build two rules were amended without review: the held-out adequacy test (|pull| ≤ 1 instead of a coverage fraction)
  and criterion 2 (group-level limits plus a 2 % population cap).
- Code: 2 inspection rounds (12 and 9 findings, EXP-023…043), all accepted; one was a missing acceptance evaluator, then written.
  The second-round fixes were not inspected.
- Outcome: the v1 rules gave INCONCLUSIVE at both points (no fit of the pre-registered family reached χ²/dof ≤ 1.5). This led to v2.

### Fitting protocol v2 (FIT_PLAN), 2026-09-16
- Written after the v1 fits had been seen. Approved before the v2 model selection first ran on the data; a regression check of the
  extended fitter on the two-point data ran before round 4.
- Plan: rounds 1–3 REVISE, round 4 APPROVED revision 4 (SHA-256 c356a2cf…). 10 findings (FIT-001…010), all accepted: degree-ladder
  ceiling, a uniquely defined crossing cross-check, extrapolation gates, correlation between the two estimators, no σ_sys from a
  single fit, a calibrated residual-structure test, χ² cuts on central fits only. The reviewer stated that approval covers the plan only.
- Code: 2 inspection rounds (9 and 3 findings, FITV2-001…012), all accepted. Examples: production status tied to every setting,
  reproducible calibration seeds, provenance hashes, saved cross-check samples, draw-level isolation of numerical exceptions.
- Scan addendum (revision 5): plan round 5 REVISE (3 findings); a third inspection, authorised by the author, REVISE (6 findings).
  All nine were applied. Both budgets were used up, so revision 6 and these fixes are unreviewed.
- One rule was a builder's implementation decision, not in the plan: a flagged or missing fit at degree d or d+1 stops the F-test
  ladder at d. The v3 plan later states it explicitly. It is the rule behind the two platform-sensitive labels and the robust-ladder
  study (below).

### Fitting protocol v3 (FIT_MODEL_V3): plan
- Written 2026-09-18 after the v2 analysis of all 20 points; those records were the planning evidence.
- v3 replaced v2's absolute σ_sys cap by a ratio label and the per-group hot/cold gate by a population rule. Under v2 the cap had
  blocked Δσ = 0.0125–0.05 and the per-group gate 0.0875 and 0.125 (one group of 50 at hot/cold z = 3.04–3.05 each).
- Pre-build rounds 1–7: all REVISE; 25 findings (V3-001…025), all accepted. Rounds 1–4 shaped the model (union of old and new
  data, in-window crossing family, complete decision table, reblocking as a prerequisite, independent seeds, quotation order).
  Rounds 5–7 concerned only the N0 diagnostic.
- After round 7 the author authorised N0 (a dense-window diagnostic run) and N1 (v3 on the existing data) under revision 8,
  which was unreviewed (last verdict REVISE).
- N0 under the pre-registered rule: INCONCLUSIVE. The pre-registered remedy (a retest at δ/2) was not run; the author chose to amend
  the rule. Revision 11 gave a provisional FAIL, traced to degree under-selection by the values-only reference.
- Post hoc rounds 8–11 reviewed the amendments: round 8 REVISE (2 findings), round 9 REVISE (4; revision 12, the joint polynomial
  test), round 10 REVISE (2), round 11 APPROVED.
- Approval: round 11, revision 14, SHA-256 f05b835b…, 2026-09-19, after the N1 results and the N0 data had been seen. The reviewer
  accepted the N0 PASS "under the disclosed amended protocol"; approval does not cover the code for merging N2 with the old data.
- 33 plan findings in total (V3-001…033), all accepted. N2 (new data at 14 points) followed the approval, with x_max = 0.35 from N0.

### Fitting protocol v3: implementation
- 23 inspection rounds, 2026-09-18 to 2026-09-20, each by a fresh Codex session. Every verdict was REVISE.
- 114 findings (per round 17, 9, 7, 7, 5, 5, 5, 7, 3, 4, 4, 3, 4, 5, 4, 4, 4, 3, 3, 4, 3, 2, 2), all accepted:
  - findings that the union-data schema was missing (rounds 1–4) were deferred to the N2 build; it was built and inspected in
    rounds 5–12 before any N2 data were merged;
  - one finding (R16-003: a §5.0 requirement cannot be met with nine temperatures) became a documented deviation in the code,
    because the approved plan text is bound to its hash.
- Rounds 1–12 covered the evaluator, the N0 code, the integration of the faster d=1 engine and the union-data schema. Fixes include
  crossings of unequal-degree polynomials (a pair had been lost silently), a campaign code in the bootstrap key, the log-correction
  variant, authentication of every input's lineage and coverage, and no quoted value for EQUILIBRATION FAILED.
- Rounds 13–23 found mostly orchestration defects (registry locking, job submission, watchers). A few touched the analysis path:
  cross-check audit fields, the fallback-pair rule, completion checks of sampler parameters and warm-up. After each new completion
  check all 9 520 production chain records on Expanse were rescanned; none failed.
- Production records were made with code inspected through rounds 18–19 plus the fixes of those rounds; each record lists the hashes.
- The loop stopped after round 23: the builder applied the author's instruction to limit review rounds, given for the d=2 plan.
  The fix of round 23 (registry lock replaced by a kernel advisory lock) is uninspected.
- The round-21 inspector noted that the final table misses the protocol's criterion 1 at Δσ = 0.0625, 0.15, 0.1625, 0.175 and
  0.1875: an outcome of the pre-registered decision table, not a code defect.

### 1D campaign report (2026-09-20)
- 3 rounds: REVISE (10 findings), REVISE (6), APPROVED, bound to the report's TeX source (SHA-256 7940ef40…).
- Changes: comparisons with the six published values rewritten point by point; inputs of the selected analysis snapshots, missing
  from the local copy for all 20 points, restored and hash-checked (564 paths); counts, a window table and the reproduction
  commands corrected; an engine-equivalence statistic described as a sum of squared pulls, not a χ²; the reference engine's RNG named.
- The reviewer's stated limits: read-only; raw trajectories and numerical reproducibility not re-established.

### Independent audit (2026-09-22)
- An OpenAI Codex session (gpt-6-astra), started at the author's request, audited the approved report, its code snapshot, the v3
  protocol and the saved results; it did not regenerate raw trajectories or rerun all production fits. A follow-up studied
  extrapolation and model uncertainty with diagnostic refits on Expanse.
- No defect in the interaction normalisation, cluster update, improved estimators or temperature derivatives. All six test suites
  passed; five exact-enumeration checks of the d=1-specialised engine (all 256 states of 8 spins) passed. Values and labels match
  all 20 records.
- F1 (high): σ_sys, half the range of the quotable fit family, is a model-sensitivity scale, not a calibrated standard deviation;
  "within 2 s.d." and "4–15× precision" need qualifying.
- F2–F6 (medium): conditional points plotted as if σ_sys were zero; the completion check does not authenticate the interaction
  kernel; lineage checks would accept one block archive as two measurements; the folder was incomplete for standalone
  reproduction; `make test` ran only half of the six suites.
- Follow-up: values stable under stronger size cuts at Δσ = 0.1, 0.1375 and 0.1727335; sensitive at 0.025 (an extra correction
  term gives 0.693 instead of 0.711), 0.175 and 0.225. The failed cross-checks at 0.15 and 0.175 pass on finer exponent grids;
  the 2026-09-30 cross-check study (see Amendment P1) judged that tension genuine. This is unresolved.
- What changed: the public note reports σ_sys as a model-family half-range, separately from σ_stat. The d=1 code is released
  unchanged, so the F3 and F4 guard weaknesses remain; the audit found no instance of either in the production records.

## d = 2

### Protocol FIT_MODEL_2D (2026-09-20)
- Revision 1: one round by a fresh Claude session while Codex was unavailable. REVISE, 8 findings, all accepted; the simulation
  design was judged sound. Changes: a fixed pair list (a missing pair gives COVERAGE-LIMITED), profiled ω′ with a resolution gate, a
  population equilibration rule, mandatory reblocking, provenance hashes, size-class packing and a preflight run.
- Codex rounds 1–3 on revisions 2–4: REVISE with 12, 6 and 5 findings (FIT2D-001…016), all accepted. Themes: every chain checked
  against the manifest and the frozen design, provenance from raw chain to evaluation, immutable outputs, safe submission and
  checked continuations. The rounds covered the evaluator `evaluate_2d.py` and Claude's changes to the engine's packing and analysis.
- The author limited the review to three Codex rounds. Revision 5 carries the round-3 fixes without a further pass. It was never
  approved. It was frozen on 2026-09-20, before production was submitted (SHA-256 4d2efc63…, pinned by the evaluators).
- No separate inspection of `evaluate_2d.py` revision 5 is recorded; its P1 revision was inspected with Amendment P1.

## d = 3

### Protocol FIT_MODEL_3D (2026-09-21)
- Rounds 1–4 REVISE (8, 5, 5, 2 findings); round 5 APPROVED revision 5 (SHA-256 b4ccf436…). The author had set a three-round cap
  and raised it to seven after round 3. The rounds covered `evaluate_3d.py` and every production wrapper.
- Changes: a reduced-statistics exception for L = 128 removed (10⁶ sweeps at every size); the preflight made a binding gate; design,
  throttle and submission checks; robust handling of missing reblock records; snapshot-bound processing of extensions.
- Post-approval amendment: the first preflight gate failed only on "τ ≤ 30 sweeps" (34.3 at s = 1.6, 32.6 at s = 1.85). Revision 6
  replaced it by τ_int ≤ 50 (block/τ ≥ 20, the rule the analysis already applies), disclosed as post hoc. The gate record, which
  holds preflight effective dimensions, had been seen.
- Round 6 REVISE (2 findings, applied): the evaluator now applies the equilibration rule to every reblock record. Round 7 REVISE
  (1 finding, FIT3D-023): a missing argument in that patch, which the builder had fixed two minutes after the round started.
- The author submitted production under revision 7 (SHA-256 682858f0…) with that one-line fix, without an eighth round.
- 23 findings in total, all accepted. No separate code inspection of `evaluate_3d.py` is recorded.

## Amendment P1 (profiled ω′ uncertainty, d = 2 and 3)

### Results review that preceded it (2026-09-24)
- A Codex review (model not recorded) read the d=2 and d=3 evaluations, per-series records and evaluator code; read-only, no refits.
- Findings: the labels match the records; statistics and temperature coverage are healthy (500/500 bootstrap draws, crossings well
  inside their brackets, ESS above the gate); the failures come mainly from correction models and weak identifiability, and more
  statistics at the same sizes is a poor priority.
- Advice: archive the data; review the nuisance-parameter uncertainty, starting with d=3 s = 1.6; larger-L pilots only for a specific
  question; do not promote conditional d=2 values or failed d=3 extrapolations to continuum results.

### Plan
- An exploratory reanalysis (2026-09-25, existing data) found that profiling ω′ in every bootstrap draw raises the individual-series
  σ by 2–10×, and that only d=3 s = 1.6 would change label. The amendment was written after this was known.
- 4 rounds: REVISE (4 findings), REVISE (2), REVISE (1), APPROVED revision 4 on 2026-09-25 (SHA-256 2a18c0ae…). The findings: a
  pooled-only calibration, no cross-check threshold, baselines chosen by the newest file, an unattainable bit-for-bit reproduction
  claim, synthetic truths mixing two models, the handling of uncalibrated points, a calibration not bound to its inputs. All were
  accepted; baselines are now pinned by path and hash. The reviewer stated that approval covers the plan, not the implementation
  or the calibration outcome.

### Implementation
- Built 2026-09-30 (`evaluate_2d.py` rev 6, `evaluate_3d.py` rev 2, `calibrate_p1.py`, tests). Two inspection rounds, each a fresh
  session: REVISE, 6 findings (P1-008…013); REVISE, 2 findings (P1-014, P1-015). All fixed; the tests grew from 30 to 56.
- The round-2 fixes are not independently inspected (the budget of two rounds was reached).
- Calibration and evaluations were rerun with the final code. One label changed: d=3 s = 1.6 (Δσ = 0.70), CROSS-CHECK FAILED →
  ACCEPTED [σ_stat above target], Δε = 1.47314 ± 0.00118 (stat) ± 0.00230 (sys). The d=2 labels did not change.
- No separate review of the P1 results is recorded; the pre-release review (below) examined them.
- A d=1 cross-check study of the same date (not part of the amendment) found that the d=1 protocol already profiles every
  nonlinear parameter per draw, so the cross-check failures at Δσ = 0.15 and 0.175 are not an artefact of a conditional σ.

## Engines
- `lri_cluster` (d=1 reference engine, campaign tools and analysis core; delivered 2026-09-14). Reviewed by Claude on delivery:
  bond rate, temperature derivatives from bond counts, improved estimators and the coupling sum rule checked; `make test` passed on
  two local machines and on Expanse. A pilot (200 chains, s = 0.8 and 0.875) showed the default temperature window too wide at
  s = 0.8 for N ≥ 8192; narrower production windows were recommended.
- `lri_1d_precision` (d=1-specialised engine, delivered 2026-09-18). Compared by Claude with the production engine (2026-09-18/19):
  its copy of the old engine is byte-identical to production; `make test` passed; 1.3–2.1× faster on one core and 2.5–3.3× on a
  packed node, same autocorrelation times; means agree after a fresh-seed replication. Before N2 it was integrated as engine `1d`
  and checked on matched campaigns: 24 comparisons of six observables, all |z| ≤ 2.2 (the mean bond count was up to 2.3σ apart; a
  longer follow-up gave a pull of +1.5). Codex inspection round 4 of the v3 loop raised no finding on the integration; round 18
  made the completion check require the production sampler parameters, and all 2 240 engine-1d records pass it.
- `lri_precision_v2` (d=2,3 engine). Audited by Claude on 2026-09-20 (every source file, tests, pilot records). No defect on the
  physics or statistics path; exact-enumeration tests reproduced bit for bit; an independent comparison with the old table-based
  engine agreed (d=2 L = 64, d=3 L = 32); pilots regenerated on Expanse were bitwise identical to the delivered chains. Eight
  non-blocking findings, e.g. a provenance field naming a nonexistent coupling file, tests overwriting archived files, Linux-only
  orchestration, an unconditional requeue, a Y versus U4 split at pilot sizes. Whether each was fixed: (not recorded).

## Release package (2026-10-07)
- No review of the package itself is recorded.
- It carries a reproduction check in a fresh workspace on a project workstation: the d=2,3 evaluations (frozen rule and P1), the P1
  calibration and the reanalysis reproduce to about 1e-11 relative; the d=1 fit stage reproduces every quoted Δε (to 1e-8) and
  18 of 20 labels.
- Δσ = 0.1625 (CONDITIONAL → ACCEPTED) and 0.1727335 (ACCEPTED → CONDITIONAL) flip off the production host: the degree-3 start of
  one configuration lands inside or on a parameter bound depending on floating point, and the ladder-stop rule then trims the
  family. Repeated with the production library versions on two machines, one a node of symmetry: same flip. The production labels
  stand; these two are reported as platform-sensitive.
- Its README listed as open: the P1 round-2 fixes and the d=1 registry-lock fix (round 23), not independently inspected.

## Pre-release review (2026-10-13)
- Subject: the public MC note and its README, REPRODUCE, DATA and Makefile drafts, the code patches and the exported MC folder.
- Form: a five-lens review (physics, statistics, numbers, readability, code and documentation) by Claude Opus 5.5 agents coordinated
  by a separate Claude Code session, followed by an item-by-item verification and a bibliography check.
- Verdict: the Monte Carlo itself is sound (sampler, cluster algorithm, estimators, reweighting, error bars, equilibration), and the
  finite-size tables reproduce exactly. Not yet sound: the claims about what the protocols establish.
- Accepted: A1, a per-dimension timeline (rule set, hash, review verdict, data seen); A2, the quadrature term in σ_D disclosed and z
  tabulated with and without it; A3, the common fit-minus-crossing offset +0.00105(28) reported; A5, d=3 s = 1.6 described as
  consistent with the ε expansion and accepted only under the post hoc amendment P1; A7; A8, an 8-loop reference with its band;
  A10, p-values of quoted fits; A12–A15. Parts B–D (numbers, readability, code and documentation) were worked through; the
  verification gives their status item by item.
- A4 accepted in substance: theory columns from the 8-loop resummation and warnings in the text; no post hoc downgrade of labels.
- A9 accepted: a robust-ladder sensitivity study refitted all 20 couplings with a fitter in which a flagged lower-degree fit no
  longer stops the ladder. Quoted values changed by less than 2e-5; both platform-sensitive couplings pass; ten couplings would pass
  instead of nine. It is a diagnostic; no protocol label changed. Records: `results/1d/robust_ladder_20261013/`.
- A11 accepted with a correction: under the misspecified calibration family d=3 s = 1.6 is flagged in every synthetic set, so it
  could not have been accepted there. Coverage is reported per series.
- A6 partly accepted: the long-range to short-range crossover of Behan et al. (BRRZ) was added as physics context. The claim that
  it explains the d=2,3 failures was rejected: the measured D_Y − D_U4 split grows with L, while the leading-order flow makes it
  shrink.
- Verification (same day): A2–A5, A7–A9, A11, A13 and A14 implemented; A1, A6 (wording), A10, A12 and A15 partly. Every recomputed
  number matched; the note compiled cleanly; all 23 bibliography entries were correct (checked against INSPIRE, arXiv, Crossref);
  the release's own checks passed (note tables 355/355, 15/15 hashes).
- The verification listed seven blocking items. All were addressed in the released texts on the same day:
  - the abstract, note §5 (Table 3 and two new paragraphs) and `protocols/PROTOCOL_HISTORY.md` now state when each rule was fixed,
    the replacement of v2's σ_sys cap and per-group equilibration rule after four couplings had failed them, and the three N0
    outcomes;
  - this file was written, and references to an unshipped data manifest were removed;
  - hooks for material not in the release were removed, and the output comparison now fails on a missing reference;
  - host names were limited to public facilities;
  - `FIT_MODEL_V3.sha256` was made checkable;
  - licence and hosting were stated (the licence was chosen later, on 2026-10-15);
  - the note reports the public-layout acceptance runs.
  Most of the not-blocking items were fixed as well: numeric and wording slips, Part B leftovers, process language, the gap in the table
  numbering, and four missing references.
- Still open: a reconciliation of the compute totals; a residual panel and per-label markers in the d=1 figure; a χ² scale factor;
  a discussion of multiple testing across couplings. The fixes of 2026-10-13 have not been re-verified.

## Recommendations not adopted
- d=1 campaign plan: run at revision 6 after five REVISE rounds, on the author's explicit override; two rules amended during the
  build without review; the second-round code fixes not inspected.
- v2: revision 6 (scan addendum) and the fixes after inspection round 3 not reviewed (budgets used up).
- v3 plan: N0 and N1 run under revision 8 (last verdict REVISE) on the author's authorisation; the plan was approved only after N1
  and the N0 data had been seen.
- v3 N0: the pre-registered remedy for INCONCLUSIVE (retest at δ/2) was not run; the rule was amended twice under review, and N2
  was released on the third rule.
- v3 plan text: one §5.0 requirement cannot be met (R16-003); it is a documented deviation in the code, the approved text unchanged.
- v3 code: the loop stopped after 23 REVISE rounds, under the author's limit on review rounds; the round-23 fix is uninspected.
- d=1 audit: F3 and F4 (kernel authentication, archive-to-measurement binding) were not implemented; the d=1 code is released
  unchanged.
- d=2 protocol: never approved; the author closed the review at three Codex rounds, and the round-3 fixes were not re-reviewed.
- d=3 protocol: production under revision 7 plus a one-line fix without an eighth round; the τ gate was amended after the preflight
  data had been seen (disclosed and reviewed in rounds 6–7).
- P1: the round-2 code fixes not inspected; the amendment was written after the reanalysis had shown which label would change.
- Pre-release A6: "the crossover explains the failures" rejected (the split grows with L; the flow makes it shrink).
- Pre-release A4: the offered downgrade of the labels of d=2 s = 1.05, 1.1 and d=3 s = 1.9 not adopted; warnings added instead.
- Pre-release A10 and A13: a χ² scale factor or p-value gate, and a label-stability study, deferred to the note's open issues.
