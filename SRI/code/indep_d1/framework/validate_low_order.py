#!/usr/bin/env python3
"""
validate_low_order.py -- validation of the response->beta map with known closed forms.

(A) b3 sector, computed from scratch (no archived numbers used as inputs).
    b3 = C3_1 + 2 v j1  =>  a = C3_1_v - 4, p = C3_1_d + 4, A = C3_1_vv/2, E = C3_1_vd + 4,
    V = C3_1_dd/2 - 4, alpha = C3_1_vvv/6, beta = C3_1_vvd/2, gamma = C3_1_vdd/2 - 4,
    W = C3_1_ddd/6 + 4   (X_1_... = [eps^0 l^1] of the derivative).
    The single logarithm of a three-kink derivative follows from the cutoff-boundary identity
    (note eq:EulerBoundary)  [eps^0 l] M = -[eps^0 l^0] B,  B = -eps dM/deps:
       B = 2 int_1^{1/eps-1} ds (1 - eps(1+s)) (1+s)^2/s^2 P(l, l+log s, l+log(1+s))
    with P = (d_v^i d_delta^j W)/W the insertion polynomial (r=eps on the face, t=eps*s).
    Only the l^0 part P0(Ls,L1) contributes to [eps^0 l^0]B, and for derivative kernels
       [eps^0 l^0] B = 2 [ G1 - sum_m g_m (-1)^m m! ],   g(Ls) = dP0/dL1 |_{L1=Ls} = sum g_m Ls^m,
       G1 = int_1^oo [ (1+1/s)^2 P0(log s, log(1+s)) - g(log s)/s ] ds.
    C3 = A3 - A1 Z2 (A1=1 at eta=0); the Z2 parts come from the exact two-kink sector.
    -> a,p,A,E compared with closed forms; V,alpha,beta,gamma,W compared with ARCHIVED numbers
       (comparison only).
(B) c, b, f from the note's displayed low-order expansions (lines 548-557, 2110-2233, 1707-1714):
    C3 = 2l^2+5l+3-2z2, d_vC3 (l.2231), K4 (l.551), C5 single log (l.555), F40 (l.2117),
    Mellin data for Q4 and d_v Q4 (l.1707-1709) with P4, R4 closed forms (l.529-530).
    Two-kink pieces (Q2, Z2 and derivatives, EE Q2) from the exact internal sector.
"""
import json
import math
import os
import sys

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lri_framework as L  # noqa: E402

DPS = 40
mp.mp.dps = DPS
OUT = os.path.join(HERE, "out")
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


# ---------------------------------------------------------------------------
# (A) three-kink single logs
# ---------------------------------------------------------------------------
S1, S2, S3, S4, zz, dd = sp.symbols("S1 S2 S3 S4 zz dd")
Ls, L1 = sp.symbols("Ls L1")


def insertion_poly(i, j):
    """(d_v^i d_delta^j W)/W at v=1, delta=0 as polynomial in S_k = sum_{pairs} q q log^k"""
    expo = 2 * zz * S1 + 2 * (1 + zz) * (dd * S2 / 2 + dd ** 2 * S3 / 6 + dd ** 3 * S4 / 24)
    ser = sp.series(sp.exp(expo), zz, 0, i + 1).removeO()
    ser = sp.series(ser, dd, 0, j + 1).removeO()
    coef = sp.expand(ser).coeff(zz, i).coeff(dd, j)
    return sp.expand(coef * sp.factorial(i) * sp.factorial(j))


def three_kink_single_log(i, j):
    P = insertion_poly(i, j)
    # face r = eps: log r -> l, log t -> l + Ls, log(r+t) -> l + L1 ; l^0 part: log r -> 0
    Sk = {S1: -Ls + L1, S2: -Ls ** 2 + L1 ** 2, S3: -Ls ** 3 + L1 ** 3, S4: -Ls ** 4 + L1 ** 4}
    P0 = sp.expand(P.subs(Sk))
    assert sp.expand(P0.subs(L1, Ls)) == 0          # derivative kernels vanish at x^0
    gpoly = sp.Poly(sp.expand(sp.diff(P0, L1).subs(L1, Ls)), Ls)
    gm = {m[0]: c for m, c in gpoly.terms()}
    corr = sum(c * (-1) ** m * sp.factorial(m) for m, c in gm.items())
    # P0(Ls, Ls+d) = sum_n d^n R_n(Ls)
    dsym = sp.Symbol("d")
    Pd = sp.Poly(sp.expand(P0.subs(L1, Ls + dsym)), dsym)
    R = {}
    for (n,), c in Pd.terms():
        R[n] = sp.lambdify(Ls, c, "mpmath")
    g1 = sp.lambdify(Ls, gpoly.as_expr(), "mpmath")
    assert 0 not in R or sp.expand(Pd.as_expr().subs(dsym, 0)) == 0

    def integrand(x):     # s = 1/x
        with mp.workdps(2 * DPS):
            x = mp.mpf(x)
            Lsv = -mp.log(x)
            d = mp.log1p(x)
            tot = mp.mpf(0)
            for n, f in R.items():
                if n == 0:
                    continue
                tot += d ** n * f(Lsv)
            val = ((1 + x) ** 2 * tot - x * g1(Lsv)) / x ** 2
        return +val
    G1 = mp.quad(integrand, [0, mp.mpf(1) / 64, mp.mpf(1) / 8, 1])
    B00 = 2 * (G1 - mp.mpf(str(sp.N(corr, 60))))
    A3_1 = -B00
    # subtract the two-kink normalization:  [l^1] d^{ij} Z2  (Taylor * i! j!)
    z2t = L.two_kink("Z", i, j, 0, 2, None, DPS).get((0, 1), mp.mpf(0)) * math.factorial(i) * math.factorial(j)
    return A3_1 - z2t, A3_1, z2t


