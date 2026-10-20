#!/usr/bin/env python3
"""Further simplifications of the Ising primitive period P5.

A positive Gamma-function moment, a second parameter derivative of one 9F8(-1),
and an alternating binomial/harmonic series all evaluate the same period.
No saved period is used as an input. The old elliptic and sixth-derivative
representations are implemented independently as optional controls.

  python evaluate_P5_further.py --digits 60 --verify --output P5_checks.json

mpmath is the only required dependency. Numerical control comparisons are not
rigorous error bounds, and this program does not check the complete C5.
"""
from __future__ import annotations
import argparse
import json
import math
import time
from pathlib import Path
import mpmath as mp


def _validate_digits(digits: int) -> None:
    if not isinstance(digits, int) or digits < 15:
        raise ValueError('digits must be an integer >= 15')


def p5_gamma(digits: int = 50, guard: int = 20):
    """Smooth, positive, exponentially decaying one-dimensional quadrature."""
    _validate_digits(digits)
    if guard < 10:
        raise ValueError('guard must be >= 10')
    with mp.workdps(digits + guard):
        def f(x):
            if x == 0:
                return mp.mpf(0)
            lg = 14 * mp.re(mp.loggamma(mp.mpf(1)/4 + 1j*x))
            terms = [c*mp.exp(lg+a*mp.pi*x)*(-mp.expm1(-2*a*mp.pi*x))/2
                     for a, c in ((6, 1), (4, 13), (2, 29))]
            return x*mp.fsum(terms)
        return mp.quad(f, [0, mp.mpf(1)/4, 1, 3, 10, mp.inf])/mp.pi**(mp.mpf(11)/2)


def h(t):
    """All seven repeated parameters retain their t dependence."""
    return mp.hyper([1, mp.mpf(5)/4+t]+[mp.mpf(1)/2+t]*7,
                    [mp.mpf(1)/4+t]+[1+t]*7, -1)


def phi(t):
    return (1+4*t)*(mp.gamma(mp.mpf(1)/2+t)/
                       (mp.sqrt(mp.pi)*mp.gamma(1+t)))**7*h(t)


