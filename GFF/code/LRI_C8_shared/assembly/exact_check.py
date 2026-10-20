#!/usr/bin/env python3
"""Independent exact-rational checks of the order-7/8 fixed-point assembly (order8_assembly.py).

Nothing here is derived from the float code. Two exact routes are built from the RG equations as the condensed note
states them (GFF/LRI_condensed_note/long_range_ising_condensed.tex, "N:" = line):

  route L  bivariate Lagrange inversion, eq. done:bivariateLagrange (N:9046-9051) = d3six:lagrange (N:9221-9226):
           C_0 = d/2,  C_n = -1/2 delta_{n1} + sum_{k=1}^n (1/k) [g^(k-1) z^(n-k)] d_g gamma_r(g,z) Bhat(g,z)^(-k),
           Bhat = sum_{L>=1} b_L(z) g^(L-1), b_1 = 3, gamma_r = sum_L c_L(z) g^L, c_1 = 1 (N:9033-9035, N:10388);
  route F  the fixed point beta(g_*, eps) = 0 of beta = -z g + sum_L b_L(z) g^(L+1) at z = eps (N:8912-8915,
           N:10388), i.e. eps = 3 g_* + sum_{L>=2} b_L(eps) g_*^L, solved coefficient by coefficient
           (u_m = ([m=1] - [eps^m] sum_{L>=2} b_L g^L)/3; the bracket involves u_1..u_{m-1} only), then
           Delta_E = d/2 - eps/2 + gamma_r(g_*, eps) (N:10681, N:2264).

Both routes take independent jets b_L, c_L (L = 2..order, c_2 free); the float code's convention c_2 = b_2/6 is a
special case. The constant-coefficient MS polynomials ms_n (n <= 8) are derived with sympy from eq:Lagrange (N:232)
with b_2 = -6A, c_2 = -A (N:2273) and compared with the note's C2..C6 formulas, the delivered ms7 and C62d's ms8.

Run:  python3 exact_check.py [--fast] [--write]   (--write stores exact_check_results.json next to this file)
Importing order8_assembly sets sys.dont_write_bytecode first, so no __pycache__ is written into this folder.
The delivered ms7 and C62d's live RECON.md are read under $LRI_ROOT (default: two levels above this file); when
absent, those two comparisons are left out (the embedded copies are still compared).
"""
from __future__ import annotations
import ast, hashlib, json, math, os, random, re, sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
LRI = Path(os.environ.get('LRI_ROOT', HERE.parents[1]))  # .../Agent_LRI (override for a vendored copy)


# ---------------------------------------------------------------------------------------------------------------
# Exact routes

def _bmul(p: dict, q: dict, G: int, Z: int) -> dict:
    """Product of bivariate polynomials {(g power, z power): Fraction}, truncated at g^G, z^Z."""
    out = {}
    for (i, j), x in p.items():
        for (k, l), y in q.items():
            if i + k <= G and j + l <= Z:
                key = (i + k, j + l); out[key] = out.get(key, 0) + x * y
    return out


def lagrange(b: dict, c: dict, order: int, half_d) -> list:
    """Route L. b, c: {L: [z^0, z^1, ...]} for L = 1..order (b[1] == [3], c[1] == [1])."""
    assert b[1][0] == 3 and c[1][0] == 1 and not any(b[1][1:]) and not any(c[1][1:])
    C = [F(0)] * (order + 1); C[0] = F(half_d); C[1] -= F(1, 2)
    for n in range(1, order + 1):
        for k in range(1, n + 1):
            G, Z = k - 1, n - k
            X = {(L - 1, j): F(x) / 3 for L in b if L >= 2 and L - 1 <= G for j, x in enumerate(b[L]) if j <= Z and x}
            dgam = {(L - 1, j): L * F(x) for L in c if L - 1 <= G for j, x in enumerate(c[L]) if j <= Z and x}
            # (1 + X)^(-k) = sum_m binom(-k, m) X^m; X = O(g), so m <= G suffices.
            S = {(0, 0): F(1)}; Xm = {(0, 0): F(1)}
            for mm in range(1, G + 1):
                Xm = _bmul(Xm, X, G, Z)
                coef = (-1) ** mm * math.comb(k + mm - 1, mm)
                for key, v in Xm.items(): S[key] = S.get(key, 0) + coef * v
            C[n] += _bmul(dgam, S, G, Z).get((G, Z), F(0)) / (k * 3 ** k)
    return C


