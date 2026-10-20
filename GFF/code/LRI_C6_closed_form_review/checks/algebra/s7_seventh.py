from common import *
import time
mp.dps = 30
t0 = time.time()
ell = log(2); A = pi+4*ell
q2 = 259*A-49*pi; q1 = 481*A-539*pi; q0 = 407*A-1127*pi
print('signs q2,q1,q0:', q2, q1, q0)
d7 = sqrt(q1**2-4*q2*q0); rho7 = sqrt((q2-q0)**2+q1**2)
etap = atan((q1+d7)/(2*q2))/pi; etam = atan((q1-d7)/(2*q2))/pi
beta = atan((13+1j*sqrt(139))/14)/pi; betab = mp.conj(beta)
print('beta7', beta, ' atan(conj)=conj?', atan((13-1j*sqrt(139))/14)/pi - betab)
def Fn(n):
    y = n+mpf(1)/4; h = h_(n); dl = dl_(n)
    u = 1-14*y*h; v = 196*y*h**2-28*h+7*y*(dl-pi**2)
    T = 80*pi**2*y-26*pi*u+11*v; K = 28*pi**2*y-10*pi*u+3*v
    return (98*Hc(2*n)+74*ell-6*pi)*T-98*pi*K-98*(11*u-13*pi*y)*(pi**2/3+4*H2c(2*n))-8624*y*(zeta(3)-H3c(2*n))
F0 = 39886*ell**3-10906*pi*ell**2-22792*ell**2-2188*pi**2*ell+8156*pi*ell-mpf(1679)/6*pi**3+mpf(2330)/3*pi**2-2156*zeta(3)
print('F0 check', Fn(0)-F0, ' F0=', F0)
Y = lambda s: 0.25-s
R = lambda s: RR(s,7)
SEC = lambda s: GP([0.5+s,0.5-s],[])/pi   # sec(pi s) = Gamma(1/2+s)Gamma(1/2-s)/pi
Psi = lambda s: psi(0,1-2*s)+euler
p = lambda z: 7*z**2+13*z+11
qq = lambda z: q2*z**2+q1*z+q0
I = lambda s: Y(s)*R(s)*SEC(s)*TAN(s)**4*(196*p(TAN(s))*Psi(s)+qq(TAN(s)))
Mj = lambda j: (lambda s: Y(s)*R(s)*SEC(s)*TAN(s)**(7-j))
def res(f, s0, r=mpf('0.3')):
    return quad(lambda th: f(s0+r*exp(1j*th))*r*exp(1j*th), [0, pi, 2*pi])/(2*pi)
for n in range(0,4):
    y = n+mpf(1)/4; h = h_(n); dl = dl_(n); c = (-1)**n*a_(n)**7
    r1 = res(Mj(1),-n)/c - pi**2.5*y
    r2 = res(Mj(2),-n)/c - pi**1.5*(14*y*h-1)
    r3 = res(Mj(3),-n)/c - sqrt(pi)*(y*(98*h**2+7*dl/2-pi**2/2)-14*h)
    rI = res(I,-n) - sqrt(pi)*c*Fn(n)
    print('n',n,' M1',mp.nstr(r1,3),' M2',mp.nstr(r2,3),' M3',mp.nstr(r3,3),' ResI-sqrt(pi)(-1)^n a^7 F', mp.nstr(rI,3), ' |ResI|', mp.nstr(abs(res(I,-n)),6))
    print('   Psi(-n)-H2n', Psi(mpf(-n))-Hc(2*n), " Psi'+..", mp.diff(Psi,-n)-(2*H2c(2*n)-pi**2/3), " Psi''", mp.diff(Psi,-n,2)+8*(zeta(3)-H3c(2*n)))
# half-integer regularity: check I near -1/2 - k is bounded
print('I near -1/2:', I(mpc(-0.5,1e-8)), I(mpc(-1.5,1e-8)))
M7s = Salt(Fn_ := (lambda n: a_(n)**7*Fn(n)), 30)
print('M7 series', M7s, ' table -15332.55419477457527697894653409303157', time.time()-t0)
M7B = B(I, 0.25)/sqrt(pi)
print('M7 Barnes - series', M7B-M7s, time.time()-t0)
# factorizations
th = mpc('0.31','0.27')
print('p factor', p(tan(th)) - sqrt(185)*sin(th+pi*beta)*sin(th+pi*betab)/cos(th)**2)
print('q factor', qq(tan(th)) - rho7*sin(th+pi*etap)*sin(th+pi*etam)/cos(th)**2)
s = mpc('0.25','0.6')
Np = lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*4+[0.25-s,s+beta,1-s-beta,s+betab,1-s-betab])
N7 = lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*4+[0.25-s,s+etap,1-s-etap,s+etam,1-s-etam])
A7 = lambda s: GP([s]*3+[0.5-s]*7+[1.25-s],[1-s]*3+[-s,0.25-s,s+beta,1-s-beta,s+betab,1-s-betab])
print('YRsec z^4 p - sqrt185/pi Np', Y(s)*R(s)*SEC(s)*TAN(s)**4*p(TAN(s))-sqrt(185)/pi*Np(s))
print('YRsec z^4 q - rho7/pi N7', Y(s)*R(s)*SEC(s)*TAN(s)**4*qq(TAN(s))-rho7/pi*N7(s))
print('A7 - (-s)Np', A7(s)-(-s)*Np(s))
# J_- and the inner identity
Jm = B(lambda t: GP([t,1-t],[])*exp(-1j*pi*t)/((1-t)*(1-2*s-t)), 0.125)
print('J_- - Psi/(-2s)', Jm-Psi(s)/(-2*s))
inner = B(lambda v: GP([v,v+0.5,1-v,0.5-v],[v+0.25,v+0.75,0.25-v,0.75-v])/((0.5-v)*(0.5-s-v)), 1/mpf(16))
print('seventhinner: B[cot/(..)] + Psi/(pi s)', inner+Psi(s)/(pi*s))
vv = mpc('0.0625','0.4')
print('cot identity', GP([vv,vv+0.5,1-vv,0.5-vv],[vv+0.25,vv+0.75,0.25-vv,0.75-vv])-cot(2*pi*vv))
H7 = B(lambda s: Np(s)*Psi(s), 0.25)/pi
G7 = B(N7, 0.25)
print('H7', H7, ' table -12.961075412927996857090472232198888')
print('M7 - (rho7 G7/pi^1.5 + 196 sqrt185 H7/sqrt pi)', M7s-(rho7*G7/pi**1.5+196*sqrt(185)*H7/sqrt(pi)))
print('24pi^3 M7/2187', 24*pi**3*M7s/2187, ' table -5217.069054363479839305067485280987', time.time()-t0)
# CS bound
f = lambda u: quad(lambda w: 1/(sqrt((mpf(7)/16)**2+w**2)*sqrt((mpf(3)/16)**2+(u+w)**2)), [-inf, -u, 0, inf])
print('CS: max over u samples', max(f(mpf(u)) for u in [0,0.1,0.5,1,3,10]), ' 16pi/sqrt21', 16*pi/sqrt(21))
