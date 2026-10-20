"""M4 part B, confirmatory delta^0 gate at complex K (run after the blind f_3_0_1 and C8 records are frozen).
Each argument is a directory with one complete cx-mode, kmax-0 run of the mirror-reduced n = 4 sector set at one
complex K (rigorous radii). J4^(0)(K) = Gamma(7 - 8K) sum_s w_s A_s is compared with the exact Bethe ansatz
a1^4 b4 / b1^4 / (2 (1 + 8 (K - 1))); default threshold 1e-12 relative (>= 12 digits), fixed before the runs.
The magnitude-bound records give a first-order roundoff bound per K, reported.
Checks: files validate against the n4 manifest and the mirror-weight file (runner sidecars verified), one approved
engine build per K (results/builds.json), mode cx, kmax 0, radii rouche; MSC-024: the K of each run is read exactly
from its header (Kdd), must be one of the two prescribed points 0.92+0.05i and 1.05+0.06i (the doubles of the -K
arguments), Im K != 0, both points present exactly once, no directory or output file used twice. The accepted comparison is published once as results/M4B_cx_check.json (frozen).
--amended (user decision 2026-10-17, post hoc, disclosed): writes results/M4B_cx_check_v2.json from the same runs with
the per-point criterion rel <= 1e-11 AND rel <= the run's own first-order roundoff bound; the v1 record (pass=false
at 1e-12) stays frozen and is marked superseded; the 'amendment' field records the rationale.
usage: python m4b_cx_check.py CX_DIR [CX_DIR ...] [--tol X] [--amended] [--dry]"""
import sys, os, json, glob, hashlib, subprocess
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
import builds
from cluster_assemble import read_many, assemble_cx, pattern_factors, gamma_derivs, OutputError
from cluster_check import J4_BA
mp.mp.dps = 40
RES = pv.RES
ROOT = os.path.join(HERE, '..')
args = sys.argv[1:]
tol = mp.mpf('1e-12')
if '--tol' in args:
    i = args.index('--tol'); tol = mp.mpf(args[i + 1]); del args[i:i + 2]
dry = '--dry' in args
if dry: args.remove('--dry')
verify = '--verify' in args          # fix round 4: rebuild the frozen record and compare byte for byte; never writes
if verify:
    args.remove('--verify'); dry = True
amended = '--amended' in args
if amended:
    args.remove('--amended'); tol = mp.mpf('1e-11')
RECNAME = 'M4B_cx_check_v2.json' if amended else 'M4B_cx_check.json'
AMENDMENT = ('post hoc amendment by user decision (2026-10-17), made after seeing the v1 result (K_B 1.62e-12 > 1e-12): '
             'criterion per point rel |J - BA| <= 1e-11 AND rel <= that run\'s own first-order roundoff bound. Rationale: '
             'the production gate delta^0 tolerance is 1e-6; the K_B run\'s first-order roundoff bound is 1.69e-9 relative; '
             'K_A agrees to 1.7e-14. Same cxA/cxB outputs as v1, no new runs. The double-double K_B rerun design (commit '
             'd4d5967, 1337 sectors, ~17k core-h) is withdrawn and was not executed. v1 (pass=false) stays frozen, superseded.')
rel = lambda p: os.path.relpath(p, ROOT)
manifest = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.manifest.json')))
mirror = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.mirror.json')))
assert mirror['input_sha256'] == manifest['input_sha256']
weights = mirror['weights']
expected = [s for s, w in enumerate(weights) if w > 0]
pfac = pattern_factors(4)
checks, results = [], []
def check(name, value, thr, ok=None):
    ok = (mp.isfinite(value) and value <= thr) if ok is None else ok
    checks.append((name, value, thr, bool(ok)))
