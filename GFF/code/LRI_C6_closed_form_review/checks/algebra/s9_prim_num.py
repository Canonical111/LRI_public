from common import *
from mpmath import hyp2f1, ellipk, meijerg, acos, matrix
import time
mp.dps = 30
t0 = time.time()
Q = gamma(mpf(1)/4)**4/pi; sQ = sqrt(Q); ell = log(2)
v = lambda z: hyp2f1(0.25,0.25,1,z)
hh = lambda z: hyp2f1(0.25,0.25,0.5,z)
eps = mpf(10)**-40
mp.dps = 50
for x in [mpf(-0.7), mpf(-3)]:
    z = mpc(x, eps)
    f = v(z); g = sQ*hh(1-z)/pi - v(z); fs = v(1-z); gs = sQ*hh(z)/pi - v(1-z)
    print('x<0', x, ' f', mp.nstr(f,12), ' g+i f:', mp.nstr(g+1j*f.real,6), ' fs', mp.nstr(fs,12), ' gs-conj(fs)', mp.nstr(gs-mp.conj(fs),6))
for x in [mpf(1.7), mpf(4)]:
    z = mpc(x, eps)
    f = v(z); g = sQ*hh(1-z)/pi - v(z); fs = v(1-z); gs = sQ*hh(z)/pi - v(1-z)
    print('x>1', x, ' f', mp.nstr(f,12), ' g-conj f', mp.nstr(g-mp.conj(f),6), ' fs', mp.nstr(fs,12), ' gs - (re + i fs):', mp.nstr(gs.imag-fs.real,6), mp.nstr(fs.imag,3))
    # connection formula
    print('   connection', mp.nstr(v(z) - (sQ/(2*pi)*hh(1-z) - 2/sQ*sqrt(1-z)*hyp2f1(0.75,0.75,1.5,1-z)),6))
mp.dps = 30
# small-x behaviour and Frobenius/elliptic matching
for x in [mpf('0.3'), mpf('0.85')]:
    m = x/(2*(1+sqrt(1-x))); Kx = ellipk(m); Kc = ellipk(1-m)
    p0 = v(x)**2; p1 = sQ*v(x)*hh(1-x); p2 = Q*hh(1-x)**2
    g1 = meijerg([[],[0.5]*3],[[0]*1,[0]*2],x) if False else None
    G = lambda j: meijerg([[0.5]*(3-j),[0.5]*j],[[0]*j,[0]*(3-j)],x)
    g1,g2,g3 = G(1),G(2),G(3)
    print('x',x,' v-2K/pi', v(x)-2*Kx/pi, ' sQh(1-x)-2(K+Kc)', sQ*hh(1-x)-2*(Kx+Kc))
    print('   g1-sqrt(pi)p0', g1-sqrt(pi)*p0, ' g2-(p1-pi p0)/sqrt(pi)', g2-(p1-pi*p0)/sqrt(pi), ' g3-(p2-2pi p1)/(2pi^1.5)', g3-(p2-2*pi*p1)/(2*pi**1.5))
    print('   elliptic g:', g1-4*Kx**2/pi**1.5, g2-4*Kx*Kc/pi**1.5, g3-2*(Kc**2-Kx**2)/pi**1.5)
x = mpf('1e-6'); L = -log(x)
print('sQ h(1-x) - (L+pi+6l) at 1e-6:', sQ*hh(1-x)-(L+pi+6*ell))
# pairings via elliptic forms with x = sin^2(theta)
def gvals(x):
    m = x/(2*(1+sqrt(1-x))); Kx = ellipk(m); Kc = ellipk(1-m)
    return [4*Kx**2/pi**1.5, 4*Kx*Kc/pi**1.5, 2*(Kc**2-Kx**2)/pi**1.5]
def pair_all():
    # returns matrix Hjk = <g_j,g_k> = int_0^1 g_j(x) g_k(1-x)/sqrt(x(1-x)) dx = 2 int_0^{pi/2} g_j(sin^2) g_k(cos^2) dth
    def F(th, j, k):
        x = sin(th)**2; xc = cos(th)**2
        return 2*gvals(x)[j]*gvals(xc)[k]
    Hm = [[None]*3 for _ in range(3)]
    for j in range(3):
        for k in range(3):
            Hm[j][k] = quad(lambda th: F(th,j,k), [0, pi/4, pi/2])
    return Hm
