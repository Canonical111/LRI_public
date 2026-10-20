#!/usr/bin/env python3
"""Tail check figure (PNG) of the joint-resampling nested-N analysis: tc_plots_joint.py NESTED_JOINT.json OUT.png
Common window 2^12..2^17 for every class (tc_nested_joint.py): (1) the C8-projected per-point variance relative to
2^12 (geometric mean over graphs), (2) the Hill estimate (median over graphs of the two-rate mean), (3) the per-graph
slopes of the double-lift targeted class with their joint-bootstrap 95% intervals (two campaigns per graph)."""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

J = json.load(open(sys.argv[1])); out = sys.argv[2]
C = ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#e87ba4', '#c9a227']
GRAY = '#8a8984'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#b5b4ad', 'axes.labelcolor': '#0b0b0b', 'xtick.color': '#52514e',
                     'ytick.color': '#52514e', 'axes.grid': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.6, 'lines.linewidth': 2})
order = ['confirmed free L8', 'confirmed power L8', 'untestable power L8, no double-lift', 'untestable power L8, double-lift (earlier sample)',
         'double-lift power L8, targeted (16 largest variance shares)', 'controls (cleared, never screened, primitives)']
W0 = [4096 << j for j in range(6)]
fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.4))
for n, col in zip(order, C):
    v = J['classes'][n]; lab = f"{n} ({v['graphs']} graphs)"
    axs[0].plot(W0, v['sigma2C_rel_geomean_W0'], 'o-', color=col, ms=4, label=lab)
    axs[1].plot(W0, v['hill_curve_W0'], 'o-', color=col, ms=4, label=lab)
axs[0].plot(W0, [(N / W0[0]) ** (2 * 0.61 - 1) for N in W0], '--', color=GRAY, lw=1.2, label='N^(2 xi - 1) at xi = 0.61 (heuristic)')
axs[0].plot(W0, [1 for N in W0], ':', color=GRAY, lw=1.2, label='constant (MC rate)')
for a_, t in zip(axs[:2], ('N Var(prefix mean), C8 projection, / value at 2^12', 'Hill xi-hat, k = 16 (median over graphs)')):
    a_.set_xscale('log', base=2); a_.set_xlabel('points per replicate N (nested prefixes, common window)'); a_.set_title(t, fontsize=9)
axs[0].set_yscale('log', base=2)
axs[1].axhline(0.5, color=GRAY, lw=1, ls=':'); axs[1].axhline(0.44, color=GRAY, lw=1, ls='--')
# per-graph slopes of the targeted class
G = [(k, g) for k, g in J['graphs'].items() if g['group'].startswith('double-lift power L8, targeted')]
graphs = sorted({g['graph'] for _, g in G}, key=lambda x: -max(g['production']['share'] for _, g in G if g['graph'] == x))
for i, gid in enumerate(graphs):
    for j, c in enumerate('ab'):
        g = next(g for _, g in G if g['graph'] == gid and g['campaign'] == c)
        s = g['slope_C8_W0']; y = i + (-0.15 if c == 'a' else 0.15)
        axs[2].errorbar(s['value'], y, xerr=[[s['value'] - s['ci95'][0]], [s['ci95'][1] - s['value']]], fmt='o', ms=3, color=C[4] if c == 'a' else C[3], lw=1)
axs[2].axvline(0, color=GRAY, lw=1, ls=':')
axs[2].set_yticks(range(len(graphs))); axs[2].set_yticklabels([f'G{x}' for x in graphs], fontsize=7); axs[2].invert_yaxis()
axs[2].set_xlabel('slope of ln N Var(prefix mean), 2^12..2^17 (C8 projection)')
axs[2].set_title('double-lift targeted, per graph: rate a (pink), b (purple), 95% CI', fontsize=8)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, fontsize=7, frameon=False, loc='lower center', ncol=3)
fig.tight_layout(rect=(0, 0.15, 1, 1)); fig.savefig(out, dpi=150); plt.close(fig)
print('written', out)
