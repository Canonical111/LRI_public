"""Pipeline test on phi^6 in d=3 (interaction g phi^6/6), McKane (2019) App. A.
Reference: the general phi^N formula, beta_K^(N) = (-1)^K (C_b(N)/2pi) ((N-2)/(N-1)!) A(N)^{-(N-2)K/2} B(N)^N
Gamma(...), with C_b(N) = [2/(pi(3N-2))]^{(d_c+1)/2} C_2(N), C_2(6) = (4/pi^2) exp(-(1/pi^2) int_0^{pi/2} x ln sin x dx),
B(6) = 8. For N=6 the amplitude multiplying (-1)^K (16/(3 pi^4))^K Gamma(2K+5) is C_b(6) (4/120) B^6/(2 pi).
Note: the simplified N=6 expression printed in the same appendix, 2^{49/8} exp(-7 zeta(3)/(16 pi^2))/(15 pi^4),
does not agree numerically with the general formula (factor 20.37); we compare with the general formula.
Here the Gaussian determinant needs only the (vanishing) tadpole subtraction."""
import mpmath as mp
mp.mp.dps = 30
pi = mp.pi
v = lambda l: mp.mpf(15)/((2*l+3)*(2*l+1))
deg = lambda l: mp.mpf(l+1)**2
L1 = mp.nsum(lambda l: deg(l)*(mp.log(1-v(l)) + v(l)), [2, mp.inf])   # rational summand: default nsum reliable here
special1 = deg(0)*v(0) + deg(1)*v(1)            # 5 + 4
A = mp.sqrt(3)*pi**2/4
neg = mp.mpf(1)/2 * (1/mp.sqrt(4))              # 1/2 |l0|^{-1/2}, l0 = 1-5
Gauss = mp.exp(-L1/2 - special1/2)
Jac = (15*pi**2*mp.sqrt(3)/(64*A))**2 / (2*pi)**2   # sqrt(det G)/(2pi)^2 in units (A/sqrt h)^2
legs = (4*pi)**6 * (mp.sqrt(3)/A)**3             # (K phi~)^6 in units (A/sqrt h)^3
mine = 2*(neg*2*Gauss*Jac*legs)/(120*pi)
C2 = 4/pi**2*mp.exp(-mp.quad(lambda x: x*mp.log(mp.sin(x)), [0, pi/2])/pi**2)
general = (2/(pi*16))**2*C2/(2*pi)*mp.mpf(4)/120*8**6
simplified = 2**(mp.mpf(49)/8)*mp.exp(-7*mp.zeta(3)/(16*pi**2))/(15*pi**4)
print('pipeline =', mp.nstr(mine, 15))
print('McKane general formula =', mp.nstr(general, 15), '  ratio =', mp.nstr(mine/general, 15))
print('McKane simplified N=6 expression =', mp.nstr(simplified, 15), '  (differs from his general formula by', mp.nstr(general/simplified, 6), ')')
