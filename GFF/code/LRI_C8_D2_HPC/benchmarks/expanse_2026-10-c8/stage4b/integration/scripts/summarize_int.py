#!/usr/bin/env python3
"""Stage-4b integration: the gate table and the A-PERF-2 decisions recomputed from the copied job records (standard
library only). Run in benchmarks/expanse_2026-10-c8/stage4b/integration/:  python3 scripts/summarize_int.py
Writes int_summary.json and prints the tables used in docs/PERFORMANCE.md ("Stage 4b integration").
The statuses it reads are the development runs' own records of that integration (a historical summary); acceptance
evidence is judged by recomputed coverage in stage4b/final/scripts/summarize_final.py (quad_differential_verdict,
thread_identity_verdict, validate_verdict; Stage-6 fix round 4, W1/W2/W22's consumers)."""
import json, statistics, sys
from pathlib import Path
H = Path(__file__).resolve().parents[1]
STAGE3 = {'c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3'}
STEPS = [('S1', '+R5 (R5a, R5b)', '138d486', 'intbuild.54669703.0', 'intgate.54669707.0/S1'),
         ('S2', '+R3a', 'd46e736', 'intbuild.54669704.0', 'intgate.54669707.0/S2'),
         ('S3', '+R4a', 'bc0bedc', 'intbuild.54669705.0', 'intgate.54669708.0/S3'),
         ('S4', '+R4f merge and scripts (default build)', 'd0f0e05', 'intbuild.54669706.0', None),
         ('B2f', '+R5 +R3a with GMP_PREFIX=zen2 (R4f without R4a)', 'd46e736 src, d0f0e05 Makefile', None, 'intgate.54669708.0/B2f'),
         ('B4', '+R5 +R3a +R4a with GMP_PREFIX=zen2', 'd0f0e05', None, 'intgate.54669708.0/B4')]
FINAL = [p for p in sorted(H.glob('intgate.*/FINAL*'))]

def j(p): return json.loads((H / p).read_text())
def sha(path, name):
    for line in (H / path).read_text().splitlines():
        h, f = line.split(None, 1)
        if f.endswith('/' + name) and '/baseline/' not in f: return h
    return None

def gate(d):
    r = {}
    if (H / d / 'l8self.json').is_file():
        x = j(f'{d}/l8self.json'); r['G-L8SELF (A-RPL-7)'] = x['status']
        r['l8self'] = {f"{t['sector']}/{t['backend']}": {k: t[k] for k in ('graphs', 'rows', 'quad_points', 'mp_points')} for t in x['tests']}
        r['l8self_baseline'] = x['tests'][0]['baseline']; r['l8self_candidate'] = x['tests'][0]['candidate']
        r['baseline_is_stage3'] = x['tests'][0]['baseline'] == {'decimal': STAGE3['c8d2_decimal'], 'gmp': STAGE3['c8d2_gmp']}
    if (H / d / 'thread_identity.json').is_file():
        x = j(f'{d}/thread_identity.json'); r['thread identity (A-RPL-6)'] = x['status']
        r['thread_identity'] = {f"{b['sector']}/{b['backend']}": {'tasks': b['tasks'], 'identical': b['identical'], 'quad': b['quad'], 'mp': b['mp']} for b in x['blocks']}
    for k, n in (('replay', 'replay subset (A-RPL-1/2/3)'), ('quad_differential', 'quad differential (R3a proof)')):
        if (H / d / f'{k}.json').is_file(): r[n] = j(f'{d}/{k}.json')['status']
    if (H / d / 'quad_differential.json').is_file():
        q = j(f'{d}/quad_differential.json'); r['quad_differential_summary'] = q.get('summary'); r['quad_differential_gates'] = q.get('gates')
    return r

out = {'steps': {}, 'final': {}}
for name, what, commit, b, g in STEPS:
    rec = {'what': what, 'commit': commit}
    if b:
        v = j(f'{b}/validate.json'); rec['validate default parts (A-RPL-1/2/3 subset)'] = v['status']; rec['validate_parts'] = v['executed']
        rec['decimal_sha256'] = sha(f'{b}/binaries.sha256', 'c8d2_decimal'); rec['gmp_sha256'] = sha(f'{b}/binaries.sha256', 'c8d2_gmp')
    if g: rec.update(gate(g)); rec.setdefault('gmp_sha256', rec.get('l8self_candidate', {}).get('gmp'))
    out['steps'][name] = rec
