#!/usr/bin/env python3
"""Evaluate the d = 2 closed forms of the note (Sections 1.1, 17.2) with mpmath, at any precision (added for the release).

  L2 = -2 log2 P4(2) = -(A/2) P4(2) = -log2 (B-^2 - B+^2)/(2 pi^3)                    (gc:L2closed)
  K2 = 32 G^2 - 28 zeta(3) log2 = (1/2)[(psi1(1/4) - psi1(3/4))^2/4 + A U]          (gc:K2closed)
  972 C5(2) = -32 P5(2) + 56 log2 P4(2) - 36 Q2^2 + (240 log^2 2 + 596 G) Q2
              - 1024 G^2 + 449 zeta(3) log2 - 80 log^4 2                              (gc:C5twoClosed)
  46656 C5(2) = -1536 (P5(2) + K2) + 1536 a P4(2) - 576 L2 - 1728 Q2^2 + (11520 a^2 + 28608 G) Q2
              - 3840 a^4 - 21456 a zeta(3)                                            (gc:d2coefficients, a = log 2)

The inputs P4(2) = (B-^2 - B+^2)/(4 pi^3) (fp:P4two) and P5(2) (fp:P5two) are the one-dimensional values:
- B- = Gamma(1/4)^4 F-; B+ = 64 pi^4 F+ / Gamma(1/4)^4;
- F- = 4F3(1/4,1/4,1/2,1/2; 3/4,3/4,1; 1); F+ = 4F3(3/4,3/4,1/2,1/2; 5/4,5/4,1; 1);
- the five 9F8(-1) values Y_r.

mpmath's hyper() sums these series at |z| = 1 with convergence acceleration. Checked: at 60 and 80 digits P4(2) agrees
with the elliptic-integral evaluation (AGM quadrature, L2_singlesums/check_vs_C62d_dps70.json) and with the stored 70-digit
Euler-Maclaurin values of B+-. C5(2) agrees with the Mathematica evaluation in drafter/check_series.out.
Q2, P4(2), P5(2), C3(2) and C4(2) are computed here only as inputs and cross-checks; their expected values are owned
by GFF/results/closed_forms_general/C0_C5.

Usage: python3 public/closed_forms_d2.py [--dps 80] [--write ../../results/closed_forms_2/closed_forms_2.json]
"""
import argparse, json, sys
import mpmath as mp


def evaluate(dps=80):
    with mp.workdps(dps + 10):
        q = mp.mpf(1) / 4; pi = mp.pi; a = mp.log(2); G = mp.catalan; z3 = mp.zeta(3)
        g4 = mp.gamma(q) ** 4
        Fm = mp.hyper([q, q, 0.5, 0.5], [3 * q, 3 * q, 1], 1)
        Fp = mp.hyper([3 * q, 3 * q, 0.5, 0.5], [5 * q, 5 * q, 1], 1)
        Bm, Bp = g4 * Fm, 64 * pi ** 4 / g4 * Fp

        def Y(r):
            r = mp.mpf(r)
            return r / 8 * (mp.gamma((r + 2) / 8) / mp.gamma((r + 6) / 8)) ** 7 * mp.hyper(
                [1, 1 + r / 8] + [(r + 2) / 8] * 7, [r / 8] + [(r + 6) / 8] * 7, -1)
        c8, s8 = mp.cos(pi / 8), mp.sin(pi / 8)
        X0 = Y(2); Xp = c8 ** 7 * Y(3) - s8 ** 7 * Y(5); Xm = c8 ** 7 * Y(1) + s8 ** 7 * Y(7)
        Q2 = g4 ** 2 / (24 * pi ** 4)
        P4 = (Bm ** 2 - Bp ** 2) / (4 * pi ** 3)
        P5 = 8 / pi * (25 * X0 ** 2 - 28 * mp.sqrt(2) * X0 * (Xp + Xm) + 18 * (Xp ** 2 + Xm ** 2) + 28 * Xp * Xm)
        A = 4 * a; U = mp.psi(2, mp.mpf(1) / 2)
        v = dict(log2=a, Catalan=G, zeta3=z3, Fm=Fm, Fp=Fp, Bm=Bm, Bp=Bp, X0=X0, Xp=Xp, Xm=Xm, Q2=Q2, P4_2=P4, P5_2=P5,
                 Z2=4 * G * Q2, A=A, U=U)
        v['L2'] = -2 * a * P4
        v['L2_form_A'] = -(A / 2) * P4
        v['L2_form_B'] = -a * (Bm ** 2 - Bp ** 2) / (2 * pi ** 3)
        v['K2'] = 32 * G ** 2 - 28 * z3 * a
        v['K2_form_psi'] = ((mp.psi(1, q) - mp.psi(1, 3 * q)) ** 2 / 4 + A * U) / 2
        v['C5_2'] = (-32 * P5 + 56 * a * P4 - 36 * Q2 ** 2 + (240 * a ** 2 + 596 * G) * Q2 - 1024 * G ** 2
                     + 449 * z3 * a - 80 * a ** 4) / 972
        v['C5_2_from_gc_d2coefficients'] = (-1536 * (P5 + v['K2']) + 1536 * a * P4 - 576 * v['L2'] - 1728 * Q2 ** 2
                                            + (11520 * a ** 2 + 28608 * G) * Q2 - 3840 * a ** 4 - 21456 * a * z3) / 46656
        v['C2_2'] = 4 * a / 9
        v['C3_2'] = 4 * a ** 2 / 27 - g4 ** 2 / (324 * pi ** 4)
        v['C4_2'] = (16 * P4 - 64 * a ** 3 - 32 * a * Q2 - 359 * z3) / 648
        return {k: +x for k, x in v.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dps', type=int, default=80)
    ap.add_argument('--write', help='write the owned 70-digit values (L2, K2, C5_2) into this results JSON (keeps other keys)')
    a = ap.parse_args()
    v = evaluate(a.dps)
    mp.mp.dps = a.dps
    for k, x in v.items():
        print(f'{k:28s} {mp.nstr(x, min(a.dps - 5, 60))}')
    if a.write:
        try:
            d = json.load(open(a.write))
        except FileNotFoundError:
            d = {}
        d['values_70_digits'] = {k: mp.nstr(v[k], 70) for k in ('L2', 'K2', 'C5_2')}
        d['values_generated_by'] = f'public/closed_forms_d2.py --dps {a.dps} (mpmath {mp.__version__}, Python {sys.version.split()[0]})'
        json.dump(d, open(a.write, 'w'), indent=1)
        open(a.write, 'a').write('\n')


if __name__ == '__main__':
    main()
