"""Closed-form (first-quantized) eps^4 and eps^5 vacuum content of the reference windows (implementation B).
Extends challenge-num/topsum.py to eps^5. Window A = (L-1/2, L] (P=8 states at E=L, N=L-2);
window B = (L-1, L] (adds P=6 states at E=L-1/2, N=L-2). Dconn ("conn") vacuum: X_{L''} = [g^2D]_{2,3}+g1^3 W.

F-representation: a P-particle vector psi = sum_{ordered n} f(n) prod_i (u_{n_i} a^dag_{n_i})|0>, f symmetric.
 <psi|phi> = P! sum_ordered prod u^2 f g ;  C(eps): f'(n) = 1/(P+1) sum_i (1+eps eta_{n_i}) f(n\\i);
 B(eps): f''(n') = P sum_m u_m^2 (1+eps eta_m) f(m,n');  C^c on P-b particles: ((P-b)!/(P-b+c)!) c! sum_{|S|=P-b} .
Vacuum RS (r1 = 0, F1 = -P/4):  f1 = -(g1/12)/(N+1) [P=4];
 f2^(8) = g1^2/(144*70) (1/E) sum_{|S|=4,N_S even} 1/(N_S+1)  (E=N+2)
 f2^(6) = g1^2/180 (1/E) sum_{|S|=3} G(N_S)                 (E=N+3/2)
 f2^(4) = -(1/E)[(g1/12)/E - g1^2/12 sum_pairs J(N_q) + g2/12 + g1/12 sum_i eta_i]   (E=N+1)
 f2^(2) = -(1/E)[-(g1^2/3)(K3(n1)+K3(n2)) + r2]     (E=N+1/2)
Window content (2n+1 rule; psi1 has no window components):
 dE4(W) = -sum_W E_T <psi2^T|psi2^T> + <psi1|dX2|psi1>
 dE5(W) = 2<psi2^W|V1|psi2> - <psi2^W|V1|psi2^W> + 2<psi2^W|V2|psi1> + <psi1|dX3|psi1> + 2<psi1|dX2|psi2^(4)>
Usage: topsum5.py L [L ...] -> appends JSON lines to top5.jsonl
"""
import sys, json, time, math, itertools
import numpy as np
from numba import njit, prange

FACT = np.array([math.factorial(i) for i in range(13)], dtype=np.float64)


def subsets(n, k):
    return np.array([sum(1 << i for i in c) for c in itertools.combinations(range(n), k)], dtype=np.int64)


def build_sub_lists(n):
    """for the n positions: list of (removed-pair masks / removed-triple masks) and, for each, sub-subsets of the rest."""
    pairs = list(itertools.combinations(range(n), 2))
    trip = list(itertools.combinations(range(n), 3))
    def subs_of(rest, k):
        return [sum(1 << rest[i] for i in c) for c in itertools.combinations(range(len(rest)), k)]
    P6 = []   # for each removed pair: rest(6) mask, 4-subs(15), 3-subs(20), 2-subs(15)
    for p in pairs:
        rest = [i for i in range(n) if i not in p]
        P6.append((sum(1 << i for i in rest), subs_of(rest, 4), subs_of(rest, 3), subs_of(rest, 2), subs_of(rest, 1)))
    T5 = []   # for each removed triple: rest(5) mask, 4-subs(5), 3-subs(10), 2-subs(10), 1-subs(5)
    for t in trip:
        rest = [i for i in range(n) if i not in t]
        T5.append((sum(1 << i for i in rest), subs_of(rest, 4), subs_of(rest, 3), subs_of(rest, 2), subs_of(rest, 1)))
    return P6, T5


def pack(lst, idx):
    return np.array([x[idx] for x in lst], dtype=np.int64)


