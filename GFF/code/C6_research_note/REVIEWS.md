# Reviews: analytic representation of C6(1)

## 1. Independent review, 8 October 2026 (shipped: `GFF/code/LRI_C6_closed_form_review/REVIEW.md`)

- **Reviewer.** Claude Code session C71d, with three independent check agents (Claude). One round; the package was
  not modified. Target: `note/C6_progress_note.tex` (28 pages, sha256 `2f6d7f9d...`), `outputs/reassembly.json` and
  the package's integrity records.
- **Verdict.** No mathematical error found. The value 14331.68703275805432044546... was reproduced independently,
  from the reduced input (eq. 2.7 of the package note) and from the final nine-value formula (eq. 3.5).
- **Checks** (scripts and recorded outputs in `checks/`; replayed by `make -f public.mk replay` there):
  - reduced input re-evaluated from its definitions with the reviewer's own summation codes, at least two methods per
    input: C6(1) to about 65 digits (difference 2e-66), all eight blocks to 69-81 digits;
  - the inherited identities (coefficient series for the sixth- and eighth-power blocks, wheel periodization and core
    identities, the primitive contour relation) hold to 1e-63 or better;
  - the nine final values by separate one-dimensional codes to 40-64 digits, the three bivariate H values as genuine
    two-fold Mellin-Barnes integrals in double precision to 9-14 digits; eq. 3.5 rebuilt from them gives the
    reference to 4e-50 relative;
  - every exact claim of Sections 2-10 and Appendix A (sympy, or numerics at 30+ digits); the Appendix A recurrence
    implemented as printed gives P_a(N=48) equal to the table value to 3e-33;
  - the package's own `audit_package.py` and `audit_final_note.py` pass (on a scratch copy); the TeX builds to 28
    pages without warnings.
- **Most important finding, not in the package note.** The independent all-graph sum (`LRI_C6_1D_HPC`, unrounded
  14331.68703276838, allowance 4.9e-7) lies 1.03e-8 above the representation, 0.021 of the allowance. The source
  repair contributes +659.278983198744; without it the value would be 13672.408. The graph sum therefore confirms the
  corrected reduced input numerically (not a proof).
- **Nature of the result.** A finite formula in nine specified values, not a closed form in standard periods: the
  three bivariate values carry W0, M7 and P_a, for which the package's PSLQ attempt found no reduction; "nine" is a
  packaging count (angle parameters merge pairs of G values; alpha_4 and eta_7 depend on Gamma(1/4), log 2 and pi).
- **Gaps listed (none changes a result).** F1 the Bailey-Mishev representation of U6 used as a black box; F2 the
  supplied identities are not listed in one place; F3 the Euler-weight tail allowance 2^(100-N) is asserted without
  its hypothesis; F4/F4b left contour closures and the H* contour convergence not justified (true numerically); F5-F9
  unclear passages (slope table row 3, Appendix A gives data not derivation, boundary table, two constants); cosmetic
  items; process-style wording and file-path bibliography entries.
- **What changed because of it.** The package was not changed. The condensed note took the review's recommendations
  into its own text: the graph-sum agreement (Sections 1, 1.2, 22.9), the list of supplied identities and the
  conditional status of the enclosure (Section 22.9), and the "nine values describe packaging" caveat.
- **Recommendations not applied.** The fixes F1-F9 and the presentation changes were addressed to the package note;
  no revised package note was produced, so `note/C6_progress_note.tex` ships as delivered.

### Is REVIEW.md a raw log or a citable report?

It is a citable report: a dated, structured document with a verdict, the list of checks and their results, numbered
findings with line references, and a file index; it is not a transcript of a session and contains no prompts or
tool output. Condensed note Section 33 cites it by path. It is therefore shipped verbatim beside its scripts. It contains
one machine path (`/Users/.../envs/sage/bin/python3`, last line) and the session name C71d; neither is bound by a
checksum, so the path may be scrubbed. **Open question for the author:** keep REVIEW.md as shipped, or replace it by
the summary above.

## 2. Self-checks of the delivering session (records inside the package)

Not reviews by a second party, listed for completeness: `outputs/package_audit.json` (structural audit: 31 task
records passed, 193 Python files parse), `outputs/final_note_audit.json` (no missing references, 22 protected
equations unchanged), `outputs/final_pdf_qa.json` (all 28 pages inspected), `outputs/portability_check.json` and
`outputs/visual_review.json` (both from the earlier 34-page edition), `provenance/reference_metadata_check.json`
(bibliography metadata). No Codex review of this package or of the review is recorded.

## 3. Public overlay (2026-10-13)

`public.mk`, `public/verify_c6_analytic.py`, `public/verify_review.py`, `public/rerun_checks.py` were written for the
public release and tested on a scratch export (test and replay PASS in both packages); they have not been reviewed
by a second model.
