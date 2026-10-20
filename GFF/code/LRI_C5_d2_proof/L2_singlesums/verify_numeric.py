# Numerical checks of every step of the proof of L2 = -2 log2 P4(2).  Usage: python3 verify_numeric.py [dps]
# Writes verify_numeric_dps<dps>.json.  Numerics are checks only; the proof is in L2_proof.md.
import mpmath as mp, json, sys, time
mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 40
t0=time.time(); pi=mp.pi; l=mp.log(2); h=mp.mpf(1)/2; out={}
def rec(name,val,tol=None):
    out[name]=mp.nstr(val,6); print('%-62s %s'%(name,mp.nstr(val,6)),flush=True)
def robust(g):
    def f(x):
        with mp.workdps(mp.mp.dps+int(mp.log10(abs(x)+10))+15): v=g(mp.mpf(x))
        return +v
    return f
def emsum(g,a,N=None):
    N=N or max(60,mp.mp.dps)
    f=robust(g);head=mp.fsum(f(k) for k in range(a,N));I=mp.quad(f,[N,2*N,4*N,16*N,64*N,mp.inf])
    J=max(6,int(mp.mp.dps*0.45));ders=list(mp.diffs(f,N,2*J));corr=mp.mpf(0);last=None
    for j in range(1,J+1):
        t=mp.bernoulli(2*j)/mp.factorial(2*j)*ders[2*j-1]
        if last is not None and abs(t)>abs(last):break
        corr+=t;last=t
    return head+I+ders[0]/2-corr
# ---------------- single sums at x=1/2
c4=lambda k: mp.exp(4*(mp.loggamma(k+h)-mp.loggamma(k+1)))/pi**2
x1=lambda k: mp.psi(0,k+h)-mp.psi(0,k+1); y=lambda k: mp.psi(0,k+h)-mp.psi(0,h); z1=lambda k: mp.psi(1,k+h)
a=emsum(c4,0); b=-2/pi*emsum(lambda k:c4(k)*x1(k),0); Sy=emsum(lambda k:c4(k)*y(k),0)
Sxy=4*emsum(lambda k:c4(k)*x1(k)*y(k),0)+emsum(lambda k:c4(k)*z1(k),0)
out['a']=str(a);out['b']=str(b);out['Sy']=str(Sy);out['Sxy']=str(Sxy)
rec('R1: Sy-(pi b-2a log2)/4',Sy-(pi*b-2*a*l)/4)
rec('R2: Sxy-(pi^2 a/4+pi b log2)',Sxy-(pi**2*a/4+pi*b*l))
P4=8*pi**3*a*b; L2=2*pi**4*a**2-4*pi**4*b**2+16*pi**3*b*Sy-8*pi**2*a*Sxy
out['P4(2)']=str(P4); out['L2']=str(L2)
rec('L2 (exact reduction) + 2 log2 P4(2)',L2+2*l*P4)
rec('L2 - C62d 70-digit value',L2-mp.mpf('-347.24915312320113105847678307522316920816760199487427083420162434'))
rec('P4(2) - note value',P4-mp.mpf('250.48731558186728553185175688791140716835571092358366654'))
# ---------------- elliptic moments (AGM, k=sin th)
K=lambda k,kp: pi/(2*mp.agm(1,kp))
def Q(F):
    G=lambda th: F(mp.sin(th),mp.cos(th),K(mp.sin(th),mp.cos(th)),K(mp.cos(th),mp.sin(th)))*mp.cos(th)
    return mp.quad(G,mp.linspace(0,pi/2,9))
