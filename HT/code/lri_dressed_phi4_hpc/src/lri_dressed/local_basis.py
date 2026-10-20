"""Portable, checksummed local-basis artifacts and numerical identity.

Basis paths are operational locations. The record checksum, not the path, is
part of a solver's numerical configuration. Results embed the record so that
later diagnostics do not silently reconstruct a different local span.
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
from .io import SCHEMA, digest, read_envelope, source_fingerprint, runtime

KIND = 'local-basis'
BASIS_SCHEMA = 'lri-dressed-density-basis-v1'


def validate_basis(record, *, current=False):
    if not isinstance(record, dict):
        raise ValueError('Invalid local-basis record')
    check = dict(record)
    sha = check.pop('sha256', None)
    if sha != digest(check) or check.get('schema') != SCHEMA or check.get('kind') != KIND:
        raise ValueError('Local-basis checksum/schema/kind failure')
    cfg, payload = record['config'], record['payload']
    if payload.get('basis_schema') != BASIS_SCHEMA or payload.get('accepted') is not True:
        raise ValueError('Unaccepted or incompatible local-basis artifact')
    if cfg.get('window') != 'vacuum' or cfg.get('window_mode') != 'consistent':
        raise ValueError('Only the consistent-window density basis is supported in this release')
    for key in ('basis_tol','teacher_tol','eig_tol','residual_tol','tuning_tol','window_tol'):
        if not isinstance(cfg.get(key),(int,float)) or not math.isfinite(cfg[key]) or cfg[key]<0:
            raise ValueError('Invalid basis numerical tolerance')
    if not 0<cfg['basis_tol']<1 or not 0<cfg['teacher_tol']<1 or not 0<cfg['window_tol']<=1e-11:
        raise ValueError('Invalid basis convergence tolerance')
    delta = cfg.get('delta', float('nan'))
    if not math.isfinite(delta) or not 0 < delta < .25:
        raise ValueError('Invalid basis delta')
    osc, keep, teacher = cfg['osc'], cfg['keep'], cfg['teacher_nz']
    if any(type(v) is not int for v in (osc, keep, teacher, cfg['bath_cut'])):
        raise ValueError('Basis dimensions must be integers')
    if not 2 <= keep <= teacher or osc % 2 or osc < 2*teacher+8 or cfg['bath_cut'] < 2 or cfg['bath_cut'] % 2:
        raise ValueError('Invalid basis dimensions')
    u = np.asarray(payload.get('isometry'), dtype=np.float64)
    if u.shape != (osc, 2*keep) or not np.all(np.isfinite(u)):
        raise ValueError('Local-basis dimensions or values are invalid')
    if np.max(np.abs(u.T@u - np.eye(2*keep))) > 2e-10:
        raise ValueError('Local-basis orthonormality gate')
    if max(np.max(np.abs(u[1::2, :keep])), np.max(np.abs(u[::2, keep:]))) > 1e-12:
        raise ValueError('Local-basis parity gate')
    scale = payload.get('scale', float('nan'))
    theta = np.asarray(payload.get('theta'), dtype=float)
    if not math.isfinite(scale) or scale <= 0 or theta.shape != (2,) or not np.all(np.isfinite(theta)):
        raise ValueError('Invalid local-basis scale or starting couplings')
    density = payload.get('density', {})
    if density.get('thermal_target') is not False:
        raise ValueError('Basis must explicitly exclude the thermal target')
    labels = [d.get('name') for d in density.get('targets', [])]
    expected = ['top vacuum', 'sigma', 'shadow'] + [f'vacuum N<={n}' for n in range(2, cfg['bath_cut'], 2)] + ['local vacuum N=0']
    if labels != expected:
        raise ValueError('Incorrect density training targets')
    weights = [v.get('weight', float('nan')) for v in density['targets']]
    expected_weights = [1/6]*3 + [1/cfg['bath_cut']]*(cfg['bath_cut']//2)
    if not np.allclose(weights, expected_weights, rtol=0., atol=1e-15):
        raise ValueError('Incorrect state-average weights')
    evals = np.asarray(density.get('density_eigenvalues'), dtype=float)
    if evals.shape != (2, teacher) or not np.all(np.isfinite(evals)) or evals.min() < -1e-10:
        raise ValueError('Invalid density eigenvalue record')
    if abs(float(evals.sum())-1.) > 1e-9 or np.max(np.diff(evals, axis=1)) > 1e-10:
        raise ValueError('Density trace/order gate')
    gates = payload.get('gates', {})
    required = ('coupling_change', 'teacher_primary_residual', 'compressed_primary_residual',
                'max_training_eigenvector_residual', 'window_max_fixed_point_residual')
    if any(not math.isfinite(gates.get(k, float('nan'))) or gates[k]<0 for k in required):
        raise ValueError('Missing finite basis acceptance gates')
    if gates['coupling_change'] > cfg['basis_tol'] or gates['teacher_primary_residual'] > cfg['teacher_tol']:
        raise ValueError('Unconverged basis training')
    if gates['compressed_primary_residual'] > max(1e-8, 5*cfg['tuning_tol']):
        raise ValueError('Unaccepted compressed primary solve')
    if gates['max_training_eigenvector_residual'] > cfg['residual_tol'] or gates['window_max_fixed_point_residual'] > 1e-11:
        raise ValueError('Basis numerical acceptance gate')
    if cfg.get('dtype') != 'float64' or cfg.get('fastmath') is not False:
        raise ValueError('Unsupported basis precision')
    if current and (cfg.get('source_sha256') != source_fingerprint() or cfg.get('runtime') != runtime()):
        raise ValueError('Basis source/runtime differs from this release: regenerate and revalidate on the target runtime')
    return record


def load_basis(path, expected_sha=None, *, current=True):
    record = read_envelope(path, KIND)
    validate_basis(record, current=current)
    if expected_sha is not None and record['sha256'] != expected_sha:
        raise ValueError('Local basis changed since the manifest was frozen (checksum mismatch)')
    return record


def for_configuration(record, *, delta, nz, osc, window, window_mode, zero_scale=1.):
    cfg = record['config']
    if float(delta) != cfg['delta']:
        raise ValueError('Density basis belongs to a different delta; cross-delta reuse is not supported')
    if osc != cfg['osc'] or not 2 <= nz <= cfg['keep']:
        raise ValueError('Requested local size or auxiliary size is incompatible with the basis')
    if window != cfg['window'] or window_mode != cfg['window_mode']:
        raise ValueError('Density basis belongs to a different Hamiltonian/window prescription')
    if zero_scale != 1.:
        raise ValueError('Saved basis fixes the primitive scale: --zero-scale must be 1')
    keep = cfg['keep']
    u = np.asarray(record['payload']['isometry'], dtype=np.float64)
    u = u[:, np.r_[np.arange(nz), np.arange(keep, keep+nz)]].copy()
    return u, float(record['payload']['scale'])


def descriptor(record):
    return {'mode': 'density', 'sha256': record['sha256'], 'schema': BASIS_SCHEMA}


def result_basis(row, config, *, current=False):
    """Check both sides of the result/config binding. Also reject unbound extras."""
    desc = config.get('local_basis')
    record = row.get('local_basis_record')
    if desc is None:
        if record is not None or row.get('local_basis_mode') == 'density':
            raise ValueError('A density result must have a basis-bound configuration')
        return None
    validate_basis(record, current=current)
    if desc != descriptor(record) or row.get('local_basis_mode') != 'density':
        raise ValueError('Result basis differs from its configuration')
    if record['config']['source_sha256'] != config['source_sha256'] or record['config']['runtime'] != config['runtime']:
        raise ValueError('Basis source/runtime differs from result')
    for_configuration(record, delta=config['delta'], nz=config['nz'], osc=config['osc'],
                      window=config['window'], window_mode=config['window_mode'], zero_scale=config['zero_scale'])
    return record


def density_plan(planned, record):
    """Same physical state count; additional fixed-span arrays have an explicit envelope."""
    p = dict(planned)
    z, osc = p['nz'], p['osc']
    # Fixed U, transported U, primitive/projected powers and state-average metadata.
    extra = 8*(4*osc*(2*z) + 12*(2*z)**2 + 2*osc**2)
    p['density_basis_extra_bytes'] = extra
    p['memory_envelope_bytes'] += int(math.ceil(1.4*extra))
    p['memory_envelope_gib'] = p['memory_envelope_bytes']/2**30
    p['local_basis'] = descriptor(record)
    p['basis_training_cutoff'] = record['config']['bath_cut']
    p['scope'] += ' Density training is a separate job; this envelope is for the fixed-basis solve only.'
    return p


def read_basis_index(path, *, current=True):
    """An explicitly frozen map from delta to basis path/checksum (no directory guessing)."""
    import json
    raw = json.loads(Path(path).read_text())
    row = dict(raw)
    sha = row.pop('sha256', None)
    if sha != digest(row) or row.get('schema') != 'lri-dressed-basis-index-v1':
        raise ValueError('Invalid basis index checksum/schema')
    entries = {}
    for entry in row['entries']:
        p = Path(entry['path'])
        if not p.is_absolute():
            raise ValueError('Basis index paths must be absolute')
        rec = load_basis(p, entry['sha256'], current=current)
        delta = float(entry['delta'])
        if delta != rec['config']['delta'] or delta in entries:
            raise ValueError('Duplicate or mismatched basis-index delta')
        entries[delta] = (str(p), rec)
    if not entries:
        raise ValueError('Empty basis index')
    return entries
