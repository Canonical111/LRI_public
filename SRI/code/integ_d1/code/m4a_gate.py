"""M4 part A gate: three bubbles at delta^2 (f_2_0_2), blind.
Inputs: two complete series-mode n = 3, kmax = 2 runs at different quadrature grids (FINE, COARSE; directories of
*.out files). Every mandatory check has an explicit threshold and must pass before anything is published:
  upstream   M2 and M3 records match the frozen-record registry; the m3_step0 maps are current and built from M2;
  files      every output validates, the merged sector set of each level equals the n = 3 manifest exactly, one
             engine build for both levels, mode ser, n 3, kmax 2;
  ba         delta^0 Laurent coefficients vs the exact Bethe ansatz (fine level, default <= 1e-20);
  m3         delta^1 Laurent coefficients vs the frozen M3 record (fine level, default <= 1e-18 relative to
             max(|c|, 1)); the delta^1 relations of M3 are implied;
  relations  EVERY delta^2 F-analyticity relation F2[d^2 w^j] = 0, j = -12..-1, of m3_step0 with the measured
             J3^(1), J3^(2) (fine level, default <= 1e-15 relative; the coarse level is reported, default <= 1e-10);
  f202       f_2_0_2 = F2[d^2 w^0] resolved and finite at both levels; two-grid error |fine - coarse| <= 0.01.
The record results/M4A_flow_coefficients.json (f_2_0_2, its two-grid error, raw Laurent coefficients) and a
provenance sidecar are published once and added to the frozen-record registry. No C_n is computed here.
usage: python m4a_gate.py FINE_DIR COARSE_DIR [--manifest PATH] [--tol-ba X] [--tol-m3 X] [--tol-rel X]
                          [--tol-rel-coarse X] [--tol-f X] [--dry]"""
import sys, os, json, hashlib, glob, subprocess
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
from cluster_assemble import read_many, assemble_ser, OutputError
from cluster_check import J3_BA
mp.mp.dps = 40
RES = pv.RES
ROOT = os.path.join(HERE, '..')

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tol_ba = mp.mpf(opt('--tol-ba', '1e-20')); tol_m3 = mp.mpf(opt('--tol-m3', '1e-18'))
tol_rel = mp.mpf(opt('--tol-rel', '1e-15')); tol_relc = mp.mpf(opt('--tol-rel-coarse', '1e-10'))
tol_f = mp.mpf(opt('--tol-f', '0.01'))
manifest_path = opt('--manifest', os.path.join(RES, 'm3_inputs', 'n3.manifest.json'))
dry = '--dry' in args
if dry: args.remove('--dry')
if os.environ.get('LRI_TEST_LEGACY_ALLOWLIST') and not dry:
    sys.exit('LRI_TEST_LEGACY_ALLOWLIST is set (test override): only --dry runs are allowed')
if len(args) != 2:
    sys.exit(__doc__)
levels = {'fine': args[0], 'coarse': args[1]}
TAG = 'M4A'

checks = []
def check(name, value, thr, ok=None):
    ok = (mp.isfinite(value) and value <= thr) if ok is None else ok
    checks.append((name, value, thr, bool(ok)))
    return ok
def report_and_exit(label):
    print(f'\n{label} checks (value / threshold / result):')
    for name, v, t, ok in checks:
        print(f'  {name:62s} {mp.nstr(v, 3) if not isinstance(v, str) else v:>10}  <= {mp.nstr(t, 2) if not isinstance(t, str) else t:>8}  {"PASS" if ok else "FAIL"}')
    allok = all(c[3] for c in checks)
    print(label, 'PASS' if allok else 'FAIL')
    sys.exit(0 if allok else 1)

# ---------------------------------------------------------------- upstream
try:
    m2sha = pv.verify_frozen('M2_flow_coefficients.json'); m3sha = pv.verify_frozen('M3_flow_coefficients.json'); ok = True
