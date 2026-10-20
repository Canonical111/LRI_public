#!/usr/bin/env python3
"""Fourth epsilon coefficient of the LRI bulk one-point function a_phi2.

Conventions: d is the physical/defect dimension, 0 < d < 4;
 epsilon=2*s-d, Delta_phi=(d-epsilon)/4, <Phi Phi>_0=|X|^(-2 Delta_phi),
 < :Phi^2:(x,y) > = a_phi2/|y|^(2 Delta_phi).
 a_phi2 = a2 epsilon^2 + a3 epsilon^3 + a4 epsilon^4 + O(epsilon^5).
This is not the thermal dimension, not a resummation, and not an error bound.

The new a4 expression was derived in this project by summing the five
four-vertex connected two-point graphs and their MS counterterms. Its RG
input is the corrected three-loop beta function (arXiv:2411.00805), in the
normalization used in the supplied long_range_ising_condensed.tex.

Dependencies: mpmath. For general-d tetrahedron quadrature, also numpy/scipy.
Run: python calculate_a4.py --d 1 2 3 --json results.json
A known tetrahedron value can be supplied for one dimension with --tetra.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import mpmath as mp


def validate_d(value: str | float | mp.mpf) -> mp.mpf:
    d = mp.mpf(str(value))
    if not mp.isfinite(d) or not 0 < d < 4:
        raise ValueError('The fixed-d expansion requires 0 < d < 4.')
    return d


def tetrahedron_mb(d: float, step: float, cutoff: float = 9.0) -> float:
    """Convergent twofold MB quadrature. Double precision, not a certified bound.

    Contours: Re(s)=Re(t)=-q/3, q=d/4. Rows are batched to bound memory.
    The tetrahedron coefficient is alpha_I4 = T_d = 6 Q_d.
    """
    import numpy as np
    from scipy.special import loggamma, gammaln
    if not 0 < d < 4 or step <= 0 or cutoff <= 0:
        raise ValueError('Invalid dimension or quadrature controls.')
    q = d / 4
    n = int(np.ceil(2 * cutoff / step))
    x = np.linspace(-cutoff, cutoff, n + 1)
    step = 2 * cutoff / n
    t = -q/3 + 1j*x[None, :]
    total = 0.0
    for start in range(0, len(x), 64):
        s = -q/3 + 1j*x[start:start+64, None]
        lg = (2*loggamma(-s) + 2*loggamma(-t)
              + loggamma(q+s) + loggamma(q+t)
              + 2*loggamma(q+s+t) + loggamma(-s-t)
              - loggamma(q-s) - loggamma(q-t) - loggamma(2*q+s+t))
        total += float(np.exp(lg).real.sum())
    pref = 2*np.exp(2*gammaln(2*q) - 4*gammaln(q))
    return float(pref * total * step**2 / (2*np.pi)**2)


def tetrahedron(d: mp.mpf) -> tuple[mp.mpf, dict]:
    if d == 1:
        t = 6*mp.gamma(mp.mpf(1)/4)**4/mp.pi
        return t, {'method': 'exact Gamma formula'}
    if d == 2:
        t = (mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4
        return t, {'method': 'exact complex-Selberg Gamma formula'}
    q = float(d)/4
    step = min(0.025, q/30)
    coarse = tetrahedron_mb(float(d), step, 9.0)
    refined = tetrahedron_mb(float(d), step/1.5, 10.0)
    return mp.mpf(str(refined)), {
        'method': 'double-precision convergent twofold Mellin-Barnes quadrature',
        'coarse': coarse, 'refined': refined,
        'observed_difference_not_error_bound': abs(coarse-refined),
        'warning': 'Computational convergence only; no rigorous quadrature error certificate.'}


def coefficients(value, tetra: str | mp.mpf | None = None) -> dict:
    d = validate_d(value); q = d/4
    A = mp.digamma(2*q) - 2*mp.digamma(q) + mp.digamma(1)
    R = mp.polygamma(1, 2*q) - mp.polygamma(1, 1)
    B = mp.pi*mp.cot(mp.pi*q) + 1/q
    S = mp.polygamma(1, 1-q) - mp.polygamma(1, q) + 1/q**2
    K = mp.gamma(1-q)*mp.gamma(2*q)**3/(54*mp.gamma(1+q)*mp.gamma(4*q))
    if tetra is None:
        T, metadata = tetrahedron(d)
    else:
        T = mp.mpf(str(tetra))
        if not mp.isfinite(T):
            raise ValueError('Tetrahedron input must be finite.')
        metadata = {'method': 'user-supplied T_d = alpha_I4 = 6 Q_d'}
    a2 = -K
    a3 = a2*(4*A/3-B/4)
    a4 = a2*(mp.mpf(25)/36*A*A - A*B/3 + (B*B+S)/32 + R/6 - 2*T/27)
    C3 = (A*A+R)/108 - T/81
    alternative = a2*(6*C3+mp.mpf(23)/36*A*A+R/9-A*B/3+(B*B+S)/32)
    assert mp.almosteq(a4, alternative)
    if d == 2:
        a4_exact = 2*T/729-100*mp.log(2)**2/243+8*mp.log(2)/81-mp.mpf(1)/108
        assert mp.almosteq(a4, a4_exact)
    return {'d': d, 'q': q, 'A': A, 'R': R, 'B': B, 'S': S, 'K': K,
            'T': T, 'Q': T/6, 'a2': a2, 'a3': a3, 'a4': a4,
            'C3_for_algebraic_check': C3, 'tetrahedron_metadata': metadata}


def serialize(row: dict) -> dict:
    return {key: mp.nstr(value, 40) if isinstance(value, mp.mpf) else value
            for key, value in row.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--d', nargs='+', default=['1','2','3'])
    parser.add_argument('--tetra', help='Optional T_d for exactly one --d value.')
    parser.add_argument('--dps', type=int, default=80)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    if args.tetra is not None and len(args.d) != 1:
        parser.error('--tetra requires exactly one dimension.')
    if args.dps < 30:
        parser.error('--dps must be at least 30.')
    mp.mp.dps = args.dps
    rows = [coefficients(d, args.tetra) for d in args.d]
    for row in rows:
        print('d =', row['d'])
        for key in ('a2','a3','a4'):
            print(' ', key, '=', mp.nstr(row[key], 25))
        print('  T_d input:', row['tetrahedron_metadata'])
    examples = []
    for row in rows:
        if row['d'] == 2:
            e = mp.mpf('0.3')
        elif row['d'] == 3:
            e = mp.mpf('0.18548')
        else:
            continue
        previous = row['a2']*e**2+row['a3']*e**3
        delta = row['a4']*e**4
        examples.append({'d':str(row['d']), 'epsilon':str(e),
            'through_epsilon3':mp.nstr(previous,25),
            'quartic_term':mp.nstr(delta,25),
            'through_epsilon4':mp.nstr(previous+delta,25),
            'warning':'Truncations, not uncertainty intervals.'})
    result = {'scope':'New diagrammatic a4 calculation; not externally published validation; fixed 0<d<4, small epsilon.',
              'formula':'a4 = -K*(25*A^2/36 - A*B/3 + (B^2+S)/32 + R/6 - 2*T/27)',
              'normalization':'<:Phi^2:> = a_phi2 / |y|^(2 Delta_phi)',
              'rows':[serialize(row) for row in rows],
              'finite_epsilon_truncations':examples}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('Saved', args.json)

if __name__ == '__main__':
    main()
