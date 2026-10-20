#!/usr/bin/env python3
"""C4(L) in every scheme vs the continuum value (fits/c4w_vs_L.png)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REF = 5.048868431354847
c = np.load(os.path.join(HERE, "..", "c4_exact", "results", "c4_L2000.npz"))
o = np.load(os.path.join(HERE, "results", "offdiag_L20000.npz"))
n = np.load(os.path.join(HERE, "results", "nm_L8000.npz"))
K = len(c["L"])
L = c["L"][1:]
s = slice(1, K)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
curves = [("raw", c["C4raw"][s], "#999999"), ("consistent (vacuum window)", c["C4cons"][s], "#4c72b0"),
          ("zeromode (diagonal zero-mode window)", c["C4corr"][s], "#dd8452"),
          ("+ off-diagonal zero-mode window", c["C4corr"][s] + o["off"][s], "#55a868"),
          ("+ chi-sunset window  (complete, W)", c["C4corr"][s] + o["off"][s] + n["dC4"][s], "#c44e52")]
for lab, y, col in curves:
    ax[0].semilogx(L, y, color=col, lw=1.6, label=lab)
ax[0].axhline(REF, color="k", ls="--", lw=1, label="continuum C4(2) = 5.048868")
ax[0].set_xlabel("L"); ax[0].set_ylabel("C4(L)"); ax[0].set_ylim(1.3, 5.2); ax[0].legend(fontsize=7.5, loc="lower right")
ax[0].set_title("C4(L), exact, L <= 2000")
W = c["C4corr"][s] + o["off"][s] + n["dC4"][s]
ax[1].loglog(L, REF - W, color="#c44e52", lw=1.6, label="continuum - C4_W(L)")
import fitlib as F
cc, res, _ = F.fit(L.astype(float), W, ["1", "1/L", "l/L", "l2/L", "1/L2", "l/L2", "l2/L2"], 300)
mod = sum(cc[k] * F.basis(k, L.astype(float)) for k in cc)
ax[1].loglog(L, REF - (c["C4corr"][s] + o["off"][s]), color="#55a868", lw=1.2, ls=":",
             label="continuum - (zeromode + off-diag)  [-> 0.01025]")
ax[1].loglog(L[L >= 300], cc["1"] - mod[L >= 300], color="k", lw=0.9, ls="--",
             label=f"tower fit L>=300: A = {cc['1']:.7f}")
ax[1].set_xlabel("L"); ax[1].legend(fontsize=7.5); ax[1].set_title("approach to the continuum")
fig.tight_layout()
os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
fig.savefig(os.path.join(HERE, "fits", "c4w_vs_L.png"), dpi=130)
print("wrote fits/c4w_vs_L.png")
