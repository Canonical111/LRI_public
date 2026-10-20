#!/usr/bin/env python3
"""Independent diagrammatic check of the LRI bulk one-point coefficient.

Dependencies: Python >= 3.10 and mpmath.
Run: python check_a_phi2.py --json results.json

Conventions:
  d = physical LRI/defect dimension (p in Behan et al.).
  epsilon = 2*s - d; Delta = (d - epsilon)/4.
  <Phi(X)Phi(0)>_free = |X|^(-2*Delta).
  S_int = lambda_B/4! * integral phi^4.
  < :Phi^2:(X) > = a_phi2 / |y|^(2*Delta).
The unit-normalized bulk composite :Phi^2:/sqrt(2) instead has coefficient
 a_phi2/sqrt(2).

This computes only the epsilon^2 and epsilon^3 coefficients. It is not a
finite-epsilon resummation, a bootstrap run, or a certified remainder estimate.

The diagrammatic calculation uses the standard two-loop quartic beta function.
Reference for that RG input: Giombi & Khanchandani, arXiv:1912.08169, Sec. 5.1,
translated to unit position-space propagator and lambda/4! conventions.
Comparison target: Behan et al., arXiv:2311.02742v6, Eqs. (2.11), (3.25),
(3.34)-(3.36), (3.47), and Appendix B.4.2.

https://arxiv.org/html/1912.08169
https://arxiv.org/html/2311.02742v6
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mpmath as mp


def dimension(value: str | int | mp.mpf) -> mp.mpf:
    d = mp.mpf(value)
    if not mp.isfinite(d) or not 0 < d < 4:
        raise ValueError("The fixed-d expansion requires 0 < d < 4.")
    return d


def kappa(d: mp.mpf) -> mp.mpf:
    return mp.pi ** (d / 2) / mp.gamma(d / 2)


def A(d: mp.mpf) -> mp.mpf:
    return mp.digamma(d / 2) - 2 * mp.digamma(d / 4) + mp.digamma(1)


def coefficients(value: str | int | mp.mpf) -> tuple[mp.mpf, mp.mpf]:
    """Return a2, a3 in a_phi2 = a2*epsilon^2 + a3*epsilon^3 + O(epsilon^4)."""
    d = dimension(value)
    K = (mp.gamma(1 - d / 4) * mp.gamma(d / 2) ** 3
         / (54 * mp.gamma(1 + d / 4) * mp.gamma(d)))
    T = mp.mpf(4) / 3 * A(d) - mp.pi / 4 * mp.cot(mp.pi * d / 4) - 1 / d
    return -K, -K * T


def J(d: mp.mpf, alpha: mp.mpf, b: mp.mpf) -> mp.mpf:
    """Analytically continued two-vertex bulk-coincidence integral, |y|=1.

    J = integral du dv [(1+u^2)(1+v^2)]^(-alpha) |u-v|^(-2*b).
    At physical exponents it means the critical-mass-subtracted continuation,
    NOT an unsubtracted integral of a positive function.
    """
    return (mp.pi ** d * mp.gamma(d / 2 - b)
            * mp.gamma(2 * alpha + b - d)
            * mp.gamma(alpha + b - d / 2) ** 2
            / (mp.gamma(alpha) ** 2 * mp.gamma(d / 2)
               * mp.gamma(2 * alpha + 2 * b - d)))


def bubble(d: mp.mpf, e: mp.mpf) -> mp.mpf:
    """Coefficient of the convolution of two doubled defect propagators."""
    return (mp.pi ** (d / 2) * mp.gamma(e / 2) ** 2
            * mp.gamma(d / 2 - e)
            / (mp.gamma((d - e) / 2) ** 2 * mp.gamma(e)))


def diagrams_at_fixed_point(value: str | int | mp.mpf, e: mp.mpf) -> mp.mpf:
    """Renormalized two-/three-vertex diagrams, retaining enough for a2 and a3.

    lambda_B = mu^e [lambda + 3*kappa*lambda^2/e + ...].
    Set mu*|y|=1. The 1/e poles cancel in the square bracket before the
    fixed point is substituted. O(lambda^4) terms are NOT included.
    """
    d = dimension(value)
    delta = (d - e) / 4
    I2 = J(d, delta, 3 * delta)
    I3 = J(d, delta, 5 * delta - d / 2)
    kap = kappa(d)
    lam = e / (3 * kap) + 2 * A(d) * e ** 2 / (9 * kap)
    return lam ** 2 * I2 / 6 + lam ** 3 * (kap * I2 / e - bubble(d, e) * I3 / 4)


def paper_R(value: str | int | mp.mpf) -> tuple[mp.mpf, mp.mpf]:
    """r1 and r2 from Eqs. (3.25), (3.34); used ONLY for an algebraic check."""
    d = dimension(value)
    r1 = (mp.gamma(1 - d / 4) * mp.gamma(d / 2)
          / (3 * mp.sqrt(6) * mp.gamma(1 + d / 4)))
    r2 = -r1 / 12 * (13 * mp.digamma(d / 4) + 3 * mp.digamma(-d / 4)
                     - 8 * mp.digamma(d / 2) - 8 * mp.digamma(1))
    return r1, r2


def coefficients_from_R(value: str | int | mp.mpf) -> tuple[mp.mpf, mp.mpf]:
    """Expand the exact bulk-defect relation with the paper's R coefficients."""
    d = dimension(value)
    r1, r2 = paper_R(d)
    F0 = mp.gamma(d / 2) * mp.gamma(d / 4) / (mp.gamma(d) * mp.gamma(-d / 4))
    Flog1 = (mp.digamma(-d / 4) - mp.digamma(d / 4)) / 4
    return F0 * r1 ** 2, F0 * (2 * r1 * r2 + Flog1 * r1 ** 2)


