#!/usr/bin/env python3
"""Write the published d = 1 tables from the shipped analysis outputs and identity records.

Outputs (in --out): delta_eps_table.md, identity_violations.md, holdout_and_local_exponent.md (HT/results/HT_1d/) and
the note fragments tab_d1_main.tex, tab_d1_omegaeff.tex, tab_d1_ident.tex (HT/note/sections/). NRG values come from
nrg_reference.json next to quoted_numbers.json. replay_ht1d.py regenerates them in
.work/tables and compares them byte for byte with the shipped copies.
Usage: python3 public/make_tables_ht1d.py --out <dir> [--quoted ../../results/HT_1d/quoted_numbers.json]
"""
import argparse, collections, json, math
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
ap.add_argument('--quoted', default=str(PKG / '../../results/HT_1d/quoted_numbers.json')); a = ap.parse_args()
O = Path(a.out); O.mkdir(parents=True, exist_ok=True)
X = {x['delta']: x for x in json.loads((PKG / 'dens_v1_extrapolation.json').read_text())}
H = {x['delta']: x for x in json.loads((PKG / 'dens_v1_holdout.json').read_text())}
Q = {q['id']: q for q in json.loads(Path(a.quoted).read_text())['numbers']}
nrg = {round(r['ds'], 6): dict(r, total_uncertainty=r.get('total') or r.get('total_uncertainty') or 0.)
       for r in json.loads((Path(a.quoted).parent / 'nrg_reference.json').read_text())}
status = {Q[k]['delta']: Q[k]['quoted'] for k in Q if k.startswith('U') and k != 'U00'}

def slopes(d):
    s = dict(zip(X[d]['cuts'], X[d]['values'])); N = sorted(s)
    return [(math.sqrt(N[i] * N[i + 1]), (s[N[i + 1]] - s[N[i]]) / math.log(N[i + 1] / N[i])) for i in range(len(N) - 1)]
def omega_eff(d):
    s = slopes(d)
    return [(-math.log(s[i + 2][1] / s[i][1]) / math.log(s[i + 2][0] / s[i][0])) if s[i][1] * s[i + 2][1] > 0 else None for i in range(0, len(s) - 2, 2)]

# delta_eps_table.md
L = ['# Delta_eps of the d = 1 long-range Ising model from finite-coupling HT (dens_v1)', '',
     'Consistent full-vacuum window, 16 density-basis states per parity, osc 384, even cutoffs N = 12..40. D_inf: median of '
     'the accepted fits (F1, F2, F3 x N_min 12..24) and half their spread (a model spread, not a confidence interval). '
     'omega: median exponent of the accepted fits. Status words are part of the result (quoted_numbers.json). NRG: bosonic '
     'NRG of the sub-ohmic spin-boson model (NRG folder), for comparison. Written by code/lri_dressed_phi4_hpc_analysis/'
     'public/make_tables_ht1d.py from dens_v1_extrapolation.json.', '',
     '| Ds | eps = 1 - 4 Ds | Delta(N = 40) | dDelta/dlnN at N = 40 | D_inf | omega | accepted fits | status | NRG |',
     '|---|---|---|---|---|---|---|---|---|']
special = {0.05: '0.6220–0.6224 (F1, F2); F3 down to 0.618'}
for d in sorted(X, reverse=True):
    x = X[d]; s40 = dict(zip(x['cuts'], x['values']))[40]; f = x['fit']; n = nrg.get(d)
    if d in special: dinf = special[d]
    elif status[d] == 'no limit' or not f: dinf = '—'
    else: dinf = '%.7f ± %.1e' % (f['D_inf'], f['spread_half']) + (' (one-sided −5e-4)' if status[d] == 'one-sided' else '')
    L.append('| %g | %.3f | %.7f | %+.2e | %s | %s | %s | %s | %s |' % (d, 1 - 4 * d, s40, slopes(d)[-1][1], dinf,
             '%.2f' % f['omega_median'] if f else '—', f['n_fits'] if f else 0, status[d],
             '%.5f ± %.5f' % (n['Delta_E'], n['total_uncertainty']) if n else '—'))
(O / 'delta_eps_table.md').write_text('\n'.join(L) + '\n')

# identity tables
V = collections.defaultdict(dict)
for f in sorted((PKG / 'identities').glob('*.json')):
    r = json.loads(f.read_text()); w = 'raw' if '_none_' in f.name else 'window'
    for op in ('sigma', 'shadow', 'epsilon'):
        l1 = r['descendants'][op].get('level1', {}); V[(r['delta'], r['bath_cut'])][(w, op)] = (l1.get('violation'), l1.get('status'))
def cell(v, tex=False):
    x, st = v
    if x is None: return '---' if tex else '—'
    amb = st != 'ok'
    if tex: return '$%+.4f%s$' % (x, '^a' if amb else '')
    return '%+.4f' % x + ('' if not amb else ' (%s)' % ('amb.' if str(st).startswith('amb') else st))
