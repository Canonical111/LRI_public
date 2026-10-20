#!/usr/bin/env python3
"""Bounded PSLQ test (basis without the duplication-redundant psi1((1+q)/2)) (negative-result probe): is Z_d / Q_d a rational combination of weight-<=2 polygamma constants
at q = d/4, as at d = 1 (Z/Q = 2pi^2/3 + 8G) and d = 2 (Z/Q = 4G)?  Uses the 90-digit jets values (results/zj90.json),
run at 70 digits (well below the ~80-digit accuracy of the generic-d values)."""
import json
import mpmath as mp

mp.mp.dps = 70
res = json.load(open('results/zj90.json'))['results']
for dstr in ('1.5', '2.5', '1.25'):
    d = mp.mpf(dstr)
    q = d / 4
    Z = mp.re(mp.mpmathify(res[dstr]['Z']))
    Q = mp.re(mp.mpmathify(res[dstr]['W'])) / 3
    p1 = lambda x: mp.psi(1, x)
    names = ['Z/Q', '1', 'pi^2', 'psi1(q)', 'psi1(2q)', 'psi1(q/2)', 'psi1(1-q/2)', 'psi1(3q/2)', 'psi1(3q)',
             'psi(q)^2', 'psi(q)psi(2q)', 'psi(2q)^2', 'pi psi(q)', 'pi psi(2q)', 'pi^2/sin^2(pi q)', 'pi cot(pi q)']
    vals = [Z / Q, 1, mp.pi ** 2, p1(q), p1(2 * q), p1(q / 2), p1(1 - q / 2), p1(3 * q / 2), p1(3 * q),
            mp.psi(0, q) ** 2, mp.psi(0, q) * mp.psi(0, 2 * q), mp.psi(0, 2 * q) ** 2, mp.pi * mp.psi(0, q),
            mp.pi * mp.psi(0, 2 * q), mp.pi ** 2 / mp.sin(mp.pi * q) ** 2, mp.pi / mp.tan(mp.pi * q)]
    rel = mp.pslq(vals, maxcoeff=10 ** 4, maxsteps=10 ** 6)
    print('d=%s  basis size %d  relation: %s' % (dstr, len(vals), rel))
    # also the d = 1, 2 pattern with the residue data: R''/R against the same basis
    Rj = [mp.re(mp.mpmathify(x)) for x in res[dstr]['R']]
    vals2 = [Rj[2] / Rj[0]] + vals[1:]
    print('      R\'\'/R:  relation: %s' % mp.pslq(vals2, maxcoeff=10 ** 4, maxsteps=10 ** 6))
