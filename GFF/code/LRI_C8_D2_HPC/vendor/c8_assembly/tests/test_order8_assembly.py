#!/usr/bin/env python3
"""Tests for LRI_C8_shared/assembly (items 1-4 of the C63d assembly task). pytest, or plain `python3 <this file>`.

Tests that need the delivered C7 packages or the C7 production data skip when those directories are absent (for
example in a vendored copy on a cluster); set LRI_ROOT to the Agent_LRI directory to point at them.
"""
from __future__ import annotations
import hashlib, json, math, os, random, sys, types
from fractions import Fraction as F
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True  # never write __pycache__ next to the delivered packages
HERE = Path(__file__).resolve().parents[1]
LRI = Path(os.environ.get('LRI_ROOT', HERE.parents[1]))
sys.path.insert(0, str(HERE))
import order8_assembly as oa  # noqa: E402
import exact_check as ec  # noqa: E402
import prepare_low8 as pl  # noqa: E402

try:
    import pytest
    skip = pytest.skip
except ImportError:  # plain-python fallback
    class _Skip(Exception): pass
    def skip(msg): raise _Skip(msg)

D3_ASSEMBLE = LRI / 'LRI_C7_D3_HPC/tools/assemble.py'
D2_ASSEMBLE = LRI / 'LRI_C7_D2_HPC/tools/assemble.py'
D3_RUN = LRI / 'LRI_C7_D3_HPC_production/results_run1-20260930-m4096'
D2_RUN = LRI / 'LRI_C7_D2_HPC_production/symmetry/c7-d2/run1-20260930-m4096'
# The delivered files these regressions were established against (2026-10-03).
PINNED_MD5 = {D3_ASSEMBLE: 'd230ee036ed7f3dc6663cdda512af051', D2_ASSEMBLE: 'f8f5ccf7e2835c9d590e2bdac82ba528'}
PUBLISHED = {3: -220.35448047392794, 2: -3876.1260927949925}  # C7_full of the two production C7_result.json


def need(*paths):
    for p in paths:
        if not Path(p).exists(): skip(f'{p} not present')


def load_delivered(path: Path) -> dict:
    """Execute a delivered assemble.py from its source (no import, so no bytecode is written into the package) with a
    stub `common` (ROOT, load, canon); returns its namespace."""
    src = path.read_text()
    common = types.ModuleType('common'); common.ROOT = path.parents[1]; common.load = lambda p: json.loads(Path(p).read_text())
    common.canon = lambda o: json.dumps(o, sort_keys=True, separators=(',', ':'), allow_nan=False); common.digest = common.dump = None
    saved = sys.modules.get('common'); sys.modules['common'] = common
    ns = {'__name__': 'delivered_' + path.parents[1].name, '__file__': str(path)}
    try: exec(compile(src, str(path), 'exec'), ns)
    finally:
        if saved is None: sys.modules.pop('common', None)
        else: sys.modules['common'] = saved
    return ns


_CACHE = {}
def delivered(d):
    path = D3_ASSEMBLE if d == 3 else D2_ASSEMBLE; need(path)
    if d not in _CACHE: _CACHE[d] = load_delivered(path)
    return _CACHE[d]


def delivered_coeffs(d, vals, B2):
    ns = delivered(d); return ns['coefficients'](vals, B2) if d == 3 else ns['coefficients'](vals)


def delivered_jac(d, vals, B2):
    ns = delivered(d); return ns['jacobians'](vals, B2) if d == 3 else ns['jacobians'](vals)


def b2_c7(d):
    """The B2 each delivered function uses: D3 passes it in (inputs/two_loop.json), D2 holds a module global."""
    if d == 2: return delivered(2)['B2']
    need(LRI / 'LRI_C7_D3_HPC/inputs/two_loop.json')
    return np.asarray(json.loads((LRI / 'LRI_C7_D3_HPC/inputs/two_loop.json').read_text())['B2'], float)


def merged(run: Path) -> dict:
    """ar[sector][campaign][L] from groups/*/merged.json, in the delivered load_campaign order (free, power; a, b)."""
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
    for g in sorted((run / 'groups').iterdir()):
        t, s, L = g.name.split('_'); d = json.loads((g / 'merged.json').read_text())
        ar[s][t][int(L[1:])] = np.asarray(d['batches'], float)
    return ar


def b2_order8(d):
    p = HERE / ('inputs_d3' if d == 3 else 'inputs_d2_check') / 'two_loop.json'
    return np.asarray(json.loads(p.read_text())['B2'], float)


# --------------------------------------------------------------------------------------------------------------
# Item 1: order-7 bitwise regressions

def test_delivered_sources_pinned():
    for p, h in PINNED_MD5.items():
        need(p); assert hashlib.md5(p.read_bytes()).hexdigest() == h, f'{p} changed since the regressions were established'


def test_order7_bitwise_random():
    rng = np.random.default_rng(20261003)
    for d, hd in ((3, 1.5), (2, 1)):
        B2 = b2_c7(d)
        for t in range(150):
            vals = {L: rng.normal(size=2 * (8 - L)) * 10 ** rng.uniform(-4, 4) for L in range(3, 8)}
            if t % 3 == 0: vals = {L: v + 1j * rng.normal(size=v.shape) * 1e-3 for L, v in vals.items()}
            if t % 5 == 0: vals = {L: v for L, v in vals.items() if L <= 3 + t % 5 + 2}  # prefix plans (missing loops)
            ref = delivered_coeffs(d, vals, B2); mine = oa.coefficients(vals, B2, 7, hd)
            assert ref.dtype == mine.dtype and ref.tobytes() == mine.tobytes()
            if t % 10 == 0:
                Jr = delivered_jac(d, vals, B2); Jm = oa.jacobians(vals, B2, 7, hd)
                assert all(Jr[L].tobytes() == Jm[L].tobytes() for L in Jr)
        # a 7-entry B2 (the order-8 input) is truncated: bit-identical to its 6-entry prefix at order 7
        B2_8 = b2_order8(d)
        assert np.array_equal(B2_8[:6], B2)
        vals = {L: rng.normal(size=2 * (8 - L)) for L in range(3, 8)}
        assert oa.coefficients(vals, B2_8, 7, hd).tobytes() == oa.coefficients(vals, B2, 7, hd).tobytes() == delivered_coeffs(d, vals, B2).tobytes()


