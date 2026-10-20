"""Three-way comparison: non-perturbative Cauchy (cauchy/) vs exact RS rationals (rs_exact/) vs the package outputs."""
import json,glob,os
from fractions import Fraction
from mpmath import mp,mpf
mp.dps=60
B='<PROJECT>/lri_2d_coeff_expanse'
def pkg(scheme,L):
    for d in ('results/check_small_symmetry/d8','results/prod1_symmetry/d8'):
        f=f'{B}/{d}/{scheme}_L{L}.json'
        if os.path.exists(f):return json.load(open(f))['payload']['result']
def scaled(a,b):return max(abs(mpf(x)-mpf(y))/max(1,abs(mpf(y))) for x,y in zip(a,b))
def cvals(v):return [mpf(e['value']) if isinstance(e,dict) else mpf(e) for e in v]
worst_cr=worst_cp=mpf(0);n=0
for f in sorted(glob.glob('cauchy/results/*.json')):
    c=json.load(open(f));s=c['scheme'];L=int(c['L'])
    r=json.load(open(f'rs_exact/results/{s}_L{L}.json'))
    ex=lambda v:[mpf(Fraction(z).numerator)/Fraction(z).denominator for z in v]
    d_cr={'C':scaled(cvals(c['C']),ex(r['C'])),'r':scaled(cvals(c['r']),ex(r['r'])),'g':scaled(cvals(c['g']),ex(r['g'])),
          'E':max(scaled(cvals(c['E'][str(p)]),ex(r['E'][p])) for p in range(4)),
          'vac':max(scaled(cvals(c['vacua'][l]),ex(r['vacua'][l])) for l in c['vacua']) if c.get('vacua') and r.get('vacua') else mpf(0)}
    m=max(d_cr.values());worst_cr=max(worst_cr,m);n+=1
    p=pkg(s,L);line=f"{s:<10} L={L}  cauchy-vs-exact: "+' '.join(f"{k}={float(v):.1e}" for k,v in d_cr.items())
    if p:
        mp_=scaled([mpf(x) for x in p['C']],cvals(c['C']));worst_cp=max(worst_cp,mp_);line+=f" | package-vs-cauchy C={float(mp_):.1e}"
    print(line)
print(f'{n} cases; worst Cauchy vs exact-RS scaled difference {float(worst_cr):.2e}; worst package vs Cauchy (C) {float(worst_cp):.2e}')
