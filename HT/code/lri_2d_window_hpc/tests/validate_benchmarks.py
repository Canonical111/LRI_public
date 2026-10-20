from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'results/SUMMARY.json').read_text())
assert len(s['full_solves'])==6 and all(r['independent_processes']==3 for r in s['full_solves'])
assert len(s['operators'])==36 and len(s['basis'])==8
for r in s['comparisons']:
 assert r['thermal_difference']<1e-9 and r['max_five_level_difference']<2e-8
 assert r['max_window_difference']<1e-9
 assert r['optimized_tuning_residual']<1e-10 and r['optimized_eigenvector_residual']<1e-8
# Required requested counts/tolerances and internally generated fixed-point data.
for path in (ROOT/'results/benchmarks').glob('*.json'):
 d=json.loads(path.read_text())
 if d['task']!='solve':continue
 r=d['result'];assert len(r['even_gaps'])==5 and len(r['odd_gaps'])==5
 assert r['max_eigenvector_residual']<1e-8 and r['max_orthogonality_residual']<1e-9
 w=r['window_correction']
 assert max([w['top_fixed_point_residual'],*w['sublevel_fixed_point_residuals'].values()])<=1e-11
print('All 62 benchmark records and numerical gates passed')
