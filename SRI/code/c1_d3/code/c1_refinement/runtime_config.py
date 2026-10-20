"""Shared run inputs and chosen allowances for the conditional numerical envelope.
Numerical reference coefficients and denominator box are loaded from the current
precision run.  The objective allowance remains an explicit, non-certified choice.
"""
from pathlib import Path
import json
import math

OBJECTIVE_ALLOWANCE = 5e-5
EPSILONPRIME_WINDOW = (1.5349, 1.5375)

def load_reference(base: Path):
    precision = base.parent / 'c1_precision'
    data = json.loads((precision / 'analysis_results.json').read_text())['central']
    box = json.loads((precision / 'input_box_results.json').read_text())['two_error_box']
    C, b = float(data['C1']), float(data['b'])
    if not math.isfinite(C + b) or b <= 0 or not math.isclose(C, data['a']/b, rel_tol=1e-13):
        raise ValueError('Inconsistent or nonpositive retained reference coefficients')
    db = max(abs(box['delta_b_min']), abs(box['delta_b_max']))
    db = math.ceil(db * 1e6) / 1e6  # outward rounding, not new physical certification
    if not 0 <= db < b:
        raise ValueError('The retained denominator box is invalid')
    return C, b, db

def ratio_interval(C, b, lower, upper, dbmax):
    """Conservative conversion when the numerator interval straddles zero."""
    if not all(math.isfinite(x) for x in (C, b, lower, upper, dbmax)):
        raise ValueError('Nonfinite ratio input')
    if not lower <= 0 <= upper:
        raise ValueError('Smaller-denominator conversion requires lower <= 0 <= upper')
    if not 0 <= dbmax < b:
        raise ValueError('Denominator not bounded strictly away from zero')
    return [C + lower/(1-dbmax/b), C + upper/(1-dbmax/b)]
