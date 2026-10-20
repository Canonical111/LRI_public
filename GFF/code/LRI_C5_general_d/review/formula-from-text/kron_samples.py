#!/usr/bin/env python3
"""Independent evaluation of the finite samples X_T, X_0, X_{1/2}, T3, M3 of general_d.tex (review formula-from-text).

Method (deliberately different from foundation/hypsums.py, which uses exact Stirling tails + Hurwitz zeta):
  * the lattice sums are split (my own derivation, see REPORT.md) into the right half-lattice ("h" sums,
    sum_{l,n>=0} d_l X_{l+n} Z_n) and the middle block ("s" sums, sum_{j,k>=0} d_{j+k+2u} a_j a_k);
  * every sum is truncated on the triangle m = l+n <= M (resp. j+k <= M); the inner convolution is done
    EXACTLY in fixed point by one big-integer (Kronecker) multiplication with GMP, so all partial sums S_M,
    M <= Mmax ~ 1e5, are available at once;
  * the limit is obtained by generalized Richardson extrapolation (least squares) with the two exponent families
    S_M - S ~ sum_i alpha_i M^{F1-i} + sum_i beta_i M^{F2-i},  F1 = d-1-r g,  F2 = d-2 r g,  g = (d-b)/2,
    which follow from singularity analysis of the generating functions (1+z)(1-z)^{1-d} and r+1F_r(z).
  * b may be complex (b-derivatives by Cauchy circles in review drivers).
"""
import sys
import gmpy2
from gmpy2 import mpfr, mpc, mpz
import mpmath as mp

CTX = gmpy2.get_context()


# ------------------------------------------------------------------ exact type conversions mpmath <-> gmpy2
def m2g_real(v):
    v = mp.mpf(v)
    if v == 0:
        return mpfr(0)
    sgn, man, ex, _ = v._mpf_
    r = mpfr(int(man)) * mpfr(2) ** int(ex)
    return -r if sgn else r


def m2g(v):
    v = mp.mpc(v)
    return mpc(m2g_real(v.real), m2g_real(v.imag))


def g2m_real(v):
    man, ex = v.as_mantissa_exp()
    return mp.mpf((int(man), int(ex)))


def g2m(v):
    v = mpc(v)
    return mp.mpc(g2m_real(v.real), g2m_real(v.imag))



def setprec(bits):
    CTX.precision = bits
    mp.mp.prec = bits + 64


# ------------------------------------------------------------------ fixed-point / Kronecker convolution
def to_fix(x, P):
    return int(gmpy2.rint(gmpy2.mul_2exp(x, P)))


def pack(vals, W):
    nb = W // 8
    mask = (1 << W) - 1
    U = int.from_bytes(b''.join((v & mask).to_bytes(nb, 'little') for v in vals), 'little')
    neg = bytearray(nb * (len(vals) + 1))
    anyneg = False
    for i, v in enumerate(vals):
        if v < 0:
            neg[nb * (i + 1)] = 1
            anyneg = True
    if anyneg:
        U -= int.from_bytes(bytes(neg), 'little')
    return U


def unpack(Pi, n, W):
    nb = W // 8
    off = int.from_bytes((b'\x00' * (nb - 1) + b'\x80') * n, 'little')
    V = (Pi + off) & ((1 << (W * n)) - 1)
    bs = V.to_bytes(nb * n, 'little')
    half = 1 << (W - 1)
    return [int.from_bytes(bs[i * nb:(i + 1) * nb], 'little') - half for i in range(n)]


def kron_mul(a, b, n, sq=False):
    """first n coefficients of the product of integer sequences a, b (signed)."""
    la = max(abs(v) for v in a).bit_length()
    lb = max(abs(v) for v in b).bit_length()
    W = la + lb + n.bit_length() + 4
    W = (W + 7) // 8 * 8
    A = gmpy2.mpz(pack(a, W))
    if sq:
        Pi = A * A
    else:
        Pi = A * gmpy2.mpz(pack(b, W))
    return unpack(int(Pi), n, W)


# ------------------------------------------------------------------ sequences
def dseq(d, M):
    d = mpfr(d) if not isinstance(d, type(mpfr(1))) else d
    out = [mpfr(1)]
    if M >= 1:
        out.append(d)
    for l in range(1, M):
        out.append(out[-1] * (2 * l + d) * (l + d - 2) / ((2 * l + d - 2) * (l + 1)))
    return out


def ratio_pow_seq(alpha, beta, r, M):
    """[ (alpha)_m/(beta)_m ]^r, m = 0..M (complex)."""
    out = [mpc(1)]
    v = mpc(1)
    for m in range(M):
        q = (alpha + m) / (beta + m)
        v = v * q ** r
        out.append(v)
    return out


