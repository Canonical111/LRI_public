#!/usr/bin/env python3
"""Compare this probe's modes with numbers produced by OTHER codes (read from their JSON outputs only; no code imported):
  - C63d per-spin code (K_general/note_fragment/topmode/results/perspin_{R5,G2,C1}.json), ~1e-14 accuracy;
  - the 50-digit wheel probe review/topmode-numeric (results/probe_mainG1.json, config A1r3)."""
import json
import os

import mpmath as mp

mp.mp.dps = 60
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '..', '..'))


def mine(name):
    d = json.load(open(os.path.join(here, 'results', name + '.json')))
    return {int(k): mp.mpmathify(v) for k, v in d['modes'].items()}


out = {}
for my, theirs in [('X_R5', 'R5'), ('X_G2', 'G2'), ('X_C1', 'C1')]:
    try:
        m = mine(my)
    except FileNotFoundError:
        continue
    t = json.load(open(os.path.join(root, 'K_general', 'note_fragment', 'topmode', 'results', 'perspin_%s.json' % theirs)))
    # their values are printed with ~15 significant digits (double precision is enough for a 1e-14 comparison)
    tm = {int(k): mp.mpmathify(complex(v['value'].replace(' ', ''))) for k, v in t['spin_summed_all_modes'].items()}
    sc = max(abs(v) for v in m.values())
    dev = {k: mp.nstr(abs(m[k] - tm[k]) / sc, 3) for k in tm}
    out[my] = dict(source='C63d perspin_%s.json' % theirs, rel_dev_by_mode=dev,
                   mine={k: mp.nstr(m[k], 15) for k in tm}, theirs={k: mp.nstr(tm[k], 15) for k in tm})
try:
    m = mine('X_TNA1')
    t = json.load(open(os.path.join(root, 'review', 'topmode-numeric', 'results', 'probe_mainG1.json')))['configs']['A1r3']
    tm = {int(k): mp.mpc(mp.mpf(v[0]), mp.mpf(v[1])) for k, v in t['modes'].items()}
    sc = max(abs(v) for v in m.values())
    dev = {k: mp.nstr(abs(m[k] - tm[k]) / sc, 3) for k in tm if k in m}
    out['X_TNA1'] = dict(source='review/topmode-numeric probe_mainG1.json A1r3 (d=1.3, b=0.6+0.1i, r=3)', rel_dev_by_mode=dev,
                         mine={k: mp.nstr(m[k], 20) for k in m}, theirs={k: mp.nstr(tm[k], 20) for k in tm})
except FileNotFoundError:
    pass
print(json.dumps(out, indent=1))
with open(os.path.join(here, 'results', 'external_comparison.json'), 'w') as f:
    json.dump(out, f, indent=1)
