#!/usr/bin/env python3
"""Independent check of the spin-summed top modes (tag topmode).  Shares no code with rblocks.py / hypsums.py.

Generic periodized kernel (PROOF.md, Lemma G):
   T(l,n,t) = prod_i Gamma(l+sigma+alpha_i+n+t)/Gamma(l+sigma+alpha_i+g_i+n+t) * prod_j Gamma(beta_j-n-t)/Gamma(beta_j+h_j-n-t)
   S_l(t)   = sum_{n in Z} T(l,n,t),   D(t) = prod_i sin pi(t+sigma+alpha_i) * prod_j sin pi(t-beta_j),
   Xi_l(t)  = D(t) S_l(t)  = sum_{|k|<=r-1} c_k^(l) e^{2 pi i k t}   (per spin; 2r sines, S_l -> 0),
   spin sum c_k = sum_l d_l(d') c_k^(l),  d_l(d') multiplicities of dimension d' (generating fn (1+z)(1-z)^{1-d'}).
The R kernel of <t^2 R_tau>_d is sigma=q, left (0,q),(0,q),(0,tau), right (0,q),(0,q),(q-tau,tau), d'=4q
(times the constant Gamma(2q)^2, irrelevant here).

Per spin: direct sum over -N_L <= n < N_R (term recurrence started from Gamma values at n=0), plus the two tails in
reflected form (one Gamma-ratio sequence each), summed with a centred 1/m expansion (Bernoulli polynomials) and
Hurwitz zeta values from Euler-Maclaurin (complex s; mpmath.zeta(s,a) is not used).
Spin sum: partial sums P_L of d_l c_top^(l), extrapolated with the exponents of PROOF.md section 5:
   P_L = P_inf + sum_k [u_k L^{d'-1-G-k} + w_k L^{d'-2G-k}],  G = sum_i g_i (= sum_j h_j).
usage:  perspin_topmode.py CASE [Lmax] [dps] [out.json]
"""
import sys, json, time
import mpmath as mp

# ----------------------------------------------------------------------------------------- cases
def cases():
    c = {}
    def R(dname, taus, dmult=None, right=None, label=None):
        d = mp.mpf(dname); q = d / 4; tau = mp.mpmathify(taus)
        rt = right(q, tau) if right else [(0, q), (0, q), (q - tau, tau)]
        return dict(label=label or 'R kernel d=%s tau=%s' % (dname, taus), d=d, dmult=mp.mpf(dmult) if dmult else d,
                    sigma=q, left=[(0, q), (0, q), (0, tau)], right=rt, balanced=(dmult is None and right is None))
    # R kernel, inside the absolute-convergence region Re tau > max(0, 2q-1, 1/2-2q)
    c['R1'] = R('1.7', '0.55+0.3j')
    c['R2'] = R('3.3', '1.6-0.4j')
    c['R3'] = R('0.5', '0.9+0.2j')          # d < 4/7: residue strip Sigma_q is empty, top-mode statement still applies
    c['R4'] = R('2.6', '2.0+0.5j')          # Re tau > 3q/2 (beyond the residue strip)
    c['R5'] = R('1.25', '0.7')              # real tau
    # controls (expected nonzero)
    c['C1'] = R('1.7', '0.55+0.3j', right=lambda q, tau: [(mp.mpf('0.15'), q), (-mp.mpf('0.15'), q), (q - tau, tau)],
                label='control C1: right shifts (+0.15,-0.15,q-tau): total balance kept, per-factor balance broken')
    c['C2'] = R('1.7', '0.55+0.3j', dmult='1.9', label='control C2: R kernel at d=1.7 with multiplicities of d\'=1.9')
    c['C3'] = R('1.7', '0.55+0.3j', right=lambda q, tau: [(0, q), (0, q), (q - tau + mp.mpf('0.1'), tau)],
                label='control C3: third right shift q-tau+0.1')
    # generic mixed balanced kernels (Lemma G beyond the R family)
    d = mp.mpf('2.2'); sig = mp.mpf('0.37')
    left = [(mp.mpf('0.11'), mp.mpf('0.48')), (mp.mpf('-0.23'), mp.mpc('0.61', '0.17')), (mp.mpf('0.05'), mp.mpf('0.4'))]
    c['G1'] = dict(label='G1: random mixed balanced r=3, d=2.2', d=d, dmult=d, sigma=sig, left=left,
                   right=[(d / 2 - sig - a - g, g) for a, g in left], balanced=True)
    d = mp.mpf('1.3'); sig = mp.mpf('0.2')
    left = [(mp.mpf('0'), mp.mpf('0.3')), (mp.mpf('0.1'), mp.mpf('0.45')), (mp.mpf('-0.05'), mp.mpc('0.35', '0.1')),
            (mp.mpf('0.2'), mp.mpf('0.25'))]
    c['G2'] = dict(label='G2: random mixed balanced r=4, d=1.3', d=d, dmult=d, sigma=sig, left=left,
                   right=[(d / 2 - sig - a - g, g) for a, g in left], balanced=True)
    return c


