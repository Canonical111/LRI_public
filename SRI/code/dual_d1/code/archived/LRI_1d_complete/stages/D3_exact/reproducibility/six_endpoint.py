from hyperlog_core import *
from pathlib import Path
import json,time
start=time.time();T=1-5*e
raw=json.loads((Path(__file__).resolve().parent / 'six_primitive.json').read_text())
result={};polecheck={}
def fib(w):
    shifted=tuple(a if sub(a,0,K.zero)==0 else a-1+v+5*e for a in w)
    return endpoint_fibrate(shifted,2)
for ws,cs in raw:
    w=tuple(K.from_expr(__import__('sympy').sympify(a.replace('^','**'))) for a in ws)
    c=K.from_expr(__import__('sympy').sympify(cs.replace('^','**')))
    try:cT=sub(c,2,T)
    except ZeroDivisionError:
        pol,poles=apart(c,2)
        cp=poles.pop((T,1),K.zero)
        assert cp and not any(a==T for a,n in poles)
        cT=sum((cv*T**n for n,cv in pol.items()),K.zero)+sum((cv/(T-a)**n for (a,n),cv in poles.items()),K.zero)
        for ww,k in fib(w).items():addto(polecheck,ww,cp*k)
        assert w and w[0]!=T
        for ww,k in fib(w[1:]).items():addto(result,ww,cp*k/(T-w[0]))
    for ww,k in fib(w).items():addto(result,ww,cT*k)
    if not w:addto(result,(),-sub(c,2,K.zero))
assert not clean(polecheck),{tuple(map(str,w)):str(c) for w,c in clean(polecheck).items()}
result=clean(result)
assert all(a.denom==K.ring.one and not a.diff(v) and not a.diff(u) and sub(a,0,K.zero)==0 for w in result for a in w)
ser=[]
for w,c in result.items():
    nums=tuple(int((a/e).as_expr()) for a in w)
    ser.append((nums,str(c)))
(Path(__file__).resolve().parent / 'six_negative.json').write_text(json.dumps(ser))
print('Endpoint pole cancellation: EXACT PASS')
print('negative words',len(result),'maxweight',max(map(len,result)))
print('seconds',time.time()-start)
