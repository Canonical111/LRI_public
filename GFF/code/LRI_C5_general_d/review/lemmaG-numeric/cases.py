#!/usr/bin/env python3
"""Case definitions for the Lemma G probe.  Every case is returned as Lemma G data (d, sigma, g, alpha, beta, dmult).

mixed wheel prod_i g_l(s+delta_i; b_i) on s=(l+sigma)/2+n+t  ->  g_i=(d-b_i)/2,
    alpha_i=(b_i/2-sigma)/2+delta_i, beta_i=(b_i/2-sigma)/2-delta_i            (lemmaG_statement.md)
R family: g=(q,q,tau), sigma=q, alpha=(0,0,0), beta=(0,0,q-tau), q=d/4.
"""
import re
import mpmath as mp



def C(x):
    """exact decimal parsing: 'a', or 'a+bj' / 'a-bj' strings; never Python floats."""
    if isinstance(x, str) and x.endswith('j'):
        m = re.fullmatch(r'([+-]?[0-9.]*)([+-][0-9.]+)j', x)
        if m:
            return mp.mpc(m.group(1) or '0', m.group(2))
        return mp.mpc(0, x[:-1])
    if isinstance(x, (float, complex)):
        raise TypeError('use strings for exact parameters: %r' % (x,))
    return mp.mpmathify(x)


def mixed(d, sigma, b, delta):
    d, sigma = C(d), C(sigma)
    b = [C(x) for x in b]
    delta = [C(x) for x in delta]
    g = [(d - bi) / 2 for bi in b]
    al = [(bi / 2 - sigma) / 2 + de for bi, de in zip(b, delta)]
    be = [(bi / 2 - sigma) / 2 - de for bi, de in zip(b, delta)]
    return dict(d=d, sigma=sigma, g=g, alpha=al, beta=be, dmult=None)


def rfam(d, tau):
    d, tau = C(d), C(tau)
    q = d / 4
    return dict(d=d, sigma=q, g=[q, q, tau], alpha=[0, 0, 0], beta=[0, 0, q - tau], dmult=None)


def raw(d, sigma, g, alpha, beta=None, dmult=None):
    """beta=None: per-factor balance (B) imposed exactly."""
    d, sigma = C(d), C(sigma)
    g = [C(x) for x in g]
    alpha = [C(x) for x in alpha]
    if beta is None:
        beta = [d / 2 - sigma - a - gg for a, gg in zip(alpha, g)]
    else:
        beta = [C(x) for x in beta]
    return dict(d=d, sigma=sigma, g=g, alpha=alpha, beta=beta, dmult=None if dmult is None else C(dmult))


def imbalance(base, eps, i=0, j=1):
    """total balance kept, per-factor balance broken: beta_i += eps, beta_j -= eps."""
    out = dict(base)
    be = list(base['beta'])
    be[i] = be[i] + C(eps)
    be[j] = be[j] - C(eps)
    out['beta'] = be
    return out


