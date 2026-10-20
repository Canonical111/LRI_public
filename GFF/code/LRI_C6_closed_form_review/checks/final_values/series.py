# Residue-series (coefficient-identity) cross-checks:
#  G4 via U4,U6;  G6 via eq:Pbseries;  G8 via eq:B8series;  G7 via residue table of M_j^(7);
#  W0 via eq:wheel;  wheel-core identity eq:wheel-core;  M7 via eq:M7.
# Non-alternating sums: direct sum to N + Euler-Maclaurin tail (smooth extension in n), done at two N.
# Alternating sums: CVZ acceleration and repeated averaging of partial sums.
import mpmath as mp, time, json, sys
from params import setup
DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 45
P = setup(DPS + 15)
mp.mp.dps = DPS + 15
pi = mp.pi; ell = mp.log(2); s2 = mp.sqrt(2)
out = {}

def a_(t): return mp.gamma(t + 0.5)/(mp.sqrt(pi)*mp.gamma(t + 1))
def h_(t): return ell + mp.digamma(t + 1) - mp.digamma(2*t + 1)
def d_(t): return mp.psi(1, t + 0.5) - mp.psi(1, t + 1)
def tau_(t): return -mp.psi(2, t + 0.5) + mp.psi(2, t + 1)

def em_sum(f, n0, N, K=12):
    """sum_{n>=n0} f(n): explicit to N-1, Euler-Maclaurin tail from N."""
    s = mp.fsum(f(mp.mpf(n)) for n in range(n0, N))
    I = mp.quad(f, [N, 2*N, 8*N, mp.inf])
    ders = mp.diffs(f, mp.mpf(N), 2*K)
    ders = list(ders)
    corr = f(mp.mpf(N))/2
    for k in range(1, K + 1):
        corr -= mp.bernoulli(2*k)/mp.factorial(2*k)*ders[2*k - 1]
    return s + I + corr

def two(f, n0, label):
    t0 = time.time()
    v1 = em_sum(f, n0, 60); v2 = em_sum(f, n0, 90)
    print(f"{label:40s} {mp.nstr(v1, DPS)}  [N=60 vs 90 diff {mp.nstr(v1 - v2, 2)}] {time.time()-t0:.1f}s", flush=True)
    return v1

# check exact-n consistency of the smooth extensions
n = 7
H = lambda k, p=1: mp.fsum(mp.mpf(1)/j**p for j in range(1, k + 1))
assert abs(a_(n) - mp.binomial(2*n, n)/4**n) < mp.mpf(10)**(-DPS)
assert abs(h_(n) - (ell + H(n) - H(2*n))) < mp.mpf(10)**(-DPS)
assert abs(d_(n) - (pi**2/3 - 4*H(2*n, 2) + 2*H(n, 2))) < mp.mpf(10)**(-DPS)
assert abs(tau_(n) - (12*mp.zeta(3) - 16*H(2*n, 3) + 4*H(n, 3))) < mp.mpf(10)**(-DPS)
print("smooth extensions agree with the harmonic definitions at n=7")

U4 = two(lambda t: a_(t)**4, 0, "U4 = sum a^4")
U6 = two(lambda t: (4*t + 1)*a_(t)**6, 0, "U6 = sum (4n+1)a^6")
G4s = (P['X4']*pi*U4 + P['Y4']*pi**2*U6/2)/P['rho4']
print("G4 from series (X4 pi U4 + Y4 pi^2 U6/2)/rho4 =", mp.nstr(G4s, DPS))
Pb = 24*pi**3*two(lambda t: a_(t)**6*(312*h_(t)**2 + 13*d_(t) + 88*pi*h_(t)), 0, "Pb sum")
G6s = 24*Pb/(192*pi*mp.sqrt(290))
print("G6 from eq:Pbseries  24 Pb/(192 pi sqrt290)   =", mp.nstr(G6s, DPS))
def b8(t):
    y = t + mp.mpf(1)/4; h = h_(t); d = d_(t)
    return a_(t)**8*((2466 - 834*s2)*pi**2*y - 1112*pi*(1 - 16*y*h) + 139*s2*(256*y*h**2 - 32*h + 8*y*d))
