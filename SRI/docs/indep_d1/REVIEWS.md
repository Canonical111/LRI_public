# Reviews: indep_d1

All reviews were by Claude Code agents separate from the agents that wrote the code; no Codex (OpenAI) review of this
package exists. The verifier reports themselves were not kept (PROVENANCE_indep_d1.md, "Unknowns"); what follows is
taken from the project's own reports (`RESULTS.md`, `RESULTS_C8.md`, `RESULTS_C8_tierA.md`, the component READMEs,
`engine/PRODUCTION_C8.md`) and the project record.

**Why the package exists.** The review of the compendium (2026-10-02, package `dual_d1`) found its mathematics sound but
noted that its raw integral expressions had been replayed only with its own code. The author then asked for an
independent re-derivation of the C6/C7 inputs, later extended to C8.

**Phase 1 (2026-10-02/03): component reviews.**
* Engine: a phase-1 reviewer gave READY WITH FIXES. The errors of correlated combinations were wrong (channel errors
  added in quadrature) and every job used the same random shifts. Version 2 fixed all nine must-fix items (per-shift
  replicates and per-replicate assembly, hashed seeds with a disjointness check, an a-priori precision floor, outlier
  criteria on the needed coefficients, explicit structural zeros, atomic outputs, task ordering, documentation, the
  planner); a regression on symmetry showed bit-identical values from the phase-1 and v2 binaries
  (`engine/README.md`, table at the top). A gate review just before production (2026-10-03) compared raw coefficients
  with the archive after the production spec and binary were frozen.
* Framework: a critic transcribed the note's recurrence, dictionary and assemblies independently
  (`framework/review/check_note_recurrence_direct.py`, run by `make test`): the module agrees to 1e-40.
* Spec: a reviewer added archive-free checks (an independent fixed-point solution with extra monomials, the three-kink
  inputs end to end from the definitions); their results are cited in `spec/spec_definitions.json`.
* Direct: an independent GLS implementation and structural probes confirmed the finite-cutoff comparison tool.

**Phase 2 (2026-10-03): three adversarial verifiers**, all returned DONE:
* independence: no archive code was used and no archive number entered any input of the production or assembly path
  (the disclosures of `RESULTS.md` list the comparisons made after the project's own values existed);
* statistics: the checks dominated by statistical error behave as N(0,1) (chi2/dof 0.42-1.30); the quoted error is the
  largest of three estimators;
* mathematics: the closed forms, pole cancellations and higher-log checks of step 2 were verified.

**Phase 3 (2026-10-03/04): C8 tier A.** A mathematics verifier checked the four exact tier-C scalars
(`engine/PRODUCTION_C8.md` 12b: A3[eps^3 l^0] = -5/9 and three structural zeros) and compared pilot-level parts of U and
Kv with the note's values after the tier-A results had been hashed.

**Phase 4 (2026-10-07): post-assembly statistics verifier** (`RESULTS_C8.md`, "How reliable is A9's error?"). It found
the sector-pooled estimator well calibrated: per-sector variance sums calibrated to 0.93-1.03 over the 20,160 sectors of
A9, about 19,900 effective degrees of freedom, a permutation null giving p = 0.07 for the low replicate ratio of A9, and
a chunk-pooled estimate sigma(A9_1) = 8.50 instead of 9.34, i.e. a C8 pull of -2.09 instead of -1.92. The protocol fixed
the quoted estimator (the largest of three, here the sector-pooled one) before the comparison; the paper quotes -1.9.

**Open items recorded by the project.** The A9[eps^0 l^1] tension (-2.19 sigma; since 2026-10-17 the
magnetization-scheme value of the SRI note, Sec. 2.7, indicates that the low C8 of this package is the one in error, and an independent A9 run of about
9k core-hours would show whether it is a fluctuation or a systematic error); the Q8_v strict re-check has no result (its job was cancelled after 41.9 h); the tier-C
heavy WARN fraction is 1.03 % against a 1 % criterion (the A9 strict re-check shows the warnings do not change values).

**Public-repository checks (2026-10-15).** `make test` and `make replay` on a simulated export (TESTS_indep_d1.md):
every assembly step reruns verbatim and reproduces the shipped results; the engine, rebuilt from source on symmetry,
gives the production binary's md5 and reproduces four production chunks to 2.4e-16 of their L1 scale.
