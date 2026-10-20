#!/usr/bin/env python3
"""Window (Dconn) pieces of C4 at even cutoffs Lambda (PLAN sec. 4):

  Delta C4^Dconn(L) = dC4_g2D(L) + shift4(L),
  shift4(L) = -B4/3,  B4 = Ec^(4)(L) - Ec^(4)(L-1) = Delta E0raw^(4)(L) + Delta R4(L),

  * Delta E0raw^(4): window (cut4-4, cut4] of the eps^4 vacuum energy with the outer couplings of cutoff L, from the
    p = 0 top shells of every eps^4 chain (c4_compute1d.compute -> 'vac_win4_chains', 'vac_win4_f');
  * R4(x) = g1^4 sum_b |V_b0|^2/E_b^2 [e(x) - e(x - E_b)] (b: states of <0|V R^2 V|0>), e(x) = <0|VRV|0>_x;
    Delta R4 evaluated cancellation-free from the two-vertex shells; must equal H_odd(L-1)/2916;
  * dC4_g2D: closed form fast(L) (vendor/exact_fast.py, copied from lri_eh_hpc/lri_eh/exact.py) and, as a check,
    the engine's own window sum  Pi_p g1^4 sum_s |V_sp|^2/E_s^2 [e(L) - e(L - E_s)]."""
import math
from fractions import Fraction as Fr

import numpy as np

import c4lib1d as lib

g1 = 1.0 / 3.0
MOFF = lib.MOFF


def two_vertex_p_shells(kinds, slice_op, Lmax, ser, p):
    """Per-p shell array (index m + MOFF) of a plain two-vertex chain: sum_keys A_p(delta) S_delta[m]."""
    recs = lib.chain2_keys(kinds, [0, 0], slice_op, Lmax, ser)
    out = np.zeros(4 * Lmax + 1 + MOFF)
    for _, amps, sh in recs:
        if amps[p] != 0:
            out += float(amps[p]) * sh
    return out


def h_odd(n):
    return math.fsum(1.0 / k for k in range(1, n + 1, 2))


def delta_R4(Lmax, ser=None):
    """Delta R4(L) = R4(4L) - R4(4L-4) for every even L <= Lmax, cancellation-free:
       R4(x4) = g1^4 sum_m h[m] W(x4, m),  W(x, m) = sum of de over shells (x - m, x]   (m <= x),
       W(x4, m) - W(x4-4, m) = w4(x4) - w4(x4 - m) for m <= x4 - 4, with w4(x) = sum of de over (x - 4, x];
       the shells m in (x4 - 4, x4] enter R4(x4) only: + h[m] W(x4, m).
    Each window sum is a short single-signed sum of de shells (never a difference of cumulative values)."""
    ser = ser or lib.Series1D(Lmax)
    de = two_vertex_p_shells(["V", "V"], (1, 0), Lmax, ser, 0)      # e shells (negative), index m + MOFF
    h = two_vertex_p_shells(["V", "V"], (2, 0), Lmax, ser, 0)       # |V|^2/E^2 shells (positive)
    nM = len(de)
    # w4[i] = sum_{j=0..3} de[i - j]  (index i = shell m + MOFF; out-of-range shells are empty)
    dpad = np.concatenate([np.zeros(3), de])
    w4 = dpad[3:] + dpad[2:-1] + dpad[1:-2] + dpad[:-3]
    mvals = np.arange(nM) - MOFF
    nz = np.nonzero(h)[0]
    out = {}
    for L in range(2, Lmax + 1, 2):
        x4 = 4 * L
        terms = []
        sel = nz[mvals[nz] <= x4 - 4]
        if sel.size:
            terms.extend((h[sel] * (w4[x4 + MOFF] - w4[x4 - mvals[sel] + MOFF])).tolist())
        for i in nz[(mvals[nz] > x4 - 4) & (mvals[nz] <= x4)]:
            m = mvals[i]
            lo = max(x4 - m + 1 + MOFF, 0)
            terms.append(h[i] * math.fsum(de[lo: x4 + MOFF + 1]))
        out[L] = (1.0 / 3.0) ** 4 * math.fsum(terms)
    return out


def g2D_window(Lmax, ser=None):
    """Own two-vertex evaluation of dC4_g2D(L) = Pi_p [g1^4 sum_s |V_sp|^2/E_s^2 (e(L) - e(L - E_s))], even L."""
    ser = ser or lib.Series1D(Lmax)
    de = two_vertex_p_shells(["V", "V"], (1, 0), Lmax, ser, 0)
    nM = len(de)
    cde = np.concatenate([[0.0], np.cumsum(de)])          # cde[i] = sum_{j < i} de[j]

    def win(x4, w):
        """e(x4) - e(x4 - w) = sum de over shells m in (x4 - w, x4]."""
        lo = max(x4 - w + 1 + MOFF, 0)
        hi = min(x4 + MOFF + 1, nM)
        return cde[hi] - cde[lo] if hi > lo else 0.0

    hp = [two_vertex_p_shells(["V", "V"], (2, 0), Lmax, ser, p) for p in lib.PS]
    W = [Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3)]
    out = {}
    for L in range(2, Lmax + 1, 2):
        x4 = 4 * L
        terms = []
        for p in lib.PS:
            for i in range(nM):
                m = i - MOFF
                if hp[p][i] == 0.0 or m + p > x4:
                    continue
                terms.append(float(W[p]) * hp[p][i] * win(x4, m + p))
        out[L] = g1 ** 4 * math.fsum(terms)
    return out
