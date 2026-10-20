"""K-path J_t as two confluent (psi-weighted) double series, symmetric-star orientation; check at |x|<1 against the MB.
   J_t(x) = N [ sum_{m,n} T_I + sum_{k,n} T_II ],  convergent at x = (1,1) for d < 2 + 2t."""
import mpmath as mp
from flint import acb, arb, acb_poly, ctx
mp.mp.dps = 30
def mb_kpath(d, t, x1, x2, c1, c2, digits=22):
    ctx.prec = int(digits * 3.33) + 80
    q = arb(d) / 4; t = arb(t); lx1 = arb(x1).log(); lx2 = arb(x2).log()
    cf1, cf2, qf, tf = float(c1), float(c2), float(d) / 4, float(t)
    delta = min(abs(cf1), abs(cf1 + tf / 2), abs(cf2), abs(cf2 + qf), abs(cf1 + cf2 + qf), abs(qf - tf / 2 - cf1 - cf2))
    L = digits * 2.302585 + 25; hs = 2 * 3.14159265 * delta / L; Y = (L + 10) / 6.2832 + 4; N = int(Y / hs) + 1
    hh = arb(hs); c1 = arb(c1); c2 = arb(c2)
    F1 = []; F2 = []
    for j in range(-N, N + 1):
        z1 = acb(c1, hh * j); z2 = acb(c2, hh * j)
        F1.append((2 * (-z1).lgamma() + (t / 2 + z1).lgamma() - (2 * q - t / 2 - z1).lgamma() + z1 * lx1).exp())
        F2.append((2 * (-z2).lgamma() + (q + z2).lgamma() - (q - z2).lgamma() + z2 * lx2).exp())
    Gw = []
    for s in range(-2 * N, 2 * N + 1):
        w = acb(c1 + c2, hh * s)
        Gw.append((2 * (q + w).lgamma() + (q - t / 2 - w).lgamma() - (q + t / 2 + w).lgamma()).exp())
    PQ = acb_poly([F2[2 * N - k] for k in range(2 * N + 1)]) * acb_poly(Gw)
    S = acb(0)
    for i in range(-N, N + 1):
        S += F1[i + N] * PQ[3 * N + i]
    Nn = ((2 * q).lgamma() * 2 - q.lgamma() * 4).exp()
    v = Nn * S * hh * hh / (4 * arb.pi() ** 2)
    return mp.mpf(v.real.mid().str(25, radius=False))

def series_kpath(d, t, x1, x2, M):
    d = mp.mpf(d); t = mp.mpf(t); q = d / 4; x1 = mp.mpf(x1); x2 = mp.mpf(x2); l1x, l2x = mp.log(x1), mp.log(x2)
    G = mp.gamma; ps = mp.digamma; p1 = lambda z: mp.polygamma(1, z)
    N = G(2 * q) ** 2 / G(q) ** 4
    SI = 0
    for m in range(M):
        for n in range(M):
            w = m + n
            f = G(q + w) ** 2 * G(q + n) / G(q - n) * G(t / 2 + m) * G(q - t / 2 - w) / (G(2 * q - t / 2 - m) * G(q + t / 2 + w))
            L1 = 2 * ps(q + w) + ps(t / 2 + m) - ps(q - t / 2 - w) + ps(2 * q - t / 2 - m) - ps(q + t / 2 + w) + l1x
            L2 = 2 * ps(q + w) + ps(q + n) + ps(q - n) - ps(q - t / 2 - w) - ps(q + t / 2 + w) + l2x
            L12 = 2 * p1(q + w) + p1(q - t / 2 - w) - p1(q + t / 2 + w)
            SI += f * x1 ** m * x2 ** n / (mp.factorial(m) ** 2 * mp.factorial(n) ** 2) * ((L1 - 2 * ps(m + 1)) * (L2 - 2 * ps(n + 1)) + L12)
    SII = 0
    for k in range(M):
        for n in range(M):
            z2 = n; w = q - t / 2 + k; z1 = w - z2
            hval = G(-z1) ** 2 * G(q + w) ** 2 * G(q + z2) / G(q - z2) * G(t / 2 + z1) / (G(2 * q - t / 2 - z1) * G(q + t / 2 + w)) * x1 ** z1 * x2 ** z2
            dlog = 2 * ps(-z1) + ps(q + z2) + ps(q - z2) - ps(t / 2 + z1) - ps(2 * q - t / 2 - z1) - l1x + l2x
            SII += (-1) ** (k + 1) / (mp.factorial(k) * mp.factorial(n) ** 2) * hval * (dlog - 2 * ps(n + 1))
    return N * SI, N * SII

if __name__ == '__main__':
    for (d, t) in [('1.5', '0.3'), ('1', '0.4')]:
        for (x1, x2) in [('0.6', '0.35')]:
            q = float(d) / 4; tf = float(t)
            c1 = repr(-tf / 4); c2 = repr(-q / 3)
            mbv = mb_kpath(d, t, x1, x2, c1, c2)
            for M in (60, 80):
                SI, SII = series_kpath(d, t, x1, x2, M)
                print('d=%s t=%s x=(%s,%s) M=%d: series = %s  [I=%s, II=%s]   MB = %s' % (d, t, x1, x2, M, mp.nstr(SI + SII, 20), mp.nstr(SI, 10), mp.nstr(SII, 10), mp.nstr(mbv, 20)), flush=True)
