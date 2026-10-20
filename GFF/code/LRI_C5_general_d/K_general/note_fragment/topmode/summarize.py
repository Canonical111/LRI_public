#!/usr/bin/env python3
"""Regenerate the numerical tables of PROOF.md from results/*.json (tag topmode).  Writes results/tables.md."""
import json, glob, os
import mpmath as mp

mp.mp.dps = 110
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'results')
KG = os.path.dirname(os.path.dirname(HERE))          # .../K_general
out = []

# ---------------------------------------------------------------- per-spin independent code
out.append('### Table 1. Independent per-spin code (perspin_topmode.py, Lmax = 200, dps 40)\n')
out.append('| case | kernel | per-factor balance sigma+alpha_i+beta_i+g_i-d\'/2 | max_l abs(d_l c_-top^(l)), abs(d_l c_+top^(l)) | spin-summed abs(c_-top), abs(c_+top) | ratio to max abs(c_k), abs(k)<top |')
out.append('|---|---|---|---|---|---|')
order = ['R1', 'R2', 'R3', 'R4', 'R5', 'G1', 'G2', 'C1', 'C2', 'C3']
for case in order:
    r = json.load(open(os.path.join(R, 'perspin_%s.json' % case)))
    top = max(int(k) for k in r['spin_summed_top'])
    dl = [mp.mpmathify(x) for x in r['d_l']]
    pm = max(abs(dl[l] * mp.mpmathify(r['perspin_top_all'][str(-top)][l])) for l in range(len(dl)))
    pp = max(abs(dl[l] * mp.mpmathify(r['perspin_top_all'][str(top)][l])) for l in range(len(dl)))
    bal = ', '.join('0' if abs(mp.mpmathify(b)) < 1e-30 else mp.nstr(mp.mpmathify(b), 3) for b in r['per_factor_balance_vs_dmult'])
    st = r['spin_summed_top']
    out.append('| %s | %s | %s | %s, %s | %s, %s | %s, %s |' % (
        case, r['label'], bal, mp.nstr(pm, 3), mp.nstr(pp, 3), st[str(-top)]['abs'], st[str(top)]['abs'],
        r['relative_top'][str(-top)], r['relative_top'][str(top)]))
out.append('')
out.append('Fit spreads of the spin-summed top modes (six extrapolation variants): ' + '; '.join(
    '%s %s/%s' % (c, json.load(open(os.path.join(R, 'perspin_%s.json' % c)))['spin_summed_top'][k1]['fit_spread'],
                  json.load(open(os.path.join(R, 'perspin_%s.json' % c)))['spin_summed_top'][k2]['fit_spread'])
    for c, k1, k2 in [(c, '-3', '3') if c == 'G2' else (c, '-2', '2') for c in order]) + '.')
out.append('Per-spin validation: tail consistency (recurrence vs reflected Gamma form) <= %s; per-spin finite-mode reconstruction <= %s.' % (
    max(mp.mpmathify(json.load(open(os.path.join(R, 'perspin_%s.json' % c)))['tail_consistency_max']) for c in order),
    mp.nstr(max(max(mp.mpmathify(x) for x in json.load(open(os.path.join(R, 'perspin_%s.json' % c)))['perspin_finite_mode_check']) for c in order), 3)))
out.append('')

