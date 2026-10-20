#!/usr/bin/env python3
"""
derive_invariants.py -- fixed point, stability trace T and determinant D from the
F, H jets, power counting, and the thermal conversion identities.

  * generic jets:  F = z + sum_{i>=1, i+j+k<=5} F_ijk u^i z^j delta^k,
                   H = -delta + sum_{i>=1, i+j+k<=5} H_ijk u^i z^j delta^k
    -> T_1..T_4, D_1..D_4 symbolically; list which coefficients enter each.
  * prescription (H_1jk = 4 delta_{j0}delta_{k0}; names a..K, W..Kv) -> compare with
    note: D2, T2 (l.563-564), D3 (eq:D3assembly), u*, z* (l.618-621),
    C6 = 4T3 (eq:C6assembly incl. B_old), D4 (l.1033 linear part; B_old^{D4} printed
    in full), C8 = 8 T4 (eq:C8assembly + appendix B_old polynomial).
  * Delta_- = 1 + T/2 - sqrt(T^2/4 - D), delta = 2 t^2 -> C_1..C_8 (eq:conversion).
  * numerical assembly checks with closed forms + ARCHIVED inputs (comparison only).

Run: python3 derive_invariants.py   (~1 min)
"""
import json
import os
import sympy as sp
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


u, z, d = sp.symbols("u z delta")
ORDER = 4          # T and D through delta^4
DEG = 5            # generic jets through total degree 5 in (u,z,delta)


def generic_jets():
    Fc, Hc = {}, {}
    F = z
    H = -d
    for i in range(1, DEG + 1):
        for j in range(0, DEG + 1 - i):
            for k in range(0, DEG + 1 - i - j):
                Fc[(i, j, k)] = sp.Symbol(f"F_{i}{j}{k}")
                Hc[(i, j, k)] = sp.Symbol(f"H_{i}{j}{k}")
                F += Fc[(i, j, k)] * u ** i * z ** j * d ** k
                H += Hc[(i, j, k)] * u ** i * z ** j * d ** k
    return F, H, Fc, Hc


def trunc(e, n):
    e = sp.expand(e)
    P = sp.Poly(e, d)
    return sp.expand(sum(c * d ** m[0] for m, c in P.terms() if m[0] <= n))


def subs_series(expr, us, zs, n):
    """evaluate polynomial expr(u,z,delta) at u=us(delta), z=zs(delta), truncated at delta^n"""
    P = sp.Poly(sp.expand(expr), u, z)
    pu = {0: sp.Integer(1)}
    pz = {0: sp.Integer(1)}
    res = 0
    for (i, j), c in P.terms():
        for m, pw, s in ((i, pu, us), (j, pz, zs)):
            while max(pw) < m:
                k = max(pw)
                pw[k + 1] = trunc(pw[k] * s, n)
        res += trunc(c * trunc(pu[i] * pz[j], n), n)
    return trunc(res, n)


def fixed_point(F, H, n):
    """u*, z* as series in delta through delta^n (F and H vanish)."""
    uk = [sp.Symbol(f"u{k}") for k in range(1, n + 1)]
    zk = [sp.Symbol(f"z{k}") for k in range(1, n + 1)]
    sol = {}
    us = sum(uk[k - 1] * d ** k for k in range(1, n + 1))
    zs = sum(zk[k - 1] * d ** k for k in range(1, n + 1))
    for m in range(1, n + 1):
        Fm = subs_series(F, us.subs(sol), zs.subs(sol), m).coeff(d, m)
        Hm = subs_series(H, us.subs(sol), zs.subs(sol), m).coeff(d, m)
        s = sp.solve([Fm, Hm], [uk[m - 1], zk[m - 1]], dict=True)
        assert len(s) == 1, (m, s)
        sol.update({kk: sp.expand(vv) for kk, vv in s[0].items()})
    return sp.expand(us.subs(sol)), sp.expand(zs.subs(sol))


