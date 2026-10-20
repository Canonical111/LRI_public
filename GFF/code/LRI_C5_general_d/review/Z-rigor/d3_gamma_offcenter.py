"""d=3: c0hat(b) from the reviewed block code at OFF-CENTRE b vs the Gamma form -N_b^3 pi^5 Gamma(3g-2)/Gamma(g)^9."""
import sys, time
import mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/Z')
import z_blocks as zb
mp.mp.dps = 25
for b in ['1.2', '1.35', '1.6', '1.45+0.05j', '0.8']:
    st = time.time()
    with mp.workdps(40):
        b = mp.mpmathify(b)
        R, Mh, _ = zb.RM(3, b)
        sb, cb = mp.sin(mp.pi*b/2), mp.cos(mp.pi*b/2)
        c0 = cb*(1+cb)**2/8*Mh - mp.pi**3*sb**3/(1+cb)*R
        g = (3-b)/2; N = mp.gamma(mp.mpf(3)/2)*mp.gamma(g)/mp.gamma(b/2)
        gam = -N**3*mp.pi**5*mp.gamma(3*g-2)/mp.gamma(g)**9
    print('b=%s  c0hat=%s  Gamma form=%s  rel dev %s  (%.1fs)' % (mp.nstr(b, 6), mp.nstr(c0, 18), mp.nstr(gam, 18), mp.nstr(abs(c0/gam-1), 3), time.time()-st))
