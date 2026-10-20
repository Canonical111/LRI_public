#!/usr/bin/env python3
"""Two-kink raw atoms needed for C8: exact eps-expansions of Z2_<der>, Q2_<der> (all rational) and of the
endpoint-source atoms EZ2_<der>, EQ2_<der> (rational except the [eps^0 l^0] constant, which is a 1D integral
evaluated to 80 digits and identified by PSLQ in the MZV basis of the right weight; the identification is
re-verified at 100 digits).

ARCHIVE-FREE.  Written from the definitions (note Secs. 4-5):
  Z2 = int_eps^1 dr (1-r) W2,   Q2 = int_eps^1 dr (1-r) r W2,   W2 = exp[-2 v f_delta(r)]
  E M2 (first source derivative, reflected form e = 2 sum_i q_i f_delta(X_i); equal to the unreflected U^even form,
  shown in the docstring of out/C8/two_kink_exact_C8.json): integrating X1 = x in [0, 1-r] exactly gives
     int_0^{1-r} e_j dx = 2 [F_j(1-r) - F_j(1) + F_j(r)],   F_j(y) = int_0^y log^{j+1}(x)/(j+1) dx,
  where e_j = d_delta^j e at delta = 0.  d_delta acts on BOTH the kernel and the source:
     E M2_<a,b> = int_eps^1 dr r^-2 [r for Q] sum_j binom(b,j) ins_{a,b-j}(log r) 2[F_j(1-r) - F_j(1) + F_j(r)].
  ins_{a,b} = d_v^a d_delta^b W2/W2 at (1,0) is derived from the exponent (same generator as scripts/two_kink_exact.py).
The 18 phase-1 Z2/Q2 atoms are regenerated and must equal ../out/two_kink_exact.json; EQ2_base, EZ2_base must
reproduce the phase-1 targets EQ2.0.l0 = -2 z2, EZ2.0 = -l^2 + 2 l + 2 z2 - 2.

Output: ../out/C8/two_kink_exact_C8.json
"""
import json, time
from fractions import Fraction
from math import comb, factorial
from pathlib import Path
import sympy as s
import mpmath as mp

SPEC = Path(__file__).resolve().parent.parent
OUT = SPEC / 'out' / 'C8'
t0 = time.time()
w, dl, L, T = s.symbols('w dl L T')       # v = 1 + w ; L = log r ; T = log(1-r)
r = s.Symbol('r', positive=True)


def insertion(a, b):
    """d_v^a d_delta^b W2 / W2 at (1,0) as a polynomial in L = log r (q1 q2 = -1)."""
    order = a + b + 1
    f = sum(dl**k * L**(k + 1) / s.factorial(k + 1) for k in range(order + 1))
    X = -2 * (1 + w) * f
    Y = s.expand(X - X.subs({w: 0, dl: 0}))
    ex = s.expand(sum(Y**n / s.factorial(n) for n in range(a + b + 1)))
    return s.expand(s.Poly(ex, w, dl).coeff_monomial(w**a * dl**b) * s.factorial(a) * s.factorial(b))


def tag(a, b):
    return 'base' if (a, b) == (0, 0) else 'v' * a + 'd' * b


def int_rn_logj(n, j):
    """int_eps^1 r^n log^j r dr -> {(p,k): Fraction} (l = log eps)"""
    out = {}
    def add(p, k, c):
        if c:
            out[(p, k)] = out.get((p, k), Fraction(0)) + c
    if n == -1:
        add(0, j + 1, Fraction(-1, j + 1))
        return out
    m = n + 1
    add(0, 0, Fraction((-1)**j * factorial(j), m**(j + 1)))
    for i in range(j + 1):
        add(m, j - i, -Fraction((-1)**i * factorial(j), factorial(j - i) * m**(i + 1)))
    return out


def zq_expansion(name, a, b):
    ins = s.Poly(insertion(a, b), L)
    weight = {-2: Fraction(1), -1: Fraction(-1)} if name == 'Z2' else {-1: Fraction(1), 0: Fraction(-1)}
    tot = {}
    for (jj,), cL in ins.terms():
        for n, cw in weight.items():
            for key, c in int_rn_logj(n, jj).items():
                tot[key] = tot.get(key, Fraction(0)) + Fraction(int(cL.p), int(cL.q)) * cw * c
    return {k: v for k, v in tot.items() if v != 0}


def F_poly(j, y_log):
    """F_j(y)/y as polynomial in log y:  (1/(j+1)) sum_i (-1)^i (j+1)!/(j+1-i)! log^{j+1-i} y"""
    n = j + 1
    return sum(s.Rational((-1)**i * factorial(n), factorial(n - i)) * y_log**(n - i) for i in range(n + 1)) / n


