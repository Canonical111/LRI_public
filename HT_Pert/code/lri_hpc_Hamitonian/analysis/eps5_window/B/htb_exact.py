"""Implementation B, exact-rational cross-check (independent code path from htb.py).

Rescaled monomial basis m'_s = prod_n (u_n a_n^dag)^{k_n}|0>: there C' = sum_n a_n^dag has unit
coefficients and B' = sum_n v_n(eps) k_n (removal), v_n = u_n^2 = ((1-eps)/2)_n/n! is a polynomial
in eps with rational coefficients. H'(eps) = S^-1 H S (S diagonal) has the same eigenvalue series,
so every RS coefficient is an exact rational. Vertex: explicit sum binom(4,k)/12 C^{4-k}B^k (no Horner).
Full Dfull tables over all basis states (no shortcut), all orders re-run per variant (no forking).
"""
from fractions import Fraction as F
from math import comb
import sys, json, time

K = 4

def vpoly(nmax, K):
    v = [F(1)] + [F(0)] * K; out = []
    for n in range(nmax + 1):
        if n:
            v = [F(2 * n - 1, 2 * n) * v[k] + (F(-1, 2 * n) * v[k - 1] if k else 0) for k in range(K + 1)]
        out.append(v)
    return out

def mulj(a, b):
    return [sum(a[i] * b[k - i] for i in range(k + 1)) for k in range(K + 1)]

def basis(L, Pmax):
    out = []
    def rec(seq, start, N):
        out.append(tuple(seq))
        if len(seq) == Pmax: return
        n = start
        while 4 * (N + n) + len(seq) + 1 <= 4 * L:
            rec(seq + [n], n, N + n); n += 1
    rec([], 0, 0)
    return out

class Sp:
    def __init__(self, L, Pmax):
        self.L = L
        self.states = basis(L, Pmax)
        self.set = set(self.states)
        self.E4 = {s: 4 * sum(s) + len(s) for s in self.states}
        self.v = vpoly(L + 1, K)

    def C(self, Y):
        out = {}
        for s, a in Y.items():
            for n in range(self.L + 1):
                t = tuple(sorted(s + (n,)))
                if t not in self.set:
                    if 4 * (sum(s) + n) + len(s) + 1 > 4 * self.L: break
                    continue
                if t in out: out[t] = [x + y for x, y in zip(out[t], a)]
                else: out[t] = list(a)
        return out

    def B(self, Y):
        out = {}
        for s, a in Y.items():
            for n in set(s):
                k = s.count(n); l = list(s); l.remove(n); t = tuple(l)
                c = mulj(self.v[n], a); c = [k * x for x in c]
                if t in out: out[t] = [x + y for x, y in zip(out[t], c)]
                else: out[t] = c
        return out

    def vertices(self, x, keep):
        """x: dict s->jets. returns (M x, V x) jets restricted to keep(s)."""
        Bs = [x]
        for _ in range(4): Bs.append(self.B(Bs[-1]))
        def addto(acc, Y, c):
            for s, a in Y.items():
                if not keep(s): continue
                if s in acc: acc[s] = [p + c * q for p, q in zip(acc[s], a)]
                else: acc[s] = [c * q for q in a]
        M = {}; V = {}
        # M = C^2 + 2 C B + B^2
        addto(M, self.C(self.C(x)), 1); addto(M, self.C(Bs[1]), 2); addto(M, Bs[2], 1)
        for k in range(5):
            Y = Bs[k]
            for _ in range(4 - k): Y = self.C(Y)
            addto(V, Y, F(comb(4, k), 12))
        return M, V

def S_table(Lmax):
    w = [F(1)] + [F(0)] * K; run = [F(0)] * (K + 1); S = [list(run)]
    for m in range(Lmax):
        if m:
            w = [F(m + 1, m) * w[k] - (F(2, m) * w[k - 1] if k else 0) for k in range(K + 1)]
        if m % 2 == 0:
            den = [F(1, (m + 1) ** (j + 1)) for j in range(K + 1)]
            for k in range(K + 1): run[k] += sum(w[a] * den[k - a] for a in range(k + 1))
        S.append(list(run))
    return S

