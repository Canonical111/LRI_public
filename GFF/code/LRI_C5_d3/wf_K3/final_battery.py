"""Consolidated integer-relation battery for K3 (FLINT LLL; hygiene rule n*log10(maxcoeff) <= digits-10).
Writes pslq_K3_results_<D>.json.  'bound' = Gram-Schmidt lower bound on max|coeff| of any relation."""
import json, sys, time, mpmath as mp
from consts import build
from lvals import build as lbuild
from bases import monomials
from irel import lll_relation
D=int(sys.argv[1]); mp.mp.dps=D+50
c=build(480); Lv=lbuild(440)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3,s2,lam,L8=c['pi'],c['l2'],c['G'],c['z3'],c['s2'],c['lam'],c['L8_2']
A=2+4*l2-pi; U=2*pi**3-56*z3
lev4=[('pi',pi,1),('l2',l2,1),('G',G,2),('z3',z3,3),('ImLi3h',c['ImLi3h'],3),('Li4h',c['Li4h'],4),('b4',c['b4'],4),('ImLi4h',c['ImLi4h'],4)]
lev8=lev4+[('lam',lam,1),('L8_2',L8,2),('L8_3',c['L8_3'],3),('L8_4',c['L8_4'],4)]
B4=[(n,v) for n,v,_ in monomials(lev4,4)]
tests=[]
tests.append(('level-4 colored-MZV space, mixed weight <=4 (complete: 1,pi,log2,G,zeta3,ImLi3((1+i)/2),Li4(1/2),beta(4),ImLi4((1+i)/2) and products)','K3',K3,B4))
tests.append(('same, Q(sqrt2) coefficients','K3',K3,[(n,v) for n,v,_ in monomials(lev4,4,sqrt2=True)]))
tests.append(('level-8 Dirichlet-type generators (+log(1+sqrt2),L(2,chi_-8),L(3,chi_8),L(4,chi_-8)), mixed weight <=4','K3',K3,[(n,v) for n,v,_ in monomials(lev8,4)]))
tests.append(('same, Q(sqrt2) coefficients','K3',K3,[(n,v) for n,v,_ in monomials(lev8,4,sqrt2=True)]))
tests.append(('Phi3=2K3-AU as quadratic form in {1,pi^2,G,L(2,chi_-8)} with Q(sqrt2) coefficients','Phi3',2*K3-A*U,[(n,v) for n,v,_ in monomials([('P',pi**2,2),('G',G,2),('L8',L8,2)],4,sqrt2=True)]))
g=c['G14']; gam=[]
for nm,v in (('g4',g**4/pi**2),('g8',g**8/pi**4),('ig4',pi**4/g**4)):
    for mn,mv,mw in monomials([('pi',pi,1),('l2',l2,1),('G',G,2)],2): gam.append((nm+'*'+mn,v*mv))
tests.append(('level-4 basis + Gamma(1/4)^{4,8,-4} x (weight<=2 level-4)','K3',K3,B4+gam))
ext=[]
for form,k in (('E32',2),('f16w3',3),('f8w3',3),('g8w4',4)):
    for s in range(1,k+3):
        if s>5 or (form,s) in (('f16w3',1),('g8w4',1)): continue
        ext.append(('pi^%d L_%s(%d)'%(4-s,form,s),Lv['L_%s_%d'%(form,s)]*pi**(4-s)))
tests.append(('level-4 basis + CM newform L-values pi^(4-s)L(f,s), f in {E32, eta(4t)^6, eta(t)^2eta(2t)eta(4t)eta(8t)^2, eta(2t)^4eta(4t)^4}','K3',K3,B4+ext))
out=[]
for tag,tn,t,B in tests:
    t0=time.time()
    r=lll_relation([t]+[v for _,v in B],D,[tn]+[n for n,_ in B])
    rec=dict(test=tag,target=tn,n=r['n'],digits=D,result=('HIT: '+r['relation']) if r.get('admissible') else 'no admissible relation',
             maxcoeff_lower_bound=r['maxcoeff_bound'],hygiene_allowed_maxcoeff=r['allowed_maxcoeff'],internal=r.get('internal_relations'),seconds=round(time.time()-t0,1))
    if r.get('found') and not r.get('admissible'): rec['shortest_vector_maxcoeff']=r['maxcoeff']
    print(json.dumps(rec),flush=True); out.append(rec)
json.dump(out,open('pslq_K3_results_%d.json'%D,'w'),indent=1)
