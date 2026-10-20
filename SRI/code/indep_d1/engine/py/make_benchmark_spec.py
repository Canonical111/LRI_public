#!/usr/bin/env python3
"""Cost/convergence benchmark spec for every production group (specs/production_D4.json):
sample of sectors (stride) at two lattice sizes, newest engine.  -> specs/pilot4_bench.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
prod = json.load(open(os.path.join(HERE, '..', 'specs', 'production_D4.json')))
moms = []
for g in prod:
    if g['dim'] <= 2:
        continue
    stride = max(1, g['sectors'] // 60)
    Ns = [16001, 64007] if g['dim'] >= 5 else [16001]
    for N in Ns:
        m = {'name': f"{g['name']}_N{N}", 'kind': g['kind'], 'n': g['n'], 'nv': g['nv'], 'nd': g['nd'], 'ne': g['ne'],
             'powers': g['powers'], 'jmin': g['jmin'], 'N': N, 'sectors': [0, 10 ** 6]}
        if stride > 1:
            m['extra'] = [f'sectorstride {stride} {stride // 2}']
        moms.append(m)
json.dump({'defaults': {'shifts': 8, 'transform': 3, 'prec': 'auto', 'chunks': 1}, 'moments': moms},
          open(os.path.join(HERE, '..', 'specs', 'pilot4_bench.json'), 'w'), indent=1)
print(len(moms), 'benchmark entries')
