"""Reference L_1 from the proved closed form eq:KLpsiReflected of the condensed note:
   L = -((3A - D)/6) P4 - (2D/3) B_-,  A = psi(1/2) + psi(1) - 2 psi(1/4), D = pi,
   B_- = Gamma(1/4)^4 F_-,  F_- = 4F3(1/4,1/4,1/2,1/2; 3/4,3/4,1; 1),  B_+ = 64 pi^4/Gamma(1/4)^4 F_+,
   F_+ = 4F3(3/4,3/4,1/2,1/2; 5/4,5/4,1; 1),  P4 = 13 B_- - 3 B_+."""
import sys
import mpmath as mp
sys.path.insert(0, '.')
from hypsums_jet import GammaSeq, single_sum
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 40
mp.mp.dps = dps + 20
q = mp.mpf(1) / 4
Fm = single_sum(GammaSeq([(q, mp.mpf(3) / 4, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 2 * dps, dps + 20)
Fp = single_sum(GammaSeq([(mp.mpf(3) / 4, mp.mpf(5) / 4, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 2 * dps, dps + 20)
Bm = mp.gamma(q) ** 4 * Fm
Bp = 64 * mp.pi ** 4 / mp.gamma(q) ** 4 * Fp
P4 = 13 * Bm - 3 * Bp
A = mp.psi(0, mp.mpf(1) / 2) + mp.psi(0, 1) - 2 * mp.psi(0, q)
D = mp.pi
L = -(3 * A - D) / 6 * P4 - 2 * D / 3 * Bm
mp.mp.dps = dps
print('P4(1) =', mp.nstr(mp.re(P4), dps)); print('L_1   =', mp.nstr(mp.re(L), dps))
print('B_- =', mp.nstr(mp.re(Bm), dps)); print('B_+ =', mp.nstr(mp.re(Bp), dps))