# ----------------------------------------------------------------------------------------- numerics
_BN = {}
def bern_numbers(n):
    if n not in _BN:
        _BN[n] = [mp.bernoulli(k) for k in range(n + 1)]
    return _BN[n]


_BIN = {}
def bernpoly_list(nmax, x):
    """[B_0(x), ..., B_nmax(x)],  B_n(x) = sum_k C(n,k) B_k x^{n-k} (Horner in x)"""
    B = bern_numbers(nmax)
    if nmax not in _BIN:
        _BIN[nmax] = [[mp.mpf(mp.binomial(n, k)) * B[k] for k in range(n + 1)] for n in range(nmax + 1)]
    tab = _BIN[nmax]
    out = []
    for n in range(nmax + 1):
        acc = 0
        for coef in tab[n]:
            acc = acc * x + coef
        out.append(acc)
    return out


def hurwitz(s, a, J=24):
    """zeta(s,a) for Re(a) large (a >= ~40), complex s, Euler-Maclaurin with N=0"""
    B = bern_numbers(2 * J)
    res = a ** (1 - s) / (s - 1) + a ** (-s) / 2
    poch = s                      # (s)_{2j-1}
    apow = a ** (-s - 1)          # a^{-s-2j+1}
    a2 = a * a
    for j in range(1, J + 1):
        term = B[2 * j] / mp.factorial(2 * j) * poch * apow
        res += term
        if abs(term) < abs(res) * mp.mpf(10) ** (-mp.mp.dps - 3):
            break
        poch *= (s + 2 * j - 1) * (s + 2 * j)
        apow /= a2
    return res


def tail_sum(ab_pairs, M, c, K):
    """sum_{m>=M} prod_k Gamma(m+a_k)/Gamma(m+b_k), expanded in 1/(m+c); ab_pairs = [(a_k, b_k)]"""
    s = mp.fsum(b - a for a, b in ab_pairs)
    clog = [mp.mpf(0)] * (K + 1)
    for a, b in ab_pairs:
        Ba = bernpoly_list(K + 1, a - c); Bb = bernpoly_list(K + 1, b - c)
        for j in range(1, K + 1):
            clog[j] += (-1) ** (j + 1) * (Ba[j + 1] - Bb[j + 1]) / (j * (j + 1))
    e = [mp.mpf(1)] + [0] * K
    for k in range(1, K + 1):
        e[k] = mp.fsum(j * clog[j] * e[k - j] for j in range(1, k + 1)) / k
    return mp.fsum(e[j] * hurwitz(s + j, M + c) for j in range(K + 1))


def mults(dm, L):
    q = dm / 4
    d = [mp.mpf(1)]
    c = 4 * q
    for k in range(L):
        d.append(c)
        c = c * (2 * q + 1 + k) * (4 * q - 1 + k) / ((2 * q + k) * (2 + k))
    return d


