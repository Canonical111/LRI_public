from mpmath import mp, mpf, log, nsum, inf
mp.dps=30
v=lambda l: mpf(15)/((2*l+3)*(2*l+1)); f=lambda l:(l+1)**2*(log(1-v(l))+v(l))
N=4000; s=sum(f(mpf(l)) for l in range(2,N))
# tail via Euler-Maclaurin-free: nsum on the tail with richardson
t=nsum(f,[N,inf],method='r+s+e')
print("L1 direct+tail",s+t, " nsum default",nsum(f,[2,inf]))
