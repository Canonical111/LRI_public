from full_runner import *
from boundary_jet_functional import jet_basis
import sys,random,sympy as s
sys.path.insert(0,'/mnt/data/P8_final_run')
import linear_boundary as lb
import asymptotic_gpl as ag
random.seed(15376);start=time.time();cases=0
for i in range(250):
 w=tuple(random.choice([0,-1,-2,-3,-5]) for _ in range(random.randrange(0,7)))
 kind=random.choice(['pole','poly']);a=random.choice([0,-1,-2,-4]);p=random.randrange(1,5) if kind=='pole' else random.randrange(0,5)
 power,log=random.choice([(0,0),(-1,0),(-1,1),(-2,0),(-2,2)])
 val=s.expand(sum(s.Rational(c.numerator,c.denominator)*ag.Z(tuple(int(x) for x in ww)) for ww,c in lb.functional(kind,a,p,w,7,0,True,power,log)))
 ref=jet_basis(kind,a,p,w,6,7,power,log)
 assert s.expand(val-ref)==0,(kind,a,p,w,power,log,s.expand(val-ref))
 cases+=1
print('EXACT_LINEAR_BOUNDARY_TEST',cases,time.time()-start,flush=True)
(ROOT/'linear_boundary_check.json').write_text(json.dumps({'exact_cases':cases,'agreement':True,'seconds':time.time()-start},indent=2))
