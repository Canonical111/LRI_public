"""M4 part B gate: four bubbles at delta^1 (f_3_0_1), blind.
Inputs: two complete series-mode n = 4, kmax >= 1 runs at different grids (FINE, COARSE; directories of *.out files) of
the mirror-reduced sector set (results/m4_inputs/n4.mirror.json: weight 2 / 1 / 0 per sector), and optionally complex-K
delta^0 runs (--cx DIR, repeatable; each a complete cx-mode run at one K). Every mandatory check has an explicit
threshold and must pass before anything is published:
  upstream   M2, M3 records match the frozen-record registry; the m4_step0 maps are current and built from them;
  input      n4.txt hash = manifest; the mirror-weight file is for that input and equals cluster_gen.mirror_weights
             (regenerated here);
  files      every output validates; the merged sector set of each level = the sectors of nonzero mirror weight
             exactly; one engine build per level; mode ser, n 4, rigorous radii (-radii rouche);
  ba         delta^0 Laurent coefficients w^-16..w^0 vs the exact Bethe ansatz (fine level; default <= 1e-6 relative to
             max(|exact|, 1)), and every resolved coefficient within 3x its error estimate (two-grid + roundoff
             estimate); every --cx run: J4^(0)(K) vs the Bethe ansatz (default <= 1e-12 relative);
  relations  EVERY delta^1 F-analyticity relation F3[d^1 w^j] = 0, j = -12..-1, of m4_step0 with the measured J4^(1)
             (fine level: <= 3x its error estimate, i.e. the two-grid change of the residual plus the propagated
             roundoff estimate, and <= 1e-7 relative; coarse reported, default <= 1e-6);
  f301       f_3_0_1 = F3[d^1 w^0] resolved and finite at both levels; total error estimate
             |fine - coarse| + roundoff estimate(fine) <= 0.4 (user decision 2026-10-14: sigma(C8) <= 0.3, weight 3/4).
The record results/M4B_flow_coefficients.json and a provenance sidecar are published once and added to the
frozen-record registry. No C_n is computed here.
  roundoff  every output carries magnitude bounds (engine -bound 1); per level the first-order magnitude bound of
             f_3_0_1, sum_s eps_s * |R . Gamma * B_s| (eps 2^-53 double, 2^-104 double-double), is reported, and the
             roundoff ESTIMATE is RO_FACTOR (default 0.01) times it: with double-double accumulators the measured
             |double - dd| / bound was <= 7.6e-3 on all 14 pilot pairs (7 heavy sectors x taurat 0.1, 0.2); gated
             (default <= 0.2; the total f_3_0_1 error estimate below is the binding check);
             sectors with a large double-precision bound may be recomputed with the double-double build at the same
             grid (--fine-dd / --coarse-dd DIR, a subset of sectors): those values replace the double ones, and every
             such pair must agree within the double bound (a check of the bound).
usage: python m4b_gate.py FINE_DIR COARSE_DIR [--fine-dd DIR] [--coarse-dd DIR] [--cx DIR ...] [--tol-ba X]
                          [--tol-cx X] [--tol-rel X] [--tol-rel-coarse X] [--tol-f X] [--tol-roundoff X] [--dry]"""
import sys, os, json, hashlib, glob, subprocess
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv
from cluster_assemble import read_many, assemble_ser, assemble_cx, OutputError
from cluster_check import J4_BA
import builds as buildmf
mp.mp.dps = 40
RES = pv.RES
ROOT = os.path.join(HERE, '..')

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
cxdirs = []
while '--cx' in args:
    cxdirs.append(opt('--cx', None))
tol_ba = mp.mpf(opt('--tol-ba', '1e-6')); tol_cx = mp.mpf(opt('--tol-cx', '1e-12'))
tol_rel = mp.mpf(opt('--tol-rel', '1e-7')); tol_relc = mp.mpf(opt('--tol-rel-coarse', '1e-6'))
tol_f = mp.mpf(opt('--tol-f', '0.37'))          # budget: 3/4 x 0.37 + 2 x 0.01 (M4A) <= 0.3 = sigma(C8) limit
tol_ro = mp.mpf(opt('--tol-roundoff', '0.2'))
tol_ratio = mp.mpf('0.1')                          # MSC-018(b): any sampled |double - dd| / (eps B) > 0.1 -> stop
ro_factor = mp.mpf('0.01')                         # replaced by max(10 x largest sampled ratio, 0.01)
dd_dirs = {'fine': opt('--fine-dd', None), 'coarse': opt('--coarse-dd', None), 'radius': opt('--radius-dd', None)}
radius_dir = opt('--radius', None)
sample_dir = opt('--dd-sample', None)
sample2_dir = opt('--dd-sample2', None)
manifest_path = os.path.join(RES, 'm4_inputs', 'n4.manifest.json')
mirror_path = os.path.join(RES, 'm4_inputs', 'n4.mirror.json')
dry = '--dry' in args
if dry: args.remove('--dry')
verify = '--verify' in args          # fix round 4: rebuild the frozen v2 record and compare byte for byte; never writes
report_path = opt('--report', None)  # MSC-031: optional NEW file for the machine-readable verify report (else stdout)
if verify:
    args.remove('--verify'); dry = True
REPORT = None
if report_path:
    import provenance as _pv0
    try:
        REPORT = _pv0.safe_create_report(report_path)     # checked before any computation; never truncates
    except _pv0.ProvenanceError as e:
        sys.exit(f'--report refused: {e}')
