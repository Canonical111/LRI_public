#!/usr/bin/env python3
"""Fast tests of the d = 1 resummation package (new tool, 2026-10-14; seconds). Run from code/resum_d1/.

1. The C8(1) switch gives the final value (8059766.723129955, allowance 17000) by default and the previous one on request.
2. The verbatim resummation (update_2026-10-12/sr_endpoint.py, function cb) evaluated afresh at Delta_sigma = 0.05,
   0.1, 0.2 equals the shipped baseline column endpoint_v_K8_L8 of curve_K.csv within 1e-12, and the K = 4 control
   with the previous C8(1) equals the archived 2026-10-07 table inputs/curve.csv (endpoint_v_L8) within 1e-12.
3. The quoted-number rule of ../../verify/rsum_lib.py: parsing and half-up rounding on known cases.
"""
import csv, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import rsum_lib as L

os.environ.pop('LRI_C8_1', None); os.environ.pop('LRI_C8_1_OUT', None)
sys.path.insert(0, str(PKG/'update_2026-10-12'))
import numpy as np
import sr_endpoint as S

T = L.Table('resum_d1 test')
L.verify_snapshot(PKG, T)
fin, prev = S.SW.c8_inputs('final'), S.SW.c8_inputs('previous')
T.check('C8(1) switch', fin['C8'] == '8059766.723129955' and fin['allowance'] == 17000 and prev['allowance'] == 33000,
        '%s / %s' % (fin['C8'], prev['C8']), '8059766.723129955 / 8066723.342964563', 'c8_1_switch.c8_inputs')
xs = [0.05, 0.1, 0.2]
curve = {round(float(r['Delta_sigma']), 7): r for r in
         csv.DictReader((PKG/'update_2026-10-13'/'C8_1_ext'/'pipeline_K8'/'results'/'curve_K.csv').open())}
new = S.cb(np.array(xs), 8)
d8 = max(abs(float(v) - float(curve[x]['endpoint_v_K8_L8'])) for v, x in zip(new, xs))
T.check('CB8, K = 8, recomputed', d8 <= 1e-12, '%.1e' % d8, '<= 1e-12', 'sr_endpoint.cb(x, 8) vs curve_K.csv endpoint_v_K8_L8')
arch = {round(float(r['Delta_sigma']), 7): r for r in csv.DictReader((PKG/'inputs'/'curve.csv').open())}
old = S.cb(np.array(xs), 4, c=S.C_PREVIOUS)
d4 = max(abs(float(v) - float(arch[x]['endpoint_v_L8'])) for v, x in zip(old, xs))
T.check('CB8, K = 4, previous C8, vs archive', d4 <= 1e-12, '%.1e' % d4, '<= 1e-12',
        'sr_endpoint.cb(x, 4, c=C_PREVIOUS) vs inputs/curve.csv endpoint_v_L8 (2026-10-07)')
import json, mpmath as mp
reg = json.loads((PKG.parent.parent/'data'/'inputs'/'INPUTS.json').read_text())
lits = {int(e['id'].split('_')[1].split()[0]): e['used_in']['literal'] for e in reg['entries'] if e['id'].startswith('C^SR_') and 'literal' in e['used_in']}
dmax = max(abs(S.CSR[n] - mp.mpf(lits[n])) for n in lits)
T.check('C^SR_1..7 = registry', len(lits) == 7 and dmax < mp.mpf(10)**-55, mp.nstr(dmax, 3), '< 1e-55',
        'sr_endpoint.CSR (65 digits) vs the literals of data/inputs/INPUTS.json, compared with the SRI folder by check-inputs')
cases = [(0.006246637286122374, '6.2466\\times10^{-3}', True), (0.00467, '4.7\\times10^{-3}', True),
         (0.00475, '4.7\\times10^{-3}', False), (0.48281, '0.4828', True), (0.0065, '0.006', False)]
ok = all(L.matches([v], t)[0] == want for v, t, want in cases)
T.check('rounding rule', ok, '%d cases' % len(cases), 'all as expected', 'rsum_lib.matches: half-up to the written digits')
sys.exit(T.report(PKG/'.work'/'test_d1.txt'))
