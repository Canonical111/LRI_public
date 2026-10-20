#!/usr/bin/env python3
"""Binding replay for HT/code/lri_dressed_phi4_hpc (the d = 1 finite-coupling solver, commit 33998bb).

The quoted d = 1 numbers are recomputed from the records by ../lri_dressed_phi4_hpc_analysis (make replay there).
This replay shows that the shipped tree is the code that produced those records and that the package's own
validator accepts every record:
  1. source fingerprint (io.source_fingerprint over src/lri_dressed/*.py) = source_sha256 of every dens_v1 result,
     basis artifact, manifest and validation receipt 570965;
  2. release fingerprint (io.release_fingerprint) = release_sha256 of the dens_v1 manifests and of receipt 570965;
  3. `python -m lri_dressed export` (read_envelope + validate_result of this package) accepts every dens_v1 result
     and every prod1-7 result (the latter were written by commit 4dfd833; same record schema).
Run from HT/code/lri_dressed_phi4_hpc: `make -f public.mk replay`. About 1 min, one core.
"""
import json, os, subprocess, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(PKG / 'src'))
from lri_dressed.io import source_fingerprint, release_fingerprint  # noqa: E402
DATA = Path(os.environ.get('DATA', PKG / '../../data/HT_1d')).resolve(); WORK = Path(os.environ.get('WORK', PKG / '.work')).resolve()
WORK.mkdir(parents=True, exist_ok=True)
rows = []
def row(i, what, ok, detail): rows.append((i, 'PASS' if ok else 'FAIL', what, detail))
src, rel = source_fingerprint(), release_fingerprint(PKG)
D = DATA / 'dens_v1'
recs = [json.loads(p.read_text()) for p in sorted(D.glob('campaigns/*/results/*.json'))]
arts = [json.loads(p.read_text()) for p in sorted(D.glob('bases/dens_v1/x*_[0-9a-f]*.json')) if not p.name.endswith('.checkpoint.json')]
mans = [json.loads(p.read_text()) for p in sorted(D.glob('campaigns/*/manifest.json'))]
rcpt = json.loads((D / 'validation/570965/receipt.json').read_text())['payload']
s = {r['config']['source_sha256'] for r in recs} | {a['config']['source_sha256'] for a in arts} | {m['source_sha256'] for m in mans} | {rcpt['source_sha256']}
row('F1', 'source fingerprint = source_sha256 of 201 results, 13 bases, 5 manifests, receipt', s == {src}, f'{src[:16]} vs {sorted(x[:16] for x in s)}')
r = {m['release_sha256'] for m in mans} | {rcpt['release_sha256']}
row('F2', 'release fingerprint = release_sha256 of the manifests and receipt 570965', r == {rel}, f'{rel[:16]} vs {sorted(x[:16] for x in r)}')
env = dict(os.environ, PYTHONPATH=str(PKG / 'src'), OPENBLAS_NUM_THREADS='1', NUMBA_CACHE_DIR=str(WORK / 'numba_cache'))
for grp, dirs in (('dens_v1', sorted(D.glob('campaigns/*/results'))), ('prod1-7', sorted((DATA / 'prod_window').glob('campaigns/*/results')))):
    n = 0; ok = True
    for d in dirs:
        out = WORK / f'export_{d.parent.name}.json'
        pr = subprocess.run([sys.executable, '-m', 'lri_dressed', 'export', '--input-dir', str(d), '--output', str(out)], env=env, capture_output=True, text=True)
        ok &= pr.returncode == 0
        if pr.returncode == 0: n += len(json.loads(out.read_text()))
        else: (WORK / f'export_{d.parent.name}.err').write_text(pr.stdout + pr.stderr)
    row('V' + grp[0], f'`python -m lri_dressed export` validates every {grp} result', ok, f'{n} records exported')
for x in rows: print('%-3s %-5s %-80s %s' % (x[0], x[1], x[2], x[3]))
(WORK / 'replay_solver.txt').write_text('\n'.join('%s %s %s %s' % x for x in rows) + '\n')
sys.exit(1 if any(x[1] == 'FAIL' for x in rows) else 0)