w=lambda k,kp: mp.log(k)-2*mp.log(kp)
M=Q(lambda k,kp,f,g:f**2); N=Q(lambda k,kp,f,g:f*g); out['M']=str(M); out['N']=str(N)
rec('a-8N/pi^3',a-8*N/pi**3); rec('b-8M/pi^3',b-8*M/pi**3)
rec('note fp:MN: M-(B-+B+)/64, N-(B--B+)/32 (B+- from 4F3 via hyper)',0)
Fm=mp.hyper([0.25,0.25,0.5,0.5],[0.75,0.75,1],1); Fp=mp.hyper([0.75,0.75,0.5,0.5],[1.25,1.25,1],1)
g4=mp.gamma(0.25)**4; Bm=g4*Fm; Bp=64*pi**4/g4*Fp
rec('  M-(B-+B+)/64',M-(Bm+Bp)/64); rec('  N-(B--B+)/32',N-(Bm-Bp)/32)
rec('G2[1]-2M (Landen)',Q(lambda k,kp,f,g:g**2)-2*M)
rec('FG[w]+log2 N (Landen)',Q(lambda k,kp,f,g:f*g*w(k,kp))+l*N)
rec('FG[log k]+pi M/2 (lp:eq:mixedlog)',Q(lambda k,kp,f,g:f*g*mp.log(k))+pi*M/2)
R=Q(lambda k,kp,f,g:f**2*w(k,kp)); rec('R-(pi N/4-log2 M) (lp:eq:R)',R-(pi*N/4-l*M))
rec('G2[w]-(-2R-4 log2 M) (Landen)',Q(lambda k,kp,f,g:g**2*w(k,kp))-(-2*R-4*l*M))
rec('U0-2N (quadrant contour, h=1)',Q(lambda k,kp,f,g:f**2/kp)-2*N)
rec('G2[log k]+pi N (quadrant contour, h=Log z, real part)',Q(lambda k,kp,f,g:g**2*mp.log(k))+pi*N)
rec('-2FG[log k]-int f^2 log(k/kp)/kp (same contour, imag part)',-2*Q(lambda k,kp,f,g:f*g*mp.log(k))-Q(lambda k,kp,f,g:f**2*mp.log(k/kp)/kp))
FGlkp=Q(lambda k,kp,f,g:f*g*mp.log(kp)); G2lkp=Q(lambda k,kp,f,g:g**2*mp.log(kp))
rec("FG[log k']-(-pi M/4+log2 N/2)",FGlkp-(-pi*M/4+l*N/2)); rec("G2[log k']-(log2 M-pi N/4)",G2lkp-(l*M-pi*N/4))
rec("Sy+(8/pi^3)FG[log k']",Sy+8/pi**3*FGlkp); rec("Sxy-(8/pi^2)G2[log k']-4N/pi",Sxy-8/pi**2*G2lkp-4*N/pi)
# Wan's Stieltjes identity f(t)^2 = (4/pi) int_0^1 k f g/(1-t^2k^2) dk
for tt in (mp.mpf('0.2'),mp.mpf('0.9')):
    rec('Stieltjes identity at t=%s'%tt,K(tt,mp.sqrt(1-tt**2))**2-4/pi*Q(lambda k,kp,f,g:k*f*g/(1-tt**2*k**2)))
# boundary values used in the quadrant contour
Kc=lambda z: pi/2*mp.hyp2f1(h,h,1,z**2)
for X in (mp.mpf('1.7'),mp.mpf('4.3')):
    k=1/X; kp=mp.sqrt(1-k**2); f=K(k,kp); g=K(kp,k)
    rec('K(x+i0)-(f(1/x)+i g(1/x))/x at x=%s'%X,abs(Kc(X+mp.mpf(10)**(-mp.mp.dps+5)*1j)-(f+1j*g)/X))
for Yv in (mp.mpf('0.6'),mp.mpf('3.1')):
    k=Yv/mp.sqrt(1+Yv**2); kp=1/mp.sqrt(1+Yv**2)
    rec('K(iy)-f(y/sqrt(1+y^2))/sqrt(1+y^2) at y=%s'%Yv,abs(Kc(1j*Yv)-K(k,kp)*kp))
# generating functions (Lemma G)
c2=lambda n: mp.exp(2*(mp.loggamma(n+h)-mp.loggamma(n+1)))/pi
for k in (mp.mpf('0.35'),mp.mpf('0.8')):
    kp=mp.sqrt(1-k**2); f=K(k,kp); g=K(kp,k); S=lambda wt: mp.nsum(lambda n: c2(n)*wt(n)*k**(2*n),[0,mp.inf])
    rec('G1 sum c^2 x1 k^2n + g + (2/pi) f ln k, k=%s'%k,S(x1)+g+2/pi*f*mp.log(k))
    rec('G2 sum c^2 y k^2n + (2/pi) f ln kp, k=%s'%k,S(y)+2/pi*f*mp.log(kp))
    rec('G3 sum c^2(4x1y+2z1)k^2n - [4g ln kp+2pi f+(8/pi)f ln k ln kp]',S(lambda n:4*x1(n)*y(n)+2*z1(n))-(4*g*mp.log(kp)+2*pi*f+8/pi*f*mp.log(k)*mp.log(kp)))
# ---------------- general x: two modes and derivative bookkeeping
NN=max(60,mp.mp.dps)
def Omega(t,x):
    S1=emsum(lambda n:mp.exp(4*(mp.loggamma(n+x+t)-mp.loggamma(n+1+t))),0,NN)
    S2=emsum(lambda j:mp.exp(4*(mp.loggamma(j+1-t)-mp.loggamma(j+2-x-t))),0,NN)
    return mp.sin(pi*(t+x))**4*S1+mp.sin(pi*t)**4*S2
Nx=lambda x: mp.gamma(1-x)/mp.gamma(x)
def hatAB(x):
    Op=Omega(-x/2,x); Om=Omega(h-x/2,x); n2=Nx(x)**2; return n2*(Op+Om)/2,n2*(Op-Om)/2
x0=mp.mpf('0.45')
Ah,Bh=hatAB(x0)
for t in (mp.mpf('0.13'),mp.mpf('-0.31')):
    rec('two modes at x=0.45, t=%s'%t,Nx(x0)**2*Omega(t,x0)-(Ah+Bh*mp.cos(2*pi*(t+x0/2))))
