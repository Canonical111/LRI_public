#!/usr/bin/env python3
"""C62d's d=2 check of the OPE package (lri_ope_reproducibility, supplied by the author 2026-10-16).

Independent of the package code: every d=2 input below is taken from the condensed GFF note
(GFF/LRI_condensed_note, HEAD 22a2850), and only the package's *formulas* (h_1..h_4, the log map,
the d=2 closed map, the Borel-Pade prescription) are re-implemented from the text of
note/lri_ope_note.tex. Nothing is imported from the package.

Checks
  E  exact (sympy): (i) the d=2 elimination formulas for Q_2, P_4(2); (ii) the compact d=2 log map
     ell_1..ell_4 against log[(1+h_1 e+...+h_4 e^4)/(1+e/2)], with C_3..C_5(2) from the note's
     d=2 coefficient formulas and K_2, L_2, Z_2 from its closed forms; (iii) the general-d log map
     at d=2; (iv) Omega_2.
  N  numeric (mpmath, 60 digits): masters from the note's closed forms, C_3..C_5(2) against the
     note's table, a_2..a_6(2) against the package's table, Omega_2 two ways, a_6(2) via the
     compact map, and the 2d Borel-Pade point (d, eps) = (2, 0.3) of the package's Sec. 7.
Usage: python -I ope_d2_check.py [--dps 60] [--out FILE.json]
"""
import argparse
import json
import sys

import mpmath as mp
import sympy as s


