#!/usr/bin/env python3
"""Finite-part extraction (FPE) from quad-precision direct data, by least-squares fits.

For each normalized response X (C3, K2=Q2, EK2=EE Q2, K4 = Q4 - Q2 Z2 and their
v/delta derivatives, formed AT FINITE eps with the Leibniz rule) the data X(eps_i),
eps_i in [1e-9, 1e-4], are fitted to
      X(eps) = sum_{k=kmin}^{K} sum_{j=0}^{D} c_{kj} eps^k l^j ,  l = log(eps),
and X_m := c_{0m} (m = 0, 1) is the finite / single-log coefficient
[eps^0 l^m] X.  The fit is repeated for several (D, K, eps-window) choices; the
spread is reported as the extraction uncertainty (not a rigorous bound).

The beta inputs are then assembled with the framework's formulas
(framework/out/beta_input_formulas.json, atoms X_m_<v..><d..>[E] =
d_v^i d_delta^j [EE] [eps^0 l^m] X) and compared with closed forms (old inputs)
and with the note/archive values (new inputs; comparison only).

Output: results/fpe_atoms.json, results/fpe_inputs.json
"""
import argparse
import itertools
import json
import math
import os
from collections import defaultdict

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
FW = os.environ.get('FW_FORMULAS', os.path.join(HERE, '..', '..', 'framework', 'out', 'beta_input_formulas.json'))


def load(path):
    data = defaultdict(dict)       # (prog,n,kind,E) -> eps_str -> {(a,b): derivative value}
    control = defaultdict(dict)
    for line in open(path):
        if not line.strip():
            continue
        d = json.loads(line)
        t = d['task']
        key = (t['prog'], t['n'], t['kind'], t.get('E', 0))
        vals = {}
        for k, v in d['coef'].items():
            a, b = map(int, k.split(','))
            vals[(a, b)] = mp.mpf(v) * math.factorial(a) * math.factorial(b)
        (control if t.get('control') else data)[key][t['eps']] = vals
    return data, control


def leibniz_prod(F, G, a, b):
    s = mp.mpf(0)
    for i in range(a + 1):
        for j in range(b + 1):
            if (i, j) in F and (a - i, b - j) in G:
                s += mp.binomial(a, i) * mp.binomial(b, j) * F[(i, j)] * G[(a - i, b - j)]
            else:
                return None
    return s


def build_atoms(data):
    """Return {name: {eps_str: (value, noise_sigma)}}, name like 'C3_vd', 'K4_dd', 'K2_v', 'EK2_vv'.
    noise_sigma = (relative accuracy of the raw data) x (sum of |raw terms|): the cancellation of the
    eps^-1 pieces in C3 = A3 - Z2 and K4 = Q4 - Q2 Z2 is what limits the precision."""
    A3 = data[('q', 3, 'A', 0)]
    Z2 = data[('q', 2, 'Z', 0)]
    Q2 = data[('q', 2, 'Q', 0)]
    Q4 = data[('q', 4, 'Q', 0)]
    EQ2 = data[('mp2', 2, 'Q', 1)]
    RQ, RM = mp.mpf('1e-28'), mp.mpf('1e-38')   # binary128 Gauss (controls: 2.6e-28), mpmath 45 digits
    atoms = defaultdict(dict)

    def suf(a, b):
        return ('v' * a + 'd' * b)
    for e in A3:
        if e not in Z2:
            continue
        for (a, b), v in A3[e].items():
            atoms['C3' + ('_' + suf(a, b) if a + b else '')][e] = (v - Z2[e][(a, b)], RQ * (abs(v) + abs(Z2[e][(a, b)])))
    for e in Q2:
        for (a, b), v in Q2[e].items():
            atoms['K2' + ('_' + suf(a, b) if a + b else '')][e] = (v, RQ * abs(v))
    for e in EQ2:
        for (a, b), v in EQ2[e].items():
            atoms['EK2' + ('_' + suf(a, b) if a + b else '')][e] = (v, RM * abs(v))
    for e in Q4:
        if e not in Q2 or e not in Z2:
            continue
        for (a, b), v in Q4[e].items():
            p = leibniz_prod(Q2[e], Z2[e], a, b)
            pa = leibniz_prod({k: abs(x) for k, x in Q2[e].items()}, {k: abs(x) for k, x in Z2[e].items()}, a, b)
            if p is not None:
                atoms['K4' + ('_' + suf(a, b) if a + b else '')][e] = (v - p, RQ * (abs(v) + pa))
    return atoms


BASE_DEG = {'C3': 2, 'K2': 1, 'EK2': 1, 'K4': 3}   # log degree at eps^0 of the underived response
KMIN = {'C3': 0, 'K2': 0, 'EK2': 0, 'K4': 0}        # singular powers cancel (diagnostic variant kmin=-1)


def deg_of(name):
    fam = name.split('_')[0]
    s = name.split('_')[1] if '_' in name else ''
    # (E Q2 has no logs at eps^0, but its eps^k, k>=1, terms do: the same degree is used for all k)
    return BASE_DEG[fam] + s.count('v') + 2 * s.count('d'), KMIN[fam]


