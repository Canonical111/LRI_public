from mpmath import mp, mpf, gamma, loggamma, exp, log, quad, inf, pi, sin, cos, sqrt, besselk, diff, psi
mp.dps=25
p=lambda n: exp(loggamma(n+mpf(3)/4)-loggamma(n+mpf(1)/4))
lam=lambda n: quad(lambda t:(2*sin(t/2))**(-0.5)*cos(n*t),[0,pi,2*pi])
l0=lam(0)
print("circle eig ratios", [ (lam(n)/l0)/(p(0)/p(n)) for n in (1,2,3,5)])
print("item3 special:", (3+mpf(9)/2)+2*(1+mpf(1)/2))
# flat-space check GV phi = 3 phi at x=0.7, R=1 (h=1)
G14=gamma(mpf(1)/4); Ag=3*pi**2/G14**4; B2=6*gamma(mpf(3)/4)/(sqrt(pi)*G14); B=sqrt(B2)
phi=lambda y,R=1,y0=0: B*(R/(R**2+(y-y0)**2))**0.25
V=lambda y: phi(y)**2/2
x=mpf('0.7')
GVphi=quad(lambda y: abs(x-y)**-0.5*V(y)*phi(y),[-inf,0,x,inf])
print("GVphi/phi",GVphi/phi(x))
Zy=lambda y: diff(lambda a: phi(y,1,a),0); ZR=lambda y: diff(lambda r: phi(y,r,0),1)
GVZ=quad(lambda y: abs(x-y)**-0.5*V(y)*ZR(y),[-inf,0,x,inf])
print("GV ZR / ZR", GVZ/ZR(x))
# item4 norms at R=1,h=1
print("Gyy",quad(lambda y:V(y)*Zy(y)**2,[-inf,0,inf]),"GRR",quad(lambda y:V(y)*ZR(y)**2,[-inf,0,inf]),"3Ag/8",3*Ag/8)
# item5 leg: (h/6) int phi^3 at R=2 vs B R^{1/4}
R=mpf(2)
print("leg",quad(lambda y: phi(y,R)**3/6,[-inf,0,inf]), B*R**0.25)
# item6: T_z=int dp/2pi |phit|^2 K_z(p), phit = B*2sqrt(pi)/G(1/4)*(p/2)^(-1/4)K_{1/4}(p)
def T(z):
    Kz=lambda q: q**((1+z)/2)/(2*gamma((1+z)/2)*sin(pi*(1-z)/4))
    ph=lambda q: B*2*sqrt(pi)/G14*(q/2)**(-0.25)*besselk(0.25,q)
    return 2*quad(lambda q: ph(q)**2*Kz(q),[0,1,inf])/(2*pi)
T0=T(0); print("T0",T0,"4Ag",4*Ag)
print("dlnT/dz",diff(T,0)/T0,"pi/4-ln2",pi/4-log(2))
