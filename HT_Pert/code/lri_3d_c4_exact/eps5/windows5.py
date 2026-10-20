#!/usr/bin/env python3
"""Diagonal window schemes at eps^4 and eps^5: consistent (D_k(N) = E_v^(k)(L) - E_v^(k)(L-N)) and zeromode
(D_k(z,N) = E_z^(k)(L) - E_z^(k)(L-N)).  Only D_2, D_3 enter E^(4), E^(5) (D vanishes on level 0, so D_k enters at
order >= k+2).  E_z^(2), E_z^(3) of the auxiliary channels do not contain D, so they are evaluated from the raw words
with the global couplings r2(L), g2(L):  E_z^(k)(l; L) = sum_kappa kappa(L) e_{z,kappa}(l),  kappa in {1, r2, g2}.

Window words (rs.unroll(windows=True)) with one ('D', k) atom are evaluated with engine.shell_w + window_contract:
    value(M) = sum_sigma R prod G [e(M) - e(M - sigma_w)],  per coupling monomial kappa (multiplied by kappa(M)).
"""
import numpy as np

import engine as eg
import chains as ch
import rs
import assemble as asm

P = (0, 1, 2, 3)


def channel_energy_parts(words, N, modes, zmax, kmax=3, verbose=False, partners=False):
    """e[(k, z)] = dict kappa -> array over l (only l-dependent parts matter for windows; single-vertex tuning
    terms are dropped).  kappa = tuple of coupling symbols (sorted); E1 is evaluated numerically."""
    zs = tuple(range(zmax + 1))
    out = {}
    for k in range(2, kmax + 1):
        for verts, lst in words[k].items():
            if any(v[0] == "D" for v in verts):
                continue
            kinds = [v[0] for v in verts]
            derivs = [v[1] for v in verts]
            uniq = sorted(set(s for (_, _, s) in lst))
            res = ch.eval_group(kinds, derivs, [(s, None) for s in uniq], N, modes, zs)
            val = dict(zip(uniq, res))
            for (c, sy, sops) in lst:
                kap = tuple(s for s in sy if not s.startswith("E"))
                for z in zs:
                    f = float(c)
                    for s in sy:
                        if s == "E1":
                            f *= (1.0 / 3.0) * z * (z - 1) / 2.0
                        elif s.startswith("E"):
                            raise ValueError("E_j with j >= 2 in a channel energy of order <= 3")
                    d = out.setdefault((k, z), {})
                    d[kap] = d.get(kap, np.zeros(N + 1)) + f * val[sops][z]
            if verbose:
                print("channel parts", k, kinds, derivs, flush=True)
    if kmax >= 3 and partners:  # 2D partner B-equation; not ported (3D: no partners below z = 9)
        raise NotImplementedError("partners")
        import partners as pt
        zp = tuple(z for z in (5, 6, 7) if z <= zmax)
        if zp:
            dE, _ = pt.dE3(modes, N, zp)
            for z in zp:
                d = out.setdefault((3, z), {})
                d[()] = d.get((), np.zeros(N + 1)) + dE[z]
    return out


def split_window_word(verts, sops):
    """word with exactly one ('D', k): returns (verts without D, merged slice ops, window slice index, k)."""
    di = [i for i, v in enumerate(verts) if v[0] == "D"]
    if len(di) != 1:
        raise ValueError("expected one window atom")
    i = di[0]
    if i == 0 or i == len(verts) - 1:
        return None                                   # D on |p> (level 0) vanishes
    k = verts[i][1]
    v2 = verts[:i] + verts[i + 1:]
    a, b = sops[i - 1], sops[i]
    s2 = sops[: i - 1] + ((a[0] + b[0], a[1] + b[1]),) + sops[i + 1:]
    return v2, s2, i - 1, k


