"""MSC-011 comparison of independent sector integrals (sector_check.cpp) with the engine's per-sector values.
Fix round 2 (MSC-012, MSC-013):
  - every checker value, engine value and difference must be finite (checked one by one, before aggregation);
  - an empty comparison fails;
  - every checker file must be complete ('# complete') and either carry a fingerprint (input sha256 equal to the
    manifest's, exact K equal to the engine output's K, one build for all files, recorded level and arguments) or be an
    archived pre-fingerprint file whose sha256 is listed, with its K and level, in
    results/m3_runs/sector_check/legacy_allowlist.json;
  - --record NAME publishes the accepted comparison (file hashes, engine output hash, manifest) as a frozen record.
Fix round 3 (MSC-022): a fingerprinted checker file is consumed only with the runner sidecar FILE.fp
(sector_check.sbatch: 'checker_sha256=.. build=.. input_sha256=.. args=..' and 'output_sha256=..', checksum, build and
input verified) or, for files archived without a sidecar, when its path and sha256 are listed in an already frozen
M3_sector_check_*.json record (registry-verified).
Fix round 4 (MSC-029): the engine output is read through the authenticated read_many path (runner sidecar for
fingerprinted outputs, hash-listed legacy allowlist otherwise) against the n3 manifest; an intentional subset must be
declared with --engine-subset (then exactly the sectors present are accepted). For checker files with a runner
sidecar the recorded argument string 'INPUT SECTOR KRE KIM [-level L] [-mc M] [-x0 X] [-extra E] [-rcfrac R]
[-split P Q | -nosplit] [-Kdd ...]' must agree with the output: input name, sector, K (as doubles) and every
numerical option given. Hash-bound legacy files (allowlist) and frozen-listed files stay explicit exceptions.
usage: python m3_sector_check.py ENGINE_CX_OUTPUT CHECK_DIR_OR_FILES... [--tol X] [--require-all]
                                 [--manifest PATH] [--record NAME | --verify-record NAME] [--engine-subset]"""
import sys, os, glob, re, json, hashlib
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cluster_assemble import read_out, read_many, OutputError
import provenance as pv
import cluster_gen
mp.mp.dps = 40
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tol = mp.mpf(opt('--tol', '1e-20'))
manifest_path = opt('--manifest', os.path.join(pv.RES, 'm3_inputs', 'n3.manifest.json'))
record = opt('--record', None)
verify_record = opt('--verify-record', None)     # fix round 4: rebuild a frozen record's content and compare, never write
require_all = '--require-all' in args
if require_all: args.remove('--require-all')
engine_subset = '--engine-subset' in args
if engine_subset: args.remove('--engine-subset')
eng, srcs = args[0], args[1:]
files = []
for a in srcs:
    files += sorted(glob.glob(os.path.join(a, 'sec*.txt'))) if os.path.isdir(a) else [a]
problems = []
def fail(msg):
    problems.append(msg)

try:
    _h0, _s0 = read_out(eng)
    hdr, secs, _hd = read_many([eng], json.load(open(manifest_path)), expected=(sorted(_s0) if engine_subset else None))
except (OutputError, OSError, ValueError) as e:
    print('engine output not authenticated:', e); print('SECTOR CHECK FAIL'); sys.exit(1)
hx = lambda x: mp.mpf(float.fromhex(x))
Keng = mp.mpc(hx(hdr['Kdd'][0]) + hx(hdr['Kdd'][1]), hx(hdr['Kdd'][2]) + hx(hdr['Kdd'][3]))
manifest = json.load(open(manifest_path))
allow_path = os.path.join(pv.RES, 'm3_runs', 'sector_check', 'legacy_allowlist.json')
allow = json.load(open(allow_path))['files'] if os.path.exists(allow_path) else {}
cluster_gen.radii = lambda sec, d, grid=None: [0.0] * d
data = cluster_gen.generate(3, verbose=False)
dc, sid = [], 0
data_terms = [s['terms'] for p in data['patterns'] for s in p['sectors']]
for p in data['patterns']:
    for s in p['sectors']:
        if any(sum(1 for a in t['a'] if a <= -2) >= 2 for t in s['terms']): dc.append(sid)
        sid += 1
SC_DEFAULTS = {'level': 3, 'mc': 24, 'extra': 10, 'x0': 5e-4, 'rcfrac': 8.0}     # sector_check.cpp struct Params
def auto_split(s):
    """sector_check.cpp: without -split/-nosplit the first term (input order) with two variables of a <= -2 gives
    (p, q) (first such pair); none -> no split (-1, -1)"""
    for t in data_terms[s]:
        a = t['a']
        for p in range(len(a)):
            for q in range(p + 1, len(a)):
                if a[p] <= -2 and a[q] <= -2:
                    return (p, q)
    return (-1, -1)