def invariants(F, H, n):
    us, zs = fixed_point(F, H, n)
    Fu, Fz, Hu, Hz = sp.diff(F, u), sp.diff(F, z), sp.diff(H, u), sp.diff(H, z)
    T = 2 * u * Fu + (1 + z) * Hz
    D = 2 * u * (1 + z) * (Fu * Hz - Fz * Hu)
    Ts = subs_series(T, us, zs, n)
    Ds = subs_series(D, us, zs, n)
    return us, zs, Ts, Ds


# ---------------------------------------------------------------------------
# prescription names
FNAMES = {(1, 0, 0): 1, (1, 1, 0): "a", (1, 0, 1): "p", (1, 2, 0): "A", (1, 1, 1): "E", (1, 0, 2): "V",
          (1, 3, 0): "alpha", (1, 2, 1): "beta", (1, 1, 2): "gamma", (1, 0, 3): "W",
          (2, 0, 0): "b", (2, 1, 0): "G", (2, 0, 1): "R", (2, 2, 0): "Phi", (2, 1, 1): "Psi", (2, 0, 2): "S",
          (3, 0, 0): "J", (3, 1, 0): "Omega", (3, 0, 1): "U", (4, 0, 0): "J9"}
HNAMES = {(1, 0, 0): 4, (2, 0, 0): "c", (2, 1, 0): "f", (2, 0, 1): "q", (2, 2, 0): "L", (2, 1, 1): "M",
          (2, 0, 2): "Q", (2, 3, 0): "L3", (2, 2, 1): "M21", (2, 1, 2): "M12",
          (3, 0, 0): "k", (3, 1, 0): "N", (3, 0, 1): "P", (3, 2, 0): "N2", (3, 1, 1): "Ndelta",
          (4, 0, 0): "K", (4, 1, 0): "Kv"}
NAMES = sorted({v for v in list(FNAMES.values()) + list(HNAMES.values()) if isinstance(v, str)})
SYM = {nm: sp.Symbol(nm) for nm in NAMES}


def prescription_subs(Fc, Hc):
    """map generic coefficients to the prescription; everything not named is set to zero
    (and that is justified only if it does not enter: checked by the generic analysis)."""
    rep = {}
    for key, s in Fc.items():
        nm = FNAMES.get(key, 0)
        rep[s] = SYM[nm] if isinstance(nm, str) else sp.Integer(nm)
    for key, s in Hc.items():
        nm = HNAMES.get(key, 0)
        rep[s] = SYM[nm] if isinstance(nm, str) else sp.Integer(nm)
    return rep


def rational_TD(coef, n):
    """exact-rational T_m, D_m (m<=n) for jets with numeric Fraction coefficients
    coef[("F",i,j,k)], coef[("H",i,j,k)];  F = z + sum, H = -delta + sum."""
    from fractions import Fraction

    def mul(a, b):
        r = [Fraction(0)] * (n + 1)
        for i, x in enumerate(a):
            if x:
                for j in range(0, n + 1 - i):
                    if b[j]:
                        r[i + j] += x * b[j]
        return r

    def add(a, b, s=1):
        return [x + s * y for x, y in zip(a, b)]

    def const(c):
        return [Fraction(c)] + [Fraction(0)] * n

    dl_ = [Fraction(0), Fraction(1)] + [Fraction(0)] * (n - 1)

    def ev(which, us, zs, du=0, dz=0):
        # evaluate d^du_u d^dz_z of F or H at series us, zs
        tot = [Fraction(0)] * (n + 1)
        if which == "F" and du == 0:
            if dz == 0:
                tot = add(tot, zs)
            elif dz == 1:
                tot = add(tot, const(1))
        if which == "H" and du == 0 and dz == 0:
            tot = add(tot, dl_, -1)
        for key, c in coef.items():
            if key[0] != which or c == 0:
                continue
            i, j, k = key[1:]
            if i < du or j < dz:
                continue
            fac = 1
            for t_ in range(du):
                fac *= (i - t_)
            for t_ in range(dz):
                fac *= (j - t_)
            term = const(c * fac)
            for _ in range(i - du):
                term = mul(term, us)
            for _ in range(j - dz):
                term = mul(term, zs)
            for _ in range(k):
                term = mul(term, dl_)
            tot = add(tot, term)
        return tot

    us = [Fraction(0)] * (n + 1)
    zs = [Fraction(0)] * (n + 1)
    F100 = coef[("F", 1, 0, 0)]
    H100 = coef[("H", 1, 0, 0)]
    for m in range(1, n + 1):
        rF = ev("F", us, zs)[m]
        rH = ev("H", us, zs)[m]
        um = -rH / H100
        zm = -rF - F100 * um
        us[m] += um
        zs[m] += zm
    Fu, Fz = ev("F", us, zs, 1, 0), ev("F", us, zs, 0, 1)
    Hu, Hz = ev("H", us, zs, 1, 0), ev("H", us, zs, 0, 1)
    onez = add(const(1), zs)
    T = add(mul(mul(const(2), us), Fu), mul(onez, Hz))
    D = mul(mul(mul(const(2), us), onez), add(mul(Fu, Hz), mul(Fz, Hu), -1))
    return T, D


