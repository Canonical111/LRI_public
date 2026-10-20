#!/usr/bin/env python3
"""High-precision validation of the general-b finite-sample formula (run on symmetry).

usage: run_validation.py OUT.json DPS PART [PART ...]
PART:
  refs      closed-form / archived references at d = 1, 2, 3 (P4, 3Q, L, Z)
  center    W_r(d; d/2), r = 3, 4, d in {1,2,3,0.8,1.25,1.5,2.5,2.75}: 'fixed' AND 'note' nodes; Fourier data
  offdiag   W_r(d; d/2 +- 0.05) at the C63d reference points (incl. d=1.5 b=0.7,0.8 and d=2.5 b=1.2)
  spectral  own spectral evaluation at d=1.5 b=0.7,0.8 and d=2.5 b=1.2 (independent of C63d's code)
  circles   Cauchy circles in b around d/2: L_d = dW4/db, Z_d = (1/9) d^2W3/db^2 (bonus end-to-end check)
Each W evaluation is one pool task.  Results are written as strings.
"""
import sys
import os
import json
import time
import mpmath as mp
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hypsums import GammaSeq, single_sum                     # noqa: E402
from wheel_general_b import Wheel, W, bmax, exceptional    # noqa: E402
from spectral import W_spectral                           # noqa: E402

GUARD = 15
DS_NONINT = ['0.8', '1.25', '1.5', '2.5', '2.75']
DS_ALL = ['1', '2', '3'] + DS_NONINT


def S(x):
    return mp.nstr(x, mp.mp.dps + 5) if not isinstance(x, (list, tuple)) else [S(y) for y in x]


def task(args):
    kind, payload, dps = args
    mp.mp.dps = dps + GUARD
    st = time.time()
    if kind == 'point':
        r, d, b, nodes = payload
        d_, b_ = mp.mpmathify(d), mp.mpmathify(b)
        if exceptional(r, d_, b_):
            v = W(r, d_, b_, dps, nodes)
            out = dict(W=S(v), exceptional=True)
        else:
            w = Wheel(r, d_, b_)
            if nodes == 'fixed':
                v, info = w.W_fixed(full=True)
                gam = info['gamma']
                c = info['c']
                out = dict(W=S(v), c=S(c), gamma={str(m): S(gam[m]) for m in gam}, asym=S(info['asym']))
                # extra off-grid sample: finite-Fourier check
                t = mp.mpc('0.2371', '0.0917')
                err, size = w.trig_check(c, t)
                out['trig_check'] = S(err / size)
                out['top_mode_rel'] = S(abs(c[r - 1]) / max(abs(x) for x in c))
            elif nodes == 'reduced':
                v = w.W_reduced()
                out = dict(W=S(v))
            else:
                v, info = w.W_note(full=True)
                out = dict(W=S(v), c=S(info['c']))
    elif kind == 'spectral':
        r, d, b, L = payload
        mp.mp.dps = dps + 10
        out = dict(W=S(W_spectral(r, mp.mpmathify(d), mp.mpmathify(b), L)))
    elif kind == 'circle':
        r, d, b0, rho, M, k = payload
        th = 2 * mp.pi * (k + mp.mpf(1) / 2) / M
        b = mp.mpmathify(b0) + mp.mpmathify(rho) * mp.expj(th)
        w = Wheel(r, mp.mpmathify(d), b)
        out = dict(W=S(w.W_fixed()))
    else:
        raise ValueError(kind)
    out['seconds'] = time.time() - st
    return kind, payload, out


