"""Step 0: sign and negative-mode conventions on Z(g)=int dphi/sqrt(2pi) exp(-phi^2/2-g phi^4/24).
Saddle at g=-h: phi_c^2=6/h, S_c=3/(2h), relative Hessian l0=1-3=-2 (same v0=3 as the field theories).
Claim to test: Im Z|_{arg g=pi} = -(1/2)|l0|^{-1/2} * 2 saddles * e^{-S_c} = -(1/sqrt2) e^{-3/(2h)},
and with Im F|_{arg g=pi} = A1 (-g)^{-xi} e^{A0/g}, [g^K]F ~ (-1)^{K+1}(A1/pi) A0^{-(K+xi)} Gamma(K+xi)."""
import mpmath as mp
mp.mp.dps = 40
def zK(K):  # exact coefficient
    return (-mp.mpf(1)/24)**K * mp.fac2(4*K-1) / mp.factorial(K)
A0 = mp.mpf(3)/2; A1 = -1/mp.sqrt(2); xi = 0
for K in (10, 20, 40, 80, 160):
    pred = (-1)**(K+1) * A1/mp.pi * A0**(-(K+xi)) * mp.gamma(K+xi)
    print(K, mp.nstr(zK(K)/pred, 12))
