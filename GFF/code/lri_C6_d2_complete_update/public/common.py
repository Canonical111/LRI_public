"""Shared helpers of public/replay.py and public/regen.py (added for the public release; not part of the delivered package).

The delivered scripts in reproduction/ write their outputs next to themselves and some overwrite their own inputs, so they
are always run in a writable copy under public/out/, never in the shipped tree.
"""
import hashlib, json, os, shutil, stat, subprocess, sys, time
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]          # GFF/code/lri_C6_d2_complete_update
ROWS = []


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())


def row(name, got, want, ok, note='', status=None):
    ROWS.append(dict(check=name, got=got, expected=want, status=status or ('PASS' if ok else 'FAIL'), note=note))


def skip(name, why):
    ROWS.append(dict(check=name, got='-', expected='-', status='SKIP', note=why))


def dec(x):
    """Decimal of a record string ('1.23e-4', '(1.2 + 0.0j)' takes the real part)."""
    s = str(x).strip()
    if s.startswith('('): s = s[1:].split('+')[0].split(' -')[0].strip() if 'j' in s else s.strip('()')
    return Decimal(s)


def quoted(name, value, text, note=''):
    """PASS when the record value, rounded half-even to the decimals (or, for 'e' notation, the significant digits) the
    note prints, equals the printed text. The note rounds (e.g. Xi_Gamma ...347130 from ...3471298959)."""
    v = dec(value); t = text.replace('\\ldots', '').replace(',', '').strip()
    with localcontext() as c:
        c.prec = 200
        if 'e' in t:
            m, e = t.split('e'); nd = len(m.split('.')[1]) if '.' in m else 0
            got = f'{v:.{nd}e}'.replace('e-0', 'e-').replace('e+0', 'e+')
            ok = Decimal(got) == Decimal(t)
        else:
            nd = len(t.split('.')[1]) if '.' in t else 0
            got = str(v.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_EVEN))
            ok = Decimal(got) == Decimal(t)
    row(name, got, text, ok, note)


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f'{p}[{i}]')
    else: yield p, x


# Comparison policy of regenerated records (second cluster run: the pure-Python mpmath backend, without gmpy2, moved a
# near-zero counterterm combination, loops[4].solved[102].b ~ 3e-41, by 6.7e-58 at 60 working digits; first cluster run,
# regen-cold with gmpy2: three diagnostic fields moved at rounding level). String identity is always the first test.
#
# Value fields (counterterms, Laurent coefficients, sums, jets, totals): a numeric string that differs passes when
#   |new - recorded| <= 10^-(dps - DIGIT_MARGIN) * scale,
# with dps the record's working precision (its 'dps' field, else the script's mp.dps passed by the caller) and scale the
# magnitude of the record entry the field belongs to: the largest |value| among the numeric strings of the nearest enclosing
# list element (one graph's counterterm vector with its b and c, one loop's totals, one contour's jet vector, one KLT case),
# or of the whole record for top-level fields, and at least |recorded|. A field that is itself nearly zero is therefore
# compared at the precision of its entry, not relative to its own size.
#
# Diagnostic fields measure the disagreement of two routes (two Cauchy settings, two admissible roots, symbolic vs
# 90-digit, Gamma-only vs coordinate counterterms, fresh vs saved two-loop jets, KLT formula vs Selberg/completion values)
# or are rounding residuals (Delta_p). They pass when |new| <= max(DIAG_FACTOR x |recorded|, DIAG_FLOOR, the note's bound)
# and the row reports the value. They do not enter the scale of their entry. Leaf names, checked against every field of
# the records that test/replay/regen compare (2026-10-13):
DIAG = {
    'max_routing_error', 'maximum_locality_error',                                    # sp_ms_90.json, per graph
    'maximum_absolute_symbolic_vs_90dps_error', 'maximum_routing_error_90dps',
    'maximum_scale_locality_error_90dps',                                             # gamma_and_coverage_checks.json
    'max_momentum_discrepancy', 'old_momentum_comparison', 'root_error',              # position_ms_results.json (root_error also kite)
    'max_Gamma_discrepancy', 'gamma_selberg_comparison',                              # position_kite_leaf_ms_*.json
    'power_contribution_C6',                                                          # power_cancellation*.json (Delta_p)
    'max_absolute_comparison', 'max_root_discrepancy',                                # analytic_extension_audit.json
    'error', 'difference',                                                            # klt_checks.json
    'largest_difference_vs_saved_input', 'largest_changed_Cauchy_contour_difference', # fresh_two_loop_mom.json
}
DIAG_FACTOR, DIAG_FLOOR = Decimal(100), Decimal('1e-40')
DIAG_BOUND = {'power_contribution_C6': Decimal('1e-30')}        # note Sec 24.3: Delta_p negligible for C6(2)
NOTE_PRINTED = {'max_absolute_comparison': ('7.38e-30', 'Sec 24.2'), 'max_root_discrepancy': ('7.97e-45', 'Sec 24.2'),
                'largest_difference_vs_saved_input': ('< 6.8e-61', 'Sec 25.3')}
