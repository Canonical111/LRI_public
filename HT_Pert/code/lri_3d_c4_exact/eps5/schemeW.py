#!/usr/bin/env python3
"""C_2..C_5 in scheme W of ../WINDOW_SPEC.md and controlled sub-variants, for every even L <= Lmax.

Variants (window components included at each order):
  W2   : D^(2) = DZ2 + DM2 (full eps^2 windows; nothing at eps^3)
  W3m  : W2 + DM3   (chi mass window at eps^3: (1/4){Dc1^(3), M'_0} + (1/4){Dc1^(2), M'_1})
  W3e  : W3m + DZ3diag (eps^3 zero-mode window in eigenvalue-diagonal form E_z^(3)(L) - E_z^(3)(L-N), z' = z)
  (W   : W3m + DZ3 Bloch -- see windowsW_bloch.py)
All window l-functions are computed self-consistently in the variant (E_z^(3)(l) and c_1^(3)(l) include the eps^2
windows of the cutoff-l Hamiltonian).  usage: python3 schemeW.py --Lmax 18 --variants W2,W3m,W3e [--prune]"""
import argparse
import os
import time
from fractions import Fraction as Fr

import numpy as np

import engine as eg
import chains as ch
import rs
import assemble as asm
import windows5 as w5
import windowsW as ww

P = (0, 1, 2, 3)
G1 = 1.0 / 3.0
COMPONENTS = {"W2": {2: {"DZ", "DM"}, 3: set()},
              "W3m": {2: {"DZ", "DM"}, 3: {"DM"}},
              "W3e": {2: {"DZ", "DM"}, 3: {"DM", "DZ"}},
              "Wb": {2: {"DZ", "DM"}, 3: {"DM", "DZ"}},       # DZ3 = Bloch h^(3) window (no partner terms)
              "W3x": {2: {"DZ", "DM"}, 3: {"DM", "DZ"}},      # W3e with partner terms dropped (partner-effect probe)
              "Z2": {2: {"DZ"}, 3: set()},                     # zero-mode Bloch window at eps^2 only (class probe)
              "Zb": {2: {"DZ"}, 3: {"DZ"}},                    # zero-mode Bloch windows eps^2 + eps^3, no D^M (probe)
              "Wc": {2: {"DZ", "DM"}, 3: {"DM", "DZ"}}}       # Wb with auxiliary windows referenced to the outer L


def inner_functions(N, modes, zmax, raw_parts, verbose=False):
    """h2[(z', z)] (normalized, ket-referenced, Q = non-level-0) and c1_2 as l-arrays (kappa = ())."""
    h2 = {}
    for z in range(zmax + 1):
        for zp in range(max(0, z - 6), min(zmax, z + 6) + 1):
            if (zp - z) % 2:
                continue
            r = ch.eval_group(["V", "V"], [0, 0], [(((1, 0),), None)], N, modes, ps=(z,), z_end={z: zp},
                              exclude_level0=True)
            h2[(zp, z)] = G1 ** 2 * r[0][z]
    c1_2 = h2[(1, 1)] - h2[(0, 0)]
    return h2, c1_2


def word_list(nmax, comps_by_order):
    """window words per order: list of (coef, symbols, decorated variant)."""
    E = rs.unroll(nmax, windows=True)
    out = {}
    for n in range(2, nmax + 1):
        lst = []
        for (c, sy, ops, pw) in E[n]:
            if not any(a[0] == "D" for a in ops):
                continue
            # D_k components allowed for this variant
            ok = all(a[0] != "D" or a[1] in comps_by_order for a in ops)
            if not ok:
                continue
            comps = set()
            for k, cs in comps_by_order.items():
                comps |= cs
            for f, ops2, pw2 in ww.expand_windows(ops, pw, comps):
                # keep only components allowed at their own order
                good = True
                for a in ops2:
                    if a[0] in ("DZ", "DM", "DV"):
                        k = a[1]
                        if a[0] not in comps_by_order.get(k, set()):
                            good = False
                    if a[0] == "DM" and a[1] == 3 and a[2] not in (0, 1):
                        good = False
                if not good:
                    continue
                for var in ww.decorate(ops2, pw2):
                    lst.append((c * f, sy, var))
        out[n] = lst
    return out


