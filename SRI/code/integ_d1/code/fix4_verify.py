"""Supplemental verification (fix round 4, hardened in fix round 5): re-runs the strengthened checks on the existing
production data, writes nothing into any frozen record, and publishes results/<OUT> (registered, write-once) with the
outcomes (MSC-031: the gate's machine-readable report is read from its stdout; no report file is written):
  gate v2 --verify (F/C/R + overrides + both dd samples), cx check v2 --verify, C8 v2 --verify, the three frozen
  sector-check comparisons (--verify-record), M4A gate --dry (would-be record hash), and the design hashes.
usage: python fix4_verify.py --out NAME   (e.g. fix5_verification.json; an existing record is never overwritten)"""
import os, sys, json, subprocess, hashlib, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
RES = pv.RES; ROOT = os.path.dirname(RES)
if '--out' not in sys.argv:
    sys.exit(__doc__)
OUTNAME = sys.argv[sys.argv.index('--out') + 1]
if OUTNAME in pv.registry() or os.path.exists(os.path.join(RES, OUTNAME)):
    sys.exit(f'{OUTNAME} exists or is registered: refusing')
P = os.path.join(RES, 'm4_runs', 'prod')
def run(args, env=None):
    r = subprocess.run([sys.executable] + args, cwd=HERE, capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    return r.returncode, r.stdout + r.stderr
reg = pv.registry()
out = {'tool': {os.path.relpath(__file__, ROOT): pv.sha256_file(__file__)}, 'commit': subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip(),
       'note': 'strengthened checks re-run on the existing data (fix rounds 4-5: MSC-026..034); no frozen record modified', 'checks': {}}
rc, txt = run(['m4b_gate.py', f'{P}/F', f'{P}/C', '--fine-dd', f'{P}/Fdd', '--coarse-dd', f'{P}/Cdd', '--radius', f'{P}/R', '--radius-dd', f'{P}/Rdd',
               '--dd-sample', f'{P}/Vdd', '--dd-sample2', f'{P}/Vdd2', '--verify'])
lines = [l for l in txt.split('\n') if l.startswith('VERIFY_REPORT_JSON ')]
if len(lines) != 1:
    print(txt[-2000:]); sys.exit('gate verify report missing')
gv = json.loads(lines[0][len('VERIFY_REPORT_JSON '):])
out['checks']['M4B_flow_coefficients_v2.json'] = {'exit': rc, 'pass': rc == 0 and 'M4B GATE (verify) PASS' in txt, 'rebuilt_sha256': gv['rebuilt_sha256'],
    'frozen_sha256': reg['M4B_flow_coefficients_v2.json']['sha256'], 'identical': gv['identical'], 'sidecar_fields_differing': gv['sidecar_fields_differing'],
    'gate_checks_failed': [c[0] for c in gv['checks'] if not c[3]], 'n_gate_checks': len(gv['checks']), 'sidecar_keys_ok': gv.get('sidecar_keys_ok'),
    'sidecar_allowed_differences': gv.get('sidecar_allowed_differences'), 'sidecar_allowed_extra': gv.get('sidecar_allowed_extra')}
out['designs'] = gv['designs_verified']
rc, txt = run(['m4b_cx_check.py', f'{P}/cxA', f'{P}/cxB', '--amended', '--verify'])
out['checks']['M4B_cx_check_v2.json'] = {'exit': rc, 'pass': 'M4B CX CHECK PASS' in txt, 'identical': 'IDENTICAL' in txt,
                                         'frozen_sha256': reg['M4B_cx_check_v2.json']['sha256']}
rc, txt = run(['c8_assemble.py', '--verify'])
out['checks']['C8_record_v2.json'] = {'exit': rc, 'pass': 'C8 ASSEMBLY (verify) PASS' in txt, 'identical': 'VERIFY C8_record_v2.json IDENTICAL' in txt,
                                      'frozen_sha256': reg['C8_record_v2.json']['sha256']}
for n in ('K0.92_L3', 'K0.92_L4', 'K1.05_L3'):
    name = f'M3_sector_check_{n}.json'; rec = json.load(open(os.path.join(RES, name)))
    rc, txt = run(['m3_sector_check.py', os.path.join(ROOT, rec['engine_output']['file'])] + [os.path.join(ROOT, c['file']) for c in rec['checks']]
                  + ['--tol', rec['threshold'], '--verify-record', name])
    out['checks'][name] = {'exit': rc, 'pass': 'SECTOR CHECK PASS' in txt, 'identical': f'VERIFY {name} IDENTICAL' in txt, 'frozen_sha256': reg[name]['sha256']}
rc, txt = run(['m4a_gate.py', os.path.join(RES, 'm4_runs', 'n3d2_B'), os.path.join(RES, 'm4_runs', 'n3d2_A'), '--dry'])
m = re.search(r'would-be record (\S+)', txt)
out['checks']['M4A_flow_coefficients.json'] = {'exit': rc, 'pass': 'M4A GATE (dry) PASS' in txt, 'rebuilt_sha256': m.group(1) if m else None,
    'frozen_sha256': reg['M4A_flow_coefficients.json']['sha256'], 'identical': bool(m) and m.group(1) == reg['M4A_flow_coefficients.json']['sha256']}
out['superseded_cx_v1'] = 'not re-verified as a current record; its rebuild differs only by two new null fields (amendment, supersedes)'
allok = all(c['pass'] and c['identical'] and c['exit'] == 0 for c in out['checks'].values()) \
    and not out['checks']['M4B_flow_coefficients_v2.json']['sidecar_fields_differing'] and out['checks']['M4B_flow_coefficients_v2.json']['sidecar_keys_ok']
out['all_identical_and_pass'] = allok
for k, c in out['checks'].items(): print(f'{k:36s} exit {c["exit"]}  pass {c["pass"]}  identical {c["identical"]}')
print('ALL IDENTICAL AND PASS' if allok else 'VERIFICATION FAILED')
if not allok:
    sys.exit(1)
text = json.dumps(out, indent=1, sort_keys=True) + '\n'
path = os.path.join(RES, OUTNAME)
pv.publish_unit([(path, text)], register=(OUTNAME, out['commit'], 'supplemental verification (no frozen record modified)'))
print(f'record results/{OUTNAME} sha256', hashlib.sha256(text.encode()).hexdigest())
