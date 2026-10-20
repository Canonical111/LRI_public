#!/usr/bin/env python3
"""Regenerate and cross-check exact analytic d=3 inputs through order eight.

Formula sources: attached long_range_ising_condensed.tex, equations
gd:twoLoopHyperDefs, gd:twoLoopHyper, d3six:twoLoop, d3six:GammaJets,
and d3six:norm.  The two-loop Cauchy extraction uses two radii and node
counts.  Gamma logarithmic jets use independent Cauchy evaluation of the
analytic log-Gamma product.  No sampled data or known C_n is an input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]


def generate(output_root=ROOT, *, order=8, dps=80, reference=None):
    if order < 3 or order > 8:
        raise ValueError('Validated generation supports orders 3 through 8')
    if dps < 65:
        raise ValueError('At least 65 decimal working digits are required')
    started = time.monotonic()
    mp.mp.dps = dps
    q = mp.mpf(3)/4
    def decimal(x):
        return mp.nstr(x, dps-5)
    def numerator(z):
        a, b = q+z/4, q+3*z/4
        f1 = mp.hyper([2*q, z/2, a], [1-z/2, a+mp.mpf('.5')], mp.mpf('.25'))
        f2 = mp.hyper([z, 2*a, b], [1+z/2, b+mp.mpf('.5')], mp.mpf('.25'))
        r = mp.gamma(2*q+z/2)/mp.gamma(1+z/2)
        w = r*r*mp.gamma(1+z)*mp.gamma(1-z/2)*mp.gamma(b)**2/(mp.gamma(a)**2*mp.gamma(2*q)*mp.gamma(2*b))
        return 4*f1-2*w*f2
    records = []
    for radius, nodes in (('0.04', 80), ('0.07', 96)):
        rad = mp.mpf(radius)
        angles = [2*mp.pi*(j+mp.mpf('.5'))/nodes for j in range(nodes//2)]
        values = [numerator(rad*mp.exp(1j*theta)) for theta in angles]
        # b2[j]=-6 [z^(j+1)](4 F1-2 W F2); reflection halves the node count.
        jets = [-12*mp.fsum(mp.re(v*mp.exp(-1j*theta*k)) for theta, v in zip(angles, values))/(nodes*rad**k)
                for k in range(1, order)]
        records.append({'radius': radius, 'nodes': nodes, 'B2': list(map(decimal, jets))})
    low_discrepancy = max(abs(mp.mpf(x)-mp.mpf(y)) for x, y in zip(records[0]['B2'], records[1]['B2']))
    tolerance = mp.mpf('1e-50')
    if low_discrepancy >= tolerance:
        raise ArithmeticError(f'Two-loop independent Cauchy evaluations disagree: {low_discrepancy}')
    overlap = None
    if reference is not None:
        reference = Path(reference)
        raw = reference.read_bytes()
        old = json.loads(raw)
        old_values = old.get('B2', old.get('B2_decimal'))
        if old.get('dimension', old.get('d', 3)) != 3 or not old_values:
            raise ValueError('Invalid old d=3 two-loop reference')
        delta = max(abs(mp.mpf(x)-mp.mpf(y)) for x, y in zip(old_values, records[-1]['B2']))
        if delta >= tolerance:
            raise ArithmeticError(f'C7 overlap differs: {delta}')
        overlap = {'filename': reference.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                   'checked_slots': min(len(old_values), order-1), 'max_abs_difference': decimal(delta)}
    rows, gamma_errors, gamma_text = [], [], []
    radius, nodes = mp.mpf('.031'), 112
    angles = [2*mp.pi*j/nodes for j in range(nodes)]
    for loop in range(2, order+1):
        norm = 2*(-1)**(loop+1)*mp.gamma(2*q)**loop/mp.gamma(q)**(2*loop)
        logs = [mp.mpf(0)]+[(loop*mp.polygamma(j-1, 2*q)/2**j+
                  ((mp.mpf(loop)/2)**j-mp.mpf(loop)/2**j)*mp.polygamma(j-1, 1)-
                  2*loop*mp.polygamma(j-1, q)/4**j)/mp.factorial(j)
                 for j in range(1, order-1)]
        def log_gamma_product(z):
            return loop*(mp.loggamma(2*q+z/2)-mp.loggamma(1+z/2)-mp.loggamma(2*q)) + mp.loggamma(1+loop*z/2) - 2*loop*(mp.loggamma(q+z/4)-mp.loggamma(q))
        values = [log_gamma_product(radius*mp.exp(1j*theta)) for theta in angles]
        for j in range(1, order-1):
            estimated = mp.fsum(value*mp.exp(-1j*j*theta) for theta, value in zip(angles, values))/(nodes*radius**j)
            error = abs(estimated-logs[j])
            if error >= tolerance:
                raise ArithmeticError(f'Gamma Cauchy mismatch at L={loop}, j={j}: {error}')
            gamma_errors.append(decimal(error))
        rows.append({'L': loop, 'max_jet': order-loop, 'norm': decimal(norm), 'log_jets': list(map(decimal, logs))})
        gamma_text.append(' '.join([str(order-loop), decimal(norm)]+list(map(decimal, logs))))
    output_root = Path(output_root)
    inputs, verification = output_root/'inputs', output_root/'verification'
    inputs.mkdir(parents=True, exist_ok=True)
    verification.mkdir(parents=True, exist_ok=True)
    low_input = {'schema': 'lri-d3-two-loop-jets-1', 'dimension': 3, 'order': order,
                 'B2': records[-1]['B2'], 'mass_jet_relation': 'c_hat_2[j] = b_hat_2[j]/6',
                 'normalization': 'finite zero-momentum scheme, epsilon=2s-3'}
    (inputs/'two_loop.json').write_text(json.dumps(low_input, indent=2)+'\n')
    (inputs/f'gamma_d3_{order}.txt').write_text('\n'.join(gamma_text)+'\n')
    gamma_report = {'dimension': 3, 'order': order, 'dps': dps, 'rows': rows,
                    'cauchy_radius': str(radius), 'cauchy_nodes': nodes,
                    'checked_jets': len(gamma_errors), 'max_abs_difference': decimal(max(map(mp.mpf, gamma_errors)))}
    (verification/'gamma_jets.json').write_text(json.dumps(gamma_report, indent=2)+'\n')
    report = {'status': 'passed', 'dimension': 3, 'order': order, 'dps': dps,
              'two_loop_records': records, 'two_loop_max_abs_difference': decimal(low_discrepancy),
              'original_C7_overlap': overlap, 'gamma_checked_jets': len(gamma_errors),
              'gamma_max_abs_difference': gamma_report['max_abs_difference'],
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'seconds': time.monotonic()-started}
    (verification/'analytic_inputs.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=ROOT)
    parser.add_argument('--order', type=int, default=8)
    parser.add_argument('--dps', type=int, default=80)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    report = generate(args.output_root, order=args.order, dps=args.dps, reference=args.reference)
    print(json.dumps({key: value for key, value in report.items() if key != 'two_loop_records'}, indent=2))


if __name__ == '__main__':
    main()