def _production(d):
    run = D3_RUN if d == 3 else D2_RUN; need(run / 'C7_result.json'); return run, json.loads((run / 'C7_result.json').read_text())


def test_order7_production_reassembly():
    for d, hd in ((3, 1.5), (2, 1)):
        run, res = _production(d); B2 = b2_c7(d); ar = merged(run)
        means, vc = oa.campaign_moments(ar, range(3, 8))
        pub = {s: {int(L): np.asarray(v, float) for L, v in res['means'][s].items()} for s in res['means']}
        assert all(np.array_equal(means[s][L], pub[s][L]) for s in means for L in means[s])  # published means, bit for bit
        m = {L: pub['free'][L] + pub['power'][L] for L in range(3, 8)}
        mine = oa.coefficients(m, B2, 7, hd); ref = delivered_coeffs(d, m, B2)
        assert mine.tobytes() == ref.tobytes()
        assert mine[7] == res['C7_full'] or abs(mine[7] - res['C7_full']) <= 8 * np.spacing(abs(res['C7_full']))
        assert res['C7_full'] == PUBLISHED[d]
        # the complete delivered assembly (bootstrap off) against sector_assembly, bit for bit
        ns = delivered(d)
        full = ns['calculate'](ar, None, 0, B2) if d == 3 else ns['combine'](ar, None, 0)
        r = oa.sector_assembly(means, vc, B2, 7, hd)
        for key in ('coefficients', 'standard_errors', 'covariance', 'power_differences', 'power_difference_errors'):
            assert np.asarray(full[key]).tobytes() == np.asarray(r[key]).tobytes(), key
        assert full['power_free_C7'] == r['power_free_coefficients'][7]
        # against the published (symmetry-built) result: CPU-dependent last bits only
        # (power_differences = mu - pf is judged on the scale of mu: its last bits come from two O(|C7|) numbers)
        for key, sk in (('coefficients', 'coefficients'), ('standard_errors', 'standard_errors'), ('power_differences', 'coefficients'),
                        ('power_difference_errors', 'power_difference_errors')):
            a, b = np.asarray(res[key]), np.asarray(r[key]); scale = np.max(np.abs(np.asarray(res[sk])))
            assert np.max(np.abs(a - b)) <= 1e-12 * scale, key


def test_order8_reduces_to_order7():
    """C_0..C_7 of the order-8 assembly equal the order-7 assembly up to rounding (top slots do not feed lower orders)."""
    rng = np.random.default_rng(8)
    for d, hd in ((3, 1.5), (2, 1)):
        B2 = b2_order8(d)
        for _ in range(20):
            v8 = {L: rng.normal(size=2 * (9 - L)) for L in range(3, 9)}
            v7 = {L: np.concatenate([v[:8 - L], v[9 - L:2 * (9 - L) - 1]]) for L, v in v8.items() if L <= 7}
            c8, c7 = oa.coefficients(v8, B2, 8, hd), oa.coefficients(v7, B2, 7, hd)
            assert np.allclose(c8[:8], c7, rtol=1e-13, atol=1e-13 * np.max(np.abs(c7)))


# --------------------------------------------------------------------------------------------------------------
# Item 2: independent exact-rational inversion

def test_exact_routes_agree():
    for order, n in ((8, 64), (7, 16)):
        rng = random.Random(80300 + order)
        for _ in range(n):
            b, c = ec.random_general(rng, order)
            assert ec.lagrange(b, c, order, F(3, 2)) == ec.fixed_point(b, c, order, F(3, 2))


def test_float_vs_exact():
    for order, n in ((8, 64), (7, 16)):
        r = ec.float_vs_exact(order, n, 8000 + order)
        assert r['max_relative_error'] < 1e-13, r['max_relative_error']


def test_ms_polynomials():
    """The note's C2..C6 formulas, C63d's recon C6..C8 and the embedded copy of C62d's ms8: no external file needed."""
    out = ec.ms_checks()
    bad = {k: v for k, v in out.items() if isinstance(v, str) and v != 'equal'}
    assert not bad, bad
    assert out['ms8 monomials (A-substituted, times 19683)'] == 34 and out['ms8 monomials (general b2, c2, times 19683)'] == 45
    assert sum(k.startswith('19683 C8 of C62d LRI_C8_D2_HPC_loop') for k in out) == 1  # the embedded copy
    assert [out[k] for k in ec.NOTE_FORMULAS] == ['equal'] * 7  # the note's C2..C6 formulas


def test_ms_polynomials_against_delivered_files():
    """The delivered ms7 and the live C62d RECON.md (skips when they are absent, e.g. in a vendored copy)."""
    need(LRI / 'LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/check_assembly.py', LRI / 'LRI_C8_D2_HPC_loop/RECON.md')
    out = ec.ms_checks()
    ms7 = [v for k, v in out.items() if 'ms7' in k]; live = [v for k, v in out.items() if 'live file' in k]
    assert ms7 == ['equal'] and live == ['equal'], (ms7, live)


def test_constant_jets_reproduce_ms():
    assert len(ec.constant_jet_checks(8, 2208)) == 8


