import mpmath as mp
from kres import consts, spin
import k3flint
mp.mp.dps=40
c=consts(mp.mpf(3)/4)
import flint
# monkeypatch: get heads+ntails per spin by running main with small L and capturing internals
src=open('k3flint.py').read()
src=src.replace("    body = sum(","    globals()['_per']=[heads[l]+ntails[l] for l in range(L)]; globals()['_h']=heads; globals()['_t']=ntails\n    body = sum(")
ns={'__name__':'dbg'}
exec(compile(src,'k3f','exec'),ns)
ns['main'](200,9,300,60,60)
for l in (0,1,7,8):
    v=spin(c,l)
    w=mp.mpf(ns['_per'][l].mid().str(45,radius=False))
    print(l,mp.nstr(v,25),mp.nstr(w,25),mp.nstr(v-w,3))
