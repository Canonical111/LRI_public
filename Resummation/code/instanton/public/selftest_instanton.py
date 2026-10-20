#!/usr/bin/env python3
"""Fast test of the instanton package (new tool, 2026-10-14). Run from code/instanton/.
Runs the zero-dimensional sign check (step0_zero_dim.py) and the d = 4 phi^4 benchmark (step1_d4_validation.py) in a
copy: the pipeline must reproduce McKane's MS beta-function constant and nu^{-1} amplitude with ratio 1 (1e-10).
"""
import re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import rsum_lib as L

work = PKG/'.work'/'test'
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(PKG, work, ignore=shutil.ignore_patterns('public', '.work', '__pycache__'))
T = L.Table('instanton test')
L.verify_snapshot(PKG, T)
for s in ('step0_zero_dim.py', 'step1_d4_validation.py'):
    r = subprocess.run([sys.executable, '-B', s], cwd=work, capture_output=True, text=True)
    T.check(s, r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'verbatim script')
    if s.startswith('step1') and r.returncode == 0:
        line = [l for l in r.stdout.splitlines() if l.startswith('with profile shift')][0]
        v = [float(x) for x in re.findall(r'=\s*([-+0-9.eE]+)', line)]
        T.check('d=4 benchmark ratios', len(v) == 2 and all(abs(x - 1) < 1e-10 for x in v), ', '.join(map(str, v)), '1, 1',
                "McKane's C_beta and nu^{-1} amplitude reproduced")
sys.exit(T.report(PKG/'.work'/'test_instanton.txt'))