# ----------------------------------------------------------------------------- exact part
def exact_checks():
    t, G, z3, P4, P5, Q, e = s.symbols('t G z3 P4 P5 Q e')
    c3, c4, c5 = s.symbols('c3 c4 c5')
    # d=2 basis (q=1/2): A=4 log2, R=0, U=psi_2(1/2)=-14 z3, V=2 psi_2(1)=-4 z3, X=0, T=6 Q_2,
    # B_j = j! 2^(j+1).
    A, R, U, V, X, T = 4*t, 0, -14*z3, -4*z3, 0, 6*Q
    B = [s.factorial(j)*2**(j+1) for j in range(4)]
    # condensed note, gc:L2closed, gc:K2closed, gs:Z2exact
    K2, L2, Z2 = 32*G**2 - 28*z3*t, -2*t*P4, 4*G*Q
    # condensed note, gc:d2coefficients (a = log 2)
    C3 = s.Rational(4, 27)*t**2 - 2*Q/27              # Gamma(1/4)^8/(324 pi^4) = 2 Q_2/27
    C4 = (16*P4 - 64*t**3 - 32*t*Q - 359*z3)/648
    C5 = (-1536*(P5 + K2) + 1536*t*P4 - 576*L2 - 1728*Q**2 + (11520*t**2 + 28608*G)*Q
          - 3840*t**4 - 21456*t*z3)/46656
    # cross-check C5 against the note's gc:C5twoClosed
    C5b = (-32*P5 + 56*t*P4 - 36*Q**2 + (240*t**2 + 596*G)*Q - 1024*G**2 + 449*z3*t - 80*t**4)/972
    out = {'C5_two_forms': str(s.expand(C5 - C5b))}
    # package eq. (eq:d2eliminate): solve C3, C4 for Q_2, P_4(2)
    Qs = 2*t**2 - s.Rational(27, 2)*c3
    P4s = s.Rational(81, 2)*c4 + 8*t**3 - 27*t*c3 + s.Rational(359, 16)*z3
    out['Q2_elimination'] = str(s.expand(Qs.subs(c3, C3) - Q))
    out['P4_elimination'] = str(s.expand(P4s.subs({c3: C3, c4: C4}) - P4))
    # package h_1..h_4 (eqs. h1-h4) at d=2
    h1 = s.Rational(4, 3)*A
    h2 = s.Rational(25, 36)*A**2 + R/6 - s.Rational(2, 27)*T
    h3 = (s.Rational(17, 108)*A**3 + A*R/12 - s.Rational(2, 27)*A*T + s.Rational(4, 27)*P4
          + s.Rational(71, 216)*U - V/36)
    h4 = (-s.Rational(7, 5184)*A**4 - s.Rational(7, 288)*A**2*R - s.Rational(7, 972)*A**2*T
          + s.Rational(14, 81)*A*P4 + s.Rational(301, 864)*A*U - s.Rational(7, 144)*A*V
          - s.Rational(28, 81)*K2 - s.Rational(7, 81)*L2 - s.Rational(16, 81)*P5
          - s.Rational(103, 5184)*R**2 + s.Rational(7, 324)*R*T - s.Rational(7, 1458)*T**2
          - s.Rational(61, 3888)*X + s.Rational(175, 162)*Z2)
    # log of (1+h1 e+..)/(1+e/2): the d=2 outer factor Gamma(-1/2-e/4)/Gamma(1/2-e/4) = -2/(1+e/2)
    series = s.series(s.log(1 + h1*e + h2*e**2 + h3*e**3 + h4*e**4) - s.log(1 + e/2), e, 0, 5).removeO()
    ell = [s.expand(series.coeff(e, k)) for k in range(1, 5)]
    # package eqs. d2log1..d2log4 with c_j -> the note's C_j(2)
    compact = [16*t/3 - s.Rational(1, 2),
               6*c3 - 4*t**2 + s.Rational(1, 8),
               6*c4 - 12*t*c3 + s.Rational(304, 81)*t**3 - s.Rational(7, 6)*z3 - s.Rational(1, 24),
               (6*c5 - 11*t*c4 + (46*t**2 - 26*G)/3*c3 - 9*c3**2 - s.Rational(380, 81)*t**4
                + s.Rational(104, 81)*G*t**2 - s.Rational(128, 27)*G**2 + s.Rational(1303, 216)*t*z3
                + s.Rational(1, 64))]
    sub = {c3: C3, c4: C4, c5: C5}
    for k in range(4):
        out[f'd2log{k+1}'] = str(s.expand(compact[k].subs(sub) - ell[k]))
    # package general-d log map (eqs. logmap1-logmap4) at d=2, Omega from its definition
    Om = 13*Z2 - L2 - 12*K2
    general = [12*(A/9) - B[0]/4,
               6*c3 - A**2/4 + R/9 + s.Rational(B[1], 32),
               6*c4 - 3*A*c3 + s.Rational(19, 324)*A**3 - A*R/12 + U/12 - s.Rational(B[2], 384),
               (6*c5 - 3*A*c4 + (A**2 - s.Rational(5, 6)*R)*c3 - 9*c3**2 - s.Rational(11, 576)*A**4
                + s.Rational(37, 864)*A**2*R - s.Rational(53, 2592)*A*U - s.Rational(5, 432)*A*V
                - s.Rational(53, 5184)*R**2 - s.Rational(47, 7776)*X + Om/81 + s.Rational(B[3], 6144))]
    for k in range(4):
        out[f'logmap{k+1}_at_d2'] = str(s.expand(general[k].subs(sub) - ell[k]))
    # Omega_2 in the package's omega_two form, with Q, P4 eliminated through C3, C4
    om_two = 52*G*Qs + 2*t*P4s - 384*G**2 + 336*t*z3
    out['Omega2_form'] = str(s.expand(om_two.subs({c3: C3, c4: C4}) - Om))
    # a_6(2) through the package's eq. d2ratio
    a6r = h4 - h3/2 + h2/4 - h1/8 + s.Rational(1, 16)
    lin = s.series(s.exp(sum(ell[k]*e**(k+1) for k in range(4))), e, 0, 5).removeO()
    out['d2ratio_a6'] = str(s.expand(lin.coeff(e, 4) - a6r))
    # exact a_n(2) as displayed in the d=2 subsection (ope:d2exact), against -(1/27) x [e^k] of
    # (1+h1 e+...+h4 e^4)/(1+e/2)
    ratio = s.series((1 + h1*e + h2*e**2 + h3*e**3 + h4*e**4)/(1 + e/2), e, 0, 5).removeO()
    shown = {3: s.Rational(1, 54) - 16*t/81,
             4: -(s.Rational(1, 4) - 8*t/3 + 100*t**2/9 - 4*Q/9)/27,
             5: -(-s.Rational(1, 8) + 4*t/3 - 50*t**2/9 + 272*t**3/27 - s.Rational(485, 108)*z3
                  + (s.Rational(2, 9) - 16*t/9)*Q + s.Rational(4, 27)*P4)/27,
             6: -(s.Rational(1, 16) - 2*t/3 + 25*t**2/9 - 136*t**3/27 - 28*t**4/81
                  + s.Rational(485, 216)*z3 - s.Rational(2933, 324)*t*z3 - s.Rational(896, 81)*G**2
                  + (s.Rational(350, 81)*G - 56*t**2/81 + 8*t/9 - s.Rational(1, 9))*Q
                  - s.Rational(14, 81)*Q**2 + (70*t/81 - s.Rational(2, 27))*P4 - s.Rational(16, 81)*P5)/27}
    for n, v in shown.items():
        out[f'exact_a{n}(2)'] = str(s.expand(v + ratio.coeff(e, n - 2)/27))
    out['Omega2_expanded'] = str(s.expand(Om - (52*G*Q + 2*t*P4 - 384*G**2 + 336*t*z3)))
    return out, {'h': (h1, h2, h3, h4), 'C': (C3, C4, C5), 'Omega': Om, 'syms': (t, G, z3, P4, P5, Q)}


