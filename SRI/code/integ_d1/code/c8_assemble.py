"""M4 part C: C8 from the magnetization-scheme pipeline (mscheme_numeric.C_numeric at order 4).
Inputs (all verified against the frozen-record registry first): the Bethe ansatz f_m_n_0 (ba_numeric4.py, degree <= 4),
the one-bubble f_0_n_k (one_bubble.py), M2 (two bubbles f_1_n_k), M3 (f_2_0_1, f_2_1_1), M4A (f_2_0_2), M4B (f_3_0_1).
Stage 1 (blind): the same assembly reproduces C3..C7 (closed forms, default <= 1e-20 relative); C8 and its uncertainty
are computed and written ONCE to results/C8_record.json (+ registry entry). No reference value of C8 is used.
  uncertainty: dC8/df_2_0_2 = 2 and dC8/df_3_0_1 = 3/4 (exact, from C_list(4)); per input
    sigma_f = f_2_0_2: max(two-grid error, |fine - variant with the frozen M3 J3^(1)|);
              f_3_0_1: the M4B total (two-grid difference + roundoff estimate);
  C8 error = |2| sigma_202 + |3/4| sigma_301 (linear, conservative) and the quadrature sum are both reported;
  the other inputs (M2, M3 ~1e-25 relative, Bethe ansatz 1e-60, one bubble exact) are propagated by finite
  differences with their recorded accuracies and are negligible.
Stage 2 (--compare --expect-sha SHA): read-only; the record must equal the recorded file and hash, and the
confirmatory complex-K check (results/M4B_cx_check.json, pass or fail) must be frozen; then C8 is compared
with the compendium value 247.3812048049935 (unproved zeta candidate) and 242.83 (quoted uncertainty 2.37): absolute
differences and labelled ratios only (MSC-034: no sigma/pull wording, no quadrature combination).
Fix round 3 (MSC-019, MSC-023): --m4b NAME selects the M4B record (default M4B_flow_coefficients_v2.json) and
--out NAME the C8 record (default C8_record_v2.json); both must be current (not superseded) in the registry. The
uncertainty inputs must be finite and nonnegative, the M4B roundoff factor >= 0.01, and sigma(C8) <= 0.3 (the
plan's acceptance limit) before anything is published. Upstream budgets: M4A <= 0.01 (x2 = 0.02) and M4B <= 0.37
(x3/4 = 0.2775) sum to <= 0.2975. When the confirmatory cx record exists at stage 1 its hash is bound into the C8
record. Stage 2 requires: C8 record current and identical to --expect-sha, its M4B upstream equal to the current
M4B record, the cx record frozen with pass = true and bound into the C8 record; otherwise it exits nonzero and the
comparison is labelled PROVISIONAL.
usage: python c8_assemble.py [--tol-c X] [--m4b NAME] [--out NAME] | --compare --expect-sha SHA [--m4b ..] [--out ..]"""
import sys, os, json, hashlib, subprocess, re
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
from mscheme_numeric import C_numeric
from one_bubble import taylor_coeffs
mp.mp.dps = 40
RES = pv.RES
ROOT = os.path.join(HERE, '..')
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
tol_c = mp.mpf(opt('--tol-c', '1e-20'))
M4BREC = opt('--m4b', 'M4B_flow_coefficients_v2.json')
OUTREC = opt('--out', 'C8_record_v2.json')
SIGMA_MAX = mp.mpf('0.3')
expect_sha = opt('--expect-sha', None)
compare = '--compare' in args
verify = '--verify' in args          # fix round 4: rebuild the frozen C8 record and compare byte for byte; never writes
if verify: args.remove('--verify')
if compare and not expect_sha:
    sys.exit('--compare needs --expect-sha (the hash printed by stage 1)')
checks = []
def check(name, value, thr, ok=None):
    ok = (mp.isfinite(value) and value <= thr) if ok is None else ok
    checks.append((name, value, thr, bool(ok)))
    return ok
def report_and_exit(label):
    print(f'\n{label} checks (value / threshold / result):')
    for name, v, t, ok in checks:
        print(f'  {name:56s} {mp.nstr(v, 3) if not isinstance(v, str) else v:>10}  <= {mp.nstr(t, 2) if not isinstance(t, str) else t:>8}  {"PASS" if ok else "FAIL"}')
    allok = all(c[3] for c in checks)
    print(label, 'PASS' if allok else 'FAIL')
    sys.exit(0 if allok else 1)

