#!/usr/bin/env python3
"""
derive_rg.py -- independent symbolic derivation of the map
    regulated (normalized, projected) responses  ->  auxiliary beta functions
    ->  essential beta functions F, H  ->  derivative dictionary.

Everything here is derived from the definitions in Secs. 3-5 of the note
(regulator, current resummation, normal ordering, matching), NOT copied from
eq:subtraction.  The note's recurrence is only used at the very end, for
comparison.

Parts
  1A  explicit minimal-subtraction counterterms at b0=1, delta=0 from the
      appendix low-order responses; reproduce the appendix counterterms
      (lo:eq:h4ct, lo:eq:g5ct) and check Callan-Symanzik consistency
      (beta independent of ell) -- this also tests the higher logs.
  1B  structured responses (current resummation: b_h=b0-sqrt2 h, v_h=b_h^2,
      eta_h = sqrt2 h b_h, normal-ordering factor N(h)), renormalization
      condition  =>  J0 beta = R1  =>  recurrence for b3..b9, h4..h8.
  1C  conversion to the essential couplings (Y, v_B) via eq:matching with b0
      kept variable  =>  F = z + sum b_{2k+1} u^k, H = -delta - 4 sum h_{2k} u^k.
  1D  eq:fugmatch expansion and its (non-)effect on single logarithms.
  1E  explicit formulas for every beta input of the derivative dictionary in
      terms of response coefficients (written to out/beta_input_formulas.txt)

Run:  python3 derive_rg.py      (about 1-2 minutes on a laptop)
"""
import json
import os
import sys
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


ell, g, h, dl, eta, v, t = sp.symbols("ell g h delta eta v t")
b0 = sp.symbols("b0", positive=True)
z2, z3, z4, z5, L2 = sp.symbols("zeta2 zeta3 zeta4 zeta5 log2")
S2 = sp.sqrt(2)


def fdelta_of_ell(dlt, n=6):
    """f_delta(eps) = (eps^delta - 1)/delta as a polynomial in ell (series in delta)."""
    return sum(dlt ** (k - 1) * ell ** k / sp.factorial(k) for k in range(1, n + 1))


