"""Acceptance gates for finite-cutoff results (review LRI-001).

A result is accepted only if every coefficient is finite and has the expected length, the independent
second-order shell residual is <= 1e-10, and every tuning residual (thermal, or both phi6 prescriptions) is
<= TUNING_TOL. The solver applies this before publishing a completed result; the CLI applies it before reusing a
completed output; export_results.py applies it before exporting. Failing results are never treated as completed.
"""
import math

SHELL_TOL = 1e-10
TUNING_TOL = 1e-6


class ResultError(ValueError):
    pass


def check_result(r, tuning_tol=TUNING_TOL):
    task, degree = r.get('task'), r.get('degree')
    if task not in ('thermal', 'phi6') or not isinstance(degree, int):
        raise ResultError('result lacks task/degree')
    recs = [('thermal', r)] if task == 'thermal' else [(p, r.get(p) or {}) for p in ('raw', 'vacuum_subtracted')]
    for name, rec in recs:
        keys = ('C', 'r', 'g') + (('D6',) if task == 'phi6' else ())
        for k in keys:
            v = rec.get(k)
            if not isinstance(v, list) or len(v) != degree + 1:
                raise ResultError(f'{name}.{k}: expected {degree + 1} coefficients')
            if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in v):
                raise ResultError(f'{name}.{k}: non-finite coefficient')
        t = rec.get('tuning_residual')
        if not (isinstance(t, (int, float)) and math.isfinite(t) and abs(t) <= tuning_tol):
            raise ResultError(f'{name}: tuning residual {t} exceeds {tuning_tol}')
    s = r.get('second_order_shell_residual')
    if not (isinstance(s, (int, float)) and math.isfinite(s) and abs(s) <= SHELL_TOL):
        raise ResultError(f'second-order shell residual {s} exceeds {SHELL_TOL}')
    return r