def _smul(a: list, b: list, N: int) -> list:
    out = [F(0)] * N
    for i, x in enumerate(a[:N]):
        if x:
            for j, y in enumerate(b[:N - i]):
                if y: out[i + j] += x * y
    return out


def fixed_point(b: dict, c: dict, order: int, half_d) -> list:
    """Route F (see module docstring)."""
    N = order + 1; u = [F(0)] * N
    for mdeg in range(1, N):
        gpow = u[:]; S = F(0)
        for L in range(2, N):
            gpow = _smul(gpow, u, N)  # g^L with the current u (u_mdeg is still 0 and cannot enter [eps^mdeg] for L >= 2)
            if L in b: S += _smul([F(x) for x in b[L]], gpow, N)[mdeg]
        u[mdeg] = (F(int(mdeg == 1)) - S) / 3
    D = [F(0)] * N; gpow = [F(1)] + [F(0)] * (N - 1)
    for L in range(1, N):
        gpow = _smul(gpow, u, N)
        if L in c: D = [x + y for x, y in zip(D, _smul([F(x) for x in c[L]], gpow, N))]
    D[0] += F(half_d); D[1] -= F(1, 2)
    return D


def from_float_convention(vals: dict, B2, order: int) -> tuple[dict, dict]:
    """Exact (b, c) from the float code's inputs: b_2 = B2, c_2 = B2/6, loop vectors split b | c."""
    N = order + 1
    b = {1: [F(3)], 2: [F(x) for x in list(B2)[:order - 1]]}; c = {1: [F(1)], 2: [x / 6 for x in b[2]]}
    for L, a in vals.items():
        k = N - L; a = [F(x) for x in a]; assert len(a) == 2 * k
        b[L] = a[:k]; c[L] = a[k:]
    return b, c


def rand_frac(rng: random.Random, num=12, den=7) -> F:
    return F(rng.randint(-num, num), rng.randint(1, den))


def random_inputs(rng: random.Random, order: int) -> tuple[dict, list]:
    """Random rational inputs in the float code's convention: (vals, B2)."""
    N = order + 1
    vals = {L: [rand_frac(rng) for _ in range(2 * (N - L))] for L in range(3, N)}
    B2 = [rand_frac(rng) for _ in range(order - 1)]
    return vals, B2


def random_general(rng: random.Random, order: int) -> tuple[dict, dict]:
    """Random independent jets b_L, c_L, L = 2..order (c_2 not tied to b_2)."""
    N = order + 1; b = {1: [F(3)]}; c = {1: [F(1)]}
    for L in range(2, N):
        b[L] = [rand_frac(rng) for _ in range(N - L)]; c[L] = [rand_frac(rng) for _ in range(N - L)]
    return b, c


# ---------------------------------------------------------------------------------------------------------------
# Exact gates

def _shift(b, c, L, channel, j, h):
    b2 = {k: list(v) for k, v in b.items()}; c2 = {k: list(v) for k, v in c.items()}
    tgt = b2 if channel == 'b' else c2
    tgt[L] = tgt.get(L, []) + [F(0)] * max(0, j + 1 - len(tgt.get(L, [])))
    tgt[L][j] += h
    return b2, c2


def exact_top_slot(order: int, cases: int, seed: int, route=fixed_point) -> list:
    """dC_order/d(b,c)_{L,order-L} = (-1,+3)/3^(L+1) for L = 2..order, exactly, at random points (general c_2), and
    no lower C_n depends on the top slot. The slot is affine, so the derivative is the exact unit difference."""
    rng = random.Random(seed); rows = []
    for t in range(cases):
        b, c = random_general(rng, order); base = route(b, c, order, F(3, 2))
        for L in range(2, order + 1):
            j = order - L; got = {}
            for ch in 'bc':
                bb, cc = _shift(b, c, L, ch, j, F(1)); new = route(bb, cc, order, F(3, 2))
                d = [x - y for x, y in zip(new, base)]
                assert all(x == 0 for x in d[:order]), (L, ch, 'lower order changed')
                got[ch] = d[order]
            want = (F(-1, 3 ** (L + 1)), F(3, 3 ** (L + 1)))
            assert (got['b'], got['c']) == want, (L, got, want)
            rows.append(dict(case=t, L=L, dC_db=str(got['b']), dC_dc=str(got['c'])))
    return rows


