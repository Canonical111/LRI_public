#!/usr/bin/env python3
"""Dconn window of C4 and C5 at even cutoffs (PLAN.md sec. 4), from an assembled raw run (assemble5.compute).

  Delta C5^Dconn = dC5_g2D + dC5_bubble + dC5_rows4 + dC5_rows5,
    dC5_g2D    = T1 + T2 + T3 + T4
      T1 = Pi <psi1| g1^2 D1 |psi1>   (two-vertex window sum with the eps^1 bubble shells e1)
      T2 = 6 g2(L) fast(L)
      T3 = 2 Pi <psi1| g1^2 D0 |psi2>  (two/three-vertex chains with a D0 insertion; at even L
           D0 = -(1/6)(N/2 + [P>=5] + [P>=13]) on a slice, affine in N, so D0 R^k = R^{k-1}/12 - (1/6)(c_P - (d+n)/8) R^k)
      T4 = 6 C2(L) Delta g4^{g2D},  Delta g4^{g2D} = F_g[ g1^4 sum |V|^2/E^2 (e(L) - e(L - E0)) ]
    dC5_bubble = -2 fast(L)
    dC5_rows4  = 2 C2(L) (3 A4 - B4),  A4/B4 = Ec^(4)(L) - Ec^(4)(L - 1/2 | L - 1)  (raw p=0 windows + Delta R4)
    dC5_rows5  = -B5/3,               B5 = raw p=0 eps^5 window (c-4, c] + Delta R5
  shift4 = -B4/3, Delta C4^Dconn = fast(L) + shift4 (C4P).
e(x) = <0|V R V|0>_x (g-stripped bubble), e1 = its eps^1 Taylor coefficient = 2 <0|V1 R V0|0> - (1/4) <0|V (P-p) R^2 V|0>.
Delta R4 = H_odd(L-1)/2916 (closed form; engine version as C4P windows1d.delta_R4); Delta R5: closed form below."""
import math
import os
import sys
from fractions import Fraction as Fr

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "vendor"))
from lib5 import keys as K5                               # noqa: E402
from lib5.common import FUNCTIONALS, G1, MOFF, ONE, PS, pvec, vpp   # noqa: E402

g1 = 1.0 / 3.0
D0EVEN = ("D0", 5, 13)                                    # c_P thresholds at even L


def p_shells(verts, sops, Lmax, ser, f=ONE):
    """Per-p shell arrays (4, M) of a chain (exact amplitudes x f(p), summed over keys and patterns)."""
    red, _ = K5.eval_chain(verts, sops, Lmax, ser, {f: f})
    return red[f]["Shp"]


def h_odd(n):
    return math.fsum(1.0 / k for k in range(1, n + 1, 2))


def window_functional(hp, de, w, Lmax):
    """sum_p w_p sum_{outer m: m+p <= c} hp[p][m] * (sum of de over shells (c - m - p, c]) at c = 4L, even L."""
    nM = len(de)
    cde = np.concatenate([[0.0], np.cumsum(de)])
    out = {}
    for L in range(2, Lmax + 1, 2):
        c = 4 * L
        terms = []
        for p in PS:
            if w[p] == 0:
                continue
            i = np.nonzero(hp[p])[0]
            m = i - MOFF
            ok = m + p <= c
            i, m = i[ok], m[ok]
            hi = min(c + MOFF + 1, nM)
            lo = np.maximum(c - m - p + 1 + MOFF, 0)
            win = cde[hi] - cde[lo]
            terms.extend((float(w[p]) * hp[p][i] * win).tolist())
        out[L] = g1 ** 4 * math.fsum(terms)
    return out


def delta_R4_engine(de, h, Lmax):
    """C4P windows1d.delta_R4 (cancellation-free): R4(4L) - R4(4L-4) at even L."""
    nM = len(de)
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
            lo = max(x4 - mvals[i] + 1 + MOFF, 0)
            terms.append(h[i] * math.fsum(de[lo: x4 + MOFF + 1]))
        out[L] = g1 ** 4 * math.fsum(terms)
    return out


