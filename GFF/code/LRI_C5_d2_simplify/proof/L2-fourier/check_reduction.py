# Quick (<= 30 digit) checks of the Fourier -> elliptic reduction used in the L2-fourier proof.
# Run: <HOME>/anaconda3/bin/python3 check_reduction.py [dps]
# Checks:
#  (1) Cauchy beta integral: int_{-pi}^{pi} (2cos(th/2))^{-x} e^{i s th} dth = 2 pi Gamma(1-x)/(Gamma(u+s)Gamma(u-s)), u=1-x/2
#  (2) Q_x(phi) = (P_x*P_x)(phi) = (2k)^{1-2x} B(1/2,1-x) 2F1(1/2,1/2;3/2-x;k^2), k=cos(phi/4); Q_{1/2} = 2K(k)
#  (3) dQ/dx at x=1/2 equals pi K(k') - 2 K(k) log(4 k k')
#  (4) A(1/2)=4 m0/pi = pi^2 a, B(1/2)=4 m1/pi = pi^2 b (m0=int K(sin b)^2 db, m1=int K(sin b)K(cos b) db over (0,pi/2))
#  (5) (E1) l0 - log2 m0 + (pi/2) m1 = 0,  (E2) l1 - log2 m1 + (pi/4) m0 = 0,  l_j with weight log(2 sin 2b)
#  (6) A'(1/2), B'(1/2) from the elliptic formulas vs. the 70-digit single sums (Sy, Sxy) of confirm_dps70.json
#  (7) A'(x), B'(x) by finite differences of the 2F1 representation (independent of the elliptic log formula)
import sys, json, mpmath as mp
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 25
mp.mp.dps = dps + 5
pi, l2 = mp.pi, mp.log(2)
K = lambda k: mp.ellipk(k**2)          # modulus convention
out = {}

# (1) Cauchy beta integral at a generic point
x, s = mp.mpf('0.37'), mp.mpf('0.61')
u = 1 - x/2
lhs = mp.quad(lambda th: (2*mp.cos(th/2))**(-x)*mp.cos(s*th), [-pi, 0, pi])
rhs = 2*pi*mp.gamma(1-x)/(mp.gamma(u+s)*mp.gamma(u-s))
out['(1) Cauchy beta integral'] = lhs - rhs

# (2) Q_x(phi): direct convolution vs closed form
def Qdirect(x, phi):
    # (P*P)(phi) = int_{phi-pi}^{pi} (2cos(th/2))^{-x} (2cos((phi-th)/2))^{-x} dth, 0<=phi<2pi
    return mp.quad(lambda th: (2*mp.cos(th/2))**(-x)*(2*mp.cos((phi-th)/2))**(-x), [phi-pi, phi/2, pi])
def Qclosed(x, phi):
    k = mp.cos(phi/4)
    return (2*k)**(1-2*x)*mp.beta(mp.mpf(1)/2, 1-x)*mp.hyp2f1(mp.mpf(1)/2, mp.mpf(1)/2, mp.mpf(3)/2-x, k**2)
for (x, phi) in [(mp.mpf('0.5'), mp.mpf('1.3')), (mp.mpf('0.43'), mp.mpf('4.1')), (mp.mpf('0.6'), mp.mpf('0.7'))]:
    out[f'(2) Q direct-closed x={x} phi={phi}'] = Qdirect(x, phi) - Qclosed(x, phi)
phi = mp.mpf('2.2')
out['(2) Q_{1/2} - 2K(cos(phi/4))'] = Qclosed(mp.mpf(1)/2, phi) - 2*K(mp.cos(phi/4))

# (3) x-derivative of Q at x=1/2
for phi in [mp.mpf('0.9'), mp.mpf('3.7'), mp.mpf('5.9')]:
    k = mp.cos(phi/4); kp = mp.sin(phi/4)
    num = mp.diff(lambda xx: Qclosed(xx, phi), mp.mpf(1)/2)
    out[f'(3) dQ/dx - [pi K(kp) - 2K(k)log(4kk\')] phi={phi}'] = num - (pi*K(kp) - 2*K(k)*mp.log(4*k*kp))

