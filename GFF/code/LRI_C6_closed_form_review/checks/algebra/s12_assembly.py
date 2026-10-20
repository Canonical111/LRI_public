from common import *
from mpmath import agm, catalan, binomial, nstr
import time
mp.dps = 32
t0 = time.time()
ell = log(2); A = pi+4*ell; Q = gamma(mpf(1)/4)**4/pi; G = catalan; z3 = zeta(3); z5 = zeta(5)
# C212 by Euler-weighted alternating sum
def C212(N):
    T = [mpf(0)]*(2*N+2); h2 = mpf(0); acc = mpf(0)
    # T(n) = sum_{m<n} (1/m) H2_{m-1}
    Hm1 = mpf(0)  # H^{(2)}_{m-1}
    for n in range(1, 2*N+2):
        T[n] = acc
        acc += Hm1/n; Hm1 += mpf(1)/n**2
    b = [T[2*k]/(4*mpf(k)**2) for k in range(1, N+1)]  # k=1..N, sign (-1)^k
    s = mpf(0); cum = mpf(0)
    for i in range(N):
        cum += binomial(N, i); w = 1-cum/mpf(2)**N
        s += (-1)**(i+1)*w*b[i]
    return s
c1, c2 = C212(150), C212(220)
print('C212', c1, c2-c1, ' table 0.032383901800869146760958099191565833')
C212v = c2
L3 = -quad(lambda t: log(2*sin(t/2))**2, [0, pi/2])
Ereal = Q/8*(63*A**3+120*A*G+79*A*pi**2+2013*pi**3+54204*z3)+Q**2*(29*pi-249*A) + (mpf(21)/640*A**5+mpf(7)/64*A**3*pi**2+mpf(1149)/64*A**2*pi**3+mpf(7863)/16*A**2*z3+192*A*G*(16*G+3*pi**2)+mpf(14853)/640*A*pi**4-mpf(15776)/3*G*pi**3-mpf(145153)/128*pi**5+mpf(722279)/48*pi**2*z3-mpf(805959)/8*z5)
# ordinary G values by line integrals
X4 = 42*A**2+18*A*pi+1227*pi**2-96*Q; Y4 = mpf(105)/4*A**2+9*A*pi+mpf(2469)/4*pi**2-60*Q
rho4 = sqrt(X4**2+Y4**2); a4 = atan(Y4/X4)/pi
G4 = B(lambda s: GP([s,s]+[0.5-s]*3,[1-s,1-s,0.5+s,s+a4,1-s-a4]),0.25).real
a6 = atan(mpf(11)/13)/pi
G6 = B(lambda s: GP([s]*4+[0.5-s]*5,[1-s]*2+[0.5+s,s+a6,1-s-a6]),0.25).real
r2 = sqrt(2); rho8 = sqrt(2177203-1028322*r2); d8 = atan(556/(1233-417*r2))/(2*pi); e8 = mp.acosh((1233-139*r2)/rho8)/(2*pi)
ap, am = mpc(d8,e8), mpc(d8,-e8)
G8 = B(lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*5+[0.5+s,0.25-s,s+ap,1-s-ap,s+am,1-s-am]),0.25).real
q2 = 259*A-49*pi; q1 = 481*A-539*pi; q0 = 407*A-1127*pi
d7 = sqrt(q1**2-4*q2*q0); rho7 = sqrt((q2-q0)**2+q1**2)
ep = atan((q1+d7)/(2*q2))/pi; em = atan((q1-d7)/(2*q2))/pi
G7 = B(lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*4+[0.25-s,s+ep,1-s-ep,s+em,1-s-em]),0.25).real
print('G4,G6,G8,G7', G4, G6, G8, G7, time.time()-t0)
aW = atan(mpf(5)/8)/pi
HW = (pi*B(lambda s: GP([s,s]+[0.5-s]*3,[1-s,1-s,0.5+s,s+aW,1-s-aW])*(psi(1,0.5-s)-psi(1,1-s)),0.25)).real
beta = atan((13+1j*sqrt(139))/14)/pi; bb = mp.conj(beta)
H7 = (B(lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*4+[0.25-s,s+beta,1-s-beta,s+bb,1-s-bb])*(psi(0,1-2*s)+euler),0.25)/pi).real
def gth(th):
    Kx = pi/(2*agm(1, cos(th/2))); Kc = pi/(2*agm(1, sin(th/2)))
    return [4*Kx**2/pi**1.5, 4*Kx*Kc/pi**1.5, 2*(Kc**2-Kx**2)/pi**1.5]
lam = mp.findroot(lambda l: 4*l**3-112*l**2+909*l-2250, 15.98)
es = sqrt(40*lam-279)/20; chi = 2*(21*lam-150)/(40*lam-279)
vp = [1, mpf(21)/20+es, lam/10+es*chi]; vm = [1, mpf(21)/20-es, lam/10-es*chi]
Hstar = 2*quad(lambda th: sum(vp[j]*gth(th)[j] for j in range(3))*sum(vm[k]*gth(pi/2-th)[k] for k in range(3)), [0,pi/8,pi/4,3*pi/8,pi/2])
print('HW,H7,H*', HW, H7, Hstar, time.time()-t0)
total = Ereal - 2176*((32*G+9*pi**2)*L3+128*C212v) - 4*pi**2*rho4*G4 + 192*pi*sqrt(290)*G6 + 16*pi**3*rho8*G8 - 393*pi*sqrt(89)*HW + 24*pi**1.5*(rho7*G7+196*pi*sqrt(185)*H7) + 7680*pi**3*Hstar
ref = mpf('14331.6870327580543204454632552462171183173230619887904582')
print('C6 from eq:preferred:', total/2187, ' ref', ref, ' diff', total/2187-ref)
W0 = sqrt(89)*HW/pi**2
print('-393pi^3W0/2187', -393*pi**3*W0/2187, ' table -437.775914461168923635033332127009')
print('n=0 wheel term: -393pi^3(8+5pi)pi^2/3 - (-1048pi^5-655pi^6) =', -393*pi**3*(8+5*pi)*pi**2/3+1048*pi**5+655*pi**6)
r1 = -393*pi**3*W0/2187; r2_ = 24*pi**1.5*(rho7*G7+196*pi*sqrt(185)*H7)/2187; r3 = 7680*pi**3*Hstar/2187
print('sum of residuals', r1+r2_+r3, ' table 9046.984177866241240164294298754541')
