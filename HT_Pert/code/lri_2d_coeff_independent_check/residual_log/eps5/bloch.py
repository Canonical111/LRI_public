#!/usr/bin/env python3
"""Third-order Bloch effective Hamiltonian of the level-0 sector, h^(3)_{z'z}(l), for WINDOW_SPEC component D^zm,(3).

h = X Lambda X^-1 (X_{z'z} = <z'|psi_z>, intermediate normalization), via the recursion (spec Sec. 2.3), unshifted
W_1 = -P/4 + g1 V:
  z' != z: h3_{z'z} = ((z-z')/2) X3_{z'z} + E1_z X2_{z'z} + E2_z X1_{z'z} - sum_{z''!=z} [h1_{z'z''} X2_{z''z} + h2_{z'z''} X1_{z''z}]
  z' == z: h3_{zz}  = E3_z - sum_{z''!=z} [h1_{zz''} X2_{z''z} + h2_{zz''} X1_{z''z}]
X1, h1, E1 are level-0 (cutoff independent).  The cutoff-dependent part of X2_{z''z} is h2_{z''z}(l)/((z-z'')/2) (the
same second-order window object), so every term carries exactly one cutoff-dependent factor except E2 x (word) terms
inside X3.  X3_{z'z}(l) = <z'|psi_3> is evaluated from the open psi_3 words of rs.unroll (windows expanded as in the
variant: D_2 = DZ2 + DM2), ending on the level-0 state |z'>.  Only cutoff-dependent parts are kept (windows).
Partners (z >= 5): not included (partner_mode='drop'); their contribution to the windows is convergent and vanishes
as L -> inf (README); exact finite-L validation uses the same convention in the brute force.
"""
from fractions import Fraction as Fr
from math import comb

import numpy as np

import engine as eg
import rs
import windowsW as ww
import schemeW as sw

G1 = 1.0 / 3.0
DEBUG_X3 = {}


def V0(zp, z):
    """<z'|V|z> at level 0 (normalized) = (1/12) <z'| :Z^4: |z>."""
    tot = 0.0
    for rs_, amp in eg.zero_mode_paths(z, [4], zp):
        tot += float(amp)
    return tot / 12.0


def decorate_open(ops, pw):
    """open psi word (pw has len(ops): last = R power on the final level-0 state).  Returns (variants, qfinal, afinal)
    or None: trailing P atoms act on the final state -> factor (z' - z)^qfinal."""
    ops = list(ops)
    pw = list(pw)
    afinal = pw[-1]
    q = 0
    while ops and ops[-1][0] == "P":
        ops.pop()
        afinal += pw[-2] if len(pw) >= 2 else 0
        pw.pop()
        q += 1
        # R powers: the R after the removed P is merged with the final R
    if not ops or ops[0][0] == "P" or ops[-1][0] == "DZ":
        return None
    inner_pw = pw[:-1]
    return ww.decorate(tuple(ops), tuple(inner_pw)), q, afinal


def X3_words(comps):
    """psi_3 terms with windows expanded: list of (coef Fr, symbols, variant, qfinal, afinal)."""
    E, psi = rs.unroll(3, windows=True, return_psi=True)
    out = []
    allc = set()
    for k, cs in comps.items():
        allc |= cs
    for (c, sy, ops, pw) in psi[3]:
        if any(a[0] == "D" and a[1] >= 3 for a in ops):
            continue                                   # D_3|z> has no P0 component
        if any(a[0] == "D" for a in ops) and not comps.get(2):
            continue
        for f, ops2, pw2 in ww.expand_windows(ops, pw, comps.get(2, set())):
            r = decorate_open(ops2, pw2)
            if r is None:
                continue
            variants, q, af = r
            for var in variants:
                if len(var[0]) < 2:
                    continue                           # single level-0 matrix element: cutoff independent
                out.append((c * f, sy, var, q, af))
    return out


def compute_H3(N, modes, inn, comps, zk=range(0, 7), zpmax=6, couplings=None, with_dm=True):
    """returns H3[(z', z)] = dict kappa -> l-array (cutoff-dependent part of h^(3)_{z'z}(l)).
    inn: dict with parts2, parts3, h2, c1_2, dm2_ind.  couplings: needed only for r2, g2 symbols -> kept as kappa."""
    parts2, parts3, h2, c1_2, dm2 = inn["parts2"], inn["parts3"], inn["h2"], inn["c1_2"], inn["dm2_ind"]
    zmax_tab = max(z for (z, _) in h2)
    words = X3_words(comps)

    def wfun(spec, p, zs):
        if spec[0] == "DM":
            return {(): 0.25 * c1_2}
        k, ji = spec[1], spec[2]
        zb, za = zs[ji], zs[ji + 1]
        return {(): h2[(za, zb)]}

    def kadd(d, kap, arr):
        kap = tuple(sorted(kap))
        d[kap] = d.get(kap, 0) + arr

    H3 = {}
    eg.DROP_ZERO_DEN = True
    try:
        _fill(H3, zk, zpmax, zmax_tab, words, N, modes, wfun, kadd, parts2, parts3, h2, dm2, with_dm)
    finally:
        eg.DROP_ZERO_DEN = False
    return H3


