#!/usr/bin/env python3
"""The d=2 low-loop inputs: the gamma rows and the two-loop jet B2 (PLAN component B; A-IN-1, A-IN-2, A-IN-6(a)).

A port of reference/LRI_C7_d2_progress/code/prepare.py:5-24 (mpmath, dps 75) with an --order option:
  gamma_d2_<order>.txt  rows L = 2..order with label order-L: the norm 2(-1)^(L+1)/pi^L, then l_0 = 0 and
                        l_j = [(L/2)^j psi_{j-1}(1) - 2L 4^-j psi_{j-1}(1/2)]/j!, j = 1..order-2, printed with
                        nstr(..., 65) as in the original (DECISIONS.md B1);
  two_loop.json         {"B2": [...]}: order-1 strings, the Taylor coefficients k = 1..order-1 of the exact 3F2
                        numerator from the Cauchy contour r = .08 with 96 nodes (the original's second contour);
                        the first contour (r = .05, 80 nodes) is the check (DECISIONS.md B2);
  verification/two_loop_extension<order>.json (order 8): both contours, a reference contour (r = 0.2, 192 nodes,
                        dps 95) and the differences per k.
At order 7 the files are C7(2)'s, byte for byte. At order 8 rows L = 2..7 repeat the norm and l_0..l_5 tokens of
gamma_d2_7.txt and append l_6; the new L = 8 row has norm -2/pi^8 and l_1 = 8 log 2 (unused: K = 0); the first six
B2 strings are C7(2)'s.

Usage:
  python3 -B tools/make_lowloop.py [--order 8] [--out inputs]        write the files (order 8: also the record)
  python3 -B tools/make_lowloop.py --verify [--cross-check DIR] [--output FILE]
      regenerates both orders in a scratch directory and requires: byte identity with inputs/gamma_d2_8.txt,
      inputs/two_loop.json and inputs/verification/two_loop_extension8.json; at order 7 byte identity with C7(2)'s
      gamma_d2_7.txt and two_loop.json (reference/c7d2_hpc_a55958f/inputs); the A-IN-1 and A-IN-2 checks; and the
      A-IN-6(a) Cauchy check: every l_{L,j} (L = 2..8, j = 1..6) as a Taylor coefficient of
      log G_L(z) = log Gamma(1 + Lz/2) - 2L log Gamma(1/2 + z/4) on a 64-node contour, agreeing with the printed
      token to <= 1e-45.
      --cross-check DIR (after G-H2: vendor/c8_assembly/inputs_d2_check) compares with C63d's HANDOFF files:
      gamma_d2_8.txt byte for byte, and the 7 B2 strings. It only compares: nothing is written into inputs/, and
      the comparison record is never an input (PLAN "One rule governs reads of vendor/").
Exit status 0 when every check passes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import mpmath as m

ROOT = Path(__file__).resolve().parents[1]
C7REF = ROOT / 'reference/c7d2_hpc_a55958f/inputs'
CONTOURS = [('.05', 80), ('.08', 96)]       # the original's two contours; the second is stored
REFERENCE = ('0.2', 192, 95)                 # radius, nodes, dps of the reference contour
B26_RECON = '-266.5209679613593817322521926190898009490'  # PLAN A-IN-2 (RECON), printed digits
CAUCHY_NODES, CAUCHY_TOL = 64, m.mpf('1e-45')


def gamma_text(order: int) -> str:
    """The original's gamma rows at dps 75 (prepare.py:7-10), generalized to rows L = 2..order."""
    lines = []
    with m.workdps(75):
        for L in range(2, order + 1):
            norm = 2 * (-1) ** (L + 1) / m.pi ** L
            logs = [m.mpf(0)] + [(m.mpf(L / 2) ** k * m.polygamma(k - 1, 1) - 2 * L * m.mpf('.25') ** k
                                  * m.polygamma(k - 1, m.mpf('.5'))) / m.factorial(k) for k in range(1, order - 1)]
            lines.append(' '.join([str(order - L), m.nstr(norm, 65), *(m.nstr(v, 65) for v in logs)]) + '\n')
    return ''.join(lines)


def numerator(z):
    """The exact 3F2 numerator of the two-loop graph (prepare.py:11-16), at the current precision."""
    a = m.mpf('.5') + z / 4
    b = m.mpf('.5') + 3 * z / 4
    F1 = m.hyper([1, z / 2, a], [1 - z / 2, a + m.mpf('.5')], m.mpf('.25'))
    F2 = m.hyper([z, 2 * a, b], [1 + z / 2, b + m.mpf('.5')], m.mpf('.25'))
    w = m.gamma(1 + z) * m.gamma(1 - z / 2) * m.gamma(b) ** 2 / (m.gamma(a) ** 2 * m.gamma(2 * b))
    return 4 * F1 - 2 * w * F2


