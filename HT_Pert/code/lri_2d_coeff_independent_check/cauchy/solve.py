"""Non-perturbative solution of the tuning problem at one complex eps.

At a given complex eps the truncated Hamiltonians are finite complex-symmetric matrices
(H0, M, V real-symmetric in the orthonormal Fock basis; eps, r, g complex; c_m = sqrt(w_m(x)) on the
principal branch).  Eigenvalues are obtained by Rayleigh-quotient (inverse) iteration with the bilinear
(transpose, not conjugate) Rayleigh quotient, which is stationary for complex-symmetric matrices/pencils.
Derivatives with respect to r and g are Hellmann-Feynman expressions  v^T (dA) v / v^T B v.
r, g are found by Newton's method on
    F1 = E1 - E0 - x,    F2 = E3 - E0 - (2 - x).
The point eps is reached by radial continuation t*eps, t = t_1 < ... < 1, in double precision (numpy/LAPACK),
starting from r = 0, g = t eps/3 and the unit reference vectors |p>, so that every E_p is the branch connected
to |p> at eps -> 0.  The double-precision solution at t = 1 (r, g and all eigenvectors) is then refined by
Newton + RQI in arbitrary precision (python-flint, ctx.prec bits).

Consistent scheme, vacuum at cutoff l: H_l(E) = A_l + E*Pi_{N>=2}, with
A_l = P_l(H0 + rM + gV)P_l - diag(E_v(l-N)) on N>=2 states.  The self-consistency E = eigenvalue of H_l(E)
is exactly the linear generalized eigenproblem  A_l psi = E Pi_0 psi  (Pi_0 = projector on the level-0 states),
solved here by RQI for the pencil (A_l, Pi_0); dE/dr = psi^T dA psi / psi^T Pi_0 psi.
"""
import numpy as np
from flint import acb, arb, acb_mat, ctx
from hamil import diagmat


# --------------------------------------------------------------------------- backends
class FlintBE:
    name = 'flint'

    def scal(self, z):
        if isinstance(z, complex):
            return acb(z.real, z.imag)
        return acb(z)

    def clean(self, z):
        return z.mid()

    def absf(self, z):
        return float(z.abs_lower())

    def diag(self, d):
        return diagmat(d)

    def unit(self, n, i):
        return acb_mat([[acb(1) if k == i else acb(0)] for k in range(n)])

    def nrows(self, v):
        return v.nrows()

    def comp(self, v, i):
        return v[i, 0]

    def bil(self, u, A, v):
        w = v if A is None else A * v
        return (u.transpose() * w)[0, 0]

    def bil_diag(self, u, d, v):
        s = acb(0)
        for i in range(len(d)):
            s += u[i, 0] * d[i] * v[i, 0]
        return s

    def solve(self, S, rhs):
        return S.solve(rhs, algorithm="approx")

    def scale(self, y, c):
        return (y * c).mid()

    def residual(self, A, v, Bv, sigma):
        res = A * v - Bv * sigma
        n = v.nrows()
        rn = max(float(res[i, 0].abs_lower()) for i in range(n))
        vn = max(float(v[i, 0].abs_lower()) for i in range(n))
        return rn / vn

    def mul(self, A, v):
        return A * v

    def tol_default(self):
        return arb(2) ** (-(ctx.prec - 20))

    def weight(self, v, ref):
        tot = 0.0
        for i in range(v.nrows()):
            tot += float(v[i, 0].abs_lower()) ** 2
        return float(v[ref, 0].abs_lower()) ** 2 / tot

    def from_numpy(self, v):
        return acb_mat([[acb(complex(z).real, complex(z).imag)] for z in v])

    def mats(self, numops, eps):
        ev = numops.eval(acb(eps))
        def sub(par, name, n):
            ent = ev[(par, name)]
            return acb_mat([row[:n] for row in ent[:n]])
        return ev['x'], (lambda par, n: diagmat(ev[(par, 'H0')][:n])), sub