def test_fraction_mode_equals_exact_lagrange():
    """coefficients() in object/Fraction mode (the PLAN.md:446-448 interface) is exact: it equals the independent
    Lagrange route exactly, at orders 7 and 8, with half_d as int, float or Fraction, B2 as a list or object array,
    and for prefix plans (missing loops). The float path is unaffected: a string B2 still reads as float."""
    rng = random.Random(4466)
    for order, n in ((8, 24), (7, 12)):
        for t in range(n):
            vals, B2 = ec.random_inputs(rng, order); hd = (1, 1.5, F(3, 2), F(1))[t % 4]
            if t % 6 == 5: vals = {L: v for L, v in vals.items() if L <= 3 + t % 4}  # prefix plan
            b, c = ec.from_float_convention(vals, B2, order)
            want = ec.lagrange(b, c, order, F(hd))
            v = {L: (np.array(x, dtype=object) if t % 2 else list(x)) for L, x in vals.items()}
            got = oa.coefficients(v, B2 if t % 3 else np.array(B2, dtype=object), order, hd)
            assert got.dtype == object and all(type(x) is F for x in got) and list(got) == want, (order, t)
    # exact mode is entered by rational B2 entries alone (float vals then count by their exact binary values)
    vals, B2 = ec.random_inputs(rng, 8); fv = {L: np.array([float(x) for x in v]) for L, v in vals.items()}
    got = oa.coefficients(fv, B2, 8, F(3, 2)); b, c = ec.from_float_convention({L: [F(x) for x in v] for L, v in fv.items()}, B2, 8)
    assert list(got) == ec.lagrange(b, c, 8, F(3, 2))
    # float path: Fraction half_d is read as float; string B2 as float (bitwise as before)
    B2s = json.loads((HERE / 'inputs_d3/two_loop.json').read_text())['B2']; vr = {L: np.random.default_rng(L).normal(size=2 * (9 - L)) for L in range(3, 9)}
    ref = oa.coefficients(vr, np.asarray(B2s, float), 8, 1.5)
    for B2x, hd in ((B2s, 1.5), (np.asarray(B2s), F(3, 2)), (np.asarray(B2s, dtype=object), 1.5)):
        out = oa.coefficients(vr, B2x, 8, hd); assert out.dtype == np.float64 and out.tobytes() == ref.tobytes()
    try: oa.coefficients(vr, B2s, 8, True)
    except ValueError: pass
    else: raise AssertionError('bool half_d accepted')


def test_ms8_rows_table():
    """ms8_rows (the fixed table in order8_assembly) equals the sympy derivation of exact_check (A-substituted and
    general b2, c2) and the embedded C62d polynomial; coefficients() in Fractions equals ms8_value exactly in the
    constant-coefficient case (16 random rational cases, b_2 = -6A, c_2 = -A, only slot 0 nonzero)."""
    import sympy as sp
    general, sub = ec.ms_polynomials(8); s = ec._syms()
    def table(general_):
        return sp.expand(sum(sp.Rational(co.numerator, co.denominator) * sp.Mul(*[s[k] ** p for k, p in m.items()])
                             for co, m in oa.ms8_rows(general_)))
    assert sp.expand(table(False) - 19683 * sub[8]) == 0 and len(oa.ms8_rows()) == 34
    assert sp.expand(table(True) - 19683 * general[8]) == 0 and len(oa.ms8_rows(True)) == 45
    assert sp.expand(table(False) - ec.parse_poly(ec.C62D_MS8)) == 0
    rng = random.Random(1683)
    for _ in range(16):
        A = F(rng.randint(1, 9), rng.randint(1, 6)); env = {'A': A}; vals = {}
        for L in range(3, 9):
            bL, cL = ec.rand_frac(rng), ec.rand_frac(rng); k = 9 - L; env[f'b{L}'], env[f'c{L}'] = bL, cL
            vals[L] = np.array([bL] + [F(0)] * (k - 1) + [cL] + [F(0)] * (k - 1), dtype=object)
        C = oa.coefficients(vals, [-6 * A] + [F(0)] * 6, 8, F(3, 2))
        assert C[8] == oa.ms8_value(env)
        genv = dict(env, b2=-6 * A, c2=-A); del genv['A']; assert oa.ms8_value(genv, general=True) == C[8]


def test_float_constant_jets_vs_ms8():
    import sympy as sp
    _, sub = ec.ms_polynomials(8); s = ec._syms(); rng = random.Random(4)
    for _ in range(6):
        A = F(rng.randint(1, 9), rng.randint(1, 6)); B2 = [float(-6 * A)] + [0.0] * 6
        vals = {}; env = {s['A']: sp.Rational(A.numerator, A.denominator)}
        for L in range(3, 9):
            bL, cL = ec.rand_frac(rng), ec.rand_frac(rng); k = 9 - L
            vals[L] = np.array([float(bL)] + [0.0] * (k - 1) + [float(cL)] + [0.0] * (k - 1))
            env[s[f'b{L}']] = sp.Rational(bL.numerator, bL.denominator); env[s[f'c{L}']] = sp.Rational(cL.numerator, cL.denominator)
        c = oa.coefficients(vals, B2, 8, 1.5)
        want = [float(sub[n].subs(env)) for n in range(2, 9)]
        assert np.allclose(c[2:], want, rtol=1e-12, atol=1e-12 * max(map(abs, want)))


# --------------------------------------------------------------------------------------------------------------
# Item 3: gates

def test_top_slot_exact():
    assert len(ec.exact_top_slot(8, 4, 3108)) == 4 * 7 and len(ec.exact_top_slot(7, 2, 3107)) == 2 * 6


def test_top_slot_float_gate():
    rng = np.random.default_rng(31)
    for d, hd in ((3, 1.5), (2, 1)):
        B2 = b2_order8(d)
        for order in (8, 7):
            for _ in range(3):
                v = {L: rng.normal(size=2 * (order + 1 - L)) * 10 for L in range(3, order + 1)}
                g = oa.top_slot_gate(oa.jacobians(v, B2, order, hd), order)
                assert [r['L'] for r in g['rows']] == list(range(3, order + 1))
    # negative control: a corrupted Jacobian fails hard
    v = {L: rng.normal(size=2 * (9 - L)) for L in range(3, 9)}; J = oa.jacobians(v, b2_order8(3), 8, 1.5); J[5][8, 3] *= 1 + 1e-9
    try: oa.top_slot_gate(J, 8)
    except ArithmeticError: pass
    else: raise AssertionError('corrupted Jacobian passed the top-slot gate')


def test_b2_top_slot_float():
    """Loop 2 top slot (B2 z^6, with c2 = B2/6): dC8/db_{2,6} = -1/27 + 3/(6*27) = -1/54."""
    B2 = b2_order8(3).astype(complex); B2[6] += 1e-20j
    v = {L: np.random.default_rng(L).normal(size=2 * (9 - L)) for L in range(3, 9)}
    c = oa.coefficients(v, B2, 8, 1.5)
    assert abs(c.imag[8] / 1e-20 + 1 / 54) < 1e-15 and not c.imag[:8].any()


