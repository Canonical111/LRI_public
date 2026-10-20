from common import *
from mpmath import agm, meijerg
mp.dps = 25
lam = mp.findroot(lambda l: 4*l**3-112*l**2+909*l-2250, 15.98)
es = sqrt(40*lam-279)/20; chi = 2*(21*lam-150)/(40*lam-279)
def gth(th):
    Kx = pi/(2*agm(1, cos(th/2))); Kc = pi/(2*agm(1, sin(th/2)))
    return [4*Kx**2/pi**1.5, 4*Kx*Kc/pi**1.5, 2*(Kc**2-Kx**2)/pi**1.5]
for sg in [1,-1]:
    Bs = mpf(21)/20+sg*es; Cs = lam/10+sg*es*chi
    b = atan(Bs/2+1j*sqrt(Cs-Bs**2/4))/pi; bb = mp.conj(b)
    D = sqrt((1-Cs)**2+Bs**2)
    for xs in [mpf('0.37'), mpf('0.8')]:
        g = gth(mp.asin(sqrt(xs)))
        G = meijerg([[0.5,0.5],[0.5,b,bb]],[[0,0,0],[b,bb]], xs)
        print('sigma',sg,'x',xs,' (g1+Bg2+Cg3)/D - G^{3,2}_{5,5}:', (g[0]+Bs*g[1]+Cs*g[2])/D - G)