def wfit(points, kmin, K, D):
    """weighted least squares; points = [(eps_str, value, sigma)]; returns ({(k,j): c}, max |resid|/sigma)."""
    idx = [(k, j) for k in range(kmin, K + 1) for j in range(D + 1)]
    rows, b = [], []
    for e, v, sg in points:
        x = mp.mpf(e)
        l = mp.log(x)
        rows.append([x ** k * l ** j / sg for (k, j) in idx])
        b.append(v / sg)
    A = mp.matrix(rows)
    sc = []
    for c in range(A.cols):
        s_ = max(abs(A[i, c]) for i in range(A.rows))
        sc.append(s_)
        for i in range(A.rows):
            A[i, c] /= s_
    x, res = mp.qr_solve(A, mp.matrix(b))
    coef = {idx[c]: x[c] / sc[c] for c in range(len(idx))}
    chi = mp.mpf(0)
    for e, v, sg in points:
        xx = mp.mpf(e)
        l = mp.log(xx)
        chi = max(chi, abs(sum(cv * xx ** k * l ** j for (k, j), cv in coef.items()) - v) / sg)
    return coef, chi


_ATOMS = _EPS = _VAR = None


def eps_sel(eps_all, win):
    if win == 'all':
        return eps_all
    if win == 'low':
        return [e for e in eps_all if float(e) <= 1.0001e-5]
    if win == 'odd':
        return eps_all[1::2]


def fit_atom(name):
    mp.mp.dps = DPS
    atoms, eps_all, variants = _ATOMS, _EPS, _VAR
    D0, _ = deg_of(name)
    res = []
    for kmin, dD, K, win in variants:
        D = D0 + dD
        el = eps_sel(eps_all, win)
        if len(el) < (K - kmin + 1) * (D + 1) + 5:
            continue
        try:
            c, chi = wfit([(e, atoms[name][e][0], atoms[name][e][1]) for e in el], kmin, K, D)
        except ValueError:      # numerically singular at this working precision: variant skipped
            continue
        res.append(dict(variant=(kmin, dD, K, win), c00=c[(0, 0)], c01=c[(0, 1)] if D >= 1 else mp.mpf(0),
                        chi=chi, sing=max([abs(c[(k, j)]) for (k, j) in c if k < 0] or [mp.mpf(0)])))
    if not res or res[0]['variant'] != variants[0]:
        nan = mp.mpf('nan')
        return name, dict(m0=nan, m0_spread=mp.inf, m1=nan, m1_spread=mp.inf, D0=D0, max_resid_over_sigma=nan,
                          singular_coef_kmin_m1=nan, nvariants=len(res), variants=[])
    base = res[0]
    sp0 = max(abs(r['c00'] - base['c00']) for r in res)
    sp1 = max(abs(r['c01'] - base['c01']) for r in res)
    return name, dict(m0=base['c00'], m0_spread=sp0, m1=base['c01'], m1_spread=sp1, D0=D0,
                      max_resid_over_sigma=base['chi'], singular_coef_kmin_m1=res[-1]['sing'], nvariants=len(res),
                      variants=[dict(variant=r['variant'], c00=mp.nstr(r['c00'], 25), c01=mp.nstr(r['c01'], 25)) for r in res])


DPS = 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(RES, 'fpe_data.jsonl'))
    ap.add_argument('--dps', type=int, default=120)
    a = ap.parse_args()
    global DPS
    DPS = a.dps
    mp.mp.dps = a.dps
    data, control = load(a.data)
    # convergence controls
    ctrl = []
    for key, d in control.items():
        for e, vals in d.items():
            ref = data[key].get(e)
            if ref:
                for ab, v in vals.items():
                    ctrl.append(abs(v - ref[ab]) / abs(ref[ab]))
    print('quad convergence controls: %d, max rel diff %s' % (len(ctrl), mp.nstr(max(ctrl), 3) if ctrl else '-'))
    atoms = build_atoms(data)
    eps_all = sorted(set.intersection(*[set(v) for v in atoms.values()]), key=lambda s: float(s))
    print('atoms: %d, cutoffs: %d  [%s .. %s]' % (len(atoms), len(eps_all), eps_all[0], eps_all[-1]))
    variants = [  # (kmin, dD, K, window); the first is the central fit
        (0, 0, 5, 'all'), (0, 1, 5, 'all'), (0, 0, 4, 'all'), (0, 0, 6, 'all'), (0, 0, 4, 'low'),
        (0, 0, 5, 'odd'), (-1, 0, 5, 'all')]

    global _ATOMS, _EPS, _VAR
    _ATOMS, _EPS, _VAR = atoms, eps_all, variants
    import multiprocessing as mpc
    with mpc.get_context('fork').Pool(processes=min(len(atoms), os.cpu_count() or 1)) as pool:
        results = pool.map(fit_atom, sorted(atoms))
    out = {}
    for name, o in results:
        out[name] = o
        print('%-8s [l^0] %s +- %s   [l^1] %s +- %s   max|r|/sigma %s  sing(k=-1) %s' % (
            name, mp.nstr(o['m0'], 22), mp.nstr(o['m0_spread'], 2), mp.nstr(o['m1'], 22), mp.nstr(o['m1_spread'], 2),
            mp.nstr(o['max_resid_over_sigma'], 2), mp.nstr(o['singular_coef_kmin_m1'], 2)), flush=True)
    json.dump({k: {kk: (mp.nstr(vv, 30) if isinstance(vv, mp.mpf) else vv) for kk, vv in v.items()} for k, v in out.items()},
              open(os.path.join(RES, 'fpe_atoms.json'), 'w'), indent=1)
    assemble(out)


