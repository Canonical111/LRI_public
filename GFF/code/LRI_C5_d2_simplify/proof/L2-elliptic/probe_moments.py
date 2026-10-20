# Probe which integer relations hold among second-order log moments of f g = K(k)K(k').
# <phi> = int_0^1 f g phi dk with p=log k, m=log(1-k), q=log(1+k).
import mpmath as mp, sys
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 45
pi, l = mp.pi, mp.log(2)
kp = lambda k: mp.sqrt((1-k)*(1+k))
f = lambda k: mp.pi/(2*mp.agm(1, kp(k)))
g = lambda k: mp.pi/(2*mp.agm(1, k))
Q = lambda F: mp.quad(F, [0, mp.mpf(1)/4, mp.mpf(1)/2, mp.mpf(3)/4, 1])
p = lambda k: mp.log(k); m = lambda k: mp.log1p(-k); q = lambda k: mp.log1p(k)
M = Q(lambda k: f(k)**2); N = Q(lambda k: f(k)*g(k))
fg = lambda phi: Q(lambda k: f(k)*g(k)*phi(k))
P2 = fg(lambda k: p(k)**2); PM = fg(lambda k: p(k)*m(k)); PQ = fg(lambda k: p(k)*q(k))
M2 = fg(lambda k: m(k)**2); MQ = fg(lambda k: m(k)*q(k)); Q2 = fg(lambda k: q(k)**2)
Y = Q(lambda k: f(k)**2*p(k))
print('T-relation R1:', MQ + PQ - Q2 + pi*l*M/2)
print('T-relation R2:', P2 - (M2 - 2*MQ + Q2))
print('target (**):', 2*P2 - PM - 3*PQ - (pi**2/2*N + pi*l*M))
print('Stieltjes+Landen chi2 for Y:', pi*Y - (-(pi**2/4)*N - PQ + PM))
basis = [P2, PM, PQ, Q2, pi**2*N, pi*l*M, l**2*N, pi**2*M, l**2*M, pi*l*N]
names = ['P2','PM','PQ','Q2','pi2N','pilM','l2N','pi2M','l2M','pilN']
r = mp.pslq(basis, maxcoeff=10**4, maxsteps=10**6)
print('pslq full basis:', r and list(zip(names, r)))
# Is Q2 in any relation?  drop P2 to look for a second relation
for drop in range(4):
    b2 = [x for i, x in enumerate(basis) if i != drop]; n2 = [x for i, x in enumerate(names) if i != drop]
    r = mp.pslq(b2, maxcoeff=10**4, maxsteps=10**6)
    print('drop', names[drop], '->', r and [(a, c) for a, c in zip(n2, r) if c])
