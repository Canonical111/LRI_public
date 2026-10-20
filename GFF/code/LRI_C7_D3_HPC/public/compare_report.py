#!/usr/bin/env python3
"""Compare a fresh tools/report.py re-verification of run1 with the shipped one (make -f public.mk reverify).

    python3 public/compare_report.py NEW.json ../../results/C7_3/run1_report_bb9d2ca.json

NEW is written by reverify_a6ce987/tools/report.py (commit a6ce987, unmodified) on the run directory extracted from the
hosted run1-20260930-m4096_full.tgz. The expected report was written on 2026-10-01 by the same tool at bb9d2ca (the
code the Codex inspection approved; a6ce987 changed only the archived gate's flag, not any value) on a symmetry
AMD EPYC 7532 node.

PASS requires identical data identity (manifest, merged files, seed scheme, backend, executable, mode, loops,
replicates, input and reference hashes); C7, its SE and the coefficients within 1e-12 relative of the expected report
and of C7_result.json (report.py's own test; bitwise on AVX2 AMD nodes); every gate within 1e-8 relative (the order-3
power difference, which vanishes in exact arithmetic, is excluded); no gate flagged. Time stamps, host, directory and
tool hashes are not compared. Exits 1 on FAIL.
"""
import json, sys

new, ref = (json.load(open(p)) for p in sys.argv[1:3])
rows = []


def chk(name, ok, got, want=''):
    rows.append(('PASS' if ok else 'FAIL', name, str(got)[:60], str(want)[:60]))


def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


def maxrel(a, b, scale=0.0):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a == b:
            return 0.0
        return abs(a - b) / max(abs(a), abs(b), scale)
    if isinstance(a, dict) and isinstance(b, dict):
        return None if a.keys() != b.keys() else max([maxrel(a[k], b[k]) for k in a] + [0.0], key=lambda x: float('inf') if x is None else x)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return None
        sc = max([abs(x) for x in a + b if isinstance(x, (int, float)) and not isinstance(x, bool)], default=0.0)
        return max([maxrel(x, y, sc) for x, y in zip(a, b)] + [0.0], key=lambda x: float('inf') if x is None else x)
    return 0.0 if a == b else None


ident = ('manifest_schema', 'manifest_sha256', 'seed_scheme', 'backend', 'executable_sha256', 'primitive_mode', 'loops', 'replicates', 'merged_sha256')
for k in ident:
    chk(f'campaign.{k}', new['campaign'][k] == ref['campaign'][k], new['campaign'][k], ref['campaign'][k])
chk('input and reference hashes', (new['provenance']['input_sha256'], new['provenance']['references_sha256'])
    == (ref['provenance']['input_sha256'], ref['provenance']['references_sha256']), 'equal', '')
for k in ('C7_full', 'sampling_standard_error'):
    chk(k, rel(new[k], ref[k]) <= 1e-12, repr(new[k]), repr(ref[k]))
chk('coefficients', maxrel(new['assembly']['coefficients'], ref['assembly']['coefficients']) <= 1e-12, 'within 1e-12', '')
ex = new['existing_result']
chk('C7_result.json re-verified (report.py, 1e-12)', ex is not None and ex['sha256'] == ref['existing_result']['sha256']
    and ex['max_relative_difference'] <= 1e-12, f"bitwise={ex and ex['bitwise']}", 'bitwise on AVX2 AMD')


def strip(c):
    c = json.loads(json.dumps(c))
    c['power_differences'] = [e for e in c['power_differences'] if e['order'] != 3]
    return c


g = maxrel(strip(new['checks']), strip(ref['checks']))
chk('gates (1e-8; power difference [3] excluded)', g is not None and g <= 1e-8, 'bitwise' if g == 0 else g, '')
chk('no gate flagged', new['checks']['flags'] == [], new['checks']['flags'], [])
for r in rows:
    print(f'{r[0]:5s} {r[1]:48s} got {r[2]:60s} expected {r[3]}')
bad = sum(r[0] == 'FAIL' for r in rows)
print('reverify:', 'FAIL' if bad else 'PASS')
sys.exit(1 if bad else 0)
