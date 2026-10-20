from common import *
import time
mp.dps = 30
t0 = time.time()
ell = log(2)
q_ = lambda n: (4*n+1)*a_(n)**6
D4 = S(lambda n: a_(n)**4*dl_(n)); D6 = S(lambda n: q_(n)*dl_(n))
Vw = S(q_)
T  = S(lambda n: a_(n)**4*h_(n)*(8*h_(n)**2+dl_(n)))
Ln = lambda n: 8*Hc(2*n)-6*Hc(n)-4*ell+2/(4*n+1)
Mn = lambda n: 5*pi**2/3-16*H2c(2*n)+6*H2c(n)-4/(4*n+1)**2
S7 = S(lambda n: q_(n)*(Ln(n)**2+Mn(n)), 40)
Bs = 2*pi**4*Vw
print('S7 - (pi^2 Vw + 2 D6)', S7-(pi**2*Vw+2*D6))
print('input1: S7 - (3Bs/(2pi^2) - 32T/pi^2)', S7-(3*Bs/(2*pi**2)-32*T/pi**2))
I2 = S(lambda n: a_(n)**4*(128*h_(n)**3+24*h_(n)*dl_(n)+tau_(n)))
print('input2: sum a^4(128h^3+24h d+tau) - Bs/2', I2-Bs/2)
core = S(lambda n: a_(n)**4*(8*h_(n)*dl_(n)+tau_(n)))
print('wheel-core: sum a^4(8h d + tau) - pi^2 D6', core-pi**2*D6)
W0 = 8*D4+5*pi*D6
print('W0', W0, ' table 78.57031213654711716068274888671985244')
Wc = S(lambda n: a_(n+1)**4*(8+5*pi*(4*(n+1)+1)*a_(n+1)**2)*dl_(n+1))
print('W0 - Wc - (8+5pi)pi^2/3', W0-Wc-(8+5*pi)*pi**2/3, time.time()-t0)
# d(s), its Mellin form, wheelinner, at sample s
s = mpc('0.25','0.7')
ds = psi(1,0.5-s)-psi(1,1-s)
dint = -4*quad(lambda x: x**(-2*s)*log(x)/(1+x), [0,1])
dmel = 4*B(lambda z: pi/sin(pi*z)/(1-2*s-z)**2, 0.25)
Pt = lambda t: GP([t,t+0.5,0.5-t,1-t],[])
dwi = B(lambda t: Pt(t)/(0.5-s-t)**2, 0.125)/pi
print('d(s):', ds, ' int-d', dint-ds, ' mellin-d', dmel-ds, ' wheelinner-d', dwi-ds)
print('P(t)=2pi^2/sin(2pi t):', Pt(mpc(0.125,0.3))-2*pi**2/sin(2*pi*mpc(0.125,0.3)))
# W0 = (1/pi) B[(8M1+5M2)d] and = sqrt89/pi B[N d]
M1 = lambda s: GP([s]+[0.5-s]*3,[1-s]*3+[0.5+s])
M2 = lambda s: GP([s,s,0.5-s,0.5-s],[1-s,1-s,0.5+s,0.5+s])
dd = lambda s: psi(1,0.5-s)-psi(1,1-s)
BM1d = B(lambda s: M1(s)*dd(s), 0.25); BM2d = B(lambda s: M2(s)*dd(s), 0.25)
print('B[M1 d] - pi D4', BM1d-pi*D4, ' B[M2 d] - pi^2 D6', BM2d-pi**2*D6)
aW = atan(mpf(5)/8)/pi
NW = lambda s: GP([s,s]+[0.5-s]*3,[1-s,1-s,0.5+s,s+aW,1-s-aW])
BNd = B(lambda s: NW(s)*dd(s), 0.25)
HW = pi*BNd   # since B_t[P/(..)^2] = pi d(s)
print('HW =', HW, ' table 82.198372839948704474444779671977025')
print('W0 - sqrt89 HW/pi^2', W0-sqrt(89)*HW/pi**2, time.time()-t0)
# tail bound and asymptotic
for N in [2,5,10,40]:
    tail = Wc - sum(a_(n)**4*(8+5*pi*(4*n+1)*a_(n)**2)*dl_(n) for n in range(1,N))
    bound = (8+20*pi/3)/(54*(N-mpf(3)/4)**3)
    print('N',N,' tail',mp.nstr(tail,8),' bound',mp.nstr(bound,8), ' ok', 0<tail<bound)
n = mpf(10)**6
print('asym ratio summand/(14/(pi^2 n^4))', a_(n)**4*(8+5*pi*(4*n+1)*a_(n)**2)*dl_(n)/(14/(pi**2*n**4)))
# a_n^2 <= 1/(3n+1)
print('max (3n+1)a_n^2 over n<=2000:', max((3*k+1)*a_(mpf(k))**2 for k in range(1,2001)))
# delta integral rep
for k in [0,3]:
    x = k+mpf(1)/4
    print('delta int rep', k, quad(lambda u: u*exp(-x*u)/mp.cosh(u/4),[0,inf])/2-dl_(k), ' bound', dl_(k) < 1/(2*x**2))
