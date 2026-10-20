#!/usr/bin/env python3
"""
Independent non-perturbative check of the eps-series (third code path).

For a given scheme and cutoff L, take the exact series r(eps), g(eps) and vacuum series E_v(l) from
results/<scheme>_L<L>.json, build the truncated Hamiltonian at a small numeric eps directly in the
ORTHONORMAL occupation basis (full J=0 sector, both reflection parities, sqrt(w) and sqrt(n) factors),
with matrix elements computed PAIRWISE from

  <n'| :phi^k:_theta |n> = k! sum_U prod_m w_m^{(s_m+t_m)/2} sqrt(n_m! n'_m!) / ((n_m-t_m)! s_m! t_m!)

(S = (n'-n)_+ + U created, T = (n-n')_+ + U annihilated, |S|+|T| = k), and find the eigenvalue analytically
connected to |p> by shifted inverse iteration (shift = series value) + Rayleigh quotient in mpmath.

Checks (each should be O(eps^9)):
   E_1 - E_0 - x(eps),  E_3 - E_0 - (2 - x(eps)),  E_2 - E_0 - sum_n C_n eps^n,  E_p - sum_n E_p^(n) eps^n,
   and for consistent/literal every vacuum E_v(l) (consistent: of its own corrected Hamiltonian; literal: raw).
"""
import argparse, json, sys, time
from fractions import Fraction as Fr
from math import factorial, comb
import mpmath as mp


def poch(x, a):
    r = mp.mpf(1)
    for i in range(a):
        r *= (x + i)
    return r


def states_J0(L, parity, Pmax):
    modes = [(a, n - a) for n in range(L + 1) for a in range(n + 1)]
    out = []

    def rec(i, lev, J, P, occ):
        if i == len(modes):
            if J == 0 and P % 2 == parity:
                out.append(dict(occ))
            return
        a, b = modes[i]
        n = a + b
        k = 0
        while lev + k * n <= L and P + k <= Pmax:
            if k:
                occ[(a, b)] = k
            else:
                occ.pop((a, b), None)
            rec(i + 1, lev + k * n, J + k * (a - b), P + k, occ)
            k += 1
        occ.pop((a, b), None)

    rec(0, 0, 0, 0, {})
    return out


def vertex_element(k, n, n2, w):
    """<n2| :phi^k:_theta |n> in the orthonormal basis (pairwise formula)."""
    modes = set(n) | set(n2)
    S0 = {m: n2.get(m, 0) - n.get(m, 0) for m in modes if n2.get(m, 0) > n.get(m, 0)}
    T0 = {m: n.get(m, 0) - n2.get(m, 0) for m in modes if n.get(m, 0) > n2.get(m, 0)}
    s0, t0 = sum(S0.values()), sum(T0.values())
    rem = k - s0 - t0
    if rem < 0 or rem % 2:
        return mp.mpf(0)
    u = rem // 2
    # spectator multisets U with U_m <= n_m - T0_m
    avail = [(m, n.get(m, 0) - T0.get(m, 0)) for m in sorted(n) if n.get(m, 0) - T0.get(m, 0) > 0]
    total = mp.mpf(0)

    def rec(i, left, U):
        nonlocal total
        if left == 0:
            term = mp.mpf(factorial(k))
            for m in modes:
                um = U.get(m, 0)
                s = S0.get(m, 0) + um
                t = T0.get(m, 0) + um
                if s + t == 0:
                    continue
                nm, n2m = n.get(m, 0), n2.get(m, 0)
                term *= mp.power(w[m], mp.mpf(s + t) / 2) * mp.sqrt(mp.mpf(factorial(nm) * factorial(n2m)))
                term /= factorial(nm - t) * factorial(s) * factorial(t)
            total += term
            return
        if i == len(avail):
            return
        m, cap = avail[i]
        for c in range(0, min(cap, left) + 1):
            if c:
                U[m] = c
            rec(i + 1, left - c, U)
        U.pop(m, None)

    rec(0, u, {})
    return total


def build(L, parity, Pmax, eps, rser, gser, Dfun_l=None):
    x = mp.mpf(1) / 2 - eps / 4
    w = {}
    for n in range(L + 1):
        for a in range(n + 1):
            b = n - a
            w[(a, b)] = poch(x, a) * poch(x, b) / (factorial(a) * factorial(b))
    sts = states_J0(L, parity, Pmax)
    dim = len(sts)
    rv = sum(mp.mpf(Fr(c).numerator) / Fr(c).denominator * eps ** k for k, c in enumerate(rser))
    gv = sum(mp.mpf(Fr(c).numerator) / Fr(c).denominator * eps ** k for k, c in enumerate(gser))
    H = mp.matrix(dim, dim)
    lev = [sum((a + b) * c for (a, b), c in s.items()) for s in sts]
    P = [sum(s.values()) for s in sts]
    for i in range(dim):
        for j in range(i, dim):
            m2 = vertex_element(2, sts[j], sts[i], w)
            m4 = vertex_element(4, sts[j], sts[i], w) / 12
            val = rv * m2 + gv * m4
            if i == j:
                val += lev[i] + P[i] * x
                if Dfun_l is not None:
                    val += Dfun_l(lev[i])
            H[i, j] = val
            H[j, i] = val
    return sts, H, lev, P