def exact_loop7(cases: int, seed: int, route=fixed_point) -> list:
    """At order 8: dC8/db_{7,0} = (3 b_{2,0} - 2 c_{2,0})/3^9 and dC8/dc_{7,0} = -7 b_{2,0}/3^9 for general jets (exact,
    random points); with c_2 = b_2/6 and b_{2,0} = -6A this is (-16A, 42A)/19683."""
    rng = random.Random(seed); rows = []
    for t in range(cases):
        b, c = random_general(rng, 8)
        if t % 2: c[2] = [x / 6 for x in b[2]]  # every other case in the float code's convention
        base = route(b, c, 8, F(1))
        db = route(*_shift(b, c, 7, 'b', 0, F(1)), 8, F(1))[8] - base[8]
        dc = route(*_shift(b, c, 7, 'c', 0, F(1)), 8, F(1))[8] - base[8]
        b20, c20 = b[2][0], c[2][0]
        assert db == (3 * b20 - 2 * c20) / 3 ** 9 and dc == -7 * b20 / 3 ** 9, (db, dc)
        if t % 2:
            A = -b20 / 6; assert (db, dc) == (-16 * A / 19683, 42 * A / 19683)
        rows.append(dict(case=t, c2_is_b2_over_6=bool(t % 2), b20=str(b20), c20=str(c20), dC8_db70=str(db), dC8_dc70=str(dc)))
    return rows


def _all_slots(order, loops):
    return [(L, ch, j) for L in loops for ch in 'bc' for j in range(order + 1 - L)]


def exact_affinity(order: int, seed: int, route=fixed_point) -> dict:
    """Exact second differences of C_0..C_order vanish for every pair (including repeats) of slots of loops >= 5, at a
    random rational point with random rational steps. Control: some loop-2/3/4 pairs are nonzero."""
    rng = random.Random(seed); b, c = random_general(rng, order); base = route(b, c, order, F(3, 2))
    sl = _all_slots(order, range(5, order + 1)); h = {s: rand_frac(rng) or F(1) for s in sl}
    single = {s: route(*_shift(b, c, *s, h[s]), order, F(3, 2)) for s in sl}
    pairs = 0
    for i, s in enumerate(sl):
        for t in sl[i:]:
            bb, cc = _shift(b, c, *s, h[s]); bb, cc = _shift(bb, cc, *t, h[t])
            both = route(bb, cc, order, F(3, 2))
            sd = [w - x - y + z for w, x, y, z in zip(both, single[s], single[t], base)]
            assert all(v == 0 for v in sd), (s, t, sd)
            pairs += 1
    controls = {}
    pairs_ctl = [((3, 'b', 0), (3, 'b', 0)), ((3, 'b', 0), (4, 'b', 0)), ((4, 'b', 0), (4, 'c', 0)), ((3, 'b', 0), (5, 'c', 0)), ((2, 'b', 0), (6, 'b', 0))]
    if order == 8: pairs_ctl.append(((4, 'b', 0), (5, 'b', 0)))  # 4 x 5 first enters at order 8 (g^4 g^5 ~ eps^9 / eps)
    for s, t in pairs_ctl:
        x = route(*_shift(b, c, *s, F(1)), order, F(3, 2)); y = route(*_shift(b, c, *t, F(1)), order, F(3, 2))
        bb, cc = _shift(b, c, *s, F(1)); w = route(*_shift(bb, cc, *t, F(1)), order, F(3, 2))
        controls[f'{s}x{t}'] = str(w[order] - x[order] - y[order] + base[order])
    assert all(F(v) != 0 for v in controls.values()), controls
    return dict(order=order, loops='5..%d' % order, slots=len(sl), pairs=pairs, all_second_differences_zero=True,
                nonzero_controls_C_order=controls)


# ---------------------------------------------------------------------------------------------------------------
# Constant-coefficient MS polynomials (sympy)

def ms_polynomials(nmax: int = 8):
    """C_n, n = 2..nmax, of eq:Lagrange (N:232) with constant B(g) = 3 + b2 g + ..., gamma_r = g + c2 g^2 + ...
    Returns (general, substituted) dicts of sympy expressions; 'substituted' has b2 = -6A, c2 = -A (N:2273)."""
    import sympy as sp
    g, A = sp.symbols('g A'); b = {L: sp.Symbol(f'b{L}') for L in range(2, nmax + 1)}; c = {L: sp.Symbol(f'c{L}') for L in range(2, nmax + 1)}
    X = sum(b[L] * g ** (L - 1) for L in range(2, nmax + 1)) / 3
    dgam = sp.expand(sp.diff(g + sum(c[L] * g ** L for L in range(2, nmax + 1)), g))
    def trunc(e, G):
        p = sp.Poly(sp.expand(e), g); return sum(coef * g ** m[0] for m, coef in zip(p.monoms(), p.coeffs()) if m[0] <= G)
    general = {}
    for n in range(2, nmax + 1):
        G = n - 1; S = 0; Xm = sp.Integer(1)
        for mm in range(0, G + 1):
            S += (-1) ** mm * sp.binomial(n + mm - 1, mm) * Xm
            Xm = trunc(Xm * X, G)
        general[n] = sp.expand(sp.Poly(trunc(dgam * S, G), g).coeff_monomial(g ** G) / (n * 3 ** n))
    sub = {n: sp.expand(e.subs({b[2]: -6 * A, c[2]: -A})) for n, e in general.items()}
    return general, sub


