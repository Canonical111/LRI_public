"""Separate, restartable state-averaged basis training (consistent window only).

The production run consumes an immutable artifact. Outer training changes never
occur invisibly inside a campaign point or its continuation checkpoint.
"""
from __future__ import annotations
import gc
import math
import time
import resource
from pathlib import Path
import numpy as np
from .io import atomic_json, claim, envelope, read_envelope, runtime, source_fingerprint
from .planning import plan, guard
from .density import DensitySolver, FixedLocal, select_density_basis
from .solver import DressedSolver
from .local_basis import BASIS_SCHEMA, KIND, validate_basis


def train_configuration(args):
    if args.bath_cut < 2 or args.bath_cut % 2:
        raise ValueError('Training requires an even bath cutoff >= 2')
    if not 2 <= args.keep <= args.teacher_nz or args.osc % 2 or args.osc < 2*args.teacher_nz+8:
        raise ValueError('Invalid training local dimensions')
    if not math.isfinite(args.delta) or not 0 < args.delta < .25:
        raise ValueError('Require 0 < Delta_sigma < 1/4')
    if args.max_sweeps < 2 or not 0 < args.basis_tol < 1 or not 0 < args.teacher_tol < 1:
        raise ValueError('Invalid basis convergence gates')
    backend = plan(args.bath_cut, args.teacher_nz, args.osc, args.backend, args.ncv, 'vacuum')['backend']
    return {'delta': float(args.delta), 'bath_cut': args.bath_cut, 'teacher_nz': args.teacher_nz,
            'keep': args.keep, 'osc': args.osc, 'resolved_backend': backend,
            'window': 'vacuum', 'window_mode': 'consistent', 'zero_scale': 1.,
            'window_tol': args.window_tol, 'window_maxiter': args.window_maxiter,
            'eig_tol': args.eig_tol, 'residual_tol': args.residual_tol, 'tuning_tol': args.tuning_tol,
            'ncv': args.ncv, 'max_eig_iter': args.max_eig_iter, 'maxiter': args.maxiter,
            'basis_tol': args.basis_tol, 'teacher_tol': args.teacher_tol, 'max_sweeps': args.max_sweeps,
            'dtype': 'float64', 'fastmath': False, 'source_sha256': source_fingerprint(), 'runtime': runtime()}


def _kwargs(cfg):
    return {k: cfg[k] for k in ('eig_tol', 'residual_tol', 'ncv', 'max_eig_iter', 'window',
                               'window_mode', 'window_tol', 'window_maxiter')}


