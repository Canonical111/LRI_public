#!/usr/bin/env python3
"""RG (Callan-Symanzik) higher-log predictions for the normalized responses, at general (v, delta), derived here.

ARCHIVE-FREE.  Derivation (written out in out/C8/rg_logs_C8.json -> derivation):
  * Auxiliary responses at h = 0 (framework.md Sec. 1, note Secs. 4-5):
        F_G = sum_{n odd} g^n C_n(v,delta;l),            d_h F_G = sqrt2 b0 sum_n g^n [-2n f_d(l) C_n - 2 d_v C_n + E C_n],
        F_H = sqrt2 b0 sum_{n even} g^n K_n(v,delta;l),   d_h F_H = 1 - 2 sum g^n K_n + 2v sum g^n [-2n f_d(l) K_n - 2 d_v K_n + E K_n],
    f_d(l) = (e^{delta l} - 1)/delta (normal-ordering factor N(h)^n), v = b0^2, C_1 = A_1 = 1, E C_1 = j1 = -2/(1+delta).
  * Essential couplings in cutoff units (note eq:matching): Y = g exp[l - v f_d(l)], v_B = (b0 - sqrt2 h)^2 e^{delta l}.
    Their flow is autonomous: beta_u = 2uF(u,z), beta_z = (1+z)H(u,z) with F = z + sum_k b_{2k+1}(v_B,delta) u^k,
    H = -delta - 4 sum_k h_{2k}(v_B,delta) u^k (h2 = -1).  The auxiliary beta along h = 0 at scale l is therefore
        beta^g(l) = g sum_{k>=1} b_{2k+1}(V(l),delta) u(l)^k,   beta^h(l) = sqrt2 b0 sum_{k>=1} h_{2k}(V(l),delta) u(l)^k,
        V(l) = v e^{delta l},  u(l) = g^2 exp[2l - 2v f_d(l)]   (= the nonautonomous auxiliary flow of the note's checks).
  * The renormalized responses are l-independent, so d_l F = beta(l) . grad F at fixed bare (g, h=0):
        d_l C_n = sum_{m+2k=n} b_{2k+1}(V,d) e_k(l) m C_m + 2v sum_{m+2k=n} h_{2k}(V,d) e_k(l) [-2m f_d C_m - 2 d_v C_m + E C_m]
        d_l K_n = sum_{m+2k=n} b_{2k+1} e_k m K_m + h_n(V,d) e_{n/2} + sum_{m+2k=n} h_{2k} e_k [-2K_m + 2v(-2m f_d K_m - 2 d_v K_m + E K_m)]
    with e_k(l) = exp[2k(l - v f_d(l))].  Only FIRST source derivatives enter (beta^h multiplies d_h F at h = 0).
  * [l^0] of this identity is the finite-response recurrence J0 beta = R1 (b3..b9, h4..h8): checked here symbolically for
    every jet the C8 inputs use (independent of derive_requirements_C8.py).  [l^k], k >= 1, predicts [l^(k+1)] of every jet
    of an order-n response from lower-order data (all log powers <= k, incl. d_v and E jets) and the beta inputs.
  * At (v,delta) = (1,0) it reduces to the assembly's second-log formula (assembly/README.md).
Validations (all archive-free): note higher logs of C3, d_v C3, d_delta C3, K4 (l.550-552, 2231-2264) exactly;
three-kink log polynomials of review/three_kink_independent.json (independent numerics, all 9 jets, all logs).
Outputs: ../out/C8/rg_logs_C8.json  (closed-form predictions for the C3/K4 jets incl. W, L3, M21, M12; formulas for the
         second log of every other C8 jet in terms of normalized atoms and beta inputs, and the raw scalars they need)
"""
import json, time, itertools
from math import factorial
from pathlib import Path
import sympy as s
import mpmath as mp

SPEC = Path(__file__).resolve().parent.parent
OUT = SPEC / 'out' / 'C8'
t0 = time.time()
R_ = s.Rational

