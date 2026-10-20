"""High-accuracy recheck of (3)/(4): E-moments by singularity-removing substitutions; 3F2 via mpmath series
with the note's Thomae forms checked against direct Euler-integral quadrature."""
import mpmath as mp
mp.mp.dps = 30
K = mp.ellipk

def E(a, b):
    a = mp.mpf(a); b = mp.mpf(b)
    h = mp.mpf(1)/2
    # int_0^{1/2} x^{a-1}(1-x)^{b-1}K(x) dx, x = u^{1/a}
    f1 = lambda u: (1-u**(1/a))**(b-1)*K(u**(1/a))/a if u > 0 else mp.pi/(2*a)
    # int_{1/2}^1 x^{a-1}(1-x)^{b-1}K(x) dx, 1-x = w^{1/b}
    Kc = lambda z: mp.pi/(2*mp.agm(1, mp.sqrt(z)))          # K(1-z), accurate for small z
    f2 = lambda w: (1-w**(1/b))**(a-1)*Kc(w**(1/b))/b if w > 0 else mp.mpf(0)
    return mp.quad(f1, [0, h**a]) + mp.quad(f2, [0, h**b])

def Is(tau):
    h = mp.mpf(1)/2
    return {1: E(h, tau), 2: E(tau, h), 3: E(1-tau, tau), 4: E(tau, 1-tau), 5: E(h, 1-tau), 6: E(1-tau, h)}

def F(t):   # 3F2(1/2,1/2,t;1,1;1) by Euler-Maclaurin-free method: use the double-Euler-equivalent K-moment
    # F(t) = (2 sin(pi t)/pi^2) I_4(t) is what we want to TEST, so compute F independently by series + Richardson
    return mp.nsum(lambda n: mp.rf(0.5, n)**2*mp.rf(t, n)/mp.factorial(n)**3, [0, mp.inf], method='richardson+euler-maclaurin')
def G(t):
    return mp.nsum(lambda n: mp.rf(t, n)**3/(mp.rf(0.5+t, n)**2*mp.factorial(n)), [0, mp.inf], method='richardson+euler-maclaurin')

for tau in [mp.mpf('0.1'), mp.mpf('0.3'), mp.mpf('0.77')]:
    I = Is(tau); s, c = mp.sinpi(tau), mp.cospi(tau)
    Fv, Gv = F(tau), G(tau)
    devs = [I[1]-(c*I[3]+s*I[4]), I[5]-(s*I[3]-c*I[4]), I[2]-s*I[3], I[6]-s*I[4],
            I[3]-mp.pi/2*mp.gamma(tau)**2/mp.gamma(0.5+tau)**2*Gv, I[4]-mp.pi**2/(2*s)*Fv]
    print('tau =', tau, ' moment-relation and Euler/Thomae residuals:', [mp.nstr(d, 2) for d in devs])
tau = mp.mpf(1)/2
I = Is(tau)
J = 4/mp.pi**2*(I[3]**2+I[4]**2)
print('J(t=1) - 3Q_2 =', mp.nstr(J-mp.gamma(0.25)**8/(8*mp.pi**4), 3))
