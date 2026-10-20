"""End-to-end numerical check of the K_2 extraction (independent of the Taylor-coefficient algebra):
evaluate the proved closed form J_t = (4/pi^2) sin^2(pi tau)(I_3^2 + I_4^2) (tau = t/2) by direct quadrature of
the elliptic moments at small tau > 0, subtract the exact J_t^Gamma, and extrapolate (J - J^Gamma)/t^2 to t = 0."""
import mpmath as mp
mp.mp.dps = 60
K = mp.ellipk

def E(a, b):
    a = mp.mpf(a); b = mp.mpf(b); h = mp.mpf(1)/2
    Kc = lambda z: mp.pi/(2*mp.agm(1, mp.sqrt(z)))
    f1 = lambda u: (1-u**(1/a))**(b-1)*K(u**(1/a))/a if u > 0 else mp.pi/(2*a)
    f2 = lambda w: (1-w**(1/b))**(a-1)*Kc(w**(1/b))/b if w > 0 else mp.mpf(0)
    return mp.quad(f1, [0, h**a]) + mp.quad(f2, [0, h**(2*b), h**b])

def B2(a, b):   # B_d(a,b) at d = 2
    g = mp.gamma
    return g((2-a)/2)*g((2-b)/2)*g((a+b-2)/2)/(g(a/2)*g(b/2)*g((4-a-b)/2))

def D(tau):
    t = 2*tau
    I3, I4 = E(1-tau, tau), E(tau, 1-tau)
    J = 4/mp.pi**2*mp.sinpi(tau)**2*(I3**2+I4**2)
    JG = B2(1, 2-t)**2 + (2/t)*(B2(1, 2-t) - B2(1+2*t, 2-t))
    return (J - JG)/t**2

nodes = [mp.mpf(k)/1000 for k in range(2, 26, 2)]
vals = [D(x) for x in nodes]
for x, v in zip(nodes, vals):
    print('tau = %-6s (J - J^Gamma)/t^2 = %s' % (mp.nstr(x, 4), mp.nstr(v, 25)))
# polynomial extrapolation to tau = 0 (Neville), using increasing numbers of nodes
def neville(xs, ys, x0=0):
    p = list(ys)
    n = len(xs)
    for m in range(1, n):
        for i in range(n-m):
            p[i] = ((x0-xs[i+m])*p[i] + (xs[i]-x0)*p[i+1])/(xs[i]-xs[i+m])
    return p[0]
target = 32*mp.catalan**2 - 28*mp.zeta(3)*mp.log(2)
for n in range(6, len(nodes)+1, 2):
    est = neville(nodes[:n], vals[:n])
    print('nodes = %2d  extrapolated K2 = %s   minus (32G^2-28 zeta3 log2) = %s' % (n, mp.nstr(est, 30), mp.nstr(est-target, 3)))
mp.mp.dps = 90
target = 32*mp.catalan**2 - 28*mp.zeta(3)*mp.log(2)
print('32 G^2 - 28 zeta(3) log 2 =', mp.nstr(target, 75))
c62d = mp.mpf('3.518109138590252241649090170307739522622672809471036069084557795421742')   # confirm_dps70.json
print('C62d dps70 value (LRI_C5_d2_simplify/confirm_dps70.json) minus closed form:', mp.nstr(c62d - target, 3))