# ------------------------------------------------------------------------- truncated series in (w, d, l)
class Ser:
    __slots__ = ('c', 'I', 'J', 'K')
    def __init__(self, c, I, J, K):
        self.c = {k_: v_ for k_, v_ in c.items() if k_[0] <= I and k_[1] <= J and k_[2] <= K and v_ != 0}
        self.I, self.J, self.K = I, J, K
    @staticmethod
    def const(x, I, J, K):
        return Ser({(0, 0, 0): s.sympify(x)}, I, J, K)
    def __add__(self, o):
        if not isinstance(o, Ser):
            o = Ser.const(o, self.I, self.J, self.K)
        c = dict(self.c)
        for k_, v_ in o.c.items():
            c[k_] = c.get(k_, 0) + v_
        return Ser(c, self.I, self.J, self.K)
    __radd__ = __add__
    def __neg__(self):
        return Ser({k_: -v_ for k_, v_ in self.c.items()}, self.I, self.J, self.K)
    def __sub__(self, o):
        return self + (-o)
    def __mul__(self, o):
        if not isinstance(o, Ser):
            o = s.sympify(o)
            return Ser({k_: v_ * o for k_, v_ in self.c.items()}, self.I, self.J, self.K)
        c = {}
        for (a1, b1, c1), x in self.c.items():
            for (a2, b2, c2), y in o.c.items():
                key = (a1 + a2, b1 + b2, c1 + c2)
                if key[0] <= self.I and key[1] <= self.J and key[2] <= self.K:
                    c[key] = c.get(key, 0) + x * y
        return Ser(c, self.I, self.J, self.K)
    __rmul__ = __mul__
    def dw(self):                       # d/dw (w = v - 1)
        return Ser({(a - 1, b, k): a * x for (a, b, k), x in self.c.items() if a > 0}, self.I, self.J, self.K)
    def expand(self):
        return Ser({k_: s.expand(v_) for k_, v_ in self.c.items()}, self.I, self.J, self.K)


def ser_exp(x):
    """exp of a series with zero constant term"""
    assert x.c.get((0, 0, 0), 0) == 0
    res = Ser.const(1, x.I, x.J, x.K)
    term = Ser.const(1, x.I, x.J, x.K)
    for n in range(1, x.I + x.J + x.K + 2):
        term = (term * x).expand() * R_(1, n)
        if not term.c:
            break
        res = res + term
    return res.expand()


def build_env(I, J, K):
    w = Ser({(1, 0, 0): 1}, I, J, K)
    dlt = Ser({(0, 1, 0): 1}, I, J, K)
    ell = Ser({(0, 0, 1): 1}, I, J, K)
    fd = Ser({(0, i - 1, i): R_(1, factorial(i)) for i in range(1, J + 2)}, I, J, K)       # (e^{d l}-1)/d
    vfac = Ser.const(1, I, J, K) + w
    Vm1 = (vfac * ser_exp(Ser({(0, 1, 1): 1}, I, J, K)) - 1).expand()          # V(l) - 1 = v e^{delta l} - 1
    return w, dlt, ell, fd, vfac, Vm1


# ------------------------------------------------------------------------- data symbols
def sym(name, k, i, j):
    return s.Symbol(f'{name}_{k}[v{i}d{j}]')


def response_series(name, I, J, K, exact=None):
    """sum_{i,j,k} X_k[vidj] w^i d^j l^k / (i! j!)  (full-derivative atoms); C1 = 1, EC1 = -2/(1+d) exactly"""
    if name == 'C1':
        return Ser.const(1, I, J, K)
    if name == 'EC1':
        return Ser({(0, j, 0): -2 * (-1)**j for j in range(J + 1)}, I, J, K)
    c = {}
    for i in range(I + 1):
        for j in range(J + 1):
            for k in range(K + 1):
                x = exact(name, k, i, j) if exact else None
                c[(i, j, k)] = (x if x is not None else sym(name, k, i, j)) * R_(1, factorial(i) * factorial(j))
    return Ser(c, I, J, K)


