#!/usr/bin/env python3
"""Closed-form / note values of the masters at d = 1, 2, 3 (from the note; P5(2) evaluated from fp:P5two)."""
import mpmath as mp


def note_values(dps):
    mp.mp.dps = dps
    pi, G, z3, l2 = mp.pi, mp.catalan, mp.zeta(3), mp.log(2)
    g4 = mp.gamma(mp.mpf(1) / 4) ** 4
    with mp.workdps(dps + 20):
        Fm = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
        Fp = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
        Y = {}
        for r in (1, 2, 3, 5, 7):
            a = mp.mpf(r) / 8
            Y[r] = a * (mp.gamma((r + 2) / mp.mpf(8)) / mp.gamma((r + 6) / mp.mpf(8))) ** 7 * \
                mp.hyper([1, 1 + a] + [(r + 2) / mp.mpf(8)] * 7, [a] + [(r + 6) / mp.mpf(8)] * 7, -1)
    Bm, Bp = g4 * Fm, 64 * pi ** 4 / g4 * Fp
    c8, s8 = mp.cos(pi / 8), mp.sin(pi / 8)
    X0, Xp, Xm = Y[2], c8 ** 7 * Y[3] - s8 ** 7 * Y[5], c8 ** 7 * Y[1] + s8 ** 7 * Y[7]
    P5_2 = 8 / pi * (25 * X0 ** 2 - 28 * mp.sqrt(2) * X0 * (Xp + Xm) + 18 * (Xp ** 2 + Xm ** 2) + 28 * Xp * Xm)
    P5_1 = 16 * pi ** 1.5 * (-35 * X0 + (22 * mp.sqrt(2) - 13) * Xp + (22 * mp.sqrt(2) + 13) * Xm)  # fx:eq:Px
    P5_3hp = mp.mpf('240.340317759083549816366546388003598256150259720636562598771853625')  # LRI_C5_d3/inputs/general_d3/period_values.json
    out = {}
    # d = 1 (note: eq:KLpsiReflected, eq:KprovedFinal, gs:d1Dictionary; P5 l.1850, 30 digits)
    A1 = pi + 4 * l2
    P4_1 = 13 * Bm - 3 * Bp
    Q1 = g4 / pi
    out['1'] = dict(P4=P4_1, Q=Q1, L=-(3 * A1 - pi) / 6 * P4_1 - 2 * pi / 3 * Bm,
                    Z=Q1 * (2 * pi ** 2 / 3 + 8 * G),
                    K=128 * G ** 2 + 24 * pi ** 2 * G - 4 * pi ** 3 * l2 - 28 * (pi + 4 * l2) * z3,
                    P5=mp.mpf('28599.2931765621035366464770214'), P5_digits=30, P5hp=P5_1,
                    C5_note=mp.mpf('-731.139476624539825853869126582527'))
    # d = 2 (gc:Q2, fp:P4two, gc:L2closed, gs:Z2exact, gc:K2closed, fp:P5two)
    Q2 = g4 ** 2 / (24 * pi ** 4)
    P4_2 = (Bm ** 2 - Bp ** 2) / (4 * pi ** 3)
    out['2'] = dict(P4=P4_2, Q=Q2, L=-2 * l2 * P4_2, Z=4 * G * Q2, K=32 * G ** 2 - 28 * z3 * l2, P5=P5_2, P5hp=P5_2,
                    P5_digits=dps, C5_note=mp.mpf('-38.83364589622536055293698'),
                    C5_closed=(-32 * P5_2 + 56 * l2 * P4_2 - 36 * Q2 ** 2 + (240 * l2 ** 2 + 596 * G) * Q2
                               - 1024 * G ** 2 + 449 * z3 * l2 - 80 * l2 ** 4) / 972)
    # d = 3 (note td values l.5655; L3, Z3, K3 from LRI_C5_d3/masters_d3.json, 43 digits)
    out['3'] = dict(P4=mp.mpf('62.0583279434066724664633885840967'), Q=mp.mpf('5.01710256455385536959085484569018'),
                    L=mp.mpf('-62.710584968387669347296173433534847460001469735251813569'),
                    Z=mp.mpf('8.8209248930600924855368673281740808743649007375934264501'),
                    K=mp.mpf('1.1485946495271793365566463108106731876338481012649133718'),
                    P5=mp.mpf('240.340317759083549816366546388004'), P5_digits=33, P5hp=P5_3hp,
                    C5_d3json=mp.mpf('-5.85035142075132722921794423049774430011099734637831397869501'),
                    C5_note=mp.mpf('-5.8503514207513272292179'))
    extras = dict(Bm=Bm, Bp=Bp, Y=Y, P5_2=P5_2)
    return out, extras


if __name__ == '__main__':
    import time
    t = time.time()
    o, e = note_values(50)
    print(time.time() - t)
    for k, v in o.items():
        print(k, {a: mp.nstr(b, 30) for a, b in v.items() if not isinstance(b, int)})
