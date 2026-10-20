#!/usr/bin/env python3
"""Dump the gdr sample data (X_T, X_0, X_1/2 and b-derivatives; T3, M3, c0hat and two b-derivatives) at b = d/2,
using the supporting codes L/L_general.py and Z/Z_general.py UNCHANGED (read-only import).
usage: python3 dump_samples.py ROOT DPS OUT.json
ROOT = directory containing L/, Z/ (LRI_C5_general_d or the cluster copy)."""
import json, sys, time
from multiprocessing import Pool
import mpmath as mp

ROOT, DPS, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
sys.path.insert(0, ROOT + '/L')
sys.path.insert(0, ROOT + '/Z')
DIMS = ['1', '2', '3', '4/5', '5/4', '3/2', '5/2', '11/4']


def work(dstr):
    from L_general import LP4
    import Z_general as ZG
    from jet import val, der
    mp.mp.dps = DPS
    t0 = time.time()
    with mp.workdps(DPS + 15):
        P4, L, sm = LP4(dstr, DPS + 15, full=True)
        zr = ZG.Z(dstr, DPS + 15, full=True)
        out = dict(P4_code=mp.re(P4), L_code=mp.re(L),
                   XT=mp.re(val(sm['Xt'])), X0=mp.re(val(sm['X0'])), Xh=mp.re(val(sm['Xh'])),
                   dXT=mp.re(der(sm['Xt'])), dX0=mp.re(der(sm['X0'])), dXh=mp.re(der(sm['Xh'])),
                   Q_code=mp.re(zr['Q']), Z_code=mp.re(zr['Z']), dW3_code=mp.re(zr['dW']),
                   T3=[mp.re(v) for v in zr['R']], M3=[mp.re(v) for v in zr['Mh']],
                   c0=[mp.re(v) for v in zr['c0hat']], engine=zr['engine'])
    out['sec'] = time.time() - t0
    ser = {}
    for k, v in out.items():
        if isinstance(v, list):
            ser[k] = [mp.nstr(x, DPS + 5) for x in v]
        elif isinstance(v, str):
            ser[k] = v
        else:
            ser[k] = mp.nstr(v, DPS + 5)
    return dstr, ser


if __name__ == '__main__':
    with Pool(len(DIMS)) as p:
        res = dict(p.map(work, DIMS))
    json.dump(dict(dps=DPS, root=ROOT, values=res), open(OUT, 'w'), indent=1)
    print('done', json.dumps({k: v['sec'] for k, v in res.items()}))
