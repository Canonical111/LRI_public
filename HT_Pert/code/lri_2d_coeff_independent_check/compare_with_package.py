"""Compare the clean-room exact RS results with the package's outputs (all quantities, all schemes, common L)."""
import json,glob,os
from fractions import Fraction
B='<PROJECT>/lri_2d_coeff_expanse'
def pkg(scheme,L):
    for d in ('results/check_small_symmetry/d8','results/prod1_symmetry/d8'):
        f=f'{B}/{d}/{scheme}_L{L}.json'
        if os.path.exists(f):return json.load(open(f))['payload']['result'],d.split('/')[1]
    return None,None
def err(a,b):  # scaled: |a-b|/max(1,|b|), b = exact
    return max(abs(x-y)/max(1,abs(y)) for x,y in zip(a,b))
rows=[];worst=0
for f in sorted(glob.glob(f'{B}/independent_check/rs_exact/results/*.json')):
    d=json.load(open(f));s=d['scheme'];L=d['L'];p,src=pkg(s,L)
    if p is None:continue
    ex=lambda v:[float(Fraction(z)) for z in v]
    e={'C':err(p['C'],ex(d['C'])),'r':err(p['r'],ex(d['r'])),'g':err(p['g'],ex(d['g'])),
       'E':max(err(pe,ex(de)) for pe,de in zip(p['energies'],d['E']))}
    grids=list(range(0,L+1,2)) if s!='raw' else [L]
    assert len(p['vacuum_coefficients'])==len(grids)
    e['vac']=max(err(row,ex(d['vacua'][str(l)])) for row,l in zip(p['vacuum_coefficients'],grids))
    m=max(e.values());worst=max(worst,m);rows.append((s,L,src,e,m))
for s,L,src,e,m in rows:print(f"{s:<10} L={L:<3} {src:<22} "+' '.join(f"{k}={v:.1e}" for k,v in e.items()))
print(f'{len(rows)} (scheme,L) pairs compared; worst scaled difference {worst:.2e}')