def runner_args_mismatch(a, s, fpd, lev, hdr_split):
    """MSC-029/033: normalize the checker runner's argument list with sector_check.cpp's defaults and option semantics
    (sequential parsing, later options override, -Kdd overrides Kre/Kim, -nosplit => split -1 -1, no split option =>
    the automatic choice) and compare EVERY effective setting with the output fingerprint and header; '' if consistent"""
    try:
        if len(a) < 4: return 'too few arguments'
        if os.path.basename(a[0]) != manifest['input']: return f'input {a[0]}'
        if int(a[1]) != s: return f'sector {a[1]}'
        eff = dict(SC_DEFAULTS); K = (float(a[2]), 0.0, float(a[3]), 0.0); split = None; nosplit = False
        i = 4
        while i < len(a):
            o = a[i]
            if o == '-nosplit': nosplit = True; i += 1
            elif o == '-split': split = (int(a[i + 1]), int(a[i + 2])); i += 3
            elif o == '-Kdd': K = tuple(float(x) for x in a[i + 1:i + 5]); i += 5
            elif o in ('-level', '-mc', '-extra'): eff[o[1:]] = int(a[i + 1]); i += 2
            elif o in ('-x0', '-rcfrac'): eff[o[1:]] = float(a[i + 1]); i += 2
            else: return f'unknown option {o}'
        if nosplit: split = (-1, -1)
        elif split is None: split = auto_split(s)
        if tuple(float.fromhex(x) for x in fpd['Kdd']) != K: return 'K'
        if eff['level'] != lev or int(fpd['level']) != eff['level']: return f'level (effective {eff["level"]})'
        if int(fpd['mc']) != eff['mc']: return f'mc (effective {eff["mc"]})'
        if int(fpd['extra']) != eff['extra']: return f'extra (effective {eff["extra"]})'
        if float.fromhex(fpd['x0']) != eff['x0']: return f'x0 (effective {eff["x0"]})'
        if float.fromhex(fpd['rcfrac']) != eff['rcfrac']: return f'rcfrac (effective {eff["rcfrac"]})'
        fsplit = tuple(int(x) for x in fpd['split'])
        if fsplit != split or hdr_split != split: return f'split (effective {split}, fingerprint {fsplit}, header {hdr_split})'
    except (ValueError, IndexError, KeyError) as e:
        return f'unparsable arguments ({e.__class__.__name__})'
    return ''


def frozen_listing():
    """(path, sha256) pairs of checker files listed in frozen, registry-verified sector-check records"""
    out = set()
    for name in pv.registry():
        if not name.startswith('M3_sector_check_'): continue
        try:
            pv.verify_frozen(name)
        except pv.ProvenanceError:
            continue
        for ch in json.load(open(os.path.join(pv.RES, name))).get('checks', []):
            out.add((ch.get('file'), ch.get('sha256')))
    return out
FROZEN = frozen_listing()
rows, builds, worst, seen = [], set(), mp.mpf(0), set()
for fn in files:
    txt = open(fn).read()
    sha = hashlib.sha256(txt.encode()).hexdigest()
    L = txt.split('\n')
    head = [l for l in L if l.startswith('sector ')]
    a00 = [l for l in L if l.startswith('A00 ')]
    fpl = [l for l in L if l.startswith('# fingerprint ')]
    if len(head) != 1 or len(a00) != 1:
        fail(f'{fn}: incomplete or malformed'); continue
    m = re.match(r'sector (\d+) split (-?\d+) (-?\d+) level (\d+)', head[0])
    s, lev = int(m.group(1)), int(m.group(4))
    if fpl:
        fp = fpl[0].split()[2:]; fpd = {}; i = 0
        nval = {'Kdd': 4, 'split': 2}
        while i < len(fp):
            kname = fp[i]; nv = nval.get(kname, 1)
            fpd[kname] = fp[i + 1] if nv == 1 else fp[i + 1:i + 1 + nv]; i += 1 + nv
        kk = fpd['Kdd']
        Kchk = mp.mpc(hx(kk[0]) + hx(kk[1]), hx(kk[2]) + hx(kk[3]))
        if '# complete' not in L: fail(f'{fn}: no completion marker'); continue
        if fpd.get('input_sha256') != manifest['input_sha256']: fail(f'{fn}: input hash differs from the manifest'); continue
        if int(fpd.get('sector', -1)) != s or int(fpd.get('level', -1)) != lev: fail(f'{fn}: fingerprint does not match the header'); continue
        if os.path.isfile(fn + '.fp'):
            sl = open(fn + '.fp').read().split('\n')
            mm = re.match(r'checker_sha256=(\S+) build=(\S+) input_sha256=(\S+) args=(.*)$', sl[0] if sl else '')
            if not mm or len(sl) < 2 or sl[1] != 'output_sha256=' + sha or mm.group(2) != fpd.get('build') or mm.group(3) != fpd.get('input_sha256'):
                fail(f'{fn}: runner sidecar does not verify (checksum/build/input)'); continue
            bad = runner_args_mismatch(mm.group(4).split(), s, fpd, lev, (int(m.group(2)), int(m.group(3))))
            if bad:
                fail(f'{fn}: runner-recorded arguments disagree with the output ({bad})'); continue
        elif (os.path.relpath(fn, os.path.dirname(pv.RES)), sha) not in FROZEN:
            fail(f'{fn}: no runner sidecar and not listed (path + sha256) in a frozen sector-check record'); continue
        builds.add(fpd.get('build'))
        kind = 'fingerprint ' + fpd.get('build')
    else:
        rel = os.path.relpath(os.path.abspath(fn), pv.RES)
        ent = allow.get(rel)
        if ent is None or ent['sha256'] != sha:
            fail(f'{fn}: no fingerprint and not in the hash-listed legacy allowlist'); continue
        if ent['level'] != lev or ent['sector'] != s: fail(f'{fn}: allowlist level/sector mismatch'); continue
        Kchk = mp.mpc(mp.mpf(float(ent['K'][0])), mp.mpf(float(ent['K'][1])))
        kind = 'legacy ' + ent['checker_sha256'][:16]
    if Kchk != Keng:
        fail(f'{fn}: checker K {Kchk} differs from the engine output K {Keng}'); continue
    p = a00[0].split()
    v = mp.mpc(hx(p[1]) + hx(p[2]), hx(p[3]) + hx(p[4]))
    if s not in secs: fail(f'{fn}: sector {s} not in the engine output'); continue
    e = secs[s]['A'][(0, 0)]
    if not (mp.isfinite(v.real) and mp.isfinite(v.imag)): fail(f'{fn}: nonfinite checker value'); continue
    if not (mp.isfinite(e.real) and mp.isfinite(e.imag)) or e == 0: fail(f'sector {s}: nonfinite or zero engine value'); continue
    d = abs(v - e) / abs(e)
    if not mp.isfinite(d): fail(f'{fn}: nonfinite difference'); continue
    if s in seen: fail(f'sector {s} checked twice'); continue
    seen.add(s)
    worst = max(worst, d)
    rows.append(dict(sector=s, split=f'{m.group(2)},{m.group(3)}', level=lev, file=os.path.relpath(fn, os.path.dirname(pv.RES)),
                     sha256=sha, kind=kind, value=v, rel_diff=d))