def printed_335_a3(value: str | int | mp.mpf) -> mp.mpf:
    """Literal Eq. (3.35) v6, NOT the corrected/verified coefficient.

    This function is intentionally kept to demonstrate its inconsistency
    with the same paper's Eq. (3.36). It has a pole at d=2.
    """
    d = dimension(value)
    if d == 2:
        raise ValueError("Printed Eq. (3.35) has an uncancelled pole at d=2.")
    _, r2 = paper_R(d)
    prefactor = (-mp.gamma(d / 2) ** 3 * mp.gamma(1 - d / 2)
                 * mp.gamma(1 - d / 4)
                 / (216 * mp.gamma(1 + d / 4) * mp.gamma(d + 1)))
    bracket = (4 - mp.gamma(d / 4) ** 2 * mp.gamma(1 - d / 4) ** 2
               / (mp.gamma(d / 2) * mp.gamma(-d / 2))
               - 96 * mp.sqrt(6) * mp.gamma(1 + d / 4) * r2
               / (mp.gamma(-d / 4) * mp.gamma(d / 2)))
    return prefactor * bracket


def run_checks() -> dict:
    mp.mp.dps = 100
    tight = mp.mpf('1e-80')
    h = mp.mpf('1e-25')
    rows = []
    for ds in ('1', '1.7', '2', '2.6', '3', '3.8'):
        d = dimension(ds)
        a2, a3 = coefficients(d)
        r_a2, r_a3 = coefficients_from_R(d)
        assert abs(a2 - r_a2) < tight
        assert abs(a3 - r_a3) < tight
        a3_from_diagrams = (diagrams_at_fixed_point(d, h) / h ** 2 - a2) / h
        assert abs(a3_from_diagrams - a3) < mp.mpf('1e-20')
        I0 = J(d, d / 4, 3 * d / 4)
        independent_a2 = I0 / (54 * kappa(d) ** 2)
        assert abs(independent_a2 - a2) < tight
        rows.append({'d': ds, 'a2': mp.nstr(a2, 40), 'a3': mp.nstr(a3, 40),
                     'a3_from_subtracted_diagrams': mp.nstr(a3_from_diagrams, 30),
                     'diagram_limit_absolute_error': mp.nstr(abs(a3_from_diagrams - a3), 8)})

    # A convergent integral normalization test: J_1(1,1/4)=pi^2.
    assert abs(J(mp.mpf(1), mp.mpf(1), mp.mpf(1)/4) - mp.pi ** 2) < tight

    # The explicit d=2,3 expressions in Eq. (3.36).
    a2_2 = -mp.mpf(1)/27
    a3_2 = mp.mpf(1)/54 - 8*mp.log(4)/81
    a2_3 = -mp.pi ** (mp.mpf(5)/2)/(576*mp.sqrt(2)*mp.gamma(mp.mpf(7)/4)**2)
    a3_3 = (4*mp.sqrt(2*mp.pi)/6075 * (13*mp.pi-28-64*mp.log(2))
            * mp.gamma(mp.mpf(9)/4)**2)
    for ds, expected in [('2', (a2_2, a3_2)), ('3', (a2_3, a3_3))]:
        found = coefficients(ds)
        assert all(abs(x-y) < tight for x,y in zip(found, expected))

    examples = []
    for ds, es in [('2', '0.3'), ('3', '0.18548')]:
        a2, a3 = coefficients(ds)
        e = mp.mpf(es)
        examples.append({'d': ds, 'epsilon': es,
                         'a_through_epsilon2': mp.nstr(a2*e**2, 30),
                         'a_through_epsilon3': mp.nstr(a2*e**2+a3*e**3, 30),
                         'cubic_to_quadratic_ratio': mp.nstr(a3/a2*e, 20)})

    return {'convention': '<:Phi^2:(X)> = a_phi2 / |y|^(2 Delta)',
            'scope': 'Fixed 0<d<4, weak-coupling expansion through epsilon^3; no remainder bound.',
            'coefficient_formula': 'a2=-K; a3=-K*T; K=Gamma(1-d/4)*Gamma(d/2)^3/[54*Gamma(1+d/4)*Gamma(d)]; T=4/3*(psi(d/2)-2*psi(d/4)+psi(1))-pi/4*cot(pi*d/4)-1/d',
            'precision_decimal_digits': mp.mp.dps,
            'checks': 'Passed: gamma integral normalization, leading diagram, subtracted cubic diagrams, exact R conversion, explicit Eq. (3.36).',
            'rows': rows, 'finite_epsilon_truncations_not_error_controlled': examples,
            'printed_formula_diagnostic': {'literal_335_a3_at_d3': mp.nstr(printed_335_a3('3'),40),
                                           'verified_a3_at_d3': mp.nstr(a3_3,40),
                                           'literal_347_a2_at_d2_N1': '+1/27',
                                           'verified_a2_at_d2_N1': '-1/27'}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', type=Path, help='Optional JSON output path.')
    args = parser.parse_args()
    result = run_checks()
    print(result['checks'])
    for row in result['rows']:
        print(f"d={row['d']:>3}  a2={row['a2']}  a3={row['a3']}")
    print('\nPrinted-formula diagnostics:')
    print(json.dumps(result['printed_formula_diagnostic'], indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f'Wrote {args.json}')


if __name__ == '__main__':
    main()
