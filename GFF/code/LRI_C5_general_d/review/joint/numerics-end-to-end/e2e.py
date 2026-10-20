#!/usr/bin/env python3
"""End-to-end numerics of the combined general-d fragments (gdr + gdk), review key numerics-end-to-end.

All formulas below are transcribed by hand from the printed TeX:
  gdr:P4, gdr:L, gdr:frozen, gdr:twonode, gdr:Q, gdr:Z, gdr:C5reduced (general_d.tex l.486-531, 744-760),
  gdr:special d=1,2,3 claims (l.620-700),
  gdk:xh, gdk:sk, gdk:Kr3, gdk:rLow (K_d_fragment.tex l.144-200), gdk values table (l.760-775),
  gs:C5, gs:psiBasis (note l.2803-2827).
Sample data (X_T, X_0, X_1/2, b-derivatives, T3, M3, c0hat jets) come from the supporting codes L/, Z/ (dump_samples.py,
symmetry job 569478, dps 60).  r3 is taken (a) from the printed gdk table, (b) from my own Cauchy extraction of
C63d's stored 72-digit circle points R_part/prod/prod_B_d*.json.
usage: python3 e2e.py samples_dps60.json
"""
import json, os, sys
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
from consts import note_values  # noqa: E402

DPS = 60
mp.mp.dps = DPS
pi = mp.pi


def P(dstr):
    if '/' in dstr:
        a, b = dstr.split('/')
        return mp.mpf(a) / mp.mpf(b)
    return mp.mpf(dstr)


def basis(q):
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    R = mp.psi(1, 2 * q) - mp.psi(1, 1)
    U = mp.psi(2, q)
    V = mp.psi(2, 1) + mp.psi(2, 2 * q)
    X = mp.psi(3, 2 * q) - mp.psi(3, 1)
    return A, R, U, V, X


# ---------------------------------------------------------------- gdr printed formulas
def gdr_P4(S, C, X0, Xh, XT):
    return 2 / (pi * S ** 7) * ((1 + C) ** 2 * (1 + 2 * C) * X0 - (1 - C) ** 2 * (1 - 2 * C) * Xh - 2 * C * XT)


def gdr_DL(C, dX0, dXh, dXT):
    return (1 + C) ** 2 * (1 + 2 * C) * dX0 - (1 - C) ** 2 * (1 - 2 * C) * dXh - 2 * C * dXT


def gdr_L(S, C, X0, Xh, XT, DL):
    return -(1 / S ** 8) * ((1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2) * X0 + (1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2) * Xh
                            - 2 * (1 + 6 * C ** 2) * XT) + 2 / (pi * S ** 7) * DL


def gdr_3Q(S, T3, c0):
    return 6 * pi ** 2 / S ** 2 * T3 + 4 / (pi * S ** 3) * c0


def gdr_Z(d, S, C, T3pp, Q, c0, c0p, c0pp):
    return (2 * pi ** 2 / (3 * S ** 2) * T3pp - pi ** 2 * mp.cos(pi * d / 2) / (6 * S ** 2) * Q
            + (pi * (1 + C ** 2) / S ** 5 * c0 - 4 * C / S ** 4 * c0p + 4 / (pi * S ** 3) * c0pp) / 9)


def u_of(b):
    return 2 * pi ** 2 * (1 + 2 * mp.cos(pi * b / 2)) / mp.sin(pi * b / 2) ** 2


def v_of(b):
    c = mp.cos(pi * b / 2)
    return c * (1 + c) ** 2 / (2 * pi * mp.sin(pi * b / 2) ** 3)


def c0_from(b, T3, M3):
    c, s = mp.cos(pi * b / 2), mp.sin(pi * b / 2)
    return c * (1 + c) ** 2 / 8 * M3 - pi ** 3 * s ** 3 / (1 + c) * T3


