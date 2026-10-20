#!/usr/bin/env python3
"""Independent exact verification in the FREE WORD shuffle algebra.

The discovery program uses Lyndon polynomials and modular elimination. This
verifier does neither: it expands each multiplier back into ordinary shuffle
words and checks the supplied rational combination coefficient by coefficient.
All analytic source rows and the weight-six endpoint constants are regenerated.
Only Python's standard library is required. No numerical period values enter.
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

def clean(row):return {w:c for w,c in row.items() if c}
def add_scaled(out,row,scale=Q(1)):
    for w,c in row.items():
        out[w]+=scale*c
        if not out[w]:del out[w]
@lru_cache(maxsize=6000)
def fixed_letters(aa:tuple[tuple[int,int],...]):
    if not aa:return {():1}
    out=defaultdict(int);endpoints=((1,0),)+aa+((0,0),)
    for i,(s,c) in enumerate(aa):
        tail=fixed_letters(aa[:i]+aa[i+1:])
        for (sn,cn),sign in ((endpoints[i],1),(endpoints[i+2],-1)):
            if sn==s:continue
            root=Q(c-cn,sn-s)
            assert root.denominator==1 and root<=0
            for w,v in tail.items():out[(-int(root),)+w]+=sign*v
    return clean(out)
def zeta_word(n):
    assert 2<=n<=6
    return {(2,)+(1,)*(n-1):-Q(2**(n-1),2**(n-1)-1)}
@lru_cache(None)
def binary_value(w):
    n=len(w);a,b=BINARY_ALL[n][w]
    out=defaultdict(Q);add_scaled(out,zeta_word(n),a)
    if b:
        assert n in (5,6)
        left,right=((2,1),(2,1,1)) if n==5 else ((2,1,1),(2,1,1))
        factor=Q(8,3) if n==5 else Q(16,9)
        add_scaled(out,shuffle(left,right),b*factor)
    return clean(out)
# Canonical positive-zeta generators: R_(0,1)=zeta(2),
# R_(0,1,1)=zeta(3), R_(0,1,1,1,1)=zeta(5).
# These follow directly from t=z/(1-z), endpoint regularization and duality.
NATURAL=((0,1),(0,1,1),(0,1,1,1,1))
def zeta_polynomial(n):
    table={2:{(1,0,0):Q(1)},3:{(0,1,0):Q(1)},
           4:{(2,0,0):Q(2,5)},5:{(0,0,1):Q(1)},6:{(3,0,0):Q(8,35)}}
    return table[n]
def convergent_zeta_polynomial(w):
    n=len(w);a,b=BINARY_ALL[n][w]
    out=defaultdict(Q);add_scaled(out,zeta_polynomial(n),a)
    if b:
        assert n in (5,6)
        out[(1,1,0) if n==5 else (0,2,0)]+=b
    return clean(out)
@lru_cache(None)
def endpoint_regularization(w):
    """Reg_{z->1} G(w;z) for words on {0,1} ending in 1.

    A leading 1 is removed by the exact shuffle of (1,) with the tail;
    Reg G(1;z)=0. No numerical endpoint limits are involved.
    """
    assert w and w[-1]==1 and set(w)<={0,1}
    if w[0]==0:return convergent_zeta_polynomial(w)
    rows=shuffle((1,),w[1:]);lead=rows[w];out=defaultdict(Q)
    for v,c in rows.items():
        if v!=w:add_scaled(out,endpoint_regularization(v),-Q(c,lead))
    return clean(out)
@lru_cache(None)
def binary_infinity_value(w):
    """R_w by t=z/(1-z): omega_0 -> omega_0-omega_1,
    omega_{-1} -> -omega_1. The endpoint constant is preserved.
    """
    assert len(w)>=2 and w[-1]==1 and set(w)<={0,1}
    out=defaultdict(Q)
    for v in product(*[(0,1) if a==0 else (1,) for a in w]):
        add_scaled(out,endpoint_regularization(v),Q((-1)**sum(v)))
    return clean(out)

@lru_cache(maxsize=512)
def source(label:tuple):
    kind,n,bs,d,*aa=label;out=defaultdict(Q)
    if kind in ('C','D'):
        bb=tuple((bs>>(n-1-i))&1 for i in range(n))
        assert bb[0]==0 and bb[-1]==1 and len(aa)==n
        assert all(a>=b for a,b in zip(aa,bb))
        add_scaled(out,fixed_letters(tuple((b,a if b else -a) for a,b in zip(aa,bb))))
        if kind=='C':
            add_scaled(out,binary_value(bb),Q(-1))
        else:
            for powers,c in convergent_zeta_polynomial(bb).items():
                factors=sum(((NATURAL[i],)*k for i,k in enumerate(powers)),())
                add_scaled(out,multiplier(factors),-c)
    elif kind=='S':
        assert d>0 and len(aa)==n and aa[-1]>0 and min(aa)>=0
        out[tuple(d*a for a in aa)]+=1
        for j in range(n+1):add_scaled(out,shuffle((d,)*j,tuple(aa[j:])),Q(-1))
    elif kind=='I':
        ww=tuple(aa);assert len(ww)==n and n>=2 and all(ww<ww[j:] for j in range(1,n))
        out[ww]+=1
        for powers,c in binary_infinity_value(ww).items():
            factors=sum(((NATURAL[i],)*k for i,k in enumerate(powers)),())
            add_scaled(out,multiplier(factors),-c)
    elif kind=='Z':
        assert n==1 and len(aa)==1 and aa[0] in (0,1);out[(aa[0],)]+=1
    elif kind=='L':
        assert n==1 and len(aa)==2 and min(aa)>0
        a,b=aa;out[(a*b,)]+=1;out[(a,)]-=1;out[(b,)]-=1
    else:raise ValueError('Unknown analytic source')
    return clean(out)
def decode_multiplier(code:int):
    assert 0<=code<2**64
    out=[]
    while code:
        n=code>>61;assert 1<=n<=6
        count=3+4*n;raw=(code>>(64-count))&((1<<(4*n))-1)
        w=tuple((raw>>(4*(n-i-1)))&15 for i in range(n))
        assert all(w<w[j:] for j in range(1,n)),('Not a Lyndon generator',w)
        out.append(w);code=(code<<count)&((1<<64)-1)
    return tuple(out)
@lru_cache(maxsize=8000)
def multiplier(words):
    out={():1}
    for w in words:
        d=defaultdict(int)
        for v,c in out.items():
            for z,m in shuffle(v,w).items():d[z]+=c*m
        out=dict(d)
    return out

def verify(target_path:Path,cert_path:Path,weight:int,log_every:int=20000):
    start=time.perf_counter()
    target={tuple(w):Q(c) for w,c in json.loads(target_path.read_text()) if len(w)==weight}
    residual=defaultdict(Q,target);count=0;expanded=0
    with cert_path.open() as stream:
        for line in stream:
            parts=line.split();assert len(parts)>=7
            c=Q(parts[0]);context=decode_multiplier(int(parts[1]));kind=parts[2]
            label=(kind,)+tuple(map(int,parts[3:]));n=label[1]
            assert sum(map(len,context))+n==weight
            row=source(label);mul=multiplier(context)
            for v,a in row.items():
                for w,b in mul.items():
                    for z,m in shuffle(v,w).items():
                        residual[z]-=c*a*b*m;expanded+=1
                        if not residual[z]:del residual[z]
            count+=1
            if log_every and count%log_every==0:print('VERIFY',weight,count,'residual',len(residual),'seconds',time.perf_counter()-start,flush=True)
    if residual:raise AssertionError(f'Weight {weight}: {len(residual)} exact residual words; examples: {list(residual.items())[:3]}')
    report={'weight':weight,'target_words':len(target),'certificate_rows':count,'expanded_terms':expanded,
            'residual_words':0,'arithmetic':'Python Fraction','space':'free shuffle words, not Lyndon polynomials',
            'seconds':time.perf_counter()-start,'certificate_sha256':hashlib.sha256(cert_path.read_bytes()).hexdigest()}
    print(json.dumps(report),flush=True);return report

def source_denominator(weight):
    from math import lcm
    den=1
    for n in range(2,weight+1):
        for w in convergent(n):
            for c in binary_value(w).values():den=lcm(den,Q(c).denominator)
            for c in convergent_zeta_polynomial(w).values():den=lcm(den,Q(c).denominator)
        for head in product((0,1),repeat=n-1):
            for c in binary_infinity_value(head+(1,)).values():den=lcm(den,c.denominator)
    return den

def verify_integer(target_path:Path,cert_path:Path,weight:int,log_every:int=20000):
    """Exact free-word verification after clearing all rational denominators.

    Denominators of analytic source rows come only from the finite binary
    tables; confluence fibration, scaling and logarithm relations are integral.
    Every actual source coefficient is checked against the clearing factor.
    """
    from math import lcm
    start=time.perf_counter()
    target={tuple(w):Q(c) for w,c in json.loads(target_path.read_text()) if len(w)==weight}
    den=1
    for c in target.values():den=lcm(den,c.denominator)
    with cert_path.open() as f:
        for line in f:den=lcm(den,Q(line.split(None,1)[0]).denominator)
    den*=source_denominator(weight)
    residual={w:(den//c.denominator)*c.numerator for w,c in target.items()}
    count=0;expanded=0
    with cert_path.open() as f:
        for line in f:
            parts=line.split();assert len(parts)>=7
            c=Q(parts[0]);context=decode_multiplier(int(parts[1]));label=(parts[2],)+tuple(map(int,parts[3:]));n=label[1]
            assert n+sum(map(len,context))==weight
            if den%c.denominator:raise AssertionError('Certificate denominator was not cleared')
            factor=(den//c.denominator)*c.numerator
            row=source(label)
            if not context:
                for v,a in row.items():
                    a=Q(a)
                    if factor%a.denominator:raise AssertionError('Source denominator was not cleared')
                    term=(factor//a.denominator)*a.numerator
                    value=residual.get(v,0)-term;expanded+=1
                    if value:residual[v]=value
                    else:residual.pop(v,None)
            else:
                mul=multiplier(context)
                for v,a in row.items():
                    a=Q(a)
                    if factor%a.denominator:raise AssertionError('Source denominator was not cleared')
                    ca=(factor//a.denominator)*a.numerator
                    for w,b in mul.items():
                        cb=ca*b
                        for z,m in shuffle(v,w).items():
                            value=residual.get(z,0)-cb*m;expanded+=1
                            if value:residual[z]=value
                            else:residual.pop(z,None)
            count+=1
            if log_every and count%log_every==0:print('VERIFY INTEGER',weight,count,'residual',len(residual),'seconds',time.perf_counter()-start,flush=True)
    if residual:raise AssertionError(f'Weight {weight}: {len(residual)} exact residual words; examples: {list(residual.items())[:3]}')
    report={'weight':weight,'target_words':len(target),'certificate_rows':count,'expanded_terms':expanded,
            'residual_words':0,'arithmetic':'Python integers after exact denominator clearing',
            'common_denominator_bits':den.bit_length(),'space':'free shuffle words, not Lyndon polynomials',
            'seconds':time.perf_counter()-start,'certificate_sha256':hashlib.sha256(cert_path.read_bytes()).hexdigest()}
    print(json.dumps(report),flush=True);return report

def main():
    if not __debug__:raise RuntimeError('Run this verifier without Python -O.')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=Path(__file__).with_name('C7_linear_words.json'))
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--weights',type=int,nargs='+',default=[2,3,4,5,6]);p.add_argument('--report',type=Path)
    args=p.parse_args();reports=[]
    for n in args.weights:reports.append(verify_integer(args.target,Path(str(args.prefix)+f'.w{n}.certificate.txt'),n))
    result={'status':'exact period certificate verified','weight_six_endpoint_derivation':MZV_REPORT,'checks':reports}
    if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
