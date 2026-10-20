#!/usr/bin/env python3
"""Independent symbolic checks (review L-rigor) of L/L_general_d.tex.

(1) residue functional at general rim exponent: W_r = -N_b^r Res_{t=0} Xi_r(t)/D_b(t)^r with
    Xi_r = sum_k c_k cos(2 pi k (t + sigma/2)), D_b = sin(pi t) sin(pi(t+sigma)), computed by a direct Laurent
    expansion (not via the Bell-polynomial weights of the note/foundation) -> compare with (F2), and B_{4,3}.
(2) three-node solve -> eq:threenode and eq:W3three.
(3) RESULT.md X-form of L_d (weights' derivative) from eq:threenode.
(4) d = 1, 2, 3 specializations in terms of Y_k = N_b^4 c_k(b).
"""
import sympy as sp

t, sg = sp.symbols('t sigma')
pi = sp.pi
c0, c1, c2, c3 = sp.symbols('c0 c1 c2 c3')


def residue_weights(r, kmax):
    D = sp.sin(pi * t) * sp.sin(pi * (t + sg))
    out = []
    for k in range(kmax + 1):
        # residue = [t^(r-1)] of t^r f (regular part expanded; avoids a sympy Laurent-series pitfall)
        g = sp.cos(2 * pi * k * (t + sg / 2)) * (t / sp.sin(pi * t)) ** r / sp.sin(pi * (t + sg)) ** r
        ser = sp.series(g, t, 0, r).removeO()
        res = ser.coeff(t, r - 1)
        out.append(sp.simplify(res))
    return out


def check_F2():
    s, co = sp.sin(pi * sg), sp.cos(pi * sg)
    R4 = residue_weights(4, 3)
    W4 = sp.expand(-(R4[0] * c0 + R4[1] * c1 + R4[2] * c2 + R4[3] * c3))          # times N^4
    F2 = sp.expand(4 / (pi * s ** 7) * (co * (3 + 2 * co ** 2) * c0 + (1 + 4 * co ** 2) * c1 + 5 * co * c2))
    print('(1) r=4 residue weights vs (F2):')
    for sym in (c0, c1, c2):
        dif = sp.simplify(sp.expand_trig(W4.coeff(sym) - F2.coeff(sym)))
        num = [sp.N((W4.coeff(sym) - F2.coeff(sym)).subs(sg, v), 30) for v in (0.23, 0.41, 0.77)]
        print('   coeff', sym, 'diff =', dif, ' numeric', num)
    # top mode weight in W4 (paper: B_{4,3} = -20 pi^3/s^3 enters W_4 ... check its statement)
    w3 = sp.simplify(W4.coeff(c3))
    print('   weight of c3 in W4/N^4:', w3, '  (times (pi s)^4 with sign: B43 =', sp.simplify(R4[3] * (pi * s) ** 4), ')')
    R3 = residue_weights(3, 2)
    W3 = sp.expand(-(R3[0] * c0 + R3[1] * c1 + R3[2] * c2))
    F2_3 = sp.expand(-2 / (pi * s ** 5) * ((1 + 2 * co ** 2) * c0 + 3 * co * c1))
    print('(1) r=3 residue weights vs (F2):')
    for sym in (c0, c1):
        num = [sp.N((W3.coeff(sym) - F2_3.coeff(sym)).subs(sg, v), 30) for v in (0.23, 0.41, 0.77)]
        print('   coeff', sym, 'numeric diff', num)
    print('   weight of c2 in W3 (top mode r=3):', sp.simplify(W3.coeff(c2)))
    return F2, F2_3


