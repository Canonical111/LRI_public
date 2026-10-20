"""Construct Hepp sectors directly from alternating Coulomb-gas kernels.
No cached symbolic objects or external data are required.
"""
import itertools
import sympy as s


def build_sectors(name: str):
    if name not in {'Q4', 'Z4', 'G5'}:
        raise ValueError('name must be Q4, Z4, or G5')
    m = 4 if name == 'G5' else 3
    rr = s.symbols('r:'+str(m), positive=True)
    if m == 3:
        r,t,w = rr
        W = (r+t)**2*(t+w)**2/(r*r*t*t*w*w*(r+t+w)**2)
        mean = r+w if name == 'Q4' else s.Integer(1)
    else:
        r,t,w,y = rr
        W = ((r+t)**2*(t+w)**2*(w+y)**2*(r+t+w+y)**2 /
             (r*r*t*t*w*w*y*y*(r+t+w)**2*(t+w+y)**2))
        mean = s.Integer(1)
    nW = 4  # all three kernels W have homogeneity -4
    xx = s.symbols('x:'+str(m-1), nonnegative=True)
    levels = [s.Integer(1)]
    for x in xx:
        levels.append(levels[-1]*x)

    def strip(f):
        num, den = s.fraction(s.cancel(f))
        pn, pd = s.Poly(num,*xx), s.Poly(den,*xx)
        emn = [min(mm[j] for mm in pn.monoms()) for j in range(m-1)]
        emd = [min(mm[j] for mm in pd.monoms()) for j in range(m-1)]
        expo = tuple(a-b for a,b in zip(emn,emd))
        return expo, s.factor(f/s.prod(x**e for x,e in zip(xx,expo)))

    seen, sectors = {}, []
    for perm in itertools.permutations(range(m)):
        mp = {rr[perm[j]]:levels[j] for j in range(m)}
        eW, Ws = strip(W.subs(mp, simultaneous=True))
        eM, Ms = strip(mean.subs(mp, simultaneous=True))
        S = sum(levels)
        k0 = m+(1 if name == 'Q4' else 0)-nW
        p = tuple(m-2-j+eW[j]+eM[j] for j in range(m-1))
        H0 = s.factor(Ws*Ms*S**(-k0))
        key = (p,eW,H0)
        if key in seen:
            sectors[seen[key]]['mult'] += 1
            continue
        seen[key] = len(sectors)
        sectors.append(dict(xx=xx,p=p,c=eW,H0=H0,W=Ws,S=S,
                            nW=nW,mult=1,perm=perm))
    return sectors
