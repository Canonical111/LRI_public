import json, time, mpmath as mp
from consts import build
from bases import monomials
from irel import lll_relation
mp.mp.dps=470
c=build(480); D=420
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3,s2,lam=c['pi'],c['l2'],c['G'],c['z3'],c['s2'],c['lam']
log=open('pslq_K3.log','a')
def run(tag,target,B,tname='K3'):
    t=time.time()
    r=lll_relation([target]+[v for _,v,_ in B],D,[tname]+[n for n,_,_ in B])
    line='%-55s n=%3d  %s | no relation with max|c| < %.3g (GS) | allowed %.3g | %.0fs'%(tag,r['n'],('HIT '+r['relation']) if r.get('admissible') else 'none',r['maxcoeff_bound'],r['allowed_maxcoeff'],time.time()-t)
    if r.get('internal_relations'): line+=' | internal: '+str(r['internal_relations'])
    print(line,flush=True); log.write(line+'\n'); log.flush()
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
lev8=lev4+[('lam',lam,1),('L8_2',c['L8_2'],2),('L8_3',c['L8_3'],3),('L8_4',c['L8_4'],4)]
B4=monomials(lev4,4)
run('[420d] level4 mixed w<=4',K3,B4)
run('[420d] level4 mixed w<=4 (+sqrt2)',K3,monomials(lev4,4,sqrt2=True))
run('[420d] level8-Dirichlet mixed w<=4',K3,monomials(lev8,4))
run('[420d] level8-Dirichlet mixed w<=4 (+sqrt2)',K3,monomials(lev8,4,sqrt2=True))
g=c['G14']
gam=[]
for nm,v in (('g4',g**4/pi**2),('g8',g**8/pi**4),('ig4',pi**4/g**4)):
    for mn,mv,mw in monomials([('pi',pi,1),('l2',l2,1),('G',G,2)],2):
        gam.append((nm+'*'+mn,v*mv,0))
run('[420d] level4 w<=4 + Gamma(1/4)^{4,8,-4} x w<=2',K3,B4+gam)
