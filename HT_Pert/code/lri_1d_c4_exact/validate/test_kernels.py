"""Unit tests (PLAN A6a-c and the series/derivative constants).

Fast tests run by default; the A6a/A6b tests at Lmax = 40 run when C4T_SLOW=1 (cluster validation job).
usage: python3 -m pytest -q validate/test_kernels.py        C4T_SLOW=1 python3 -m pytest -q validate/test_kernels.py"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import c4lib1d as lib  # noqa: E402

SLOW = os.environ.get("C4T_SLOW") == "1"
LM = int(os.environ.get("C4T_LMAX", "40"))


def _u(eps, m, mp):
    return mp.sqrt(mp.rf((1 - eps) / 2, m) / mp.factorial(m))


def test_log_u_taylor_constants():
    mp = pytest.importorskip("mpmath")
    mp.mp.dps = 40
    ser = lib.Series1D(25)
    for m in range(1, 26):
        c = mp.taylor(lambda e: mp.log(_u(e, m, mp)), 0, 2)
        assert abs(float(c[1]) - ser.a[m]) <= 1e-14 * max(1.0, abs(ser.a[m]))
        assert abs(float(c[2]) - ser.b[m]) <= 1e-14 * max(1.0, abs(ser.b[m]))
    assert ser.a[0] == 0.0 and ser.b[0] == 0.0


def test_dchi_closed_form():
    """dchi = (1/4) log(1-y) V_1(y) (no constant term)."""
    N = 60
    ser = lib.Series1D(N)
    L1 = np.zeros(N + 1)
    L1[1:] = -1.0 / np.arange(1, N + 1)
    ref = 0.25 * np.convolve(L1, ser.u2)[: N + 1]
    assert np.max(np.abs(ser.dchi - ref) / np.maximum(np.abs(ref), 1e-300) * (ref != 0)) <= 1e-13
    assert ser.dchi[0] == 0.0


def test_bundle_series_positive_and_vanishing():
    ser = lib.Series1D(50)
    for n in range(1, 9):
        assert np.all(ser.S[n][:n] == 0.0) and np.all(ser.S[n][n:] > 0.0)
        assert np.all(ser.dS[n][:n] == 0.0) and np.all(ser.dS[n][n:] < 0.0)


def test_two_vertex_series_vs_mpmath():
    mp = pytest.importorskip("mpmath")
    mp.mp.dps = 30
    N = 7
    ser = lib.Series1D(N)

    def coeff(e1, e2, m, Nl):
        # [y^Nl] (sum_{k>=1} u_k(e1) u_k(e2) y^k)^m by explicit convolution
        w = [mp.mpf(0)] + [_u(e1, k, mp) * _u(e2, k, mp) for k in range(1, Nl + 1)]
        p = [mp.mpf(1)] + [mp.mpf(0)] * Nl
        for _ in range(m):
            q = [mp.mpf(0)] * (Nl + 1)
            for i in range(Nl + 1):
                for j in range(Nl + 1 - i):
                    q[i + j] += p[i] * w[j]
            p = q
        return p[Nl]

    for m in (1, 2, 3, 4):
        for d1, d2 in ((0, 0), (1, 0), (0, 1), (2, 0), (0, 2), (1, 1)):
            mine = lib.two_vertex_series(m, d1, d2, ser)
            for Nl in range(m, N + 1):
                ref = mp.diff(lambda a, b: coeff(a, b, m, Nl), (0, 0), (d1, d2))
                assert abs(mine[Nl] - float(ref)) <= 1e-12 * max(1.0, abs(float(ref))), (m, d1, d2, Nl)


@pytest.mark.parametrize("N", [10, 23, 41])
def test_stream_vs_dense(N):
    rng = np.random.default_rng(N)
    ser = lib.Series1D(N)
    pats = [n for n in lib.patterns(["V"] * 4) if all(lib.slice_counts(n, 4))]
    for n in [pats[i] for i in rng.choice(len(pats), 10, replace=False)]:
        ref = lib.density_even(4, n, ser, [N, N, N], stream=False)
        for blk in (1, 4, 64):
            st = lib.density_even(4, n, ser, [N, N, N], stream=True, block=blk)
            nz = ref != 0
            assert np.all(st[~nz] == 0.0)
            assert np.max(np.abs(st[nz] - ref[nz]) / np.abs(ref[nz])) <= 1e-13


@pytest.mark.parametrize("N", [12, 37])
def test_k3_fast_vs_dense(N):
    ser = lib.Series1D(N)
    for kinds in (["V"] * 3, ["M", "V", "V"], ["V", "M", "V"]):
        for n in lib.patterns(kinds):
            if not all(lib.slice_counts(n, 3)):
                continue
            for dv in (None, 0, 1):
                if dv is not None and lib.legs_of(n, 3)[dv] == 0:
                    continue
                a = lib.density_even(3, n, ser, [N, N], dv, stream=True)
                b = lib.density_even(3, n, ser, [N, N], dv, stream=False)
                nz = b != 0
                assert np.all(a[~nz] == 0.0)
                assert np.max(np.abs(a[nz] - b[nz]) / np.abs(b[nz])) <= 1e-13


def test_parity_even_only():
    """The even-parity density equals the all-parity density on even points (dense reference)."""
    N = 16
    ser = lib.Series1D(N)
    n = {(0, 1): 1, (0, 2): 1, (0, 3): 1, (1, 2): 0, (1, 3): 1, (2, 3): 1}
    full = lib.build_rho_dense(4, {b: ser.S[n[b]] for b in lib.pairs_of(4)}, [N, N, N])
    ev = lib.density_even(4, n, ser, [N, N, N])
    assert np.array_equal(ev, full[::2, ::2, ::2]) or np.allclose(ev, full[::2, ::2, ::2], rtol=1e-14, atol=0)


@pytest.mark.skipif(not SLOW, reason="A6a at Lmax=40: set C4T_SLOW=1")
def test_A6a_mirror_pairs_identical_shells():
    K = 4
    ser = lib.Series1D(LM)
    ops = [(1, 0)] * 3
    seen = set()
    npairs = 0
    for n in lib.patterns(["V"] * 4):
        k, kr = lib.pattern_key(n), lib.pattern_key(lib.reverse_pattern(n, K))
        if k == kr or (min(k, kr), max(k, kr)) in seen:
            continue
        seen.add((min(k, kr), max(k, kr)))
        a_keys, a_sh, _ = lib.key_shells(["V"] * 4, ops, n, LM, ser)
        b_keys, b_sh, _ = lib.key_shells(["V"] * 4, ops, lib.reverse_pattern(n, K), LM, ser)
        assert len(a_keys) == len(b_keys)
        if not a_keys:
            continue
        npairs += 1
        bl = list(b_keys)
        for t, key in enumerate(a_keys):
            rk = tuple(reversed(key))
            assert a_keys[key] == b_keys[rk]
            u = bl.index(rk)
            sc = np.max(np.abs(a_sh[t]))
            assert np.max(np.abs(a_sh[t] - b_sh[u])) <= 1e-13 * sc
    assert npairs > 100


@pytest.mark.skipif(not SLOW, reason="A6b at Lmax=40: set C4T_SLOW=1")
def test_A6b_mirror_reduced_equals_full():
    ser = lib.Series1D(LM)
    ops = [(1, 0)] * 3
    full = lib.chain_reduced(["V"] * 4, ops, LM, ser, mirror=False)
    red = lib.chain_reduced(["V"] * 4, ops, LM, ser, mirror=True)
    for w in ("r", "g", "C"):
        a = lib.functional_from_reduced(full["1"], w)
        b = lib.functional_from_reduced(red["1"], w)
        assert np.max(np.abs(a - b)) <= 1e-13 * max(1.0, np.max(np.abs(a)))
    for p in lib.PS:
        a = lib.perp_from_reduced(full["1"], p)
        b = lib.perp_from_reduced(red["1"], p)
        assert np.max(np.abs(a - b)) <= 1e-13 * max(1.0, np.max(np.abs(a)))
