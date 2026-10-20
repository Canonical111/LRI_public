from lyndon import primitive
from analytic_sources import fixed_letters, convergent_zeta_polynomial, NATURAL, multiplier, Q
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import time,json,sys
@lru_cache(maxsize=10000)
def inverse(w,m):
    states={()}
    for letter in w[::-1]:
        new=set()
        for st in states:
            ext=((1,0),)+st+((0,0),)
            for i in range(len(st)+1):
                for b,a in (ext[i],ext[i+1]):
                    nb=1-b;na=letter-a
                    if na<nb:continue
                    ns=st[:i]+((nb,na),)+st[i:]
                    if max((a for b,a in ns if b==0),default=0)+max((a for b,a in ns if b==1),default=0)<=m:new.add(ns)
        states=new
    return tuple(s for s in states if s[0][0]==0 and s[-1][0]==1)
def row(st,m):
    out=defaultdict(int)
    for w,c in fixed_letters(tuple((b,a if b else -a) for b,a in st)).items():
        if max(w)!=m:continue
        for v,d in primitive(w).items():out[v]+=c*d
    return {w:Q(c) for w,c in out.items() if c}
def fullrow(st):
    out=defaultdict(Q)
    for w,c in fixed_letters(tuple((b,a if b else -a) for b,a in st)).items():out[w]+=c
    for powers,c in convergent_zeta_polynomial(tuple(b for b,a in st)).items():
        words=sum(((NATURAL[i],)*k for i,k in enumerate(powers)),())
        for w,d in multiplier(words).items():out[w]-=c*d
    return {w:c for w,c in out.items() if c}
def label(st):
    bs=0
    for b,a in st:bs=bs*2+b
    return ('D',len(st),bs,0,*(a for b,a in st))
class Exact:
    def __init__(self):self.basis={}
    def reduce(self,row,expression):
        row=dict(row);expression=dict(expression)
        while row:
            lead=max(row)
            if lead not in self.basis:break
            fac=row[lead];b,e=self.basis[lead]
            for k,c in b.items():
                row[k]=row.get(k,0)-fac*c
                if not row[k]:del row[k]
            for k,c in e.items():
                expression[k]=expression.get(k,0)-fac*c
                if not expression[k]:del expression[k]
        return row,expression
    def insert(self,rr,index):
        r,e=self.reduce(rr,{index:Q(1)})
        if not r:return False
        lead=max(r);fac=r[lead];self.basis[lead]=({k:c/fac for k,c in r.items()},{k:c/fac for k,c in e.items()});return True
