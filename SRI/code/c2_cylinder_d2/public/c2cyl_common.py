"""Shared helpers of the c2_cylinder_d2 public tools (new file, 2026-10-15; not part of the verbatim package).

PKG is this package (SRI/code/c2_cylinder_d2/, the repository LRI_C2_expanse at commit 98e1935 plus its cluster
records under outputs/); the shared SRI helper sri_lib.py lives in SRI/verify/.
"""
import json, re, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRI = PKG.parent.parent
sys.path.insert(0, str(SRI / 'verify'))
import sri_lib as L                                  # noqa: E402

RESULTS = PKG / 'results' / 'continuum_2026-10'
PACKAGE = 'c2_cylinder_d2'
# Closed form of c_2 (paper appendix, crossover in two dimensions; derived by GPT-6 astra, sibling package
# c2_closed_d2). The value the paper compares with, to the digits given to this package:
C2_CLOSED_TEXT = '-4.06627014813252155'


def current_generation(results=RESULTS):
    """The generation directory named by results/continuum_2026-10/CURRENT (the authoritative result)."""
    rel = (Path(results) / 'CURRENT').read_text().strip()
    gen = (Path(results) / rel).resolve()
    if not (rel.startswith('generations/') and gen.is_dir() and gen.parent == (Path(results) / 'generations').resolve()):
        raise ValueError(f'CURRENT does not name a generation: {rel!r}')
    return gen


def load_json(p):
    return json.loads(Path(p).read_text())


def c2_closed(dps=30):
    """c_2 = 16/R^2 - R^2/9 - (pi^2 R^2/16) (P - 5R^2 Q/384) (P - 5R^2 Q/128 - 512 T/(25 pi R^2)), R = Gamma(1/4)/Gamma(3/4),
    P, Q, T the three 4F3(1) values of the closed form (each series decays as n^-3)."""
    import mpmath as mp
    mp.mp.dps = dps
    f = mp.mpf
    R = mp.gamma(f(1) / 4) / mp.gamma(f(3) / 4)
    P = mp.hyper([-f(1) / 2, -f(1) / 2, f(3) / 2, f(3) / 4], [1, 2, f(1) / 4], 1)
    Q = mp.hyper([f(1) / 2, f(3) / 2, f(3) / 2, f(9) / 4], [3, 3, f(7) / 4], 1)
    T = mp.hyper([f(3) / 2, -f(1) / 4, f(3) / 4, f(3) / 4], [f(1) / 4, f(9) / 4, f(9) / 4], 1)
    return (16 / R ** 2 - R ** 2 / 9 - mp.pi ** 2 * R ** 2 / 16 * (P - 5 * R ** 2 / 384 * Q)
            * (P - 5 * R ** 2 / 128 * Q - 512 / (25 * mp.pi * R ** 2) * T))


def b0_a1():
    """b0 = 9 pi^4/(4 Gamma(1/4)^4) (= 9 pi^2/8 (Gamma(3/4)/Gamma(1/4))^2) and a1 = -pi^2/4, written independently of
    continuum_analysis.c2_from_h0: C2 = a1/b0 + h0/b0^2, dC2 = E(h0)/b0^2."""
    import mpmath as mp
    mp.mp.dps = 50
    return 9 * mp.pi ** 4 / (4 * mp.gamma(mp.mpf(1) / 4) ** 4), -mp.pi ** 2 / 4


_PAREN = re.compile(r'^\s*([+-]?\d+\.(\d+))\((\d+)\)\s*$')


def parse_paren(text):
    """'-4.0670(24)' -> (Decimal('-4.0670'), Decimal('0.0024'), 4): value, uncertainty, decimals."""
    m = _PAREN.match(text)
    if not m:
        raise ValueError(f'not a value(uncertainty) text: {text!r}')
    d = len(m.group(2))
    return Decimal(m.group(1)), Decimal(m.group(3)).scaleb(-d), d


