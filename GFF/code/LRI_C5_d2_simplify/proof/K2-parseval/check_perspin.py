# Per-spin checks at d=2 (q=1/2):
#  (1) tau>0: (1/2pi) int_R t_l^2 R_tau dnu  =  sum_n [rho_a + rho_b](l+n, n)        (Lemma B; residues of two families)
#  (2) tau=0: the note's series summand at spin l, sum_n [2 S_ln^2 - T_ln^2 R_ln/4]  =  (1/2pi) int_R (1/4) t_l^2 W dnu
#  (3) the finder's square-lattice factorization g(m,n) = 2E_mE_n - (1/4)C_mC_n R(m,n) agrees with the note's general-q
#      formulas gs:seriesBase..gs:Kpoly evaluated at q=1/2.
import sys, mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_d2_simplify')
from emsum import emsum
from rsum import rsum
mp.mp.dps = 20
h = mp.mpf(1)/2; lg = mp.loggamma; psi = mp.psi

def tl(l, s):      # t_l at s (complex), q=1/2
    a, b = mp.mpf(l)/2+mp.mpf(1)/4, mp.mpf(l)/2+mp.mpf(3)/4
    return mp.exp(lg(a+s)+lg(a-s)-lg(b+s)-lg(b-s))
def Rtau(l, tau, s):
    a, b = mp.mpf(l)/2+mp.mpf(1)/4, mp.mpf(l)/2+mp.mpf(3)/4
    return mp.exp(lg(a+s)+lg(b-tau-s)-lg(a+tau+s)-lg(b-s))

print('(1) tau>0 per-spin residue identity', flush=True)
tau = mp.mpf('0.3'); S, Co = mp.sinpi(tau), mp.cospi(tau)
fa  = lambda x: mp.exp(3*lg(x+h)-2*lg(x+1)-lg(x+h+tau))
fap = lambda x: fa(x)*(3*psi(0,x+h)-2*psi(0,x+1)-psi(0,x+h+tau))
fc  = lambda x: mp.exp(3*lg(x+1-tau)-2*lg(x+mp.mpf(3)/2-tau)-lg(x+1))
def rho(m, n):
    ra = (-fap(m)*fa(n) - fa(m)*fap(n) - mp.pi*(S/Co)*fa(m)*fa(n))/(mp.pi**2*Co)
    rb = S**3/(mp.pi*Co**2)*fc(m)*fc(n)
    return ra + rb
for l in (0, 3):
    barnes = mp.quad(lambda nu: mp.re(tl(l, 1j*nu)**2*Rtau(l, tau, 1j*nu)), [0, 1, 10, 100, mp.inf])/mp.pi
    ressum = rsum(lambda n: rho(l+n, n), 1+2*tau, N0=20, J=9)
    print('  l=%d  Barnes = %s   residue sum = %s   diff = %s' % (l, mp.nstr(barnes, 16), mp.nstr(ressum, 16), mp.nstr(barnes-ressum, 3)), flush=True)

print('(2) tau=0 per-spin identity of the note (series vs spectral)', flush=True)
q = h; cstar = psi(0, 1) + psi(0, 2*q)
def W(l, nu):
    a, b = mp.mpf(l)/2+q/2, mp.mpf(l)/2+3*q/2
    A, B = a+1j*nu, b+1j*nu
    p = mp.re(psi(0, A)+psi(0, B)); hh = mp.im(psi(0, A)-psi(0, B))
    j = mp.re(psi(1, A)-psi(1, B)); kk = mp.im(psi(1, A)+psi(1, B)); r = mp.re(psi(2, A)+psi(2, B))
    E2 = -hh**2/2 - 5*j/8
    return (cstar-p)*E2 - hh*kk/2 - 5*r/32
def chi(mm, n): return (-1)**mm*psi(mm, n+1-q) + psi(mm, q) - (-1)**mm*psi(mm, 1-q)
def summand_note(l, n):          # note's general-q formulas at q=1/2:  M^2 S^2/8 - T^2 R/4
    T = mp.rf(q, l+n)*mp.rf(1-q, n)/(mp.rf(2*q, l+n)*mp.factorial(n))
    Sln = mp.rf(2*q, l+n)*mp.factorial(n)/(mp.rf(3*q, l+n)*mp.rf(1+q, n))
    an, bn = l+n+q, l+n+2*q
    lam = {mm: psi(mm-1, an)-psi(mm-1, bn)-(-1)**mm*chi(mm-1, n)+(1+(-1)**mm)*psi(mm-1, 1)-psi(mm-1, n+1) for mm in (1, 2, 3, 4)}
    r = {jj: lam[jj+1]/2 + psi(jj, bn) + psi(jj, n+1) - (1-(-1)**jj)*psi(jj, 1) for jj in (0, 1, 2, 3)}
    l1, l2, l3, l4 = lam[1], lam[2], lam[3], lam[4]
    Rp = ((r[0]-cstar)/2*(l1**3+3*l1*l2+l3) + mp.mpf(3)/4*r[1]*(l1**2+l2) - (l1*r[2]+r[3])/4
          - l1**4/12 + l1**2*l2/8 + mp.mpf(7)/24*l1*l3 + l2**2/8 + l4/12)
    M = mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)
    return M**2*Sln**2/8 - T**2*Rp/4
def g_finder(mm, n):             # finder's factorized form (factor_K2.py)
    C = lambda k: (mp.rf(h, k)/mp.factorial(k))**2
    E = lambda k: (mp.factorial(k)/mp.rf(mp.mpf(3)/2, k))**2
    x = lambda jj, k: psi(jj-1, k+h) - psi(jj-1, k+1)
    k2, k4 = 2*(psi(1, 1)-psi(1, h)), 2*(psi(3, 1)-psi(3, h))
    l1 = x(1, mm)+x(1, n); l2 = x(2, mm)+x(2, n)+k2; l3 = x(3, mm)+x(3, n); l4 = x(4, mm)+x(4, n)+k4
    lamd = {1: l1, 2: l2, 3: l3, 4: l4}
    pone = {0: 0, 1: psi(1, 1), 2: 0, 3: psi(3, 1)}
    r = {jj: lamd[jj+1]/2 + psi(jj, mm+1) + psi(jj, n+1) - (1-(-1)**jj)*pone[jj] for jj in range(4)}
    cs = 2*psi(0, 1)
    R = ((r[0]-cs)/2*(l1**3+3*l1*l2+l3) + mp.mpf(3)/4*r[1]*(l1**2+l2) - (l1*r[2]+r[3])/4
         - l1**4/12 + l1**2*l2/8 + mp.mpf(7)/24*l1*l3 + l2**2/8 + l4/12)
    return 2*E(mm)*E(n) - C(mm)*C(n)*R/4
print('(3) finder factorization vs note formulas:', flush=True)
for (l, n) in [(0, 0), (1, 2), (3, 1), (5, 7)]:
    print('   (l,n)=(%d,%d):' % (l, n), mp.nstr(summand_note(l, n) - g_finder(l+n, n), 3), flush=True)
for l in (0, 1):
    spec = mp.quad(lambda nu: tl(l, 1j*nu).real**2*W(l, nu)/4, [0, 1, 10, 100, mp.inf])/mp.pi
    ser = emsum(lambda n: summand_note(l, n), 0, 30)
    print('  l=%d  spectral = %s   series = %s   diff = %s' % (l, mp.nstr(spec, 16), mp.nstr(ser, 16), mp.nstr(spec-ser, 3)), flush=True)
