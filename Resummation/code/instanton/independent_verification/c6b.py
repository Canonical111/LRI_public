from mpmath import mp, mpf, log, sumem, inf, nsum
mp.dps=30
v=lambda l: mpf(15)/((2*l+3)*(2*l+1)); f=lambda l:(l+1)**2*(log(1-v(l))+v(l))
N=200; head=sum(f(mpf(l)) for l in range(2,N))
print("EM tail:",head+sumem(f,[N,inf]))
print("nsum euler-maclaurin:",nsum(f,[2,inf],method='euler-maclaurin'))