def _syms():
    import sympy as sp
    names = ['A', 'R', 'Q', 'M', 'N'] + [f'b{L}' for L in range(2, 9)] + [f'c{L}' for L in range(2, 9)]
    return {n: sp.Symbol(n) for n in names}


def parse_poly(text: str):
    """Parse a polynomial written in the recon/RECON plain-text style (implicit products, ^, unicode minus)."""
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication, convert_xor
    t = text.replace('−', '-').replace('\n', ' ')
    t = re.sub(r'([bc][2-8])(?=[bcA])', r'\1 ', t)  # theory.md writes products like b3c3 without a space
    return sp.expand(parse_expr(t, local_dict=_syms(), transformations=standard_transformations + (implicit_multiplication, convert_xor)))


# Verbatim copies (the live files are re-read and compared when present).
C62D_MS8_SOURCE = 'LRI_C8_D2_HPC_loop/RECON.md:91-95 (md5 3bb715b1f748ebbaa6eefc97949b18fa on 2026-10-03)'
C62D_MS8 = """3c8 - b8 + 42A c7 - 16A b7 + 324A^2 c6 - 144A^2 b6 + 3b3 b6 - 6b3 c6 - 3b6 c3
 + 1800A^3 c5 - 960A^3 b5 + 54A b3 b5 - 90A b3 c5 - 54A b5 c3 + 3b4 b5 - 5b4 c5 - 4b5 c4
 + 82368A^7 - 25344A^5 b3 + 28512A^5 c3 - 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2
 - 3960A^3 b3 c3 + 540A^2 b3 b4 - 720A^2 b3 c4 - 540A^2 b4 c3 - (100/3)A b3^3 + 90A b3^2 c3
 + 27A b4^2 - 72A b4 c4 - 5b3^2 b4 + 6b3^2 c4 + 9b3 b4 c3"""
C63D_RECON_SOURCE = 'LRI_C8_D3_HPC_loop/recon/theory.md:263-271 (md5 c16fb42c451e6df7f54dfffd75ea9a88 on 2026-10-03)'
C63D_MS = {8: ("19683", """82368A^7 − 25344A^5 b3 + 28512A^5 c3 − 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2 − 3960A^3 b3c3
       − 960A^3 b5 + 1800A^3 c5 + 540A^2 b3b4 − 720A^2 b3c4 − 540A^2 b4c3 − 144A^2 b6 + 324A^2 c6
       − (100/3)A b3^3 + 90A b3^2 c3 + 54A b3b5 − 90A b3c5 + 27A b4^2 − 72A b4c4 − 54A b5c3 − 16A b7 + 42A c7
       − 5b3^2 b4 + 6b3^2 c4 + 9b3b4c3 + 3b3b6 − 6b3c6 + 3b4b5 − 5b4c5 − 4b5c4 − 3b6c3 + (3c8 − b8)"""),
           7: ("6561", """12672A^6 − 3360A^4 b3 + 4320A^4 c3 − 672A^3 b4 + 1152A^3 c4 + 192A^2 b3^2 − 432A^2 b3c3 − 112A^2 b5
       + 240A^2 c5 + (128/3)A b3b4 − 64A b3c4 − 48A b4c3 − 14A b6 + 36A c6 − (4/3)b3^3 + 4b3^2 c3 + (8/3)b3b5
       − 5b3c5 + (4/3)b4^2 − 4b4c4 − 3b5c3 + (3c7 − b7)"""),
           6: ("2187", """2016A^5 − 448A^3 b3 + 672A^3 c3 − 84A^2 b4 + 168A^2 c4 + (49/3)A b3^2 − 42A b3c3 − 12A b5 + 30A c5
       + (7/3)b3b4 − 4b3c4 − 3b4c3 + (3c6 − b6)""")}
