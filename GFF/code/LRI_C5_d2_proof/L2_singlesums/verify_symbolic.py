# Exact symbolic checks for the proof of L2 = -2 log2 P4(2) (single-sum route).  Run: python3 verify_symbolic.py
import sympy as sp, json
pi=sp.pi; h=sp.Rational(1,2); L=sp.log(2)
ok=lambda e: sp.simplify(e)==0
report=[]
def chk(name,cond):
    report.append((name,bool(cond))); print(('PASS ' if cond else 'FAIL ')+name)
# ---------------------------------------------------------------- 1. note's gs:lambda, gs:etaTheta at q=1/2
m,n=sp.symbols('m n',nonnegative=True,integer=True)
q=h
psi=lambda j,z: sp.polygamma(j,z)
chi=lambda j: (-1)**j*psi(j,n+1-q)+psi(j,q)-(-1)**j*psi(j,1-q)
a_ln=m+q; b_ln=m+2*q            # a_{ln}=l+n+q, b_{ln}=l+n+2q with m=l+n
lam={j: psi(j-1,a_ln)-psi(j-1,b_ln)-(-1)**j*chi(j-1)+(1+(-1)**j)*psi(j-1,1)-psi(j-1,n+1) for j in (1,2,3)}
eta={j: (psi(j,a_ln)+(-1)**j*chi(j))/2 for j in (1,2,3)}
mu1=(psi(0,a_ln)-psi(0,q)+psi(0,n+1-q)-psi(0,1-q))/2
X=lambda j,k: psi(j-1,k+h)-psi(j-1,k+1)
Z=lambda j,k: psi(j,k+h)
Y=lambda k: psi(0,k+h)-psi(0,h)
kap={1:0,2:2*(psi(1,1)-psi(1,h)),3:0}
eps={1:psi(1,h),2:0,3:psi(3,h)}
for j in (1,2,3):
    chk(f'lambda_{j} = X_{j}(m)+X_{j}(n)+kappa_{j}  (q=1/2)',ok(sp.expand_func(lam[j]-(X(j,m)+X(j,n)+kap[j]))))
    chk(f'eta_{j} = (Z_{j}(m)+Z_{j}(n))/2 - eps_{j}  (q=1/2)',ok(sp.expand_func(eta[j]-((Z(j,m)+Z(j,n))/2-eps[j]))))
chk('mu_1 = (y_m+y_n)/2  (q=1/2)',ok(mu1-(Y(m)+Y(n))/2))
chk('kappa_2 = -2pi^2/3, eps_1 = pi^2/2, eps_3 = pi^4',ok(kap[2]+2*pi**2/3) and ok(eps[1]-pi**2/2) and ok(eps[3]-pi**4))
# ---------------------------------------------------------------- 2. general-x constants: log[(pi u/sin pi u)(sin pi(x+u)/sin pi x)]
u,x=sp.symbols('u x')
logk=sp.log(pi*u/sp.sin(pi*u))+sp.log(sp.sin(pi*(x+u))/sp.sin(pi*x))
ser=sp.series(logk,u,0,5).removeO()
C={j: sp.simplify((ser.coeff(u,j)*sp.factorial(j)).rewrite(sp.cos)) for j in (1,2,3)}
print('   C_j(x) =',C)
for j in (1,2,3):
    chk(f'C_{j}(1/2) = kappa_{j}',ok(sp.limit(C[j],x,h)-kap[j]))
    chk(f'(1/2) dC_{j}/dx(1/2) = -eps_{j}',ok(sp.limit(sp.diff(C[j],x),x,h)/2+eps[j]))
