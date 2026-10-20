"""d=2: (i) R(2;b) = sum d_l T^3 collapses to Dixon(sigma)^2 [my derivation: 2q=1, 1-g=sigma, d_l=(1,2,2,..)];
(ii) compare with the paper's eq (R2) = s^2/(4pi^2(1+2c)) gamma_C(b/4)^3/gamma_C(3b/4);
(iii) Mh(2;b) = -(sum_m phi_m^3)^2 = 0 by brute force; (iv) Z2 = 4 G Q2 from W3(2;b)=u R."""
import mpmath as mp
mp.mp.dps = 30
gC = lambda z: mp.gamma(z)/mp.gamma(1-z)
dix = lambda a: mp.gamma(1+a/2)*mp.gamma(1-3*a/2)/(mp.gamma(1+a)*mp.gamma(1-a/2)**2*mp.gamma(1-a))
def R2_paper(b):
    s, c = mp.sin(mp.pi*b/2), mp.cos(mp.pi*b/2)
    return s**2/(4*mp.pi**2*(1+2*c))*gC(b/4)**3/gC(3*b/4)
for b in ['1', '0.8', '1.2', '0.5', '1.1+0.2j']:
    b = mp.mpmathify(b)
    print('b=%s  Dixon(b/2)^2 / R2_paper - 1 = %s' % (b, mp.nstr(dix(b/2)**2/R2_paper(b) - 1, 3)))
    # direct partial-sum check that sum d_l T_ln^3 = (sum_m f_m)^2 on a finite square (exact rearrangement)
sig = mp.mpf('0.45'); f = [(mp.rf(sig, m)/mp.factorial(m))**3 for m in range(60)]
T = lambda l, n: mp.rf(sig, l+n)*mp.rf(sig, n)/(mp.factorial(l+n)*mp.factorial(n))
lhs = sum((1 if l == 0 else 2)*T(l, n)**3 for l in range(60) for n in range(60) if l+n < 60)
rhs = sum(f[m]*f[n]*(1 if m == n else 1) for m in range(60) for n in range(60) if max(m, n) < 60 and True)
rhs2 = sum((2 if m > n else 1)*f[m]*f[n] for m in range(60) for n in range(m+1))
print('finite rearrangement sum_{l+n<60} d_l T^3 vs sum_{n<=m<60}(2-delta)f_m f_n:', mp.nstr(lhs - rhs2, 3))
# (iii) Mh(2;b): phi_m = Gamma(m+alpha)/Gamma(m+2-alpha), alpha=(1+sigma)/2 ; phi_{-1-m} = -phi_m
b = mp.mpf('0.9'); sig = b/2; al = (1+sig)/2
phi = lambda m: mp.gamma(m+al)/mp.gamma(m+2-al)
print('phi_{-1-m}+phi_m (m=0..5):', [mp.nstr(phi(-1-m)+phi(m), 3) for m in range(6)])
# check g_l(n+(l+1)/2) = -phi_{l+n} phi_n directly from the kernel at d=2
g = (2-b)/2
def gl(l, s):
    a = (l+sig)/2; be = a+g
    return mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(be+s)*mp.gamma(be-s))
e = max(abs(gl(l, n+mp.mpf(l+1)/2) + phi(l+n)*phi(n)) for l in range(4) for n in range(-6, 6))
print('max |g_l(n+(l+1)/2) + phi_{l+n} phi_n|:', mp.nstr(e, 3))
# (iv) Z2
W = lambda b: 0.5*gC(b/4)**3/gC(3*b/4)
Q2 = mp.gamma(0.25)**8/(24*mp.pi**4)
print("W3(2;1)/(3Q2)-1 =", mp.nstr(W(mp.mpf(1))/(3*Q2)-1, 3), "  W3'(1) =", mp.nstr(mp.diff(W, 1), 3),
      "  W3''/9 /(4 G Q2) - 1 =", mp.nstr(mp.diff(W, 1, 2)/9/(4*mp.catalan*Q2) - 1, 3))
