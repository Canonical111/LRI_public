import json, mpmath as mp
from pieces import taylor, KEYS
def load(fn, extra=10):
    d = json.load(open(fn))
    mp.mp.dps = d['dps'] + extra
    vals = {int(k): [mp.mpmathify(x) for x in v] for k, v in d['values'].items()}
    T = taylor(vals, d['M'], mp.mpf(d['rho']))
    cen = dict(zip(KEYS, [mp.mpmathify(x).real for x in d['centre']]))
    V = {k: T[k][0].real for k in KEYS}
    D = {k: T[k][1].real for k in KEYS}
    D2 = {k: T[k][2].real for k in KEYS}
    return d, V, D, D2, cen