def part_A():
    log("=" * 78)
    log("(A) b3 sector from three-kink boundary single logs (independent integration)")
    log("=" * 78)
    beta_cf, _ = L.closed_forms(DPS)
    need = {"v": (1, 0), "d": (0, 1), "vv": (2, 0), "vd": (1, 1), "dd": (0, 2),
            "vvv": (3, 0), "vvd": (2, 1), "vdd": (1, 2), "ddd": (0, 3)}
    C31 = {}
    for nm, (i, j) in need.items():
        c, a3, z2t = three_kink_single_log(i, j)
        C31[nm] = c
        log(f"  [eps^0 l^1] d^({nm}) C3 = {mp.nstr(c, 30)}    (A3 part {mp.nstr(a3, 20)}, Z2 part {mp.nstr(z2t, 10)})")
    vals = {
        "a": C31["v"] - 4, "p": C31["d"] + 4, "A": C31["vv"] / 2, "E": C31["vd"] + 4,
        "V": C31["dd"] / 2 - 4, "alpha": C31["vvv"] / 6, "beta": C31["vvd"] / 2, "gamma": C31["vdd"] / 2 - 4,
        "W": C31["ddd"] / 6 + 4,
    }
    arch = json.load(open("<PROJECT>/LRI_SRI_research_compendium/data/archived/"
                          "C8_full_numerical_completion/data/F3_final_100.json"))["values"]
    archW = mp.mpf("-37.708111514952555")   # note sec. fullpackages table (15 digits)
    res = {}
    ok = True
    for nm, x in vals.items():
        if nm in beta_cf:
            ref, src = beta_cf[nm], "closed form"
        elif nm == "W":
            ref, src = archW, "note table (archived)"
        else:
            ref, src = mp.mpf(arch["beta_" + nm]), "archived F3_final_100.json"
        d = x - ref
        tol = mp.mpf(10) ** (-13 if nm == "W" else -25)
        good = abs(d) < tol * (1 + abs(ref))
        ok &= good
        log(f"  {nm:6s} = {mp.nstr(x, 32):>38s}   vs {src}: diff {mp.nstr(d, 3)}  {'OK' if good else 'MISMATCH'}")
        res[nm] = {"value": mp.nstr(x, 35), "reference": mp.nstr(ref, 35), "ref_source": src, "diff": mp.nstr(d, 4)}
    res["C3_single_logs"] = {k: mp.nstr(v, 35) for k, v in C31.items()}
    return ok, res, C31


