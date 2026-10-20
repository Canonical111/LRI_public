import json, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
mp.mp.dps=460
c=build(480)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
lev4=[('pi',c['pi'],1),('l2',c['l2'],1),('G',c['G'],2),('z3',c['z3'],3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
B=monomials(lev4,4)
print(mp.nstr(K3,30), [ (n,mp.nstr(v,10)) for n,v,_ in B[:5]])
r=lll_relation([K3]+[v for _,v,_ in B],420,['K3']+[n for n,_,_ in B])
print(r['coeffs']); print(r['relation'][:500])
