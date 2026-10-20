from mpmath import mp, mpf, mpc, gamma, rgamma, sin, pi, binomial, taylor
mp.dps=40
d=mpf('1.7'); q=d/4; tau=mpc('0.55','0.3'); t=mpc('0.123','0.04')
def dl(l):
    if l==0: return mpf(1)
    return (2*l+d-2)*gamma(l+d-2)/(gamma(d-1)*gamma(l+1))
# 1 generating function
z=mpf('0.3'); s=sum(dl(l)*z**l for l in range(400)); print('Dgen',abs(s-(1+z)*(1-z)**(1-d)))
# Pochhammer form of d_l used in gdk sample proof
from mpmath import rf
print('dl poch',max(abs(dl(l)-rf(4*q-2,l)*rf(2*q,l)/(rf(2*q-1,l)*gamma(l+1))) for l in range(8)))
# gdr kernel
def g(l,s,b):
    a=l/mpf(2)+b/4; gg=(d-b)/2
    return gamma(a+s)*gamma(a-s)/(gamma(a+gg+s)*gamma(a+gg-s))
def N(b): return gamma(d/2)*gamma((d-b)/2)/gamma(b/2)
fg=lambda gg,w: gamma(w)/gamma(w+gg)
# note a_l,b_l, R_tau
al=lambda l: l/mpf(2)+q/2; bl=lambda l: al(l)+q
R=lambda l,s: gamma(al(l)+s)*gamma(bl(l)-tau-s)/(gamma(al(l)+tau+s)*gamma(bl(l)-s))
tl=lambda l,s: gamma(2*q)*gamma(al(l)+s)*gamma(al(l)-s)/(gamma(bl(l)+s)*gamma(bl(l)-s))
sig=q; G=[q,q,tau]; A=[0,0,0]; B=[0,0,q-tau]
# gdr:mixed from b_i, delta_i
b_i=[d/2,d/2,d-2*tau]; de=[0,0,(tau-q)/2]
Gm=[(d-bb)/2 for bb in b_i]; Am=[(bb/2-sig)/2+dd for bb,dd in zip(b_i,de)]; Bm=[(bb/2-sig)/2-dd for bb,dd in zip(b_i,de)]
print('mixed dict', max(abs(x-y) for x,y in zip(Gm+Am+Bm,G+A+B)))
print('balance', [sig+a+bb+gg-d/2 for a,bb,gg in zip(A,B,G)])
def T(l,zz): 
    p=1
    for gi,ai,bi in zip(G,A,B): p*=fg(gi,l+sig+ai+zz)*fg(gi,bi-zz)
    return p
Phi=lambda m: gamma(m+q+t)**3/(gamma(m+2*q+t)**2*gamma(m+q+tau+t))
Psi=lambda n: gamma(-n-t)**2*gamma(q-tau-n-t)/gamma(q-n-t)**3
err=0
for l in (0,1,3):
  for n in (-6,-2,-1,0,2):
    s=al(l)+n+t
    lhs=tl(l,s)**2*R(l,s)
    prod=gamma(2*q)**2*g(l,s,d/2)**2*g(l,s+(tau-q)/2,d-2*tau)
    tt=gamma(2*q)**2*T(l,n+t)
    lat=gamma(2*q)**2*Phi(l+n)*Psi(n)
    err=max(err,abs(lhs-prod)/abs(lhs),abs(lhs-tt)/abs(lhs),abs(lhs-lat)/abs(lhs))
print('R kernel: tl^2R = prod (gdk:Rproduct) = Gamma^2 T_l (gdr:TG) = Phi Psi (gdk:latticeFactor):',err)
# g_l(s;b) = f_g(l/2+b/4+s) f_g(l/2+b/4-s)
b=mpc('0.9','0.2'); l=2; s=mpc('0.3','1.1')
print('gdr factorization', abs(g(l,s,b)-fg((d-b)/2,l/2+b/4+s)*fg((d-b)/2,l/2+b/4-s)))
# D
DR=sin(pi*t)**2*sin(pi*(t+q))**3*sin(pi*(t-q+tau))
DT=1
for ai,bi in zip(A,B): DT*=sin(pi*(t+sig+ai))*sin(pi*(t-bi))
print('D_R = D_T',abs(DR-DT))
C=gamma(2*q)*gamma(tau)/gamma(2*q-tau)
print('C(tau)=N_{d-2tau}',abs(C-N(d-2*tau)))
# S family kernel
bp=d/2-tau; X=(gamma(q-tau/2)/gamma(q+tau/2))**2
Stau=lambda l,s: ((gamma(al(l)-tau/4+s)*gamma(al(l)-tau/4-s)*gamma(bl(l)+s)*gamma(bl(l)-s))/(gamma(bl(l)+tau/4+s)*gamma(bl(l)+tau/4-s)*gamma(al(l)+s)*gamma(al(l)-s)))**2
s=mpc('0.2','0.7'); l=3
print('Skernel', abs(tl(l,s)**2*Stau(l,s)-X*(N(bp)*g(l,s,bp))**2))
# balanced wheel eigenvalue at real b equals N_b g(i nu;b); complex b: modulus form differs
nu=mpf('0.8')
for bb in (mpf('0.9'), mpc('0.9','0.3')):
    mod=gamma(d/2)*gamma((d-bb)/2)/gamma(bb/2)*abs(gamma(l/mpf(2)+bb/4+1j*nu)/gamma(l/mpf(2)+d/2-bb/4+1j*nu))**2
    print('balancedWheel |.|^2 vs N_b g, b=',bb, abs(mod-N(bb)*g(l,1j*nu,bb)))
