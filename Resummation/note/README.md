# Note: Borel resummation of the long-range Ising epsilon expansion in d = 1, 2, 3

`lri_resummation.tex` / `.pdf` (32 pages): the self-contained note behind the paper's sections on resummation and on the
comparison of the descriptions. Large orders and the critical instanton (with the d = 1 amplitude K_I and its benchmarks),
the conformal Borel resummation with the short-range end imposed in d = 1, 2, 3, the sensitivity ranges, the comparison
with Hamiltonian truncation, NRG and Monte Carlo, robustness (held-out coefficients, order and Borel-Leroy stability,
the precision of C8 and a ninth coefficient), limitations, formulas, and the reproduction (Appendix "Reproduction":
packages in `../code/`, `make replay`).

Build: `latexmk -pdf lri_resummation.tex` (pdfLaTeX; figures in `figures/`, the `_clean` renders of the package
figure scripts). `python3 tools/check_note.py` checks the figures and, in the published tree, `MANIFEST.json`.
Single writer: the resum session (Claude Code); built from its internal note (revised 2026-10-15 after a readability
review) by removing the internal provenance comments and replacing the file map with the public reproduction appendix.
