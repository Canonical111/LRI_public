import json, sys, time, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
digits=int(sys.argv[1]); mp.mp.dps=digits+40
c=build(480)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3=c['pi'],c['l2'],c['G'],c['z3']
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
def show(tag,r):
    print(tag,{k:r[k] for k in r if k not in ('coeffs','relation')},flush=True)
    if r.get('admissible'): print('   RELATION:',r['relation'],flush=True)
for tag,B in (('T1 level4 w<=4',monomials(lev4,4)),('T2 level4+sqrt2 w<=4',monomials(lev4,4,sqrt2=True))):
    t=time.time()
    r=lll_relation([K3]+[v for _,v,_ in B],digits,['K3']+[n for n,_,_ in B])
    show(tag+' (n=%d, %.0fs)'%(len(B)+1,time.time()-t),r)
