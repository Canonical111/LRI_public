import json, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
mp.mp.dps=470
c=build(480); D=420
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3,s2,lam,L8=c['pi'],c['l2'],c['G'],c['z3'],c['s2'],c['lam'],c['L8_2']
A=2+4*l2-pi; U=2*pi**3-56*z3
Phi=2*K3-A*U
print('Phi3 =',mp.nstr(Phi,30))
def run(tag,target,B):
    r=lll_relation([target]+[v for _,v,_ in B],D,['T']+[n for n,_,_ in B])
    print(tag,'n=%d'%r['n'],'HIT '+r['relation'] if r.get('admissible') else 'none','| maxcoeff bound %.3g'%r['maxcoeff_bound'],'| internal:',r.get('internal_relations','-'),flush=True)
w2=[('P',pi**2,2),('G',G,2),('L8',L8,2)]
run('quad(pi2,G,L8) +sqrt2, deg<=2 incl 1',Phi,monomials(w2,4,sqrt2=True))
w1=[('pi',pi,1),('l2',l2,1),('lam',lam,1)]
run('w<=4 in pi,l2,lam,G,L8,z3 (+sqrt2)',Phi,monomials(w1+[('G',G,2),('L8',L8,2),('z3',z3,3)],4,sqrt2=True))
