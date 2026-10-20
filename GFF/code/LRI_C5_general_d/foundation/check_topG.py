"""Quick independent checks of Theorem 6 (top modes of products of balanced kernels), 2026-10-03.

(i)   kernel identity of Step 5: h_i(v) = exp(-i pi (g_i-1)) exp(i(d/2-1-sigma) v) h'_i(v) on (0, 2 pi)
      under per-factor balance, principal powers, complex g_i;
(ii)  mixed-wheel dictionary: prod_i g_l((l+sigma)/2+n+t+delta_i; b_i) = T_l(n+t) with
      g_i=(d-b_i)/2, alpha_i=(b_i/2-sigma)/2+delta_i, beta_i=(b_i/2-sigma)/2-delta_i;
(iii) top modes gamma_{+-(r-1)} of Xi = D S from 2r+1 real nodes, in the large-varkappa regime where plain
      truncated lattice sums are accurate (no tail acceleration). Truncation level is read off from the
      boundary modes gamma_{+-r} (absent by part (b)) and from the change between two cutoffs.
      Cases include one Re g_i < 0 (Step 7, continuation), r = 3, 4, d = 0.6, 1.7, 3.3, complex sigma and shifts.
      Controls keep the total balance but shift beta_1 by +0.1 and beta_2 by -0.1.
Run: python3 check_topG.py > check_topG.log   (about 20 s on one Mac core; mpmath, dps 30)
"""
import time, random, mpmath as mp
mp.mp.dps = 30

def fg(g, w):
    return mp.gamma(w)*mp.rgamma(w+g)

def kernel(l, s, b, d):            # balanced Barnes kernel g_l(s;b), eq. (2)
    a = mp.mpf(l)/2 + b/4; G = (d-b)/2
    return mp.gamma(a+s)*mp.gamma(a-s)*mp.rgamma(a+G+s)*mp.rgamma(a+G-s)

def dl_list(d, M):                 # coefficients of (1+z)(1-z)^(1-d)
    c = [mp.mpf(1)]
    for k in range(1, M+1):
        c.append(c[-1]*(d-1+k-1)/k)
    return [c[0]] + [c[l]+c[l-1] for l in range(1, M+1)]

def xi(t, d, sig, al, be, g, N, M, dl):
    r = len(g)
    L = {m: mp.fprod(fg(g[i], m+t+sig+al[i]) for i in range(r)) for m in range(-N, M+1)}
    R = {n: mp.fprod(fg(g[i], be[i]-n-t) for i in range(r)) for n in range(-N, N+1)}
    S = mp.fsum(R[n]*mp.fsum(dl[m-n]*L[m] for m in range(n, M+1)) for n in range(-N, N+1))
    D = mp.fprod(mp.sin(mp.pi*(t+sig+al[i]))*mp.sin(mp.pi*(t-be[i])) for i in range(r))
    return D*S

def modes(d, sig, al, g, N, M, defect=None, t0=mp.mpf('0.0731')):
    r = len(g); d = mp.mpf(d)
    be = [d/2 - sig - al[i] - g[i] for i in range(r)]
    if defect:
        be = [be[i] + defect[i] for i in range(r)]
    dl = dl_list(d, N+M+2); K = 2*r+1
    ts = [t0 + mp.mpf(j)/K for j in range(K)]
    X = [xi(t, d, sig, al, be, g, N, M, dl) for t in ts]
    gam = {m: mp.fsum(X[j]*mp.expjpi(-2*m*ts[j]) for j in range(K))/K for m in range(-r, r+1)}
    mx = max(abs(gam[m]) for m in gam)
    return {m: float(abs(gam[m])/mx) for m in sorted(gam)}

def C(x, y): return mp.mpc(x, y)

random.seed(20261003)
print('(i) kernel identity h_i = exp(-i pi(g-1)) exp(i(d/2-1-sigma)v) h\'_i on (0,2pi)')
worst = 0
for _ in range(200):
    d = mp.mpf(random.uniform(0.2, 3.8)); sig = C(random.uniform(-1, 1), random.uniform(-1, 1))
    al = C(random.uniform(-1, 1), random.uniform(-1, 1)); g = C(random.uniform(-2, 3), random.uniform(-1, 1))
    be = d/2 - sig - al - g; v = mp.mpf(random.uniform(0.01, 2*3.14159))
    h = mp.expj(al*v)*mp.power(1-mp.expj(v), g-1)
    hp = mp.expj(-be*v)*mp.power(1-mp.expj(-v), g-1)
    rhs = mp.expjpi(-(g-1))*mp.expj((d/2-1-sig)*v)*hp
    worst = max(worst, abs(h-rhs)/abs(h))
