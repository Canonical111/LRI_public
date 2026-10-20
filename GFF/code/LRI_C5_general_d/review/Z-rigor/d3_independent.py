"""d=3, independent of the reviewed Horn code (no Stirling tails, no Hurwitz zeta, no convolution asymptotics):
R(3;b) and Mh(3;b) from partial sums + generalized Richardson extrapolation with the known integer-spaced tail
exponents, using only the polynomial multiplicity d_l = 2l+1.  Then
  W3 = u R + v Mh   and   c0hat = c(1+c)^2 Mh/8 - pi^3 s^3 R/(1+c)  vs  -N_b^3 pi^5 Gamma(3g-2)/Gamma(g)^9.
Usage: python d3_independent.py b [dps] [M0] [K]"""
import sys, time
import mpmath as mp

b = mp.mpmathify(sys.argv[1]) if len(sys.argv) > 1 else mp.mpf('1.2')
DPS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
M0 = int(sys.argv[3]) if len(sys.argv) > 3 else 64
K = int(sys.argv[4]) if len(sys.argv) > 4 else 12
mp.mp.dps = DPS + 20
b = mp.mpmathify(sys.argv[1]) if len(sys.argv) > 1 else mp.mpf('1.2')
sig = b/2; q2 = mp.mpf(3)/2; g = q2 - sig
Mmax = M0*2**K

def seq(first, ratio, n):
    """x_0 = first, x_{k+1} = x_k * ratio(k) for k < n-1 (cubed Gamma-ratio sequences by recurrence)."""
    out = [first]
    for k in range(n-1):
        out.append(out[-1]*ratio(k))
    return out

def richardson(partials, e0):
    """partials[i] = S(M0 2^i); tail ~ sum_k c_k M^{e0-k}, k = 0..len-2 eliminated. Returns extrapolated value and
    the difference between the last two orders (error proxy)."""
    n = len(partials)
    # solve S_i = S + sum_{k<n-1} c_k M_i^{e0-k}
    Ms = [mp.mpf(M0)*2**i for i in range(n)]
    A = mp.matrix(n, n); y = mp.matrix(n, 1)
    for i in range(n):
        A[i, 0] = 1
        for k in range(n-1):
            A[i, k+1] = Ms[i]**(e0-k)
        y[i] = partials[i]
    x1 = mp.lu_solve(A, y)[0]
    # one order less (drop the smallest M)
    A2 = mp.matrix(n-1, n-1); y2 = mp.matrix(n-1, 1)
    for i in range(1, n):
        A2[i-1, 0] = 1
        for k in range(n-2):
            A2[i-1, k+1] = Ms[i]**(e0-k)
        y2[i-1] = partials[i]
    x2 = mp.lu_solve(A2, y2)[0]
    return x1, abs(x1-x2)

def single(terms, e0):
    """sum_{m>=0} terms[m] with tail exponent family e0, e0-1, ..."""
    parts = []; acc = 0; idx = 0
    for i in range(K+1):
        Mi = M0*2**i
        while idx < Mi:
            acc += terms[idx]; idx += 1
        parts.append(acc)
    return richardson(parts, e0)

def conv_part(F, G, P0, P1, eF, eE):
    """sum_m F_m H_m, H_m = sum_{n<=m} (2m-2n+1) G_n = (2m+1)P0 - 2P1 - e_m,
    e_m = (2m+1) t0_m - 2 t1_m, t0_m = sum_{n>m} G_n, t1_m = sum_{n>m} n G_n."""
    SF, eSF = single(F, eF)
    S2F, eS2F = single([(2*m+1)*F[m] for m in range(Mmax)], eF+1)
    # remainder
    c0 = 0; c1 = 0; E = []
    for m in range(Mmax):
        c0 += G[m]; c1 += m*G[m]
        t0 = P0 - c0; t1 = P1 - c1
        E.append(F[m]*((2*m+1)*t0 - 2*t1))
    SE, eSE = single(E, eE)
    return P0*S2F - 2*P1*SF - SE, max(abs(P0)*eS2F, abs(P1)*eSF, eSE)

