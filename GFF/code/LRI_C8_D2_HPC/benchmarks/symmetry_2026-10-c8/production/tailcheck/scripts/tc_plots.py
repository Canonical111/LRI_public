#!/usr/bin/env python3
"""Tail check figures (PNG): tc_plots.py AB_HILL.json NESTED_SPLIT.json OUT_DIR
 1. hill_vs_n.png: pilot-to-production Hill ratio of the confirmed graphs (cross-selected) against the tail models.
 2. nested.png: the fresh nested-N runs per group (tc_nested_split.py): sigma2(N)/sigma2(2^12), the Hill estimate and
    the top share."""
import json, math, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ab, nest, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), Path(sys.argv[3])
C = ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#e87ba4']
GRAY = '#8a8984'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#b5b4ad', 'axes.labelcolor': '#0b0b0b', 'xtick.color': '#52514e',
                     'ytick.color': '#52514e', 'axes.grid': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.6, 'lines.linewidth': 2})

# 1
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ratios = [8, 16, 32]
models = ab['hill_ratio_models_k16']
for (name, lab), col, ls in zip((('pareto', 'regularly varying (any xi)'), ('log_type', 'slowly varying / log-type'),
                                  ('lognormal', 'lognormal'), ('bounded_b4', 'bounded peak, b = 4')), (GRAY, GRAY, GRAY, GRAY), ('-', '--', ':', '-.')):
    ax.plot(ratios, [models[str(4096 * r)][name] for r in ratios], ls, color=col, lw=1.2, label=lab)
pts = {'free': {}, 'power': {}}
for k, v in ab['pilot_to_production'].items():
    s, lab, n2 = [x.strip() for x in k.split('|')]
    if lab.startswith('classified on a'):
        pts[s][int(n2.split('=')[1]) // 4096] = v['ratio']['median']
for (s, d), col in zip(pts.items(), C):
    xs = sorted(d)
    ax.plot(xs, [d[x] for x in xs], 'o-', color=col, ms=6, label=f'measured, confirmed {s} L8 (classified on a, measured on b)')
ax.set_xscale('log', base=2); ax.set_xticks(ratios); ax.set_xticklabels(['8', '16', '32'])
ax.set_xlabel('production / pilot points per replicate'); ax.set_ylabel('median xi-hat(production) / xi-hat(pilot)')
ax.set_ylim(0, 1.08); ax.legend(fontsize=7, frameon=False, loc='lower left')
ax.set_title('Hill estimate (k = 16) against sample size', fontsize=10)
fig.tight_layout(); fig.savefig(out / 'hill_vs_n.png', dpi=150); plt.close(fig)

# 2
cls = nest
order = ['conf_free', 'conf_power, no double-lift', 'untest_power, no double-lift', 'untest_power, double-lift',
         'controls (cleared, never screened, primitives)']
fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.3))
for n, col in zip(order, C):
    v = cls[n]; lv = v['levels']; lab = n + f" ({v['graphs']} graphs x 2 rates)"
    axs[0].plot(lv, v['sigma2_rel_geomean'], 'o-', color=col, ms=4, label=lab)
    axs[1].plot(lv, v['hill16_median'], 'o-', color=col, ms=4, label=lab)
    axs[2].plot(lv, v['share_median'], 'o-', color=col, ms=4, label=lab)
lv = cls[order[0]]['levels']
axs[0].plot(lv, [(N / lv[0]) ** (2 * 0.61 - 1) for N in lv], '--', color=GRAY, lw=1.2, label='infinite variance with xi = 0.61')
axs[0].plot(lv, [1 for N in lv], ':', color=GRAY, lw=1.2, label='finite variance at the MC rate')
for a_, t in zip(axs, ('N sigma^2(N) / its value at 2^12 (geometric mean)', 'Hill xi-hat, k = 16 (median)', 'largest |t| / sum |t| (median)')):
    a_.set_xscale('log', base=2); a_.set_xlabel('points per replicate N (nested prefixes)'); a_.set_title(t, fontsize=9)
axs[2].set_yscale('log'); axs[0].set_yscale('log', base=2)
axs[1].axhline(0.5, color=GRAY, lw=1, ls=':'); axs[1].axhline(0.44, color=GRAY, lw=1, ls='--')
axs[1].text(lv[-1], 0.455, 'rule 0.44', fontsize=7, color='#52514e', ha='right', va='bottom')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, fontsize=7, frameon=False, loc='lower center', ncol=4)
fig.tight_layout(rect=(0, 0.13, 1, 1)); fig.savefig(out / 'nested.png', dpi=150); plt.close(fig)
print('written', out / 'hill_vs_n.png', out / 'nested.png')
