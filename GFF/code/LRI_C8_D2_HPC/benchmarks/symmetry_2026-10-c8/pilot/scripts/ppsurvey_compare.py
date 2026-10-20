#!/usr/bin/env python3
"""Compare the per-node runtime-fingerprint survey records of the C8(2) L8 pilot preparation (scripts/ppsurvey.slurm)
and write survey/survey.json: one row per amdq node (surveyed or not), the majority runtime identity key, the nodes
whose identity differs from it (they would refuse claims with exit 64 under the campaign's runtime pin, X8), and the
--exclude lists for the pilot. Standard library only (runs on the Mac).
  ppsurvey_compare.py SURVEY_DIR NODE_STATES.txt OUT.json
NODE_STATES.txt: `sinfo -N -h -p amdq -o '%N %t %E'` as taken at the survey (unsurveyed nodes keep their state and
reason). HISTORY (constant below): earlier runtime-identity records of nodes not reachable now (same function,
common.runtime_identity_key; the key of an ordinary node is unchanged by fix rounds 3 and 4, docs/HPC.md Z6, W7)."""
import collections, json, sys
from pathlib import Path
d, states_f, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HISTORY = {
    'cn095': {'key': '04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b', 'cpu_model': 'AMD EPYC 7532 32-Core Processor',
              'source': 'benchmarks/symmetry_2026-10-c8/s6fix2/s2prec.570416.0/y6_y7.json (job 570416, 2026-10-06, Y6 survey of bin/c8d2_gmp)'},
    'cn106': {'key': '04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b', 'cpu_model': 'AMD EPYC 7543 32-Core Processor',
              'source': '/mnt/beegfs/zzheng1/c8-d2/sweepdd-997639178c1f/runtime_identity.json (first claim, job 570538, 2026-10-06T10:30:27Z; '
                        'bin/c8d2_gmp_dd+mp256, which loads the same libraries as bin/c8d2_gmp: s6fix2 found equal keys for both)'},
}
recs = {}
for f in sorted(d.glob('cn*.json')):
    r = json.loads(f.read_text()); recs[r['host']] = (f.name, r)
states = {}
for line in states_f.read_text().splitlines():
    p = line.split(None, 2)
    if len(p) >= 2: states[p[0]] = {'state': p[1], 'reason': p[2] if len(p) > 2 else ''}
keys = collections.Counter(r['runtime_identity_key'] for _, r in recs.values())
major, nmaj = keys.most_common(1)[0]
idents = {r['runtime_identity_key']: r['runtime_identity'] for _, r in recs.values()}
rows = []
for node in sorted(set(states) | set(recs)):
    st = states.get(node, {})
    if node in recs:
        name, r = recs[node]; s = r['summary']
        rows.append({'node': node, 'surveyed': True, 'record': f'survey/{name}', 'slurm_job': r['slurm_job'], 'partition': r['partition'], 'utc': r['utc'],
                     'cpu_vendor': s['cpu_vendor'], 'cpu_model': s['cpu_model'], 'cpus': s['cpus'], 'numa_nodes': s['numa_nodes'], 'glibc': s['glibc'],
                     'runtime_identity_key': r['runtime_identity_key'], 'majority': r['runtime_identity_key'] == major,
                     'fingerprint_complete': s['complete'], 'fingerprint_problems': r['fingerprint_problems'], 'unexplained_ldd_lines':
                     [k for k in r['fingerprint']['libraries'] if k.startswith('unexplained')], 'loader_overrides': r['loader_overrides'],
                     'preload_order': s['preload_order'], 'loader_env': s['loader_env'], 'etc_ld_so_preload': r['etc_ld_so_preload'],
                     'export_path_key_equal': s['export_path_key_equal'], 'executable_ok': s['executable_ok'], 'fingerprint_bytes': s['fingerprint_bytes'],
                     'libgmp': s['libgmp'], 'libquadmath': s['libquadmath'], 'libgomp': s['libgomp'], 'ok': r['ok'], 'state_at_survey': st.get('state')})
    else:
        h = HISTORY.get(node)
        why = ('excluded by rule (cn112: the known bad node; largememq node)' if node == 'cn112' else
               f"not reachable: {st.get('state')}" + (f" ({st.get('reason')})" if st.get('reason') and st.get('reason') != 'none' else ''))
        rows.append({'node': node, 'surveyed': False, 'state_at_survey': st.get('state'), 'why': why,
                     'history': h, 'history_majority': (h or {}).get('key') == major if h else None})
differs = [r['node'] for r in rows if r['surveyed'] and not r['majority']]
bad = [r['node'] for r in rows if r['surveyed'] and not r['ok']]
unsurveyed = [r['node'] for r in rows if not r['surveyed'] and r['node'] != 'cn112']
amdq_nodes = [r['node'] for r in rows]
excl_min = sorted(set(['cn112'] + differs + bad))
excl_cons = sorted(set(excl_min + unsurveyed))
models = collections.Counter(r['cpu_model'] for r in rows if r['surveyed'])
zen2 = sorted(r['node'] for r in rows if r['surveyed'] and '7532' in (r['cpu_model'] or ''))
rec = {'schema': 'c8-d2-pilot-node-survey-summary-1', 'records': len(recs), 'amdq_nodes': amdq_nodes,
       'majority_runtime_identity_key': major, 'majority_count': nmaj, 'keys': dict(keys), 'majority_identity': idents[major],
       'differing_nodes': differs, 'not_ok_nodes': bad, 'unsurveyed_nodes': unsurveyed, 'cpu_models': dict(models), 'zen2_7532_nodes': zen2,
       'exclude_minimal': ','.join(excl_min), 'exclude_recommended': ','.join(excl_cons),
       'rule': 'a node whose runtime identity differs from the campaign pin (runtime_identity.json, published by the first claim) makes every claim on it '
               'exit 64 (production.pin_runtime_identity); the first claim pins the identity of whatever node it lands on, so an unsurveyed node is '
               'excluded too in the recommended list (minimal list: cn112 and the surveyed nodes that differ or are incomplete)',
       'rows': rows}
out.write_text(json.dumps(rec, indent=1) + '\n')
print(f'{len(recs)} surveyed; majority key {major[:16]} on {nmaj}; keys {dict((k[:12], v) for k, v in keys.items())}')
print('differing:', differs or 'none', '; not ok:', bad or 'none', '; unsurveyed:', ' '.join(unsurveyed))
print('cpu models:', dict(models), '; Zen 2 (7532):', ' '.join(zen2))
print('exclude (minimal):', rec['exclude_minimal']); print('exclude (recommended):', rec['exclude_recommended'])
for r in rows:
    if r['surveyed']:
        print(f"{r['node']} {r['slurm_job']} {r['cpu_model'][9:]:<16} {r['runtime_identity_key'][:12]} complete={r['fingerprint_complete']} preload={r['preload_order']} env={r['loader_env']} ok={r['ok']}")
    else:
        print(f"{r['node']} unsurveyed: {r['why']}" + (f"; history {r['history']['key'][:12]} ({r['history']['cpu_model'][9:]})" if r.get('history') else ''))
