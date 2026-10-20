"""Skeptic's minimal from-scratch HT engine through eps^5 (no code shared with A, B or the package).

H(eps) = H0 + eps F1 + r(eps) M(eps) + g(eps) V(eps) + X(eps)   (X = diagonal disconnected-window correction)
  H0 = N + P/4, F1 = -P/4, u_n(eps)^2 = ((1-eps)/2)_n / n!, C = sum u_n a_n^+, B = sum u_n a_n,
  M = :(C+B)^2:, V = :(C+B)^4:/12, states N even, N + P/4 <= cut (projection after every complete vertex).
Couplings tuned order by order: E(|1>)-E(|0>) = (1-eps)/4, E(|3>)-E(|0>) = (3+eps)/4, |p> = a0^p.
C_k = eps^k coefficient of E(|2>) - E(|0>).
Dconn definition used here (self-similar): X_L(E) = Evac^Dconn(L) - Evac^Dconn(L - E), with Evac^Dconn(c) the vacuum
energy of the same corrected HT at cutoff c (its own intermediates carry X_c). Through eps^3 Evac^Dconn = Evac^raw.
For C5 only X^(2), X^(3) on all states and X^(4), X^(5) on the references are needed (X^(4) on intermediates is eps^6).
Variants: raw (X=0); g2D3W (X^(2),X^(3) only); Dconn (+ X^(4,5) on refs from conn vacua); Dfull (refs from raw vacua).
"""
import sys, math, time, json
import numpy as np
import scipy.sparse as sps

K = 6  # series orders 0..5


def sexp(lg):
    e = np.zeros(K); e[0] = 1.
    for k in range(1, K):
        e[k] = sum(j * lg[j] * e[k - j] for j in range(1, k + 1)) / k
    return e


def useries(nmax):
    U = np.zeros((nmax + 1, K))
    for n in range(nmax + 1):
        lg = np.zeros(K)
        for j in range(n):
            for k in range(1, K):
                lg[k] -= 0.5 / (k * (2 * j + 1) ** k)
        u0sq = 1.
        for j in range(n):
            u0sq *= (j + 0.5) / (j + 1)
        U[n] = math.sqrt(u0sq) * sexp(lg)
    return U


def smul(a, b):
    return np.convolve(a, b)[:K]


def states(cut, pmax, ppar):
    """multisets (sorted tuples) with N even, N + P/4 <= cut, P <= pmax, P = ppar mod 2."""
    out = []
    ncut = int(math.floor(cut))

    def parts(rem, maxpart, cur):
        yield cur
        for m in range(min(rem, maxpart), 0, -1):
            yield from parts(rem - m, m, cur + [m])
    for N in range(0, ncut + 1, 2):
        for pr in parts(N, N, []):
            if sum(pr) != N:
                continue
            nz = len(pr)
            for P in range(nz, pmax + 1):
                if P % 2 != ppar or N + P / 4 > cut + 1e-12:
                    continue
                out.append(tuple(sorted([0] * (P - nz) + pr)))
    out.sort(key=lambda s: (sum(s) + len(s) / 4, len(s), s))
    return out


def e0(s):
    return sum(s) + len(s) / 4.


class Space:
    def __init__(self, cut, pmax, ppar, U):
        self.cut = cut
        self.st = states(cut, pmax, ppar)
        self.idx = {s: i for i, s in enumerate(self.st)}
        self.dim = len(self.st)
        self.E0 = np.array([e0(s) for s in self.st])
        self.P = np.array([len(s) for s in self.st], float)
        self.U = U
        self.build()

    def applyB(self, d):
        out = {}
        for s, a in d.items():
            prev = None
            for i, m in enumerate(s):
                if m == prev:
                    continue
                prev = m
                k = s.count(m)
                ns = s[:i] + s[i + 1:]
                v = smul(a, self.U[m]) * math.sqrt(k)
                if ns in out:
                    out[ns] = out[ns] + v
                else:
                    out[ns] = v
        return out

    def applyC(self, d, remaining):
        """add one particle; remaining = number of creations still to come after this one (for pruning)."""
        out = {}
        for s, a in d.items():
            E = e0(s)
            nmax = int(math.floor(self.cut - E - 0.25 * (remaining + 1) + 1e-12))
            for n in range(0, nmax + 1):
                ns = tuple(sorted(s + (n,)))
                k = ns.count(n)
                v = smul(a, self.U[n]) * math.sqrt(k)
                if ns in out:
                    out[ns] = out[ns] + v
                else:
                    out[ns] = v
        return out

    def build(self):
        rowsM, colsM, valsM = [], [], []
        rowsV, colsV, valsV = [], [], []
        cM = {(2, 0): 1., (1, 1): 2., (0, 2): 1.}
        cV = {(4, 0): 1 / 12, (3, 1): 4 / 12, (2, 2): 6 / 12, (1, 3): 4 / 12, (0, 4): 1 / 12}
        for j, s in enumerate(self.st):
            Bd = [{s: np.eye(K)[0].copy()}]
            for b in range(1, 5):
                Bd.append(self.applyB(Bd[-1]))
            for (cdict, rows, cols, vals, tot) in ((cM, rowsM, colsM, valsM, 2), (cV, rowsV, colsV, valsV, 4)):
                for b in range(0, tot + 1):
                    a = tot - b
                    d = Bd[b]
                    if not d:
                        continue
                    for r in range(a):
                        d = self.applyC(d, a - r - 1)
                    for f, amp in d.items():
                        i = self.idx.get(f)
                        if i is None:
                            continue
                        rows.append(i); cols.append(j); vals.append(cdict[(a, b)] * amp)
        self.M = self._mats(rowsM, colsM, valsM)
        self.V = self._mats(rowsV, colsV, valsV)

    def _mats(self, rows, cols, vals):
        vals = np.array(vals) if vals else np.zeros((0, K))
        return [sps.csr_matrix((vals[:, k], (rows, cols)), shape=(self.dim, self.dim)) for k in range(K)]

    def sub(self, cut):
        """index array of states with E0 <= cut."""
        return np.where(self.E0 <= cut + 1e-12)[0]


