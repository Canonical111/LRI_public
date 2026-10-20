"""Shared helpers of the SRI/ replays (new tool, 2026-10-15; standard library only; adapted from the Resummation/
replay helpers of the same repository).

- quoted(): the macro entries of ../results/quoted_numbers.json (macro texts as written in the paper's numbers.tex),
  and the whole file (equations eq:sr-closed, eq:sr-C8 and the cells of tab:sr).
- tex_numbers(): the numbers in a macro text with the precision they are written at.
- Table: collects PASS/FAIL/INFO/SKIP rows, prints them, writes them to a file and gives the exit status.
- compare_csv(), compare_json(): compare a regenerated output with the shipped one (by column name; abs/rel tolerance).
- verify_snapshot(): the dated snapshot list public/SNAPSHOT.sha256 of a package (SCRUBBED.txt entries: presence only).
Rounding rule of every quoted-number row: the recomputed value is rounded half-up to the precision at which the
macro writes it (same number of decimals of the mantissa, same power of ten) and must equal the written value.
"""
import csv, json, math, re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

VERIFY = Path(__file__).resolve().parent
ROOT = VERIFY.parent                                  # SRI/
QUOTED = ROOT/'results'/'quoted_numbers.json'


def quoted(path=QUOTED):
    """({macro: entry}, whole file); the file also holds 'equations' (eq:sr-closed, eq:sr-C8) and 'tab_sr'."""
    d = json.loads(Path(path).read_text())
    return {m['macro']: m for m in d['macros']}, d


_NUM = re.compile(r'([+-]?\d+(?:\.\d+)?)(?:\s*\\times\s*10\^\{?([+-]?\d+)\}?)?')


def tex_numbers(text):
    """Numbers of a TeX macro text: [(Decimal value, mantissa string, exponent)], in order of appearance."""
    t = text.replace('\\,', '').replace('\\text{--}', ' -- ').replace('--', ' -- ')
    out = []
    for m in _NUM.finditer(t):
        mant, exp = m.group(1), int(m.group(2)) if m.group(2) else 0
        out.append((Decimal(mant) * (Decimal(10) ** exp), mant, exp))
    return out


def round_like(x, mant, exp):
    """Round float x half-up to the precision of a number written as mant x 10^exp."""
    q = Decimal(1).scaleb(-(len(mant.split('.')[1]) if '.' in mant else 0) + exp)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def matches(values, text, absolute=False):
    """True if each value, rounded like the corresponding number of `text`, equals it. absolute: compare |value|."""
    nums = tex_numbers(text)
    if len(nums) != len(values):
        return False, 'text has %d numbers, %d computed' % (len(nums), len(values))
    shown = []
    for v, (q, mant, exp) in zip(values, nums):
        r = round_like(abs(v) if absolute else v, mant, exp)
        shown.append(str(r))
        if r != q:
            return False, 'rounded %s' % ', '.join(shown)
    return True, 'rounded %s' % ', '.join(shown)


