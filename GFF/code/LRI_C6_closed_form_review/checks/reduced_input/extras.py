import mpmath as mp, json
mp.mp.dps = 80
pi = mp.pi
I = {k: mp.mpf(v) for k, v in json.load(open('primitive_dps95.json')).items() if k.startswith('I')}
def Ip(i, j):
    k = 'I%d%d' % (min(i,j), max(i,j)); return pi**(i+j)*I[k]   # <p_i,p_j>
# g_j in the p basis: g1 = sqrt(pi) p0, g2 = (p1 - pi p0)/sqrt(pi), g3 = (p2 - 2 pi p1)/(2 pi^1.5)
sp_ = mp.sqrt(pi)
gco = {1: {0: sp_}, 2: {1: 1/sp_, 0: -pi/sp_}, 3: {2: 1/(2*pi*sp_), 1: -2*pi/(2*pi*sp_)}}
def H(j, k):
    return mp.fsum(cj*ck*Ip(a, b) for a, cj in gco[j].items() for b, ck in gco[k].items())
Pa = mp.mpf(json.load(open('primitive_dps95.json'))['Pa'])
print('H33+2H13-H22 =', mp.nstr(H(3,3) + 2*H(1,3) - H(2,2), 3), ' (scale H22', mp.nstr(H(2,2), 5), ')')
print('8pi^3(10H11+21H12+18H22+15H23) - P_a =', mp.nstr(8*pi**3*(10*H(1,1)+21*H(1,2)+18*H(2,2)+15*H(2,3)) - Pa, 3))
# lambda_* and the rank-2 factorisation
lam = mp.findroot(lambda l: 4*l**3 - 112*l**2 + 909*l - 2250, 15.5)
lam2 = (28 + mp.sqrt(409)*mp.cos(mp.acos(mp.mpf(7298)/(409*mp.sqrt(409)))/3))/3
print('lambda* =', mp.nstr(lam, 30), ' explicit form diff', mp.nstr(lam - lam2, 3))
Mm = mp.matrix([[10, mp.mpf(21)/2, 0], [mp.mpf(21)/2, 18, mp.mpf(15)/2], [0, mp.mpf(15)/2, 0]])
Nn = mp.matrix([[0, 0, 1], [0, -1, 0], [1, 0, 1]])
print('4 det(M+lam N) =', mp.nstr(4*mp.det(Mm + lam*Nn), 3))
es = mp.sqrt(40*lam - 279)/20; chi = 2*(21*lam - 150)/(40*lam - 279)
v = {}
for s in (1, -1):
    v[s] = mp.matrix([1, mp.mpf(21)/20 + s*es, lam/10 + s*es*chi])
R = Mm + lam*Nn - 5*(v[1]*v[-1].T + v[-1]*v[1].T)
print('max|M+lam N - 5(v+v-^T+v-v+^T)| =', mp.nstr(max(abs(R[i, j]) for i in range(3) for j in range(3)), 3))
Pp = lambda s, z: z**2 + v[s][1]*z + v[s][2]
print('P+(i)P-(i) =', mp.nstr(Pp(1, 1j)*Pp(-1, 1j), 20), ' D+D- =',
      mp.nstr(abs(Pp(1, 1j))*abs(Pp(-1, 1j)), 20))
H_P = Pa/(80*pi**3)
print('10<f+,f-> check: 10 H_* =', mp.nstr(10*H_P, 30), ' vs 10H11+21H12+18H22+15H23 =',
      mp.nstr(10*H(1,1)+21*H(1,2)+18*H(2,2)+15*H(2,3), 30))
# wheel tail bound eq:wheeltail and eq:deltabound
W0 = mp.mpf(json.load(open('wheel.json'))['Wc_from0'])
Wc = W0 - (8 + 5*pi)*pi**2/3
for N in [2, 5, 10, 50, 200]:
    s = mp.mpf(0)
    for n in range(1, N):
        a = mp.gamma(n + 0.5)/(mp.sqrt(pi)*mp.gamma(n + 1)); d = mp.psi(1, n + 0.5) - mp.psi(1, n + 1)
        s += a**4*(8 + 5*pi*(4*n + 1)*a**2)*d
    bound = (8 + 20*pi/3)/(54*(N - mp.mpf(3)/4)**3)
    print('N=%d: Wc-Wc,N = %s  bound %s  ok=%s' % (N, mp.nstr(Wc - s, 6), mp.nstr(bound, 6), 0 < Wc - s < bound))
ok = True
for n in range(0, 400):
    d = mp.psi(1, n + 0.5) - mp.psi(1, n + 1); x = n + mp.mpf(1)/4
    a2 = (mp.gamma(n + 0.5)/(mp.sqrt(pi)*mp.gamma(n + 1)))**2
    ok &= (0 < d < 1/(2*x**2)) and (a2 <= 1/mp.mpf(3*n + 1) + mp.mpf(10)**-70)
print('0<delta_n<1/(2(n+1/4)^2) and a_n^2<=1/(3n+1) for n<400:', ok)
# n=0 term of -393 pi^3 W0
print('n=0 term check:', mp.nstr(-393*pi**3*(8 + 5*pi)*pi**2/3 - (-1048*pi**5 - 655*pi**6), 3))
