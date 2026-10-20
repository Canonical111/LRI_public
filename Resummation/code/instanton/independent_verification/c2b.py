from mpmath import mp, mpf, gamma, loggamma, exp, log, zeta, bernpoly
mp.dps=40
K=40  # series order in x=n^{-1/2}
p0=exp(loggamma(mpf(3)/4)-loggamma(mpf(1)/4))
# power series ops (lists of length K+1 in x)
def mul(a,b):
    c=[mpf(0)]*(K+1)
    for i,ai in enumerate(a):
        if ai==0: continue
        for j in range(K+1-i): c[i+j]+=ai*b[j]
    return c
def sexp(a):  # a[0]==0
    r=[mpf(0)]*(K+1); r[0]=mpf(1); term=r[:]
    for m in range(1,K+1):
        term=[t/m for t in mul(term,a)]
        r=[x+y for x,y in zip(r,term)]
    return r
# -sum_k c_k n^-k, c_k = (-1)^{k+1}[B_{k+1}(3/4)-B_{k+1}(1/4)]/(k(k+1)); n^-k = x^{2k}
E=[mpf(0)]*(K+1)
for k in range(1,K//2+1):
    ck=(-1)**(k+1)*(bernpoly(k+1,mpf(3)/4)-bernpoly(k+1,mpf(1)/4))/(k*(k+1))
    E[2*k]=-ck
ex=sexp(E)
vs=[mpf(0)]+[3*p0*c for c in ex[:K]]  # v = 3 p0 x * exp(E)
fser=[mpf(0)]*(K+1); vm=vs[:]
vm=mul(vs,vs)
for m in range(3,K+1):
    vm=mul(vm,vs)
    fser=[a-b/m for a,b in zip(fser,vm)]
def fexact(n):
    v=3*p0/exp(loggamma(n+mpf(3)/4)-loggamma(n+mpf(1)/4))
    return log(1-v)+v+v**2/2
for N in [200,400,1000]:
    n=mpf(N); x=n**-0.5
    print("check series at",N, fexact(n)-sum(c*x**i for i,c in enumerate(fser)))
    s=sum(fexact(mpf(m)) for m in range(2,N))
    tail=sum(c*zeta(mpf(i)/2,N) for i,c in enumerate(fser) if i>=3)
    print(N,"L_sub=",2*(s+tail))