class NumpyBE:
    name = 'numpy'

    def scal(self, z):
        return complex(z)

    def clean(self, z):
        return z

    def absf(self, z):
        return float(abs(z))

    def diag(self, d):
        return np.diag(np.array(d, dtype=complex))

    def unit(self, n, i):
        v = np.zeros(n, dtype=complex)
        v[i] = 1
        return v

    def nrows(self, v):
        return len(v)

    def comp(self, v, i):
        return v[i]

    def bil(self, u, A, v):
        return complex(u @ v) if A is None else complex(u @ (A @ v))

    def bil_diag(self, u, d, v):
        return complex(np.sum(u * np.array(d, dtype=complex) * v))

    def solve(self, S, rhs):
        return np.linalg.solve(S, rhs)

    def scale(self, y, c):
        return y * c

    def residual(self, A, v, Bv, sigma):
        return float(np.max(np.abs(A @ v - Bv * sigma)) / np.max(np.abs(v)))

    def mul(self, A, v):
        return A @ v

    def tol_default(self):
        return 1e-13

    def weight(self, v, ref):
        return float(abs(v[ref]) ** 2 / np.sum(np.abs(v) ** 2))

    def mats(self, numops, eps):
        ev = numops.eval64(complex(eps))
        return ev['x'], (lambda par, n: np.diag(ev[(par, 'H0')][:n])), \
            (lambda par, name, n: ev[(par, name)][:n, :n])


# --------------------------------------------------------------------------- RQI
def rqi(be, A, I, v, ref, B=None, Bdiag=None, tol=None, maxit=12):
    """Rayleigh-quotient iteration for A v = E B v (B = I if None).  B given as matrix and as diagonal list.
    v: start vector; ref: index used for normalisation (v[ref] = 1)."""
    if tol is None:
        tol = be.tol_default()

    def rq(y):
        num = be.bil(y, A, y)
        den = be.bil(y, None, y) if B is None else be.bil_diag(y, Bdiag, y)
        return num / den

    sigma = be.clean(rq(v))
    hist = []
    for it in range(maxit):
        S = A - (I if B is None else B) * sigma
        rhs = v if B is None else be.mul(B, v)
        try:
            y = be.solve(S, rhs)
        except (ZeroDivisionError, np.linalg.LinAlgError):
            break
        y = be.scale(y, 1 / be.comp(y, ref))
        new = be.clean(rq(y))
        d = be.absf(new - sigma)
        hist.append(d if d < 1e300 else 1e300)
        v, sigma = y, new
        if d <= tol * max(1.0, be.absf(sigma)):
            break
    Bv = v if B is None else be.mul(B, v)
    return sigma, v, {'it': len(hist), 'res': be.residual(A, v, Bv, sigma), 'hist': hist}


