#!/usr/bin/env python3
"""Compare a fresh archived-stream replay with the cited one (make -f public.mk archived-replay).

    python3 public/compare_archived_replay.py NEW/replay_report.json ../../results/C7_3/evidence/replay_report.json

NEW is written by public/replay_archived.py, the code review's script (job 566411, 2026-09-30, AMD EPYC 7532, 64
threads): it reruns the production worker on the 168,528 archived rows of the previous calculation (production_a and
production_b: archived nets, tasks and seeds) and rebuilds the previous C7(3) with tools/assemble.py.

PASS requires: the same 168,528 rows; binary128 and GMP promotion counts identical to the archived rows in all 20
groups (and to the cited replay); largest normalized difference |new-old|/max(1,|old|) <= 1e-10 (the cited run:
1.0e-11; across CPU types the worker differs by up to 2.0e-11, so the bound has a factor-5 margin); the rebuilt C7(3) and
its SE within 1e-10 relative of the published -227.61810947469945 +- 3.8273968756607397 (cited: 2.3e-13 and 0). The share
of bitwise rows is reported (cited: 162,044 of 168,528, 96%); on another CPU type it can be lower. Exits 1 on FAIL.
"""
import json, sys
from decimal import Decimal

new, ref = (json.load(open(p)) for p in sys.argv[1:3])
rows = []


def chk(name, ok, got, want):
    rows.append(('PASS' if ok else 'FAIL', name, str(got), str(want)))


chk('rows', new['rows'] == ref['rows'] == 168528, new['rows'], ref['rows'])
chk('groups', sorted(new['groups']) == sorted(ref['groups']) and len(new['groups']) == 20, len(new['groups']), 20)
prom = all(g['quad_old'] == g['quad_new'] and g['mp_old'] == g['mp_new'] for g in new['groups'].values())
same = all((new['groups'][k]['quad_new'], new['groups'][k]['mp_new']) == (ref['groups'][k]['quad_new'], ref['groups'][k]['mp_new'])
           for k in ref['groups'] if k in new['groups'])
chk('promotion counts = archived rows', prom and not new['fallback_mismatch_groups'], new['fallback_mismatch_groups'], [])
chk('promotion counts = cited replay', same, 'equal' if same else 'different', 'equal')
mx = Decimal(new['max_normalized_difference'])
chk('max normalized difference <= 1e-10', mx <= Decimal('1e-10'), f'{float(mx):.2e}', f"cited {float(Decimal(ref['max_normalized_difference'])):.2e}")
chk('archived C7, SE are the published ones', (new['archived_C7_full'], new['archived_se']) == (ref['archived_C7_full'], ref['archived_se']),
    (new['archived_C7_full'], new['archived_se']), (ref['archived_C7_full'], ref['archived_se']))
rel = abs(new['C7_full'] - new['archived_C7_full']) / abs(new['archived_C7_full'])
rse = abs(new['sampling_standard_error'] - new['archived_se']) / new['archived_se']
chk('rebuilt C7(3) within 1e-10 relative', rel <= 1e-10, repr(new['C7_full']), f"cited {ref['C7_full']!r}")
chk('rebuilt SE within 1e-10 relative', rse <= 1e-10, repr(new['sampling_standard_error']), repr(ref['sampling_standard_error']))
rows.append(('INFO', 'bitwise rows', f"{new['bitwise_rows']} ({100 * new['bitwise_rows'] / new['rows']:.1f}%)",
             f"cited {ref['bitwise_rows']} ({100 * ref['bitwise_rows'] / ref['rows']:.1f}%)"))
for r in rows:
    print(f'{r[0]:5s} {r[1]:40s} got {r[2]:40s} expected {r[3]}')
bad = sum(r[0] == 'FAIL' for r in rows)
print('archived-stream replay:', 'FAIL' if bad else 'PASS')
sys.exit(1 if bad else 0)
