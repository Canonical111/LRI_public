#!/usr/bin/env python3
"""Exact small-weight multiple-zeta endpoint reductions.

Adapted from the endpoint-identity portion of the preceding C7 certificate
verifier in this conversation. This module derives the convergent binary
values used by the new Euler-kernel exclusion. It does not rerun the C7
period certificate or any RG/kink integral. Only Python's standard library
is needed for this module; other package modules use SymPy and mpmath.
"""
from __future__ import annotations
import argparse, json, time, hashlib
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as Q
from functools import lru_cache
from itertools import product
from math import comb, factorial

Word=tuple[int,...]
@lru_cache(maxsize=60000)
def shuffle(a:Word,b:Word)->dict[Word,int]:
    if not a:return {b:1}
    if not b:return {a:1}
    out=defaultdict(int)
    for w,c in shuffle(a[1:],b).items():out[(a[0],)+w]+=c
    for w,c in shuffle(a,b[1:]).items():out[(b[0],)+w]+=c
    return dict(out)
@lru_cache(None)
def stuffle(a:Word,b:Word)->dict[Word,int]:
    if not a:return {b:1}
    if not b:return {a:1}
    out=defaultdict(int)
    for w,c in stuffle(a[1:],b).items():out[(a[0],)+w]+=c
    for w,c in stuffle(a,b[1:]).items():out[(b[0],)+w]+=c
    for w,c in stuffle(a[1:],b[1:]).items():out[(a[0]+b[0],)+w]+=c
    return dict(out)
def indices(w:Word)->Word:
    result=[];count=1
    for b in w:
        if b==0:count+=1
        elif b==1:result.append(count);count=1
        else:raise ValueError('Nonbinary letter')
    assert count==1
    return tuple(result)
def bits(a:Word)->Word:return sum(((0,)*(v-1)+(1,) for v in a),())
def convergent(n:int):return [(0,)+m+(1,) for m in product((0,1),repeat=n-2)]
def derive_weight_six():
    words=convergent(6);cs=[indices(w) for w in words];cols={w:i for i,w in enumerate(cs)};rows=[]
    def equation(data,rhs):
        data={w:c for w,c in data.items() if c}
        assert all(w in cols for w in data),'Divergent terms did not cancel'
        rows.append([Q(data.get(w,0)) for w in cs]+[Q(v) for v in rhs])
    for p in range(1,4):
        aa=[(1,)] if p==1 else [indices(w) for w in convergent(p)]
        for a in aa:
            for b in map(indices,convergent(6-p)):
                row=defaultdict(int)
                for w,c in shuffle(bits(a),bits(b)).items():row[indices(w)]+=c
                for w,c in stuffle(a,b).items():row[w]-=c
                equation(row,(0,0))
    for w in words:
        row=defaultdict(int);row[indices(w)]+=1;row[indices(tuple(1-v for v in w[::-1]))]-=1
        equation(row,(0,0))
    equation({(6,):1},(1,0))
    equation(stuffle((3,),(3,)),(0,1))
    equation(stuffle((2,),(4,)),(Q(7,4),0))
    original=[r[:] for r in rows];rank=0
    for col in range(16):
        pivot=next((j for j in range(rank,len(rows)) if rows[j][col]),None)
        if pivot is None:raise AssertionError('Endpoint equations do not determine all constants')
        rows[rank],rows[pivot]=rows[pivot],rows[rank]
        div=rows[rank][col];rows[rank]=[v/div for v in rows[rank]]
        for j in range(len(rows)):
            if j==rank or not rows[j][col]:continue
            fac=rows[j][col];rows[j]=[a-fac*b for a,b in zip(rows[j],rows[rank])]
        rank+=1
    values={cs[i]:tuple(rows[i][16:]) for i in range(16)}
    for row in original:
        for j in (0,1):assert sum(row[i]*values[cs[i]][j] for i in range(16))==row[16+j]
    table={w:tuple((-1)**len(indices(w))*v for v in values[indices(w)]) for w in words}
    return table,{'equations':len(original),'rank':rank,'arithmetic':'rational','basis':['zeta(6)','zeta(3)^2']}
