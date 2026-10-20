import sys, time
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/foundation')
import mpmath as mp
from wheel_general_b import Wheel, W
from hypsums import GammaSeq, PolySeq, single_sum, conv_sum, moment_product_sum

def R_of_b(w):
    """residue-prefactor sum R(b) = sum_{l,n>=0} d_l T_ln^3."""
    r, q, s, g = w.r, w.q, w.sig, w.g
    T0 = GammaSeq([(s, 2*q, r), (1-g, 1, r)])
    val = single_sum(T0, 0, w.N, w.K)
    F = GammaSeq([(1+s, 1+2*q, r)])
    Gs = GammaSeq([(1-g, 1, r)])
    pre = w.pref4q * (s/(2*q))**r
    if w.mult == 'delta':
        val += pre * single_sum(F.product(Gs), 0, w.N, w.K)
    else:
        muY = getattr(w, 'muD', None)
        val += pre * conv_sum(F, w.mult, Gs, M=w.M, N=w.N, K=w.K, muY=muY)
    return val

def M_of_b(w):
    tb = (1 - w.sig)/2
    S = 2*w.A0(tb) + 2*w.Aplus(tb) + w.Cmid(tb)
    return w.Nb()**w.r * S, S

mp.mp.dps = 25
for d, b in [(1, '0.5'), (1, '0.43'), (2, '1'), (2, '0.9'), (3, '1.5'), (3, '1.4'), ('1.5', '0.75'), ('1.5','0.7'), ('2.5','1.25'), ('2.5','1.2')]:
    st = time.time()
    d = mp.mpf(d) if not isinstance(d, int) else d
    b = mp.mpf(b)
    w = Wheel(3, d, b)
    R = R_of_b(w)
    Mh, S = M_of_b(w)
    sg = mp.sin(mp.pi*b/2); cg = mp.cos(mp.pi*b/2)
    u = 2*mp.pi**2*(1+2*cg)/sg**2
    v = cg*(1+cg)**2/(2*mp.pi*sg**3)
    Wred = u*R + v*Mh
    Wref = W(3, d, b, 20)
    # zero mode
    c0hat = cg*(1+cg)**2*Mh/8 - mp.pi**3*sg**3*R/(1+cg)
    print(d, b, mp.nstr(Wred, 18), mp.nstr(Wref, 18), mp.nstr(abs(Wred-Wref)/abs(Wref), 3), 'Mhat=', mp.nstr(Mh, 10), 'c0hat=', mp.nstr(c0hat, 10), '%.1fs' % (time.time()-st))
