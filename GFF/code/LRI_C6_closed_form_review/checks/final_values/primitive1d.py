# Step 4(e): H_star = <f+, f-> and P_a, high precision, with endpoint-safe evaluation:
# <F1,F2> = int_0^{1/2} [F1(x)F2(1-x) + F1(1-x)F2(x)] / sqrt(x(1-x)) dx,
# every function receives (z, 1-z) computed without cancellation.
import mpmath as mp, time, json, sys
from params import setup
DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
P = setup(DPS + 10)
mp.mp.dps = DPS + 10
pi = mp.pi
Q = mp.gamma(mp.mpf(1)/4)**4/pi
c32 = pi**mp.mpf(1.5)

def gj(z, zc):
    # m = z/(2(1+sqrt(1-z))), 1-m = (1+sqrt(1-z))/2 ; K(m) = pi/(2 agm(1, sqrt(1-m)))
    r = mp.sqrt(zc)
    m = z/(2*(1 + r)); onem = (1 + r)/2
    K = pi/(2*mp.agm(1, mp.sqrt(onem)))
    Kc = pi/(2*mp.agm(1, mp.sqrt(m)))
    return (4*K**2/c32, 4*K*Kc/c32, 2*(Kc**2 - K**2)/c32)

def pairing(F1, F2):
    # x = y^2 removes the sqrt(x) branch structure at the endpoint (tanh-sinh then converges fast)
    def f(y):
        x = y*y; xc = 1 - x  # x <= 1/2: no cancellation
        A1, A2 = F1(x, xc), F2(xc, x)
        B1, B2 = F1(xc, x), F2(x, xc)
        return 2*(A1*A2 + B1*B2)/mp.sqrt(xc)
    return mp.quad(f, [0, mp.mpf(1)/4, mp.mpf(1)/2, 1/mp.sqrt(2)])

memo = {}
def G(z, zc):
    k = (z, zc)
    if k not in memo: memo[k] = gj(z, zc)
    return memo[k]
t0 = time.time()
fp = lambda z, zc: (lambda g: g[0] + P['Bp']*g[1] + P['Cp']*g[2])(G(z, zc))
fm = lambda z, zc: (lambda g: g[0] + P['Bm']*g[1] + P['Cm']*g[2])(G(z, zc))
Hs = pairing(fp, fm)
print(f"H_star = <f+,f->  = {mp.nstr(Hs, DPS)}   {time.time()-t0:.1f}s", flush=True)
# second quadrature (different breakpoints) for an error estimate
def pairing2(F1, F2):
    def f(y):
        x = y*y; xc = 1 - x
        return 2*(F1(x, xc)*F2(xc, x) + F1(xc, x)*F2(x, xc))/mp.sqrt(xc)
    return mp.quad(f, [0, mp.mpf(1)/10, mp.mpf(1)/3, mp.mpf(3)/5, 1/mp.sqrt(2)])
Hs_b = pairing2(fp, fm)
print("  alt breakpoints diff:", mp.nstr(Hs - Hs_b, 3))
print("P_a = 80 pi^3 H_star =", mp.nstr(80*pi**3*Hs, DPS))
Hjk = {}
for j in range(3):
    for k in range(j, 3):
        Hjk[(j + 1, k + 1)] = pairing(lambda z, zc, j=j: G(z, zc)[j], lambda z, zc, k=k: G(z, zc)[k])
Pa4 = 8*pi**3*(10*Hjk[(1, 1)] + 21*Hjk[(1, 2)] + 18*Hjk[(2, 2)] + 15*Hjk[(2, 3)])
print("P_a = 8pi^3(10H11+21H12+18H22+15H23) =", mp.nstr(Pa4, DPS))
print("H33 + 2H13 - H22 =", mp.nstr(Hjk[(3, 3)] + 2*Hjk[(1, 3)] - Hjk[(2, 2)], 3))

