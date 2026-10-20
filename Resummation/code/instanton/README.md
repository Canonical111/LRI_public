# One-loop instanton amplitude of the 1d LRI epsilon expansion

Result (note Section 7): `C_n ~ K_I (-1/A_eps)^n Gamma(n+4)`, `A_eps = 9 pi^2/Gamma(1/4)^4`,
`K_I = 6.2466e-3` (MS, analytic regulator `G_z(y) = |y|^{-(1-z)/2}`). The MS beta function behaves as
`b_L ~ (-1)^{L+1} C_beta A_g^{-(L+1)} Gamma(L+4)` with `C_beta = 0.024373`.
Order-z terms: the constrained-profile shift `(3/2) A_g (pi - 4 ln 2)` is kept; the O(z) term of the fixed-profile
action is argued to be a pure size rescaling that does not contribute; the explicit residue derivation is still to
be written out. The variants `K_I = 5.681e-3` (no profile shift) and `5.167e-3` (opposite sign) are disfavored by
the d=4 benchmark, which the adopted rule reproduces exactly, but are not excluded.

Data: C_3..C_8 confirm the sign of K_I; fits with 1/(n+3) corrections give asymptotic ratios 0.24-0.73, which are
model-dependent extrapolations, so the size is not tested to a stated accuracy. The next-to-leading coefficient d_1 is not computed (known
pieces -6.40; fits suggest d_1 of about -22 to -25).

| File | Purpose |
|---|---|
| `step0_zero_dim.py` | Sign, negative-mode factor and dispersion relation on the zero-dimensional phi^4 integral. |
| `step1c_phi6_d3.py` | phi^6 in d=3: reproduces McKane's general phi^N formula (2019, App. A) to 15 digits; the simplified N=6 expression printed there differs from that general formula by a factor 20.37 (the script prints both). |
| `step1_d4_validation.py` | phi^4 in d=4-eps, MS: reproduces McKane's C_beta and the nu^{-1} amplitude (with e^{-17/9}) exactly once the constrained-profile shift (-9/2) is included. |
| `step1b_bubble_check.py` | Flat-space bubble trace equals the analytically continued S^d mode sum (d=3). |
| `step2b_Lsub_check.py`, `step2c_Lsub_asymptotic.py` | Two independent evaluations of the slowly convergent circle sum L_sub. Generic accelerators (mpmath `nsum` defaults) fail on this n^{-3/2} tail. |
| `independent_verification/` | Scripts of the independent re-derivation (7 Oct 2026), with their own README. |
| `lri_instanton_amplitude.py` | The LRI calculation; writes `results.json` (amplitude, pieces, numerical checks of the closed forms, data ratios). |

All programs run in seconds with `mpmath`, `numpy` and `scipy`. The ingredients:
`L_sub = -1.769169774220360678`, bubble finite part `36 A_g ln 2`, special modes `21/2`,
profile shift `(3/2) A_g (pi - 4 ln 2)`, collective coordinates and legs `9/(2 pi^2 A_g)`,
negative mode and two saddles `2^{-1/2}`, composition `e^{-2 calA A_g}/(3 pi A_g)` with `calA = pi + 4 ln 2`.
