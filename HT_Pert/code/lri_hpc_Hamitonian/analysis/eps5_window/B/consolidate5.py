"""Consolidated finite-cutoff reference numbers (implementation B, eps^5) for exact comparison."""
import json, glob, numpy as np
out = {'full_basis': {}, 'vacuum_windows': {}, 'dC5_table': json.load(open('dC5_table.json'))}
for f in sorted(glob.glob('full5_c*.json'), key=lambda x: int(x.split('_c')[1][:-5])):
    o = json.load(open(f)); c = o['cut4']
    rec = {'Lambda': o['Lambda'], 'dim': o['dim'], 'Pmax': o.get('Pmax', 11)}
    for v, d in o['variants'].items():
        rec[v] = {k: d[k] for k in ('r', 'g', 'C', 'spacing_d1', 'spacing_d2', 'spacing_d3') if k in d}
        if 'Xrow' in d: rec[v]['Xrow'] = d['Xrow']
    out['full_basis'][c] = rec
for f in glob.glob('vacwin_L*.json'):
    w = json.load(open(f)); L = w['L']; E = w['E']; j = 2 * L
    c = lambda jj, t='conn': np.array(E[str(jj)][t])
    out['vacuum_windows'][L] = dict(A=(c(j) - c(j - 1)).tolist(), B=(c(j) - c(j - 2)).tolist(), D3=(c(j) - c(j - 3)).tolist(),
                                    A_raw=(c(j, 'raw') - c(j - 1, 'raw')).tolist(), B_raw=(c(j, 'raw') - c(j - 2, 'raw')).tolist(),
                                    S2g_window_D3=E[str(j)]['S2g'] - E[str(j - 3)]['S2g'],
                                    note='E_c(L)-E_c(L-1/2), -E_c(L-1), -E_c(L-3/2); eps^5 with g4=0 (add 2*g4*S2g_window for D3)')
json.dump(out, open('B_eps5_finite_values.json', 'w'), indent=1)
print('written', len(out['full_basis']), 'full-basis cutoffs,', len(out['vacuum_windows']), 'vacuum windows,', len(out['dC5_table']), 'dC5 rows')