BETA_TAYLOR = {   # [w^i d^j] of the beta coefficients in terms of the dictionary inputs (note l.1122-1137)
    'b3': {(0, 0): 1, (1, 0): 'a', (0, 1): 'p', (2, 0): 'A', (1, 1): 'E', (0, 2): 'V', (3, 0): 'alpha', (2, 1): 'beta',
           (1, 2): 'gamma', (0, 3): 'W'},
    'b5': {(0, 0): 'b', (1, 0): 'G', (0, 1): 'R', (2, 0): 'Phi', (1, 1): 'Psi', (0, 2): 'S'},
    'b7': {(0, 0): 'J', (1, 0): 'Omega', (0, 1): 'U'},
    'b9': {(0, 0): 'J9'},
    'h2': {(0, 0): -1},
    'h4': {(0, 0): '-c/4', (1, 0): '-f/4', (0, 1): '-q/4', (2, 0): '-L/4', (1, 1): '-M/4', (0, 2): '-Q/4', (3, 0): '-L3/4',
           (2, 1): '-M21/4', (1, 2): '-M12/4'},
    'h6': {(0, 0): '-k/4', (1, 0): '-N/4', (0, 1): '-P/4', (2, 0): '-N2/4', (1, 1): '-Ndelta/4'},
    'h8': {(0, 0): '-K/4', (1, 0): '-Kv/4'},
}
INPUT_SYMS = {n: s.Symbol(n) for n in 'a p A E V alpha beta gamma W b G R Phi Psi S J Omega U J9 c f q L M Q L3 M21 M12 '
                                       'k N P N2 Ndelta K Kv'.split()}


def beta_series(name, Vm1, dlt, I, J, K):
    """b(V(l), delta) as a series: sum_ij B_ij (V-1)^i delta^j; Taylor coefficients beyond the dictionary are symbols
    X<name>_<i><j> (they must not appear in any prediction that is reported as complete)"""
    h2 = name == 'h2'
    out = Ser.const(0, I, J, K)
    Vp = [Ser.const(1, I, J, K)]
    for _ in range(I + J):              # V - 1 = w + (1+w)(delta l + ...): powers up to I + J survive the truncation
        Vp.append((Vp[-1] * Vm1).expand())
    for i in range(I + J + 1):
        for j in range(J + 1):
            if h2:
                coef = -1 if (i, j) == (0, 0) else 0         # h2 = -1 identically in (v, delta)
            else:
                t_ = BETA_TAYLOR[name].get((i, j))
                coef = s.sympify(t_, locals=INPUT_SYMS) if t_ is not None else s.Symbol(f'X{name}_{i}{j}')
            if coef == 0:
                continue
            dj = Ser({(0, j, 0): 1}, I, J, K)
            out = out + (Vp[i] * dj).expand() * coef
    return out.expand()


