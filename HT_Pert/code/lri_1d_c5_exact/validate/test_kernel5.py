"""Tests of the five-vertex streaming kernel lib5/kernel5.density5_stream (PLAN A6c, K = 5 part).

Reference: dense5 = sequential shifted products of the ten bundle series on the full all-parity box [0, N]^4, then
the even part (copied from proto/k5_middle_split_proto.py, generalised to an arbitrary series dict).
Requirement on every comparison: exact zeros where the reference is zero, relative deviation <= 1e-13 elsewhere.
Bundle series: S_n = (V_1 - 1)^n from C4P c4lib1d.Series1D(N).S[n] (lri_1d_c4_exact, override with C4P_DIR); when C4P
is not importable (cluster snapshot) a verbatim copy of its recursion is used, and test_local_series_equals_c4p checks
bitwise agreement whenever both exist.
usage: python -m pytest -q validate/test_kernel5.py"""
import os
import sys
import tracemalloc

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib5.kernel5 import density5_stream, PAIRS5, CROSSING  # noqa: E402

C4P_DIR = os.environ.get("C4P_DIR", "<PROJECT>/lri_1d_c4_exact")
try:
    sys.path.insert(0, C4P_DIR)
    _dwb = sys.dont_write_bytecode
    sys.dont_write_bytecode = True               # read-only use of the frozen C4P tree
    import c4lib1d                               # noqa: E402
    HAVE_C4P = True
except Exception:  # pragma: no cover
    HAVE_C4P = False
finally:
    sys.dont_write_bytecode = _dwb
    sys.path.remove(C4P_DIR)

BLOCKS = (1, 2, 5, 10 ** 6)
TOL = 1e-13
SL = {(i, j): tuple(range(i, j)) for (i, j) in PAIRS5}       # bundle (i, j) crosses slice axes i..j-1
LOCAL = ((0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4))


def _local_S(N, nmax=4):
    """Verbatim copy of c4lib1d.Series1D(N).S (u2 = (1/2)_m/m!, chi = u2 without m = 0, S[n] = chi^n)."""
    u2 = np.empty(N + 1)
    u2[0] = 1.0
    for j in range(1, N + 1):
        u2[j] = u2[j - 1] * (j - 0.5) / j
    chi = u2.copy()
    chi[0] = 0.0
    delta = np.zeros(N + 1)
    delta[0] = 1.0
    S = [delta]
    for n in range(1, nmax + 1):
        S.append(np.convolve(S[-1], chi)[: N + 1])
    return S


_SCACHE = {}


def series_S(N):
    if N not in _SCACHE:
        _SCACHE[N] = c4lib1d.Series1D(N).S if HAVE_C4P else _local_S(N)
    return _SCACHE[N]


def dense5(s, N):
    """Reference: sequential shifted products on the full all-parity 4D box, then even part."""
    X = np.zeros((N + 1,) * 4)
    X[0, 0, 0, 0] = 1.0
    for b, sl in SL.items():
        v = s[b]
        Y = np.zeros_like(X)
        for l in range(N + 1):
            if v[l] == 0.0:
                continue
            src = [slice(None)] * 4
            dst = [slice(None)] * 4
            for a in sl:
                src[a] = slice(0, N + 1 - l)
                dst[a] = slice(l, N + 1)
            Y[tuple(dst)] += v[l] * X[tuple(src)]
        X = Y
    return X[::2, ::2, ::2, ::2]


def deviation(st, ref):
    """Exact zeros where ref == 0 (asserted); returns the max relative deviation on the nonzero entries."""
    assert st.shape == ref.shape and st.dtype == np.float64
    nz = ref != 0
    assert np.all(st[~nz] == 0.0), "nonzero where the reference is zero"
    if not nz.any():
        return 0.0
    return float(np.max(np.abs(st[nz] - ref[nz]) / np.abs(ref[nz])))


def pattern_series(N, n):
    S = series_S(N)
    return {b: S[n[b]] for b in PAIRS5}


def mask_lines(mask, rng, nmax=4):
    """Bundle line counts for a presence mask (bit k <-> PAIRS5[k]): absent = 0, present = 1..nmax."""
    return {b: (int(rng.integers(1, nmax + 1)) if mask >> k & 1 else 0) for k, b in enumerate(PAIRS5)}


def bits(bundles):
    return sum(1 << PAIRS5.index(b) for b in bundles)


ALL = bits(PAIRS5)
SPECIAL = {"none": 0, "all ten": ALL, "no crossing": bits(LOCAL), "crossing only": bits(CROSSING),
           "chain only": bits(((0, 1), (1, 2), (2, 3), (3, 4))), "all but crossing 04": ALL & ~bits(((0, 4),)),
           "only 04": bits(((0, 4),)), "only 13": bits(((1, 3),))}


def test_local_series_equals_c4p():
    if not HAVE_C4P:
        pytest.skip("C4P not importable")
    for N in (6, 9, 24):
        for a, b in zip(_local_S(N), c4lib1d.Series1D(N).S[:5]):
            assert np.array_equal(a, b)


def test_all_presence_classes_one_line():
    """Every one of the 2^10 presence classes, one line per present bundle (all densities nonzero at N = 9), blocks
    cycled over 1, 2, 5, large."""
    N = 9
    worst = 0.0
    for mask in range(1 << 10):
        n = {b: (mask >> k) & 1 for k, b in enumerate(PAIRS5)}
        s = pattern_series(N, n)
        ref = dense5(s, N)
        assert np.any(ref != 0)
        worst = max(worst, deviation(density5_stream(s, N, BLOCKS[mask % 4]), ref))
    assert worst <= TOL, worst