def delta_R5_closed(g2, Lmax):
    """Closed form of Delta R5(L) = R5(L) - R5(L-1) (self-consistency part of B5) at even L, with the outer g2(L)
    (array over cut4).  Derived in the recon (eps5_window structure):
      Delta R5 = sum_{odd E <= L-1} (g1^2/(6E)) [g2/9 - 1/27 + (1/54)(1/(L-E) - 2 H_{L-E} + 2)] + (1/27) <psi1|psi2^(4)>,
      <psi1|psi2^(4)> = (g1^2/6) sum 1/E^2 + (g1 g2/6) H_odd(L-1) - (g1^2/6) sum (H_E - 1)/E
                        - g1^3 sum_{N1,N2 even <= L-2} (min(N1,N2)+1)/((N1+1)^2 (N2+1)),
    sums over odd E <= L-1, H_k harmonic numbers.  Cross-checked by delta_R5_engine (A5) and the exact vac_conn -
    vac_raw rationals (A2).  O(L) per cutoff (harmonic numbers and the double sum are built incrementally)."""
    H = np.zeros(Lmax + 2)
    acc = []
    for k in range(1, Lmax + 2):
        acc.append(1.0 / k)
        H[k] = math.fsum(acc) if k <= 64 else H[k - 1] + 1.0 / k
    out = {}
    D = 0.0
    for L in range(2, Lmax + 1, 2):
        t = L - 2
        add = []
        for N in range(0, t + 1, 2):
            add.append((min(N, t) + 1) / ((N + 1) ** 2 * (t + 1)))
            if N != t:
                add.append((min(N, t) + 1) / ((t + 1) ** 2 * (N + 1)))
        D += math.fsum(add)
        gg2 = g2[4 * L]
        E = np.arange(1, L, 2)
        Ef = E.astype(float)
        HLmE = H[L - E]
        HE = H[E]
        part1 = math.fsum(((g1 ** 2 / (6 * Ef)) * (gg2 / 9 - 1 / 27 + (1 / 54) * (1 / (L - Ef) - 2 * HLmE + 2))).tolist())
        psi = (g1 ** 2 / 6) * math.fsum((1 / Ef ** 2).tolist()) + (g1 * gg2 / 6) * math.fsum((1 / Ef).tolist()) \
            - (g1 ** 2 / 6) * math.fsum(((HE - 1) / Ef).tolist()) - g1 ** 3 * D
        out[L] = part1 + psi / 27
    return out


D0ODD = ("D0", 1, 9)                                     # c_P thresholds at odd sub-cutoff x


def delta_window(de, h, Lmax):
    """W(4L) - W(4L-4) for every even L, W(x4) = sum_{m <= x4} h[m] * (sum of de over shells (x4 - m, x4]),
    cancellation-free (no difference of cumulative values): for m <= x4 - 4 the bracket difference is
    w4(x4) - w4(x4 - m), w4(x) = sum of de over (x - 4, x]; shells m in (x4 - 4, x4] enter W(x4) only."""
    nM = len(de)
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
            lo = max(x4 - mvals[i] + 1 + MOFF, 0)
            terms.append(h[i] * math.fsum(de[lo: x4 + MOFF + 1]))
        out[L] = math.fsum(terms)
    return out


