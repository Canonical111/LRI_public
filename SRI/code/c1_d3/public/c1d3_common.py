"""Shared helpers of the c1_d3 public tools (new tool, 2026-10-15; standard library only).

- work_copy(): a copy of the verbatim package (without public/, public.mk and .work/) in a work directory, where the
  package's own workflow scripts run unchanged (they resolve every path relative to themselves and write their
  outputs next to their --output/--results arguments, so the shipped tree is never written to).
- run(): run one verbatim script with the thread settings and the temporary directory of the package's own driver.
- check_snapshot(), check_delivery_list(): the dated snapshot public/SNAPSHOT.sha256 and the authors' delivery checksum
  list SHA256SUMS (shipped verbatim, subset mode). A listed file passes if its sha256 equals the pin, or the published
  sha256 that a re-pin map (RE-PINNED.json of the package, if present: files[].original_sha256 -> published_sha256)
  gives for that pin, or if it is listed in public/SCRUBBED.txt (written by the repository's scrub: presence only).
  Files listed in public/NOT_SHIPPED.txt were left out of the export and must be absent (SHA256SUMS only).
- compare_table(): compare a CSV table written by make_assets.py (list cells are JSON) with tolerances.
"""
import csv, hashlib, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                   # SRI/code/c1_d3
SRI = PKG.parent.parent                             # SRI/
sys.path.insert(0, str(SRI/'verify'))
import sri_lib as L                                 # noqa: E402

SKIP_TOP = {'public', 'public.mk', '.work', '__pycache__'}


def _names(path):
    p = PKG/path
    if not p.exists():
        return set()
    return {l.split('#')[0].strip() for l in p.read_text().splitlines() if l.split('#')[0].strip()}


def work_copy(dest):
    """Fresh copy of the verbatim package in dest (removed first)."""
    dest = Path(dest)
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for item in PKG.iterdir():
        if item.name in SKIP_TOP:
            continue
        if item.is_dir():
            shutil.copytree(item, dest/item.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(item, dest/item.name)
    return dest


def run(args, cwd, tmp, log=None):
    """Run [python, *args] in cwd with one BLAS thread and TMPDIR=tmp; returns (returncode, output, seconds)."""
    Path(tmp).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1',
               TMPDIR=str(Path(tmp).resolve()))
    t = time.time()
    r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, env=env, capture_output=True, text=True)
    dt = time.time() - t
    out = r.stdout + r.stderr
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_text(out)
    return r.returncode, out, dt


def _cell(s):
    """CSV cell -> number, JSON list/dict (make_assets.py writes list cells as JSON) or the string itself."""
    try:
        return float(s)
    except (TypeError, ValueError):
        pass
    if isinstance(s, str) and s[:1] in '[{':
        try:
            return json.loads(s)
        except ValueError:
            pass
    return s


def _close(x, y, atol, rtol, worst):
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all([_close(u, v, atol, rtol, worst) for u, v in zip(x, y)])
    if isinstance(x, dict) and isinstance(y, dict):
        return set(x) == set(y) and all([_close(x[k], y[k], atol, rtol, worst) for k in x])
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        if math.isnan(x) or math.isnan(y):
            return math.isnan(x) and math.isnan(y)
        d = abs(x - y)
        worst[0] = max(worst[0], d)
        return d <= atol + rtol*abs(x)
    return x == y


def compare_table(shipped, rerun, atol, rtol):
    """Compare two CSV files written by make_assets.py: same header and rows; numbers, also inside JSON-list cells,
    within atol + rtol*|x|; other cells equal. Returns (ok, summary)."""
    a = list(csv.reader(open(shipped, newline=''))); b = list(csv.reader(open(rerun, newline='')))
    if not a or not b or a[0] != b[0] or len(a) != len(b):
        return False, 'header or row count differs'
    worst, bad = [0.0], []
    for i, (r, s) in enumerate(zip(a[1:], b[1:])):
        for c, u, v in zip(a[0], r, s):
            if u != v and not _close(_cell(u), _cell(v), atol, rtol, worst):
                bad.append('row %d %s' % (i, c))
    return not bad, '%d rows; largest |diff| %.1e%s' % (len(a) - 1, worst[0], '; outside: %s' % bad[:3] if bad else '')


def _repins():
    """original sha256 -> published sha256 from the package's RE-PINNED.json (none if the file is absent)."""
    for p in (PKG/'RE-PINNED.json', PKG/'public'/'RE-PINNED.json'):
        if p.exists():
            d = json.loads(p.read_text())
            return {f['original_sha256']: f['published_sha256'] for f in d.get('files', [])}
    return {}


def _pin_ok(path, pinned, repin):
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h == pinned or (pinned in repin and h == repin[pinned])


def check_snapshot(T):
    """public/SNAPSHOT.sha256 (the shipped production files)."""
    scrubbed, repin = _names('public/SCRUBBED.txt'), _repins()
    bad, n, ns = [], 0, 0
    for line in (PKG/'public'/'SNAPSHOT.sha256').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        h, rel = line.split(None, 1)
        p = PKG/rel
        n += 1
        if not p.is_file():
            bad.append(rel + ' (missing)')
        elif rel in scrubbed:
            ns += 1
        elif not _pin_ok(p, h, repin):
            bad.append(rel)
    return T.check('verbatim snapshot', not bad, '%d files (%d scrubbed: presence only; %d re-pins known)%s'
                   % (n, ns, len(repin), '; differ: %s' % bad[:4] if bad else ''), 'all sha256 equal',
                   'public/SNAPSHOT.sha256 (dated snapshot of the production files; RE-PINNED.json, SCRUBBED.txt honoured)')


def check_delivery_list(T):
    """Rows for the authors' SHA256SUMS (verbatim) in subset mode."""
    lst = PKG/'SHA256SUMS'
    absent, scrubbed, repin = _names('public/NOT_SHIPPED.txt'), _names('public/SCRUBBED.txt'), _repins()
    bad, n, nok, nabs, nscr = [], 0, 0, 0, 0
    listed = set()
    for line in lst.read_text().splitlines():
        if not line.strip():
            continue
        h, rel = line.split('  ', 1)
        listed.add(rel)
        n += 1
        p = PKG/rel
        if rel in absent:
            nabs += 1
            if p.exists():
                bad.append(rel + ' (listed as not shipped, but present)')
        elif not p.is_file():
            bad.append(rel + ' (missing)')
        elif rel in scrubbed:
            nscr += 1
        elif not _pin_ok(p, h, repin):
            bad.append(rel + ' (sha256 differs)')
        else:
            nok += 1
    stray = sorted(absent - listed)
    if stray:
        bad.append('NOT_SHIPPED.txt names unlisted files: %s' % stray[:3])
    return T.check('authors\' delivery list', not bad,
                   '%d listed: %d equal, %d scrubbed (presence only), %d not shipped%s'
                   % (n, nok, nscr, nabs, '; problems: %s' % bad[:4] if bad else ''),
                   'every shipped listed file equal', 'SHA256SUMS of the 2026-10-08 delivery, subset mode '
                   '(public/NOT_SHIPPED.txt: left out of the export; RE-PINNED.json map; public/SCRUBBED.txt: presence only)')
