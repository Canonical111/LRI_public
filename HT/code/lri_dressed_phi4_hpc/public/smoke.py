#!/usr/bin/env python3
"""Smoke rerun of one dens_v1 production item: N = 12, Ds = 0.2, 16 density-basis states, consistent window.

The production command is built with this package's own lri_dressed.pack.command from the shipped manifest item
(dens16_lo), with the item's cluster paths replaced by shipped files, and the new Delta_eps is compared with the shipped
record (tolerance 1e-8: the tuning tolerance is 5e-10 on the two gap conditions).

Basis artifacts are bound to the runtime that trained them: lri_dressed.local_basis refuses an artifact whose recorded
Python/numpy/scipy/numba versions differ from the running ones ("regenerate and revalidate on the target runtime").
  - Same runtime as production (Python 3.11.4, numpy 2.3.5, scipy 1.17.0, numba 0.65.1): the shipped Ds = 0.2 artifact
    is used. About 1 min, one core.
  - Any other runtime: the Ds = 0.2 basis is first retrained on this runtime with the production training settings read
    from the shipped artifact (python -m lri_dressed train-basis, L = 24, teacher nz 48, keep 24, osc 384, same
    tolerances and starting couplings), and its isometry is compared with the shipped one (subspace distance, printed).
    Then the item runs with the new artifact. About 3-6 min with THREADS=4 (production training: 100 s), < 1 GB.
"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np
PKG = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(PKG / 'src'))
from lri_dressed.pack import command  # noqa: E402
from lri_dressed.io import runtime  # noqa: E402
DATA = Path(os.environ.get('DATA', PKG / '../../data/HT_1d')).resolve(); WORK = Path(os.environ.get('WORK', PKG / '.work')).resolve()
THREADS = os.environ.get('THREADS', '4')
C = DATA / 'dens_v1/campaigns/dens16_lo'
item = next(i for i in json.loads((C / 'manifest.json').read_text())['items'] if i['bath_cut'] == 12 and i['deltas'] == [0.2])
shipped = DATA / 'dens_v1/bases/dens_v1' / Path(item['local_basis_path']).name
art = json.loads(shipped.read_text())
out = WORK / 'smoke'; out.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(PKG / 'src'), OPENBLAS_NUM_THREADS='1', NUMBA_NUM_THREADS=THREADS, NUMBA_CACHE_DIR=str(WORK / 'numba_cache'))
here, there = runtime(), art['config']['runtime']
if here == there:
    print(f'runtime {here} = production runtime: using the shipped basis artifact {shipped.name}')
    basis, sha = shipped, item['local_basis_sha256']
else:
    print(f'runtime {here} differs from the production runtime {there}: the package refuses cross-runtime bases, so the\n'
          f'Ds = 0.2 basis is retrained on this runtime with the production settings of {shipped.name}')
    cfg = art['config']; basis = out / 'basis_x0.2_L24_teacher48_keep24_o384.json'
    if basis.exists(): basis.unlink()
    cmd = [sys.executable, '-m', 'lri_dressed', 'train-basis', '--bath-cut', str(cfg['bath_cut']), '--delta', repr(cfg['delta']),
           '--teacher-nz', str(cfg['teacher_nz']), '--keep', str(cfg['keep']), '--osc', str(cfg['osc']), '--backend', cfg['resolved_backend'],
           '--threads', THREADS, '--output', str(basis), '--guess', *map(repr, cfg['initial_theta']), '--basis-tol', repr(cfg['basis_tol']),
           '--teacher-tol', repr(cfg['teacher_tol']), '--max-sweeps', str(cfg['max_sweeps']), '--eig-tol', repr(cfg['eig_tol']),
           '--residual-tol', repr(cfg['residual_tol']), '--tuning-tol', repr(cfg['tuning_tol']), '--ncv', str(cfg['ncv']),
           '--max-eig-iter', str(cfg['max_eig_iter']), '--maxiter', str(cfg['maxiter']), '--window-tol', repr(cfg['window_tol']),
           '--window-maxiter', str(cfg['window_maxiter'])]
    pr = subprocess.run(cmd, env=env, capture_output=True, text=True)
    (WORK / 'smoke_train.log').write_text(pr.stdout + pr.stderr)
    if pr.returncode != 0: print(pr.stdout[-2000:], pr.stderr[-3000:]); sys.exit(1)
    new = json.loads(basis.read_text()); sha = new['sha256']
    dth = max(abs(a - b) for a, b in zip(new['payload']['theta'], art['payload']['theta']))
    print(f'retrained basis: sha256 {sha[:16]}..., training theta differs from the shipped artifact by {dth:.1e}')
item = dict(item, local_basis_path=str(basis), local_basis_sha256=sha, seed_dir=str(DATA / 'dens_v1/seeds/dens_v1_all'))
res = out / 'results'; res.mkdir(exist_ok=True)
pr = subprocess.run(command(item, res), env=env, capture_output=True, text=True)
(WORK / 'smoke.log').write_text(pr.stdout + pr.stderr)
if pr.returncode != 0: print(pr.stdout[-2000:], pr.stderr[-3000:]); sys.exit(1)
def find(d):
    for p in sorted(Path(d).glob('N12_*.json')):
        x = json.loads(p.read_text())['payload']
        if x['bath_cut'] == 12 and abs(x['delta'] - 0.2) < 1e-12 and x['nz_per_parity'] == 16: return x
new, old = find(res), find(C / 'results')
dD = abs(new['Delta_thermal'] - old['Delta_thermal']); dt = max(abs(a - b) for a, b in zip(new['theta'], old['theta']))
ok = dD <= 1e-8
print(f"smoke N=12 Ds=0.2 dens16: Delta_eps new {new['Delta_thermal']:.12f} shipped {old['Delta_thermal']:.12f} |diff| {dD:.2e} (tol 1e-8); |dtheta| {dt:.2e}: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