def rs(sp, s, r, g, Xfun=None, cut4=None, tune_refs=None):
    """RS for state(s). If tune_refs is a dict p->state, tune r,g in place on p=0,1,3. Returns E dict."""
    cut4 = 4 * sp.L if cut4 is None else cut4
    refs = tune_refs if tune_refs is not None else {'x': s}
    data = {}
    for name, st in refs.items():
        par = sum(st) % 2
        keep = (lambda par: (lambda t: sum(t) % 2 == par and sp.E4[t] <= cut4))(par)
        data[name] = dict(s=st, keep=keep, psi=[{st: F(1)}], E=[F(sp.E4[st], 4)], Mj=[], Vj=[])
    def vert(d, m):
        x = {t: [a] + [F(0)] * K for t, a in d['psi'][m].items()}
        Mx, Vx = sp.vertices(x, d['keep']); d['Mj'].append(Mx); d['Vj'].append(Vx)
    for d in data.values(): vert(d, 0)
    for n in range(1, K + 1):
        tp = {}
        for name, d in data.items():
            t = {}
            def add(k, val):
                if val != 0: t[k] = t.get(k, 0) + val
            for k, a in d['psi'][n - 1].items(): add(k, F(-len(k), 4) * a)
            for m in range(n):
                for j in range(1, n - m + 1):
                    if m == 0 and j == n: continue
                    l = n - m - j
                    for k, a in d['Mj'][m].items(): add(k, r[j] * a[l])
                    for k, a in d['Vj'][m].items(): add(k, g[j] * a[l])
            if Xfun is not None:
                for m in range(n - 1):
                    for k, a in d['psi'][m].items(): add(k, Xfun(k)[n - m] * a)
            t = {k: v for k, v in t.items() if d['keep'](k)}
            tp[name] = t
        if tune_refs is not None:
            raw = {p: tp[p].get(data[p]['s'], 0) for p in (0, 1, 3)}
            r[n] = ((F(-1, 4) if n == 1 else 0) - (raw[1] - raw[0])) / 2
            g[n] = ((F(1, 4) if n == 1 else 0) - (raw[3] - raw[0]) - 6 * r[n]) / 3
        for name, d in data.items():
            t = dict(tp[name])
            for k, a in d['Mj'][0].items():
                t[k] = t.get(k, 0) + r[n] * a[0]
            for k, a in d['Vj'][0].items():
                t[k] = t.get(k, 0) + g[n] * a[0]
            En = t.get(d['s'], F(0)); d['E'].append(En)
            for j in range(1, n + 1):
                for k, a in d['psi'][n - j].items():
                    t[k] = t.get(k, 0) - d['E'][j] * a
            E0 = F(sp.E4[d['s']], 4); psi = {}
            for k, a in t.items():
                if k == d['s'] or a == 0 or not d['keep'](k): continue
                den = E0 - F(sp.E4[k], 4)
                assert den != 0
                psi[k] = a / den
            d['psi'].append(psi)
            if n < K: vert(d, n)
    return {name: d['E'] for name, d in data.items()}

def main(L):
    t0 = time.time()
    sp = Sp(L, 11)
    S = S_table(L + 1)
    r = [F(0)] * (K + 1); g = [F(0)] * (K + 1)
    E = rs(sp, None, r, g, tune_refs={0: (), 1: (0,), 3: (0, 0, 0)})
    rraw, graw = list(r), list(g)
    out = {'L': L, 'dim': len(sp.states), 'r': [str(x) for x in r], 'g': [str(x) for x in g]}
    gg = [sum(graw[a] * graw[k - a] for a in range(k + 1)) for k in range(K + 1)]
    def Dj(cut4, s):
        top = cut4 // 4; up = max(0, (cut4 - sp.E4[s]) // 4)
        return [-(S[top][k] - S[up][k]) / 6 for k in range(K + 1)]
    def g2D_at(cut4):
        cache = {}
        def f(s):
            if s not in cache:
                d = Dj(cut4, s)
                cache[s] = [sum(gg[a] * d[k - a] for a in range(k + 1)) for k in range(K + 1)]
            return cache[s]
        return f
    # vacuum tables over all half-integer cutoffs
    vac_raw = []; vac_conn = []
    for j in range(2 * L + 1):
        cut4 = 2 * j
        vac_raw.append(rs(sp, (), rraw, graw, None, cut4)['x'])
        vac_conn.append(rs(sp, (), rraw, graw, g2D_at(cut4), cut4)['x'])
    def dfull(table):
        def f(s):
            j = (4 * L - sp.E4[s]) // 2
            return [table[2 * L][k] - table[j][k] for k in range(K + 1)]
        return f
    def g3W(s):
        base = g2D_at(4 * L)(s)
        up = (4 * L - sp.E4[s]) // 4
        W = (L + 1) // 2 - (up + 1) // 2
        return [base[k] + (graw[1] ** 3 * W if k == 3 else 0) for k in range(K + 1)]
    variants = {'raw': None, 'g2D': g2D_at(4 * L), 'g2D+g3W': g3W,
                'Dfull_raw': dfull(vac_raw), 'Dfull_c': dfull(vac_conn)}
    states = {'p2': (0, 0), 'd1': (1,), 'd2': (0, 1), 'd3': (0, 0, 1)}
    out['variants'] = {}
    for name, Xf in variants.items():
        r = list(rraw); g = list(graw)
        Er = rs(sp, None, r, g, Xf, tune_refs={0: (), 1: (0,), 3: (0, 0, 0)})
        Es = {k: rs(sp, s, r, g, Xf)['x'] for k, s in states.items()}
        Es.update({'p0': Er[0], 'p1': Er[1], 'p3': Er[3]})
        o = {'r4': str(r[4]), 'g4': str(g[4]),
             'C': [str(Es['p2'][k] - Es['p0'][k]) for k in range(K + 1)]}
        for p in (1, 2, 3):
            o['spacing_d%d' % p] = [str(Es['d%d' % p][k] - Es['p%d' % p][k]) for k in range(K + 1)]
        out['variants'][name] = o
        print(name, 'r4=%.15g g4=%.15g' % (float(r[4]), float(g[4])),
              'C4=%.15g' % float(Es['p2'][4] - Es['p0'][4]),
              ' '.join('d%d:%s' % (p, ['%.13g' % float(Es['d%d' % p][k] - Es['p%d' % p][k]) for k in (2, 3, 4)]) for p in (1, 2, 3)),
              flush=True)
    out['seconds'] = time.time() - t0
    return out

if __name__ == '__main__':
    for L in [int(a) for a in sys.argv[1:]]:
        o = main(L)
        print('L', L, 'dim', o['dim'], 'r', [float(F(x)) for x in o['r']], 'g', [float(F(x)) for x in o['g']], '%.1fs' % o['seconds'], flush=True)
        json.dump(o, open('exact_L%d.json' % L, 'w'), indent=1)