recs = ['M2_flow_coefficients.json', 'M3_flow_coefficients.json', 'M4A_flow_coefficients.json', M4BREC]
shas = {}
for r in recs:
    try:
        shas[r] = pv.verify_frozen(r); ok = pv.is_current(r)
        if not ok: print(f'{r} is superseded')
    except pv.ProvenanceError as e:
        print(e); ok = False
    check(f'{r} matches the frozen registry and is current', 'ok' if ok else 'bad', 'all', ok)
if not all(c[3] for c in checks):
    report_and_exit('C8 ASSEMBLY')
fl, err = {(1, 0, 0): mp.mpf(1)}, {}
for (nn, k), v in taylor_coeffs(N=4, nmax=4).items():
    if k >= 1: fl[(0, nn, k)] = v
outba = subprocess.run([sys.executable, os.path.join(HERE, 'ba_numeric4.py'), '80'], capture_output=True, text=True).stdout
for line in outba.splitlines():
    mm = re.match(r'\((\d+), (\d+)\) (\S+)', line)
    if mm: fl[(int(mm.group(1)), int(mm.group(2)), 0)] = mp.mpf(mm.group(3))
resid = re.search(r'residual norm (\S+)', outba)
check('Bethe-ansatz fit residual (degree 4)', mp.mpf(resid.group(1)) if resid else mp.inf, mp.mpf('1e-40'))
for r in recs:
    d = json.load(open(os.path.join(RES, r)))
    for key, v in d['flow_coefficients'].items():
        _, a, b, k = key.split('_'); fl[(int(a), int(b), int(k))] = mp.mpf(v)
    for key, v in d.get('errors', {}).items():
        err[key] = v
m4a = json.load(open(os.path.join(RES, 'M4A_flow_coefficients.json')))['errors']
m4b = json.load(open(os.path.join(RES, M4BREC)))['errors']
sig202 = max(mp.mpf(m4a['f_2_0_2_two_grid']), abs(mp.mpf(m4a['f_2_0_2_with_M3_J1_minus_fine'])))
sig301 = mp.mpf(m4b['f_3_0_1_total'])
rof = mp.mpf(m4b.get('roundoff_factor', 'nan'))
okin = all(mp.isfinite(x) and x >= 0 for x in (sig202, sig301)) and mp.isfinite(rof) and rof >= mp.mpf('0.01')
check('uncertainty inputs finite, nonnegative; M4B roundoff factor >= 0.01', 'ok' if okin else 'bad', 'all', okin)
# the symbolic C8 depends on exactly these 26 coefficients (c8_dependency.py); all must be present
dep8 = [(0, 0, 1), (0, 0, 2), (0, 0, 3), (0, 1, 1), (0, 1, 2), (0, 2, 1), (1, 0, 0), (1, 0, 1), (1, 0, 2), (1, 0, 3), (1, 1, 0),
        (1, 1, 1), (1, 1, 2), (1, 2, 0), (1, 2, 1), (1, 3, 0), (2, 0, 0), (2, 0, 1), (2, 0, 2), (2, 1, 0), (2, 1, 1), (2, 2, 0),
        (3, 0, 0), (3, 0, 1), (3, 1, 0), (4, 0, 0)]
# C3..C7 additionally need the one-bubble f_0_1_3, f_0_2_2, f_0_3_1 (degree 4 enters C7 = C_{2*4-1}; C8 does not
# depend on them symbolically), so the assembly uses the union of the C7 inputs (m3_gate need7) and the C8 inputs
need7 = [(0, 0, 1), (0, 0, 2), (0, 0, 3), (0, 1, 1), (0, 1, 2), (0, 1, 3), (0, 2, 1), (0, 2, 2), (0, 3, 1), (1, 0, 0), (1, 0, 1),
         (1, 0, 2), (1, 1, 0), (1, 1, 1), (1, 1, 2), (1, 2, 0), (1, 2, 1), (1, 3, 0), (2, 0, 0), (2, 0, 1), (2, 1, 0), (2, 1, 1),
         (2, 2, 0), (3, 0, 0), (3, 1, 0)]
need = sorted(set(dep8) | set(need7))
miss = [k for k in need if k not in fl or not mp.isfinite(fl[k])]
check(f'all {len(need)} inputs of C3..C8 resolved and finite', 'ok' if not miss else f'missing {miss[:3]}', 'all', not miss)
if miss:
    report_and_exit('C8 ASSEMBLY')
