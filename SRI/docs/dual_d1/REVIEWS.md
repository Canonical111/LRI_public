# Reviews: dual_d1

- **2026-10-02, review of the compendium** (Claude Code; a multi-agent workflow over ten dimensions with adversarial
  verification of each finding). Verdict: no error in any coefficient or proof claim.
  - C3..C7 were recomputed independently from the stated formulas; the C5, C6 and C7 certificates are sound
    (mutation-tested: altered rows are rejected).
  - Every `reproduce.py` task passed on a Linux personal desktop, including `c8-numerical`, which reproduced the P6
    evaluation byte for byte.
  - The C8 zeta expression is the unique integer relation found against an enlarged basis of 26 further constants.
  - The numerical C8 is good to about 1e-85, limited by six inherited inputs that have neither an exact expression
    nor a second evaluation in the archive. pi_0 C8 = 88 is sound.
  - Resummed, the series agrees with the authors' d = 1 Monte Carlo (chi^2 about 8 for 9 degrees of freedom).
  - Defects found (archive and attribution, none mathematical):
    - the case-colliding pair `a_check_symbolic.expr` / `A_check_symbolic.expr`, lost on macOS (handled here: DATA);
    - 21 omitted ordered-integration "stage" programs (raw regeneration impossible);
    - the `p8-source` workflow does not recreate the `old_C7` and `rational_stages` paths;
    - in the note, Kosterlitz (1976) and Anderson-Yuval are not cited, the arXiv number given for Behan, Rastelli,
      Rychkov and Zan is wrong, and the `\src` footnotes give equation numbers of arXiv v2.
- **2026-10-03 to 2026-10-07, independent re-derivation** of the inputs of C^SR_5..C^SR_8 by separate Claude Code
  workflows that did not use the compendium's engines (package `indep_d1`): all 25 inputs of C5..C7 agree (rms pull
  0.34; C5 -0.13, C6 -0.78, C7 -0.08 sigma); the six inherited C8 inputs agree to about 1e-11 or within 2.1 sigma; the
  full C8 is 242.8 +- 2.4 against 247.38 (-1.9 sigma), the whole difference sitting in one input (the single-log part
  of the integral A9). The A9 tension was left open (see 2026-10-17).
- **2026-10-14, status of eq:sr-C8**: the author regards the C8 expression as likely correct and is working on a proof;
  the paper displays it as conjectured, not proved.
- **2026-10-15, this package** (Claude Code, dual_d1 builder): the paper's Eqs. eq:sr-closed and eq:sr-C8 equal,
  exactly, the compendium registry, its note, its C8 record and the closed forms its C6 and C7 input maps prove; every
  replayed task passes on symmetry (TESTS_dual_d1.md). Not reviewed by Codex.
- **2026-10-17, magnetization-scheme value of C^SR_8** (SRI note, Sec. 2.7 and Appendix I; its code and records are not
  in this release): 247.38118 +- 0.13, an empirical numerical uncertainty, from a scheme defined by the magnetization at
  the integrable point s = 1 that shares no input with this package or with `indep_d1` and uses no A9. It reproduces
  C3..C7 to 7e-26 and agrees with the record to 2.5e-5, which indicates that the low value of the re-derivation is the
  one in error (its own input comparison locates the difference in A9[eps^0 l^1]). At 5e-4 relative it does not test the coefficients of eq:sr-C8. OpenAI Codex reviewed its plan and
  inspected its code six times; two check criteria were amended after their data were seen (SRI note, Appendix I.7).
