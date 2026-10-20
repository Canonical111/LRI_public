# Numerical values of a, b, Sy, Sxy (single sums over c_k=(1/2)_k/k!) by Euler-Maclaurin, and the claimed relations R1, R2.
import mpmath as mp, sys, json
mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 30
def robust(g):
    def f(x):
        with mp.workdps(mp.mp.dps+int(mp.log10(abs(x)+10))+15): v=g(mp.mpf(x))
        return +v
    return f
def emsum(g,a,N):
    f=robust(g);head=mp.fsum(f(k) for k in range(a,N));I=mp.quad(f,[N,2*N,4*N,16*N,64*N,mp.inf])
    J=max(6,int(mp.mp.dps*0.45));ders=list(mp.diffs(f,N,2*J));corr=mp.mpf(0);last=None
    for j in range(1,J+1):
        t=mp.bernoulli(2*j)/mp.factorial(2*j)*ders[2*j-1]
        if last is not None and abs(t)>abs(last):break
        corr+=t;last=t
    return head+I+ders[0]/2-corr
h=mp.mpf(1)/2
c=lambda k: mp.exp(mp.loggamma(k+h)-mp.loggamma(k+1))/mp.sqrt(mp.pi)
x1=lambda k: mp.psi(0,k+h)-mp.psi(0,k+1)
y=lambda k: mp.psi(0,k+h)-mp.psi(0,h)
z1=lambda k: mp.psi(1,k+h)
N=max(60,mp.mp.dps)
a=emsum(lambda k:c(k)**4,0,N)
Sx=emsum(lambda k:c(k)**4*x1(k),0,N)
Sy=emsum(lambda k:c(k)**4*y(k),0,N)
Sxy=4*emsum(lambda k:c(k)**4*x1(k)*y(k),0,N)+emsum(lambda k:c(k)**4*z1(k),0,N)
b=-2*Sx/mp.pi; l=mp.log(2); pi=mp.pi
print('a  =',a); print('b  =',b); print('Sy =',Sy); print('Sxy=',Sxy)
print('R1 residual Sy-(pi b-2a log2)/4      :',mp.nstr(Sy-(pi*b-2*a*l)/4,5))
print('R2 residual Sxy-(pi^2 a/4+pi b log2) :',mp.nstr(Sxy-(pi**2*a/4+pi*b*l),5))
print('P4(2)=8pi^3ab =',8*pi**3*a*b)
json.dump({'dps':mp.mp.dps,'a':str(a),'b':str(b),'Sy':str(Sy),'Sxy':str(Sxy)},open(f'singles_dps{mp.mp.dps}.json','w'),indent=1)
