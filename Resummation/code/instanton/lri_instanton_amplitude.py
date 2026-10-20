"""Leading one-instanton amplitude of the 1d long-range Ising epsilon expansion (MS, analytic regulator).
Result: C_n ~ K_I (-1/A_eps)^n Gamma(n+4) with A_eps = 9 pi^2/Gamma(1/4)^4.
Pipeline validated in step1_d4_validation.py (phi^4, d=4, McKane's MS amplitude to 12 digits once the
constrained-profile shift is included) and step1c_phi6_d3.py (phi^6, d=3, McKane's general formula to 15 digits).
The O(z) term of the fixed-profile action is a pure size rescaling R -> R e^{-(pi/2 - 2 ln 2)} and does not
contribute (argued; the explicit residue derivation is not yet written out). The variant without the profile
shift is disfavored by the d=4 benchmark, not excluded.
Writes results.json."""
import json, mpmath as mp
mp.mp.dps = 40
pi, ln2 = mp.pi, mp.log(2)
G4 = mp.gamma(mp.mpf(1)/4)
Ag = 3*pi**2/G4**4; Aeps = 3*Ag; a = 1/Aeps
calA = pi + 4*ln2
B4 = 24*Ag/pi
# --- circle spectrum relative to the free kinetic form: v_n = 3 p_0 / p_|n|
qa, qb = mp.mpf(1)/4, mp.mpf(3)/4
p0 = mp.gamma(qb)/mp.gamma(qa)
v = lambda n: 3*p0*mp.gamma(n+qa)/mp.gamma(n+qb)
f = lambda n: mp.log(1-v(n)) + v(n) + v(n)**2/2
def L_sub_exact(N=200, K=40, M=60):
    d = [(-1)**(k+1)*(mp.bernpoly(k+1, qa)-mp.bernpoly(k+1, qb))/(k*(k+1)) for k in range(1, K+1)]
    L = [mp.mpf(0)]*(M+1)
    for k, dk in enumerate(d, start=1):
        if 2*k <= M: L[2*k] = dk
    E = mp.taylor(lambda t: mp.exp(sum(L[j]*t**j for j in range(M+1))), 0, M)
    V = [mp.mpf(0)] + [3*p0*E[j] for j in range(M)]
    F = mp.taylor(lambda t: (lambda x: mp.log(1-x)+x+x**2/2)(sum(V[j]*t**j for j in range(M+1))), 0, M)
    head = mp.fsum(f(n) for n in range(2, N+1))
    tail = mp.fsum(F[m]*mp.zeta(mp.mpf(m)/2, N+1) for m in range(3, M+1))
    return 2*(head+tail)
L_sub = L_sub_exact()
special = (v(0)+v(0)**2/2) + 2*(v(1)+v(1)**2/2)          # 7.5 + 3 = 10.5
F_bubble = 36*Ag*ln2                                       # lim [Tr(G_z V G_z V) - 12 A_g/z]
shift = mp.mpf(3)/2*Ag*(pi-4*ln2)                          # constrained-profile shift, (3/2) h T'
# numerical checks of the two closed forms (Fourier representations at R=1)
def Tr_bubble(z):   # (B^4/4) int dp/2pi [2 K0(p)]^2 * 2 Gamma(z) cos(pi z/2) |p|^{-z}
    return B4/4*(8/pi)*mp.gamma(z)*mp.cos(pi*z/2)*mp.quad(lambda q: q**(-z)*mp.besselk(0, q)**2, [0, 1, mp.inf])
zz = mp.mpf('1e-6')
F_check = ((Tr_bubble(zz) - 12*Ag/zz) + (Tr_bubble(-zz) + 12*Ag/zz))/2
def T_of_z(z):      # <phi0, K_z phi0>, phi0~(p) ~ p^{-1/4} K_{1/4}(p), K~_z = |p|^{(1+z)/2}/(2 Gamma((1+z)/2) cos(pi(1+z)/4))
    Kt = lambda q: q**((1+z)/2)/(2*mp.gamma((1+z)/2)*mp.cos(pi*(1+z)/4))
    return 2*mp.quad(lambda q: Kt(q)*q**mp.mpf(-0.5)*mp.besselk(mp.mpf(1)/4, q)**2, [0, 1, mp.inf])/(2*pi)
T_ratio_check = mp.diff(T_of_z, 0)/T_of_z(0)
def amp(with_shift):
    Gauss = mp.exp(-L_sub/2 + F_bubble/4 - special/2 + (shift if with_shift else 0))
    N = 2**mp.mpf(-0.5)*Gauss*9/(2*pi**2*Ag)
    return dict(Gauss=Gauss, N=N, C_beta=N/pi, K_I=N*mp.exp(-2*calA*Ag)/(3*pi*Ag))
main, alt = amp(True), amp(False)
C = {3:'-3.719856322901833', 4:'45.42488010356', 5:'-731.13947662454', 6:'14331.6870327683769636',
     7:'-322549.88881298894', 8:'8066723.342964563'}
rows = []
for n, s in C.items():
    c = mp.mpf(s); asym = main['K_I']*(-a)**n*mp.gamma(n+4)
    rows.append(dict(n=n, ratio_Gamma=float(c/asym), ratio_fac=float(c/(main['K_I']*(-a)**n*mp.factorial(n)*n**3)),
                     normalized=float(abs(c)/(a**n*mp.gamma(n+4)))))
b = {1: mp.mpf(3), 2: -6*calA, 3: 6*G4**4/pi + mp.mpf(87)/4*calA**2 - mp.mpf(3)/4*pi**2 - 4*pi}
brows = [dict(L=L, b_L=float(b[L]), ratio_Gamma=float(b[L]/((-1)**(L+1)*main['C_beta']*Ag**(-(L+1))*mp.gamma(L+4)))) for L in b]
out = dict(checks=dict(F_numeric=float(F_check), F_closed=float(F_bubble),
                       Tprime_over_T0_numeric=float(T_ratio_check), Tprime_over_T0_closed=float(pi/4-ln2)),
           A_g=float(Ag), A_eps=float(Aeps), a=float(a), L_sub=mp.nstr(L_sub, 25), F_bubble=float(F_bubble),
           special=float(special), profile_shift=float(shift), Gauss=float(main['Gauss']), C_beta=float(main['C_beta']),
           K_I=float(main['K_I']), K_I_disfavored_variant_without_profile_shift=float(alt['K_I']), coefficient_ratios=rows, beta_ratios=brows)
from pathlib import Path
json.dump(out, open(Path(__file__).resolve().parent/'results.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
