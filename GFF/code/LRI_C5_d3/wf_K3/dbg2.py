import mpmath as mp
from kres import consts, summand, spin
mp.mp.dps=45
c=consts(mp.mpf(3)/4)
src=open('k3flint.py').read()
src=src.replace("    body = sum(","    globals()['_h']=heads; globals()['_t']=ntails\n    body = sum(")
ns={'__name__':'dbg'}
exec(compile(src,'k3f','exec'),ns)
ns['main'](200,9,300,60,60)
for l in (1,8):
    hm=mp.fsum(summand(c,l,n) for n in range(300))
    hf=mp.mpf(ns['_h'][l].mid().str(50,radius=False)); tf=mp.mpf(ns['_t'][l].mid().str(50,radius=False))
    tot=spin(c,l)
    print(l,'head diff',mp.nstr(hm-hf,3),' tail mp',mp.nstr(tot-hm,20),' tail fl',mp.nstr(tf,20),' diff',mp.nstr(tot-hm-tf,3))
    print('  summand at n=0:',mp.nstr(summand(c,l,0),20))
