import json, re, mpmath as mp, sys
sys.path.insert(0,'.')
from consts import build
from lvals import build as lbuild
mp.mp.dps=470
c=build(480); Lv=lbuild(440)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
pi,l2,G,z3=c['pi'],c['l2'],c['G'],c['z3']
env=dict(K3=K3,pi=pi,l2=l2,G=G,z3=z3,ImLi3h=c['ImLi3h'],Li4h=c['Li4h'],b4=c['b4'],ImLi4h=c['ImLi4h'])
rel=[x for x in json.load(open('pslq_K3_results_300.json')) if 'HIT' in x['result']][0]['result'][5:]
tot=mp.mpf(0); scale=0
for term in rel.split(' + '):
    co,nm=term.split('*',1); co=int(co)
    m=re.match(r'pi\^(-?\d) L_(\w+)\((\d)\)',nm)
    if m:
        v=pi**int(m.group(1))*Lv['L_%s_%s'%(m.group(2),m.group(3))]
    else:
        v=mp.mpf(1)
        if nm!='1':
            for f in nm.split('*'):
                b,_,e=f.partition('^'); v*=env[b]**(int(e) if e else 1)
    tot+=co*v; scale=max(scale,abs(co*v))
print('residual',mp.nstr(tot,5),'rel',mp.nstr(tot/scale,5))