def dAB(xc,d=mp.mpf('1e-5')):
    p1=hatAB(xc+d);m1=hatAB(xc-d);p2=hatAB(xc+d/2);m2=hatAB(xc-d/2)
    return [(4*(P2-M2)/d-(P1-M1)/(2*d))/3 for P1,M1,P2,M2 in zip(p1,m1,p2,m2)]
# Taylor data of h at (0,x0) from single sums
phi4=lambda n,x: mp.exp(4*(mp.loggamma(n+x)-mp.loggamma(n+1)))
def hdata(x):
    D=lambda n: mp.psi(0,n+x)-mp.psi(0,n+1)
    return (emsum(lambda n:phi4(n,x),0), emsum(lambda n:4*phi4(n,x)*D(n),0),
            emsum(lambda n:4*phi4(n,x)*mp.psi(0,n+x),0), emsum(lambda n:phi4(n,x)*(16*mp.psi(0,n+x)*D(n)+4*mp.psi(1,n+x)),0))
H0,Hu,Hx,Hux=hdata(x0)
pre0=lambda x: Nx(x)**2*mp.sin(pi*x)**4; pre1=lambda x: Nx(x)**2*4*pi*mp.sin(pi*x)**3*mp.cos(pi*x)
F0p=mp.diff(pre0,x0)*H0+pre0(x0)*Hx
F1p=mp.diff(pre1,x0)*H0+pre1(x0)*Hx+mp.diff(pre0,x0)*Hu+pre0(x0)*Hux
Ap,Bp=dAB(x0)
rec('x=0.45: d/dx Hh(0;x) - [A\'+B\'cos(pi x)-pi B sin(pi x)]',F0p-(Ap+Bp*mp.cos(pi*x0)-pi*Bh*mp.sin(pi*x0)))
rec('x=0.45: d/dx dHh/du(0;x) - [-2pi B\' sin(pi x)-2pi^2 B cos(pi x)]',F1p-(-2*pi*Bp*mp.sin(pi*x0)-2*pi**2*Bh*mp.cos(pi*x0)))
# x=1/2: Ah', Bh' by finite differences, and the residue-derivative formula with these (independent of Sy, Sxy)
Ah5,Bh5=hatAB(h); Ap5,Bp5=dAB(h)
rec("x=1/2: Ah'-(pi Bh+4pi^2 Sy)  [finite diff.]",Ap5-(pi*Bh5+4*pi**2*Sy))
rec("x=1/2: Bh'-(2pi^3 a-2pi Sxy) [finite diff.]",Bp5-(2*pi**3*a-2*pi*Sxy))
rho=[lambda x:-4*(mp.cos(2*pi*x)+4)*mp.cos(pi*x)/(pi*mp.sin(pi*x)**7),
     lambda x:4*(4*mp.sin(pi*x)**2-5)/(pi*mp.sin(pi*x)**7),lambda x:4*(mp.sin(pi*x)**2-5)*mp.cos(pi*x)/(pi*mp.sin(pi*x)**7)]
Wq=lambda x: -(rho[0](x)*hatAB(x)[0]**2+2*rho[1](x)*hatAB(x)[0]*hatAB(x)[1]+rho[2](x)*hatAB(x)[1]**2)
# direct W(x) from the one-sided Taylor data (no two-mode input)
def Wdirect(x):
    D=lambda j,n: mp.psi(j-1,n+x)-mp.psi(j-1,n+1)
    Yb=[lambda n:1,lambda n:4*D(1,n),lambda n:(4*D(1,n))**2+4*D(2,n),lambda n:(4*D(1,n))**3+48*D(1,n)*D(2,n)+4*D(3,n)]
    hs=[emsum(lambda n,Yj=Yj:phi4(n,x)*Yj(n),0) for Yj in Yb]
    Hp=lambda v: sum(hs[j]*v**j/mp.factorial(j) for j in range(4))
    reg=lambda v: mp.sin(pi*(x+v))**4*Hp(v)**2*(v/mp.sin(pi*v))**4 if v!=0 else mp.sin(pi*x)**4*hs[0]**2/pi**4
    return -Nx(x)**4*mp.taylor(reg,0,3,method='quad',radius=mp.mpf('0.25'))[3]
xg=mp.mpf('0.45')
rec('x=0.45: W from residue of one-sided data - W from two-mode form',Wdirect(xg)-Wq(xg))
rec("x=1/2: W'(1/2) via rho-formula with finite-diff Ah',Bh' + 4 log2 W(1/2)",
    (-12*Ah5**2-16*Bh5**2+8/pi*(Ap5*Bh5+Ah5*Bp5))+4*l*8*Ah5*Bh5/pi)
out['seconds']=time.time()-t0
json.dump(out,open(f'verify_numeric_dps{mp.mp.dps}.json','w'),indent=1)
print('done in %.0fs'%(time.time()-t0))
