"""D3 = Im Li_{2,1}(i,1), D5 = Re Li_{2,1,2}(i,1,1) from the nested-sum
definition eq:mpl (descending, n1>n2>...>=1).
 D3 = sum_{k>=0} (-1)^k H_{2k}/(2k+1)^2
 D5 = sum_{k>=1} (-1)^k S(2k-1)/(2k)^2,  S(m) = sum_{j=1}^m H^{(2)}_{j-1}/j
Methods: Euler averaging of partial sums; CVZ.  Extra checks: D3 via the
integral of d/dz Li_{2,1}(z,1) = log^2(1-z)/(2z) along z=it, and the claimed
identity D3 = -Ls3(pi/2)/2 - 7 pi^3/192 with Ls3 by quadrature of eq:Lsdef."""
import mpmath as mp, json, time
from tools import euler_avg, cvz

mp.mp.dps = 90
pi = mp.pi; G = mp.catalan
t0 = time.time()
NMAX = 4400
# D3 terms
b3 = []; H = mp.mpf(0)
for k in range(NMAX):
    if k > 0: H += mp.mpf(1)/(2*k-1) + mp.mpf(1)/(2*k)
    b3.append(H/(2*k+1)**2)
# D5 terms (k>=1) ; reindex k'=k-1 so series is sum_{k'>=0} (-1)^{k'} c_k' with sign flip
c5 = []; S = mp.mpf(0); H2 = mp.mpf(0); j = 0
for k in range(1, NMAX+1):
    m = 2*k - 1
    while j < m:
        j += 1
        S += H2/j            # H2 = H^{(2)}_{j-1}
        H2 += mp.mpf(1)/j**2
    c5.append(S/(2*k)**2)    # term (-1)^k c  = -(-1)^{k-1} c
print('terms t=%.1f' % (time.time()-t0))

def partials(b):
    out = []; s = mp.mpf(0)
    for n, x in enumerate(b):
        s += (-1)**n * x; out.append(+s)
    return out
P3 = partials(b3); P5 = partials(c5)
res = {}
for name, P, b, sgn in [('D3', P3, b3, 1), ('D5', P5, c5, -1)]:
    vals = {}
    for N0, m in [(1000, 60), (2000, 100), (4000, 150)]:
        vals['avg_%d_%d' % (N0, m)] = sgn*euler_avg(P[N0-1:N0+m], m)
    for n in [120, 160, 200]:
        vals['cvz_%d' % n] = sgn*cvz(b, n)
    ref = vals['avg_4000_150']
    print(name, '=', mp.nstr(ref, 70))
    for k, v in vals.items():
        print('   %s - ref = %s' % (k, mp.nstr(v-ref, 3)))
    res[name] = ref

D3, D5 = res['D3'], res['D5']
# D3 via integral representation: Li21(i,1) = int_0^1 log^2(1-i t)/(2t) dt
I = mp.quad(lambda t: mp.im(mp.log(1 - 1j*t)**2)/(2*t) if t != 0 else mp.mpf(0), [0, 0.5, 1])
print('D3 integral rep - D3 =', mp.nstr(I - D3, 3))
# Ls3(pi/2) by quadrature
Ls3 = -mp.quad(lambda th: mp.log(2*mp.sin(th/2))**2, [0, pi/8, pi/4, pi/2])
print('Ls3(pi/2) =', mp.nstr(Ls3, 70))
print('D3 - (-Ls3/2 - 7pi^3/192) =', mp.nstr(D3 - (-Ls3/2 - 7*pi**3/192), 3))
Bpol = 4352*((32*G + 9*pi**2)*D3 - 64*D5)
print('Bpol =', mp.nstr(Bpol, 70))
json.dump({'D3': mp.nstr(D3, 85), 'D5': mp.nstr(D5, 85), 'Ls3': mp.nstr(Ls3, 85),
           'Bpol': mp.nstr(Bpol, 85)}, open('polylog.json', 'w'), indent=1)
print('t=%.1f' % (time.time()-t0))
