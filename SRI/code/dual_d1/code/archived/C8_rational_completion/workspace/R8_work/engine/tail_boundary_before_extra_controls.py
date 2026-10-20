"""Fresh scaled boundary evaluation for odd and vacuum tail moments.
No conjectured C8 value is an input. All outputs are block contributions until summed.
"""
import os,sys,json,time,hashlib,argparse
from functools import lru_cache
from pathlib import Path
from math import comb
import install_fastq
install_fastq.install_domain()
import scaled_b as sb
install_fastq.install_endpoint()
import native_fused
native_fused.install()
from hyperlog_core import *
import ordered_moments as om
import grouped_stage as gs
gs.install(from_stage=2)
import fast_exact_text
fast_exact_text.install()
F=sb.F; mt=sb.mt;tp=sb.tp;tb=sb.tb
ROOT=Path(__file__).resolve().parent.parent

def configure(kind,deriv):
    global KIND,DERIV,OUT,KAPPA
    KIND=kind;DERIV=deriv;KAPPA=-1 if kind=='Z' else 0
    OUT=ROOT/'tail_blocks'/f'{kind}_{deriv}';OUT.mkdir(parents=True,exist_ok=True)
    sb.OUT=tb.OUT=OUT
    tb.setup=setup;tb.last_two=last_two

def setup(n,face):
    N=n-2;ids=[0]+[i if i<face else i-1 for i in range(1,n)]
    coords=[K(i)+(GEN[j] if j else K.zero) for i,j in enumerate(ids)]
    factors=[]; lv={};ld={}
    for i in range(n):
        for j in range(i+1,n):
            sign=(-1)**(i+j);factors.append((coords[j]-coords[i],2*sign))
            ia,ib=ids[i],ids[j];c=K(j-i)
            if ia==ib:continue
            words=[()]*N; L={}
            if ia:
                words[ia-1]=(GEN[ib]+c,);addto(L,(tuple(words),()),K.one);words[ia-1]=()
            words[ib-1]=(-c,);addto(L,(tuple(words),()),K.one)
            for key,co in L.items(): addto(lv,key,2*sign*co)
            if 'd' in DERIV:
                for key,co in om.multiply(L,L,N).items():addto(ld,key,sign*co)
    if DERIV=='base':ins={(tuple([()]*N),()):K.one}
    elif DERIV=='v':ins=clean(lv)
    elif DERIV=='d':ins=clean(ld)
    elif DERIV=='vd':
        ins=om.multiply(clean(lv),clean(ld),N)
        for key,co in ld.items():addto(ins,key,co)
    else:raise ValueError(DERIV)
    return factors,clean(ins),N,ids

@lru_cache(maxsize=50000)
def proper_infinity(num,den,last):
    """z^-m coefficients of a proper fraction through m=last."""
    order=sum(o for a,o in den)
    needed=last+len(num)-1-order
    if needed<0:return tuple(F(0) for _ in range(last+1))
    ser=[F(1)]+[F(0)]*needed
    for a,o in den:
        fac=[F(comb(o+j-1,j))*a**j for j in range(needed+1)]
        ser=[sum((ser[k]*fac[j-k] for k in range(j+1)),F(0)) for j in range(needed+1)]
    out=[F(0)]*(last+1)
    for m in range(1,last+1):
        out[m]=sum((c*ser[m+k-order] for k,c in enumerate(num) if 0<=m+k-order<=needed),F(0))
    return tuple(out)

@lru_cache(maxsize=20000)
def shift_series(N,a,hp,d):
    """[eps^d](1-N eps)^a log(1-N eps)^hp, including negative a."""
    if d<0:return F(0)
    logser=(F(0),)+tuple(F(-N**j,j) for j in range(1,d+1))
    poly=(F(1),)
    for _ in range(hp):poly=tp.pmul(poly,logser)[:d+1]
    def bc(a,j):
        if j<0:return 0
        if a>=0:return comb(a,j) if j<=a else 0
        return (-1)**j*comb(j-a-1,j)
    return sum((c*bc(a,d-j)*(-N)**(d-j) for j,c in enumerate(poly) if j<=d),F(0))

