"""Regulated ordered kink moments for the next thermal trace coefficient.
Raw moments and analytic parameter derivatives, with exact primitive audits.
"""
from pathlib import Path
import json,os,time,sys
import faulthandler,signal
faulthandler.register(signal.SIGUSR1)
import sympy as sp
from functools import lru_cache
@lru_cache(maxsize=30000)
def parseK(text):return K.from_expr(sp.sympify(text))
import hyperlog_core as hc
from hyperlog_core import *
import ordered_moments as om
BASE=Path(__file__).resolve().parent

def product(*args,N):
    out={(tuple([()]*N),()):K.one}
    for a in args: out=om.multiply(out,a,N)
    return out

def log_affine(coord,offset,N):
    """log(offset*e+T_coord), coord is 1-based; offset>=0."""
    w=[()]*N;w[coord-1]=(-offset*e,)
    ans={(tuple(w),()):K.one}
    if offset: ans[(tuple([()]*N),(offset,))]=K.one
    return ans

def distance_log(i,j,N,absolute):
    if not absolute:return om.log_distance(i,j,N)
    ww=[()]*N;out={};c=(j-i)*e
    ww[i]=(GEN[j+1]+c,);out[(tuple(ww),())]=K.one;ww[i]=()
    ww[j]=(-c,);out[(tuple(ww),())]=K.one;ww[j]=()
    out[(tuple(ww),(j-i,))]=K.one
    return out

def initial(n,kind,deriv,kernel=True):
    absolute=kind.startswith('E')
    Q=kind.endswith('Q')
    N=n if absolute else n-1
    Xs=[j*e+GEN[j+1] for j in range(n)] if absolute else [K.zero]+[j*e+GEN[j] for j in range(1,n)]
    W=K.one
    if kernel:
        for i in range(n):
            for j in range(i+1,n): W*=(Xs[j]-Xs[i])**(2*(-1)**(i+j))
        if not absolute:W*=1-Xs[-1]
        if Q:W*=sum((Xs[i+1]-Xs[i] for i in range(0,n,2)),K.zero)
    base={(tuple([()]*N),()):W}
    if deriv=='base' and not absolute:return base,N
    lv={};ld={};ld2={}
    for i in range(n):
        for j in range(i+1,n):
            L=distance_log(i,j,N,absolute)
            for key,co in L.items():addto(lv,key,2*(-1)**(i+j)*co)
            if 'd' in deriv:
                L2=om.multiply(L,L,N)
                for key,co in L2.items():addto(ld,key,(-1)**(i+j)*co)
                if deriv=='dd':
                    for key,co in om.multiply(L2,L,N).items():addto(ld2,key,K(2)/3*(-1)**(i+j)*co)
    lv=clean(lv);ld=clean(ld)
    one={(tuple([()]*N),()):K.one}
    if deriv=='base':ins=one
    elif deriv=='v':ins=lv
    elif deriv=='vv':ins=product(lv,lv,N=N)
    elif deriv=='vvv':ins=product(lv,lv,lv,N=N)
    elif deriv=='d':ins=ld
    elif deriv=='vd':
        ins=product(lv,ld,N=N)
        for key,co in ld.items():addto(ins,key,co)
    elif deriv=='vvd':
        ins=product(lv,lv,ld,N=N)
        for key,co in product(lv,ld,N=N).items():addto(ins,key,2*co)
    elif deriv=='dd':
        ins=product(ld,ld,N=N)
        for key,co in ld2.items():addto(ins,key,co)
    else:raise ValueError(deriv)
    if absolute:
        ee={};ed={}
        for i in range(n):
            LL=log_affine(i+1,i,N)
            for key,co in LL.items():addto(ee,key,2*(-1)**i*co)
            if 'd' in deriv:
                for key,co in product(LL,LL,N=N).items():addto(ed,key,(-1)**i*co)
        ins=product(ins,clean(ee),N=N)
        if deriv=='d':
            for key,co in ed.items():addto(ins,key,co)
        if deriv=='vd':
            for key,co in product(clean(ed),lv,N=N).items():addto(ins,key,co)
        if deriv=='vvd':
            for key,co in product(clean(ed),lv,lv,N=N).items():addto(ins,key,co)
    return product(base,clean(ins),N=N),N

