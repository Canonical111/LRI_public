#!/usr/bin/env python3
"""Finite-sample (periodization) representation of C(tau) <t_l^2 R_tau>_d at GENERIC d   (tag R_part).

Notation (condensed note gs:spectrum, gs:RS): q = d/4, a_l = (l+q)/2, b_l = a_l + q,
  f_l(s) = Gamma(2q)^2 g_l(s)^2 R_tau(s) = Gamma(2q)^2 G(a+s)^3 G(a-s)^2 G(b-tau-s) / [G(b+s)^2 G(b-s)^3 G(a+tau+s)].

Lattice form (exact, all l >= 0, n in Z):   f_l(a_l+n+t) = Gamma(2q)^2 Phi_t(l+n) Psi_t(n),
  Phi_t(m) = G(m+q+t)^3 / [G(m+2q+t)^2 G(m+q+tau+t)],     Psi_t(n) = G(-n-t)^2 G(q-tau-n-t) / G(q-n-t)^3.
Periodized sample:  Xi(t) = D_R(t) Gamma(2q)^2 sum_{l>=0} d_l sum_{n in Z} Phi_t(l+n) Psi_t(n),
  D_R(t) = sin^2(pi t) sin^3(pi(t+q)) sin(pi(t-q+tau)).
Finite modes: Xi(t) = sum_{k=-2..2} c_k e^{2 pi i k t};   <t^2 R_tau>_d = sum_k rho_k c_k   (rho_k below).

Blocks (n>=0 right / -l<=n<=-1 middle / n<=-l-1 left):
  Xi(t) = D_R Gamma(2q)^2 [ P_R H_R + P_M H_M + P_L H_L ],
  P_R = Phi_t(0) Psi_t(0),  P_M = Phi_t(0) Psi_t(-1),  P_L = Phi_t(-1) Psi_t(-1),
  H_R = sum_{l,n>=0} d_l Phih(l+n) Psih(n)            Phih(m) = (q+t)_m^3 / [(2q+t)_m^2 (q+tau+t)_m]
  H_M = sum_{j,k>=0} d_{j+k+1} PsiMh(j) Phih(k)        Psih(n) = (1-q+t)_n^3 / [(1+t)_n^2 (1-q+tau+t)_n]
  H_L = sum_{l,p>=0} d_l PsiMh(l+p) PhiLh(p)           PsiMh(m)= (1-t)_m^2 (1+q-tau-t)_m / (1+q-t)_m^3
                                                       PhiLh(p)= (2-2q-t)_p^2 (2-q-tau-t)_p / (2-q-t)_p^3
Continuation in tau (regularization): every sequence X ~ kappa m^{a-1}, a = 1-2q-tau; subtract the K-term model
  X(m) ~ sum_i x_i B_i(m),  B_i(m) = Gamma(m+a-i)/Gamma(m+1);  model sums are Gauss / Chu-Vandermonde closed forms.
"""
import mpmath as mp


# ----------------------------------------------------------------------------- basic data
def dlist(q, L):
    """d_0..d_L via fp:degeneracy (no 0/0 at d=1,2)"""
    d = [mp.mpf(1)]
    c = 4 * q
    for k in range(L):
        d.append(c)
        c = c * (2 * q + 1 + k) * (4 * q - 1 + k) / ((2 * q + k) * (2 + k))
    return d


def poch_seq(ups, downs, M):
    """X(m) = prod (u)_m / prod (v)_m, m = 0..M"""
    X = [mp.mpf(1)]
    for m in range(M):
        num = 1
        for u in ups:
            num *= (u + m)
        den = 1
        for v in downs:
            den *= (v + m)
        X.append(X[-1] * num / den)
    return X


def series_exp(g, K):
    """exp(sum_{k>=1} g[k] u^k) to order u^{K-1}; g[0] ignored"""
    E = [mp.mpf(1)] + [0] * (K - 1)
    for k in range(1, K):
        E[k] = mp.fsum(j * g[j] * E[k - j] for j in range(1, k + 1)) / k
    return E


