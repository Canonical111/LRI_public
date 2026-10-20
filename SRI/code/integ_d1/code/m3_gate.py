"""M3 gate (fix round 1: MSC-005, MSC-006, MSC-009).
Stage 1 (blind): Laurent coefficients of J3^{(0)} and J3^{(1)} in w = 1 - K from series-mode engine outputs.
Every mandatory check has an explicit threshold and must pass before anything is published:
  files      every output validates (complete records, footers, unique sectors, consistent run parameters) and the
             merged sector set equals the independent manifest of the engine input exactly (patterns, term counts,
             input hash for fingerprinted files);
  ba         delta = 0 Laurent coefficients vs the exact Bethe ansatz (default <= 1e-20; plan minimum 1e-10);
  relations  EVERY delta^1 F-analyticity relation of m3_step0 (default <= 1e-20 relative);
  finite     every needed Laurent coefficient is present (resolved) and finite, flow coefficients finite;
  upstream   the M2 record matches the frozen-record registry and the step-0 maps are not stale.
Then results/<TAG>_flow_coefficients.json is written ONCE (an existing file must be byte-identical) with a
provenance sidecar (output files, engine input, step-0 maps, upstream M2 record).
Stage 2 (--stage2 --expect-sha SHA): read-only; the regenerated record must equal the recorded file, the expected
hash and (for TAG M3) the frozen-record registry; the sidecar must match; then C3..C7 vs the compendium
(default <= 1e-20 relative for all five: the plan asks 20 digits for C3-C5 and >= 8 for C6, C7; the 8-digit plan
threshold is also reported). Exit status 0 only if every check passes.
usage: python m3_gate.py OUTDIR_OR_FILES... [--manifest PATH] [--tag NAME] [--dry]
                         [--stage2 --expect-sha SHA] [--tol-ba X] [--tol-rel X] [--tol-c X]"""
import sys, os, json, hashlib, glob, subprocess, re
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
from cluster_assemble import read_many, assemble_ser, OutputError
from cluster_check import J3_BA
mp.mp.dps = 40
RES = pv.RES

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tol_ba = mp.mpf(opt('--tol-ba', '1e-20')); tol_rel = mp.mpf(opt('--tol-rel', '1e-20')); tol_c = mp.mpf(opt('--tol-c', '1e-20'))
PLAN67 = mp.mpf('1e-8')
tag = opt('--tag', 'M3')
expect_sha = opt('--expect-sha', None)
manifest_path = opt('--manifest', os.path.join(RES, 'm3_inputs', 'n3.manifest.json'))
stage2 = '--stage2' in args
if stage2: args.remove('--stage2')
dry = '--dry' in args
if dry: args.remove('--dry')
if stage2 and not expect_sha:
    sys.exit('stage 2 needs --expect-sha (the hash recorded by the blind stage 1)')
if os.environ.get('LRI_TEST_LEGACY_ALLOWLIST') and not dry:
    sys.exit('LRI_TEST_LEGACY_ALLOWLIST is set (test override): only --dry runs are allowed')
if stage2 and dry:
    sys.exit('--dry cannot be combined with --stage2 (stage 2 is already read-only; run it without --dry)')   # MSC-017
files = []
for a in args:
    files += sorted(glob.glob(os.path.join(a, '*.out'))) if os.path.isdir(a) else [a]

checks = []
def check(name, value, thr, ok=None):
    ok = (mp.isfinite(value) and value <= thr) if ok is None else ok
    checks.append((name, value, thr, bool(ok)))
    return ok
def report_and_exit(label):
    print(f'\n{label} checks (value / threshold / result):')
    for name, v, t, ok in checks:
        print(f'  {name:52s} {mp.nstr(v, 3) if not isinstance(v, str) else v:>10}  <= {mp.nstr(t, 2) if not isinstance(t, str) else t:>8}  {"PASS" if ok else "FAIL"}')
    allok = all(c[3] for c in checks)
    print(label, 'PASS' if allok else 'FAIL')
    sys.exit(0 if allok else 1)