# The note's formulas (plain-text transcriptions; N: = condensed-note line).
NOTE_FORMULAS = {
    'C2 = A/9  [gd:C03, N:2264]': (2, '1/9', 'A', False),
    'C3 = (A^2+R-8Q)/108 with gd:bc3  [gd:C03 N:2265; gd:bc3 N:2273-2275]': (3, '1/108', 'A^2 + R - 8Q', True),
    '243 C4 = 60A^3-8Ab3+18Ac3+3c4-b4  [eq:C4RG, N:250-251]': (4, '1/243', '60A^3 - 8A b3 + 18A c3 + 3c4 - b4', False),
    '243 C4 = D4-51A^3+9AR-48AQ-2AM with gd:bc3  [gd:C4, N:2653-2654]': (4, '1/243', '(3c4 - b4) - 51A^3 + 9A R - 48A Q - 2A M', True),
    '729 C5 = 336A^4-60A^2b3+108A^2c3+b3^2-3b3c3-10Ab4+24Ac4+3c5-b5  [eq:C5RG, N:253-256]':
        (5, '1/729', '336A^4 - 60A^2 b3 + 108A^2 c3 + b3^2 - 3b3 c3 - 10A b4 + 24A c4 + 3c5 - b5', False),
    '729 C5 = D5+10AD4-6Ac4-... with gd:bc3  [gd:C5, N:2655-2660]':
        (5, '1/729', '(3c5 - b5) + 10A(3c4 - b4) - 6A c4 - (5541/16)A^4 - (51/4)A^2 M - 162A^2 Q + (315/8)A^2 R'
                     ' + 6M Q - (3/4)M R + 36Q^2 - 18Q R + (27/16)R^2', True),
    '2187 C6 = c6:RGassembly  [N:7492-7499]':
        (6, '1/2187', '3c6 - b6 + 2016A^5 - 448A^3 b3 + 672A^3 c3 - 84A^2 b4 + 168A^2 c4 + (49/3)A b3^2 - 42A b3 c3'
                      ' - 12A b5 + 30A c5 + (7/3)b3 b4 - 4b3 c4 - 3b4 c3', False),
}
GD_BC3 = {'b3': '6Q + (87/4)A^2 - (9/4)R + M', 'c3': '(7/2)A^2 - (1/2)R + (1/3)M'}  # gd:bc3, N:2273-2275


def live_c62d_ms8():
    """C62d's ms8 as it stands now in LRI_C8_D2_HPC_loop/RECON.md (None if the file is absent)."""
    p = LRI / 'LRI_C8_D2_HPC_loop/RECON.md'
    if not p.exists(): return None, None
    text = p.read_text(); m = re.search(r'```\n19683 C8 = (.*?)\n```', text, re.S)
    return (m.group(1) if m else None), hashlib.md5(text.encode()).hexdigest()


def delivered_ms7():
    """ms7 extracted (not imported) from LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/check_assembly.py:53-55,
    evaluated on sympy symbols with Q = sympy.Rational."""
    import sympy as sp
    p = LRI / 'LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/check_assembly.py'
    if not p.exists(): return None, None
    src = p.read_text(); tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ms7')
    ns = {'Q': sp.Rational}; exec(compile(ast.Module(body=[fn], type_ignores=[]), str(p), 'exec'), ns)
    s = _syms(); b = {L: [s[f'b{L}']] for L in range(3, 8)}; c = {L: [s[f'c{L}']] for L in range(3, 8)}
    return sp.expand(ns['ms7'](s['A'], b, c)), hashlib.md5(src.encode()).hexdigest()