DIGIT_MARGIN = 10
# Working precision of the records without a 'dps' field (the scripts' mp.dps, limited by their inputs):
DPS = {'power_cancellation.json': 50, 'power_cancellation_high.json': 50,   # power_cancellation.py: mp.dps = 50
       'analytic_extension_audit.json': 60,                                 # mp.dps = 65, inputs at 60 and 65 digits
       'gamma_and_coverage_checks.json': 80,                                # check_gamma_coverage.py: mp.dps = 80
       'mom_lagrange_checks.json': 50}                                      # exact rational; no numeric strings differ


def leaf(k):
    import re
    return re.sub(r'\[\d+\]', '', k).split('.')[-1]


def flatb(x, p='', blk=''):
    """Like flat(), but also yields the record entry (block) of each leaf: the nearest enclosing list element that is a
    dict or a list, or '' (the whole record)."""
    if isinstance(x, dict):
        for k, v in x.items(): yield from flatb(v, f'{p}.{k}' if p else k, blk)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            q = f'{p}[{i}]'; yield from flatb(v, q, q if isinstance(v, (dict, list)) else blk)
    else: yield p, x, blk


def block_scales(rec):
    """Largest |value| among the numeric strings (mpmath/sympy outputs) of each block, diagnostic fields excluded."""
    sc = {}
    for k, v, blk in flatb(rec):
        if not isinstance(v, str) or leaf(k) in DIAG: continue
        try: a = abs(dec(v))
        except Exception: continue
        if a > sc.get(blk, Decimal(0)): sc[blk] = a
    return sc


def compare_json(name, got, ref, ignore=('seconds',), dps=None):
    """Field-by-field comparison of a regenerated record with the shipped one under the policy above. `dps` overrides the
    working precision (default: the record's 'dps' field, else DPS[file name, the part of `name` before ':'], else 50). Keys in `ignore` (wall-clock seconds, a prose 'scope'
    edited after a record was written) are skipped."""
    G = dict(flat(got)); FB = {k: (v, blk) for k, v, blk in flatb(ref)}; sc = block_scales(ref)
    fname = name.split(':')[0].strip()
    wdps = int(dps if dps is not None else ref.get('dps') or DPS.get(fname, 50))
    eps = Decimal(10) ** -(wdps - DIGIT_MARGIN)
    bad = []; vals = []; diag = []
    for k in sorted(set(G) | set(FB)):
        if k.split('.')[-1].split('[')[0] in ignore or k.split('.')[0].split('[')[0] in ignore: continue
        if k not in G or k not in FB: bad.append(f'{k}: only in {"shipped" if k in FB else "regenerated"}'); continue
        a, (b, blk) = G[k], FB[k]
        if a == b: continue
        try: da, db = dec(a), dec(b)
        except Exception: bad.append(f'{k}: {str(a)[:40]!r} != {str(b)[:40]!r}'); continue
        if leaf(k) in DIAG:
            bound = max(DIAG_FACTOR * abs(db), DIAG_FLOOR, DIAG_BOUND.get(leaf(k), Decimal(0)))
            diag.append((abs(da) / bound, k, da, db, bound))
            if abs(da) > bound: bad.append(f'{k} (diagnostic): {da:.3e} > bound {bound:.1e} (recorded {db:.3e})')
            continue
        scale = max(sc.get(blk, Decimal(0)), abs(db)); d = abs(da - db)
        r = d / scale if scale else (Decimal(0) if not d else Decimal('Infinity'))
        vals.append((r, k, d, scale))
        if r > eps: bad.append(f'{k}: |diff| {d:.2e} > 1e-{wdps - DIGIT_MARGIN} x entry scale {scale:.2e}')
    notes = []
    if not vals and not diag: notes.append('all fields string-identical')
    if vals:
        r, k, d, scale = max(vals, key=lambda t: t[0])
        notes.append(f'{len(vals)} value fields within 1e-{wdps - DIGIT_MARGIN} x entry scale; largest scaled difference '
                     f'{r:.2e} ({k}: |diff| {d:.2e}, scale {scale:.2e})')
    if diag:
        r, k, da, db, bd = max(diag, key=lambda t: t[0])
        notes.append(f'{len(diag)} diagnostic fields changed, all within max(100 x recorded, 1e-40, note); closest to its '
                     f'bound: {k} = {da:.3e} (recorded {db:.3e}, bound {bd:.1e})')
    for k, v in G.items():
        if leaf(k) in NOTE_PRINTED and k in FB and v != FB[k][0]:
            txt, sec = NOTE_PRINTED[leaf(k)]
            notes.append(f'{k} = {dec(v):.3e} (note {sec} prints {txt})')
    msg = (f'{len(bad)} fields out of tolerance; first: {bad[0]}' if bad else '; '.join(notes))
    row(name, f'{len(FB)} fields', 'identical / within tolerance', not bad, msg)
    return not bad


