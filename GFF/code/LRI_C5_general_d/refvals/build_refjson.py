#!/usr/bin/env python3
"""Assemble LRI_C5_general_d/references/reference_values.json from the available runs.
Sources per d: first production (ref_b/ref_t, dps50 L48 K52 M64), analytic-nu-tail reruns (refn_*), second setting (ref2_*, dps56 L60 K60 M72, nu-tail on).
'digits' = number of agreeing significant digits between two independent settings when both exist; otherwise an internal estimate."""
import json, os
import mpmath as mp
from combine_general import combine
mp.mp.dps = 70
OUT = '<PROJECT>/LRI_C5_general_d/references/reference_values.json'
D = ['0.8', '1.25', '1.5', '2.5', '2.75']
def agree(x, y):
    x, y = mp.re(x), mp.re(y)
    if x == y: return 60
    return int(max(0, -mp.log10(abs(x - y) / abs(x))))
def pick(d, part):
    c = []
    for pre in ('ref2_', 'refn_', 'ref_'):
        f = f'{pre}{part}_{d}.json'
        if os.path.exists(f): c.append(f)
    return c
res = {'status': None, 'producer': 'session C63d, LRI_C5_general_d/refvals/hp_general_d.py (spectral trace; finite spins by quadrature with an analytic large-nu tail; '
       'spin tail by Stirling + generic-d multiplicity expansion + Euler-Maclaurin Hurwitz zeta; b- and tau-derivatives by Cauchy circles)',
       'conventions': 'W_r(d;b) = <t_{l,b}^r>_d (gs:balancedWheel, gs:spectrum); P4 = W4(d;d/2); threeQ = W3(d;d/2) = 3 Q_d; L = dW4/db; Z = (1/9) d2W3/db2 at b=d/2 '
       '(gs:wheelJets); dW3db = dW3/db at b=d/2 (should vanish); K per gs:Kspectral (= -AU/4 + (F3 + c* F2)/4, F(tau) = <t^2(R_tau - S_tau)>_d); offdiag: W3, W4 at real b = d/2 +- rho_off',
       'validation': 'd=3: P4, 3Q, L, Z, K reproduce the 43+-digit values (LRI_C5_d3) to 22-24 digits at dps 25; d=2: L2 = -2log2 P4(2), K2 = 32G^2-28zeta3 log2 to 22-23 digits',
       'values': {}}
incomplete = []
for d in D:
    bs, ts = pick(d, 'b'), pick(d, 't')
    entry = {}
    rb = [combine(f, ts[0] if ts else f) for f in bs] if bs else []
    rt = [combine(bs[0], f) for f in ts] if (ts and bs) else []
    rt = [r for r in rt if abs(mp.re(r[0]['F0'])) < mp.mpf('1e-30')]      # drop runs whose F(0) = 0 check fails (pre-nu-tail small-d runs)
    for key in ('P4', 'threeQ', 'L', 'Z', 'dW3db'):
        if not rb: continue
        v = rb[0][0][key]
        dig = agree(rb[0][0][key], rb[1][0][key]) if len(rb) > 1 else None
        entry[key] = {'value': mp.nstr(mp.re(v), 50), 'digits': dig if dig is not None else 'internal estimate >= 30 (single setting)',
                      'method': 'b-circle ' + ', '.join(bs)}
    if rt:
        v = rt[0][0]['K']; dig = agree(rt[0][0]['K'], rt[1][0]['K']) if len(rt) > 1 else None
        f0 = mp.re(rt[0][0]['F0'])
        entry['K'] = {'value': mp.nstr(mp.re(v), 50), 'digits': dig if dig is not None else 'single setting; F0 check = %s (must vanish)' % mp.nstr(f0, 3),
                      'method': 'tau-circle ' + ', '.join(ts)}
        if abs(f0) > mp.mpf('1e-30'): entry['K']['WARNING'] = 'F0 does not vanish: K not reliable from %s' % ts[0]
    if rb:
        entry['offdiag'] = [{'b': o[2][:20], 'W3': o[0].split(' ')[0].strip('('), 'W4': o[1].split(' ')[0].strip('(')} for o in rb[0][1].values()]
    if not entry or 'K' not in entry or 'WARNING' in entry.get('K', {}): incomplete.append(d)
    res['values']['d=' + d] = entry
res['status'] = 'COMPLETE' if not incomplete else 'INTERIM: still pending or flagged at d = ' + ', '.join(incomplete)
json.dump(res, open(OUT, 'w'), indent=1)
print(res['status'])
for d, e in res['values'].items():
    print(d, {k: (v['value'][:22], v['digits']) for k, v in e.items() if isinstance(v, dict)})
