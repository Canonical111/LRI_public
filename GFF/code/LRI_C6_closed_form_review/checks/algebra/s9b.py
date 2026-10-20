from common import *
from mpmath import agm, matrix
import time
mp.dps = 30
t0 = time.time()
def gth(th):
    # x = sin^2 th: m = sin^2(th/2)
    Kx = pi/(2*agm(1, cos(th/2))); Kc = pi/(2*agm(1, sin(th/2)))
    return [4*Kx**2/pi**1.5, 4*Kx*Kc/pi**1.5, 2*(Kc**2-Kx**2)/pi**1.5]
Hm = [[mpf(0)]*3 for _ in range(3)]
for j in range(3):
    for k in range(3):
        Hm[j][k] = 2*quad(lambda th: gth(th)[j]*gth(pi/2-th)[k], [0, pi/8, pi/4, 3*pi/8, pi/2])
print('symmetry', Hm[0][1]-Hm[1][0], Hm[1][2]-Hm[2][1], Hm[0][2]-Hm[2][0], time.time()-t0)
H11,H12,H13,H22,H23,H33 = Hm[0][0],Hm[0][1],Hm[0][2],Hm[1][1],Hm[1][2],Hm[2][2]
print('H33+2H13-H22 =', H33+2*H13-H22)
Pa = 8*pi**3*(10*H11+21*H12+18*H22+15*H23)
print('P_a (four H) =', Pa, ' table 334926.04524805183788322200124007778661')
gh = [[1,0,0],[1,1,0],[2,2,2]]
def Iij(i,j): return sum(gh[i][a]*gh[j][b]*Hm[a][b] for a in range(3) for b in range(3))/pi
print('P_a input pi^4(15I22+24I11-4I00) =', pi**4*(15*Iij(2,2)+24*Iij(1,1)-4*Iij(0,0)))
print('relation I22-4I12+4I02-4I00 =', Iij(2,2)-4*Iij(1,2)+4*Iij(0,2)-4*Iij(0,0))
lam = mp.findroot(lambda l: 4*l**3-112*l**2+909*l-2250, 15.98)
es = sqrt(40*lam-279)/20; chi = 2*(21*lam-150)/(40*lam-279)
Bp, Bm = mpf(21)/20+es, mpf(21)/20-es; Cp, Cm = lam/10+es*chi, lam/10-es*chi
vp = [1,Bp,Cp]; vm = [1,Bm,Cm]
fpfm = sum(vp[j]*vm[k]*Hm[j][k] for j in range(3) for k in range(3))
print('<f+,f-> =', fpfm, ' table H* 135.02348601116092499084881978216882', ' 80pi^3<f+,f-> - Pa', 80*pi**3*fpfm-Pa)
print('96 Pa/2187', 96*Pa/2187, ' table 14701.829146690890003104395116162537', time.time()-t0)
# direct 1D Barnes check of H*: H* = <F+,F-> with F_sigma = B_s[k_sigma x^-s], k = Gamma(s)^3 Gamma(1/2-s)^2/(Gamma(1/2+s) prod)
bp = atan(Bp/2+1j*sqrt(Cp-Bp**2/4))/pi; bm = atan(Bm/2+1j*sqrt(Cm-Bm**2/4))/pi
Dp = sqrt((1-Cp)**2+Bp**2); Dm = sqrt((1-Cm)**2+Bm**2)
print('D+, D-', Dp, Dm, Dp*Dm)
mp.dps = 20
xs = mpf('0.37')
for (b, Bs, Cs, D) in [(bp,Bp,Cp,Dp),(bm,Bm,Cm,Dm)]:
    k = lambda s: GP([s]*3+[0.5-s]*2,[0.5+s,s+b,1-s-b,s+mp.conj(b),1-s-mp.conj(b)])
    Fx = B(lambda s: k(s)*xs**(-s), 0.25)
    g = gth(mp.asin(sqrt(xs)))
    print('f_sigma/D_sigma vs Barnes kernel:', (g[0]+Bs*g[1]+Cs*g[2])/D - Fx)
