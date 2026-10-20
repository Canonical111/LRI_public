# Spot checks of the analytic bounds quoted with the wheel series (eq:deltabound, a_n^2<=1/(3n+1), eq:wheeltail)
import mpmath as mp, json
mp.mp.dps = 40
pi = mp.pi
W0 = mp.mpf(json.load(open('series_out.json'))['W0_series']); Wc = W0 - (8 + 5*pi)*pi**2/3
# eq:deltabound integral representation and bound
for n in (0, 1, 5, 40):
    x = n + mp.mpf(1)/4
    d = mp.psi(1, n + 0.5) - mp.psi(1, n + 1)
    I = mp.quad(lambda u: u*mp.exp(-x*u)*mp.sech(u/4), [0, mp.inf])/2
    print(f"n={n}: delta_n={mp.nstr(d,15)}  integral rep diff {mp.nstr(d-I,3)}  bound 1/(2x^2)={mp.nstr(1/(2*x**2),15)}  ok={d < 1/(2*x**2)}")
ok = True; worst = 0
a = mp.mpf(1)
for n in range(1, 3001):
    a *= mp.mpf(2*n - 1)/(2*n)
    r = a**2*(3*n + 1)
    worst = max(worst, r)
print("max_{1<=n<=3000} a_n^2 (3n+1) =", mp.nstr(worst, 10), "(<=1 claimed)")
# eq:wheeltail for the literal sum over 1<=n<N
S = mp.mpf(0); a = mp.mpf(1); H2n2 = mp.mpf(0); Hn2 = mp.mpf(0)
checks = {}
for n in range(1, 2001):
    a *= mp.mpf(2*n - 1)/(2*n)
    Hn2 += mp.mpf(1)/n**2; H2n2 += mp.mpf(1)/(2*n - 1)**2 + mp.mpf(1)/(2*n)**2
    d = pi**2/3 - 4*H2n2 + 2*Hn2
    S += a**4*(8 + 5*pi*(4*n + 1)*a**2)*d
    N = n + 1
    if N in (2, 5, 10, 100, 1000, 2001):
        bound = (8 + 20*pi/3)/(54*(N - mp.mpf(3)/4)**3)
        checks[N] = (Wc - S, bound)
for N, (r, b) in checks.items():
    print(f"N={N}: W_c - W_c,N = {mp.nstr(r, 6)}  bound {mp.nstr(b, 6)}  ok={0 < r < b}  ratio {mp.nstr(r/b, 4)}")
# summand asymptotic 14/(pi^2 n^4)
n = 2000
print("n^4 * summand at n=2000 vs 14/pi^2:", mp.nstr(n**4*a**4*(8 + 5*pi*(4*n + 1)*a**2)*d, 8), mp.nstr(14/pi**2, 8))
