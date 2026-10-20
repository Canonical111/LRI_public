"""Evaluate the full exact finite-cutoff responses by convergent Taylor ODE.
Compared against independent direct Sobol integration of original kernels.
"""
import mpmath as mp,sympy as s,json,sys,time
from pathlib import Path
from functools import lru_cache
from hyperlog_core import shuffle
ROOT=Path(__file__).resolve().parent
mp.mp.dps=65

@lru_cache(None)
def detrail(word):
    # Return {non-trailing-zero word: polynomial in log T}.
    L=s.Symbol('L')
    if not word:return {():s.S.One}
    if all(a==0 for a in word):return {():L**len(word)/s.factorial(len(word))}
    if word[-1]!=0:return {word:s.S.One}
    sh=shuffle((0,),word[:-1]).copy();mu=sh.pop(word);out={}
    for w,c in detrail(word[:-1]).items():out[w]=out.get(w,0)+L*c
    for ww,nn in sh.items():
        for w,c in detrail(ww).items():out[w]=out.get(w,0)-nn*c
    return {w:s.expand(c/mu) for w,c in out.items() if c}

def finite_values(words,T,ntaylor=200):
    closure={()}
    for word in words:
        for k in range(len(word)+1):closure.add(word[k:])
    ws=sorted(closure,key=lambda w:(len(w),w));ix={w:i for i,w in enumerate(ws)}
    tails=[ix[w[1:]] if w else 0 for w in ws];aa=[mp.mpf(-w[0]) if w else mp.mpf(-1) for w in ws]
    vals=[mp.mpf(1)]+[mp.mpf(0)]*(len(ws)-1);t=mp.mpf(0)
    while t<T:
        h=min(T-t,mp.mpf('.35')*(t if t>0 and any(a==0 for a in aa[1:]) else t+1))
        prev=vals.copy();ans=vals.copy();hn=mp.mpf(1)
        for n in range(1,ntaylor+1):
            cur=[mp.mpf(0)]
            for i in range(1,len(ws)):
                if t==0 and aa[i]==0:cur.append(cur[tails[i]]/n)
                else:cur.append((prev[tails[i]]-(n-1)*prev[i])/(t-aa[i])/n)
            hn*=h;ans=[ans[i]+hn*cur[i] for i in range(len(ws))];prev=cur
        t+=h;vals=ans
    return {w:vals[ix[w]] for w in words}

def run(n,kind,der='base',eps=mp.mpf(1)/8):
    f=ROOT/f'{kind}{n}_{der}_negative.json';rr=json.loads(f.read_text());exprs=[];want=set();start=time.time()
    for word,logs,cc in rr:
        word=tuple(-a for a in word)
        ds=detrail(word);want.update(ds);exprs.append((ds,logs,cc))
    T=(1-(n-1)*eps)/eps;vals=finite_values(want,T)
    ans=mp.mpf(0);le=mp.log(eps);Lt=mp.log(T);se=s.Symbol('e');L=s.Symbol('L')
    for ds,logs,cc in exprs:
        c=s.sympify(cc).subs({se:s.Float(str(eps),65),**{s.Symbol(f'Z{k}'):s.zeta(k) for k in range(2,7)}})
        val=mp.mpf(str(s.N(c,65)))
        val*=mp.fprod(le+mp.log(a) for a in logs)
        val*=sum(vals[w]*mp.mpf(str(s.N(p.subs(L,s.Float(str(Lt),65)),65))) for w,p in ds.items())
        ans+=val
    print(n,kind,der,'epsilon',mp.nstr(eps),'exact integral',mp.nstr(ans,55),'seconds',time.time()-start,flush=True)
    return str(ans)

if __name__=='__main__':
    out={}
    for n,k,d in [(5,'EA','base'),(6,'Q','v'),(7,'A','base')]:
        if (ROOT/f'{k}{n}_{d}_negative.json').exists():out[f'{k}{n}_{d}']=run(n,k,d)
    (ROOT/'finite_cutoff_hyperlog.json').write_text(json.dumps(out,indent=2))