def delta_R5_engine(Lmax, res, ser, de0, de1, h0):
    """Engine evaluation of Delta R5(L) = R5(L) - R5(L-1) (vacuum problem, outer couplings of L), cancellation-free:
      R5(x) = A(x) + B(x),  A = g1^2 [g1^2 W(de1; x) + (2 g1 g2 - 2 g1^2) W(de0; x)]  (<psi1|D3^[x]|psi1>, with
      g1^3 W = -2 g1^2 D0),  B = 2 g1^2 <psi1|D0^[x]|psi2>  (D0 insertion chains at p = 0; affine form with thresholds
      (5, 13) at even x, (1, 9) at odd x).
      Delta A from delta_window (local shell windows); Delta B per chain t = (1/12) chain(R^{k-1}) - (1/6) chain(R^k mod):
      Delta t = (1/12) top_{(c-4, c]}[chain(R^{k-1})] - (1/6) { top_{(c-4, c]}[chain(R^k, even)] + chain(R^k, even - odd)(c-4) },
      the last chain carrying the exact constant difference c_even - c_odd (no subtraction of large values).
    Independent of the closed form delta_R5_closed (A5/v7 compare them)."""
    V0, V1, M0 = ("V", 0), ("V", 1), ("M", 0)
    dWA1 = delta_window(de1, h0, Lmax)
    dWA0 = delta_window(de0, h0, Lmax)

    def red(verts, sops):
        return K5.eval_chain(verts, sops, Lmax, ser, {ONE: ONE})[0][ONE]

    def dt(verts, pw, q):
        """Delta t at every cutoff c (array over cut4; used at c = 4L)."""
        pre = tuple([(1, 0)] * (len(verts) - 2))
        out = 0.0
        if pw > 1:
            out = K5.top(red(verts, pre + ((pw - 1, q),)), 0, 0, 4) / 12.0
        top_even = K5.top(red(verts, pre + ((pw, q, D0EVEN),)), 0, 0, 4)
        diff = K5.perp(red(verts, pre + ((pw, q, ("D0d", 5, 13, 1, 9)),)), 0)        # X_0 at cut4 c
        diff_m4 = np.concatenate([np.zeros(4), diff[:-4]])                             # value at c - 4
        return out - (top_even + diff_m4) / 6.0
    d = dict(VVV=dt((V0, V0, V0), 2, 0), VPV=dt((V0, V0), 3, 1), MV=dt((M0, V0), 2, 0), VV=dt((V0, V0), 2, 0),
             V1V=dt((V1, V0), 2, 0))
    out = {}
    for L in range(2, Lmax + 1, 2):
        c = 4 * L
        gg2, rr2 = res["g2"][c], res["r2"][c]
        dA = g1 ** 2 * (g1 ** 2 * dWA1[L] + (2 * g1 * gg2 - 2 * g1 ** 2) * dWA0[L])
        dB = 2 * g1 ** 2 * math.fsum([g1 ** 3 * d["VVV"][c], -(g1 ** 2 / 4.0) * d["VPV"][c], g1 * rr2 * d["MV"][c],
                                      g1 * gg2 * d["VV"][c], g1 ** 2 * d["V1V"][c]])
        out[L] = dA + dB
    return out