def train(cfg, guess, *, checkpoint=None, recovered=None, stop_requested=lambda: False):
    """Outer teacher-selection/inner-retuning loop. No thermal convergence target."""
    from .cli import InterruptedRun
    start = time.perf_counter()
    teacher = DressedSolver(cfg['bath_cut'], cfg['teacher_nz'], cfg['osc'],
                            backend=cfg['resolved_backend'], **_kwargs(cfg))
    teacher.set_delta(cfg['delta'])
    theta = teacher.initial(1-4*cfg['delta']) if guess is None else np.asarray(guess, dtype=float)
    if theta.shape != (2,) or not np.all(np.isfinite(theta)):
        raise ValueError('Invalid training starting theta')
    state = recovered
    history = [] if state is None else list(state['history'])
    first = 0 if state is None else int(state['sweep'])
    if state is not None:
        theta = np.asarray(state['theta'], dtype=float)
    if not 0 <= first < cfg['max_sweeps']:
        raise ValueError('Invalid training checkpoint sweep')

    def save(data):
        if checkpoint:
            checkpoint(data)
        if stop_requested():
            raise InterruptedRun('Basis training checkpointed at a safe boundary')

    for sweep in range(first, cfg['max_sweeps']):
        if state is not None and state.get('phase') == 'inner':
            u = np.asarray(state['candidate']['isometry'], dtype=float)
            scale = state['candidate']['scale']
            density = state['candidate']['density']
            selected_theta = np.asarray(state['candidate']['selected_theta'], dtype=float)
            FixedLocal(u, scale)  # validate checkpoint span before any solve
        else:
            save({'phase': 'select', 'sweep': sweep, 'theta': theta.tolist(), 'history': history})
            u, scale, density = select_density_basis(teacher, theta, cfg['keep'])
            selected_theta = theta.copy()
        candidate = {'isometry': u.tolist(), 'scale': float(scale), 'density': density,
                     'selected_theta': selected_theta.tolist()}
        save({'phase': 'inner', 'sweep': sweep, 'theta': theta.tolist(), 'history': history,
              'candidate': candidate})
        small = DensitySolver(cfg['bath_cut'], u, scale, backend=cfg['resolved_backend'],
                              basis=teacher.basis, **_kwargs(cfg))
        small.set_delta(cfg['delta'])

        def inner_checkpoint(th, steps):
            save({'phase': 'inner', 'sweep': sweep, 'theta': th.tolist(), 'history': history,
                  'candidate': candidate, 'inner_history': steps})

        small.checkpoint = inner_checkpoint
        sol = small.solve(theta, tol=cfg['tuning_tol'], maxiter=cfg['maxiter'])
        final_theta = np.asarray(sol['theta'])
        coupling_change = float(np.max(np.abs(final_theta-selected_theta)))
        # Validate calibration in the larger teacher, without requesting thermal.
        _, _, teacher_check = select_density_basis(teacher, final_theta, cfg['keep'])
        teacher_residual = float(np.max(np.abs(teacher_check['teacher_primary_residual'])))
        gates = {
            'coupling_change': coupling_change,
            'teacher_primary_residual': teacher_residual,
            'compressed_primary_residual': float(sol['tuning_residual']),
            'max_training_eigenvector_residual': max(density['max_training_eigenvector_residual'],
                                                    teacher_check['max_training_eigenvector_residual']),
            'window_max_fixed_point_residual': max(density['window_max_fixed_point_residual'],
                                                  teacher_check['window_max_fixed_point_residual']),
        }
        history.append({'sweep': sweep, 'selected_theta': selected_theta.tolist(),
                        'theta': final_theta.tolist(), 'gates': gates,
                        'discarded_by_parity': density['discarded_by_parity'],
                        'inner_solve_seconds': sol['seconds']})
        if sweep >= 1 and coupling_change <= cfg['basis_tol'] and teacher_residual <= cfg['teacher_tol']:
            payload = {'basis_schema': BASIS_SCHEMA, 'accepted': True,
                       'isometry': u.tolist(), 'scale': float(scale), 'theta': final_theta.tolist(),
                       'selection_theta': selected_theta.tolist(), 'density': density, 'gates': gates,
                       'history': history, 'training_seconds_this_process': time.perf_counter()-start,
                       'checkpoint_recovered': recovered is not None,
                       'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                       'scope': 'Numerical local span for the unchanged consistent-window model. No physical matching correction.'}
            result = envelope(KIND, cfg, payload)
            validate_basis(result, current=True)
            # A signal between the final solve and publication must not lose recovery.
            save({'phase': 'complete', 'sweep': sweep, 'theta': final_theta.tolist(),
                  'history': history, 'result': result})
            return result
        theta = final_theta
        state = None
        del small
        gc.collect()
    raise RuntimeError(f'Local-basis training did not converge in {cfg["max_sweeps"]} sweeps; last gates {gates}')


def execute_training(args):
    from .cli import setup_runtime, seed_theta, InterruptedRun
    from . import cli
    setup_runtime(args.threads)
    cfg = train_configuration(args)
    if args.seed and args.guess is not None:
        raise ValueError('Choose a seed or an explicit guess, not both')
    guess = seed_theta(args.seed, args.delta) if args.seed else args.guess
    if guess is None and args.delta < .23:
        raise ValueError('Strong-coupling basis training requires --seed or --guess; use a validated prior coupling as the initial guess')
    cfg['initial_theta'] = None if guess is None else list(map(float, guess))
    path = Path(args.output).resolve()
    cp = path.with_name(path.name+'.checkpoint.json')
    pl = plan(args.bath_cut, args.teacher_nz, args.osc, args.backend, args.ncv, 'vacuum')
    small = plan(args.bath_cut, args.keep, args.osc, args.backend, args.ncv, 'vacuum')
    # Teacher and compressed operator caches coexist; do not advertise only keep-size RSS.
    pl['memory_envelope_bytes'] += small['memory_envelope_bytes'] + 8*args.osc*args.osc*4
    pl['memory_envelope_gib'] = pl['memory_envelope_bytes']/2**30
    with claim(path.with_name(path.name+'.lock')):
        if path.exists():
            if not args.resume:
                raise FileExistsError(f'Basis artifact already exists: {path}; use --resume or a new path')
            record = read_envelope(path, KIND, cfg)
            validate_basis(record, current=True)
            print(__import__('json').dumps({'status': 'basis_reused', 'path': str(path), 'sha256': record['sha256']}), flush=True)
            return
        recovered = read_envelope(cp, 'basis-training-checkpoint', cfg)['payload'] if cp.exists() and args.resume else None
        guard(pl, args.memory_limit_gib)
        if recovered is not None and recovered.get('phase') == 'complete':
            result = recovered['result']
            validate_basis(result, current=True)
            if result['config'] != cfg:
                raise ValueError('Completed basis checkpoint configuration mismatch')
            if cli.STOP:
                raise InterruptedRun('Complete basis checkpoint retained; publication deferred by stop')
        else:
            try:
                result = train(cfg, guess, recovered=recovered,
                    checkpoint=lambda payload: atomic_json(cp, envelope('basis-training-checkpoint', cfg, payload)),
                    stop_requested=lambda: cli.STOP)
            except InterruptedRun:
                raise
            except Exception as exc:
                atomic_json(path.with_name(path.name+'.failure.json'), envelope('basis-training-failure', cfg,
                            {'type': type(exc).__name__, 'error': str(exc)}))
                raise
        atomic_json(path, result)
        print(__import__('json').dumps({'status': 'basis_completed', 'path': str(path), 'sha256': result['sha256'],
              'sweeps': len(result['payload']['history']), 'gates': result['payload']['gates']}), flush=True)