# d/dx of X_j(k;x)=psi_{j-1}(k+x)-psi_{j-1}(k+1) is psi_j(k+x)=Z_j; d/dx log (x)_k/k! = psi(k+x)-psi(x) = y_k : chain rule
# ---------------------------------------------------------------- 3. F_{4,1} = sum_j dF4/dlambda_j * eta_j, and residue -> F4
l1,l2,l3,e1,e2,e3=sp.symbols('l1 l2 l3 e1 e2 e3')
F4=sp.Rational(32,3)*l1**3+8*l1*l2+sp.Rational(2,3)*l3
F41=32*l1**2*e1+8*e1*l2+8*l1*e2+sp.Rational(2,3)*e3
chk('F41 = sum_j (dF4/dlambda_j) eta_j',ok(sp.expand(F41-(sp.diff(F4,l1)*e1+sp.diff(F4,l2)*e2+sp.diff(F4,l3)*e3))))
chk('F4 = [u^3] exp(4(l1 u + l2 u^2/2 + l3 u^3/6))',ok(sp.series(sp.exp(4*(l1*u+l2*u**2/2+l3*u**3/6)),u,0,4).removeO().coeff(u,3)-F4))
# ---------------------------------------------------------------- 4. reproduce C62d's 48-term factorization
X1m,X2m,X3m,Ym,Z1m,Z2m,Z3m,X1n,X2n,X3n,Yn,Z1n,Z2n,Z3n=sp.symbols('X1m X2m X3m Ym Z1m Z2m Z3m X1n X2n X3n Yn Z1n Z2n Z3n')
k2,p1,p3=sp.symbols('kappa2 psi1h psi3h')
L1=X1m+X1n; L2_=X2m+X2n+k2; L3=X3m+X3n
M1=(Ym+Yn)/2; E1=(Z1m+Z1n)/2-p1; E2=(Z2m+Z2n)/2; E3=(Z3m+Z3n)/2-p3
P=sp.expand(4*M1*F4.subs({l1:L1,l2:L2_,l3:L3})+F41.subs({l1:L1,l2:L2_,l3:L3,e1:E1,e2:E2,e3:E3}))
ms=[X1m,X2m,X3m,Ym,Z1m,Z2m,Z3m]; ns=[X1n,X2n,X3n,Yn,Z1n,Z2n,Z3n]
terms={}
for mono,coef in sp.Poly(P,*ms,*ns).terms(): terms[(tuple(mono[:7]),tuple(mono[7:]))]=coef
c62=json.load(open('<PROJECT>/LRI_C5_d2_simplify/L2_factorized.json'))
c62t={(tuple(t['m']),tuple(t['n'])):sp.sympify(t['coef'],locals={'kappa2':k2,'psi1h':p1,'psi3h':p3}) for t in c62['terms']}
chk('48-term factorization identical to C62d L2_factorized.json (%d terms)'%len(terms),
    set(terms)==set(c62t) and all(sp.simplify(terms[k]-c62t[k])==0 for k in terms))