PRESCRIBED = {(0.92, 0.05): 'K_A', (1.05, 0.06): 'K_B'}     # exact doubles of the -K arguments
real = [os.path.realpath(d) for d in args]
allfiles = [os.path.realpath(f) for d in args for f in glob.glob(os.path.join(d, '*.out'))]
ok = len(args) == 2 and len(set(real)) == 2 and len(set(allfiles)) == len(allfiles)
check('two distinct run directories, no output used twice', f'{len(set(real))} dirs', '2', ok)
seenK = {}
for d in args:
    files = sorted(glob.glob(os.path.join(d, '*.out')))
    try:
        h, secs, hdrs = read_many(files, manifest, expected=expected)
        blds = sorted({hh['fingerprint'].get('build') if hh['fingerprint'] else 'legacy' for hh in hdrs.values()})
        ok = h['mode'] == 'cx' and h.get('radii') == 'rouche' and int(h['kmax']) == 0 and len(blds) == 1 and 'legacy' not in blds
        # MSC-027: the roundoff epsilon follows the verified build precision (double 2^-53, dd 2^-104)
        eps = mp.mpf(builds.eps(blds[0])) if ok else mp.nan
        kd = [float.fromhex(x) for x in h['Kdd']]
        if kd[1] != 0.0 or kd[3] != 0.0:
            raise ValueError('K is not a plain double pair')
        tag = PRESCRIBED.get((kd[0], kd[2]))
        if tag is None or kd[2] == 0.0:
            raise ValueError(f'K = {kd[0]} + {kd[2]} i is not one of the prescribed complex points')
        if tag in seenK:
            raise ValueError(f'{tag} appears twice ({seenK[tag]} and {d})')
        seenK[tag] = d
        K = mp.mpc(mp.mpf(kd[0]), mp.mpf(kd[2]))
        J, _ = assemble_cx(4, secs, K, 0, weights=weights)
        G = gamma_derivs(7 - 8 * K, 0)[0]
        ro = sum(abs(G) * s['B'][(0, 0)] * weights[sid] * pfac[s['pat']] for sid, s in secs.items()) * eps \
            if all('B' in s for s in secs.values()) else mp.nan
        ex = J4_BA(K); r = abs(J[0] / ex - 1)
        print(f'K = {mp.nstr(K, 10)}: engine {mp.nstr(J[0], 20)}  exact {mp.nstr(ex, 20)}  rel {mp.nstr(r, 3)}  '
              f'(first-order roundoff bound {mp.nstr(ro / abs(ex), 3)} relative; grid {h["nseg"]},{h["m"]},{h["nplain"]}; build {blds})')
        results.append(dict(dir=rel(d), point=tag, K_hex=[h['Kdd'][0], h['Kdd'][2]], K=[mp.nstr(K.real, 17), mp.nstr(K.imag, 17)], J=[mp.nstr(J[0].real, 22), mp.nstr(J[0].imag, 22)],
                            exact=[mp.nstr(ex.real, 22), mp.nstr(ex.imag, 22)], rel_diff=mp.nstr(r, 3), roundoff_bound_rel=mp.nstr(ro / abs(ex), 3),
                            grid=[h['nseg'], h['m'], h['nplain']], taurat=h['taurat'], build=blds[0],
                            files={rel(p): pv.sha256_file(p) for p in files}))
        check(f'{os.path.basename(d.rstrip("/"))}: files, single build, cx/kmax 0/rouche', 'ok' if ok else 'bad', 'all', ok)
        check(f'{os.path.basename(d.rstrip("/"))}: J4^(0)(K) vs Bethe ansatz (relative)', r, tol)
        if amended:
            check(f'{os.path.basename(d.rstrip("/"))}: rel <= own first-order roundoff bound', r, ro / abs(ex))
    except (OutputError, OSError, KeyError, ValueError, builds.BuildError) as e:
        print(d, 'failed:', e)
        check(f'{os.path.basename(d.rstrip("/"))}: readable and complete', 'bad', 'all', False)
check('both prescribed points K_A, K_B present exactly once', ','.join(sorted(seenK)), 'K_A,K_B', sorted(seenK) == ['K_A', 'K_B'])
print('\nM4B cx check (value / threshold / result):')
for name, v, t, ok in checks:
    print(f'  {name:58s} {mp.nstr(v, 3) if not isinstance(v, str) else v:>10}  <= {mp.nstr(t, 2) if not isinstance(t, str) else t:>8}  {"PASS" if ok else "FAIL"}')
allok = all(c[3] for c in checks)
print('M4B CX CHECK', 'PASS' if allok else 'FAIL')
rec = {'threshold': mp.nstr(tol, 3), 'pass': allok, 'results': results, 'amendment': AMENDMENT if amended else None,
       'supersedes': 'M4B_cx_check.json' if amended else None,
       'checks': [[n, v if isinstance(v, str) else mp.nstr(v, 3), t if isinstance(t, str) else mp.nstr(t, 3), ok] for n, v, t, ok in checks],
       'frozen_before': {r_: pv.registry().get(r_, {}).get('sha256') for r_ in ('M4B_flow_coefficients.json', 'C8_record.json')}}
blob = json.dumps(rec, indent=1, sort_keys=True) + '\n'
if verify:
    want = pv.registry().get(RECNAME, {}).get('sha256'); p = os.path.join(RES, RECNAME)
    got = hashlib.sha256(blob.encode()).hexdigest()
    same = got == want and os.path.exists(p) and open(p).read() == blob
    print('VERIFY', RECNAME, 'IDENTICAL' if same else f'DIFFERS (rebuilt {got}, frozen {want})')
    sys.exit(0 if (same and allok) else 1)
if dry:
    print('(dry run: nothing written)'); sys.exit(0 if allok else 1)
commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or 'unknown'
path = os.path.join(RES, RECNAME)
pv.publish_unit([(path, blob)], register=(RECNAME, commit, 'confirmatory delta^0 check at complex K (pass or fail recorded)'
                                         + (' -- AMENDED criterion (post hoc, user decision 2026-10-17)' if amended else '')))
print('record', rel(path), 'sha256', hashlib.sha256(blob.encode()).hexdigest())
if amended:
    pv.mark_superseded('M4B_cx_check.json', RECNAME, 'post hoc amended criterion (user decision 2026-10-17): rel <= 1e-11 and '
                       '<= own roundoff bound; v1 failed K_B at 1e-12 (1.62e-12); dd rerun design withdrawn')
    print('M4B_cx_check.json marked superseded by', RECNAME)
sys.exit(0 if allok else 1)