# --------------------------------------------------------------------------
# Part 1A : explicit counterterms with the appendix low-order data
# --------------------------------------------------------------------------
def part_1A():
    log("=" * 78)
    log("PART 1A: explicit minimal-subtraction counterterms (b0=1, delta=0)")
    log("=" * 78)
    P4, S5, C50, F40 = sp.symbols("P4 S5 C5_0 F40")
    # ---- structural check of the two-kink / one-kink mixed responses -----
    # model: F_G = sum g^n N^n C_n(v_h, eta_h),  F_H = h + sqrt2 b_h sum g^n N^n K_n
    # N = exp[-f(eps) (b0^2 - b_h^2)],  b_h = b0 - sqrt2 h,  eta_h = sqrt2 h b_h
    bh = 1 - S2 * h
    vh = bh ** 2
    etah = S2 * h * bh
    N = sp.exp(-ell * (1 - vh))
    # A1(eta) = B(1+eta,1+eta) (U^odd, uncut endpoints), to second order in eta
    x = sp.symbols("x")
    A1ser = sp.series(sp.gamma(1 + x) ** 2 / sp.gamma(2 + 2 * x), x, 0, 3).removeO()
    A1ser = sp.expand(sp.expand_func(A1ser)).subs(sp.EulerGamma, 0)  # gamma cancels
    A1ser = sp.nsimplify(sp.expand(A1ser.subs(sp.pi ** 2, 6 * z2)))
    A1h = sp.expand(sp.series((A1ser.subs(x, etah)) * N, h, 0, 3).removeO())
    Fgh = sp.expand(A1h.coeff(h, 1))
    Fgh2 = sp.expand(A1h.coeff(h, 2))
    log("model F_gh   =", Fgh, "   appendix: -2*sqrt2*(ell+1)")
    log("model F_gh^2 =", Fgh2, "   appendix: 4 ell^2+10 ell+12-2 zeta2")
    assert sp.simplify(Fgh - (-2 * S2 * (ell + 1))) == 0
    assert sp.simplify(Fgh2 - (4 * ell ** 2 + 10 * ell + 12 - 2 * z2)) == 0
    # Q2(v) eps^0 part, two-kink: Q2 = int_eps^1 r^{1-2v}(1-r) dr ;  v=1+zz
    zz = sp.symbols("zz")
    # eps^0 part of Q2 as a series in zz: 1/(2-2v)-1/(3-2v) + e^{-2 zz ell}/(2 zz)
    Q2v = sp.series(-1 / (2 * zz) - 1 / (1 - 2 * zz) + sp.exp(-2 * zz * ell) / (2 * zz), zz, 0, 3).removeO()
    Q2v = sp.expand(Q2v)
    log("Q2(v=1+z) eps^0 part through z^2:", Q2v)
    # EE Q2 at v=1: -2 zeta2 (+O(eps)); its v-derivative J_end'(1) = -4(zeta2+zeta3)
    EEQ2 = -2 * z2 - 4 * (z2 + z3) * zz
    Q2model = Q2v + EEQ2 * sp.Symbol("ETA")
    FH2 = S2 * bh * N ** 2 * Q2model.subs({zz: vh - 1, sp.Symbol("ETA"): etah})
    FH2 = sp.expand(sp.series(FH2, h, 0, 2).removeO())
    Fhg2 = sp.expand(FH2.coeff(h, 1))
    log("model F_hg^2 =", Fhg2, "   appendix: 4 ell^2+10 ell+10-4 zeta2")
    assert sp.simplify(Fhg2 - (4 * ell ** 2 + 10 * ell + 10 - 4 * z2)) == 0
    log("  -> current resummation + normal-ordering factor N(h) + prefactor sqrt2*b_h")
    log("     reproduce all three displayed mixed responses (incl. their logarithms).")

    # ---- full counterterm construction with the displayed responses ------
    C3 = 2 * ell ** 2 + 5 * ell + 3 - 2 * z2
    K4 = -sp.Rational(4, 3) * ell ** 3 - 6 * ell ** 2 + (-8 + 4 * z2) * ell + P4 + 4 * z2 - 10
    C5 = (sp.Rational(10, 3) * ell ** 4 + sp.Rational(62, 3) * ell ** 3
          + (sp.Rational(95, 2) - 24 * z2) * ell ** 2 + (96 - 40 * z2 - S5) * ell + C50)
    Fg3h = S2 * (-sp.Rational(20, 3) * ell ** 3 - 28 * ell ** 2 + (-48 + 24 * z2) * ell + F40)
    Q2 = -ell - 1
    FG = g + Fgh * g * h + Fgh2 * g * h ** 2 + C3 * g ** 3 + Fg3h * g ** 3 * h + C5 * g ** 5
    FH = h + S2 * g ** 2 * Q2 + Fhg2 * h * g ** 2 + S2 * g ** 4 * K4
    # weights: g ~ 1, h ~ 2 (h is generated at order g^2); F_G to weight 5, F_H to weight 4
    def wtrunc(expr, wmax):
        e = sp.expand(expr)
        if e == 0:
            return e
        P = sp.Poly(e, g, h)
        return sp.expand(sum(c * g ** i * h ** j for (i, j), c in P.terms() if i + 2 * j <= wmax))

    def compose(Fx, Pg, Ph, wmax):
        P = sp.Poly(sp.expand(Fx), g, h)
        powg = {0: sp.Integer(1)}
        powh = {0: sp.Integer(1)}
        res = 0
        for (i, j), c in P.terms():
            for n, pw, base in ((i, powg, Pg), (j, powh, Ph)):
                m = max(pw)
                while m < n:
                    pw[m + 1] = wtrunc(pw[m] * base, wmax)
                    m += 1
            res += c * powg[i] * powh[j]
        return wtrunc(res, wmax)

    def log_part(e, w):
        """ell-dependent part of the exactly-weight-w component of e"""
        e = sp.expand(e)
        if e == 0:
            return e
        P = sp.Poly(e, g, h)
        out = 0
        for (i, j), c in P.terms():
            if i + 2 * j == w:
                cc = sp.expand(c)
                out += (cc - cc.subs(ell, 0)) * g ** i * h ** j
        return sp.expand(out)

    Psig_s, Psih_s = g, h
    for w in range(1, 6):
        FGr = compose(FG, Psig_s, Psih_s, w)
        Psig_s = sp.expand(Psig_s - log_part(FGr, w))
        if w <= 4:
            FHr = compose(FH, Psig_s, Psih_s, w)
            Psih_s = sp.expand(Psih_s - log_part(FHr, w))
    # verify finiteness
    FGr = compose(FG, Psig_s, Psih_s, 5)
    FHr = compose(FH, Psig_s, Psih_s, 4)
    assert sp.expand(sp.diff(FGr, ell)) == 0 and sp.expand(sp.diff(FHr, ell)) == 0
    log("renormalized responses (ell-free):  F_G =", sp.collect(FGr, [g, h]))
    log("                                    F_H =", sp.collect(FHr, [g, h]))
    hb = sp.expand(Psih_s.subs(h, 0))
    gb = sp.expand(Psig_s.subs(h, 0))
    log("h_bare(h_R=0) =", sp.collect(hb, g))
    log("g_bare(h_R=0) =", sp.collect(gb, g))
    hb_app = S2 * g ** 2 * ell + S2 * g ** 4 * (sp.Rational(4, 3) * ell ** 3 - 2 * ell ** 2 - 4 * ell)
    assert sp.expand(hb - hb_app) == 0
    log("  h_bare matches lo:eq:h4ct")
    b1 = sp.Symbol("b1")
    g5_app = sp.Rational(10, 3) * ell ** 4 - sp.Rational(22, 3) * ell ** 3 - (8 * 6 * z2 + 39) / sp.Integer(6) * ell ** 2 - b1 * ell
    g5 = gb.coeff(g, 5)
    diff = sp.expand(g5 - g5_app)
    b1val = sp.solve(diff.coeff(ell, 1), b1)[0]
    log("g^5 counterterm matches lo:eq:g5ct for ell^4..ell^2:",
        sp.expand(diff - diff.coeff(ell, 1) * ell) == 0)
    assert sp.expand(diff - diff.coeff(ell, 1) * ell) == 0
    log("  single-log coefficient  b1 =", sp.expand(b1val),
        "   [appendix lo:eq:bperiod: -21+38 z2+60 z3+32 log2 - S, with F40 = -62+36z2+30z3+16log2]")
    b1chk = sp.expand(b1val.subs(F40, -62 + 36 * z2 + 30 * z3 + 16 * L2))
    assert sp.expand(b1chk - (-21 + 38 * z2 + 60 * z3 + 32 * L2 - S5)) == 0
    # ---- beta = -(D Psi)^{-1} d_ell Psi by weight iteration; must be ell independent ----
    X = sp.Matrix([[sp.diff(Psig_s, g) - 1, sp.diff(Psig_s, h)], [sp.diff(Psih_s, g), sp.diff(Psih_s, h) - 1]])
    dPsi = sp.Matrix([sp.diff(Psig_s, ell), sp.diff(Psih_s, ell)])
    beta_g, beta_h = -dPsi[0], -dPsi[1]
    for _ in range(8):
        ng = wtrunc(-dPsi[0] - X[0, 0] * beta_g - X[0, 1] * beta_h, 5)
        nh = wtrunc(-dPsi[1] - X[1, 0] * beta_g - X[1, 1] * beta_h, 4)
        beta_g, beta_h = ng, nh
    log("beta_g(g,h) =", sp.collect(beta_g, [g, h]))
    log("beta_h(g,h) =", sp.collect(beta_h, [g, h]))
    indep = (sp.expand(sp.diff(beta_g, ell)) == 0, sp.expand(sp.diff(beta_h, ell)) == 0)
    log("Callan-Symanzik consistency: beta independent of ell ?", indep)
    assert all(indep)
    # published leading terms
    assert sp.expand(beta_g.coeff(g, 1).coeff(h, 1) + 2 * S2) == 0
    assert sp.expand(beta_g.coeff(g, 1).coeff(h, 2) - 2) == 0
    assert sp.expand(beta_g.coeff(g, 3).coeff(h, 0) - 1) == 0
    assert sp.expand(beta_h.coeff(g, 2).coeff(h, 0) + S2) == 0
    assert sp.expand(beta_h.coeff(g, 2).coeff(h, 1) - 2) == 0
    log("  reproduces published beta_g=-2sqrt2 gh+2gh^2+g^3, beta_h=-sqrt2 g^2+2hg^2")
    log("  h4 = beta_h[g^4]/sqrt2 =", sp.expand(beta_h.coeff(g, 4).coeff(h, 0) / S2), " => c=-4 h4 = -16")
    # essential-coupling consistency at h != 0 (b0=1): beta_g/g = z_h + g^2 (1 + a z_h) + ..., z_h=(1-sqrt2 h)^2-1
    zh = (1 - S2 * h) ** 2 - 1
    a_ = sp.Symbol("a_")
    chk = wtrunc(sp.expand(beta_g / g - zh - g ** 2 * (1 + a_ * zh) - g ** 4 * beta_g.coeff(g, 5).coeff(h, 0)), 4)
    sol_a = sp.solve(chk.coeff(g, 2).coeff(h, 1), a_)
    log("  beta_g/g - [z_h + g^2(1 + a z_h)] at weight<=4 vanishes for a =", sol_a,
        "(= -4 zeta2, the note's a): auxiliary beta at h!=0 depends on h only via v_h")
    assert sp.expand(sol_a[0] + 4 * z2) == 0
    assert sp.expand(chk.subs(a_, -4 * z2)) == 0
    bv = wtrunc(sp.expand(-2 * S2 * (1 - S2 * h) * beta_h), 4)
    log("  beta_v = -2 sqrt2 b_h beta_h =", sp.factor(bv), " = 4 v_h u + O(g^4): H = 4u (+ -16 u^2 ...)")
    # J0 beta = R1 check
    J0 = sp.Matrix([[sp.diff(FG, g), sp.diff(FG, h)], [sp.diff(FH, g), sp.diff(FH, h)]]).subs(ell, 0)
    R1 = sp.Matrix([sp.diff(FG, ell), sp.diff(FH, ell)]).subs(ell, 0)
    lhs = J0 * sp.Matrix([beta_g, beta_h])
    rG = wtrunc(sp.expand(lhs[0] - R1[0]), 5)
    rH = wtrunc(sp.expand(lhs[1] - R1[1]), 4)
    log("J0*beta - R1 (weight-truncated) =", rG, ",", rH)
    assert rG == 0 and rH == 0
    log("  -> the explicit MS counterterms obey J0 beta = R1 (ell^0 Jacobian, ell^1 residues).")
    return {"b1": str(b1val), "beta_g": str(beta_g), "beta_h": str(beta_h)}


