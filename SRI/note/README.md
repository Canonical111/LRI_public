# Note: expansions about the short-range end of the long-range Ising model in d = 1, 2, 3

`sri_short_range.tex` / `.pdf` (161 pages): the self-contained note behind the paper's Sec. 3.2, "Near the short-range
end". It is the only note of `SRI/`: since 16 October 2026 the derivations of the six separate notes that accompanied
the packages are its appendices.

Main text (Secs. 1 to 6, 26 pages):
- Sec. 1: conventions, the sources and who produced them, the status words, and one table with every quoted result,
  its status word, basis and caveats.
- Sec. 2, d = 1, the strong-weak dual of the chain (Benedetti, Lauria, Mazac, van Vliet): the matched two-coupling
  prescription and what "proved within the prescription" covers, the published C1 = -2 and C2 = 1/2, the closed forms
  of C3..C7 (zeta values, with exact certificates for C5..C7), C8 (a numerical record printed to about 85 digits and
  cross-checked to about 57 decimal places; rational part 88 exact; weight-seven formula conjectured), the independent
  re-derivation of the inputs of C5..C8 (its C8 1.9 to 4.0 standard errors below the record, depending on the error
  estimator), the magnetization-scheme calculation of C8 from the integrable point s = 1 (Sec. 2.7: 247.38118 +- 0.13,
  an empirical numerical uncertainty, 2.5e-5 from the record; the value the paper quotes), and the caveats.
- Sec. 3, d = 2, c2: the closed form in Gamma values and three 4F3(1) constants, the step that is not proved, the Monte
  Carlo of the regulated integral (three configurations), and fourth-order perturbation theory with the truncated
  cylinder Hamiltonian with its continuum analysis, its error budget and the revision of its error rule.
- Sec. 4, d = 3, c1: the retained-spectrum value, the review's two independent re-implementations, the estimated
  range (conditional on assumed gaps) and its sensitivity to the input box and the gaps.
- Secs. 5 and 6: authorship and provenance; open problems.

Appendices (derivations, edited to the note's notation and status words, and checked against their sources):
- A, B, C: the dual of the chain, from the compendium: the model, regulator and finite-response renormalization; the
  third to sixth orders (periods, trilogarithm lemma, endpoint inputs); the exact certificates and the seventh and
  eighth orders (rational part, the four packages, the zeta-value candidate, B_old).
- D: the two-coupling closure and the prescription (two formal, unrefereed arguments, with the review's checks).
- E: the closed form of c2 (elliptic cover, contact, Landen, period pairing, hypergeometric evaluation, telescoping).
- F: c2 from fourth-order perturbation theory on the cylinder (method of the base study).
- G: c1 in three dimensions (folded functional, blocks, conditional control of the omitted spectrum, the 60 retained
  primaries).
- H: Reproduction: each result mapped to `SRI/code/<package>/` (documentation in `SRI/docs/<package>/`), its record,
  target, tolerance and measured cost, and the stable pointers of `SRI/results/sr_values.json`.
- I: C8 from the integrable point in the magnetization scheme (package `integ_d1`): the Bethe-ansatz magnetization,
  the normal form of the s = 1 flow, the scheme, the kink clusters and their continuation, the gates, the 29 inputs,
  the comparison with its disclosures, and the records.

Status words (Sec. 1.3): literature; proved closed form within the prescription; closed form conditional on one
unproved step; numerical; conjectured; conditional. `SRI/results/sr_values.json` uses the short forms literature,
closed form, numerical, conjectured and conditional.

Build: `make` (or `latexmk -pdf -synctex=1 sri_short_range.tex`; pdfLaTeX, standard packages only, embedded
bibliography, no external input files, no figures). The PDF records the MD5 of the source it was built from.

Check: `make check` (or `python3 tools/check_note.py`; from `SRI/`, `make note`) verifies that the PDF is current (its
recorded source MD5 equals that of `sri_short_range.tex`), that the note's text files name no personal machine, user,
private folder or path, e-mail address or session id, lists the open items marked TODO, and, in the published tree,
verifies `MANIFEST.json`. `make strict` also fails while any TODO is open. No TODO is open.

Authorship: C3..C8 (the compendium), the c2 closed form, the cylinder base study, the c1 package and the two-coupling
closure and prescription arguments were written by OpenAI GPT-6 astra (via ChatGPT) and supplied by the author; the
derivations in Appendices A to G are theirs. The reviews, the independent re-derivation, the Monte Carlo, the cluster
layer, the continuum analysis and the magnetization-scheme calculation are by Claude Code (Anthropic) sessions, with
OpenAI Codex reviews of the cylinder analysis and of the magnetization-scheme calculation. The note, and the merge of the derivations into its appendices (16 October 2026), are by Claude Code
sessions. Single writer of this note: the SRI session (Claude Code).
