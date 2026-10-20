"""Re-evaluate the three residuals using the supplied, error-bounded evaluators.

The primitive is evaluated through the retained geometric recurrence; its new
Chebyshev sum is obtained from the exact normalization Pa/(8*pi**3). This does
not claim a new finite special-value evaluation or upstream graph verification.
"""
from pathlib import Path
from fractions import Fraction
import importlib.util
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'work'
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)
sys.path.insert(0, str(WORK / 'C6_complete_interval'))
sys.path.insert(1, str(WORK / 'C6_central_binomial_wheel'))
import dyadic
from dyadic import I
from elementary import Constants
import primitive

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

wheel = module('wheel_certificate', WORK / 'C6_central_binomial_wheel/certify.py')
seventh = module('seventh_certificate', WORK / 'C6_central_seventh_reduction/certify.py')

def unpack(record):
    if 'denominator_power_of_two' in record:
        den = 1 << record['denominator_power_of_two']
        return I.bounds(Fraction(int(record['lower_numerator']), den),
                        Fraction(int(record['upper_numerator']), den))
    def frac(o):
        return Fraction(int(o['numerator']), int(o['denominator']))
    return I.bounds(frac(record['lower']), frac(record['upper']))

def overlap(x, y):
    return x.lower() <= y.upper() and y.lower() <= x.upper()

def main():
    started = time.time()
    dyadic.set_precision(1280)
    const = Constants(euler_N=1000, gamma_shift=256, gamma_M=96)
    env = const.environment()
    p = env['pi']
    print('Initial constants independently enclosed.', flush=True)

    # Exact-rational wheel approximant and its explicit omitted-tail bound.
    comp = wheel.approximant(256, 40)
    err = wheel.tail_bound(40, 256)
    raw = wheel.interval_for(comp, (p.lower(), p.upper()))
    Wcentral = I.bounds(raw[0] - err, raw[1] + err)
    Wzero = Wcentral + (8 + 5*p)*p**2/3
    Rwheel = -393*p**3*Wzero
    print('Wheel recomputed; interval width =', float(Wcentral.width()), flush=True)

    # Fresh Euler approximant of the current cubic-harmonic seventh series.
    M7, m7info = seventh.compute(600, p, env['ell'], env['z3'])
    print('Seventh recomputed; interval width =', float(M7.width()), flush=True)

    # Fresh geometric primitive recurrence with its last-two-state tail bound.
    source = json.loads((WORK / 'C6_complete_interval/inputs/expression.json').read_text())
    obj = next(v for v in source['single_index_recurrence_series_terms'] if v['id'] == 'Pa')
    seed_checks = primitive.exact_seed_checks(obj)
    Pa, painfo = primitive.compute(obj, env, N=200)
    Pspectral = Pa/(8*p**3)
    Pcubic = Pa/(2*p**2)
    print('Primitive recomputed; interval width =', float(Pa.width()), flush=True)

    residual_r6 = {'wheel': Rwheel, 'seventh': 24*p**3*M7, 'primitive': 96*Pa}
    residual_C6 = {k: v/2187 for k,v in residual_r6.items()}
    sum_resid = sum(residual_C6.values(), I(0))
    values = {'Wcentral_n_ge_1': Wcentral, 'Wzero_n_ge_0': Wzero,
              'Rwheel_in_r6': Rwheel, 'M7': M7, 'Pa': Pa,
              'PaCubic': Pcubic, 'primitive_spectral_bracket': Pspectral}

    # The existing certificates are read AFTER evaluation; used only as checks.
    oldwheel = json.loads((WORK/'C6_central_binomial_wheel/results/rational_intervals.json').read_text())
    oldm7 = json.loads((WORK/'C6_central_seventh_reduction/results/intervals.json').read_text())
    oldcomplete = json.loads((WORK/'C6_complete_interval/results/complete_refined.json').read_text())
    oldpa = unpack(oldcomplete['values']['Pa'])
    oldC6 = unpack(oldcomplete['C6_representation'])
    checks = {
        'wheel_overlaps_saved_certificate': overlap(Wcentral, unpack(oldwheel['enclosures'][-1]['Wcentral'])),
        'M7_overlaps_saved_certificate': overlap(M7, unpack(oldm7['runs'][-1]['M7central'])),
        'Pa_overlaps_saved_certificate': overlap(Pa, oldpa),
        'primitive_seed_checks_passed': len(seed_checks),
    }
    assert all(checks.values())

    # This finite-block value is derived by subtraction from the inherited C6;
    # it is not an independent all-sector evaluation, and is labelled accordingly.
    finite_C6 = oldC6 - sum_resid
    values['three_residuals_total_in_C6'] = sum_resid
    values['finite_part_in_C6_derived_from_saved_full_certificate'] = finite_C6
    values['C6_saved_full_certificate'] = oldC6

    out = {
        'explicit_infinite_sum_count': 3,
        'each_current_representation_has_one_infinite_index': True,
        'precision_bits': 1280,
        'methods': {
            'wheel': {'N': 256, 'M4': 40, 'M6': 41,
                      'tail_bound_exact': str(err),
                      'source': 'C6_central_binomial_wheel_reduction.zip/certify.py'},
            'seventh': {'Euler_N': 600, 'tail_bound_exact': m7info['Euler_error_bound'],
                        'source': 'C6_central_seventh_reduction.zip/certify.py'},
            'primitive': dict(painfo, source='C6_complete_interval.zip/primitive.py'),
            'spectral': 'Exact equality spectral_bracket = Pa/(8*pi**3); not a raw spectral partial sum.'
        },
        'values': {k: v.package(170) for k,v in values.items()},
        'contributions_in_r6': {k: v.package(170) for k,v in residual_r6.items()},
        'contributions_in_C6': {k: v.package(170) for k,v in residual_C6.items()},
        'comparison_checks': checks,
        'full_C6_freshly_recomputed': False,
        'scope': 'Numerical values of the retained analytic series. The interval bounds and identities are those supplied in the source packages. No finite closed-form evaluation or independent graph/RG validation is asserted.',
        'elapsed_seconds': time.time()-started,
    }
    (ROOT/'results.json').write_text(json.dumps(out,indent=2)+'\n')
    for k,v in values.items():
        print(k, v.package(65)['decimal_lower'], flush=True)
    print('Contributions to C6:', flush=True)
    for k,v in residual_C6.items():
        print(k, v.package(65)['decimal_lower'], flush=True)
    print('Checks:', checks, '\nElapsed:', time.time()-started, flush=True)

if __name__ == '__main__':
    main()