def hk_list(Ms, Vs, P, r, g, X, kmax, idx=None):
    """H_k (k=1..kmax) as sparse matrices on (sub)space idx; r, g coupling lists (index = order), X dict k->diag."""
    H = {}
    for k in range(1, kmax + 1):
        A = None
        for i in range(1, k + 1):
            j = k - i
            if r[i] != 0:
                A = r[i] * Ms[j] if A is None else A + r[i] * Ms[j]
            if g[i] != 0:
                A = g[i] * Vs[j] if A is None else A + g[i] * Vs[j]
        d = np.zeros(len(P))
        if k == 1:
            d -= P / 4
        if k in X:
            d += X[k]
        Dm = sps.diags(d)
        H[k] = Dm if A is None else (A + Dm)
    return H


def rs_energy(H, E0, ref, kmax):
    """plain RS (intermediate normalization) for nondegenerate reference index ref. Returns E[1..kmax], psi list."""
    dim = len(E0)
    den = E0[ref] - E0
    R = np.zeros(dim)
    m = np.arange(dim) != ref
    R[m] = 1.0 / den[m]
    psi = [np.zeros(dim)]; psi[0][ref] = 1.
    E = [0.]
    for n in range(1, kmax + 1):
        t = np.zeros(dim)
        for k in range(1, n + 1):
            if k in H:
                t += H[k] @ psi[n - k]
        En = t[ref]
        E.append(En)
        for k in range(1, n):
            t -= E[k] * psi[n - k]
        p = R * t
        p[ref] = 0.
        psi.append(p)
    return E, psi