def compute(Lmax, res, ser, verbose=False):
    """Even-grid window pieces; res = assemble5.compute(...) on the same Lmax (raw run)."""
    sys.path.insert(0, os.path.join(HERE, "vendor"))
    import exact_fast
    V0, V1, M0 = ("V", 0), ("V", 1), ("M", 0)
    # bubble shells (p = 0) and outer |V|^2/E^2 shells (per p)
    de0 = p_shells((V0, V0), ((1, 0),), Lmax, ser)[0]
    de1 = 2 * p_shells((V1, V0), ((1, 0),), Lmax, ser)[0] - 0.25 * p_shells((V0, V0), ((2, 1),), Lmax, ser)[0]
    hp = p_shells((V0, V0), ((2, 0),), Lmax, ser)
    W_C, W_G = FUNCTIONALS["C"], FUNCTIONALS["g"]
    g2D4 = window_functional(hp, de0, W_C, Lmax)             # = dC4_g2D (= fast)
    dg4 = window_functional(hp, de0, W_G, Lmax)              # Delta g4^{g2D}
    T1w = window_functional(hp, de1, W_C, Lmax)              # T1
    # T3: chains with a D0 insertion (even L), D0 R^k = R^{k-1}/12 - (1/6)(c_P - (d+n)/8) R^k
    def d0chain(verts, pw, q, f=ONE):
        a = K5.eval_chain(verts, tuple([(1, 0)] * (len(verts) - 2)) + ((pw - 1, q),), Lmax, ser, {f: f})[0][f] \
            if pw > 1 else None
        b = K5.eval_chain(verts, tuple([(1, 0)] * (len(verts) - 2)) + ((pw, q, D0EVEN),), Lmax, ser, {f: f})[0][f]
        Fa = K5.functional(a, "C") / 12.0 if a is not None else 0.0
        return Fa - K5.functional(b, "C") / 6.0
    nc = 4 * Lmax + 1
    t3 = np.zeros(nc)
    # <psi1|D0|psi2> = g1^3 <V R D0 R V R V> - (g1^2/4) <V R D0 (P-p) R^2 V> - g1^3 Vpp <V D0 R^3 V>
    #                  + g1 r2 <V R D0 R M> + g1 g2 <V R D0 R V> + g1^2 <V R D0 R V1>
    # (first-acting vertex first; the D0 slice is the last slice, adjacent to the bra vertex)
    t3 += g1 ** 3 * d0chain((V0, V0, V0), 2, 0)
    t3 += -(g1 ** 2 / 4.0) * d0chain((V0, V0), 3, 1)
    t3 += -(g1 ** 3) * d0chain((V0, V0), 3, 0, pvec(vpp))
    t3 += g1 * res["r2"] * d0chain((M0, V0), 2, 0)
    t3 += g1 * res["g2"] * d0chain((V0, V0), 2, 0)
    t3 += g1 ** 2 * d0chain((V1, V0), 2, 0)
    T3 = 2 * g1 ** 2 * t3
    h = hp[0]
    dR4e = delta_R4_engine(de0, h, Lmax)
    dR5 = delta_R5_closed(res["g2"], Lmax)
    dR5e = delta_R5_engine(Lmax, res, ser, de0, de1, h)
    Ls = np.arange(2, Lmax + 1, 2)
    ev = {"L": Ls}
    c = 4 * Ls
    ev["fast_g2D"] = np.array([exact_fast.fast(int(L)) for L in Ls])
    ev["g2D_C4_engine"] = np.array([g2D4[int(L)] for L in Ls])
    ev["dR4"] = np.array([dR4e[int(L)] for L in Ls])
    ev["dR4_closed"] = np.array([h_odd(int(L) - 1) / 2916.0 for L in Ls])
    ev["dR5"] = np.array([dR5[int(L)] for L in Ls])
    ev["dR5_engine"] = np.array([dR5e[int(L)] for L in Ls])
    ev["A4"] = res["vacwinA4"][c] + ev["dR4"]
    ev["B4"] = res["vacwinB4"][c] + ev["dR4"]
    ev["B5"] = res["vacwinB5"][c] + ev["dR5"]
    ev["A5"] = res["vacwinA5"][c] + ev["dR5"]
    ev["vacodd5"] = res["vacodd5"][c]                      # must vanish at even L (P parity / N parity)
    ev["shift4"] = -ev["B4"] / 3.0
    ev["C4raw"] = res["C4"][c]
    ev["C4Dconn"] = ev["C4raw"] + ev["fast_g2D"] + ev["shift4"]
    C2 = res["C2"][c]
    ev["T1"] = np.array([T1w[int(L)] for L in Ls])
    ev["T2"] = 6 * res["g2"][c] * ev["fast_g2D"]
    ev["T3"] = T3[c]
    ev["dg4_g2D"] = np.array([dg4[int(L)] for L in Ls])
    ev["T4"] = 6 * C2 * ev["dg4_g2D"]
    ev["dC5_g2D"] = ev["T1"] + ev["T2"] + ev["T3"] + ev["T4"]
    ev["dC5_bubble"] = -2 * ev["fast_g2D"]
    ev["dC5_rows4"] = 2 * C2 * (3 * ev["A4"] - ev["B4"])
    ev["dC5_rows5"] = -ev["B5"] / 3.0
    ev["dC5_Dconn"] = ev["dC5_g2D"] + ev["dC5_bubble"] + ev["dC5_rows4"] + ev["dC5_rows5"]
    ev["C5raw"] = res["C5"][c]
    ev["C5Dconn"] = ev["C5raw"] + ev["dC5_Dconn"]
    return ev
