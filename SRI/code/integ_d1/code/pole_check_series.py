"""One-bubble magnetization-scheme flow F(0,X,delta) as an exact delta-series (no numerical differentiation).
s = 2-2K = -2X. m_n = Gamma^{(n)}(s)/Gamma(s) (complete Bell in polygammas); dm_n/ds = m_{n+1} - psi0 m_n.
j = J/Gamma(s) = 1 + d j1 + d^2 j2,  j1 = -K m2,  j2 = -(K/3) m3 + (K^2/2) m4   (log insertions of f_delta)
l = d_K log J = -2 psi0 + d j1' + d^2 (j2' - j1 j1');   g = 2X - d K l;   F0 = (g - d K g_K / g)/2."""
import mpmath as mp
mp.mp.dps = 40
def run(X):
    X = mp.mpf(X); K = 1 + X; s = -2*X
    psi = [mp.polygamma(k, s) for k in range(9)]
    Y = [mp.mpf(1)]
    for n in range(8):
        Y.append(sum(mp.binomial(n, k)*psi[k]*Y[n-k] for k in range(n+1)))
    m = Y
    mK = lambda n: -2*(m[n+1] - psi[0]*m[n])
    mKK = lambda n: 4*(m[n+2] - 2*psi[0]*m[n+1] - psi[1]*m[n] + psi[0]**2*m[n])
    j1 = -K*m[2]; j1p = -m[2] - K*mK(2); j1pp = -2*mK(2) - K*mKK(2)
    j2 = -(K/3)*m[3] + (K**2/2)*m[4]
    j2p = -m[3]/3 - (K/3)*mK(3) + K*m[4] + (K**2/2)*mK(4)
    j2pp = -(2*mK(3))/3 - (K/3)*mKK(3) + m[4] + 2*K*mK(4) + (K**2/2)*mKK(4)
    l = [-2*psi[0], j1p, j2p - j1*j1p]
    lK = [4*psi[1], j1pp, j2pp - j1p**2 - j1*j1pp]
    N = 4
    g = [2*X] + [-K*l[k] for k in range(3)]                   # g_0..g_3
    gK = [mp.mpf(2)] + [-(l[k] + K*lK[k]) for k in range(3)]  # g_K coefficients
    # 1/g series
    inv = [1/g[0]] + [mp.mpf(0)]*(N-1)
    for n in range(1, N):
        inv[n] = -sum(g[k]*inv[n-k] for k in range(1, n+1))/g[0]
    ratio = [sum(gK[k]*inv[n-k] for k in range(n+1)) for n in range(N)]
    F = [g[n]/2 - (K*ratio[n-1]/2 if n >= 1 else 0) for n in range(N)]
    return F
for X in ['0.2', '0.1', '0.03', '0.01', '0.003', '-0.003', '-0.01', '-0.03']:
    F = run(X)
    print('X=%7s  ' % X + '  '.join('d^%d: %s' % (k, mp.nstr(F[k], 12)) for k in range(4)))
