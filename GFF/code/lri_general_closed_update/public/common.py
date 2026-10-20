"""Shared helpers of the public replay of the three general-d packages (C0..C5 at general dimension).

The same file ships in lri_general_special_functions_update, lri_general_closed_update and
lri_general_periodization_update (public/common.py, byte-identical). It never modifies a shipped file: every delivered
script that is rerun writes its record in place, so it runs in a fresh copy of the package under public/out/work/.

Comparison tiers (reasons in the header of each package's public/replay.py):
  exact  JSON equal after dropping timing keys (seconds, sec, elapsed...); text files byte-equal. If a leaf differs,
         numeric strings with >= 30 significant digits may differ by 1e-45 relative and SymPy expression strings must be
         SymPy-equal (both reported as PASS with a note). These records come from SymPy or mpmath and are deterministic.
  float  numpy/scipy records: values relative 1e-8 (absolute 1e-12 where |ref| <= 1e-9); difference-type fields
         (keys containing difference, residual, error, minus, imag, off_grid, tail) absolute 1e-6, because they are
         differences of nearly equal quadrature results or least-squares tail extrapolations (the angular-tail fit of
         spectral_evaluate.py moves by 5.5e-9 relative between BLAS builds while the masters move by 5e-11); strings,
         booleans and integers equal.
  gz     gzip files compared on their decompressed bytes (the gzip header stores a write time).
"""
import gzip, hashlib, json, os, re, shutil, subprocess, sys, time
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, InvalidOperation
from pathlib import Path

getcontext().prec = 120
PKG = Path(__file__).resolve().parents[1]
ROWS = []
TIMING = re.compile(r'^(seconds|sec|elapsed_seconds|elapsed|time|runtime)$')
DIFFKEY = re.compile(r'(difference|residual|error|minus|resid|imag|off_grid|tail)', re.I)


def row(check, got, expected, ok, note=''):
    ROWS.append(dict(check=check, got=got, expected=expected, status='PASS' if ok else 'FAIL', note=note))
    return ok


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def load(p): return json.loads(Path(p).read_text())


# ---------------------------------------------------------------- integrity
def verify_sums(listfile, root=PKG):
    """public/SOURCE_SHA256SUMS: every shipped source file, hashes from the bundle MANIFEST.json. Complete list."""
    bad, n = [], 0
    for line in Path(listfile).read_text().splitlines():
        h, rel = line.split('  ', 1); n += 1
        p = root / rel
        if not p.is_file(): bad.append(f'missing {rel}')
        elif sha(p) != h: bad.append(f'changed {rel}')
    return row(f'integrity: {Path(listfile).name} (complete list)', f'{n - len(bad)}/{n} match', f'{n}/{n}', not bad,
               '; '.join(bad[:5]))


def verify_hashes(label, mapping, root, ignore_missing):
    """mapping: relative path -> sha256. With ignore_missing, absent files are counted, not failed."""
    ok = miss = 0; bad = []
    for rel, h in mapping.items():
        p = root / rel
        if not p.is_file(): miss += 1; continue
        if sha(p) == h: ok += 1
        else: bad.append(rel)
    pres = len(mapping) - miss
    good = not bad and (ignore_missing or miss == 0)
    mode = 'ignore-missing' if ignore_missing else 'complete'
    return row(f'integrity: {label} ({mode})', f'{ok}/{pres} present match, {miss} not shipped',
               f'all present match' + ('' if ignore_missing else ', none missing'), good, '; '.join(bad[:5]))


# ---------------------------------------------------------------- running delivered scripts in a copy
def work_copy(dest):
    """Fresh copy of the shipped package (without public/, the release overlay, and without the output folder)."""
    dest = Path(dest).resolve()
    if dest.exists(): shutil.rmtree(dest)
    root = PKG.resolve()

    def ignore(d, names):
        if Path(d).resolve() != root: return [n for n in names if n == '__pycache__']
        return [n for n in names if n in ('public', '__pycache__') or (root / n) in dest.parents]
    shutil.copytree(root, dest, ignore=ignore)
    return dest


def remove(work, *rels):
    """Delete outputs in the work copy before a script regenerates them, so that a script that fails or writes nothing
    cannot pass the comparison with the shipped copy."""
    for r in rels:
        p = Path(work) / r
        if p.is_file(): p.unlink()


_RUNS = [0]


def run(work, script, *args, show=None, outputs=(), timeout=3600):
    """Run a delivered script of the work copy with the current interpreter (cwd = the script's folder).
    One row (exit status, seconds). stdout goes to <work>/../logs/NN_<script>.log, stderr to NN_<script>.err.
    outputs: files (relative to work) that the script writes; they are deleted first (see remove).
    Returns the stdout log path, or None if the script failed."""
    remove(work, *outputs)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    work = Path(work).resolve(); sp = work / script
    logdir = work.parent / 'logs'; logdir.mkdir(parents=True, exist_ok=True)
    _RUNS[0] += 1
    stem = f'{_RUNS[0]:02d}_{Path(script).stem}'
    log, err = logdir / f'{stem}.log', logdir / f'{stem}.err'
    t = time.time()
    with open(log, 'w') as f, open(err, 'w') as e:
        p = subprocess.run([sys.executable, '-B', str(sp), *map(str, args)], cwd=sp.parent, env=env, stdout=f,
                           stderr=e, timeout=timeout)
    dt = time.time() - t
    shown = show if show is not None else ' '.join(str(a) for a in args)
    row(f'run {script} {shown}'.strip(), f'exit {p.returncode}, {dt:.1f} s', 'exit 0', p.returncode == 0,
        f'log logs/{log.name}')
    return log if p.returncode == 0 else None


