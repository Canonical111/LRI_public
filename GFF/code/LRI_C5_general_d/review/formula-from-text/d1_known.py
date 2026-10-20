import mpmath as mp
mp.mp.dps = 34
K = lambda k: mp.ellipk(k**2)
Me = mp.quad(lambda k: K(k)**2, [0, 0.5, 1])
Ne = mp.quad(lambda k: K(k)*mp.pi/(2*mp.agm(1, k)), [0, 0.5, 1])
P4 = 320*Me + 256*Ne
L1 = -(128*mp.pi + 640*mp.log(2))*Me - (96*mp.pi + 512*mp.log(2))*Ne
Q1 = mp.gamma(0.25)**4/mp.pi
Z1 = Q1*(2*mp.pi**2/3 + 8*mp.catalan)
print('Me', Me); print('Ne', Ne)
print('P4(1) from 320Me+256Ne', P4, ' given 2229.5220610709419642945251997485')
print('L1', L1); print('3Q1', 3*Q1); print('Z1', Z1)
