"""Shared helpers of the c2_closed_d2 test and replay (new tool, 2026-10-15; mpmath and the standard library only).

closed_form(dps)  the closed form of c_2 in d = 2 exactly as printed in the closed-forms appendix (subsection
                  "Crossover in two dimensions"): R_Gamma = Gamma(1/4)/Gamma(3/4), the three 4F3(1) values P, Q, T with
                  the printed parameters, and c_2; plus the derived constants of the study (SRI note, Sec. 3.5 and App. E; b_0 = 9 pi^2/(8
                  R_Gamma^2), the elliptic finite part I, B_31, z_41, J(0), Omega_4(0) = 2 pi J(0) and the two
                  contributions to c_2), all at `dps` working digits.
nsum_4f3(...)     an independent summation of a 4F3(1) series (mpmath nsum on the explicit terms).
mc_load(), mc_est(), mc_combine(), mc_to_c2()
                  the end-to-end Monte Carlo of the review (2026-10-08): per-chunk batch records of mc/run_{A,B,C},
                  the batch-means estimator of mc/summ.py, the inverse-variance combination of the three
                  configurations and the map Omega_4(0) -> J(0) -> z_41 -> c_2.
"""
from fractions import Fraction as Fr
import math
from pathlib import Path

import mpmath as mp

# Parameters of P, Q, T as printed in the appendix (eq. cf:cr-PQT): (numerator parameters, denominator parameters).
PQT_PARAMS = {
    'P': ((Fr(-1, 2), Fr(-1, 2), Fr(3, 2), Fr(3, 4)), (Fr(1), Fr(2), Fr(1, 4))),
    'Q': ((Fr(1, 2), Fr(3, 2), Fr(3, 2), Fr(9, 4)), (Fr(3), Fr(3), Fr(7, 4))),
    'T': ((Fr(3, 2), Fr(-1, 4), Fr(3, 4), Fr(3, 4)), (Fr(1, 4), Fr(9, 4), Fr(9, 4))),
}


def _mpf(fr):
    return mp.mpf(fr.numerator)/fr.denominator


def closed_form(dps=50):
    """c_2 and the constants around it at `dps` working digits (mpmath values)."""
    with mp.workdps(dps):
        R = mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4)
        v = {k: mp.hyper([_mpf(x) for x in a], [_mpf(x) for x in b], 1) for k, (a, b) in PQT_PARAMS.items()}
        P, Q, T = v['P'], v['Q'], v['T']
        # eq. cf:cr-c2, coefficient by coefficient as printed
        c2 = (16/R**2 - R**2/9
              - mp.pi**2*R**2/16*(P - 5*R**2/384*Q)*(P - 5*R**2/128*Q - 512/(25*mp.pi*R**2)*T))
        b0 = 9*mp.pi**2/(8*R**2)
        I = -4*b0**2*c2/mp.pi - mp.pi*b0                       # c_2 = -pi I/(4 b0^2) - pi^2/(4 b0)
        B31 = mp.pi**2/96*(12 - mp.pi*mp.sqrt(3) - 9*mp.log(3))
        z41 = (mp.pi*I + mp.pi**2*b0)/16                       # = -c_2 b0^2/4
        J0 = I - 16*b0*B31/mp.pi + mp.pi*b0
        return dict(R=R, P=P, Q=Q, T=T, C2=c2, C2_s=c2/4, b0=b0, I=I, B31=B31, z41=z41, J0=J0,
                    Omega4=2*mp.pi*J0, period=-mp.pi*I/(4*b0**2), contact=-mp.pi**2/(4*b0))


def nsum_4f3(a, b, dps=50):
    """sum_n prod (a_i)_n / prod (b_j)_n / n! by mpmath nsum (Richardson extrapolation on the explicit terms)."""
    with mp.workdps(dps + 10):
        A = [_mpf(x) for x in a]
        B = [_mpf(x) for x in b] + [mp.mpf(1)]
        def term(n):
            return mp.rf(A[0], n)*mp.rf(A[1], n)*mp.rf(A[2], n)*mp.rf(A[3], n)/(
                mp.rf(B[0], n)*mp.rf(B[1], n)*mp.rf(B[2], n)*mp.rf(B[3], n))
        return mp.nsum(term, [0, mp.inf], method='richardson')


def source_constant(power, dps=30):
    """B_{3,1} of the source e^{-|w|^p} (p = 2 Gaussian, p = 4 quartic): A(0) = pi^2/8 - (pi/p) FP int F_0(z)
    log(3|z|^p + 1) d^2z, the finite part by the study's radial identity (SRI note, App. E). p = 2 gives the
    closed form B_31 = pi^2 (12 - pi sqrt 3 - 9 log 3)/96."""
    with mp.workdps(dps):
        h = lambda r: mp.log(3*r**power + 1)
        k = lambda r: abs(r - 1)/(1 + r)**3*h(r)
        fp = mp.pi/2*(mp.quad(k, [0, 1]) + mp.quad(k, [1, mp.inf])) - mp.pi/4*h(1)
        return mp.pi**2/8 - mp.pi/power*fp


