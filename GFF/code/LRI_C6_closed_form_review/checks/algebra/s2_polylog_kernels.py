import sympy as sp
from mpmath import mp, mpf, mpc, gamma, psi, pi, log, zeta, sqrt, atan, cos, sin, tan, exp, binomial, quad, nsum, inf, catalan, sec, cot, asinh, acosh
mp.dps = 40
# ---- Section 9 exact arithmetic
G, P, L3, C212 = sp.symbols('G pi L3 C212')
Bpol = 4352*((32*G+9*P**2)*(-L3/2 - sp.Rational(7,192)*P**3) - 64*C212)
target = -2176*((32*G+9*P**2)*L3+128*C212) - sp.Rational(476,3)*P**3*(32*G+9*P**2)
print('Bpol expansion residual:', sp.expand(Bpol-target))
print('Gpi3 coeff:', sp.Rational(-544,3)-sp.Rational(476*32,3), 'pi5 coeff:', sp.Rational(37631,128)-sp.Rational(476*9,3))
print('7pi^3/192 integral:', sp.integrate((sp.Symbol('t')-sp.pi)**2/8,(sp.Symbol('t'),0,sp.pi/2)))
# Ereal - E
A,Q,z3,z5 = sp.symbols('A Q z3 z5')
Pcal = sp.Rational(21,640)*A**5+sp.Rational(7,64)*A**3*P**2+sp.Rational(1149,64)*A**2*P**3+sp.Rational(7863,16)*A**2*z3+192*A*G*(16*G+3*P**2)+sp.Rational(14853,640)*A*P**4-sp.Rational(544,3)*G*P**3+sp.Rational(37631,128)*P**5+sp.Rational(722279,48)*P**2*z3-sp.Rational(805959,8)*z5
Preal = sp.Rational(21,640)*A**5+sp.Rational(7,64)*A**3*P**2+sp.Rational(1149,64)*A**2*P**3+sp.Rational(7863,16)*A**2*z3+192*A*G*(16*G+3*P**2)+sp.Rational(14853,640)*A*P**4-sp.Rational(15776,3)*G*P**3-sp.Rational(145153,128)*P**5+sp.Rational(722279,48)*P**2*z3-sp.Rational(805959,8)*z5
print('Ereal-E - shift:', sp.expand(Preal-Pcal + sp.Rational(476,3)*P**3*(32*G+9*P**2)))
Ebr = Q/8*(63*A**3+120*A*G+79*A*P**2+2013*P**3+54204*z3)+Q**2*(29*P-249*A)
print('monomials in E:', len(sp.Poly(sp.expand(Ebr+Pcal),A,Q,G,P,z3,z5).terms()))
# ---- D3 numerics: Im Li_{2,1}(i,1) = sum_k (-1)^k H_{2k}/(2k+1)^2
from mpmath import harmonic, euler
D3 = nsum(lambda k: (-1)**int(k)*(psi(0,2*k+1)+euler)/(2*k+1)**2, [0,inf])
Ls3 = -quad(lambda t: log(2*sin(t/2))**2, [0, pi/2])
print('L3 numeric', Ls3, ' table -2.0335765060720546009120689697005182')
print('D3 + L3/2 + 7pi^3/192 =', D3 + Ls3/2 + 7*pi**3/192)
# ---- positivity bounds
print('C_s bound', 60*sp.Rational(256,3)-sp.Rational(105,4)*25-9*5*3-sp.Rational(2469,4)*9, 'C_d bound', 96*sp.Rational(256,3)-42*25-18*15-1227*9)
Qn = gamma(mpf(1)/4)**4/pi; An = pi+4*log(2); Gn = catalan
X4 = 42*An**2+18*An*pi+1227*pi**2-96*Qn; Y4 = mpf(105)/4*An**2+9*An*pi+mpf(2469)/4*pi**2-60*Qn
print('Q', Qn, 'X4', X4, 'Y4', Y4)
# ---- kernel identities at random complex s
s = mpc('0.23','0.71')
M1 = gamma(s)*gamma(0.5-s)**3/(gamma(1-s)**3*gamma(0.5+s))
M2 = gamma(s)**2*gamma(0.5-s)**2/(gamma(1-s)**2*gamma(0.5+s)**2)
R4 = (gamma(s)/gamma(s+0.5))**4
print('M1=R4 tan^3', M1-R4*tan(pi*s)**3, ' M2=R4tan^2', M2-R4*tan(pi*s)**2)
al = mpf('0.137')
Na = gamma(s)**2*gamma(0.5-s)**3/(gamma(1-s)**2*gamma(0.5+s)*gamma(s+al)*gamma(1-s-al))
print('Nalpha', Na-(cos(pi*al)*M1+sin(pi*al)*M2))
K = gamma(s)**2*gamma(0.5-s)**4/gamma(1-s)**2; M0 = gamma(0.5-s)**4/gamma(1-s)**4
print('K=pi^2(M2+M0)', K-pi**2*(M2+M0))
R6 = (gamma(s)/gamma(s+0.5))**6; t = tan(pi*s)
Mj6 = lambda j, ss: (gamma(ss)/gamma(ss+0.5))**6*tan(pi*ss)**(6-j)
print('M6 reflection', [Mj6(j,0.5-s)-Mj6(6-j,s) for j in range(1,6)])
N35 = gamma(s)**3*gamma(0.5-s)**5/(gamma(1-s)**3*gamma(0.5+s)); N44 = gamma(s)**4*gamma(0.5-s)**4/(gamma(1-s)**2*gamma(0.5+s)**2)
print('N35', N35-pi**2*(Mj6(1,s)+Mj6(3,s)), 'N44', N44-pi**2*(Mj6(2,s)+Mj6(4,s)))
a6 = atan(mpf(11)/13)/pi
N6 = gamma(s)**4*gamma(0.5-s)**5/(gamma(1-s)**2*gamma(0.5+s)*gamma(s+a6)*gamma(1-s-a6))
print('N6', N6-(cos(pi*a6)*N35+sin(pi*a6)*N44), cos(pi*a6)-13/sqrt(290), sin(pi*a6)-11/sqrt(290))
# eighth
r2 = sqrt(2); aa = 1233-278*r2; bb = mpf(556); cc = 139*r2
rho8 = sqrt(2177203-1028322*r2); d8 = atan(556/(1233-417*r2))/(2*pi); e8 = acosh((1233-139*r2)/rho8)/(2*pi)
ap, am = mpc(d8,e8), mpc(d8,-e8)
print('rho8^2', rho8**2-((aa-cc)**2+bb**2), '4ac-b^2', 4*aa*cc-bb**2-(685548*r2-618272))
th = pi*s
print('sine product', aa*sin(th)**2+bb*sin(th)*cos(th)+cc*cos(th)**2 - rho8*sin(pi*(s+ap))*sin(pi*(s+am)))
R8 = (gamma(s)/gamma(s+0.5))**8
lhs = (0.25-s)*R8*(aa*t**7+bb*t**6+cc*t**5)
ker8 = gamma(s)**3*gamma(0.5-s)**7*gamma(1.25-s)/(gamma(1-s)**5*gamma(0.5+s)*gamma(0.25-s)*gamma(s+ap)*gamma(1-s-ap)*gamma(s+am)*gamma(1-s-am))
print('eighth kernel', lhs - rho8*ker8)
