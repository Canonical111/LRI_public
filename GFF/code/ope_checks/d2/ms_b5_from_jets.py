#!/usr/bin/env python3
"""MS b_3..b_5 and c_3..c_5 at d=2 from the finite-MOM jets of our C8(2) production, against the OPE package's
five-loop RG input (eqs. b3, b4, b5, clower, c5 of lri_ope_note.tex, supplied by the author 2026-10-16).

Why this is possible. Our d=2 productions use the finite-MOM scheme (condensed note Sec. cn:finiteAssembly):
  beta^(g,z) = -z g + 3 g^2 + sum_{L>=2} b^_L(z) g^(L+1),  gamma^(g,z) = g + sum_{L>=2} c^_L(z) g^L,
with Taylor jets b^_L(z), c^_L(z). A coupling redefinition g = g' + sum_k rho_k(z) g'^(k+1) and an operator
normalization log f = sum_k psi_k(z) g'^k, both regular at z=0, give
  beta'(g') = beta^(g(g'))/g'(g'),   gamma'(g') = gamma^(g(g')) + beta'(g') d/dg' log f.
Demanding that beta' = -z g' + sum b_L g'^(L+1) and gamma' = sum c_L g'^L have z-INDEPENDENT coefficients fixes
rho_k and psi_k uniquely order by order (the -z g' term turns every redefinition into a z-dependent change), so the
result is the constant-coefficient (MS) beta function and mass anomalous dimension of the same critical theory.
b_5 needs b^_2 to z^3, b^_3 to z^2, b^_4 to z^1 and b^_5 at z^0 (c likewise); the production has more.

Inputs (passed as arguments): the production's groups/ directory ({a,b}_{free,power}_L{3..8}/merged.json, 'batches'
= replicates x jets, layout b-jet z^0..z^(k-1) then c-jet, k = 9-L) and inputs/two_loop.json (b^_2(z) = B2(z),
c^_2 = B2/6). Means and covariances as in the package (campaign_moments: two campaigns, weights 1/2; sectors free
and power independent; loops independent). Errors by linear propagation (the maps are polynomial in the jets).
Usage: python -I ms_b5_from_jets.py GROUPS_DIR TWO_LOOP_JSON [--order 7|8] [--out FILE.json]
"""
import argparse
import json
import sys
from pathlib import Path

import mpmath as mp
import numpy as np
import sympy as s

ORDER = 8          # production order (--order): loop L carries k = ORDER + 1 - L Taylor slots
NMAX = 5           # highest MS loop order extracted


def load(groups: Path):
    means, covs = {}, {}
    for L in range(3, NMAX + 1):
        k = ORDER + 1 - L
        m_tot, v_tot = np.zeros(2 * k), np.zeros((2 * k, 2 * k))
        for sector in ('free', 'power'):
            ms, vs = [], []
            for camp in ('a', 'b'):
                d = json.loads((groups / f'{camp}_{sector}_L{L}' / 'merged.json').read_text())
                assert d['L'] == L and d['sector'] == sector and d.get('campaign', camp) == camp and d['complete'] and d['dimension'] == 2
                assert d['order'] == ORDER, (d['order'], ORDER)
                x = np.asarray(d['batches'], dtype=float)
                assert x.shape[1] == 2 * k
                ms.append(x.mean(0)); vs.append(np.cov(x, rowvar=False, ddof=1) / len(x))
            m_tot += (ms[0] + ms[1]) / 2; v_tot += (vs[0] + vs[1]) / 4
        means[L], covs[L] = m_tot, v_tot
    return means, covs