print('    200 random points: max rel. deviation %.1e' % worst)

print('(ii) mixed-wheel dictionary')
worst = 0
for _ in range(60):
    d = mp.mpf(random.uniform(0.2, 3.8)); r = random.choice([2, 3, 4]); l = random.randint(0, 6); n = random.randint(-8, 8)
    sig = C(random.uniform(-1, 1), random.uniform(-.5, .5)); t = C(random.uniform(0, 1), random.uniform(-.7, .7))
    b = [C(random.uniform(-1, 3), random.uniform(-.5, .5)) for _ in range(r)]
    de = [C(random.uniform(-1, 1), random.uniform(-.5, .5)) for _ in range(r)]
    lhs = mp.fprod(kernel(l, (l+sig)/2+n+t+de[i], b[i], d) for i in range(r))
    gi = [(d-b[i])/2 for i in range(r)]; al = [(b[i]/2-sig)/2+de[i] for i in range(r)]; be = [(b[i]/2-sig)/2-de[i] for i in range(r)]
    rhs = mp.fprod(fg(gi[i], l+sig+al[i]+n+t)*fg(gi[i], be[i]-n-t) for i in range(r))
    bal = max(abs(sig+al[i]+be[i]+gi[i]-d/2) for i in range(r))
    worst = max(worst, abs(lhs-rhs)/abs(lhs), bal)
print('    60 random (d, r, l, n, sigma, t, b_i, delta_i): max rel. deviation (and balance defect) %.1e' % worst)

print('(iii) top modes |gamma_m|/max|gamma| from 2r+1 real nodes; cutoffs (N, M)')
cases = {
 'A d=1.7 r=3 all Re g_i>0':
   dict(d='1.7', sig=C('0.31', '0.12'), al=[C('0.2', '-0.15'), C('-0.4', '0.3'), C('0.05', '0.1')],
        g=[C('4.3', '0.4'), C('3.1', '-0.3'), C('2.6', '0.2')]),
 'B d=1.7 r=3 Re g_3<0':
   dict(d='1.7', sig=C('0.31', '0.12'), al=[C('0.2', '-0.15'), C('-0.4', '0.3'), C('0.05', '0.1')],
        g=[C('5.3', '0.4'), C('5.1', '-0.3'), C('-0.7', '0.2')]),
 'C d=3.3 r=3 Re g_3<0':
   dict(d='3.3', sig=C('-0.45', '0.2'), al=[C('0.6', '0.1'), C('-0.25', '-0.2'), C('0.33', '0')],
        g=[C('6.2', '-0.5'), C('4.4', '0.3'), C('-1.3', '0.25')]),
 'D d=0.6 r=4 Re g_4<0':
   dict(d='0.6', sig=C('0.7', '-0.1'), al=[C('0.1', '0.2'), C('-0.3', '0'), C('0.45', '-0.2'), C('0', '0.05')],
        g=[C('3.2', '0.1'), C('3.3', '-0.2'), C('3.9', '0.3'), C('-0.6', '0.1')]),
}
for name, c in cases.items():
    for (N, M) in [(60, 60), (110, 110)]:
        t = time.time(); md = modes(c['d'], c['sig'], c['al'], c['g'], N, M)
        print('  %-26s (%3d,%3d) ' % (name, N, M) + '  '.join('%+d:%.1e' % (m, v) for m, v in md.items()) + '  (%.1fs)' % (time.time()-t), flush=True)
    r = len(c['g']); de = [0]*r; de[0] = mp.mpf('0.1'); de[1] = mp.mpf('-0.1')
    md = modes(c['d'], c['sig'], c['al'], c['g'], 110, 110, defect=de)
    print('  %-26s (110,110) ' % '  control (B broken)' + '  '.join('%+d:%.1e' % (m, v) for m, v in md.items()), flush=True)
