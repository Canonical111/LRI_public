# Expansions about the short-range end

The long-range Ising model expanded about its short-range end. In d = 1 the dual series of the chain,
Delta_eps = 1 + sum_n C^SR_n Delta_sigma^(n/2), through C^SR_8; in d = 2 and 3,
Delta_eps = Delta_eps^SR + sum_n c_n delta^n with delta = (s_* - s)/2, the crossover coefficients c_2 (d = 2) and c_1
(d = 3). This folder reproduces every number of the paper's Sec. 3.2 ("Near the short-range end"): the \SR* macros
(also where the abstract and the Discussion reuse them), Eqs. eq:sr-closed and eq:sr-C8, Table tab:sr, the c_2 row of
Table tab:htpert (the C^SR_2(2) row, with the caption), and the closed form of c_2 in the closed-forms appendix (cf:sec:cr2).

- `note/`: the self-contained note (TeX, PDF), the only note of this folder: the status of every quoted result,
  provenance, open problems, and in its appendices the full derivations behind every package (A to C: the d = 1 dual;
  D: the two-coupling closure and prescription arguments; E: the closed form of c_2; F: the cylinder method; G: c_1 in
  d = 3; I: C^SR_8 from the integrable point s = 1) and Appendix H "Reproduction".
- `code/<pkg>/`: one package per result (below). Production code ships verbatim, at its git commit or as a dated
  snapshot with a sha256 list (`public/SNAPSHOT.sha256`); `public.mk` and `public/` are added.
- `results_map.md`: one table of every quoted number (each \SR* macro the paper prints, the equations and the
  table cells) with status, record, command and tolerance; the per-package maps are `docs/<pkg>/results_map.md`.
- `docs/<pkg>/`: the documentation of each package: README, REPRODUCE, PROVENANCE, DATA, REVIEWS, requirements,
  `results_map.md` (every quoted number -> record, command, tolerance) and TESTS (the export tests on symmetry).
- `results/`: `quoted_numbers.json` (every \SR* macro with its text as printed and whether the paper prints it, the
  TeX of eq:sr-closed and eq:sr-C8, the cells of tab:sr); `sr_values.json` (machine-readable values for other folders,
  each with the file and JSON pointer where it lives in this tree).
- `verify/`: `sri_lib.py` (the shared replay helper: PASS/FAIL/INFO/SKIP table, half-up rounding to the printed
  digits) and `check_sr_values.py` (`results/sr_values.json` against the tree).

| Package | What |
|---|---|
| `code/dual_d1/` | the compendium of the dual of the chain: C^SR_3..C^SR_8, the exact certificates of C^SR_5..C^SR_7, the 85-digit record of C^SR_8 (pruned dated snapshot) |
| `code/indep_d1/` | the independent re-derivation of every input of C^SR_5..C^SR_8 with separately written code (Mellin-Hepp sector engine, own RG framework), compared with the compendium only at the end |
| `code/integ_d1/` | C^SR_8 from the integrable point s = 1 in a scheme defined by the magnetization: the Bethe-ansatz flow, kink clusters of up to four bubbles continued in the kink charge, the gates and the assembly, with the frozen records and the raw engine outputs they are rebuilt from; no nine-kink integral and no input shared with `dual_d1` or `indep_d1` |
| `code/c2_closed_d2/` | the closed form of c_2 (one Gamma ratio, three 4F3(1) constants) and the review's end-to-end 8D Monte Carlo |
| `code/c2_cylinder_d2/` | c_2 from fourth-order perturbation theory with the truncated cylinder Hamiltonian: solver, cluster records (symmetry, SDSC Expanse) and the continuum analysis |
| `code/c1_d3/` | c_1 in d = 3 from the retained 60-primary spectrum of the 3d Ising CFT, with the estimated range from a crossing linear program, and the review's two independent re-implementations (`review_indep/`) |
| `code/closure_d1/` | checks of two formal arguments on the dual by OpenAI GPT-6 astra, which are in the note's Appendix D (no quoted number): an independent check of the closure argument's finite algebra (two bulk counterterm directions suffice, formally at every order) and, in `prescription/`, the prescription argument's checker archive (the archive's normalized interval responses extract the local beta functions) with an independent re-derivation of the beta recurrence |

