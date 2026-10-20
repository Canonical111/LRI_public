# Numerical checks of the general-x structure:
#  (1) Omega(t;x) = A(x) + B(x) cos(2 pi (t+x/2)) for x != 1/2 (two-mode structure),
#  (2) Ah'(1/2) = pi Bh + 4 pi^2 Sy,  Bh'(1/2) = 2 pi^3 a - 2 pi Sxy  (hat: times N_x^2, N_x = Gamma(1-x)/Gamma(x)),
#  (3) W(x) = -N_x^4 Res_u [sin^4(pi(x+u)) h(u;x)^2 / sin^4(pi u)] from the one-sided Taylor data, and W'(1/2) = -4 log2 W(1/2).
import mpmath as mp, json, sys
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
pi=mp.pi; NN=max(60,mp.mp.dps)
def Omega(t,x):
    S1=emsum(lambda n:mp.exp(4*(mp.loggamma(n+x+t)-mp.loggamma(n+1+t))),0,NN)
    S2=emsum(lambda j:mp.exp(4*(mp.loggamma(j+1-t)-mp.loggamma(j+2-x-t))),0,NN)
    return mp.sin(pi*(t+x))**4*S1+mp.sin(pi*t)**4*S2
def AB(x):
    Op=Omega(-x/2,x); Om=Omega(mp.mpf(1)/2-x/2,x); return (Op+Om)/2,(Op-Om)/2
Nx=lambda x: mp.gamma(1-x)/mp.gamma(x)
# (1) two-mode check at x=0.45 and x=0.6
for x in [mp.mpf('0.45'),mp.mpf('0.6')]:
    A,B=AB(x)
    for t in [mp.mpf('0.13'),mp.mpf('0.31'),mp.mpf('-0.21')]:
        print('x=%s t=%s  Omega-(A+B cos) = %s'%(x,t,mp.nstr(Omega(t,x)-(A+B*mp.cos(2*pi*(t+x/2))),5)))
# (2) derivatives of Ah, Bh at x=1/2 by central differences with Richardson (step d, d/2)
s=json.load(open(f'singles_dps{mp.mp.dps}.json')); a=mp.mpf(s['a']); b=mp.mpf(s['b']); Sy=mp.mpf(s['Sy']); Sxy=mp.mpf(s['Sxy'])
def hat(x):
    A,B=AB(x); n2=Nx(x)**2; return n2*A,n2*B
h0=mp.mpf(1)/2; d=mp.mpf('1e-4')
def cdiff(F,d):
    p=F(h0+d); m=F(h0-d); return [(pp-mm)/(2*d) for pp,mm in zip(p,m)]
D1=cdiff(hat,d); D2=cdiff(hat,d/2)
Ap,Bp=[(4*u2-u1)/3 for u1,u2 in zip(D1,D2)]
Ah,Bh=hat(h0)
print('Ah(1/2)-pi^2 a =',mp.nstr(Ah-pi**2*a,5),'  Bh(1/2)-pi^2 b =',mp.nstr(Bh-pi**2*b,5))
print("Ah'(1/2) =",mp.nstr(Ap,20),'  pi Bh+4pi^2 Sy   =',mp.nstr(pi*Bh+4*pi**2*Sy,20),' diff',mp.nstr(Ap-(pi*Bh+4*pi**2*Sy),3))
print("Bh'(1/2) =",mp.nstr(Bp,20),'  2pi^3 a-2pi Sxy  =',mp.nstr(2*pi**3*a-2*pi*Sxy,20),' diff',mp.nstr(Bp-(2*pi**3*a-2*pi*Sxy),3))
# (3) W(x) from one-sided Taylor data (independent of the two-mode structure)
def taylor_h(x):
    psis=lambda j,n: mp.psi(j-1,n+x)-mp.psi(j-1,n+1)
    w=lambda n: mp.exp(4*(mp.loggamma(n+x)-mp.loggamma(n+1)))
    # Bell polynomials: d^j/du^j exp(4 sum X_j u^j/j!) at 0
    Y=[lambda n:1, lambda n:4*psis(1,n), lambda n:(4*psis(1,n))**2+4*psis(2,n),
       lambda n:(4*psis(1,n))**3+3*(4*psis(1,n))*(4*psis(2,n))+4*psis(3,n)]
    return [emsum(lambda n,Yj=Yj:w(n)*Yj(n),0,NN) for Yj in Y]
def W_direct(x):
    hs=taylor_h(x)
    # residue of sin^4(pi(x+u)) H(u)^2 / sin^4(pi u), H cubic Taylor polynomial: use mp.taylor on regular part
    Hp=lambda u: sum(hs[j]*u**j/mp.factorial(j) for j in range(4))
    reg=lambda u: mp.sin(pi*(x+u))**4*Hp(u)**2*(u/mp.sin(pi*u))**4 if u!=0 else mp.sin(pi*x)**4*hs[0]**2/pi**4
    co=mp.taylor(reg,0,3,method='quad',radius=mp.mpf('0.25'))
    return -Nx(x)**4*co[3]
W0=W_direct(h0)
print('W(1/2) - 8 pi^3 a b =',mp.nstr(W0-8*pi**3*a*b,5))
dd=mp.mpf('1e-3')
w1=(W_direct(h0+dd)-W_direct(h0-dd))/(2*dd); w2=(W_direct(h0+dd/2)-W_direct(h0-dd/2))/dd
Wp=(4*w2-w1)/3
print("W'(1/2)/2 (=L2)   =",mp.nstr(Wp/2,18)); print('-2 log2 P4(2)     =',mp.nstr(-2*mp.log(2)*W0,18))
print('L2 formula mine   =',mp.nstr(2*pi**4*a**2-4*pi**4*b**2+16*pi**3*b*Sy-8*pi**2*a*Sxy,18))