def check_threenode(F2, F2_3):
    s, co = sp.sin(pi * sg), sp.cos(pi * sg)
    XT, X0, Xh = sp.symbols('XT X0 Xh')
    # t = 0 <-> tau = b/4 = sigma/2 : cos(2 pi tau) = cos(pi sigma), cos(4 pi tau) = cos(2 pi sigma)
    sol = sp.solve([sp.Eq(XT, c0 + c1 * co + c2 * sp.cos(2 * pi * sg)), sp.Eq(X0, c0 + c1 + c2),
                    sp.Eq(Xh, c0 - c1 + c2)], [c0, c1, c2], dict=True)[0]
    W = sp.expand(F2.subs(sol))
    cand = sp.expand(2 / (pi * s ** 7) * ((1 + co) ** 2 * (1 + 2 * co) * X0 - (1 - co) ** 2 * (1 - 2 * co) * Xh - 2 * co * XT))
    print('(2) three-node r=4:', [sp.N((W - cand).coeff(v).subs(sg, val), 25) for v in (XT, X0, Xh)
                                   for val in (0.23, 0.61)])
    M = sp.Matrix([[1, co, sp.cos(2 * pi * sg)], [1, 1, 1], [1, -1, 1]])
    print('    det =', sp.simplify(sp.expand_trig(M.det())), ' (paper: 4 sin^2 pi sigma up to sign)')
    sol3 = sp.solve([sp.Eq(XT, c0 + c1 * co), sp.Eq(Xh, c0 - c1)], [c0, c1], dict=True)[0]
    W3 = F2_3.subs(sol3)
    cand3 = -2 / (pi * s ** 5) * ((1 + 2 * co) * XT - 2 * co * (1 - co) * Xh)
    print('    three-node r=3:', sp.simplify(W3 - cand3))
    return cand


def check_Xform():
    # b-derivative of 2/(pi s^7) w(c) with s = sin(pi b/2), c = cos(pi b/2)
    b = sp.symbols('b')
    s, co = sp.sin(pi * b / 2), sp.cos(pi * b / 2)
    C = sp.symbols('C')
    S = sp.sqrt(1 - C ** 2)
    res = {}
    for name, w in (('X0', (1 + co) ** 2 * (1 + 2 * co)), ('Xh', -(1 - co) ** 2 * (1 - 2 * co)), ('XT', -2 * co)):
        dw = sp.diff(2 / (pi * s ** 7) * w, b)
        res[name] = dw
    claim = {'X0': -(1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2), 'Xh': -(1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2),
             'XT': 2 * (1 + 6 * C ** 2)}
    for name in res:
        devs = []
        for bv in (0.3, 0.9, 1.4, 1.9):
            Cv = sp.cos(pi * bv / 2)
            Sv = sp.sin(pi * bv / 2)
            devs.append(sp.N(res[name].subs(b, bv) - (claim[name] / Sv ** 8).subs(C, Cv), 25))
        print('(3) RESULT X-form weight derivative', name, devs)