@lru_cache(maxsize=150000)
def functional(num,den,H,kappa,N,p=0,m=0):
    """Exact upper cutoff + regularized lower endpoint, allowing kappa=-1.
    This extends the archived kappa=0,1 endpoint rule by retaining decaying
    large-z terms that can become finite after multiplication by epsilon^-1.
    """
    pol,rem=tp.quotient(num,den);out=F(0)
    def upper(a,rhs):
        d=a+p-kappa
        if d<0:return F(0)
        integ=mt.intlog(rhs) if a==0 else tp.integrate_exp(rhs,a)
        return sum((c*comb(j,m)*(-1)**m*shift_series(N,a,j-m,d)
                    for j,c in enumerate(integ) if j>=m and c),F(0))
    for k,c in enumerate(pol):
        if not c:continue
        if kappa==p and m==0:out+=c*mt.const_poly(k,H)
        for j in range(max(-1,k+1+p-kappa)+1):
            out+=c*upper(k-j+1,mt.large(H,j))
    if kappa==p and m==0:
        _,poles=tp.apart(rem,den)
        out+=sum((c*mt.const_pole(a,o,H) for a,o,c in poles),F(0))
    last=1+p-kappa
    if rem and last>=1:
        coef=proper_infinity(rem,den,last)
        for j in range(1,last+1):
            rhs=()
            for r in range(1,j+1):
                if coef[r]:rhs=tp.padd(rhs,tp.pscale(mt.large(H,j-r),coef[r]))
            out+=upper(1-j,rhs)
    return out

@lru_cache(maxsize=60000)
def parts(co,N):
    num,den=sb.rparts(co,N)
    scale=next((v for v in num if v),F(0))
    if not scale:return F(0),(),den
    return scale,tuple(v/scale for v in num),den

def last_two(items,n):
    tb.br.rr.rm.parseK.cache_clear();N=n-2;idx=N-1
    demands=[(0,0)]+[(p,r) for p in range(-n//2,0) for r in (0,1,2)]
    vals=[F(0)]*len(demands);st=time.time();count=0
    # Only these requested coefficients are evaluated; no physical tail
    # restoration is made in the dimensionless output at this stage.
    for j,((words,logs),R) in enumerate(items):
        assert not logs and not any(words[:idx-1])
        pp,po=apart(R,idx)
        bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
        def endpoint(c,w,sgn):
            nonlocal count
            scale,num,den=parts(c,N)
            if not scale:return
            H=mt.canon((sb.aword_scaled(w,N),sb.aword_scaled(words[N-1],N)))
            for k,(p,m) in enumerate(demands):
                v=functional(num,den,H,KAPPA,n-1,p,m)
                v-=(n-1)*functional(num,den,H,KAPPA+1,n-1,p,m)
                v-=functional((F(0),)+num,den,H,KAPPA+1,n-1,p,m)
                vals[k]+=sgn*scale*v
            count+=1
        for kind,root,power,pref in bases:
            audit_basis(kind,root,power,words[idx-1],idx)
            for w,c in integrate_basis(kind,root,power,words[idx-1],idx).items():
                for ww,cc in endpoint_value(c,w,idx,GEN[N]).items():endpoint(pref*cc,ww,1)
                for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
                    assert not ww;endpoint(pref*cc,(),-1)
        items[j]=None
        if j%100==0:print('TAIL_FINAL',KIND,DERIV,n,j,len(items),'value',vals[0],time.time()-st,flush=True)
    return vals[0],count,vals[1:]

def worker(name):
    f=OUT/name
    n=int(name.split('_')[0][1:])
    if n==4:
        src=f/'stage1.jsonl';items=tb.br.rr.load(src);demands=[(0,0)]+[(p,r) for p in range(-n//2,0) for r in (0,1,2)];values=[F(0)]*len(demands)
        for (words,logs),co in items:
            assert not logs and not any(words[:-1])
            scale,num,den=parts(co,2);H=mt.canon((sb.aword_scaled(words[-1],2),))
            for i,(p,m) in enumerate(demands):
                values[i]+=scale*(functional(num,den,H,KAPPA,3,p,m)-3*functional(num,den,H,KAPPA+1,3,p,m)-functional((F(0),)+num,den,H,KAPPA+1,3,p,m))
        meta=json.loads((f/'source.json').read_text())
        d=dict(status='complete_block_not_full_integral',id=name,value=str(values[0]),dimensionless_negative_inverse_euler=list(map(str,values[1:])),source_sha256=meta['source_sha256'],terminal_rows=len(items))
        (f/'result.json').write_text(json.dumps(d,indent=2))
    else:
        tb.worker(name)
    d=json.loads((f/'result.json').read_text());n=d.get('n',int(name.split('_')[0][1:]));d.update(kind=KIND,derivative=DERIV,kappa=KAPPA,
        demands=[[0,0]]+[[p,r] for p in range(-n//2,0) for r in (0,1,2)],
        method='dimensionless boundary with exact extended final functional')
    (f/'result.json').write_text(json.dumps(d,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['A','Z'],required=True);ap.add_argument('--deriv',default='d');ap.add_argument('--n',type=int);ap.add_argument('--face',type=int);ap.add_argument('--sources',action='store_true');ap.add_argument('--block')
    a=ap.parse_args();configure(a.kind,a.deriv)
    if a.sources:tb.sources(a.n,a.face)
    else:
        import fcntl
        with (OUT/a.block/'.compute.lock').open('a') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            worker(a.block)