def refs(dps):
    mp.mp.dps = dps + GUARD
    q = mp.mpf(1) / 4
    G4 = mp.gamma(q) ** 4
    Fm = single_sum(GammaSeq([(q, 3 * q, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 120, 80)
    Fp = single_sum(GammaSeq([(3 * q, 5 * q, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 120, 80)
    Bm, Bp = G4 * Fm, 64 * mp.pi ** 4 / G4 * Fp
    A = mp.digamma(mp.mpf(1) / 2) + mp.digamma(1) - 2 * mp.digamma(q)
    out = {}
    P41 = 13 * Bm - 3 * Bp
    Q1 = G4 / mp.pi
    out['1'] = dict(P4=P41, threeQ=3 * Q1, L=-(3 * A - mp.pi) / 6 * P41 - 2 * mp.pi / 3 * Bm,
                    Z=Q1 * (2 * mp.pi ** 2 / 3 + 8 * mp.catalan))
    P42 = (Bm ** 2 - Bp ** 2) / (4 * mp.pi ** 3)
    Q2 = (mp.gamma(q) / mp.gamma(3 * q)) ** 4 / 6
    out['2'] = dict(P4=P42, threeQ=3 * Q2, L=-2 * mp.log(2) * P42, Z=4 * mp.catalan * Q2)
    out['3'] = dict(
        P4=mp.mpf('62.0583279434066724664633885840967369182686384706117573441491501766188713247020243698768399388939806676546885270759068218993623275696090168216768350333584058636576408'),
        threeQ=3 * mp.mpf('5.017102564553855369590854845690183699564491593500508978295918913380760766092034955549525020958745158926040891951167571181792373917843720100400440507977939870937099018238331693856015396032811952796865580636757478003188578147998815905745458849725997859'),
        L=mp.mpf('-62.7105849683876693472961734335348474600014697352518163896150217947496042860433131091729840559702816816683104633970696658925815930184380551174181370988788355561200694'),
        Z=mp.mpf('8.820924893060092485536867328174080874364900737593360435525373273389046616758898739535524883847961700954827040371517686629136174820673111833426524943357606691278950649832780817764057345117656190754219042363241412501412235085311469153686326659739191162'))
    return {d: {k: S(v) for k, v in dd.items()} for d, dd in out.items()}


def circle_params(r, d):
    d = mp.mpmathify(d)
    b0 = d / 2
    R = (d * (r - 2) / (2 * r)) if d >= 1 else (d / 2 - mp.mpf(1) / r)   # distance to nearest singularity of W(b)
    Reff = min(R, bmax(r, d) - b0)
    return b0, Reff / 3


if __name__ == '__main__':
    out_path, dps = sys.argv[1], int(sys.argv[2])
    parts = sys.argv[3:]
    tasks = []
    result = dict(dps=dps, guard=GUARD, parts=parts)
    if 'refs' in parts:
        result['refs'] = refs(dps)
    if 'center' in parts:
        for d in DS_ALL:
            for r in (3, 4):
                b = str(mp.mpmathify(d) / 2)
                tasks.append(('point', (r, d, b, 'fixed'), dps))
                tasks.append(('point', (r, d, b, 'note'), dps))
    if 'offdiag' in parts:
        for d in DS_NONINT:
            for r in (3, 4):
                for sgn in (1, -1):
                    b = str(mp.mpmathify(d) / 2 + sgn * mp.mpf('0.05'))
                    tasks.append(('point', (r, d, b, 'fixed'), dps))
                    tasks.append(('point', (r, d, b, 'note'), dps))
    if 'spectral' in parts:
        for (d, b) in [('1.5', '0.7'), ('1.5', '0.8'), ('2.5', '1.2')]:
            for r in (3, 4):
                tasks.append(('spectral', (r, d, b, 40), dps))
    if 'extra' in parts:
        # C63d's d = 0.8 off-diagonal points; reduced node sets; d = 2 closed form for W3; continuation; resonance
        for b in ('0.43', '0.37'):
            for r in (3, 4):
                tasks.append(('point', (r, '0.8', b, 'fixed'), dps))
                tasks.append(('point', (r, '0.8', b, 'reduced'), dps))
        for (r, d, b) in [(4, '1.5', '0.7'), (3, '1.5', '0.8'), (4, '2.5', '1.2'), (3, '2.5', '1.2'), (4, '2', '1'), (3, '3', '1.5')]:
            tasks.append(('point', (r, d, b, 'reduced'), dps))
        for b in ('0.8', '1.2'):
            tasks.append(('point', (3, '2', b, 'fixed'), dps))
            tasks.append(('point', (4, '2', b, 'fixed'), dps))
        for (r, d, b) in [(4, '2.5', '1.8'), (3, '2.5', '1.55'), (4, '2.75', '1.95'), (3, '2.75', '1.65')]:
            tasks.append(('point', (r, d, b, 'fixed'), dps))
            tasks.append(('spectral', (r, d, b, 40), dps))
        for (r, d, b) in [(4, '2.5', '1.5'), (3, '1.3333333333333333333333333333333333333333333333333333333333333333333333', '0.66666666666666666666666666666666666666666666666666666666666666666666667')]:
            tasks.append(('point', (r, d, b, 'fixed'), dps))
            tasks.append(('spectral', (r, d, b, 40), dps))
    circ = {}
    if 'circles' in parts:
        Mc = int(os.environ.get('MCIRC', 96))
        for d in os.environ.get('CIRCLE_DS', '1,2,3,1.5,2.5').split(','):
            for r in (3, 4):
                mp.mp.dps = dps + GUARD
                b0, rho = circle_params(r, d)
                circ[(r, d)] = (S(b0), S(rho), Mc)
                for k in range(Mc // 2):          # conjugate symmetry W(conj b) = conj W(b)
                    tasks.append(('circle', (r, d, S(b0), S(rho), Mc, k), dps))
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    print('tasks', len(tasks), 'workers', workers, flush=True)
    st = time.time()
    res = []
    with Pool(workers) as pool:
        for i, x in enumerate(pool.imap_unordered(task, tasks, chunksize=1)):
            res.append(x)
            if i % 10 == 0:
                print('done %d/%d  %.0f s' % (i + 1, len(tasks), time.time() - st), flush=True)
    result['points'] = [dict(kind=k, payload=p, out=o) for k, p, o in res if k in ('point', 'spectral')]
    # circles -> Taylor coefficients
    mp.mp.dps = dps + GUARD
    result['circles'] = {}
    for (r, d), (b0, rho, Mc) in circ.items():
        vals = {}
        for k, p, o in res:
            if k == 'circle' and p[0] == r and p[1] == d:
                vals[p[5]] = mp.mpmathify(o['W'])
        full = []
        for k in range(Mc):
            full.append(vals[k] if k < Mc // 2 else mp.conj(vals[Mc - 1 - k]))
        rho_ = mp.mpmathify(rho)
        coef = []
        for j in range(5):
            s = mp.fsum(full[k] * mp.expj(-j * 2 * mp.pi * (k + mp.mpf(1) / 2) / Mc) for k in range(Mc)) / Mc / rho_ ** j
            coef.append(s)
        result['circles']['r%d_d%s' % (r, d)] = dict(b0=b0, rho=rho, M=Mc, taylor=S(coef),
                                                      W0=S(coef[0]), dW=S(coef[1]), d2W=S(2 * coef[2]),
                                                      L_if_r4=S(coef[1]), Z_if_r3=S(2 * coef[2] / 9))
    result['seconds'] = time.time() - st
    json.dump(result, open(out_path, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