def endpoint_integrand(name, a, b):
    """E M2_<a,b> integrand in r as sympy expression in L = log r, T = log(1-r), r"""
    tot = 0
    for j in range(b + 1):
        Fj1 = s.Integer((-1)**(j + 1) * factorial(j))            # F_j(1)
        G = 2 * ((1 - r) * F_poly(j, T) - Fj1 + r * F_poly(j, L))
        tot += comb(b, j) * insertion(a, b - j) * G
    pref = r**-2 if name == 'EZ2' else r**-1
    return s.expand(pref * tot)


NMAX = 4          # eps^p up to p = 3 (needed: p <= 2)


def endpoint_expansion2(name, a, b):
    """robust version of the small-r expansion: multiply by r^2, expand as polynomial in (r, L)"""
    K = endpoint_integrand(name, a, b)
    Tser = -sum(r**m / m for m in range(1, NMAX + 4))
    P = s.Poly(s.expand(K.subs(T, Tser) * r**2), r, L)
    kappa = {}
    for (n2, k), c in P.terms():
        n = n2 - 2
        if n <= NMAX:
            kappa[(n, k)] = kappa.get((n, k), 0) + s.Rational(c)
    assert all(n >= -1 for (n, k), c in kappa.items() if c != 0), 'unexpected r^-2 term'
    return K, kappa


def mzv_basis(wmax):
    z = {k: mp.zeta(k) for k in range(2, 8)}
    B = [('1', mp.mpf(1)), ('z2', z[2]), ('z3', z[3]), ('z4', z[4]), ('z5', z[5]), ('z2*z3', z[2] * z[3]),
         ('z6', z[6]), ('z3^2', z[3]**2), ('z7', z[7]), ('z2*z5', z[2] * z[5]), ('z3*z4', z[3] * z[4])]
    wt = {'1': 0, 'z2': 2, 'z3': 3, 'z4': 4, 'z5': 5, 'z2*z3': 5, 'z6': 6, 'z3^2': 6, 'z7': 7, 'z2*z5': 7, 'z3*z4': 7}
    return [x for x in B if wt[x[0]] <= wmax]


def constant(name, a, b, kappa, K, dps):
    """[eps^0 l^0] = int_0^1 (K - sum_k kappa_{-1,k} L^k / r) dr  (mpmath tanh-sinh, adaptive working precision)"""
    sing = sum(c * L**k for (n, k), c in kappa.items() if n == -1) / r
    f = s.lambdify((r, L, T), s.expand(K - sing).subs({}), 'mpmath')
    def g(x):
        extra = int(max(0, -2 * mp.log10(x))) + 20 if x < 0.5 else int(max(0, -mp.log10(1 - x))) + 20
        with mp.workdps(dps + extra):
            x = mp.mpf(x)
            return f(x, mp.log(x), mp.log1p(-x))
    with mp.workdps(dps):
        return mp.quad(g, [0, mp.mpf(1) / 8, mp.mpf(1) / 2, mp.mpf(7) / 8, 1])