def rhs(n, kind, I, J, K, exact=None):
    """RHS of d_l X_n = beta(l) . grad X_n  (X = C for odd n, K for even n), as a truncated series"""
    w, dlt, ell, fd, vfac, Vm1 = build_env(I, J, K)
    tot = Ser.const(0, I, J, K)
    for kk in range(1, n // 2 + 1):
        m = n - 2 * kk
        ek = ser_exp((ell - vfac * fd).expand() * (2 * kk))
        bk = beta_series(f'b{2 * kk + 1}', Vm1, dlt, I, J, K)
        hk = beta_series(f'h{2 * kk}', Vm1, dlt, I, J, K)
        if kind == 'C':
            Xm = response_series(f'C{m}', I + 1, J, K, exact)
            EXm = response_series(f'EC{m}', I, J, K, exact)
        else:
            if m == 0:
                tot = tot + (hk * ek).expand()
                continue
            Xm = response_series(f'K{m}', I + 1, J, K, exact)
            EXm = response_series(f'EK{m}', I, J, K, exact)
        Xm_t = Ser(Xm.c, I, J, K)
        dvX = Xm.dw()
        dvX = Ser(dvX.c, I, J, K)
        inner = (Xm_t * fd).expand() * (-2 * m) - dvX * 2 + EXm
        if kind == 'C':
            tot = tot + (bk * ek * Xm_t).expand() * m + (hk * ek * vfac * inner).expand() * 2
        else:
            tot = tot + (bk * ek * Xm_t).expand() * m + (hk * ek * (Xm_t * (-2) + vfac * inner * 2)).expand()
    return tot.expand()


def predict(n, kind, i, j, k, exact=None):
    """[eps^0 l^k] d_v^i d_delta^j X_n at (1,0) predicted from [l^(k-1)] of the RHS (k >= 1)"""
    S_ = rhs(n, kind, i, j, k - 1, exact)
    return s.expand(s.sympify(S_.c.get((i, j, k - 1), 0)) * s.Rational(factorial(i) * factorial(j), k))


# ------------------------------------------------------------------------- exact two-kink data (K2 = Q2, EK2 = EQ2)
TK = json.load(open(OUT / 'two_kink_exact_C8.json'))
TK1 = json.load(open(SPEC / 'out' / 'two_kink_exact.json'))['atoms']
z2_, z3_, z4_, z5_, z6_, z7_ = s.symbols('z2 z3 z4 z5 z6 z7')
ZLOC = {'z2': z2_, 'z3': z3_, 'z4': z4_, 'z5': z5_, 'z6': z6_, 'z7': z7_}


def tag(i, j):
    return 'base' if (i, j) == (0, 0) else 'v' * i + 'd' * j


def parse_mzv(txt):
    """'(c1)*b1 + (c2)*b2 ...' with b in 1, z2, ..., z2*z3, z3^2 -> sympy"""
    tot = s.Integer(0)
    for term in txt.split(' + '):
        cs, bn = term.split(')*', 1)
        base = s.Integer(1) if bn == '1' else s.Mul(*[ZLOC[x] if '^' not in x else ZLOC[x.split('^')[0]]**int(x.split('^')[1])
                                                       for x in bn.split('*')])
        tot += s.Rational(cs[1:]) * base
    return tot


def exact_two_kink(name, k, i, j):
    """K2 = Q2, EK2 = EQ2 at [eps^0 l^k] (only eps^0 enters normalized two-kink responses: K2 and EK2 have no other factors)"""
    if name not in ('K2', 'EK2'):
        return None
    atom = ('Q2_' if name == 'K2' else 'EQ2_') + tag(i, j)
    if name == 'K2':
        from fractions import Fraction
        tbl = TK['atoms'].get(atom) or TK1.get(atom)
        if tbl is None:                       # generate on the fly (any derivative order)
            import two_kink_exact_C8 as T2
            co = T2.zq_expansion('Q2', i, j)
            return s.Rational(str(co.get((0, k), Fraction(0))))
        return s.Rational(tbl.get('0', {}).get(str(k), '0'))
    tbl = TK['atoms'].get(atom)
    if tbl is None:
        return None
    if k == 0:
        return parse_mzv(TK['constants'][atom]['eps0_l0_exact'])
    return s.Rational(tbl.get('0', {}).get(str(k), '0'))


# ------------------------------------------------------------------------- 1. the recurrence from [l^0]
def recurrence_check(n, kind, i, j):
    """[l^0] of the CS identity: X_{n,1}[vidj] = [w^i d^j l^0] RHS; solve for the top beta coefficient and compare with the
    dictionary/recurrence of derive_requirements_C8 (expansion of the input in normalized atoms)."""
    S_ = rhs(n, kind, i, j, 0)
    return s.expand(S_.c.get((i, j, 0), 0) * factorial(i) * factorial(j))


if __name__ == '__main__':
    mp.mp.dps = 40
    res = {'note': 'ARCHIVE-FREE RG higher-log predictions (scripts/rg_logs_C8.py); see the module docstring for the derivation.',
           'conventions': 'X_k[vidj] = [eps^0 l^k] d_v^i d_delta^j X at (v,delta) = (1,0), full derivatives; X in C3..C9, K2..K8 '
                          '(K2 = Q2), EC3..EC7, EK2..EK6 (EK2 = EQ2); beta inputs as in the dictionary (note l.1122-1137); '
                          'z2..z7 = zeta values.',
           'derivation': __doc__}
    defs = json.load(open(OUT / 'input_definitions_C8.json'))

    # ---- 1. [l^0] = recurrence: for every input that is a single Taylor coefficient of b_n or h_n, the CS identity at l^0,
    #      solved for that input, must equal the expansion of derive_requirements_C8.py
    def sym_expr(sx):
        loc = {}
        def rep(m):
            nm = m.group(0)
            loc_name = 'Y' + str(len(loc))
            loc[loc_name] = s.Symbol(nm)
            return loc_name
        import re
        code = re.sub(r'[A-Z]+\d_\d\[v\dd\d\]', rep, sx)
        return s.expand(s.sympify(code, locals=loc | INPUT_SYMS))
    rec_rows = {}
    TARGETS_REC = {  # input: (n, kind, i, j, Taylor factor relating the derivative jet to the input)
        'a': (3, 'C', 1, 0), 'p': (3, 'C', 0, 1), 'A': (3, 'C', 2, 0), 'E': (3, 'C', 1, 1), 'V': (3, 'C', 0, 2),
        'alpha': (3, 'C', 3, 0), 'beta': (3, 'C', 2, 1), 'gamma': (3, 'C', 1, 2), 'W': (3, 'C', 0, 3),
        'b': (5, 'C', 0, 0), 'G': (5, 'C', 1, 0), 'R': (5, 'C', 0, 1), 'Phi': (5, 'C', 2, 0), 'Psi': (5, 'C', 1, 1), 'S': (5, 'C', 0, 2),
        'J': (7, 'C', 0, 0), 'Omega': (7, 'C', 1, 0), 'U': (7, 'C', 0, 1), 'J9': (9, 'C', 0, 0),
        'c': (4, 'K', 0, 0), 'f': (4, 'K', 1, 0), 'q': (4, 'K', 0, 1), 'L': (4, 'K', 2, 0), 'M': (4, 'K', 1, 1), 'Q': (4, 'K', 0, 2),
        'L3': (4, 'K', 3, 0), 'M21': (4, 'K', 2, 1), 'M12': (4, 'K', 1, 2),
        'k': (6, 'K', 0, 0), 'N': (6, 'K', 1, 0), 'P': (6, 'K', 0, 1), 'N2': (6, 'K', 2, 0), 'Ndelta': (6, 'K', 1, 1),
        'K': (8, 'K', 0, 0), 'Kv': (8, 'K', 1, 0),
    }
    for nm, (n, kind, i, j) in TARGETS_REC.items():
        lhs = sym(f'{kind}{n}', 1, i, j)
        idn = recurrence_check(n, kind, i, j)                  # = X_{n,1}[vidj] predicted
        x = INPUT_SYMS[nm]
        sol = s.solve(s.Eq(lhs, idn), x)
        assert len(sol) == 1, (nm, sol)
        # substitute lower inputs by their own expansions (recursively, via the spec definitions) and compare
        mine = sym_expr(defs[nm]['expansion_in_normalized_atoms'])
        sub = {INPUT_SYMS[o]: sym_expr(defs[o]['expansion_in_normalized_atoms']) for o in INPUT_SYMS if o != nm}
        # exact two-kink normalized atoms in the spec expansions are symbols K2_k[..], EK2_k[..] there as well
        got = s.expand(sol[0].xreplace(sub))
        # the CS form uses b3(1,0) = 1 (tree-level normalization F = z + u + ...), i.e. C3_1[v0d0] = 5 (note l.550)
        d_ = s.expand((got - mine).subs(sym('C3', 1, 0, 0), 5))
        # the CS form keeps K2/EK2 symbolic too; both sides use the same symbols -> exact comparison
        rec_rows[nm] = {'equal_to_derive_requirements_C8 (given C3_1[v0d0] = 5)': d_ == 0}
        if d_ != 0:
            rec_rows[nm]['difference'] = s.sstr(d_)[:400]
        print('recurrence', nm, d_ == 0, round(time.time() - t0, 1), 's', flush=True)
    res['l0_identity_equals_recurrence'] = rec_rows
    assert all(all(v_ for k_, v_ in r_.items() if k_.startswith('equal')) for r_ in rec_rows.values())

    # numeric values of the beta inputs available archive-free (for evaluating closed-form predictions)
    z = {k_: mp.zeta(k_) for k_ in range(2, 8)}
    Lg2, Li4h = mp.log(2), mp.polylog(4, mp.mpf(1) / 2)
    NUMIN = {'a': -4 * z[2], 'p': 8 - 2 * z[2] - 7 * z[3] - 8 * Lg2, 'A': -8 - 4 * z[2] - 2 * z[3] + 16 * Lg2,
             'E': (-16 + 14 * z[2] - 22 * z[3] + 12 * z[4] + 8 * Lg2 - 8 * Lg2**2 - 16 * Li4h - 14 * z[3] * Lg2
                   + 4 * z[2] * Lg2**2 - mp.mpf(2) / 3 * Lg2**4),
             'c': mp.mpf(-16),
             'f': 32 - mp.mpf(136) / 3 * z[3] - 64 * Lg2 + 48 * mp.log(3) + 16 * Lg2**2 + 32 * mp.polylog(2, -mp.mpf(1) / 2)}
    tki = json.load(open(SPEC / 'review' / 'three_kink_independent.json'))
    tk8 = json.load(open(SPEC / 'review' / 'three_kink_C8.json'))
    for nm in ('V', 'alpha', 'beta', 'gamma'):
        NUMIN[nm] = mp.mpf(tki['inputs'][nm]['value'])
    NUMIN['W'] = mp.mpf(tk8['inputs']['W']['value'])
    ZNUM = {z2_: z[2], z3_: z[3], z4_: z[4], z5_: z[5], z6_: z[6], z7_: z[7]}
    def numval(ex):
        ex = s.sympify(ex)
        sub = {INPUT_SYMS[k_]: s.Float(mp.nstr(v_, 45), 45) for k_, v_ in NUMIN.items()}
        sub.update({k_: s.Float(mp.nstr(v_, 45), 45) for k_, v_ in ZNUM.items()})
        val = ex.xreplace(sub)
        return mp.mpf(str(s.N(val, 40))) if not val.free_symbols else None

    # ---- 2. C3 jets: every higher log in closed form (C1 = 1, E C1 = j1, h2 = -1 exact; b3 Taylor coefficients only)
    JETS3 = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (3, 0), (2, 1), (1, 2), (0, 3)]
    tklogs = dict(tki['C3_eps0_logcoeffs']); tklogs['ddd'] = tk8['C3_eps0_logcoeffs']['ddd']
    c3rows, worst3 = {}, mp.mpf(0)
    for (i, j) in JETS3:
        tg = tag(i, j)
        rows = {}
        for k in range(2, i + 2 * j + 5):
            pr = predict(3, 'C', i, j, k)
            unknown = sorted(str(x) for x in pr.free_symbols if str(x).startswith('X'))
            assert not unknown, (tg, k, unknown)
            nv = numval(pr)
            ref = mp.mpf(tklogs[tg].get(str(k), '0'))
            rows[str(k)] = {'prediction': s.sstr(pr), 'value': mp.nstr(nv, 25), 'three_kink_independent': mp.nstr(ref, 25),
                            'difference': mp.nstr(nv - ref, 3)}
            worst3 = max(worst3, abs(nv - ref) / max(1, abs(ref)))
        c3rows[f'C3[{tg}]'] = rows
        print('C3', tg, 'logs', list(rows), 'max rel diff so far', mp.nstr(worst3, 3), round(time.time() - t0, 1), 's', flush=True)
    assert worst3 < mp.mpf(10)**-20, worst3
    res['C3_jets_all_logs'] = {'note': 'closed form in the b3 Taylor coefficients (a, p, A, E, V, alpha, beta, gamma, W); value with '
                                       'note closed forms of a, p, A, E and the independent three-kink V, alpha, beta, gamma, W; '
                                       'compared with the independent three-kink log polynomials (review/three_kink_independent.json, '
                                       'review/three_kink_C8.json)', 'max_relative_difference': mp.nstr(worst3, 3), 'jets': c3rows}
    # note statements (exact)
    a_, p_, A_, E_ = (INPUT_SYMS[x] for x in 'a p A E'.split())
    g3 = lambda tg_, k_: s.sympify(c3rows[f'C3[{tg_}]'][str(k_)]['prediction'], locals=INPUT_SYMS)
    note3 = {'C3 l^2 = 2 (l.550)': g3('base', 2) == 2,
             'd_v C3 l^3 = -8/3, l^2 = -3 (l.2231-2234)': (g3('v', 3), g3('v', 2)) == (R_(-8, 3), -3),
             'd_delta C3 l^4 = -1, l^3 = -1, l^2 = -2 z2 (l.2263-2264; a = -4 z2)':
                 (g3('d', 4), g3('d', 3), s.expand(g3('d', 2).subs(a_, -4 * z2_))) == (-1, -1, -2 * z2_)}
    Z2dd0 = {int(k_): s.Rational(v_) for k_, v_ in TK1['Z2_dd']['0'].items()}
    A3dd_half = {k_: s.expand((g3('dd', k_) + Z2dd0.get(k_, 0)) / 2) for k_ in range(2, 7)}
    rel = {6: R_(1, 3), 5: R_(-1, 15), 4: R_(-1, 3) - a_ / 4, 3: R_(4, 3) + a_ / 6 + A_ / 3 - p_ / 3, 2: E_ / 2}
    note3['A3_dd/2 l^6..l^2 = phase-1 note-closed-forms relation (1/3, -1/15, -1/3 - a/4, 4/3 + a/6 + A/3 - p/3, E/2)'] = all(
        s.expand(A3dd_half[k_] - rel[k_]) == 0 for k_ in rel)
    assert all(note3.values()), note3
    res['C3_note_checks'] = note3
    print('note C3 checks', note3, flush=True)

    # ---- 3. K4 jets: every higher log in closed form (K2 = Q2, EK2 = EQ2 exact; b3 and h4 Taylor coefficients)
    JETS4 = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (3, 0), (2, 1), (1, 2)]
    k4rows = {}
    for (i, j) in JETS4:
        tg = tag(i, j)
        rows = {}
        for k in range(2, i + 2 * j + 6):
            pr = predict(4, 'K', i, j, k, exact=exact_two_kink)
            unknown = sorted(str(x) for x in pr.free_symbols if str(x).startswith('X') or '[' in str(x))
            assert not unknown, (tg, k, unknown)
            rows[str(k)] = {'prediction': s.sstr(pr)}
            nv = numval(pr)
            if nv is not None:
                rows[str(k)]['value_with_note_and_three_kink_inputs'] = mp.nstr(nv, 25)
        k4rows[f'K4[{tg}]'] = rows
        print('K4', tg, 'logs', list(rows), round(time.time() - t0, 1), 's', flush=True)
    note4 = {'K4 l^3 = -4/3, l^2 = -6 (l.551-552)': (s.sympify(k4rows['K4[base]']['3']['prediction']),
                                                    s.sympify(k4rows['K4[base]']['2']['prediction'], locals=INPUT_SYMS))
             == (R_(-4, 3), -6)}
    assert all(note4.values()), note4
    res['K4_jets_all_logs'] = {'note': 'closed form in the b3 and h4 Taylor coefficients (c = -4 h4 etc.) and zeta values (exact '
                                       'two-kink Q2, EQ2 of out/C8/two_kink_exact_C8.json); the [l^k] of K4 = Q4 - Q2 Z2 jets',
                               'note_checks': note4, 'jets': k4rows}

    # ---- 4. second log of every other C/K jet the C8 inputs use (formula in normalized atoms + beta inputs)
    import re
    used = sorted({at for nm in defs for at in defs[nm]['normalized_atoms']})
    second = {}
    extra_atoms = set()
    for at in used:
        m_ = re.match(r'([A-Z]+)(\d)_(\d)\[v(\d)d(\d)\]', at)
        X, n, mlog, i, j = m_.group(1), int(m_.group(2)), int(m_.group(3)), int(m_.group(4)), int(m_.group(5))
        if X not in ('C', 'K') or mlog != 1 or n < 5:
            continue
        pr = predict(n, X, i, j, 2, exact=exact_two_kink)
        unknown = sorted(str(x) for x in pr.free_symbols if str(x).startswith('X'))
        atoms_needed = sorted(str(x) for x in pr.free_symbols if '[' in str(x))
        new_atoms = [x for x in atoms_needed if x not in used]
        extra_atoms |= set(new_atoms)
        second[f'{X}{n}_2[v{i}d{j}]'] = {'prediction': s.sstr(pr), 'n_terms': len(s.Add.make_args(pr)),
                                         'normalized_atoms': atoms_needed, 'atoms_not_in_the_C8_input_set': new_atoms,
                                         'beta_inputs': sorted(str(x) for x in pr.free_symbols if str(x) in INPUT_SYMS),
                                         'unknown_taylor_coefficients': unknown}
        print('second log', f'{X}{n}[v{i}d{j}]', len(s.Add.make_args(pr)), 'terms; extra atoms', new_atoms,
              round(time.time() - t0, 1), 's', flush=True)
    res['second_log_formulas'] = {
        'note': 'X_2[vidj] (= [eps^0 l^2] d_v^i d_delta^j X) predicted from l^0, l^1 data of lower orders and the beta inputs; '
                'evaluate with the same data as the inputs (per replicate) and compare with the engine [l^2]. Exact two-kink '
                'K2 = Q2, EK2 = EQ2 substituted. At (v,delta) = (1,0) these reduce to the assembly second-log formula.',
        'formulas': second, 'extra_normalized_atoms_needed': sorted(extra_atoms)}
    # ---- 5. every higher log (k = 3 .. top) of the C/K jets with n >= 5 that the C8 inputs use (data-dependent formulas)
    higher = {}
    for key in second:
        m_ = re.match(r'([CK])(\d)_2\[v(\d)d(\d)\]', key)
        X, n, i, j = m_.group(1), int(m_.group(2)), int(m_.group(3)), int(m_.group(4))
        top = n - 1 + i + 2 * j
        rows = {}
        for k in range(3, top + 2):
            pr = predict(n, X, i, j, k, exact=exact_two_kink)
            unknown = sorted(str(x) for x in pr.free_symbols if str(x).startswith('X'))
            rows[str(k)] = {'prediction': s.sstr(pr), 'n_terms': len(s.Add.make_args(pr)) if pr != 0 else 0,
                            'unknown_taylor_coefficients': unknown}
        higher[f'{X}{n}[v{i}d{j}]'] = {'structural_top_log': top, 'logs': rows}
        print('higher logs', f'{X}{n}[v{i}d{j}]', 'k = 3 ..', top + 1, round(time.time() - t0, 1), 's', flush=True)
    res['higher_log_formulas'] = {
        'note': 'X_k[vidj] for k = 3 .. top+1 predicted from lower-order data at log powers <= k-1 (normalized C, K and E jets) '
                'and the beta inputs; [l^(top+1)] must vanish. top = n - 1 + i + 2j (each d_v adds one log, each d_delta two).',
        'jets': higher}
    json.dump(res, open(OUT / 'rg_logs_C8.json', 'w'), indent=1)
    print('done', round(time.time() - t0, 1), 's')