# ---------------------------------------------------------------- comparisons
def strip(x):
    if isinstance(x, dict): return {k: strip(v) for k, v in x.items() if not TIMING.match(k)}
    if isinstance(x, list): return [strip(v) for v in x]
    return x


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f'{p}[{i}]')
    else: yield p, x


def as_complex(v):
    if isinstance(v, bool) or v is None: return None
    if isinstance(v, (int, float)): return complex(v)
    s = str(v).strip().strip('()').replace(' ', '')
    try: return complex(s)
    except ValueError:
        try: return complex(float(Decimal(s)))
        except (InvalidOperation, ValueError): return None


def as_decimal(v):
    try: return Decimal(str(v).strip())
    except InvalidOperation: return None


def sympy_equal(a, b):
    try:
        import sympy
        return sympy.expand(sympy.sympify(a) - sympy.sympify(b)) == 0
    except Exception:
        return False


def cmp_exact(label, new, ref):
    new, ref = Path(new), Path(ref)
    if not new.is_file(): return row(f'{label}', 'missing', 'regenerated file', False, str(new))
    if ref.suffix not in ('.json',):
        same = new.read_bytes() == ref.read_bytes()
        return row(label, 'byte-identical' if same else 'differs', 'byte-identical', same)
    a, b = strip(load(new)), strip(load(ref))
    if a == b: return row(label, 'identical (timing keys dropped)', 'identical', True)
    A, Bf = dict(flat(a)), dict(flat(b))
    if set(A) != set(Bf):
        return row(label, 'different keys', 'identical', False, f'{sorted(set(A) ^ set(Bf))[:3]}')
    notes, bad = [], []
    for k, w in Bf.items():
        g = A[k]
        if g == w: continue
        dg, dw = as_decimal(g), as_decimal(w)
        if dg is not None and dw is not None and len(str(w).lstrip('-').replace('.', '').lstrip('0')) >= 30:
            if abs(dg - dw) <= Decimal('1e-45') * max(Decimal(1), abs(dw)): notes.append(k); continue
        if isinstance(g, str) and isinstance(w, str) and sympy_equal(g, w): notes.append(k); continue
        bad.append(k)
    return row(label, 'identical up to printing' if not bad else f'{len(bad)} leaves differ', 'identical', not bad,
               (f'printing differences at {notes[:3]}' if notes else '') + (f' differing: {bad[:3]}' if bad else ''))


def cmp_float(label, new, ref, rtol=1e-8, atol=1e-12, datol=1e-6):
    new = Path(new)
    if not new.is_file(): return row(label, 'missing', 'regenerated file', False, str(new))
    A, Bf = dict(flat(strip(load(new)))), dict(flat(strip(load(ref))))
    if set(A) != set(Bf): return row(label, 'different keys', 'same keys', False, f'{sorted(set(A) ^ set(Bf))[:3]}')
    wv = wd = 0.0; bad = []
    for k, w in Bf.items():
        g = A[k]
        if g == w: continue
        x, y = as_complex(g), as_complex(w)
        if x is None or y is None or isinstance(w, bool) or (isinstance(w, int) and not isinstance(w, bool)):
            bad.append(k); continue
        d = abs(x - y)
        if DIFFKEY.search(k):
            wd = max(wd, d)
            if d > datol: bad.append(k)
        elif abs(y) > 1e-9:
            wv = max(wv, d / abs(y))
            if d / abs(y) > rtol: bad.append(k)
        elif d > atol: bad.append(k)
    return row(label, f'values rel {wv:.1e}, differences abs {wd:.1e}',
               f'rel <= {rtol:g}, differences abs <= {datol:g}', not bad, f'differing: {bad[:3]}' if bad else '')


def cmp_gz(label, new, ref):
    new = Path(new)
    if not new.is_file(): return row(label, 'missing', 'regenerated file', False, str(new))
    same = gzip.decompress(new.read_bytes()) == gzip.decompress(Path(ref).read_bytes())
    return row(label, 'decompressed identical' if same else 'differs', 'decompressed identical', same)


# ---------------------------------------------------------------- quoted numbers
def rounded(value, text):
    """value (str/Decimal/number) rounded half-even to as many decimals as text shows."""
    t = text.replace('+', '').replace(',', '').strip()
    nd = len(t.split('.')[1]) if '.' in t else 0
    v = Decimal(str(value)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_EVEN)
    return f'{v:f}', t


def quoted(check, value, text, note=''):
    got, t = rounded(value, text)
    return row(check, got, text, Decimal(got) == Decimal(t), note)


def close(check, value, reference, tol, relative=False, note=''):
    v, r = Decimal(str(value)), Decimal(str(reference))
    d = abs(v - r) / (abs(r) if relative else 1)
    return row(check, f'{"rel" if relative else "abs"} diff {float(d):.2e}', f'<= {tol:g}', d <= Decimal(str(tol)), note)


# ---------------------------------------------------------------- report
def report(out, name, extra=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    import platform
    vers = {}
    for m in ('numpy', 'scipy', 'sympy', 'mpmath'):
        try: vers[m] = __import__(m).__version__
        except Exception: vers[m] = None
    (out / f'{name}.json').write_text(json.dumps(dict(package=PKG.name, python=sys.version.split()[0],
                                                      platform=platform.platform(), versions=vers, rows=ROWS,
                                                      **(extra or {})), indent=1) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS:
        print(f"{x['status']}  {x['check']:<{w}}  {str(x['got']):>34}  (expected {x['expected']})"
              + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS)
    print(f"\n{PKG.name} {name}: {len(ROWS) - fails} PASS, {fails} FAIL "
          f"(python {sys.version.split()[0]}, " + ', '.join(f'{k} {v}' for k, v in vers.items()) + ')')
    return 1 if fails else 0
