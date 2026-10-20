# Independent verification of the one-loop instanton amplitude (7 October 2026)

An independent agent re-derived each ingredient of `../lri_instanton_amplitude.py` before reading it.
These are its scripts, copied unchanged from the session scratch directory; each prints its checks.

| Script | Claim checked |
|---|---|
| `c0d.py` | Negative-mode sign: zero-dimensional integral continued to arg g -> pi, Im Z/Z0 = -|l0|^{-1/2} e^{-S} |
| `c1.py` | Bubble finite part 36 A_g ln 2 (Fourier and position-space forms) |
| `c2.py`, `c2b.py` | L_sub = -1.76916977422036067824909414 (exact asymptotic tail via Hurwitz zeta) |
| `c3.py` | Circle spectrum v_0 = 3, v_1 = 1 from the chord-kernel Fourier coefficients |
| `c6.py`, `c6b.py`, `c6c.py` | phi^6 (d=3) spectral sum L1 by three methods |
| `c7.py` | Assembly of N, C_beta and K_I = 6.2466e-3, including the sign of the profile shift |
| `c7b.py` | Data ratios, effective Gamma power b_eff(n), and fits with 1/(n+3) corrections |
| `c8.py` | Next-order composition algebra (sympy): 2 calA - A_g kappa = -0.568 |

Requirements: `mpmath`, `sympy`. Each runs in seconds.