def run(Lmax, variants, nmax=5, prune=False, verbose=True):
    N = Lmax // 2
    modes = eg.Modes(N, 3)
    t0 = time.time()
    words = asm.collect_words(nmax)
    vals = asm.evaluate_words(words, nmax, N, modes, prune=prune, verbose=False)
    raw = asm.assemble(words, vals, nmax, N)
    if verbose:
        print(f"[{time.time() - t0:7.1f}s] raw words done", flush=True)
    zmax = 11
    parts3 = w5.channel_energy_parts(asm.collect_words(3), N, modes, zmax, partners=False)     # raw E_z^(3)(l) parts, kappa in {(),r2,g2}
    parts3np = w5.channel_energy_parts(asm.collect_words(3), N, modes, zmax, partners=False)
    parts2 = w5.channel_energy_parts(asm.collect_words(2), N, modes, zmax, kmax=2)
    h2, c1_2 = inner_functions(N, modes, zmax, None)
    if verbose:
        print(f"[{time.time() - t0:7.1f}s] inner functions done", flush=True)
    results = {"raw": raw}
    for var in variants:
        comps = COMPONENTS[var]
        P3 = parts3np if var == "Wb" else parts3
        # ---- self-consistent eps^3 channel energies of the variant: raw + 2 g1 <z|V R DM2_l|z> (DZ2 vanishes on |z>)
        dm2_ind = {}
        if "DM" in comps[2]:
            v, s, w = ([("V", 0, 0), ("M", 0, 1)], [([(1, 0)], [])], [(0, ("DM", 2, 0))])
            vv = ww.eval_decorated(v, s, w, N, modes, lambda spec, p, zs: {(): 0.25 * c1_2},
                                   ps=tuple(range(zmax + 1)))
            # word order: M acts first? decorate convention: verts[0] acts first -> V first, M (DM) last.
            for z in range(zmax + 1):
                dm2_ind[z] = 2 * G1 * vv[()][z]
        def E3parts(z):
            d = {k: v.copy() for k, v in P3[(3, z)].items()}
            if z in dm2_ind:
                d[()] = d.get((), 0) + dm2_ind[z]
            return d
        c1_3 = {}
        for kap in set(E3parts(1)) | set(E3parts(0)):
            c1_3[kap] = E3parts(1).get(kap, 0) - E3parts(0).get(kap, 0)

        def wfun(spec, p, zs):
            if spec[0] == "DM":
                k, j = spec[1], spec[2]
                if k - j == 2:
                    return {(): 0.25 * c1_2}
                if k - j == 3:
                    return {kap: 0.25 * arr for kap, arr in c1_3.items()}
                raise KeyError(spec)
            if spec[0] == "DZ":
                k, ji = spec[1], spec[2]
                zb, za = zs[ji], zs[ji + 1]
                if k == 2:
                    if (za, zb) not in h2:
                        raise KeyError((za, zb))
                    return {(): h2[(za, zb)]}
                if k == 3 and H3 is not None:       # Bloch form
                    return H3.get((za, zb), {(): np.zeros(N + 1)})
                if k == 3:                          # eigenvalue-diagonal form
                    if za != zb:
                        return {(): np.zeros(N + 1)}
                    return E3parts(zb)
            raise KeyError(spec)

        H3 = None
        if var == "Wb":
            import bloch
            inn = dict(parts2=parts2, parts3=parts3np, h2=h2, c1_2=c1_2, dm2_ind=dm2_ind)
            H3 = bloch.compute_H3(N, modes, inn, comps)
            if verbose:
                print(f"[{time.time() - t0:7.1f}s] Bloch h3 done", flush=True)
        wl = word_list(nmax, comps)
        wvals = {}
        for n in range(3, nmax + 1):
            for idx, (c, sy, (verts, slices, windows)) in enumerate(wl[n]):
                kw = {}
                if prune and n == nmax and not any(s.startswith("E") for s in sy) and \
                        not any(sp[0] == "DZ" for _, sp in windows):
                    kw["min_zero_legs"] = 6
                wvals[(n, idx)] = ww.eval_decorated(verts, slices, windows, N, modes, wfun, **kw)
            if verbose:
                print(f"[{time.time() - t0:7.1f}s] {var}: {len(wl[n])} window words at order {n}", flush=True)
        # ---- assembly order by order
        E = {1: raw["E"][1]}
        r = {1: np.zeros(N + 1)}
        g = {1: np.full(N + 1, G1)}
        C, X = {}, {}
        coup = lambda s: (r if s[0] == "r" else g)[int(s[1:])]
        for n in range(2, nmax + 1):
            Xn = {p: np.zeros(N + 1) for p in P}
            for verts, lst in words[n].items():
                for (c, sy, sops) in lst:
                    val = vals[(n, verts, sops)]
                    for p in P:
                        coef = np.full(N + 1, float(c))
                        for s in sy:
                            coef = coef * (E[int(s[1:])][p] if s[0] == "E" else coup(s))
                        Xn[p] = Xn[p] + coef * val[p]
            for idx, (c, sy, _) in enumerate(wl.get(n, [])):
                for kap, d in wvals[(n, idx)].items():
                    for p in P:
                        coef = np.full(N + 1, float(c))
                        for s in tuple(sy) + tuple(kap):
                            coef = coef * (E[int(s[1:])][p] if s[0] == "E" else coup(s))
                        Xn[p] = Xn[p] + coef * d[p]
            X[n] = Xn
            r[n] = -(Xn[1] - Xn[0]) / 2.0
            g[n] = -(Xn[3] - Xn[0] + 6.0 * r[n]) / 3.0
            E[n] = {p: Xn[p] + 2 * p * r[n] + p * (p - 1) / 2.0 * g[n] for p in P}
            C[n] = asm.Pi(Xn)
        results[var] = dict(C=C, r=r, g=g, E=E)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=12)
    ap.add_argument("--variants", default="W2,W3m,W3e")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.Lmax, a.variants.split(","), prune=a.prune)
    N = a.Lmax // 2
    for var, d in res.items():
        for i in range(N + 1):
            print(f"{var:5s} L={2*i:4d} " + " ".join(f"C{n}={d['C'][n][i]:+.12f}" for n in range(2, 6))
                  + f"  r3={d['r'][3][i]:+.10f} g3={d['g'][3][i]:+.10f} r4={d['r'][4][i]:+.10f} g4={d['g'][4][i]:+.10f}")
    if a.out:
        out = {"L": 2 * np.arange(N + 1)}
        for var, d in res.items():
            for n in range(2, 6):
                out[f"{var}_C{n}"] = d["C"][n]
                out[f"{var}_r{n}"] = d["r"][n]
                out[f"{var}_g{n}"] = d["g"][n]
        np.savez(a.out, **out)


if __name__ == "__main__":
    main()
