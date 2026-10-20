# Check that parameter lists reproduce the simplified kernels, and the trigonometric kernel identities.
import mpmath as mp
from params import setup
from kernels import *
P = setup(40)
pi = mp.pi
L = Glists(P)
pts = [mp.mpc('0.25', '0.7'), mp.mpc('0.25', '-3.3'), mp.mpc('0.11', '1.9'), mp.mpc('-0.37', '0.45')]
def rel(x, y): return abs(x - y)/abs(y)
for s in pts:
    print("s =", s)
    print("  G4 list vs N_alpha4 :", mp.nstr(rel(gkernel(s, *L['G4']), N_alpha(s, P['alpha4'])), 3))
    print("  G6 list vs N_6      :", mp.nstr(rel(gkernel(s, *L['G6']), N_6(s, P['alpha6'])), 3))
    print("  G8 list vs N_8      :", mp.nstr(rel(gkernel(s, *L['G8']), N_8(s, P['a8p'], P['a8m'])), 3))
    print("  G7 list vs N_7      :", mp.nstr(rel(gkernel(s, *L['G7']), N_7(s, P['eta7p'], P['eta7m'])), 3))
    # trig forms
    z = mp.tan(pi*s); R = lambda k: (G(s)/G(s + 0.5))**k
    M1 = G(s)*G(0.5 - s)**3/(G(1 - s)**3*G(0.5 + s)); M2 = G(s)**2*G(0.5 - s)**2/(G(1 - s)**2*G(0.5 + s)**2)
    print("  M1 = R4 tan^3       :", mp.nstr(rel(M1, R(4)*z**3), 3), "  M2 = R4 tan^2:", mp.nstr(rel(M2, R(4)*z**2), 3))
    for al in (P['alpha4'], P['alphaW']):
        print("  N_al = cos M1 + sin M2:", mp.nstr(rel(N_alpha(s, al), mp.cos(pi*al)*M1 + mp.sin(pi*al)*M2), 3))
    M6 = lambda j: R(6)*z**(6 - j)
    N35 = G(s)**3*G(0.5 - s)**5/(G(1 - s)**3*G(0.5 + s)); N44 = G(s)**4*G(0.5 - s)**4/(G(1 - s)**2*G(0.5 + s)**2)
    print("  N35 = pi^2(M1+M3)   :", mp.nstr(rel(N35, pi**2*(M6(1) + M6(3))), 3), "  N44 = pi^2(M2+M4):", mp.nstr(rel(N44, pi**2*(M6(2) + M6(4))), 3))
    print("  N6 = cos N35+sin N44:", mp.nstr(rel(N_6(s, P['alpha6']), mp.cos(pi*P['alpha6'])*N35 + mp.sin(pi*P['alpha6'])*N44), 3))
    s2 = mp.sqrt(2); a, b, c = 1233 - 278*s2, 556, 139*s2
    K8 = (0.25 - s)*R(8)*(a*z**7 + b*z**6 + c*z**5)
    print("  (1/4-s)R8(a t^7+b t^6+c t^5) = rho8 N_8:", mp.nstr(rel(K8, P['rho8']*N_8(s, P['a8p'], P['a8m'])), 3))
    sec = 1/mp.cos(pi*s); Y = 0.25 - s
    p = 7*z**2 + 13*z + 11; q = P['q72']*z**2 + P['q71']*z + P['q70']
    print("  Y R7 sec z^4 p = sqrt185/pi N_p:", mp.nstr(rel(Y*R(7)*sec*z**4*p, mp.sqrt(185)/pi*N_p(s, P['beta7'])), 3))
    print("  Y R7 sec z^4 q = rho7/pi N_7  :", mp.nstr(rel(Y*R(7)*sec*z**4*q, P['rho7']/pi*N_7(s, P['eta7p'], P['eta7m'])), 3))
    print("  A7 = (-s) N_p              :", mp.nstr(rel(A_7(s, P['beta7']), -s*N_p(s, P['beta7'])), 3))
    # conjugation symmetry K(conj s) = conj K(s)
    print("  conj symmetry G8, G7:", mp.nstr(rel(gkernel(mp.conj(s), *L['G8']), mp.conj(gkernel(s, *L['G8']))), 3),
          mp.nstr(rel(gkernel(mp.conj(s), *L['G7']), mp.conj(gkernel(s, *L['G7']))), 3))
    # primitive local kernels M_j (eq:primitiveM)
    for j in (1, 2, 3):
        Mj = G(s)**j*G(0.5 - s)**(3 - j)/(G(1 - s)**(3 - j)*G(0.5 + s)**j)
        print(f"  primitive M_{j} = R3 tan^{3-j}:", mp.nstr(rel(Mj, R(3)*z**(3 - j)), 3), end='')
    print()
    # P_sigma reduction: (M1 + B M2 + C M3)/D = Psi_sigma/Gamma(1/2-s)
    for nm, sg in (('p', '+'), ('m', '-')):
        B = P['B' + nm]; C = P['C' + nm]; D = mp.sqrt((1 - C)**2 + B**2)
        Mj = [G(s)**j*G(0.5 - s)**(3 - j)/(G(1 - s)**(3 - j)*G(0.5 + s)**j) for j in (1, 2, 3)]
        comb = (Mj[0] + B*Mj[1] + C*Mj[2])/D
        print(f"  (M1+B{sg}M2+C{sg}M3)/D{sg} = Psi{sg}/Gamma(1/2-s):", mp.nstr(rel(comb, Psi_sig(s, P['beta' + nm])/G(0.5 - s)), 3))
