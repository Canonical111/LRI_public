import mpmath as mp
mp.mp.dps = 30
pi = mp.pi
def TrFlat(d):
    nu = d/2 - 2
    Sd = 2*pi**(d/2)/mp.gamma(d/2)
    Vpref = 24*(2*pi)**(d/2)/2
    cPi = mp.gamma(2-d/2)*mp.gamma(d/2-1)**2/((4*pi)**(d/2)*mp.gamma(d-2))
    mom = mp.sqrt(pi)*mp.gamma(d/2+nu)*mp.gamma(d/2-nu)*mp.gamma(d/2)/(4*mp.gamma((d+1)/2))
    return Sd/(2*pi)**d * Vpref**2 * cPi * mom
def TrSphere(d):
    deg = lambda l: (2*l+d-1)*mp.gamma(l+d-1)/(mp.gamma(d)*mp.factorial(l))
    v = lambda l: 6/((l+d/2)*(l+d/2-1))
    return mp.nsum(lambda l: deg(l)*v(l)**2, [0, mp.inf])
def TrGVsphere(d):
    deg = lambda l: (2*l+d-1)*mp.gamma(l+d-1)/(mp.gamma(d)*mp.factorial(l))
    v = lambda l: 6/((l+d/2)*(l+d/2-1))
    return mp.nsum(lambda l: deg(l)*v(l), [0, mp.inf])
for d in (mp.mpf('3.0'), mp.mpf('3.5'), mp.mpf('3.8')):
    print('d=',d,' flat',mp.nstr(TrFlat(d),15),' sphere',mp.nstr(TrSphere(d),15))
print('Tr(GV) sphere sum at d=1.5:', mp.nstr(TrGVsphere(mp.mpf('1.5')),12), ' d=1.2:', mp.nstr(TrGVsphere(mp.mpf('1.2')),12))
