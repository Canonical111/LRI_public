import json, sys, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
digits=int(sys.argv[2]); mp.mp.dps=digits+40
c=build(480)
K3=mp.mpf(json.load(open(sys.argv[1]))['K3'])
pi,l2,G,z3=c['pi'],c['l2'],c['G'],c['z3']
A=2+4*l2-pi; U=2*pi**3-56*z3
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
B=monomials(lev4,4)
print('basis size',len(B))
for tname,t in (('K3',K3),):
    r=lll_relation([t]+[v for _,v,_ in B],digits,[tname]+[n for n,_,_ in B])
    print(json.dumps(r,indent=0,default=str))