| Result (paper) | Value | Status | Package |
|---|---|---|---|
| C^SR_1, C^SR_2 (tab:sr; \SRorderLitword) | -2, 1/2 | literature | cited (dual_d1 registry) |
| C^SR_3..C^SR_7 (\SRCthree..\SRCseven; eq:sr-closed) | 5.72737, -12.1962, 29.2378, -58.6657, 51.0690 | proved closed form within the prescription | dual_d1 |
| C^SR_8 (\SRCeight; eq:sr-C8) | 247.381, conjectured closed form agreeing with the record to about 85 digits | conjectured closed form (record without an interval bound) | dual_d1 |
| rational part of C^SR_8 | 88 | proved closed form (exact rational projection) | dual_d1 |
| inputs of C^SR_5..C^SR_7, independent (\SRindepPullMax, note only) | largest pull 0.9 (0.915, Omega; coefficients 0.78) | numerical (statistical) | indep_d1 |
| C^SR_8, independent (\SRCeightIndep, \SRCeightPull, \SRCeightPullMax; note only since paper e89a94a0) | 242.8 +- 2.4; 1.9 to 4.0 standard errors below the record, by error estimator (SRI note) | numerical (statistical); the magnetization-scheme value indicates that this value is the one in error | indep_d1 |
| C^SR_8, magnetization scheme (\SRCeightMag, \SRCeightMagDiff, \SRintegClosedDev; Sec. 3.2 "Checks") | 247.38 +- 0.13 (247.38118 +- 0.13 in the note); 2.5e-5 from the record (SRI note, Sec. 2.7 and Appendix I) | numerical (empirical numerical uncertainty, not a standard deviation or a bound; two check criteria amended after their data were seen) | integ_d1 |
| order counts (\SRorderword, \SRorderLitword; \SRorder, \SRclosed, \SRorderLit note only) | eight, two | as above | dual_d1 |
| c_1 in d = 2 (tab:sr) | 0 | literature | cited (c2_closed_d2 checks I_2(0) = 0) |
| c_2 closed form (\SRtwoCtwo; tab:sr; cf:sec:cr2) | -4.06627 | closed form, conditional on one unproved step | c2_closed_d2 |
| c_2 Monte Carlo (\SRtwoCtwoMC) | -4.075 +- 0.019 | numerical (one standard error) | c2_closed_d2 |
| c_2 cylinder (\SRtwoCtwoHT, \SRtwoCtwoHTDev; tab:htpert; \SRtwoCtwoHTNmax note only) | -4.0670(24); 2x10^-4 from the closed form; N <= 1024 | numerical (linear sum of systematic diagnostics, not a standard deviation) | c2_cylinder_d2 |
| c_1 in d = 3 (\SRthreeCone; tab:sr) | 0.2732 (0.273152) | numerical | c1_d3 |
| two independent implementations of c_1 agree to 10^-12 (\SRthreeConeImplDev, note only) | c_1 within 4e-14 and 3e-13 of the package | numerical (check; a bound) | c1_d3 |
| c_1 estimated range (\SRthreeConeRange) | [0.2690, 0.2760] | conditional (assumed gaps) | c1_d3 |
| earlier estimate of c_1 (\SRthreeConeBRRZ) | 0.27(4) | literature | cited (c1_d3) |

Status words (as in the note): *literature*, a published value, cited where it is used (C^SR_1, C^SR_2 and c_1 in
d = 2, re-derived here as checks; S and E_SR in d = 3 used as inputs); *proved closed form within the
prescription*, an exact expression whose derivation is complete, with exact certificates where it is computer-assisted,
and never beyond the stated prescription; *numerical*, with the kind of error stated; *conjectured*, an exact expression
supported numerically without a proof; *conditional*, holds only under stated, unproved assumptions.

Start with `make test` (about 12 min on one node) and `make replay` (about 17 min); `REPRODUCE.md` gives the order and
the cost. Every quoted number, its record, rule and tolerance: each package's `docs/<pkg>/results_map.md` and the note's Appendix
"Reproduction".

Caveats (kept wherever these numbers are used):
- **The two-coupling closure is argued, not tested.** Every C^SR_n above n = 2 is computed within the compendium's
  matched two-coupling prescription of the dual. Two unrefereed arguments (the note's Appendix D; checks in
  `code/closure_d1/`) support formally that only the two couplings need counterterms and that the prescription extracts
  the local beta functions; neither checks the historical high-order integrations or the identification of the dual
  with the chain. "Proved" means proved
  within the prescription; no calculation here tests the closure numerically, and the independent re-derivation tests
  the numbers within the same prescription. The NRG of the paper, which does not use the dual, confirms C^SR_3..C^SR_5.
- **C^SR_8 is a conjectured closed form.** The paper reports eq:sr-C8 as conjectured: it agrees with the numerical
  record to about 85 digits (residual 3.1e-86, below the printing floor) but has no certificate, and the record has no
  interval bound (six of its inputs are single numerical records). The
  independent re-derivation gives 242.8 +- 2.4, 1.9 to 4.0 standard errors below the record depending on the error
  estimator, the whole difference in one input
  (the single-log part of the integral A9 inside the nine-kink input J9, -2.19 standard errors). A third calculation,
  in a scheme defined by the magnetization at the integrable point s = 1 (SRI note, Sec. 2.7 and Appendix I;
  `code/integ_d1/`), shares no input with either and gives 247.38118 +- 0.13 (empirical numerical uncertainty, not a
  standard deviation or a bound; two check criteria amended after their data were seen), 2.5e-5 from the record; the
  paper quotes it as 247.38 +- 0.13 in Sec. 3.2 ("Checks"). It indicates that the low value of the re-derivation is the one in error, and it
  does not test the coefficients of eq:sr-C8.
- **The raw integrals of the compendium cannot be regenerated** (21 stage programs are missing from its archive). The
  folder offers the replay of every quoted number from the shipped records, the exact certificate checks and the
  independent re-derivation instead.
- **The c_2 closed form rests on an unproved step.** It is a formal result in a critically tuned analytic
  minimal-subtraction prescription; identifying it with the physical coefficient needs a regulator-uniform bound on the
  remainder of the nested subtractions, which is not proved. It is checked numerically: the Monte Carlo agrees at 0.5
  standard errors (a 0.5 % test), the cylinder Hamiltonian to 1.9e-4 relative.
- **The cylinder error is a linear sum of diagnostics**, 64 % of it the choice of regulator model; it is not a standard
  deviation or an enclosure. The error rule was revised (plan rev 4 to rev 7) after the first result had been seen; the
  central value did not change. The closed form was known but is not an input. The last code fixes are not
  Codex-inspected (no number changed).
- **The estimated range of c_1 is conditional** on gap assumptions (no unlisted Z2-even primary below dimension 8, no Z2-odd
  below 7), inputs within twice their quoted errors and chosen allowances. It is not a confidence interval or a
  certified bound; modest relaxations reach outside it, and the central inputs are infeasible in the nominal linear
  program.
