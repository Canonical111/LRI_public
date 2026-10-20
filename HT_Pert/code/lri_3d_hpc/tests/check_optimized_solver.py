#!/usr/bin/env python3
"""Compare both optimized algorithms against the frozen finite-cutoff solver.

The comparisons cover C, r, g, all primary energies, every subcutoff vacuum,
all computed window coefficients, and each wavefunction order retained by the
optimized method.  These are deterministic numerical equivalence checks;
their runtimes are not controlled performance benchmarks.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import pickle
import sys

import numpy as np


def scaled_error(a, b):
    a, b = np.asarray(a, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
    if a.shape != b.shape:
        raise AssertionError((a.shape, b.shape))
    difference = np.abs(a-b)
    return float(np.max(difference/np.maximum(1, np.maximum(np.abs(a), np.abs(b))), initial=0))


def compare(left, right):
    a, _, roots_a, vacua_a = left
    b, _, roots_b, vacua_b = right
    errors = {key: scaled_error(a[key], b[key]) for key in ('C', 'r', 'g')}
    for group in ('energies_by_seed', 'vacuum_energies_by_subcutoff'):
        assert a[group].keys() == b[group].keys()
        errors[group] = max(scaled_error(a[group][key], b[group][key]) for key in a[group])
    errors['wavefunctions'] = 0.0
    errors['windows'] = 0.0
    for states_a, states_b in ((roots_a, roots_b), (vacua_a, vacua_b)):
        for key, state_b in states_b.items():
            state_a = states_a[key]
            for i, psi in enumerate(state_b.psi):
                errors['wavefunctions'] = max(errors['wavefunctions'], scaled_error(state_a.psi[i], psi))
            for i, window in enumerate(state_b.windows):
                errors['windows'] = max(errors['windows'], scaled_error(state_a.windows[i], window))
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--trusted-cache', type=Path, help='Locally generated pickle only; never unpickle an untrusted upload')
    p.add_argument('--cutoffs', type=int, nargs='+', default=[0, 2, 4])
    p.add_argument('--orders', type=int, nargs='+', default=[2, 3, 4, 5, 6, 7, 8])
    p.add_argument('--dtype', choices=['float64', 'longdouble'], default='longdouble')
    p.add_argument('--backend', choices=['native', 'scipy', 'auto'], default='scipy')
    p.add_argument('--native-cache', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root/'code'))
    sys.path.insert(0, str(root/'vendor'))
    spec = importlib.util.spec_from_file_location('frozen_reference_solver', root/'reference'/'perturbative.py')
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    from optimized_solver import solve_coefficients
    from native_backend import load_backend
    from taylor_vertices import build_taylor_vertices
    dtype = np.longdouble if args.dtype == 'longdouble' else np.float64
    backend = load_backend(args.backend, threads=1, cache_dir=args.native_cache)
    if args.trusted_cache is None:
        N, P, W = build_taylor_vertices(max(args.cutoffs), degree=max(args.orders)-2, dtype=dtype)
    else:
        with args.trusted_cache.open('rb') as f:
            data = pickle.load(f)
        if data['cutoff'] < max(args.cutoffs) or data['degree'] < max(args.orders)-2:
            raise ValueError('The cache does not cover the requested fixture grid')
        N, P, W = data['N'], data['P'], data['W']
    tolerance = 2e-10 if dtype == np.float64 else 5e-13
    rows = []
    for cutoff in args.cutoffs:
        for order in args.orders:
            for mode in ('raw', 'consistent'):
                nz = (3+4*(order//2)+2)//2
                exact = reference.solve_coefficients(N, P, W, cutoff, order=order, nz=nz,
                                                     mode=mode, dtype=dtype, keep_states=True)
                for strategy in ('recurrence', 'stationary'):
                    observed = solve_coefficients(N, P, W, cutoff, order=order, nz=nz,
                        mode=mode, dtype=dtype, keep_states=True, strategy=strategy, spmm=backend.csr_spmm)
                    errors = compare(exact, observed)
                    record = {'cutoff': cutoff, 'order': order, 'scheme': mode,
                              'strategy': strategy, 'errors': errors,
                              'optimization': observed[0]['optimization']}
                    rows.append(record)
                    if max(errors.values()) > tolerance:
                        raise AssertionError(record)
    result = {'passed': True, 'dtype': str(np.dtype(dtype)),
              'significand_bits': int(np.finfo(dtype).nmant+1),
              'tolerance': tolerance, 'backend': backend.metadata,
              'fixtures': rows, 'max_scaled_difference': max(max(row['errors'].values()) for row in rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': True, 'fixtures': len(rows),
                      'max_scaled_difference': result['max_scaled_difference']}))


if __name__ == '__main__':
    main()
