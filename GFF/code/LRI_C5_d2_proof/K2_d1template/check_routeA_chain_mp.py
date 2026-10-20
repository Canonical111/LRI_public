"""Numerical record (not a proof step) of the full Route-A chain at d=2:
H0, H1, K0 by direct summation -> J_{2tau} from the residue formula -> compare with the Euler-moment forms
and with Pi^2 (F(tau)^2 + F(1-tau)^2)."""
import mpmath as mp
mp.mp.dps = 30
lg = mp.loggamma
F = lambda t: mp.hyp3f2(0.5, 0.5, t, 1, 1, 1)
Kp = lambda m: mp.ellipk(m)
E = lambda a, b: mp.quad(lambda x: x**(a-1)*(1-x)**(b-1)*Kp(x), [0, 0.25, 0.5, 0.75, 0.9, 0.99, 0.999, 1])
for tau in [mp.mpf(3)/10, mp.mpf(9)/20, mp.mpf(3)/5]:
    S, C = mp.sin(mp.pi*tau), mp.cos(mp.pi*tau)
    h  = lambda z: mp.exp(3*lg(z+0.5) - 2*lg(z+1) - lg(z+0.5+tau))
    hp = lambda z: h(z)*(3*mp.digamma(z+0.5) - 2*mp.digamma(z+1) - mp.digamma(z+0.5+tau))
    k  = lambda z: mp.exp(3*lg(z+1-tau) - 2*lg(z+1.5-tau) - lg(z+1))
    H0 = mp.nsum(h, [0, mp.inf], method='e'); H1 = mp.nsum(hp, [0, mp.inf], method='e'); K0 = mp.nsum(k, [0, mp.inf], method='e')
    J = mp.gamma(tau)/mp.gamma(1-tau)*(-(S/(mp.pi*C**2))*H0**2 - (2/(mp.pi**2*C))*H0*H1 + (S**3/(mp.pi*C**2))*K0**2)
    print("tau=%s" % mp.nstr(tau, 6))
    print("  H0 - 2E(1/2,tau)/Gamma(tau)         = %s" % mp.nstr(H0 - 2*E(0.5, tau)/mp.gamma(tau), 3))
    print("  H1 + 2pi E(tau,1/2)/Gamma(tau)      = %s" % mp.nstr(H1 + 2*mp.pi*E(tau, 0.5)/mp.gamma(tau), 3))
    print("  K0 - 2Gamma(1-tau)E(tau,1-tau)/pi   = %s" % mp.nstr(K0 - 2*mp.gamma(1-tau)*E(tau, 1-tau)/mp.pi, 3))
    print("  H0 - (pi^2/Gamma)[F+cot F']          = %s" % mp.nstr(H0 - mp.pi**2/mp.gamma(tau)*(F(tau) + mp.cot(mp.pi*tau)*F(1-tau)), 3))
    print("  H1 + (pi^3/Gamma) F'                 = %s" % mp.nstr(H1 + mp.pi**3/mp.gamma(tau)*F(1-tau), 3))
    print("  K0 - Gamma(tau)Gamma(1-tau)^2 F      = %s" % mp.nstr(K0 - mp.gamma(tau)*mp.gamma(1-tau)**2*F(tau), 3))
    print("  J(residue formula) = %s   Pi^2(F^2+F'^2) = %s   diff = %s" % (mp.nstr(J, 22), mp.nstr(mp.pi**2*(F(tau)**2+F(1-tau)**2), 22),
          mp.nstr(J - mp.pi**2*(F(tau)**2+F(1-tau)**2), 3)))