fuse = {k: fl[k] for k in need}
Cs = C_numeric(fuse, 4)
z = mp.zeta
exact = {3: mp.mpf(39) / 16 + 2 * z(2),
         4: 4 - 4 * z(2) - 8 * z(3),
         5: mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z(2) + 24 * z(3) + mp.mpf(49) / 2 * z(4),
         6: 26 - 38 * z(2) + 104 * z(3) - 80 * z(4) - 272 * z(5) + 112 * z(2) * z(3),
         7: mp.mpf(1798583) / 32768 - mp.mpf(90637) / 1024 * z(2) + mp.mpf(453) / 4 * z(3) - mp.mpf(16835) / 64 * z(4)
            + 1224 * z(5) - 540 * z(2) * z(3) + mp.mpf(4335) / 8 * z(6) - 320 * z(3) ** 2}
print('C3..C7 from the same assembly vs the closed forms:')
for nn in (3, 4, 5, 6, 7):
    v, ref = Cs[nn - 1], exact[nn]; r = abs((v - ref) / ref)
    print(f'  C{nn}: {mp.nstr(v, 25):>30}  exact {mp.nstr(ref, 25):>30}  rel {mp.nstr(r, 3)}')
    check(f'C{nn} vs closed form (relative)', r, tol_c)
# sensitivities (finite differences; C8 is linear in f_2_0_2 and f_3_0_1)
def C8_of(over):
    f2 = dict(fuse); f2.update(over); return C_numeric(f2, 4)[7]
C8 = Cs[7]
h = mp.mpf('1e-6')
d202 = (C8_of({(2, 0, 2): fuse[(2, 0, 2)] + h}) - C8) / h
d301 = (C8_of({(3, 0, 1): fuse[(3, 0, 1)] + h}) - C8) / h
check('dC8/df_2_0_2 = 2 (symbolic)', abs(d202 - 2), mp.mpf('1e-20'))
check('dC8/df_3_0_1 = 3/4 (symbolic)', abs(d301 - mp.mpf(3) / 4), mp.mpf('1e-20'))
# other inputs: M2/M3 recorded to ~1e-25 relative (gates); propagate a 1e-20 relative shift of each as a bound
oth = mp.mpf(0)
for k in need:
    if k in ((2, 0, 2), (3, 0, 1)) or k[0] == 0 and k[2] == 0: continue
    oth += abs(C8_of({k: fuse[k] * (1 + mp.mpf('1e-20'))}) - C8)
lin = abs(d202) * sig202 + abs(d301) * sig301 + oth
quad = mp.sqrt((d202 * sig202) ** 2 + (d301 * sig301) ** 2 + oth ** 2)
check('sigma(C8) finite, >= 0 and <= 0.3 (linear sum)', lin if (mp.isfinite(lin) and lin >= 0) else mp.inf, SIGMA_MAX)
# confirmatory cx record: the current (non-superseded) one; its amendment flag is bound into the C8 record
cxname = next((n for n in ('M4B_cx_check_v2.json', 'M4B_cx_check.json') if n in pv.registry() and pv.is_current(n)), 'M4B_cx_check_v2.json')
cxsha, cxamend = None, None
if cxname in pv.registry():
    try:
        cxsha = pv.verify_frozen(cxname)
        cxamend = json.load(open(os.path.join(RES, cxname))).get('amendment')
    except (pv.ProvenanceError, OSError) as e:
        print(e); cxsha = 'bad'
def show_c8():   # printed only once the record is frozen (stage 1) or verified (stage 2)
    print(f'\nC8 = {mp.nstr(C8, 15)}  +- {mp.nstr(lin, 3)} (linear sum; quadrature {mp.nstr(quad, 3)})')
    print(f'  components: 2 x sigma(f_2_0_2) = {mp.nstr(abs(d202) * sig202, 3)}, 3/4 x sigma(f_3_0_1) = {mp.nstr(abs(d301) * sig301, 3)}, '
          f'other inputs {mp.nstr(oth, 3)}')
out = {'C8': mp.nstr(C8, 20), 'C8_error': mp.nstr(lin, 3), 'C8_error_quadrature': mp.nstr(quad, 3),
       'components': {'2*sigma_f_2_0_2': mp.nstr(abs(d202) * sig202, 3), '0.75*sigma_f_3_0_1': mp.nstr(abs(d301) * sig301, 3),
                      'other_inputs': mp.nstr(oth, 3)},
       'sigma_inputs': {'f_2_0_2': mp.nstr(sig202, 3), 'f_3_0_1': mp.nstr(sig301, 3)},
       'inputs': {f'f_{a}_{b}_{c}': mp.nstr(v, 25) for (a, b, c), v in sorted(fuse.items())},
       'C3_C7': {f'C{nn}': mp.nstr(Cs[nn - 1], 25) for nn in (3, 4, 5, 6, 7)},
       'upstream_records': shas, 'confirmatory_cx_record': cxsha, 'confirmatory_cx_name': cxname,
       'confirmatory_cx_amended': cxamend is not None, 'confirmatory_cx_amendment': cxamend,
       'm4b_amendment': json.load(open(os.path.join(RES, M4BREC))).get('amendment') if os.path.exists(os.path.join(RES, M4BREC)) else None}
