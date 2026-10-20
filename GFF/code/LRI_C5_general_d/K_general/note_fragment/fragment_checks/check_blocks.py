#!/usr/bin/env python3
"""Fragment check 4: termwise identities behind the three-block sample formula of gdk:sample, typed from the fragment.

 (a) f_l(a_l+n+t) = Gamma(2q)^2 Phi_t(l+n) Psi_t(n)  (gdk:latticeFactor), all l >= 0, n in Z;
 (b) the Horn coefficients of H_R, H_M, H_L built from the printed rows (fp:HornDefinition convention)
     times P_R, P_M, P_L reproduce Phi_t(l+n) Psi_t(n) on the right, middle and left parts;
 (c) the kernels G, S, T, V by direct summation where the sums converge;
 (d) rho_k from numerical residues of e^{2 pi i k t}/D_R;
 (e) the Laurent form of D_R used in the top-mode proof.
"""
import mpmath as mp
mp.mp.dps = 40
rng = mp.rand
G, rG = mp.gamma, mp.rgamma

def poch(a, n):
    return mp.rf(a, n)

def dl_spec(q, l):
    d = 4*q
    if l == 0:
        return mp.mpf(1)
    return (2*l + d - 2)*G(l + d - 2)/(G(d - 1)*G(l + 1))

def dl_horn(q, l):
    return poch(4*q - 2, l)*poch(2*q, l)/(poch(2*q - 1, l)*mp.factorial(l))

def f_l(q, tau, l, s):
    a = (l + q)/2; b = a + q
    return G(2*q)**2*G(a+s)**3*G(a-s)**2*G(b-tau-s)/(G(b+s)**2*G(b-s)**3*G(a+tau+s))

def Phi(q, tau, t, m):
    return G(m+q+t)**3/(G(m+2*q+t)**2*G(m+q+tau+t))

def Psi(q, tau, t, n):
    return G(-n-t)**2*G(q-tau-n-t)/G(q-n-t)**3

def horn_coef(rows_up, rows_dn, nvec):
    """fp:HornDefinition coefficient: prod (a)_{u.n} / prod (b)_{v.n} / prod n_i!"""
    c = mp.mpf(1)
    for a, u in rows_up:
        c *= poch(a, u[0]*nvec[0] + u[1]*nvec[1])
    for b, v in rows_dn:
        c /= poch(b, v[0]*nvec[0] + v[1]*nvec[1])
    return c/(mp.factorial(nvec[0])*mp.factorial(nvec[1]))

e, f, c = (1, 0), (0, 1), (1, 1)
def arrays(q, tau, t):
    HR_U = [(4*q-2, e), (2*q, e)] + [(q+t, c)]*3 + [(1, f)] + [(1-q+t, f)]*3
    HR_V = [(2*q-1, e)] + [(2*q+t, c)]*2 + [(q+tau+t, c)] + [(1+t, f)]*2 + [(1-q+tau+t, f)]
    HM_U = [(4*q-1, c), (2*q+1, c), (1, e)] + [(1-t, e)]*2 + [(1+q-tau-t, e), (1, f)] + [(q+t, f)]*3
    HM_V = [(2*q, c), (2, c)] + [(1+q-t, e)]*3 + [(2*q+t, f)]*2 + [(q+tau+t, f)]
    HL_U = [(4*q-2, e), (2*q, e)] + [(1-t, c)]*2 + [(1+q-tau-t, c), (1, f)] + [(2-2*q-t, f)]*2 + [(2-q-tau-t, f)]
    HL_V = [(2*q-1, e)] + [(1+q-t, c)]*3 + [(2-q-t, f)]*3
    return (HR_U, HR_V), (HM_U, HM_V), (HL_U, HL_V)

def prefs(q, tau, t):
    PR = G(q+t)**3*G(-t)**2*G(q-tau-t)/(G(2*q+t)**2*G(q+tau+t)*G(q-t)**3)
    PM = G(q+t)**3*G(1-t)**2*G(1+q-tau-t)/(G(2*q+t)**2*G(q+tau+t)*G(1+q-t)**3)
    PL = G(q-1+t)**3*G(1-t)**2*G(1+q-tau-t)/(G(2*q-1+t)**2*G(q+tau-1+t)*G(1+q-t)**3)
    return PR, PM, PL

worst = {'a': 0, 'b_right': 0, 'b_middle': 0, 'b_left': 0, 'mult': 0}
for trial in range(6):
    q = mp.mpf('0.07') + mp.mpf('0.86')*rng()
    tau = mp.mpc(mp.mpf('0.3') + 2*rng(), rng() - mp.mpf('0.5'))
    t = mp.mpc(mp.mpf('0.1') + mp.mpf('0.7')*rng(), mp.mpf('0.6')*(rng() - mp.mpf('0.5')))
    (HRU, HRV), (HMU, HMV), (HLU, HLV) = arrays(q, tau, t)
    PR, PM, PL = prefs(q, tau, t)
    for l in range(0, 7):
        worst['mult'] = max(worst['mult'], abs(dl_spec(q, l) - dl_horn(q, l)))
        for n in range(-l-4, 5):
            s = (l + q)/2 + n + t
            lhs = f_l(q, tau, l, s)
            rhs = G(2*q)**2*Phi(q, tau, t, l+n)*Psi(q, tau, t, n)
            worst['a'] = max(worst['a'], abs(lhs/rhs - 1))
            term = dl_spec(q, l)*Phi(q, tau, t, l+n)*Psi(q, tau, t, n)
            if n >= 0:                                   # right part, index (l, n)
                h = PR*horn_coef(HRU, HRV, (l, n)); key = 'b_right'
            elif n >= -l:                                # middle part: n = -j-1, l = j+k+1, index (j, k)
                j = -n - 1; k = l - j - 1
                h = PM*4*q*horn_coef(HMU, HMV, (j, k)); key = 'b_middle'
            else:                                        # left part: n = -l-1-p, index (l, p)
                p = -n - l - 1
                h = PL*horn_coef(HLU, HLV, (l, p)); key = 'b_left'
            worst[key] = max(worst[key], abs(h/term - 1))
