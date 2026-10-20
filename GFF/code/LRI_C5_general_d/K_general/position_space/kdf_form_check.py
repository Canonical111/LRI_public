"""Check the Kampe de Feriet (Pochhammer) form of the four Frobenius families F_ij of the general kite against
the residue (Gamma-product) form used in kite_general.family_sums, at |x| < 1."""
import mpmath as mp
from kite_general import family_sums
mp.mp.dps = 30
d, nu1, nu2, nu3, a3, a4 = [mp.mpf(s) for s in ('1.7', '0.395', '0.387', '0.380', '0.159', '0.620')]
x1, x2 = mp.mpf('0.6'), mp.mpf('0.35')
h = d / 2; lam = nu1 + nu2 + nu3 - h; cw = a3 + a4 - h; s1 = nu2 - lam; s2 = nu1 - lam
G = mp.gamma; rf = mp.rf
P0 = G(h) ** 2 / (G(nu1) * G(nu2) * G(nu3) * G(d - nu1 - nu2 - nu3))
def Fij(i, j, M=90):
    S1 = i * s1; S2 = j * s2; S = S1 + S2
    C = G(s1 if i == 0 else -s1) * G(s2 if j == 0 else -s2) * G(h - a3 + S1) * G(h - a4 + S2) * G(lam + S) * G(nu3 + S) * G(cw - S) \
        / (G(a3 - S1) * G(a4 - S2) * G(h - cw + S))
    l1 = 1 - s1 if i == 0 else 1 + s1
    l2 = 1 - s2 if j == 0 else 1 + s2
    tot = 0
    for m in range(M):
        for n in range(M):
            tot += rf(lam + S, m + n) * rf(nu3 + S, m + n) * rf(h - a3 + S1, m) * rf(1 - a3 + S1, m) * rf(h - a4 + S2, n) * rf(1 - a4 + S2, n) \
                / (rf(1 - cw + S, m + n) * rf(h - cw + S, m + n) * rf(l1, m) * rf(l2, n) * mp.factorial(m) * mp.factorial(n)) * x1 ** m * x2 ** n
    return P0 * C * tot * x1 ** S1 * x2 ** S2
fam = family_sums('1.7', '0.395', '0.387', '0.380', '0.159', '0.620', '0.6', '0.35', 90)
for (i, j) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
    v = Fij(i, j)
    print('F_%d%d  KdF form %s   residue form %s' % (i, j, mp.nstr(v, 18), mp.nstr(fam['%d%d' % (i, j)], 18)))
