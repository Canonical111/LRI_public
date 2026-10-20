import mpmath as mp
mp.mp.dps = 30
# h_i(w) = e^{i al w} (1-e^{iw})^{g-1}; evaluate with w = 2pi - delta when near 2pi: 1-e^{iw} = 1-e^{-i delta}
def h_small(g, al, w):          # w near 0
    return mp.expj(al*w)*mp.power(-2j*mp.sin(w/2)*mp.expj(w/2), g-1)
def h_near2pi(g, al, delta):    # w = 2pi - delta, delta small (either sign)
    w = 2*mp.pi - delta
    z = 1-mp.expj(-delta)       # = 1 - e^{iw}
    z = 2j*mp.sin(delta/2)*mp.expj(-delta/2)
    return mp.expj(al*w)*mp.power(z, g-1)
def a_conv(g, al, eps):         # a(V) at V = 2pi - eps, r=2
    V = 2*mp.pi - eps
    def piece(i, j):            # factor i small variable u in (0, V/2); factor j at V-u = 2pi - (eps+u)
        def F(u):
            return h_small(g[i], al[i], u)*h_near2pi(g[j], al[j], eps+u)
        pts = set([mp.mpf(0), V/2]); e = abs(eps); k = e/8
        while k < V/2: pts.add(k); k *= 4
        if eps < 0: pts.add(-eps)
        return mp.quad(F, sorted(pts))
    return piece(0,1) + piece(1,0)
def pred_log_coef(g,al):
    return mp.expj(2*mp.pi*al[0])*mp.expjpi((g[0]-g[1])/2) + mp.expj(2*mp.pi*al[1])*mp.expjpi((g[1]-g[0])/2)
cases=[ ('kappa=0.7: g=(0.3+0.2i,0.4-0.1i): expect |a| ~ eps^-0.3', [mp.mpc(0.3,0.2),mp.mpc(0.4,-0.1)], [mp.mpc(0.1,0.05),mp.mpf(-0.2)]),
        ('kappa=1:   g=(0.45+0.3i,0.55): expect a ~ c log(1/eps)', [mp.mpc(0.45,0.3),mp.mpf(0.55)], [mp.mpf(0.1),mp.mpf(0.2)]),
        ('kappa=1.2: g=(0.3,0.9+0.2i): expect finite nonzero limit', [mp.mpf(0.3),mp.mpc(0.9,0.2)], [mp.mpf(0.1),mp.mpf(0.25)]),
        ('kappa=1.2 single Re g=0.3<1 and other 0.9 with alpha=(0,g1): limit 0 by 1/Gamma(0)', [mp.mpf(0.3),mp.mpc(0.9,0.2)], [mp.mpf(0),mp.mpf(0.3)]),
]
for name,g,al in cases:
    print(name)
    prev=None; prevA=None
    for k in [2,3,4,5,6,8]:
        eps=mp.mpf(10)**-k
        a=a_conv(g,al,eps); ap=a_conv(g,al,-eps)
        line='  eps=1e-%d  |a(2pi-eps)|=%.6e  |a(2pi+eps)|=%.6e' % (k, abs(a), abs(ap))
        if prev is not None:
            line+='  slope=%.4f' % (mp.log(abs(a)/prev)/mp.log(eps/prevE))
            if abs(sum(mp.re(x) for x in g)-1)<1e-12:
                line+='  da/dlog(1/eps)=%s' % mp.nstr((a-prevA)/mp.log(prevE/eps),6)
        prev=abs(a); prevA=a; prevE=eps
        print(line)
    if abs(sum(mp.re(x) for x in g)-1)<1e-12:
        print('  predicted da/dlog(1/eps) =', mp.nstr(pred_log_coef(g,al),6))
