#!/usr/bin/env python3
"""Review LRI-004: the extended analysis uses the original model code unchanged.

Checks that analysis/extended/analyze_joint.py is byte-identical to analysis_original/analyze_joint.py, that the
saved data copies here are identical to the originals, and that run_extended.py defines no model classes or fit
functions of its own (it may only configure and call them).
"""
import ast, hashlib, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG = HERE.parent.parent / 'analysis_original'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bad = []
for name in ['analyze_joint.py', 'phi6_validation.json', 'phi6_production.json', 'phi6_extension.json',
             'phi6_thin3.json', 'phi6_thin3_extension.json', 'C7_extension.json', 'prior_c7/C7_completed_runs.json']:
    if sha(HERE / name) != sha(ORIG / name):
        bad.append(name)
tree = ast.parse((HERE / 'run_extended.py').read_text())
own = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
own += [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in
        ('ls', 'eseries', 'design', 'load', 'fit', 'predict')]
if bad or own:
    sys.exit(f'FAIL: differs from original: {bad}; redefined in run_extended.py: {own}')
print('PASS: analyze_joint.py and saved data byte-identical to analysis_original; no model code redefined')