def tables(L, g1, g2, r2):
    M = L - 2
    n = L + 3
    u2 = np.empty(n); u2[0] = 1.
    for k in range(1, n): u2[k] = u2[k - 1] * (k - .5) / k
    eta = np.zeros(n)
    for k in range(1, n): eta[k] = eta[k - 1] - 0.5 / (2 * k - 1)
    c3 = np.empty(n); c3[0] = 1.
    for k in range(1, n): c3[k] = c3[k - 1] * (k + .5) / k
    T = {}
    nb = 2 * n + 4
    G = np.zeros(nb); Ge = np.zeros(nb); J = np.zeros(nb); K3 = np.zeros(nb)
    for s in range(M + 1):
        ms = np.arange(s % 2, M - s + 1, 2)
        G[s] = math.fsum(u2[ms] / (s + ms + 1)); Ge[s] = math.fsum(u2[ms] * eta[ms] / (s + ms + 1))
        J[s] = math.fsum(1.0 / (s + ms + 1)); K3[s] = math.fsum(c3[ms] / (s + ms + 1))
    q1 = np.zeros(nb); h0 = np.zeros(nb); e0 = np.zeros(nb); h0b = np.zeros(nb); e0b = np.zeros(nb)
    for c in range(M + 1):
        ms = np.arange(c % 2, M - c + 1, 2)
        q1[c] = math.fsum(u2[ms] / (c + ms + 2)); h0[c] = math.fsum(1.0 / (c + ms + 2))
        e0[c] = math.fsum(u2[ms] / (c + ms + 1.5)); h0b[c] = math.fsum(c3[ms] / (c + ms + 2))
        e0b[c] = math.fsum(1.0 / (c + ms + 1.5))
    h1 = np.zeros((n, n)); h2 = np.zeros((n, n)); e1 = np.zeros((n, n)); h1b = np.zeros((n, n)); h2b = np.zeros((n, n))
    h3b = np.zeros((n, n)); e1b = np.zeros((n, n)); e2b = np.zeros((n, n)); pJ = np.zeros((n, n))
    for b in range(M + 1):
        for a in range(M + 1):
            m1 = np.arange(a % 2, M - b + 1, 2)            # m1 == a (mod 2), b+m1 <= M
            h1[b, a] = math.fsum(u2[m1] / (a + m1 + 1) * q1[b + m1])
            h1b[b, a] = math.fsum(u2[m1] / (a + m1 + 1) * h0[b + m1])
            h2b[b, a] = math.fsum(1.0 / (a + m1 + 1) * q1[b + m1])          # s2 == a, c2=1
            if (a - b) % 2 == 0:
                s = np.arange(b % 2, M - b + 1, 2)
                h2[b, a] = math.fsum(1.0 / ((b + s + 2) * (s + a + 1)))
                h3b[b, a] = math.fsum(c3[s] / ((s + a + 1) * (b + s + 2)))
            mb = np.arange(b % 2, M - b + 1, 2)            # m == b (mod 2)
            e1[b, a] = math.fsum(u2[mb] * G[a + mb] / (b + mb + 1.5))
            e2b[b, a] = math.fsum(G[a + mb] / (b + mb + 1.5))                 # s2 == b, c2=1
            pJ[b, a] = math.fsum(u2[mb] * J[mb + a] / (b + mb + 1)) if a <= M else 0.
            mm = np.arange(0, M - b + 1)
            e1b[b, a] = math.fsum(u2[mm] * G[a + mm] * e0[b + mm])
    h1W = np.zeros((n, n)); h1bW = np.zeros((n, n)); h2bW = np.zeros((n, n)); e1bW = np.zeros((n, n))
    for b in range(M + 1):
        sW = M - b
        for a in range(M + 1):
            m1 = np.arange(a % 2, sW + 1, 2)
            h1W[b, a] = math.fsum(u2[m1] * u2[sW - m1] / (a + m1 + 1))
            h1bW[b, a] = math.fsum(u2[m1] / (a + m1 + 1))
            h2bW[b, a] = math.fsum(u2[sW - m1] / (m1 + a + 1))
            mm = np.arange(0, sW + 1)
            e1bW[b, a] = math.fsum(u2[mm] * u2[sW - mm] * G[a + mm])
    p1 = np.zeros(n); p2 = np.zeros(n); pe = np.zeros(n)
    for b in range(M + 1):
        mb = np.arange(b % 2, M - b + 1, 2)
        p1[b] = math.fsum(u2[mb] / (b + mb + 1)); p2[b] = math.fsum(u2[mb] / (b + mb + 1) ** 2)
        pe[b] = math.fsum(u2[mb] * eta[mb] / (b + mb + 1))
    return dict(u2=u2, eta=eta, c3=c3, G=G, Ge=Ge, J=J, K3=K3, h0=h0, h1=h1, h2=h2, e0=e0, e1=e1,
                h1W=h1W, h1bW=h1bW, h2bW=h2bW, e1bW=e1bW,
                h0b=h0b, h1b=h1b, h2b=h2b, h3b=h3b, e0b=e0b, e1b=e1b, e2b=e2b, p1=p1, p2=p2, pe=pe, pJ=pJ)


