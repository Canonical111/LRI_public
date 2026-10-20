"""Step 1: validate the amplitude pipeline on phi^4 in d=4-eps (MS, dimensional regularization)
against McKane (2019) / McKane-Wallace-de Alcantara Bonfim (1984), as also used by Kompaniets-Panzer (2017):
  beta_K -> 6 C_beta (-1)^K K! K^{7/2} (16 pi^2)^{-K}   (interaction g phi^4/4!),
  C_beta = 2^{13/2} 3 exp(3 zeta'(2)/pi^2 - 7 gamma/2 - 15/4),
  nu^{-1}_K -> -Cbar (-1/3)^K K! K^{9/2},  Cbar = (2^{7/2} 3/pi^2) exp(3 zeta'(2)/pi^2 - 7 gamma/2 - 203/36).
Pipeline (K-metric; relative eigenvalues 1 - v_l of 1 - G V on S^4):
  -1/2 log det'_{l>=2} = -1/2 L_sub + 1/2 Tr(GV) + 1/4 Tr(GVGV) - 1/2 sum_special,
  Tr(GV) = 0, 1/4 Tr(GVGV) = 3/eps + F/4, the 3/eps cancels the one-loop coupling counterterm,
  plus the constrained-profile shift delta = (3 kappa/4) h0 <phi0, d_eps S'[phi0]>, kappa = 1/(8 pi^2)."""
import mpmath as mp
mp.mp.dps = 40
pi = mp.pi
v = lambda l: mp.mpf(6)/((l+1)*(l+2))
deg = lambda l: mp.mpf((l+1)*(l+2)*(2*l+3))/6
L_sub = mp.nsum(lambda l: deg(l)*(mp.log(1-v(l)) + v(l) + v(l)**2/2), [2, mp.inf])   # rational summand: default nsum is reliable
special = deg(0)*(v(0)+v(0)**2/2) + deg(1)*(v(1)+v(1)**2/2)                               # 7.5 + 7.5
def TrGVGV(d):   # flat d-dim bubble with V = 24/(1+x^2)^2
    nu = d/2 - 2
    Sd = 2*pi**(d/2)/mp.gamma(d/2); Vpref = 24*(2*pi)**(d/2)/2
    cPi = mp.gamma(2-d/2)*mp.gamma(d/2-1)**2/((4*pi)**(d/2)*mp.gamma(d-2))
    mom = mp.sqrt(pi)*mp.gamma(d/2+nu)*mp.gamma(d/2-nu)*mp.gamma(d/2)/(4*mp.gamma((d+1)/2))
    return Sd/(2*pi)**d*Vpref**2*cPi*mom
e = mp.mpf('1e-12'); F = ((TrGVGV(4-e)-12/e) + (TrGVGV(4+e)+12/e))/2         # = 16
# constrained-profile shift: -Laplacian_d phi0 = c(8 f^3 - 2 eps f^2) => d_eps S'[phi0] = -2 c f^2,
# h0 <phi0, d_eps S'> = -2 c^2 h0 int d^4x f^3 = -2*48*pi^2/2 = -48 pi^2;  delta = (3/(32 pi^2)) * (-48 pi^2) = -9/2
delta = mp.mpf(3)/(32*pi**2) * (-48*pi**2)
Jac = (mp.mpf('38.4')/16)**mp.mpf(2.5)/(2*pi)**mp.mpf(2.5)
legs = (4*pi**2)**4*(mp.mpf(3)/pi**2)**2
c = 3*mp.zeta(2, derivative=1)/pi**2 - 7*mp.euler/2
Cbeta = 2**mp.mpf(6.5)*3*mp.exp(c - mp.mpf(15)/4)
Cbar = 2**mp.mpf(3.5)*3/pi**2*mp.exp(c - mp.mpf(203)/36)
for label, shift in (('without profile shift', 0), ('with profile shift', delta)):
    N4 = mp.mpf(1)/2*2**mp.mpf(-0.5)*2*mp.exp(-L_sub/2 + F/4 - special/2 + shift)*Jac*legs
    print(f'{label:24s} N4/pi / (6 C_beta) = {mp.nstr(N4/pi/(6*Cbeta), 15)}   '
          f'composition N4 e^(-17/9)/(48 pi^3) / Cbar = {mp.nstr(N4*mp.exp(-mp.mpf(17)/9)/(48*pi**3)/Cbar, 15)}')
print('L_sub =', mp.nstr(L_sub, 20), ' F =', mp.nstr(F, 15), ' delta =', delta)
