#!/usr/bin/env python3
"""Compare Z_d (and W, W') from the two-node formula (jets / Cauchy engines) with the reference values:
d=1, 2 closed forms (note gs:d1Dictionary, gs:Z2exact), d=3 (LRI_C5_d3/wf_Z3/Z3_values.json, 250 digits),
non-integer d: C63d's independent spectral values (references/reference_values.json).
usage: compare_refs.py results/zj60.json [results/zc60.json ...]"""
import json
import sys
import os
import mpmath as mp

mp.mp.dps = 120
HERE = os.path.dirname(os.path.abspath(__file__))


def references():
    G = mp.catalan
    Q1 = mp.gamma(mp.mpf(1) / 4) ** 4 / mp.pi
    Q2 = mp.gamma(mp.mpf(1) / 4) ** 8 / (24 * mp.pi ** 4)
    refs = {'1': dict(Z=Q1 * (2 * mp.pi ** 2 / 3 + 8 * G), W=3 * Q1, src='closed form Q1(2pi^2/3+8G)', digits=80),
            '2': dict(Z=4 * G * Q2, W=3 * Q2, src='closed form 4G Q2', digits=80)}
    z3 = json.load(open(os.path.join(HERE, '..', '..', 'LRI_C5_d3', 'wf_Z3', 'Z3_values.json')))['values']
    refs['3'] = dict(Z=mp.mpf(z3['Z3']), W=3 * mp.mpf(z3['Q3']), src='C63d wf_Z3 (250 digits)', digits=80)
    rv = json.load(open(os.path.join(HERE, '..', 'references', 'reference_values.json')))['values']
    for k, v in rv.items():
        d = k.split('=')[1]
        refs[d] = dict(Z=mp.mpf(v['Z']['value']), W=mp.mpf(v['threeQ']['value']),
                       src='C63d spectral (%d digits)' % v['Z']['digits'], digits=v['Z']['digits'],
                       Wdigits=v['threeQ']['digits'])
    sp = os.path.join(HERE, 'spectral_ref', 'spec_refs.json')
    if os.path.exists(sp):
        for d, v in json.load(open(sp)).items():
            refs[d] = dict(Z=mp.mpf(v['Z']), W=mp.mpf(v['threeQ']), digits=38,
                           src='new spectral run, C63d code hp_general_d.py, dps %s, M %s' % (v['dps'], v['M']))
    return refs


def main():
    refs = references()
    summary = {}
    for fn in sys.argv[1:]:
        res = json.load(open(fn))
        print('== %s  (engine %s, dps %s)' % (fn, res.get('engine'), res.get('dps')))
        for d, r in res['results'].items():
            ref = refs.get(d)
            Z = mp.re(mp.mpmathify(r['Z']))
            W = mp.re(mp.mpmathify(r['W']))
            dW = abs(mp.mpmathify(r['dW']))
            if ref is None:
                print('d=%-5s Z=%s  (no reference)' % (d, mp.nstr(Z, 40)))
                continue
            eZ = abs(Z - ref['Z']) / abs(ref['Z'])
            eW = abs(W - ref['W']) / abs(ref['W'])
            dig = min(ref['digits'], int(-mp.log10(eZ))) if eZ > 0 else ref['digits']
            print('d=%-5s Z=%s  relerr(Z)=%s  relerr(3Q)=%s  |dW/db|=%s  [%s]' % (
                d, mp.nstr(Z, 45), mp.nstr(eZ, 3), mp.nstr(eW, 3), mp.nstr(dW, 3), ref['src']))
            summary.setdefault(d, {})[os.path.basename(fn)] = dict(
                Z=mp.nstr(Z, 60), relerr_Z=mp.nstr(eZ, 3), relerr_3Q=mp.nstr(eW, 3), dWdb=mp.nstr(dW, 3),
                reference=ref['src'], Z_reference=mp.nstr(ref['Z'], 60))
    if os.environ.get('SUMMARY'):
        json.dump(summary, open(os.environ['SUMMARY'], 'w'), indent=1)


if __name__ == '__main__':
    main()