# ------------------------------------------------------------------ partial sums of the two sum types
def h_partials(d, x, y, u, r, M, P, dvals):
    """S_M = sum_{l+n<=M} d_l [(u+x)_{l+n}/(u+y)_{l+n}]^r [(u+1-y)_n/(u+1-x)_n]^r, all M <= Mmax."""
    X = ratio_pow_seq(u + x, u + y, r, M)
    Z = ratio_pow_seq(u + 1 - y, u + 1 - x, r, M)
    dI = [to_fix(v, P) for v in dvals[:M + 1]]
    Zr = [to_fix(v.real, P) for v in Z]
    Zi = [to_fix(v.imag, P) for v in Z]
    cr = kron_mul(dI, Zr, M + 1)
    ci = kron_mul(dI, Zi, M + 1) if any(Zi) else [0] * (M + 1)
    sc = mpfr(2) ** (-2 * P)
    out = []
    acc = mpc(0)
    for m in range(M + 1):
        acc += X[m] * mpc(mpfr(cr[m]) * sc, mpfr(ci[m]) * sc)
        out.append(acc)
    return out


def s_partials(d, x, y, u2, r, M, P, dvals):
    """S_M = sum_{j+k<=M} d_{j+k+u2} a_j a_k, a_j = [(u+x)_j/(u+y)_j]^r, u = u2/2 (u2 in {0,1})."""
    u = mpfr(u2) / 2
    a = ratio_pow_seq(u + x, u + y, r, M)
    ar = [to_fix(v.real, P) for v in a]
    ai = [to_fix(v.imag, P) for v in a]
    rr = kron_mul(ar, ar, M + 1, sq=True)
    if any(ai):
        ii = kron_mul(ai, ai, M + 1, sq=True)
        ri = kron_mul(ar, ai, M + 1)
    else:
        ii = [0] * (M + 1)
        ri = [0] * (M + 1)
    sc = mpfr(2) ** (-2 * P)
    out = []
    acc = mpc(0)
    for m in range(M + 1):
        e = mpc(mpfr(rr[m] - ii[m]) * sc, mpfr(2 * ri[m]) * sc)
        acc += dvals[m + u2] * e
        out.append(acc)
    return out


# ------------------------------------------------------------------ generalized Richardson (least squares)
def richardson(partials, Ms, F1, F2, J1, J2, Mref=None):
    """Fit S_M = S + sum_{i<J1} a_i (M/Mref)^{F1-i} + sum_{i<J2} b_i (M/Mref)^{F2-i}; return S."""
    if Mref is None:
        Mref = Ms[-1]
    F1 = mp.mpc(F1)
    F2 = mp.mpc(F2)
    rows = []
    rhs = []
    for M in Ms:
        z = mp.mpf(M) / Mref
        row = [mp.mpc(1)]
        row += [z ** (F1 - i) for i in range(J1)]
        row += [z ** (F2 - i) for i in range(J2)]
        rows.append(row)
        S = partials[M]
        rhs.append(g2m(S))
    A = mp.matrix(rows)
    bvec = mp.matrix(rhs)
    if A.rows == A.cols:
        sol = mp.lu_solve(A, bvec)
    else:
        AH = A.H
        sol = mp.lu_solve(AH * A, AH * bvec)
    return sol[0]


def default_Ms(Mmax, K, Mmin_frac=8):
    lo = Mmax // Mmin_frac
    ratio = (mp.mpf(Mmax) / lo) ** (mp.mpf(1) / (K - 1))
    Ms = sorted(set(int(mp.nint(lo * ratio ** k)) for k in range(K)))
    Ms[-1] = Mmax
    return Ms