L = ['# Level-1 descendant violations E(dO) - E(O) - 1 (exactly 0 in the CFT)', '',
     'From the identity records in code/lri_dressed_phi4_hpc_analysis/identities/ (python -m lri_dressed identities on the '
     'prod1-7 records; nz 24 at Ds >= 0.1, 32 at 0.01..0.075, 40 at 0.001). "amb." = ambiguous identification with the free '
     'L_-1. Estimators of the quoted summaries: quoted_numbers.json, rows V1-V4.', '']
for N in (16, 20, 24, 28):
    L += ['## N = %d' % N, '', '| Ds | raw sigma | raw shadow (phi^3) | raw E | window sigma | window shadow | window E |', '|---|---|---|---|---|---|---|']
    for d in sorted({k[0] for k in V}, reverse=True):
        v = V[(d, N)]; L.append('| %g | ' % d + ' | '.join(cell(v[(w, op)]) for w in ('raw', 'window') for op in ('sigma', 'shadow', 'epsilon')) + ' |')
    L.append('')
(O / 'identity_violations.md').write_text('\n'.join(L))
T = ['% Generated by make_tables_ht1d.py: rows of Table tab:d1-ident (N = 28).']
for d in (0.249, 0.2, 0.15, 0.125, 0.1, 0.075, 0.05, 0.025, 0.01):
    v = V[(d, 28)]; T.append('%g & ' % d + ' & '.join(cell(v[(w, op)], True) for w in ('raw', 'window') for op in ('sigma', 'shadow', 'epsilon')) + '\\\\')
(O / 'tab_d1_ident.tex').write_text('\n'.join(T) + '\n')

# held-out and local exponent
cuts = list(H[0.2]['by_cut'])
L = ['# Held-out-cutoff test and local exponent (d = 1, dens_v1)', '',
     'D_inf (median; half-spread x1e-5 in parentheses) from fits on N <= N_cut; * = fails the stability rule. From dens_v1_holdout.json.', '',
     '| Ds | ' + ' | '.join('N <= %s' % c for c in cuts) + ' |', '|---|' + '---|' * len(cuts)]
for d in sorted(H, reverse=True):
    L.append('| %g | ' % d + ' | '.join('%.5f(%d)%s' % (b['D_inf'], round(b['half_spread'] * 1e5), '' if b['stable'] else '*') for b in H[d]['by_cut'].values()) + ' |')
hold = max(abs(p['actual'] - p['median']) for x in H.values() if x['delta'] >= 0.05 for p in x['by_cut']['32']['pred'].values())
L += ['', 'Fits on N <= 32 predict N = 34..40: max |actual - median prediction| = %.2g over Ds >= 0.05.' % hold, '',
      '## Local exponent omega_eff(N) = -dln(dDelta/dlnN)/dlnN, from the slopes on [N-3, N-1] and [N+1, N+3] (labelled by the centre N of the four cutoffs)', '',
      '| Ds | N ~ 15 | 19 | 23 | 27 | 31 | 35 |', '|---|---|---|---|---|---|---|']
T = ['% Generated by make_tables_ht1d.py: rows of Table tab:d1-holdout (local exponent).']
for d in sorted(X, reverse=True):
    o = omega_eff(d)
    L.append('| %g | ' % d + ' | '.join('%.2f' % w if w is not None else 'sign change' for w in o) + ' |')
    if d in (0.249, 0.24, 0.2, 0.15, 0.125, 0.1, 0.075, 0.05):
        T.append('%g & ' % d + ' & '.join('%.2f' % w for w in o) + '\\\\')
    if d == 0.025:
        k = next(i for i, w in enumerate(o) if w is None)
        T.append('%g & ' % d + ' & '.join('%.2f' % w for w in o[:k]) + ' & \\multicolumn{%d}{c}{slope changes sign near $N=22$}\\\\' % (len(o) - k))
(O / 'holdout_and_local_exponent.md').write_text('\n'.join(L) + '\n')
(O / 'tab_d1_omegaeff.tex').write_text('\n'.join(T) + '\n')
# note: rows of Table tab:d1 (HT values through the \\HTq macros of the note; NRG from nrg_reference.json)
byd = collections.defaultdict(dict)
for q in Q.values():
    if q.get('delta') is not None and q['id'][0] in 'TDU' and q['id'] not in ('D12', 'D13', 'D14', 'U00'): byd[q['delta']][q['id'][0]] = q['id']
T = ['% Generated by make_tables_ht1d.py: rows of Table tab:d1 (HT: \\HTq macros from quoted_numbers.json; NRG: nrg_reference.json).']
for d in sorted(X, reverse=True):
    ids = byd[d]; n = nrg[d]
    dinf = '$\\HTq{%s}$' % ids['D'] if 'D' in ids else ''
    if d == 0.05: dinf = '$\\HTq{D10}$, or down to $\\HTq{D11}$'
    nv = '%.6f' % n['Delta_E'] + (('(%d)' % round(n['total_uncertainty'] * 1e6)) if n['total_uncertainty'] else '$^{\\rm nc}$')
    T.append('%g & %g & $\\HTq{%s}$ & %s & %s & %s\\\\' % (d, round(1 - 4 * d, 3), ids['T'], dinf, Q[ids['U']]['quoted'], nv))
(O / 'tab_d1_main.tex').write_text('\n'.join(T) + '\n')
print('wrote', ', '.join(sorted(p.name for p in O.iterdir())))
