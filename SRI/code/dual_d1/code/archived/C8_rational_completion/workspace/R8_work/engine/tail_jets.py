"""Independent vector form of the complete boundary logarithmic jets.
These are boundary polynomials, not inverse-Euler moments.
"""
import tail_boundary as tb
from hyperlog_core import *
import json,time,sys,hashlib,argparse
from functools import lru_cache
from math import comb
F=tb.F;mt=tb.mt;tp=tb.tp;sb=tb.sb

@lru_cache(maxsize=70000)
def jet(num,den,H,kappa,N,p):
    pol,rem=tp.quotient(num,den);out=()
    def upper(a,rhs):
        d=a+p-kappa
        if d<0:return ()
        integ=mt.intlog(rhs) if a==0 else tp.integrate_exp(rhs,a)
        val=[F(0)]*len(integ)
        for j,c in enumerate(integ):
            if c:
                for m in range(j+1):val[m]+=c*comb(j,m)*(-1)**m*tb.shift_series(N,a,j-m,d)
        return tp.trim(val)
    for k,c in enumerate(pol):
        if not c:continue
        if kappa==p:out=tp.padd(out,(c*mt.const_poly(k,H),))
        for j in range(max(-1,k+1+p-kappa)+1):out=tp.padd(out,tp.pscale(upper(k-j+1,mt.large(H,j)),c))
    if kappa==p:
        _,poles=tp.apart(rem,den)
        out=tp.padd(out,(sum((c*mt.const_pole(a,o,H) for a,o,c in poles),F(0)),))
    last=1+p-kappa
    if rem and last>=1:
        cs=tb.proper_infinity(rem,den,last)
        for j in range(1,last+1):
            rhs=()
            for r in range(1,j+1):
                if cs[r]:rhs=tp.padd(rhs,tp.pscale(mt.large(H,j-r),cs[r]))
            out=tp.padd(out,upper(1-j,rhs))
    return out

def run(kind,deriv,name):
    tb.configure(kind,deriv);folder=tb.OUT/name;n=int(name.split('_')[0][1:]);N=n-2;idx=N-1
    source=folder/f'stage{max(1,N-2)}.jsonl';outpath=folder/'full_boundary_jets.json';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if outpath.exists():
        old=json.loads(outpath.read_text());assert old['source_sha256']==digest;print('REUSE',name);return
    items=tb.tb.br.rr.load(source);ps=list(range(-n//2,1));jets={p:() for p in ps};count=0;st=time.time()
    def endpoint(co,w,other,sgn):
        nonlocal count
        scale,num,den=tb.parts(co,N)
        if not scale:return
        H=mt.canon((sb.aword_scaled(w,N),sb.aword_scaled(other,N)))
        for p in ps:
            v=jet(num,den,H,tb.KAPPA,n-1,p)
            v=tp.padd(v,tp.pscale(jet(num,den,H,tb.KAPPA+1,n-1,p),-(n-1)))
            v=tp.padd(v,tp.pscale(jet((F(0),)+num,den,H,tb.KAPPA+1,n-1,p),-1))
            jets[p]=tp.padd(jets[p],tp.pscale(v,sgn*scale))
        count+=1
    for j,((words,logs),R) in enumerate(items):
        assert not logs and not any(words[:idx-1]);pp,po=apart(R,idx)
        bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
        for kin,root,power,pref in bases:
            audit_basis(kin,root,power,words[idx-1],idx)
            for w,c in integrate_basis(kin,root,power,words[idx-1],idx).items():
                for ww,cc in endpoint_value(c,w,idx,GEN[N]).items():endpoint(pref*cc,ww,words[N-1],1)
                for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
                    assert not ww;endpoint(pref*cc,(),words[N-1],-1)
        items[j]=None
        if j%300==0:print('JETS',kind,n,deriv,name,j,len(items),time.time()-st,flush=True)
    ref=json.loads((folder/'result.json').read_text())
    data=[ref['value']]+ref['dimensionless_negative_inverse_euler'];checks=0
    for (p,m),value in zip(ref['demands'],data):
        actual=jets[p][m] if m<len(jets[p]) else F(0)
        assert str(actual)==value,(p,m,actual,value);checks+=1
    d={'id':name,'kind':kind,'deriv':deriv,'source_sha256':digest,'source':str(source.relative_to(tb.ROOT)),
       'boundary_polynomials':{str(p):list(map(str,v)) for p,v in jets.items()},'agreement_with_separate_scalar_functional':checks,
       'seconds':time.time()-st,'endpoint_terms':count,'no_new_residue_or_C8_conjecture_input':True}
    outpath.write_text(json.dumps(d,indent=2));print('JET_DONE',d['id'],d['seconds'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('deriv');p.add_argument('block');a=p.parse_args()
    import fcntl
    tb.configure(a.kind,a.deriv)
    with (tb.OUT/a.block/'.jets.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        run(a.kind,a.deriv,a.block)
