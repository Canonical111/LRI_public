"""Primitive P_a from eq:primitive-input via the Gauss pairings eq:Iij.
All Gauss functions evaluated on x in (0,1/2] by own series:
 v(x)=2F1(1/4,1/4;1;x), h(x)=2F1(1/4,1/4;1/2;x)   (direct)
 v(1-x) = sqrt(pi)/G(3/4)^2 h(x) - 2 sqrt(pi)/G(1/4)^2 sqrt(x) 2F1(3/4,3/4;3/2;x)
 h(1-x) = sqrt(pi)/G(1/4)^2 [ sum c_n (2psi(n+1)-2psi(n+1/4)) x^n - log(x) v(x) ]
I_ij = int_0^{1/2} [p_i(x)p_j(1-x)+p_j(x)p_i(1-x)] / (pi^{i+j} sqrt(x(1-x))) dx
"""
import mpmath as mp, json, time, sys

mp.mp.dps = 75
pi = mp.pi
t0 = time.time()
Q = mp.gamma(mp.mpf(1)/4)**4/pi
sQ = mp.sqrt(Q)
NT = 300
q4 = mp.mpf(1)/4
c = []; d = []; e = []; kap = []
cn = mp.mpf(1); dn = mp.mpf(1); en = mp.mpf(1)
for n in range(NT):
    c.append(cn); d.append(dn); e.append(en)
    kap.append(2*mp.digamma(n+1) - 2*mp.digamma(n+q4))
    cn *= ((n+q4)/(n+1))**2
    dn *= (n+q4)**2/((n+mp.mpf(1)/2)*(n+1))
    en *= (n+3*q4)**2/((n+mp.mpf(3)/2)*(n+1))
ck = [c[n]*kap[n] for n in range(NT)]
pref_v1 = mp.sqrt(pi)/mp.gamma(3*q4)**2
pref_w = -2*mp.sqrt(pi)/mp.gamma(q4)**2
pref_h1 = mp.sqrt(pi)/mp.gamma(q4)**2

def horner(co, x, nt):
    s = mp.mpf(0)
    for k in range(nt-1, -1, -1):
        s = s*x + co[k]
    return s

cache = {}
def funcs(x):
    key = x
    if key in cache: return cache[key]
    # number of terms needed: x^n < 10^-(dps+5)
    if x > 0:
        nt = min(NT, int((mp.mp.dps + 8)/max(-mp.log10(x), mp.mpf('0.3'))) + 5)
    else:
        nt = 1
    v = horner(c, x, nt); h = horner(d, x, nt); w = horner(e, x, nt)
    v1 = pref_v1*h + pref_w*mp.sqrt(x)*w
    h1 = pref_h1*(horner(ck, x, nt) - mp.log(x)*v)
    out = (v, h, v1, h1)
    cache[key] = out
    return out

# validation of the connection formulas against mpmath hyp2f1 at moderate x
for x in [mp.mpf('0.1'), mp.mpf('0.3'), mp.mpf('0.47')]:
    v, h, v1, h1 = funcs(x)
    print('x=%s: v %s  h %s  v(1-x) %s  h(1-x) %s' % (x,
        mp.nstr(v - mp.hyp2f1(q4, q4, 1, x), 3), mp.nstr(h - mp.hyp2f1(q4, q4, 0.5, x), 3),
        mp.nstr(v1 - mp.hyp2f1(q4, q4, 1, 1-x), 3), mp.nstr(h1 - mp.hyp2f1(q4, q4, 0.5, 1-x), 3)))
    # note's elliptic identities (eq:elliptic-coordinate), tested only
    for xx, vv, hh1 in [(x, v, h1), (1-x, v1, h)]:
        m = xx/(2*(1+mp.sqrt(1-xx)))
        Kx = mp.ellipk(m); Kc = mp.ellipk(1-m)
        print('   elliptic check at %s: v-2K/pi %s, sqrtQ h(1-x)-2(K+Kc) %s' % (mp.nstr(xx, 3),
              mp.nstr(vv - 2*Kx/pi, 3), mp.nstr(sQ*hh1 - 2*(Kx+Kc), 3)))
cache.clear()

def p(i, y_is_x, x):
    v, h, v1, h1 = funcs(x)
    if y_is_x:   # p_i(x)
        return [v**2, sQ*v*h1, Q*h1**2][i]
    else:        # p_i(1-x)
        return [v1**2, sQ*v1*h, Q*h**2][i]

def integrand(i, j):
    def f(x):
        if x == 0: return mp.mpf(0)
        num = p(i, True, x)*p(j, False, x) + p(j, True, x)*p(i, False, x)
        return num/(pi**(i+j)*mp.sqrt(x*(1-x)))
    return f

res = {}
def integrand_w(i, j):
    f = integrand(i, j)
    return lambda w: 2*w*f(w*w) if w != 0 else mp.mpf(0)
r2 = 1/mp.sqrt(2)
for mode, split in (('x', [0, mp.mpf(1)/16, mp.mpf(1)/4, mp.mpf(1)/2]), ('w', [0, r2/4, r2/2, r2])):
    for (i, j) in [(0,0), (1,1), (2,2), (1,2), (0,2), (0,1)]:
        F = integrand(i, j) if mode == 'x' else integrand_w(i, j)
        val, err = mp.quad(F, split, error=True, maxdegree=9)
        res.setdefault('I%d%d' % (i, j), []).append(val)
        print('I%d%d mode %s = %s  (quad err est %s)  t=%.1f' % (i, j, mode,
              mp.nstr(val, 60), mp.nstr(err, 3), time.time()-t0)); sys.stdout.flush()
    cache.clear()

out = {}
for k, vals in res.items():
    print(k, 'split difference', mp.nstr(vals[1]-vals[0], 3))
    out[k] = mp.nstr(vals[1], 72)
I = {k: res[k][1] for k in res}
Pa_in = pi**4*(15*I['I22'] + 24*I['I11'] - 4*I['I00'])
rel = I['I22'] - 4*I['I12'] + 4*I['I02'] - 4*I['I00']
Pa_rw = pi**4*(60*(I['I12'] - I['I02']) + 24*I['I11'] + 56*I['I00'])
print('P_a (eq:primitive-input)    =', mp.nstr(Pa_in, 65))
print('contour relation I22-4I12+4I02-4I00 =', mp.nstr(rel, 3), ' (scale I22 =', mp.nstr(I['I22'], 5), ')')
print('P_a rewritten - P_a input   =', mp.nstr(Pa_rw - Pa_in, 3))
print('96 P_a =', mp.nstr(96*Pa_in, 65))
out['Pa'] = mp.nstr(Pa_in, 72); out['Pa_rewritten'] = mp.nstr(Pa_rw, 72); out['relation'] = mp.nstr(rel, 5)
json.dump(out, open('primitive.json', 'w'), indent=1)
print('t=%.1f' % (time.time()-t0))
