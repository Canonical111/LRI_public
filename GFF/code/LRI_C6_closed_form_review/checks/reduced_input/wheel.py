"""Wheel block W0 (eq:wheel) and the supplied wheel identities
eq:wheel-core, eq:wheelvanish, eq:wheelperiodinputs.
Methods: EM (analytic continuation via polygamma) at N=100 and N=200;
Richardson in 1/N (pure-power tails) or a log-polynomial least-squares-free
exact fit (log^j N / N^k, j<=2) for the sums with log^2 tails."""
import mpmath as mp, json, time, sys
from tools import em_tail, richardson

mp.mp.dps = 80
pi = mp.pi; ell = mp.log(2); z2 = mp.zeta(2); z3 = mp.zeta(3); gE = mp.euler
t0 = time.time()

def a(x): return mp.gamma(x + mp.mpf(1)/2) / (mp.sqrt(pi) * mp.gamma(x + 1))
def hh(x): return ell + mp.digamma(x + 1) - mp.digamma(2*x + 1)
def dd(x): return 4*mp.psi(1, 2*x + 1) - 2*mp.psi(1, x + 1)
def tau(x): return -8*mp.psi(2, 2*x + 1) + 2*mp.psi(2, x + 1)
def qq(x): return (4*x + 1)*a(x)**6
def AA(x): return 4*mp.digamma(2*x+1) - 3*mp.digamma(x+1) + gE - 2*ell + 1/(4*x+1)
def RR(x): return 3*z2 - 4*mp.psi(1, 2*x+1) + mp.psi(1, x+1) + 2/(4*x+1)**2
def MM(x): return 16*mp.psi(1, 2*x+1) - 6*mp.psi(1, x+1) - 4/(4*x+1)**2

cont = {
 'Wc_from0': lambda x: a(x)**4*(8 + 5*pi*(4*x+1)*a(x)**2)*dd(x),   # n>=0, i.e. W0
 'D4': lambda x: a(x)**4*dd(x),
 'D6': lambda x: (4*x+1)*a(x)**6*dd(x),
 'core': lambda x: a(x)**4*(8*hh(x)*dd(x) + tau(x)),
 'T': lambda x: a(x)**4*hh(x)*(8*hh(x)**2 + dd(x)),
 'line2': lambda x: a(x)**4*(128*hh(x)**3 + 24*hh(x)*dd(x) + tau(x)),
 'S7': lambda x: qq(x)*(4*AA(x)**2 + MM(x)),
 'vanish': lambda x: qq(x)*(AA(x)**2 - RR(x)/2),
 'Vw': lambda x: qq(x),
}
logtail = {'S7', 'vanish'}

def rec_terms(nmax):
    """definition-based terms from harmonic numbers"""
    an = mp.mpf(1); H = mp.mpf(0); H2n = mp.mpf(0)
    S2n = mp.mpf(0); S22n = mp.mpf(0); S3n = mp.mpf(0); S32n = mp.mpf(0)
    for n in range(nmax):
        if n > 0:
            an *= mp.mpf(2*n-1)/(2*n)
            H += mp.mpf(1)/n; H2n += mp.mpf(1)/(2*n-1) + mp.mpf(1)/(2*n)
            S2n += mp.mpf(1)/n**2; S22n += mp.mpf(1)/(2*n-1)**2 + mp.mpf(1)/(2*n)**2
            S3n += mp.mpf(1)/n**3; S32n += mp.mpf(1)/(2*n-1)**3 + mp.mpf(1)/(2*n)**3
        h = ell + H - H2n
        d = pi**2/3 - 4*S22n + 2*S2n
        ta = 12*z3 - 16*S32n + 4*S3n
        q = (4*n+1)*an**6
        A = 4*H2n - 3*H - 2*ell + mp.mpf(1)/(4*n+1)
        R = 4*S22n - S2n + mp.mpf(2)/(4*n+1)**2
        L = 8*H2n - 6*H - 4*ell + mp.mpf(2)/(4*n+1)
        M = 5*pi**2/3 - 16*S22n + 6*S2n - mp.mpf(4)/(4*n+1)**2
        yield n, dict(
            Wc_from0=an**4*(8 + 5*pi*(4*n+1)*an**2)*d,
            D4=an**4*d, D6=(4*n+1)*an**6*d,
            core=an**4*(8*h*d + ta), T=an**4*h*(8*h**2 + d),
            line2=an**4*(128*h**3 + 24*h*d + ta),
            S7=q*(L**2 + M), vanish=q*(A**2 - R/2), Vw=q,
            _pointwise=(L**2 + M - (pi**2 + 2*d)) - 4*(A**2 - R/2),
            _delta=d)

