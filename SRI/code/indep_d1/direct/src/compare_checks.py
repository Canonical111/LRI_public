#!/usr/bin/env python3
"""Internal validation of the direct Gauss table.

  * exact closed forms: Z2 = 1/eps + l - 1, Q2 = -l - 1 + eps, A3(eps) (dilog form)
  * Cauchy-contour Taylor coefficients of the unexpanded two-kink kernels (Z2, Q2, EZ2, EQ2)
  * randomized QMC (independent numpy code, different domain maps): z-scores
  * Gauss form 0 vs form 1 (cross-parametrization)
Output: results/internal_checks.json and a printed summary.
"""
import json
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')


def name_of(n, kind, E, a, b):
    suf = 'v' * a + 'd' * b
    return '%s%s%d_%s' % ('E' if E else '', kind, n, suf if suf else 'base')


def main():
    tab = json.load(open(os.path.join(RES, 'direct_table.json')))
    out = {}
    # exact references
    ex = []
    p = os.path.join(RES, 'exact_refs.json')
    if os.path.exists(p):
        refs = json.load(open(p))
        for el, d in refs['closed_forms'].items():
            el2 = '%.6g' % float(el)
            for nm, v in d.items():
                e = tab.get(el2, {}).get(nm)
                if e:
                    x = float(v)
                    ex.append(dict(kind='closed_form', eps=el2, name=nm, exact=v, ours=e['value'],
                                   rel=(e['value'] - x) / abs(x), our_err=e['err']))
        for el, dd in refs['cauchy_two_kink'].items():
            el2 = '%.6g' % float(el)
            for mom, coefs in dd.items():
                for key, v in coefs.items():
                    a, b = map(int, key.split(','))
                    nm = '%s_%s' % (mom, ('v' * a + 'd' * b) or 'base')
                    e = tab.get(el2, {}).get(nm)
                    if e:
                        x = float(v) * math.factorial(a) * math.factorial(b)
                        ex.append(dict(kind='cauchy', eps=el2, name=nm, exact=x, ours=e['value'],
                                       rel=(e['value'] - x) / abs(x), our_err=e['err']))
    out['exact'] = ex
    # QMC
    qm = []
    p = os.path.join(RES, 'qmc.jsonl')
    if os.path.exists(p):
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            el = '%.6g' % r['eps']
            gmap = 'seq' if 'seq' in r['method'] else 'box'
            for key, (mean, se) in r['coef'].items():
                a, b = map(int, key.split(','))
                fac = math.factorial(a) * math.factorial(b)
                nm = name_of(r['n'], r['kind'], r['E'], a, b)
                e = tab.get(el, {}).get(nm)
                if not e:
                    continue
                qv, qse = mean * fac, se * fac
                z = (qv - e['value']) / qse if qse > 0 else float('nan')
                qm.append(dict(eps=el, name=nm, map=gmap, qmc=qv, qmc_se=qse, gauss=e['value'], z=z,
                               qmc_rel_se=qse / abs(e['value'])))
    out['qmc'] = qm
    cf = json.load(open(os.path.join(RES, 'crossform_check.json'))) if os.path.exists(os.path.join(RES, 'crossform_check.json')) else []
    out['crossform'] = cf
    json.dump(out, open(os.path.join(RES, 'internal_checks.json'), 'w'), indent=1)
    # summary
    if ex:
        m = max(ex, key=lambda d: abs(d['rel']))
        print('exact/Cauchy comparisons: %d, max |rel diff| = %.2e (%s eps=%s)' % (len(ex), abs(m['rel']), m['name'], m['eps']))
    if qm:
        zs = [abs(d['z']) for d in qm if d['z'] == d['z']]
        print('QMC comparisons: %d, max |z| = %.2f, rms z = %.2f, #|z|>3: %d' % (
            len(zs), max(zs), math.sqrt(sum(z * z for z in zs) / len(zs)), sum(1 for z in zs if z > 3)))
        bym = defaultdict(list)
        for d in qm:
            bym[d['map']].append(d['qmc_rel_se'])
        for k, v in bym.items():
            v.sort()
            print('   map %s: median relative QMC s.e. %.1e' % (k, v[len(v) // 2]))
    if cf:
        m = max(cf, key=lambda d: abs(d['rel'] or 0))
        print('form0 vs form1: %d, max |rel| = %.2e (%s eps=%s)' % (len(cf), abs(m['rel']), m['name'], m['eps']))


if __name__ == '__main__':
    main()