def ms_map():
    """Symbolic MS b_2..b_NMAX, c_2..c_NMAX as polynomials in the jet symbols."""
    z, x = s.symbols('z x')                       # x = g'
    K = NMAX + 1                                  # z-orders kept: enough for every needed slot
    bj = {L: [s.Symbol(f'b{L}_{j}') for j in range(K)] for L in range(2, NMAX + 1)}
    cj = {L: [s.Symbol(f'c{L}_{j}') for j in range(K)] for L in range(2, NMAX + 1)}
    bh = {1: s.Integer(3), **{L: sum(bj[L][j]*z**j for j in range(K)) for L in range(2, NMAX + 1)}}
    ch = {1: s.Integer(1), **{L: sum(cj[L][j]*z**j for j in range(K)) for L in range(2, NMAX + 1)}}
    rho = {k: [s.Symbol(f'r{k}_{j}') for j in range(K)] for k in range(1, NMAX + 1)}
    psi = {k: [s.Symbol(f'p{k}_{j}') for j in range(K)] for k in range(1, NMAX + 1)}
    bms = {1: s.Integer(3), **{L: s.Symbol(f'B{L}') for L in range(2, NMAX + 1)}}
    cms = {1: s.Integer(1), **{L: s.Symbol(f'C{L}') for L in range(2, NMAX + 1)}}
    R = lambda k: sum(rho[k][j]*z**j for j in range(K))
    P = lambda k: sum(psi[k][j]*z**j for j in range(K))
    def trunc(e):                                 # drop x^(>NMAX+1) and z^(>NMAX): never needed below
        p = s.Poly(s.expand(e), x, z)
        return sum(cf*x**i*z**j for (i, j), cf in p.terms() if i <= NMAX + 1 and j <= NMAX)
    g = x + sum(R(k)*x**(k + 1) for k in range(1, NMAX + 1))
    gpow = {1: g}
    for n in range(2, NMAX + 2):
        gpow[n] = trunc(gpow[n - 1]*g)
    lhs = trunc(-z*g + sum(bh[L]*gpow[L + 1] for L in range(1, NMAX + 1)))
    betap = -z*x + sum(bms[L]*x**(L + 1) for L in range(1, NMAX + 1))
    rhs = trunc(s.diff(g, x)*betap)
    gam = trunc(sum(ch[L]*gpow[L] for L in range(1, NMAX + 1))
                + betap*s.diff(sum(P(k)*x**k for k in range(1, NMAX + 1)), x)
                - sum(cms[L]*x**L for L in range(1, NMAX + 1)))
    eqb, eqc = s.Poly(lhs - rhs, x), s.Poly(gam, x)
    sol = {}
    for n in range(1, NMAX + 1):                  # order g'^(n+1) of beta, g'^n of gamma
        # z-orders needed at loop n: the conversion of loop NMAX needs z^(NMAX-n) at loop n
        for eqs, unk_const, unk_ser in ((eqb.coeff_monomial(x**(n + 1)), bms.get(n), rho[n]),
                                        (eqc.coeff_monomial(x**n), cms.get(n), psi[n])):
            e = s.expand(eqs.subs(sol))
            for m in range(0, NMAX - n + 1):
                cm = s.expand(e.coeff(z, m))
                if m == 0:
                    if n == 1:                    # b_1, c_1 fixed: forces rho_1 = psi_1 = 0 at all orders
                        assert cm == 0, cm
                        continue
                    sol[unk_const] = s.solve(cm, unk_const)[0]
                else:
                    sol[unk_ser[m - 1]] = s.solve(cm, unk_ser[m - 1])[0]
            if n == 1:
                for j in range(K):
                    sol[unk_ser[j]] = s.Integer(0)
            sol = {k: s.expand(v.subs(sol)) for k, v in sol.items()}
    out = {}
    for L in range(2, NMAX + 1):
        out[f'b{L}'] = sol[bms[L]]
        out[f'c{L}'] = sol[cms[L]]
    return out, bj, cj