def rational_first(n,kind):
    """First gap integration by the Cauchy-square double-pole decomposition."""
    N=n-1;Xs=[K.zero]+[j*e+GEN[j] for j in range(1,n)]
    plus=Xs[::2];neg=Xs[3::2]
    out=[]
    for p in plus:
        rem=[x for x in plus if x!=p]
        rest=[(xx,1) for xx in rem]+[(yy,-1) for yy in neg]
        W=K.one
        for i,(xi,qi) in enumerate(rest):
            for xj,qj in rest[i+1:]:W*=(xi-xj)**(2*qi*qj)
        W*=1-Xs[-1]
        Csum=[2/(p-y) for y in neg]+[-2/(p-x) for x in rem]
        if kind=='Q':
            dip=sum(neg,K.zero)-sum(rem,K.zero)
            D=dip*W;simple=[W]+[D*co for co in Csum]
        else:D=W;simple=[W*co for co in Csum]
        root=p-e;keys=tuple([()]*N)
        out.append(((keys,()),-D/(GEN[2]-root)))
        out.append(((keys,()),-D/root))
        for ww,m in endpoint_fibrate((root,),2).items():
            keys=[()]*N;keys[1]=ww
            for C in simple:out.append(((tuple(keys),()),C*m))
    return out,N

def factored_first(n,kind,deriv):
    """Partial fractions before polynomial expansion of the full kernel.
    Each pole coefficient is a lower-point Cauchy-square kernel.
    """
    absolute=kind.startswith('E');Q=kind.endswith('Q')
    N=n if absolute else n-1
    Xs=[j*e+GEN[j+1] for j in range(n)] if absolute else [K.zero]+[j*e+GEN[j] for j in range(1,n)]
    active=0 if absolute else 1
    same=[i for i in range(n) if (i-active)%2==0 and i!=active]
    opposite=[i for i in range(n) if (i-active)%2]
    def Wsub(indices):
        W=K.one
        for k,i in enumerate(indices):
            for j in indices[k+1:]:W*=(Xs[j]-Xs[i])**(2*(-1)**(i+j))
        return W*(1-Xs[-1] if not absolute else 1)
    blocks=[]
    if absolute and n%2:
        assert not Q
        blocks.append(('poly',K.zero,0,Wsub(list(range(1,n)))))
    for p in opposite:
        rem=[i for i in range(n) if i not in (active,p)]
        C=Wsub(rem);root=Xs[p]-(0 if absolute else e)
        dlogs=[2/(Xs[p]-Xs[j]) for j in same]+[-2/(Xs[p]-Xs[j]) for j in opposite if j!=p]
        if Q:
            dip=sum(((-1)**(i+1)*Xs[i] for i in rem),K.zero)
            # Total dipole evaluated at the collision is precisely rem dip.
            D=C*dip;simple=[C*(-1 if absolute else 1)]+[D*cc for cc in dlogs]
        else:D=C;simple=[C*cc for cc in dlogs]
        blocks.append(('pole',root,2,D))
        blocks.extend(('pole',root,1,cc) for cc in simple)
    insert,_=initial(n,kind,deriv,kernel=False)
    items=list(insert.items());out=[];counter=0;now=time.time()
    print('factored first',n,kind,deriv,'blocks',len(blocks),'insertions',len(items),flush=True)
    for kk,(pole,root,power,C) in enumerate(blocks):
        local={}
        for (words,logs),ll in items:
            ant=integrate_basis(pole,root,power,words[0],1)
            rr=differentiate(ant,1)
            test=GEN[1]**power if pole=='poly' else (GEN[1]-root)**(-power)
            addto(rr,words[0],-test);assert not clean(rr)
            counter+=1
            for wa,cc in ant.items():
                for wb,cb in endpoint_value(cc,wa,1,GEN[2]).items():
                    for wf,mu in endpoint_fibrate(wb,2).items():
                        for wn,mv in shuffle(wf,words[1]).items():
                            keys=list(words);keys[0]=();keys[1]=wn
                            addto(local,(tuple(keys),logs),cb*mu*mv*ll)
                for wb,cb in endpoint_value(cc,wa,1,K.zero,lower=True).items():
                    assert not wb;keys=list(words);keys[0]=()
                    addto(local,(tuple(keys),logs),-cb*ll)
        # Sum small active-variable primitives before multiplying the spectator kernel.
        for key,coef in clean(local).items():out.append((key,C*coef))
        print('factored block',kk+1,'/',len(blocks),'terms',len(out),'seconds',time.time()-now,flush=True)
    print('factored first checks',counter,flush=True)
    return out,N

def emit(out,key,value):
    if isinstance(out,list):
        if value:out.append((key,value))
    else:addto(out,key,value)

