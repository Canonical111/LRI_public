"""Independent R(3;b) (Richardson, polynomial multiplicity) and checks at b = 3/2:
 3Q3 = 12 pi^2 R + 8 sqrt2 c0/pi with c0 = -Gamma(1/4)^10/(2^{15/2} pi^{5/2}); then Z3 from Cor. integer(c) via
 a Cauchy circle of the independent R(3;b) (second derivative)."""
import sys, time
import mpmath as mp
DPS = 40; mp.mp.dps = DPS + 20
M0, K = 32, 11
q2 = mp.mpf(3)/2

def richardson(parts, e0):
    n = len(parts); Ms = [mp.mpf(M0)*2**i for i in range(n)]
    A = mp.matrix(n, n); y = mp.matrix(n, 1)
    for i in range(n):
        A[i, 0] = 1
        for k in range(n-1): A[i, k+1] = Ms[i]**(e0-k)
        y[i] = parts[i]
    return mp.lu_solve(A, y)[0]

def single(terms, e0):
    parts = []; acc = 0; idx = 0
    for i in range(K+1):
        while idx < M0*2**i:
            acc += terms[idx]; idx += 1
        parts.append(acc)
    return richardson(parts, e0), richardson(parts[1:], e0)

def R3(b):
    sig = b/2; a = sig - mp.mpf(1)/2; Mmax = M0*2**K
    F = [mp.mpf(1)]; G = [mp.mpf(1)]
    for k in range(Mmax-1):
        F.append(F[-1]*((sig+k)/(q2+k))**3); G.append(G[-1]*((a+k)/(1+k))**3)
    P0 = mp.gamma(1+a/2)*mp.gamma(1-3*a/2)/(mp.gamma(1+a)*mp.gamma(1-a/2)**2*mp.gamma(1-a))
    eG = 1 - 3*(1-a)
    P1, _ = single([n*G[n] for n in range(Mmax)], eG+1)
    eF = 1 + 3*(sig - q2)
    SF, SFb = single(F, eF); S2F, S2Fb = single([(2*m+1)*F[m] for m in range(Mmax)], eF+1)
    E = []; c0 = 0; c1 = 0
    for m in range(Mmax):
        c0 += G[m]; c1 += m*G[m]
        E.append(F[m]*((2*m+1)*(P0-c0) - 2*(P1-c1)))
    SE, SEb = single(E, eF + 2 - 3*(1-a))
    return P0*S2F - 2*P1*SF - SE, abs((P0*S2F - 2*P1*SF - SE) - (P0*S2Fb - 2*P1*SFb - SEb))

t0 = time.time()
R, err = R3(mp.mpf(3)/2)
Q3 = mp.mpf('5.01710256455385536959085484569018')
c0 = -mp.gamma(0.25)**10/(2**mp.mpf(7.5)*mp.pi**2.5)
mp.mp.dps = 30
print('R(3;3/2) indep = %s (order diff %s, %.1fs)' % (mp.nstr(R, 30), mp.nstr(err, 3), time.time()-t0))
print('  3Q3 from two-node zero-mode form: rel dev', mp.nstr((12*mp.pi**2*R + 8*mp.sqrt(2)*c0/mp.pi)/(3*Q3) - 1, 3))
mp.mp.dps = DPS + 20
# Cauchy circle for R''(3/2)
Mc = int(sys.argv[1]) if len(sys.argv) > 1 else 24; rho = mp.mpf('0.04')
vals = []
for k in range(Mc):
    bk = mp.mpf(3)/2 + rho*mp.expjpi(2*mp.mpf(k)/Mc)
    vals.append(R3(bk)[0])
R2 = 2*sum(vals[k]*mp.expjpi(-2*mp.mpf(k)*2/Mc) for k in range(Mc))/(Mc*rho**2)
R1 = sum(vals[k]*mp.expjpi(-2*mp.mpf(k)/Mc) for k in range(Mc))/(Mc*rho)
G = mp.catalan
Z3 = 4*mp.pi**2/3*R2 - (4*G + mp.pi**2/2)*mp.gamma(0.25)**10/(16*mp.pi**3.5)
Z3ref = mp.mpf('8.82092489306009248553686732817408087436')
R1pred = -mp.pi*R + mp.gamma(0.25)**10/(64*mp.pi**4.5)
mp.mp.dps = 30
print("  R'(3/2) Cauchy vs -pi R + Gamma(1/4)^10/(64 pi^{9/2}) (Prop first at d=3): rel", mp.nstr(abs(R1/R1pred - 1), 3))
print('  Z3 from Cor. integer (c) with independent R\'\' =', mp.nstr(mp.re(Z3), 25), ' vs ref: rel', mp.nstr(abs(Z3/Z3ref - 1), 3), ' (%.0fs total)' % (time.time()-t0))