def wtr_t(e, nmax):
    e = sp.expand(e)
    if not e.has(t):
        return e
    P = sp.Poly(e, t)
    return sp.expand(sum(c * t ** m[0] for m, c in P.terms() if m[0] <= nmax))


# --------------------------------------------------------------------------
# Part 1B : structured derivation of the recurrence
# --------------------------------------------------------------------------
ODD = [1, 3, 5, 7, 9]
EVEN = [2, 4, 6, 8]


def resp_funcs():
    """C_{n,k}(v,delta,eta) and K_{n,k}(v,delta,eta), k=0,1,2 (k=2 only to show it drops)."""
    C = {(n, k): sp.Function(f"C{n}_{k}") for n in ODD for k in range(3)}
    K = {(n, k): sp.Function(f"K{n}_{k}") for n in EVEN for k in range(3)}
    return C, K


def part_1B(order=9):
    log("=" * 78)
    log("PART 1B: renormalization condition with the resummed current -> J0 beta = R1")
    log("=" * 78)
    C, K = resp_funcs()
    bh = b0 - S2 * h
    vh = bh ** 2
    etah = S2 * h * bh
    fe = fdelta_of_ell(dl)
    N = sp.exp(-fe * (b0 ** 2 - vh))
    FG = sum(g ** n * N ** n * sum(C[(n, k)](vh, dl, etah) * ell ** k for k in range(3)) for n in ODD if n <= order)
    FH = h + S2 * bh * sum(g ** n * N ** n * sum(K[(n, k)](vh, dl, etah) * ell ** k for k in range(3))
                            for n in EVEN if n <= order - 1)
    # Jacobian at ell = 0 (h=0) and single-log residues R1 = d_ell F at ell=0, h=0
    J0 = sp.Matrix([[sp.diff(FG, g), sp.diff(FG, h)], [sp.diff(FH, g), sp.diff(FH, h)]])
    J0 = J0.subs(ell, 0).subs(h, 0).doit()
    R1 = sp.Matrix([sp.diff(FG, ell), sp.diff(FH, ell)]).subs(ell, 0).subs(h, 0).doit()
    # Note: d_ell N^n at ell=0 is -(b0^2-v_h) n -> 0 at h=0; ell^2 terms drop.
    J0 = J0.applyfunc(sp.expand)
    R1 = R1.applyfunc(sp.expand)
    # replace function objects by readable symbols ----------------------------
    rep = {}
    names = {}

    def nm(base, n, k, dv=0, de=0):
        s = f"{base}{n}{k}" + ("_v" * dv if dv else "") + ("_E" if de else "")
        s = s.replace("_v_v", "_vv").replace("_vv_v", "_vvv")
        return sp.Symbol(s)

    for (n, k), Fn in list(C.items()) + list(K.items()):
        base = "C" if n % 2 else "K"
        f0 = Fn(b0 ** 2, dl, 0)
        rep[f0] = nm(base, n, k)
    def sym_of_deriv(expr):
        # Subs(Derivative(F(_xi_1, delta, eta), _xi_1), _xi_1, b0**2) etc.
        return expr
    # Simplify Subs/Derivative objects
    J0 = J0.applyfunc(lambda e: e.doit())
    R1 = R1.applyfunc(lambda e: e.doit())
    def replace_derivs(e):
        e = e.doit()
        reps = {}
        for d in e.atoms(sp.Subs):
            expr, vars_, pts = d.args
            if isinstance(expr, sp.Derivative):
                fn = expr.expr.func
                n = int(str(fn).split("_")[0][1:])
                k = int(str(fn).split("_")[1])
                base = "C" if str(fn)[0] == "C" else "K"
                # which argument is differentiated
                args = expr.expr.args
                dv = de = 0
                for var, cnt in expr.variable_count:
                    pos = args.index(var)
                    if pos == 0:
                        dv += cnt
                    elif pos == 2:
                        de += cnt
                # evaluate point: vars_ -> pts
                reps[d] = nm(base, n, k, dv, de)
        e = e.xreplace(reps)
        for d in e.atoms(sp.Derivative):
            fn = d.expr.func
            n = int(str(fn).split("_")[0][1:])
            k = int(str(fn).split("_")[1])
            base = "C" if str(fn)[0] == "C" else "K"
            args = d.expr.args
            dv = de = 0
            for var, cnt in d.variable_count:
                pos = args.index(var)
                if pos == 0:
                    dv += cnt
                elif pos == 2:
                    de += cnt
            reps[d] = nm(base, n, k, dv, de)
        e = e.xreplace(reps)
        e = e.xreplace(rep)
        return sp.expand(e)

    J0 = J0.applyfunc(replace_derivs)
    R1 = R1.applyfunc(replace_derivs)
    # structural facts for the one-kink response A1 (single kink, no hard core):
    #   C1_0 = A1(eta) : independent of v, =1 at eta=0, ell-independent.
    one = {sp.Symbol("C10"): 1, sp.Symbol("C10_v"): 0, sp.Symbol("C11"): 0,
           sp.Symbol("C12"): 0, sp.Symbol("C11_v"): 0, sp.Symbol("C11_E"): 0}
    J0 = J0.applyfunc(lambda e: sp.expand(e.subs(one)))
    R1 = R1.applyfunc(lambda e: sp.expand(e.subs(one)))
    log("J0 =")
    for i in range(2):
        for j in range(2):
            log(f"  J0[{i}{j}] =", sp.collect(J0[i, j], g))
    log("R1 =")
    log("  R1[G] =", sp.collect(R1[0], g))
    log("  R1[H] =", sp.collect(R1[1], g))
    # solve J0 beta = R1 order by order (no ansatz for which terms vanish)
    bg = {n: sp.Symbol(f"bg{n}") for n in range(1, order + 1)}
    bhh = {n: sp.Symbol(f"bh{n}") for n in range(0, order + 1)}
    beta_g = sum(bg[n] * g ** n for n in bg)
    beta_h = sum(bhh[n] * g ** n for n in bhh)
    # The system is triangular in the order of g: at g^m, row G contains bg[m] with unit
    # coefficient (J0[00]=1+O(g^2)) and row H contains bh[m] with unit coefficient.
    sol = {}
    for m in range(0, order + 1):
        for row, unk in ((1, bhh.get(m)), (0, bg.get(m))):
            if unk is None:
                continue
            res_m = sp.expand((J0[row, 0] * beta_g + J0[row, 1] * beta_h - R1[row]).subs(sol)).coeff(g, m)
            s_ = sp.solve(res_m, unk)
            assert len(s_) == 1
            sol[unk] = sp.expand(s_[0])
    # verify the full system
    chk = (J0 * sp.Matrix([beta_g, beta_h]) - R1).applyfunc(lambda e: sp.expand(e.subs(sol)))
    for comp in chk:
        for m in range(order + 1):
            assert sp.expand(comp.coeff(g, m)) == 0
    # name the results as in the note:  beta_g = sum b_n g^n,  beta_h = sqrt2 b0 sum h_n g^n
    out = {}
    for n in bg:
        out[f"b{n}"] = sp.expand(sol.get(bg[n], bg[n]))
    for n in bhh:
        out[f"h{n}"] = sp.expand(sol.get(bhh[n], bhh[n]) / (S2 * b0))
    log("Solved beta coefficients (beta_g = sum b_n g^n, beta_h = sqrt2 b0 sum h_n g^n); fully expanded:")
    for k_, val in out.items():
        if val != 0:
            log(f"  {k_}: {len(sp.Add.make_args(val))} terms" + (f"  = {val}" if k_ in ("b3", "h2", "h4") else ""))
    # kept for derive_C8.py (reads j_n, lambda_n off the Jacobian); no effect on this script's output
    LAST_J0R1.clear()
    LAST_J0R1.update({"J0": J0, "R1": R1, "order": order})
    return out


