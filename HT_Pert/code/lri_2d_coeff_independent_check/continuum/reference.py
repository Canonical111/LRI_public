#!/usr/bin/env python3
"""Continuum (diagrammatic) d = 2 coefficients C_n(2) of Delta_E = sum C_n(2) eps^n, eps = 2s - d.

Sources (all in <PROJECT>/GFF/LRI_condensed_note/long_range_ising_condensed.tex):
  * conventions eq. (cn:expansion), lines 77-83: eps = 2s - d, Delta_phi = (d - eps)/4, C_0(d) = d/2, C_1 = -1/6;
  * C_2(2) = 4 log2 / 9, C_3(2) = 4 log^2 2 / 27 - Gamma(1/4)^8 / (324 pi^4),
    648 C_4(2) = 16 P_4(2) - 64 log^3 2 - 32 log2 Q_2 - 359 zeta(3)      eq. (gc:d2coefficients), lines 3463-3474;
    Q_2 = Gamma(1/4)^8 / (24 pi^4) eq. (gc:Q2); P_4(2) to 50 digits, lines 3549-3553;
  * C_5(2) = -38.8336458962253605529369824675329232 (closed form gc:C5twoClosed; 35 digits, line 6572);
  * C_6(2), C_7(2), C_8(2): Monte Carlo estimators and sampling SE, table lines 106-122; quoted allowances
    (4 SE, rounded up) in the coefficient table lines 95-101.
The general-d forms C_2(d) = A_d/9, C_3(d) = (A_d^2 + R_d - 8 Q_d)/108 (eq. gd:C03, lines 2269-2274) reduce to the
d = 2 values with A_2 = 4 log 2, R_2 = 0; both are recomputed here as a check.
"""
import csv
import os

from mpmath import mp, mpf, log, gamma, pi, zeta, psi

mp.dps = 50
HERE = os.path.dirname(os.path.abspath(__file__))

a = log(2)
Q2 = gamma(mpf(1) / 4) ** 8 / (24 * pi ** 4)
P4_2 = mpf("250.48731558186728553185175688791140716835571092358")


def references():
    q = mpf(1) / 2  # q = d/4 at d = 2
    A2 = psi(0, 2 * q) + psi(0, 1) - 2 * psi(0, q)
    R2 = psi(1, 2 * q) - psi(1, 1)
    C2 = 4 * a / 9
    C3 = 4 * a ** 2 / 27 - gamma(mpf(1) / 4) ** 8 / (324 * pi ** 4)
    assert abs(C2 - A2 / 9) < mpf(10) ** -45
    assert abs(C3 - (A2 ** 2 + R2 - 8 * Q2) / 108) < mpf(10) ** -45
    C4 = (16 * P4_2 - 64 * a ** 3 - 32 * a * Q2 - 359 * zeta(3)) / 648
    C5 = mpf("-38.8336458962253605529369824675329232")
    rows = [
        (0, mpf(1), 0, 0, "exact", "C_0(d) = d/2"),
        (1, mpf(-1) / 6, 0, 0, "exact", "C_1 = -1/6"),
        (2, C2, 0, 0, "exact", "4 log2/9 (gd:C03, gc:d2coefficients)"),
        (3, C3, 0, 0, "exact", "4 log^2 2/27 - Gamma(1/4)^8/(324 pi^4) (gc:d2coefficients)"),
        (4, C4, 0, 0, "exact", "(16 P4(2) - 64 log^3 2 - 32 log2 Q2 - 359 zeta3)/648 (gc:d2coefficients)"),
        (5, C5, 0, 0, "exact", "closed form gc:C5twoClosed, 35 digits"),
        (6, mpf("362.36647176375726"), mpf("0.0007997307"), mpf("0.004"), "MC", "SE 8.0e-4; quoted +-0.004 (4 SE)"),
        (7, mpf("-3876.1260927949925"), mpf("0.5244496691"), mpf("2.1"), "MC", "SE 0.524; quoted +-2.1 (4 SE)"),
        (8, mpf("45990.00263614446"), mpf("8.216820958"), mpf("33"), "MC", "SE 8.2; quoted +-33 (4 SE)"),
    ]
    return rows


def load():
    """Return {n: (value, SE)} as floats, for use by the fit scripts."""
    return {n: (float(v), float(se)) for n, v, se, _, _, _ in references()}


def main():
    out = os.path.join(HERE, "reference_values.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "C_n(2)", "sampling_SE", "quoted_allowance", "status", "source"])
        for n, v, se, al, st, src in references():
            w.writerow([n, mp.nstr(v, 30), mp.nstr(se, 6), mp.nstr(al, 3), st, src])
            print(f"C_{n}(2) = {mp.nstr(v, 25):>32}  SE {mp.nstr(se, 4):>10}  {st}")
    print("wrote", out)


if __name__ == "__main__":
    main()