blob = json.dumps(out, indent=1, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()
recp = os.path.join(RES, OUTREC)
if verify:
    want = pv.registry().get(OUTREC, {}).get('sha256')
    same = sha == want and os.path.exists(recp) and open(recp).read() == blob
    check(f'rebuilt {OUTREC} byte-identical to the frozen record', 'identical' if same else f'differs ({sha[:12]})', 'identical', same)
    print('VERIFY', OUTREC, 'IDENTICAL' if same else 'DIFFERS', sha)
    report_and_exit('C8 ASSEMBLY (verify)')
if not compare:
    if not all(c[3] for c in checks):
        print('\nchecks failed: nothing published'); report_and_exit('C8 ASSEMBLY')
    commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or 'unknown'
    created = pv.publish_unit([(recp, blob)], register=(OUTREC, commit, 'C8 with uncertainty, frozen before any comparison'))[0]
    print(f'\nC8 record {"written" if created else "identical to the existing record"}: {os.path.relpath(recp, ROOT)} sha256 {sha}')
    show_c8()
    report_and_exit('C8 ASSEMBLY STAGE 1')
# ---------------------------------------------------------------- stage 2: comparison (read-only)
ok = os.path.exists(recp) and open(recp).read() == blob and sha == expect_sha
check('record identical to the recorded file and --expect-sha', 'ok' if ok else 'bad', 'all', ok)
try:
    pv.verify_frozen(OUTREC, expect_sha); ok = pv.is_current(OUTREC)
except pv.ProvenanceError as e:
    print(e); ok = False
check('C8 record matches the frozen registry and is current', 'ok' if ok else 'bad', 'all', ok)
rec = json.load(open(recp)) if os.path.exists(recp) else {}
ok = rec.get('upstream_records', {}).get(M4BREC) == pv.registry().get(M4BREC, {}).get('sha256') and pv.is_current(M4BREC)
check('C8 record bound to the current M4B record', 'ok' if ok else 'bad', 'all', ok)
try:
    s_cx = pv.verify_frozen(cxname)
    cxpass = json.load(open(os.path.join(RES, cxname))).get('pass') is True and pv.is_current(cxname)
    ok = cxpass and rec.get('confirmatory_cx_record') == s_cx
    print('confirmatory cx delta^0 check recorded:', 'PASS' if cxpass else 'FAIL', '; bound into the C8 record:', rec.get('confirmatory_cx_record') == s_cx)
except (pv.ProvenanceError, OSError, KeyError, ValueError) as e:
    print(e); ok = False
check('confirmatory cx check frozen, pass = true, bound into the C8 record', 'ok' if ok else 'bad', 'all', ok)
if not all(c[3] for c in checks):
    print('\nPROVISIONAL: comparison not run (failed checks above)')
    report_and_exit('C8 COMPARISON')
show_c8()
ref1 = mp.mpf('247.3812048049935')
ref2, sref2 = mp.mpf('242.83'), mp.mpf('2.37')
print('\nStage 2: comparison (C8 uncertainty = empirical numerical estimate, not a calibrated standard deviation)')
d1, d2 = C8 - ref1, C8 - ref2
print(f'  C8 (this work)                        = {mp.nstr(C8, 12)} +- {mp.nstr(lin, 3)} (empirical numerical uncertainty)')
print(f'  compendium value (unproved candidate) = {mp.nstr(ref1, 16)}')
print(f'    difference Delta = {mp.nstr(d1, 4)};  Delta / (our empirical uncertainty) = {mp.nstr(d1 / lin, 3)}')
print(f'  independent estimate                  = 242.83 (quoted uncertainty 2.37)')
print(f'    difference Delta = {mp.nstr(d2, 4)};  Delta / (our empirical uncertainty) = {mp.nstr(d2 / lin, 3)};  '
      f'Delta / 2.37 (ratio to that value\'s own quoted uncertainty) = {mp.nstr(d2 / sref2, 3)}')
report_and_exit('C8 COMPARISON')
