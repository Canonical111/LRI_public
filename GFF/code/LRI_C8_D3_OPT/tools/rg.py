#!/usr/bin/env python3
"""Order-general finite-scheme RG assembly for the long-range Ising model.

All regulator jets are retained before z = epsilon is substituted.  The
normalization is b_1 = 3, c_1 = 1 and epsilon = 2s - d.  In particular,
C_8(3) contains (3*c[8,0] - b[8,0])/19683.

The numerical public interface uses vectors
    vals[L] = [b[L,0], ..., b[L,N-L], c[L,0], ..., c[L,N-L]].
Missing loop orders are errors by default; partial algebra requires the
explicit require_complete=False switch and is not a physical coefficient.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import json
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def multiply(a, b, length):
    """Truncated product, preserving Fraction or symbolic scalar arithmetic."""
    z = a[0] * b[0] * 0
    out = [z for _ in range(length)]
    for i, x in enumerate(a[:length]):
        if x == 0:
            continue
        for j, y in enumerate(b[:length-i]):
            if y != 0:
                out[i+j] += x*y
    return out


def fixed_point_series(b, c, order=8, dimension=3):
    """Return C_0,...,C_order from explicit per-loop beta and mass jets.

    This low-level routine accepts exact rational inputs and allows missing
    higher loops as zero for algebraic checks.  Use ``coefficients`` for
    checked physical input.  Nine iterations suffice at order eight because
    the nonlinear fixed-point map raises the error's epsilon order.
    """
    if not isinstance(order, int) or order < 1:
        raise ValueError('order must be a positive integer')
    if list(b.get(1, ())) != [3] or list(c.get(1, ())) != [1]:
        raise ValueError('This normalization requires b1=3 and c1=1 exactly')
    length = order+1
    # Fraction(1,3) prevents accidental floating division for exact inputs.
    third = Fraction(1, 3)
    g = [Fraction(0)] * length
    epsilon = g.copy()
    epsilon[1] = Fraction(1)
    for _ in range(length):
        power = g.copy()
        nonlinear = [Fraction(0)] * length
        for loop in range(2, order+1):
            power = multiply(power, g, length)
            term = multiply(b.get(loop, [Fraction(0)]), power, length)
            nonlinear = [x+y for x, y in zip(nonlinear, term)]
        g = [(x-y)*third for x, y in zip(epsilon, nonlinear)]
    gamma = [Fraction(0)] * length
    power = [Fraction(1)] + [Fraction(0)]*order
    for loop in range(1, order+1):
        power = multiply(power, g, length)
        term = multiply(c.get(loop, [Fraction(0)]), power, length)
        gamma = [x+y for x, y in zip(gamma, term)]
    gamma[0] += Fraction(dimension, 2)
    gamma[1] -= Fraction(1, 2)
    return gamma


def load_two_loop(path=None, order=8, dimension=3):
    source = Path(path) if path else ROOT/'inputs'/'two_loop.json'
    data = json.loads(source.read_text())
    if data.get('dimension') != dimension or data.get('order', 0) < order:
        raise ValueError('Two-loop data have wrong dimension or insufficient jet order')
    values = np.asarray(data['B2'], dtype=float)
    if values.shape[0] < order-1 or not np.isfinite(values).all():
        raise ValueError('Invalid or incomplete two-loop jets')
    return values[:order-1]


def coefficients(vals, B2=None, *, order=8, dimension=3, require_complete=True):
    """Numerical physical coefficient vector; both sectors must first be added.

    Compute a power-sector correction as coefficients(f+p)-coefficients(f),
    including the nonlinear lower-loop changes.  Do not sum top-loop power
    graphs alone.  The complex dtype is preserved for Jacobian evaluation.
    """
    if not isinstance(order, int) or order < 2:
        raise ValueError('Numerical assembly requires order >= 2')
    if dimension != 3:
        raise ValueError('This package supplies analytic low inputs only for d=3')
    if set(vals)-set(range(3, order+1)):
        raise ValueError('Unexpected loop order in supplied jets')
    if require_complete and set(vals) != set(range(3, order+1)):
        missing = sorted(set(range(3, order+1))-set(vals))
        raise ValueError(f'Missing loop inputs {missing}; result would be incomplete')
    low = load_two_loop(order=order, dimension=dimension) if B2 is None else np.asarray(
        B2, dtype=complex if np.iscomplexobj(B2) else float)
    if low.ndim != 1 or len(low) < order-1 or not np.isfinite(low).all():
        raise ValueError(f'Two-loop input requires at least {order-1} finite Taylor slots')
    dtype = np.result_type(low, *[np.asarray(x) for x in vals.values()], float)
    b = {1: np.array([3], dtype=dtype), 2: np.asarray(low[:order-1], dtype=dtype)}
    c = {1: np.array([1], dtype=dtype), 2: b[2]/6}
    for loop, value in vals.items():
        value = np.asarray(value, dtype=dtype)
        slots = order-loop+1
        if value.shape != (2*slots,) or not np.isfinite(value).all():
            raise ValueError(f'L={loop} requires exactly {2*slots} finite b/c jet entries')
        b[loop], c[loop] = value[:slots], value[slots:]
    length = order+1
    def mul(x, y):
        return np.convolve(x, y)[:length]
    g = np.zeros(length, dtype=dtype)
    epsilon = g.copy()
    epsilon[1] = 1
    for _ in range(length):
        power = g.copy()
        nonlinear = np.zeros(length, dtype=dtype)
        for loop in range(2, order+1):
            power = mul(power, g)
            nonlinear += mul(b.get(loop, np.zeros(1, dtype=dtype)), power)
        g = (epsilon-nonlinear)/3
    gamma = np.zeros(length, dtype=dtype)
    power = gamma.copy()
    power[0] = 1
    for loop in range(1, order+1):
        power = mul(power, g)
        gamma += mul(c.get(loop, np.zeros(1, dtype=dtype)), power)
    gamma[0] += dimension/2
    gamma[1] -= .5
    return gamma


def jacobians(means, B2=None, *, order=8, dimension=3, require_complete=True):
    """Complex-step Jacobians of all physical coefficients in each loop vector."""
    out = {}
    for loop, value in means.items():
        columns = []
        for j in range(len(value)):
            shifted = {k: np.asarray(v, dtype=complex).copy() for k, v in means.items()}
            shifted[loop][j] += 1e-20j
            columns.append(coefficients(shifted, B2, order=order, dimension=dimension,
                                        require_complete=require_complete).imag/1e-20)
        out[loop] = np.asarray(columns).T
    return out


def top_loop_weights(order=8):
    """Exact coefficients of b[order,0] and c[order,0]."""
    return -Fraction(1, 3**(order+1)), Fraction(1, 3**order)


def high_loop_affine(low_means, B2=None, *, order=8, first_high_loop=5):
    """Return an exact-in-the-high-inputs affine representation C=K+sum J_L v_L.

    The low numerical jets are held fixed.  Two high-loop insertions can
    first contribute at order 2*first_high_loop-1; the map is affine only
    strictly below that order.  For C8, loops five through eight qualify.
    This routine is an algebraic decomposition and never fills missing
    physical high-loop data with estimated values.
    """
    if order >= 2*first_high_loop-1:
        raise ValueError('High-loop inputs have nonlinear cross terms at this order')
    if set(low_means) != set(range(3, first_high_loop)):
        raise ValueError('Supply every low loop from 3 to first_high_loop-1')
    means = {k: np.asarray(v).copy() for k, v in low_means.items()}
    for loop in range(first_high_loop, order+1):
        means[loop] = np.zeros(2*(order-loop+1))
    constant = coefficients(means, B2, order=order)
    all_jacobians = jacobians(means, B2, order=order)
    return constant, {k: all_jacobians[k] for k in range(first_high_loop, order+1)}


if __name__ == '__main__':
    print(json.dumps({'dimension': 3, 'order': 8, 'epsilon': '2s-3',
                      'required_jet_orders': {str(k): 8-k for k in range(2, 9)},
                      'dC8_db80': str(top_loop_weights()[0]),
                      'dC8_dc80': str(top_loop_weights()[1])}, indent=2))
