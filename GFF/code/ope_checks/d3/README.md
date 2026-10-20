# OPE data: independent checks, general d and d = 3

These scripts back Section 34 of the GFF note ("Checks made for this note", label `ope:checks`). They were written for
the note's review of the bulk one-point calculation supplied by the author on 16 October 2026, and they do not use the
package's code, except where a script checks the package's own finite-ε representation (stated below). Every script
runs as `python -I SCRIPT ARGS`, using the package's pinned Python set (3.11+, mpmath 1.3.0, sympy 1.14.0, numpy 2.3.5,
scipy 1.17.0). Each script exits 0 when its checks pass. `commands.json` lists the commands that the public replay runs.

| Script | What it checks | Inputs | Output shipped | In commands.json |
|---|---|---|---|---|
| `check_symbolic.py` | 32 exact identities: the package's C2..C5, b3, c3, b4, c4 and 3c5 − b5 against the note (gs:C0C4, gs:C5, gd:bc3, gs:b4, gs:c4, gs:D5); Lagrange inversion; fixed point; uncollected → collected H4 (c_x cancels); outer factor; log map; thermal forms | none | `check_symbolic.json` | yes |
| `check_transcription.py` | the formulas written in the note with Q_d, Ñ, c_x against the package's forms with T = 6Q_d, J_m, C_x | none | (prints) | yes |
| `check_blnv.py` | a^(2), a^(3) at d = 2, 3 against the explicit values of BLNV v6, Eq. (3.36) | none | `check_blnv.json` | yes |
| `check_numeric.py` | the d = 2 power parts of b5, c5 against the note's MS power sums (done:powerSums); C2..C5 from the masters against the status table; a^(2..6) at d = 1, 2, 3 from this note's masters, directly and through the log map; J_d closed form and bubble jet; amplitude re-assembly through a^(5) (poles cancel); symmetric kite from Pattern A; four- and five-vertex kernel sums | `GFF/code/LRI_C5_d3/masters_d3.json` | `check_numeric.json` | yes (a few minutes) |
| `check_bp3.py` | the four d = 3 Borel–Padé rows of Section 34 (own implementation), and, given the package's `results/bootstrap`, agreement with its historical and current runs | package results | `check_bp3.json` | yes |
| `check_kx_d2.py` | the crossed and symmetric four-vertex kites at d = 2 and ε = 0.02–0.15 from the note's two-dimensional kite formula (done:kiteFactorization, Thomae for slow ₃F₂(1)) against the package's finite-ε Mellin–Barnes form (`code/a4/full_kite_checks.py`, the object under test) | package `code/a4` | `check_kx_d2.json` | yes |
| `ms_b5_d3.py` | the MS b5, c5 at d = 3 from the finite-scheme Taylor jets of a production, against the package's b5, c5 and the note's D5 (a port to d = 3 of the d = 2 script in `../d2/ms_b5_from_jets.py`) | production `groups/`, `inputs/two_loop.json`, `masters_d3.json` | `ms_b5_c7d3.json` (C7(3) run1), `ms_b5_c8d3.json` (C8(3) prod1) | C7(3) only; the C8(3) groups are hosted data |
| `check_fig11.py` | kinks and the plotted cubic-order point of BLNV Figure 11, from the figure's vector paths | an SVG made with `pdftocairo -svg fig/plot_kinks_3d.pdf` from the arXiv source of arXiv:2311.02742v6 (not shipped) | `check_fig11.json` | no |
| `check_kx_scipy.py` | a rough double-precision direct quadrature of both kites at d = 1 (prints values; not a precision check: it misses the exact symmetric kite by 0.7% at ε = 0.15) | ε | none | no |

Records of the original runs: the symmetry cluster, sharedq (Intel Xeon Gold 6148), Python 3.13.3 with the pinned set;
`check_symbolic.json` and `check_numeric.json` come from jobs 576376 and 576377, and `ms_b5_c7d3.json` and
`ms_b5_c8d3.json` from job 576384. `check_blnv.json`, `check_bp3.json`, `check_fig11.json` and `check_kx_d2.json` were
made on a personal desktop in seconds.
