import mpmath as mp
mp.mp.dps = 20
def conv2(g, al, V, eps):
    h=[(lambda v,i=i: mp.expj(al[i]*v)*mp.power(1-mp.expj(v), g[i]-1)) for i in range(2)]
    e=abs(eps)
    pts=set([mp.mpf(0), V/2, V])
    k=e
    while k < V/4:
        pts.add(k); pts.add(V-k); k*=4
    if V>2*mp.pi: pts.add(V-2*mp.pi); pts.add(2*mp.pi)
    pts=sorted(pts)
    return mp.quad(lambda v: h[0](v)*h[1](V-v), pts)
def pred_log_coef(g,al):
    # predicted coefficient of log(1/eps) at kappa=1 (r=2), from the two vertices
    return mp.expj(2*mp.pi*al[0])*mp.expjpi((g[0]-g[1])/2) + mp.expj(2*mp.pi*al[1])*mp.expjpi((g[1]-g[0])/2)
cases=[ ('r=2 g=(0.3+0.2i,0.4-0.1i) kappa=0.7: expect slope -0.3', [mp.mpc(0.3,0.2),mp.mpc(0.4,-0.1)], [mp.mpc(0.1,0.05),mp.mpf(-0.2)]),
        ('r=2 g=(0.45+0.3i,0.55) kappa=1: expect log', [mp.mpc(0.45,0.3),mp.mpf(0.55)], [mp.mpf(0.1),mp.mpf(0.2)]),
        ('r=2 g=(0.3,0.9+0.2i) alpha=(0.1,0.25) kappa=1.2: expect bounded, nonzero limit', [mp.mpf(0.3),mp.mpc(0.9,0.2)], [mp.mpf(0.1),mp.mpf(0.25)]),
]
for name,g,al in cases:
    print(name)
    prev=None; prevA=None
    for k in [2,3,4,5,6,7]:
        eps=mp.mpf(10)**-k
        a=conv2(g,al,2*mp.pi-eps,eps); ap=conv2(g,al,2*mp.pi+eps,eps)
        line='  eps=1e-%d  |a(2pi-eps)|=%.6e  |a(2pi+eps)|=%.6e' % (k, abs(a), abs(ap))
        if prev is not None:
            line+='  slope=%.4f  d a/d log10(1/eps)=%s' % (mp.log(abs(a)/prev)/mp.log(mp.mpf(10)**-1), mp.nstr((a-prevA)/1,6))
        prev=abs(a); prevA=a
        print(line)
    if abs(sum(mp.re(x) for x in g)-1)<1e-12:
        print('  predicted d a/d log10(1/eps) =', mp.nstr(pred_log_coef(g,al)*mp.log(10),6))