# ---------------------------------------------------------------- upstream and inputs
try:
    m2sha = pv.verify_frozen('M2_flow_coefficients.json'); ok = True
except pv.ProvenanceError as e:
    print(e); ok = False; m2sha = None
check('upstream M2 record matches the frozen registry', 'ok' if ok else 'bad', 'all', ok)
try:
    resp_raw, pv_resp = pv.load_step0('m3_step0_response.json')
    base_raw, pv_base = pv.load_step0('m3_step0_F2base.json')
    ok = pv_resp['upstream'].get('M2_flow_coefficients.json') == m2sha == pv_base['upstream'].get('M2_flow_coefficients.json')
except pv.ProvenanceError as e:
    print(e); ok = False
check('step-0 maps current and built from that M2 record', 'ok' if ok else 'bad', 'all', ok)
if not all(c[3] for c in checks):
    report_and_exit(f'{tag} GATE')
manifest = json.load(open(manifest_path))
try:
    hdr0, secs, hdrs = read_many(files, manifest)
    ok = hdr0['mode'] == 'ser' and int(hdr0['n']) == 3 and int(hdr0['kmax']) >= 1
    msg = 'ok' if ok else 'wrong mode/n/kmax'
except (OutputError, OSError, KeyError, ValueError) as e:
    print('file validation failed:', e); ok = False; msg = 'bad'
check(f'files: {len(files)} outputs complete, sector set == manifest ({manifest["nsec"]})', msg, 'all', ok)
if not ok:
    report_and_exit(f'{tag} GATE')
print(f'{len(secs)} sectors merged from {len(files)} files; run parameters: ' +
      ', '.join(f'{k} {hdr0[k]}' for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS')))
cpu = sum(s['time'] for s in secs.values())
J, A, top = assemble_ser(3, secs, int(hdr0['kmax']), elo=-9, ehi=4)
c = {k: {e: mp.re(v) for e, v in J[k].items()} for k in J}
fin = all(mp.isfinite(v) for k in c for v in c[k].values())
check('Laurent coefficients finite', 'ok' if fin else 'bad', 'all', fin)

# ---------------------------------------------------------------- (1) delta = 0 vs the Bethe ansatz
def laurent_exact(fun, lo, hi, rad=mp.mpf('0.04'), npts=400):
    with mp.workdps(60):
        pts = [rad * mp.expjpi(2 * mp.mpf(m) / npts) for m in range(npts)]
        vals = [fun(1 - p) for p in pts]
        return {j: mp.re(sum(v * p ** (-j) for v, p in zip(vals, pts)) / npts) for j in range(lo, hi + 1)}
ba = laurent_exact(J3_BA, -9, max(c[0]))
print('\ndelta = 0 Laurent coefficients of J3 vs the exact Bethe ansatz:')
dev0 = 0
for e in sorted(c[0]):
    d = abs(c[0][e] - ba[e]); sc = max(abs(ba[e]), 1)
    dev0 = max(dev0, d / sc)
    print(f'  w^{e:3d}: engine {mp.nstr(c[0][e], 28):>36}  exact {mp.nstr(ba[e], 28):>36}  diff/max(|exact|,1) {mp.nstr(d / sc, 3)}')
print('  max deviation:', mp.nstr(dev0, 3))
check('delta0 Laurent vs Bethe ansatz (max rel, w^-9..w^2)', dev0, tol_ba)

# ---------------------------------------------------------------- (2) F-analyticity relations and flow coefficients
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in dd.items()} for k, dd in resp_raw.items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in base_raw.items()}
unresolved = []
def c3(k, j):
    if k not in c: return mp.mpf(0)
    if j < min(c[k]): return mp.mpf(0)      # below the engine window: identically zero (no deeper poles)
    if j > max(c[k]):
        unresolved.append((k, j)); return mp.nan
    return c[k][j]
def F2(target):
    tot = base.get(target, mp.mpf(0))
    for src, dd in resp.items():
        if target in dd and src[0] == 1: tot += dd[target] * c3(*src)
    return tot
