#!/usr/bin/env python3
"""Fast test of the d = 2, 3 resummation package (new tool, 2026-10-14). Run from code/resum_d23/.

Reruns the verbatim 3d/code/calculate.py in a copy (about 12 s on one core) and compares the baseline columns of the
regenerated 3d/results/curves.csv (slope_CB8, slope_core_low, slope_core_high, direct_CB8) with the shipped table,
|diff| <= 1e-12; checks that the 2d and 3d inputs read by the scripts are present and parse.
"""
import csv, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import rsum_lib as L

T = L.Table('resum_d23 test')
L.verify_snapshot(PKG, T)
need = {'2d': ['protocol.json', 'sri_summary.json', 'C8_production.json', 'monte_carlo.json', 'previous_curves.csv',
               'previous_C8_forecasts.csv', 'ht_prod1/index.json'],
        '3d': ['protocol.json', 'sri_summary.json', 'C8_production.json', 'mc_accepted.json', 'previous_curves.csv',
               'previous_C8_forecasts.csv', 'ht_l20/index.json']}
ok = True
for d, files in need.items():
    for f in files:
        p = PKG/d/'inputs'/f
        try:
            (json.loads(p.read_text()) if p.suffix == '.json' else list(csv.reader(p.open())))
        except Exception as e:
            ok = False; print('input problem:', p, e)
T.check('inputs present and parse', ok, '%d files' % sum(map(len, need.values())), 'all', '2d/inputs, 3d/inputs')
work = PKG/'.work'/'test3d'
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(PKG/'3d', work/'3d', ignore=shutil.ignore_patterns('__pycache__'))
env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
r = subprocess.run([sys.executable, 'code/calculate.py'], cwd=work/'3d', env=env, capture_output=True, text=True)
T.check('3d calculate.py rerun', r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'verbatim script in a copy')
if r.returncode == 0:
    a = list(csv.DictReader((PKG/'3d'/'results'/'curves.csv').open()))
    b = list(csv.DictReader((work/'3d'/'results'/'curves.csv').open()))
    cols = ('slope_CB8', 'slope_core_low', 'slope_core_high', 'direct_CB8')
    d = max(abs(float(x[c]) - float(y[c])) for x, y in zip(a, b) for c in cols) if len(a) == len(b) else float('inf')
    T.check('3d baseline columns', d <= 1e-12, '%.1e' % d, '<= 1e-12', 'regenerated vs shipped 3d/results/curves.csv, %s' % ', '.join(cols))
else:
    print(r.stdout[-1500:], r.stderr[-1500:])
sys.exit(T.report(PKG/'.work'/'test_d23.txt'))
