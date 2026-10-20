"""Seventh-sector central series eq:M7, M7 = sum_{n>=0} (-1)^n a_n^7 F_n.
Method 1: m-fold Euler averaging of partial sums (several N0, m).
Method 2: Cohen-Villegas-Zagier (several n)."""
import mpmath as mp, json, time
from tools import euler_avg, cvz

mp.mp.dps = 90
pi = mp.pi; ell = mp.log(2); z3 = mp.zeta(3)
t0 = time.time()

def terms(nmax):
    out = []
    an = mp.mpf(1); H = mp.mpf(0); H2n = mp.mpf(0)
    S2n = mp.mpf(0); S22n = mp.mpf(0); S32n = mp.mpf(0)
    for n in range(nmax):
        if n > 0:
            an *= mp.mpf(2*n-1)/(2*n)
            H += mp.mpf(1)/n; H2n += mp.mpf(1)/(2*n-1) + mp.mpf(1)/(2*n)
            S2n += mp.mpf(1)/n**2; S22n += mp.mpf(1)/(2*n-1)**2 + mp.mpf(1)/(2*n)**2
            S32n += mp.mpf(1)/(2*n-1)**3 + mp.mpf(1)/(2*n)**3
        h = ell + H - H2n
        d = pi**2/3 - 4*S22n + 2*S2n
        y = n + mp.mpf(1)/4
        u = 1 - 14*y*h
        v = 196*y*h**2 - 28*h + 7*y*(d - pi**2)
        T = 80*pi**2*y - 26*pi*u + 11*v
        K = 28*pi**2*y - 10*pi*u + 3*v
        F = ((98*H2n + 74*ell - 6*pi)*T - 98*pi*K
             - 98*(11*u - 13*pi*y)*(pi**2/3 + 4*S22n)
             - 8624*y*(z3 - S32n))
        out.append((an**7*F, F))
    return out

NMAX = 4200
tl = terms(NMAX)
print('terms done t=%.1f' % (time.time()-t0))
F0 = tl[0][1]
F0given = (39886*ell**3 - 10906*pi*ell**2 - 22792*ell**2 - 2188*pi**2*ell + 8156*pi*ell
           - mp.mpf(1679)/6*pi**3 + mp.mpf(2330)/3*pi**2 - 2156*z3)
print('F0 from definition', mp.nstr(F0, 40))
print('F0 given (l.924)  ', mp.nstr(F0given, 40), ' diff', mp.nstr(F0 - F0given, 3))
print('F_1, F_2, F_10:', mp.nstr(tl[1][1], 20), mp.nstr(tl[2][1], 20), mp.nstr(tl[10][1], 20))

partial = []; s = mp.mpf(0)
for n, (b, F) in enumerate(tl):
    s += (-1)**n * b
    partial.append(+s)
res = {}
for N0, m in [(1000, 60), (2000, 60), (2000, 100), (3000, 120), (4000, 150)]:
    val = euler_avg(partial[N0-1:N0+m], m)   # partial[i] = S_{i+1}
    res['avg_%d_%d' % (N0, m)] = val
    print('Euler avg N0=%d m=%d:' % (N0, m), mp.nstr(val, 60))
bs = [b for b, F in tl]
for n in [80, 120, 160, 200]:
    val = cvz(bs, n)
    res['cvz_%d' % n] = val
    print('CVZ n=%d:' % n, mp.nstr(val, 60))
ref = res['avg_4000_150']
for k, v in res.items():
    print('  %s - avg_4000_150 = %s' % (k, mp.nstr(v - ref, 3)))
print('M7 =', mp.nstr(ref, 65))
print('24 pi^3 M7 =', mp.nstr(24*pi**3*ref, 60))
json.dump({k: mp.nstr(v, 80) for k, v in res.items()}, open('m7.json', 'w'), indent=1)
print('t=%.1f' % (time.time()-t0))
