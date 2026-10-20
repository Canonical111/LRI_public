# Build bivariate H kernels from the ordered parameter lists of eq:HW, eq:H7, eq:HP using the
# convention around eq:localH (shared group: m0=0; first n0 upper -> Gamma(1-e-Es-Ft) numerator,
# remaining upper -> Gamma(e+Es+Ft) denominator, every lower -> Gamma(1-f-As-Bt) denominator)
# and compare with the simplified kernels eq:HWkernel, eq:H7kernel/eq:A7kernel, eq:HPkernel.
import mpmath as mp
from params import setup
from kernels import N_alpha, Pt, A_7, Psi_sig
P = setup(40); mp.mp.dps = 40
G = mp.gamma; pi = mp.pi
h = mp.mpf(1)/2; q = mp.mpf(1)/4

def local(x, a, b, m, n):   # a,b: lists of (param, coeff)
    num = 1; den = 1
    for j, (bj, Bj) in enumerate(b):
        if j < m: num *= G(bj + Bj*x)
        else: den *= G(1 - bj - Bj*x)
    for j, (aj, Aj) in enumerate(a):
        if j < n: num *= G(1 - aj - Aj*x)
        else: den *= G(aj + Aj*x)
    return num/den

def shared(s, t, up, low, n0):  # up, low: lists of (param, E, F)
    num = 1; den = 1
    for j, (e, E, F) in enumerate(up):
        if j < n0: num *= G(1 - e - E*s - F*t)
        else: den *= G(e + E*s + F*t)
    for (f, A_, B_) in low:
        den *= G(1 - f - A_*s - B_*t)
    return num/den

def rel(x, y): return mp.nstr(abs(x - y)/abs(y), 3)
pts = [(mp.mpc(0.25, 0.7), mp.mpc(0.125, -0.4)), (mp.mpc(0.25, -2.1), mp.mpc(0.0625, 1.3)), (mp.mpc(0.1, 0.33), mp.mpc(0.2, 0.9))]
aW = P['alphaW']; b7 = P['beta7']; bp = P['betap']; bm = P['betam']
for s, t in pts:
    # eq:HW : H^{0,2;2,3;2,2}_{2,2;5,5;2,2}
    K = (shared(s, t, [(h, 1, 1)]*2, [(-h, 1, 1)]*2, 2)
         * local(s, [(h, 1)]*4 + [(aW, 1)], [(0, 1)]*4 + [(aW, 1)], 2, 3)
         * local(t, [(h, 1), (0, 1)], [(0, 1), (h, 1)], 2, 2))
    Ks = N_alpha(s, aW)*Pt(t)/(h - s - t)**2
    # eq:H7 : H^{0,1;3,8;2,3}_{1,1;10,10;5,5}
    a7 = [(-q, 1)] + [(h, 1)]*7 + [(b7, 1), (mp.conj(b7), 1)]
    bb7 = [(0, 1)]*6 + [(1, 1), (3*q, 1), (b7, 1), (mp.conj(b7), 1)]
    c7 = [(0, 1), (h, 1), (h, 1), (q, 1), (3*q, 1)]
    d7 = [(0, 1), (h, 1), (-h, 1), (q, 1), (3*q, 1)]
    K7 = shared(s, t, [(h, 1, 1)], [(-h, 1, 1)], 1)*local(s, a7, bb7, 3, 8)*local(t, c7, d7, 2, 3)
    K7s = A_7(s, b7)*mp.cot(2*pi*t)/((h - t)*(h - s - t))
    # eq:HP : H^{0,0;3,3;3,3}_{0,1;6,5;6,5}
    ap = [(h, 1)]*4 + [(bp, 1), (mp.conj(bp), 1)]; bp_ = [(0, 1)]*3 + [(bp, 1), (mp.conj(bp), 1)]
    am = [(h, 1)]*4 + [(bm, 1), (mp.conj(bm), 1)]; bm_ = [(0, 1)]*3 + [(bm, 1), (mp.conj(bm), 1)]
    KP = shared(s, t, [], [(0, 1, 1)], 0)*local(s, ap, bp_, 3, 3)*local(t, am, bm_, 3, 3)
    KPs = Psi_sig(s, bp)*Psi_sig(t, bm)/G(1 - s - t)
    print(f"(s,t)=({mp.nstr(s,4)},{mp.nstr(t,4)}):  HW list/kernel rel diff {rel(K, Ks)};  H7 {rel(K7, K7s)};  H* {rel(KP, KPs)}")
    # also the stated 'second local gamma quotient = cot(2 pi t)/(1/2-t)'
    print("    t-group of eq:H7 vs cot(2pi t)/(1/2-t):", rel(local(t, c7, d7, 2, 3), mp.cot(2*pi*t)/(h - t)),
          "; shared HW quotient vs 1/(1/2-s-t)^2:", rel(shared(s, t, [(h, 1, 1)]*2, [(-h, 1, 1)]*2, 2), 1/(h - s - t)**2))
