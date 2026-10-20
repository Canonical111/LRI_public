#!/usr/bin/env python3
"""Build the raw-moment production list for C6/C7 (D4 order) from the framework agent's minimal requirement
list (../specs/framework_required_inputs_D4.json, derivative convention, 'E' = endpoint source EE).

Output: ../specs/production_D4.json with one entry per (moment, derivative): kind, n, nv, nd, ne, geometry,
eps powers, jmin (lowest log power needed at each power), integration dimension, number of sectors,
and the largest C7 / C6 sensitivity of its coefficients (from ../specs/framework_sensitivities_C6_C7_D4.json).
"""
import json, os, re, sys
from math import factorial
HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, '..', 'specs')
req = json.load(open(os.path.join(SPEC, 'framework_required_inputs_D4.json')))['flat_names']
sens = json.load(open(os.path.join(SPEC, 'framework_sensitivities_C6_C7_D4.json')))['sens']

groups = {}
for name in req:
    m = re.match(r'([AZQ])(\d+)(?:_([vdE]+))?\[eps\^(-?\d+) l\^(\d+)\]', name)
    kind, n, der, p, l = m.group(1), int(m.group(2)), m.group(3) or '', int(m.group(4)), int(m.group(5))
    key = f'{kind}{n}_{der or "base"}'
    g = groups.setdefault(key, {'kind': kind, 'n': n, 'nv': der.count('v'), 'nd': der.count('d'), 'ne': der.count('E'),
                                'coeffs': {}, 'sens_C7': 0.0, 'sens_C6': 0.0})
    g['coeffs'].setdefault(p, []).append(l)
    g['sens_C7'] = max(g['sens_C7'], float(sens['C7'].get(name, 0)))
    g['sens_C6'] = max(g['sens_C6'], float(sens['C6'].get(name, 0)))

out = []
for key, g in sorted(groups.items(), key=lambda kv: (kv[1]['n'], kv[0])):
    if g['n'] <= 2:
        continue  # two-kink sector is exact in the framework
    geom = 'full' if g['ne'] else 'angular'
    M = g['n'] + 1 if geom == 'full' else g['n'] - 1
    d = M - 1
    powers = sorted(g['coeffs'])
    jmin = {str(p): min(g['coeffs'][p]) for p in powers}
    out.append({'name': key, 'kind': g['kind'], 'n': g['n'], 'nv': g['nv'], 'nd': g['nd'], 'ne': g['ne'], 'geom': geom,
                'dim': d, 'sectors': factorial(M) // 2, 'powers': powers, 'jmin': jmin,
                'coeffs': {str(p): sorted(v) for p, v in g['coeffs'].items()},
                'sens_C7': g['sens_C7'], 'sens_C6': g['sens_C6']})
json.dump(out, open(os.path.join(SPEC, 'production_D4.json'), 'w'), indent=1)
print(f'{len(out)} moment/derivative groups, {sum(sum(len(v) for v in o["coeffs"].values()) for o in out)} coefficients')
for o in out:
    print(f"{o['name']:10s} {o['geom']:7s} d={o['dim']} sec={o['sectors']:5d} powers={o['powers']} jmin={o['jmin']} "
          f"sens(C7)={o['sens_C7']:.3g}")
