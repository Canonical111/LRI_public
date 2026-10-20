from functools import lru_cache
from collections import defaultdict
from fractions import Fraction as Q
from analytic_sources import shuffle
@lru_cache(maxsize=200000)
def factor(w):
    i=0;out=[]
    while i<len(w):
        j=i+1;k=i
        while j<len(w) and w[k]<=w[j]:
            if w[k]<w[j]:k=i
            else:k+=1
            j+=1
        step=j-k
        while i<=k:out.append(w[i:i+step]);i+=step
    return tuple(out)
@lru_cache(maxsize=400000)
def primitive(w):
    ff=factor(w)
    if len(ff)==1:return {w:1}
    sh=dict(shuffle(ff[0],w[len(ff[0]):]))
    div=sh.pop(w);out=defaultdict(int)
    for v,c in sh.items():
        assert v<w
        for p,d in primitive(v).items():out[p]-=c*d
    assert all(c%div==0 for c in out.values())
    return {p:c//div for p,c in out.items() if c}