def test_loop7_gate_and_A_d():
    import mpmath as mp
    with mp.workdps(60):
        Ad = lambda d: mp.digamma(mp.mpf(d) / 2) + mp.digamma(1) - 2 * mp.digamma(mp.mpf(d) / 4)  # gd:blocks, N:2247
        assert abs(Ad(3) - (2 + 4 * mp.log(2) - mp.pi)) < mp.mpf('1e-55')  # N:8781
        assert abs(Ad(2) - 4 * mp.log(2)) < mp.mpf('1e-55')  # N:7822
        for d in (3, 2):
            b20 = json.loads((HERE / ('inputs_d3' if d == 3 else 'inputs_d2_check') / 'two_loop.json').read_text())['B2'][0]
            assert abs(-mp.mpf(b20) / 6 - Ad(d)) < mp.mpf('1e-55')  # b_{2,0} = -6 A_d (gd:bc3, N:2273)
    rng = np.random.default_rng(7)
    for d, hd, A in ((3, 1.5, 2 + 4 * math.log(2) - math.pi), (2, 1, 4 * math.log(2))):
        B2 = b2_order8(d)
        for _ in range(3):
            v = {L: rng.normal(size=2 * (9 - L)) * 10 for L in range(3, 9)}
            g = oa.loop7_gate(oa.jacobians(v, B2, 8, hd), B2, 8)
            assert abs(g['A_d'] - A) < 1e-14 and abs(g['ratio_c_over_b'] + 42 / 16) < 1e-12
    assert len(ec.exact_loop7(8, 7008)) == 8


def test_affinity_exact():
    for order in (8, 7):
        r = ec.exact_affinity(order, 5500 + order)
        assert r['all_second_differences_zero'] and r['pairs'] == {8: 210, 7: 78}[order]


def test_affinity_gate():
    """affinity_gate: float mode (Jacobians of loops 5..order unchanged when those jets move) at both d and orders,
    exact mode (Fraction second differences over all slot pairs of loops 5..8), and negative controls: perturbing
    loop 4 does move J_5 (so the gate must not perturb loops < 5), and an injected nonlinearity fails hard."""
    rng = np.random.default_rng(55)
    for d, hd in ((3, 1.5), (2, 1)):
        B2 = b2_order8(d)
        for order in (8, 7):
            v = {L: rng.normal(size=2 * (order + 1 - L)) * 10 ** rng.uniform(0, 4) for L in range(3, order + 1)}
            g = oa.affinity_gate(v, B2, order, hd)
            assert g['mode'] == 'float' and [r['L'] for r in g['rows']] == list(range(5, order + 1))
            assert all(r['rel_deviation'] <= 1e-10 for r in g['rows'])
    vals, B2 = ec.random_inputs(random.Random(58), 8)
    g = oa.affinity_gate({L: np.array(x, dtype=object) for L, x in vals.items()}, B2, 8, F(3, 2))
    assert g['mode'] == 'exact' and g['pairs'] == 210 and g['all_second_differences_zero']
    # control: loop 4 is not affine-separated from loop 5 (exact control (4,5) at order 8)
    B2 = b2_order8(3); v = {L: rng.normal(size=2 * (9 - L)) for L in range(3, 9)}
    J0 = oa.jacobians(v, B2, 8, 1.5); w = dict(v); w[4] = v[4] + 1.0; J1 = oa.jacobians(w, B2, 8, 1.5)
    assert np.max(np.abs(J1[5] - J0[5])) > 1e-6 * np.max(np.abs(J0[5]))
    try: oa.affinity_gate(v, B2, 8, 1.5, loops=[4, 5])
    except ArithmeticError: pass
    else: raise AssertionError('the gate did not see loop 4 nonlinearity')
    # injected violation: C8 gains 1e-3 b_{5,0}^2 (a monkeypatched coefficients, as in C62d's A-ASM-4)
    orig = oa.coefficients
    def bad(vals_, B2_, order_, hd_):
        out = orig(vals_, B2_, order_, hd_)
        if 5 in vals_: out = out.copy(); out[order_] = out[order_] + 1e-3 * np.asarray(vals_[5])[0] ** 2
        return out
    oa.coefficients = bad
    try:
        for m in (v, {L: np.array(x, dtype=object) for L, x in vals.items()}):
            try: oa.affinity_gate(m, B2, 8, F(3, 2))
            except ArithmeticError: pass
            else: raise AssertionError('injected nonlinearity passed the affinity gate')
    finally:
        oa.coefficients = orig


