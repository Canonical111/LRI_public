# Provenance: indep_d1

**Snapshot.** `code/indep_d1/` is a dated snapshot of the project folder `LRI_SRI_C6C7_independent/` (not a git
repository): selected files, layout kept, taken 2026-10-15; every shipped file was last changed between 2026-10-02 and
2026-10-07 (no file of the folder changed after 2026-10-07). sha256 of each file: `public/SNAPSHOT.sha256`.

**Authors.** Everything in the snapshot was written by Claude Code sessions (Anthropic) between 2026-10-02 and
2026-10-07, as multi-agent workflows started by one host session on the author's request (2026-10-02: "re-derive the
C6/C7 inputs independently on a cluster", after the review of the compendium found that its raw integrals had only been
replayed with its own code). The author set the budgets (tier 1 about 2.4k core-hours; C8 tiers B and C at most 20k
amdq-equivalent core-hours, tier B at sigma(C8 without J9) = 0.01, tier C as a gross check at sigma(C8) about 3) and
approved each phase; the author wrote none of the code. The folder records no contribution of an OpenAI model
(GPT-6 astra, Codex): no Codex review of this package exists.

| phase | dates | agents (Claude Code subagents) | output |
|---|---|---|---|
| 1 | 2026-10-02/03 | spec, framework, engine and direct agents; a critic | definitions (`spec/`), the RG map (`framework/`), the engine with its validation ladder and v2 error model (`engine/`), the finite-cutoff tables (`direct/`) |
| 2 | 2026-10-03 | engine production, assembly agent; three adversarial verifiers | tier-1 production + top-up, `assembly/`, `RESULTS.md`, `RESULTS_independent.json`, `RESULTS_archive_comparison.json` |
| 3 | 2026-10-03/04 | spec, framework and engine agents (C8 extension); tier-A assembly agent; verifiers | `spec/out/C8`, `framework/derive_C8.py`, tier A, `RESULTS_C8_tierA.md` and its json files |
| 4 | 2026-10-04..07 | prepare agent, engine production (tiers B, C, budget guard), assembly agent; post-assembly statistics verifier | tiers B and C, `RESULTS_C8.md`, `RESULTS_C8_independent.json`, `RESULTS_C8_archive_comparison.json` |

**Independence rule** (set 2026-10-02). No code of the compendium (`LRI_SRI_research_compendium`, package `dual_d1`)
was imported, called or copied, and no archived raw data (`*_negative.json`, `*_audit.json`, `*.expr`, expression
files) was used as input. The compendium's note was read for the definitions and for its proved closed forms (the
archive-free targets in `spec/out/`). Archived numbers were read only for comparison: by `assembly/compare_archive.py`
and `compare_archive_C8.py`, which refuse to run before the archive-free json file exists and record its sha256
(`RESULTS_independent.json`, sha256 `7b633827...`, written 2026-10-03 10:11; `RESULTS_C8_independent.json`,
`83065f0a...`, written 2026-10-07). The C8 archive-free steps ran in a copy of the project without the sealed
directories, under a Python audit hook (`assembly/audit_run.py`). The exceptions in which archive numbers were visible
before results were fixed (task briefs quoting the claimed C8, phase-1 comparisons of raw coefficients after the
production spec was frozen, the tier-A report read by the phase-4 agent, one hard-coded comparison-only check in
`framework/derive_invariants.py`) are listed in `RESULTS.md` and `RESULTS_C8.md` ("Independence statement"); none
enters any computed value, which the independence verifier audited.

**Inputs from elsewhere.**
* The compendium's TeX source `LRI_perturbation_compendium.tex` (definitions, eq:C8assembly, the appendix polynomial
  B_old, proved closed forms; not shipped since 2026-10-17: the blocks the self-test needs are in
  `../dual_d1/public/compendium_extract.json`, and its content is in the SRI note,
  Appendices A to C) and the archived 100-digit values in `spec/comparison/` and `spec/comparison_C8/` (extracted
  and sealed by the spec agent on 2026-10-02 and 2026-10-03): written by another AI system as part of the research
  compendium the author supplied (see `dual_d1/PROVENANCE_dual_d1.md`). `framework/tests/test_c8.py` and
  `test_archive_pipeline.py` read that source and one archived record from the sibling package `../dual_d1`.
* The claims tested by the replay are the paper's eq:sr-closed and eq:sr-C8 (`SRI/results/quoted_numbers.json`).

**Compute.** Engine production on the symmetry cluster (`amdq`, AMD EPYC 7532/7543, at most eight 64-core nodes),
except: C8 tier A (183.1 core-hours, 2026-10-03/04, symmetry was down), the cheap tier-B/C groups and most strict
re-checks (528.6 core-hours; the tier-B/C runs on the personal desktop, directory suffix `_can`), the C8 validation and
pilot of phase 3, and
the C8 archive-free assembly job ran on a personal desktop; the comparisons and reports ran on the author's
workstation. Totals in `public/REPLAY_FULL.md`.

**Later changes.** None to the project folder. For publication (author's decision of 2026-10-15), 22 snapshot files that
named the personal desktop were scrubbed and re-pinned (MC pattern; `RE-PINNED.json`, `RE-PINNED.md`, built by the SRI
maintenance tool `repin_indep_d1.py`): the hash-bound result records `RESULTS_C8_independent.json` and
`RESULTS_C8_independent_tierA.json` (only the machine word replaced; no number changed) with their hash cascade (`.sha256`
files, the two C8 comparison files, the reports `RESULTS*.md` regenerated by the published `make_report*.py`), and the
documents and code that used the name as the machine word. Twelve files that named the personal desktop as a host and
that no test or replay needs were not exported (core-hour ledger and submission list of tiers B/C, the tier-B/C drivers,
the budget guard, four production-check json files, three pilot check files). The tier-B/C runs on the personal desktop
keep their directory suffix `_can`. Added for the public repository by Claude Code (SRI session, indep_d1 builder),
2026-10-15: `public.mk` and `public/` (`selftest_indep.py`, `replay_indep.py`, `run_step.py`, `pooled_shim.py`,
`make_pooled_record.py`, `pooled_sector_record.json`, `RAW_SHA256SUMS.txt`, `REPLAY_FULL.md`, `SNAPSHOT.sha256`);
`pooled_sector_record.json` was built on 2026-10-15 on symmetry (job 575616) from the raw chunk
outputs with the verbatim `assembly/pooled_errors.job_sector_values()`.

**Unknowns.**
* The reports of the three adversarial verifiers of phase 2 (independence, statistics, mathematics), of the phase-3
  verifiers and of the phase-4 statistics verifier were kept in the host session's scratch directory, which no longer
  holds them. What is known about them comes from `RESULTS*.md`, `engine/PRODUCTION_C8.md` and the project memory
  (REVIEWS.md).
* The compendium's note and archived values (the claims this package compares with): written by OpenAI GPT-6 astra
  (via ChatGPT) and supplied by the author; see `dual_d1`.
