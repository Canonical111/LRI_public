"""Sector and term generator for the n-bubble connected Mayer cluster J_n(K, delta) of the 1D kink gas.

Geometry. 2n kinks at x_0 < ... < x_{2n-1}; a charge pattern q (Dyck word, +1 = start, -1 = end of a down bubble);
gaps u_g = x_{g+1} - x_g (g = 0..2n-2); coverage n_g = number of bubbles containing gap g (= Dyck height).
A matching pairs every end with an earlier start: bubbles (s, e). Label symmetry turns (1/n!) * sum over labelled
orderings into the plain sum over (pattern, matching).

Integrand of a matching: W_1..W_n * Q(C), Q = sum over connected graphs of prod f_ab,
f_ab = C_ab - 1 (bubbles disjoint) or -1 (overlapping), C_ab = product of the 4 cross-pair weights.
All monomials are homogeneous of degree -2nK, so (Cheng-Wu, largest gap L = 1, scale lambda):
  int d^{2n-1}u e^{-sum n_g u_g} F(u) = Gamma(alpha) int_{sector} d^{2n-2}u s^{-alpha} F(u),
  alpha = 2n-1-2nK, s = sum_g n_g u_g, and log insertions: (ell + L_ij) -> D + log(x_ij/s), D^j -> Gamma^{(j)}(alpha).

Sector decomposition: primary Cheng-Wu sectors (gap L largest) + iterated Binoth-Heinrich splitting until every
interval sum x_ij and s is (monomial) * (positive constant + positive monomials).

Near/far: a disjoint pair (a, b) (a left of b, gap interval g between them) is FAR in a sector when
lead(g) >= lead(r_a) and lead(g) >= lead(r_b); then C_ab = 1 + G_ab with G_ab = expm1(2K log1p z_ab),
z_ab = r_a r_b / (g (g + r_a + r_b)), computed cancellation-free; otherwise C_ab is kept as a monomial factor.
Each resulting term carries an exponent vector c_k = a_k + b_k w (w = 1 - K) per sector variable.
Check: no term may have a_k <= -1 with b_k = 0 (a K-independent divergence)."""
import itertools, json, sys
import numpy as np
from collections import defaultdict


def dyck(n):
    out = []
    def rec(s, op, cl):
        if len(s) == 2 * n:
            out.append(tuple(s)); return
        if op < n: rec(s + [1], op + 1, cl)
        if cl < op: rec(s + [-1], op, cl + 1)
    rec([], 0, 0)
    return out


def mirror(p):
    return tuple(-x for x in reversed(p))


def matchings(pat):
    res = []
    def rec(i, open_, bub):
        if i == len(pat):
            res.append(tuple(sorted(bub))); return
        if pat[i] == 1:
            rec(i + 1, open_ + [i], bub)
        else:
            for k, s in enumerate(open_):
                rec(i + 1, open_[:k] + open_[k + 1:], bub + [(s, i)])
    rec(0, [], [])
    return res


def disjoint(b1, b2):
    return b1[1] < b2[0] or b2[1] < b1[0]


def connected_graphs(n):
    pairs = list(itertools.combinations(range(n), 2))
    out = []
    for r in range(n - 1, len(pairs) + 1):
        for E in itertools.combinations(pairs, r):
            # connectivity
            adj = {i: set() for i in range(n)}
            for a, b in E: adj[a].add(b); adj[b].add(a)
            seen, st = {0}, [0]
            while st:
                x = st.pop()
                for y in adj[x]:
                    if y not in seen: seen.add(y); st.append(y)
            if len(seen) == n: out.append(E)
    return out