def test_rational_b2_guards():
    """Repair round 2. A rational B2 puts coefficients() in exact mode, where a complex step is lost (object .imag = 0).
    jacobians() and sector_assembly() refuse it (ValueError); affinity_gate() then runs in exact mode, also for float
    means, and still catches an injected nonlinearity; the float gate refuses an identically zero J_L; loop7_gate reads
    A_d from a Fraction b_{2,0}. Float-path results are unchanged (tobytes)."""
    vals, B2 = ec.random_inputs(random.Random(58), 8); B2f = [float(x) for x in B2]
    rng = np.random.default_rng(3)
    fv = {L: np.round(rng.normal(size=2 * (9 - L)) * 8) / 8 for L in range(3, 9)}  # float means (dyadic: fast exact mode)
    for B2x in (B2, np.array(B2, dtype=object), np.array([int(round(x)) for x in B2f], dtype=object)):
        try: oa.jacobians(fv, B2x, 8, 1.5)
        except ValueError: pass
        else: raise AssertionError('jacobians accepted a rational B2')
    B2c = np.asarray(B2f, complex); B2c[3] += 1e-20j
    try: oa.jacobians(fv, B2c, 8, 1.5)
    except ValueError: pass
    else: raise AssertionError('jacobians accepted a complex B2 with a nonzero imaginary part')
    J = oa.jacobians(fv, B2f, 8, 1.5)  # float B2 (a list of floats) is the delivered path
    assert all(J[L].tobytes() == oa.jacobians(fv, np.asarray(B2f), 8, 1.5)[L].tobytes() for L in J)
    assert all(np.array_equal(oa.jacobians({L: [F(x) for x in v] for L, v in fv.items()}, B2f, 8, 1.5)[L], J[L]) for L in J)
    assert oa.loop7_gate(J, B2, 8)['A_d'] == oa.loop7_gate(J, B2f, 8)['A_d']
    vc = {s: {L: np.eye(len(v)) for L, v in fv.items()} for s in ('free', 'power')}
    try: oa.sector_assembly({'free': fv, 'power': fv}, vc, B2, 8, 1.5)
    except ValueError: pass
    else: raise AssertionError('sector_assembly accepted a rational B2')
    g = oa.affinity_gate(fv, B2, 8, F(3, 2))  # float means, Fraction B2: exact mode
    assert g['mode'] == 'exact' and g['pairs'] == 210 and g['all_second_differences_zero']
    orig_c, orig_j = oa.coefficients, oa.jacobians
    def bad(vals_, B2_, order_, hd_):
        out = orig_c(vals_, B2_, order_, hd_)
        if 5 in vals_: out = out.copy(); out[order_] = out[order_] + 1e-3 * np.asarray(vals_[5])[0] ** 2
        return out
    try:
        oa.coefficients = bad  # the verifiers' negative control: float means, Fraction B2, injected 1e-3 b50^2
        try: oa.affinity_gate(fv, B2, 8, F(3, 2))
        except ArithmeticError: pass
        else: raise AssertionError('injected nonlinearity passed the affinity gate (float means, Fraction B2)')
        oa.coefficients = orig_c
        oa.jacobians = lambda m, *a: {L: np.zeros((9, len(v))) for L, v in m.items()}  # zero Jacobians must fail
        try: oa.affinity_gate(fv, B2f, 8, 1.5)
        except ArithmeticError: pass
        else: raise AssertionError('identically zero Jacobians passed the float affinity gate')
    finally:
        oa.coefficients, oa.jacobians = orig_c, orig_j


def test_campaign_moments_requires_two_campaigns():
    """Repair round 2: the fixed weights 1/2 and 1/4 need exactly the campaigns {'a', 'b'} in both sectors (as in the
    delivered wrappers); one or three campaigns, a missing sector or loop, or mismatched loop keys raise ValueError.
    The two-campaign result is the explicit equal-weight formula."""
    rng = np.random.default_rng(12); loops = range(3, 9)
    ar = {s: {t: {L: rng.normal(size=(5, 2 * (9 - L))) for L in loops} for t in 'ab'} for s in ('free', 'power')}
    means, vc = oa.campaign_moments(ar, loops)
    for s in ar:
        for L in loops:
            assert np.allclose(means[s][L], (ar[s]['a'][L].mean(0) + ar[s]['b'][L].mean(0)) / 2, rtol=1e-15, atol=1e-15)
            want = (np.cov(ar[s]['a'][L], rowvar=False) / 5 + np.cov(ar[s]['b'][L], rowvar=False) / 5) / 4
            assert np.allclose(vc[s][L], want, rtol=1e-14, atol=1e-16)
    bads = [{s: {'a': ar[s]['a']} for s in ar},                                   # one campaign (means would be halved)
            {s: dict(ar[s], c=ar[s]['a']) for s in ar},                           # three campaigns (means x 1.5)
            {'free': ar['free']},                                                 # missing sector
            {s: {t: {L: x for L, x in ar[s][t].items() if L != 6} for t in 'ab'} for s in ar},  # missing loop
            {s: {t: {**ar[s][t], 3: ar[s][t][3][:1]} for t in 'ab'} for s in ar}]                # one replicate
    for b in bads:
        try: oa.campaign_moments(b, loops)
        except ValueError: pass
        else: raise AssertionError(f'campaign_moments accepted {[(s, sorted(b[s])) for s in b]}')
    B2 = b2_order8(3)
    bad_vc = {'free': {L: v for L, v in vc['free'].items() if L != 8}, 'power': vc['power']}
    try: oa.sector_assembly(means, bad_vc, B2, 8, 1.5)
    except ValueError: pass
    else: raise AssertionError('sector_assembly accepted mismatched vc loop keys')
    r = oa.sector_assembly(means, vc, B2, 8, 1.5); assert np.isfinite(r['standard_errors']).all()


def _ar(rng, order, K, n=5, sectors=('free', 'power')):
    return {s: {t: {L: rng.normal(size=(n, 2 * (order + 1 - L))) for L in range(3, K + 1)} for t in 'ab'} for s in sectors}


