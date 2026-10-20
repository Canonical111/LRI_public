#!/usr/bin/env python3
"""Write the d = 2 table (tab_d2_values.tex) and figure (fig_d2_DeltaE.pdf) of the HT note from the shipped results.

usage: python make_d2_note_inputs.py POINTS_CSV OUTDIR
POINTS_CSV = HT/results/HT_2d/prod1/points.csv (main records nz = 16 are used; collect.py output, = the records).
"""
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def classify(x, D):
    st = [b - a for a, b in zip(D, D[1:])]
    if x >= 0.45:
        return "small steps"
    if 0.25 <= x <= 0.4:
        g = (st[-1] / st[-5]) ** 0.25
        return f"rises; shrink {100 * (1 - g):.0f}\\%/step"
    if x == 0.2:
        return "not monotone"
    return "falls; steps grow"


def main(points, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    seq = defaultdict(dict)
    s_of = {}
    for r in csv.DictReader(open(points)):
        if r["chain"].startswith("x") and r["nz"] == "16":
            x = float(r["x"])
            seq[x][int(r["L"])] = float(r["Delta_thermal"])
            s_of[x] = float(r["s"])
    cols = [16, 20, 22, 24]
    lines = [r"\begin{tabular}{@{}l l " + "l " * len(cols) + r"l l@{}}", r"\toprule",
             r"$\Delta_\sigma$ & $s$ & " + " & ".join(f"$N={c}$" for c in cols) + r" & last step & behaviour\\", r"\midrule"]
    for x in sorted(seq):
        Ls = sorted(seq[x])
        D = [seq[x][L] for L in Ls]
        vals = [f"{seq[x][c]:.8f}" if c in seq[x] else "n.s." for c in cols]
        last = D[-1] - D[-2]
        e = int(math.floor(math.log10(abs(last))))
        laststr = f"${last / 10**e:+.2f}\\times10^{{{e}}}$"
        lines.append(f"{x:g} & {s_of[x]:g} & " + " & ".join(vals) + f" & {laststr} & {classify(x, D)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "tab_d2_values.tex").write_text("\n".join(lines) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9))
    for x in sorted(seq):
        Ls = sorted(seq[x])
        D = [seq[x][L] for L in Ls]
        ax = axes[0] if x <= 0.2 else axes[1]
        ax.plot(Ls, D, "o-", ms=3, lw=1, label=f"{x:g}")
    for ax, t, loc in zip(axes, (r"$\Delta_\sigma\leq0.2$", r"$\Delta_\sigma\geq0.25$"), ("lower left", "center right")):
        ax.set_xlabel(r"bath cutoff $N$")
        ax.set_xticks(range(8, 25, 2))
        ax.set_title(t, fontsize=10)
        ax.legend(fontsize=7, title=r"$\Delta_\sigma$", title_fontsize=7, ncol=4, loc="upper center",
                  bbox_to_anchor=(0.5, -0.2), frameon=False)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"$\Delta_{\varepsilon}(N)$")
    fig.tight_layout()
    fig.savefig(out / "fig_d2_DeltaE.pdf")
    print("wrote", out / "tab_d2_values.tex", out / "fig_d2_DeltaE.pdf")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