B8 = 8*pi**4*two(b8, 0, "B8 sum")
G8s = B8/(16*pi**3*P['rho8'])
print("G8 from eq:B8series  B8/(16 pi^3 rho8)        =", mp.nstr(G8s, DPS))
Wc = two(lambda t: a_(t)**4*(8 + 5*pi*(4*t + 1)*a_(t)**2)*d_(t), 1, "W_c")
W0 = Wc + (8 + 5*pi)*pi**2/3
print("W0 = W_c + (8+5pi)pi^2/3                     =", mp.nstr(W0, DPS))
D6 = two(lambda t: (4*t + 1)*a_(t)**6*d_(t), 0, "D6")
D4 = two(lambda t: a_(t)**4*d_(t), 0, "D4")
lhs = two(lambda t: a_(t)**4*(8*h_(t)*d_(t) + tau_(t)), 0, "sum a^4(8 h delta + tau)")
print("wheel-core: lhs - pi^2 D6 =", mp.nstr(lhs - pi**2*D6, 3), "; W0 - (8D4+5pi D6) =", mp.nstr(W0 - (8*D4 + 5*pi*D6), 3))
out.update(U4=str(U4), U6=str(U6), G4_series=str(G4s), G6_series=str(G6s), G8_series=str(G8s), W0_series=str(W0))

# ---------- alternating series
def cvz(a, n):
    d = (3 + mp.sqrt(8))**n; d = (d + 1/d)/2
    b = mp.mpf(-1); c = -d; s = mp.mpf(0)
    for k in range(n):
        c = b - c; s = s + c*a[k]
        b = (k + n)*(k - n)*b/((k + mp.mpf(1)/2)*(k + 1))
    return s/d
def avg(a, npass=120, M=220):
    ps = []; s = mp.mpf(0)
    for k, ak in enumerate(a):
        s += (-1)**k*ak; ps.append(s)
    row = ps[-M:]
    for it in range(npass):
        row = [(row[i] + row[i + 1])/2 for i in range(len(row) - 1)]
    return row[-1]

NT = 400
an = []; hn = []; dn = []; H2n_l = []; H2n2_l = []; H2n3_l = []
Hn = Hn2 = H2n = H2n2 = H2n3 = mp.mpf(0); a = mp.mpf(1)
for n in range(NT):
    if n > 0:
        a *= mp.mpf(2*n - 1)/(2*n)
        Hn += mp.mpf(1)/n; Hn2 += mp.mpf(1)/n**2
        for j in (2*n - 1, 2*n):
            H2n += mp.mpf(1)/j; H2n2 += mp.mpf(1)/j**2; H2n3 += mp.mpf(1)/mp.mpf(j)**3
    an.append(a); hn.append(ell + Hn - H2n); dn.append(pi**2/3 - 4*H2n2 + 2*Hn2)
    H2n_l.append(H2n); H2n2_l.append(H2n2); H2n3_l.append(H2n3)
z3 = mp.zeta(3)
# G7 residue series
q72, q71, q70, rho7 = P['q72'], P['q71'], P['q70'], P['rho7']
g7t = []
for n in range(NT):
    y = n + mp.mpf(1)/4; h = hn[n]; d = dn[n]
    r1 = pi**mp.mpf(2.5)*y; r2 = pi**mp.mpf(1.5)*(14*y*h - 1); r3 = mp.sqrt(pi)*(y*(98*h**2 + 7*d/2 - pi**2/2) - 14*h)
    g7t.append(an[n]**7*(q72*r1 + q71*r2 + q70*r3))
for nn in (80, 100, 120):
    print(f"G7 residue series CVZ n={nn}:", mp.nstr(pi/rho7*cvz(g7t, nn), DPS))
G7s = pi/rho7*cvz(g7t, 120)
print("G7 residue series (averaging):", mp.nstr(pi/rho7*avg(g7t), DPS))
# M7 series eq:M7
m7t = []
for n in range(NT):
    y = n + mp.mpf(1)/4; h = hn[n]; d = dn[n]
    u = 1 - 14*y*h
    v = 196*y*h**2 - 28*h + 7*y*(d - pi**2)
    T = 80*pi**2*y - 26*pi*u + 11*v
    K = 28*pi**2*y - 10*pi*u + 3*v
    F = ((98*H2n_l[n] + 74*ell - 6*pi)*T - 98*pi*K - 98*(11*u - 13*pi*y)*(pi**2/3 + 4*H2n2_l[n])
         - 8624*y*(z3 - H2n3_l[n]))
    m7t.append(an[n]**7*F)
for nn in (80, 100, 120):
    print(f"M7 series CVZ n={nn}:", mp.nstr(cvz(m7t, nn), DPS))
M7s = cvz(m7t, 120)
print("M7 series (averaging):", mp.nstr(avg(m7t), DPS))
out.update(G7_series=str(G7s), M7_series=str(M7s))
json.dump(out, open('series_out.json', 'w'), indent=1)
