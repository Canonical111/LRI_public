#!/usr/bin/env python3
"""Build the CSV/LaTeX tables and the summary figure of the 1D report from the copied records.

Inputs (records/): FIT_V3_SCAN.json (20 production rows, scan_v3_report.py, 2026-09-20), points/pre_ds*.json (frozen
(beta_c^pre, Delta_eps^pre) per point), published_and_epsilon_reference.csv (published MC values and the pre-campaign
epsilon-expansion reference values). Outputs: tables/*.csv, tables/*.tex, figures/*.pdf|png.
"""
import csv, json, math, os, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
rows = json.load(open(ROOT / 'records' / 'FIT_V3_SCAN.json'))
rows.sort(key=lambda r: r['ds'])

def dsname(ds):
    s = f'{ds:.7f}'.rstrip('0').rstrip('.')
    return s

# published MC + epsilon reference
ref = {}
with open(ROOT / 'records' / 'published_and_epsilon_reference.csv') as f:
    for r in csv.DictReader(f):
        ref[round(float(r['Delta_sigma']), 7)] = r

pre = {}
for r in rows:
    p = json.load(open(ROOT / 'records' / 'points' / f'pre_{"ds"+dsname(r["ds"])}.json'))
    (skey, v), = p.items()
    pre[r['ds']] = (float(skey), v['beta_c'], v['Delta_epsilon'], v['source'])

def fmt(x, nd=5):
    return '—' if x is None else f'{x:.{nd}f}'

def short_label(st):
    return (st.replace('sigma_sys', r'$\sigma_{\rm sys}$').replace('EXTRAPOLATION UNAVAILABLE', 'EXTRAP.\ UNAVAILABLE')
              .replace(' (sigma_sys coverage absent)', ''))

# ---------- CSV ----------
out = ROOT / 'tables' / 'final_table.csv'
with open(out, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Delta_sigma', 's', 'epsilon', 'decision', 'Delta_epsilon', 'sigma_stat', 'sigma_sys', 'sys_over_median_stat',
                'n_quotable', 'quoted_configuration', 'degree', 'crossing_Delta_inf', 'sigma_inf', 'Delta_omega_prime',
                'beta_c_pre', 'Delta_epsilon_pre', 'published_MC', 'published_MC_error', 'published_source'])
    for r in rows:
        ds = r['ds']; s = 1 - 2 * ds; eps = 1 - 4 * ds
        rr = ref.get(round(ds, 7), {})
        w.writerow([dsname(ds), f'{s:.6f}', f'{eps:.3f}', r['status'], fmt(r.get('Delta_epsilon')), fmt(r.get('sigma_stat')),
                    fmt(r.get('sigma_sys')), fmt(r.get('cap'), 1), r.get('n_quotable'), r.get('config'), r.get('degree'),
                    fmt(r.get('Delta_inf')), fmt(r.get('sigma_inf')), fmt(r.get('Delta_omega')),
                    f'{pre[ds][1]:.7f}', f'{pre[ds][2]:.5f}', rr.get('published_MC_Delta_epsilon', ''),
                    rr.get('published_MC_quoted_error', ''), rr.get('published_MC_source', '')])
print('wrote', out)

# ---------- LaTeX main table ----------
lines = []
for r in rows:
    ds = r['ds']; rr = ref.get(round(ds, 7), {})
    pub = ''
    if rr.get('published_MC_Delta_epsilon'):
        pub = f"{float(rr['published_MC_Delta_epsilon']):.4f}({rr['published_MC_quoted_error']})".replace('(0.0', '(').replace('(0.', '(')
        # compact form e.g. 0.5876(13)
        pv = float(rr['published_MC_Delta_epsilon']); pe = float(rr['published_MC_quoted_error'])
        e10 = int(math.floor(math.log10(pe))) if pe > 0 else -2
        mant = pe / 10 ** e10
        nd = -e10 + (1 if (1 <= mant < 2 and round(mant * 10) % 10 != 0) else 0)   # 0.0013 -> (13), 0.01 -> (1), 0.014 -> (14)
        pub = f'{pv:.{nd}f}({int(round(pe*10**nd))})'
        pub += r'\,' + ('UGA' if 'Uzelac' in rr['published_MC_source'] else 'APR')
    de = r.get('Delta_epsilon')
    if de is None:
        val = '—'
    else:
        val = f"{de:.5f}(" + f"{r['sigma_stat']*1e5:.0f})"
        val += f"({r['sigma_sys']*1e5:.0f})" if r.get('sigma_sys') is not None else r'($\dagger$)'
    xval = '—' if r.get('Delta_inf') is None else f"{r['Delta_inf']:.5f}({r['sigma_inf']*1e5:.0f})({r['Delta_omega']*1e5:.0f})"
    cfg = '—' if not r.get('config') else (r['config'].replace('_', r'\_') + f" d{r['degree']}")
    lines.append(f"{dsname(ds)} & {1-2*ds:.4g} & {short_label(r['status'])} & {val} & {r.get('n_quotable', 0)} & {cfg} & {xval} & {pub} \\\\")