def contour(rad: str, n: int, kmax: int) -> list[str]:
    """B2 coefficients k = 1..kmax from one Cauchy contour (prepare.py:19-20, same expressions and order)."""
    r = m.mpf(rad)
    v = [numerator(r * m.exp(2j * m.pi * (j + m.mpf('.5')) / n)) for j in range(n // 2)]
    cs = [-12 * m.fsum(m.re(v[j] * m.exp(-2j * m.pi * (j + m.mpf('.5')) * k / n)) for j in range(n // 2)) / (n * r ** k)
          for k in range(1, kmax + 1)]
    return list(map(str, cs))


def two_loop(order: int, with_reference: bool) -> tuple[str, dict]:
    kmax = order - 1
    with m.workdps(75):
        rr = [dict(radius=rad, nodes=n, B2=contour(rad, n, kmax)) for rad, n in CONTOURS]
        diff = [m.nstr(abs(m.mpf(x) - m.mpf(y)), 3) for x, y in zip(rr[0]['B2'], rr[1]['B2'])]
    text = json.dumps(dict(B2=rr[-1]['B2']), indent=2)  # the original writes no final newline
    rec = dict(dps=75, records=rr, stored='the r = .08, 96-node contour (the original\'s convention)',
               two_contour_abs_difference=diff,
               max_two_contour_difference=max(diff, key=lambda s: m.mpf(s)))
    if with_reference:
        rad, n, dps = REFERENCE
        with m.workdps(dps):
            ref = contour(rad, n, kmax)
        with m.workdps(dps):
            dref = [m.nstr(abs(m.mpf(x) - m.mpf(y)), 3) for x, y in zip(rr[-1]['B2'], ref)]
        rec.update(reference=dict(radius=rad, nodes=n, dps=dps, B2=ref), stored_vs_reference_abs_difference=dref,
                   max_stored_vs_reference=max(dref, key=lambda s: m.mpf(s)))
    return text, rec


def write(order: int, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    gtext = gamma_text(order)
    (out / f'gamma_d2_{order}.txt').write_bytes(gtext.encode())
    ttext, rec = two_loop(order, with_reference=order == 8)
    (out / 'two_loop.json').write_bytes(ttext.encode())
    files = {f'gamma_d2_{order}.txt': gtext.encode(), 'two_loop.json': ttext.encode()}
    if order == 8:
        rec = dict(schema='c8-d2-two-loop-extension-1', order=8, generator='tools/make_lowloop.py', **rec)
        data = (json.dumps(rec, indent=1) + '\n').encode()
        (out / 'verification').mkdir(exist_ok=True)
        (out / 'verification/two_loop_extension8.json').write_bytes(data)
        files['verification/two_loop_extension8.json'] = data
    return files


def cauchy_logs(L: int, jmax: int) -> list:
    """l_{L,1..jmax} as Taylor coefficients of log G_L on a CAUCHY_NODES-node circle of radius 0.3/L (the nearest
    singularity, the pole of Gamma(1 + Lz/2) at z = -2/L, is 6.7 radii away)."""
    with m.workdps(75):
        r = m.mpf('0.3') / L
        N = CAUCHY_NODES
        pts = [r * m.exp(2j * m.pi * (n + m.mpf('.5')) / N) for n in range(N)]
        f = [m.loggamma(1 + L * z / 2) - 2 * L * m.loggamma(m.mpf('.5') + z / 4) for z in pts]
        return [m.re(m.fsum(f[n] * m.exp(-2j * m.pi * (n + m.mpf('.5')) * j / N) for n in range(N)) / (N * r ** j))
                for j in range(1, jmax + 1)]


def verify(a) -> int:
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1500:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-500:]}' if detail and not ok else ''), flush=True)

    sha = lambda b: hashlib.sha256(b).hexdigest()
    with tempfile.TemporaryDirectory(prefix='c8d2_lowloop_') as td:
        t8, t7 = Path(td) / 'o8', Path(td) / 'o7'
        f8, f7 = write(8, t8), write(7, t7)
        for name, data in f8.items():
            shipped = (ROOT / 'inputs' / name)
            check(f'inputs/{name} regenerates byte for byte', shipped.is_file() and shipped.read_bytes() == data,
                  dict(regenerated=sha(data), shipped=sha(shipped.read_bytes()) if shipped.is_file() else None))
        for name in ('gamma_d2_7.txt', 'two_loop.json'):
            ref = (C7REF / name).read_bytes()
            check(f'--order 7 reproduces C7(2)\'s {name} byte for byte (sha256 {sha(ref)[:8]})', f7[name] == ref,
                  dict(regenerated=sha(f7[name]), c7=sha(ref)))
    # A-IN-1
    rows = [ln.split(' ') for ln in f8['gamma_d2_8.txt'].decode().splitlines()]
    rows7 = [ln.split(' ') for ln in (C7REF / 'gamma_d2_7.txt').read_text().splitlines()]
    check('gamma_d2_8.txt: 7 rows, labels 6..0, 9 tokens per row',
          len(rows) == 7 and [r[0] for r in rows] == [str(x) for x in range(6, -1, -1)] and all(len(r) == 9 for r in rows))
    check('rows L=2..7 repeat the norm and l_0..l_5 tokens of gamma_d2_7.txt',
          all(rows[i][1:8] == rows7[i][1:8] for i in range(6)) and len(rows7) == 6)
    with m.workdps(75):
        n8 = -2 / m.pi ** 8
        check('the L=8 norm equals -2/pi^8 to 60 digits', abs(m.mpf(rows[6][1]) - n8) <= m.mpf('1e-60') * abs(n8),
              dict(token=rows[6][1], value=m.nstr(n8, 30)))
        check('the L=8 row has l_1 = 8 log 2', abs(m.mpf(rows[6][3]) - 8 * m.log(2)) <= m.mpf('1e-60'), rows[6][3])
    # A-IN-2
    b2 = json.loads(f8['two_loop.json'])['B2']
    b2c7 = json.loads((C7REF / 'two_loop.json').read_text())['B2']
    check('two_loop.json has 7 strings, the first 6 identical to C7(2)\'s', len(b2) == 7 and b2[:6] == b2c7)
    rec = json.loads(f8['verification/two_loop_extension8.json'])
    with m.workdps(95):
        two = max(m.mpf(x) for x in rec['two_contour_abs_difference'])
        ref = max(m.mpf(x) for x in rec['stored_vs_reference_abs_difference'])
    check('the two contours agree to <= 1e-50 for k = 1..7', two <= m.mpf('1e-50'), rec['two_contour_abs_difference'])
    check('the stored values agree with the reference contour (r = 0.2, 192 nodes, dps 95) to <= 1e-60',
          ref <= m.mpf('1e-60'), rec['stored_vs_reference_abs_difference'])
    digits = B26_RECON.lstrip('-')
    with m.workdps(75):
        close = abs(m.mpf(b2[6]) - m.mpf(B26_RECON)) <= m.mpf(10) ** (-(len(digits.split('.')[1]))) / 2
    check(f'b_2,6 matches {B26_RECON} to the printed digits', b2[6].startswith(B26_RECON) or close, b2[6])
    # A-IN-6(a)
    worst, rowsdiff = m.mpf(0), {}
    for i, L in enumerate(range(2, 9)):
        got = cauchy_logs(L, 6)
        with m.workdps(75):  # the printed tokens are parsed at the generator's precision, never at mpmath's default 15
            d = [abs(got[j - 1] - m.mpf(rows[i][2 + j])) for j in range(1, 7)]
            rowsdiff[f'L{L}'] = [m.nstr(x, 3) for x in d]
            worst = max([worst] + d)
    check(f'Cauchy check of every l_(L,j), L = 2..8, j = 1..6 ({CAUCHY_NODES} nodes): agreement <= 1e-45',
          worst <= CAUCHY_TOL, dict(max=m.nstr(worst, 3), per_row=rowsdiff))
    out = dict(schema='c8-d2-gate-1', gate='A-IN-1, A-IN-2, A-IN-6(a) make_lowloop --verify',
               mpmath=m.__version__, python=sys.version.split()[0], cauchy_max_abs_difference=m.nstr(worst, 3),
               cauchy_per_row=rowsdiff, two_contour_abs_difference=rec['two_contour_abs_difference'],
               stored_vs_reference_abs_difference=rec['stored_vs_reference_abs_difference'], b26=b2[6],
               sha256={k: sha(v) for k, v in f8.items()})
    # cross-check with C63d's HANDOFF version (after G-H2); comparison only
    if a.cross_check:
        d = a.cross_check
        cg = (d / 'gamma_d2_8.txt').read_bytes()
        cb = json.loads((d / 'two_loop.json').read_bytes())['B2']
        check(f'cross-check: gamma_d2_8.txt byte-identical to {d}/gamma_d2_8.txt (sha256 {sha(cg)[:8]})',
              cg == f8['gamma_d2_8.txt'], dict(ours=sha(f8['gamma_d2_8.txt']), theirs=sha(cg)))
        check(f'cross-check: the 7 B2 strings equal {d}/two_loop.json\'s', cb == b2,
              [(i, x, y) for i, (x, y) in enumerate(zip(b2, cb)) if x != y] or len(cb))
        out['cross_check'] = dict(directory=str(d), gamma_sha256=sha(cg), two_loop_sha256=sha((d / 'two_loop.json').read_bytes()),
                                  note='comparison only (DECISIONS.md A2): never an input')
    out.update(passed=not failed, failed=failed, checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(out, indent=1) + '\n')
    print(f'make_lowloop --verify: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--order', type=int, choices=(7, 8), default=8)
    ap.add_argument('--out', type=Path, default=ROOT / 'inputs')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--cross-check', type=Path, help='compare with C63d\'s inputs_d2_check (only with --verify)')
    ap.add_argument('--output', type=Path, help='--verify: write the JSON record here')
    a = ap.parse_args()
    if a.cross_check and not a.verify:
        raise SystemExit('--cross-check needs --verify (it only compares)')
    if a.verify:
        return verify(a)
    files = write(a.order, a.out)
    print(json.dumps({k: hashlib.sha256(v).hexdigest() for k, v in files.items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
