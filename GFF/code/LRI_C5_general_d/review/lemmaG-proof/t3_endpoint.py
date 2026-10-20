# Test 3: endpoint behaviour of the product convolution a(V) near V=2pi (eq:endpoint):
# |a(2pi-eps)| ~ eps^{min(kappa-1,0)} (log at kappa=1), governed by the SUM kappa, not by single Re g_i.
import mpmath as mp
mp.mp.dps = 20
def conv2(g, al, V):
    h=[(lambda v,i=i: mp.expj(al[i]*v)*mp.power(1-mp.expj(v), g[i]-1)) for i in range(2)]
    pts=[0, V-2*mp.pi if V>2*mp.pi else None, V/2, 2*mp.pi if V>2*mp.pi else None, V]
    pts=sorted([p for p in pts if p is not None])
    return mp.quad(lambda v: h[0](v)*h[1](V-v), pts)
def conv3(g, al, V):
    # a = h1 * (h2*h3)
    h1=lambda v: mp.expj(al[0]*v)*mp.power(1-mp.expj(v), g[0]-1)
    inner=lambda W: conv2(g[1:], al[1:], W)
    return mp.quad(lambda v: h1(v)*inner(V-v), [0, V/2, V-mp.mpf(1)/10**6 if V>1 else V, V])
cases=[ ('r=2 g=(0.3,0.4)  kappa=0.7: expect slope -0.3', 2, [mp.mpc(0.3,0.2),mp.mpc(0.4,-0.1)], [mp.mpc(0.1,0.05),mp.mpf(-0.2)]),
        ('r=2 g=(0.45,0.55) kappa=1: expect log', 2, [mp.mpc(0.45,0.3),mp.mpf(0.55)], [mp.mpf(0.1),mp.mpf(0.2)]),
        ('r=2 g=(0.3,0.9) kappa=1.2: expect bounded', 2, [mp.mpf(0.3),mp.mpc(0.9,0.2)], [mp.mpf(0),mp.mpf(0.3)]),
        ('r=2 g=(0.15,0.25) kappa=0.4 (<1/2, outside (C)): expect slope -0.6', 2, [mp.mpf(0.15),mp.mpf(0.25)], [mp.mpf(0),mp.mpf(0)]),
]
for name,r,g,al in cases:
    print(name)
    prev=None
    for k in [2,3,4,5,6]:
        eps=mp.mpf(10)**-k
        for sgn in [+1,-1]:
            V=2*mp.pi-sgn*eps
            a=conv2(g,al,V)
            if sgn==+1:
                line='  eps=1e-%d  |a(2pi-eps)|=%.6e' % (k, abs(a))
                if prev is not None: line+='  slope=%.4f' % (mp.log(abs(a)/prev)/mp.log(mp.mpf(10)**-1))
                prev=abs(a)
            else:
                line+='   |a(2pi+eps)|=%.6e' % abs(a)
        print(line)