# ----------------------------------------------------------------------------- numeric part
def masters_from_note():
    t, G, z3, pi = mp.log(2), mp.catalan, mp.zeta(3), mp.pi
    g4 = mp.gamma(mp.mpf(1)/4)
    Q2 = g4**8/(24*pi**4)                                                 # gc:Q2
    Fm = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
    Fp = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
    Bm, Bp = g4**4*Fm, 64*pi**4/g4**4*Fp
    P4 = (Bm**2 - Bp**2)/(4*pi**3)                                        # fp:P4two

    def Y(r):                                                             # fp:YDictionary
        r = mp.mpf(r)
        a, b = (r + 2)/8, (r + 6)/8
        return r/8*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper([1, 1 + r/8] + [a]*7, [r/8] + [b]*7, -1)
    c8, s8 = mp.cos(pi/8), mp.sin(pi/8)
    X0, Xp, Xm = Y(2), c8**7*Y(3) - s8**7*Y(5), c8**7*Y(1) + s8**7*Y(7)
    P5 = 8/pi*(25*X0**2 - 28*mp.sqrt(2)*X0*(Xp + Xm) + 18*(Xp**2 + Xm**2) + 28*Xp*Xm)   # fp:P5two
    return {'t': t, 'G': G, 'z3': z3, 'Q2': Q2, 'P4': P4, 'P5': P5,
            'K2': 32*G**2 - 28*z3*t, 'L2': -2*t*P4, 'Z2': 4*G*Q2}


def borel_pade(c, L, M, x):
    """Package Sec. 7: F_[L/M](x) = int_0^oo e^{-u} [L/M]_{BF}(x u) du, BF = sum c_k u^k / k!."""
    b = [c[k]/mp.factorial(k) for k in range(L + M + 1)]
    p, q = mp.pade(b, L, M)
    roots = mp.polyroots(q[::-1]) if M > 0 else []
    pos = [r for r in roots if abs(mp.im(r)) < mp.mpf(10)**(-20) and mp.re(r) > 0]
    f = lambda u: mp.exp(-u)*mp.polyval(p[::-1], x*u)/mp.polyval(q[::-1], x*u)
    return mp.quad(f, [0, 1, 10, mp.inf]), [mp.nstr(r, 8) for r in roots], len(pos)