Hm = pair_all()
print('H symmetric?', Hm[0][1]-Hm[1][0], Hm[1][2]-Hm[2][1], Hm[0][2]-Hm[2][0], time.time()-t0)
H11,H12,H13,H22,H23,H33 = Hm[0][0],Hm[0][1],Hm[0][2],Hm[1][1],Hm[1][2],Hm[2][2]
print('H33+2H13-H22 =', H33+2*H13-H22)
Pa = 8*pi**3*(10*H11+21*H12+18*H22+15*H23)
print('P_a (four H) =', Pa, ' table 334926.04524805183788322200124007778661')
# primitive input form with I_ij
gh = [[1,0,0],[1,1,0],[2,2,2]]
def Iij(i,j): return sum(gh[i][a]*gh[j][b]*Hm[a][b] for a in range(3) for b in range(3))/pi
print('P_a input pi^4(15I22+24I11-4I00) =', pi**4*(15*Iij(2,2)+24*Iij(1,1)-4*Iij(0,0)))
print('relation I22-4I12+4I02-4I00 =', Iij(2,2)-4*Iij(1,2)+4*Iij(0,2)-4*Iij(0,0))
# lambda*, B, C, beta, D
lam = mp.findroot(lambda l: 4*l**3-112*l**2+909*l-2250, 15.98)
lam2 = (28+sqrt(409)*cos(acos(7298/(409*sqrt(409)))/3))/3
print('lambda*', lam, ' explicit-lambda', lam2-lam)
es = sqrt(40*lam-279)/20; chi = 2*(21*lam-150)/(40*lam-279)
Bp, Bm = mpf(21)/20+es, mpf(21)/20-es; Cp, Cm = lam/10+es*chi, lam/10-es*chi
print('radicands 40lam-279', 40*lam-279, ' C-B^2/4:', Cp-Bp**2/4, Cm-Bm**2/4)
vp = matrix([1,Bp,Cp]); vm = matrix([1,Bm,Cm])
Mm = matrix([[10,10.5,0],[10.5,18,7.5],[0,7.5,0]]); Nm = matrix([[0,0,1],[0,-1,0],[1,0,1]])
print('M+lam N - 5(v+v-^T+v-v+^T) max:', mp.mnorm(Mm+lam*Nm-5*(vp*vm.T+vm*vp.T),1))
Pp = lambda z: z**2+Bp*z+Cp; Pm = lambda z: z**2+Bm*z+Cm
print('P+(i)P-(i)', Pp(1j)*Pm(1j), ' D+D-', sqrt((1-Cp)**2+Bp**2)*sqrt((1-Cm)**2+Bm**2))
bp = atan(Bp/2+1j*sqrt(Cp-Bp**2/4))/pi; bm = atan(Bm/2+1j*sqrt(Cm-Bm**2/4))/pi
th = mpc('0.4','0.2')
Dp = sqrt((1-Cp)**2+Bp**2)
print('P+ factorization', Pp(tan(th)) - Dp*sin(th+pi*bp)*sin(th+pi*mp.conj(bp))/cos(th)**2)
fpm = 10*(Hm[0][0] + (Bm+Bp)*Hm[0][1] + Bp*Bm*Hm[1][1] + (Cp+Cm)*Hm[0][2] + (Bp*Cm+Bm*Cp)*Hm[1][2] + Cp*Cm*Hm[2][2])/2*2/2
# <f+,f-> = sum_jk v+_j v-_k H_jk
fpfm = sum(vp[j]*vm[k]*Hm[j][k] for j in range(3) for k in range(3))
print('<f+,f-> =', fpfm, ' table H* 135.02348601116092499084881978216882', ' 80pi^3<f+,f-> - Pa', 80*pi**3*fpfm-Pa)
print('96 Pa/2187', 96*Pa/2187, ' table 14701.829146690890003104395116162537', time.time()-t0)