class Table:
    def __init__(self, title):
        self.title, self.rows = title, []

    def add(self, name, status, computed, expected, rule):
        assert status in ('PASS', 'FAIL', 'INFO', 'SKIP'), status
        self.rows.append((name, status, str(computed), str(expected), rule))

    def quoted(self, entry, values, rule, absolute=False, info=False):
        """Row for a quoted macro (entry from quoted()); 'note only' macros and info=True give INFO rows."""
        ok, how = matches(values, entry['text'], absolute)
        st = 'INFO' if (info or entry['status'] != 'printed') else ('PASS' if ok else 'FAIL')
        if st == 'INFO' and not ok:
            how += ' (differs)'
        comp = ', '.join('%.10g' % v for v in values)
        self.add(entry['macro'], st, '%s [%s]' % (comp, how), entry['text'] + ('' if entry['status'] == 'printed' else ' (note only)'), rule)
        return ok

    def check(self, name, ok, computed, expected, rule):
        self.add(name, 'PASS' if ok else 'FAIL', computed, expected, rule)
        return ok

    def report(self, out=None):
        w = [max(len(r[i]) for r in self.rows + [('check', 'status', 'computed', 'expected', 'rule')]) for i in range(4)]
        w = [min(x, c) for x, c in zip(w, (34, 6, 60, 40))]
        lines = ['== ' + self.title, '%-*s  %-*s  %-*s  %-*s  %s' % (w[0], 'check', w[1], 'status', w[2], 'computed',
                                                                     w[3], 'expected', 'rule')]
        for r in self.rows:
            lines.append('%-*s  %-*s  %-*s  %-*s  %s' % (w[0], r[0], w[1], r[1], w[2], r[2], w[3], r[3], r[4]))
        n = {s: sum(r[1] == s for r in self.rows) for s in ('PASS', 'FAIL', 'INFO', 'SKIP')}
        lines.append('== %s: %d PASS, %d FAIL, %d INFO, %d SKIP' % (self.title, n['PASS'], n['FAIL'], n['INFO'], n['SKIP']))
        text = '\n'.join(lines)
        print(text)
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(text + '\n')
        return 1 if n['FAIL'] else 0


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def compare_csv(shipped, rerun, atol=1e-12, rtol=1e-12, key=None, ignore=()):
    """Compare two CSV files by column name (row order kept). Returns (ok, summary, worst list)."""
    a = list(csv.DictReader(open(shipped, newline=''))); b = list(csv.DictReader(open(rerun, newline='')))
    if len(a) != len(b):
        return False, 'rows %d vs %d' % (len(a), len(b)), []
    ca, cb = set(a[0]) if a else set(), set(b[0]) if b else set()
    if ca != cb:
        return False, 'columns differ: only shipped %s, only rerun %s' % (sorted(ca - cb)[:5], sorted(cb - ca)[:5]), []
    worst, bad = {}, []
    for i, (x, y) in enumerate(zip(a, b)):
        for c in ca - set(ignore):
            u, v = x[c], y[c]
            if u == v:
                continue
            fu, fv = _num(u), _num(v)
            if fu is None or fv is None or math.isnan(fu) != math.isnan(fv):
                bad.append((i, c, u, v)); continue
            if math.isnan(fu):
                continue
            d = abs(fu - fv)
            if d > atol + rtol * abs(fu):
                bad.append((i, c, u, v))
            worst[c] = max(worst.get(c, 0.0), d)
    top = sorted(worst.items(), key=lambda kv: -kv[1])[:3]
    return (not bad), '%d values outside tolerance; largest |diff| %s' % (
        len(bad), ', '.join('%s %.1e' % kv for kv in top) or '0'), bad[:5]


def compare_json(shipped, rerun, atol=1e-12, rtol=1e-12, ignore_keys=()):
    """Compare two JSON files: same structure, numbers within tolerance, other leaves equal (keys in ignore_keys and
    keys whose name contains sha256 skipped)."""
    bad, worst = [], [0.0, '']

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k in ignore_keys or 'sha256' in str(k):       # provenance hashes of rerun files are not compared
                    continue
                if k not in x or k not in y:
                    bad.append(path + '/' + k + ' (missing)'); continue
                walk(x[k], y[k], path + '/' + k)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                bad.append(path + ' (length)'); return
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, '%s[%d]' % (path, i))
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            d = abs(x - y)
            if d > worst[0]:
                worst[:] = [d, path]
            if d > atol + rtol * abs(x):
                bad.append(path)
        elif x != y:
            bad.append(path)
    walk(json.loads(Path(shipped).read_text()), json.loads(Path(rerun).read_text()), '')
    return (not bad), '%d leaves differ; largest numeric |diff| %.1e at %s' % (len(bad), worst[0], worst[1] or '-'), bad[:5]


def verify_snapshot(pkg_dir, T):
    """Check the dated snapshot list public/SNAPSHOT.sha256 of a package (the verbatim production files). Files listed
    in public/SCRUBBED.txt (placeholders substituted at export) are checked for presence only."""
    import hashlib
    pkg_dir = Path(pkg_dir)
    lst = pkg_dir/'public'/'SNAPSHOT.sha256'
    scrubbed = set()
    if (pkg_dir/'public'/'SCRUBBED.txt').exists():
        scrubbed = {l.strip() for l in (pkg_dir/'public'/'SCRUBBED.txt').read_text().splitlines() if l.strip() and not l.startswith('#')}
    bad, n, ns = [], 0, 0
    for line in lst.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        h, rel = line.split(None, 1)
        p = pkg_dir/rel
        n += 1
        if not p.exists():
            bad.append(rel + ' (missing)')
        elif rel in scrubbed:
            ns += 1
        elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(rel)
    return T.check('verbatim snapshot', not bad, '%d files (%d scrubbed: presence only)%s' % (n, ns, '; differ: %s' % bad[:4] if bad else ''),
                   'all sha256 equal', 'public/SNAPSHOT.sha256 (dated snapshot of the production files)')
