"""M2 gate (fix round 1: MSC-005, MSC-009).
Stage 1 (blind): Laurent coefficients of J2^{(k)} from the circle data; every mandatory check has an explicit
threshold and must pass before anything is published:
  data       all contour points present once, consistent parameters, finite values;
  ba         delta = 0 Laurent coefficients vs the exact Bethe ansatz (default <= 1e-25: the plan's 25 digits for c2/c1^2);
  relations  EVERY F-analyticity relation of m2_step0 (default <= 1e-20 relative);
  finite     the flow coefficients are finite and resolved.
Then results/M2_flow_coefficients.json is written ONCE (an existing file must be byte-identical; it is never
overwritten), plus a provenance sidecar (data and step-0 map hashes).
Stage 2 (--stage2 --expect-sha SHA): read-only. Regenerates the record in memory, requires it to equal the recorded
file, the expected hash and the frozen-record registry, checks the sidecar, then compares C3, C4, C5 with the
compendium (default <= 1e-20 relative: the plan's 20 digits). Exit status 0 only if every check passes.
usage: python m2_gate.py DATA.jsonl [--stage2 --expect-sha SHA] [--tol-ba X] [--tol-rel X] [--tol-c X]"""
import sys, os, json, hashlib, re, subprocess
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
from two_bubble import J2_BA
mp.mp.dps = 40

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tol_ba = mp.mpf(opt('--tol-ba', '1e-25')); tol_rel = mp.mpf(opt('--tol-rel', '1e-20')); tol_c = mp.mpf(opt('--tol-c', '1e-20'))
expect_sha = opt('--expect-sha', None)
stage2 = '--stage2' in args
if stage2: args.remove('--stage2')
if stage2 and not expect_sha:
    sys.exit('stage 2 needs --expect-sha (the hash recorded by the blind stage 1)')
src = args[0]
checks = []
def check(name, value, thr, ok=None):
    ok = (mp.isfinite(value) and value <= thr) if ok is None else ok
    checks.append((name, value, thr, bool(ok)))
    return ok
def report_and_exit(label):
    print(f'\n{label} checks (value / threshold / result):')
    for name, v, t, ok in checks:
        print(f'  {name:46s} {mp.nstr(v, 3) if not isinstance(v, str) else v:>10}  <= {mp.nstr(t, 2) if not isinstance(t, str) else t:>8}  {"PASS" if ok else "FAIL"}')
    allok = all(c[3] for c in checks)
    print(f'{label}', 'PASS' if allok else 'FAIL')
    sys.exit(0 if allok else 1)

# ---------------------------------------------------------------- data
data = [json.loads(l) for l in open(src)]
NPTS = data[0]['npts']; RAD = mp.mpf(data[0]['rad'])
params = {(d['npts'], d['rad'], d['level'], d['dps'], json.dumps(d.get('fp'), sort_keys=True)) for d in data}
js = [d['j'] for d in data]
vals = {}
finite = True
for d in data:
    w = mp.mpc(mp.mpf(d['w'][0]), mp.mpf(d['w'][1]))
    J = [mp.mpc(mp.mpf(a), mp.mpf(b)) for a, b in d['J']]
    finite = finite and all(mp.isfinite(x) for x in J) and mp.isfinite(w)
    vals[d['j']] = (w, J)
    if 0 < d['j'] < NPTS - d['j']:
        vals[NPTS - d['j']] = (mp.conj(w), [mp.conj(x) for x in J])
