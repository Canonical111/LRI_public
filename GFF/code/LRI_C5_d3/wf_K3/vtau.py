# V(tau) = sum_{k>=j>=0} 2(x-y) Phi1(x) Phi1(y),  x=k+5/8, y=j+1/8,  Phi1(w)=Gamma(w+1/8)^3/(Gamma(w+7/8)^2 Gamma(w+1/8+tau))
import mpmath as mp, sys, time
from emsum import emsum
mp.mp.dps=int(sys.argv[2]) if len(sys.argv)>2 else 25
tau=mp.mpf(sys.argv[1])
e8=mp.mpf(1)/8
def Phi1(w): return mp.exp(3*mp.loggamma(w+e8)-2*mp.loggamma(w+7*e8)-mp.loggamma(w+e8+tau))
def C(j):  # sum_{l>=0}(2l+1)Phi1(j+l+5/8), continuous j
    return emsum(lambda l:(2*l+1)*Phi1(j+l+5*e8),0,25)
t=time.time()
V=emsum(lambda j:Phi1(j+e8)*C(j),0,25)
print('tau',tau,'V =',mp.nstr(V,mp.mp.dps-3),' %.0fs'%(time.time()-t))