def ms_checks() -> dict:
    """ms_n against the note's C2..C6, the delivered ms7, C63d's recon C6-C8 and C62d's ms8 (symbolic equality)."""
    import sympy as sp
    general, sub = ms_polynomials(8); s = _syms(); out = {}
    bc3 = {s['b3']: parse_poly(GD_BC3['b3']), s['c3']: parse_poly(GD_BC3['c3'])}
    for name, (n, scale, text, with_bc3) in NOTE_FORMULAS.items():
        mine = sub[n].subs(bc3) if with_bc3 else sub[n]
        diff = sp.expand(mine - sp.Rational(scale) * parse_poly(text))
        out[name] = 'equal' if diff == 0 else f'DIFFERENT: {diff}'
    ms7, h7 = delivered_ms7()
    if ms7 is not None:
        d = sp.expand(sub[7] - ms7); out[f'C7 = ms7 of LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/check_assembly.py:53-55 (md5 {h7})'] = 'equal' if d == 0 else f'DIFFERENT: {d}'
    for n, (scale, text) in C63D_MS.items():
        d = sp.expand(sub[n] - parse_poly(text) / int(scale)); out[f'{scale} C{n} of C63d recon {C63D_RECON_SOURCE}'] = 'equal' if d == 0 else f'DIFFERENT: {d}'
    d = sp.expand(sub[8] - parse_poly(C62D_MS8) / 19683); out[f'19683 C8 of C62d {C62D_MS8_SOURCE}'] = 'equal' if d == 0 else f'DIFFERENT: {d}'
    live, hlive = live_c62d_ms8()
    if live is not None:
        d = sp.expand(sub[8] - parse_poly(live) / 19683)
        out[f'19683 C8 of C62d, live file now (md5 {hlive})'] = 'equal' if d == 0 else f'DIFFERENT: {d}'
    p8 = sp.Poly(sp.expand(19683 * sub[8]), *[s[k] for k in s if k not in ('R', 'Q', 'M', 'N', 'b2', 'c2')])
    out['ms8 monomials (A-substituted, times 19683)'] = len(p8.terms())
    out['ms8 monomials (general b2, c2, times 19683)'] = len(sp.Poly(sp.expand(19683 * general[8]), *[s[k] for k in s if k not in ('A', 'R', 'Q', 'M', 'N')]).terms())
    return out


def ms8_text() -> str:
    """19683 ms8 as a sympy string (A-substituted)."""
    import sympy as sp
    _, sub = ms_polynomials(8); return str(sp.expand(19683 * sub[8]))


def constant_jet_checks(cases: int, seed: int) -> list:
    """Both exact routes with z-independent jets reproduce ms_2..ms_8 exactly (general A, b_L, c_L)."""
    import sympy as sp
    _, sub = ms_polynomials(8); s = _syms(); rng = random.Random(seed); rows = []
    for t in range(cases):
        A = F(rng.randint(1, 9), rng.randint(1, 6))
        b = {1: [F(3)], 2: [-6 * A]}; c = {1: [F(1)], 2: [-A]}
        for L in range(3, 9): b[L] = [rand_frac(rng)]; c[L] = [rand_frac(rng)]
        x = fixed_point(b, c, 8, F(3, 2)); y = lagrange(b, c, 8, F(3, 2)); assert x == y
        env = {s['A']: sp.Rational(A.numerator, A.denominator)}
        for L in range(3, 9):
            env[s[f'b{L}']] = sp.Rational(b[L][0].numerator, b[L][0].denominator); env[s[f'c{L}']] = sp.Rational(c[L][0].numerator, c[L][0].denominator)
        for n in range(2, 9):
            v = sub[n].subs(env); assert F(int(v.p), int(v.q)) == x[n], (t, n)
        rows.append(dict(case=t, A=str(A), C8=str(x[8])))
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Power-sector bookkeeping (POWER_PROTOCOL.md section 4)