if len(builds) > 1:
    fail(f'checker files from several builds: {sorted(builds)}')
if not rows:
    fail('empty comparison')
missing = sorted(set(dc) - seen)
if require_all and missing:
    fail(f'double-contact sectors without a check: {missing}')
K = hdr['K']
print(f'independent sector check at K = {K[0]} + {K[1]} i vs engine output {os.path.basename(eng)} '
      f'(grid nseg {hdr["nseg"]}, m {hdr["m"]}, nplain {hdr["nplain"]})')
print(f'{"sector":>6} {"split":>7} {"lvl":>3}  {"checker A00":>52}  rel. diff   source')
for r in sorted(rows, key=lambda r: r['sector']):
    print(f'{r["sector"]:6d} {r["split"]:>7} {r["level"]:3d}  {mp.nstr(r["value"], 22):>52}  {mp.nstr(r["rel_diff"], 3):9}  {r["kind"]}')
print(f'{len(rows)} sectors checked ({sum(1 for r in rows if r["sector"] in dc)} of {len(dc)} double-contact sectors); '
      f'max relative difference {mp.nstr(worst, 3)}; threshold {mp.nstr(tol, 2)}')
for pr in problems: print('PROBLEM:', pr)
ok = not problems and worst <= tol
print('SECTOR CHECK', 'PASS' if ok else 'FAIL')
if ok and (record or verify_record):
    out = {'engine_output': {'file': os.path.relpath(eng, os.path.dirname(pv.RES)), 'sha256': pv.sha256_file(eng)},
           'manifest_input_sha256': manifest['input_sha256'], 'K': [K[0], K[1]], 'threshold': mp.nstr(tol, 3),
           'max_rel_diff': mp.nstr(worst, 3), 'double_contact_sectors_checked': sum(1 for r in rows if r['sector'] in dc),
           'checks': [{k: (mp.nstr(v, 3) if k == 'rel_diff' else v) for k, v in r.items() if k != 'value'} for r in sorted(rows, key=lambda r: r['sector'])]}
    text = json.dumps(out, indent=1, sort_keys=True) + '\n'
    if verify_record:
        want = pv.verify_frozen(verify_record)
        got = hashlib.sha256(text.encode()).hexdigest()
        same = got == want and text == open(os.path.join(pv.RES, verify_record)).read()
        print('VERIFY', verify_record, 'IDENTICAL' if same else f'DIFFERS (rebuilt {got}, frozen {want})')
        sys.exit(0 if same else 1)
    path = os.path.join(pv.RES, record)
    pv.publish_unit([(path, text)], register=(record, 'fix-round-2', 'accepted MSC-011 sector-check comparison'))
    print('record', record, 'sha256', pv.sha256_file(path))
sys.exit(0 if ok else 1)
