"""Negative and positive tests of the M2/M3 gates (fix round 1, MSC-005/006). Corrupted copies of the archived data
must FAIL (nonzero exit, nothing published); the archived data must PASS. Runs in about a minute.
  1. M3, delta^0 records of every sector set to zero (flow coefficients unchanged): FAIL on delta0 vs BA;
  2. M3, one of the six sector files missing: FAIL on the manifest check;
  3. M3, one file truncated mid-sector: FAIL on file validation;
  4. M3, one delta^1 coefficient perturbed by 1e-12: FAIL on the relations;
  5. M2, delta^0 values set to zero: FAIL on delta0 vs BA (nothing written);
  6. M2, one contour point missing: FAIL on data completeness;
  7. the archived M3 (s3) and M2 data: PASS (stage 1 dry / stage 1 with the existing identical record).
Fix round 2: sector-check NaN / empty / wrong input hash / wrong K / two builds / missing completion marker /
modified legacy file all FAIL and the archived check passes (MSC-012, MSC-013); merging a modified legacy chunk fails
(MSC-014); concurrent write_once: exactly one of 16 different writers wins, identical writers all succeed, a
publication unit is refused as a whole (MSC-015); m3_gate --stage2 --dry is rejected (MSC-017).
Fix round 3: MSC-019 (comparison provisional without a current C8 record and a passing, bound cx check), MSC-020
(B-record duplicates, gaps, arity, bound mode), MSC-021 (approved, reproducible builds and their precision), MSC-022
(runner checksum/args verified by the consumer), MSC-023 (sigma(C8) <= 0.3, roundoff factor >= 0.01), MSC-024 (cx
check needs two distinct directories and both prescribed K), MSC-025 (submitter state only after sbatch success,
missing task files stop it).
Fix round 4: MSC-026 (shifted B window, invalid k), MSC-027 (eps from build precision), MSC-028 (design file differs
from its pre-data commit; design scripts never overwrite), MSC-029 (unauthenticated engine reference, checker runner
arguments with wrong K / sector / level; the three frozen sector checks rebuilt byte-identically).
Fix round 5: MSC-031 (--report onto the registry / a frozen record / a symlink refused, files untouched), MSC-032
(missing, empty or field-dropped provenance sidecar fails verify), MSC-033 (-nosplit vs split 0 1; omitted -level vs a
level-4 output), MSC-034 (comparison formatting with fake records: differences and labelled ratios, no sigma/pull)."""
import sys, os, json, glob, shutil, subprocess, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
S3 = sorted(glob.glob(os.path.join(RES, 'm3_runs', 's3', 'c*.out')))
M2DATA = os.path.join(RES, 'm2_runs', 'm2_laurent_L4_d40_r0.1_n96.jsonl')
tmp = tempfile.mkdtemp()
fails = 0


def gate(script, *a, allow=False):
    env = dict(os.environ)
    if allow: env['LRI_TEST_LEGACY_ALLOWLIST'] = TEST_ALLOW
    r = subprocess.run([sys.executable, os.path.join(HERE, script)] + list(a), capture_output=True, text=True, cwd=HERE, env=env)
    return r.returncode, r.stdout + r.stderr


def expect(name, rc, out, want_fail, needle=None):
    global fails
    ok = (rc != 0) == want_fail and (needle is None or needle in out)
    fails += not ok
    print(f'{"PASS" if ok else "FAIL"}  {name}: exit {rc}' + (f' ({needle!r} {"found" if needle in out else "NOT found"})' if needle else ''))


TEST_ALLOW = os.path.join(tmp, 'test_allowlist.json')
test_allow = {'files': {}}
def copy_s3(name, edit=None, drop=None):
    """copies of the archived s3 outputs (legacy); their hashes go to a test allowlist so that the gate's own checks,
    not the allowlist, decide (the gates refuse to publish while the override is set)"""
    import hashlib
    d = os.path.join(tmp, name); os.makedirs(d)
    for p in S3:
        if drop and p.endswith(drop): continue
        txt = open(p).read()
        if edit: txt = edit(os.path.basename(p), txt)
        q = os.path.join(d, os.path.basename(p))
        open(q, 'w').write(txt)
        test_allow['files'][os.path.relpath(os.path.abspath(q), os.path.abspath(RES))] = {'sha256': hashlib.sha256(txt.encode()).hexdigest()}
    json.dump(test_allow, open(TEST_ALLOW, 'w'))
    return d