# ---------------------------------------------------------------------------
# (B) c, b, f from displayed expansions
# ---------------------------------------------------------------------------
def part_B(C31):
    log("=" * 78)
    log("(B) c, b, f (and a, p) from the note's displayed low-order expansions")
    log("=" * 78)
    z2, z3, z4 = mp.zeta(2), mp.zeta(3), mp.zeta(4)
    L2_, L3_ = mp.log(2), mp.log(3)
    Li2h = mp.polylog(2, -mp.mpf(1) / 2)
    P4 = 4 * z2 + mp.mpf(8) / 3 * z3 - 2 + 3 * L3_ + L2_ ** 2 + 2 * Li2h
    R4 = 24 - 20 * z2 - 30 * z3 - 16 * L2_
    S5 = 44 * z2 + mp.mpf(152) / 3 * z3 - 3 + 12 * L3_ + 4 * L2_ ** 2 + 8 * Li2h
    F40 = -62 + 36 * z2 + 30 * z3 + 16 * L2_
    C3v0 = 18 - 14 * z2 - 15 * z3 - 8 * L2_
    # --- [eps^0 l^1] d_v Q4 from the Mellin data (exact Laurent algebra) ---------
    q, Pp, Rr, zt = sp.symbols("q P R zeta2")
    Aq = 8 / q ** 2 - 6 / q - 6 - 4 * zt + Pp * q
    Apq = 32 / q ** 3 - 4 / q ** 2 + (4 + 16 * zt) / q + Rr
    dM = Apq / (q ** 2 * (q + 1)) + 4 * (2 * q + 1) * Aq / (q ** 3 * (q + 1) ** 2)
    M0 = Aq / (q ** 2 * (q + 1))
    lser = sp.series(dM, q, 0, 0).removeO()
    lser0 = sp.series(M0, q, 0, 0).removeO()
    cm2 = sp.expand(lser).coeff(q, -2)
    Q4v_1 = -cm2      # c/q^{n+1} <-> c (-1)^n l^n/n!
    Q4_1 = -sp.expand(lser0).coeff(q, -2)
    log("  from Mellin data:  [eps^0 l^1] Q4 =", Q4_1, ";  [eps^0 l^1] d_v Q4 =", Q4v_1)
    # two-kink pieces (Taylor coefficients; first derivatives equal Taylor coefficients)
    def tk(kind, i, j, e):
        return L.two_kink(kind, i, j, e, 3, None, DPS)

    def prod_l1(A, B):   # [eps^0 l^1] of product of two eps-log series
        s = mp.mpf(0)
        for (p1, k1), x in A.items():
            for (p2, k2), y in B.items():
                if p1 + p2 == 0 and k1 + k2 == 1:
                    s += x * y
        return s
    Z2, Q2 = tk("Z", 0, 0, 0), tk("Q", 0, 0, 0)
    Z2v, Q2v = tk("Z", 1, 0, 0), tk("Q", 1, 0, 0)
    K4v_1 = mp.mpf(str(sp.N(Q4v_1.subs({Pp: sp.Float(mp.nstr(P4, 50), 50), Rr: sp.Float(mp.nstr(R4, 50), 50),
                                        zt: sp.Float(mp.nstr(z2, 50), 50)}), 45))) - prod_l1(Z2v, Q2) - prod_l1(Z2, Q2v)
    K4_1_check = mp.mpf(str(sp.N(Q4_1.subs(zt, sp.Float(mp.nstr(z2, 50), 50)), 45))) - prod_l1(Z2, Q2)
    log("  [eps^0 l^1] K4 from Mellin+two-kink =", mp.nstr(K4_1_check, 25), "  displayed -8+4 zeta2 =",
        mp.nstr(-8 + 4 * z2, 25))
    assert abs(K4_1_check - (-8 + 4 * z2)) < mp.mpf(10) ** -30
    log("  [eps^0 l^1] d_v K4 =", mp.nstr(K4v_1, 30))
    norm = {
        "C3[l^1]": 5, "C3[l^0]": 3 - 2 * z2,
        "C3_v[l^1]": 4 - 4 * z2, "C3_v[l^0]": C3v0,
        "C3_E[l^0]": F40 + 2 * C3v0,          # j3 = -2 C3_v + C3_E = F40 (lo:eq:F40)
        "C3_d[l^1]": C31["d"],                # from part (A); displayed form is (p-4)
        "C5[l^1]": 96 - 40 * z2 - S5,
        "K4[l^1]": -8 + 4 * z2, "K4[l^0]": P4 + 4 * z2 - 10,
        "K4_v[l^1]": K4v_1,
    }
    fw = L.Framework("D4", dps=DPS)
    # strict for the five inputs this data determines; every other output is reported MISSING
    res = fw.from_normalized(norm, outputs=["a", "p", "c", "b", "f"])
    beta_cf, _ = L.closed_forms(DPS)
    ok = True
    out = {}
    for nm in ("a", "p", "c", "b", "f"):
        x = res.beta[nm]
        if x.is_missing:
            log(f"  {nm}: MISSING {sorted(x.miss)[:4]}")
            ok = False
            continue
        d = x.v - beta_cf[nm]
        good = abs(d) < mp.mpf(10) ** -30
        ok &= good
        log(f"  {nm} = {mp.nstr(x.v, 32):>38s}   closed form diff {mp.nstr(d, 3)}  {'OK' if good else 'MISMATCH'}")
        out[nm] = {"value": mp.nstr(x.v, 35), "diff_closed_form": mp.nstr(d, 4)}
    # appendix forms: b1 = -21+38 z2+60 z3+32 log2 - S5 ; f1 = 16P+4R4-32+16z2+32z3
    f1 = 16 * P4 + 4 * R4 - 32 + 16 * z2 + 32 * z3
    log("  appendix f1 = 16P+4R4-32+16z2+32z3 =", mp.nstr(f1, 25), " (agrees:", abs(f1 - res.beta['f'].v) < 1e-30, ")")
    # outputs that need more data must be reported missing, not silently zero
    miss = [nm for nm in fw.beta_names if res.beta[nm].is_missing]
    log("  beta inputs correctly reported as MISSING (need higher responses):", miss)
    return ok, out


def main():
    okA, resA, C31 = part_A()
    okB, resB = part_B(C31)
    log("=" * 78)
    log("VALIDATION", "PASSED" if (okA and okB) else "FAILED")
    with open(os.path.join(OUT, "validate_low_order.json"), "w") as fh:
        json.dump({"three_kink_b3_sector": resA, "displayed_data_betas": resB, "passed": okA and okB}, fh, indent=1)
    with open(os.path.join(OUT, "validate_low_order.log"), "w") as fh:
        fh.write("\n".join(LOG) + "\n")
    return okA and okB


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