# Gauss-product input (eq:primitive-input), with exact connection formulas near z=1
A_c = mp.gamma(1)*mp.gamma(0.5)/mp.gamma(0.75)**2
B_c = mp.gamma(1)*mp.gamma(-0.5)/mp.gamma(0.25)**2
def v_(z, zc):
    if z <= 0.5: return mp.hyp2f1(0.25, 0.25, 1, z)
    # 2F1(1/4,1/4;1;1-x) = A 2F1(1/4,1/4;1/2;x) + B x^{1/2} 2F1(3/4,3/4;3/2;x), x = zc
    return A_c*mp.hyp2f1(0.25, 0.25, 0.5, zc) + B_c*mp.sqrt(zc)*mp.hyp2f1(0.75, 0.75, 1.5, zc)
def hcomp_(z, zc):
    # returns h(1-z) = 2F1(1/4,1/4;1/2; zc)
    if zc <= 0.5: return mp.hyp2f1(0.25, 0.25, 0.5, zc)
    # zero-balanced log series (DLMF 15.8.10) in z = 1 - zc
    pref = mp.gamma(0.5)/mp.gamma(0.25)**2
    s = 0; term = mp.mpf(1); k = 0; lz = mp.log(z)
    while True:
        t = term*(2*mp.digamma(k + 1) - 2*mp.digamma(0.25 + k) - lz)
        s += t
        if abs(t) < mp.mpf(10)**(-(DPS + 12)) and k > 5: break
        term *= ((mp.mpf(k) + mp.mpf(1)/4)/(k + 1))**2*z; k += 1
    return pref*s
memo2 = {}
def VH(z, zc):
    k = (z, zc)
    if k not in memo2: memo2[k] = (v_(z, zc), hcomp_(z, zc))
    return memo2[k]
p = [lambda z, zc: VH(z, zc)[0]**2,
     lambda z, zc: mp.sqrt(Q)*VH(z, zc)[0]*VH(z, zc)[1],
     lambda z, zc: Q*VH(z, zc)[1]**2]
# quick identity checks at x = 0.3: v = 2K/pi, sqrtQ h(1-x) = 2(K+Kc)
x = mp.mpf('0.3'); g = gj(x, 1 - x)
K = mp.sqrt(g[0]*c32/4); Kc = g[1]*c32/(4*K)
print("v(0.3)-2K/pi:", mp.nstr(VH(x, 1 - x)[0] - 2*K/pi, 3), "; sqrtQ h(0.7)-2(K+Kc):", mp.nstr(mp.sqrt(Q)*VH(x, 1 - x)[1] - 2*(K + Kc), 3))
x = mp.mpf('0.8')
print("connection-formula branches at x=0.8: v diff", mp.nstr(v_(x, 1 - x) - mp.hyp2f1(0.25, 0.25, 1, x), 3),
      " h(1-x) diff", mp.nstr(hcomp_(x, 1 - x) - mp.hyp2f1(0.25, 0.25, 0.5, 1 - x), 3))
t0 = time.time()
I = lambda i, j: pairing(p[i], p[j])/pi**(i + j)
I00, I11, I22, I12, I02 = I(0, 0), I(1, 1), I(2, 2), I(1, 2), I(0, 2)
Pa_in = pi**4*(15*I22 + 24*I11 - 4*I00)
print(f"P_a from Gauss input pi^4(15I22+24I11-4I00) = {mp.nstr(Pa_in, DPS)}  {time.time()-t0:.1f}s")
print("I22-4I12+4I02-4I00 =", mp.nstr(I22 - 4*I12 + 4*I02 - 4*I00, 3),
      "; pi^4[60(I12-I02)+24I11+56I00] - Pa =", mp.nstr(pi**4*(60*(I12 - I02) + 24*I11 + 56*I00) - Pa_in, 3))
json.dump(dict(H_star_1d=str(Hs), H_star_1d_b=str(Hs_b), Pa_from_Hstar=str(80*pi**3*Hs), Pa_four=str(Pa4), Pa_gauss_input=str(Pa_in)),
          open(f'primitive1d_{DPS}.json', 'w'), indent=1)
