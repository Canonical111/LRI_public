"""Core unit tests (PLAN.md A6a-c, A6e-type regression).  Fast tests by default; the mirror tests at Lmax = 24 run
with C5T_SLOW=1.   usage: python -m pytest -q validate/test_core.py      C5T_SLOW=1 python -m pytest -q validate/test_core.py"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib5 import density as D, keys as K5, paths   # noqa: E402
from lib5.common import ONE                       # noqa: E402
from lib5.series import Series5                   # noqa: E402

SLOW = os.environ.get("C5T_SLOW") == "1"
C4P = "<PROJECT>/lri_1d_c4_exact"


def _u(eps1, eps2, m, mp):
    return mp.sqrt(mp.rf((1 - eps1) / 2, m) / mp.factorial(m)) * mp.sqrt(mp.rf((1 - eps2) / 2, m) / mp.factorial(m))


def test_two_ended_jets_vs_mpmath():
    mp = pytest.importorskip("mpmath")
    mp.mp.dps = 30
    N = 6
    ser = Series5(N)

    def coeff(e1, e2, n, l):
        w = [mp.mpf(0)] + [_u(e1, e2, k, mp) for k in range(1, l + 1)]
        p = [mp.mpf(1)] + [mp.mpf(0)] * l
        for _ in range(n):
            q = [mp.mpf(0)] * (l + 1)
            for i in range(l + 1):
                for j in range(l + 1 - i):
                    q[i + j] += p[i] * w[j]
            p = q
        return p[l]

    for n in (1, 2, 3):
        for al in range(4):
            for be in range(4 - al):
                mine = ser.U(n, al, be)
                for l in range(n, N + 1):
                    d = mp.diff(lambda a, b: coeff(a, b, n, l), (0, 0), (al, be))
                    ref = float(d / (mp.factorial(al) * mp.factorial(be)))      # Taylor coefficient
                    if ref == 0.0:                                             # exact zero (A6c): must be ~0
                        assert abs(mine[l]) <= 1e-15, (n, al, be, l, mine[l])
                    else:
                        assert abs(mine[l] - ref) <= 1e-13 * abs(ref), (n, al, be, l, mine[l], ref)


def test_zero_mode_not_a_line():
    ser = Series5(10)
    for al in range(4):
        for be in range(4 - al):
            assert ser.line(al, be)[0] == 0.0


@pytest.mark.parametrize("K,N", [(2, 9), (3, 11), (4, 10), (5, 8)])
def test_density_even_vs_reference_with_jets(K, N):
    rng = np.random.default_rng(K * 100 + N)
    ser = Series5(N)
    kinds = ["V"] * K
    pats = paths.patterns(kinds)
    done = 0
    for n in [pats[i] for i in rng.choice(len(pats), min(40, len(pats)), replace=False)]:
        legs = paths.legs_of(n, K)
        ords = [0] * K
        tot = {2: 3, 3: 2, 4: 1, 5: 0}[K]
        for _ in range(tot):
            cand = [i for i in range(K) if legs[i] > 0]
            if cand:
                ords[rng.choice(cand)] += 1
        a = D.density_even(K, n, ords, ser, N, block=3)
        b = D.density_even(K, n, ords, ser, N, reference=True)
        if a is None or b is None:
            assert a is None and b is None
            continue
        nz = b != 0
        assert np.all(np.abs(a[~nz]) <= 1e-300)
        if nz.any():
            assert np.max(np.abs(a[nz] - b[nz]) / np.abs(b[nz])) <= 1e-12
            done += 1
    assert done >= min(5, len(pats) - 1)          # K = 2 has only 5 patterns (n01 = 0..4), one of them line-free


@pytest.mark.skipif(not os.path.exists(os.path.join(C4P, "c4_compute1d.py")),
                    reason="C4P checkout not available (cluster snapshot); A6e compares C2..C4 with the C4P result")
def test_orders_2_to_4_regression_vs_c4p():
    """The rs5-generated assembly reproduces C4P's hand-written assembly (r, g, C at orders 2..4)."""
    sys.path.insert(0, C4P)
    import c4_compute1d as cc
    import assemble5
    a = assemble5.compute(10, nmax=4, verbose=False)
    b = cc.compute(10, verbose=False)
    for n in (2, 3, 4):
        for k in ("r", "g", "C"):
            x, y = a[f"{k}{n}"][3:], b[f"{k}{n}"][3:]
            assert np.max(np.abs(x - y) / np.maximum(np.abs(y), 1e-300)) <= 1e-12, (k, n)