# ---------------------------------------------------------------- Horn-block code
out.append('### Table 2. Horn-block code (K_general/R_part/rblocks.py unchanged), five nodes t0 + j/5, dps 40\n')
out.append('| d | tau | region | ratio abs(c_-2), abs(c_+2) to max abs(c_k) at (K,M)=(14,160) | same at (20,240) | change of c_0 between settings | 3-node vs 5-node rel. diff (20,240) |')
out.append('|---|---|---|---|---|---|---|')
files = sorted(glob.glob(os.path.join(R, 'modes_*.json')), key=lambda s: (float(os.path.basename(s).split('_d')[1].split('_t')[0]), s))
for f in files:
    r = json.load(open(f))
    a, b = r['settings']['K14_M160'], r['settings']['K20_M240']
    reg = r['region']
    regs = ('convergence region' if reg['in_convergence_region'] else 'continued') + (', residue strip' if reg['in_residue_strip'] else '')
    c0 = abs(mp.mpmathify(r['settings']['K20_M240']['c']['0']))
    out.append('| %s | %s | %s | %s, %s | %s, %s | %s | %s |' % (
        r['d'], r['tau'].replace('j', 'i'), regs, a['rel_top']['-2'], a['rel_top']['2'], b['rel_top']['-2'], b['rel_top']['2'],
        mp.nstr(mp.mpmathify(r['setting_change']['0']) / c0, 2), b['rel_diff_3_vs_5']))
out.append('')

# ---------------------------------------------------------------- cross-check of the two codes (lower modes)
out.append('### Table 3. Cross-check of the two codes: lower modes, per-spin extrapolation vs Horn blocks (20,240) / Gamma(2q)^2\n')
out.append('| case | d | tau | rel. diff c_-1 | rel. diff c_0 | rel. diff c_1 |')
out.append('|---|---|---|---|---|---|')
pairs = {'R1': ('1.7', '0.55+0.3j'), 'R2': ('3.3', '1.6-0.4j'), 'R3': ('0.5', '0.9+0.2j'), 'R4': ('2.6', '2.0+0.5j'), 'R5': ('1.25', '0.7')}
for case, (d, t) in pairs.items():
    p = json.load(open(os.path.join(R, 'perspin_%s.json' % case)))
    m = json.load(open(os.path.join(R, 'modes_d%s_t%s.json' % (d, t))))['settings']['K20_M240']['c']
    g2 = mp.gamma(mp.mpf(d) / 2) ** 2
    row = []
    for k in ('-1', '0', '1'):
        x = mp.mpmathify(p['spin_summed_all_modes'][k]['value']); y = mp.mpmathify(m[k]) / g2
        row.append(mp.nstr(abs(x - y) / abs(y), 2))
    out.append('| %s | %s | %s | %s |' % (case, d, t.replace('j', 'i'), ' | '.join(row)))
out.append('')

# ---------------------------------------------------------------- K_d with three nodes
out.append('### Table 4. K_d from the three-node rule vs the 100-digit MB values and the five-node production run (same settings)\n')
out.append('| d | settings (r, N, K, M, dps) | K_d, three nodes (first 40 digits) | rel. dev. from MB, 3 nodes | rel. dev. from MB, 5 nodes | rel. diff 3 vs 5 | [tau^0]F | [tau^1]F - (3/2)psi_2(q) |')
out.append('|---|---|---|---|---|---|---|---|')
mb = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']
for d in ('0.8', '1.25', '2.75'):
    r3 = json.load(open(os.path.join(R, 'kjet3_B_d%s.json' % d)))
    r5 = json.load(open(os.path.join(KG, 'R_part', 'prod', 'prod_B_d%s.json' % d)))
    K3, K5, KM = mp.mpf(r3['K_d']), mp.mpf(r5['K_d']), mp.mpf(mb[d]['K'])
    assert (r3['r'], r3['N'], r3['K'], r3['M'], r3['dps']) == (r5['r'], r5['N'], r5['K'], r5['M'], r5['dps'])
    out.append('| %s | %s, %s, %s, %s, %s | %s | %s | %s | %s | %s | %s |' % (
        d, r3['r'], r3['N'], r3['K'], r3['M'], r3['dps'], r3['K_d'][:41], mp.nstr((K3 - KM) / KM, 2), mp.nstr((K5 - KM) / KM, 2),
        mp.nstr((K3 - K5) / KM, 2), r3['F0'], r3['tE2_minus_1p5psi2']))
out.append('')
txt = '\n'.join(out)
open(os.path.join(R, 'tables.md'), 'w').write(txt + '\n')
print(txt)