def gdr_C5reduced(d, P5, K, X0, Xh, XT, DL, T3, T3pp, c0, c0p, c0pp):
    q = d / 4
    S, C = mp.sin(pi * q), mp.cos(pi * q)
    A, R, U, V, X = basis(q)
    k0 = (1 + C) ** 2 * (768 * A * (1 + 2 * C) / (pi * S ** 7) + 576 * (4 + 9 * C + 8 * C ** 2) / S ** 8)
    kh = (1 - C) ** 2 * (-768 * A * (1 - 2 * C) / (pi * S ** 7) + 576 * (4 - 9 * C + 8 * C ** 2) / S ** 8)
    kT = -1536 * A * C / (pi * S ** 7) - 1152 * (1 + 6 * C ** 2) / S ** 8
    Q = 2 * pi ** 2 / S ** 2 * T3 + 4 / (3 * pi * S ** 3) * c0
    tot = (-1536 * (P5 + K) - 1728 * Q ** 2 + (720 * A ** 2 + 1008 * R - 1192 * pi ** 2 * mp.cos(pi * d / 2) / S ** 2) * Q
           + k0 * X0 + kh * Xh + kT * XT - 1152 / (pi * S ** 7) * DL + 4768 * pi ** 2 / S ** 2 * T3pp
           + mp.mpf(2384) / 3 * (pi * (1 + C ** 2) / S ** 5 * c0 - 4 * C / S ** 4 * c0p + 4 / (pi * S ** 3) * c0pp)
           - 15 * A ** 4 - 90 * A ** 2 * R + 414 * A * U - 108 * A * V - 117 * R ** 2 - 75 * X)
    return tot / 46656


def gs_C5(d, P5, K, P4, L, Q, Z):
    A, R, U, V, X = basis(d / 4)
    return (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q ** 2 + 720 * A ** 2 * Q + 1008 * Q * R + 7152 * Z
            - 15 * A ** 4 - 90 * A ** 2 * R + 414 * A * U - 108 * A * V - 117 * R ** 2 - 75 * X) / 46656


# ---------------------------------------------------------------- gdk printed formulas
def gdk_s(q):
    A, R, U, V, X = basis(q)
    cs = mp.psi(0, 1) + mp.psi(0, 2 * q)
    x1, x2, x3, x4 = cs - 4 * mp.psi(0, q), -R, V - U, -X
    s0 = x1
    s1 = (x1 ** 2 + x2) / 2
    s2 = (x1 ** 3 + 3 * x1 * x2 + x3) / 6
    s3 = (x1 ** 4 + 6 * x1 ** 2 * x2 + 4 * x1 * x3 + 3 * x2 ** 2 + x4) / 24
    return [s0, s1, s2, s3]


def gdk_s_taylor(q):
    """independent: Taylor coefficients of tau*Gamma(2q)Gamma(tau)Gamma(q-tau/2)^4/(Gamma(2q-tau)Gamma(q+tau/2)^4)
    (gdk:Sclosed) at tau = 0, through tau^4 -> s_{-1..3}."""
    f = lambda t: mp.gamma(2 * q) * mp.gamma(1 + t) * mp.gamma(q - t / 2) ** 4 / (mp.gamma(2 * q - t) * mp.gamma(q + t / 2) ** 4)
    with mp.workdps(DPS + 30):
        c = mp.taylor(f, 0, 4)
    return [c[1], c[2], c[3], c[4]], c[0]


def gdk_K(q, r3):
    A, R, U, V, X = basis(q)
    s3 = gdk_s(q)[3]
    return U / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q)) + (r3 - s3) / 4


GDK_TABLE = {  # printed gdk:numerics values table (K_d position space, r3 by gdk:Kr3)
    '0.8': ('92.372770239922771632645391899036', '1894.360867513991151448939858'),
    '1': ('39.331569128259039057503187151598', '767.2452094446567860904798157'),
    '1.25': ('17.203345729921688327085720106549', '302.1379775430212297584696879'),
    '1.5': ('9.0182974015948205470847431046793', '136.5685443212260369206603723'),
    '2': ('3.5181091385902522416490901703077', '35.63714944308140680727039972'),
    '2.5': ('1.8405012954285880307301818602723', '11.46731776044183878576775169'),
    '2.75': ('1.4292491886603120000991755368839', '6.984719816576732523926795216'),
    '3': ('1.1485946495271793365566463108107', '4.511759358236005780256620898'),
}
GDK_SPECIAL_R3 = {'1': '767.24520944465678609047981573762', '2': '35.637149443081406807270399721681',
                  '3': '4.51175935823600578025662089796'}


