import json, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
mp.mp.dps=300
c=build(480)
a=json.load(open('spins_a.json'));b=json.load(open('spins_b.json'))
pi,l2,G,z3=c['pi'],c['l2'],c['G'],c['z3']
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
lev8=lev4+[('lam',c['lam'],1),('L8_2',c['L8_2'],2),('L8_3',c['L8_3'],3),('L8_4',c['L8_4'],4)]
for d in ('d1','d3'):
    for l in ('0','1','2'):
        x,y=mp.mpf(a[d][l]),mp.mpf(b[d][l]); dig=int(-mp.log10(abs(x-y)/abs(y)))-1
        print(d,'l=',l,mp.nstr(y,20),'agree',dig,flush=True)
        for tag,B in (('lev4',monomials(lev4,4)),('lev4+s2',monomials(lev4,4,sqrt2=True))):
            r=lll_relation([y]+[v for _,v,_ in B],min(dig,235),['I']+[n for n,_,_ in B])
            print('   ',tag,'n',r['n'],'admissible' if r.get('admissible') else 'none','maxcoeff_bound %.3g'%r['maxcoeff_bound'],r.get('relation','')[:400] if r.get('admissible') else '',flush=True)
