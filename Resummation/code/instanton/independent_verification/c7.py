from mpmath import mp, mpf, gamma, pi, log, exp, sqrt
mp.dps=25
G14=gamma(mpf(1)/4); Ag=3*pi**2/G14**4; cA=pi+4*log(2)
L=mpf('-1.769169774220360678249094144'); F=36*Ag*log(2)
kap=pi/2-2*log(2)          # A(z)=Ag(1+kap z)
for name,dl in [("delta=+3kapAg (claim)",3*kap*Ag),("delta=0",0),("delta=-3kapAg",-3*kap*Ag)]:
    Gauss=exp(-L/2+F/4-mpf(21)/4+dl)
    N=Gauss*9/(sqrt(2)*2*pi**2*Ag)
    KI=N*exp(-2*cA*Ag)/(3*pi*Ag)
    print(name,"delta",dl,"Gauss",Gauss,"N",N,"K_I",KI)
    if dl==3*kap*Ag: KIc=KI
a=1/(3*Ag)
C={3:-3.719856322901833,4:45.42488010356,5:-731.13947662454,6:14331.6870327684,7:-322549.888813,8:8066723.342964563}
print("a=",a)
for n,c in C.items():
    print(n, c/(KIc*(-a)**n*gamma(n+4)))
