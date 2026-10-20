# Provenance: c1_d3

Dated snapshot of the **review-revised delivery** of the package `ising3d_C1_reproducibility` (note dated 7 October
2026, "Review-revised final-method note"; archive file times 2026-10-08 01:00 to 03:18 UTC; received as an archive of
305 files and extracted unchanged on 2026-10-15, all 304 entries of its `SHA256SUMS` verified). Not a git repository;
the shipped files and their sha256 are in `public/SNAPSHOT.sha256`.

| Stage | Date | Who | What |
|---|---|---|---|
| The package (pre-review delivery `ising3d_C1_final_method.zip`, 138 files) | 7 October 2026 (note date; archive file times 2026-10-08 01:00 to 01:09 UTC) | **OpenAI GPT-6 astra (via ChatGPT), supplied by the author** | code, inputs, single-file note, reference and reproduced outputs. Its `data/provenance/package_sources.json` names four earlier archives it was consolidated from (`lri_crossover_research_bundle.zip`, `independent_3d_audit.zip`, `c1_precision_update.zip`, `c1_errorbar_refinement.zip`, with sha256). Kept in the project unchanged; not exported (superseded by the revision) |
| Review | 2026-10-07 | Claude Code (four review agents: physics, inputs, code/reproduction, bounds) | reproduction on a personal desktop, two independent re-implementations of a0 and b0, stress tests of the envelope; see REVIEWS.md |
| Review revision (**this snapshot**) | note dated 7 October 2026; archive file times 2026-10-08 02:54 to 03:18 UTC | **OpenAI GPT-6 astra (via ChatGPT), after our review, supplied by the author** (stated by the author 2026-10-15; the files themselves name no author: the response to the review is written in the first person) | 11 code files changed (explicit guards; `runtime_config.py` reading the reference coefficients and denominator box from the current run; side-run safety of `reproduce.py` and `verify.py`; `f = 0` in the denominator box), 4 review-diagnostic scripts added, inputs relabelled (source labels of the sigma, epsilon, T rows; no number changed), the note extended (folding derivation, gap evidence, literature comparison, sensitivity tables), full 20-stage rerun from scratch; numerical results unchanged at the reported precision. Record: `review/RESPONSE_TO_REVIEW.md`, `data/provenance/review_revision.json`, `changed_sources.json` |
| Check of the revision | 2026-10-08 | Claude Code (two agents) | all majors and nearly all minors fixed; numbers bit-identical; 23/23 regression checks |
| `review_indep/` (4 files) | 2026-10-07 (file times 22:34 to 22:38 US Eastern) | **Claude Code review agents**, written for the 2026-10-07 review of this package (code-and-reproduction agent: `indep/`; physics agent: `physics_review/`) | two independent re-implementations of a0, b0, c_1 (REVIEWS.md says what they check). Fetched read-only on 2026-10-15 from the review's working folder on a personal desktop into a staging folder, with sha256 and file times recorded; byte-identical, unchanged since 2026-10-07. Not part of the authors' delivery, so not in `SHA256SUMS`; in `public/SNAPSHOT.sha256` |
| Public tools (`public.mk`, `public/`, `review_indep/README.md`) | 2026-10-15 | Claude Code (SRI package builder) | test, replay, replay-full, SNAPSHOT.sha256, NOT_SHIPPED.txt |

Environment of the package's runs (from `outputs/verification/environment.json` and the receipts): Linux, Python
3.13.5, NumPy 2.3.5, SciPy 1.17.0, mpmath 1.3.0, pdfTeX (TeX Live 2025).

Inputs:

| Input | Source | Transcribed by | Checked |
|---|---|---|---|
| `data/inputs/published_spectrum.json` (60 primaries below 24: SS0, EE0, SS1, SE0 families and others; dimensions, OPE coefficients, quoted errors) | D. Simmons-Duffin, JHEP 03 (2017) 086 [arXiv:1612.08471], Tables 3 to 7 | the package (GPT-6 astra) | review 2026-10-07: all 60 rows equal the published tables; selection = the stable entries below 24 |
| `data/inputs/low_inputs.json`: S = Delta_sigma = 0.518148806(24), E = Delta_epsilon = 1.41262528(29), lambda_sse = 1.05185373(11), lambda_eee = 1.53244304(58), c_T/c_B = 0.946538675(42) | C.-H. Chang, V. Dommes, R. S. Erramilli, A. Homrich, P. Kravchuk, A. Liu, M. S. Mitchell, D. Poland, D. Simmons-Duffin, JHEP 03 (2025) 136 [arXiv:2411.15300v2], Table 1 | the package (GPT-6 astra) | review: values and the Ward-identity stress couplings check out; only S and E are rigorous |
| epsilon-prime window [1.5349, 1.5375] (`assumptions.json`, `runtime_config.py`) | M. Reehorst, JHEP 09 (2022) 177 [arXiv:2111.12093], Table 4 (conditional sparse-bootstrap constraint) | the package (GPT-6 astra) | review: applied faithfully |
| normalization and comparison | C. Behan, L. Rastelli, S. Rychkov, B. Zan, J. Phys. A 50 (2017) 354002 [arXiv:1703.05325]; PRL 118 (2017) 241601 [arXiv:1703.03430] | | a0, b0 agree term by term with the published I_sigma, beta_3, gamma_eps |

The same S and E_SR are used by the 3d resummation of the Resummation folder (`Resummation/code/resum_d23/3d/inputs/
protocol.json`: S = 0.518148806, E_SR = 1.41262528); its frozen copy `sri_summary.json` is byte-identical to the
pre-review `outputs/tables/current_summary.json` and differs from this snapshot's only in three status/warning strings
(all numbers equal).

Earlier archives: the four archives named in `package_sources.json` were all written by OpenAI GPT-6 astra (via ChatGPT)
(stated by the author 2026-10-15); three of them are not in the project files and are not shipped.
