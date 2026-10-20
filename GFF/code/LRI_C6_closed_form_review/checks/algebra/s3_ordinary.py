from common import *
import time
mp.dps = 30
t0=time.time()
U4 = S(lambda n: a_(n)**4)
U6 = S(lambda n: (4*n+1)*a_(n)**6)
U8 = S(lambda n: (4*n+1)*a_(n)**8)
print('U4',U4,'U6',U6,'U8',U8, time.time()-t0)
M1 = lambda s: GP([s]+[0.5-s]*3,[1-s]*3+[0.5+s])
M2 = lambda s: GP([s,s,0.5-s,0.5-s],[1-s,1-s,0.5+s,0.5+s])
M0 = lambda s: GP([0.5-s]*4,[1-s]*4)
K  = lambda s: GP([s,s]+[0.5-s]*4,[1-s]*2)
g13 = B(M1, 0.25); g22 = B(M2, 0.25)
print('g13 - pi U4 =', g13-pi*U4)
print('g22 - pi^2 U6/2 =', g22-pi**2*U6/2)
print('B[M0] =', B(M0,0.25))
print('B[K]/pi^5 - U6/(2pi) =', B(K,0.25)/pi**5-U6/(2*pi))
# residue form of g22: 8 sum a^4 h
print('8 sum a^4 h - g22', 8*S(lambda n: a_(n)**4*h_(n)) - g22, time.time()-t0)
# --- sixth block
Mj6 = lambda j: (lambda s: RR(s,6)*TAN(s)**(6-j))
X35 = pi**2*(B(Mj6(1),0.25)+B(Mj6(3),0.25)); X44 = pi**2*(B(Mj6(2),0.25)+B(Mj6(4),0.25))
X35s = 3*pi**2*S(lambda n: a_(n)**6*(24*h_(n)**2+dl_(n))); X44s = 24*pi**3*S(lambda n: a_(n)**6*h_(n))
print('X35 line-series', X35-X35s, ' X44 line-series', X44-X44s)
Pb_series = 24*pi**3*S(lambda n: a_(n)**6*(312*h_(n)**2+13*dl_(n)+88*pi*h_(n)))
print('Pb - 8pi(13X35+11X44)', Pb_series-8*pi*(13*X35s+11*X44s))
Q = gamma(mpf(1)/4)**4/pi
r = lambda x, y, n: exp(loggamma(x+n)-loggamma(x)-loggamma(y+n)+loggamma(y))
Hm = S(lambda n: r(mpf(1)/4, mpf(3)/4, n)**6)
H0 = S(lambda n: a_(n)**6)
Hp = S(lambda n: r(mpf(3)/4, mpf(5)/4, n)**6)
Pb_input = 6*Q**3/pi*(2*Hm-1) - 104*pi**5*H0 + 2**18*pi**5/Q**3*Hp
print('Pb input', Pb_input, ' series', Pb_series, ' diff', Pb_input-Pb_series, time.time()-t0)
a6 = atan(mpf(11)/13)/pi
N6 = lambda s: GP([s]*4+[0.5-s]*5,[1-s]*2+[0.5+s,s+a6,1-s-a6])
G6 = B(N6, 0.25)
print('B6=24Pb vs 192 pi sqrt290 G6', 24*Pb_series - 192*pi*sqrt(290)*G6)
# --- eighth block
r2 = sqrt(2); aa = 1233-278*r2; bb = mpf(556); cc = 139*r2
y = lambda n: n+mpf(1)/4
B8s = 8*pi**4*S(lambda n: a_(n)**8*((2466-834*r2)*pi**2*y(n)-1112*pi*(1-16*y(n)*h_(n))+139*r2*(256*y(n)*h_(n)**2-32*h_(n)+8*y(n)*dl_(n))))
def Yr(rr):
    t = mpf(rr)/8
    return S(lambda n: (t+n)*exp(8*(loggamma(t+0.25+n)-loggamma(t+0.75+n))))
B8in = pi**6*(4932-5004*r2)*U8 + 556*pi**2*((17+12*r2)*Yr(1)-(17-12*r2)*Yr(7))
print('B8 input', B8in, ' series', B8s, ' diff', B8in-B8s, time.time()-t0)
Kj = lambda j: B(lambda s: (0.25-s)*RR(s,8)*TAN(s)**(8-j), 0.25)
K1,K2,K3 = Kj(1),Kj(2),Kj(3)
K1s = pi**3*S(lambda n: a_(n)**8*y(n)); K2s = pi**2*S(lambda n: a_(n)**8*(16*y(n)*h_(n)-1)); K3s = pi*S(lambda n: a_(n)**8*(y(n)*(128*h_(n)**2+4*dl_(n)-pi**2)-16*h_(n)))
print('K1,K2,K3 line-series', K1-K1s, K2-K2s, K3-K3s)
print('B8 - 16pi^3(aK1+bK2+cK3)', B8s-16*pi**3*(aa*K1s+bb*K2s+cc*K3s))
rho8 = sqrt(2177203-1028322*r2); d8 = atan(556/(1233-417*r2))/(2*pi); e8 = mp.acosh((1233-139*r2)/rho8)/(2*pi)
ap, am = mpc(d8,e8), mpc(d8,-e8)
ker8 = lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*5+[0.5+s,0.25-s,s+ap,1-s-ap,s+am,1-s-am])
G8 = B(ker8, 0.25)
print('B8 - 16pi^3 rho8 G8', B8s-16*pi**3*rho8*G8, ' G8', G8, time.time()-t0)
# --- lower block assembly
A = pi+4*log(2)
X4 = 42*A**2+18*A*pi+1227*pi**2-96*Q; Y4 = mpf(105)/4*A**2+9*A*pi+mpf(2469)/4*pi**2-60*Q
rho4 = sqrt(X4**2+Y4**2); a4 = atan(Y4/X4)/pi
N4 = lambda s: GP([s,s]+[0.5-s]*3,[1-s,1-s,0.5+s,s+a4,1-s-a4])
G4 = B(N4, 0.25)
Blow_in = 4*pi**3*(-X4)*U4 + 2*pi**4*(-Y4)*U6
print('Blow input - (-4pi^2 rho4 G4)', Blow_in + 4*pi**2*rho4*G4, time.time()-t0)