def eig_near(H, idx, sigma, iters=3):
    dim = H.rows
    A = H - sigma * mp.eye(dim)
    # factorise once (mp.lu_solve would re-factorise a copy on every call)
    LU, perm = mp.mp.LU_decomp(A.copy(), use_cache=False)
    v = mp.matrix(dim, 1)
    v[idx] = 1
    for _ in range(iters):
        y = mp.mp.U_solve(LU, mp.mp.L_solve(LU, v.copy(), perm))
        nrm = mp.sqrt(sum(y[i] ** 2 for i in range(dim)))
        v = y / nrm
    Hv = H * v
    return sum(v[i] * Hv[i] for i in range(dim)) / sum(v[i] ** 2 for i in range(dim))


def series_val(coeffs, eps):
    return sum(mp.mpf(Fr(c).numerator) / Fr(c).denominator * eps ** k for k, c in enumerate(coeffs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--eps", default="1e-3,5e-4")
    ap.add_argument("--Kdiag", type=int, default=24)
    ap.add_argument("--dps", type=int, default=90)
    a = ap.parse_args()
    mp.mp.dps = a.dps
    R = json.load(open(a.json))
    L, scheme = R["L"], R["scheme"]
    rser, gser = R["r"], R["g"]
    Cser = R["C"]
    Eser = R["E"]
    vac = {int(l): v for l, v in R["vacua"].items()}
    out = {"scheme": scheme, "L": L, "Kdiag": a.Kdiag, "checks": {}}
    for es in a.eps.split(","):
        eps = mp.mpf(es)
        t0 = time.time()

        def Dfun_from(l, vacd):
            def D(N):
                return series_val([Fr(vacd[l][k]) - Fr(vacd[l - N][k]) for k in range(9)], eps)
            return D

        E = {}
        cache = {}

        def H_for(l, parity, D):
            key = (l, parity, D is None)
            if key not in cache:
                cache[key] = build(l, parity, (2 if parity == 0 else 3) + a.Kdiag, eps, rser, gser,
                                   None if D is None else Dfun_from(*D))
            return cache[key]

        # primaries at cutoff L
        Dprim = None if scheme == "raw" else (L, vac)
        for p in range(4):
            sts, H, lev, P = H_for(L, p % 2, Dprim)
            idx = [i for i, s in enumerate(sts) if s == ({(0, 0): p} if p else {})][0]
            E[p] = eig_near(H, idx, series_val(Eser[p], eps))
        x = mp.mpf(1) / 2 - eps / 4
        chk = {
            "tune1: E1-E0-x": E[1] - E[0] - x,
            "tune3: E3-E0-(2-x)": E[3] - E[0] - (2 - x),
            "Delta - sum C_n eps^n": E[2] - E[0] - series_val(Cser, eps),
        }
        for p in range(4):
            chk[f"E_{p} - series"] = E[p] - series_val(Eser[p], eps)
        if scheme in ("consistent", "literal"):
            for l in sorted(vac):
                if scheme == "consistent":
                    sts, H, lev, P = build(l, 0, 2 + a.Kdiag, eps, rser, gser, Dfun_from(l, vac))
                else:
                    sts, H, lev, P = build(l, 0, 2 + a.Kdiag, eps, rser, gser, None)
                idx = [i for i, s in enumerate(sts) if s == {}][0]
                ev = eig_near(H, idx, series_val(vac[l], eps))
                chk[f"vacuum l={l} - series"] = ev - series_val(vac[l], eps)
        out["checks"][es] = {k: mp.nstr(v, 6) for k, v in chk.items()}
        out["checks"][es + " /eps^9"] = {k: mp.nstr(v / eps ** 9, 8) for k, v in chk.items()}
        out["checks"][es]["eps^9"] = mp.nstr(eps ** 9, 3)
        out["checks"][es]["max|res|/eps^9"] = mp.nstr(max(abs(v) for v in chk.values()) / eps ** 9, 6)
        print(f"# eps={es}  ({time.time()-t0:.1f}s)", flush=True)
        for k, v in out["checks"][es].items():
            print(f"   {k:28s} {v:>14s}   (/eps^9: {out['checks'][es + ' /eps^9'].get(k, '')})", flush=True)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