# --------------------------------------------------------------------------- one eps point
class Point:
    """All matrices at one eps for one scheme/L, in backend be."""

    def __init__(self, numops, scheme, L, eps, be):
        self.be = be
        self.sp = sp = numops.sp
        self.scheme, self.L = scheme, L
        self.x, H0f, subf = be.mats(numops, eps)
        self.mats = {}
        cut_even = list(range(0, L + 1, 2)) if scheme in ('consistent', 'literal') else [L]
        one, zero = be.scal(1), be.scal(0)
        for par, cuts in ((0, cut_even), (1, [L])):
            sec = sp.sectors[par]
            for l in cuts:
                n = sp.dim(par, l)
                lev = sec['level'][:n]
                m = {'n': n, 'lev': lev, 'H0': H0f(par, n), 'M': subf(par, 'M', n), 'V': subf(par, 'V', n),
                     'I': be.diag([one] * n), 'B0': [one if N == 0 else zero for N in lev]}
                m['B0m'] = be.diag(m['B0'])
                self.mats[(par, l)] = m
        self.vecs = {}
        self.refs = {p: sp.ref_index(p) for p in range(4)}

    def _start(self, key, n, ref):
        v = self.vecs.get(key)
        if v is None or self.be.nrows(v) != n:
            v = self.be.unit(n, ref)
        return v

    def matrices(self, r, g, vac=None):
        """primary-channel matrices (par -> A) for given r, g (and vacua for the corrected schemes)."""
        be, L = self.be, self.L
        out = {}
        for par in (0, 1):
            m = self.mats[(par, L)]
            A = m['H0'] + m['M'] * r + m['V'] * g
            if vac is not None:
                A = A + be.diag([(vac[L] - vac[L - N]) if N >= 2 else be.scal(0) for N in m['lev']])
            out[par] = A
        return out

    def energies(self, r, g, tol=None):
        """E_p (p=0..3), dE_p/dr, dE_p/dg, vacua; scheme-dependent."""
        be, L = self.be, self.L
        r, g = be.scal(r), be.scal(g)
        zero = be.scal(0)
        info = {}
        out = {}
        Dd = {0: None, 1: None}
        dDr = {0: None, 1: None}
        dDg = {0: None, 1: None}
        if self.scheme != 'raw':
            Ev, dEr, dEg = {}, {}, {}
            for l in range(0, L + 1, 2):
                m = self.mats[(0, l)]
                n = m['n']
                key = ('vac', l)
                if self.scheme == 'consistent':
                    corr = [(-Ev[l - N]) if N >= 2 else zero for N in m['lev']]
                    A = m['H0'] + m['M'] * r + m['V'] * g + be.diag(corr)
                    E, v, inf = rqi(be, A, m['I'], self._start(key, n, 0), 0, B=m['B0m'], Bdiag=m['B0'], tol=tol)
                    den = be.bil_diag(v, m['B0'], v)
                    cr = [(-dEr[l - N]) if N >= 2 else zero for N in m['lev']]
                    cg = [(-dEg[l - N]) if N >= 2 else zero for N in m['lev']]
                    dEr[l] = (be.bil(v, m['M'], v) + be.bil_diag(v, cr, v)) / den
                    dEg[l] = (be.bil(v, m['V'], v) + be.bil_diag(v, cg, v)) / den
                else:  # literal: raw vacua
                    A = m['H0'] + m['M'] * r + m['V'] * g
                    E, v, inf = rqi(be, A, m['I'], self._start(key, n, 0), 0, tol=tol)
                    den = be.bil(v, None, v)
                    dEr[l] = be.bil(v, m['M'], v) / den
                    dEg[l] = be.bil(v, m['V'], v) / den
                Ev[l] = E
                self.vecs[key] = v
                info[key] = inf
            out['vacua'] = Ev
            for par in (0, 1):
                lev = self.mats[(par, L)]['lev']
                Dd[par] = [(Ev[L] - Ev[L - N]) if N >= 2 else zero for N in lev]
                dDr[par] = [(dEr[L] - dEr[L - N]) if N >= 2 else zero for N in lev]
                dDg[par] = [(dEg[L] - dEg[L - N]) if N >= 2 else zero for N in lev]
        E, Er, Eg, wts = {}, {}, {}, {}
        for par, ps in ((0, (0, 2)), (1, (1, 3))):
            m = self.mats[(par, L)]
            A = m['H0'] + m['M'] * r + m['V'] * g
            if Dd[par] is not None:
                A = A + be.diag(Dd[par])
            for p in ps:
                ref = self.refs[p]
                key = ('prim', p)
                Ep, v, inf = rqi(be, A, m['I'], self._start(key, m['n'], ref), ref, tol=tol)
                self.vecs[key] = v
                info[key] = inf
                den = be.bil(v, None, v)
                dr = be.bil(v, m['M'], v)
                dg = be.bil(v, m['V'], v)
                if dDr[par] is not None:
                    dr += be.bil_diag(v, dDr[par], v)
                    dg += be.bil_diag(v, dDg[par], v)
                E[p], Er[p], Eg[p] = Ep, dr / den, dg / den
                wts[p] = be.weight(v, ref)
        out.update({'E': E, 'Er': Er, 'Eg': Eg, 'info': info, 'wts': wts})
        if self.scheme == 'consistent':
            # E_0 of the consistent primary Hamiltonian must equal E_v(L) (self-consistency check)
            out['E0_minus_EvL'] = be.absf(E[0] - out['vacua'][L])
        return out

    def newton(self, r, g, tolF, maxit=40, tol_eig=None):
        be, x = self.be, self.x
        hist = []
        for it in range(maxit):
            o = self.energies(r, g, tol=tol_eig)
            E = o['E']
            F1 = E[1] - E[0] - x
            F2 = E[3] - E[0] - (2 - x)
            nF = max(be.absf(F1), be.absf(F2))
            hist.append(nF)
            if nF <= tolF:
                return r, g, o, hist
            a = o['Er'][1] - o['Er'][0]
            b = o['Eg'][1] - o['Eg'][0]
            c = o['Er'][3] - o['Er'][0]
            d = o['Eg'][3] - o['Eg'][0]
            det = a * d - b * c
            dr = (d * F1 - b * F2) / det
            dg = (-c * F1 + a * F2) / det
            r = be.clean(r - dr)
            g = be.clean(g - dg)
        raise RuntimeError(f"Newton did not converge: {hist}")


