"""Figure fig_c4_delta_d2.pdf of the d = 2 section of the HT_Pert note.

(a) exact C4(L), L <= 2000, in the raw, consistent, diagonal zero-mode, full zero-mode (diagonal + off-diagonal) and
    complete windows, against the continuum C4(2);
(b) the eps^3 external-line coefficient delta^(3)(L), L <= 16000, against -4/(81 pi);
(c) the distance to the continuum, C4(2) - C4(L), log-log, for the complete window and for the full zero-mode window
    alone (which tends to C4(2) - 5.0386139 = 0.0102545, the part the mass window D^M supplies); beyond the data
    (L > 2000) thin lines extend each series with its no-log tower T22 fitted on 300 <= L <= 2000 (Appendix A.5).

Inputs (shipped in HT_Pert/code/lri_2d_coeff_independent_check/):
  residual_log/C4W_by_L.csv                     columns L, C4_raw, C4_consistent, C4_corrected_zm_diag, C4_full_zm, C4_W
  residual_log/large_L/results/tag3_L16000.npz  arrays L, delta3
Usage (from HT_Pert/):  python3 note/make_fig_d2.py [--pkg code/lri_2d_coeff_independent_check] [--out fig_c4_delta_d2.pdf]
Needs numpy and matplotlib.
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C4_CONT = 5.048868431354847   # C4(2), closed form (GFF condensed note)

ap = argparse.ArgumentParser()
ap.add_argument("--pkg", default="code/lri_2d_coeff_independent_check")
ap.add_argument("--out", default="fig_c4_delta_d2.pdf")
a = ap.parse_args()

rows = list(csv.DictReader(open(os.path.join(a.pkg, "residual_log", "C4W_by_L.csv"))))
col = lambda k: np.array([float(r[k]) for r in rows])
L4 = col("L")
m = L4 >= 2
t = np.load(os.path.join(a.pkg, "residual_log", "large_L", "results", "tag3_L16000.npz"))
L3, d3 = t["L"].astype(float), t["delta3"]
k = L3 >= 2

plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.6})
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.45))
for key, lab, st in (("C4_raw", "raw", "-"), ("C4_consistent", "consistent", "--"),
                     ("C4_corrected_zm_diag", "zero-mode (diagonal)", "-."),
                     ("C4_full_zm", "full zero-mode", ":"), ("C4_W", "complete window", "-")):
    ax[0].plot(L4[m], col(key)[m], st, lw=1.4 if key == "C4_W" else 0.9, label=lab)
ax[0].axhline(C4_CONT, color="k", lw=0.6, ls=":", label=r"continuum $C_4(2)$")
ax[0].set_xscale("log")
ax[0].set_xlabel(r"$L$")
ax[0].set_ylabel(r"$C_4(L)$")
ax[0].set_ylim(2.0, 5.3)
ax[0].legend(frameon=False, fontsize=6, loc="lower right")
ax[0].set_title("(a)", fontsize=9, loc="left")

ax[1].plot(L3[k], d3[k], lw=1.0, label=r"$\delta^{(3)}(L)$")
ax[1].axhline(-4 / (81 * np.pi), color="k", lw=0.6, ls=":", label=r"$-4/(81\pi)$")
ax[1].set_xscale("log")
ax[1].set_xlabel(r"$L$")
ax[1].set_ylabel(r"$\delta^{(3)}(L)$")
ax[1].set_ylim(-0.0162, -0.0130)
ax[1].legend(frameon=False, fontsize=6, loc="upper right")
ax[1].set_title("(b)", fontsize=9, loc="left")

def t22(Lf, y, lo=300):
    """No-log tower T22: 1, ln^i L/L and ln^i L/L^2 (i <= 2), fitted on lo <= L <= 2000; returns a callable."""
    basis = lambda x: np.column_stack([np.ones_like(x)] + [np.log(x) ** i / x for i in range(3)]
                                      + [np.log(x) ** i / x ** 2 for i in range(3)])
    sel = Lf >= lo
    A = basis(Lf[sel]); sc = np.abs(A).max(0)
    c = np.linalg.lstsq(A / sc, y[sel], rcond=None)[0] / sc
    return lambda x: basis(x) @ c
Lx = np.geomspace(2000, 1e6, 200)
for key, lab, st, lw in (("C4_W", "complete window", "-", 1.4), ("C4_full_zm", "full zero-mode", "--", 0.9)):
    ln, = ax[2].plot(L4[m], C4_CONT - col(key)[m], st, lw=lw, label=lab)
    ax[2].plot(Lx, C4_CONT - t22(L4, col(key))(Lx), st, lw=0.5, color=ln.get_color())
ax[2].axhline(C4_CONT - 5.0386139, color="k", lw=0.6, ls=":", label="0.01025")
ax[2].set_xscale("log")
ax[2].set_yscale("log")
ax[2].set_xlabel(r"$L$")
ax[2].set_ylabel(r"$C_4(2)-C_4(L)$")
ax[2].legend(frameon=False, fontsize=6, loc="lower left")
ax[2].set_title("(c)", fontsize=9, loc="left")

fig.tight_layout()
fig.savefig(a.out)
print("wrote", a.out)
