# Reviews: SRI

Summaries only; raw review logs and transcripts are not published. Each package's `REVIEWS.md` has the details.

- **dual_d1, review of the compendium (2026-10-02)**: Claude Code, a multi-agent workflow over ten dimensions with
  adversarial verification of each finding. No error in any coefficient or proof claim: C^SR_3..C^SR_7 recomputed
  independently from the stated formulas; the C5, C6 and C7 certificates sound (altered rows are rejected); every task
  of the compendium reran on Linux, the C8 evaluation byte for byte; eq:sr-C8 is the unique integer relation against a
  basis enlarged by 26 further constants; the numerical C^SR_8 is good to about 1e-85, limited by six inherited inputs
  with neither an exact expression nor a second evaluation; the rational part 88 is sound. Defects (archive and
  attribution, none mathematical): the case-colliding input pair, the 21 omitted stage programs (raw regeneration
  impossible), one workflow that does not recreate its paths, citation errors in the compendium's note. The paper
  displays eq:sr-C8 as conjectured (author, 2026-10-14). `docs/dual_d1/REVIEWS.md`.
- **indep_d1, the independent re-derivation and its verifiers (2026-10-02 to 2026-10-07)**: started because the review
  found that the compendium's raw integrals had only been replayed with its own code. Separate Claude Code agents
  reviewed each component (the engine was fixed to version 2 before production, nine must-fix items), three
  adversarial verifiers (independence, statistics, mathematics) passed phase 2, a mathematics verifier checked the C8
  tier A, and a post-assembly statistics verifier found the sector-pooled error estimator well calibrated (a
  chunk-pooled estimate would give a C8 pull of -2.09 instead of the protocol's -1.92). Results: the 25 inputs of
  C^SR_5..C^SR_7 agree (rms pull 0.34; C5 -0.13, C6 -0.78, C7 -0.08); C^SR_8 = 242.8 +- 2.4 against 247.38 (-1.9
  sigma), the whole difference in A9[eps^0 l^1] (-2.19 sigma). The tension was left open (see the next item). The
  verifiers' reports were not kept; no Codex review. `docs/indep_d1/REVIEWS.md`.
- **integ_d1, magnetization-scheme value of C^SR_8 (2026-10-14 to 2026-10-17)**: a scheme defined by the
  magnetization at the integrable point s = 1, with the s = 1 part from the Bethe ansatz, sharing no input with
  dual_d1 or indep_d1. OpenAI Codex reviewed the plan in three rounds (approved) and inspected the code six times; the
  sixth approved quoting 247.38118 +- 0.13 (empirical numerical uncertainty) with its disclosures: central value frozen
  before any comparison, two check criteria amended by the author after their data were seen. It agrees with the
  record to 2.5e-5 and reproduces C^SR_3..C^SR_7 to 7e-26. The SRI note, Sec. 2.7 and Appendix I, gives it in full;
  `docs/integ_d1/REVIEWS.md` summarises the reviews and the disclosures (including the computing session's exposure to
  the comparison before the error bar was evaluated). No review log or transcript is shipped.
- **c2_closed_d2, review of the closed form of c_2 (2026-10-08)**: Claude Code, four reviews (physics and derivation,
  special-function reduction, an end-to-end numerical evaluation, code and reproduction); the study was not modified.
  c_2 = -4.0662701481325... confirmed. The review's Monte Carlo of the full regulated 8D integral, with no use of the
  study's reductions, gives -4.075 +- 0.019 (0.47 sigma; three configurations agree), which also supports numerically
  the exchange-of-limits step the study leaves unproved. The finite matching term is required (without it c_2 = -2.12,
  excluded); the elliptic finite part agrees with its direct evaluation to 51 digits; the reduction chain was checked
  step by step; no Gamma-only relation exists by PSLQ. Majors: (M1) the regulator-uniform remainder bound is not
  proved; (M2) the study's own checks share its last derivation step (the review reproduced the upstream steps
  independently). The 2026-10-15 package build recovered the Monte Carlo's chunks and its recombination rule (the
  script was lost) and observed that the configurations agree less well on the source-shape control (chi^2 7.6 on 2
  dof) than on c_2. `docs/c2_closed_d2/REVIEWS.md`.