def test_loop_set_rule_and_sector_order():
    """Repair round 3. campaign_moments and sector_assembly apply the delivered loop-set rule (loops exactly 3..K,
    5 <= K <= order; LRI_C7_D3_HPC/tools/assemble.py:81-82): an extra loop in `ar` (order-8 data with
    loops=range(3, 8)), a non-contiguous set, K < 5 or K > order raise ValueError instead of being dropped or counted as
    zero. The helpers compose for any key order of sectors and loops (results pickle-identical to the free-first,
    ascending case), and a prefix plan K < order reports orders 0..K only, with max_order = K."""
    import pickle
    rng = np.random.default_rng(31003); B2 = b2_order8(3)
    ar = _ar(rng, 8, 8); means, vc = oa.campaign_moments(ar, range(3, 9)); full = oa.sector_assembly(means, vc, B2, 8, 1.5)
    assert full['max_order'] == 8 and full['loops'] == list(range(3, 9)) and len(full['coefficients']) == 9
    def refused(f, *a):
        try: f(*a)
        except ValueError: return True
        return False
    # the verifiers' loopset.py case: order-8 data, loops 3..7 requested -> loop 8 was silently dropped (C8 8.218 vs 8.219)
    assert refused(oa.campaign_moments, ar, range(3, 8))
    ar7 = _ar(rng, 7, 7)
    for bad_loops in ((3, 4, 6), (3, 4), range(3, 10), [3, 4, 5, 5, 6, 7], [True, 4, 5, 6, 7], ['3', '4', '5', '6', '7'], []):
        assert refused(oa.campaign_moments, ar7, bad_loops), bad_loops
    ar_nc = {s: {t: {L: ar7[s][t][L] for L in (3, 4, 6)} for t in 'ab'} for s in ar7}
    assert refused(oa.campaign_moments, ar_nc, (3, 4, 6))          # D3 delivered refuses {3,4,6} too
    ar_x = {s: {t: {**ar7[s][t], 9: np.zeros((5, 2))} for t in 'ab'} for s in ar7}
    assert refused(oa.campaign_moments, ar_x, range(3, 8))         # extra loop in one campaign set
    ar_b = {s: {t: (ar7[s][t] if t == 'a' else {L: x for L, x in ar7[s][t].items() if L != 7}) for t in 'ab'} for s in ar7}
    assert refused(oa.campaign_moments, ar_b, range(3, 8))         # campaigns with different K
    m7, v7 = oa.campaign_moments(ar7, range(3, 8))
    nc_m = {s: {L: m7[s][L] for L in (3, 4, 6)} for s in m7}; nc_v = {s: {L: v7[s][L] for L in (3, 4, 6)} for s in v7}
    assert refused(oa.sector_assembly, nc_m, nc_v, B2, 7, 1.5)    # was accepted, C7 = 3.197 in the verifiers' probe
    assert refused(oa.sector_assembly, means, vc, B2, 7, 1.5)     # K = 8 > order 7
    # any key order composes: power-first ar, permuted loops, permuted dict keys -> identical results
    ar_pf = {'power': {'b': ar['power']['b'], 'a': ar['power']['a']}, 'free': ar['free']}
    mp, vp = oa.campaign_moments(ar_pf, [8, 3, 6, 4, 7, 5])
    assert list(mp) == list(vp) == ['free', 'power'] and all(list(mp[s]) == list(range(3, 9)) for s in mp)
    assert pickle.dumps((mp, vp)) == pickle.dumps((means, vc))
    rev = lambda d: {s: {L: d[s][L] for L in reversed(list(d[s]))} for s in reversed(list(d))}
    r = oa.sector_assembly(rev(means), rev(vc), B2, 8, 1.5)
    assert pickle.dumps(r) == pickle.dumps(full)
    # prefix plan at order 8 (K = 6): orders 0..6 only, the same bits as the full-length computation
    ar6 = _ar(rng, 8, 6); m6, v6 = oa.campaign_moments(ar6, range(3, 7)); r6 = oa.sector_assembly(m6, v6, B2, 8, 1.5)
    assert r6['max_order'] == 6 and r6['loops'] == [3, 4, 5, 6]
    for key in ('coefficients', 'power_free_coefficients', 'power_differences', 'standard_errors', 'power_difference_errors', 'power_free_standard_errors'):
        assert r6[key].shape == (7,), key
    for key in ('covariance', 'power_difference_covariance', 'power_free_covariance', 'cross'): assert r6[key].shape == (7, 7), key
    assert all(r6['J'][L].shape[0] == r6['Jf'][L].shape[0] == 7 for L in r6['J'])
    assert all(v.shape == (7, 7) for d in r6['contributions'].values() for v in d.values())
    msum = {L: m6['free'][L] + m6['power'][L] for L in range(3, 7)}
    assert r6['coefficients'].tobytes() == oa.coefficients(msum, B2, 8, 1.5)[:7].tobytes()


def test_prefix_plans_against_delivered_d3():
    """Repair round 3: at order 7 the prefix plans K = 5 and 6 equal the delivered D3 calculate (bootstrap off),
    which reports orders 0..K only (LRI_C7_D3_HPC/tools/assemble.py:124-133), bit for bit; K = 7 has max_order 7."""
    ns = delivered(3); B2 = b2_c7(3); rng = np.random.default_rng(5671)
    for K in (5, 6, 7):
        ar = _ar(rng, 7, K, n=6); full = ns['calculate'](ar, None, 0, B2)
        means, vc = oa.campaign_moments(ar, range(3, K + 1)); r = oa.sector_assembly(means, vc, B2, 7, 1.5)
        assert r['max_order'] == K == full['max_order']
        for key in ('coefficients', 'standard_errors', 'covariance', 'power_differences', 'power_difference_errors',
                    'power_free_coefficients', 'power_free_standard_errors'):
            assert np.asarray(full[key]).tobytes() == np.asarray(r[key]).tobytes(), (K, key)


def test_b2_int_inputs_documented_mode():
    """Repair round 3 (documentation): exact mode needs B2 with object dtype holding an int or Fraction. A plain list
    or array of ints is int64 and takes the float path: float64 output, bit-identical to the same B2 as floats,
    _b2_holds_rational False, accepted by jacobians(), affinity_gate in float mode. An object array of ints, or a list
    holding a Fraction, is exact mode (Fractions out; jacobians() refuses it)."""
    rng = np.random.default_rng(1); fv = {L: rng.normal(size=2 * (9 - L)) for L in range(3, 9)}
    Bi = [-10, 13, 0, 0, 0, 0, 0]
    for B in (Bi, np.array(Bi), np.array(Bi, dtype=np.int32)):
        c = oa.coefficients(fv, B, 8, F(3, 2))
        assert c.dtype == np.float64 and c.tobytes() == oa.coefficients(fv, [float(x) for x in Bi], 8, 1.5).tobytes()
        assert not oa._b2_holds_rational(B, 8)
        J = oa.jacobians(fv, B, 8, 1.5); Jf = oa.jacobians(fv, [float(x) for x in Bi], 8, 1.5)
        assert all(J[L].tobytes() == Jf[L].tobytes() for L in J)
        assert oa.affinity_gate(fv, B, 8, 1.5)['mode'] == 'float'
    for B in (np.array(Bi, dtype=object), [F(-10)] + Bi[1:]):
        assert oa._b2_holds_rational(B, 8)
        c = oa.coefficients(fv, B, 8, F(3, 2)); assert c.dtype == object and all(type(x) is F for x in c)
        try: oa.jacobians(fv, B, 8, 1.5)
        except ValueError: pass
        else: raise AssertionError('jacobians accepted an exact-mode B2')


