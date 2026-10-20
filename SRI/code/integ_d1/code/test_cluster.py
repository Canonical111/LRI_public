"""Regression tests for the cluster engine (seconds on a laptop):
  1. n = 2, cx mode: J2^{(0)}, J2^{(1)} at two M2 contour points vs the M2 values (results/m2_runs), < 1e-28;
  2. n = 2, cx mode: J2^{(0)} vs the exact Bethe ansatz at real and complex K, < 1e-27;
  3. n = 2, ser mode: Laurent coefficients of J2^{(0)}, J2^{(1)} vs M2's raw Laurent coefficients, < 1e-27;
  4. mscheme_numeric vs the symbolic mscheme_invariants.C_list(3) at random flow coefficients, < 1e-35;
  5. (M4 part A) the generic delta path (-generic) equals the specialized one at kmax = 1 (ser and cx, n = 2);
     the default build refuses kmax = 2 in ser mode; with --k2 BINARY (a build with -DLS=13 -DVMIN=-8):
     n = 2 Laurent coefficients of J2^{(0..2)} vs M2's raw Laurent coefficients (delta^2 included), < 1e-27;
  6. (M4 engine prep) -radii rouche (rigorous circle radii computed by the engine): n = 2 Laurent coefficients vs M2
     < 1e-27; an input without sampled radii is refused unless -radii rouche is given.
usage: python test_cluster.py PATH_TO_ENGINE_BINARY [PATH_TO_SECTOR_CHECK_BINARY] [--k2 PATH_TO_K2_ENGINE]"""
import sys, os, json, subprocess, tempfile, random, hashlib
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cluster_assemble import read_out, assemble_cx, assemble_ser
from cluster_check import J2_BA
import cluster_gen
mp.mp.dps = 40
CE2 = None
if '--k2' in sys.argv:
    i = sys.argv.index('--k2'); CE2 = sys.argv[i + 1]; del sys.argv[i:i + 2]
CE = sys.argv[1]
tmp = tempfile.mkdtemp()
inp = os.path.join(tmp, 'n2.txt')
cluster_gen.write_engine_input(cluster_gen.generate(2, verbose=False), inp)
GRID = ['-tau', '0.1', '-taurat', '0.1', '-nseg', '24', '-m', '32', '-nplain', '30']
fails = 0


def ddp(x):
    hi = float(x); lo = float(x - mp.mpf(hi)); return [hi.hex(), lo.hex()]