out['steps']['S4']['default_build_equals_S3'] = j('intbuild.54669706.0/default_vs_S3.json')['identical']
vc = j('intbuild.54669706.0/variants_check.json'); out['zen2_variants'] = vc
s = j('intspeed.54669709.0/int_speed.json')
out['speed'] = {'job': 54669709, 'host': s['host'], 'shape': s['shape'], 'repeats': s['repeats'], 'workload': s['workload'],
                'binaries': s['binaries'], 'medians': s['medians'], 'speedups': s['speedups'], 'cumulative_vs_B0': s['cumulative_vs_first'],
                'rows_identical': s['rows_identical'], 'rows_digest': s['rows_digest'], 'runs': len(s['runs']),
                'spread': {k: (min(x['lane_thread_seconds'] for x in s['runs'] if x['binary'] == k), max(x['lane_thread_seconds'] for x in s['runs'] if x['binary'] == k)) for k in s['binaries']},
                'ipc': [{k: x[k] for k in ('binary', 'sha256', 'cpus', 'threads', 'ipc', 'multiplexed', 'integration_seconds', 'rows_digest')} for x in s['ipc']['runs']],
                'ipc_rows_identical': s['ipc']['rows_identical']}
sp = s['speedups']
out['decisions'] = {
    'R5a': {'speedup': sp['R5a']['lane_thread_seconds'], 'decision': 'kept' if sp['R5a']['meets_3pct_bar'] else 'revert'},
    'R5b': {'decision': 'kept: the default lanes are P4\'s best shapes (Expanse 16 x 8, symmetry 8 x 8); scheduling only'},
    'R3a': {'speedup': sp['R3a']['lane_thread_seconds'], 'decision': 'kept' if sp['R3a']['meets_3pct_bar'] else 'revert'},
    'R4a': {'speedup': sp['R4a']['lane_thread_seconds'], 'decision': 'kept' if sp['R4a']['meets_3pct_bar'] else 'reverted (code only)'},
    'R4f': {'speedup_without_R4a': sp['R4f_without_R4a']['lane_thread_seconds'], 'speedup_on_R4a': sp['R4f']['lane_thread_seconds'],
            'decision': 'kept as the opt-in GMP_PREFIX knob' if sp['R4f_without_R4a']['meets_3pct_bar'] else 'revert'},
    'R3c': {'ipc': {x['binary']: x['ipc'] for x in s['ipc']['runs']}, 'decision': 'not attempted' if min(x['ipc'] for x in s['ipc']['runs']) >= 1.5 else 'attempt'}}
for d in FINAL: out['final'][d.name] = gate(d.relative_to(H))
fb = sorted(H.glob('intbuild.*'))[-1]
if fb.name == 'intbuild.54672108.0':
    v = j(f'{fb.name}/validate.json'); z = (H / fb.name / 'final_zen2.sha256').read_text().split()[0]
    out['final']['build'] = {'job': 54672108, 'commit': 'e7ef98d', 'validate default parts (A-RPL-1/2/3 subset)': v['status'],
        'decimal_sha256': sha(f'{fb.name}/binaries.sha256', 'c8d2_decimal'), 'gmp_sha256': sha(f'{fb.name}/binaries.sha256', 'c8d2_gmp'), 'zen2_gmp_sha256': z}
    out['final']['build']['default_equals_B2'] = (out['final']['build']['decimal_sha256'], out['final']['build']['gmp_sha256']) == (out['steps']['S2']['decimal_sha256'], out['steps']['S2']['gmp_sha256'])
    out['final']['build']['zen2_equals_B2f'] = z == s['binaries']['B2f']['sha256']
(H / 'int_summary.json').write_text(json.dumps(out, indent=1) + '\n')
M = s['medians']
print('| Binary | lane-thread s (median) | free | power | node wall s | load share | busy | vs B0 |')
for k in s['binaries']:
    print(f"| {k} | {M['lane_thread_seconds'][k]:.1f} | {M['free_lane_thread_seconds'][k]:.1f} | {M['power_lane_thread_seconds'][k]:.1f} | {M['node_wall_seconds'][k]:.2f} | {M['load_share'][k]:.4f} | {M['busy_fraction'][k]:.3f} | {s['cumulative_vs_first'][k]:.4f} |")
print('| Step | from -> to | speedup | free | power | node wall | >= 1.03 |')
for k, v in sp.items():
    print(f"| {k} | {v['from']} -> {v['to']} | {v['lane_thread_seconds']:.4f} | {v['free_lane_thread_seconds']:.4f} | {v['power_lane_thread_seconds']:.4f} | {v['node_wall_seconds']:.4f} | {v['meets_3pct_bar']} |")
for k, v in out['steps'].items():
    print(k, {x: v.get(x) for x in ('validate default parts (A-RPL-1/2/3 subset)', 'G-L8SELF (A-RPL-7)', 'thread identity (A-RPL-6)', 'replay subset (A-RPL-1/2/3)', 'gmp_sha256')})
for k, v in out['final'].items(): print('final', k, {x: v.get(x) for x in ('G-L8SELF (A-RPL-7)', 'thread identity (A-RPL-6)', 'replay subset (A-RPL-1/2/3)', 'quad differential (R3a proof)', 'validate default parts (A-RPL-1/2/3 subset)', 'default_equals_B2', 'zen2_equals_B2f')})
print(json.dumps(out['decisions'], indent=1))