print('\nF-analyticity relations at delta^1 (must vanish):')
rel_max = 0
for j in range(-12, 0):
    v = F2((1, j))
    terms = [abs(base.get((1, j), 0))] + [abs(dd[(1, j)] * c3(*s)) for s, dd in resp.items() if (1, j) in dd and s[0] == 1]
    sc = max(terms + [mp.mpf(1)])
    r = abs(v) / sc
    rel_max = max(rel_max, r)
    print(f'  [d^1 w^{j:3d}] = {mp.nstr(v, 5):>12}   (scale {mp.nstr(sc, 3)}, relative {mp.nstr(r, 3)})')
    check(f'relation [d^1 w^{j}] (relative)', r, tol_rel)
f = {'f_2_0_1': F2((1, 0)), 'f_2_1_1': -F2((1, 1))}
ok = not unresolved and all(mp.isfinite(v) for v in f.values())
check('flow coefficients resolved and finite', 'ok' if ok else f'unresolved {unresolved[:3]}', 'all', ok)
# the published record (format unchanged since the frozen M3 record)
out = {'flow_coefficients': {k: mp.nstr(v, 30) for k, v in f.items()},
       'raw_laurent': {str(k): {str(e): mp.nstr(v, 32) for e, v in c[k].items()} for k in c},
       'delta0_vs_BA_max_rel': mp.nstr(dev0, 3), 'relations_max_rel': mp.nstr(rel_max, 3),
       'run': {k: hdr0[k] for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS')},
       'sources': [os.path.relpath(x, os.path.join(HERE, '..')) for x in files], 'engine_cpu_seconds': round(cpu, 1)}
blob = json.dumps(out, indent=1, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()
rec = os.path.join(RES, f'{tag}_flow_coefficients.json')
side = os.path.join(RES, f'{tag}_flow_coefficients.provenance.json')
sidecar = json.dumps({'record': os.path.basename(rec), 'record_sha256': sha,
                      'sources': {os.path.relpath(x, os.path.join(HERE, '..')): pv.sha256_file(x) for x in files},
                      'engine_input': {'manifest': os.path.relpath(manifest_path, os.path.join(HERE, '..')),
                                       'input_sha256': manifest['input_sha256'], 'nsec': manifest['nsec']},
                      'output_fingerprints': {os.path.relpath(p, os.path.join(HERE, '..')): (h['fingerprint'] or 'legacy (pre-fix-round-1 engine)') for p, h in hdrs.items()},
                      'step0_maps': {n: pv.sha256_file(os.path.join(RES, n)) for n in ('m3_step0_response.json', 'm3_step0_F2base.json')},
                      'step0_generator': {pv_resp['generator']: pv_resp['generator_sha256']},
                      'upstream_records': {'M2_flow_coefficients.json': m2sha}}, indent=1, sort_keys=True) + '\n'
for k, v in f.items(): print(f'  {k} = {mp.nstr(v, 25)}')
if dry:
    print('\n(dry run: nothing written)  sha256 of the would-be record', sha)
    report_and_exit(f'{tag} GATE (dry)')
if not stage2:
    if not all(ch[3] for ch in checks):
        print('\nstage 1 checks failed: nothing published')
        report_and_exit(f'{tag} GATE STAGE 1')
    created = pv.publish_unit([(rec, blob), (side, sidecar)])[0]
    print(f'\nflow coefficients {"written" if created else "identical to the existing record"}: '
          f'{os.path.relpath(rec, HERE)} sha256', sha)
    report_and_exit(f'{tag} GATE STAGE 1')

# ---------------------------------------------------------------- stage 2: C3..C7 (read-only)
ok = os.path.exists(rec) and open(rec).read() == blob and sha == expect_sha
check('record identical to the recorded file and --expect-sha', 'ok' if ok else 'bad', 'all', ok)
if f'{tag}_flow_coefficients.json' in pv.registry():
    try:
        pv.verify_frozen(f'{tag}_flow_coefficients.json', expect_sha); ok = True
    except pv.ProvenanceError as e:
        print(e); ok = False
    check('record matches the frozen-record registry', 'ok' if ok else 'bad', 'all', ok)
ok = os.path.exists(side) and open(side).read() == sidecar
check('provenance sidecar matches outputs, input, maps, M2', 'ok' if ok else 'bad', 'all', ok)
from mscheme_numeric import C_numeric
from one_bubble import taylor_coeffs
fl = {(1, 0, 0): mp.mpf(1)}
ob = taylor_coeffs(N=4, nmax=4)
for (nn, k), v in ob.items():
    if k >= 1: fl[(0, nn, k)] = v
outba = subprocess.run([sys.executable, os.path.join(HERE, 'ba_numeric4.py'), '80'], capture_output=True, text=True).stdout
for line in outba.splitlines():
    mm = re.match(r'\((\d+), (\d+)\) (\S+)', line)
    if mm: fl[(int(mm.group(1)), int(mm.group(2)), 0)] = mp.mpf(mm.group(3))
resid = re.search(r'residual norm (\S+)', outba)
check('Bethe-ansatz fit residual (degree 4)', mp.mpf(resid.group(1)) if resid else mp.inf, mp.mpf('1e-40'))
m2 = json.load(open(os.path.join(RES, 'M2_flow_coefficients.json')))['flow_coefficients']
for key, v in m2.items():
    _, a, b, k = key.split('_'); fl[(int(a), int(b), int(k))] = mp.mpf(v)
for key, v in f.items():
    _, a, b, k = key.split('_'); fl[(int(a), int(b), int(k))] = v
need7 = [(0, 0, 1), (0, 0, 2), (0, 0, 3), (0, 1, 1), (0, 1, 2), (0, 1, 3), (0, 2, 1), (0, 2, 2), (0, 3, 1), (1, 0, 0), (1, 0, 1),
         (1, 0, 2), (1, 1, 0), (1, 1, 1), (1, 1, 2), (1, 2, 0), (1, 2, 1), (1, 3, 0), (2, 0, 0), (2, 0, 1), (2, 1, 0), (2, 1, 1),
         (2, 2, 0), (3, 0, 0), (3, 1, 0)]
miss = [k for k in need7 if k not in fl or not mp.isfinite(fl[k])]
check('all inputs of C3..C7 resolved and finite', 'ok' if not miss else f'missing {miss[:3]}', 'all', not miss)
if miss:
    report_and_exit(f'{tag} GATE')
fuse = {k: fl[k] for k in need7}   # degree-4 coefficients that do not enter C7 are set to zero
Cs = C_numeric(fuse, 4)
z = mp.zeta
exact = {3: mp.mpf(39) / 16 + 2 * z(2),
         4: 4 - 4 * z(2) - 8 * z(3),
         5: mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z(2) + 24 * z(3) + mp.mpf(49) / 2 * z(4),
         6: 26 - 38 * z(2) + 104 * z(3) - 80 * z(4) - 272 * z(5) + 112 * z(2) * z(3),
         7: mp.mpf(1798583) / 32768 - mp.mpf(90637) / 1024 * z(2) + mp.mpf(453) / 4 * z(3) - mp.mpf(16835) / 64 * z(4)
            + 1224 * z(5) - 540 * z(2) * z(3) + mp.mpf(4335) / 8 * z(6) - 320 * z(3) ** 2}
print('\nStage 2: C_n from the magnetization-scheme pipeline vs the compendium closed forms')
for nn in (3, 4, 5, 6, 7):
    v, ref = Cs[nn - 1], exact[nn]
    d = v - ref; rel = abs(d / ref)
    print(f'  C{nn}: pipeline {mp.nstr(v, 22):>28}  exact {mp.nstr(ref, 22):>28}  diff {mp.nstr(d, 3):>10}  '
          f'agreeing digits {mp.nstr(-mp.log10(rel) if rel else mp.inf, 3)}')
    check(f'C{nn} vs compendium (relative)', rel, tol_c)
    if nn >= 6: check(f'C{nn} vs compendium at the plan threshold', rel, PLAN67)
report_and_exit(f'{tag} GATE')