# (4),(5) angle moments.  Fold (0,pi/2) onto (0,pi/4] (beta -> pi/2-gamma) and use K(k)=pi/(2 agm(1,k')),
# so that the logarithmic endpoint singularity sits at gamma=0 where floating point resolves it.
Kc = lambda s, c: pi/(2*mp.agm(1, c))     # K(s) given s=sin, c=cos (complementary modulus c)
def fold(H):
    # int_0^{pi/2} H(sin b, cos b) db = int_0^{pi/4} [H(sin g,cos g) + H(cos g, sin g)] dg
    return mp.quad(lambda g: H(mp.sin(g), mp.cos(g)) + H(mp.cos(g), mp.sin(g)), [0, pi/8, pi/4])
F2 = lambda s, c: Kc(s, c)**2
FG = lambda s, c: Kc(s, c)*Kc(c, s)
LG = lambda s, c: mp.log(4*s*c)           # log(2 sin 2b)
m0 = fold(F2); m1 = fold(FG)
l0 = fold(lambda s, c: F2(s, c)*LG(s, c)); l1 = fold(lambda s, c: FG(s, c)*LG(s, c))
import os
d = json.load(open(os.environ.get('CONFIRM_JSON', '<PROJECT>/LRI_C5_d2_simplify/confirm_dps70.json')))
S = lambda key: mp.mpf(d['singles'][key])
a = S("('L', (0, 0, 0, 0, 0, 0, 0))")
b = -2*S("('L', (1, 0, 0, 0, 0, 0, 0))")/pi
Sy = S("('L', (0, 0, 0, 1, 0, 0, 0))")
Sxy = 4*S("('L', (1, 0, 0, 1, 0, 0, 0))") + S("('L', (0, 0, 0, 0, 1, 0, 0))")
A0, B0 = pi**2*a, pi**2*b
out['(4) 4 m0/pi - pi^2 a'] = 4*m0/pi - A0
out['(4) 4 m1/pi - pi^2 b'] = 4*m1/pi - B0
out['(5) E1: l0 - log2 m0 + (pi/2) m1'] = l0 - l2*m0 + pi/2*m1
out['(5) E2: l1 - log2 m1 + (pi/4) m0'] = l1 - l2*m1 + pi/4*m0

# (6) A'(1/2), B'(1/2): elliptic formulas vs single sums
V0, V1 = 32*m0, 16*m1
V0p, V1p = 32*(pi*m1 - 2*l0), 16*(pi*m0 - 2*l1)
psih = mp.digamma(mp.mpf(1)/2)
Ap = (V0p + 4*psih*V0)/(8*pi)
Bp = (V1p + 4*psih*V1)/(4*pi)
out['(6) A\'(1/2) [elliptic] - (pi B + 4pi^2 (Sy + psi(1/2) a)) [sums]'] = Ap - (pi*B0 + 4*pi**2*(Sy + psih*a))
out['(6) -2pi B\'(1/2) [elliptic] - (-4pi^4 a + 4pi^2 Sxy - 8pi^3 psi(1/2) b) [sums]'] = -2*pi*Bp - (-4*pi**4*a + 4*pi**2*Sxy - 8*pi**3*psih*b)
g = mp.euler
out['(6) A\'(1/2) - [2pi B - (10log2+4gamma) A]'] = Ap - (2*pi*B0 - (10*l2 + 4*g)*A0)
out['(6) B\'(1/2) - [(3pi/2) A - (10log2+4gamma) B]'] = Bp - (3*pi/2*A0 - (10*l2 + 4*g)*B0)