def jet_laurent(dkey):
    """my own Cauchy extraction of the Laurent coefficients of <t^2 R_tau> from C63d's stored circle points."""
    fn = os.path.join(ROOT, 'K_general', 'R_part', 'prod', 'prod_B_d%s.json' % dkey)
    js = json.load(open(fn))
    N, r = int(js['N']), mp.mpf(js['r'])
    pts = js['points']
    f = {}
    for j in range(N // 2 + 1):
        p = pts[str(j)]
        f[j] = mp.mpc(p['Re_tR'], p['Im_tR'])
    for j in range(N // 2 + 1, N):
        f[j] = mp.conj(f[N - j])
    coef = {}
    for k in range(-1, 5):
        coef[k] = mp.re(mp.fsum(f[j] * mp.expjpi(-2 * mp.mpf(j) * k / N) for j in range(N)) / (N * r ** k))
    return coef, js


def rel(a, b):
    return abs(a - b) / abs(b)


def nd(a, b):
    """digits of agreement"""
    e = rel(a, b)
    return float('inf') if e == 0 else float(-mp.log10(e))


def main():
    samp = json.load(open(sys.argv[1]))['values']
    refs = json.load(open(os.path.join(ROOT, 'references', 'reference_values.json')))['values']
    notev, extras = note_values(DPS)
    mp.mp.dps = DPS
    report = {}
    for dstr, sv in samp.items():
        d = P(dstr)
        q = d / 4
        b = d / 2
        S, C = mp.sin(pi * q), mp.cos(pi * q)
        A, R, U, V, X = basis(q)
        g = {k: (mp.mpf(v) if isinstance(v, str) and k not in ('engine',) else v) for k, v in sv.items()}
        T3 = [mp.mpf(x) for x in sv['T3']]
        M3 = [mp.mpf(x) for x in sv['M3']]
        c0 = [mp.mpf(x) for x in sv['c0']]
        X0, Xh, XT = g['X0'], g['Xh'], g['XT']
        DL = gdr_DL(C, g['dX0'], g['dXh'], g['dXT'])
        P4 = gdr_P4(S, C, X0, Xh, XT)
        L = gdr_L(S, C, X0, Xh, XT, DL)
        Q3 = gdr_3Q(S, T3[0], c0[0])
        Q = Q3 / 3
        Z = gdr_Z(d, S, C, T3[2], Q, c0[0], c0[1], c0[2])
        # internal consistency of printed three-wheel formulas
        c0_chk = c0_from(b, T3[0], M3[0])
        W3_two = u_of(b) * T3[0] + v_of(b) * M3[0]
        # full jet 9Z = (u T3 + v M3)''
        u0, u1, u2 = u_of(b), mp.diff(u_of, b, 1), mp.diff(u_of, b, 2)
        v0, v1, v2 = v_of(b), mp.diff(v_of, b, 1), mp.diff(v_of, b, 2)
        Zjet = (u2 * T3[0] + 2 * u1 * T3[1] + u0 * T3[2] + v2 * M3[0] + 2 * v1 * M3[1] + v0 * M3[2]) / 9
        dW3 = u1 * T3[0] + u0 * T3[1] + v1 * M3[0] + v0 * M3[1]
        row = dict(P4=P4, L=L, Q=Q, Z=Z, DL=DL)
        chk = dict(c0_printed_vs_code=rel(c0_chk, c0[0]) if c0[0] != 0 else abs(c0_chk),
                   W3_twonode_vs_3Q=rel(W3_two, Q3), Zjet_vs_Zprinted=rel(Zjet, Z), dW3_at_centre=abs(dW3),
                   P4_vs_code=rel(P4, g['P4_code']), L_vs_code=rel(L, g['L_code']),
                   Q_vs_code=rel(Q, g['Q_code']), Z_vs_code=rel(Z, g['Z_code']))
        # gdk: s_k Bell form vs direct Taylor
        sB = gdk_s(q)
        sT, sm1 = gdk_s_taylor(q)
        chk['s_Bell_vs_Taylor'] = max(rel(sB[i], sT[i]) for i in range(4))
        chk['s_m1'] = abs(sm1 - 1)
        dkey = mp.nstr(d, 5).rstrip('0').rstrip('.') if dstr not in ('1', '2', '3') else dstr
        # K from printed table r3, from my jet extraction
        Ktab = gdk_K(q, mp.mpf(GDK_TABLE[dkey][1]))
        Kmb = mp.mpf(GDK_TABLE[dkey][0])
        lau, js = jet_laurent(dkey)
        Kjet = gdk_K(q, lau[3])
        chk['jet_r_m1_minus_1'] = abs(lau[-1] - 1)
        chk['jet_r0_minus_s0'] = abs(lau[0] - sB[0])
        chk['jet_r1_minus_s1'] = abs(lau[1] - sB[1])
        chk['jet_r2_minus_s2_minus_1.5U'] = abs(lau[2] - sB[2] - mp.mpf(3) / 2 * U)
        chk['jet_r3_vs_table_r3'] = rel(lau[3], mp.mpf(GDK_TABLE[dkey][1]))
        chk['Ktab_vs_Kmb_table'] = rel(Ktab, Kmb)
        chk['Kjet_vs_their_prodB_K'] = rel(Kjet, mp.mpf(js['K_d']))
        row.update(K_from_table_r3=Ktab, K_from_jet_r3=Kjet, r3_jet=lau[3], s3=sB[3])
        if dkey in GDK_SPECIAL_R3:
            chk['special_r3_vs_table_r3'] = rel(mp.mpf(GDK_SPECIAL_R3[dkey]), mp.mpf(GDK_TABLE[dkey][1]))
        if dstr in ('1', '2', '3'):
            nv = notev[dstr]
            # closed-form r3(1), r3(2) of gdk:special
            G, z3, l2, gE = mp.catalan, mp.zeta(3), mp.log(2), mp.euler
            if dstr == '1':
                r3c = sB[3] + 4 * nv['K'] - 2 * (pi ** 3 + 28 * z3) * (3 * gE + 7 * l2 + pi)
                chk['r3_closed_vs_printed_special'] = rel(r3c, mp.mpf(GDK_SPECIAL_R3['1']))
            if dstr == '2':
                r3c = sB[3] + 128 * G ** 2 - 168 * z3 * l2 - 42 * gE * z3
                chk['r3_closed_vs_printed_special'] = rel(r3c, mp.mpf(GDK_SPECIAL_R3['2']))
            if dstr == '3':
                r3c = sB[3] + 4 * nv['K'] - 4 * U / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q))
                chk['r3_from_K3_vs_printed_special'] = rel(r3c, mp.mpf(GDK_SPECIAL_R3['3']))
            Kspec = gdk_K(q, mp.mpf(GDK_SPECIAL_R3[dstr]))
            for nm in ('P4', 'L', 'Q', 'Z'):
                chk[nm + '_vs_note'] = rel(row[nm], nv[nm])
            chk['K_table_r3_vs_note'] = rel(Ktab, nv['K'])
            chk['K_special_r3_vs_note'] = rel(Kspec, nv['K'])
            chk['K_jet_r3_vs_note'] = rel(Kjet, nv['K'])
            P5 = nv['P5']
            C5_red_tab = gdr_C5reduced(d, P5, Ktab, X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
            C5_red_spec = gdr_C5reduced(d, P5, Kspec, X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
            C5_red_jet = gdr_C5reduced(d, P5, Kjet, X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
            C5_gs = gs_C5(d, P5, Ktab, P4, L, Q, Z)
            C5_allnote = gs_C5(d, P5, nv['K'], nv['P4'], nv['L'], nv['Q'], nv['Z'])
            row.update(C5_reduced_tableK=C5_red_tab, C5_reduced_specialK=C5_red_spec, C5_reduced_jetK=C5_red_jet,
                       C5_gsC5_printedmasters=C5_gs, C5_gs_note_masters=C5_allnote, C5_note=nv['C5_note'])
            chk['C5red_tableK_vs_note'] = rel(C5_red_tab, nv['C5_note'])
            chk['C5red_specialK_vs_note'] = rel(C5_red_spec, nv['C5_note'])
            chk['C5red_jetK_vs_note'] = rel(C5_red_jet, nv['C5_note'])
            chk['C5red_vs_gsC5_same_inputs'] = rel(C5_red_tab, C5_gs)
            chk['C5_note_masters_vs_note'] = rel(C5_allnote, nv['C5_note'])
            # high-precision P5 (d=1: fx:eq:Px evaluated here; d=3: LRI_C5_d3 period_values) with jet-K
            C5hp = gdr_C5reduced(d, nv['P5hp'], Kjet, X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
            row['C5_reduced_jetK_P5hp'] = C5hp
            chk['P5note_vs_P5hp'] = rel(nv['P5'], nv['P5hp'])
            chk['C5red_jetK_P5hp_vs_note'] = rel(C5hp, nv['C5_note'])
            if 'C5_d3json' in nv:
                chk['C5red_jetK_P5hp_vs_LRI_C5_d3_json'] = rel(C5hp, nv['C5_d3json'])
                C5hp_spec = gdr_C5reduced(d, nv['P5hp'], Kspec, X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
                chk['C5red_specialK_P5hp_vs_LRI_C5_d3_json'] = rel(C5hp_spec, nv['C5_d3json'])
                C5hp_K3 = gdr_C5reduced(d, nv['P5hp'], nv['K'], X0, Xh, XT, DL, T3[0], T3[2], c0[0], c0[1], c0[2])
                chk['C5red_K3json_P5hp_vs_LRI_C5_d3_json'] = rel(C5hp_K3, nv['C5_d3json'])
            if dstr == '2':
                chk['C5red_jetK_vs_C5_twoClosed'] = rel(C5hp, nv['C5_closed'])
            if dstr == '2':
                chk['C5_closed_twoClosed_vs_note'] = rel(nv['C5_closed'], nv['C5_note'])
                chk['C5red_tableK_vs_C5_twoClosed'] = rel(C5_red_tab, nv['C5_closed'])
                chk['C5red_specialK_vs_C5_twoClosed'] = rel(C5_red_spec, nv['C5_closed'])
        else:
            rf = refs['d=' + dkey]
            for nm, key, fac in (('P4', 'P4', 1), ('L', 'L', 1), ('Z', 'Z', 1), ('Q', 'threeQ', mp.mpf(1) / 3)):
                chk[nm + '_vs_ref'] = rel(row[nm], mp.mpf(rf[key]['value']) * fac)
            Kref = mp.mpf(rf['K']['value'])
            chk['K_table_r3_vs_ref'] = rel(Ktab, Kref)
            chk['K_jet_r3_vs_ref'] = rel(Kjet, Kref)
            chk['K_table_MB_vs_ref'] = rel(Kmb, Kref)
            row['Kref'] = Kref
        report[dstr] = dict(values={k: mp.nstr(v, 40) for k, v in row.items()},
                            checks={k: mp.nstr(v, 3) for k, v in chk.items()})
        print('==== d =', dstr, flush=True)
        for k, v in row.items():
            print('  %-26s %s' % (k, mp.nstr(v, 36)))
        for k, v in chk.items():
            print('  chk %-36s %s' % (k, mp.nstr(v, 3)))
    json.dump(report, open(os.path.join(HERE, 'e2e_report.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