- **c2_cylinder_d2, the cylinder Hamiltonian (2026-10-12 to 2026-10-14)**: three Claude Code agents reviewed the
  supplied study (formalism valid, solver rebuilt independently to about 1e-11, about -4.067 +- 0.004; recommended
  larger cutoffs and an analysis at any N). Codex (OpenAI, gpt-6-astra) then:
  - inspected the cluster layer twice: 12 findings fixed; 9 findings fixed but not re-inspected;
  - reviewed the continuum-analysis plan in seven rounds, approved at rev 4; the rev-4 result had an error dominated by
    a worst-case grid-extraction rule, so the rule was revised after the first result (post-hoc amendment rev 5, every
    point then measured), and plan rev 7 was approved; the central value did not change. Deviation D1 (N = 1024 grids
    rebuilt on symmetry after an SDSC Expanse file-system fault) was approved by the author;
  - inspected the analysis code twice: inspection 1, seven findings, all fixed (no number changed); inspection 2, four
    hardening findings, fixed without re-inspection by the author's decision (no number changed), so these fixes are
    **uninspected**. Codex confirmed that the closed form is not an input.
  `docs/c2_cylinder_d2/REVIEWS.md`.
- **c1_d3, review of c_1 (2026-10-07) and the revision (2026-10-08)**: Claude Code, four agents. The from-scratch run
  reproduced every number bit for bit; two independent re-implementations by the reviewers agreed (c_1 to 1e-15 and
  3e-13); all 60 inputs match Simmons-Duffin 2016; c_1 agrees with 0.27(4) of Behan, Rastelli, Rychkov and Zan. Majors:
  the central inputs are infeasible in the nominal linear program, no gap sensitivity was shown and modest weakenings
  leave the range, the gap hypotheses lacked evidence, a documented command overwrote a shipped receipt. The revision
  of 2026-10-08 (its author is not recorded) addressed all majors and nearly all minors and reports the value
  separately from the estimated range; a check by two Claude Code agents found the numbers bit-identical, with
  leftovers that change neither c_1 nor the envelopes (the widened-box sensitivity rows are too narrow by up to
  2.7e-4). The two re-implementations now ship (`code/c1_d3/review_indep/`), and `make replay` reruns them: c_1
  within 4e-14 and 3e-13 of the package (the note's "agree to 10^-12", Table 2); the package's own two integrated forms are a
  same-domain consistency check, not an independent test. `docs/c1_d3/REVIEWS.md`.
- **Public export (2026-10-15)**: `test`, `replay` and, where present, `replay-full` of every package passed on a
  simulated export on symmetry, Intel and AMD nodes (`docs/<pkg>/TESTS_<pkg>.md`). The public tools were not reviewed by Codex.

## closure_d1 (2026-10-15)

The two notes assessed below are not shipped since 2026-10-16; their arguments are the note's Appendix D, and the checks of the review are its Appendix D.15.

SRI assessment of the counterterm-closure note: the proof is sound as a standard perturbative power-counting sketch (finite algebra rechecked independently); the operator content is closed formally; the matching of the archived prescription is open (two projected responses solve a square system for the beta functions; endpoint and insertion logarithms are not separated on one interval); NRG confirms C^SR_3 to C^SR_5.

SRI assessment of the prescription-equivalence note (2026-10-15): the prescription link is closed at the formal level, at the same rigour as the first note (endpoint power counting and classification, the surviving endpoint-source terms, the normal-ordering cancellation and the beta recurrence b3..b9, h4..h8 re-derived independently; the note's own checker passes). Stated rather than shown in detail: the sharp-edge limit, the hard-core recursion when exclusion regions do not factorize, and the far-field probe projection. See `docs/closure_d1/REVIEWS.md`.
