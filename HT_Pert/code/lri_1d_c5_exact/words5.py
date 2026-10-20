#!/usr/bin/env python3
"""Catalogue of the RS assembly at orders 2..nmax (PLAN.md sec. 3.1): rs5.unroll -> reduced words -> terms.

A term is  coef (Fraction) x coupling monomial (tuple of 'r_k'/'g_k') x f(p) (exact prefactor vector) x chain A
[x chain B]  (B only for the genuine products from E_k, k >= 2).  Symbol expansion:
  E1 -> g1 Vpp(p)  (shift trick);  E_k (k >= 2) -> X_k-terms (products) + 2p r_k + Vpp g_k.
Chains are canonicalised under reversal (verts and slice ops reversed; the chain value is reversal symmetric because
V_j, M_j are real symmetric and R, (P-p) diagonal).  chain_plan collects, per canonical chain, the prefactor vectors
needed for single-chain terms and whether key records are needed (product factors)."""
import hashlib
import json
from fractions import Fraction as Fr

import rs5
from lib5.common import G1, ONE, PS, pmul, pvec, vpp


def canon(verts, sops):
    a = (tuple(verts), tuple(tuple(s) for s in sops))
    b = (tuple(reversed(verts)), tuple(tuple(s) for s in reversed(sops)))
    return min(a, b, key=repr)


def raw_words(nmax):
    E = rs5.unroll(nmax)
    out = {}
    for n in range(1, nmax + 1):
        lst = []
        for (c, sy, ops, pw) in E[n]:
            r = rs5.reduce_word(ops, pw)
            if r is None or len(r[0]) < 2:
                continue             # single-vertex words: only the 2p r_n + Vpp g_n tuning (<p|V_j|p> = 0, j >= 1)
            lst.append((c, tuple(sy), tuple(r[0]), tuple(r[1])))
        out[n] = lst
    return out


def _split(sy):
    cpl = tuple(s for s in sy if s[0] in "rg")
    e1 = sum(1 for s in sy if s == "E1")
    ek = [int(s[1:]) for s in sy if s[0] == "E" and s != "E1"]
    return cpl, e1, ek


def terms(nmax):
    """{n: [dict(coef, cpl, f, A, B)]} for n = 2..nmax."""
    W = raw_words(nmax)
    out = {}
    e1f = pvec(lambda p: G1 * vpp(p))
    for n in range(2, nmax + 1):
        lst = []
        for (c, sy, verts, sops) in W[n]:
            cpl, e1, ek = _split(sy)
            if len(ek) > 1:
                raise NotImplementedError(f"product of two E_k at order {n}: {sy}")
            f = ONE
            for _ in range(e1):
                f = pmul(f, e1f)
            A = canon(verts, sops)
            if not ek:
                lst.append(dict(coef=c, cpl=cpl, f=f, A=A, B=None))
                continue
            k = ek[0]
            lst.append(dict(coef=c, cpl=cpl + (f"r{k}",), f=pmul(f, pvec(lambda p: 2 * p)), A=A, B=None))
            lst.append(dict(coef=c, cpl=cpl + (f"g{k}",), f=pmul(f, pvec(vpp)), A=A, B=None))
            for (c2, sy2, v2, s2) in W[k]:
                cpl2, e12, ek2 = _split(sy2)
                if ek2:
                    raise NotImplementedError(f"nested E_k inside X_{k}: {sy2}")
                f2 = f
                for _ in range(e12):
                    f2 = pmul(f2, e1f)
                lst.append(dict(coef=c * c2, cpl=cpl + cpl2, f=f2, A=A, B=canon(v2, s2)))
        out[n] = lst
    return out


def chain_plan(nmax):
    """{chain: {'prefs': set of f vectors, 'records': bool}} over all terms of orders 2..nmax."""
    plan = {}
    for n, lst in terms(nmax).items():
        for t in lst:
            if t["B"] is None:
                plan.setdefault(t["A"], {"prefs": set(), "records": False})["prefs"].add(t["f"])
            else:
                for X in (t["A"], t["B"]):
                    plan.setdefault(X, {"prefs": set(), "records": False})["records"] = True
    return plan


def catalogue_hash(nmax):
    T = terms(nmax)
    s = json.dumps({n: [[str(t["coef"]), t["cpl"], [str(x) for x in t["f"]], repr(t["A"]), repr(t["B"])]
                        for t in lst] for n, lst in T.items()}, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()


if __name__ == "__main__":
    T = terms(5)
    plan = chain_plan(5)
    for n in range(2, 6):
        npr = sum(1 for t in T[n] if t["B"] is not None)
        print(f"order {n}: {len(T[n])} terms ({npr} products)")
    byK = {}
    for (verts, sops), d in plan.items():
        byK.setdefault(len(verts), []).append(d)
    print("canonical chains by K:", {K: len(v) for K, v in sorted(byK.items())},
          "with records:", sum(1 for d in plan.values() if d["records"]),
          "max prefs per chain:", max(len(d["prefs"]) for d in plan.values()))
    print("catalogue sha256:", catalogue_hash(5))