def package_values():
    """The OPE package's b_L, c_L at d=2 (A=4log2, R=X=0, U=-14z3, V=-4z3, T=6Q2, M=-4, N=4-4log2, J_m=8),
    with the masters from the condensed note's closed forms (as in ope_d2_check.py)."""
    t, G, z3, pi = mp.log(2), mp.catalan, mp.zeta(3), mp.pi
    g4 = mp.gamma(mp.mpf(1)/4)
    Q = g4**8/(24*pi**4)
    Fm = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
    Fp = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
    Bm, Bp = g4**4*Fm, 64*pi**4/g4**4*Fp
    P4 = (Bm**2 - Bp**2)/(4*pi**3)

    def Y(r):
        r = mp.mpf(r); a, b = (r + 2)/8, (r + 6)/8
        return r/8*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper([1, 1 + r/8] + [a]*7, [r/8] + [b]*7, -1)
    c8, s8 = mp.cos(pi/8), mp.sin(pi/8)
    X0, Xp, Xm = Y(2), c8**7*Y(3) - s8**7*Y(5), c8**7*Y(1) + s8**7*Y(7)
    P5 = 8/pi*(25*X0**2 - 28*mp.sqrt(2)*X0*(Xp + Xm) + 18*(Xp**2 + Xm**2) + 28*Xp*Xm)
    K, Lm, Z = 32*G**2 - 28*z3*t, -2*t*P4, 4*G*Q
    A, R, U, V, X, T, M, N, Jm = 4*t, 0, -14*z3, -4*z3, 0, 6*Q, -4, 4 - 4*t, 8
    # sanity of the d=2 mass functions against their definitions (eq. massfunctions)
    q = mp.mpf(1)/2
    assert abs(M - mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)) < mp.mpf(10)**(-40)
    assert abs(N - (mp.digamma(-q) + mp.digamma(3*q) - mp.digamma(1) - mp.digamma(2*q))) < mp.mpf(10)**(-40)
    assert abs(Jm - (mp.polygamma(1, -q) - mp.polygamma(1, 3*q))) < mp.mpf(10)**(-40)
    f = mp.mpf
    b3 = T + f(87)/4*A**2 - f(9)/4*R + M
    b4 = (-f(393)/4*A**3 - f(11)/2*A*M - 9*A*T + f(117)/4*A*R - f(3)/2*M*N - 6*P4 - f(165)/8*U + f(9)/4*V)
    b5 = (f(64341)/128*A**4 + f(2145)/64*A**2*M - f(17001)/64*A**2*R + f(1053)/16*A**2*T + f(393)/32*A*M*N
          + 63*A*P4 + f(14907)/64*A*U - f(603)/32*A*V + 87*K + f(51)/4*Lm + f(3)/4*M**2
          + f(81)/64*M*N**2 - f(9)/8*M*R + M*T + f(81)/64*M*Jm + 24*P5 + f(1839)/128*R**2
          - f(153)/16*R*T + f(7)/4*T**2 + f(565)/128*X - f(1311)/8*Z)
    c3 = f(7)/2*A**2 - R/2 + M/f(3)
    c4 = (-f(127)/8*A**3 - f(7)/6*A*M - A*T/2 + f(51)/8*A*R - M*N/2 - f(57)/16*U + f(3)/8*V)
    c5 = (f(10549)/128*A**4 + f(411)/64*A**2*M - f(3561)/64*A**2*R + f(89)/16*A**2*T + f(99)/32*A*M*N
          + 3*A*P4 + f(2531)/64*A*U - f(75)/32*A*V + 21*K + f(5)/4*Lm + M**2/4
          + f(27)/64*M*N**2 - M*R/8 + f(27)/64*M*Jm + f(463)/128*R**2 - f(21)/16*R*T
          + f(415)/384*X - f(139)/8*Z)
    # our condensed note, gs:D5 at d=2 (D_5 = 3c_5 - b_5), Q = T/6
    D5rem = (-f(16347)/64*A**4 - f(57)/4*A**2*M - f(1179)/4*A**2*Q + f(3159)/32*A**2*R - 3*A*M*N
             - f(3657)/32*A*U + f(189)/16*A*V - 24*K - 6*M*Q + f(3)/4*M*R + f(135)/4*Q*R
             - f(225)/64*R**2 - f(75)/64*X + f(447)/4*Z)
    D5 = D5rem - 54*A*P4 - 9*Lm - 63*Q**2 - 24*P5
    return {'b2': -6*A, 'c2': -A, 'b3': b3, 'b4': b4, 'b5': b5, 'c3': c3, 'c4': c4, 'c5': c5,
            '3c5-b5_package': 3*c5 - b5, 'D5_note_gsD5': D5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('groups', type=Path)
    ap.add_argument('two_loop', type=Path)
    ap.add_argument('--out')
    ap.add_argument('--order', type=int, default=8, help='7 for the C7(2) production, 8 for C8(2)')
    ap.add_argument('--expect', type=Path, help='recorded output; exit 1 unless every from_jets value and se agrees '
                                               'with it to 1e-9 relative (a replay check, not a physics check)')
    a = ap.parse_args()
    global ORDER
    ORDER = a.order
    mp.mp.dps = 50
    means, covs = load(a.groups)
    B2 = [float(v) for v in json.loads(a.two_loop.read_text())['B2']]
    exprs, bj, cj = ms_map()
    # numeric environment: two-loop exact (B2, c2 = B2/6); loops 3..5 sampled
    env = {}
    for j, sym in enumerate(bj[2]):
        env[sym] = B2[j] if j < len(B2) else 0.0
    for j, sym in enumerate(cj[2]):
        env[sym] = B2[j]/6 if j < len(B2) else 0.0
    sampled = []                                  # (symbol, loop, index in the jet vector)
    for L in range(3, NMAX + 1):
        k = ORDER + 1 - L
        for j in range(len(bj[L])):
            for sym, off in ((bj[L][j], 0), (cj[L][j], k)):
                if j < k:
                    env[sym] = means[L][off + j]; sampled.append((sym, L, off + j))
                else:
                    env[sym] = 0.0
    pkg = package_values()
    res = {'order': ORDER, 'groups': str(a.groups), 'two_loop_sha256': __import__('hashlib').sha256(a.two_loop.read_bytes()).hexdigest(),
           'note': 'MS coefficients from finite-MOM jets of a d=2 production; errors: linear propagation of the '
                   'replicate covariance (2 campaigns x 2 sectors). Not the package code.', 'rows': {}}
    avail = {sym for sym, _, _ in sampled} | set(bj[2][:len(B2)]) | set(cj[2][:len(B2)])
    for name, ex in exprs.items():
        assert ex.free_symbols <= avail, (name, ex.free_symbols - avail)
        used = sorted({str(v) for v in ex.free_symbols})
        val = float(ex.subs(env))
        var = 0.0
        for L in range(3, NMAX + 1):
            idx = [(sym, i) for sym, LL, i in sampled if LL == L and sym in ex.free_symbols]
            if not idx:
                continue
            grad = np.zeros(len(means[L]))
            for sym, i in idx:
                grad[i] = float(s.diff(ex, sym).subs(env))
            var += grad @ covs[L] @ grad
        se = var**0.5
        ref = float(pkg[name])
        res['rows'][name] = {'from_jets': val, 'se': se, 'package_formula': mp.nstr(pkg[name], 20),
                             'diff': val - ref, 'pull': (val - ref)/se if se > 0 else None,
                             'jet_symbols_used': used}
    def value_se(ex):
        var = 0.0
        for L in range(3, NMAX + 1):
            grad = np.zeros(len(means[L]))
            for sym, LL, i in sampled:
                if LL == L and sym in ex.free_symbols:
                    grad[i] = float(s.diff(ex, sym).subs(env))
            var += grad @ covs[L] @ grad
        return float(ex.subs(env)), var**0.5
    d5v, d5se = value_se(3*exprs['c5'] - exprs['b5'])
    res['rows']['3c5-b5'] = {'from_jets': d5v, 'se': d5se,
                             'package_formula': mp.nstr(pkg['3c5-b5_package'], 20),
                             'note_gsD5': mp.nstr(pkg['D5_note_gsD5'], 20),
                             'package_minus_note': mp.nstr(pkg['3c5-b5_package'] - pkg['D5_note_gsD5'], 5),
                             'pull_vs_note': (d5v - float(pkg['D5_note_gsD5']))/d5se}
    # b_5 given the proved D_5 (gs:D5): b_5 = 3 c_5 - D_5, so only c_5 is sampled
    c5v, c5se = value_se(exprs['c5'])
    b5c = 3*c5v - float(pkg['D5_note_gsD5'])
    res['rows']['b5_via_proved_D5'] = {'from_jets': b5c, 'se': 3*c5se, 'package_formula': mp.nstr(pkg['b5'], 20),
                                       'diff': b5c - float(pkg['b5']), 'pull': (b5c - float(pkg['b5']))/(3*c5se)}
    res['symbolic_b5'] = str(exprs['b5'])
    txt = json.dumps(res, indent=1)
    if a.expect:
        rec = json.loads(a.expect.read_text())['rows']
        worst = 0.0
        for k, v in res['rows'].items():
            for f in ('from_jets', 'se'):
                if f in v and v[f] is not None:
                    x, y = float(v[f]), float(rec[k][f])
                    worst = max(worst, abs(x - y) / max(abs(y), 1e-300))
        res['replay_max_relative_difference'] = worst
        txt = json.dumps(res, indent=1)
        if worst > 1e-9:
            print(txt)
            sys.exit(f'replay differs from {a.expect}: {worst:.3e}')
    if a.out:
        Path(a.out).write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
