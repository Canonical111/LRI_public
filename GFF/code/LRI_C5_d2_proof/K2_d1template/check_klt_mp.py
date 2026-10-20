"""Numerical check (not a proof step) of Route B (KLT) at tau = 0.3, 0.6:
 (i) inner elliptic reductions of the ordered real integrals at sample points,
 (ii) ordered integrals = 2 x Euler moments,
 (iii) (1/pi^2)[sin(pi tau) I_{0xy1} I_{x01y} + I_{0yx1} I_{y01x}] = Pi^2 (F(tau)^2 + F(1-tau)^2)."""
import mpmath as mp
mp.mp.dps = 25
K = lambda m: mp.ellipk(m)          # parameter convention
F = lambda t: mp.hyp3f2(0.5, 0.5, t, 1, 1, 1)
E = lambda a, b: mp.quad(lambda x: x**(a-1)*(1-x)**(b-1)*K(x), [0, 0.5, 1])
# (i) inner integrals
for y in [mp.mpf('0.37'), mp.mpf('0.81')]:
    a1 = mp.quad(lambda x: 1/mp.sqrt(x*(1-x)*(y-x)), [0, y])
    a2 = mp.quad(lambda x: 1/mp.sqrt(x*(1-x)*(x-y)), [y, 1])
    print("y=%s: int_0^y = %s  2K(y) = %s ; int_y^1 = %s  2K(1-y) = %s" % (y, mp.nstr(a1,15), mp.nstr(2*K(y),15), mp.nstr(a2,15), mp.nstr(2*K(1-y),15)))
for y in [mp.mpf(-2), mp.mpf('-0.4')]:
    a3 = mp.quad(lambda x: 1/mp.sqrt(x*(x-1)*(x-y)), [1, 2, mp.inf])
    print("y=%s<0: int_1^inf = %s  2K(y) = %s" % (y, mp.nstr(a3,15), mp.nstr(2*K(y),15)))
for y in [mp.mpf(3), mp.mpf('1.3')]:
    a4 = mp.quad(lambda v: 1/mp.sqrt(v*(v+1)*(v+y)), [0, 1, mp.inf])
    print("y=%s>1: int_-inf^0 = %s  (2/sqrt y)K(1-1/y) = %s" % (y, mp.nstr(a4,15), mp.nstr(2*K(1-1/y)/mp.sqrt(y),15)))
# (ii),(iii)
for tau in [mp.mpf('0.3'), mp.mpf('0.6')]:
    I_0xy1 = 2*mp.quad(lambda y: y**-0.5*(1-y)**(tau-1)*K(y), [0, 0.5, 1])
    I_0yx1 = 2*mp.quad(lambda y: y**-0.5*(1-y)**(tau-1)*K(1-y), [0, 0.5, 1])
    I_y01x = 2*mp.quad(lambda y: abs(y)**-0.5*(1-y)**(tau-1)*K(y), [-mp.inf, -1, 0])
    I_x01y = mp.quad(lambda y: y**-0.5*(y-1)**(tau-1)*2*K(1-1/y)/mp.sqrt(y), [1, 2, mp.inf])
    print("tau=%s" % tau)
    print("  I_0xy1 - 2E(1/2,tau)   = %s" % mp.nstr(I_0xy1 - 2*E(0.5, tau), 3))
    print("  I_0yx1 - 2E(tau,1/2)   = %s" % mp.nstr(I_0yx1 - 2*E(tau, 0.5), 3))
    print("  I_y01x - 2E(1/2,1-tau) = %s" % mp.nstr(I_y01x - 2*E(0.5, 1-tau), 3))
    print("  I_x01y - 2E(tau,1-tau) = %s" % mp.nstr(I_x01y - 2*E(tau, 1-tau), 3))
    klt = (mp.sin(mp.pi*tau)*I_0xy1*I_x01y + I_0yx1*I_y01x)/mp.pi**2
    print("  KLT side = %s   Pi^2(F^2+F'^2) = %s" % (mp.nstr(klt, 20), mp.nstr(mp.pi**2*(F(tau)**2 + F(1-tau)**2), 20)))
