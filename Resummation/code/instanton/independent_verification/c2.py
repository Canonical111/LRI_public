from mpmath import mp, mpf, gamma, loggamma, exp, log, quad, inf, diff, bernoulli, factorial, nsum, zeta, pi, cos
mp.dps=30
p=lambda n: exp(loggamma(n+mpf(3)/4)-loggamma(n+mpf(1)/4))
p0=p(0)
v=lambda n: 3*p0/p(n)
f=lambda n: log(1-v(n))+v(n)+v(n)**2/2
print("v0,v1",v(0),v(1))
# Euler-Maclaurin: sum_{n=2}^{N-1} f(n) + int_N^inf f + f(N)/2 - sum B2k/(2k)! f^(2k-1)(N)
def EM(N,K=6):
    s=sum(f(n) for n in range(2,N))
    s+=quad(f,[N,10*N,100*N,inf])+f(N)/2
    for k in range(1,K+1):
        s-=bernoulli(2*k)/factorial(2*k)*diff(f,N,2*k-1)
    return 2*s
for N in [20,40,80]:
    print(N,EM(N))
# independent: direct sum with asymptotic tail fit via Richardson on partial sums with n^-1/2 structure
mp.dps=20
S=mpf(0); part={}
for n in range(2,20001):
    S+=f(n)
    if n in (2500,5000,10000,20000): part[n]=S
print({k:2*v_ for k,v_ in part.items()})