(ROOT / 'tables' / 'final_table_rows.tex').write_text('\n'.join(lines) + '\n')
print('wrote final_table_rows.tex')

# ---------- LaTeX largest-pair fallback table ----------
lines = []
for r in rows:
    prs = r.get('pairs') or []
    cells = []
    for p in prs[-2:]:
        cells.append(f"{p['N']//1024}k--{p['N2']//1024}k: {p['Delta_eff_U']:.4f}({p['sigma_U']*1e4:.0f}) / {p['Delta_eff_Y']:.4f}({p['sigma_Y']*1e4:.0f})")
    lines.append(f"{dsname(r['ds'])} & " + ' & '.join(cells + ['—'] * (2 - len(cells))) + r' \\')
(ROOT / 'tables' / 'largest_pairs_rows.tex').write_text('\n'.join(lines) + '\n')

# ---------- beta_c^pre / window table ----------
lines = []
for r in rows:
    ds = r['ds']; s, bc, dep, src = pre[ds]
    hp = {N: 0.35 / (100 * (N / 1024) ** (1 - dep)) for N in (65536, 131072, 262144, 524288)}   # production x_max 0.35 (N0 window rule; registry x_max)
    n2 = 'yes' if ds >= 0.0625 and ds != 0.075 and ds != 0.0875 else 'no'
    lines.append(f"{dsname(ds)} & {s:.6g} & {bc:.6f} & {dep:.4f} & {hp[65536]*1e4:.2f} & {hp[524288]*1e4:.2f} & {n2} \\\\")
(ROOT / 'tables' / 'pre_rows.tex').write_text('\n'.join(lines) + '\n')
print('wrote pre_rows.tex')

# ---------- figure ----------
fig, ax = plt.subplots(figsize=(7.2, 4.6))
acc = [r for r in rows if r['status'].startswith('ACCEPTED')]
oth = [r for r in rows if r.get('Delta_epsilon') is not None and not r['status'].startswith('ACCEPTED')]
def err(rs):
    return [math.hypot(r['sigma_stat'], r.get('sigma_sys') or 0.0) for r in rs]
ax.errorbar([r['ds'] for r in acc], [r['Delta_epsilon'] for r in acc], yerr=err(acc), fmt='o', color='C0', ms=5,
            capsize=2, label=r'global fit, ACCEPTED ($\sigma_{\rm stat}\oplus\sigma_{\rm sys}$)')
ax.errorbar([r['ds'] for r in oth], [r['Delta_epsilon'] for r in oth], yerr=err(oth), fmt='s', mfc='white', color='C0', ms=5,
            capsize=2, label='global fit, other label (see table)')
xr = [r for r in rows if r.get('Delta_inf') is not None]
ax.errorbar([r['ds'] + 0.0015 for r in xr], [r['Delta_inf'] for r in xr],
            yerr=[math.hypot(r['sigma_inf'], r['Delta_omega']) for r in xr], fmt='^', color='C3', ms=4, capsize=2, alpha=0.8,
            label=r'crossing extrapolation $\Delta_\varepsilon^\infty$')
fb = [r for r in rows if r.get('Delta_epsilon') is None and r.get('pairs')]
ax.errorbar([r['ds'] for r in fb], [r['pairs'][-1]['Delta_eff_U'] for r in fb], yerr=[r['pairs'][-1]['sigma_U'] for r in fb],
            fmt='v', color='C2', ms=5, capsize=2, label=r'largest-pair $\Delta_{\varepsilon,{\rm eff}}(U)$ (no quotable fit)')
pubx, puby, pube = [], [], []
for k, rr in ref.items():
    if rr.get('published_MC_Delta_epsilon'):
        pubx.append(k); puby.append(float(rr['published_MC_Delta_epsilon'])); pube.append(float(rr['published_MC_quoted_error']))