def test_affinity_loop4_control_order_dependence():
    """Repair round 3 (affinity_gate docstring): (4,5) is a nonzero control at order 8 only. At order 7 every
    loop-4 x loop-5 exact second difference vanishes (48 slot pairs) and moving loop 4 leaves J_5 unchanged; at order 8
    some do not (80 pairs) and J_5 moves."""
    for order, want_nonzero in ((7, False), (8, True)):
        rng = random.Random(45 + order); b, c = ec.random_general(rng, order); base = ec.fixed_point(b, c, order, F(3, 2))
        s4, s5 = ec._all_slots(order, [4]), ec._all_slots(order, [5]); nonzero = 0
        y = {t: ec.fixed_point(*ec._shift(b, c, *t, F(1)), order, F(3, 2)) for t in s5}
        for s in s4:
            x = ec.fixed_point(*ec._shift(b, c, *s, F(1)), order, F(3, 2)); bb, cc = ec._shift(b, c, *s, F(1))
            for t in s5:
                w = ec.fixed_point(*ec._shift(bb, cc, *t, F(1)), order, F(3, 2))
                nonzero += any(p - q - r_ + u != 0 for p, q, r_, u in zip(w, x, y[t], base))
        assert len(s4) * len(s5) == {7: 48, 8: 80}[order] and (nonzero > 0) == want_nonzero, (order, nonzero)
        B2 = b2_order8(3); v = {L: np.random.default_rng(3).normal(size=2 * (order + 1 - L)) for L in range(3, order + 1)}
        J0 = oa.jacobians(v, B2, order, 1.5); w4 = dict(v); w4[4] = v[4] + 1.0; J1 = oa.jacobians(w4, B2, order, 1.5)
        moved = float(np.max(np.abs(J1[5] - J0[5]))) / float(np.max(np.abs(J0[5])))
        assert (moved > 1e-6) == want_nonzero and (want_nonzero or moved <= 1e-14), (order, moved)


def test_exact_check_writes_no_bytecode():
    """Repair round 3: exact_check.py sets sys.dont_write_bytecode before importing order8_assembly, so running it
    without PYTHONDONTWRITEBYTECODE writes no __pycache__ next to the module. Checked on a temporary copy (TMPDIR),
    with a control showing that a plain import there does write one."""
    import subprocess, shutil, tempfile
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONDONTWRITEBYTECODE'}
    with tempfile.TemporaryDirectory() as tmp:
        for f in ('exact_check.py', 'order8_assembly.py'): shutil.copy(HERE / f, tmp)
        env['LRI_ROOT'] = tmp
        code = "import runpy, sys; ns = runpy.run_path(sys.argv[1]); ns['float_vs_exact'](7, 1, 1)"
        subprocess.run([sys.executable, '-c', code, str(Path(tmp) / 'exact_check.py')], check=True, env=env, cwd=tmp, capture_output=True)
        assert not [p for p in Path(tmp).rglob('*') if p.suffix == '.pyc' or p.name == '__pycache__']
        ctl = f"import sys; sys.path.insert(0, {tmp!r}); import order8_assembly"
        subprocess.run([sys.executable, '-c', ctl], check=True, env=env, cwd=tmp, capture_output=True)
        assert (Path(tmp) / '__pycache__').is_dir()  # control: the environment does write bytecode without the guard


def test_no_bytecode_written_into_delivered_packages():
    """Repair round 2: loading the delivered assemble.py (exec from source) and this folder's modules writes no
    bytecode into LRI_C7_D3_HPC or LRI_C7_D2_HPC. (Files already there are reported in README, not removed here.)"""
    need(D3_ASSEMBLE, D2_ASSEMBLE)
    def snapshot():
        out = {}
        for pkg in ('LRI_C7_D3_HPC', 'LRI_C7_D2_HPC'):
            for p in (LRI / pkg).rglob('*'):
                if p.suffix == '.pyc' or p.name == '__pycache__': out[str(p)] = p.stat().st_mtime_ns
        return out
    before = snapshot()
    for path in (D3_ASSEMBLE, D2_ASSEMBLE): load_delivered(path)
    assert snapshot() == before


def test_slot_shift_rule_float():
    """dC8/d(slot z^j of loop L) = dC7/d(slot z^(j-1)) at the same point (the response to eps^j g^(L+1) is eps^j times
    a j-independent series)."""
    rng = np.random.default_rng(5); B2 = b2_order8(3)
    v8 = {L: rng.normal(size=2 * (9 - L)) for L in range(3, 9)}
    J8 = oa.jacobians(v8, B2, 8, 1.5)
    for L in range(3, 8):
        k = 9 - L
        for ch in (0, k):
            for j in range(1, k):
                assert abs(J8[L][8, ch + j] - J8[L][7, ch + j - 1]) <= 1e-12 * max(1, abs(J8[L][7, ch + j - 1]))


def test_power_bookkeeping_and_null_rows():
    r = ec.power_bookkeeping(); assert set(r['R8_free_symbols']) == {'A', 'b3', 'b4', 'b5', 'b6', 'c3', 'c4', 'c5', 'c6'}
    # repair round 2: the MS order-5 power difference at d=2 is a numerical zero (POWER_PROTOCOL section 2, order-5 row)
    assert abs(float(r['d2_order5_power_difference'])) < float(r['d2_order5_printed_digit_resolution']) < 2e-20
    assert abs(float(r['d2_order5_lower_part']) + 1.0775357715447757) < 1e-15
    fake = oa.power_null_rows(np.array([0] * 3 + [0, 1e-3, 0, 0, 0.5, 9.0]), np.array([1.] * 9), 8)
    assert [x['order'] for x in fake['flags']] == [] and fake['top']['delta'] == 9.0
    assert fake['top']['pull'] == 9.0 and 'flag' not in fake['top']  # top pull: diagnostic only, never flagged (repair round 2)
    # repair round 3: the role cites what the d=2/3 C7 sections say, not the d=1 'conjecture' sentence (N:10220-10221)
    role = fake['top']['role']; assert 'conjectur' not in role and 'not proved' in role and 'N:10659-10661' in role and 'N:10220' not in role
    assert oa.power_null_rows(np.zeros(9), np.zeros(9), 8)['top']['pull'] is None
    for d in (3, 2):
        run, res = _production(d)
        rows = oa.power_null_rows(np.asarray(res['power_differences']), np.asarray(res['power_difference_errors']), 7)
        assert [x['order'] for x in rows['null_rows']] == [3, 4, 5, 6] and not rows['flags'] and rows['top']['order'] == 7
        assert abs(rows['top']['pull'] - {3: 1.14245, 2: -1.22175}[d]) < 1e-4  # C7 top-order pulls of 0.018 +- 0.016 (N:10818), -0.056 +- 0.046 (N:10661)
    fake = oa.power_null_rows(np.array([0] * 3 + [0, 1e-3, 0, 0, 5.0, 9.0]), np.array([1.] * 9), 8)
    assert [(x['order'], x['flag']) for x in fake['flags']] == [(7, 'not proved zero')]