def atom_value(out, sym):
    """framework symbol like C3_1_vd, K2_0_vE, K4_1 -> (value, spread)."""
    parts = sym.split('_')
    fam, m = parts[0], int(parts[1])
    suf = parts[2] if len(parts) > 2 else ''
    E = suf.endswith('E')
    if E:
        suf = suf[:-1]
    name = ('E' if E else '') + fam + ('_' + suf if suf else '')
    o = out[name]
    return (o['m0'], o['m0_spread']) if m == 0 else (o['m1'], o['m1_spread'])


def assemble(out):
    import sympy as sp
    fw = json.load(open(FW))
    z2, z3, z4 = mp.zeta(2), mp.zeta(3), mp.zeta(4)
    L2 = mp.log(2)
    closed = {
        'a': -4 * z2,
        'c': mp.mpf(-16),
        'p': 8 - 2 * z2 - 7 * z3 - 8 * L2,
        'f': 32 - mp.mpf(136) / 3 * z3 - 64 * L2 + 48 * mp.log(3) + 16 * L2 ** 2 + 32 * mp.polylog(2, mp.mpf(-1) / 2),
        'A': -8 - 4 * z2 - 2 * z3 + 16 * L2,
        'E': -16 + 14 * z2 - 22 * z3 + 12 * z4 + 8 * L2 - 8 * L2 ** 2 - 16 * mp.polylog(4, mp.mpf(1) / 2)
             - 14 * z3 * L2 + 4 * z2 * L2 ** 2 - mp.mpf(2) / 3 * L2 ** 4,
    }
    # note values of new inputs (comparison only; note lines 610-612, 667-672, 1097)
    note = {
        'q': mp.mpf('-103.5603579270427462132101236545'),
        'V': mp.mpf('-19.518741011574465808'),
        'L': mp.mpf('-7.677303759056569914'),
        'M': mp.mpf('13.315217322864044765'),
        'Q': mp.mpf('-107.0654814955476394045726813165'),
        # archive C7-stage evaluation (data/archived/C7_completion/engine/final_evaluation_C7_second.json)
        'alpha': mp.mpf('-1.657651083870007227923778461576055470366'),
        'beta': mp.mpf('-16.02790869041850611398759442304075347399'),
        'gamma': mp.mpf('-44.00968406476779152371454000068112649710'),
    }
    res = {}
    print('\ninput   FPE value                         +- spread     reference                       diff')
    for inp in ['a', 'p', 'A', 'E', 'V', 'alpha', 'beta', 'gamma', 'c', 'f', 'q', 'L', 'M', 'Q']:
        expr = sp.sympify(fw[inp])
        syms = sorted(expr.free_symbols, key=str)
        vals = {}
        unc = mp.mpf(0)
        for s in syms:
            v, spr = atom_value(out, str(s))
            vals[s] = v
        f = sp.lambdify(syms, expr, modules='mpmath')
        val = f(*[vals[s] for s in syms])
        # propagate spreads linearly (numerical partial derivatives)
        for s in syms:
            v, spr = atom_value(out, str(s))
            h = mp.mpf('1e-20') * (1 + abs(v))
            args = [vals[t] + (h if t == s else 0) for t in syms]
            unc += abs((f(*args) - val) / h) * spr
        ref = closed.get(inp, note.get(inp))
        reftype = 'closed form' if inp in closed else ('archive value (alpha,beta,gamma) / note value' if inp in note else '')
        determined = bool(unc < mp.mpf('1e-6') * (1 + abs(val)))
        res[inp] = dict(value=mp.nstr(val, 30), spread=mp.nstr(unc, 3), determined=determined,
                        reference=mp.nstr(ref, 30) if ref is not None else None,
                        reference_type=reftype, diff=mp.nstr(val - ref, 3) if ref is not None else None,
                        formula=fw[inp])
        print('%-7s %-3s %-33s +- %-10s %-31s %s' % (inp, 'OK' if determined else 'n/d', mp.nstr(val, 25), mp.nstr(unc, 2),
                                               mp.nstr(ref, 22) if ref is not None else '-', mp.nstr(val - ref, 3) if ref is not None else ''))
    json.dump(res, open(os.path.join(RES, 'fpe_inputs.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