# ------------------------------------------------------------------ the samples
def samples(d, b, Mmax, P=240, J=(10, 10), K=None, Mmin_frac=8, want=('4', '3'), verbose=False, dropF1=False):
    """Return dict with XT, X0, Xh (r=4) and T3, M3, c0hat (r=3) at dimension d, rim exponent b (complex ok),
    each with an extrapolation-spread estimate (difference of two fits)."""
    d = m2g_real(d)
    b = m2g(b)
    x = b / 4
    y = d / 2 - b / 4
    g = y - x
    dvals = dseq(d, Mmax + 2)
    res = {}
    J1, J2 = J
    if K is None:
        K = 2 * (J1 + J2) + 8
    Ms = default_Ms(Mmax, K, Mmin_frac)

    def ext(parts, r):
        F1 = g2m_real(d) - 1 - r * g2m(g)
        F2 = g2m_real(d) - 2 * r * g2m(g)
        j1 = 0 if dropF1 else J1
        v1 = richardson(parts, Ms, F1, F2, j1, J2)
        v2 = richardson(parts, Ms[: len(Ms) - 6], F1, F2, max(j1 - 1, 0), J2 - 1)
        return v1, abs(v1 - v2)

    mpb = g2m(b)
    mpd = g2m_real(d)
    mx = mpb / 4
    my = mpd / 2 - mpb / 4
    mg = (mpd - mpb) / 2
    sig = mpb / 2
    q = mpd / 4
    Nb = mp.gamma(2 * q) * mp.gamma(mg) / mp.gamma(sig)
    sb = mp.sin(mp.pi * mpb / 2)
    cb = mp.cos(mp.pi * mpb / 2)
    rho0 = mx * (1 - my) / (my * (1 - mx))
    rhoh = (1 - 2 * my) / (1 - 2 * mx)
    kap0 = Nb * mp.sin(mp.pi * mx) ** 2 * mp.gamma(mx) ** 2 / mp.gamma(my) ** 2
    kaph = Nb * mp.cos(mp.pi * mx) ** 2 * mp.gamma(mp.mpf(1) / 2 + mx) ** 2 / mp.gamma(mp.mpf(1) / 2 + my) ** 2
    errs = {}
    if '4' in want:
        hx, e_hx = ext(h_partials(d, x, y, x, 4, Mmax, P, dvals), 4)
        h1, e_h1 = ext(h_partials(d, x, y, mpfr(1), 4, Mmax, P, dvals), 4)
        hh, e_hh = ext(h_partials(d, x, y, mpfr(1) / 2, 4, Mmax, P, dvals), 4)
        s0, e_s0 = ext(s_partials(d, x, y, 0, 4, Mmax, P, dvals), 4)
        sh, e_sh = ext(s_partials(d, x, y, 1, 4, Mmax, P, dvals), 4)
        res['XT'] = (mp.pi * sb) ** 4 * hx
        res['X0'] = kap0 ** 4 * (s0 + 2 * rho0 ** 4 * h1)
        res['Xh'] = kaph ** 4 * (sh + 2 * rhoh ** 4 * hh)
        errs['XT'] = abs((mp.pi * sb) ** 4) * e_hx
        errs['X0'] = abs(kap0 ** 4) * (e_s0 + 2 * abs(rho0 ** 4) * e_h1)
        errs['Xh'] = abs(kaph ** 4) * (e_sh + 2 * abs(rhoh ** 4) * e_hh)
        res['raw4'] = dict(hx=hx, h1=h1, hh=hh, s0=s0, sh=sh)
    if '3' in want:
        T3, e_T3 = ext(h_partials(d, x, y, x, 3, Mmax, P, dvals), 3)
        hh3, e_hh3 = ext(h_partials(d, x, y, mpfr(1) / 2, 3, Mmax, P, dvals), 3)
        sh3, e_sh3 = ext(s_partials(d, x, y, 1, 3, Mmax, P, dvals), 3)
        pref = Nb ** 3 * (mp.gamma(mp.mpf(1) / 2 + mx) / mp.gamma(mp.mpf(1) / 2 + my)) ** 6
        M3 = pref * (sh3 + 2 * rhoh ** 3 * hh3)
        res['T3'] = T3
        res['M3'] = M3
        res['c0hat'] = cb * (1 + cb) ** 2 / 8 * M3 - mp.pi ** 3 * sb ** 3 * T3 / (1 + cb)
        errs['T3'] = e_T3
        errs['M3'] = abs(pref) * (e_sh3 + 2 * abs(rhoh ** 3) * e_hh3)
        res['raw3'] = dict(T3=T3, hh3=hh3, sh3=sh3)
    res['err'] = errs
    return res


def W4_from(sm, b):
    b = mp.mpc(b)
    s = mp.sin(mp.pi * b / 2)
    c = mp.cos(mp.pi * b / 2)
    return 2 / (mp.pi * s ** 7) * ((1 + c) ** 2 * (1 + 2 * c) * sm['X0'] - (1 - c) ** 2 * (1 - 2 * c) * sm['Xh']
                                   - 2 * c * sm['XT'])


def W3_from(sm, b):
    b = mp.mpc(b)
    s = mp.sin(mp.pi * b / 2)
    return 6 * mp.pi ** 2 / s ** 2 * sm['T3'] + 4 / (mp.pi * s ** 3) * sm['c0hat']


if __name__ == '__main__':
    import time
    d = mp.mpf(sys.argv[1]) if len(sys.argv) > 1 else mp.mpf('1.5')
    Mmax = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    setprec(240)
    t0 = time.time()
    sm = samples(d, d / 2, Mmax, P=220, J=(6, 6))
    print('time', time.time() - t0)
    for k in ('XT', 'X0', 'Xh', 'T3', 'M3', 'c0hat'):
        print(k, mp.nstr(sm[k].real, 30), mp.nstr(sm[k].imag, 5), 'err~', mp.nstr(sm['err'].get(k, 0), 3))
    print('P4', mp.nstr(W4_from(sm, d / 2).real, 35))
    print('3Q', mp.nstr(W3_from(sm, d / 2).real, 35))