@njit(cache=True)
def msum(t, mask, n):
    s = 0
    for i in range(n):
        if (mask >> i) & 1: s += t[i]
    return s


@njit(cache=True)
def wmult(t, k, u2, FACT):
    w = 1.
    for i in range(k): w *= u2[t[i]]
    run = 1
    for i in range(1, k):
        if t[i] == t[i - 1]: run += 1
        else:
            w /= FACT[run]; run = 1
    w /= FACT[run]
    return w


@njit(cache=True)
def t8_terms(t, L, g1, g2, S4, P6rest, P6s4, P6s3, P6s2, T5rest, T5s3, T5s2,
             u2, eta, G, J, h0, h1, h2, e0, e1, h1W, Nm):
    """for a top 8-tuple t (N = L-2): returns f2, V (=V1 psi2 full), VA (W_A-restricted), VB (W_B-restricted), V2 (V2 psi1)."""
    M = L - 2
    c8 = g1 * g1 / (144. * 70.); c6 = g1 * g1 / 180.
    Nm[0] = 0
    for mk in range(1, 256):
        low = mk & (-mk); i = 0
        while (low >> i) != 1: i += 1
        Nm[mk] = Nm[mk ^ low] + t[i]
    # f2^(8)(t)
    s4 = 0.
    for S in S4:
        N = Nm[S]
        if N % 2 == 0: s4 += 1.0 / (N + 1)
    f2 = c8 / L * s4
    # V2 psi1 at t: (1/12)(1/70) sum_S f1(t_S)[g2 + g1 sum_{i notin S} eta]
    v2 = 0.
    for S in S4:
        N = Nm[S]
        if N % 2 == 0:
            et = 0.
            for i in range(8):
                if not ((S >> i) & 1): et += eta[t[i]]
            v2 += (-(g1 / 12.) / (N + 1)) * (g2 + g1 * et)
    v2 *= 1.0 / (12. * 70.)
    # C^2B^2 f2^(8): sum over removed pairs of H6(rest)
    sH6 = 0.; sH6W = 0.
    for ip in range(P6rest.shape[0]):
        b = Nm[P6rest[ip]]
        if b > M: continue
        sW = M - b              # added pair sum that lands in the window (E=L)
        a4 = 0.
        for S in P6s4[ip]:
            N = Nm[S]
            if N % 2 == 0: a4 += 1.0 / (N + 1)
        acc = a4 * h0[b]
        accW = 0.
        # window part: s = sW fixed, E = L
        accW = a4 / L    # c2(s)=1, parity of total automatically even
        for S in P6s3[ip]:
            a = Nm[S]
            acc += 2 * h1[b, a]
            accW += 2 * h1W[b, a] / L
        for S in P6s2[ip]:
            a = Nm[S]
            acc += h2[b, a]
            if (sW + a) % 2 == 0:
                accW += 1.0 / (L * (sW + a + 1))
        sH6 += c8 * acc; sH6W += c8 * accW
    # C^3B f2^(6): sum over removed triples of H5(rest)
    sH5 = 0.; sH5W = 0.
    for it in range(T5rest.shape[0]):
        b = Nm[T5rest[it]]
        if b > M: continue
        acc = 0.; accW = 0.
        sW = M - b          # removed mode m such that (m, rest) is a window P=6 state
        for S in T5s3[it]:
            a = Nm[S]
            acc += G[a] * e0[b]
            accW += G[a] * u2[sW] / (L - 0.5)
        for S in T5s2[it]:
            a = Nm[S]
            acc += e1[b, a]
            accW += u2[sW] * G[a + sW] / (L - 0.5)
        sH5 += c6 * acc; sH5W += c6 * accW
    # C^4 f2^(4): (1/70) sum_{4-subsets} f2^(4)(t_S)
    s24 = 0.
    for S in S4:
        N = Nm[S]
        if N % 2 != 0: continue
        E = N + 1.
        jj = 0.; et = 0.
        idx = np.empty(4, np.int64); k = 0
        for i in range(8):
            if (S >> i) & 1:
                idx[k] = t[i]; k += 1; et += eta[t[i]]
        for x in range(4):
            for y in range(x + 1, 4):
                jj += J[idx[x] + idx[y]]
        s24 += -(1.0 / E) * ((g1 / 12.) / E - (g1 * g1 / 12.) * jj + g2 / 12. + (g1 / 12.) * et)
    V = -2. * f2 + g1 * sH6 + g1 * sH5 / 28. + g1 * s24 / (12. * 70.)
    VA = -2. * f2 + g1 * sH6W
    VB = VA + g1 * sH5W / 28.
    return f2, V, VA, VB, v2


