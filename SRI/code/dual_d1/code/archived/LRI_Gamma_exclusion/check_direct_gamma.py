#!/usr/bin/env python3
"""Independent endpoint derivatives by direct Gamma evaluation (not a proof)."""
from pathlib import Path
import json
import mpmath as mp
import exact_endpoint as ex

def run(dps):
    mp.mp.dps=dps
    def num(v):
        v=ex.s.Rational(v)
        return mp.mpf(int(v.p))/int(v.q)
    def kernel(a,b,y,t):
        return 1-mp.gamma(1+a*y)**2*mp.rgamma(1+a*y+b*t)*mp.rgamma(1+a*y-b*t)
    def polys(y,rows):return sum(num(v)*y**j for j,v in enumerate(rows))
    def model(y,t,tau):
        v=y*y-4*t*t+t*t*polys(y,ex.P)
        v+=t*t*sum(polys(y,a)*kernel(*ab,y,t) for ab,a in ex.PS.items())
        for (pt,py,ab),(c0,c1) in ex.extra.items():
            v+=(num(c0)+tau*num(c1))*t**pt*y**py*(1 if ab is None else kernel(*ab,y,t))
        return v
    q=mp.mpf(1)/2
    f0=lambda y,t:model(y,t,0)
    f1=lambda y,t:model(y,t,1)-model(y,t,0)
    reports={}
    for label,fn,jet in [('S0',f0,ex.S0),('S1',f1,ex.S1)]:
        worst=mp.mpf(0)
        for n in range(4):
            for i in range(n+1):
                j=n-i
                got=mp.diff(fn,(q,q),(i,j))
                target=ex.get(jet,i,j).subs({ex.pi:ex.s.pi,ex.L:ex.s.log(2),ex.Z:ex.s.zeta(3)})
                target=mp.mpf(str(ex.s.N(target,dps)))
                worst=max(worst,abs(got-target))
        assert worst < mp.power(10,-dps+8)
        reports[label]=mp.nstr(worst,12)
    return {'dps':dps,'max_absolute_residual':reports}
if __name__=='__main__':
    report={'scope':'Direct numerical differentiation; distinct from the rational interval proof.','runs':[run(40),run(60)]}
    Path(__file__).with_name('direct_gamma_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
