# High-precision single sums S[phi] = sum_{k>=0} c_k^4 phi(k), c_k=(1/2)_k/k!, via direct partial sum + Euler-Maclaurin tail.
import mpmath as mp
from emsum import emsum
def make(dps):
    mp.mp.dps=dps
    h=mp.mpf(1)/2
    def c(k):return mp.exp(mp.loggamma(k+h)-mp.loggamma(k+1))/mp.sqrt(mp.pi)
    basis={'x1':lambda k:mp.psi(0,k+h)-mp.psi(0,k+1),'x2':lambda k:mp.psi(1,k+h)-mp.psi(1,k+1),
           'x3':lambda k:mp.psi(2,k+h)-mp.psi(2,k+1),'y':lambda k:mp.psi(0,k+h)-mp.psi(0,h),
           'z1':lambda k:mp.psi(1,k+h),'z2':lambda k:mp.psi(2,k+h),'z3':lambda k:mp.psi(3,k+h)}
    return c,basis
def S(expo,names,dps=30,power=4,N=None):
    c,basis=make(dps)
    def f(k):
        v=c(k)**power
        for nm,p in zip(names,expo):
            if p:v*=basis[nm](k)**p
        return v
    N=N or max(40,dps)
    return emsum(f,0,N)