def gamma_height(weight):
    A={}
    for n in range(2,weight+1):
        for j in range(1,n):A[(j,n-j,(n,))]=-Q(comb(n,j),n)
    def mul(a,b):
        out=defaultdict(Q)
        for (i,j,z),c in a.items():
            for (k,l,y),d in b.items():
                if i+j+k+l<=weight:out[(i+k,j+l,tuple(sorted(z+y)))]+=c*d
        return {k:v for k,v in out.items() if v}
    out=defaultdict(Q);power={(0,0,()):Q(1)}
    for k in range(1,weight//2+1):
        power=mul(power,A)
        for key,c in power.items():out[key]-=c/factorial(k)
    def basis(z):
        if z==(weight,):return (Q(1),Q(0))
        if z==(2,2):return (Q(5,2),Q(0))
        if z==(2,3):return (Q(0),Q(1))
        if z==(2,4):return (Q(7,4),Q(0))
        if z==(3,3):return (Q(0),Q(1))
        if z==(2,2,2):return (Q(35,8),Q(0))
        raise ValueError(z)
    result={j:[Q(0),Q(0)] for j in range(1,weight)}
    for (i,j,z),c in out.items():
        if i+j==weight:
            b=basis(z)
            for k in (0,1):result[i][k]+=c*b[k]
    return result

def derive_convergent_table(n):
    ws=convergent(n);cs=list(map(indices,ws));rows=[];labels=[]
    def eq(d,rhs,label):
        d={w:c for w,c in d.items() if c};assert set(d)<=set(cs)
        rows.append([Q(d.get(w,0)) for w in cs]+list(rhs));labels.append(label)
    for p in range(2,n//2+1):
        for a in map(indices,convergent(p)):
            for b in map(indices,convergent(n-p)):
                d=defaultdict(int)
                for w,c in shuffle(bits(a),bits(b)).items():d[indices(w)]+=c
                for w,c in stuffle(a,b).items():d[w]-=c
                eq(d,(Q(0),Q(0)),('convergent_double_shuffle',a,b))
    for w in ws:
        d=defaultdict(int);d[indices(w)]+=1;d[indices(tuple(1-a for a in w[::-1]))]-=1
        eq(d,(Q(0),Q(0)),('duality',w))
    height=gamma_height(n)
    for j,rhs in height.items():eq({(j+1,)+(1,)*(n-j-1):1},rhs,('convergent_beta_coefficient',j,n-j))
    if n==4:eq(stuffle((2,),(2,)),(Q(5,2),Q(0)),('even_zeta_product',))
    if n==5:eq(stuffle((2,),(3,)),(Q(0),Q(1)),('basis_product',2,3))
    if n==6:
        eq(stuffle((2,),(4,)),(Q(7,4),Q(0)),('even_zeta_product',))
        eq(stuffle((3,),(3,)),(Q(0),Q(1)),('basis_product',3,3))
    original=[r[:] for r in rows];rank=0;count=len(cs)
    for col in range(count):
        pivot=next((i for i in range(rank,len(rows)) if rows[i][col]),None)
        if pivot is None:continue
        rows[rank],rows[pivot]=rows[pivot],rows[rank];d=rows[rank][col];rows[rank]=[a/d for a in rows[rank]]
        for i in range(len(rows)):
            if i!=rank and rows[i][col]:
                fac=rows[i][col];rows[i]=[a-fac*b for a,b in zip(rows[i],rows[rank])]
        rank+=1
    assert rank==count
    answer={w:tuple((-1)**len(indices(w))*a for a in rows[i][count:]) for i,w in enumerate(ws)}
    # Verify every original identity, not merely the pivot equations.
    zeta_values={indices(w):tuple((-1)**len(indices(w))*c for c in value) for w,value in answer.items()}
    for row in original:
        for k in (0,1):
            assert sum(row[i]*zeta_values[cs[i]][k] for i in range(count))==row[count+k]
    return answer,{'weight':n,'rank':rank,'unknowns':count,'equations':len(rows),'height_one_coefficients':{str(j):list(map(str,r)) for j,r in height.items()},'values':[[list(w),list(map(str,c))] for w,c in answer.items()],'source_labels':labels}

def derive_convergent_tables():
    tables={};reports=[]
    for n in range(2,7):
        tables[n],report=derive_convergent_table(n);reports.append(report)
    return tables,{'method':'convergent shuffle/stuffle, duality, and the beta/Gamma height-one integral',
                   'arithmetic':'rational','weights':reports}

BINARY_ALL,MZV_REPORT=derive_convergent_tables()
WEIGHT_SIX=BINARY_ALL[6]
assert WEIGHT_SIX==derive_weight_six()[0]  # independent cross-check

