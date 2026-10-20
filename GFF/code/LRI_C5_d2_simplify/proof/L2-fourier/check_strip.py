# Numerical checks (<= 25 digits) of the half-strip contour proof of (E1), (E2).
# F(beta)=K(sin beta), G(beta)=K(cos beta), modulus convention K(k)=ellipk(k^2); strip 0<Re beta<pi/2, Im beta>0.
# Boundary values (y>0, k=tanh y, k'=sech y, f=K(k), g=K(k')):
#   F(iy)=k' f,  F(pi/2+iy-0)=k'(g+i f),  G(iy+0)=k'(g-i f),  G(pi/2+iy)=k' f,
#   log sin 2beta: iy+0 -> omega + i pi/2,  pi/2+iy-0 -> omega - i pi/2,  omega=log(2k/k'^2)=log sinh 2y.
# Contour identity: int_0^{pi/2} h dbeta = -i int_0^infty [h(pi/2+iy) - h(iy)] dy.
import sys, mpmath as mp
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 20
mp.mp.dps = dps + 5
pi, l2 = mp.pi, mp.log(2)
K = lambda k: mp.ellipk(k**2)
F = lambda be: K(mp.sin(be)); G = lambda be: K(mp.cos(be))
out = {}
# boundary values vs. interior limits (eps small)
eps = mp.mpf(10)**(-(dps + 2))
for y in [mp.mpf('0.3'), mp.mpf('1.7')]:
    k, kp = mp.tanh(y), mp.sech(y); f, g = K(k), K(kp)
    out[f'F(iy) y={y}'] = F(eps + 1j*y) - kp*f
    out[f'F(pi/2+iy) y={y}'] = F(pi/2 - eps + 1j*y) - kp*(g + 1j*f)
    out[f'G(iy) y={y}'] = G(eps + 1j*y) - kp*(g - 1j*f)
    out[f'G(pi/2+iy) y={y}'] = G(pi/2 - eps + 1j*y) - kp*f
    om = mp.log(2*k/kp**2)
    out[f'log sin2b left y={y}'] = mp.log(mp.sin(2*(eps + 1j*y))) - (om + 1j*pi/2)
    out[f'log sin2b right y={y}'] = mp.log(mp.sin(2*(pi/2 - eps + 1j*y))) - (om - 1j*pi/2)
# moments on the bottom edge (fold to avoid floating endpoint rounding, AGM form of K)
Kc = lambda s, c: pi/(2*mp.agm(1, c))
def fold(H):
    return mp.quad(lambda t: H(mp.sin(t), mp.cos(t)) + H(mp.cos(t), mp.sin(t)), [0, pi/8, pi/4])
L = lambda s, c: mp.log(2*s*c)        # log sin 2beta
m0 = fold(lambda s, c: Kc(s, c)**2); m1 = fold(lambda s, c: Kc(s, c)*Kc(c, s))
lt0 = fold(lambda s, c: Kc(s, c)**2*L(s, c)); lt1 = fold(lambda s, c: Kc(s, c)*Kc(c, s)*L(s, c))
# k-integrals over (0,1): f=K(k), g=K(k'); write k=sin t to avoid endpoint rounding: dk = cos t dt
def kint(H):   # int_0^1 H(k,k') dk with k=sin t
    return mp.quad(lambda t: H(mp.sin(t), mp.cos(t))*mp.cos(t), [0, pi/4, pi/2 - mp.mpf(10)**(-dps - 3)])
fK = lambda k, kp: pi/(2*mp.agm(1, kp)); gK = lambda k, kp: pi/(2*mp.agm(1, k))
om = lambda k, kp: mp.log(2*k/kp**2)
M = kint(lambda k, kp: fK(k, kp)**2); N = kint(lambda k, kp: fK(k, kp)*gK(k, kp))
Ig2 = kint(lambda k, kp: gK(k, kp)**2)
Ifgw = kint(lambda k, kp: fK(k, kp)*gK(k, kp)*om(k, kp))
If2w = kint(lambda k, kp: fK(k, kp)**2*om(k, kp))
Ig2w = kint(lambda k, kp: gK(k, kp)**2*om(k, kp))
out['(C1) m0 - 2N'] = m0 - 2*N
out['(C1) int g^2 - 2M'] = Ig2 - 2*M
out['(C2) m1 - 2M'] = m1 - 2*M
out['(C3) lt0 - (2 int fg w - pi/2 int g^2)'] = lt0 - (2*Ifgw - pi/2*Ig2)
out['(C3) int (g^2-2f^2) w + pi N'] = Ig2w - 2*If2w + pi*N
out['(C4) lt1 - (2 int f^2 w - pi N)'] = lt1 - (2*If2w - pi*N)
out['(Landen) int fg w'] = Ifgw
out['(Landen) int g^2 w + 2 int f^2 w'] = Ig2w + 2*If2w
out['=> int f^2 w - pi N/4'] = If2w - pi*N/4
out['(E1) lt0 + (pi/2) m1'] = lt0 + pi/2*m1
out['(E2) lt1 + (pi/4) m0'] = lt1 + pi/4*m0
# direct contour check for h = F^2 log sin 2beta (side integrals computed from interior boundary values)
side = lambda h: -1j*mp.quad(lambda y: h(pi/2 + 1j*y) - h(1j*y), [mp.mpf(10)**(-dps-8), 1, 4, 12, 40, 80])
def hF2L(be):
    if mp.re(be) < 1:   # left side: use boundary formula
        y = mp.im(be); k, kp = mp.tanh(y), mp.sech(y)
        return (kp*fK(k, kp))**2*(mp.log(2*k/kp**2) + 1j*pi/2)
    y = mp.im(be); k, kp = mp.tanh(y), mp.sech(y)
    return (kp*(gK(k, kp) + 1j*fK(k, kp)))**2*(mp.log(2*k/kp**2) - 1j*pi/2)
out['(C3) direct: lt0 - side integral'] = lt0 - side(hF2L)
mp.mp.dps = dps
for k_, v in out.items():
    print(f'{k_:45s} {mp.nstr(v, 5)}')
print('M =', mp.nstr(M, dps), ' N =', mp.nstr(N, dps))