data_ok = (len(params) == 1 and sorted(js) == list(range(NPTS // 2 + 1)) and len(vals) == NPTS and finite)
check('data: complete, consistent, finite', 'ok' if data_ok else 'bad', 'all', data_ok)
if not data_ok:
    report_and_exit('M2 GATE')

def laurent(k, jlo=-12, jhi=4):
    return {j: mp.re(sum(J[k] * w ** (-j) for w, J in vals.values()) / NPTS) for j in range(jlo, jhi + 1)}
c = {k: laurent(k) for k in range(4)}
# (1) delta = 0 continuation check against the exact Bethe-ansatz J2
ba = {j: mp.re(sum(J2_BA(1 - w) * w ** (-j) for w, _ in vals.values()) / NPTS) for j in range(-12, 5)}
dev0 = max(abs(c[0][j] - ba[j]) / max(abs(ba[j]), mp.mpf(1)) for j in range(-12, 5))
print('delta=0 Laurent vs Bethe ansatz, max relative deviation:', mp.nstr(dev0, 3))
check('delta0 Laurent vs Bethe ansatz (max rel)', dev0, tol_ba)
# (2) F-analyticity relations and flow coefficients (provenance-checked step-0 maps)
resp_raw, pv_resp = pv.load_step0('m2_step0_response.json')
base_raw, pv_base = pv.load_step0('m2_step0_F1base.json')
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in dd.items()} for k, dd in resp_raw.items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in base_raw.items()}
def F1(target):
    return base.get(target, 0) + sum(dd[target] * c[src_[0]][src_[1]] for src_, dd in resp.items() if target in dd)
print('\nF-analyticity relations (must vanish):')
rel_max = 0
for k in (1, 2, 3):
    for j in range(-14, 0):
        v = F1((k, j))
        if abs(v) > 0 or (k, j) in base:
            scale = max([abs(base.get((k, j), 0))] + [abs(dd[(k, j)] * c[s[0]][s[1]]) for s, dd in resp.items() if (k, j) in dd] + [mp.mpf(1)])
            r = abs(v) / scale
            rel_max = max(rel_max, r)
            print(f'  [d^{k} w^{j}] = {mp.nstr(v, 5)}   (relative {mp.nstr(r, 3)})')
            check(f'relation [d^{k} w^{j}] (relative)', r, tol_rel)
f = {}
for (n, k) in [(0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (0, 3)]:
    f[f'f_1_{n}_{k}'] = (-1) ** n * F1((k, n))
check('flow coefficients finite', 'ok' if all(mp.isfinite(v) for v in f.values()) else 'bad', 'all',
      all(mp.isfinite(v) for v in f.values()))
# the published record (format unchanged since the frozen M2 record)
out = {'flow_coefficients': {k: mp.nstr(v, 32) for k, v in f.items()},
       'raw_laurent': {str(k): {str(j): mp.nstr(v, 32) for j, v in c[k].items()} for k in c},
       'delta0_vs_BA_max_rel': mp.nstr(dev0, 3), 'relations_max_rel': mp.nstr(rel_max, 3), 'source': src}
blob = json.dumps(out, indent=1, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()
rec = os.path.join(pv.RES, 'M2_flow_coefficients.json')
side = os.path.join(pv.RES, 'M2_flow_coefficients.provenance.json')
sidecar = json.dumps({'record': 'M2_flow_coefficients.json', 'record_sha256': sha,
                      'sources': {os.path.relpath(os.path.abspath(src), os.path.dirname(pv.RES)): pv.sha256_file(src)},
                      'step0_maps': {n: pv.sha256_file(os.path.join(pv.RES, n)) for n in ('m2_step0_response.json', 'm2_step0_F1base.json')},
                      'step0_generator': {pv_resp['generator']: pv_resp['generator_sha256']}}, indent=1, sort_keys=True) + '\n'
for k, v in f.items(): print(f'  {k} = {mp.nstr(v, 25)}')
if not stage2:
    if not all(ch[3] for ch in checks):
        print('\nstage 1 checks failed: nothing published')
        report_and_exit('M2 GATE STAGE 1')
    created = pv.publish_unit([(rec, blob), (side, sidecar)])[0]
    print(f'\nflow coefficients {"written" if created else "identical to the existing record"}: results/M2_flow_coefficients.json sha256', sha)
    report_and_exit('M2 GATE STAGE 1')

# ---------------------------------------------------------------- stage 2 (read-only)
ok_rec = os.path.exists(rec) and open(rec).read() == blob and sha == expect_sha
check('record identical to the recorded file and --expect-sha', 'ok' if ok_rec else 'bad', 'all', ok_rec)
try:
    pv.verify_frozen('M2_flow_coefficients.json', expect_sha); ok_reg = True
except pv.ProvenanceError as e:
    print(e); ok_reg = False
check('record matches the frozen-record registry', 'ok' if ok_reg else 'bad', 'all', ok_reg)
ok_side = os.path.exists(side) and open(side).read() == sidecar
check('provenance sidecar matches data and step-0 maps', 'ok' if ok_side else 'bad', 'all', ok_side)
import sympy as sp
from mscheme_invariants import C_list, fsym
from one_bubble import taylor_coeffs
ob = taylor_coeffs(N=4, nmax=4)
outba = subprocess.run([sys.executable, os.path.join(HERE, 'ba_numeric.py')], capture_output=True, text=True, cwd=HERE).stdout
sub = {fsym(1, 0, 0): mp.mpf(1)}
for line in outba.splitlines():
    mm = re.match(r'\((\d+), (\d+)\) (\S+)', line)
    if mm: sub[fsym(int(mm.group(1)), int(mm.group(2)), 0)] = mp.mpf(mm.group(3))
resid = re.search(r'residual norm (\S+)', outba)
check('Bethe-ansatz fit residual', mp.mpf(resid.group(1)) if resid else mp.inf, mp.mpf('1e-40'))
for (n, k), v in ob.items():
    if k >= 1: sub[fsym(0, n, k)] = v
for key, v in f.items():
    _, m_, n_, k_ = key.split('_'); sub[fsym(int(m_), int(n_), int(k_))] = v
Cs = C_list(3)
z = mp.zeta
exact = {3: mp.mpf(39) / 16 + 2 * z(2), 4: 4 - 4 * z(2) - 8 * z(3),
         5: mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z(2) + 24 * z(3) + mp.mpf(49) / 2 * z(4)}
for n in (3, 4, 5):
    e = Cs[n - 1].subs({s: sp.Float(mp.nstr(sub[s], 38), 38) for s in Cs[n - 1].free_symbols if s in sub})
    if e.free_symbols:
        check(f'C{n} resolved', 'unresolved', 'all', False); continue
    v = mp.mpf(str(sp.N(e, 40)))
    rel = abs(v - exact[n]) / abs(exact[n])
    print(f'C{n}: pipeline {mp.nstr(v, 25)}   compendium {mp.nstr(exact[n], 25)}   diff {mp.nstr(v - exact[n], 3)}')
    check(f'C{n} vs compendium (relative)', rel, tol_c)
report_and_exit('M2 GATE')