def eval_window_group(kinds, derivs, wwords, N, modes, efun, ps=P, max_lines=None, min_zero_legs=0):
    """wwords: list of (slice_ops, sw, k).  efun(k, z) -> dict kappa -> e array (l = 0..N, hol units, z channel).
    Returns per word: dict kappa -> {p: array over M}."""
    K = len(kinds)
    res = [dict() for _ in wwords]
    pats = eg.patterns(kinds, max_lines, min_zero_legs)
    sops_list = [w[0] for w in wwords]
    for n in pats:
        r = ch.word_keyamps(kinds, n, ps, sops_list)
        if r is None:
            continue
        kas, nsl = r
        if not any(kas):
            continue
        legs = eg.legs_of(n, K)
        if any(derivs[i] > 0 and legs[i] == 0 for i in range(K)):
            continue
        Ns = [N if nsl[s] > 0 else 0 for s in range(K - 1)]
        R = None
        for wi, (sops, sw, k) in enumerate(wwords):
            ka = kas[wi]
            if not ka or nsl[sw] == 0:
                continue                              # window on a level-0 slice vanishes
            if R is None:
                R = eg.density(kinds, n, Ns, modes, derivs)
                if R is None:
                    break
            keys = list(ka)
            Gs = []
            for s in range(K - 1):
                Gs.append(np.array([eg.slice_G(eg.X0 * (kk[s] + nsl[s]), sops[s][0], nsl[s], Ns[s] + 1) for kk in keys]))
            f = eg.shell_w(R, Gs, N, sw)               # (T, Nsw+1, N+1)
            for t, kk in enumerate(keys):
                for p, a in ka[kk].items():
                    z = p + kk[sw]
                    for kap, e in efun(k, z).items():
                        val = eg.window_contract(f[t], e)
                        d = res[wi].setdefault(kap, {q: np.zeros(N + 1) for q in ps})
                        d[p] += float(a) * val
    return res


def window_extra(scheme, nmax, N, modes, couplings, Eraw, prune=True, zmax=11, verbose=True):
    """X^(n) contributions of the window words for n = 4..nmax (scheme 'consistent' or 'zeromode').
    couplings: dict 'r2','g2','r3','g3' -> arrays over L (scheme independent through order 3);
    Eraw: E[j][p] arrays for j <= 3 (scheme independent)."""
    words_raw = asm.collect_words(3)
    parts = channel_energy_parts(words_raw, N, modes, zmax if scheme == "zeromode" else 0)

    def efun(k, z):
        zz = 0 if scheme == "consistent" else z
        if (k, zz) not in parts:
            raise KeyError((k, zz))
        return parts[(k, zz)]

    wwords = asm.collect_words(nmax, windows=True)
    extra = {}
    for n in range(4, nmax + 1):
        acc = {p: np.zeros(N + 1) for p in P}
        groups = {}
        for verts, lst in wwords[n].items():
            nd = sum(1 for v in verts if v[0] == "D")
            if nd == 0:
                continue
            if verts[0][0] == "D" or verts[-1][0] == "D":
                continue                              # a diagonal window on |p> (level 0) vanishes
            if nd > 1:
                raise ValueError("two inner windows at order <= 5?")
            for (c, sy, sops) in lst:
                sp = split_window_word(verts, sops)
                if sp is None:
                    continue
                v2, s2, sw, k = sp
                key = tuple(v2)
                groups.setdefault(key, []).append((c, sy, s2, sw, k))
        for v2, lst in groups.items():
            kinds = [v[0] for v in v2]
            derivs = [v[1] for v in v2]
            uniq = sorted(set((s2, sw, k) for (_, _, s2, sw, k) in lst))
            kw = {}
            if prune and n == nmax and all(not any(s.startswith("E") for s in sy) for (_, sy, _, _, _) in lst):
                kw["min_zero_legs"] = 6
            res = eval_window_group(kinds, derivs, uniq, N, modes, efun, **kw)
            val = dict(zip(uniq, res))
            for (c, sy, s2, sw, k) in lst:
                for kap, d in val[(s2, sw, k)].items():
                    for p in P:
                        coef = np.full(N + 1, float(c))
                        for s in sy + kap:
                            if s.startswith("E"):
                                coef = coef * Eraw[int(s[1:])][p]
                            else:
                                coef = coef * couplings[s]
                        acc[p] = acc[p] + coef * d[p]
            if verbose:
                print(f"window n={n} {''.join(f'{k}{d}' for k, d in zip(kinds, derivs))} {len(uniq)} words {kw}",
                      flush=True)
        extra[n] = acc
    return extra
