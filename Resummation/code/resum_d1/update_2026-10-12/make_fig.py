#!/usr/bin/env python3
"""Diagnostic figure (draft, matplotlib): 1d residuals relative to the endpoint-v CB8 with C^SR_1..C^SR_8.
2026-10-13: C8 from the C8(1) switch (sr_endpoint.py); reads references_refreshed.csv next to this file and writes
fig_1d_srK_residuals.{png,pdf} to <switch output root>/sr_endpoint/ (the 2026-10-12 draft here is not overwritten)."""
import csv, numpy as np, matplotlib
from pathlib import Path
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import sr_endpoint as S
x = np.linspace(0.0005, 0.2495, 400)
ref = S.cb(x, 8)
cores = {K: [S.cb(x, K, o, b, a) for o in (6, 7, 8) for b in (2, 3, 4) for a in (-1, 0, 1)] for K in (5, 6, 7, 8)}
lo = np.min([np.min(c, 0) for c in cores.values()], 0); hi = np.max([np.max(c, 0) for c in cores.values()], 0)
k4 = S.cb(x, 4); k4c = [S.cb(x, 4, o, b, a) for o in (6, 7, 8) for b in (2, 3, 4) for a in (-1, 0, 1)]
HERE = Path(__file__).resolve().parent; OUTD = S.SW.out_root()/'sr_endpoint'; OUTD.mkdir(parents=True, exist_ok=True)
R = {(r['method'], round(float(r['x']), 6)): r for r in csv.DictReader(open(S.SW.references_csv()))}
s = 1e3
fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=150)
ax.fill_between(x, s*(np.min(k4c, 0)-ref), s*(np.max(k4c, 0)-ref), color='#eb6834', alpha=0.10, lw=0,
                label=r'core band, $C^{\rm SR}_{1..4}$ (archived)')
ax.fill_between(x, s*(lo-ref), s*(hi-ref), color='0.55', alpha=0.35, lw=0, label=r'envelope, $C^{\rm SR}_{1..K}$, $K=5$-$8$')
for K, ls in ((5, ':'), (6, '-.'), (7, '--')):
    ax.plot(x, s*(S.cb(x, K)-ref), color='0.25', lw=0.9, ls=ls, label=f'CB8, K={K}')
ax.plot(x, s*(k4-ref), color='#eb6834', lw=1.6, ls='--', label='CB8, K=4 (archived baseline)')
ax.axhline(0, color='#2a78d6', lw=2, label='CB8, K=8 (reference)')
def pts(method, keep):
    out = []
    for (m, xx), r in R.items():
        if m == method and keep(r): out.append((xx, float(r['y']), r))
    return sorted(out)
def refat(xx): return S.cb(np.array([xx]), 8)[0]
ht = pts('HT', lambda r: r['status'] in ('final', 'one_sided'))
ax.errorbar([p[0] for p in ht], [s*(p[1]-refat(p[0])) for p in ht], yerr=[s*float(p[2]['error'] or 0) for p in ht],
            fmt='s', ms=6, color='#1baf7a', mec='white', mew=0.8, capsize=2, lw=1, label='HT, finite coupling (final)')
nrg = pts('NRG', lambda r: r['status'] not in ('flagged', 'not_converged'))
ax.errorbar([p[0] for p in nrg], [s*(p[1]-refat(p[0])) for p in nrg], yerr=[s*float(p[2]['error']) for p in nrg],
            fmt='D', ms=5.5, color='#2a78d6', mfc='white', capsize=2, lw=1, label='NRG')
nf = pts('NRG', lambda r: r['status'] in ('flagged', 'not_converged'))
ax.plot([p[0] for p in nf], [s*(p[1]-refat(p[0])) for p in nf], 'D', ms=5.5, color='#2a78d6', mfc='none', alpha=0.45,
        label=r'NRG, not converged in chain depth' if any(p[2]['status'] == 'not_converged' for p in nf) else r'NRG, flagged near $s=1/2$')
mc = pts('MC', lambda r: r['status'].startswith('ACCEPTED'))
ax.errorbar([p[0] for p in mc], [s*(p[1]-refat(p[0])) for p in mc],
            yerr=[s*(float(p[2]['stat'])**2+float(p[2]['error'])**2)**.5 for p in mc],
            fmt='o', ms=5, color='#6250d6', mec='white', mew=0.8, capsize=2, lw=1, label='MC, accepted (stat $\\oplus$ sys)')
ax.set_xlim(0, 0.25); ax.set_ylim(-6, 6)
ax.set_xlabel(r'$\Delta_\sigma$'); ax.set_ylabel(r'$10^{3}\times[\Delta_\mathcal{E}-\Delta_\mathcal{E}^{\rm CB8,\,K=8}]$')
ax.grid(color='0.9', lw=0.6); ax.set_axisbelow(True)
ax.legend(fontsize=7.2, ncol=2, loc='lower left', frameon=False)
ax.set_title('1d: resummation with the short-range series through $C^{\\rm SR}_K$ vs HT, NRG, MC', fontsize=9.5)
fig.tight_layout(); fig.savefig(OUTD/'fig_1d_srK_residuals.png'); fig.savefig(OUTD/'fig_1d_srK_residuals.pdf')
print('saved; off-scale points:', [round(p[0],4) for p in mc+ht+nrg if abs(s*(p[1]-refat(p[0])))>6])
