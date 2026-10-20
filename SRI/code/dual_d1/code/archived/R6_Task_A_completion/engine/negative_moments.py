"""Exact inverse-Euler moments of the negative-power boundary jets.

At p<0, if B_p(L)=sum b_j L^j, then the volume polynomial solving
(p+d/dL)M_p=-B_p has M_p(0)=sum j! b_j/(-p)^(j+1) and
M'_p(0)=sum_{j>=1} j! b_j/(-p)^j. This module applies those linear
functionals directly, without calculating any integration constants.
The explicit scale corrections to the mixed insertion are added later.
"""
from pathlib import Path
from fractions import Fraction as Q
from functools import lru_cache
from math import comb,factorial
import os,json,time,hashlib,argparse
os.environ.setdefault('R6_ACCEL','1');os.environ.setdefault('R6_NATIVE','1' if Path(__file__).with_name('poly_multiply.so').exists() else '0')
import finish_boundaries as fb
import moving_terminal as mt
import terminal_projection as tp
ROOT=Path(__file__).resolve().parent.parent
DEMANDS=((-2,0),(-2,1),(-1,0),(-1,1))
@lru_cache(maxsize=100000)
def weighted_poly(k,H,kappa,N,p,r,shift=0):
    assert p<0 and r in (0,1)
    out=Q(0)
    for n in range(k+2):
        a=k-n+1;d=a+p-kappa
        if d<0:continue
        h=mt.large(H,n)
        integ=mt.intlog(h) if a==0 else tp.integrate_exp(h,a)
        for j,c in enumerate(integ):
            if not c:continue
            for m in range(max(0,r-shift),j+1):
                out+=c*comb(j,m)*(-1)**m*tp.shift_positive(N,a,j-m,d)*Q(factorial(m+shift),(-p)**(m+shift-r+1))
    return out

def apply_field(coef,H,N,qindex,demands=DEMANDS,shift=0):
    out=[Q(0)]*len(demands)
    for kappa,c,num,den in tp.scale_field(coef,qindex):
        pol,_=tp.quotient(num,den)
        for k,v in enumerate(pol):
            if v:
                for i,(p,r) in enumerate(demands):out[i]+=c*v*weighted_poly(k,H,kappa,N,p,r,shift)
    return out

def worker(row):
    path=ROOT/'boundary_batches'/Path(row['path']).name
    src=path.with_suffix('.stage2.jsonl') if row['stage']==1 else path
    marker=path.with_suffix('.result.json');dest=path.with_suffix('.negative_moments.json')
    while not marker.exists() or not src.exists():time.sleep(2)
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if dest.exists():
        old=json.loads(dest.read_text())
        if old['source_sha256']==digest:return old
    st=time.time();items=fb.br.rr.load(src)
    fb.DEMANDS=DEMANDS;mt.apply_field=apply_field
    values,count=fb.integrate_last_two(items)
    data={'source':src.name,'source_sha256':digest,'demands':DEMANDS,
        'meaning':'dimensionless boundary inverse-Euler moment, explicit scale insertions not yet restored',
        'values':list(map(str,values)),'rows':len(items),'terminal_terms':count,'seconds':time.time()-st}
    dest.write_text(json.dumps(data,indent=2));print('NEG_DONE',path.name,data['seconds'],flush=True)
    weighted_poly.cache_clear();mt.clear();fb.aword.cache_clear();fb.br.rr.clear()
    return data

def test():
    import random
    random.seed(9502);checks=0
    for _ in range(80):
        H=mt.canon((tuple(random.choice(((Q(0),Q(-1)),(Q(0),Q(0)),(Q(1),Q(2)))) for _ in range(random.randrange(5))),))
        k=random.randrange(5);kappa=random.randrange(2)
        for p,r in DEMANDS:
            ref=sum(mt.poly_functional(k,H,kappa,5,p,m)*Q(factorial(m),(-p)**(m-r+1)) for m in range(r,10))
            actual=weighted_poly(k,H,kappa,5,p,r)
            assert actual==ref,(H,k,p,r,actual,ref)
            checks+=1
    d={'test':'direct inverse-Euler functional versus complete boundary log polynomial','exact_comparisons':checks,'all_equal':True}
    (ROOT/'negative_functional_checks.json').write_text(json.dumps(d,indent=2));print(d)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');a=p.parse_args()
    if a.test:test()
