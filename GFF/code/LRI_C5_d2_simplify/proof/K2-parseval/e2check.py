# Independent end-to-end check of the tau-regularized machinery at order tau^1:
#   the proof gives [tau^1]{C(tau) D(tau)} = D_2 = <t_l^2 E_2>_2  and evaluates it as
#   2 pi^2 u - 8 pi^2 log2 + 2 sigma + 7 zeta3  = -21 zeta(3)   (u = 4log2-8G/pi, sigma = 8 pi G - 14 zeta3).
# Here <t_l^2 E_2>_2 = (1/pi) sum_l d_l int_0^oo t_l(nu)^2 E_2(l,nu) dnu is computed directly (spectral side),
# E_2 = -h^2/2 - 5 j/8 with h = Im{psi(a+i nu)-psi(b+i nu)}, j = Re{psi_1(a+i nu)-psi_1(b+i nu)} (note gs:Kweights).
# The spin sum is accelerated by generalized Richardson extrapolation (tail ~ sum_j c_j L^{-2-j}).
import sys, time, mpmath as mp
from multiprocessing import Pool
DPS = 25

def e_l(l):
    mp.mp.dps = DPS
    a = mp.mpf(l)/2 + mp.mpf(1)/4; b = a + mp.mpf(1)/2
    def f(nu):
        A, B = a + 1j*nu, b + 1j*nu
        t = abs(mp.exp(mp.loggamma(A) - mp.loggamma(B)))**2
        h = mp.im(mp.psi(0, A) - mp.psi(0, B)); j = mp.re(mp.psi(1, A) - mp.psi(1, B))
        return t**2*(-h**2/2 - 5*j/8)
    L = mp.mpf(l) + 1
    return mp.quad(f, [0, L/2, 2*L, 8*L, 64*L, mp.inf])/mp.pi

if __name__ == '__main__':
    t0 = time.time()
    L0, I = 32, 7
    Lmax = L0*2**I
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8) as pool:
        vals = pool.map(e_l, range(Lmax), chunksize=16)
    mp.mp.dps = DPS
    d = lambda l: 1 if l == 0 else 2
    Ls = [L0*2**i for i in range(I+1)]
    P = [mp.fsum(d(l)*vals[l] for l in range(L)) for L in Ls]
    J = I
    Amat = mp.matrix(J+1, J+1); bvec = mp.matrix(J+1, 1)
    for i, L in enumerate(Ls):
        Amat[i, 0] = 1
        for k in range(J):
            Amat[i, k+1] = -mp.mpf(L)**(-2-k)
        bvec[i] = P[i]
    S = mp.lu_solve(Amat, bvec)[0]
    # lower-order extrapolation for an error estimate
    J2 = I-1
    A2 = mp.matrix(J2+1, J2+1); b2 = mp.matrix(J2+1, 1)
    for i, L in enumerate(Ls[1:]):
        A2[i, 0] = 1
        for k in range(J2):
            A2[i, k+1] = -mp.mpf(L)**(-2-k)
        b2[i] = P[i+1]
    S2 = mp.lu_solve(A2, b2)[0]
    print('e(0..3) =', [mp.nstr(v, 12) for v in vals[:4]])
    print('partial sums:', [mp.nstr(p, 15) for p in P])
    print('<t^2 E_2>_2 (Richardson)       =', mp.nstr(S, 20))
    print('   (one order lower, from L>=64) =', mp.nstr(S2, 20))
    print('-21 zeta(3)                      =', mp.nstr(-21*mp.zeta(3), 20))
    print('difference                       =', mp.nstr(S + 21*mp.zeta(3), 3))
    print('elapsed %.1f s' % (time.time()-t0))
