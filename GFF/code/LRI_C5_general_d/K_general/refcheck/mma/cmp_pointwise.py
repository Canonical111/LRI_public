import sys, re
sys.path.insert(0,'<PROJECT>/LRI_C5_general_d/K_general/refcheck')
import mpmath as mp
import routeA_spectral as A
A.init('1.25', 45)
mp.mp.dps = 45
def parse(s):
    s = s.strip()
    s = re.sub(r'``-?[0-9.]+', '', s); s = re.sub(r'`-?[0-9.]*', '', s)
    s = s.replace('*^', 'e')
    m = re.match(r'^\(?([-+]?[0-9.]+(?:e[-+]?[0-9]+)?)\s*([-+])\s*([0-9.]+(?:e[-+]?[0-9]+)?)\*I\)?$', s)
    if m:
        re_, sg, im_ = m.groups(); return mp.mpc(mp.mpf(re_), (1 if sg == '+' else -1) * mp.mpf(im_))
    m = re.match(r'^([-+0-9.e]+)$', s)
    if m: return mp.mpf(s)
    m = re.match(r'^([-+]?[0-9.e]+)\*I$', s)
    if m: return mp.mpc(0, mp.mpf(m.group(1)))
    raise ValueError(s)
worst = 0
for line in open('<PROJECT>/LRI_C5_general_d/K_general/refcheck/mma/pointwise_check.out'):
    parts = [x.strip() for x in line.split('|')]
    ls, nus, vals = parts[0], parts[1], [parse(x) for x in parts[2:]]
    l = mp.mpc(0.5, 3) if 'I' in ls else mp.mpf(ls)
    nu = mp.mpf(mp.fraction(*map(int, nus.split('/')))) if '/' in nus else mp.mpf(nus)
    real = not isinstance(l, mp.mpc)
    a = l/2 + A.G['al0']
    v, env = A.vec_integrand(a, nu, real)
    rels = [abs(v[i]-vals[i])/abs(vals[i]) for i in range(5)]
    worst = max(worst, max(rels))
    print('l=%-10s nu=%-5s max rel diff mpmath vs Mathematica over 5 integrands: %s' % (ls, nus, mp.nstr(max(rels), 3)))
print('worst', mp.nstr(worst, 3))