ax.errorbar([x - 0.0015 for x in pubx], puby, yerr=pube, fmt='D', color='0.45', ms=4, capsize=2, label='published MC (UGA 2001, APR 2014)')
xs = [i / 400 for i in range(0, 101)]
ax.plot(xs, [2 * x for x in xs], ':', color='0.6', lw=1, label=r'$\Delta_\varepsilon = 2\Delta_\sigma$ (Gaussian)')
ax.axhline(0.5, color='0.8', lw=0.8)
ax.axhline(1.0, color='0.8', lw=0.8)
ax.set_xlabel(r'$\Delta_\sigma = (1-s)/2$')
ax.set_ylabel(r'$\Delta_\varepsilon$')
ax.set_xlim(0, 0.25); ax.set_ylim(0.44, 0.82)
ax.legend(fontsize=7.5, loc='upper right', frameon=False)
ax.set_title(r'1D long-range Ising: leading $\mathbb{Z}_2$-even scalar dimension, v3 protocol (2026-09-20)', fontsize=9.5)
fig.tight_layout()
fig.savefig(ROOT / 'figures' / 'delta_eps_vs_delta_sigma.pdf')
fig.savefig(ROOT / 'figures' / 'delta_eps_vs_delta_sigma.png', dpi=160)
print('wrote figure')

# zoom figure for the interior
fig, ax = plt.subplots(figsize=(7.2, 4.2))
sub = [r for r in rows if 0.1 <= r['ds'] <= 0.24 and r.get('Delta_epsilon') is not None]
ax.errorbar([r['ds'] for r in sub], [r['Delta_epsilon'] for r in sub], yerr=[r['sigma_stat'] for r in sub], fmt='o', color='C0', ms=5, capsize=2, label=r'global fit $\pm\sigma_{\rm stat}$')
ax.errorbar([r['ds'] for r in sub if r.get('sigma_sys')], [r['Delta_epsilon'] for r in sub if r.get('sigma_sys')],
            yerr=[r['sigma_sys'] for r in sub if r.get('sigma_sys')], fmt='none', ecolor='C0', alpha=0.35, capsize=0, elinewidth=5, label=r'$\pm\sigma_{\rm sys}$')
xr = [r for r in rows if 0.1 <= r['ds'] <= 0.24 and r.get('Delta_inf') is not None]
ax.errorbar([r['ds'] + 0.001 for r in xr], [r['Delta_inf'] for r in xr], yerr=[r['sigma_inf'] for r in xr], fmt='^', color='C3', ms=4, capsize=2, label=r'crossing $\Delta_\varepsilon^\infty \pm \sigma_\infty$')
allp = [r for r in rows if 0.1 <= r['ds'] <= 0.24 and r.get('pairs')]
ax.errorbar([r['ds'] - 0.001 for r in allp], [r['pairs'][-1]['Delta_eff_U'] for r in allp], yerr=[r['pairs'][-1]['sigma_U'] for r in allp], fmt='v', color='C2', ms=4, capsize=2, alpha=0.8, label=r'largest pair $\Delta_{\varepsilon,{\rm eff}}(U)$')
ax.errorbar([r['ds'] - 0.001 for r in allp], [r['pairs'][-1]['Delta_eff_Y'] for r in allp], yerr=[r['pairs'][-1]['sigma_Y'] for r in allp], fmt='x', color='C2', ms=5, capsize=2, alpha=0.8, label=r'largest pair $\Delta_{\varepsilon,{\rm eff}}(Y)$')
ax.plot(xs, [2 * x for x in xs], ':', color='0.6', lw=1)
ax.axhline(0.5, color='0.8', lw=0.8)
ax.set_xlim(0.095, 0.245); ax.set_ylim(0.42, 0.545)
ax.set_xlabel(r'$\Delta_\sigma$'); ax.set_ylabel(r'$\Delta_\varepsilon$')
ax.legend(fontsize=7.5, frameon=False, loc='upper right')
ax.set_title(r'Regime C detail: fits, crossing extrapolations and largest-pair effective exponents', fontsize=9.5)
fig.tight_layout()
fig.savefig(ROOT / 'figures' / 'regimeC_detail.pdf'); fig.savefig(ROOT / 'figures' / 'regimeC_detail.png', dpi=160)
print('wrote detail figure')