def matches_paren(value, unc, text):
    """Half-up rounding of value and uncertainty to the decimals of `text` (PDG style, uncertainty in units of the last
    digit) must reproduce it exactly."""
    v, u, d = parse_paren(text)
    q = Decimal(1).scaleb(-d)
    rv = Decimal(repr(float(value))).quantize(q, rounding=ROUND_HALF_UP)
    ru = Decimal(repr(float(unc))).quantize(q, rounding=ROUND_HALF_UP)
    return (rv == v and ru == u), f'rounded {rv}({int(ru.scaleb(d))})'


def quoted_entries():
    Q, whole = L.quoted(SRI / 'results' / 'quoted_numbers.json')
    return {k: v for k, v in Q.items() if v.get('package') == PACKAGE}, Q


def leaves(x, path=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f'{path}[{i}]')
    else:
        yield path, x


def compare_tree(a, b, rtol, atol, skip=lambda path: False, rel_tol_for=None):
    """Leaf-by-leaf comparison of two JSON trees. Structure (keys, list lengths, leaf types), strings, booleans, None and
    integers must be equal; floats within atol + rtol |a| (rel_tol_for(path) may return rtol or (rtol, atol) for a leaf
    category).
    Returns a summary dict."""
    out = dict(leaves=0, numeric=0, exact_numeric=0, max_abs=0.0, max_abs_at='', max_rel=0.0, max_rel_at='', bad=[])

    def walk(x, y, path):
        if skip(path):
            return
        if isinstance(x, dict) and isinstance(y, dict):
            if set(x) != set(y):
                out['bad'].append(f'{path}: keys differ {sorted(set(x) ^ set(y))[:4]}')
            for k in sorted(set(x) & set(y)):
                walk(x[k], y[k], f'{path}/{k}')
            return
        if isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                out['bad'].append(f'{path}: length {len(x)} vs {len(y)}')
                return
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f'{path}[{i}]')
            return
        out['leaves'] += 1
        if isinstance(x, float) or isinstance(y, float):
            if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                out['bad'].append(f'{path}: {x!r} vs {y!r}')
                return
            out['numeric'] += 1
            d = abs(x - y)
            if d == 0:
                out['exact_numeric'] += 1
                return
            r = d / max(abs(x), abs(y))
            if d > out['max_abs']:
                out['max_abs'], out['max_abs_at'] = d, path
            if r > out['max_rel']:
                out['max_rel'], out['max_rel_at'] = r, path
            rt = rel_tol_for(path) if rel_tol_for else None
            rt, at = (rtol, atol) if rt is None else (rt if isinstance(rt, tuple) else (rt, atol))
            if d > at + rt * abs(x):
                out['bad'].append(f'{path}: {x!r} vs {y!r}')
            return
        if not same_leaf(x, y):
            out['bad'].append(f'{path}: {x!r} vs {y!r}')
    walk(a, b, '')
    return out


_TOKEN = re.compile(r'<[A-Z][A-Z_]*>')


def same_leaf(shipped, rerun):
    """Equality of two non-float leaves. A shipped string may carry the placeholders of the public export (AGENTS.md
    rule 7: <NODE>, <USER>, <PROJECT>, ...) in place of the original host or path; each placeholder then matches any
    non-empty text."""
    if type(shipped) is not type(rerun):
        return False
    if isinstance(shipped, str) and _TOKEN.search(shipped):
        pat = ''.join('.+?' if _TOKEN.fullmatch(t) else re.escape(t) for t in re.split(r'(<[A-Z][A-Z_]*>)', shipped))
        return re.fullmatch(pat, rerun, re.S) is not None
    return shipped == rerun


def fit_detail_tol(path):
    """Tolerance categories of the regulator-fit leaves. The intercept h0, the influence row (pinv row 0), E, eps_model
    and C2 are compared at the default (1e-9 relative). The regulator coefficients beyond the intercept, the residuals
    and the condition numbers of the 4- and 5-parameter fits are ill-conditioned (condition numbers up to ~2e8, saturated
    fits with residuals at roundoff); they are diagnostics that enter neither h0 nor E, and are compared at 1e-6 relative
    or 1e-12 absolute."""
    if path.endswith('/condition') or path.endswith('/max_residual') or '/residuals[' in path or \
            ('/coefficients[' in path and not path.endswith('/coefficients[0]')):
        return (1e-6, 1e-12)
    return None