def power_bookkeeping() -> dict:
    """(i) R8 := 3^9 ms8 - 82368A^7 - (3c8-b8) + 16A b7 - 42A c7 involves loops 3..6 only, so
         3^9 Delta_p = (3c8-b8)^p - 16A b7^p + 42A c7^p + R8(b,c) - R8(b-b^p, c-c^p)   (generalizes N:8693-8700, N:8838-8845);
       (ii) the MS order-4 power difference vanishes identically with the three/four-loop power pieces
         b3^p = M, c3^p = M/3, b4^p = -(11/2)AM - (3/2)MN, c4^p = -(7/6)AM - (1/2)MN  (d3six:lowerPower, N:8846-8851);
         d=2 values b3^p = -4, c3^p = -4/3, b4^p = 16A+24, c4^p = (8/3)A+8 (done:powerSums, N:8705-8713) are this
         formula at M_2 = -4, N_2 = 4 - A (checked numerically at 60 digits);
       (iii) (repair round 2) the MS order-5 power difference is 729 Delta_p[5] = [M(57A^2 + 12AN + 24Q - 3R)
         + 4(3c5 - b5)^p]/4 with lowerPower and gd:bc3 (exact), and at d=2 with done:powerSums (N:8707-8712), Q_2
         (N:2407) and R_2 = 0 it is a numerical zero below the printed-digit resolution of b5^p, c5^p."""
    import sympy as sp, mpmath as mp
    _, sub = ms_polynomials(8); s = _syms(); A = s['A']
    R8 = sp.expand(19683 * sub[8] - 82368 * A ** 7 - (3 * s['c8'] - s['b8']) + 16 * A * s['b7'] - 42 * A * s['c7'])
    free = sorted(str(x) for x in R8.free_symbols)
    assert not ({'b7', 'c7', 'b8', 'c8'} & set(free))
    p = {k: sp.Symbol(k + 'p') for k in [f'{x}{L}' for x in 'bc' for L in range(3, 9)]}
    full = sp.expand(19683 * sub[8]); pf = full.subs({s[k]: s[k] - p[k] for k in p}, simultaneous=True)
    shifted = R8.subs({s[k]: s[k] - p[k] for k in p}, simultaneous=True)
    ident = sp.expand(full - pf - ((3 * p['c8'] - p['b8']) - 16 * A * p['b7'] + 42 * A * p['c7'] + R8 - shifted))
    assert ident == 0
    M, N = s['M'], s['N']
    pw = {'b3': M, 'c3': M / 3, 'b4': -sp.Rational(11, 2) * A * M - sp.Rational(3, 2) * M * N, 'c4': -sp.Rational(7, 6) * A * M - M * N / 2}
    d4 = sp.expand(sub[4] - sub[4].subs({s[k]: s[k] - v for k, v in pw.items()}, simultaneous=True))
    assert d4 == 0
    mp.mp.dps = 60; q = mp.mpf(1) / 2; A2 = 4 * mp.log(2)
    N2 = mp.digamma(-q) + mp.digamma(3 * q) - mp.digamma(1) - mp.digamma(2 * q); M2 = mp.gamma(-q) * mp.gamma(2 * q) ** 2 / mp.gamma(3 * q)
    e1 = abs(M2 + 4); e2 = abs(N2 - (4 - A2)); e3 = abs((-mp.mpf(11) / 2 * A2 * M2 - mp.mpf(3) / 2 * M2 * N2) - (16 * A2 + 24))
    e4 = abs((-mp.mpf(7) / 6 * A2 * M2 - M2 * N2 / 2) - (mp.mpf(8) / 3 * A2 + 8))
    assert max(e1, e2, e3, e4) < mp.mpf('1e-55')
    # (iii) repair round 2: the MS order-5 power difference. With d3six:lowerPower and gd:bc3 (N:2273-2275),
    #   729 Delta_p[5] = [M(57A^2 + 12AN + 24Q - 3R) + 4(3c5 - b5)^p]/4   (sympy identity, any d);
    # at d=2 (done:powerSums N:8707-8712: b3^p..c4^p exact, b5^p and c5^p to 21 digits; Q_2 of gd:d2exact N:2407;
    # R_2 = psi1(1) - psi1(1) = 0; A_2 = 4 log 2) it is a numerical zero, like the order-6 one (N:8714-8719).
    p5 = {k: sp.Symbol(k + 'p') for k in ['b3', 'c3', 'b4', 'c4', 'b5', 'c5']}
    D5 = sp.expand(729 * (sub[5] - sub[5].subs({s[k]: s[k] - p5[k] for k in p5}, simultaneous=True)))
    bc3 = {s['b3']: parse_poly(GD_BC3['b3']), s['c3']: parse_poly(GD_BC3['c3'])}
    Q, R = s['Q'], s['R']
    D5g = sp.expand(D5.subs({p5[k]: v for k, v in pw.items()}).subs(bc3))
    assert sp.expand(D5g - (M * (57 * A ** 2 + 12 * A * N + 24 * Q - 3 * R) + 4 * (3 * p5['c5'] - p5['b5'])) / 4) == 0
    Q2 = (mp.gamma(mp.mpf(1) / 4) / mp.gamma(mp.mpf(3) / 4)) ** 4 / 6; R2 = mp.psi(1, 2 * q) - mp.psi(1, 1)
    b5p, c5p = mp.mpf('-1540.38932947914290838'), mp.mpf('-251.621917341000466476')  # N:8711-8712, as printed
    env = {A: A2, Q: Q2, R: R2, M: M2, N: N2, s['b3']: _gd_bc3_eval(Q2, A2, R2, M2)[0], s['c3']: _gd_bc3_eval(Q2, A2, R2, M2)[1],
           p5['b3']: mp.mpf(-4), p5['c3']: -mp.mpf(4) / 3, p5['b4']: 16 * A2 + 24, p5['c4']: 8 * A2 / 3 + 8, p5['b5']: b5p, p5['c5']: c5p}
    f5 = sp.lambdify(list(env), D5, 'mpmath'); dp5 = f5(*env.values()) / 729
    lower5 = f5(*[(0 if k in (p5['b5'], p5['c5']) else v) for k, v in env.items()]) / 729
    resolution5 = (mp.mpf('1e-17') + 3 * mp.mpf('1e-18')) / 729  # last printed digits of b5^p, c5^p, through (3c5 - b5)^p/729
    assert abs(dp5) < resolution5
    return dict(R8_free_symbols=free, R8_monomials=len(sp.Poly(R8, *[s[k] for k in free]).terms()), bookkeeping_identity='exact (sympy)',
                ms_order4_power_difference='identically zero for any A, M, N', d2_lowerPower_consistency_max_error=mp.nstr(max(e1, e2, e3, e4), 3),
                ms_order5_power_difference='729 Dp5 = [M(57A^2 + 12AN + 24Q - 3R) + 4(3c5 - b5)^p]/4 (with d3six:lowerPower, gd:bc3; exact)',
                d2_order5_power_difference=mp.nstr(dp5, 3), d2_order5_lower_part=mp.nstr(lower5, 25),
                d2_order5_printed_digit_resolution=mp.nstr(resolution5, 3))