n0 = 50; J = 36
partials = {k: [] for k in cont}; Ns = []
sums = {k: mp.mpf(0) for k in cont}
pw = []
for n, tm in rec_terms(n0*J):
    for k in cont: sums[k] += tm[k]
    if n < 6: pw.append(mp.nstr(tm['_pointwise'], 3))
    if n == 1: d1 = tm['_delta'] - (pi**2/3 - 3)
    if n == 2: d2 = tm['_delta'] - (pi**2/3 - mp.mpf(115)/36)
    if (n+1) % n0 == 0:
        Ns.append(n+1)
        for k in cont: partials[k].append(+sums[k])
print('pointwise identity L^2+M-(pi^2+2delta)-4(A^2-R/2), n=0..5:', pw)
print('delta_1, delta_2 checks:', mp.nstr(d1, 3), mp.nstr(d2, 3))

def logfit(Ps, Ns, K):
    # S_N = S + sum_{k=1..K} sum_{j=0..2} c_kj log^j N / N^k ; use last 3K+1 points
    m = 3*K + 1
    Ps = Ps[-m:]; Ns = Ns[-m:]
    A = mp.matrix(m, m); b = mp.matrix(m, 1)
    for i, (P, N) in enumerate(zip(Ps, Ns)):
        N = mp.mpf(N); lN = mp.log(N)
        A[i, 0] = 1; col = 1
        for k in range(1, K+1):
            for j in range(3):
                A[i, col] = lN**j / N**k; col += 1
        b[i] = P
    x = mp.lu_solve(A, b)
    return x[0]

res = {}
for k, f in cont.items():
    S1 = mp.fsum(f(mp.mpf(n)) for n in range(100)); t1, _ = em_tail(f, 100, K=25)
    S2 = mp.fsum(f(mp.mpf(n)) for n in range(200)); t2, _ = em_tail(f, 200, K=25)
    v1 = S1 + t1; v2 = S2 + t2
    if k in logtail:
        with mp.workdps(200):
            r1 = logfit(partials[k], Ns, 11); r2 = logfit(partials[k], Ns, 9)
        alt = 'logfitK11-EM %s  logfitK9-EM %s' % (mp.nstr(r1-v1, 3), mp.nstr(r2-v1, 3))
    else:
        r1 = richardson(partials[k], Ns); r2 = richardson(partials[k][4:], Ns[4:])
        alt = 'R-EM %s  R2-R %s' % (mp.nstr(r1-v1, 3), mp.nstr(r2-r1, 3))
    res[k] = mp.nstr(v1, 75)
    print(k, mp.nstr(v1, 55), '| EM200-EM100', mp.nstr(v2-v1, 3), '|', alt,
          ' t=%.1f' % (time.time()-t0)); sys.stdout.flush()

json.dump(res, open('wheel.json', 'w'), indent=1)
v = {k: mp.mpf(res[k]) for k in res}
W0 = v['Wc_from0']
U6 = v['Vw']
print('W0 =', mp.nstr(W0, 60))
print('W0 - (8D4+5pi D6)       =', mp.nstr(W0 - 8*v['D4'] - 5*pi*v['D6'], 3))
print('core: sum a^4(8h d+tau) - pi^2 D6 =', mp.nstr(v['core'] - pi**2*v['D6'], 3), ' (scale', mp.nstr(v['core'], 5), ')')
Bs = 2*pi**4*U6
print('line2: sum - Bs/2         =', mp.nstr(v['line2'] - Bs/2, 3), ' (scale', mp.nstr(Bs/2, 5), ')')
print('line1: S7 - (3Bs/(2pi^2) - 32T/pi^2) =', mp.nstr(v['S7'] - (3*Bs/(2*pi**2) - 32*v['T']/pi**2), 3), ' (scale', mp.nstr(v['S7'], 5), ')')
print('vanish: sum q(A^2-R/2)    =', mp.nstr(v['vanish'], 3))
print('S7 - (pi^2 Vw + 2 D6)     =', mp.nstr(v['S7'] - pi**2*U6 - 2*v['D6'], 3))
print('wheel block -393 pi^3 W0  =', mp.nstr(-393*pi**3*W0, 60))
