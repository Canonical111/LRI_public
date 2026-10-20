#!/usr/bin/env python3
"""ln L coefficients of every window class: analytic closed forms (README Sec. 3) vs fits of the exact window
shifts to L = 20000 (../c4_exact/results/windows_L20000.npz, results/offdiag_L20000.npz) and L = 8000
(results/nm_L8000.npz).  Writes results/log_coeffs.txt."""
import os
import numpy as np
import fitlib as F

HERE = os.path.dirname(os.path.abspath(__file__))
pi = np.pi
w = np.load(os.path.join(HERE, "..", "c4_exact", "results", "windows_L20000.npz"))
o = np.load(os.path.join(HERE, "results", "offdiag_L20000.npz"))
n = np.load(os.path.join(HERE, "results", "nm_L8000.npz"))
L = w["L"].astype(float)
Ln = n["L"].astype(float)
T = ["1/L", "l/L", "l2/L", "1/L2", "l/L2"]
rows = [
    ("vacuum window (consistent - raw), outer 1 chi line x vacuum bubble", L, w["Delta_cons"], -5 / (8748 * pi), ["L"]),
    ("zero-mode window, diagonal, outer 2 chi x zero-mode sunset", L, w["Delta_zm_m2"], 12 / (243 * pi), []),
    ("zero-mode window, diagonal, outer 4 chi x 1-chi-line bubble", L, w["Delta_zm_m4"], 5 / (4374 * pi), []),
    ("zero-mode window, diagonal, outer 1 chi (all inner)", L, w["Delta_zm_m1"], 0.0, []),
    ("zero-mode window, diagonal, outer 3 chi (all inner)", L, w["Delta_zm_m3"], 0.0, []),
    ("zero-mode window, OFF-diagonal (dz=+-2), outer 2 chi x sunset", L, o["off_m2_m3"], 8 / (243 * pi), []),
    ("zero-mode window, off-diagonal, all other (m,m')", L, o["off"] - o["off_m2_m3"], 0.0, []),
    ("chi-sunset window -(g1^2/3pi){N,M'}: total", Ln, n["dC4"], 0.0, []),
    ("chi-sunset window: direct eps^4 part", Ln, n["direct"], None, []),
    ("chi-sunset window: part through g3", Ln, n["via_g3"], None, []),
]
out = ["# class | analytic ln L coefficient | fitted (Lmin = 2000 and 4000) | finite part"]
for name, x, y, ana, extra in rows:
    fits = []
    for Lmin in (2000, 4000):
        c, res, _ = F.fit(x, y, extra + ["l", "1"] + T, Lmin)
        fits.append((c["l"], c["1"], res))
    a = "  (not closed form)" if ana is None else f"{ana:+.12f}"
    out.append(f"{name}\n    analytic {a}   fit {fits[0][0]:+.12f} / {fits[1][0]:+.12f}   const {fits[1][1]:+.10f}"
               f"   res {fits[1][2]:.0e}")
beta_cons = -(20 / (243 * pi) + 5 / (4374 * pi))
out.append("")
out.append(f"beta_raw  = -(lambda + 20/(243 pi) + 5/(4374 pi)) = -725/(8748 pi) = {-725 / (8748 * pi):+.10f}")
out.append(f"beta_cons = -(20/(243 pi) + 5/(4374 pi))          = -365/(4374 pi) = {beta_cons:+.10f}")
out.append(f"beta_corr = -8/(243 pi)                                            = {-8 / (243 * pi):+.10f}")
out.append("beta_W    = 0")
txt = "\n".join(out)
open(os.path.join(HERE, "results", "log_coeffs.txt"), "w").write(txt + "\n")
print(txt)
