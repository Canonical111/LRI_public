#!/usr/bin/env python3
"""Gate 7 part 2, `check_dimension8` (PLAN.md A.3 gate 7 (i)-(iv); A-IN-2). Port of C7(3)'s
reference/code/check_dimension.py (byte copy at c8-rb) to order 8, with every length asserted and every comparison
counted.

 (i)   with --d2 DIR --d3 DIR: every d=3 payload L<L>_<sector>/G<id>.txt under --d3 equals its d=2 G-file under --d2
       except the magic and the last line (the rate line);
 (ii)  the two-loop jet b_{2,0..6}(3), recomputed independently: the exact two-3F2(1/4) numerator of the note
       (long_range_ising_condensed.tex gd:twoLoopHyperDefs, gd:twoLoopHyper; d3six:twoLoop), re-coded here,
         N(z) = 4 F1 - 2 W F2,  a = (d+z)/4,  b = (d+3z)/4,  r = Gamma(2a)/Gamma(1+z/2),
         F1 = 3F2(d/2, z/2, a; 1-z/2, a+1/2; 1/4),  F2 = 3F2(z, 2a, b; 1+z/2, b+1/2; 1/4),
         W  = r^2 Gamma(1+z) Gamma(1-z/2) Gamma(b)^2 / (Gamma(a)^2 Gamma(d/2) Gamma(2b)),
       so that bhat_2(z) = -6 z (S_d(z) - 2/z^2) with S_d = N/z^2 gives b_{2,j} = -6 [z^(j+1)] N, j = 0..6; evaluated
       at mpmath dps 80 by a Cauchy contour of radius 0.1 with 160 nodes and by mpmath.taylor; both agree with the 7
       strings of the order-8 two_loop.json to <= 1e-50 relative.
       Lengths, asserted separately (each failure names its file): order-8 B2 has exactly 7 strings, order-7 B2
       exactly 6, the historical file's B2_decimal exactly 5. Prefixes on explicit slices through zip(strict=True):
       order-8 [:6] string-equal to order-7 [:6]; order-7 [:5] and order-8 [:5] each within 1e-46 absolute of the
       historical [:5]; the recomputation against all 7 order-8 strings (contour and Taylor). The comparisons are
       counted and must be 6, 5, 5, 7 and 7;
 (iii) the gamma file has exactly 7 rows of 9 tokens (label 8-L, norm, l_0..l_6), labels 6..0 in that order; for
       L = 2..8, l_{L,1..6} (tokens 4..9 of the row labelled 8-L) agree with a 64-node Cauchy contour (r = 0.041) of
       log G_L to <= 1e-46: exactly 42 comparisons;
 (iv)  Gamma(-q) Gamma(2q)^2 / Gamma(3q) = -16 pi / 15 at q = 3/4 to 1e-60.
 S4-006: every number a comparison reads (the B2 strings of the three files, the gamma rows' tokens 2..9) must be a
 finite decimal string (g3common.NUM_RE; "nan", "inf" or anything else malformed fails the check, naming it, and that
 value is not compared); every recomputed reference value must be finite (and non-zero where it divides); every
 difference must be finite and within its tolerance (a NaN difference fails).
Usage: check_dimension8.py [--two-loop inputs/two_loop.json] [--two-loop-order7 inputs/order7/two_loop.json]
       [--historical reference/reference/d3_C6_two_loop.json] [--gamma inputs/gamma_d3_8.txt]
       [--d2 DIR --d3 DIR] --output FILE
Exit 0 when every check passes, 1 when one fails, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DPS = 80
D = 3


def numerator(m, z):
    d = m.mpf(D)
    a = (d + z) / 4
    b = (d + 3 * z) / 4
    F1 = m.hyp3f2(d / 2, z / 2, a, 1 - z / 2, a + m.mpf(1) / 2, m.mpf(1) / 4)
    F2 = m.hyp3f2(z, 2 * a, b, 1 + z / 2, b + m.mpf(1) / 2, m.mpf(1) / 4)
    r = m.gamma(2 * a) / m.gamma(1 + z / 2)
    W = r ** 2 * m.gamma(1 + z) * m.gamma(1 - z / 2) * m.gamma(b) ** 2 / (m.gamma(a) ** 2 * m.gamma(d / 2) * m.gamma(2 * b))
    return 4 * F1 - 2 * W * F2


def b2_contour(m, radius: str, nodes: int, count: int) -> list:
    r = m.mpf(radius)
    vals = [numerator(m, r * m.expjpi(2 * m.mpf(k) / nodes)) for k in range(nodes)]
    out = []
    for j in range(count):
        p = j + 1
        coef = m.fsum(vals[k] * m.expjpi(-2 * m.mpf(k) * p / nodes) for k in range(nodes)) / (nodes * r ** p)
        out.append(-6 * m.re(coef))
    return out


def b2_taylor(m, count: int) -> list:
    co = m.taylor(lambda z: numerator(m, z), 0, count)
    return [-6 * co[j + 1] for j in range(count)]


def log_gamma_jets(m, L: int, radius: str = '.041', nodes: int = 64) -> list:
    q = m.mpf(D) / 4
    r = m.mpf(radius)

    def logG(z):
        return (L * (m.loggamma(2 * q + z / 2) - m.loggamma(1 + z / 2) - m.loggamma(2 * q)) + m.loggamma(1 + L * z / 2)
                - 2 * L * (m.loggamma(q + z / 4) - m.loggamma(q)))
    vals = [logG(r * m.expjpi(2 * m.mpf(k) / nodes)) for k in range(nodes)]
    return [m.re(m.fsum(vals[k] * m.expjpi(-2 * m.mpf(k) * j / nodes) for k in range(nodes)) / (nodes * r ** j))
            for j in range(1, 7)]


def finite(m, s, where: str, errors: list):
    """S4-006: the mpf of a finite decimal string, or None (the reason appended to errors)."""
    if not isinstance(s, str) or not c.NUM_RE.fullmatch(s):
        errors.append(f'{where}: {str(s)[:40]!r} is not a finite decimal number')
        return None
    v = m.mpf(s)
    if not m.isfinite(v):
        errors.append(f'{where}: {s[:40]!r} is not finite')
        return None
    return v


def within(m, d, tol: str) -> bool:
    """A difference passes only when it is finite and <= tol (a NaN or infinite difference fails)."""
    return bool(m.isfinite(d) and d <= m.mpf(tol))


def load_b2(p: Path, key: str, want: int, errors: list) -> list[str] | None:
    try:
        v = json.loads(p.read_text())[key]
    except (OSError, ValueError, KeyError) as ex:
        errors.append(f'{p}: cannot read {key} ({ex})')
        return None
    if not isinstance(v, list) or len(v) != want or not all(isinstance(x, str) for x in v):
        errors.append(f'{p}: {key} has {len(v) if isinstance(v, list) else "no"} entries, expected exactly {want} strings')
        return None
    return v


def check(a) -> dict:
    import mpmath as m
    m.mp.dps = DPS
    res: dict = {}
    # (i)
    if a.d2 or a.d3:
        e, n = [], 0
        if not (a.d2 and a.d3):
            e.append('(i) needs both --d2 and --d3')
        else:
            for p in sorted(Path(a.d3).glob('L*_*/G*.txt')):
                rel = p.relative_to(a.d3)
                q = Path(a.d2) / rel
                n += 1
                try:
                    if not c.same_body(q.read_bytes(), p.read_bytes()):
                        e.append(f'{rel}: differs from its d=2 G-file beyond the magic and the rate line')
                except (OSError, c.Gen3Error) as ex:
                    e.append(f'{rel}: {ex}')
            if n == 0:
                e.append(f'{a.d3}: no payloads')
        res['i_payload_equals_d2_except_magic_and_rate_line'] = dict(passed=not e, files=n, errors=e[:50], error_count=len(e))
    # (ii)
    e: list[str] = []
    o8 = load_b2(Path(a.two_loop), 'B2', 7, e)
    o7 = load_b2(Path(a.two_loop_order7), 'B2', 6, e)
    hist = load_b2(Path(a.historical), 'B2_decimal', 5, e)
    counts = dict(order8_vs_order7_strings=0, order7_vs_historical=0, order8_vs_historical=0, contour=0, taylor=0)
    worst = {}
    if not e:
        for x, y in zip(o8[:6], o7[:6], strict=True):
            counts['order8_vs_order7_strings'] += 1
            if x != y:
                e.append(f'{a.two_loop} and {a.two_loop_order7}: B2 entries differ ({x[:20]}... vs {y[:20]}...)')
        for name, seq, path in (('order7_vs_historical', o7, a.two_loop_order7), ('order8_vs_historical', o8, a.two_loop)):
            w = m.mpf(0)
            for k, (x, y) in enumerate(zip(seq[:5], hist[:5], strict=True)):
                counts[name] += 1
                xv, yv = finite(m, x, f'{path}: B2 entry {k}', e), finite(m, y, f'{a.historical}: B2_decimal entry {k}', e)
                if xv is None or yv is None:
                    continue
                d = abs(xv - yv)
                w = max(w, d) if m.isfinite(d) else w
                if not within(m, d, '1e-46'):
                    e.append(f'{path}: entry differs from {a.historical} by {m.nstr(d, 3)} > 1e-46')
            worst[name] = m.nstr(w, 3)
        for name, vals in (('contour', b2_contour(m, '0.1', 160, 7)), ('taylor', b2_taylor(m, 7))):
            w = m.mpf(0)
            for k, (x, v) in enumerate(zip(o8, vals, strict=True)):
                counts[name] += 1
                xv = finite(m, x, f'{a.two_loop}: B2 entry {k}', e)
                if not (m.isfinite(v) and v != 0):
                    e.append(f'{a.two_loop}: the {name} recomputation of entry {k} is {m.nstr(v, 3)} (not finite and non-zero)')
                    continue
                if xv is None:
                    continue
                d = abs(xv - v) / abs(v)
                w = max(w, d) if m.isfinite(d) else w
                if not within(m, d, '1e-50'):
                    e.append(f'{a.two_loop}: entry {x[:24]}... differs from the {name} recomputation by {m.nstr(d, 3)} relative > 1e-50')
            worst[name] = m.nstr(w, 3)
        if counts != dict(order8_vs_order7_strings=6, order7_vs_historical=5, order8_vs_historical=5, contour=7, taylor=7):
            e.append(f'comparison counts {counts} differ from 6, 5, 5, 7, 7')
    res['ii_two_loop'] = dict(passed=not e, counts=counts, worst=worst, method='dps 80; contour r = 0.1, 160 nodes; mpmath.taylor',
                              files=dict(order8=str(a.two_loop), order7=str(a.two_loop_order7), historical=str(a.historical)),
                              errors=e)
    # (iii)
    e = []
    n3, w3 = 0, m.mpf(0)
    try:
        rows = [ln.split() for ln in Path(a.gamma).read_text().splitlines() if ln.strip()]
    except OSError as ex:
        rows = []
        e.append(f'{a.gamma}: {ex}')
    if not e:
        if len(rows) != 7 or any(len(r) != 9 for r in rows):
            e.append(f'{a.gamma}: {len(rows)} rows with {[len(r) for r in rows]} tokens; expected exactly 7 rows of 9')
        elif [r[0] for r in rows] != [str(k) for k in range(6, -1, -1)]:
            e.append(f'{a.gamma}: labels {[r[0] for r in rows]}, expected 6..0')
        else:
            for r in rows:
                for k, tok in enumerate(r[1:3], 2):
                    finite(m, tok, f'{a.gamma}: row {r[0]} token {k}', e)
            for L in range(2, 9):
                row = next(r for r in rows if r[0] == str(8 - L))
                jets = log_gamma_jets(m, L)
                for k, (tok, v) in enumerate(zip(row[3:9], jets, strict=True), 4):
                    n3 += 1
                    tv = finite(m, tok, f'{a.gamma}: row {row[0]} token {k}', e)
                    if not m.isfinite(v):
                        e.append(f'{a.gamma}: L = {L}: the contour value of token {k} is not finite')
                        continue
                    if tv is None:
                        continue
                    d = abs(tv - v)
                    w3 = max(w3, d) if m.isfinite(d) else w3
                    if not within(m, d, '1e-46'):
                        e.append(f'{a.gamma}: L = {L} jet {tok[:20]}... differs from the contour by {m.nstr(d, 3)} > 1e-46')
            if n3 != 42:
                e.append(f'{n3} gamma comparisons, expected 42')
    res['iii_gamma_rows'] = dict(passed=not e, comparisons=n3, worst=m.nstr(w3, 3), file=str(a.gamma), errors=e[:50])
    # (iv)
    q = m.mpf(3) / 4
    val = m.gamma(-q) * m.gamma(2 * q) ** 2 / m.gamma(3 * q)
    d4 = abs(val + 16 * m.pi / 15)
    res['iv_power_three_loop_b3'] = dict(passed=bool(m.isfinite(d4) and d4 < m.mpf('1e-60')), difference=m.nstr(d4, 3), exact='-16*pi/15')
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--two-loop', default=str(ROOT / 'inputs/two_loop.json'))
    ap.add_argument('--two-loop-order7', default=str(ROOT / 'inputs/order7/two_loop.json'))
    ap.add_argument('--historical', default=str(ROOT / 'reference/reference/d3_C6_two_loop.json'))
    ap.add_argument('--gamma', default=str(ROOT / 'inputs/gamma_d3_8.txt'))
    ap.add_argument('--d2')
    ap.add_argument('--d3')
    ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    c.refuse_c62d(a.output, 'output')
    res = check(a)
    passed = all(v['passed'] for v in res.values())
    c.write_json(a.output, dict(schema='c8-d3-check-dimension8-1', gate='7 check_dimension8 (i)-(iv)', passed=passed, checks=res))
    for k, v in res.items():
        print(f'{k}: {"PASS" if v["passed"] else "FAIL"}' + ('' if v['passed'] else f' {v.get("errors", [])[:3]}'))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