LAST_J0R1 = {}


def note_recurrence(vv):
    """eq:subtraction (lines 425-464) + h8, b9 (lines 1149-1155) written with the
    note's j_n, lambda_n.  Symbols as in part 1B (b0^2 = vv)."""
    s = sp.Symbol
    j = {1: s("C10_E"),
         3: -2 * s("C30_v") + s("C30_E"),
         5: -2 * s("C50_v") + s("C50_E"),
         7: -2 * s("C70_v") + s("C70_E")}
    lam = {}
    for n in (2, 4, 6):
        Kn0 = s(f"K{n}0")
        lam[n] = -2 * Kn0 - 4 * vv * s(f"K{n}0_v") + 2 * vv * s(f"K{n}0_E")
    C30, C50, C70 = s("C30"), s("C50"), s("C70")
    Q20, K40, K60 = s("K20"), s("K40"), s("K60")
    b3 = s("C31") + 2 * vv * j[1]
    h4 = s("K41") - 2 * Q20 * b3 + lam[2]
    b5 = s("C51") - 3 * C30 * b3 - 2 * vv * j[1] * h4 + 2 * vv * j[3]
    h6 = s("K61") - 2 * Q20 * b5 - 4 * K40 * b3 - lam[2] * h4 + lam[4]
    b7 = s("C71") - 3 * C30 * b5 - 5 * C50 * b3 - 2 * vv * j[1] * h6 - 2 * vv * j[3] * h4 + 2 * vv * j[5]
    h8 = s("K81") - 2 * Q20 * b7 - 4 * K40 * b5 - 6 * K60 * b3 - lam[2] * h6 - lam[4] * h4 + lam[6]
    b9 = (s("C91") - 3 * C30 * b7 - 5 * C50 * b5 - 7 * C70 * b3
          - 2 * vv * j[1] * h8 - 2 * vv * j[3] * h6 - 2 * vv * j[5] * h4 + 2 * vv * j[7])
    return {"b3": b3, "h4": h4, "b5": b5, "h6": h6, "b7": b7, "h8": h8, "b9": b9}