class Engine:
    """order-by-order RS for refs p=0..3 with tuning, for a given variant."""
    def __init__(self, L, pcap_even=12, pcap_odd=13):
        self.L = L
        nm = int(L) + 2
        self.U = useries(nm)
        t0 = time.time()
        self.Se = Space(L, pcap_even, 0, self.U)
        self.So = Space(L, pcap_odd, 1, self.U)
        self.Sv = Space(L, 8, 0, self.U)
        self.tbuild = time.time() - t0
        self.ref = {0: self.Se.idx[()], 2: self.Se.idx[(0, 0)], 1: self.So.idx[(0,)], 3: self.So.idx[(0, 0, 0)]}

    def vac(self, cut, r, g, kmax, X=None):
        """vacuum energy series at cutoff cut on vacuum space, with optional diag X (dict k -> function of E0 array)."""
        S = self.Sv
        ii = S.sub(cut)
        Ms = [M[ii][:, ii] for M in S.M]; Vs = [V[ii][:, ii] for V in S.V]
        Xd = {} if X is None else {k: f(S.E0[ii]) for k, f in X.items()}
        H = hk_list(Ms, Vs, S.P[ii], r, g, Xd, kmax)
        ref = int(np.where(S.E0[ii] == 0)[0][0])
        E, _ = rs_energy(H, S.E0[ii], ref, kmax)
        return E

    def run(self, variant, kmax=5):
        L = self.L
        r = [0.] * (kmax + 1); g = [0.] * (kmax + 1)
        tgt1 = {1: -0.25}; tgt3 = {1: 0.25}
        sp = {0: self.Se, 2: self.Se, 1: self.So, 3: self.So}
        mdiag = {p: sp[p].M[0][self.ref[p], self.ref[p]] for p in range(4)}
        vdiag = {p: sp[p].V[0][self.ref[p], self.ref[p]] for p in range(4)}
        psi = {p: [None] for p in range(4)}
        for p in range(4):
            v = np.zeros(sp[p].dim); v[self.ref[p]] = 1.; psi[p][0] = v
        E = {p: [0.] for p in range(4)}
        Xs = {0: {}, 1: {}}   # per space parity: k -> diag array
        halfgrid = np.arange(0, 2 * L + 1) / 2.
        evtab = {}            # raw vacuum table: c -> E series (orders <= 3)
        for k in range(1, kmax + 1):
            # --- diagonal corrections at order k (need couplings < k) ---
            if variant != 'raw' and k in (2, 3):
                if k == 2:
                    for c in halfgrid:
                        evtab[c] = None
                for c in halfgrid:
                    evtab[c] = self.vac(c, r, g, 3)
                ev = lambda c, kk: evtab[math.floor(2 * c + 1e-9) / 2.][kk]
                for par, S in ((0, self.Se), (1, self.So)):
                    Xs[par][k] = np.array([ev(L, k) - ev(L - e, k) for e in S.E0])
            if variant in ('Dconn', 'Dfull') and k in (4, 5):
                # reference-state shifts from vacua at L, L-1/2, L-1
                evr = lambda c, kk: evtab[math.floor(2 * c + 1e-9) / 2.][kk]
                if variant == 'Dconn':
                    def Xf(c):
                        return {kk: (lambda E0arr, kk=kk, c=c: np.array([evr(c, kk) - evr(c - e, kk) for e in E0arr]))
                                for kk in (2, 3)}
                else:
                    Xf = lambda c: None
                ec = {c: self.vac(c, r, g, k, Xf(c)) for c in (L, L - 0.5, L - 1.0)}
                for par, S in ((0, self.Se), (1, self.So)):
                    d = np.zeros(S.dim)
                    for p in ((0, 2) if par == 0 else (1, 3)):
                        cp = math.floor(2 * (L - p / 4) + 1e-9) / 2.
                        d[self.ref[p]] = ec[L][k] - ec[cp][k]
                    Xs[par][k] = d
            # --- E_k with r_k = g_k = 0 ---
            Hs = {}
            for par, S in ((0, self.Se), (1, self.So)):
                Hs[par] = hk_list(S.M, S.V, S.P, r, g, Xs[par], k)
            Ek0 = {}
            for p in range(4):
                par = p % 2
                t = np.zeros(sp[p].dim)
                for j in range(1, k + 1):
                    t += Hs[par][j] @ psi[p][k - j]
                Ek0[p] = t[self.ref[p]]
            # --- tuning ---
            d1 = tgt1.get(k, 0.) - (Ek0[1] - Ek0[0])
            d3 = tgt3.get(k, 0.) - (Ek0[3] - Ek0[0])
            # r m1 + g v1 - (r m0 + g v0) = d1 ; same for 3
            a11 = mdiag[1] - mdiag[0]; a12 = vdiag[1] - vdiag[0]
            a21 = mdiag[3] - mdiag[0]; a22 = vdiag[3] - vdiag[0]
            det = a11 * a22 - a12 * a21
            r[k] = (d1 * a22 - a12 * d3) / det
            g[k] = (a11 * d3 - a21 * d1) / det
            for par, S in ((0, self.Se), (1, self.So)):
                Hs[par] = hk_list(S.M, S.V, S.P, r, g, Xs[par], k)
            for p in range(4):
                par = p % 2
                S = sp[p]
                t = np.zeros(S.dim)
                for j in range(1, k + 1):
                    t += Hs[par][j] @ psi[p][k - j]
                Ek = t[self.ref[p]]
                E[p].append(Ek)
                for j in range(1, k):
                    t -= E[p][j] * psi[p][k - j]
                den = S.E0[self.ref[p]] - S.E0
                R = np.zeros(S.dim); msk = np.arange(S.dim) != self.ref[p]
                R[msk] = 1. / den[msk]
                pk = R * t; pk[self.ref[p]] = 0.
                psi[p].append(pk)
        C = [0.5] + [E[2][k] - E[0][k] for k in range(1, kmax + 1)]
        chk1 = [E[1][k] - E[0][k] for k in range(1, kmax + 1)]
        chk3 = [E[3][k] - E[0][k] for k in range(1, kmax + 1)]
        Xref = {p: {k: float(Xs[p % 2][k][self.ref[p]]) for k in Xs[p % 2]} for p in range(4)}
        return dict(C=C, r=r, g=g, chk1=chk1, chk3=chk3, Xref=Xref)


if __name__ == '__main__':
    out = {}
    for L in [int(a) for a in sys.argv[1:]]:
        t0 = time.time()
        eng = Engine(L)
        res = {v: eng.run(v) for v in ('raw', 'g2D3W', 'Dconn', 'Dfull')}
        res['dims'] = (eng.Se.dim, eng.So.dim, eng.Sv.dim)
        res['sec'] = time.time() - t0
        out[L] = res
        R = res
        print(f"L={L} dims={res['dims']} build={eng.tbuild:.1f}s total={res['sec']:.1f}s")
        print('  raw C:', ' '.join(f'{c:.13g}' for c in R['raw']['C']))
        print('  r:', R['raw']['r'][1:], ' g:', R['raw']['g'][1:])
        for v in ('g2D3W', 'Dconn', 'Dfull'):
            print(f'  {v:6s} dC4={R[v]["C"][4]-R["raw"]["C"][4]:.13f} dC5={R[v]["C"][5]-R["raw"]["C"][5]:.13f}')
        sys.stdout.flush()
        json.dump({str(k): v for k, v in out.items()}, open(f'ht5_out_{"_".join(sys.argv[1:])}.json', 'w'), indent=1, default=float)
