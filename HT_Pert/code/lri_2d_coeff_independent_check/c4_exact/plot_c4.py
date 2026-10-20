#!/usr/bin/env python3
"""fits/c4_vs_L.png: (left) C_4(L) for raw / consistent / corrected vs L (log axis) with the continuum value;
(right) the same data minus the fitted 1/L tower (log model 'log T22', fit on L >= 200), which leaves
A + beta ln L: straight lines in ln L (residual logarithmic divergence) instead of flat lines at 5.0489."""
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fitlib as F

HERE = os.path.dirname(os.path.abspath(__file__))
files = [f for f in glob.glob(os.path.join(HERE, "results", "c4_L*.npz")) if "local" not in f]
d = np.load(max(files, key=lambda f: int(os.path.basename(f)[4:].split(".")[0])))
L = d["L"].astype(float)
REF = F.REF[4]
COL = {"C4raw": "#2a78d6", "C4cons": "#eb6834", "C4corr": "#1baf7a"}
LAB = {"C4raw": "raw", "C4cons": "consistent", "C4corr": "corrected (zero-mode-aware)"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), facecolor="#fcfcfb")
for ax in (ax1, ax2):
    ax.set_facecolor("#fcfcfb")
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_xscale("log")
    ax.axhline(REF, color=INK2, lw=1.2, ls=(0, (4, 3)))
sel = L >= 4
for key in ("C4raw", "C4cons", "C4corr"):
    ax1.plot(L[sel], d[key][sel], color=COL[key], lw=2, label=LAB[key])
    ax1.text(L[-1] * 1.04, d[key][-1], LAB[key].split(" ")[0], color=INK, va="center", fontsize=9)
ax1.text(5, REF + 0.04, f"continuum C4 = {REF:.4f}", color=INK2, fontsize=9)
ax1.set_xlabel("cutoff L")
ax1.set_ylabel("C4(L)")
ax1.set_title("Exact finite-cutoff C4(L)", color=INK, loc="left")
ax1.set_xlim(4, L[-1] * 1.6)
ax1.legend(frameon=False, loc="lower right", fontsize=9)

names = ["1", "l"] + F.tower(2, 2)
for key in ("C4cons", "C4corr"):
    c, mr, n = F.fit(L, d[key], names, 200)
    tail = sum(c[k] * F.basis(k, L) for k in names if k not in ("1", "l"))
    m = L >= 50
    ax2.plot(L[m], d[key][m] - tail[m], color=COL[key], lw=2,
             label=f"{LAB[key]}:  {c['1']:.4f} {c['l']:+.5f} ln L")
    ax2.text(L[-1] * 1.04, d[key][-1] - tail[-1], LAB[key].split(" ")[0], color=INK, va="center", fontsize=9)
ax2.set_xlabel("cutoff L")
ax2.set_ylabel("C4(L) minus fitted 1/L, 1/L^2 tower")
ax2.set_title("Tower removed: a residual ln L remains", color=INK, loc="left")
ax2.set_xlim(50, L[-1] * 1.9)
ax2.legend(frameon=False, loc="lower left", fontsize=9)
fig.tight_layout()
os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
fig.savefig(os.path.join(HERE, "fits", "c4_vs_L.png"), dpi=150)
print("wrote fits/c4_vs_L.png")