@njit(parallel=True, cache=True)
def sum8(L, g1, g2, S4, P6rest, P6s4, P6s3, P6s2, T5rest, T5s3, T5s2, u2, eta, G, J, h0, h1, h2, e0, e1, h1W, FACT):
    M = L - 2
    nn = M // 8 + 1
    out = np.zeros((nn, 4))
    for n1 in prange(nn):
        t = np.zeros(8, dtype=np.int64)
        Nm = np.zeros(256, dtype=np.int64)
        t[0] = n1; r1 = M - n1
        a0 = 0.; aA = 0.; aB = 0.; a4 = 0.
        for n2 in range(n1, r1 // 7 + 1):
            t[1] = n2; r2 = r1 - n2
            for n3 in range(n2, r2 // 6 + 1):
                t[2] = n3; r3 = r2 - n3
                for n4 in range(n3, r3 // 5 + 1):
                    t[3] = n4; r4 = r3 - n4
                    for n5 in range(n4, r4 // 4 + 1):
                        t[4] = n5; r5 = r4 - n5
                        for n6 in range(n5, r5 // 3 + 1):
                            t[5] = n6; r6 = r5 - n6
                            for n7 in range(n6, r6 // 2 + 1):
                                t[6] = n7; t[7] = r6 - n7
                                w = wmult(t, 8, u2, FACT)
                                f2, V, VA, VB, v2 = t8_terms(t, L, g1, g2, S4, P6rest, P6s4, P6s3, P6s2, T5rest, T5s3, T5s2,
                                                             u2, eta, G, J, h0, h1, h2, e0, e1, h1W, Nm)
                                a4 += w * f2 * f2
                                aA += w * f2 * (2 * V - VA + 2 * v2)
                                aB += w * f2 * (2 * V - VB + 2 * v2)
        out[n1, 0] = a4; out[n1, 1] = aA; out[n1, 2] = aB
    return out


@njit(cache=True)
def t6_terms(t, L, g1, g2, r2, S3, S4, Q4rest, Q4s3, Q4s2, Q4s1, F5rest, F5s4, F5s3, F5s2, F5s1, S3all, S2all,
             u2, eta, c3, G, Ge, J, K3, h0b, h1b, h2b, h3b, e0b, e1b, e2b, p1, p2, pe, pJ, h1bW, h2bW, e1bW):
    """top 6-tuple t (N=L-2, E=L-1/2). Returns f2, V, VB, V2."""
    M = L - 2
    c8 = g1 * g1 / (144. * 70.); c6 = g1 * g1 / 180.
    E6 = L - 0.5
    sg = 0.
    for S in S3:
        sg += G[msum(t, S, 6)]
    f2 = c6 / E6 * sg
    # V2 psi1 at t: r2 (1/15) sum_{4-sub} f1 + (1/3)[g2 (1/20) sum_3 (-(g1/3))G + g1 (1/20) sum_3 (-(g1/3))(Ge + G*eta_out)]
    v2 = 0.
    for S in S4:
        N = msum(t, S, 6)
        if N % 2 == 0: v2 += r2 * (1. / 15.) * (-(g1 / 12.) / (N + 1))
    for S in S3:
        a = msum(t, S, 6)
        et = 0.
        for i in range(6):
            if not ((S >> i) & 1): et += eta[t[i]]
        v2 += (1. / 3.) * (1. / 20.) * (-(g1 / 3.)) * (g2 * G[a] + g1 * (Ge[a] + G[a] * et))
    # CB^3 f2^(8): 56 sum_{5-subsets (removed single)} H5b(rest)
    sH5b = 0.; sH5bW = 0.
    for ir in range(F5rest.shape[0]):
        b = msum(t, F5rest[ir], 6)
        sW = M - b
        a4 = 0.
        for S in F5s4[ir]:
            N = msum(t, S, 6)
            if N % 2 == 0: a4 += 1.0 / (N + 1)
        acc = a4 * h0b[b]; accW = a4 * c3[sW] / L
        for S in F5s3[ir]:
            a = msum(t, S, 6)
            acc += 3 * h1b[b, a]
            accW += 3 * h1bW[b, a] / L
        for S in F5s2[ir]:
            a = msum(t, S, 6)
            acc += 3 * h2b[b, a]
            accW += 3 * h2bW[b, a] / L
        for S in F5s1[ir]:
            a = msum(t, S, 6)
            acc += h3b[b, a]
            if (sW + a) % 2 == 0: accW += c3[sW] / (L * (sW + a + 1))
        sH5b += c8 * acc; sH5bW += c8 * accW
    # C^2B^2 f2^(6): 2 sum_{4-subsets (removed pair)} H4(rest)
    sH4 = 0.; sH4W = 0.
    for iq in range(Q4rest.shape[0]):
        b = msum(t, Q4rest[iq], 6)
        sW = M - b
        acc = 0.; accW = 0.
        for S in Q4s3[iq]:
            a = msum(t, S, 6)
            acc += G[a] * e0b[b]; accW += G[a] / E6
        for S in Q4s2[iq]:
            a = msum(t, S, 6)
            acc += 2 * e1b[b, a]
            accW += 2 * e1bW[b, a] / E6
        for S in Q4s1[iq]:
            a = msum(t, S, 6)
            acc += e2b[b, a]; accW += G[a + sW] / E6
        sH4 += c6 * acc; sH4W += c6 * accW
    # C^3B f2^(4): (1/5) sum_{3-subsets} H3(t_S);  H3(k3) = sum_m u2 f2^(4)(m,k3)
    sH3 = 0.
    for S in S3all:
        b = msum(t, S, 6)
        k = np.empty(3, np.int64); c = 0; et = 0.
        for i in range(6):
            if (S >> i) & 1:
                k[c] = t[i]; c += 1; et += eta[t[i]]
        jkk = J[k[0] + k[1]] + J[k[0] + k[2]] + J[k[1] + k[2]]
        sJ = pJ[b, k[0]] + pJ[b, k[1]] + pJ[b, k[2]]
        sH3 += (-(g1 / 12.) * p2[b] + (g1 * g1 / 12.) * (jkk * p1[b] + sJ) - (g2 / 12.) * p1[b]
                - (g1 / 12.) * (pe[b] + et * p1[b]))
    # C^4 f2^(2): (1/15) sum_{pairs} f2^(2)
    s22 = 0.
    for S in S2all:
        k0 = -1; k1 = -1
        for i in range(6):
            if (S >> i) & 1:
                if k0 < 0: k0 = t[i]
                else: k1 = t[i]
        N = k0 + k1
        if N % 2 == 0:
            s22 += -(1.0 / (N + 0.5)) * (-(g1 * g1 / 3.) * (K3[k0] + K3[k1]) + r2)
    V = -1.5 * f2 + g1 * ((56. / 3.) * sH5b + sH4 + sH3 / 15. + s22 / 180.)
    VB = -1.5 * f2 + g1 * ((56. / 3.) * sH5bW + sH4W)
    return f2, V, VB, v2


@njit(parallel=True, cache=True)
def sum6(L, g1, g2, r2, S3, S4, Q4rest, Q4s3, Q4s2, Q4s1, F5rest, F5s4, F5s3, F5s2, F5s1, S3all, S2all,
         u2, eta, c3, G, Ge, J, K3, h0b, h1b, h2b, h3b, e0b, e1b, e2b, p1, p2, pe, pJ, h1bW, h2bW, e1bW, FACT):
    M = L - 2
    nn = M // 6 + 1
    out = np.zeros((nn, 2))
    for n1 in prange(nn):
        t = np.zeros(6, dtype=np.int64)
        t[0] = n1; r1 = M - n1
        a4 = 0.; aB = 0.
        for n2 in range(n1, r1 // 5 + 1):
            t[1] = n2; r2_ = r1 - n2
            for n3 in range(n2, r2_ // 4 + 1):
                t[2] = n3; r3 = r2_ - n3
                for n4 in range(n3, r3 // 3 + 1):
                    t[3] = n4; r4 = r3 - n4
                    for n5 in range(n4, r4 // 2 + 1):
                        t[4] = n5; t[5] = r4 - n5
                        w = wmult(t, 6, u2, FACT)
                        f2, V, VB, v2 = t6_terms(t, L, g1, g2, r2, S3, S4, Q4rest, Q4s3, Q4s2, Q4s1, F5rest, F5s4, F5s3, F5s2, F5s1,
                                                 S3all, S2all, u2, eta, c3, G, Ge, J, K3, h0b, h1b, h2b, h3b, e0b, e1b, e2b, p1, p2, pe, pJ, h1bW, h2bW, e1bW)
                        a4 += w * f2 * f2
                        aB += w * f2 * (2 * V - VB + 2 * v2)
        out[n1, 0] = a4; out[n1, 1] = aB
    return out


def subs_rest(n, kremove):
    rem = list(itertools.combinations(range(n), kremove))
    rows = []
    for r_ in rem:
        rest = [i for i in range(n) if i not in r_]
        def sub(k):
            return [sum(1 << rest[i] for i in c) for c in itertools.combinations(range(len(rest)), k)]
        rows.append((sum(1 << i for i in rest), sub(4), sub(3), sub(2), sub(1)))
    return rows


def arr(rows, j):
    return np.array([r[j] for r in rows], dtype=np.int64)


def dX_terms(L, g1, g2, r2):
    """<psi1|dX3|psi1> + 2<psi1|dX2|psi2^(4)> and <psi1|dX2|psi1> for windows A (L''=L-1/2) and B (L-1),
    computed in the second-quantized P<=4 space (htb5 ladders)."""
    from htb5 import Space, bubble_S_table, g2D3W_diag
    K = 5
    sp = Space(4 * L, 4, None, K, keep_modes=False)
    mask = (sp.N % 2 == 0)
    E0 = sp.E4 / 4.
    Rinv = np.where(mask & (sp.E4 > 0), -1.0 / np.where(sp.E4 > 0, E0, 1.), 0.)
    e0 = np.zeros(sp.dim); e0[0] = 1.
    M0, V0 = sp.vertices(e0, 1, mask)
    psi1 = Rinv * g1 * V0[:, 0]
    M1, V1 = sp.vertices(psi1, 0, mask)
    F1 = -sp.P / 4.
    rr = [0, 0, r2]; gg = [0, g1, g2]
    t2 = F1 * psi1 + g1 * V1[:, 0] + r2 * M0[:, 0] + g2 * V0[:, 0] + g1 * V0[:, 1]
    psi2 = Rinv * t2
    p4 = (sp.P == 4)
    S = bubble_S_table(L + 2, K); Sf = np.array([[float(x) for x in row] for row in S])
    g = np.array([0, g1, g2, 0, 0, 0.])
    X = {c4: g2D3W_diag(sp.E4, g, c4, Sf, K) for c4 in (4 * L, 4 * L - 2, 4 * L - 4)}
    out = {}
    for name, c4 in (('A', 4 * L - 2), ('B', 4 * L - 4)):
        d2 = X[4 * L][:, 2] - X[c4][:, 2]; d3 = X[4 * L][:, 3] - X[c4][:, 3]
        out[name] = dict(dX4=float(psi1 @ (d2 * psi1)),
                         dX5=float(psi1 @ (d3 * psi1) + 2 * (psi1 @ (d2 * (psi2 * p4)))))
    return out


def compute(L, g1, g2, r2, threads=None):
    t0 = time.time()
    T = tables(L, g1, g2, r2)
    S4 = subsets(8, 4)
    R6 = subs_rest(8, 2); R5 = subs_rest(8, 3)
    o8 = sum8(L, g1, g2, S4, arr(R6, 0), arr(R6, 1), arr(R6, 2), arr(R6, 3), arr(R5, 0), arr(R5, 2), arr(R5, 3),
              T['u2'], T['eta'], T['G'], T['J'], T['h0'], T['h1'], T['h2'], T['e0'], T['e1'], T['h1W'], FACT)
    S3_6 = subsets(6, 3); S4_6 = subsets(6, 4); S2_6 = subsets(6, 2)
    Q4 = subs_rest(6, 2); F5 = subs_rest(6, 1)
    o6 = sum6(L, g1, g2, r2, S3_6, S4_6, arr(Q4, 0), arr(Q4, 2), arr(Q4, 3), arr(Q4, 4), arr(F5, 0), arr(F5, 1), arr(F5, 2), arr(F5, 3), arr(F5, 4),
              S3_6, S2_6, T['u2'], T['eta'], T['c3'], T['G'], T['Ge'], T['J'], T['K3'], T['h0b'], T['h1b'], T['h2b'], T['h3b'],
              T['e0b'], T['e1b'], T['e2b'], T['p1'], T['p2'], T['pe'], T['pJ'], T['h1bW'], T['h2bW'], T['e1bW'], FACT)
    f8 = math.factorial(8) ** 2; f6 = math.factorial(6) ** 2
    s4_8 = math.fsum(o8[:, 0]); sA = math.fsum(o8[:, 1]); sB8 = math.fsum(o8[:, 2])
    s4_6 = math.fsum(o6[:, 0]); sB6 = math.fsum(o6[:, 1])
    dX = dX_terms(L, g1, g2, r2)
    A4 = -f8 * L * s4_8 + dX['A']['dX4']
    B4 = -f8 * L * s4_8 - f6 * (L - 0.5) * s4_6 + dX['B']['dX4']
    A5 = f8 * sA + dX['A']['dX5']
    B5 = f8 * sB8 + f6 * sB6 + dX['B']['dX5']
    return dict(L=L, A4=A4, B4=B4, A5=A5, B5=B5, top8_5=f8 * sA, top8B_5=f8 * sB8, top6_5=f6 * sB6, dX=dX,
                top8_4=-f8 * L * s4_8, top6_4=-f6 * (L - .5) * s4_6, sec=time.time() - t0)


if __name__ == '__main__':
    from couplings import raw_couplings
    for L in [int(a) for a in sys.argv[1:]]:
        r, g = raw_couplings(L)
        res = compute(L, g[1], g[2], r[2])
        res['g2'] = g[2]; res['r2'] = r[2]
        print(json.dumps(res), flush=True)
        with open('top5.jsonl', 'a') as f:
            f.write(json.dumps(res) + '\n')