# ---------------------------------------------------------------- 5. gs:Lseries summand = (1/2) d/dx [T^4 F4] at x=1/2 (formal chain rule)
# general x: lambda_j(x) = X_j(m;x)+X_j(n;x)+C_j(x), dX_j/dx = Z_j, dlogT/dx = y_m+y_n ; at x=1/2 C_j -> kappa_j, C_j' -> -2 eps_j
dl={1:Z1m+Z1n-2*p1,2:Z2m+Z2n,3:Z3m+Z3n-2*p3}
lamv={l1:L1,l2:L2_,l3:L3}
half_dx=sp.expand((4*(Ym+Yn)*F4.subs(lamv)+sum(sp.diff(F4,v).subs(lamv)*dl[j] for j,v in ((1,l1),(2,l2),(3,l3))))/2)
chk('(1/2) d/dx[T^4 F4]/T^4 at x=1/2 equals 4 mu1 F4 + F41 (the gs:Lseries summand)',ok(half_dx-P))
# ---------------------------------------------------------------- 6. two-mode Taylor data -> Ah, Bh, Ah', Bh' at x=1/2
# Hh(u;x) = N_x^2 sin^4(pi(x+u)) h(u;x) = Ah(x) + Bh(x) cos(2 pi u + pi x) + O(u^4);  N_x = Gamma(1-x)/Gamma(x)
d=sp.symbols('delta')
h0,hu,hx,hux=sp.symbols('h0 hu hx hux')          # h(0;1/2), d_u h, d_x h, d_u d_x h at (0,1/2)
A0,B0,A1,B1=sp.symbols('A0 B0 A1 B1')
xx=h+d
N2=sp.series((sp.gamma(1-xx)/sp.gamma(xx))**2,d,0,2).removeO()
hh=h0+hx*d+u*(hu+hux*d)                            # h to first order in u and delta
Hh=sp.expand(sp.series(sp.series(N2*sp.sin(pi*(xx+u))**4*hh,u,0,2).removeO(),d,0,2).removeO())
Om=sp.expand(sp.series(sp.series((A0+A1*d)+(B0+B1*d)*sp.cos(2*pi*u+pi*xx),u,0,2).removeO(),d,0,2).removeO())
eqs=[sp.expand(Hh-Om).coeff(u,i).coeff(d,j) for i in (0,1) for j in (0,1)]
sol=sp.solve(eqs,[A0,B0,A1,B1],dict=True)[0]
a,b,Sy,Sxy=sp.symbols('a b S_y S_xy')
psih=sp.polygamma(0,h)
hvals={h0:pi**2*a, hu:-2*pi**3*b, hx:4*pi**2*(Sy+psih*a), hux:4*pi**2*(Sxy-2*pi*psih*b)}
Ah,Bh,Ahp,Bhp=[sp.simplify(sp.expand_func(sol[v].subs(hvals))) for v in (A0,B0,A1,B1)]
print('   Ah(1/2)=',Ah,'  Bh(1/2)=',Bh,"  Ah'(1/2)=",Ahp,"  Bh'(1/2)=",Bhp)
chk("Ah=pi^2 a, Bh=pi^2 b, Ah'=pi Bh+4pi^2 Sy, Bh'=2pi^3 a-2pi Sxy",
    ok(Ah-pi**2*a) and ok(Bh-pi**2*b) and ok(Ahp-(pi*Bh+4*pi**2*Sy)) and ok(Bhp-(2*pi**3*a-2*pi*Sxy)))
# ---------------------------------------------------------------- 7. residue functional and L2 in (a,b,Sy,Sxy)
def rho(p):
    e=sp.cos(2*pi*u+pi*x)**p*(u/sp.sin(pi*u))**4/sp.sin(pi*(u+x))**4
    return sp.simplify(sp.series(e,u,0,4).removeO().coeff(u,3))
rh=[rho(p) for p in range(3)]
chk('rho0,rho1,rho2 closed forms',ok(rh[0]+4*(sp.cos(2*pi*x)+4)*sp.cos(pi*x)/(pi*sp.sin(pi*x)**7)) and
    ok(rh[1]-4*(4*sp.sin(pi*x)**2-5)/(pi*sp.sin(pi*x)**7)) and ok(rh[2]-4*(sp.sin(pi*x)**2-5)*sp.cos(pi*x)/(pi*sp.sin(pi*x)**7)))
