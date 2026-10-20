from mpmath import mp, mpf, log, taylor, zeta
mp.dps=40
v=lambda l: mpf(15)/((2*l+3)*(2*l+1)); f=lambda l:(l+1)**2*(log(1-v(l))+v(l))
def g(t):
    vv=15*t**2/((2+3*t)*(2+t)); return (1+t)**2/t**2*(log(1-vv)+vv)
c=taylor(lambda t: g(t) if t!=0 else mpf(0), mpf('1e-30'), 0)  # placeholder
# use series in t via analytic expression: compute taylor of h(t)=t^2 g(t)/(1+t)^2 = log(1-v)+v
h=lambda t: log(1-15*t**2/((2+3*t)*(2+t)))+15*t**2/((2+3*t)*(2+t))
H=taylor(h,0,40); P=[1,2,1]
G=[sum(P[j]*H[k+2-j] for j in range(3) if 0<=k+2-j<len(H)) for k in range(37)]  # g = (1+t)^2 h/t^2
for N in (100,300):
    head=sum(f(mpf(l)) for l in range(2,N))
    tail=sum(G[k]*zeta(k,N) for k in range(2,37))
    print(N,head+tail)
