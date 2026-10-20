# Checks of Part V at d = 1

`check_d1.py` is the independent d = 1 check of Sections 34.9 and 34.12 of the GFF note. It imports no code of
`lri_ope_reproducibility`.
- The masters come from the note's own d = 1 closed forms: Sec. 1.1, `eq:KprovedFinal`, `gdr:L1` and `gs:d1Dictionary`.
- The one-point formulas are retyped from Part V.
- Numbers of the package and of the shipped five-loop records appear only as reference strings.
- It needs only mpmath (tested with 1.3.0, Python 3.13).

What it checks (112 checks and 3 recorded rows):
- the masters and C2..C5(1) against the note and the package;
- a(2)..a(6) at d = 1:
  - by convolution and by Taylor expansion of the factorized form;
  - against the low-order closed form and the published BLNV values;
  - against the printed formulas of BLNV (arXiv:2311.02742v6) at p = d = 1: R^(1), R^(2) of Eq. (3.34), the Ising
    quadratic coefficient of Eq. (3.35) and the O(N) cubic coefficient of Eq. (3.47) at N = 1; the printed (3.47)
    quadratic coefficient is checked with the opposite sign;
- the thermal forms, the log map and its exponentiation, including the map from the printed C2..C5(1) of Sec. 1;
- the RG input:
  - b3, c3, b4, c4 and 3c5 - b5 against the note;
  - b5 and c5 against the two-channel five-loop graph sums
    (`lri_numerical_resolution/verification/records/amplitude5_{maxgap,span}_18.json`, assembled in
    `LRI_C6_1D_HPC/reference/assembly_lower6.json`);
  - Lagrange inversion and the fixed-point series;
- the uncollected sixth-order assembly for three values of the crossed-kite coefficient;
- the bulk-leg integral J_1(a, b) against direct quadrature at two convergent points;
- the one-dimensional functional cross-check values.

Three rows are recorded, not checked, and are counted as INFO: the two residuals of the g* series (they should be
O(1) and similar at both values of eps) and the BLNV Eq. (3.35) cubic coefficient read literally (-1.5073 at d = 1,
against a3(1) = -0.85043).

Run: `python3 -I check_d1.py --dps 80 --json out.json`. It takes about 2 minutes on one core, most of it the two
quadratures; `--skip-quad` drops them.

The recorded run is `d1check_576652.out` and `check_d1_576652.json`: an Intel Xeon Gold 6148 node of the symmetry
cluster, 2026-10-16, 112 PASS, 0 FAIL, 3 INFO. The script was written by a Claude Code session for the review of the
bulk one-point data.