def workcopy(dest):
    """Writable copy of reproduction/ (and nothing else) under dest; dest is wiped first."""
    dest = Path(dest)
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(PKG / 'reproduction', dest / 'reproduction')
    for r, ds, fs in os.walk(dest):
        for x in ds + fs:
            p = os.path.join(r, x); os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
    return dest / 'reproduction'


def run(script, cwd, args=(), env=None, log=None):
    """Run a delivered script with this Python in cwd; returns (returncode, seconds)."""
    t = time.time(); e = dict(os.environ, **(env or {}))
    with open(log or os.devnull, 'w') as f:
        rc = subprocess.run([sys.executable, '-B', script, *args], cwd=cwd, env=e, stdout=f, stderr=subprocess.STDOUT).returncode
    return rc, time.time() - t


def sums_check(results=None):
    """Bind the shipped files to the package's own SHA256SUMS.json (487 entries; files not shipped are ignored) and, when
    given, the expected-value records under GFF/results/C6_2/power_compensation (same relative paths)."""
    S = load(PKG / 'SHA256SUMS.json'); ok = 0; bad = []; unlisted = []
    for p in sorted(PKG.rglob('*')):
        if not p.is_file(): continue
        rel = p.relative_to(PKG).as_posix()
        if rel.startswith(('public/', 'public.mk', 'REVIEWS.md')) or rel == 'SHA256SUMS.json': continue
        if any(c.startswith('.') or c == '__pycache__' for c in p.relative_to(PKG).parts): continue  # .venv, .git, caches
        if rel not in S: unlisted.append(rel); continue
        if sha(p) == S[rel]: ok += 1
        else: bad.append(rel)
    row('code files bound by SHA256SUMS.json', ok, f'{ok} match', not bad and not unlisted,
        (f'mismatch: {bad[:3]}' if bad else f'unlisted: {unlisted[:3]}' if unlisted else f'{len(S) - ok} listed files not shipped (ignored)'))
    if results is not None:
        rok = 0; rbad = []; n = 0
        for p in sorted(Path(results).rglob('*.json')):
            n += 1; rel = p.relative_to(results).as_posix()
            if S.get(rel) == sha(p): rok += 1
            else: rbad.append(rel)
        row('result records bound by SHA256SUMS.json', rok, f'{n} of {n}', n > 0 and not rbad, f'not bound: {rbad[:3]}' if rbad else '')


def report(out, name, extra=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    import mpmath, sympy, networkx
    vers = dict(python=sys.version.split()[0], mpmath=mpmath.__version__, sympy=sympy.__version__, networkx=networkx.__version__)
    (out / f'{name}.json').write_text(json.dumps(dict(versions=vers, rows=ROWS, **(extra or {})), indent=1) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS:
        print(f"{x['status']}  {x['check']:<{w}}  {str(x['got']):>26}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS); skips = sum(x['status'] == 'SKIP' for x in ROWS)
    print(f"\n{len(ROWS) - fails - skips} PASS, {fails} FAIL, {skips} SKIP  (python {vers['python']}, mpmath {vers['mpmath']}, "
          f"sympy {vers['sympy']}, networkx {vers['networkx']})")
    return 1 if fails else 0