def calc(n,kind,deriv='base',resume=0):
    start=time.time();tag=f'{kind}{n}_{deriv}';startidx=1
    if resume:
        rows=json.loads((BASE/f'{tag}_stage{resume}.json').read_text())
        expr=[((tuple(tuple(parseK(s) for s in w) for w in ww),tuple(logs)),parseK(c)) for ww,logs,c in rows]
        N=n if kind.startswith('E') else n-1;startidx=resume+1
    elif (n>=6 and deriv!='base') or (n>=5 and kind.startswith('E')):
        expr,N=factored_first(n,kind,deriv);startidx=2
        if isinstance(expr,dict):om.dump(BASE/f'{tag}_stage1.json',expr)
        else:
            (BASE/f'{tag}_stage1.json').write_text(json.dumps([([list(map(str,w)) for w in ww],list(logs),str(cc)) for (ww,logs),cc in expr]))
    elif n>=6 and deriv=='base' and not kind.startswith('E'):
        expr,N=rational_first(n,kind);startidx=2
    else:expr,N=initial(n,kind,deriv)
    print('initial',tag,'terms',len(expr),'dim',N,'seconds',time.time()-start,flush=True)
    audit=0
    for idx in range(startidx,N+1):
        out=[] if idx in (2,3) and idx<N else {};items=list(expr.items()) if isinstance(expr,dict) else expr
        for j,((words,logs),R) in enumerate(items):
            active=words[idx-1];ant=integrate_rat(R,active,idx)
            audit_primitive(ant,R,active,idx)
            audit+=1
            if idx<N:
                bound=GEN[idx+1]
                for wa,c in ant.items():
                    for wb,cb in endpoint_value(c,wa,idx,bound).items():
                        for wf,mu in endpoint_fibrate(wb,idx+1).items():
                            for wn,mv in shuffle(wf,words[idx]).items():
                                keys=list(words);keys[idx-1]=();keys[idx]=wn
                                emit(out,(tuple(keys),logs),cb*mu*mv)
                    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
                        assert not wb
                        keys=list(words);keys[idx-1]=();emit(out,(tuple(keys),logs),-cb)
            else:
                bound=1-(n-1)*e
                for wa,c in ant.items():
                    for wb,cb in endpoint_value(c,wa,idx,bound).items():
                        keys=[()]*N;keys[-1]=wb;emit(out,(tuple(keys),logs),cb)
                    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
                        assert not wb
                        emit(out,(tuple([()]*N),logs),-cb)
            if j%10==0:print('stage',idx,'item',j+1,'/',len(items),'terms',len(out),'seconds',time.time()-start,flush=True)
        expr=clean(out) if isinstance(out,dict) else out
        if isinstance(expr,dict):om.dump(BASE/f'{tag}_stage{idx}.json',expr)
        else:(BASE/f'{tag}_stage{idx}.json').write_text(json.dumps([([list(map(str,w)) for w in ww],list(logs),str(cc)) for (ww,logs),cc in expr]))
        print('stage done',idx,len(expr),time.time()-start,flush=True)
        # Clear the largest rational-function caches between stages.
        apart.cache_clear();integrate_basis.cache_clear();_pc=None
        if os.getenv('STOP_STAGE')==str(idx):return
    rows=[]
    for (ww,logs),c in expr.items():
        assert all(not q for q in ww[:-1]);word=ww[-1]
        aa=[int((a/e).as_expr()) for a in word]
        trailing=0
        for aa0 in reversed(aa):
            if aa0:break
            trailing+=1
        # Rescaling a tangential-base GPL generates powers of log(e).
        for jj in range(trailing+1):
            wr=aa[:-jj] if jj else aa
            rows.append((wr,list(logs)+[1]*jj,str(c/factorial(jj))))
    (BASE/f'{tag}_negative.json').write_text(json.dumps(rows))
    (BASE/f'{tag}_audit.json').write_text(json.dumps({'antiderivative_checks':audit,'seconds':time.time()-start,'terms':len(rows),'startidx':startidx,'audit_methods':hc.AUDIT_METHODS},indent=2))
    print('DONE',tag,len(rows),'seconds',time.time()-start,'checks',audit,flush=True)
    return rows

if __name__=='__main__':
    import argparse
    pa=argparse.ArgumentParser();pa.add_argument('n',type=int);pa.add_argument('kind');pa.add_argument('deriv',nargs='?',default='base');pa.add_argument('--resume',type=int,default=0)
    ar=pa.parse_args();calc(ar.n,ar.kind,ar.deriv,ar.resume)
