import json, mpmath as mp
from consts import build
from lvals import build as lbuild
from bases import monomials
from irel import lll_relation
mp.mp.dps=470
c=build(480); Lv=lbuild(440); D=420
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3=c['pi'],c['l2'],c['G'],c['z3']
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
B4=[(n,v) for n,v,_ in monomials(lev4,4)]
log=open('pslq_K3.log','a')
def run(tag,extra):
    B=B4+extra
    r=lll_relation([K3]+[v for _,v in B],D,['K3']+[n for n,_ in B])
    line='%-55s n=%3d  %s | no relation with max|c| < %.3g (GS) | allowed %.3g'%(tag,r['n'],('HIT '+r['relation']) if r.get('admissible') else 'none',r['maxcoeff_bound'],r['allowed_maxcoeff'])
    if r.get('internal_relations'): line+=' | internal: '+str(r['internal_relations'])
    print(line,flush=True); log.write(line+'\n')
ext=[]
for form,k in (('E32',2),('f16w3',3),('f8w3',3),('g8w4',4)):
    for s in range(1,k+3):
        if s>5 or (form,s) in (('f16w3',1),('g8w4',1)): continue
        v=Lv['L_%s_%d'%(form,s)]
        ext.append(('pi^%d L_%s(%d)'%(4-s,form,s),v*pi**(4-s)))
run('[420d] level4 w<=4 + CM L-values (E32,f16w3,f8w3,g8w4) x pi^(4-s)',ext)
ext2=ext+[('l2*'+n,l2*v/pi) for n,v in ext]
run('[420d] ... + log2 x pi^(3-s) L',ext2)
