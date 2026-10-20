#!/usr/bin/env python3
"""Compare fresh lri_hpc outputs with the saved reference tables (PLAN G4, validation V).

Usage: check_regression.py OUTPUT_ROOT SUMMARY.json
OUTPUT_ROOT contains thermal/thermal_d7_L{40,50}.json, phi6_5/phi6_d5_L50.json, phi6_3/phi6_d3_L128.json.
Tolerance: |new - ref| <= 1e-7 + 2e-11 |ref| (the package's regression threshold), on every coefficient present in
the reference: thermal C0..C7 from validation_data/thermal_coefficients_through_C7.csv; phi6 D6 (raw and
vacuum_subtracted) from validation_data/phi6_gap_coefficients.csv. Also requires the built-in second-order shell
residual <= 1e-10 and tuning residual <= 1e-6. Exit status 0 iff every check passes.
"""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
out, summ = Path(sys.argv[1]), Path(sys.argv[2])
th = {int(r['cutoff']): [float(r[f'C{k}']) for k in range(8)] for r in csv.DictReader(open(ROOT / 'validation_data/thermal_coefficients_through_C7.csv'))}
gp = {}
for r in csv.DictReader(open(ROOT / 'validation_data/phi6_gap_coefficients.csv')):
    gp[(int(r['cutoff']), r['prescription'])] = [float(r[f'epsilon_power_{k}']) for k in range(6) if r[f'epsilon_power_{k}'] != '']
tol = lambda ref: 1e-7 + 2e-11 * abs(ref)
checks = []
def add(name, new, ref):
    worst = max((abs(a - b) - tol(b) for a, b in zip(new, ref)), default=float('inf'))
    checks.append({'check': name, 'pass': len(new) >= len(ref) and worst <= 0,
                   'max_abs_diff': max(abs(a - b) for a, b in zip(new, ref)), 'n': len(ref)})
def gates(name, r, recs):
    ok = abs(r['second_order_shell_residual']) <= 1e-10 and all(abs(x['tuning_residual']) <= 1e-6 for x in recs)
    checks.append({'check': name + ' gates', 'pass': ok, 'shell': r['second_order_shell_residual'],
                   'tuning': [x['tuning_residual'] for x in recs]})
for L in (40, 50):
    r = json.loads((out / f'thermal/thermal_d7_L{L}.json').read_text())
    add(f'thermal d7 L{L} C', r['C'], th[L]); gates(f'thermal d7 L{L}', r, [r])
for sub, d, L in (('phi6_5', 5, 50), ('phi6_3', 3, 128)):
    r = json.loads((out / f'{sub}/phi6_d{d}_L{L}.json').read_text())
    for p in ('raw', 'vacuum_subtracted'):
        add(f'phi6 d{d} L{L} {p} D6', r[p]['D6'], gp[(L, p)])
    gates(f'phi6 d{d} L{L}', r, [r['raw'], r['vacuum_subtracted']])
ok = all(c['pass'] for c in checks)
summ.write_text(json.dumps({'pass': ok, 'checks': checks}, indent=1) + '\n')
for c in checks:
    print(('PASS ' if c['pass'] else 'FAIL ') + c['check'], {k: v for k, v in c.items() if k not in ('check', 'pass')})
sys.exit(0 if ok else 1)
