"""Fresh lower-moment prediction of the mixed Q6 power divergences.
Extracts rational log polynomials directly from the archived finite-cutoff
2-/4-kink functions, then differentiates the vacuum-normalization products.
No new mixed six-kink integral or guessed C8 is read.
"""
from pathlib import Path
from functools import lru_cache
from itertools import product
import json,time
import sympy as s
import asymptotic_gpl as ag
ROOT=Path(__file__).resolve().parent
# Projection is on pure endpoint constants, after the full raw integration.
ag.Z=lambda word: s.S.One if not word else s.S.Zero
ag.big.cache_clear()
L=ag.ell
DER={(0,0):'base',(1,0):'v',(0,1):'d',(1,1):'vd'}
POWERS={(2,'Q'):(0,1),(2,'Z'):(-1,0),(4,'Q'):(-2,-1,0),(4,'Z'):(-2,-1)}
@lru_cache(None)
def raw(n,kind,iv,idd,p):
    path=ROOT/f'{kind}{n}_{DER[iv,idd]}_negative.json'
    rows=json.loads(path.read_text());out=ag.extract_rows(rows,n-1,p,None)
    subs={x:0 for x in out.free_symbols if x!=L}
    for atom in out.atoms(s.log,s.polylog,s.zeta):
        assert not atom.has(L);subs[atom]=0
    out=s.expand(out.subs(subs).subs(s.pi,0))
    assert out.free_symbols <= {L}
    assert all(c.is_Rational for c in s.Poly(out,L).all_coeffs())
    return out

def convolution(factors,iv,idd,p):
    out=0
    for ps in product(*(POWERS[f] for f in factors)):
        if sum(ps)!=p:continue
        v=1
        for (n,k),a,b,power in zip(factors,iv,idd,ps):v*=raw(n,k,a,b,power)
        out+=v
    return s.expand(out)

def main():
    st=time.time();result=[];table={}
    terms=[(1,[(4,'Q'),(2,'Z')]),(-1,[(2,'Q'),(2,'Z'),(2,'Z')]),(1,[(2,'Q'),(4,'Z')])]
    targets={-2:(-7,-32),-1:(2193,555)}
    for p in (-2,-1):
        out=0
        for sign,factors in terms:
            n=len(factors)
            for i in range(n):
                for j in range(n):
                    iv=[int(k==i) for k in range(n)];idd=[int(k==j) for k in range(n)]
                    out+=sign*convolution(factors,iv,idd,p)
        out=s.expand(out);vals=[out.coeff(L,j) for j in (0,1)];assert tuple(vals)==targets[p],(p,vals,out)
        result.append({'power':p,'polynomial':str(out),'constant':str(vals[0]),'single_log':str(vals[1]),'matches_archived_prediction':True})
    for (n,k),ps in POWERS.items():
        for v,d in DER:
            for p in ps:table[f'{k}{n}_{DER[v,d]}_p{p}']=str(raw(n,k,v,d,p))
    report={'identity':'Q6 singular part = Q4 Z2 - Q2 Z2^2 + Q2 Z4; derivative v delta before evaluation',
        'method':'fresh cutoff extraction of complete archived lower moments followed by product differentiation','prediction':result,'lower_rational_polynomials':table,'seconds':time.time()-st,'new_R6_integral_read':False,'C8_conjecture_read':False}
    (ROOT.parent/'lower_divergence_prediction.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='lower_rational_polynomials'},indent=2))
if __name__=='__main__':main()