# --------------------------------------------------------------------------------------------------------------
# Item 4: low-loop inputs

def test_low_inputs_reproducible_and_regressions():
    for d in (3, 2):
        need(LRI / pl.SETTINGS[d]['delivered_two_loop'], LRI / pl.SETTINGS[d]['delivered_gamma'])
        files = pl.build(d)  # asserts two-contour agreement, the high-precision reference and the order-7 regressions
        for name, data in files.items():
            assert (HERE / pl.SETTINGS[d]['outdir'] / name).read_bytes() == data, name
        ch = json.loads(files['checks.json'])
        assert all(v is True for k, v in ch['order7_regression'].items() if isinstance(v, bool))
        assert len(json.loads(files['two_loop.json'])['B2']) == 7
        # repair round 3: every printed Gamma token is correctly rounded (independent 128/160-node check at dps + 35),
        # and the stored B2 agrees with a direct 130-digit series (58.2 / 69.5 significant digits at z^6, d=3 / d=2)
        gc, sc = ch['gamma']['cauchy_check'], ch['two_loop']['series_check']
        assert gc['all_printed_tokens_correctly_rounded'] is True and gc['jets_checked'] == 42
        assert float(gc['max_difference_in_last_printed_digit_units']) <= 0.5 and float(gc['check_contours_max_abs_difference']) < 1e-80
        assert float(sc['reference_vs_series_max']) < 1e-85 and float(sc['stored_significant_digits'][6]) >= {3: 58, 2: 69}[d]
        rows = files[f'gamma_d{d}_8.txt'].decode().splitlines()
        assert [int(r.split()[0]) for r in rows] == [6, 5, 4, 3, 2, 1, 0] and all(len(r.split()) == 9 for r in rows)
    assert json.loads(pl.build(2)['checks.json'])['C62d_b26']['agrees_to_printed_digits']


def test_order8_assembly_on_c7_production_point():
    """Regression value only: C8 at the C7(2)/C7(3) production means, with the new top slots and loop 8 set to zero,
    and SE from the C7 replicate covariances (zero rows and columns for the new slots). This is NOT the complete
    C7-level part of C8: the C7 productions omitted the loop-7 s_G = 4 classes (LRI_C7_D2_HPC/tools/prepare_inputs.py:36;
    d=3 used 2,298 + 590 L7 kernels), so the b_{7,0} and c_{7,0} means are individually incomplete (only 3c_{7,0} -
    b_{7,0} is complete), while C8 weighs them as (-16A, 42A)/19683. C7 from the order-8 run equals the published C7
    to rounding. The d=2 value reproduces the arithmetic of C62d's RECON.md:100 (-192,711 +- 8)."""
    want = {3: (-6237.087138964107, 0.33241527680041183), 2: (-192710.59113786137, 8.20010636042147)}
    def pad(v, L): k = 8 - L; return np.concatenate([v[:k], [0.], v[k:], [0.]])
    def padc(V, L):
        k = 8 - L; idx = list(range(k)) + list(range(k + 1, 2 * k + 1)); W = np.zeros((2 * k + 2, 2 * k + 2)); W[np.ix_(idx, idx)] = V; return W
    for d, hd in ((3, 1.5), (2, 1)):
        run, res = _production(d); B2 = b2_order8(d)
        means, vc = oa.campaign_moments(merged(run), range(3, 8))
        m8 = {s: {**{L: pad(means[s][L], L) for L in range(3, 8)}, 8: np.zeros(2)} for s in means}
        v8 = {s: {**{L: padc(vc[s][L], L) for L in range(3, 8)}, 8: np.zeros((2, 2))} for s in vc}
        r = oa.sector_assembly(m8, v8, B2, 8, hd); c, se = r['coefficients'], r['standard_errors']
        assert np.isfinite(c).all() and abs(c[7] - res['C7_full']) <= 1e-12 * abs(res['C7_full'])
        assert abs(c[8] - want[d][0]) <= 1e-9 * abs(want[d][0]) and abs(se[8] - want[d][1]) <= 1e-9 * want[d][1], (d, c[8], se[8])
        # The loop-7 z^0 share of that value, (-16A b70 + 42A c70)/19683 = 14A(3c70 - b70)/19683 - 2A b70/19683: the
        # first term uses the complete combination, the second the b70 mean that lacks the s_G = 4 classes.
        A = -float(B2[0]) / 6; b70, c70 = m8['free'][7][0] + m8['power'][7][0], m8['free'][7][2] + m8['power'][7][2]
        part = r['J'][7][8, 0] * b70 + r['J'][7][8, 2] * c70; full, incomplete = 14 * A * (3 * c70 - b70) / 19683, -2 * A * b70 / 19683
        want7 = {3: (-1977.916858543992, -310.7906330363848), 2: (-81617.04677425987, -12595.681301234707)}[d]
        assert abs(part - want7[0]) <= 1e-9 * abs(want7[0]) and abs(incomplete - want7[1]) <= 1e-9 * abs(want7[1])
        assert abs(full + incomplete - part) <= 1e-9 * abs(part)


if __name__ == '__main__':
    import time
    names = [n for n in sorted(globals()) if n.startswith('test_')]; fails = 0
    for n in names:
        t = time.time()
        try: globals()[n](); print(f'PASS {n} ({time.time() - t:.1f} s)')
        except Exception as e:
            if type(e).__name__ in ('_Skip', 'Skipped'): print(f'SKIP {n}: {e}')
            else: fails += 1; print(f'FAIL {n}: {type(e).__name__}: {e}')
    sys.exit(1 if fails else 0)