def get(name):
    CASES = {
        # ---- (a) mixed wheels, r=3
        'A1': lambda: mixed('1.3', '0.35', ['0.5', '0.8', '0.9'], ['0.11', '-0.07', '0.23']),
        'A2': lambda: mixed('1.3', '0.3+0.15j', ['0.45+0.2j', '0.8-0.1j', '0.7+0.15j'],
                            ['0.1+0.05j', '-0.2', '0.15-0.1j']),
        'A3': lambda: mixed('2.4', '0.6', ['1.0', '1.3', '1.1'], ['0.2', '-0.15', '0.05']),
        'A4': lambda: mixed('2.4', '0.5-0.1j', ['2.55+0.1j', '0.5-0.2j', '0.7+0.25j'],
                            ['0.15j', '0.3', '-0.12+0.1j']),          # Re g_1 < 0
        'A5': lambda: mixed('3.1', '0.9', ['1.3', '1.5', '1.1'], ['0.1', '0.25', '-0.2']),
        'A6': lambda: mixed('3.1', '0.8+0.2j', ['1.2+0.3j', '1.6-0.1j', '1.0+0.2j'],
                            ['0.05-0.1j', '-0.2', '0.3+0.05j']),
        # ---- (a) mixed wheels, r=4
        'B1': lambda: mixed('1.3', '0.4', ['0.6', '0.9', '0.75', '1.0'], ['0.1', '-0.05', '0.2', '-0.15']),
        'B2': lambda: mixed('1.3', '0.25+0.1j', ['0.5+0.2j', '0.9-0.15j', '0.7', '1.05+0.1j'],
                            ['0.1j', '0.2', '-0.1-0.05j', '0.05']),
        'B3': lambda: mixed('2.4', '0.7', ['1.3', '1.6', '1.4', '1.5'], ['0.2', '-0.1', '0.05', '-0.25']),
        'B4': lambda: mixed('2.4', '0.55-0.15j', ['1.2+0.2j', '1.7-0.1j', '1.35+0.15j', '1.5-0.25j'],
                            ['0.2', '-0.1+0.1j', '0.05j', '-0.25']),
        'B5': lambda: mixed('3.1', '1.0', ['1.8', '2.0', '1.6', '1.9'], ['0.1', '0.15', '-0.2', '0.3']),
        'B6': lambda: mixed('3.1', '0.9+0.1j', ['1.7+0.1j', '2.0-0.2j', '1.6+0.3j', '1.8'],
                            ['0.1-0.05j', '0.15', '-0.2+0.1j', '0.05j']),
        # ---- sanity: equal wheel of Theorem 6 (b_i=b, delta_i=0, sigma=b/2)
        'W0': lambda: mixed('2.4', '0.55', ['1.1'] * 3, ['0'] * 3),
        # ---- (b) R family
        'R1': lambda: rfam('1.5', '0.45'),
        'R2': lambda: rfam('1.5', '1.2'),
        'R3': lambda: rfam('2.5', '0.6'),
        'R4': lambda: rfam('2.5', '1.1'),
        # ---- external cross-checks against C63d's per-spin numbers (PROOF.md Table 1; ~1e-14)
        'X_R5': lambda: rfam('1.25', '0.7'),
        'X_G2': lambda: raw('1.3', '0.2', ['0.3', '0.45', '0.35+0.1j', '0.25'], ['0.0', '0.1', '-0.05', '0.2'], None),
        'X_C1': lambda: imbalance(rfam('1.7', '0.55+0.3j'), '0.15'),
        # ---- external cross-check against the 50-digit wheel probe review/topmode-numeric (config A1r3)
        'X_TNA1': lambda: mixed('1.3', '0.3+0.05j', ['0.6+0.1j'] * 3, ['0'] * 3),
    }
    if name in CASES:
        return CASES[name]()
    bc = boundary_cases()
    if name in bc:
        return bc[name]
    # ---- (c) controls, generated: CI_<base>_<eps>  (per-factor imbalance, total balance kept)
    if name.startswith('CI_'):
        _, base, eps = name.split('_', 2)
        eps = eps.replace('p', '+').replace('m', '-') if 'j' in eps else eps
        return imbalance(get(base), eps)
    raise KeyError(name)


# outside-(C) / near-boundary points (handled with the analytic continuation of the corner integral)
def boundary_cases():
    return {
        # d=1.3: (C) needs alpha > 0.65.  O1: alpha=0.62 (outside), I1: alpha=0.70 (inside, same shape)
        'O1': mixed('1.3', '0.35', ['0.80', '0.90', '0.96'], ['0.11', '-0.07', '0.23']),
        'I1': mixed('1.3', '0.35', ['0.72', '0.84', '0.94'], ['0.11', '-0.07', '0.23']),
        'O2': mixed('1.3', '0.3+0.15j', ['0.8+0.2j', '0.9-0.1j', '0.96-0.1j'],
                    ['0.1+0.05j', '-0.2', '0.15-0.1j']),
        # R family at continued points (only the outer corner integral diverges there)
        'RC1': rfam('1.25', '0.08j'),            # C63d jet-circle point: Re tau = 0, on the (C) boundary
        'RC2': rfam('1.5', '-0.05+0.07j'),       # outside (C): 2 alpha - d = -0.1
    }