except pv.ProvenanceError as e:
    print(e); ok = False; m2sha = m3sha = None
check('upstream M2, M3 records match the frozen registry', 'ok' if ok else 'bad', 'all', ok)
try:
    resp_raw, pv_resp = pv.load_step0('m3_step0_response.json')
    base_raw, pv_base = pv.load_step0('m3_step0_F2base.json')
    ok = pv_resp['upstream'].get('M2_flow_coefficients.json') == m2sha == pv_base['upstream'].get('M2_flow_coefficients.json')
except pv.ProvenanceError as e:
    print(e); ok = False
check('m3_step0 maps current and built from that M2 record', 'ok' if ok else 'bad', 'all', ok)
if not all(c[3] for c in checks):
    report_and_exit(f'{TAG} GATE')
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in dd.items()} for k, dd in resp_raw.items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in base_raw.items()}
m3rec = json.load(open(os.path.join(RES, 'M3_flow_coefficients.json')))
m3c1 = {int(e): mp.mpf(v) for e, v in m3rec['raw_laurent']['1'].items()}
manifest = json.load(open(manifest_path))

# ---------------------------------------------------------------- per level: files, Laurent coefficients
data, builds = {}, set()
for lev, src in levels.items():
    files = sorted(glob.glob(os.path.join(src, '*.out'))) if os.path.isdir(src) else [src]
    try:
        hdr0, secs, hdrs = read_many(files, manifest)
        ok = hdr0['mode'] == 'ser' and int(hdr0['n']) == 3 and int(hdr0['kmax']) == 2
        msg = 'ok' if ok else 'wrong mode/n/kmax'
        for h in hdrs.values(): builds.add(h['fingerprint'].get('build') if h['fingerprint'] else 'legacy')
    except (OutputError, OSError, KeyError, ValueError) as e:
        print(f'{lev}: file validation failed:', e); ok = False; msg = 'bad'
    check(f'{lev}: {len(files)} outputs complete, sector set == manifest ({manifest["nsec"]})', msg, 'all', ok)
    if not ok:
        report_and_exit(f'{TAG} GATE')
    J, A, top = assemble_ser(3, secs, 2, elo=-14, ehi=4)
    c = {k: {e: mp.re(v) for e, v in J[k].items()} for k in J}
    fin = all(mp.isfinite(v) for k in c for v in c[k].values())
    check(f'{lev}: Laurent coefficients finite', 'ok' if fin else 'bad', 'all', fin)
    data[lev] = dict(files=files, hdr=hdr0, hdrs=hdrs, c=c, cpu=sum(s['time'] for s in secs.values()))
    print(f'{lev}: {len(secs)} sectors from {len(files)} files; ' + ', '.join(f'{k} {hdr0[k]}' for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS', 'VMIN'))
          + f'; resolved exponents: ' + ', '.join(f'd^{k} w^{min(c[k])}..w^{max(c[k])}' for k in c) + f'; engine cpu {data[lev]["cpu"] / 3600:.1f} h')
check('one engine build for both levels', ', '.join(sorted(builds)), 'one', len(builds) == 1 and 'legacy' not in builds)
grid = lambda lev: tuple(int(data[lev]['hdr'][k]) for k in ('nseg', 'm', 'nplain'))
check('the two levels use different grids (fine > coarse)', f'{grid("fine")} vs {grid("coarse")}', 'all',
      all(a >= b for a, b in zip(grid('fine'), grid('coarse'))) and grid('fine') != grid('coarse'))

# ---------------------------------------------------------------- (1) delta^0 vs the Bethe ansatz, delta^1 vs M3
def laurent_exact(fun, lo, hi, rad=mp.mpf('0.04'), npts=400):
    with mp.workdps(60):
        pts = [rad * mp.expjpi(2 * mp.mpf(m) / npts) for m in range(npts)]
        vals = [fun(1 - p) for p in pts]
        return {j: mp.re(sum(v * p ** (-j) for v, p in zip(vals, pts)) / npts) for j in range(lo, hi + 1)}
cf = data['fine']['c']
ba = laurent_exact(J3_BA, -14, max(cf[0]))
dev0 = max(abs(cf[0][e] - ba[e]) / max(abs(ba[e]), 1) for e in cf[0])
print('\ndelta^0 (fine) vs the Bethe ansatz: max |diff|/max(|exact|,1) =', mp.nstr(dev0, 3))
check('fine: delta^0 Laurent vs Bethe ansatz (w^-14..)', dev0, tol_ba)
devc = max(abs(data['coarse']['c'][0][e] - ba[e]) / max(abs(ba[e]), 1) for e in data['coarse']['c'][0] if e in ba)
print('delta^0 (coarse) vs the Bethe ansatz:', mp.nstr(devc, 3))
dev1 = 0
for e in cf[1]:
    ref = m3c1.get(e, mp.mpf(0)) if e >= min(m3c1) else mp.mpf(0)
    if e > max(m3c1): continue
    dev1 = max(dev1, abs(cf[1][e] - ref) / max(abs(ref), 1))
print('delta^1 (fine) vs the frozen M3 record: max |diff|/max(|M3|,1) =', mp.nstr(dev1, 3))
check('fine: delta^1 Laurent vs frozen M3 record', dev1, tol_m3)

# ---------------------------------------------------------------- (2) delta^2 relations and f_2_0_2
def F2_level(c):
    unresolved = []
    def c3(k, j):
        if k not in c: return mp.mpf(0)
        if j < min(c[k]): return mp.mpf(0)      # below the assembled window (w^-14): no poles that deep
        if j > max(c[k]):
            unresolved.append((k, j)); return mp.nan
        return c[k][j]
    def F2(target):
        tot = base.get(target, mp.mpf(0)); terms = [abs(tot)]
        for src, dd in resp.items():
            if target in dd and 1 <= src[0] <= target[0]:
                t = dd[target] * c3(*src); tot += t; terms.append(abs(t))
        return tot, max(terms + [mp.mpf(1)])
    return F2, unresolved
res = {}
for lev in ('fine', 'coarse'):
    F2, unres = F2_level(data[lev]['c'])
    rel_max, rows = mp.mpf(0), []
    for j in range(-12, 0):
        v, sc = F2((2, j)); r = abs(v) / sc
        rel_max = max(rel_max, r) if mp.isfinite(r) else mp.inf
        rows.append((j, v, sc, r))
    f202, _ = F2((2, 0))
    res[lev] = dict(rows=rows, rel_max=rel_max, f=f202, unresolved=list(unres))
    print(f'\n{lev}: F-analyticity relations at delta^2 (must vanish):')
    for j, v, sc, r in rows:
        print(f'  [d^2 w^{j:3d}] = {mp.nstr(v, 5):>12}   (scale {mp.nstr(sc, 3)}, relative {mp.nstr(r, 3)})')
    print(f'  max relative {mp.nstr(rel_max, 3)};  f_2_0_2 = {mp.nstr(f202, 25)}')
for j, v, sc, r in res['fine']['rows']:
    check(f'fine: relation [d^2 w^{j}] (relative)', r, tol_rel)
check('coarse: all delta^2 relations (max relative)', res['coarse']['rel_max'], tol_relc)
ok = all(not res[l]['unresolved'] and mp.isfinite(res[l]['f']) for l in res)
check('f_2_0_2 resolved and finite at both levels', 'ok' if ok else f'unresolved {res["fine"]["unresolved"][:3]}', 'all', ok)
err2 = abs(res['fine']['f'] - res['coarse']['f'])
check('f_2_0_2 two-grid error |fine - coarse| (absolute)', err2, tol_f)
# cross-check: f_2_0_2 with the frozen M3 J3^(1) instead of the fine run's own
calt = {0: cf[0], 1: {e: m3c1.get(e, cf[1][e]) for e in cf[1]}, 2: cf[2]}
F2alt, _ = F2_level(calt)
falt = F2alt((2, 0))[0]
print(f'\nf_2_0_2 fine {mp.nstr(res["fine"]["f"], 25)}  coarse {mp.nstr(res["coarse"]["f"], 25)}  two-grid error {mp.nstr(err2, 3)}')
print(f'f_2_0_2 with the frozen M3 J3^(1): {mp.nstr(falt, 25)} (difference {mp.nstr(falt - res["fine"]["f"], 3)})')

# ---------------------------------------------------------------- record
rel = lambda p: os.path.relpath(p, ROOT)
out = {'flow_coefficients': {'f_2_0_2': mp.nstr(res['fine']['f'], 30)},
       'errors': {'f_2_0_2_two_grid': mp.nstr(err2, 3), 'f_2_0_2_coarse': mp.nstr(res['coarse']['f'], 30),
                  'f_2_0_2_with_M3_J1_minus_fine': mp.nstr(falt - res['fine']['f'], 3)},
       'raw_laurent': {str(k): {str(e): mp.nstr(v, 32) for e, v in cf[k].items()} for k in cf},
       'checks': {'delta0_vs_BA_max_rel': mp.nstr(dev0, 3), 'delta1_vs_M3_max_rel': mp.nstr(dev1, 3),
                  'delta2_relations_max_rel_fine': mp.nstr(res['fine']['rel_max'], 3),
                  'delta2_relations_max_rel_coarse': mp.nstr(res['coarse']['rel_max'], 3)},
       'run': {lev: {k: data[lev]['hdr'][k] for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS', 'VMIN')} for lev in data},
       'sources': {lev: [rel(x) for x in data[lev]['files']] for lev in data},
       'engine_cpu_seconds': {lev: round(data[lev]['cpu'], 1) for lev in data}}
blob = json.dumps(out, indent=1, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()
recname = f'{TAG}_flow_coefficients.json'
rec = os.path.join(RES, recname)
side = os.path.join(RES, f'{TAG}_flow_coefficients.provenance.json')
sidecar = json.dumps({'record': recname, 'record_sha256': sha,
                      'sources': {rel(x): pv.sha256_file(x) for lev in data for x in data[lev]['files']},
                      'engine_input': {'manifest': rel(manifest_path), 'input_sha256': manifest['input_sha256'], 'nsec': manifest['nsec']},
                      'output_fingerprints': {rel(p): h['fingerprint'] for lev in data for p, h in data[lev]['hdrs'].items()},
                      'step0_maps': {n: pv.sha256_file(os.path.join(RES, n)) for n in ('m3_step0_response.json', 'm3_step0_F2base.json')},
                      'step0_generator': {pv_resp['generator']: pv_resp['generator_sha256']},
                      'gate': {rel(__file__): pv.sha256_file(__file__)},
                      'upstream_records': {'M2_flow_coefficients.json': m2sha, 'M3_flow_coefficients.json': m3sha}},
                     indent=1, sort_keys=True) + '\n'
if dry:
    print('\n(dry run: nothing written)  sha256 of the would-be record', sha)
    report_and_exit(f'{TAG} GATE (dry)')
if not all(ch[3] for ch in checks):
    print('\nchecks failed: nothing published')
    report_and_exit(f'{TAG} GATE')
try:
    commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or 'unknown'
except OSError:
    commit = 'unknown'
created = pv.publish_unit([(rec, blob), (side, sidecar)],
                          register=(recname, commit, 'M4 part A blind record (three-bubble f_2_0_2), hashed before any C8 assembly'))[0]
print(f'\nrecord {"written" if created else "identical to the existing record"}: {rel(rec)} sha256 {sha}')
report_and_exit(f'{TAG} GATE')