def _fill(H3, zk, zpmax, zmax_tab, words, N, modes, wfun, kadd, parts2, parts3, h2, dm2, with_dm):
    for z in zk:
        E1u = -z / 4.0 + G1 * z * (z - 1) / 2.0
        X1 = {zz: (G1 * V0(zz, z) / ((z - zz) / 2.0) if zz != z else 0.0) for zz in range(0, zmax_tab + 1)}
        X2 = {zz: (h2[(zz, z)] / ((z - zz) / 2.0)) for zz in range(0, zmax_tab + 1) if zz != z and (zz, z) in h2}
        E2l = parts2[(2, z)][()]
        # X3 for all z' (needed z' <= zpmax only)
        for zp in range(0, zpmax + 1):
            if (zp - z) % 2 or zp == z:
                continue
            X3 = {}
            for (c, sy, (verts, slices, windows), q, af) in words:
                vals = ww.eval_decorated(verts, slices, windows, N, modes, wfun, ps=(z,), z_end={z: zp})
                if not vals:
                    continue
                fin = float((zp - z) ** q) * (2.0 / (z - zp)) ** af
                for kap, d in vals.items():
                    base = float(c) * fin * d[z]
                    # coefficient symbols
                    terms = [((), base)]
                    for s in sy:
                        new = []
                        for (kk, arr) in terms:
                            if s == "E1":
                                new.append((kk, arr * G1 * z * (z - 1) / 2.0))
                            elif s == "E2":
                                new.append((kk, arr * E2l))                      # cutoff-dependent part
                                new.append((kk + ("r2",), arr * 2 * z))         # 2z r2 + C(z,2) g2 (constant parts)
                                new.append((kk + ("g2",), arr * z * (z - 1) / 2.0))
                            else:
                                new.append((kk + (s,), arr))
                        terms = new
                    for (kk, arr) in terms:
                        kadd(X3, tuple(kap) + kk, arr)
            DEBUG_X3[(zp, z)] = dict(X3)
            # h3 (z' != z)
            out = {}
            for kap, arr in X3.items():
                kadd(out, kap, ((z - zp) / 2.0) * arr)
            if zp in X2:
                kadd(out, (), E1u * X2[zp])
            # (the recursion's + E2 X1 term cancels exactly against the single-vertex psi_3 word -E2 R psi_1, which
            #  X3_words drops; both are omitted -- keeping only one of them was the bug fixed 2026-10-09)
            for zz in range(0, zmax_tab + 1):
                if zz == z:
                    continue
                h1 = (-zz / 4.0 if zz == zp else 0.0) + G1 * V0(zp, zz)
                if zz in X2 and h1 != 0.0:
                    kadd(out, (), -h1 * X2[zz])
                if X1.get(zz, 0.0) != 0.0 and (zp, zz) in h2:
                    kadd(out, (), -h2[(zp, zz)] * X1[zz])
            H3[(zp, z)] = out
        # diagonal
        out = {}
        for kap, arr in parts3[(3, z)].items():
            kadd(out, kap, arr)
        if with_dm:
            kadd(out, (), dm2[z])
        for zz in range(0, zmax_tab + 1):
            if zz == z:
                continue
            h1 = G1 * V0(z, zz)
            if zz in X2 and h1 != 0.0:
                kadd(out, (), -h1 * X2[zz])
            if X1.get(zz, 0.0) != 0.0 and (z, zz) in h2:
                kadd(out, (), -h2[(z, zz)] * X1[zz])
        H3[(z, z)] = out


# ------------------------------------------------------------------------------------ outer-referenced aux windows
def X3_words_Mp():
    """psi_3 terms linear in a plain M'_0 insertion at eps^2 (the D_2 atom replaced by M' with unit coefficient, no
    window): list of (coef, symbols, (verts, slices, windows_without_DM), qfinal, afinal)."""
    E, psi = rs.unroll(3, windows=True, return_psi=True)
    out = []
    for (c, sy, ops, pw) in psi[3]:
        nd = sum(1 for a in ops if a[0] == "D")
        if nd != 1 or any(a[0] == "D" and a[1] != 2 for a in ops):
            continue
        for f, ops2, pw2 in ww.expand_windows(ops, pw, {"DM"}):
            r = decorate_open(ops2, pw2)
            if r is None:
                continue
            variants, q, af = r
            if not variants:
                continue
            verts, slices, windows = variants[0]
            if len(verts) < 2:
                continue
            out.append((c * f, sy, (verts, slices, [w for w in windows if w[1][0] != "DM"]), q, af))
    return out


def compute_H3_Mp(N, modes, A_E, zk=range(0, 7), zpmax=6):
    """Response of the Bloch h^(3)_{z'z}(l) to adding M'_0 (unit coefficient) at eps^2 to the auxiliary Hamiltonian:
    off-diagonal ((z - z')/2) X3^{M'}; diagonal 2 g1 <z|M' R V|z> = 2 g1 A_E[z].  Returns {(z', z): {(): l-array}}."""
    words = X3_words_Mp()
    H = {}
    eg.DROP_ZERO_DEN = True
    try:
        for z in zk:
            for zp in range(0, zpmax + 1):
                if (zp - z) % 2 or zp == z:
                    continue
                acc = np.zeros(N + 1)
                for (c, sy, (verts, slices, windows), q, af) in words:
                    vals = ww.eval_decorated(verts, slices, windows, N, modes, None, ps=(z,), z_end={z: zp})
                    if not vals:
                        continue
                    fin = float((zp - z) ** q) * (2.0 / (z - zp)) ** af
                    for kap, d in vals.items():
                        v = float(c) * fin * d[z]
                        for s in sy:
                            if s == "E1":
                                v = v * (G1 * z * (z - 1) / 2.0)
                            else:
                                raise ValueError(f"unexpected symbol {s} in an M' word")
                        acc = acc + v
                H[(zp, z)] = {(): ((z - zp) / 2.0) * acc}
            H[(z, z)] = {(): 2 * G1 * A_E[z]}
    finally:
        eg.DROP_ZERO_DEN = False
    return H