def numeric_checks(sym):
    m = masters_from_note()
    t, G, z3, P4s, P5s, Qs = sym['syms']
    args = (m['t'], m['G'], m['z3'], m['P4'], m['P5'], m['Q2'])
    ev = lambda ex: s.lambdify((t, G, z3, P4s, P5s, Qs), ex, 'mpmath')(*args)
    C3, C4, C5 = (ev(x) for x in sym['C'])
    h = [ev(x) for x in sym['h']]
    a2 = -mp.mpf(1)/27
    hs = [mp.mpf(1)] + h
    a = {n: a2*sum(hs[j]*(-mp.mpf(1)/2)**(n - 2 - j) for j in range(n - 1)) for n in range(2, 7)}
    Om = 13*m['Z2'] - m['L2'] - 12*m['K2']
    tt, GG, zz = m['t'], m['G'], m['z3']
    Qe = 2*tt**2 - mp.mpf(27)/2*C3
    P4e = mp.mpf(81)/2*C4 + 8*tt**3 - 27*tt*C3 + mp.mpf(359)/16*zz
    om_two = 52*GG*Qe + 2*tt*P4e - 384*GG**2 + 336*tt*zz
    ell = [16*tt/3 - mp.mpf(1)/2, 6*C3 - 4*tt**2 + mp.mpf(1)/8,
           6*C4 - 12*tt*C3 + mp.mpf(304)/81*tt**3 - mp.mpf(7)/6*zz - mp.mpf(1)/24,
           (6*C5 - 11*tt*C4 + (46*tt**2 - 26*GG)/3*C3 - 9*C3**2 - mp.mpf(380)/81*tt**4
            + mp.mpf(104)/81*GG*tt**2 - mp.mpf(128)/27*GG**2 + mp.mpf(1303)/216*tt*zz + mp.mpf(1)/64)]
    r = [mp.mpf(1)]
    for n in range(1, 5):
        r.append(sum(j*ell[j - 1]*r[n - j] for j in range(1, n + 1))/n)
    a_log = {n + 2: a2*r[n] for n in range(5)}

    claims = {  # package note, Table tab:coefficients and eq. d2-updated; README; condensed-note table
        'a2': '-0.0370370370370', 'a3': '-0.118399443074', 'a4': '0.0717109289556',
        'a5': '-0.751719824443', 'a6': '6.099467952385830582',
        'a6_historical': '6.099467952386100308',
        'C3': '-0.874850012653', 'C4': '5.048868431', 'C5': '-38.833645896',
        'P4_note': '250.48731558186728553185175688791140716835571092358',
        'L2_note': '-347.24915312320113105847678307522316920816760199487',
        'K2_note': '3.5181091385902522416490901703077395226226728094710',
        'Q2_note': '12.7713811986469576577497636845240084220372849859347',
        'pkg_T': '76.628287191881745946498582107144050532223709915607993587500504784',
        'pkg_P4': '250.48731558186728553185175688791140716835571092358366654053930764',
        'pkg_P5': '1548.0826402331206151324390739457893403881102323228503714758370968',
        'pkg_K_hist': '3.518109138591562', 'pkg_L_hist': '-347.2491531231221',
        'pkg_Z': '46.792583072329696656738825877981084215947919848450519873953130477'}
    cmp = lambda x, c: mp.nstr(x - mp.mpf(claims[c]), 3)
    res = {
        'masters': {k: mp.nstr(v, 40) for k, v in m.items() if k not in ('t', 'G', 'z3')},
        'Omega2': mp.nstr(Om, 40), 'Omega2_via_C3C4_minus_def': mp.nstr(om_two - Om, 3),
        'C': {'C3': mp.nstr(C3, 30), 'C4': mp.nstr(C4, 30), 'C5': mp.nstr(C5, 30),
              'C3-table': cmp(C3, 'C3'), 'C4-table': cmp(C4, 'C4'), 'C5-table': cmp(C5, 'C5')},
        'master_diffs': {'P4-note': cmp(m['P4'], 'P4_note'), 'L2-note': cmp(m['L2'], 'L2_note'),
                         'K2-note': cmp(m['K2'], 'K2_note'), 'Q2-note': cmp(m['Q2'], 'Q2_note'),
                         '6Q2-pkgT': cmp(6*m['Q2'], 'pkg_T'), 'P4-pkg': cmp(m['P4'], 'pkg_P4'),
                         'P5-pkg': cmp(m['P5'], 'pkg_P5'), 'Z2-pkg': cmp(m['Z2'], 'pkg_Z'),
                         'K2-pkg_hist': cmp(m['K2'], 'pkg_K_hist'), 'L2-pkg_hist': cmp(m['L2'], 'pkg_L_hist')},
        'h': [mp.nstr(x, 30) for x in h],
        'a': {f'a{n}': mp.nstr(a[n], 25) for n in a},
        'a-claim': {f'a{n}': cmp(a[n], f'a{n}') for n in a},
        'a6-historical_claim': cmp(a[6], 'a6_historical'),
        'a_log_map-a': {f'a{n}': mp.nstr(a_log[n] - a[n], 3) for n in a},
        'ell': [mp.nstr(x, 25) for x in ell],
    }
    # ------------------------------------------------------------ 2d Borel-Pade point
    x = mp.mpf('0.3')
    F = [a[n] for n in range(2, 7)]                       # a_phi2/eps^2
    bp = {}
    for (L, M) in ((3, 1), (1, 3), (2, 2)):
        val, roots, npos = borel_pade(F, L, M, x)
        bp[f'a_[{L}/{M}]'] = {'value': mp.nstr(x**2*val, 10), 'Borel_poles': roots, 'positive_real': npos}
    partial = {f'through_eps{k}': mp.nstr(sum(a[n]*x**n for n in range(2, k + 1)), 12) for k in (4, 5, 6)}
    C2 = 4*tt/9
    th_fixed = [mp.mpf(1), -mp.mpf(1)/6, C2, C3, C4, C5]
    for label, C6 in (('historical_362.3', '362.3'), ('current_362.366', '362.366'),
                      ('362.366+0.004', '362.370'), ('362.366-0.004', '362.362')):
        cs = th_fixed + [mp.mpf(C6)]
        val, roots, npos = borel_pade(cs, 4, 2, x)
        v32, _, np32 = borel_pade(cs[:6], 3, 2, x)
        bp[f'Delta_[4/2]_{label}'] = {'value': mp.nstr(val, 10), 'Borel_poles': roots, 'positive_real': npos,
                                      'Delta_[3/2]_through_C5': mp.nstr(v32, 10), 'positive_real_[3/2]': np32}
    # diagnostic only: the condensed note also has C7(2) = -3876.1 +- 2.1 (Sec 28), C8(2) = 45990 +- 33 (Sec 31)
    cs8 = th_fixed + [mp.mpf('362.366'), mp.mpf('-3876.1'), mp.mpf('45990')]
    for (L, M) in ((4, 3), (3, 4), (4, 4), (5, 3), (3, 5)):
        n = L + M
        val, roots, npos = borel_pade(cs8[:n + 1], L, M, x)
        bp[f'diag_Delta_[{L}/{M}]_through_C{n}'] = {'value': mp.nstr(val, 10), 'positive_real': npos}
    bp['diag_partial_sums_Delta'] = {f'through_C{k}': mp.nstr(sum(cs8[j]*x**j for j in range(k + 1)), 10)
                                     for k in range(4, 9)}
    pkg = {'a_[3/1]': '-0.00654824', 'a_[1/3]': '-0.00601150', 'Delta_[4/2]_historical': '0.96781787',
           'partial': ['-0.00594925977', '-0.00777593895', '-0.00332942681'],
           'Delta_shift_current_minus_historical': '1.75e-6', 'kink_reading': '(-0.00676, 0.960)'}
    res['bootstrap_2d'] = {'point': '(d, eps) = (2, 0.3), Delta_phi = 0.425', 'ours': bp,
                           'a_partial_sums': partial, 'package_claims': pkg}
    # ------------------------------------------------------------ all four 2d points of the package
    # Delta_phi = (2 - eps)/4 = 0.425, 0.35, 0.275, 0.2; current thermal input C6(2) = 362.366.
    # An approximant with a positive-axis Borel pole is rejected (value None), as in the package.
    def bp_or_none(c, L, M, xx, scale=1):
        val, _, npos = borel_pade(c, L, M, xx)
        return None if npos else mp.nstr(scale*val, 10)
    cs6 = th_fixed + [mp.mpf('362.366')]
    rows = []
    for lab, ex in (('A', '0.3'), ('B', '0.6'), ('C', '0.9'), ('D', '1.2')):
        xx = mp.mpf(ex)
        row = {'label': lab, 'eps': ex, 'Delta_phi': mp.nstr((2 - xx)/4, 4),
               'a_[3/1]': bp_or_none(F, 3, 1, xx, xx**2), 'a_[1/3]': bp_or_none(F, 1, 3, xx, xx**2),
               'Delta_[4/2]': bp_or_none(cs6, 4, 2, xx)}
        # diagnostic: through C8(2) with [5/3], and its sensitivity to C7(2) +- 2.1, C8(2) +- 33
        vals = {}
        for d7 in (-1, 0, 1):
            for d8 in (-1, 0, 1):
                c = cs6 + [mp.mpf('-3876.1') + d7*mp.mpf('2.1'), mp.mpf('45990') + d8*33]
                vals[(d7, d8)] = bp_or_none(c, 5, 3, xx)
        row['diag_Delta_[5/3]_through_C8'] = vals[(0, 0)]
        good = [mp.mpf(v) for v in vals.values() if v is not None]
        row['diag_[5/3]_range_over_C7C8_allowances'] = (
            [mp.nstr(min(good), 10), mp.nstr(max(good), 10)] if len(good) == 9 else f'{9 - len(good)} of 9 rejected')
        rows.append(row)
    res['bootstrap_2d_rows'] = rows
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dps', type=int, default=60)
    ap.add_argument('--out')
    a = ap.parse_args()
    mp.mp.dps = a.dps
    ex, sym = exact_checks()
    bad = [k for k, v in ex.items() if v != '0']
    res = {'exact_residuals': ex, 'exact_status': 'PASS' if not bad else f'FAIL {bad}',
           'numeric': numeric_checks(sym), 'dps': a.dps,
           'python': sys.version.split()[0], 'mpmath': mp.__version__, 'sympy': s.__version__}
    txt = json.dumps(res, indent=2)
    if a.out:
        open(a.out, 'w').write(txt + '\n')
    print(txt)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