@pytest.mark.skipif(not SLOW, reason="A6a/b at Lmax=24: set C5T_SLOW=1")
def test_A6a_five_vertex_mirror_pairs():
    L = 24
    ser = Series5(L)
    verts = tuple(("V", 0) for _ in range(5))
    sops = tuple((1, 0) for _ in range(4))
    seen, npairs = set(), 0
    for n in paths.patterns(["V"] * 5):
        k, kr = paths.pattern_key(n), paths.pattern_key(paths.reverse_pattern(n, 5))
        if k == kr or (min(k, kr), max(k, kr)) in seen:
            continue
        seen.add((min(k, kr), max(k, kr)))
        ka, sa, _ = K5.key_shells(verts, sops, n, L, ser)
        kb, sb, _ = K5.key_shells(verts, sops, paths.reverse_pattern(n, 5), L, ser)
        if ka is None:
            assert kb is None
            continue
        npairs += 1
        lb = list(kb)
        for t, key in enumerate(ka):
            rk = tuple(reversed(key))
            assert ka[key] == kb[rk]
            u = lb.index(rk)
            assert np.max(np.abs(sa[t] - sb[u])) <= 1e-13 * max(np.max(np.abs(sa[t])), 1e-300)
    # exhaustive (A6a): every non-palindromic reversal pair of the VVVVV patterns was compared
    allpairs = {(min(paths.pattern_key(m), paths.pattern_key(paths.reverse_pattern(m, 5))),
                 max(paths.pattern_key(m), paths.pattern_key(paths.reverse_pattern(m, 5))))
                for m in paths.patterns(["V"] * 5)
                if paths.pattern_key(m) != paths.pattern_key(paths.reverse_pattern(m, 5))}
    assert seen == allpairs and npairs > 1000


def test_density_even_single_full_density_memory():
    """A full four-slice density is not copied by density_even (C5-A9-002): peak <= R + kernel tables + small temps."""
    import tracemalloc
    verts = tuple(("V", 0) for _ in range(5))
    sops = tuple((1, 0) for _ in range(4))
    n = [p for p in paths.patterns(["V"] * 5) if all(paths.slice_counts(p, 5)) and sum(p.values()) >= 8][0]
    K5.key_shells(verts, sops, n, 8, Series5(8), block=1)            # numba warm-up
    N = 96
    ser = Series5(N)
    for k in range(9):
        ser.U(k)
    H = N // 2 + 1
    full = H ** 4 * 8
    tables = (N + 1) ** 3 * 8 + 2 * (N + 1) ** 2 * H * 8                # crossing kernel + stage-A table
    tracemalloc.start()
    R = D.density_even(5, n, [0] * 5, ser, N, block=1)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert R.shape == (H, H, H, H)
    assert peak <= full + tables + 0.25 * full, (peak / full)


@pytest.mark.skipif(not SLOW, reason="A6b at Lmax=24: set C5T_SLOW=1")
def test_A6b_mirror_reduced_equals_full_C5_chain():
    L = 24
    ser = Series5(L)
    verts = tuple(("V", 0) for _ in range(5))
    sops = tuple((1, 0) for _ in range(4))
    full, _ = K5.eval_chain(verts, sops, L, ser, {ONE: ONE}, keep_records=True)     # records => no mirror
    red, _ = K5.eval_chain(verts, sops, L, ser, {ONE: ONE})
    for w in ("r", "g", "C"):
        x, y = K5.functional(full[ONE], w), K5.functional(red[ONE], w)
        assert np.max(np.abs(x - y)) <= 1e-12 * max(1.0, np.max(np.abs(x)))