def S_spin(case, l, t, K=30):
    sig, left, right = case['sigma'], case['left'], case['right']
    A = [l + sig + al + t for al, g in left]
    G, rG = mp.gamma, mp.rgamma
    T0 = mp.mpf(1)
    for (al, g), a in zip(left, A):
        T0 *= G(a) * rG(a + g)
    for be, h in right:
        T0 *= G(be - t) * rG(be + h - t)
    NR = 3 * l + 60
    NL = 4 * l + 60
    # upward n = 0 .. NR-1
    tot = [T0]
    T = T0
    for n in range(0, NR - 1):
        fac = 1
        for (al, g), a in zip(left, A):
            fac *= (a + n) / (a + g + n)
        for be, h in right:
            fac *= (be + h - n - 1 - t) / (be - n - 1 - t)
        T *= fac
        tot.append(T)
    T_up_next = T
    fac = 1
    n = NR - 1
    for (al, g), a in zip(left, A):
        fac *= (a + n) / (a + g + n)
    for be, h in right:
        fac *= (be + h - n - 1 - t) / (be - n - 1 - t)
    T_NR_rec = T * fac                      # term at n = NR from the recurrence (consistency check)
    # downward n = -1 .. -NL
    T = T0
    for n in range(0, -NL, -1):
        fac = 1
        for (al, g), a in zip(left, A):
            fac *= (a + g + n - 1) / (a + n - 1)
        for be, h in right:
            fac *= (be - n - t) / (be + h - n - t)
        T *= fac
        tot.append(T)
    direct = mp.fsum(tot)
    # right tail n >= NR: T = TR * prod Gamma(n+A_i)/Gamma(n+A_i+g_i) * prod Gamma(n+B_j)/Gamma(n+B_j+h_j)
    TR = 1
    for be, h in right:
        TR *= mp.sin(mp.pi * (be + h - t)) / mp.sin(mp.pi * (be - t))
    pairs = [(a, a + g) for (al, g), a in zip(left, A)] + [(1 - be - h + t, 1 - be + t) for be, h in right]
    T_NR_refl = TR
    for a, b in pairs:
        T_NR_refl *= G(NR + a) * rG(NR + b)
    rtail = TR * tail_sum(pairs, NR, mp.mpf(l) / 2, K)
    # left tail n = -m, m >= NL+1
    TL = 1
    for al, g in left:
        TL *= mp.sin(mp.pi * (sig + al + g + t)) / mp.sin(mp.pi * (sig + al + t))
    pairsL = [(1 - l - sig - al - g - t, 1 - l - sig - al - t) for al, g in left] + [(be - t, be + h - t) for be, h in right]
    ltail = TL * tail_sum(pairsL, NL + 1, -mp.mpf(l) / 2, K)
    # left-tail consistency: term at n = -NL-1 from the recurrence vs reflected form (m = NL+1)
    n = -NL
    fac = 1
    for (al, g), a in zip(left, A):
        fac *= (a + g + n - 1) / (a + n - 1)
    for be, h in right:
        fac *= (be - n - t) / (be + h - n - t)
    T_L_rec = T * fac
    T_L_refl = TL
    for a, b in pairsL:
        T_L_refl *= G(NL + 1 + a) * rG(NL + 1 + b)
    chk = max(abs(T_NR_rec / T_NR_refl - 1), abs(T_L_rec / T_L_refl - 1))
    return direct + rtail + ltail, chk


def Dfac(case, t):
    D = 1
    for al, g in case['left']:
        D *= mp.sin(mp.pi * (t + case['sigma'] + al))
    for be, h in case['right']:
        D *= mp.sin(mp.pi * (t - be))
    return D


def modes_spin(case, l, nodes, K=30):
    r = len(case['left'])
    N = len(nodes)
    xs = []
    chk = 0
    for t in nodes:
        S, c = S_spin(case, l, t, K)
        chk = max(chk, c)
        xs.append(Dfac(case, t) * S)
    cs = {k: mp.fsum(x * mp.expj(-2 * mp.pi * k * t) for x, t in zip(xs, nodes)) / N for k in range(-(r - 1), r)}
    return cs, chk


def extrapolate(P, exps, Lmin, Lmax, nterm, npts=None):
    """least squares P_L = P_inf + sum_{j<nterm} c_j L^{exps[j]} on geometric L in [Lmin, Lmax]"""
    npts = npts or 2 * nterm + 6
    Ls = sorted(set(int(mp.nint(Lmin * (mp.mpf(Lmax) / Lmin) ** (mp.mpf(i) / (npts - 1)))) for i in range(npts)))
    with mp.workdps(mp.mp.dps + 20):
        A = mp.matrix(len(Ls), nterm + 1); b = mp.matrix(len(Ls), 1)
        for i, L in enumerate(Ls):
            A[i, 0] = 1
            for j in range(nterm):
                A[i, j + 1] = mp.power(L, exps[j])
            b[i] = P[L]
        x, res = mp.qr_solve(A, b)
    return x[0]