# MSC-032: in verify mode the frozen provenance sidecar must exist, be the committed blob, and carry every mandatory field
SIDECAR_FIELDS = ('record', 'record_sha256', 'sources', 'engine_input', 'output_fingerprints', 'step0_maps', 'step0_generator',
                  'gate', 'design', 'builds_manifest', 'upstream_records')
SIDECAR_ALLOWED_DIFF = ('gate',)              # the gate file hash changes with every code fix
SIDECAR_ALLOWED_EXTRA = ('designs_verified',)  # supplemental since fix round 4
if verify:
    import provenance as _pv1
    _side = os.path.join(_pv1.RES, 'M4B_flow_coefficients_v2.provenance.json')
    _ok, _c, _b = _pv1.committed_blob_ok(_side)
    try:
        _fz = json.load(open(_side)); _miss = [k for k in SIDECAR_FIELDS if not _fz.get(k)]
        _okr = _fz.get('record_sha256') == _pv1.registry().get('M4B_flow_coefficients_v2.json', {}).get('sha256')
    except (OSError, ValueError):
        _fz, _miss, _okr = None, list(SIDECAR_FIELDS), False
    if not (_ok and not _miss and _okr):
        print(f'verify: provenance sidecar not authentic (committed blob {_ok}, missing fields {_miss}, record hash bound {_okr})')
        print('M4B GATE (verify) FAIL'); sys.exit(1)
if os.environ.get('LRI_TEST_LEGACY_ALLOWLIST') and not dry:
    sys.exit('LRI_TEST_LEGACY_ALLOWLIST is set (test override): only --dry runs are allowed')
if len(args) != 2:
    sys.exit(__doc__)
levels = {'fine': args[0], 'coarse': args[1]}
if radius_dir: levels['radius'] = radius_dir
if not dry and not (radius_dir and sample_dir and sample2_dir):
    sys.exit('fix round 3: publishing needs --radius DIR, --dd-sample DIR and --dd-sample2 DIR (MSC-018, amendment B); use --dry otherwise')
TAG = 'M4B'
RECNAME = 'M4B_flow_coefficients_v2.json'
V1 = 'M4B_flow_coefficients.json'

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
rel = lambda p: os.path.relpath(p, ROOT)

# ---------------------------------------------------------------- upstream, input, mirror weights
try:
    m2sha = pv.verify_frozen('M2_flow_coefficients.json'); m3sha = pv.verify_frozen('M3_flow_coefficients.json'); ok = True
except pv.ProvenanceError as e:
    print(e); ok = False; m2sha = m3sha = None
check('upstream M2, M3 records match the frozen registry', 'ok' if ok else 'bad', 'all', ok)
try:
    resp_raw, pv_resp = pv.load_step0('m4_step0_response.json')
    base_raw, pv_base = pv.load_step0('m4_step0_F3base.json')
    ok = all(p['upstream'].get('M2_flow_coefficients.json') == m2sha and p['upstream'].get('M3_flow_coefficients.json') == m3sha
             for p in (pv_resp, pv_base))
except pv.ProvenanceError as e:
    print(e); ok = False
check('m4_step0 maps current and built from those records', 'ok' if ok else 'bad', 'all', ok)
manifest = json.load(open(manifest_path))
mirror = json.load(open(mirror_path))
import cluster_gen
regen = cluster_gen.mirror_weights(cluster_gen.generate(4, verbose=False, sampled_radii=False))
ok = mirror['input_sha256'] == manifest['input_sha256'] and mirror['weights'] == regen and len(regen) == manifest['nsec']
check('mirror weights: for the n4 input and equal to cluster_gen.mirror_weights', 'ok' if ok else 'bad', 'all', ok)
if not all(c[3] for c in checks):
    report_and_exit(f'{TAG} GATE')
weights = mirror['weights']
expected = [s for s, w in enumerate(weights) if w > 0]
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in dd.items()} for k, dd in resp_raw.items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in base_raw.items()}

# ---------------------------------------------------------------- per-sector f_3_0_1 functional and roundoff bound
from cluster_assemble import laurent_gamma_derivs, pattern_factors
Rf = {src[1]: dd[(1, 0)] for src, dd in resp.items() if src[0] == 1 and (1, 0) in dd}
Lg4 = laurent_gamma_derivs(4, 2, -4, 8)
pfac = pattern_factors(4)
def f_sector(sec, field):
    """R . (Gamma-convolved sector series), with the mirror and pattern weights; field 'S' value, 'B' magnitude"""
    tot = mp.mpf(0)
    for (k, j, ea), v in sec[field].items():
        if k != 1: continue
        for e, r in Rf.items():
            if (e - ea) in Lg4[j]:
                tot += (abs(r * Lg4[j][e - ea]) * v) if field == 'B' else r * Lg4[j][e - ea] * mp.re(v)
    return tot
EPS = {'double': mp.mpf(2) ** -53, 'dd': mp.mpf(2) ** -104}
PAR = ('n', 'mode', 'kmax', 'tau', 'nseg', 'm', 'nplain', 'taurat', 'K', 'Kdd', 'plainR', 'conj', 'radii', 'bound')

