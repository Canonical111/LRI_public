"""One-bubble (two-kink) part of the magnetization-scheme flow: F(0,X,delta) = sum_{n,k} f_0_n_k X^n delta^k.
Exact delta-series in terms of polygammas of s = -2X (log insertions of f_delta = (r^delta-1)/delta),
Taylor coefficients at X = 0 (K = 1) by a Cauchy contour integral (the poles at X = 0 cancel)."""
import mpmath as mp
def delta_series(X, N=4):
    K = 1 + X; s = -2*X
    psi = [mp.polygamma(k, s) for k in range(10)]
    m = [mp.mpf(1)]
    for n in range(9):
        m.append(sum(mp.binomial(n, k)*psi[k]*m[n-k] for k in range(n+1)))
    mK = lambda n: -2*(m[n+1] - psi[0]*m[n])
    mKK = lambda n: 4*(m[n+2] - 2*psi[0]*m[n+1] - psi[1]*m[n] + psi[0]**2*m[n])
    # j = J/Gamma(s) = 1 + d j1 + d^2 j2 + d^3 j3   (exp(-2K[d L^2/2 + d^2 L^3/6 + d^3 L^4/24]))
    jc = [(1, [(-1, 1, 2)]),                                    # j1 = -K m2
          (2, [(-mp.mpf(1)/3, 1, 3), (mp.mpf(1)/2, 2, 4)]),          # j2
          (3, [(-mp.mpf(1)/12, 1, 4), (mp.mpf(1)/3, 2, 5), (-mp.mpf(1)/6, 3, 6)])]  # j3
    jv, jp, jpp = [mp.mpf(1)], [mp.mpf(0)], [mp.mpf(0)]
    for _, terms in jc:
        v = sum(c*K**p*m[n] for c, p, n in terms)
        vp = sum(c*(p*K**(p-1)*m[n] + K**p*mK(n)) for c, p, n in terms)
        vpp = sum(c*(p*(p-1)*K**(p-2)*m[n] + 2*p*K**(p-1)*mK(n) + K**p*mKK(n)) for c, p, n in terms)
        jv.append(v); jp.append(vp); jpp.append(vpp)
    # log j series and its K-derivatives (to order d^3)
    def series_log(a):            # log(1 + a1 d + a2 d^2 + a3 d^3)
        return [0, a[1], a[2] - a[1]**2/2, a[3] - a[1]*a[2] + a[1]**3/3]
    lj = series_log(jv)
    ljp = [0, jp[1], jp[2] - jv[1]*jp[1], jp[3] - jp[1]*jv[2] - jv[1]*jp[2] + jv[1]**2*jp[1]]
    ljpp = [0, jpp[1], jpp[2] - jp[1]**2 - jv[1]*jpp[1],
            jpp[3] - jpp[1]*jv[2] - 2*jp[1]*jp[2] - jv[1]*jpp[2] + 2*jv[1]*jp[1]**2 + jv[1]**2*jpp[1]]
    l = [-2*psi[0] + ljp[0]] + ljp[1:]          # d_K log J = -2 psi0 + d_K log j
    lK = [4*psi[1] + ljpp[0]] + ljpp[1:]
    g = [2*X] + [-K*l[k] for k in range(N-1)]
    gK = [mp.mpf(2)] + [-(l[k] + K*lK[k]) for k in range(N-1)]
    inv = [1/g[0]] + [0]*(N-1)
    for n in range(1, N):
        inv[n] = -sum(g[k]*inv[n-k] for k in range(1, n+1))/g[0]
    ratio = [sum(gK[k]*inv[n-k] for k in range(n+1)) for n in range(N)]
    return [g[n]/2 - (K*ratio[n-1]/2 if n >= 1 else 0) for n in range(N)]
def taylor_coeffs(N=4, nmax=4, r=mp.mpf('0.2'), npts=96):
    """f[(n,k)] = [X^n delta^k] F(0,X,delta) at X=0, k < N."""
    acc = {(n, k): mp.mpc(0) for n in range(nmax+1) for k in range(N)}
    for j in range(npts):
        Xj = r*mp.expjpi(2*mp.mpf(j)/npts)
        F = delta_series(Xj, N)
        for n in range(nmax+1):
            for k in range(N):
                acc[(n, k)] += F[k]/Xj**n
    return {key: mp.re(v/npts) for key, v in acc.items()}
if __name__ == '__main__':
    mp.mp.dps = 40
    f = taylor_coeffs()
    for (n, k), v in sorted(f.items(), key=lambda t: (t[0][1], t[0][0])):
        print(f'f_0_{n}_{k} = {mp.nstr(v, 30)}')
    print('check f_0_0_1 + gamma_E =', mp.nstr(f[(0, 1)] + mp.euler, 5))