print('(a),(b) termwise identities, max rel. deviation:', {k: mp.nstr(v, 3) for k, v in worst.items()})

# (c) kernels by direct summation (Euler-Maclaurin tails; the summands are smooth in the index) where convergent
def B(al, m):
    return G(m + al)*rG(m + 1)
def dls(q, l):                                   # d_l of gs:spectrum as a smooth function of l >= 1
    d = 4*q
    return (2*l + d - 2)*G(l + d - 2)/(G(d - 1)*G(l + 1))
def ssum(fn, head=60):
    """sum_{m>=0} fn(m): exact head plus Euler-Maclaurin tail"""
    return mp.fsum(fn(m) for m in range(head)) + mp.sumem(fn, [head, mp.inf])
q = mp.mpf('0.3')
al, be = mp.mpf('-1.55'), mp.mpf('-1.35')
n0, j0 = 2, 3
Gk = lambda n, a: G(n+a)*G(2-4*q-a)*(2*n+2-4*q+a)/(G(n+3-4*q)*G(1-a))
G_direct = B(al, n0) + ssum(lambda l: dls(q, l + 1)*B(al, l + 1 + n0))
G_closed = Gk(n0, al)
S_direct = ssum(lambda n: Gk(n, al)*B(be, n))
S_closed = G(al)*G(be)*G(2-4*q-al-be)*(2-4*q+al-be)/(G(1-al)*G(3-4*q-be))
Tk = lambda j, a: dls(q, j+1)*G(a)*G(j+2)*G(2-4*q-a)/(G(3-4*q)*G(j+2-a))*((2-4*q-a) + (4*q-1+j)*a/(2*q+j))
T_direct = ssum(lambda k: dls(q, j0 + k + 1)*B(al, k))
T_closed = Tk(j0, al)
V_direct = ssum(lambda j: B(be, j)*Tk(j, al))
V_closed = 2*(1-2*q)*G(al)*G(be)*G(2-4*q-al-be)*(4*q-al-be)/(G(3-4*q)*G(2-al-be))
print('(c) kernels: G %s  S %s  T %s  V %s' % tuple(mp.nstr(abs(x/y-1), 3) for x, y in
      [(G_direct, G_closed), (S_direct, S_closed), (T_direct, T_closed), (V_direct, V_closed)]))

# (d) rho_k vs numerical residues;  (e) D_R Laurent form
def DR(q, tau, t):
    return mp.sin(mp.pi*t)**2*mp.sin(mp.pi*(t+q))**3*mp.sin(mp.pi*(t-q+tau))
def rho(k, q, tau):
    pi = mp.pi
    r0 = (2j*pi*k - pi*(3*mp.cot(pi*q) + mp.cot(pi*(tau-q))))/(pi**2*mp.sin(pi*q)**3*mp.sin(pi*(tau-q)))
    r1 = mp.expj(2*pi*k*(q-tau))/(pi*mp.sin(pi*(q-tau))**2*mp.sin(pi*(2*q-tau))**3)
    return -r0 - r1
wr = 0; wd = 0
for (qq, tt) in [(mp.mpf('0.31'), mp.mpc('0.2', '0.07')), (mp.mpf('0.66'), mp.mpc('0.55', '-0.1'))]:
    for k in range(-2, 3):
        res = 0
        for z0 in (0, qq - tt):
            rr = mp.mpf('1e-3')
            res += mp.quad(lambda th: mp.expj(2*mp.pi*k*(z0 + rr*mp.expj(th)))/DR(qq, tt, z0 + rr*mp.expj(th))*1j*rr*mp.expj(th), [0, 2*mp.pi])/(2j*mp.pi)
        wr = max(wr, abs(-res - rho(k, qq, tt))/abs(rho(k, qq, tt)))
    tpt = mp.mpc('0.13', '0.4')
    w = mp.expj(2*mp.pi*tpt)
    form = -mp.mpf(1)/64*mp.expj(-mp.pi*(2*qq+tt))*w**-3*(1-w)**2*(1-mp.expj(2*mp.pi*qq)*w)**3*(1-mp.expj(2*mp.pi*(tt-qq))*w)
    wd = max(wd, abs(form/DR(qq, tt, tpt) - 1))
print('(d) rho_k vs residues: %s   (e) D_R Laurent form: %s' % (mp.nstr(wr, 3), mp.nstr(wd, 3)))