def specializations():
    b = sp.symbols('b')
    Y0, Y1, Y2, Y0p, Y1p, Y2p = sp.symbols('Y0 Y1 Y2 Y0p Y1p Y2p')
    s, co = sp.sin(pi * b / 2), sp.cos(pi * b / 2)
    f = [co * (3 + 2 * co ** 2), 1 + 4 * co ** 2, 5 * co]
    W = 4 / (pi * s ** 7) * (f[0] * Y0 + f[1] * Y1 + f[2] * Y2)
    L = sum(sp.diff(4 / (pi * s ** 7) * f[k], b) * [Y0, Y1, Y2][k] + 4 / (pi * s ** 7) * f[k] * [Y0p, Y1p, Y2p][k]
            for k in range(3))
    # d = 3, b = 3/2
    L3 = sp.nsimplify(sp.simplify(L.subs(b, sp.Rational(3, 2))))
    P4 = sp.simplify(W.subs(b, sp.Rational(3, 2)))
    N4 = pi ** 2 / 16
    X0 = (Y0 - Y1 / sp.sqrt(2)) / N4                      # X_T/N^4 = c0 + c1 cos(3pi/4) + c2 cos(3pi/2)
    a4b4 = Y1 / (2 * N4)                                    # c1 = 2 a4 b4
    dH = (16 / pi ** 2) * (4 * Y0p + 5 * Y2p)
    b4 = sp.symbols('b4')
    da = (8 / pi ** 2) * Y1p / b4 - (pi / 2 - sp.log(2)) * a4b4 / b4
    L3c = 4 * pi * P4 - 2 * pi ** 2 * X0 + 6 * sp.sqrt(2) * pi * (pi - 2 * sp.log(2)) * a4b4 - 2 * pi * dH \
        + 12 * sp.sqrt(2) * pi * b4 * da
    print('(4) d=3: generic L - C63d L3 with dictionary =', sp.simplify(sp.expand(L3 - L3c)))
    # d = 1, b = 1/2 ; c1 = 0 ; Y0 = F(b) A(b), Y2 = F(b) B(b), F = (pi^2/4) tan^2(pi b/2), A' = d/db = d/dx
    A, B = sp.symbols('A B')
    Fb = pi ** 2 / 4 * sp.tan(pi * b / 2) ** 2
    l2 = sp.log(2)
    Ap = 2 * pi * B - 2 * l2 * A
    Bp = sp.Rational(3, 2) * pi * A - 2 * l2 * B
    sub1 = {Y0: Fb * A, Y1: 0, Y2: Fb * B,
            Y0p: sp.diff(Fb, b) * A + Fb * Ap, Y1p: 0, Y2p: sp.diff(Fb, b) * B + Fb * Bp}
    L1 = sp.simplify(L.subs(sub1).subs(b, sp.Rational(1, 2)))
    P41 = sp.simplify(W.subs(sub1).subs(b, sp.Rational(1, 2)))
    print('(4) d=1: P4 =', sp.expand(P41), '   claim 32 pi A + 40 pi B')
    print('    d=1: L1 =', sp.expand(L1))
    claim = -2 * (pi + l2) * (32 * pi * A + 40 * pi * B) + 52 * pi ** 2 * A + 64 * pi ** 2 * B
    print('    d=1: L1 - RESULT claim =', sp.simplify(sp.expand(L1 - claim)))
    Ne, Me = sp.symbols('N_e M_e')
    L1NM = sp.expand(L1.subs({A: 8 * Ne / pi, B: 8 * Me / pi}))
    print('    d=1: L1 in N_e, M_e =', sp.collect(L1NM, [Ne, Me]), '  (lp:eq:MN: -(128pi+640l)M-(96pi+512l)N)')
    # D_L(1): frozen-weight derivative of the three samples; X0 = Xh = Y0+Y2, XT = Y0 + cos(pi b) Y2
    X0b = Y0 + Y2
    XTb = Y0 + sp.cos(pi * b) * Y2
    X0p = sp.diff(X0b.subs(sub1), b) if False else (sub1[Y0p] + sub1[Y2p])
    XTp = sub1[Y0p] + sp.cos(pi * b) * sub1[Y2p] - pi * sp.sin(pi * b) * sub1[Y2]
    C = sp.cos(pi * b / 2)
    DL = ((1 + C) ** 2 * (1 + 2 * C) - (1 - C) ** 2 * (1 - 2 * C)) * X0p - 2 * C * XTp
    DL1 = sp.simplify(DL.subs(b, sp.Rational(1, 2)))
    claimDL = sp.sqrt(2) * pi ** 2 / 4 * ((31 * pi / 2 - 8 * l2) * A + (19 * pi - 10 * l2) * B)
    print('    d=1: D_L - RESULT claim =', sp.simplify(sp.expand(DL1 - claimDL)))
    # d = 2, b = 1 ; N_b^4 Xi = (A + B cos 2 pi tau)^2 with A = A(x = b/2): d/db = (1/2) d/dx
    Ab = sp.Function('A')(b)
    Bb = sp.Function('B')(b)
    Y0d2 = Ab ** 2 + Bb ** 2 / 2
    Y1d2 = 2 * Ab * Bb
    Y2d2 = Bb ** 2 / 2
    sub2 = {Y0: Y0d2, Y1: Y1d2, Y2: Y2d2, Y0p: sp.diff(Y0d2, b), Y1p: sp.diff(Y1d2, b), Y2p: sp.diff(Y2d2, b)}
    dA, dB = sp.symbols('dA dB')
    L2 = L.subs(sub2)
    L2 = L2.subs({sp.Derivative(Ab, b): dA, sp.Derivative(Bb, b): dB}).subs({Ab: A, Bb: B}).subs(b, 1)
    L2 = L2.subs({dA: Ap / 2, dB: Bp / 2})
    P42 = sp.simplify(W.subs(sub2).subs({Ab: A, Bb: B}).subs(b, 1))
    print('(4) d=2: P4 =', P42, ';  L2 =', sp.simplify(L2), ';  L2 + 2 log2 P4 =', sp.simplify(L2 + 2 * l2 * P42))


if __name__ == '__main__':
    F2, F2_3 = check_F2()
    check_threenode(F2, F2_3)
    check_Xform()
    specializations()
