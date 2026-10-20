"""d=1: direct midpoint-lattice sum Mh(1;b) (Lemma nodeb, by brute force + Richardson) versus the relation
Mh = 8 pi^3 s^3 R/(c (1+c)^3) implied by c0hat = 0 (parity) and the two-node formula; R by Dixon."""
import mpmath as mp, time
mp.mp.dps = 45
M0, K = 32, 10
def run(b):
    b = mp.mpmathify(b); d = 1; sig = b/2; g = (mp.mpf(d)-b)/2
    N = mp.gamma(mp.mpf(d)/2)*mp.gamma(g)/mp.gamma(sig)
    tot = 0
    for l in (0, 1):
        a = (l + sig)/2; be = a + g
        gl = lambda s: mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(be+s)*mp.gamma(be-s))
        s0 = mp.mpf(l+1)/2 - 1 if l == 0 else mp.mpf(0)   # l=0: lattice 1/2+Z, symmetric pairs +-1/2,+-3/2..; l=1: Z
        # sum over the lattice using evenness: l=0 -> 2*sum_{k>=0} g(k+1/2)^3 ; l=1 -> g(0)^3 + 2 sum_{k>=1} g(k)^3
        if l == 0:
            term = lambda k: 2*gl(k + mp.mpf(1)/2)**3
            base = 0
        else:
            term = lambda k: 2*gl(k + 1)**3
            base = gl(0)**3
        parts = []; acc = 0; idx = 0
        for i in range(K+1):
            Mi = M0*2**i
            while idx < Mi:
                acc += term(idx); idx += 1
            parts.append(acc)
        e0 = 1 - 6*g
        n = len(parts); Ms = [mp.mpf(M0)*2**i for i in range(n)]
        A = mp.matrix(n, n); y = mp.matrix(n, 1)
        for i in range(n):
            A[i, 0] = 1
            for k in range(n-1): A[i, k+1] = Ms[i]**(e0-k)
            y[i] = parts[i]
        tot += base + mp.lu_solve(A, y)[0]
    Mh = N**3*tot
    R = mp.gamma(1+b/2)*mp.gamma(1-3*b/2)/(mp.gamma(1+b)*mp.gamma(1-b/2)**2*mp.gamma(1-b))
    s, c = mp.sin(mp.pi*b/2), mp.cos(mp.pi*b/2)
    pred = 8*mp.pi**3*s**3*R/(c*(1+c)**3)
    return Mh, pred
for b in ['0.3', '0.5', '0.2']:
    st = time.time(); Mh, pred = run(b)
    print('b=%s  Mh direct = %s   8pi^3 s^3 R/(c(1+c)^3) = %s   rel %s  (%.0fs)' % (b, mp.nstr(Mh, 25), mp.nstr(pred, 25), mp.nstr(abs(Mh/pred-1), 3), time.time()-st))
