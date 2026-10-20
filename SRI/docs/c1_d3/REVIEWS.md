# Reviews: c1_d3

- **2026-10-07, review of the pre-review delivery** (package written by OpenAI GPT-6 astra via ChatGPT; review by
  Claude Code, four parallel agents: physics and derivation; inputs and literature; code and reproduction; error-bound
  logic; reproduction runs on a personal desktop). Findings:
  - Solid: a0 = 3.3474594917, b0 = 12.2549141055, c_1 = 0.2731524238. The full from-scratch run reproduced every
    shipped number bit for bit (also with the newest dependency versions, up to a 2e-19 LP gap, and with Python 3.10,
    within 1e-13). Two independent re-implementations by the reviewers (one with its own blocks and quadrature; one with
    blocks from the Zamolodchikov-type recursion of Kos, Poland and Simmons-Duffin and the other arrangement of the
    integrals in Behan et al.) agreed with the
    package: c_1 to 1e-15 and 3e-13, a0 and b0 to between 6e-14 and 4e-12 (finest grids). All 60 inputs match
    Simmons-Duffin 2016; the leading inputs of Chang et al. and the Ward couplings check out; the folding passes closed-form tests; the
    d = 2 transplant reproduces the published values; c_1 agrees with 0.27(4) of Behan, Rastelli, Rychkov and Zan
    (a0 and b0 term by term) and with 0.269 of Behan 2018.
  - Major: (M1) the nominal linear program excludes the central inputs (68 sigma^4 rows; the inputs must move by up to
    1.15 quoted errors) and the envelope width follows the assumed error box; (M2) no gap sensitivity shown, and modest
    weakenings ((8, 6.5), (7, 7)) leave the estimated range [0.269, 0.276]; (M3) the gap hypotheses lacked evidence and
    citations (the Z2-odd margin above 7 is only about 0.3 to 0.7); (M4) a documented command overwrote the shipped receipt.
  - Minor: hard-coded reference constants, unasserted sign conditions, chosen (not derived) allowances, gaps in the
    verifier, bare asserts, the symmetric "0.2725 +- 0.0035" headline, missing literature comparison and citations, the
    folding and the odd-spin sign not derived in the note, the input-error status not stated; the package's
    "independent folding" check is a same-domain consistency check, not an independent test.
- **2026-10-08, review revision** (`review/RESPONSE_TO_REVIEW.md`; made by OpenAI GPT-6 astra (via ChatGPT) after our review and supplied by the author, as the author stated on 2026-10-15; the files name no author): all major and nearly all
  minor items addressed (feasibility analysis, gap and box sensitivity tables rerun by the package, derivations,
  guards, side-run-safe workflow, citations); the retained value is reported separately from the scenario-specific
  range; the independent re-implementations of the review were not part of the delivery.
- **2026-10-08, check of the revision** (Claude Code, two agents): numbers bit-identical, 23/23 regression checks pass.
  Leftovers: the widened-box scenarios (3, 4 and 6 quoted errors) keep the 5e-5 objective allowance although their
  sampled remainder exceeds it (ratios 1.08, 1.92, 4.32), so those sensitivity rows are too narrow by up to 2.7e-4; the
  README still says "15 checks / relocation test"; a Windows path bug in `verify.py integrity`; one citation missing
  (Behan, Lauria, Nocchi, van Vliet), Behan 2018 without journal reference, a wrong title (Zhu et al.); the spurious odd
  minima near 2.2 and 4.1 of Henriksson, Kousvos and Reehorst not mentioned. The review itself had one slip (it wrote
  I_sigma = -1.950413; -b0/(2 pi) = -1.950430) and had overlooked those minima. None of the leftovers changes c_1 or the
  nominal and doubled-padding envelopes.
- **2026-10-15, public export** (Claude Code): `make test`, `make replay` and `make replay-full` on a simulated export
  on symmetry (TESTS_c1_d3.md). The two independent re-implementations of the 2026-10-07 review now ship in
  `review_indep/` (verbatim) and `make replay` reruns them against the shipped `data/inputs/retained_spectrum.json`:
  - `review_indep/indep/` (code-and-reproduction reviewer): conformal blocks from the Dolan-Osborn quadratic Casimir
    equation, derived with sympy and solved as a double power series (its own engine, checked in the review against
    the exact d = 2 and d = 4 blocks); a0 and b0 from the note's integrals with its own quadrature in (r, theta) and its own subtraction
    radius (finest settings n = 128, r0 = 0.2, K = 44). It checks the package's blocks, quadrature and analytic
    continuation, not the arrangement of the integrals.
  - `review_indep/physics_review/` (physics reviewer): blocks from the Zamolodchikov-type recursion of Kos, Poland and
    Simmons-Duffin (arXiv:1406.4858); a0 and b0
    from the other arrangement of the integrals in Behan, Rastelli, Rychkov and Zan (Method 2), with the power
    divergences at r -> 0 subtracted analytically (NS = 34, r0 = 0.3, 160 x 160 nodes). It also checks the folding
    and arrangement of the integrals.
  - Result (symmetry, Python 3.12, NumPy 2.3.5, SciPy 1.17.1; Intel Xeon 6148 / AMD EPYC 7532): c_1 differs from the
    package's rerun value by 4.2e-14 / 5.8e-14 (indep) and 2.9e-13 / 4.6e-13 (physics_review), and the two differ by
    2.5e-13 / 4.0e-13; a0 by relative 1.6e-13 / 2.3e-13 and 1.3e-12 / 2.1e-12, b0 by 5.7e-15 / 1.4e-14 and
    2.5e-13 / 3.8e-13. The note's "agree to 10^{-12}" (Table 2) is tested on c_1 (absolute 1e-12); a0 and b0 agree at the
    10^{-12} level (relative up to 2.1e-12).
