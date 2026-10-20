#!/usr/bin/env python3
"""Replay of every quoted d = 1 finite-coupling HT number from the shipped records.

Run from HT/code/lri_dressed_phi4_hpc_analysis (or via `make -f public.mk replay`). No production rerun; about one
minute on one core (the cutoff fits dominate).

  1. Records. Every JSON envelope under HT/data/HT_1d verifies against its own sha256 field (io.digest of the shipped
     solver). The dens_v1 results, manifests, bases and receipt are bound to the shipped solver code
     (source_sha256 = fingerprint of ../lri_dressed_phi4_hpc/src/lri_dressed/*.py, release_sha256 = its release
     fingerprint). Each result's local-basis sha256 names a shipped basis artifact. The prod1-7 records carry the
     source fingerprint of commit 4dfd833 (see PROVENANCE).
  2. Rows. dens_v1_rows.json (the input of the shipped analysis) is rebuilt from the dens_v1 result records with the
     field map of the production dump script (campaigns/dump_dens_v1.py) and compared value for value.
  3. Analysis. The shipped dens_v1.py and dens_v1_holdout.py run unchanged in a work copy on the rebuilt rows. Their
     outputs are compared with the shipped dens_v1_extrapolation.json and dens_v1_holdout.json within an environment
     tolerance (a quarter of the quoted half-spread plus 1e-8; see A2): scipy curve_fit may land in slightly different
     minima under other numpy/scipy versions.
  4. Quoted numbers. Each number of results/HT_1d/quoted_numbers.json is recomputed with the estimator named in its
     "rule" from the shipped analysis outputs (exact comparison rule) and, for fit-derived numbers, again from the
     step-3 refit, which must pass the same rule or lie within the environment tolerance of the shipped-output value.

Comparison rules (quoted_numbers.json "compare"):
  round    computed value rounded to the quoted number of decimals equals the quoted value
  paren    value(err): central value rounded to the quoted decimals and the error to the quoted last digit;
           value(err)(extra): also the extra one-sided shift (rule oneSided, signed, 1 significant figure) in the same
           last digit, e.g. 0.56733(20)(-50)
  range    both ends, each rounded to the quoted decimals (or to the quoted significant figures with "sig")
  sig      computed value rounded to the quoted significant figures equals the quoted value
  le       computed value <= quoted bound
  exact    equality (integers, protocol constants)
  about    'about X' statements: computed value within a factor 2 of X
  info     a judgement or a statement with no computation; listed, not compared
Floating point tolerances of step 3 are stated next to each check. Relative differences are used only for |ref| > 1e-9.
Writes a PASS/FAIL table to <work>/replay_ht1d.txt and exits 1 on any FAIL.
"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument('--data', default=str(PKG / '../../data/HT_1d'))
ap.add_argument('--results', default=str(PKG / '../../results/HT_1d'))
ap.add_argument('--code', default=str(PKG / '../lri_dressed_phi4_hpc'))
ap.add_argument('--work', default=str(PKG / '.work'))
a = ap.parse_args()
DATA, RES, CODE, WORK = (Path(x).resolve() for x in (a.data, a.results, a.code, a.work))
WORK.mkdir(parents=True, exist_ok=True)

ROWS = []          # (id, what, quoted, computed, verdict)
def row(i, what, quoted, computed, ok):
    v = 'INFO' if ok is None else ('PASS' if bool(ok) else 'FAIL')
    ROWS.append((i, what, str(quoted), str(computed), v))

def canonical(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(o): return hashlib.sha256(canonical(o)).hexdigest()

# ---------------------------------------------------------------- 1. records
def self_hash_ok(path):
    d = json.loads(Path(path).read_text()); s = d.pop('sha256', None)
    return s is not None and digest(d) == s, s

def source_fp(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).glob('*.py')): h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()

RELEASE_GLOBS = ('src/lri_dressed/*.py', 'scripts/*.py', 'cluster/symmetry/*', 'tests/*.py', 'reference/*.py',
                 'inputs/*.json', 'reference/production_*/src/lri_dressed/*.py', 'pyproject.toml', 'requirements-tested.txt')
def release_fp(root):  # same definition as lri_dressed.io.release_fingerprint
    root = Path(root); files = set()
    for g in RELEASE_GLOBS: files.update(p for p in root.glob(g) if p.is_file())
    h = hashlib.sha256()
    for p in sorted(files, key=lambda q: q.relative_to(root).as_posix()):
        h.update(p.relative_to(root).as_posix().encode() + b'\0'); h.update(p.read_bytes())
    return h.hexdigest()

DENS = DATA / 'dens_v1'; PROD = DATA / 'prod_window'
DENS_CAMPAIGNS = ('dens16_lo', 'dens16_mid', 'dens16_hi8', 'dens16_hi16', 'dens24_ctl')
PROD_SOURCE_4DFD833 = '92546a9d82d29b03f831cc7bc360a692da82c45204dec937791dfcbddd1c2404'  # fingerprint of 4dfd833 src, see PROVENANCE
allj = sorted(DATA.rglob('*.json'))
bad = [str(p.relative_to(DATA)) for p in allj if not self_hash_ok(p)[0]]
row('R1', 'JSON envelopes under data/HT_1d verify against their sha256', 'all', f'{len(allj)-len(bad)}/{len(allj)}', not bad and len(allj) > 0)
code_src = source_fp(CODE / 'src/lri_dressed'); code_rel = release_fp(CODE)
dres = sorted(DENS.glob('campaigns/*/results/*.json'))
srcs = {json.loads(p.read_text())['config']['source_sha256'] for p in dres}
row('R2', 'dens_v1 results: source_sha256 = fingerprint of shipped solver src', code_src[:16], ','.join(s[:16] for s in srcs), srcs == {code_src})
mans = [json.loads((DENS / 'campaigns' / c / 'manifest.json').read_text()) for c in DENS_CAMPAIGNS]
rels = {m['release_sha256'] for m in mans} | {json.loads((DENS / 'validation/570965/receipt.json').read_text())['payload']['release_sha256']}
row('R3', 'dens_v1 manifests and receipt 570965: release_sha256 = release fingerprint of shipped solver tree', code_rel[:16], ','.join(r[:16] for r in rels), rels == {code_rel})
rcpt = json.loads((DENS / 'validation/570965/receipt.json').read_text())['payload']
row('R4', 'validation receipt 570965 passed (6 stages)', 'True', f"{rcpt['passed']} ({len(rcpt['stages'])} stages)", rcpt['passed'] is True and len(rcpt['stages']) == 6)
ARTIFACTS = sorted(p for p in (DENS / 'bases/dens_v1').glob('x*.json') if re.search(r'_[0-9a-f]{12}\.json$', p.name))
bases = {json.loads(p.read_text())['sha256']: p.name for p in ARTIFACTS}
used = {json.loads(p.read_text())['config']['local_basis']['sha256'] for p in dres}
row('R5', 'every dens_v1 result names a shipped basis artifact (13 artifacts)', 13, f'{len(used & set(bases))} used, {len(bases)} shipped', used <= set(bases) and len(bases) == 13)
pres = sorted(PROD.glob('campaigns/*/results/*.json'))
dres_payloads = [json.loads(p.read_text())['payload'] for p in dres if 'dens16' in p.parts[-3]]
psrc = {json.loads(p.read_text())['config']['source_sha256'] for p in pres}
row('R6', 'prod1-7 results: source fingerprint of commit 4dfd833', PROD_SOURCE_4DFD833[:16], ','.join(x[:16] for x in psrc), psrc == {PROD_SOURCE_4DFD833})
row('R7', 'record counts: dens_v1 results, prod results', '201, 680', f'{len(dres)}, {len(pres)}', len(dres) == 201 and len(pres) == 680)

# ---------------------------------------------------------------- 2. rows (field map of campaigns/dump_dens_v1.py)
rebuilt = []
for c in DENS_CAMPAIGNS:
    for f in sorted((DENS / 'campaigns' / c / 'results').glob('N*.json')):
        d = json.loads(f.read_text()); p = d.get('payload', d)
        rebuilt.append(dict(campaign=c, sha256=d.get('sha256'), N=p['bath_cut'], nz=p['nz_per_parity'], delta=p['delta'],
            Delta_thermal=p['Delta_thermal'], even_gaps=p.get('even_gaps'), odd_gaps=p.get('odd_gaps'), theta=p.get('theta'),
            tuning_residual=p.get('tuning_residual'), seconds=p.get('seconds'), threads=p.get('execution', {}).get('threads'),
            peak_rss_mib=p.get('execution', {}).get('peak_rss_mib'), host_campaign=c))
shipped_rows = json.loads((PKG / 'dens_v1_rows.json').read_text())
key = lambda r: r['sha256']
sm = {key(r): {k: v for k, v in r.items() if k != 'path'} for r in shipped_rows}
rb = {key(r): r for r in rebuilt}
row('W1', 'dens_v1_rows.json rebuilt from the records (all fields except the cluster path, exact)', len(shipped_rows),
    f'{sum(rb.get(k) == v for k, v in sm.items())} equal of {len(rebuilt)}', rb == sm)

# ---------------------------------------------------------------- 3. analysis in a work copy
A = WORK / 'analysis'
if A.exists(): shutil.rmtree(A)
(A / 'nrg').mkdir(parents=True)
for f in ('extrapolate.py', 'collected.json', 'dens_v1.py', 'dens_v1_holdout.py'): shutil.copy2(PKG / f, A / f)
shutil.copy2(PKG / 'nrg/ds13_final.json', A / 'nrg/ds13_final.json')
shutil.copy2(PKG / 'extrapolation.json', A / 'extrapolation.json')  # rewritten by importing extrapolate.py
(A / 'dens_v1_rows.json').write_text(json.dumps([dict(r, path=None) for r in rebuilt]))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
for script in ('dens_v1.py', 'dens_v1_holdout.py'):
    pr = subprocess.run([sys.executable, script], cwd=A, env=env, capture_output=True, text=True)
    (WORK / (script + '.out')).write_text(pr.stdout + pr.stderr)
    row('A0', f'{script} runs unchanged on the rebuilt rows', 'rc 0', f'rc {pr.returncode}', pr.returncode == 0)
X = json.loads((A / 'dens_v1_extrapolation.json').read_text()); X0 = json.loads((PKG / 'dens_v1_extrapolation.json').read_text())
H = json.loads((A / 'dens_v1_holdout.json').read_text()); H0 = json.loads((PKG / 'dens_v1_holdout.json').read_text())
OLD = json.loads((A / 'extrapolation.json').read_text()); OLD0 = json.loads((PKG / 'extrapolation.json').read_text())

# The cutoff fits use scipy curve_fit from several starting exponents. Different numpy/scipy/libm versions can land in
# slightly different minima (measured: production analysis environment Python 3.10.12, numpy 1.24.4, scipy 1.11.1 vs
# symmetry Python 3.11.4, numpy 2.3.5, scipy 1.17.0: D_inf moves by at most 0.11 of its half-spread, 1.7e-6 at
# Ds = 0.175, and by <= 3e-8 elsewhere). Environment tolerance: a quarter of the shipped half-spread plus 1e-8 for
# every fitted value; 0.02 for median exponents. Flags (stable, number of accepted fits) must be equal.
def envtol(sp): return 0.25 * sp + 1e-8
bad2 = []; meta_ok = True; worst2 = 0.
for x, y in zip(X, X0):
    meta_ok &= (x['delta'] == y['delta'] and x['stable'] == y['stable'] and bool(x['fit']) == bool(y['fit']))
    if x['fit'] and y['fit']:
        meta_ok &= x['fit']['n_fits'] == y['fit']['n_fits']; t = envtol(y['fit']['spread_half'])
        for k in ('D_inf', 'spread_half', 'min', 'max'):
            dv = abs(x['fit'][k] - y['fit'][k]); worst2 = max(worst2, dv / t)
            if dv > t: bad2.append((y['delta'], k, dv))
        if abs(x['fit']['omega_median'] - y['fit']['omega_median']) > 0.02: bad2.append((y['delta'], 'omega_median', 0))
row('A2', 'refit vs shipped fit summaries (D_inf, half-spread, min, max <= 1/4 half-spread + 1e-8; omega <= 0.02; flags equal)', 'shipped',
    f'worst {worst2:.2f} of tolerance, flags {"equal" if meta_ok else "DIFFER"}', meta_ok and not bad2)
bad3 = []; worst3 = 0.
for x, y in zip(H, H0):
    for c in y['by_cut']:
        u, v = x['by_cut'].get(c), y['by_cut'][c]
        if u is None or u['n'] != v['n'] or u['stable'] != v['stable']: bad3.append((y['delta'], c, 'flags')); continue
        dv = abs(u['D_inf'] - v['D_inf']); t = envtol(v['half_spread']); worst3 = max(worst3, dv / t)
        if dv > t: bad3.append((y['delta'], c, dv))
        for n in v['pred']:
            dv = abs(u['pred'][n]['median'] - v['pred'][n]['median']); t = envtol(v['pred'][n]['half_spread']); worst3 = max(worst3, dv / t)
            if dv > t: bad3.append((y['delta'], c, n, dv))
row('A3', 'refit vs shipped held-out fits (D_inf and predictions per N_cut, same tolerance)', 'shipped', f'worst {worst3:.2f} of tolerance', not bad3)
w4 = max([abs(x['fit']['D_inf'] - y['fit']['D_inf']) / envtol(y['fit']['spread_half']) for x, y in zip(OLD['results'], OLD0['results']) if x.get('fit') and y.get('fit')] or [0.])
row('A4', 'refit vs shipped earlier composite-series extrapolation (extrapolation.json, rewritten on import; same tolerance)', 'shipped', f'worst {w4:.2f} of tolerance', w4 <= 1)

# ---------------------------------------------------------------- 4. quoted numbers
def set_ctx(Xl, Hl):  # the quoted numbers are computed from the shipped outputs (exact) and from the refit (environment)
    global X, H, XD, HD, ser, MDROWS
    X, H = Xl, Hl; XD = {x['delta']: x for x in X}; HD = {r['delta']: r for r in H}
    if 'MDROWS_SHIPPED' in globals(): MDROWS = MDROWS_SHIPPED if Xl is X0 else MDROWS_REFIT
    ser = {d: dict(zip(XD[d]['cuts'], XD[d]['values'])) for d in XD}
X_refit, H_refit = X, H
set_ctx(X0, H0)
def accepted(fl, ymax, RMS=3e-6):  # extrapolate.summarize acceptance
    return [f for f in fl if f['rms'] < RMS and 0.2 < f['omega'] < 4 and abs(f['D_inf'] - ymax) < 0.05]
def slopes(d):
    N = sorted(ser[d]); y = [ser[d][n] for n in N]
    return [(math.sqrt(N[i] * N[i + 1]), (y[i + 1] - y[i]) / math.log(N[i + 1] / N[i])) for i in range(len(N) - 1)]
def omega_eff(d):  # -dln(slope)/dlnN from the slopes on [N-3, N-1] and [N+1, N+3], at N ~ 15, 19, ..., 35
    s = slopes(d); out = []
    for i in range(0, len(s) - 2, 2):
        (n0, s0), (n1, _), (n2, s2) = s[i], s[i + 1], s[i + 2]
        out.append((n1, -math.log(s2 / s0) / math.log(n2 / n0) if s0 * s2 > 0 else float('nan')))
    return out
REF_EPS = {2: (math.pi + 4 * math.log(2)) / 9, 3: -3.71985632290183342249, 4: 45.42488010356, 5: -731.13947662454,
           6: 14331.68703277, 7: -322550.}  # = extrapolate.REF_EPS (GFF coefficients C2..C7 in d = 1)
def eps_sum(d, k):
    e = 1 - 4 * d; return 0.5 - e / 6 + sum(REF_EPS[j] * e ** j for j in range(2, k + 1))
# NRG reference for the comparisons: results/HT_1d/nrg_reference.json, a copy of the NRG folder's final table
# (NRG/results/ds13_final.json, re-analysed 2026-10-13: settled late-window estimator). The analysis folder's own
# nrg/ds13_final.json is the earlier NRG table that dens_v1.py printed; it is not used for any quoted comparison.
nrg = {round(r['ds'], 6): dict(r, total_uncertainty=r.get('total') or r.get('total_uncertainty') or 0.) for r in json.loads((RES / 'nrg_reference.json').read_text())}
NRG_PUB = PKG / '../../../NRG/results/ds13_final.json'
if NRG_PUB.exists():
    row('N0', 'nrg_reference.json equals the NRG folder\'s published table NRG/results/ds13_final.json', 'equal',
        'equal' if NRG_PUB.read_bytes() == (RES / 'nrg_reference.json').read_bytes() else 'DIFFERENT', NRG_PUB.read_bytes() == (RES / 'nrg_reference.json').read_bytes())
else:
    row('N0', 'nrg_reference.json vs NRG/results/ds13_final.json (not in this tree)', 'equal', 'NRG folder absent', None)
sys.path.insert(0, str(HERE)); import model_dependence_ht1d as MD
MDROWS_REFIT = {r['delta']: r for r in MD.compute(RES / 'nrg_reference.json')}
MDROWS_SHIPPED = {r['delta']: r for r in json.loads((RES / 'model_dependence.json').read_text())}
MDROWS = MDROWS_SHIPPED

# identity records (python -m lri_dressed identities on prod records at N = 16, 20, 24, 28)
ident = {}
prod_sha = {json.loads(p.read_text())['sha256'] for p in pres}
ibind = True
for f in sorted((PKG / 'identities').glob('*.json')):
    d = json.loads(f.read_text()); w = 'raw' if '_none_' in f.name else 'win'
    ibind &= d['record_sha256'] in prod_sha
    for op in ('sigma', 'shadow', 'epsilon'):
        l1 = d['descendants'][op].get('level1', {})
        ident[(d['delta'], d['bath_cut'], w, op)] = (l1.get('violation'), l1.get('status'))
row('I0', 'identity records name a shipped prod record (record_sha256)', '104/104', f"{len(list((PKG / 'identities').glob('*.json')))} files, bound={ibind}", ibind)

def computed(q):
    r = q['rule']; d = q.get('delta')
    if r == 'N40':      return ser[d][40]
    if r == 'Dinf':  # (D_inf, half-spread[, -one-sided shift when the quoted text has a second bracket])
        v = (XD[d]['fit']['D_inf'], XD[d]['fit']['spread_half'])
        return v + (-computed(dict(q, rule='oneSided')),) if str(q['quoted']).count('(') == 2 else v
    if r == 'status':  # computed part of the status word: 'stable' (quoted final or one-sided): the fits pass the
        # stability rule; 'unstable': they fail it while Delta(N) still rises at N = 40; 'no limit': Delta(N) falls at
        # N = 40 (the sequence has turned over) or no fit is accepted. final vs one-sided is a judgement (row U00).
        st, s40 = XD[d]['stable'], slopes(d)[-1][1]
        if st: return 'stable'
        return 'unstable' if (XD[d]['fit'] and s40 > 0) else 'no limit'
    if r == 'Nmin':     return min(min(x['cuts']) for x in X)
    if r == 'Nmax':     return min(max(x['cuts']) for x in X)
    if r == 'NminRange':return sorted({f['Nmin'] for x in X for f in x['fits']})[::6]  # [12, 24]
    if r == 'Nfits':    return max(len(x['fits']) for x in X)
    if r == 'densK':    return sorted({x['nz'] for x in rebuilt if x['campaign'].startswith('dens16')})[0]
    if r in ('densTrain', 'densTeacher', 'densKeep'):  # config of the 13 shipped basis artifacts
        t = [json.loads(p.read_text())['config'] for p in ARTIFACTS]
        vals = {tt[{'densTrain': 'bath_cut', 'densTeacher': 'teacher_nz', 'densKeep': 'keep'}[r]] for tt in t}
        return vals.pop() if len(vals) == 1 else sorted(vals)
    if r == 'omegaRange':
        om = [XD[x]['fit']['omega_median'] for x in XD if XD[x]['stable']]; return (min(om), max(om))
    if r == 'omegaEffLevel':  # value at the largest N (35), where it levels off
        return omega_eff(d)[-1][1]
    if r == 'omegaEffRange':
        o = omega_eff(d); return (o[0][1], o[-1][1])
    if r == 'holdout':  # max |actual - median prediction| at N = 34..40 from fits on N <= cut, over Ds >= 0.05
        return max(abs(p['actual'] - p['median']) for x in H if x['delta'] >= 0.05 for p in x['by_cut'][str(q['cut'])]['pred'].values())
    if r == 'oneSided':  # slope at N = 40 times (1/w - 1/(w + 0.2)), w = omega_eff at N ~ 35
        s = slopes(d)[-1][1]; w = omega_eff(d)[-1][1]; return s * (1 / w - 1 / (w + 0.2))
    if r == 'epsDiff':  return XD[d]['fit']['D_inf'] - eps_sum(d, 7)
    if r == 'epsBand':
        v = [eps_sum(d, k) for k in (4, 5, 6, 7)]; return (min(v), max(v))
    if r == 'epsBandContains':
        v = [eps_sum(d, k) for k in (4, 5, 6, 7)]; return min(v) <= XD[d]['fit']['D_inf'] <= max(v)
    if r == 'extrapShift':
        v = [XD[x]['fit']['D_inf'] - ser[x][40] for x in (0.125, 0.1, 0.075)]; return (min(v), max(v))
    if r == 'peak':     return max(ser[d], key=ser[d].get)
    if r == 'slopeN40': return slopes(d)[-1][1]
    if r == 'fitsRange':  # accepted fits of the named forms, N <= 40
        fl = [f for f in accepted(XD[d]['fits'], ser[d][40]) if f['form'] in q['forms']]
        return (min(f['D_inf'] for f in fl), max(f['D_inf'] for f in fl))
    if r == 'fitsMin':
        fl = [f for f in accepted(XD[d]['fits'], ser[d][40]) if f['form'] in q['forms']]; return min(f['D_inf'] for f in fl)
    if r == 'spreadMaxWeak':  # largest half-spread at Ds >= 0.15
        return max(XD[x]['fit']['spread_half'] for x in XD if x >= 0.15)
    if r == 'nrgMax':
        return max(abs(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E']) for x in XD if 0.075 <= x <= 0.2)
    if r == 'nrgDiffs':  return tuple(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E'] for x in q['deltas'])
    if r == 'nrgPulls':  return tuple((XD[x]['fit']['D_inf'] - nrg[x]['Delta_E']) / math.hypot(XD[x]['fit']['spread_half'], nrg[x]['total_uncertainty']) for x in q['deltas'])
    if r == 'nrgDiffN40': return ser[d][40] - nrg[d]['Delta_E']
    if r == 'nrgBracket':  # NRG inside [Delta(40), Delta(40) + slope(40)/omega_eff(35)] of the window series at every Ds
        return all(MDROWS[x]['bracket'][0] <= MDROWS[x]['nrg'] <= MDROWS[x]['bracket'][1] for x in q['deltas'])
    if r == 'rawBelowWinAbove':  # raw limit below NRG and window limit above it
        return all(MDROWS[x]['raw'] < MDROWS[x]['nrg'] < MDROWS[x]['window'] for x in q['deltas'])
    if r == 'tailShiftMax': return max(MDROWS[x]['tail_shift'] for x in q['deltas'])
    if r == 'winMinusRaw': return tuple(MDROWS[x]['window'] - MDROWS[x]['raw'] for x in q['deltas'])
    if r == 'winMinusRawRange':
        v = [MDROWS[x]['window'] - MDROWS[x]['raw'] for x in q['deltas']]; return (min(v), max(v))
    if r == 'nrgDiffMin': return min(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E'] for x in q['deltas'])
    if r == 'nrgDiffMaxAbs': return max(abs(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E']) for x in q['deltas'])
    if r == 'nrgRelMax': return max(abs(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E']) / nrg[x]['Delta_E'] for x in q['deltas'])
    if r == 'nrgAllAbove': return all(XD[x]['fit']['D_inf'] > nrg[x]['Delta_E'] for x in q['deltas'])
    if r == 'gapExceedsSpread': return all(XD[x]['fit']['D_inf'] - nrg[x]['Delta_E'] > XD[x]['fit']['spread_half'] for x in q['deltas'])
    if r == 'winMinusRawMax': return max(abs(MDROWS[x]['window'] - MDROWS[x]['raw']) for x in q['deltas'])
    if r == 'Asign':  # A of the dens16 records: largest Ds with A of both signs over the cutoffs
        sg = {}
        for x in dres_payloads: sg.setdefault(x['delta'], set()).add(x['A'] > 0)
        assert all(sg[d0] == {False} for d0 in (0.2, 0.175)) and all(sg[d0] == {True} for d0 in sg if d0 >= 0.225)
        return max(d0 for d0, v in sg.items() if v == {True, False})
    if r == 'nzSeries':  # prod records, consistent window, N = 28, nz 32/40/48
        out = {}
        for p in pres:
            dd = json.loads(p.read_text()); c, pl = dd['config'], dd['payload']
            if c.get('window') == 'vacuum' and c.get('window_mode') == 'consistent' and pl['bath_cut'] == 28 and abs(pl['delta'] - d) < 1e-12:
                out[pl['nz_per_parity']] = pl['Delta_thermal']
        return tuple(out[n] for n in (32, 40, 48))
    if r == 'spreadMaxFinal':
        return max(XD[x]['fit']['spread_half'] for x in XD if x >= 0.1)
    if r == 'basisErrN32':  # dens16 vs the largest-nz prod reference (nz >= 48, osc 384, consistent window) at N = 32
        ref = {}
        for p in pres:
            dd = json.loads(p.read_text()); c, pl = dd['config'], dd['payload']
            if c.get('window') == 'vacuum' and c.get('window_mode') == 'consistent' and pl['nz_per_parity'] >= 48 and c.get('osc') == 384 and pl['bath_cut'] == 32:
                k = round(pl['delta'], 6)
                if k not in ref or pl['nz_per_parity'] > ref[k][0]: ref[k] = (pl['nz_per_parity'], pl['Delta_thermal'])
        return max(abs(x['Delta_thermal'] - ref[round(x['delta'], 6)][1]) for x in rebuilt if x['nz'] == 16 and x['N'] == 32 and round(x['delta'], 6) in ref)
    if r == 'rawViol':  # raw level-1 violations, Ds <= 0.1, N = 16..28, sigma/shadow/E with an unambiguous identification
        v = [abs(x) for (dl, N, w, op), (x, st) in ident.items() if w == 'raw' and dl <= 0.1 and st == 'ok']; return (min(v), max(v))
    if r == 'winReduce':  # |raw/window| for sigma at N = 28, Ds <= 0.15, wherever both are identified (ok or ambiguous)
        v = []
        for dl in sorted({k[0] for k in ident}):
            rr, ww = ident[(dl, 28, 'raw', 'sigma')], ident[(dl, 28, 'win', 'sigma')]
            if dl <= 0.15 and rr[0] is not None and ww[0] is not None: v.append(abs(rr[0] / ww[0]))
        return (min(v), max(v))
    if r == 'resSig':  # median |window violation| of sigma and shadow, Ds <= 0.1, N = 28, unambiguous
        v = sorted(abs(x) for (dl, N, w, op), (x, st) in ident.items() if w == 'win' and dl <= 0.1 and N == 28 and op in ('sigma', 'shadow') and st == 'ok')
        return v[len(v) // 2]
    if r == 'resE':  # largest |window violation| of E, Ds <= 0.05, N = 28, unambiguous
        return max(abs(x) for (dl, N, w, op), (x, st) in ident.items() if w == 'win' and op == 'epsilon' and dl <= 0.05 and N == 28 and st == 'ok')
    if r == 'violN':  # cutoffs of the raw identity records behind V1 (Ds <= 0.1)
        n = {N for (dl, N, w, op) in ident if w == 'raw' and dl <= 0.1}; return (min(n), max(n))
    if r == 'identN':  # largest cutoff of the identity records: the N of tab_d1_ident.tex and of V2-V4
        return max(N for (dl, N, w, op) in ident)
    if r == 'identRows':  # rows of tab_d1_ident.tex (N = 28) at q['deltas'], formatted as make_tables_ht1d.py writes them
        cell = lambda v: '---' if v[0] is None else '$%+.4f%s$' % (v[0], '' if v[1] == 'ok' else '^a')
        return ['%g & ' % dl + ' & '.join(cell(ident[(dl, 28, w, op)]) for w in ('raw', 'win') for op in ('sigma', 'shadow', 'epsilon')) + '\\\\'
                for dl in q['deltas']]
    raise KeyError(r)

def decimals(s): s = s.strip(); return len(s.split('.')[1]) if '.' in s else 0
def sigfig_round(x, n): return 0. if x == 0 else round(x, n - 1 - int(math.floor(math.log10(abs(x)))))
def check(q, c):
    m = q['compare']; Q = q['quoted']
    if m == 'info': return None
    if m == 'exact': return c == Q
    if m == 'le': return c <= float(Q)
    if m == 'round': return round(c, decimals(Q)) == float(Q)
    if m == 'sig': return sigfig_round(c, q.get('sig', 1)) == float(Q)
    if m == 'about': return float(Q) / 2 <= c <= 2 * float(Q)  # an 'about' statement: within a factor 2
    if m == 'paren':  # "0.50612(4)" or "0.56733(20)(-50)"
        val, err, extra = re.fullmatch(r'(-?[0-9.]+)\((\d+)\)(?:\((-?\d+)\))?', Q).groups(); n = decimals(val)
        ok = round(c[0], n) == float(val) and round(c[1] * 10 ** n) == int(err)
        return ok and (extra is None or round(sigfig_round(c[2], 1) * 10 ** n) == int(extra))
    if m == 'range':
        lo, hi = Q
        if q.get('sig'): return sigfig_round(c[0], q['sig']) == float(lo) and sigfig_round(c[1], q['sig']) == float(hi)
        return round(c[0], decimals(lo)) == float(lo) and round(c[1], decimals(hi)) == float(hi)
    if m == 'true': return c is True
    if m == 'list_sig1': return all(sigfig_round(u, 1) == float(v) for u, v in zip(c, Q))
    if m == 'list_round': return all(round(u, decimals(v)) == float(v) for u, v in zip(c, Q))
    if m == 'list_sig': return all(sigfig_round(u, q.get('sig', 1)) == float(v) for u, v in zip(c, Q))
    if m == 'range_sigs': return all(sigfig_round(u, n) == float(v) for u, v, n in zip(c, Q, q['sigs']))
    if m == 'status': return c == {'final': 'stable', 'one-sided': 'stable'}.get(Q, Q)
    raise KeyError(m)

def fmt(c):
    if isinstance(c, float): return f'{c:.10g}'
    if isinstance(c, tuple): return '(' + ', '.join(fmt(x) for x in c) + ')'
    return str(c)

FIT_RULES = {'nrgDiffMin', 'nrgDiffMaxAbs', 'nrgRelMax', 'nrgAllAbove', 'gapExceedsSpread', 'tailShiftMax', 'spreadMaxFinal', 'Dinf', 'epsDiff', 'epsBandContains', 'extrapShift', 'fitsRange', 'fitsMin', 'nrgMax', 'nrgDiffs', 'nrgPulls', 'spreadMaxWeak', 'holdout', 'omegaRange', 'status'}
def env_close(q, c0, c1):  # refit value within the environment tolerance of the shipped-output value
    if q['rule'] == 'omegaRange': return all(abs(u - v) <= 0.02 for u, v in zip(c0, c1))
    if q['rule'] in ('status', 'epsBandContains', 'nrgAllAbove', 'gapExceedsSpread'): return c0 == c1
    sp = XD0[q['delta']]['fit']['spread_half'] if q.get('delta') in XD0 and XD0[q['delta']]['fit'] else 0.
    if q['rule'] == 'spreadMaxWeak': sp = c0
    if q['rule'] == 'holdout': sp = 1e-6
    if q['rule'] in ('extrapShift', 'nrgMax', 'nrgDiffs', 'nrgDiffMin', 'nrgDiffMaxAbs'): sp = max(XD0[d]['fit']['spread_half'] for d in (0.2, 0.175, 0.15, 0.125, 0.1, 0.075))
    if q['rule'] == 'nrgPulls': return all(abs(u - v) <= 0.05 for u, v in zip(c0, c1))
    if q['rule'] == 'tailShiftMax': sp = 2e-4
    a0 = c0 if isinstance(c0, tuple) else (c0,); a1 = c1 if isinstance(c1, tuple) else (c1,)
    return all(abs(u - v) <= envtol(sp) for u, v in zip(a0, a1))
XD0 = {x['delta']: x for x in X0}
Qs = json.loads((RES / 'quoted_numbers.json').read_text())
for q in Qs['numbers']:
    if q['compare'] == 'info':
        row(q['id'], q['what'], q['quoted'], q.get('note', 'judgement; not computed'), None); continue
    try:
        set_ctx(X0, H0); c0 = computed(q); ok = check(q, c0); txt = fmt(c0)
        if q.get('rule') in FIT_RULES:
            set_ctx(X_refit, H_refit); c1 = computed(q)
            ok1 = check(q, c1) or env_close(q, c0, c1); ok = ok and ok1
            txt += f' | refit {fmt(c1)}' + ('' if check(q, c1) else (' (within env. tolerance)' if ok1 else ' (OUTSIDE env. tolerance)'))
    except Exception as e:  # noqa: BLE001
        txt, ok = f'error: {e!r}', False
    row(q['id'], q['what'], q['quoted'], txt, ok)
set_ctx(X0, H0)

# ---------------------------------------------------------------- 5. published tables
T = WORK / 'tables'
pr = subprocess.run([sys.executable, str(HERE / 'make_tables_ht1d.py'), '--out', str(T), '--quoted', str(RES / 'quoted_numbers.json')],
                    capture_output=True, text=True, env=env)
same = [n for n in ('delta_eps_table.md', 'identity_violations.md', 'holdout_and_local_exponent.md')
        if (T / n).exists() and (RES / n).exists() and (T / n).read_bytes() == (RES / n).read_bytes()]
same += [n for n in ('tab_d1_main.tex', 'tab_d1_ident.tex', 'tab_d1_omegaeff.tex')
         if (T / n).exists() and (RES / 'note_tables' / n).exists() and (T / n).read_bytes() == (RES / 'note_tables' / n).read_bytes()]
row('T1', 'results/HT_1d tables and note table fragments regenerated byte for byte (make_tables_ht1d.py, shipped outputs)', '6 files', f'{len(same)} equal (rc {pr.returncode})', pr.returncode == 0 and len(same) == 6)

# ---------------------------------------------------------------- report
w = max(len(r[1]) for r in ROWS)
lines = [f"{'id':6} {'verdict':7} {'check':{w}}  quoted | computed"] + \
        [f'{i:6} {v:7} {what:{w}}  {qq} | {cc}' for i, what, qq, cc, v in ROWS]
nf = sum(r[4] == 'FAIL' for r in ROWS); npass = sum(r[4] == 'PASS' for r in ROWS); ninfo = sum(r[4] == 'INFO' for r in ROWS)
lines.append(f'\n{npass} PASS, {nf} FAIL, {ninfo} INFO (judgements, not computed)')
(WORK / 'replay_ht1d.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
sys.exit(1 if nf else 0)