def mayer_poly(bubbles):
    """Q as {frozenset(disjoint pairs whose C appears): coeff}."""
    n = len(bubbles)
    disj = {(a, b): disjoint(bubbles[a], bubbles[b]) for a, b in itertools.combinations(range(n), 2)}
    Q = defaultdict(int)
    for E in connected_graphs(n):
        # product of f's: f = C - 1 or -1
        terms = {frozenset(): 1}
        for e in E:
            new = defaultdict(int)
            for S, c in terms.items():
                if disj[e]:
                    new[S | {e}] += c
                    new[S] -= c
                else:
                    new[S] -= c
            terms = new
        for S, c in terms.items(): Q[S] += c
    return {S: c for S, c in Q.items() if c != 0}, disj


# ---------------------------------------------------------------- sector decomposition
def leq(u, v):
    return all(x <= y for x, y in zip(u, v))


def gcd_vec(rows):
    return tuple(min(r[k] for r in rows) for k in range(len(rows[0])))


def bh_decompose(E, jac, polys, depth=0):
    """E: tuple of rows (per gap); polys: list of lists of gap indices. Returns list of (E, jac)."""
    d = len(jac)
    for P in polys:
        rows = [E[g] for g in P]
        m = gcd_vec(rows)
        red = [tuple(x - y for x, y in zip(r, m)) for r in rows]
        if any(all(x == 0 for x in r) for r in red):
            continue
        # minimal hitting set of variables
        S = None
        for size in range(1, d + 1):
            for cand in itertools.combinations(range(d), size):
                if all(any(r[k] > 0 for k in cand) for r in red):
                    S = cand; break
            if S: break
        out = []
        for l in S:
            newE = tuple(tuple(r[k] + (sum(r[j] for j in S if j != l) if k == l else 0) for k in range(d)) for r in E)
            newjac = tuple(jac[k] + ((sum(jac[j] for j in S if j != l) + len(S) - 1) if k == l else 0)
                           for k in range(d))
            out += bh_decompose(newE, newjac, polys, depth + 1)
        return out
    return [(E, jac)]


def lead_of(E, gaps):
    rows = [E[g] for g in gaps]
    m = gcd_vec(rows)
    assert any(r == m for r in rows), 'polynomial does not factorize'
    return m


def radii(sec, d, grid=(0.0, 0.25, 0.5, 0.75, 1.0)):
    """Lower estimate of the distance from t_k = 0 to the nearest complex zero of any interval/s regular part,
    with the other variables on a real grid in [0,1] (worst case over the grid)."""
    polys = [[(e, 1) for e in red] for red in sec['red']] + [[(e, c) for e, c in sec['reds']]]
    out = []
    for k in range(d):
        best = 1e9
        others = [i for i in range(d) if i != k]
        for vals in itertools.product(grid, repeat=len(others)):
            tv = dict(zip(others, vals))
            for P in polys:
                deg = max(e[k] for e, c in P)
                if deg == 0: continue
                co = np.zeros(deg + 1)
                for e, c in P:
                    m = c
                    for i in others: m *= tv[i] ** e[i]
                    co[e[k]] += m
                r = np.roots(co[::-1])
                if len(r): best = min(best, float(min(abs(r))))
        out.append(best)
    return out


