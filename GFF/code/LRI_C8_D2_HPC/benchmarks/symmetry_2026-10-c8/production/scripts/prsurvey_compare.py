#!/usr/bin/env python3
"""Compare the production runtime-fingerprint survey (scripts/prsurvey.slurm, the PRODUCTION worker
bin/c8d2_gmp_dd+mp256 a46f3060...; plus the build job's own fingerprint of a staged copy on its node, prbuild.slurm) with
the pilot's survey of bin/c8d2_gmp (../pilot/survey/), and write survey/survey.json: one row per amdq node, the runtime
identity key of each, the CPU model, and the production node pool and --exclude list. Standard library only (Mac).
  prsurvey_compare.py PRSURVEY_DIR BUILD_IDENTITY.json PILOT_SURVEY_DIR NODE_STATES.txt OUT.json
Production pool rule (the pilot's, docs/HPC.md F5/X8 and pilot/README.md section 2): a node is usable when the
PRODUCTION executable's fingerprint on it is complete, has no loader override and has the campaign's expected runtime
identity key (04f1e51d..., the pilot's pin and the gate's libgmp 4dc20a90...), AND its CPU is the profile cost model's
(AMD EPYC 7543: lane class factor 1.0, every per-graph cost of the design measured on it). Every other amdq node is
excluded: Zen 2 (7532) nodes (identity equal, but class factor 1.5 and another CPU model), nodes not surveyed now
(another user's job, a reservation, down), and cn112 (rule)."""
import collections, json, sys
from pathlib import Path
KEY = '04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b'
MODEL = 'AMD EPYC 7543 32-Core Processor'
d, build_f, pilot_d, states_f, out = (Path(x) for x in sys.argv[1:6])
recs = {}
for f in sorted(d.glob('cn*.json')):
    r = json.loads(f.read_text()); s = r['summary']
    recs[r['host']] = {'record': f'survey/{f.name}', 'slurm_job': r['slurm_job'], 'source': 'prsurvey.slurm', 'cpu_model': s['cpu_model'], 'cpu_vendor': s['cpu_vendor'],
                       'glibc': s['glibc'], 'key': r['runtime_identity_key'], 'complete': s['complete'], 'no_loader_override': s['no_loader_override'],
                       'executable_ok': s['executable_ok'], 'libgmp': s['libgmp'], 'numa_nodes': s['numa_nodes'], 'cpus': s['cpus'],
                       'preload_order': s['preload_order'], 'loader_env': s['loader_env'], 'ok': r['ok']}
b = json.loads(build_f.read_text()); fp = b['fingerprint']; host = b['host'].split('.')[0]
recs.setdefault(host, {'record': f'{build_f.parent.name}/{build_f.name}', 'slurm_job': b['slurm_job'], 'source': 'prbuild.slurm (staged copy of the new build)',
                       'cpu_model': fp['cpu_model'], 'cpu_vendor': fp['cpu_vendor'], 'glibc': fp['glibc'], 'key': fp['runtime_identity_key'],
                       'complete': not fp['problems'] and fp['malformed'] is None, 'no_loader_override': not fp['loader_overrides'],
                       'executable_ok': b['profile_is_gated_build'], 'libgmp': str(fp['libraries'].get('libgmp.so.10') or '')[:12],
                       'numa_nodes': None, 'cpus': None, 'preload_order': fp['preload_order'], 'loader_env': fp['loader_env'], 'ok': b['ok']})
pilot = {}
for f in sorted(pilot_d.glob('cn*.json')):
    r = json.loads(f.read_text()); pilot[r['host']] = {'slurm_job': r['slurm_job'], 'key': r['runtime_identity_key'], 'cpu_model': r['summary']['cpu_model']}
states = {}
for line in states_f.read_text().splitlines():
    p = line.split(None, 2)
    if len(p) >= 2 and p[0].startswith('cn'): states[p[0]] = {'state': p[1], 'reason': p[2] if len(p) > 2 else ''}
rows = []
for node in sorted(set(states) | set(recs)):
    st = states.get(node, {}); pr = pilot.get(node)
    row = {'node': node, 'state_at_survey': st.get('state'), 'pilot_survey': pr}
    if node in recs:
        r = recs[node]; row.update(surveyed=True, **r)
        row['usable'] = r['ok'] and r['complete'] and r['no_loader_override'] and r['key'] == KEY and r['cpu_model'] == MODEL
        row['why_not'] = None if row['usable'] else ('Zen 2 (EPYC 7532): class factor 1.5, not the cost model\'s CPU' if '7532' in (r['cpu_model'] or '') else 'identity or fingerprint')
    else:
        row.update(surveyed=False, usable=False, why_not=('excluded by rule (cn112)' if node == 'cn112' else
                                                          ('Zen 2 (EPYC 7532, the pilot survey): class factor 1.5, not the cost model\'s CPU' if pr and '7532' in pr['cpu_model'] else
                                                           f"not surveyed now: {st.get('state')}" + (f" ({st.get('reason')})" if st.get('reason') and st.get('reason') != 'none' else ''))))
    rows.append(row)
usable = [r['node'] for r in rows if r['usable']]; excl = [r['node'] for r in rows if not r['usable']]
keys = collections.Counter(r['key'] for r in rows if r['surveyed'])
rec = {'schema': 'c8-d2-production-node-survey-summary-1', 'expected_key': KEY, 'cost_model_cpu': MODEL, 'keys': dict(keys),
       'usable_nodes': usable, 'usable_count': len(usable), 'exclude': ','.join(excl), 'rule': __doc__, 'rows': rows}
out.write_text(json.dumps(rec, indent=1) + '\n')
print(f'{sum(1 for r in rows if r["surveyed"])} surveyed with the production executable; keys {dict((k[:12], v) for k, v in keys.items())}')
print(f'usable ({len(usable)}):', ','.join(usable)); print('exclude:', rec['exclude'])
for r in rows:
    print(f"{r['node']} {r['state_at_survey'] or '':6} " + (f"{r['slurm_job']} {(r['cpu_model'] or '')[9:]:<16} {r['key'][:12]} ok={r['ok']} usable={r['usable']}"
          if r['surveyed'] else f"unsurveyed: {r['why_not']}") + (f"  [pilot {r['pilot_survey']['slurm_job']} {r['pilot_survey']['key'][:12]}]" if r['pilot_survey'] else ''))