def spectral_gaps(pt, r, g, o):
    """double-precision diagnostic: distance of each tracked eigenvalue to the rest of its spectrum."""
    gaps = {}
    vac = o.get('vacua')
    A = pt.matrices(r, g, vac)
    for par, ps in ((0, (0, 2)), (1, (1, 3))):
        w = np.linalg.eigvals(A[par])
        for p in ps:
            dist = np.sort(np.abs(w - o['E'][p]))
            gaps[f'prim{p}'] = float(dist[1])
    if vac is not None:
        be = pt.be
        for l in range(0, pt.L + 1, 2):
            m = pt.mats[(0, l)]
            A = m['H0'] + m['M'] * r + m['V'] * g
            if pt.scheme == 'consistent':
                lev = np.array(m['lev'])
                A = A - np.diag([vac[l - N] if N >= 2 else 0 for N in m['lev']])
                i0 = np.where(lev == 0)[0]
                iq = np.where(lev >= 2)[0]
                if len(iq):
                    Heff = A[np.ix_(i0, i0)] - A[np.ix_(i0, iq)] @ np.linalg.solve(A[np.ix_(iq, iq)], A[np.ix_(iq, i0)])
                else:
                    Heff = A
                w = np.linalg.eigvals(Heff)
            else:
                w = np.linalg.eigvals(A)
            dist = np.sort(np.abs(w - vac[l]))
            gaps[f'vac{l}'] = float(dist[1]) if len(dist) > 1 else float('inf')
            if pt.scheme == 'consistent':
                gaps[f'vac{l}_schur_check'] = float(dist[0])  # Schur-complement eigenvalue = RQI pencil value
    return gaps


def solve_point(numops, scheme, L, eps, tsteps=(0.25, 0.5, 0.75, 1.0), tol64=1e-11):
    """Radial continuation from 0 to eps in double precision, then full-precision refinement at eps."""
    eps = acb(eps)
    eps_c = complex(float(eps.real.mid()), float(eps.imag.mid()))
    be64 = NumpyBE()
    sols = [(0.0, 0j, 0j)]  # r = g = 0 at eps = 0
    vecs = {}
    diag = []
    for k, t in enumerate(tsteps):
        pt = Point(numops, scheme, L, eps_c * t, be64)
        pt.vecs = vecs
        if len(sols) == 1:
            r0, g0 = 0j, eps_c * t / 3  # first-order start (r_1 = 0, g_1 = 1/3)
        else:
            last = sols[-4:]  # polynomial (up to cubic) extrapolation in t
            r0, g0 = 0j, 0j
            for i, (ti, ri, gi) in enumerate(last):
                li = 1.0
                for j, (tj, _, _) in enumerate(last):
                    if j != i:
                        li *= (t - tj) / (ti - tj)
                r0 += ri * li
                g0 += gi * li
        r, g, o, hist = pt.newton(r0, g0, tol64)
        vecs = pt.vecs
        sols.append((t, r, g))
        diag.append({'t': t, 'newton': hist, 'wts': o['wts']})
    gaps = spectral_gaps(pt, r, g, o)
    # full precision refinement at t = 1
    be = FlintBE()
    ptf = Point(numops, scheme, L, eps, be)
    ptf.vecs = {key: be.from_numpy(v) for key, v in vecs.items()}
    tolF = arb(2) ** (-(ctx.prec - 24))
    rf, gf, of, histf = ptf.newton(be.scal(r), be.scal(g), tolF)
    diag.append({'t': 'final', 'newton': histf, 'wts': of['wts'],
                 'rqi_it': {str(k2): v['it'] for k2, v in of['info'].items()},
                 'rqi_res': max(v['res'] for v in of['info'].values()),
                 'gaps64': gaps})
    return {'eps': eps, 'x': ptf.x, 'r': rf, 'g': gf, 'E': of['E'], 'vacua': of.get('vacua'),
            'Delta': of['E'][2] - of['E'][0], 'diag': diag,
            'E0_minus_EvL': of.get('E0_minus_EvL')}