def compare_with_note(out):
    log("-" * 78)
    log("Comparison with the note's recurrence (eq:subtraction, h8/b9 at lines 1149-1155)")
    log("  K20 = Q2 (two-kink current response),  h2 must be -1 identically")
    nr = note_recurrence(b0 ** 2)
    # h2: R1[H] at g^2 is sqrt2 b0 K21 ; the note writes -1 because [eps^0 l^1]Q2 = -1 for all v,delta
    log("  derived h2 =", out["h2"], " (note: -1, since [eps^0 l^1]Q2(v,delta) = -1 identically)")
    sub_h2 = {sp.Symbol("K21"): -1}
    ok = True
    for key in ["b3", "h4", "b5", "h6", "b7", "h8", "b9"]:
        d = sp.expand(out[key].subs(sub_h2) - nr[key])
        log(f"  {key}: derived - note = {d}")
        ok &= (d == 0)
    zero = [k for k in out if out[k] == 0]
    log("  vanishing coefficients (parity):", zero)
    log("  ==> AGREEMENT" if ok else "  ==> DISCREPANCY")
    return ok


# --------------------------------------------------------------------------
# Part 1C : essential couplings
# --------------------------------------------------------------------------
def part_1C():
    log("=" * 78)
    log("PART 1C: essential couplings via eq:matching (b0 kept variable)")
    log("=" * 78)
    Bg, Bh = sp.symbols("beta_g beta_h")   # auxiliary betas at h=0 (functions of g, b0)
    # cutoff-unit (essential) couplings as functions of auxiliary bare (g,h,b0) and ell
    Y = g * sp.exp(ell + b0 ** 2 * (1 - sp.exp(dl * ell)) / dl)
    vB = (b0 - S2 * h) ** 2 * sp.exp(dl * ell)
    # beta_ess = -d/dell (Y,vB) at fixed renormalized couplings, at ell=0:
    #   = -dY/dell|aux + dY/dg beta_g + dY/dh beta_h      (d g_bare/d ell|ren = -beta_g at ell=0)
    def betaE(Xc):
        return (-sp.diff(Xc, ell) + sp.diff(Xc, g) * Bg + sp.diff(Xc, h) * Bh).subs(ell, 0)
    bY = sp.simplify(betaE(Y).subs(h, 0))
    bV = sp.simplify(betaE(vB).subs(h, 0))
    log("beta_Y =", bY)
    log("beta_v =", bV)
    vv, z, u = sp.symbols("v z u")
    # F = beta_u/(2u) = beta_Y/Y ; H = beta_v/v  (u=Y^2=g^2 at ell=0, v=b0^2)
    F = sp.expand(bY / g)
    H = sp.expand(bV / b0 ** 2)
    log("F = beta_Y/Y =", F, "   ->  z + beta_g/g  with z = b0^2 - 1")
    log("H = beta_v/v =", H, "   ->  -delta - 2 sqrt2 beta_h / b0")
    # with beta_g = sum b_n g^n, beta_h = sqrt2 b0 sum h_n g^n :
    bs = {n: sp.Symbol(f"b{n}") for n in (3, 5, 7, 9)}
    hs = {n: sp.Symbol(f"h{n}") for n in (2, 4, 6, 8)}
    Fsub = sp.expand(F.subs(Bg, sum(bs[n] * g ** n for n in bs)))
    Hsub = sp.expand(H.subs(Bh, S2 * b0 * sum(hs[n] * g ** n for n in hs)))
    Fsub = sp.expand(Fsub.subs(b0, sp.sqrt(1 + z)).subs(g, sp.sqrt(u)))
    Hsub = sp.expand(Hsub.subs(b0, sp.sqrt(1 + z)).subs(g, sp.sqrt(u)))
    log("F(u,z) =", sp.collect(Fsub, u))
    log("H(u,z) =", sp.collect(Hsub, u))
    assert sp.expand(Fsub - (z + sum(bs[n] * u ** ((n - 1) // 2) for n in bs))) == 0
    assert sp.expand(Hsub - (-dl - 4 * sum(hs[n] * u ** (n // 2) for n in hs))) == 0
    log("  ==> F = z + b3 u + b5 u^2 + b7 u^3 + b9 u^4 ;  H = -delta - 4(h2 u + h4 u^2 + h6 u^3 + h8 u^4)")
    log("      with h2=-1: H = -delta + 4u - 4h4 u^2 - 4h6 u^3 - 4h8 u^4 ; all b_n,h_n at v=1+z.")
    log("  Note: only the ell-linear part of the matching enters beta (canonical terms z and -delta);")
    log("        b0 must be variable (Y depends on b0^2, giving the tree term z).")
    return Fsub, Hsub


# --------------------------------------------------------------------------
# Part 1D : eq:fugmatch and the appendix finite-delta counterterm
# --------------------------------------------------------------------------
def part_1D():
    log("=" * 78)
    log("PART 1D: eq:fugmatch expansion; effect on bare counterterms only")
    log("=" * 78)
    fac = sp.exp(ell + (1 - sp.exp(dl * ell)) / dl)
    ser = sp.expand(sp.series(fac, dl, 0, 3).removeO())
    log("Y/g_aux at b0=1 =", sp.collect(ser, dl))
    assert sp.expand(ser - (1 - dl * ell ** 2 / 2 + dl ** 2 * (ell ** 4 / 8 - ell ** 3 / 6))) == 0
    # appendix: g_bare|_{delta g^3} -> Y_bare|_{delta g^3}
    p = sp.Symbol("p")
    gb = g + g ** 3 * (2 * ell ** 2 - ell) + dl * g ** 3 * (-ell ** 4 / 3 + sp.Rational(5, 3) * ell ** 3 + 2 * z2 * ell ** 2 - p * ell)
    Yb = sp.expand(gb * ser)
    c = sp.expand(Yb.coeff(dl, 1).coeff(g, 3))
    log("Y_bare|_{delta g^3} =", c, "   appendix lo:eq:physicalDeltaCt: -4/3 l^4 + 13/6 l^3 + 2 z2 l^2 - p l")
    assert sp.expand(c - (-sp.Rational(4, 3) * ell ** 4 + sp.Rational(13, 6) * ell ** 3 + 2 * z2 * ell ** 2 - p * ell)) == 0
    log("  single log -p*ell unchanged: the ell^2, ell^3,... terms of eq:fugmatch only reshuffle")
    log("  higher logarithms; the beta coefficient p = d_delta b3 is fixed by J0 beta = R1 alone.")
    # also derive the one-pair finite-delta current counterterm consistency
    return True


# --------------------------------------------------------------------------
# Part 1E : explicit beta-input formulas (derivative dictionary)
# --------------------------------------------------------------------------
DICT = {
    # name: (which, dv, dd, factor)   which in b3,b5,b7,b9,h4,h6,h8 ; Taylor coefficient * factor
    "a": ("b3", 1, 0, 1), "p": ("b3", 0, 1, 1), "A": ("b3", 2, 0, 1), "E": ("b3", 1, 1, 1),
    "V": ("b3", 0, 2, 1), "alpha": ("b3", 3, 0, 1), "beta": ("b3", 2, 1, 1), "gamma": ("b3", 1, 2, 1),
    "b": ("b5", 0, 0, 1), "G": ("b5", 1, 0, 1), "R": ("b5", 0, 1, 1), "Phi": ("b5", 2, 0, 1),
    "Psi": ("b5", 1, 1, 1), "J": ("b7", 0, 0, 1), "Omega": ("b7", 1, 0, 1),
    "c": ("h4", 0, 0, -4), "f": ("h4", 1, 0, -4), "q": ("h4", 0, 1, -4), "L": ("h4", 2, 0, -4),
    "M": ("h4", 1, 1, -4), "Q": ("h4", 0, 2, -4), "k": ("h6", 0, 0, -4), "N": ("h6", 1, 0, -4),
    "P": ("h6", 0, 1, -4), "K": ("h8", 0, 0, -4),
    # C8 extension (not needed for D4)
    "W": ("b3", 0, 3, 1), "S": ("b5", 0, 2, 1), "U": ("b7", 0, 1, 1), "J9": ("b9", 0, 0, 1),
    "L3": ("h4", 3, 0, -4), "M21": ("h4", 2, 1, -4), "M12": ("h4", 1, 2, -4),
    "N2": ("h6", 2, 0, -4), "Ndelta": ("h6", 1, 1, -4), "Kv": ("h8", 1, 0, -4),
}
NOTE_DICT = {  # note lines 1122-1136, as derivative expressions
    "a": ("b3", 1, 0, 1), "p": ("b3", 0, 1, 1), "A": ("b3", 2, 0, sp.Rational(1, 2)),
    "E": ("b3", 1, 1, 1), "V": ("b3", 0, 2, sp.Rational(1, 2)), "alpha": ("b3", 3, 0, sp.Rational(1, 6)),
    "beta": ("b3", 2, 1, sp.Rational(1, 2)), "gamma": ("b3", 1, 2, sp.Rational(1, 2)),
    "b": ("b5", 0, 0, 1), "G": ("b5", 1, 0, 1), "R": ("b5", 0, 1, 1), "Phi": ("b5", 2, 0, sp.Rational(1, 2)),
    "Psi": ("b5", 1, 1, 1), "J": ("b7", 0, 0, 1), "Omega": ("b7", 1, 0, 1),
    "c": ("h4", 0, 0, -4), "f": ("h4", 1, 0, -4), "q": ("h4", 0, 1, -4), "L": ("h4", 2, 0, -2),
    "M": ("h4", 1, 1, -4), "Q": ("h4", 0, 2, -2), "k": ("h6", 0, 0, -4), "N": ("h6", 1, 0, -4),
    "P": ("h6", 0, 1, -4), "K": ("h8", 0, 0, -4),
    "W": ("b3", 0, 3, sp.Rational(1, 6)), "S": ("b5", 0, 2, sp.Rational(1, 2)), "U": ("b7", 0, 1, 1),
    "J9": ("b9", 0, 0, 1), "L3": ("h4", 3, 0, -sp.Rational(2, 3)), "M21": ("h4", 2, 1, -2),
    "M12": ("h4", 1, 2, -2), "N2": ("h6", 2, 0, -2), "Ndelta": ("h6", 1, 1, -4), "Kv": ("h8", 1, 0, -4),
}


def part_1E_dictionary():
    log("=" * 78)
    log("PART 1E: derivative dictionary from Taylor coefficients of F, H")
    log("=" * 78)
    ok = True
    for nm, (w, dv, dd, fac) in DICT.items():
        nw, ndv, ndd, nfac = NOTE_DICT[nm]
        # Taylor coefficient [z^dv delta^dd] = derivative/(dv! dd!)
        mine = sp.Rational(fac, sp.factorial(dv) * sp.factorial(dd))
        same = (w == nw and dv == ndv and dd == ndd and sp.nsimplify(mine - nfac) == 0)
        ok &= same
        log(f"  {nm:7s} = {fac:+d} * [z^{dv} delta^{dd}] {w}  = {mine} * d^{dv+dd}{w}/dv^{dv} ddelta^{dd}"
            f"   note: {nfac}  {'OK' if same else 'MISMATCH'}")
    log("  ==> dictionary AGREES with note lines 1122-1136" if ok else "  ==> DICTIONARY DISCREPANCY")
    return ok


def explicit_input_formulas():
    """beta inputs as explicit polynomials in derivative-coefficients of normalized responses.
    Uses the derived recurrence with C_{n,k}, K_{n,k} as functions of (v, delta) and
    first eta-derivatives.  Symbols:  C5_1_vvd  = d_v^2 d_delta [eps^0 l^1] C5  (v=1, delta=0)
                                       C5_0_vE   = d_v EE [eps^0 l^0] C5, etc."""
    log("=" * 78)
    log("Explicit beta-input formulas (written to out/beta_input_formulas.txt)")
    log("=" * 78)
    vv, dd = sp.symbols("v delta")
    F = {}
    for n in ODD + EVEN:
        base = "C" if n % 2 else "K"
        for k in (0, 1):
            F[(n, k)] = sp.Function(f"{base}{n}_{k}")(vv, dd)
            F[(n, k, "E")] = sp.Function(f"{base}{n}_{k}E")(vv, dd)
    j = {1: -2 / (1 + dd)}
    for n in (3, 5, 7):
        j[n] = -2 * sp.diff(F[(n, 0)], vv) + F[(n, 0, "E")]
    lam = {}
    for n in (2, 4, 6):
        lam[n] = -2 * F[(n, 0)] - 4 * vv * sp.diff(F[(n, 0)], vv) + 2 * vv * F[(n, 0, "E")]
    C30, C50, C70 = F[(3, 0)], F[(5, 0)], F[(7, 0)]
    Q20, K40, K60 = F[(2, 0)], F[(4, 0)], F[(6, 0)]
    b3 = F[(3, 1)] + 2 * vv * j[1]
    h4 = F[(4, 1)] - 2 * Q20 * b3 + lam[2]
    b5 = F[(5, 1)] - 3 * C30 * b3 - 2 * vv * j[1] * h4 + 2 * vv * j[3]
    h6 = F[(6, 1)] - 2 * Q20 * b5 - 4 * K40 * b3 - lam[2] * h4 + lam[4]
    b7 = F[(7, 1)] - 3 * C30 * b5 - 5 * C50 * b3 - 2 * vv * j[1] * h6 - 2 * vv * j[3] * h4 + 2 * vv * j[5]
    h8 = F[(8, 1)] - 2 * Q20 * b7 - 4 * K40 * b5 - 6 * K60 * b3 - lam[2] * h6 - lam[4] * h4 + lam[6]
    b9 = (F[(9, 1)] - 3 * C30 * b7 - 5 * C50 * b5 - 7 * C70 * b3
          - 2 * vv * j[1] * h8 - 2 * vv * j[3] * h6 - 2 * vv * j[5] * h4 + 2 * vv * j[7])
    W = {"b3": b3, "b5": b5, "b7": b7, "b9": b9, "h4": h4, "h6": h6, "h8": h8}

    def symb(e):
        reps = {}
        for d in e.atoms(sp.Derivative):
            fn = str(d.expr.func)
            nv = sum(c for var, c in d.variable_count if var == vv)
            nd = sum(c for var, c in d.variable_count if var == dd)
            base, rest = fn.split("_")
            k = rest[0]
            Ef = "E" if rest.endswith("E") else ""
            reps[d] = sp.Symbol(f"{base}_{k}_" + "v" * nv + "d" * nd + Ef)
        e = e.xreplace(reps)
        for f in e.atoms(sp.Function):
            fn = str(f.func)
            base, rest = fn.split("_")
            k = rest[0]
            Ef = "E" if rest.endswith("E") else ""
            suf = Ef
            reps2 = {f: sp.Symbol(f"{base}_{k}" + (("_" + suf) if suf else ""))}
            e = e.xreplace(reps2)
        return e

    formulas = {}
    for nm, (w, dv, dd_, fac) in DICT.items():
        expr = W[w]
        if dv:
            expr = sp.diff(expr, vv, dv)
        if dd_:
            expr = sp.diff(expr, dd, dd_)
        expr = expr * sp.Rational(fac, sp.factorial(dv) * sp.factorial(dd_))
        expr = symb(expr.doit())          # derivatives/functions -> symbols first
        expr = sp.expand(expr.subs({vv: 1, dd: 0}))   # then explicit v, delta factors
        formulas[nm] = expr
    # structural simplifications at v=1: K2 = Q2 is two-kink; leave symbolic
    with open(os.path.join(OUT, "beta_input_formulas.txt"), "w") as fh:
        fh.write("# beta inputs in terms of normalized-response coefficients at v=1, delta=0\n")
        fh.write("# X_k_<v..><d..>[E] = d_v^i d_delta^j [EE] [eps^0 ell^k] X ;  X = C1(=A1),C3,C5,C7,C9,K2(=Q2),K4,K6,K8\n")
        fh.write("# j1 = -2/(1+delta) has been inserted analytically (EE A1).\n\n")
        for nm, ex in formulas.items():
            fh.write(f"{nm} = {ex}\n\n")
    for nm in ["a", "p", "c", "b", "f", "G", "q", "k"]:
        log(f"  {nm} =", formulas[nm])
    log("  (all 35 formulas in out/beta_input_formulas.txt; number of terms:",
        {k_: len(sp.Add.make_args(v_)) for k_, v_ in formulas.items()}, ")")
    return formulas


def main():
    res = {}
    res["1A"] = part_1A()
    out = part_1B()
    ok = compare_with_note(out)
    res["1B_agree"] = ok
    part_1C()
    part_1D()
    res["dict_agree"] = part_1E_dictionary()
    formulas = explicit_input_formulas()
    with open(os.path.join(OUT, "beta_input_formulas.json"), "w") as fh:
        json.dump({k_: str(v_) for k_, v_ in formulas.items()}, fh, indent=1)
    with open(os.path.join(OUT, "derive_rg.log"), "w") as fh:
        fh.write("\n".join(LOG) + "\n")
    log("done.")


if __name__ == "__main__":
    main()