# (7) independent: A(x)=pi V0(x)/(8 Gamma(1-x)^4), B(x)=pi V1(x)/(4 Gamma(1-x)^4) via the 2F1 form of Q_x,
#     written in k = sin(beta): V0 = 8 int_0^{pi/2} Qt(sin b)^2 db, V1 = 4 int_0^{pi/2} Qt(sin b) Qt(cos b) db,
#     Qt(k) = (2k)^{1-2x} B(1/2,1-x) 2F1(1/2,1/2;3/2-x;k^2). Central differences in x.
def Qt(x, k, kp):
    z = k**2
    if 1 - z < mp.mpf(10)**(-mp.mp.dps + 3):
        return mp.mpf(0)                       # measure-zero endpoint; neglected piece ~ eps log^2 eps
    return (2*k)**(1-2*x)*mp.beta(mp.mpf(1)/2, 1-x)*mp.hyp2f1(mp.mpf(1)/2, mp.mpf(1)/2, mp.mpf(3)/2-x, z)
def V(x, kk):
    if kk == 0:
        return 8*fold(lambda s, c: Qt(x, s, c)**2)
    return 4*fold(lambda s, c: Qt(x, s, c)*Qt(x, c, s))
if dps <= 20:
    Afun = lambda x: pi*V(x, 0)/(8*mp.gamma(1-x)**4)
    Bfun = lambda x: pi*V(x, 1)/(4*mp.gamma(1-x)**4)
    h = mp.mpf('1e-3')
    xh = mp.mpf(1)/2
    Ad = (-Afun(xh+2*h) + 8*Afun(xh+h) - 8*Afun(xh-h) + Afun(xh-2*h))/(12*h)
    Bd = (-Bfun(xh+2*h) + 8*Bfun(xh+h) - 8*Bfun(xh-h) + Bfun(xh-2*h))/(12*h)
    out['(7) A(1/2) [2F1 form] - pi^2 a'] = Afun(xh) - A0
    out['(7) B(1/2) [2F1 form] - pi^2 b'] = Bfun(xh) - B0
    out['(7) A\'(1/2) finite diff (h=1e-3, O(h^4)) - elliptic'] = Ad - Ap
    out['(7) B\'(1/2) finite diff (h=1e-3, O(h^4)) - elliptic'] = Bd - Bp
mp.mp.dps = dps
for k_, v in out.items():
    print(f'{k_:75s} {mp.nstr(v, 5)}')
print('a  =', mp.nstr(a, dps), '\nb  =', mp.nstr(b, dps))
print('m0 =', mp.nstr(m0, dps), ' m1 =', mp.nstr(m1, dps))

# (8) structural collapse  L_2 = -6A^2 - 8B^2 + (4/pi)(A B' + A' B) - (32/pi) psi(1/2) A B   (all at x=1/2)
mp.mp.dps = dps + 5
L2_struct = -6*A0**2 - 8*B0**2 + 4/pi*(A0*Bp + Ap*B0) - 32/pi*psih*A0*B0
L2_finder = mp.mpf(d['checks']['L2'])
Bm, Bpl = mp.mpf(d['B-']), mp.mpf(d['B+'])
P4 = (Bm**2 - Bpl**2)/(4*pi**3)
res8 = {'(8) L2 structural [elliptic A,B,A\',B\'] - L2 [70-digit series]': L2_struct - L2_finder,
        '(8) 8AB/pi - (B-^2-B+^2)/(4pi^3)': 8*A0*B0/pi - P4,
        '(8) L2 + 2 log2 P4(2)': L2_struct + 2*l2*P4,
        '(8) structural-form in sums: 2pi^4a^2-4pi^4b^2+16pi^3 b Sy-8pi^2 a Sxy - L2': 2*pi**4*a**2 - 4*pi**4*b**2 + 16*pi**3*b*Sy - 8*pi**2*a*Sxy - L2_finder,
        '(8) gap between collapse forms: pi^4a^2+2pi^4b^2-8pi^3 b Sy-4pi^2 a Sxy': pi**4*a**2 + 2*pi**4*b**2 - 8*pi**3*b*Sy - 4*pi**2*a*Sxy}
mp.mp.dps = dps
for k_, v in res8.items():
    print(f'{k_:75s} {mp.nstr(v, 5)}')
