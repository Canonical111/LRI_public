#!/usr/bin/env python3
"""Assembly check of the reduced C5(d) formula (general_d.tex, gdr:C5reduced) at d = 1, 2, 3 and five non-integer d.

Computes, with the five-Horn (L/L_general.py) and two-node (Z/Z_general.py) codes at b = d/2:
  * P4, L_d and the compact sample form of L_d:
      L_d = -(1/S^8)[(1+C)^2(4+9C+8C^2) X0 + (1-C)^2(4-9C+8C^2) Xh - 2(1+6C^2) XT] + 2/(pi S^7) Dfr,
      Dfr = (1+C)^2(1+2C) X0' - (1-C)^2(1-2C) Xh' - 2C XT'     (frozen-weight derivative),
  * Q_d, Z_d (zero-mode form) and the block
      B(d) = 384 A P4 - 576 L - 1728 Q^2 + (720 A^2 + 1008 Rpsi) Q + 7152 Z
    against the same block from reference values (closed forms at d = 1, 2; C63d at d = 3 and non-integer d),
  * the reduced block in sample form (kappa_0 X0 + kappa_h Xh + kappa_T XT - 1152/(pi S^7) Dfr + ...),
  * full C5(1) with P5(1) (30 digits, note) and K_1 (eq:KLpsiReflected).
Usage: python3 c5_assembly.py dps
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
sys.path.insert(0, os.path.join(_HERE, '..', 'Z'))

DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DIMS = ['1', '2', '3', '4/5', '5/4', '3/2', '5/2', '11/4']
REFJ = os.path.join(_HERE, '..', 'references', 'reference_values.json')
C63D_L = os.path.join(_HERE, 'L3_final_values.json')


def parse(dstr):
    if '/' in dstr:
        a, b = dstr.split('/')
        return mp.mpf(a) / mp.mpf(b)
    return mp.mpf(dstr)


def compute(dstr):
    from L_general import LP4
    import Z_general as ZG
    from jet import val, der
    mp.mp.dps = DPS
    t0 = time.time()
    with mp.workdps(DPS + 15):
        P4, L, sm = LP4(dstr, DPS + 15, full=True)
        Xt, X0, Xh = sm['Xt'], sm['X0'], sm['Xh']
        zr = ZG.Z(dstr, DPS + 15, full=True)
        out = dict(P4=mp.re(P4), L=mp.re(L), Xt=mp.re(val(Xt)), X0=mp.re(val(X0)), Xh=mp.re(val(Xh)),
                   dXt=mp.re(der(Xt)), dX0=mp.re(der(X0)), dXh=mp.re(der(Xh)), Q=zr['Q'], Z=zr['Z'],
                   Zzm=zr['Z_zero_mode'], R=[mp.re(v) for v in zr['R']], c0=[mp.re(v) for v in zr['c0hat']])
    out['time'] = time.time() - t0
    return dstr, {k: (str(v) if not isinstance(v, list) else [str(x) for x in v]) for k, v in out.items()}


def psibasis(q):
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    Rp = mp.psi(1, 2 * q) - mp.psi(1, 1)
    U = mp.psi(2, q)
    V = mp.psi(2, 1) + mp.psi(2, 2 * q)
    X = mp.psi(3, 2 * q) - mp.psi(3, 1)
    return A, Rp, U, V, X


def refs(dstr, d):
    pi, G = mp.pi, mp.catalan
    if dstr in ('1', '2'):
        G4 = mp.gamma(mp.mpf(1) / 4) ** 4
        Fm = None
        # B_- , B_+ from 4F3(1) by mpmath at raised precision (convergent, excess 1)
        with mp.workdps(DPS + 30):
            Fm = mp.hyper([mp.mpf(1) / 4, mp.mpf(1) / 4, mp.mpf(1) / 2, mp.mpf(1) / 2],
                          [mp.mpf(3) / 4, mp.mpf(3) / 4, 1], 1)
            Fp = mp.hyper([mp.mpf(3) / 4, mp.mpf(3) / 4, mp.mpf(1) / 2, mp.mpf(1) / 2],
                          [mp.mpf(5) / 4, mp.mpf(5) / 4, 1], 1)
        Bm, Bp = G4 * Fm, 64 * pi ** 4 / G4 * Fp
        if dstr == '1':
            Q = G4 / pi
            P4 = 13 * Bm - 3 * Bp
            A = pi + 4 * mp.log(2)
            L = -(3 * A - pi) / 6 * P4 - 2 * pi / 3 * Bm
            Z = Q * (2 * pi ** 2 / 3 + 8 * G)
        else:
            Q = G4 ** 2 / (24 * pi ** 4)
            P4 = (Bm ** 2 - Bp ** 2) / (4 * pi ** 3)
            L = -2 * mp.log(2) * P4
            Z = 4 * G * Q
        return dict(P4=P4, Q=Q, L=L, Z=Z, src='closed forms')
    if dstr == '3':
        v = json.load(open(C63D_L))['values']
        z3 = mp.mpf('8.82092489306009248553686732817408087436490074')
        return dict(P4=mp.mpf(v['P4']), L=mp.mpf(v['L3']), Q=mp.mpf('5.01710256455385536959085484569018'), Z=z3,
                    src='C63d (Q3 to 33 digits)')
    rj = json.load(open(REFJ))['values']
    key = 'd=' + mp.nstr(d, 4).rstrip('0').rstrip('.')
    e = rj[key]
    return dict(P4=mp.mpf(e['P4']['value']), L=mp.mpf(e['L']['value']), Q=mp.mpf(e['threeQ']['value']) / 3,
                Z=mp.mpf(e['Z']['value']), K=mp.mpf(e['K']['value']), src='C63d spectral refs %s' % key)


def main():
    with Pool(len(DIMS)) as pool:
        res = dict(pool.map(compute, DIMS))
    mp.mp.dps = DPS
    report = {}
    for dstr in DIMS:
        r = {k: (mp.mpf(v) if not isinstance(v, list) else [mp.mpf(x) for x in v]) for k, v in res[dstr].items()}
        d = parse(dstr)
        q = d / 4
        pi = mp.pi
        S, C = mp.sin(pi * q), mp.cos(pi * q)
        A, Rp, U, V, X = psibasis(q)
        # compact sample form of L and P4
        Dfr = (1 + C) ** 2 * (1 + 2 * C) * r['dX0'] - (1 - C) ** 2 * (1 - 2 * C) * r['dXh'] - 2 * C * r['dXt']
        P4c = 2 / (pi * S ** 7) * ((1 + C) ** 2 * (1 + 2 * C) * r['X0'] - (1 - C) ** 2 * (1 - 2 * C) * r['Xh']
                                   - 2 * C * r['Xt'])
        Lc = -(1 / S ** 8) * ((1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2) * r['X0']
                              + (1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2) * r['Xh'] - 2 * (1 + 6 * C ** 2) * r['Xt']) \
            + 2 / (pi * S ** 7) * Dfr
        # reduced sample form of the wheel block 384 A P4 - 576 L
        k0 = (1 + C) ** 2 * (768 * A * (1 + 2 * C) / (pi * S ** 7) + 576 * (4 + 9 * C + 8 * C ** 2) / S ** 8)
        kh = (1 - C) ** 2 * (-768 * A * (1 - 2 * C) / (pi * S ** 7) + 576 * (4 - 9 * C + 8 * C ** 2) / S ** 8)
        kT = -1536 * A * C / (pi * S ** 7) - 1152 * (1 + 6 * C ** 2) / S ** 8
        wheel_red = k0 * r['X0'] + kh * r['Xh'] + kT * r['Xt'] - 1152 / (pi * S ** 7) * Dfr
        # Z in zero-mode form with Q (gdr:Zzm)
        Rr, c0 = r['R'], r['c0']
        Zq = (2 * pi ** 2 / (3 * S ** 2)) * Rr[2] - pi ** 2 * mp.cos(2 * pi * q) / (6 * S ** 2) * r['Q'] \
            + (pi * (1 + C ** 2) * c0[0] / S ** 5 - 4 * C * c0[1] / S ** 4 + 4 * c0[2] / (pi * S ** 3)) / 9
        Qc = (6 * pi ** 2 / S ** 2 * Rr[0] + 4 / (pi * S ** 3) * c0[0]) / 3
        ref = refs(dstr, d)
        B_new = 384 * A * r['P4'] - 576 * r['L'] - 1728 * r['Q'] ** 2 + (720 * A ** 2 + 1008 * Rp) * r['Q'] + 7152 * r['Z']
        B_red = wheel_red - 1728 * Qc ** 2 + (720 * A ** 2 + 1008 * Rp - 1192 * pi ** 2 * mp.cos(2 * pi * q) / S ** 2) * Qc \
            + 7152 * ((2 * pi ** 2 / (3 * S ** 2)) * Rr[2]
                      + (pi * (1 + C ** 2) * c0[0] / S ** 5 - 4 * C * c0[1] / S ** 4 + 4 * c0[2] / (pi * S ** 3)) / 9)
        B_ref = 384 * A * ref['P4'] - 576 * ref['L'] - 1728 * ref['Q'] ** 2 + (720 * A ** 2 + 1008 * Rp) * ref['Q'] \
            + 7152 * ref['Z']
        rel = lambda a, b: mp.nstr(abs(a - b) / abs(b), 3)  # noqa: E731
        row = dict(P4=mp.nstr(r['P4'], 30), L=mp.nstr(r['L'], 30), Q=mp.nstr(r['Q'], 30), Z=mp.nstr(r['Z'], 30),
                   Dfr=mp.nstr(Dfr, 30), B=mp.nstr(B_new, 30),
                   dev_P4_compact=rel(P4c, r['P4']), dev_L_compact=rel(Lc, r['L']), dev_Z_Qform=rel(Zq, r['Z']),
                   dev_Q_c0form=rel(Qc, r['Q']), dev_Bred_vs_B=rel(B_red, B_new),
                   dev_P4_ref=rel(r['P4'], ref['P4']), dev_L_ref=rel(r['L'], ref['L']), dev_Q_ref=rel(r['Q'], ref['Q']),
                   dev_Z_ref=rel(r['Z'], ref['Z']), dev_B_ref=rel(B_new, B_ref), ref=ref['src'],
                   time=mp.nstr(r['time'], 4))
        if dstr == '1':
            T, Tb, Up = mp.psi(1, mp.mpf(1) / 4), mp.psi(1, mp.mpf(3) / 4), mp.psi(2, mp.mpf(1) / 4)
            K1 = (T * (3 * T - Tb) + A * U) / 2
            P5 = mp.mpf('28599.2931765621035366464770214')
            C5 = (-1536 * (P5 + K1) + B_red - 15 * A ** 4 - 90 * A ** 2 * Rp + 414 * A * U - 108 * A * V
                  - 117 * Rp ** 2 - 75 * X) / 46656
            row['C5(1)'] = mp.nstr(C5, 25)
            row['C5(1)_note'] = '-731.13947662454'
        report[dstr] = row
        print(dstr, json.dumps(row, indent=1), flush=True)
    json.dump(report, open(os.path.join(_HERE, 'results', 'c5_assembly_dps%d.json' % DPS), 'w'), indent=1)


if __name__ == '__main__':
    main()