AA,BB,AAp,BBp=sp.symbols('AA BB AAp BBp')
W0=-(rh[0]*AA**2+2*rh[1]*AA*BB+rh[2]*BB**2).subs(x,h)
W1=-(sp.diff(rh[0],x)*AA**2+2*sp.diff(rh[1],x)*AA*BB+sp.diff(rh[2],x)*BB**2).subs(x,h)-(2*rh[0]*AA*AAp+2*rh[1]*(AAp*BB+AA*BBp)+2*rh[2]*BB*BBp).subs(x,h)
W0=sp.simplify(W0); W1=sp.simplify(W1)
chk("W(1/2) = 8 Ah Bh/pi,  W'(1/2) = -12Ah^2 - 16Bh^2 + (8/pi)(Ah Bh)'",ok(W0-8*AA*BB/pi) and ok(W1-(-12*AA**2-16*BB**2+8*(AAp*BB+AA*BBp)/pi)))
sub={AA:Ah,BB:Bh,AAp:Ahp,BBp:Bhp}
L2=sp.expand(W1.subs(sub)/2); P4=sp.simplify(W0.subs(sub))
print('   L2 =',L2,'   P4(2) =',P4)
chk('L2 = 2pi^4 a^2 - 4pi^4 b^2 + 16pi^3 b Sy - 8pi^2 a Sxy  (exact, no R1/R2 used)',ok(L2-(2*pi**4*a**2-4*pi**4*b**2+16*pi**3*b*Sy-8*pi**2*a*Sxy)))
chk('P4(2) = 8 pi^3 a b',ok(P4-8*pi**3*a*b))
r1,r2=sp.symbols('rho_1 rho_2')   # R1, R2 residuals
SyR=(pi*b-2*a*L)/4+r1; SxyR=pi**2*a/4+pi*b*L+r2
chk('L2 + 2log2 P4 = 8 pi^2 (2 pi b rho1 - a rho2)  (only one combination needed)',
    ok(sp.expand(L2.subs({Sy:SyR,Sxy:SxyR})+2*L*P4-8*pi**2*(2*pi*b*r1-a*r2))))
C62=3*pi**4*a**2-2*pi**4*b**2+8*pi**3*b*Sy-12*pi**2*a*Sxy
chk("C62d's form = exact form - (8pi^3 b rho1 + 4pi^2 a rho2)  (equal only modulo R1,R2)",
    ok(sp.expand((C62-L2).subs({Sy:SyR,Sxy:SxyR})+8*pi**3*b*r1+4*pi**2*a*r2)))
# ---------------------------------------------------------------- 8. elliptic values -> final result
M,N=sp.symbols('M N',positive=True)
ell={a:8*N/pi**3, b:8*M/pi**3, Sy:2*M/pi**2-4*L*N/pi**3, Sxy:8*L*M/pi**2+2*N/pi}
chk('R1 holds identically after the elliptic substitution',ok(sp.expand((Sy-(pi*b-2*a*L)/4).subs(ell))))
chk('R2 holds identically after the elliptic substitution',ok(sp.expand((Sxy-(pi**2*a/4+pi*b*L)).subs(ell))))
L2e=sp.expand(L2.subs(ell)); P4e=sp.expand(P4.subs(ell))
chk('L2 = -1024 log2 M N/pi^3 and P4(2) = 512 M N/pi^3, so L2 = -2 log2 P4(2)',ok(L2e+1024*L*M*N/pi**3) and ok(P4e-512*M*N/pi**3) and ok(L2e+2*L*P4e))
# elliptic substitutions: Sy = -(8/pi^3) FG[log k'], Sxy = (8/pi^2) G2[log k'] + 4N/pi with the two moment evaluations
FGlkp=-pi*M/4+L*N/2; G2lkp=L*M-pi*N/4
chk('Sy = -(8/pi^3)FG[log kp] and Sxy = (8/pi^2)G2[log kp]+4N/pi reproduce the substitution',
    ok(-8/pi**3*FGlkp-ell[Sy]) and ok(8/pi**2*G2lkp+4*N/pi-ell[Sxy]))
# elliptic bookkeeping: FG[log k'] = (FG[log k]-FG[w])/2, G2[log k'] = (G2[log k]-G2[w])/2, G2[w]=-2R-4 l M, R = pi N/4 - l M
R_=pi*N/4-L*M
chk("FG[log k'] = (1/2)(-pi M/2 + l N)",ok(FGlkp-(-pi*M/2+L*N)/2))
chk("G2[log k'] = (1/2)(-pi N - (-2R - 4 l M))",ok(G2lkp-(-pi*N-(-2*R_-4*L*M))/2))
print('\nall passed' if all(v for _,v in report) else '\nSOME FAILED')
json.dump({k:v for k,v in report},open('verify_symbolic_report.json','w'),indent=1)