def run(args, ce=None):
    out = os.path.join(tmp, 'o.out')
    r = subprocess.run([ce or CE, '-i', inp, '-o', out] + args + GRID, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return read_out(out)


def check(name, err, tol):
    global fails
    ok = err < tol
    fails += not ok
    print(f'{"PASS" if ok else "FAIL"}  {name}: {mp.nstr(err, 3)} (tol {tol})')


m2 = {json.loads(l)['j']: json.loads(l) for l in open(os.path.join(HERE, '..', 'results', 'm2_runs', 'm2_laurent_L4_d40_r0.1_n96.jsonl'))}
for j in (4, 37):
    d = m2[j]; w = mp.mpc(mp.mpf(d['w'][0]), mp.mpf(d['w'][1])); K = 1 - w
    hdr, secs = run(['-mode', 'cx', '-k', '1', '-Kdd'] + ddp(mp.re(K)) + ddp(mp.im(K)))
    J, _ = assemble_cx(2, secs, K, 1)
    ref = [mp.mpc(mp.mpf(a), mp.mpf(b)) for a, b in d['J']]
    check(f'n=2 cx vs M2 at contour point j={j}', max(abs(J[k] / ref[k] - 1) for k in (0, 1)), 1e-28)
for Ks in ['0.3:0', '0.92:0.07', '1.05:0.05']:
    K = mp.mpc(*[mp.mpf(x) for x in Ks.split(':')])
    hdr, secs = run(['-mode', 'cx', '-k', '0', '-Kdd'] + ddp(mp.re(K)) + ddp(mp.im(K)))
    J, _ = assemble_cx(2, secs, K, 0)
    check(f'n=2 cx delta^0 vs Bethe ansatz at K={Ks}', abs(J[0] / J2_BA(K) - 1), 1e-27)
hdr, secs = run(['-mode', 'ser', '-k', '1'])
J, _, _ = assemble_ser(2, secs, 1, elo=-6, ehi=3)
ref = json.load(open(os.path.join(HERE, '..', 'results', 'M2_flow_coefficients.json')))['raw_laurent']
err = max(abs(mp.re(J[k][e]) - mp.mpf(ref[str(k)][str(e)])) / max(1, abs(mp.mpf(ref[str(k)][str(e)])))
          for k in (0, 1) for e in J[k] if str(e) in ref[str(k)])
check('n=2 ser Laurent coefficients vs M2', err, 1e-27)
# M4 part A: generic delta path vs the specialized path at kmax = 1; delta^2 vs M2
def maxdiff(a, b):
    """max |difference| relative to the largest coefficient of the same (k, j) series (or value) of that sector"""
    d = 0
    for s in a:
        for f in ('A', 'S'):
            for key, v in a[s][f].items():
                if key not in b[s][f]: continue
                sc = max(abs(x) for kk, x in a[s][f].items() if kk[:2] == key[:2])
                d = max(d, abs(v - b[s][f][key]) / sc)
    return d
for md in (['-mode', 'ser', '-k', '1'], ['-mode', 'cx', '-k', '1', '-K', '0.92', '0.05', '-conj', '0']):
    _, sa = run(md); _, sb = run(md + ['-generic'])
    check(f'generic delta path == specialized path ({md[1]}, kmax 1, n=2, per sector)', maxdiff(sa, sb), 1e-27)
r = subprocess.run([CE, '-i', inp, '-o', os.path.join(tmp, 'k2.out'), '-mode', 'ser', '-k', '2'] + GRID, capture_output=True, text=True)
check('default build refuses kmax 2 in ser mode', 0 if r.returncode != 0 else 1, 0.5)
if CE2:
    hdr, secs = run(['-mode', 'ser', '-k', '2'], ce=CE2)
    J, _, _ = assemble_ser(2, secs, 2, elo=-9, ehi=3)
    err, nk2 = 0, 0
    for k in (0, 1, 2):
        for e in J[k]:
            if str(e) not in ref[str(k)]: continue
            rv = mp.mpf(ref[str(k)][str(e)])
            err = max(err, abs(mp.re(J[k][e]) - rv) / max(1, abs(rv))); nk2 += k == 2
    check(f'n=2 ser Laurent coefficients delta^0..2 vs M2 ({nk2} delta^2 coefficients)', err if nk2 >= 8 else mp.inf, 1e-27)
inp_nr = os.path.join(tmp, 'n2_norad.txt')
cluster_gen.write_engine_input(cluster_gen.generate(2, verbose=False, sampled_radii=False), inp_nr)
out = os.path.join(tmp, 'nr.out')
r = subprocess.run([CE, '-i', inp_nr, '-o', out, '-mode', 'ser', '-k', '1'] + GRID, capture_output=True, text=True)
check('input without sampled radii refused without -radii rouche', 0 if (r.returncode != 0 and not os.path.exists(out)) else 1, 0.5)
r = subprocess.run([CE, '-i', inp_nr, '-o', out, '-mode', 'ser', '-k', '1', '-radii', 'rouche'] + GRID, capture_output=True, text=True)
hdr, secs = read_out(out)
J, _, _ = assemble_ser(2, secs, 1, elo=-6, ehi=3)
err = max(abs(mp.re(J[k][e]) - mp.mpf(ref[str(k)][str(e)])) / max(1, abs(mp.mpf(ref[str(k)][str(e)])))
          for k in (0, 1) for e in J[k] if str(e) in ref[str(k)])
check('n=2 ser Laurent coefficients vs M2 with -radii rouche', err if hdr.get('radii') == 'rouche' else mp.inf, 1e-27)
from mscheme_invariants import C_list
from mscheme_numeric import C_numeric
import sympy as sp
random.seed(1)
f = {(m, n, k): mp.mpf(random.uniform(-2, 2)) for m in range(4) for n in range(4) for k in range(4)
     if m + n + k <= 3 and not (m == 0 and k == 0)}
f[(1, 0, 0)] = mp.mpf(1)
num = C_numeric(f, 3); Cs = C_list(3)
err = 0
for i, c in enumerate(Cs):
    v = c.subs({s: sp.Float(mp.nstr(f[tuple(map(int, str(s).split('_')[1:]))], 38), 38) for s in c.free_symbols})
    err = max(err, abs(num[i] - mp.mpf(str(sp.N(v, 40)))))
check('mscheme_numeric vs symbolic C_list(3)', err, 1e-35)
# fix round 2, MSC-016: -conj 1 with a complex K in cx mode must be rejected before any output
out = os.path.join(tmp, 'conj.out')
r = subprocess.run([CE, '-i', inp, '-o', out, '-mode', 'cx', '-k', '0', '-K', '0.92', '0.05', '-conj', '1'] + GRID, capture_output=True, text=True)
check('engine rejects -conj 1 with complex K (exit status)', 0 if (r.returncode != 0 and not os.path.exists(out) and not os.path.exists(out + '.partial')) else 1, 0.5)
r = subprocess.run([CE, '-i', inp, '-o', out, '-mode', 'cx', '-k', '0', '-K', '0.3', '0', '-conj', '1'] + GRID, capture_output=True, text=True)
check('engine accepts -conj 1 with real K', 0 if r.returncode == 0 else 1, 0.5)
r = subprocess.run([CE, '-version'], capture_output=True, text=True)
check('engine reports a build id', 0 if r.returncode == 0 and r.stdout.strip() else 1, 0.5)
# MSC-014: validate_output checks build and arguments
args = ['-i', inp, '-mode', 'cx', '-k', '0', '-K', '0.3', '0', '-conj', '1'] + GRID
insha = hashlib.sha256(open(inp, 'rb').read()).hexdigest()
bid = r.stdout.strip()
v = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, 'validate_output.py'), out, insha, *a], capture_output=True, text=True).returncode
check('validate_output accepts matching build and arguments', v(bid, *args), 0.5)
check('validate_output rejects a different build', 0 if v('otherbuild', *args) != 0 else 1, 0.5)
check('validate_output rejects different arguments', 0 if v(bid, *(args[:-1] + ['31'])) != 0 else 1, 0.5)
if len(sys.argv) > 2:   # MSC-012: the sector checker rejects nonfinite input and writes no result
    r = subprocess.run([sys.argv[2], inp, '1', 'nan', '0.05', '-level', '2'], capture_output=True, text=True)
    check('sector_check rejects a nonfinite K (no result written)', 0 if (r.returncode != 0 and 'A00' not in r.stdout) else 1, 0.5)
    r = subprocess.run([sys.argv[2], inp, '1', '0.92', '0.05', '-level', '2'], capture_output=True, text=True)
    check('sector_check writes fingerprint and completion marker', 0 if (r.returncode == 0 and '# fingerprint input_sha256' in r.stdout and '# complete' in r.stdout) else 1, 0.5)
print('ALL PASS' if fails == 0 else f'{fails} FAILED')
sys.exit(1 if fails else 0)