def run(name, Lmax=200, dps=40, out=None):
    mp.mp.dps = dps
    case = cases()[name]
    r = len(case['left'])
    N = 2 * r - 1
    t0 = mp.mpf('0.0731')
    nodes = [t0 + mp.mpf(j) / N for j in range(N)]
    dl = mults(case['dmult'], Lmax + 2)
    top = r - 1
    st = time.time()
    per = []
    P = {k: [] for k in range(-top, top + 1)}
    acc = {k: mp.mpf(0) for k in range(-top, top + 1)}
    maxchk = 0
    for l in range(Lmax + 1):
        cs, chk = modes_spin(case, l, nodes)
        maxchk = max(maxchk, chk)
        for k in cs:
            acc[k] += dl[l] * cs[k]
            P[k].append(acc[k])
        per.append({k: cs[k] for k in (-top, top)})
    # per-spin finite-mode check at an off-grid node for two spins
    fm = []
    for l in (0, 5):
        cs, _ = modes_spin(case, l, nodes)
        tx = mp.mpf('0.3917')
        S, _ = S_spin(case, l, tx)
        x = Dfac(case, tx) * S
        pred = mp.fsum(cs[k] * mp.expj(2 * mp.pi * k * tx) for k in cs)
        fm.append(mp.nstr(abs(pred / x - 1), 3))
    Gs = mp.fsum(g for a, g in case['left'])
    dm = case['dmult']
    exps = []
    for k in range(40):
        exps += [dm - 1 - Gs - k, dm - 2 * Gs - k]
    exps = sorted(exps, key=lambda e: -mp.re(e))
    res = dict(case=name, label=case['label'], d=str(case['d']), d_mult=str(dm), sigma=mp.nstr(case['sigma'], 10),
               left=[[mp.nstr(a, 10), mp.nstr(g, 10)] for a, g in case['left']],
               right=[[mp.nstr(b, 10), mp.nstr(h, 10)] for b, h in case['right']],
               per_factor_balance_vs_dmult=[mp.nstr(case['sigma'] + a + b - case['dmult'] / 2 + g, 5) for (a, g), (b, h) in zip(case['left'], case['right'])],
               G=mp.nstr(Gs, 10), Lmax=Lmax, dps=dps, nodes=[mp.nstr(t, 6) for t in nodes],
               tail_consistency_max=mp.nstr(maxchk, 3), perspin_finite_mode_check=fm,
               perspin_top=[{'l': l, 'd_l': mp.nstr(dl[l], 8), 'c_-top': mp.nstr(per[l][-top], 12), 'c_+top': mp.nstr(per[l][top], 12)}
                            for l in (0, 1, 2, 5, 10, 20, 50, 100, 200) if l <= Lmax],
               partial_sums_at_Lmax={str(k): mp.nstr(P[k][Lmax], 15) for k in P})
    ext = {}
    for k in sorted(P):
        vals = []
        for nterm, Lmin in ((8, Lmax // 8), (10, Lmax // 8), (12, Lmax // 8), (12, Lmax // 6), (14, Lmax // 8), (16, Lmax // 10)):
            vals.append(extrapolate(P[k], exps, Lmin, Lmax, nterm))
        best = vals[-2]
        spread = max(abs(v - best) for v in vals[2:])
        ext[str(k)] = dict(value=mp.nstr(best, 15), abs=mp.nstr(abs(best), 4), fit_spread=mp.nstr(spread, 3),
                           all=[mp.nstr(v, 12) for v in vals])
    scale = max(abs(mp.mpmathify(ext[str(k)]['value'])) for k in P if abs(k) < top)
    res['spin_summed_all_modes'] = ext
    res['spin_summed_top'] = {str(k): ext[str(k)] for k in (-top, top)}
    res['scale_max_|c_k|_lower_modes'] = mp.nstr(scale, 6)
    res['relative_top'] = {str(k): mp.nstr(abs(mp.mpmathify(ext[str(k)]['value'])) / scale, 3) for k in (-top, top)}
    res['perspin_top_all'] = {str(k): [mp.nstr(per[l][k], 20) for l in range(Lmax + 1)] for k in (-top, top)}
    res['d_l'] = [mp.nstr(dl[l], 20) for l in range(Lmax + 1)]
    res['seconds'] = round(time.time() - st, 1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('perspin_top_all', 'd_l')}, indent=1), flush=True)
    if out:
        json.dump(res, open(out, 'w'), indent=1)
    return res


if __name__ == '__main__':
    a = sys.argv[1:]
    run(a[0], int(a[1]) if len(a) > 1 else 200, int(a[2]) if len(a) > 2 else 40, a[3] if len(a) > 3 else None)