# ---------------------------------------------------------------- per level: files, Laurent coefficients
data, builds = {}, {}
for lev, src in levels.items():
    files = sorted(glob.glob(os.path.join(src, '*.out'))) if os.path.isdir(src) else [src]
    try:
        hdr0, secs, hdrs = read_many(files, manifest, expected=expected)
        ok = hdr0['mode'] == 'ser' and int(hdr0['n']) == 4 and int(hdr0['kmax']) >= 1 and hdr0.get('radii') == 'rouche' \
            and hdr0.get('bound') == '1' and all('B' in s for s in secs.values())
        msg = 'ok' if ok else 'wrong mode/n/kmax/radii or no magnitude bounds'
        builds[lev] = sorted({h['fingerprint'].get('build') if h['fingerprint'] else 'legacy' for h in hdrs.values()})
    except (OutputError, OSError, KeyError, ValueError) as e:
        print(f'{lev}: file validation failed:', e); ok = False; msg = 'bad'
    check(f'{lev}: {len(files)} outputs complete, sector set == mirror-reduced manifest ({len(expected)})', msg, 'all', ok)
    if not ok:
        report_and_exit(f'{TAG} GATE')
    try:
        mainb = buildmf.verify(builds[lev][0]) if len(builds[lev]) == 1 else None
    except buildmf.BuildError as e:
        print(e); mainb = None
    check(f'{lev}: main build approved and reproducible (results/builds.json)', mainb['precision'] if mainb else 'bad', 'all', mainb is not None)
    if mainb is None:
        report_and_exit(f'{TAG} GATE')
    prec = {s: mainb['precision'] for s in secs}
    dsecs = dict(secs)                                   # the main-build values, kept for the validation sample
    ddfiles, ddcmp = [], []
    if dd_dirs[lev]:
        ddfiles = sorted(glob.glob(os.path.join(dd_dirs[lev], '*.out')))
        try:
            hdd, sdd, hdrsdd = read_many(ddfiles, None)
            from cluster_assemble import check_against_manifest
            check_against_manifest(sdd, hdrsdd, manifest, expected=set(sdd))
            ok = set(sdd) <= set(expected) and all(hdd.get(k) == hdr0.get(k) for k in PAR) and all('B' in s for s in sdd.values())
            bdd = sorted({h['fingerprint'].get('build') for h in hdrsdd.values()})
            msg = 'ok' if ok else 'not a subset / different run parameters / no bounds'
        except (OutputError, OSError, KeyError, ValueError) as e:
            print(f'{lev}: dd file validation failed:', e); ok = False; msg = 'bad'
        check(f'{lev}: double-double overrides ({len(ddfiles)} files) consistent with the level', msg, 'all', ok)
        if not ok:
            report_and_exit(f'{TAG} GATE')
        try:
            okb = len(bdd) == 1 and buildmf.verify(bdd[0])['precision'] == 'dd'
        except buildmf.BuildError as e:
            print(e); okb = False
        check(f'{lev}: overrides from one approved double-double build (MSC-021)', ', '.join(bdd), 'one dd', okb)
        worst = mp.mpf(0)
        for s, sec in sdd.items():
            fd, fq = f_sector(secs[s], 'S'), f_sector(sec, 'S')
            bd = EPS[prec[s]] * f_sector(secs[s], 'B')
            ratio = abs(fd - fq) / bd if bd > 0 else (mp.mpf(0) if fd == fq else mp.inf)
            worst = max(worst, ratio); ddcmp.append((s, fd - fq, bd))
            secs[s] = sec; prec[s] = 'dd'
        check(f'{lev}: |double - dd| <= double roundoff bound on every overridden sector (max ratio)', worst, mp.mpf(1))
    bsec = {s: EPS[prec[s]] * f_sector(sec, 'B') * weights[s] * pfac[sec['pat']] for s, sec in secs.items()}
    ro = sum(bsec.values())
    print(f'{lev}: first-order magnitude bound of f_3_0_1 roundoff {mp.nstr(ro, 3)} ({sum(1 for p in prec.values() if p == "dd")} dd sectors)')
    J, A, top = assemble_ser(4, secs, 1, elo=-16, ehi=4, weights=weights)
    c = {k: {e: mp.re(v) for e, v in J[k].items()} for k in J}
    # Laurent-level first-order roundoff bound of J4^(k) coefficients: sum_s eps_s wt_s |Gamma^(j) * B_s(k, j)|
    bj = {k: {e: mp.mpf(0) for e in c[k]} for k in c}
    for s, sec in secs.items():
        wt = EPS[prec[s]] * weights[s] * pfac[sec['pat']]
        for (k, j, ea), b in sec['B'].items():
            if k not in bj: continue
            for e in bj[k]:
                if (e - ea) in Lg4[j]: bj[k][e] += abs(Lg4[j][e - ea]) * b * wt
    fin = all(mp.isfinite(v) for k in c for v in c[k].values())
    check(f'{lev}: Laurent coefficients finite', 'ok' if fin else 'bad', 'all', fin)
    data[lev] = dict(files=files + ddfiles, hdr=hdr0, hdrs=dict(hdrs, **({p: h for p, h in hdrsdd.items()} if ddfiles else {})), c=c,
                     cpu=sum(s['time'] for s in secs.values()), roundoff=ro, bj=bj, ndd=sum(1 for p in prec.values() if p == 'dd'),
                     bsec=bsec, prec=prec, dsecs=dsecs, mainprec=mainb['precision'])
    print(f'{lev}: {len(secs)} sectors from {len(files)} files; build {builds[lev]}; ' + ', '.join(f'{k} {hdr0[k]}' for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS', 'radii'))
          + '; resolved exponents: ' + ', '.join(f'd^{k} w^{min(c[k])}..w^{max(c[k])}' for k in c) + f'; engine node-time {data[lev]["cpu"] / 3600:.1f} h')
    check(f'{lev}: one engine build (double outputs)', ', '.join(builds[lev]), 'one', len(builds[lev]) == 1 and builds[lev][0] != 'legacy')
grid = lambda lev: tuple(int(data[lev]['hdr'][k]) for k in ('nseg', 'm', 'nplain'))
check('the two levels use different grids (fine > coarse)', f'{grid("fine")} vs {grid("coarse")}', 'all',
      all(a >= b for a, b in zip(grid('fine'), grid('coarse'))) and grid('fine') != grid('coarse'))
if 'radius' in data:
    tr = lambda lev: data[lev]['hdr']['taurat']
    check('radius run uses a different taurat than the fine and coarse levels', f'{tr("radius")} vs {tr("fine")}', 'all',
          tr('radius') != tr('fine') and tr('radius') != tr('coarse'))

# ---------------------------------------------------------------- MSC-018(b): double-double validation samples (fine grid)
# Amendment B (user decision 2026-10-17, post hoc after a sampled ratio 0.411; rule fixed in fix3b_design.json before
# the new sample was computed): per-stratum factors, stop only on rank9_24 / decile 9 / decile 10.
# MSC-028: the design files must be the pre-data committed versions (git blob hash of the working file == blob at the
# commit that froze it), the strata must partition the non-override nonzero-bound sectors (recomputed from the fine level)
# and the samples must be members of their strata without overlap
DESIGNS = {'fix3_design.json': '6295185', 'fix3b_design.json': 'e49157f'}
design_hash = {}
for fname, commit in DESIGNS.items():
    pth = os.path.join(RES, 'm4_inputs', fname)
    try:
        want = subprocess.run(['git', '-C', ROOT, 'rev-parse', f'{commit}:results/m4_inputs/{fname}'], capture_output=True, text=True, check=True).stdout.strip()
        got = subprocess.run(['git', '-C', ROOT, 'hash-object', pth], capture_output=True, text=True, check=True).stdout.strip()
        ok = want == got
    except (subprocess.CalledProcessError, OSError) as e:
        print(e); ok, want, got = False, '?', '?'
    design_hash[fname] = {'committed_in': commit, 'git_blob': got, 'sha256': pv.sha256_file(pth) if os.path.exists(pth) else None}
    check(f'{fname} identical to its pre-data commit {commit} (git blob)', got[:12] if ok else 'differs', 'same', ok)
design = json.load(open(os.path.join(RES, 'm4_inputs', 'fix3_design.json')))
design_b = json.load(open(os.path.join(RES, 'm4_inputs', 'fix3b_design.json')))
STRAT = {s: name for name, lst in design_b['strata'].items() for s in lst}      # fine-level strata by sector id
def partition_problems():
    fb, fprec = data['fine']['bsec'], data['fine']['prec']
    out = []
    names = list(design_b['strata'])
    if sum(len(v) for v in design_b['strata'].values()) != len(STRAT): out.append('strata overlap')
    nonov = {s for s in fb if fprec[s] != 'dd'}
    if set(STRAT) != {s for s in nonov if fb[s] > 0}: out.append('strata are not exactly the non-override nonzero-bound sectors')
    cand = sorted(nonov, key=lambda s: -fb[s])
    if design_b['strata']['rank9_24'] != cand[:16] or design['dd_sample']['rank9_24'] != cand[:16]: out.append('rank9_24 differs from the fine-level top 16')
    rest = sorted((s for s in cand[16:] if fb[s] > 0), key=lambda s: fb[s]); n = len(rest)
    if any(design_b['strata'][f'decile{i + 1}'] != sorted(rest[i * n // 10:(i + 1) * n // 10]) for i in range(10)): out.append('deciles differ from the fine-level bound order')
    old_dec = design['dd_sample']['decile']; new = design_b['new_sample']
    if any(STRAT.get(s, '').startswith('decile') is False for s in old_dec): out.append('old decile sample outside the deciles')
    if [sum(1 for s in old_dec if STRAT.get(s) == f'decile{i + 1}') for i in range(10)] != [2] * 8 + [4, 4]: out.append('old decile sample counts')
    parts = design_b['new_sample_parts']
    if sorted(parts['decile10_upper'] + parts['decile10_lower'] + parts['decile9']) != sorted(new): out.append('new sample parts')
    if any(STRAT.get(s) != 'decile10' for s in parts['decile10_upper'] + parts['decile10_lower']) or any(STRAT.get(s) != 'decile9' for s in parts['decile9']):
        out.append('new sample outside its strata')
    if set(new) & (set(old_dec) | set(design['dd_sample']['rank9_24'])): out.append('old and new samples overlap')
    if set(new) & {s for s in fb if fprec[s] == 'dd'}: out.append('new sample contains overrides')
    return out
pp = partition_problems()
check('strata partition the non-override nonzero-bound sectors; samples in their strata, disjoint', '; '.join(pp) or 'ok', 'all', not pp)
STOP_STRATA = ('rank9_24', 'decile9', 'decile10')
sample_out, fac = None, {}
if sample_dir:
    want = sorted(set(design['dd_sample']['rank9_24']) | set(design['dd_sample']['decile']))
    want2 = sorted(design_b['new_sample'])
    rows = []
    for tag, sdir, wl in (('old', sample_dir, want), ('new', sample2_dir, want2)):
        if sdir is None:
            check(f'dd validation sample ({tag}) given', 'missing', 'all', False); continue
        sfiles = sorted(glob.glob(os.path.join(sdir, '*.out')))
        try:
            hs, ss, hss = read_many(sfiles, None)
            from cluster_assemble import check_against_manifest
            check_against_manifest(ss, hss, manifest, expected=set(wl))
            bs = sorted({h['fingerprint'].get('build') for h in hss.values()})
            ok = len(bs) == 1 and buildmf.verify(bs[0])['precision'] == 'dd' and all(hs.get(k) == data['fine']['hdr'].get(k) for k in PAR) \
                and not (set(ss) & {s for s, p in data['fine']['prec'].items() if p == 'dd'})
            msg = 'ok' if ok else 'not the design sample / not approved dd / different run parameters'
        except (OutputError, OSError, KeyError, ValueError, buildmf.BuildError) as e:
            print(f'dd sample ({tag}) validation failed:', e); ok = False; msg = 'bad'
        check(f'dd validation sample ({tag}): exactly the {len(wl)} design sectors, approved dd build, fine parameters', msg, 'all', ok)
        if not ok:
            report_and_exit(f'{TAG} GATE')
        for s, sec in sorted(ss.items()):
            dsec = data['fine']['dsecs'][s]
            fd, fq = f_sector(dsec, 'S'), f_sector(sec, 'S')
            bd = EPS['double'] * f_sector(dsec, 'B')
            ratio = abs(fd - fq) / bd if bd > 0 else (mp.mpf(0) if fd == fq else mp.inf)
            rows.append((s, STRAT[s], ratio, abs(fd - fq) * weights[s] * pfac[dsec['pat']], tag))
        sample_out = sample_out or {'files': {}, 'build': bs[0]}
        sample_out['files'].update({rel(p): pv.sha256_file(p) for p in sfiles})
    check('no sector sampled twice', 'ok' if len({r[0] for r in rows}) == len(rows) else 'dup', 'all', len({r[0] for r in rows}) == len(rows))
    print('\ndouble-double validation at the fine grid, per stratum (|double - dd| / (eps B); weighted |double - dd|):')
    sampled = {r[0] for r in rows}
    fb, fprec = data['fine']['bsec'], data['fine']['prec']
    strata_out = {}
    for name in design_b['strata']:
        rs = sorted(r[2] for r in rows if r[1] == name)
        mx = rs[-1] if rs else mp.inf
        fac[name] = max(10 * mx, mp.mpf('0.01'))
        sm = sum(r[3] for r in rows if r[1] == name)
        nb = sum(v for s, v in fb.items() if STRAT.get(s) == name and s not in sampled and fprec[s] != 'dd')
        strata_out[name] = {'n_sampled': len(rs), 'ratio_max': mp.nstr(mx, 3), 'ratio_median': mp.nstr(rs[len(rs) // 2], 3) if rs else None,
                            'factor': mp.nstr(fac[name], 3), 'sum_abs_diff': mp.nstr(sm, 3), 'nonsampled_bound': mp.nstr(nb, 4),
                            'term': mp.nstr(fac[name] * nb, 3), 'n_new': sum(1 for r in rows if r[1] == name and r[4] == 'new')}
        print(f'  {name:9s} n={len(rs):2d} (new {strata_out[name]["n_new"]})  max ratio {mp.nstr(mx, 3):>9}  factor {mp.nstr(fac[name], 3):>7}  '
              f'non-sampled bound {mp.nstr(nb, 4):>9}  term {mp.nstr(fac[name] * nb, 3):>9}  sum |double - dd| {mp.nstr(sm, 3)}')
    for name in STOP_STRATA:
        mx = max((r[2] for r in rows if r[1] == name), default=mp.inf)
        check(f'dd validation: largest ratio in {name} (stop if > 0.1)', mx, tol_ratio)
    dd_bound = sum(v for s, v in fb.items() if fprec[s] == 'dd')
    rest_terms = sum(fac[STRAT[s]] * v for s, v in fb.items() if s not in sampled and fprec[s] != 'dd' and v > 0)
    ro_fine = rest_terms + sum(r[3] for r in rows) + dd_bound
    tot_double = sum(v for s, v in fb.items() if fprec[s] != 'dd')
    ro_factor = ro_fine / tot_double if tot_double > 0 else mp.mpf('0.01')     # effective factor for the Laurent-level checks
    sample_out.update({'rule': 'amendment B (fix3b_design.json)', 'strata': strata_out, 'sampled_sum_abs_diff': mp.nstr(sum(r[3] for r in rows), 3),
                       'dd_override_bound': mp.nstr(dd_bound, 3), 'effective_factor': mp.nstr(ro_factor, 3),
                       'rows': [[r[0], r[1], mp.nstr(r[2], 3), mp.nstr(r[3], 3), r[4]] for r in rows]})
    print(f'  fine roundoff estimate = {mp.nstr(rest_terms, 3)} (strata terms) + {mp.nstr(sum(r[3] for r in rows), 3)} (sampled) '
          f'+ {mp.nstr(dd_bound, 2)} (dd) = {mp.nstr(ro_fine, 3)}; effective factor {mp.nstr(ro_factor, 3)}')
else:
    ro_fine = ro_factor * data['fine']['roundoff']
def level_roundoff(lev):
    """coarse/radius (and fine as a cross-check): fine-level stratum factor x that level's double bound + its dd bound"""
    if not fac:
        return ro_factor * data[lev]['roundoff']
    tot = mp.mpf(0)
    for s, v in data[lev]['bsec'].items():
        if data[lev]['prec'][s] == 'dd' or v == 0:
            tot += v
        elif s in STRAT:
            tot += fac[STRAT[s]] * v
        else:
            raise SystemExit(f'{lev}: double sector {s} with nonzero bound outside the fine-level strata')
    return tot
lro = {}
for lev in data:
    lro[lev] = ro_fine if (lev == 'fine') else level_roundoff(lev)
    check(f'{lev}: roundoff estimate of f_3_0_1 (per-stratum rule)', lro[lev], tol_ro)

# ---------------------------------------------------------------- (1) delta^0 vs the Bethe ansatz
def laurent_exact(fun, lo, hi, rad=mp.mpf('0.04'), npts=400):     # J4_BA has a pole at w = 1/8: rad 0.04 < 0.125
    with mp.workdps(60):
        pts = [rad * mp.expjpi(2 * mp.mpf(m) / npts) for m in range(npts)]
        vals = [fun(1 - p) for p in pts]
        return {j: mp.re(sum(v * p ** (-j) for v, p in zip(vals, pts)) / npts) for j in range(lo, hi + 1)}
ba = laurent_exact(J4_BA, -16, 4)
dev0 = {}
for lev in data:
    c0 = data[lev]['c'][0]
    dev0[lev] = max(abs(c0[e] - ba[e]) / max(abs(ba[e]), 1) for e in c0 if e <= 0)
    print(f'\n{lev}: delta^0 Laurent coefficients of J4 vs the exact Bethe ansatz (max |diff|/max(|exact|,1) = {mp.nstr(dev0[lev], 3)}):')
    for e in sorted(c0):
        if abs(ba[e]) > 1e-20 or abs(c0[e]) > 1e-12:
            print(f'  w^{e:3d}: engine {mp.nstr(c0[e], 20):>28}  exact {mp.nstr(ba[e], 20):>28}  rel {mp.nstr(abs(c0[e] - ba[e]) / max(abs(ba[e]), 1), 3)}')
check('fine: delta^0 Laurent vs Bethe ansatz, w^-16..w^0 (max |diff|/max(|BA|,1))', dev0['fine'], tol_ba)
# consistency: every resolved delta^0 coefficient agrees with the Bethe ansatz within 3x its own error estimate
# (|fine - coarse| + RO_FACTOR x Laurent-level roundoff bound) + 1e-12 relative
cf0, cc0, bj0 = data['fine']['c'][0], data['coarse']['c'][0], data['fine']['bj'][0]
cons0 = max(abs(cf0[e] - ba[e]) / (3 * (abs(cf0[e] - cc0.get(e, cf0[e])) + ro_factor * bj0[e]) + mp.mpf('1e-12') * max(abs(ba[e]), 1))
            for e in cf0)
check('fine: delta^0 Laurent vs Bethe ansatz within 3x the error estimate (max ratio)', cons0, mp.mpf(1))
cxres = []
for d in cxdirs:
    files = sorted(glob.glob(os.path.join(d, '*.out')))
    try:
        h, secs, hd = read_many(files, manifest, expected=expected)
        K = mp.mpc(mp.mpf(float.fromhex(h['Kdd'][0])) + mp.mpf(float.fromhex(h['Kdd'][1])),
                   mp.mpf(float.fromhex(h['Kdd'][2])) + mp.mpf(float.fromhex(h['Kdd'][3])))
        ok = h['mode'] == 'cx' and h.get('radii') == 'rouche'
        J, _ = assemble_cx(4, secs, K, 0, weights=weights)
        ex = J4_BA(K); r = abs(J[0] / ex - 1)
        cxres.append(dict(dir=rel(d), K=[mp.nstr(K.real, 17), mp.nstr(K.imag, 17)], J=[mp.nstr(J[0].real, 20), mp.nstr(J[0].imag, 20)],
                          exact=[mp.nstr(ex.real, 20), mp.nstr(ex.imag, 20)], rel=mp.nstr(r, 3), grid=[h['nseg'], h['m'], h['nplain']],
                          files={rel(p): pv.sha256_file(p) for p in files}))
        print(f'cx delta^0 at K = {mp.nstr(K, 8)}: engine {mp.nstr(J[0], 18)}  exact {mp.nstr(ex, 18)}  rel {mp.nstr(r, 3)}')
    except (OutputError, OSError, KeyError, ValueError) as e:
        print(f'{d}: cx validation failed:', e); ok = False; r = mp.inf
    check(f'cx delta^0 vs Bethe ansatz ({os.path.basename(d.rstrip("/"))})', r if ok else mp.inf, tol_cx)

# ---------------------------------------------------------------- (2) delta^1 relations and f_3_0_1
def F3_level(c):
    unresolved = []
    def c4(k, j):
        if j < min(c[k]): return mp.mpf(0)      # below the assembled window (w^-16)
        if j > max(c[k]):
            unresolved.append((k, j)); return mp.nan
        return c[k][j]
    def F3(target):
        tot = base.get(target, mp.mpf(0)); terms = [abs(tot)]
        for src, dd in resp.items():
            if target in dd and src[0] == 1:
                t = dd[target] * c4(*src); tot += t; terms.append(abs(t))
        return tot, max(terms + [mp.mpf(1)])
    return F3, unresolved
res = {}
for lev in [l for l in ('fine', 'coarse', 'radius') if l in data]:
    F3, unres = F3_level(data[lev]['c'])
    rel_max, rows = mp.mpf(0), []
    for j in range(-12, 0):
        v, sc = F3((1, j)); r = abs(v) / sc
        rel_max = max(rel_max, r) if mp.isfinite(r) else mp.inf
        rows.append((j, v, sc, r))
    f301, _ = F3((1, 0))
    res[lev] = dict(rows=rows, rel_max=rel_max, f=f301, unresolved=list(unres))
    print(f'\n{lev}: F-analyticity relations at delta^1 (must vanish):')
    for j, v, sc, r in rows:
        print(f'  [d^1 w^{j:3d}] = {mp.nstr(v, 5):>12}   (scale {mp.nstr(sc, 3)}, relative {mp.nstr(r, 3)})')
    print(f'  max relative {mp.nstr(rel_max, 3)};  f_3_0_1 = {mp.nstr(f301, 20)}')
# relation error estimate: |fine - coarse| + RO_FACTOR x sum_src |response| x Laurent-level roundoff bound (fine)
bj1 = data['fine']['bj'][1]
for (j, v, sc, r), (_, vc, _, _) in zip(res['fine']['rows'], res['coarse']['rows']):
    rb = sum(abs(dd[(1, j)]) * bj1.get(src[1], mp.mpf(0)) for src, dd in resp.items() if src[0] == 1 and (1, j) in dd)
    est = abs(v - vc) + ro_factor * rb
    check(f'fine: relation [d^1 w^{j}] (relative)', r, tol_rel)
    check(f'fine: relation [d^1 w^{j}] within 3x its error estimate (ratio)', abs(v) / (3 * est + mp.mpf('1e-12') * sc), mp.mpf(1))
check('coarse: all delta^1 relations (max relative)', res['coarse']['rel_max'], tol_relc)
if 'radius' in res:
    check('radius: all delta^1 relations (max relative)', res['radius']['rel_max'], tol_relc)
    check('radius: delta^0 Laurent vs Bethe ansatz, w^-16..w^0', dev0['radius'], tol_ba)
ok = all(not res[l]['unresolved'] and mp.isfinite(res[l]['f']) for l in res)
check('f_3_0_1 resolved and finite at both levels', 'ok' if ok else f'unresolved {res["fine"]["unresolved"][:3]}', 'all', ok)
err2 = abs(res['fine']['f'] - res['coarse']['f'])
errR = abs(res['fine']['f'] - res['radius']['f']) if 'radius' in res else mp.mpf(0)
errtot = err2 + errR + ro_fine
check('f_3_0_1 error |fine - coarse| + |fine - radius| + validated roundoff (absolute)', errtot, tol_f)
if 'radius' in res:
    print(f'f_3_0_1 radius run (taurat {data["radius"]["hdr"]["taurat"]}): {mp.nstr(res["radius"]["f"], 20)}  |fine - radius| {mp.nstr(errR, 3)}')
print(f'\nf_3_0_1 fine {mp.nstr(res["fine"]["f"], 20)}  coarse {mp.nstr(res["coarse"]["f"], 20)}  two-grid error {mp.nstr(err2, 3)}')

# ---------------------------------------------------------------- record
out = {'flow_coefficients': {'f_3_0_1': mp.nstr(res['fine']['f'], 25)},
       'errors': {'f_3_0_1_total': mp.nstr(errtot, 3), 'f_3_0_1_two_grid': mp.nstr(err2, 3), 'f_3_0_1_coarse': mp.nstr(res['coarse']['f'], 25),
                  'f_3_0_1_radius_diff': mp.nstr(errR, 3), 'f_3_0_1_radius': mp.nstr(res['radius']['f'], 25) if 'radius' in res else None,
                  'roundoff_estimate_fine': mp.nstr(ro_fine, 3), 'roundoff_factor': mp.nstr(max(ro_factor, mp.mpf('0.01')), 3),
                  'roundoff_estimate_levels': {l: mp.nstr(v, 3) for l, v in lro.items()},
                  'roundoff_rule': 'per-stratum (amendment B, user decision 2026-10-17, post hoc; fix3b_design.json)',
                  'f_3_0_1_roundoff_bound_fine': mp.nstr(data['fine']['roundoff'], 3),
                  'f_3_0_1_roundoff_bound_coarse': mp.nstr(data['coarse']['roundoff'], 3)},
       'dd_sectors': {lev: data[lev]['ndd'] for lev in data},
       'dd_validation_sample': sample_out, 'supersedes': V1,
       'amendment': ('post hoc amendment B by user decision (2026-10-17) after the pre-set MSC-018 rule stopped on a sampled '
                     'ratio 0.411 (sector 2890, low-bound decile): per-decile factors max(10 x max ratio, 0.01), stop only on '
                     'rank9_24/decile 9/decile 10, fresh held-out sample of 16 sectors (random.Random(20261017)); rule and '
                     'sample committed in e49157f before the new data'),
       'raw_laurent': {str(k): {str(e): mp.nstr(v, 25) for e, v in data['fine']['c'][k].items()} for k in data['fine']['c']},
       'raw_laurent_coarse': {str(k): {str(e): mp.nstr(v, 25) for e, v in data['coarse']['c'][k].items()} for k in data['coarse']['c']},
       'checks': {'delta0_vs_BA_max_rel': {l: mp.nstr(dev0[l], 3) for l in dev0},
                  'delta1_relations_max_rel': {l: mp.nstr(res[l]['rel_max'], 3) for l in res}, 'cx_delta0': cxres},
       'run': {lev: {k: data[lev]['hdr'][k] for k in ('kmax', 'tau', 'taurat', 'nseg', 'm', 'nplain', 'LS', 'radii')} for lev in data},
       'sources': {lev: [rel(x) for x in data[lev]['files']] for lev in data},
       'engine_node_seconds': {lev: round(data[lev]['cpu'], 1) for lev in data}}
blob = json.dumps(out, indent=1, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()
recname = RECNAME
recp = os.path.join(RES, recname)
side = os.path.join(RES, recname.replace('.json', '.provenance.json'))
sidecar = json.dumps({'record': recname, 'record_sha256': sha,
                      'sources': {rel(x): pv.sha256_file(x) for lev in data for x in data[lev]['files']},
                      'engine_input': {'manifest': rel(manifest_path), 'input_sha256': manifest['input_sha256'], 'nsec': manifest['nsec'],
                                       'mirror_weights': {rel(mirror_path): pv.sha256_file(mirror_path)}},
                      'output_fingerprints': {rel(p): h['fingerprint'] for lev in data for p, h in data[lev]['hdrs'].items()},
                      'step0_maps': {n: pv.sha256_file(os.path.join(RES, n)) for n in ('m4_step0_response.json', 'm4_step0_F3base.json')},
                      'step0_generator': {pv_resp['generator']: pv_resp['generator_sha256']},
                      'gate': {rel(__file__): pv.sha256_file(__file__)},
                      'design': {rel(os.path.join(RES, 'm4_inputs', 'fix3_design.json')): pv.sha256_file(os.path.join(RES, 'm4_inputs', 'fix3_design.json'))},
                      'designs_verified': design_hash,
                      'builds_manifest': {rel(buildmf.MANIFEST): pv.sha256_file(buildmf.MANIFEST)},
                      'upstream_records': {'M2_flow_coefficients.json': m2sha, 'M3_flow_coefficients.json': m3sha}},
                     indent=1, sort_keys=True) + '\n'
if verify:
    want = pv.registry().get(RECNAME, {}).get('sha256')
    same = os.path.exists(recp) and open(recp).read() == blob and sha == want
    check(f'rebuilt record byte-identical to the frozen {RECNAME}', 'identical' if same else f'differs ({sha[:12]} vs {str(want)[:12]})', 'identical', same)
    fz = json.load(open(side))
    nw = json.loads(sidecar)
    keys_ok = set(nw) == set(fz) | set(SIDECAR_ALLOWED_EXTRA)
    diffk = sorted(k for k in set(fz) | set(nw) if k not in SIDECAR_ALLOWED_DIFF + SIDECAR_ALLOWED_EXTRA and fz.get(k) != nw.get(k))
    check('provenance sidecar: key set = frozen + designs_verified; all values except the gate hash reproduced',
          ', '.join(diffk) or ('ok' if keys_ok else 'key set differs'), 'all', keys_ok and not diffk)
    print('\n(verify mode: nothing written)  rebuilt record sha256', sha)
    verify_out = {'record': RECNAME, 'rebuilt_sha256': sha, 'identical': same, 'sidecar_fields_differing': diffk, 'sidecar_keys_ok': keys_ok,
                  'sidecar_allowed_differences': list(SIDECAR_ALLOWED_DIFF), 'sidecar_allowed_extra': list(SIDECAR_ALLOWED_EXTRA),
                  'designs_verified': design_hash,
                  'checks': [[n, v if isinstance(v, str) else mp.nstr(v, 6), t if isinstance(t, str) else mp.nstr(t, 3), ok] for n, v, t, ok in checks]}
    rep_txt = json.dumps(verify_out, sort_keys=True)
    if REPORT is not None:
        REPORT.write(rep_txt + '\n'); REPORT.close()
    print('VERIFY_REPORT_JSON ' + rep_txt)
    report_and_exit(f'{TAG} GATE (verify)')
if dry:
    print('\n(dry run: nothing written)  sha256 of the would-be record', sha)
    report_and_exit(f'{TAG} GATE (dry)')
if not all(ch[3] for ch in checks):
    print('\nchecks failed: nothing published')
    report_and_exit(f'{TAG} GATE')
commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or 'unknown'
created = pv.publish_unit([(recp, blob), (side, sidecar)],
                          register=(recname, commit, 'M4 part B record v2 (four-bubble f_3_0_1, fix round 3 error budget), hashed before C8 v2'))[0]
print(f'\nrecord {"written" if created else "identical to the existing record"}: {rel(recp)} sha256 {sha}')
if V1 in pv.registry():
    pv.mark_superseded(V1, recname, 'fix round 3 (MSC-018): error estimate not validated; v2 adds an independent radius run '
                       '(|fine - radius|) and a double-double validation of the roundoff factor at the fine grid')
    print(f'{V1} marked superseded by {recname}')
report_and_exit(f'{TAG} GATE')