t0 = time.time()
# ---------- R(3;b): F_m = [(sig)_m/(3/2)_m]^3, G_n = [(sig-1/2)_n/n!]^3 ----------
a = sig - mp.mpf(1)/2
F = seq(mp.mpf(1), lambda k: ((sig+k)/(q2+k))**3, Mmax)
G = seq(mp.mpf(1), lambda k: ((a+k)/(1+k))**3, Mmax)
eG = 1 - 3*(1 - a)          # G_n ~ n^{-3(1-a)} -> tail exponent 1-3(1-a)
P0, eP0 = single(G, eG)
P0dixon = mp.gamma(1+a/2)*mp.gamma(1-3*a/2)/(mp.gamma(1+a)*mp.gamma(1-a/2)**2*mp.gamma(1-a))
P1, eP1 = single([n*G[n] for n in range(Mmax)], eG+1)
eF = 1 + 3*(sig - q2)        # F_m ~ m^{3(sig-3/2)}
eE = eF + 3*(1-(1-a)) + 0    # F_m e_m ~ m^{3(sig-3/2)} m^{2-3(1-a)}: tail exponent 1 + 3sig - 9/2 + 2 - 3(1-a)
eE = 1 + 3*(sig - q2) + 2 - 3*(1 - a)
R, eR = conv_part(F, G, P0dixon, P1, eF, eE)
print('P0 Richardson vs Dixon closed form: %s  (proxy %s)' % (mp.nstr(abs(P0-P0dixon), 3), mp.nstr(eP0, 3)))
# ---------- Mh(3;b) at t_b = (1-sig)/2 : 2*Right + Mid, times N^3 ----------
t = (1 - sig)/2
Kf = -mp.sin(mp.pi*(g - t))/mp.sin(mp.pi*t)
Fp = seq((mp.gamma(sig+t)/mp.gamma(q2+t))**3, lambda k: ((sig+t+k)/(q2+t+k))**3, Mmax)
Gp = seq((mp.gamma(1-g+t)/mp.gamma(1+t))**3, lambda k: ((1-g+t+k)/(1+t+k))**3, Mmax)
eGp = 1 - 3*g
P0p, _ = single(Gp, eGp)
P1p, _ = single([n*Gp[n] for n in range(Mmax)], eGp+1)
Right, eRight = conv_part(Fp, Gp, P0p, P1p, 1 + 3*(sig - q2), 1 + 3*(sig - q2) + 2 - 3*g)
Right *= Kf**3
A = seq((mp.gamma(1-t)/mp.gamma(1+g-t))**3, lambda k: ((1-t+k)/(1+g-t+k))**3, Mmax)
B = seq((mp.gamma(sig+t)/mp.gamma(q2+t))**3, lambda k: ((sig+t+k)/(q2+t+k))**3, Mmax)
SA, _ = single(A, 1-3*g); SjA, _ = single([j*A[j] for j in range(Mmax)], 2-3*g)
SB, _ = single(B, 1-3*g); SkB, _ = single([k*B[k] for k in range(Mmax)], 2-3*g)
Mid = 2*SjA*SB + 2*SA*SkB + 3*SA*SB          # sum_{j,k} (2(j+k+1)+1) A_j B_k
N = mp.gamma(q2)*mp.gamma(g)/mp.gamma(sig)
Mh = N**3*(2*Right + Mid)
sb, cb = mp.sin(mp.pi*b/2), mp.cos(mp.pi*b/2)
u = 2*mp.pi**2*(1+2*cb)/sb**2; v = cb*(1+cb)**2/(2*mp.pi*sb**3)
W3 = u*R + v*Mh
c0 = cb*(1+cb)**2/8*Mh - mp.pi**3*sb**3/(1+cb)*R
gam = -N**3*mp.pi**5*mp.gamma(3*g-2)/mp.gamma(g)**9
mp.mp.dps = DPS
print('b = %s   (M0=%d, K=%d, Mmax=%d, %.1fs)' % (mp.nstr(b, 8), M0, K, Mmax, time.time()-t0))
print('  R(3;b)   =', mp.nstr(R, 30), '  err proxy', mp.nstr(eR, 3))
print('  Mh(3;b)  =', mp.nstr(Mh, 30), '  (Right err proxy', mp.nstr(eRight, 3), ')')
print('  W3 = uR+vMh =', mp.nstr(W3, 30))
print('  c0hat    =', mp.nstr(c0, 30))
print('  Gamma    =', mp.nstr(gam, 30), '  rel dev', mp.nstr(abs(c0/gam - 1), 3))