def generate(n, verbose=True, sampled_radii=True):
    """sampled_radii=False (fast; needed for n = 4): no sampled radii are written (R = -1); the engine must then
    compute rigorous Rouche bounds itself (-radii rouche)."""
    nk, ng = 2 * n, 2 * n - 1
    d = ng - 1
    pats = dyck(n)
    done, out_patterns = set(), []
    intervals = [(i, j) for i in range(nk) for j in range(i + 1, nk)]
    iidx = {iv: k for k, iv in enumerate(intervals)}
    for pat in pats:
        if pat in done: continue
        mp_ = mirror(pat)
        done.add(pat); done.add(mp_)
        factor = 1 if mp_ == pat else 2
        cov = [sum(pat[:g + 1]) for g in range(ng)]
        polys = [list(range(i, j)) for (i, j) in intervals if j - i >= 2]
        spoly = [g for g in range(ng) if cov[g] > 0]
        polys.append(spoly)
        sectors, prim = [], []
        for L in range(ng):
            vars_ = [g for g in range(ng) if g != L]
            E = tuple(tuple(1 if vars_[k] == g else 0 for k in range(d)) for g in range(ng))
            sub = bh_decompose(E, tuple([0] * d), polys)
            sectors += sub; prim += [L] * len(sub)
        mats = matchings(pat)
        mdata = []
        for mt in mats:
            Q, disj = mayer_poly(list(mt))
            mdata.append((mt, Q, disj))
        sec_out = []
        nviol = 0
        for (E, jac), Lprim in zip(sectors, prim):
            M = [lead_of(E, list(range(i, j))) for (i, j) in intervals]
            red = [[tuple(x - y for x, y in zip(E[g], M[iidx[(i, j)]])) for g in range(i, j)] for (i, j) in intervals]
            Ms = lead_of(E, spoly)
            reds = [(tuple(x - y for x, y in zip(E[g], Ms)), cov[g]) for g in spoly]
            terms = []
            for (mt, Q, disj) in mdata:
                bub = list(mt)
                far = {}
                for (a, b), dj in disj.items():
                    if not dj: continue
                    A, B = (bub[a], bub[b]) if bub[a][1] < bub[b][0] else (bub[b], bub[a])
                    ra, rb, g = iidx[A], iidx[B], iidx[(A[1], B[0])]
                    gra, grb, tot = iidx[(A[0], B[0])], iidx[(A[1], B[1])], iidx[(A[0], B[1])]
                    isfar = leq(M[g], M[ra]) and leq(M[g], M[rb])
                    if isfar:
                        assert M[grb] == M[g] and M[gra] == M[g] and M[tot] == M[g]
                    la = tuple(x - y for x, y in zip(M[ra], M[g]))
                    lb = tuple(x - y for x, y in zip(M[rb], M[g]))
                    far[(a, b)] = dict(far=isfar, spec=[ra, rb, g, gra, grb, tot],
                                       cross=[(iidx[(A[0], B[0])], 1), (iidx[(A[1], B[1])], 1),
                                              (iidx[(A[0], B[1])], -1), (iidx[(A[1], B[0])], -1)],
                                       Mz=tuple(x + y for x, y in zip(la, lb)))
                # expand Q with C = 1 + G for far pairs
                T = defaultdict(int)
                for S, c in Q.items():
                    nearS = frozenset(p for p in S if not far[p]['far'])
                    farS = [p for p in S if far[p]['far']]
                    for r in range(len(farS) + 1):
                        for G in itertools.combinations(farS, r):
                            T[(nearS, frozenset(G))] += c
                for (nearS, G), c in T.items():
                    if c == 0: continue
                    pairs = [(iidx[(s, e)], -1) for (s, e) in bub]
                    for p in nearS: pairs += far[p]['cross']
                    a_, b_ = [], []
                    for k in range(d):
                        sq = sum(qq * M[I][k] for I, qq in pairs)
                        fz = sum(far[p]['Mz'][k] for p in G)
                        a_.append(jac[k] + 2 * sq + Ms[k] + fz)
                        b_.append(-2 * sq - 2 * n * Ms[k])
                        if a_[-1] <= -1 and b_[-1] == 0: nviol += 1
                    terms.append(dict(coef=c, pairs=pairs, far=[far[p]['spec'] for p in sorted(G)],
                                      a=a_, b=b_))
            # variable flags: plain (analytic, no split) at delta^0 and delta>=1
            plain0, plain1 = [], []
            for k in range(d):
                ok0 = all(t['b'][k] == 0 and t['a'][k] >= 0 for t in terms)
                ok1 = ok0 and all(M[I][k] == Ms[k] for t in terms for I, _ in t['pairs']) and \
                    all(M[f[2]][k] == Ms[k] for t in terms for f in t['far'])
                plain0.append(ok0); plain1.append(ok1)
            sd = dict(E=E, jac=jac, M=M, red=red, Ms=Ms, reds=reds, terms=terms, plain0=plain0, plain1=plain1, L=Lprim)
            sd['R'] = radii(sd, d, grid=(0.0, 0.5, 1.0) if d > 4 else (0.0, 0.25, 0.5, 0.75, 1.0)) if sampled_radii else [-1.0] * d
            sec_out.append(sd)
        if verbose:
            nt = sum(len(s['terms']) for s in sec_out)
            print(f'pattern {"".join("+" if x > 0 else "-" for x in pat)} factor {factor}: {len(mats)} matchings, '
                  f'{len(sectors)} sectors, {nt} terms, violations {nviol}, '
                  f'split vars d0 {sum(d - sum(s["plain0"]) for s in sec_out)}, '
                  f'd1 {sum(d - sum(s["plain1"]) for s in sec_out)}', file=sys.stderr)
        assert nviol == 0, 'K-independent divergence: near/far rule failed'
        out_patterns.append(dict(pattern=pat, factor=factor, cov=cov, sectors=sec_out))
    return dict(n=n, intervals=intervals, patterns=out_patterns)


