from mpmath import mp, mpf, gamma, pi, log, quad, besselk, inf, diff, psi, euler, sqrt, cos, sin
mp.dps=30
G14=gamma(mpf(1)/4); Ag=3*pi**2/G14**4
B2=6*gamma(mpf(3)/4)/(sqrt(pi)*G14)
print("Ag",Ag,"B2",B2)
# Item1: Tr(G_z V G_z V) via Fourier: V=(B2/2)(1+y^2)^(-1/2), Vt=B2*K0(p)
def Tr(z):
    I=quad(lambda p: besselk(0,p)**2*p**(-z),[0,1,inf])
    return (B2**2)/(2*pi)*2*gamma(z)*cos(pi*z/2)*2*I   # int dp/2pi |Vt|^2 Gt^2 ; Gt^2 FT=2Gamma(z)cos(pi z/2)|p|^-z
for z in [mpf('1e-3'),mpf('1e-4')]:
    t=Tr(z); print("z",z,"Tr-12Ag/z",t-12*Ag/z,"36Agln2",36*Ag*log(2))
# direct position-space check at z=0.3 (finite) vs Fourier
z=mpf('0.3')
V=lambda y:(B2/2)/sqrt(1+y**2)
# int dx dy V(x)V(y)|x-y|^{-1+z}: use u=x-y
inner=lambda u: quad(lambda x: V(x)*V(x-u),[-inf,0,u,inf]) if u!=0 else quad(lambda x:V(x)**2,[-inf,inf])
mp.dps=15
pos=2*quad(lambda u: inner(u)*u**(-1+z),[0,1,10,inf])
mp.dps=30
print("z=0.3 position",pos,"fourier",Tr(z))