def source_shape_prediction(dps=30):
    """Omega_4(quartic) - Omega_4(Gaussian) = 32 b0 (B_Gauss - B_quartic): z_41 = Omega_4/32 + b0 B is source
    independent (the review's predicted 16.150)."""
    with mp.workdps(dps):
        b0 = closed_form(dps)['b0']
        return 32*b0*(source_constant(2, dps) - source_constant(4, dps))


def i2_zero(dps=50):
    """First-order energy integral at delta = 0 by the study's radial finite-part identity (SRI note, App. E; h = 1):
    I_2(0) = (pi/2) int_0^inf |r-1|/(1+r)^3 dr - pi/4 (vanishes: c_1 = 0 in d = 2)."""
    with mp.workdps(dps):
        return mp.pi/2*(mp.quad(lambda r: (1 - r)/(1 + r)**3, [0, 1]) + mp.quad(lambda r: (r - 1)/(1 + r)**3, [1, mp.inf])) - mp.pi/4


# ---------------------------------------------------------------------------------------------------------------
# Monte Carlo (mc/): histogram layout of c2mc3.c / summ.py
NBIN, BLO, BW = 120, -58.0, 0.5
RUNS = ('A', 'B', 'C')
CUT = -15.0     # Lambda cut of the quoted value (see mc_cut_rule)


def mc_cut_rule():
    return ('Lambda > -15: the deepest cut of summ.py\'s grid at which both slicings are complete. Samples are drawn '
            'with Lambda > LMIN = -16; on S^7 the quartic-source slice variable Lambda_S = Lambda - log(sum|w|^4)/2 '
            'is at most Lambda + log(4)/2, so Lambda_S > c needs Lambda > c - 0.69, inside the sampled region only '
            'for c >= -15.31 (at -16 the quartic slice equals the Gaussian one by construction)')


def mc_files(mc_dir, run):
    """Chunk outputs of one configuration, in summ.py argument order (sorted file names)."""
    return sorted(Path(mc_dir, 'run_' + run).glob('out_*.txt'), key=lambda p: p.name)


def mc_load(files):
    """Per-batch records of the chunk outputs: headers, B (Gaussian slice), BS (quartic slice), BD (finite delta)."""
    heads, H, HS, BD = [], [], [], []
    for f in files:
        for line in open(f):
            t = line.split()
            if not t:
                continue
            if t[0] == 'eta':
                heads.append(dict(zip(t[0::2], t[1::2])))
            elif t[0] == 'B':
                H.append((int(t[2]), [float(x) for x in t[3:]]))
            elif t[0] == 'BS':
                HS.append((int(t[2]), [float(x) for x in t[3:]]))
            elif t[0] == 'BD':
                BD.append((int(t[2]), [float(x) for x in t[3:]]))
    return heads, H, HS, BD


def mc_est(batches, cut):
    """Batch-means estimate of summ.py: the integral over bins with Lambda above `cut`, weighted by batch size."""
    ci = int(round((cut - BLO)/BW))
    vals = [math.fsum(h[ci:])/nb for nb, h in batches]
    ws = [float(nb) for nb, _ in batches]
    W = math.fsum(ws)
    m = math.fsum(v*w for v, w in zip(vals, ws))/W
    se = math.sqrt(math.fsum((v - m)**2*w for v, w in zip(vals, ws))/W/(len(vals) - 1))
    return m, se


def mc_diff(H, HS):
    return [(nb, [y - x for x, y in zip(h, hs)]) for (nb, h), (_, hs) in zip(H, HS)]


def mc_combine(est):
    """Inverse-variance mean of [(value, se), ...], its se and chi^2."""
    w = [1/s**2 for _, s in est]
    m = math.fsum(wi*x for wi, (x, _) in zip(w, est))/math.fsum(w)
    return m, 1/math.sqrt(math.fsum(w)), math.fsum(wi*(x - m)**2 for wi, (x, _) in zip(w, est))


def mc_to_c2(omega, se, b0, B31):
    """Omega_4(0) -> J(0) = Omega_4/(2 pi) -> z_41 = pi J/16 + b0 B31 -> c_2 = -4 z_41/b0^2 (SRI note, Sec. 3.4 and
    App. E, Gaussian source)."""
    J = omega/(2*math.pi)
    z41 = math.pi*J/16 + b0*B31
    return dict(J=J, J_se=se/(2*math.pi), z41=z41, z41_se=se/32, C2=-4*z41/b0**2, C2_se=se/(8*b0**2))