def mirror_weights(data):
    """Mirror reduction inside self-mirror patterns (factor 1): the summed integrand of such a pattern is invariant under
    gap reversal g -> 2n-2-g, which maps the Cheng-Wu primary sector L (largest gap L) onto primary sector 2n-2-L, so
    their integrals (every A^(k)_j) are equal. Returns one weight per global sector index: 2 for L < n-1, 1 for the
    middle L = n-1, 0 (not computed) for L > n-1; patterns already mirror-paired (factor 2) keep weight 1."""
    ng = 2 * data['n'] - 1; mid = (ng - 1) // 2
    w = []
    for p in data['patterns']:
        for s in p['sectors']:
            if p['factor'] == 2: w.append(1)
            else: w.append(2 if s['L'] < mid else (1 if s['L'] == mid else 0))
    return w


def write_engine_input(data, path):
    """Flat text format for the C++ engine."""
    n = data['n']; nk = 2 * n; ng = nk - 1; d = ng - 1
    iv = data['intervals']
    L = [f'n {n} nint {len(iv)} npat {len(data["patterns"])}']
    for p in data['patterns']:
        L.append(f'pattern {" ".join(map(str, p["pattern"]))} factor {p["factor"]} nsec {len(p["sectors"])}')
        for s in p['sectors']:
            L.append('sector ' + ' '.join(map(str, s['jac'])) + ' plain0 ' + ' '.join(str(int(x)) for x in s['plain0'])
                     + ' plain1 ' + ' '.join(str(int(x)) for x in s['plain1']) + ' R ' + ' '.join('%.6g' % x for x in s['R']))
            for I in range(len(iv)):
                L.append('int ' + ' '.join(map(str, s['M'][I])) + ' ' + str(len(s['red'][I])) + ' ' +
                         ' '.join(' '.join(map(str, r)) for r in s['red'][I]))
            L.append('s ' + ' '.join(map(str, s['Ms'])) + ' ' + str(len(s['reds'])) + ' ' +
                     ' '.join(' '.join(map(str, r)) + ' ' + str(c) for r, c in s['reds']))
            L.append(f'nterm {len(s["terms"])}')
            for t in s['terms']:
                L.append(f'term {t["coef"]} {len(t["pairs"])} ' + ' '.join(f'{I} {q}' for I, q in t['pairs'])
                         + f' {len(t["far"])} ' + ' '.join(' '.join(map(str, f)) for f in t['far'])
                         + ' a ' + ' '.join(map(str, t['a'])) + ' b ' + ' '.join(map(str, t['b'])))
    open(path, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    # usage: python cluster_gen.py N [OUTPUT] [--no-radii]
    norad = '--no-radii' in sys.argv
    argv = [a for a in sys.argv if a != '--no-radii']
    n = int(argv[1])
    data = generate(n, sampled_radii=not norad)
    sys.argv = argv
    if len(sys.argv) > 2:
        write_engine_input(data, sys.argv[2])
