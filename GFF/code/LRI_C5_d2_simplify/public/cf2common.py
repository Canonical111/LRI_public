"""Shared helpers of the public test/replay scripts of LRI_C5_d2_simplify and LRI_C5_d2_proof (added for the release).

The same file ships in both packages' public/ folders.

- PASS/FAIL rows and their report (stdout table, public/out/<name>.json, exit status).
- Comparison of a computed number with a quoted decimal at the printed digits.
- A reader for the numbers printed by Mathematica (precision marks).
- run_pinned(): runs a shipped script unchanged in a work copy under public/out/work/. The shipped scripts hard-code the
  absolute location of the research tree; this helper rewrites that prefix to GFF/code in the work copy only. The
  prefix is whatever precedes '/LRI_C5_d...' in an absolute path: the authors' original home-directory path or any
  sequence of path segments that starts with a scrub token (<PROJECT>, <HOME>/Documents/<PROJECT>, ...).
  Shipped files are never modified.
"""
import hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROWS = []
# an absolute path (/Users/<name>/..., /home/<name>/...) or a scrub token, followed by any further path segments, up to
# the package folder name
PREFIX = re.compile(r'(?:/(?:Users|home)/[^/\s\'"]+|<[A-Z]+>)(?:/[^/\s\'"]+?)*?(?=/LRI_C5_d)')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def row(name, got, want, ok, note=''):
    ROWS.append(dict(check=name, got=str(got), expected=str(want), status='PASS' if ok else 'FAIL', note=note))
    return ok


def quoted(name, value, text, note=''):
    """PASS when value (an mpmath number) rounds to the quoted decimal text at its printed digits (correct rounding)."""
    import mpmath as mp
    t = text.replace('\\ldots', '').replace('...', '').replace('…', '').strip()
    neg = t.startswith('-')
    digits = t.lstrip('+-')
    nd = len(digits.split('.')[1]) if '.' in digits else 0
    q = int(digits.replace('.', '')) * (-1 if neg else 1)
    with mp.workdps(max(mp.mp.dps, nd + 30)):
        r = int(mp.nint(mp.mpf(value) * mp.mpf(10) ** nd))
    got = ('-' if r < 0 else '') + (f'{abs(r):0{nd + 1}d}'[:-nd] + '.' + f'{abs(r):0{nd + 1}d}'[-nd:] if nd else str(abs(r)))
    return row(name, got, t, r == q, note)


def quoted_sci(name, value, text, note=''):
    """PASS when |value| printed with the quoted significant digits (e.g. '4.5e-69', '3e-70') equals the quoted text."""
    m, e = text.lower().split('e')
    nd = len(m.split('.')[1]) if '.' in m else 0
    got = f'{abs(float(value)):.{nd}e}'
    gm, ge = got.split('e')
    got = f'{gm}e{int(ge)}'
    return row(name, got, f'{m}e{int(e)}', got == f'{m}e{int(e)}', note)


MMA = re.compile(r'(-?\d+(?:\.\d*)?)(?:`(?:`)?(-?[\d.]*))?(?:\*\^(-?\d+))?')


def mma_abs(s):
    """Upper bound of |x| for a number printed by Mathematica: '0``35.9' -> 10^-35.9; '-4.6`0.03*^-35' -> 4.6e-35."""
    s = s.strip()
    if s.startswith('0``'):
        return 10.0 ** (-float(s[3:]))
    m = MMA.match(s)
    if not m:
        raise ValueError(s)
    return abs(float(m.group(1))) * (10.0 ** int(m.group(3)) if m.group(3) else 1.0)


def run_pinned(pkg, script, args=(), work=None, extra_files=(), prepare=None, env=None, timeout=None):
    """Copy the files of the script's folder (not subfolders) and extra_files into public/out/work/<work>, rewrite the
    research-tree prefix in the copied .py/.sh/.wl files, run the script there with this Python, return
    (returncode, stdout+stderr text, work dir, seconds)."""
    pkg = Path(pkg).resolve()
    code_root = pkg.parent
    src = (pkg / script).resolve()
    wd = pkg / 'public' / 'out' / 'work' / (work or src.stem)
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    for f in list(src.parent.iterdir()) + [pkg / x for x in extra_files]:
        if f.is_file() and f.name != '.DS_Store':
            shutil.copy2(f, wd / f.name)
    nsub = 0
    for f in wd.iterdir():
        if f.suffix in ('.py', '.sh', '.wl', '.m'):
            txt = f.read_text()
            new, n = PREFIX.subn(str(code_root), txt)
            if n:
                f.write_text(new)
                nsub += n
    if prepare:
        prepare(wd)
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(env or {}))
    t0 = time.time()
    p = subprocess.run([sys.executable, '-B', src.name, *map(str, args)], cwd=wd, env=e, capture_output=True, text=True,
                       timeout=timeout)
    out = p.stdout + (('\n[stderr]\n' + p.stderr) if p.stderr.strip() else '')
    (wd / (src.stem + '.stdout')).write_text(out)
    return p.returncode, out, wd, time.time() - t0, nsub


def same_text(a, b, drop=None):
    """Compare two outputs line by line, optionally dropping lines that match the regex drop."""
    la = [x.rstrip() for x in a.splitlines() if x.strip() and not (drop and re.search(drop, x))]
    lb = [x.rstrip() for x in b.splitlines() if x.strip() and not (drop and re.search(drop, x))]
    return la == lb


def report(out_dir, name, meta):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'{name}.json').write_text(json.dumps(dict(meta, rows=ROWS), indent=1) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS:
        print(f"{x['status']}  {x['check']:<{w}}  {x['got']:>24}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS)
    print(f"\n{len(ROWS) - fails} PASS, {fails} FAIL ({', '.join(f'{k} {v}' for k, v in meta.items())})")
    return 1 if fails else 0


def versions():
    import mpmath, sympy
    return dict(python=sys.version.split()[0], mpmath=mpmath.__version__, sympy=sympy.__version__)


if __name__ == '__main__':
    # python3 public/cf2common.py run <script relative to the package> [args...]: run one shipped script in a work copy
    # (public/out/work/<script stem>/) with the research-tree prefix mapped to GFF/code; prints its output and, when the
    # package ships an output of the same stem (.out or .log), whether the new output is identical.
    if len(sys.argv) < 3 or sys.argv[1] != 'run':
        sys.exit(__doc__)
    pkg = Path(__file__).resolve().parents[1]
    script = sys.argv[2]
    rc, out, wd, secs, nsub = run_pinned(pkg, script, sys.argv[3:], work=Path(script).stem)
    print(out)
    ref = [p for p in (pkg / script).parent.glob(Path(script).stem + '*') if p.suffix in ('.out', '.log')]
    print(f'[{script}] exit {rc}, {secs:.1f} s, {nsub} path(s) mapped; output in {wd}'
          + ''.join(f'; {"identical to" if same_text(out, r.read_text()) else "differs from"} shipped {r.name}' for r in ref))
    sys.exit(rc)