def zero_delta0(fn, txt):
    out = []
    for line in txt.split('\n'):
        p = line.split()
        if p[:1] == ['S'] and p[1] == '0':
            p[4:8] = ['0x0p+0'] * 4; line = ' '.join(p)
        out.append(line)
    return '\n'.join(out)


def truncate(fn, txt):
    return txt[:len(txt) // 2] if fn == 'c2.out' else txt


def perturb(fn, txt):
    if fn != 'c0.out': return txt
    out, done = [], False
    for line in txt.split('\n'):
        p = line.split()
        if not done and p[:4] == ['S', '1', '0', '-3']:
            v = float.fromhex(p[4]); p[4] = (v * (1 + 1e-12)).hex(); line = ' '.join(p); done = True
        out.append(line)
    return '\n'.join(out)


rc, out = gate('m3_gate.py', copy_s3('zero', zero_delta0), '--tag', 'TEST', '--dry', allow=True)
expect('M3 with delta^0 data zeroed', rc, out, True, 'delta0 Laurent vs Bethe ansatz')
rc, out = gate('m3_gate.py', copy_s3('missing', drop='c5.out'), '--tag', 'TEST', '--dry', allow=True)
expect('M3 with sectors 167-186 missing', rc, out, True, 'sector set mismatch')
rc, out = gate('m3_gate.py', copy_s3('trunc', truncate), '--tag', 'TEST', '--dry', allow=True)
expect('M3 with a truncated file', rc, out, True, 'file validation failed')
rc, out = gate('m3_gate.py', copy_s3('perturb', perturb), '--tag', 'TEST', '--dry', allow=True)
expect('M3 with one delta^1 coefficient changed by 1e-12', rc, out, True, 'relation')
rc, out = gate('m3_gate.py', os.path.join(RES, 'm3_runs', 's3'), '--tag', 'TEST', '--dry')
expect('M3 archived s3 data (dry)', rc, out, False)
# M2
recs = [json.loads(l) for l in open(M2DATA)]
p = os.path.join(tmp, 'm2zero.jsonl')
with open(p, 'w') as f:
    for r in recs:
        r = dict(r); r['J'] = [['0', '0']] + r['J'][1:]; f.write(json.dumps(r) + '\n')
before = open(os.path.join(RES, 'M2_flow_coefficients.json')).read()
rc, out = gate('m2_gate.py', p)
expect('M2 with delta^0 data zeroed', rc, out, True, 'nothing published')
p2 = os.path.join(tmp, 'm2missing.jsonl')
with open(p2, 'w') as f:
    for r in recs[:-1]: f.write(json.dumps(r) + '\n')
rc, out = gate('m2_gate.py', p2)
expect('M2 with one contour point missing', rc, out, True, 'data: complete')
rc, out = gate('m2_gate.py', '../results/m2_runs/m2_laurent_L4_d40_r0.1_n96.jsonl')
expect('M2 archived data, stage 1 (record identical, not rewritten)', rc, out, False, 'identical to the existing record')
assert open(os.path.join(RES, 'M2_flow_coefficients.json')).read() == before, 'M2 record changed!'
# ---------------------------------------------------------------- fix round 2
import hashlib
sys.path.insert(0, HERE)
import provenance as pv
from cluster_assemble import read_many, OutputError
ENG = os.path.join(RES, 'm3_runs', 'g2g3', 'g3_K0.92_0.05_L2.out')
man = json.load(open(os.path.join(RES, 'm3_inputs', 'n3.manifest.json')))
kdd = [l for l in open(ENG) if l.startswith('# n ')][0].split()
kdd = kdd[kdd.index('Kdd') + 1:kdd.index('Kdd') + 5]
def synth(dirname, sector, a00, insha=man['input_sha256'], build='testbuild', k=kdd, complete=True, args=None, lev=3, split=(0, 1)):
    d = os.path.join(tmp, dirname); os.makedirs(d, exist_ok=True)
    txt = (f'sector {sector} split {split[0]} {split[1]} level {lev} mc 24 x0 5e-4 extra 10 rcfrac 8 radii rouche nodes 55\n'
           f'# fingerprint input_sha256 {insha} build {build} sector {sector} Kdd {" ".join(k)} level {lev} mc 24 x0 0x1.0624dd2f1a9fcp-11 extra 10 rcfrac 0x1p+3 split {split[0]} {split[1]}\n'
           f'A00 {a00}\n' + ('# complete\n' if complete else ''))
    open(os.path.join(d, f'sec{sector:03d}.txt'), 'w').write(txt)
    # runner sidecar (sector_check.sbatch format; required since fix round 3, MSC-022)
    open(os.path.join(d, f'sec{sector:03d}.txt.fp'), 'w').write(
        f'checker_sha256={"0" * 64} build={build} input_sha256={insha} '
        f'args={args or ("n3.txt %d %r %r -level %d -split %d %d" % (sector, float.fromhex(k[0]), float.fromhex(k[2]), lev, split[0], split[1]))}\n'
        f'output_sha256={hashlib.sha256(txt.encode()).hexdigest()}\n')
    return d
# MSC-012: NaN, empty
rc, out = gate('m3_sector_check.py', ENG, synth('nan', 6, 'nan 0x0p+0 0x0p+0 0x0p+0'))
expect('sector check with a NaN checker value', rc, out, True, 'nonfinite checker value')
os.makedirs(os.path.join(tmp, 'empty'))
rc, out = gate('m3_sector_check.py', ENG, os.path.join(tmp, 'empty'))
expect('sector check with no files', rc, out, True, 'empty comparison')
# MSC-013: fingerprint checks
rc, out = gate('m3_sector_check.py', ENG, synth('badin', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', insha='0' * 64))
expect('sector check with a wrong input hash', rc, out, True, 'input hash differs')
rc, out = gate('m3_sector_check.py', ENG, synth('badK', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', k=['0x1p-1', '0x0p+0', '0x0p+0', '0x0p+0']))
expect('sector check with a different K', rc, out, True, 'differs from the engine output K')
synth('twob', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', build='b1'); d = synth('twob', 8, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', build='b2')
rc, out = gate('m3_sector_check.py', ENG, d)
expect('sector check with two checker builds', rc, out, True, 'several builds')
rc, out = gate('m3_sector_check.py', ENG, synth('incompl', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', complete=False))
expect('sector check without completion marker', rc, out, True, 'no completion marker')
leg = os.path.join(RES, 'm3_runs', 'sector_check', 'sc2_K0.92_0.05_L3', 'sec006.txt')
d = os.path.join(tmp, 'legmod'); os.makedirs(d); open(os.path.join(d, 'sec006.txt'), 'w').write(open(leg).read().replace('A00 0x1', 'A00 0x1.0000000000001'))
rc, out = gate('m3_sector_check.py', ENG, d)
expect('modified legacy sector-check file', rc, out, True, 'legacy allowlist')
rc, out = gate('m3_sector_check.py', ENG, os.path.join(RES, 'm3_runs', 'sector_check', 'sc2_K0.92_0.05_L3'), '--tol', '1e-18', '--require-all')
expect('archived sector check (63 sectors, legacy allowlist)', rc, out, False, '63 of 63')
# MSC-014: merging chunks
d = os.path.join(tmp, 's3mod'); os.makedirs(d)
for p in S3:
    t = open(p).read()
    if p.endswith('c0.out'): t = t.replace('time ', 'time 0', 1)
    open(os.path.join(d, os.path.basename(p)), 'w').write(t)
try:
    read_many(sorted(glob.glob(os.path.join(d, 'c*.out'))), man); ok = False; msg = ''
except OutputError as e:
    ok = True; msg = str(e)
expect('merge with a modified legacy chunk', 0 if not ok else 1, msg, True, 'allowlist')
rc, out = gate('m3_gate.py', copy_s3('pubtest'), '--tag', 'TEST', allow=True)
expect('gate refuses to publish while the test allowlist override is set', rc, out, True, 'only --dry runs')
# MSC-015: concurrent write_once (independent processes started together)
WRITER = ("import sys; sys.path.insert(0, sys.argv[1]); import provenance as pv\n"
          "try:\n    print('created' if pv.write_once_text(sys.argv[2], sys.argv[3]) else 'identical')\n"
          "except pv.ProvenanceError:\n    print('refused')\n")
def race(path, texts):
    procs = [subprocess.Popen([sys.executable, '-c', WRITER, HERE, path, t], stdout=subprocess.PIPE, text=True) for t in texts]
    return [p.communicate()[0].strip() for p in procs]
target = os.path.join(tmp, 'race.json')
res = race(target, [f'content {i}\n' for i in range(16)])
ok = res.count('created') == 1 and res.count('refused') == 15 and open(target).read() == f'content {res.index("created")}\n'
expect(f'16 concurrent writers of different content: exactly one wins ({res.count("created")} created)', 0 if ok else 1, '', False)
res2 = race(os.path.join(tmp, 'race2.json'), ['same\n'] * 16)
expect('16 concurrent writers of identical content', 0 if res2.count('created') == 1 and res2.count('identical') == 15 else 1, '', False)
try:
    pv.publish_unit([(os.path.join(tmp, 'u1.json'), 'a'), (target, 'other')]); ok = False
except pv.ProvenanceError:
    ok = not os.path.exists(os.path.join(tmp, 'u1.json'))
expect('publication unit refuses as a whole when one file differs', 0 if ok else 1, '', False)
# MSC-017: --stage2 --dry
rc, out = gate('m3_gate.py', os.path.join(RES, 'm3_runs', 's3'), '--stage2', '--dry', '--expect-sha', '0' * 64)
expect('m3_gate --stage2 --dry rejected', rc, out, True, 'cannot be combined')
# ---------------------------------------------------------------- fix round 3
from cluster_assemble import read_out
import builds as buildmf
ONE = os.path.join(RES, 'm4_runs', 'prod', 'Cdd', 'c0_482.out')        # one-sector, bound-enabled, fingerprinted
def variant(name, edit, sidecar=True, fp_edit=None):
    """copy of ONE with an edited body; a matching runner sidecar (checksum recomputed) unless sidecar=False"""
    d = os.path.join(tmp, 'v_' + name); os.makedirs(d, exist_ok=True)
    q = os.path.join(d, os.path.basename(ONE)); txt = edit(open(ONE).read()); open(q, 'w').write(txt)
    if sidecar:
        l1 = open(ONE + '.fp').read().split('\n')[0]
        if fp_edit: l1 = fp_edit(l1)
        open(q + '.fp', 'w').write(l1 + '\noutput_sha256=' + hashlib.sha256(txt.encode()).hexdigest() + '\n')
    return q
def expect_err(name, fn, needle):
    try:
        fn(); rc, msg = 0, ''
    except (OutputError, buildmf.BuildError) as e:
        rc, msg = 1, str(e)
    expect(name, rc, msg, True, needle)
blines = [l for l in open(ONE).read().split('\n') if l.startswith('B ')]
# MSC-020: magnitude-bound records
expect_err('MSC-020 duplicate B record', lambda: read_out(variant('dupB', lambda s: s.replace(blines[3] + '\n', blines[3] + '\n' + blines[3] + '\n', 1))), 'duplicate B record')
expect_err('MSC-020 missing B record', lambda: read_out(variant('missB', lambda s: s.replace(blines[5] + '\n', '', 1))), 'magnitude-bound windows differ')
expect_err('MSC-020 B record with wrong arity', lambda: read_out(variant('arB', lambda s: s.replace(blines[2], blines[2] + ' 0x1p+0', 1))), 'fields')
expect_err('MSC-020 B records in an output without bound 1', lambda: read_out(variant('nob', lambda s: s.replace(' bound 1\n', ' bound 0\n', 1))), 'without bound 1')
q_ok = variant('okB', lambda s: s)
try:
    read_many([q_ok]); rc = 0
except OutputError as e:
    rc = 1; print(e)
expect('MSC-020/022 unmodified bound-enabled output with a verified sidecar is accepted', rc, '', False)
# MSC-022: runner sidecar verified by the consumer
q = variant('numedit', lambda s: s, sidecar=True)
open(q, 'a').close(); body = open(q).read().replace(blines[0], blines[0][:-1] + ('1' if blines[0][-1] != '1' else '2'), 1); open(q, 'w').write(body)
expect_err('MSC-022 output edited after the runner recorded its checksum', lambda: read_many([q]), 'runner-recorded output checksum')
expect_err('MSC-022 fingerprinted output without runner sidecar', lambda: read_many([variant('nofp', lambda s: s, sidecar=False)]), 'no runner fingerprint sidecar')
expect_err('MSC-022 sidecar arguments differ from the header', lambda: read_many([variant('fpargs', lambda s: s, fp_edit=lambda l: l.replace('-nseg 10', '-nseg 11'))]), 'arguments differ')
# MSC-021: approved builds and their precision
ok = buildmf.verify('b0da6f7bc003c829')['precision'] == 'double' and buildmf.verify('06c88f4c378ed21d')['precision'] == 'dd'
expect('MSC-021 production builds reproduce from git and carry double / dd', 0 if ok else 1, '', False)
expect_err('MSC-021 unknown build rejected', lambda: buildmf.verify('0123456789abcdef'), 'not an approved build')
fake = os.path.join(tmp, 'builds_fake.json'); json.dump({'b0da6f7bc003c829': {'approved': True, 'commit': '3bf22f0', 'extra_flags': '-DUSE_DOUBLE', 'precision': 'dd'}}, open(fake, 'w'))
old_m = buildmf.MANIFEST; buildmf.MANIFEST = fake; buildmf._cache.clear()
expect_err('MSC-021 double build recorded as dd rejected', lambda: buildmf.verify('b0da6f7bc003c829'), 'recorded precision')
buildmf.MANIFEST = old_m; buildmf._cache.clear()
# MSC-019 / MSC-023: C8 assembler in a throw-away copy of the code and records (no comparison is ever run here)
tc = os.path.join(tmp, 'c8tree'); shutil.copytree(HERE, os.path.join(tc, 'code'), ignore=shutil.ignore_patterns('__pycache__', '*.pkl'))
os.makedirs(os.path.join(tc, 'results'))
for n in ('frozen_records.json', 'M2_flow_coefficients.json', 'M3_flow_coefficients.json', 'M4A_flow_coefficients.json', 'M4B_flow_coefficients.json', 'builds.json',
          'M4B_flow_coefficients_v2.json', 'M4B_cx_check.json', 'M4B_cx_check_v2.json'):
    shutil.copy(os.path.join(RES, n), os.path.join(tc, 'results', n))
def c8(*a):
    r = subprocess.run([sys.executable, os.path.join(tc, 'code', 'c8_assemble.py')] + list(a), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
m4b = json.load(open(os.path.join(RES, 'M4B_flow_coefficients.json')))
def fake_m4b(name, total, factor):
    d = json.loads(json.dumps(m4b)); d['errors']['f_3_0_1_total'] = total; d['errors']['roundoff_factor'] = factor
    p = os.path.join(tc, 'results', name); txt = json.dumps(d); open(p, 'w').write(txt)
    reg = json.load(open(os.path.join(tc, 'results', 'frozen_records.json')))
    reg[name] = {'sha256': hashlib.sha256(txt.encode()).hexdigest(), 'frozen_in_commit': 'test', 'note': 'test'}
    json.dump(reg, open(os.path.join(tc, 'results', 'frozen_records.json'), 'w'))
fake_m4b('M4B_big.json', '0.5', '0.01')
rc, out = c8('--m4b', 'M4B_big.json', '--out', 'C8_big.json')
expect('MSC-023 sigma(C8) above 0.3 is not published', rc, out, True, 'sigma(C8) finite')
expect('MSC-023 ... and nothing was written', 0 if not os.path.exists(os.path.join(tc, 'results', 'C8_big.json')) else 1, '', False)
fake_m4b('M4B_lowfac.json', '0.1', '0.001')
rc, out = c8('--m4b', 'M4B_lowfac.json', '--out', 'C8_lowfac.json')
expect('MSC-023 roundoff factor below 0.01 rejected', rc, out, True, 'roundoff factor >= 0.01')
rc, out = c8('--compare', '--expect-sha', '0' * 64, '--m4b', 'M4B_flow_coefficients_v2.json', '--out', 'C8_none.json')   # the current M4B (v1 is superseded)
expect('MSC-019 comparison without a current C8 record / cx pass is PROVISIONAL and fails', rc, out, True, 'PROVISIONAL')
# MSC-024: cx check needs two distinct directories (dry: nothing published)
cxd = os.path.join(RES, 'm4_runs', 'prod', 'cxA')
r = subprocess.run([sys.executable, os.path.join(HERE, 'm4b_cx_check.py'), cxd, cxd, '--dry'], capture_output=True, text=True)
expect('MSC-024 same cx directory twice rejected', r.returncode, r.stdout, True, 'two distinct run directories')
r = subprocess.run([sys.executable, os.path.join(HERE, 'm4b_cx_check.py'), cxd, '--dry'], capture_output=True, text=True)
expect('MSC-024 a single cx directory rejected', r.returncode, r.stdout, True, 'both prescribed points')
# MSC-025: submitter state only after a successful sbatch; unreadable task files stop it
ts = os.path.join(tmp, 'subm'); os.makedirs(os.path.join(ts, 'code', 'm4')); os.makedirs(os.path.join(ts, 'logs')); os.makedirs(os.path.join(ts, 'results', 'm4')); os.makedirs(os.path.join(ts, 'bin'))
cm = os.path.join(ts, 'code', 'm4'); txt = open(os.path.join(HERE, 'submit_q.sh')).read()
txt = txt.replace('export PATH=$PATH:/cm/shared/apps/slurm/current/bin', f'export PATH={ts}/bin:$PATH').replace('sleep 60', 'sleep 0').replace('sleep 15', 'sleep 0').replace('sleep 30', 'sleep 0')
open(os.path.join(cm, 'submit_q.sh'), 'w').write(txt)
open(os.path.join(cm, 'ce'), 'w').write('#!/bin/bash\n'); os.chmod(os.path.join(cm, 'ce'), 0o755)
open(os.path.join(cm, 'a.tasks'), 'w').write('x/a1 -i n4.txt\n'); open(os.path.join(cm, 'b.tasks'), 'w').write('x/b1 -i n4.txt\n')
open(os.path.join(cm, 'q.txt'), 'w').write('./ce a.tasks\n./ce b.tasks\n')
open(os.path.join(ts, 'bin', 'sinfo'), 'w').write('#!/bin/bash\n[ "$3" = "defq" ] && echo "cn001 idle" || echo "cn099 alloc"\n')
open(os.path.join(ts, 'bin', 'squeue'), 'w').write('#!/bin/bash\n')
open(os.path.join(ts, 'bin', 'sbatch'), 'w').write(f'#!/bin/bash\nn=$(cat {ts}/n 2>/dev/null || echo 0); n=$((n+1)); echo $n > {ts}/n\n'
                                                    '[ $n -eq 1 ] && { echo "sbatch: error: submission failed"; exit 1; }\necho 1000$n\n')
for b in ('sinfo', 'squeue', 'sbatch'): os.chmod(os.path.join(ts, 'bin', b), 0o755)
r = subprocess.run(['bash', 'submit_q.sh', 'q.txt'], cwd=cm, capture_output=True, text=True, timeout=60)
state = open(os.path.join(ts, 'logs', 'submitted_q.txt')).read().split()
ok = r.returncode == 0 and state == ['a.tasks', 'b.tasks'] and 'sbatch failed' in r.stdout + r.stderr and open(os.path.join(ts, 'n')).read().strip() == '3'
expect('MSC-025 a failed sbatch is not recorded and is retried', 0 if ok else 1, '', False)
os.remove(os.path.join(cm, 'a.tasks')); os.remove(os.path.join(ts, 'logs', 'submitted_q.txt'))
r = subprocess.run(['bash', 'submit_q.sh', 'q.txt'], cwd=cm, capture_output=True, text=True, timeout=60)
expect('MSC-025 a missing task file stops the submitter', r.returncode, r.stdout + r.stderr, True, 'missing or unreadable')
# ---------------------------------------------------------------- fix round 4
# MSC-026: B windows must equal the S windows exactly (a complete but shifted window fails); valid k, j
def shift_window(s):
    out = []
    for line in s.split('\n'):
        p = line.split()
        if p[:1] == ['B'] and p[1] == '1' and p[2] == '2':
            p[3] = str(int(p[3]) + 1); line = ' '.join(p)
        out.append(line)
    return '\n'.join(out)
expect_err('MSC-026 complete B window shifted to other exponents', lambda: read_out(variant('shiftB', shift_window)), 'windows differ')
expect_err('MSC-026 B record with negative k', lambda: read_out(variant('negk', lambda s: s.replace(blines[0], 'B -1' + blines[0][3:], 1))), 'invalid (k, j)')
# MSC-027: roundoff epsilon from the verified build precision, both modes
ok = buildmf.eps('b0da6f7bc003c829') == 2.0 ** -53 and buildmf.eps('06c88f4c378ed21d') == 2.0 ** -104
expect('MSC-027 builds.eps: double 2^-53, double-double 2^-104', 0 if ok else 1, '', False)
r = subprocess.run([sys.executable, os.path.join(HERE, 'm4b_cx_check.py'), os.path.join(RES, 'm4_runs', 'prod', 'cxA'),
                    os.path.join(RES, 'm4_runs', 'prod', 'cxB'), '--amended', '--dry'], capture_output=True, text=True)
cxv2 = json.load(open(os.path.join(RES, 'M4B_cx_check_v2.json')))
ok = r.returncode == 0 and all(f'first-order roundoff bound {x["roundoff_bound_rel"]} relative' in r.stdout for x in cxv2['results'])
expect('MSC-027 cx check (double build) reproduces the frozen v2 roundoff bounds', 0 if ok else 1, '', False)
# MSC-029: authenticated engine side and validated checker runner arguments
d = os.path.join(tmp, 'engmod'); os.makedirs(d)
q = os.path.join(d, 'g3_K0.92_0.05_L2.out'); open(q, 'w').write(open(ENG).read().replace('time 1.03', 'time 1.04', 1))
rc, out = gate('m3_sector_check.py', q, synth('engauth', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0'))
expect('MSC-029 modified engine reference is not authenticated', rc, out, True, 'engine output not authenticated')
rc, out = gate('m3_sector_check.py', ENG, synth('argK', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', args='n3.txt 6 0.5 0.05 -level 3 -split 0 1'))
expect('MSC-029 checker runner arguments with a different K', rc, out, True, 'runner-recorded arguments disagree')
rc, out = gate('m3_sector_check.py', ENG, synth('argS', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', args='n3.txt 8 0.92 0.05 -level 3 -split 0 1'))
expect('MSC-029 checker runner arguments with a different sector', rc, out, True, 'runner-recorded arguments disagree')
rc, out = gate('m3_sector_check.py', ENG, synth('argL', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', args='n3.txt 6 0.92 0.05 -level 4 -split 0 1'))
expect('MSC-029 checker runner arguments with a different level', rc, out, True, 'runner-recorded arguments disagree')
for nrec in ('K0.92_L3', 'K0.92_L4', 'K1.05_L3'):
    rec = json.load(open(os.path.join(RES, f'M3_sector_check_{nrec}.json')))
    rc, out = gate('m3_sector_check.py', os.path.join(HERE, '..', rec['engine_output']['file']), *[os.path.join(HERE, '..', c['file']) for c in rec['checks']],
                   '--tol', rec['threshold'], '--verify-record', f'M3_sector_check_{nrec}.json')
    expect(f'MSC-029 frozen sector check {nrec} rebuilt byte-identically through the authenticated path', rc, out, False, 'IDENTICAL')
# MSC-028: a design file that differs from its pre-data commit fails the gate (in a local clone; nothing frozen changes)
cl = os.path.join(tmp, 'clone')
subprocess.run(['git', 'clone', '-q', '--local', os.path.join(HERE, '..'), cl], check=True)
with open(os.path.join(cl, 'results', 'm4_inputs', 'fix3b_design.json'), 'a') as fh: fh.write(' ')
P = os.path.join(cl, 'results', 'm4_runs', 'prod')
r = subprocess.run([sys.executable, os.path.join(cl, 'code', 'm4b_gate.py'), os.path.join(P, 'F'), os.path.join(P, 'C'), '--fine-dd', os.path.join(P, 'Fdd'),
                    '--coarse-dd', os.path.join(P, 'Cdd'), '--dry'], capture_output=True, text=True)
expect('MSC-028 modified fix3b_design.json rejected (git blob differs from e49157f)', r.returncode, r.stdout, True, 'differs')
r = subprocess.run([sys.executable, os.path.join(cl, 'code', 'm4_fix3b_design.py')], capture_output=True, text=True)
expect('MSC-028 the design script refuses to overwrite an existing design', r.returncode, r.stdout + r.stderr, True, 'refusing to overwrite')
# ---------------------------------------------------------------- fix round 5
# MSC-033: effective checker settings (real defaults, -nosplit => split -1 -1)
rc, out = gate('m3_sector_check.py', ENG, synth('nosplitbad', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', args='n3.txt 6 0.92 0.05 -level 3 -x0 0.0005 -nosplit'))
expect('MSC-033 -nosplit sidecar with a split 0 1 output', rc, out, True, 'split (effective (-1, -1)')
rc, out = gate('m3_sector_check.py', ENG, synth('nolevel4', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', lev=4, args='n3.txt 6 0.92 0.05 -x0 0.0005 -split 0 1'))
expect('MSC-033 omitted -level (default 3) with a level-4 output', rc, out, True, 'level (effective 3)')
rc, out = gate('m3_sector_check.py', ENG, synth('nox0', 6, '0x1p+4 0x0p+0 0x1p+4 0x0p+0', args='n3.txt 6 0.92 0.05 -split 0 1'))
expect('MSC-033 default arguments consistent with the fingerprint pass the argument check (reach the value comparison)',
       0 if ('max relative difference' in out and 'disagree' not in out) else 1, '', False)
# MSC-031: --report never truncates; registry, frozen records and symlinks refused (checked before any computation)
GARGS = [os.path.join(P, 'F'), os.path.join(P, 'C'), '--verify']
for name, target in (('registry', os.path.join(RES, 'frozen_records.json')), ('frozen record', os.path.join(RES, 'M4B_flow_coefficients_v2.json'))):
    before_b = open(target, 'rb').read()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'm4b_gate.py')] + GARGS + ['--report', target], capture_output=True, text=True)
    expect(f'MSC-031 --report onto the {name} refused', r.returncode, r.stdout + r.stderr, True, '--report refused')
    expect(f'MSC-031 ... and the {name} is byte-identical', 0 if open(target, 'rb').read() == before_b else 1, '', False)
lnk = os.path.join(tmp, 'rep_link.json'); os.symlink(os.path.join(tmp, 'rep_target.json'), lnk)
r = subprocess.run([sys.executable, os.path.join(HERE, 'm4b_gate.py')] + GARGS + ['--report', lnk], capture_output=True, text=True)
expect('MSC-031 symlinked report path refused', r.returncode, r.stdout + r.stderr, True, 'symlink')
expect('MSC-031 ... and nothing created behind the symlink', 0 if not os.path.exists(os.path.join(tmp, 'rep_target.json')) else 1, '', False)
# MSC-032: the frozen provenance sidecar must exist, be its committed blob and carry every mandatory field (local clone)
cl5 = os.path.join(tmp, 'clone5'); subprocess.run(['git', 'clone', '-q', '--local', os.path.join(HERE, '..'), cl5], check=True)
sidep = os.path.join(cl5, 'results', 'M4B_flow_coefficients_v2.provenance.json'); orig = open(sidep).read()
P5 = os.path.join(cl5, 'results', 'm4_runs', 'prod')
def verify5():
    r = subprocess.run([sys.executable, os.path.join(cl5, 'code', 'm4b_gate.py'), os.path.join(P5, 'F'), os.path.join(P5, 'C'), '--verify'], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
os.remove(sidep); rc, out = verify5()
expect('MSC-032 missing provenance sidecar fails verify', rc, out, True, 'not authentic')
open(sidep, 'w').write(''); rc, out = verify5()
expect('MSC-032 empty provenance sidecar fails verify', rc, out, True, 'not authentic')
for fld in ('sources', 'step0_maps', 'builds_manifest'):
    dsc = json.loads(orig); del dsc[fld]; open(sidep, 'w').write(json.dumps(dsc, indent=1, sort_keys=True) + '\n')
    rc, out = verify5()
    expect(f'MSC-032 sidecar without {fld} fails verify', rc, out, True, 'not authentic')
# MSC-034: comparison formatting (fake records in a throw-away tree; real values are never compared here)
tc5 = os.path.join(tmp, 'c8tree5'); shutil.copytree(HERE, os.path.join(tc5, 'code'), ignore=shutil.ignore_patterns('__pycache__', '*.pkl'))
os.makedirs(os.path.join(tc5, 'results'))
for n in ('frozen_records.json', 'M2_flow_coefficients.json', 'M3_flow_coefficients.json', 'M4A_flow_coefficients.json', 'M4B_flow_coefficients_v2.json', 'builds.json'):
    shutil.copy(os.path.join(RES, n), os.path.join(tc5, 'results', n))
reg5 = json.load(open(os.path.join(tc5, 'results', 'frozen_records.json')))
def fake(name, obj):
    txt = json.dumps(obj); open(os.path.join(tc5, 'results', name), 'w').write(txt)
    reg5[name] = {'sha256': hashlib.sha256(txt.encode()).hexdigest(), 'frozen_in_commit': 'test', 'note': 'test'}
    json.dump(reg5, open(os.path.join(tc5, 'results', 'frozen_records.json'), 'w'))
fm = json.load(open(os.path.join(RES, 'M4B_flow_coefficients_v2.json'))); fm['flow_coefficients']['f_3_0_1'] = str(float(fm['flow_coefficients']['f_3_0_1']) + 1000.0)
fake('M4B_fake.json', fm)
fake('M4B_cx_check_v2.json', {'pass': True, 'amendment': None})
r = subprocess.run([sys.executable, os.path.join(tc5, 'code', 'c8_assemble.py'), '--m4b', 'M4B_fake.json', '--out', 'C8_fake.json'], capture_output=True, text=True)
shaf = re.search(r'C8 record written: \S+ sha256 (\S+)', r.stdout)
r = subprocess.run([sys.executable, os.path.join(tc5, 'code', 'c8_assemble.py'), '--compare', '--expect-sha', shaf.group(1) if shaf else '0',
                    '--m4b', 'M4B_fake.json', '--out', 'C8_fake.json'], capture_output=True, text=True)
st2 = r.stdout.split('Stage 2: comparison')[-1] if 'Stage 2: comparison' in r.stdout else ''
ok = bool(st2) and 'Delta / (our empirical uncertainty)' in st2 and "ratio to that value's own quoted uncertainty" in st2 \
    and 'sigma' not in st2.split('checks (value')[0] and 'pull' not in st2.split('checks (value')[0]
expect('MSC-034 comparison prints differences and labelled ratios, no sigma/pull wording (fake records)', 0 if ok else 1, '', False)
shutil.rmtree(tmp)
print('ALL PASS' if fails == 0 else f'{fails} FAILED')
sys.exit(1 if fails else 0)
