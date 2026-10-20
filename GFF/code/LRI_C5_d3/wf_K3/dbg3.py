import mpmath as mp
from kres import consts, summand
mp.mp.dps=60
c=consts(mp.mpf(3)/4)
src=open('k3flint.py').read()
src=src.replace("        ntails.append(","        globals().setdefault('_s',{})[l]=(c0,c1,ET,ES,Rp,P3)\n        ntails.append(")
ns={'__name__':'dbg'}
exec(compile(src,'k3f','exec'),ns)
ns['main'](300,9,300,60,60)
cv=lambda a: mp.mpf(a.mid().str(70,radius=False))
for l in (1,8):
    c0,c1,ET,ES,Rp,P3=ns['_s'][l]
    for n in (300,1000):
        X=mp.mpf(n)+mp.mpf(1)/2
        val=X**-3*(mp.fsum(cv(a)*X**-k for k,a in enumerate(c0))+mp.log(X)*mp.fsum(cv(a)*X**-k for k,a in enumerate(c1)))
        ex=summand(c,l,n)
        print(l,n,mp.nstr(ex,20),mp.nstr((val-ex)/ex,3))