def model_coeffs(ups, downs, a, K):
    """x_i (i<K) with prod(u)_m/prod(v)_m - sum_i x_i Gamma(m+a-i)/Gamma(m+1) = O(m^{a-1-K}).
    Requires sum(ups) - sum(downs) = a - 1 (checked)."""
    sig = mp.fsum(ups) - mp.fsum(downs)
    assert abs(sig - (a - 1)) < mp.mpf(10) ** (-mp.mp.dps // 2), (sig, a)
    kap = 1
    for u in ups:
        kap *= mp.rgamma(u)
    for v in downs:
        kap *= mp.gamma(v)
    g = [0] * K
    for k in range(1, K):
        s = mp.fsum(mp.bernpoly(k + 1, u) for u in ups) - mp.fsum(mp.bernpoly(k + 1, v) for v in downs)
        g[k] = (-1) ** (k + 1) * s / (k * (k + 1))
    A = [kap * e for e in series_exp(g, K)]
    Bs = []
    for i in range(K):
        h = [0] * K
        for k in range(1, K):
            h[k] = (-1) ** (k + 1) * (mp.bernpoly(k + 1, a - i) - mp.bernpoly(k + 1, 1)) / (k * (k + 1))
        Bs.append(series_exp(h, K))          # B_i m^{1-a} = u^i * Bs[i](u)
    x = [0] * K
    for k in range(K):                       # coefficient of u^k
        x[k] = A[k] - mp.fsum(x[i] * Bs[i][k - i] for i in range(k))
    return x


def basis_seq(a, K, M):
    """B_i(m) = Gamma(m+a-i)/Gamma(m+1), i<K, m=0..M"""
    out = []
    for i in range(K):
        b = [mp.gamma(a - i)]
        for m in range(M):
            b.append(b[-1] * (m + a - i) / (m + 1))
        out.append(b)
    return out


def delta_seq(X, x, B, M):
    return [X[m] - mp.fsum(x[i] * B[i][m] for i in range(len(x))) for m in range(M + 1)]


# ----------------------------------------------------------------------------- closed-form kernels
def kG(al, n, q):
    """G_al(n) = sum_{l>=0} d_l B_al(l+n)   (Gauss, continued)"""
    return (mp.gamma(n + al) * mp.gamma(2 - 4 * q - al) * (2 * n + 2 - 4 * q + al)
            * mp.rgamma(n + 3 - 4 * q) * mp.rgamma(1 - al))


def kS(al, be, q):
    """S(al,be) = sum_n G_al(n) B_be(n)"""
    return (mp.gamma(al) * mp.gamma(be) * mp.gamma(2 - 4 * q - al - be) * (2 - 4 * q + al - be)
            * mp.rgamma(1 - al) * mp.rgamma(3 - 4 * q - be))


def kT(al, j, q, dj1):
    """T_al(j) = sum_{k>=0} d_{j+k+1} B_al(k)   (dj1 = d_{j+1})"""
    return (dj1 * mp.gamma(al) * mp.gamma(j + 2) * mp.gamma(2 - 4 * q - al) * mp.rgamma(3 - 4 * q) * mp.rgamma(j + 2 - al)
            * ((2 - 4 * q - al) + (4 * q - 1 + j) * al / (2 * q + j)))


def kV(al, be, q):
    """V(al,be) = sum_{j,k>=0} d_{j+k+1} B_be(j) B_al(k)   (Chu-Vandermonde + Gauss)"""
    return (2 * (1 - 2 * q) * mp.gamma(al) * mp.gamma(be) * mp.gamma(2 - 4 * q - al - be) * (4 * q - al - be)
            * mp.rgamma(3 - 4 * q) * mp.rgamma(2 - al - be))


# ----------------------------------------------------------------------------- blocks
def block_toeplitz(Xp, Yp, q, a, K, M, d):
    """H = sum_{l,n>=0} d_l X(l+n) Y(n)   (X, Y given as (ups, downs)); returns (H, parts)"""
    X = poch_seq(*Xp, M); Y = poch_seq(*Yp, M)
    x = model_coeffs(*Xp, a, K); y = model_coeffs(*Yp, a, K)
    B = basis_seq(a, K, M)
    dX = delta_seq(X, x, B, M); dY = delta_seq(Y, y, B, M)
    # P1 = sum_m dX(m) E_Y(m),  E_Y(m) = sum_{n<=m} d_{m-n} Y(n)
    P1 = mp.fsum(dX[m] * mp.fsum(d[m - n] * Y[n] for n in range(m + 1)) for m in range(M + 1))
    al = [a - i for i in range(K)]
    P2 = mp.fsum(mp.fsum(x[i] * kG(al[i], n, q) for i in range(K)) * dY[n] for n in range(M + 1))
    P3 = mp.fsum(x[i] * y[j] * kS(al[i], al[j], q) for i in range(K) for j in range(K))
    return P1 + P2 + P3, dict(P1=P1, P2=P2, P3=P3, tailX=dX[M], tailY=dY[M])


def block_middle(Xp, Yp, q, a, K, M, d):
    """H = sum_{j,k>=0} d_{j+k+1} Y(j) X(k)"""
    X = poch_seq(*Xp, M); Y = poch_seq(*Yp, M)
    x = model_coeffs(*Xp, a, K); y = model_coeffs(*Yp, a, K)
    B = basis_seq(a, K, M)
    dX = delta_seq(X, x, B, M); dY = delta_seq(Y, y, B, M)
    Q1 = mp.fsum(dY[j] * mp.fsum(d[j + k + 1] * dX[k] for k in range(M + 1)) for j in range(M + 1))
    al = [a - i for i in range(K)]
    Tk = [[kT(al[i], j, q, d[j + 1]) for i in range(K)] for j in range(M + 1)]
    Q2 = mp.fsum(dY[j] * mp.fsum(x[i] * Tk[j][i] for i in range(K)) for j in range(M + 1))
    Q3 = mp.fsum(dX[k] * mp.fsum(y[i] * Tk[k][i] for i in range(K)) for k in range(M + 1))
    Q4 = mp.fsum(x[i] * y[j] * kV(al[i], al[j], q) for i in range(K) for j in range(K))
    return Q1 + Q2 + Q3 + Q4, dict(Q1=Q1, Q2=Q2, Q3=Q3, Q4=Q4)


def seqs(q, t, tau):
    Phi = ([q + t] * 3, [2 * q + t] * 2 + [q + tau + t])
    Psi = ([1 - q + t] * 3, [1 + t] * 2 + [1 - q + tau + t])
    PsiM = ([1 - t] * 2 + [1 + q - tau - t], [1 + q - t] * 3)
    PhiL = ([2 - 2 * q - t] * 2 + [2 - q - tau - t], [2 - q - t] * 3)
    return Phi, Psi, PsiM, PhiL


def prefactors(q, t, tau):
    G, rG = mp.gamma, mp.rgamma
    Phi0 = G(q + t) ** 3 * rG(2 * q + t) ** 2 * rG(q + tau + t)
    Psi0 = G(-t) ** 2 * G(q - tau - t) * rG(q - t) ** 3
    Phim = G(q - 1 + t) ** 3 * rG(2 * q - 1 + t) ** 2 * rG(q + tau - 1 + t)
    Psim = G(1 - t) ** 2 * G(1 + q - tau - t) * rG(1 + q - t) ** 3
    D = mp.sin(mp.pi * t) ** 2 * mp.sin(mp.pi * (t + q)) ** 3 * mp.sin(mp.pi * (t - q + tau))
    return D, Phi0 * Psi0, Phi0 * Psim, Phim * Psim


def sample(q, t, tau, K=12, M=120, parts=False):
    a = 1 - 2 * q - tau
    d = dlist(q, 2 * M + 2)
    Phi, Psi, PsiM, PhiL = seqs(q, t, tau)
    HR, pR = block_toeplitz(Phi, Psi, q, a, K, M, d)
    HM, pM = block_middle(Phi, PsiM, q, a, K, M, d)
    HL, pL = block_toeplitz(PsiM, PhiL, q, a, K, M, d)
    D, PR, PM, PL = prefactors(q, t, tau)
    Xi = D * mp.gamma(2 * q) ** 2 * (PR * HR + PM * HM + PL * HL)
    if parts:
        return Xi, dict(HR=HR, HM=HM, HL=HL, pR=pR, pM=pM, pL=pL, D=D, PR=PR, PM=PM, PL=PL)
    return Xi


# ----------------------------------------------------------------------------- residue functional
def rho(k, q, tau):
    pi = mp.pi
    r0 = (2j * pi * k - pi * (3 * mp.cot(pi * q) + mp.cot(pi * (tau - q)))) / (pi ** 2 * mp.sin(pi * q) ** 3 * mp.sin(pi * (tau - q)))
    r1 = mp.expj(2 * pi * k * (q - tau)) / (pi * mp.sin(pi * (q - tau)) ** 2 * mp.sin(pi * (2 * q - tau)) ** 3)
    return -r0 - r1


def default_nodes(t0=mp.mpf('0.0917')):
    return [t0 + mp.mpf(j) / 5 for j in range(5)]


def weights(q, tau, nodes):
    """<t^2 R_tau> = sum_j w_j Xi(t_j) for 5 nodes t_j = t0 + j/5"""
    t0 = nodes[0]
    w = []
    for j in range(5):
        w.append(mp.fsum(rho(k, q, tau) * mp.expj(-2 * mp.pi * k * nodes[j]) for k in range(-2, 3)) / 5)
    return w


def tR(q, tau, K=12, M=120, nodes=None, verbose=False):
    """<t_l^2 R_tau>_d from the five samples"""
    nodes = nodes or default_nodes()
    w = weights(q, tau, nodes)
    xs = [sample(q, t, tau, K, M) for t in nodes]
    if verbose:
        for t, x in zip(nodes, xs):
            print('   Xi(%s) = %s' % (mp.nstr(t, 6), mp.nstr(x, 20)))
    return mp.fsum(wj * x for wj, x in zip(w, xs))


def Cfac(q, tau):
    return mp.gamma(2 * q) * mp.gamma(tau) * mp.rgamma(2 * q - tau)


if __name__ == '__main__':
    import sys, time
    mp.mp.dps = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    d = mp.mpf(sys.argv[1]); tau = mp.mpf(sys.argv[2])
    q = d / 4
    for K, M in ((10, 80), (12, 120), (14, 160)):
        st = time.time()
        v = tR(q, tau, K, M)
        print('d', d, 'tau', tau, 'K', K, 'M', M, ' <t^2 R> =', mp.nstr(v, 25), ' J =', mp.nstr(Cfac(q, tau) * v, 25), ' %.1fs' % (time.time() - st))


# ----------------------------------------------------------------------------- three-node rule (uses c_{+-2} = 0)
def weights3(q, tau, nodes3):
    """<t^2 R_tau> = sum_j w_j Xi(t_j), nodes t_j = t0 + j/3 -- valid because the spin-summed sample has only the modes
    k = 0, +-1 (c_{+-2} = 0: observed numerically to 1e-28..1e-32 for all tested d, proved at d = 1, 2, 3)."""
    return [mp.fsum(rho(k, q, tau) * mp.expj(-2 * mp.pi * k * nodes3[j]) for k in (-1, 0, 1)) / 3 for j in range(3)]


def tR3(q, tau, K=14, M=160, t0=mp.mpf('0.0917')):
    nodes = [t0 + mp.mpf(j) / 3 for j in range(3)]
    w = weights3(q, tau, nodes)
    return mp.fsum(wj * sample(q, t, tau, K, M) for wj, t in zip(w, nodes))