def _gd_bc3_eval(Q, A, R, M):
    """gd:bc3 (N:2273-2275) numerically: (b3, c3)."""
    return 6 * Q + A ** 2 * 87 / 4 - R * 9 / 4 + M, A ** 2 * 7 / 2 - R / 2 + M / 3


# ---------------------------------------------------------------------------------------------------------------
# Float comparison (needs order8_assembly; only numpy)

def float_vs_exact(order: int, cases: int, seed: int) -> dict:
    import numpy as np
    # repair round 3: never write __pycache__ next to order8_assembly (this folder is vendored with pinned hashes)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(HERE)); import order8_assembly as oa
    rng = random.Random(seed); worst = 0.0; rows = []
    for t in range(cases):
        vals, B2 = random_inputs(rng, order); half_d = (1, 1.5)[t % 2]
        b, c = from_float_convention(vals, B2, order)
        ex = lagrange(b, c, order, F(half_d)); ex2 = fixed_point(b, c, order, F(half_d)); assert ex == ex2
        fl = oa.coefficients({L: np.array([float(x) for x in v]) for L, v in vals.items()}, np.array([float(x) for x in B2]), order, half_d)
        scale = max(1.0, max(abs(float(x)) for x in ex))
        err = max(abs(fl[n] - float(ex[n])) for n in range(order + 1)) / scale
        worst = max(worst, err); rows.append(dict(case=t, half_d=half_d, C_top=str(ex[order]), max_rel_err=err))
    return dict(order=order, cases=cases, max_relative_error=worst, rows=rows)


def run_all(fast: bool = False) -> dict:
    n8, n7 = (16, 8) if fast else (64, 16)
    res = {'module_md5': hashlib.md5(Path(__file__).read_bytes()).hexdigest()}
    for order, n in ((8, n8), (7, n7)):
        rng = random.Random(80300 + order); eq = 0
        for t in range(n):
            b, c = random_general(rng, order)
            assert lagrange(b, c, order, F(3, 2)) == fixed_point(b, c, order, F(3, 2)); eq += 1
        res[f'route_L_equals_route_F_order{order}'] = eq
    res['float_vs_exact_order8'] = {k: v for k, v in float_vs_exact(8, n8, 8081).items() if k != 'rows'}
    res['float_vs_exact_order7'] = {k: v for k, v in float_vs_exact(7, n7, 7071).items() if k != 'rows'}
    res['top_slot_exact_order8'] = len(exact_top_slot(8, 2 if fast else 4, 3108))
    res['top_slot_exact_order7'] = len(exact_top_slot(7, 2, 3107))
    res['loop7_exact'] = exact_loop7(4 if fast else 8, 7008)
    res['affinity_order8'] = exact_affinity(8, 5508)
    res['affinity_order7'] = exact_affinity(7, 5507)
    res['ms_checks'] = ms_checks()
    res['constant_jets_vs_ms'] = len(constant_jet_checks(4 if fast else 8, 2208))
    res['ms8_19683'] = ms8_text()
    res['power_bookkeeping'] = power_bookkeeping()
    return res


if __name__ == '__main__':
    import time
    t0 = time.time(); r = run_all(fast='--fast' in sys.argv)
    if '--write' in sys.argv: (HERE / 'exact_check_results.json').write_text(json.dumps(r, indent=1) + '\n')  # deterministic: no timing
    print(json.dumps(r, indent=1)); print(f'all exact checks passed in {time.time() - t0:.1f} s', file=sys.stderr)