def main():
    mp.mp.dps = 110          # global precision for the basis constants (quadratures set their own working precision)
    req = json.load(open(OUT / 'raw_requirements_C8.json'))
    needed = sorted({a for key in ('total_tight', 'total_safe') for a in req[key] if a.split('_')[0] in ('Z2', 'Q2', 'EZ2', 'EQ2')})
    DV = {}
    for a_ in needed:
        der = a_.split('_', 1)[1]
        DV[a_] = (0, 0) if der == 'base' else (der.count('v'), der.count('d'))
    res = {'note': 'ARCHIVE-FREE expansions [eps^p l^k] (l = log eps) of the two-kink raw atoms needed for C8 at (v,delta)=(1,0). '
                   'Z2_*, Q2_*: exact rationals, complete (every unlisted coefficient is exactly zero). EZ2_*, EQ2_*: all listed '
                   'coefficients exact rationals except [eps^0 l^0] (key "0" -> "0"), which is given as an exact MZV expression '
                   '(PSLQ at 80 digits, re-verified at 100 digits) and as a 60-digit decimal; listed eps powers 0..5, all log powers; '
                   'unlisted coefficients with p <= 5 are exactly zero (in particular every eps^-1 coefficient). Generated by scripts/two_kink_exact_C8.py.',
           'reflection': 'E M2 uses e = 2 sum q_i f_delta(X_i); the unreflected U^even factor sum q_i[f(X_i) - f(1-X_i)] gives, after '
                         'the X1 integral, the same 2[F(1-r) - F(1) + F(r)] (substitution x -> 1-r-x), also for every d_delta^j.',
           'atoms': {}, 'constants': {}, 'checks': {}}
    for atom in needed:
        name = atom.split('_')[0]
        a, b = DV[atom]
        if name in ('Z2', 'Q2'):
            co = zq_expansion(name, a, b)
            res['atoms'][atom] = {str(p): {str(k): str(co[(p, k)]) for k in sorted(k_ for (p_, k_) in co if p_ == p)}
                                  for p in sorted({p_ for (p_, _) in co})}
            continue
        K, kappa = endpoint_expansion2(name, a, b)
        co = {}
        for (n, k), c in kappa.items():
            if c == 0:
                continue
            if n == -1:                      # int_eps^1 r^-1 L^k = -l^{k+1}/(k+1)
                co[(0, k + 1)] = co.get((0, k + 1), 0) - c / (k + 1)
            else:                            # - int_0^eps r^n L^k
                m = n + 1
                for i in range(k + 1):
                    co[(m, k - i)] = co.get((m, k - i), 0) - c * s.Rational((-1)**i * factorial(k), factorial(k - i) * m**(i + 1))
        cval = constant(name, a, b, kappa, K, 80)
        wmax = a + 2 * b + 2
        basis = mzv_basis(wmax)
        with mp.workdps(80):
            basis = mzv_basis(wmax)
            rel = mp.pslq([cval] + [x[1] for x in basis], maxcoeff=10**9, maxsteps=10**6, tol=mp.mpf(10)**-70)
        assert rel is not None and rel[0] != 0, (atom, 'PSLQ failed')
        expr = sum(s.Rational(-ri, rel[0]) * s.Symbol(bn.replace('^2', '**2').replace('*', '_')) for ri, (bn, _) in zip(rel[1:], basis))
        expr_str = ' + '.join(f'({s.Rational(-ri, rel[0])})*{bn}' for ri, (bn, _) in zip(rel[1:], basis) if ri) or '0'
        # re-verify at 100 digits
        c100 = constant(name, a, b, kappa, K, 100)
        with mp.workdps(100):
            ev = sum(mp.mpf(-ri) / rel[0] * bv for ri, (bn, bv) in zip(rel[1:], mzv_basis(wmax)))
            resid = c100 - ev
        assert abs(resid) < mp.mpf(10)**-90, (atom, resid)
        co[(0, 0)] = 'CONST'
        res['atoms'][atom] = {}
        for (p, k) in sorted(co):
            if co[(p, k)] == 0:
                continue
            res['atoms'][atom].setdefault(str(p), {})[str(k)] = (str(co[(p, k)]) if co[(p, k)] != 'CONST'
                                                               else mp.nstr(c100, 60))
        res['constants'][atom] = {'eps0_l0_exact': expr_str, 'eps0_l0_decimal_60': mp.nstr(c100, 60),
                                  'pslq_dps': 80, 'verified_dps': 100, 'residual_at_100_digits': mp.nstr(resid, 3),
                                  'max_weight': wmax}
        print(atom, 'const =', expr_str, ' resid', mp.nstr(resid, 3), round(time.time() - t0, 1), 's', flush=True)
    # regression against phase 1
    old = json.load(open(SPEC / 'out' / 'two_kink_exact.json'))['atoms']
    res['checks']['phase1_Z2_Q2_atoms_identical'] = all(res['atoms'][k_] == v_ for k_, v_ in old.items() if k_ in res['atoms'])
    assert res['checks']['phase1_Z2_Q2_atoms_identical']
    ez = res['constants']['EZ2_base']['eps0_l0_exact'].replace(' ', '')
    eq = res['constants']['EQ2_base']['eps0_l0_exact'].replace(' ', '')
    res['checks']['EQ2_base_eps0_l0 = -2 z2 (phase-1 target EQ2.0.l0)'] = eq == '(-2)*z2'
    res['checks']['EZ2_base_eps0 = -l^2 + 2 l + 2 z2 - 2 (phase-1 targets EZ2.0.l*)'] = (
        ez == '(-2)*1+(2)*z2' and res['atoms']['EZ2_base']['0'].get('2') == '-1' and res['atoms']['EZ2_base']['0'].get('1') == '2')
    assert all(res['checks'].values()), res['checks']
    # supports: Z2 in {-1,0}, Q2 in {0,1}; EZ2, EQ2 have no negative powers (tight bound eps^0)
    for atom, dd in res['atoms'].items():
        sup = {int(p) for p in dd}
        nm = atom.split('_')[0]
        assert sup <= {'Z2': {-1, 0}, 'Q2': {0, 1}}.get(nm, set(range(0, NMAX + 2))), (atom, sup)
    res['checks']['supports'] = 'Z2 in {-1,0}, Q2 in {0,1}; EZ2, EQ2 start at eps^0 (no eps^-1: the below-tight-bound safe extras vanish)'
    json.dump(res, open(OUT / 'two_kink_exact_C8.json', 'w'), indent=1)
    print('atoms', len(res['atoms']), 'checks', res['checks'], round(time.time() - t0, 1), 's')


if __name__ == '__main__':
    main()