@pytest.mark.parametrize("N", [6, 12])
def test_all_presence_classes_random_lines(N):
    """Every presence class with random 1..4 lines per present bundle (zeros included and checked exactly)."""
    rng = np.random.default_rng(1000 + N)
    worst = 0.0
    nonzero = 0
    for mask in range(1 << 10):
        s = pattern_series(N, mask_lines(mask, rng))
        ref = dense5(s, N)
        nonzero += bool(np.any(ref != 0))
        worst = max(worst, deviation(density5_stream(s, N, BLOCKS[(mask + N) % 4]), ref))
    assert worst <= TOL, worst
    assert nonzero >= (100 if N == 6 else 400), nonzero


@pytest.mark.parametrize("N", [6, 9, 12, 17, 24])
def test_random_patterns_all_blocks(N):
    """Special classes (none, all ten, no crossing, crossing only, ...) and random classes, every block size."""
    rng = np.random.default_rng(N)
    masks = list(SPECIAL.values()) + [int(m) for m in rng.integers(0, 1 << 10, 6 if N >= 17 else 12)]
    worst = 0.0
    nonzero = 0
    for i, mask in enumerate(masks):
        nmax = 4 if N >= 17 else (1, 2, 4)[i % 3]          # small N: mix of line caps so most densities are nonzero
        s = pattern_series(N, mask_lines(mask, rng, nmax))
        ref = dense5(s, N)
        nonzero += bool(np.any(ref != 0))
        for blk in BLOCKS:
            worst = max(worst, deviation(density5_stream(s, N, blk), ref))
    assert worst <= TOL, worst
    assert nonzero >= len(masks) // 2, nonzero


@pytest.mark.parametrize("N", [0, 1, 2, 3, 7, 10, 13])
def test_arbitrary_positive_series(N):
    """Arbitrary non-negative series (random magnitudes over ~10 decades, nonzero constant terms, sprinkled exact
    zeros, some unit and some scaled-unit series): the kernel is exact for any series, not only S_n."""
    rng = np.random.default_rng(77 + N)
    worst = 0.0
    for trial in range(6):
        s = {}
        for b in PAIRS5:
            kind = rng.integers(0, 5)
            if kind == 0:
                v = np.zeros(N + 1)
                v[0] = 1.0
            elif kind == 1:
                v = np.zeros(N + 1)
                v[0] = rng.uniform(0.1, 3.0)
            else:
                v = rng.uniform(0.0, 1.0, N + 1) * np.exp(rng.normal(0.0, 2.5, N + 1))
                v[rng.random(N + 1) < 0.25] = 0.0
            s[b] = v
        if trial == 0:                       # crossing bundles all units -> factorised branch
            for b in CROSSING:
                s[b] = np.eye(1, N + 1)[0]
        ref = dense5(s, N)
        for blk in BLOCKS:
            worst = max(worst, deviation(density5_stream(s, N, blk), ref))
    assert worst <= TOL, worst


def test_longer_series_are_truncated():
    """Arrays longer than N+1 are allowed; only levels <= N enter."""
    N = 8
    S = series_S(20)
    s = {b: S[1] for b in PAIRS5}
    ref = dense5({b: S[1][: N + 1] for b in PAIRS5}, N)
    assert deviation(density5_stream(s, N, 3), ref) <= TOL


def test_timings_and_factorised_flag():
    N = 10
    S = series_S(N)
    tm = {}
    density5_stream({b: S[1] for b in PAIRS5}, N, 2, timings=tm)
    assert {"LR", "C", "A", "B1", "B2a", "B2b", "store"} <= set(tm) and "factorised" not in tm
    tm = {}
    density5_stream({b: S[1] if b in LOCAL else S[0] for b in PAIRS5}, N, 2, timings=tm)
    assert tm.get("factorised") == 1.0


def test_streaming_memory():
    """Blocks 1, 2 at N = 40: peak traced allocation = R + O(H (N+1)^2): Lft gather table (~1 unit H (N+1)^2),
    crossing kernel C ((N+1)^3 ~ 2 units), per-block P and Q (~block units each); far below one full P
    (H^2 (N+1)^2 = H units) or an all-parity 4D box ((N+1)^4)."""
    N = 40
    H = N // 2 + 1
    S = series_S(N)
    s = {b: S[1] for b in PAIRS5}
    density5_stream(s, 4, 1)                 # compile outside the trace
    unit = H * (N + 1) ** 2 * 8
    for blk in (1, 2):
        tracemalloc.start()
        R = density5_stream(s, N, blk)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        extra = peak - R.nbytes
        assert extra <= (2 * blk + 5) * unit, (blk, extra, unit)
        assert extra < 0.6 * H * H * (N + 1) ** 2 * 8
        assert peak < (N + 1) ** 4 * 8


def test_input_validation():
    N = 6
    S = series_S(N)
    good = {b: S[1] for b in PAIRS5}
    with pytest.raises(ValueError):
        density5_stream({b: v for b, v in good.items() if b != (1, 3)}, N)
    with pytest.raises(ValueError):
        density5_stream({**good, (2, 4): S[1][:N]}, N)
    bad = S[1].copy()
    bad[3] = -1e-30
    with pytest.raises(ValueError):
        density5_stream({**good, (0, 2): bad}, N)
    nan = S[1].copy()
    nan[2] = np.nan
    with pytest.raises(ValueError):
        density5_stream({**good, (3, 4): nan}, N)
    for blk in (0, -1, 2.0, None):
        with pytest.raises(ValueError):
            density5_stream(good, N, blk)
    with pytest.raises(ValueError):
        density5_stream(good, -1)