def main():
    res = {}
    log("=" * 78)
    log("PART 2: fixed point, stability invariants, power counting")
    log("=" * 78)
    F, H, Fc, Hc = generic_jets()
    # ---- power counting: exact-rational dependency test --------------------------
    # weight argument: u*, z* = O(delta); a coefficient of total degree n=i+j+k enters
    #   D at delta^n (directly through F_z if j>=1, through H_u/u* for H terms), and
    #   T at delta^n (2u F_u, or via u*) or at delta^(n-1) (H terms with j>=1 via H_z).
    # The test below confirms this with random exact rationals (no sympy expression swell).
    from fractions import Fraction
    import random
    random.seed(12345)
    keys = sorted(Fc)
    base = {("F",) + kk: Fraction(random.randint(-9, 9), random.randint(1, 5)) for kk in keys}
    base.update({("H",) + kk: Fraction(random.randint(-9, 9), random.randint(1, 5)) for kk in keys})
    base[("F", 1, 0, 0)] = Fraction(1)
    base[("H", 1, 0, 0)] = Fraction(4)
    for kk in keys:   # prescription: H_1jk = 0 except H_100 = 4
        if kk[0] == 1 and kk != (1, 0, 0):
            base[("H",) + kk] = Fraction(0)
    T0, D0 = rational_TD(base, ORDER)
    dep = {f"T{m}": [] for m in range(1, ORDER + 1)}
    dep.update({f"D{m}": [] for m in range(1, ORDER + 1)})
    for key in sorted(base):
        if key[0] == "H" and key[1] == 1:
            continue
        pert = dict(base)
        pert[key] = base[key] + Fraction(7, 3)
        T1_, D1_ = rational_TD(pert, ORDER)
        nm = (FNAMES if key[0] == "F" else HNAMES).get(key[1:])
        lab = f"{key[0]}_{key[1]}{key[2]}{key[3]}" + (f"={nm}" if nm is not None else "")
        for m in range(1, ORDER + 1):
            if T1_[m] != T0[m]:
                dep[f"T{m}"].append(lab)
            if D1_[m] != D0[m]:
                dep[f"D{m}"].append(lab)
    unn = {}
    for lab, lst in dep.items():
        log(f"  {lab}: {', '.join(lst)}")
        bad = [x for x in lst if "=" not in x]
        if bad:
            unn[lab] = bad
    log("  ==> every coefficient entering T1..T4, D1..D4 is a named dictionary input"
        if not unn else f"  ==> UNNAMED coefficients enter: {unn}")
    res["power_counting_ok"] = not unn
    res["dependencies"] = dep
    rep = prescription_subs(Fc, Hc)
    # ---- prescription --------------------------------------------------------
    Fp = sp.expand(F.subs(rep))
    Hp = sp.expand(H.subs(rep))
    log("F (prescription) =", sp.collect(Fp, u))
    log("H (prescription) =", sp.collect(Hp, u))
    usp, zsp, Ts, Ds = invariants(Fp, Hp, ORDER)
    T = {m: sp.expand(Ts.coeff(d, m)) for m in range(1, ORDER + 1)}
    D = {m: sp.expand(Ds.coeff(d, m)) for m in range(1, ORDER + 1)}
    a, p, A, E, V, b, G, R, J, c, f, q, L, M, Q, k, N, P, K = [SYM[s] for s in
        "a p A E V b G R J c f q L M Q k N P K".split()]
    al, be, ga, Phi, Psi, Om = [SYM[s] for s in "alpha beta gamma Phi Psi Omega".split()]
    log("-" * 78)
    log("T1 =", T[1], "  D1 =", D[1])
    assert T[1] == sp.Rational(1, 2) and D[1] == -2
    chk = {}
    chk["D2"] = sp.expand(D[2] - (sp.Rational(1, 2) - a / 2 - c / 8))
    chk["T2"] = sp.expand(T[2] - (-a / 8 + b / 4 - c / 32 + f / 16 + p / 2))
    chk["D3"] = sp.expand(D[3] - (16 * A - 32 * E - 8 * G + 8 * b + c ** 2 + 4 * f - 4 * k + 32 * p - 8 * q) / 64)
    chk["u*"] = sp.expand(usp - (d / 4 - c / 64 * d ** 2 + (c ** 2 / 512 + (f - k) / 256 - q / 64) * d ** 3)).coeff(d, 3)
    chk["u*12"] = sp.expand(usp - (d / 4 - c / 64 * d ** 2)).coeff(d, 2)
    chk["z*"] = sp.expand(zsp - (-d / 4 + ((a - b) / 16 + c / 64 - p / 4) * d ** 2)).coeff(d, 2)
    Bold = (A / 8 - E / 2 - G / 4 + (a ** 2 - a * b) / 8 + a * c / 16 - a * p / 2 - b * c / 8 + c ** 2 / 64
            - c * f / 32 - c * p / 8 - f / 32 - k / 32 - q / 8)
    C6note = Bold + 2 * V + R + sp.Rational(3, 8) * J - L / 8 + M / 4 + N / 16
    chk["C6=4T3"] = sp.expand(4 * T[3] - C6note)
    for kk, vv in chk.items():
        log(f"  {kk}: derived - note = {vv}")
    log("  u* =", sp.collect(usp, d))
    log("  z* =", sp.collect(zsp, d))
    log("  D2 =", D[2])
    log("  T2 =", T[2])
    log("  D3 =", D[3])
    log("  T3 =", T[3])
    # D4
    lin4 = (-sp.Rational(3, 32) * al + be / 4 - ga / 2 + Phi / 16 - Psi / 8 - Om / 32 - Q / 8 - P / 16
            - sp.Rational(3, 128) * K)
    new4 = [al, be, ga, Phi, Psi, Om, Q, P, K]
    D4lin = sum(sp.diff(D[4], s) * s for s in new4)
    B4 = sp.expand(D[4] - D4lin)
    chk_lin = sp.expand(D4lin - lin4)
    log("  D4 linear part in new inputs: derived - note(l.1033) =", chk_lin)
    log("  B_old^{D4} (derived; old inputs only) =", B4)
    assert not any(B4.has(s) for s in new4)
    chk["D4lin"] = chk_lin
    # C8 = 8 T4
    C8 = sp.expand(8 * T[4])
    W, S, U, J9, L3, M21, M12, N2, Nd, Kv = [SYM[s] for s in "W S U J9 L3 M21 M12 N2 Ndelta Kv".split()]
    new8 = [W, S, U, J9, L3, M21, M12, N2, Nd, Kv]
    lin8 = (4 * W + 2 * S + sp.Rational(3, 4) * U + J9 / 4 + sp.Rational(3, 32) * L3 - M21 / 4 + M12 / 2
            - N2 / 16 + Nd / 8 + Kv / 32)
    C8lin = sum(sp.diff(C8, s) * s for s in new8)
    B8 = sp.expand(C8 - C8lin)
    Bnote8 = (-ga - sp.Rational(5, 1024) * c ** 3 - sp.Rational(3, 16) * Om - Psi / 2 - Q / 4 - M / 16 - P / 16
              - al / 16 - a ** 3 / 16 - K / 64 - N / 64 + be / 4 + Phi / 8 + f ** 2 / 64 + sp.Rational(3, 64) * L
              + A * p / 2 + E * a / 2 - E * p - V * a - sp.Rational(9, 64) * J * c - sp.Rational(5, 256) * a * c ** 2
              - sp.Rational(3, 16) * A * a - sp.Rational(3, 64) * A * c - sp.Rational(3, 64) * a ** 2 * c
              - sp.Rational(3, 128) * N * c - G * p / 2 - E * b / 4 - L * p / 4 - R * a / 4 - R * c / 4
              - V * c / 4 - b * q / 4 - p * q / 4 - G * b / 8 - J * a / 16 - L * b / 16 - M * c / 16 - b * k / 16
              - f * q / 16 - k * p / 16 - a * f / 64 - f * k / 64 + a ** 2 * p / 4 + A * b / 8 + E * c / 8
              + a * q / 8 + L * a / 16 + a ** 2 * b / 16 + c * q / 16 + a * k / 32 + c ** 2 * p / 32
              + c * f / 256 + sp.Rational(3, 16) * G * a + sp.Rational(3, 32) * G * c + sp.Rational(3, 64) * L * c
              + sp.Rational(3, 64) * b * f + sp.Rational(5, 128) * b * c ** 2 + sp.Rational(5, 256) * c * k
              + sp.Rational(5, 512) * c ** 2 * f + a * c * p / 8 + sp.Rational(3, 64) * a * b * c)
    chk["C8lin"] = sp.expand(C8lin - lin8)
    chk["C8Bold"] = sp.expand(B8 - Bnote8)
    log("  C8=8T4 linear part: derived - note(eq:C8assembly) =", chk["C8lin"])
    log("  C8 old part: derived - note(appendix app:C8polynomial) =", chk["C8Bold"])
    allok = all(vv == 0 for vv in chk.values())
    log("  ==> ALL ASSEMBLIES AGREE WITH THE NOTE" if allok else "  ==> DISCREPANCY (see above)")
    res["assemblies_ok"] = allok

    # ---- conversion identities ----------------------------------------------
    log("-" * 78)
    log("Conversion: Delta_- = 1 + T/2 - sqrt(T^2/4 - D), delta = 2 t^2")
    tt = sp.Symbol("t", positive=True)
    Tk = {m: sp.Symbol(f"T{m}") for m in range(2, 5)}
    Dk = {m: sp.Symbol(f"D{m}") for m in range(2, 6)}
    dd = 2 * tt ** 2
    Tser = dd / 2 + sum(Tk[m] * dd ** m for m in Tk)
    Dser = -2 * dd + sum(Dk[m] * dd ** m for m in Dk)
    disc = sp.expand(Tser ** 2 / 4 - Dser)          # = 4 t^2 (1 + O(t^2))
    X = sp.expand(disc / (4 * tt ** 2))
    sq = 2 * tt * sp.series(sp.sqrt(X), tt, 0, 9).removeO()
    Dm = sp.expand(1 + Tser / 2 - sq)
    Cn = {m: sp.expand(Dm.coeff(tt, m)) for m in range(1, 9)}
    for m in range(1, 9):
        log(f"  C{m} =", Cn[m])
    C3 = Dk[2] - sp.Rational(1, 16)
    C5 = 2 * Dk[3] - Tk[2] / 2 + (Dk[2] - sp.Rational(1, 16)) ** 2 / 4
    conv = {1: -2, 2: sp.Rational(1, 2), 3: C3, 4: 2 * Tk[2], 5: C5, 6: 4 * Tk[3],
            7: 4 * Dk[4] - Tk[3] - Tk[2] ** 2 + C3 * C5 / 2, 8: 8 * Tk[4]}
    cok = True
    for m in range(1, 9):
        dlt = sp.expand(Cn[m] - conv[m])
        log(f"  C{m} - eq:conversion = {dlt}")
        cok &= (dlt == 0)
    res["conversion_ok"] = cok
    log("  ==> eq:conversion verified (C1..C8)" if cok else "  ==> CONVERSION DISCREPANCY")

    # ---- save formulas -------------------------------------------------------
    formulas = {"D2": str(D[2]), "T2": str(T[2]), "D3": str(D[3]), "T3": str(T[3]), "D4": str(D[4]),
                "T4": str(T[4]), "B_old_D4": str(B4), "B_old_C8": str(B8), "u_star": str(usp), "z_star": str(zsp),
                "C_from_TD": {str(m): str(Cn[m]) for m in Cn}}
    with open(os.path.join(OUT, "invariant_formulas.json"), "w") as fh:
        json.dump(formulas, fh, indent=1)
    res["formulas"] = formulas

    # ---- numerical assembly checks ------------------------------------------
    log("-" * 78)
    log("Numerical assembly (closed forms for a,p,A,E,b,c,f; ARCHIVED numbers for the rest, comparison only)")
    mp.mp.dps = 45
    z2_, z3_, z4_, z5_, z6_ = mp.zeta(2), mp.zeta(3), mp.zeta(4), mp.zeta(5), mp.zeta(6)
    L2_, L3_ = mp.log(2), mp.log(3)
    Li2h = mp.polylog(2, -mp.mpf(1) / 2)
    Li4 = mp.polylog(4, mp.mpf(1) / 2)
    closed = {
        "a": -4 * z2_, "c": mp.mpf(-16), "p": 8 - 2 * z2_ - 7 * z3_ - 8 * L2_,
        "b": -18 - 6 * z2_ + mp.mpf(28) / 3 * z3_ + 32 * L2_ - 12 * L3_ - 4 * L2_ ** 2 - 8 * Li2h,
        "f": 32 - mp.mpf(136) / 3 * z3_ - 64 * L2_ + 48 * L3_ + 16 * L2_ ** 2 + 32 * Li2h,
        "A": -8 - 4 * z2_ - 2 * z3_ + 16 * L2_,
        "E": (-16 + 14 * z2_ - 22 * z3_ + 12 * z4_ + 8 * L2_ - 8 * L2_ ** 2 - 16 * Li4 - 14 * z3_ * L2_
              + 4 * z2_ * L2_ ** 2 - mp.mpf(2) / 3 * L2_ ** 4),
    }
    arch_path = "<PROJECT>/LRI_SRI_research_compendium/data/archived/C8_full_numerical_completion/data/F3_final_100.json"
    arch = json.load(open(arch_path))["values"]
    vals = {nm[5:]: mp.mpf(x) for nm, x in arch.items() if nm.startswith("beta_")}
    # compare closed forms to archived numbers
    for nm, x in closed.items():
        log(f"  closed {nm} - archived = {mp.nstr(x - vals[nm], 5)}")
    vals.update(closed)
    # C8 new inputs from the note (sec. fullpackages / eq:NdP6, eq:P6full)
    P6 = mp.mpf("1261.944897843140491372852392951531767542124984174")
    c8in = {"W": "-37.708111514952555", "S": "878.183733747745103", "L3": "-0.638692810583406",
            "M21": "-171.235576565588699", "M12": "-422.715057969894520", "N2": "189.742012494084223",
            "U": "-1296.687960291526491656393773342069", "J9": "-273.724515999324646514077910398647",
            "Kv": "-1486.962109278823406127742917363593"}
    for kk, vv in c8in.items():
        vals[kk] = mp.mpf(vv)
    vals["Ndelta"] = -4 * P6 + mp.mpf("11218.914021881803142302231182488606")
    subsn = {SYM[nm]: vals[nm] for nm in NAMES}
    num = {}
    for lab, ex in [("D2", D[2]), ("T2", T[2]), ("D3", D[3]), ("T3", T[3]), ("D4", D[4]), ("T4", T[4]),
                    ("B_old_C6", Bold), ("B_old_C8", B8)]:
        num[lab] = sp.N(ex.subs(subsn), 40)
    Tn_ = {2: num["T2"], 3: num["T3"], 4: num["T4"]}
    Dn_ = {2: num["D2"], 3: num["D3"], 4: num["D4"]}
    C3n = Dn_[2] - sp.Rational(1, 16)
    C5n = 2 * Dn_[3] - Tn_[2] / 2 + C3n ** 2 / 4
    numC = {"C3": C3n, "C4": 2 * Tn_[2], "C5": C5n, "C6": 4 * Tn_[3],
            "C7": 4 * Dn_[4] - Tn_[3] - Tn_[2] ** 2 + C3n * C5n / 2, "C8": 8 * Tn_[4]}
    target = {
        "D2": 2.5 + 2 * z2_, "T2": 2 - 2 * z2_ - 4 * z3_,
        "D3": mp.mpf(21) / 4 - 13 * z2_ + 11 * z3_ + 11 * z4_,
        "C3": mp.mpf(39) / 16 + 2 * z2_, "C4": 4 - 4 * z2_ - 8 * z3_,
        "C5": mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z2_ + 24 * z3_ + mp.mpf(49) / 2 * z4_,
        "C6": 26 - 38 * z2_ + 104 * z3_ - 80 * z4_ - 272 * z5_ + 112 * z2_ * z3_,
        "D4": (13 - mp.mpf(179) / 8 * z2_ + mp.mpf(47) / 2 * z3_ - mp.mpf(493) / 8 * z4_ + 289 * z5_
               - 130 * z2_ * z3_ + mp.mpf(499) / 4 * z6_ - 76 * z3_ ** 2),
        "C7": (mp.mpf(1798583) / 32768 - mp.mpf(90637) / 1024 * z2_ + mp.mpf(453) / 4 * z3_
               - mp.mpf(16835) / 64 * z4_ + 1224 * z5_ - 540 * z2_ * z3_ + mp.mpf(4335) / 8 * z6_ - 320 * z3_ ** 2),
        "C8": mp.mpf("247.3812048049935484073550747661"),
        "B_old_C6": mp.mpf("-48.0003600840977427059"),
        "B_old_C8": mp.mpf("-861.6635672354797792014971909923"),
    }
    allnum = dict(num)
    allnum.update(numC)
    numres = {}
    for kk in ["D2", "T2", "C3", "C4", "D3", "C5", "B_old_C6", "C6", "D4", "C7", "B_old_C8", "C8"]:
        x = mp.mpf(str(allnum[kk]))
        diffv = x - target[kk]
        log(f"  {kk:9s} = {mp.nstr(x, 30):>36s}   claimed {mp.nstr(target[kk], 25):>32s}   diff {mp.nstr(diffv, 3)}")
        numres[kk] = (mp.nstr(x, 35), mp.nstr(diffv, 5))
    res["numeric"] = numres
    with open(os.path.join(OUT, "derive_invariants.log"), "w") as fh:
        fh.write("\n".join(LOG) + "\n")
    with open(os.path.join(OUT, "derive_invariants_result.json"), "w") as fh:
        json.dump({k_: v_ for k_, v_ in res.items() if k_ != "formulas"}, fh, indent=1, default=str)
    return res


if __name__ == "__main__":
    main()