def _cauchy_coefficients(function, degrees, radius, nodes):
    if nodes < 16 or nodes % 2:
        raise ValueError('nodes must be an even integer >= 16')
    if max(degrees) >= nodes:
        raise ValueError('coefficient degree must be smaller than node count')
    r = mp.mpf(radius)
    if not (0 < r < mp.mpf('0.1')):
        raise ValueError('radius must be between 0 and 0.1')
    sums = {k: [] for k in degrees}
    for j in range(nodes//2 + 1):
        angle = 2*mp.pi*j/nodes
        value = function(r*mp.exp(1j*angle))
        multiplicity = 1 if j in (0, nodes//2) else 2
        for k in degrees:
            sums[k].append(multiplicity*mp.re(value*mp.exp(-1j*k*angle)))
    return {k: mp.fsum(sums[k])/(nodes*r**k) for k in degrees}


def p5_second_derivative(digits: int = 50, nodes: int | None = None,
                         radius: str = '0.02'):
    """Cauchy evaluation of the new zeroth, first and second coefficients."""
    _validate_digits(digits)
    nodes = nodes or 2*math.ceil((digits+20)/2)
    with mp.workdps(digits+25):
        c = _cauchy_coefficients(phi, (0, 1, 2), radius, nodes)
        return mp.pi**3*(22*c[2]-26*mp.pi*c[1]+3*mp.pi**2*c[0])


def p5_euler_series(digits: int = 50, terms: int | None = None):
    """Euler acceleration of the explicitly differentiated harmonic series."""
    _validate_digits(digits)
    terms = terms or math.ceil(3.5*(digits+20))
    if terms < 16:
        raise ValueError('terms must be >= 16')
    with mp.workdps(digits+30):
        coeff = mp.mpf(1)
        d = -2*mp.log(2)
        e = mp.pi**2/3
        values = []
        for n in range(terms):
            values.append(coeff*((4*n+1)*(539*d*d+77*e-182*mp.pi*d+3*mp.pi**2)
                                       +616*d-104*mp.pi))
            nh, n1 = mp.mpf(n)+mp.mpf(1)/2, mp.mpf(n)+1
            d += 1/nh - 1/n1
            e += -1/nh**2 + 1/n1**2
            coeff *= (nh/n1)**7
        transformed = []
        for k in range(terms):
            transformed.append(values[0]/mp.mpf(2)**(k+1))
            values = [values[j]-values[j+1] for j in range(len(values)-1)]
        return mp.pi**3*mp.fsum(transformed)


def p5_old_sixth_derivative(digits: int = 50):
    """Previous representation, with its different Gamma prefactor."""
    _validate_digits(digits)
    with mp.workdps(digits+30):
        def old(t):
            rho = mp.sqrt(mp.pi)*mp.gamma(1-t/2)*mp.gamma(mp.mpf(1)/4+t/2)
            rho /= mp.gamma(mp.mpf(1)/4-t/2)*mp.gamma(mp.mpf(1)/2+t/2)
            return (1+4*t)*mp.tan(mp.pi/4+mp.pi*t)*rho**7*h(t)
        nodes = 2*math.ceil((digits+30)/2)
        c = _cauchy_coefficients(old, (6,), '0.02', nodes)
        return -8*c[6]/mp.pi


def p5_old_elliptic(digits: int = 50):
    """The previous positive elliptic integral; AGM avoids endpoint loss."""
    _validate_digits(digits)
    with mp.workdps(digits+20):
        def psi(m, mc):
            k = mp.pi/(2*mp.agm(1, mp.sqrt(mc)))
            kc = mp.pi/(2*mp.agm(1, mp.sqrt(m)))
            return (k+kc)*(2*k+kc)
        def f(x):
            if x == 0 or x == 1:
                return mp.mpf(0)
            xx = x*x
            a = mp.pi/mp.agm(1, mp.sqrt((1-x)*(1+x)*(1+xx)))
            a += mp.pi/(2*mp.agm(1, xx))
            b = 2*x*psi(xx, (1-x)*(1+x))
            b += (1+x)**2/(1+xx)*psi(xx/(1+xx), 1/(1+xx))
            return 64*a*b
        return mp.quad(f, [0, mp.mpf(1)/4, mp.mpf(1)/2, mp.mpf(3)/4, 1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digits', type=int, default=50)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('P5_checks.json'))
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        main_value = p5_gamma(args.digits)
        higher_value = p5_gamma(args.digits, guard=30)
        with mp.workdps(args.digits+35):
            out = {'P5_gamma': mp.nstr(main_value, args.digits),
                   'P5_gamma_higher_precision': mp.nstr(higher_value, args.digits),
                   'gamma_precision_difference': mp.nstr(higher_value-main_value, 15)}
        if args.verify:
            controls = {'second_parameter_derivative': p5_second_derivative(args.digits),
                        'Euler_accelerated_harmonic_series': p5_euler_series(args.digits),
                        'previous_elliptic_integral': p5_old_elliptic(args.digits),
                        'previous_sixth_parameter_derivative': p5_old_sixth_derivative(args.digits)}
            with mp.workdps(args.digits+35):
                out['control_values'] = {k: mp.nstr(v, args.digits) for k,v in controls.items()}
                out['control_minus_gamma'] = {k: mp.nstr(v-higher_value, 20) for k,v in controls.items()}
        out.update(requested_digits=args.digits, saved_period_values_used=False,
                   rigorous_error_enclosure=False,
                   scope='Comparison of representations of the primitive period P5, not full C5 validation.',
                   mpmath_version=mp.__version__, elapsed_seconds=time.perf_counter()-started)
    except (ValueError, ZeroDivisionError) as exc:
        parser.exit(2, f'Evaluation failed: {exc}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
