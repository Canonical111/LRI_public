#!/usr/bin/env python3
"""Double-precision evaluation of K_d from the position-space 2-fold MB representation (symmetric-star form).
   J_t = N int int Phi_t,  N = G(2q)^2/G(q)^4,
   Phi_t = G(-z1)^2 G(-z2)^2 G(q+w)^2 G(q+z2)/G(q-z2) * G(t/2+z1) G(q-t/2-w)/(G(2q-t/2-z1) G(q+t/2+w)),  w = z1+z2.
   Pole split: moving Re z1 left of -t/2 picks Res_{z1=-t/2} -> Barnes' first lemma:
   J_pole(t) = G(2q) G(t/2)^2 G(q-t/2)^4 / (G(q)^4 G(2q-t));  J_reg(t) = N int int_{C'} Phi_t is analytic at t=0.
   K_d = [t^2](J_pole - J^Gamma) + [t^2] J_reg ,  [t^k]J_reg = N int int_{C'} Phi_0 * [t^k] exp(L(t)-L(0))."""
import numpy as np
from scipy.special import loggamma as lg, psi as digamma
import mpmath as mp

def trigamma(z):
    z = np.asarray(z, dtype=complex)
    acc = np.zeros_like(z)
    for k in range(12):
        acc += 1.0 / (z + k) ** 2
    x = z + 12
    x2 = 1.0 / (x * x)
    ser = 1.0 / x + 0.5 * x2 + (1.0 / x) * x2 * (1.0/6 - x2 * (1.0/30 - x2 * (1.0/42 - x2 * (1.0/30 - x2 * 5.0/66))))
    return acc + ser

def reg_coeffs(d, c1, c2, h, Y):
    """returns ([t^0],[t^1],[t^2]) of J_reg"""
    q = d / 4.0
    y = np.arange(-Y, Y + h / 2, h)
    out = np.zeros(3, dtype=complex)
    for chunk in np.array_split(y, max(1, len(y) // 200)):
        Y1, Y2 = np.meshgrid(chunk, y, indexing='ij')
        z1 = c1 + 1j * Y1; z2 = c2 + 1j * Y2; w = z1 + z2
        L0 = (2 * lg(-z1) + 2 * lg(-z2) + 2 * lg(q + w) + lg(q + z2) - lg(q - z2)
              + lg(z1) + lg(q - w) - lg(2 * q - z1) - lg(q + w))
        P = np.exp(L0)
        l1 = 0.5 * (digamma(z1) - digamma(q - w) + digamma(2 * q - z1) - digamma(q + w))
        l2 = 0.25 * (trigamma(z1) + trigamma(q - w) - trigamma(2 * q - z1) - trigamma(q + w))
        out[0] += P.sum(); out[1] += (P * l1).sum(); out[2] += (P * (l1 * l1 + l2) / 2).sum()
    N = np.exp(2 * lg(2 * q) - 4 * lg(q)).real
    return N * out * h * h / (4 * np.pi ** 2)

def gamma_coeffs(d, dps=40):
    """Laurent coefficients [t^-2..t^2] of J_pole(t) - J^Gamma(t), by Cauchy integral at high precision."""
    mp.mp.dps = dps
    d = mp.mpf(d); q = d / 4; hh = d / 2
    G = mp.gamma
    def Bd(a, b):
        return G(hh) * G((d - a) / 2) * G((d - b) / 2) * G((a + b - d) / 2) / (G(a / 2) * G(b / 2) * G((2 * d - a - b) / 2))
    def f(t):
        Jp = G(2 * q) * G(t / 2) ** 2 * G(q - t / 2) ** 4 / (G(q) ** 4 * G(2 * q - t))
        JG = Bd(hh, d - t) ** 2 + 2 / t * (Bd(hh, d - t) - Bd(hh + 2 * t, d - t))
        return Jp - JG, Jp, JG
    M = 64; r = mp.mpf('0.05')
    res = {}
    for k in range(-2, 3):
        res[k] = [mp.mpf(0)] * 3
    for j in range(M):
        tt = r * mp.expj(2 * mp.pi * j / M)
        vals = f(tt)
        for k in range(-2, 3):
            for i in range(3):
                res[k][i] += vals[i] * tt ** (-k) / M
    return {k: [mp.re(x) for x in v] for k, v in res.items()}

if __name__ == '__main__':
    import sys, time
    d = float(sys.argv[1]); c1 = float(sys.argv[2]); c2 = float(sys.argv[3]); h = float(sys.argv[4]); Y = float(sys.argv[5])
    st = time.time()
    rc = reg_coeffs(d, c1, c2, h, Y)
    gc = gamma_coeffs(d)
    print('d=%g  J_reg coeffs t^0,t^1,t^2:' % d, [complex(x) for x in rc], ' (%.1f s)' % (time.time() - st))
    print('Gamma part (Jpole-JGamma) t^-2..t^2:', [mp.nstr(gc[k][0], 16) for k in range(-2, 3)])
    print('check t^0:', rc[0].real + float(gc[0][0]), '  t^1:', rc[1].real + float(gc[1][0]))
    print('K_d(MB) =', repr(rc[2].real + float(gc[2][0])))
